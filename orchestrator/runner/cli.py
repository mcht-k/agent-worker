#!/usr/bin/env python3
"""Agent Runner CLI — universal AI task orchestrator."""

import argparse
import logging
import shutil
import sys
import re
from pathlib import Path
from datetime import datetime

from . import __version__
from .config import load_config, Config
from .queue_manager import load_queue, add_entry, save_queue, update_entry_status
from .models import TaskStatus
from .scheduler import run_once, run_daemon, get_agent


def _get_template_path(filename: str) -> Path:
    """Resolve a template file from the installed package.

    Uses importlib.resources.files (3.9+) with fallback to
    importlib.resources.path (3.8).  Returns a Path object.
    """
    try:
        from importlib.resources import files
        ref = files("runner.templates").joinpath(filename)
        # as_file is needed for zipped packages; for normal installs
        # the traversable already _is_ a Path.
        p = Path(str(ref))
        if p.exists():
            return p
    except (ImportError, TypeError):
        pass

    # Python 3.8 fallback
    try:
        from importlib import resources as _res
        with _res.path("runner.templates", filename) as p:
            return Path(p)
    except Exception:
        pass

    # Last resort: relative path (editable install / running from source)
    return Path(__file__).parent / "templates" / filename

# ── ANSI colors ──────────────────────────────────────────────────────────────
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
GRAY = "\033[37m"
BOLD = "\033[1m"
NC = "\033[0m"

STATUS_STYLE = {
    "queued":                  (GRAY,   "[.]"),
    "blocked":                 (YELLOW, "[B]"),
    "in_progress":             (YELLOW, "[>]"),
    "waiting_for_limit_reset": (BLUE,   "[W]"),
    "review_required":         (YELLOW, "[?]"),
    "completed":               (GREEN,  "[+]"),
    "failed":                  (RED,    "[X]"),
    "cancelled":               (GRAY,   "[-]"),
}


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")


def resolve_paths(args) -> tuple:
    """Resolve repo root and .agent directory from CLI args."""
    repo = Path(args.repo).resolve() if hasattr(args, "repo") and args.repo else Path.cwd()
    agent_dir = repo / ".agent"
    return repo, agent_dir


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_init(args):
    """Initialize a repo with .agent/ structure and default config."""
    repo = Path(args.path).resolve() if args.path else Path.cwd()
    agent_dir = repo / ".agent"

    if agent_dir.exists() and (agent_dir / "config.yml").exists():
        print(f"{YELLOW}Warning: .agent/ already exists in {repo}{NC}")
        if not args.force:
            print("Use --force to overwrite")
            return 1

    dirs = ["tasks", "state", "logs", "transcripts", "results", "locks", "context"]
    for d in dirs:
        (agent_dir / d).mkdir(parents=True, exist_ok=True)

    # Copy templates
    for tmpl in ["config.yml", "queue.md", "PROJECT.md", ".env.example"]:
        src = _get_template_path(tmpl)
        dst = agent_dir / tmpl
        if src.exists() and (not dst.exists() or args.force):
            shutil.copy2(src, dst)

    # Add runtime dirs and secrets to .gitignore
    gitignore = repo / ".gitignore"
    ignore_entries = [
        ".agent/.env",
        ".agent/state/",
        ".agent/logs/",
        ".agent/locks/",
        ".agent/transcripts/",
        ".agent/results/",
        ".agent/worktrees/",
        ".agent/context/",
    ]
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    new_entries = [e for e in ignore_entries if e not in existing]
    if new_entries:
        with open(gitignore, "a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("\n# Agent Runner runtime artifacts\n")
            for entry in new_entries:
                f.write(entry + "\n")

    print(f"{GREEN}Initialized .agent/ in {repo}{NC}")
    print(f"  config:  {agent_dir / 'config.yml'}")
    print(f"  queue:   {agent_dir / 'queue.md'}")
    print(f"  tasks:   {agent_dir / 'tasks/'}")
    print(f"\nNext steps:")
    print(f"  1. Edit .agent/config.yml")
    print(f"  2. Create task files in .agent/tasks/")
    print(f"  3. Add tasks: agent-runner add tasks/my-task.md")
    print(f"  4. Run: agent-runner run")
    return 0


def cmd_run(args):
    """Run one scheduler cycle."""
    repo, agent_dir = resolve_paths(args)
    config = load_config(agent_dir / "config.yml")
    did_work = run_once(repo, agent_dir, config)
    if not did_work:
        print(f"{GRAY}No work to do{NC}")
    return 0


def cmd_daemon(args):
    """Run scheduler in continuous loop."""
    repo, agent_dir = resolve_paths(args)
    config = load_config(agent_dir / "config.yml")
    run_daemon(repo, agent_dir, config)
    return 0


def cmd_status(args):
    """Show queue status."""
    repo, agent_dir = resolve_paths(args)
    queue_path = agent_dir / "queue.md"
    entries = load_queue(queue_path)

    if not entries:
        print(f"{GRAY}Queue is empty{NC}")
        return 0

    # Column widths
    print(f"\n{BOLD}Agent Runner — Queue Status{NC}")
    print("=" * 102)
    print(f"{BOLD}{'Id':<6} {'Task':<30} {'Status':<24} {'Agent':<8} {'Model':<22} {'Att':>3} {'Target':<12}{NC}")
    print("-" * 102)

    from .state_manager import load_state as _load_state
    state_dir = agent_dir / "state"

    counts = {}
    for e in entries:
        color, icon = STATUS_STYLE.get(e.status.value, (NC, " "))
        task_name = e.task_file.replace("tasks/", "").replace(".md", "")
        # Show resolved model from state file (actual model used), fall back to queue value
        model = e.model if e.model not in ("—", "") else "auto"
        if state_dir.exists():
            st = _load_state(state_dir, e.id)
            if st and st.model and st.model not in ("auto", ""):
                model = st.model
        target = e.target_branch if e.target_branch not in ("—", "") else ""
        print(f"{color}{e.id:<6} {task_name:<30} {icon} {e.status.value:<20} {e.agent:<8} {model:<22} {e.attempts:>3} {target:<12}{NC}")
        counts[e.status.value] = counts.get(e.status.value, 0) + 1

    print("-" * 102)
    summary = "  ".join(
        f"{STATUS_STYLE.get(s, (NC, ''))[0]}{STATUS_STYLE.get(s, (NC, ''))[1]} {s}: {c}{NC}"
        for s, c in sorted(counts.items())
    )
    print(summary)

    # State details for non-terminal tasks
    state_dir = agent_dir / "state"
    if state_dir.exists():
        active = [e for e in entries if not TaskStatus.is_terminal(e.status) and e.status != TaskStatus.QUEUED]
        if active:
            from .state_manager import load_state
            print(f"\n{BOLD}Active tasks:{NC}")
            for e in active:
                state = load_state(state_dir, e.id)
                if state:
                    print(f"  {e.id}: attempts={state.attempts}/{state.max_attempts} "
                          f"last_result={state.last_result} updated={state.updated_at}")

    # Rotation status
    config = load_config(agent_dir / "config.yml")
    if config.agents.rotation.enabled:
        from .rotation import get_rotation_status
        statuses = get_rotation_status(
            state_dir, config.agents.rotation.order,
            config.runner.limit_retry_wait_seconds,
        )
        print(f"\n{BOLD}Agent rotation:{NC} enabled")
        for s in statuses:
            if s["limited"]:
                mins = s["remaining_seconds"] // 60
                secs = s["remaining_seconds"] % 60
                print(f"  {RED}{s['agent']:<10} LIMITED ({mins}m{secs:02d}s remaining){NC}")
            else:
                print(f"  {GREEN}{s['agent']:<10} available{NC}")

    print()
    return 0


def cmd_add(args):
    """Add a task to the queue."""
    repo, agent_dir = resolve_paths(args)
    config = load_config(agent_dir / "config.yml")

    task_file = args.task_file
    # Normalize path
    if task_file.startswith(".agent/"):
        task_file = task_file[len(".agent/"):]
    if not task_file.startswith("tasks/"):
        task_file = f"tasks/{task_file}"

    # Check file exists
    full_path = agent_dir / task_file
    if not full_path.exists():
        print(f"{RED}Task file not found: {full_path}{NC}")
        return 1

    deps = [d.strip() for d in args.depends_on.split(",")] if args.depends_on else []

    entry = add_entry(
        agent_dir / "queue.md",
        task_file=task_file,
        agent=args.agent or config.agents.default,
        model=args.model or "auto",
        depends_on=deps,
        base_branch=args.base_branch or config.git.default_base_branch,
        target_branch=args.target_branch or config.git.default_target_branch,
    )

    print(f"{GREEN}Added task {entry.id}: {task_file}{NC}")
    print(f"  agent={entry.agent} model={entry.model} branch={entry.effective_work_branch()}")
    return 0


def cmd_cancel(args):
    """Cancel a task."""
    repo, agent_dir = resolve_paths(args)
    update_entry_status(agent_dir / "queue.md", args.task_id, TaskStatus.CANCELLED)
    print(f"{YELLOW}Cancelled task {args.task_id}{NC}")
    return 0


def cmd_retry(args):
    """Re-queue a failed or review_required task.

    --resume   Mark as in_progress so the scheduler calls agent.resume()
               (--continue flag for Claude). Preserves conversation context
               and the existing worktree. Use when the task failed due to an
               environment issue (e.g. validation failure) and the code is
               already correct.

    Default (no flag): re-queue as queued → agent starts a fresh run but
               sees the existing worktree state.
    """
    repo, agent_dir = resolve_paths(args)
    entries = load_queue(agent_dir / "queue.md")
    found = None
    for e in entries:
        if e.id == args.task_id:
            found = e
            break
    if not found:
        print(f"{RED}Task {args.task_id} not found{NC}")
        return 1
    if found.status not in (TaskStatus.FAILED, TaskStatus.REVIEW_REQUIRED, TaskStatus.CANCELLED):
        print(f"{YELLOW}Task {args.task_id} is {found.status.value}, not retryable{NC}")
        return 1

    from .state_manager import load_state, save_state
    state = load_state(agent_dir / "state", args.task_id)

    if getattr(args, "resume", False):
        # Resume mode: scheduler will call agent.resume() (--continue)
        update_entry_status(agent_dir / "queue.md", args.task_id, TaskStatus.IN_PROGRESS)
        if state:
            state.status = "in_progress"
            state.consecutive_same_failures = 0
            save_state(agent_dir / "state", state)
        print(f"{GREEN}Re-queued task {args.task_id} for RESUME (agent will --continue){NC}")
    else:
        # Fresh run: agent starts new conversation, sees existing worktree
        update_entry_status(agent_dir / "queue.md", args.task_id, TaskStatus.QUEUED)
        if state:
            state.status = "queued"
            state.consecutive_same_failures = 0
            save_state(agent_dir / "state", state)
        print(f"{GREEN}Re-queued task {args.task_id} (fresh agent run){NC}")

    return 0


def cmd_new_task(args):
    """Create a new task file from template."""
    repo, agent_dir = resolve_paths(args)
    task_name = args.name
    task_path = agent_dir / "tasks" / f"{task_name}.md"

    if task_path.exists() and not args.force:
        print(f"{YELLOW}Task file already exists: {task_path}{NC}")
        print("Use --force to overwrite")
        return 1

    tmpl = _get_template_path("task.md")
    if tmpl.exists():
        content = tmpl.read_text(encoding="utf-8")
        content = content.replace("{{ID}}", task_name)
    else:
        content = f"---\nid: {task_name}\nagent: claude\nmodel: auto\n---\n\n## Task\n\nDescribe the task here.\n\n## Acceptance Criteria\n- [ ] \n"

    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(content, encoding="utf-8")
    print(f"{GREEN}Created: {task_path}{NC}")
    return 0


def cmd_generate_task(args):
    """Generate a full task from a description and optionally add it to the queue."""
    repo, agent_dir = resolve_paths(args)
    config = load_config(agent_dir / "config.yml")

    from .task_generator import generate_task_markdown, suggest_dependencies
    
    agent_name = args.agent or config.agents.default
    model_tier = args.model or "low"  # Default to low for generation
    
    # Generate content
    content = generate_task_markdown(
        repo_path=repo,
        description=args.description,
        agent_name=agent_name,
        model_tier=model_tier,
        template_path=_get_template_path("task.md")
    )
    
    print(f"\n{BOLD}--- GENERATED TASK CONTENT ---{NC}")
    print(content)
    print(f"{BOLD}------------------------------{NC}\n")
    
    # Suggest dependencies
    deps = suggest_dependencies(agent_dir / "queue.md")
    if deps:
        print(f"{YELLOW}Suggested dependencies: {', '.join(deps)}{NC}")
    
    confirm = input(f"{BOLD}Add this task to the queue? [y/N]: {NC}").lower()
    if confirm != 'y':
        # Even if not added to queue, we should probably save it to a file
        task_name = input(f"Enter filename to save (e.g. my-task) or leave empty to discard: ").strip()
        if task_name:
            task_path = agent_dir / "tasks" / f"{task_name}.md"
            task_path.write_text(content, encoding="utf-8")
            print(f"{GREEN}Saved to {task_path}{NC}")
        else:
            print(f"{GRAY}Discarded{NC}")
        return 0

    # Save and add
    task_name = args.name
    if not task_name:
        # Try to extract from content or generate a slug
        import re
        m = re.search(r"^id:\s*(\S+)", content, re.MULTILINE)
        if m and m.group(1) != "{{ID}}":
            task_name = m.group(1)
        else:
            task_name = "generated-task-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    
    task_path = agent_dir / "tasks" / f"{task_name}.md"
    # Ensure ID is correct in content
    content = re.sub(r"^id:\s*(\S+)", f"id: {task_name}", content, flags=re.MULTILINE)
    task_path.write_text(content, encoding="utf-8")
    
    # Parse deps from user or use suggestions
    user_deps = input(f"Enter dependencies (comma-separated) [{', '.join(deps)}]: ").strip()
    if user_deps:
        final_deps = [d.strip() for d in user_deps.split(",")]
    else:
        final_deps = deps

    entry = add_entry(
        agent_dir / "queue.md",
        task_file=f"tasks/{task_name}.md",
        agent=agent_name,
        model="auto",
        depends_on=final_deps,
        base_branch=config.git.default_base_branch,
        target_branch=config.git.default_target_branch,
    )

    print(f"{GREEN}Added task {entry.id}: tasks/{task_name}.md{NC}")
    return 0


# ── Main ─────────────────────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="agent-runner",
        description="Agent Runner — universal AI task orchestrator",
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")

    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Initialize .agent/ in a repo")
    p_init.add_argument("path", nargs="?", default=None, help="Repo path (default: cwd)")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing config")

    # run
    p_run = sub.add_parser("run", help="Run one scheduler cycle")
    p_run.add_argument("--repo", default=None, help="Repo path (default: cwd)")

    # daemon
    p_daemon = sub.add_parser("daemon", help="Run scheduler in continuous loop")
    p_daemon.add_argument("--repo", default=None, help="Repo path (default: cwd)")

    # status
    p_status = sub.add_parser("status", help="Show queue status")
    p_status.add_argument("--repo", default=None, help="Repo path (default: cwd)")

    # add
    p_add = sub.add_parser("add", help="Add a task to the queue")
    p_add.add_argument("task_file", help="Path to task file (relative to .agent/)")
    p_add.add_argument("--repo", default=None)
    p_add.add_argument("--agent", default=None, help="Agent to use")
    p_add.add_argument("--model", default=None, help="Model tier (high/medium/low/auto)")
    p_add.add_argument("--depends-on", default=None, help="Comma-separated dependency task IDs")
    p_add.add_argument("--base-branch", default=None)
    p_add.add_argument("--target-branch", default=None)

    # cancel
    p_cancel = sub.add_parser("cancel", help="Cancel a task")
    p_cancel.add_argument("task_id", help="Task ID to cancel")
    p_cancel.add_argument("--repo", default=None)

    # retry
    p_retry = sub.add_parser("retry", help="Re-queue a failed/review task")
    p_retry.add_argument("task_id", help="Task ID to retry")
    p_retry.add_argument("--repo", default=None)
    p_retry.add_argument(
        "--resume", action="store_true",
        help="Resume with --continue (preserves agent conversation context). "
             "Use when failure was environmental, not a code issue.",
    )

    # new-task
    p_new = sub.add_parser("new-task", help="Create a task file from template")
    p_new.add_argument("name", help="Task name (used as filename)")
    p_new.add_argument("--repo", default=None)
    p_new.add_argument("--force", action="store_true")

    # generate-task
    p_gen = sub.add_parser("generate-task", help="Generate a full task from description")
    p_gen.add_argument("description", help="Short description of the task")
    p_gen.add_argument("--name", help="Filename to save as")
    p_gen.add_argument("--agent", help="Agent to use for generation")
    p_gen.add_argument("--model", help="Model tier for generation (default: low)")
    p_gen.add_argument("--repo", default=None)

    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "init": cmd_init,
        "run": cmd_run,
        "daemon": cmd_daemon,
        "status": cmd_status,
        "add": cmd_add,
        "cancel": cmd_cancel,
        "retry": cmd_retry,
        "new-task": cmd_new_task,
        "generate-task": cmd_generate_task,
    }

    return commands[args.command](args)



if __name__ == "__main__":
    sys.exit(main())
