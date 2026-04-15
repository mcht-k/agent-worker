"""Git operations — branch lifecycle, merge, worktree management."""

import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple

log = logging.getLogger(__name__)


def _run(cmd: list, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    log.debug("git: %s (cwd=%s)", " ".join(cmd), cwd)
    result = subprocess.run(
        cmd, cwd=str(cwd),
        capture_output=True, text=True, encoding='utf-8', timeout=120,
    )
    if check and result.returncode != 0:
        log.error("git failed: %s\nstderr: %s", " ".join(cmd), result.stderr.strip())
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result


def current_branch(repo: Path) -> str:
    r = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
    return r.stdout.strip()


def branch_exists(repo: Path, branch: str) -> bool:
    r = _run(["git", "rev-parse", "--verify", branch], repo, check=False)
    return r.returncode == 0


def is_repo_clean(repo: Path) -> bool:
    r = _run(["git", "status", "--porcelain"], repo)
    return r.stdout.strip() == ""


def fetch(repo: Path) -> None:
    _run(["git", "fetch", "--all", "--prune"], repo, check=False)


def checkout(repo: Path, branch: str) -> None:
    result = _run(["git", "checkout", branch], repo, check=False)
    if result.returncode != 0:
        # Verify the branch is actually correct — non-zero may come from a
        # post-checkout hook failure even when the checkout itself succeeded.
        try:
            actual = current_branch(repo)
        except Exception:
            actual = ""
        if actual == branch:
            log.warning(
                "git checkout %s exited %d but branch is correct "
                "(likely a post-checkout hook warning): %s",
                branch, result.returncode, result.stderr.strip()[:300],
            )
            return
        log.error("git failed: git checkout %s\nstderr: %s", branch, result.stderr.strip())
        raise subprocess.CalledProcessError(
            result.returncode, ["git", "checkout", branch],
            result.stdout, result.stderr,
        )


def create_branch(repo: Path, branch: str, base: str) -> None:
    """Create and checkout a new branch from base."""
    fetch(repo)
    if branch_exists(repo, branch):
        log.info("Branch %s already exists, checking out", branch)
        checkout(repo, branch)
        return
    _run(["git", "checkout", "-b", branch, base], repo)


def commit_all(repo: Path, message: str) -> bool:
    """Stage all changes (except queue.md) and commit. Returns False if nothing to commit.

    queue.md is excluded here because it is committed separately by
    commit_tracking_files() on the base/target branch — committing it
    on a feature branch causes merge conflicts.
    """
    _run(["git", "add", "-A"], repo)
    # Unstage queue.md so it is never committed on a feature branch
    _run(["git", "reset", "HEAD", ".agent/queue.md"], repo, check=False)
    r = _run(["git", "diff", "--cached", "--quiet"], repo, check=False)
    if r.returncode == 0:
        return False  # nothing staged
    _run(["git", "commit", "-m", message], repo)
    return True


def push(repo: Path, branch: str) -> None:
    _run(["git", "push", "-u", "origin", branch], repo)


def merge_branch(
    repo: Path,
    source: str,
    target: str,
    mode: str = "direct",
) -> Tuple[bool, str]:
    """Merge source branch into target. Returns (success, error_message)."""
    try:
        commit_tracking_files(repo, f"queue: {source} → merging to {target}")
        checkout(repo, target)
        _run(["git", "pull", "origin", target], repo, check=False)

        if mode == "rebase":
            _run(["git", "rebase", source], repo)
        else:
            _run(["git", "merge", source, "--no-ff",
                  "-m", f"Merge {source} into {target}"], repo)
        return True, ""
    except subprocess.CalledProcessError as e:
        stdout = (e.stdout or "").strip()
        stderr = (e.stderr or "").strip()
        error = "\n".join(filter(None, [stdout, stderr])) or str(e)
        # Abort failed merge
        _run(["git", "merge", "--abort"], repo, check=False)
        _run(["git", "rebase", "--abort"], repo, check=False)
        return False, error


def delete_branch(repo: Path, branch: str) -> None:
    _run(["git", "branch", "-d", branch], repo, check=False)
    _run(["git", "push", "origin", "--delete", branch], repo, check=False)


# ── Worktree support ─────────────────────────────────────────────────────────

def create_worktree(repo: Path, worktree_dir: Path, branch: str, base: str) -> Path:
    """Create a git worktree for isolated parallel execution."""
    worktree_path = worktree_dir / branch.replace("/", "-")
    if worktree_path.exists():
        log.info("Worktree %s already exists", worktree_path)
        return worktree_path

    worktree_dir.mkdir(parents=True, exist_ok=True)

    if not branch_exists(repo, branch):
        _run(["git", "branch", branch, base], repo)

    _run(["git", "worktree", "add", str(worktree_path), branch], repo)
    return worktree_path


def remove_worktree(repo: Path, worktree_path: Path) -> None:
    if worktree_path.exists():
        _run(["git", "worktree", "remove", str(worktree_path), "--force"], repo, check=False)


def commit_tracking_files(repo: Path, message: str) -> bool:
    """Commit any pending changes to orchestrator-managed tracked files (queue.md).

    Called before every branch switch so git doesn't refuse checkout due to
    uncommitted queue state changes.
    """
    queue_md = repo / ".agent" / "queue.md"
    if not queue_md.exists():
        return False
    _run(["git", "add", str(queue_md)], repo, check=False)
    r = _run(["git", "diff", "--cached", "--quiet"], repo, check=False)
    if r.returncode == 0:
        return False  # nothing staged
    _run(["git", "commit", "-m", message], repo)
    log.info("Committed queue state: %s", message)
    return True


def setup_task_branch(
    repo: Path,
    work_branch: str,
    base_branch: str,
    use_worktrees: bool = False,
    worktree_dir: Optional[Path] = None,
) -> Path:
    """Set up the branch for a task. Returns the working directory path.

    If use_worktrees is True, creates a worktree and returns its path.
    Otherwise, creates/checks out the branch in the main repo and returns repo path.
    """
    fetch(repo)

    # Commit any pending queue.md changes (e.g. status → in_progress set just before
    # this call) so that git allows switching branches.
    commit_tracking_files(repo, f"queue: {work_branch} → in_progress")

    if use_worktrees and worktree_dir:
        return create_worktree(repo, worktree_dir, work_branch, base_branch)

    create_branch(repo, work_branch, base_branch)
    return repo


def finalize_task_branch(
    repo: Path,
    work_branch: str,
    target_branch: str,
    merge_mode: str = "direct",
    auto_push: bool = True,
    delete_after: bool = False,
    working_dir: Optional[Path] = None,
) -> Tuple[bool, str]:
    """After agent finishes: merge work branch to target and optionally push.

    By the time this is called, the scheduler should have already committed all
    agent work via _commit_work(). The safety-net commit below only fires if
    something slipped through (e.g. agent wrote files outside normal flow).
    """
    # Safety net: commit anything still uncommitted before switching branches
    effective_dir = working_dir if (working_dir and working_dir != repo) else repo
    if not is_repo_clean(effective_dir):
        log.warning(
            "Safety-net commit: uncommitted files found on %s before merge "
            "(should have been committed by _commit_work earlier)",
            work_branch,
        )
        commit_all(effective_dir, f"chore: safety-net commit [{work_branch}]")

    # If using worktree, push from worktree first
    if working_dir and working_dir != repo:
        push_result = _run(
            ["git", "push", "-u", "origin", work_branch],
            working_dir, check=False,
        )
        if push_result.returncode != 0:
            return False, f"Push from worktree failed: {push_result.stderr}"
        remove_worktree(repo, working_dir)

    if work_branch == target_branch:
        # No merge needed — direct push
        if auto_push:
            push(repo, work_branch)
        return True, ""

    # Push feature branch to remote before merging (for visibility / backup)
    if auto_push:
        push_result = _run(["git", "push", "-u", "origin", work_branch], repo, check=False)
        if push_result.returncode != 0:
            log.warning("Could not push feature branch %s: %s",
                        work_branch, push_result.stderr.strip()[:200])

    success, error = merge_branch(repo, work_branch, target_branch, merge_mode)
    if not success:
        return False, error

    if auto_push:
        push(repo, target_branch)

    if delete_after:
        delete_branch(repo, work_branch)

    return True, ""
