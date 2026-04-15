"""Hook system — pre/post task lifecycle hooks with built-in implementations.

Hook phases:
  pre_task   — before agent runs (context building, graphify)
  post_task  — after agent succeeds, before merge (lint, format)
  post_merge — after successful merge (rebuild, update CLAUDE.md)
  on_failure — when task fails (cleanup, notifications)
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


# ── Built-in hook: Graphify (pre_task) ───────────────────────────────────────

def _extract_task_keywords(task_file: Path, task_content: str) -> str:
    """Extract search keywords from task filename and first heading.

    Uses the filename slug and the first non-empty line of the task body
    to produce a short query string for graphify — no extra API call needed.

    Examples:
      001-users-be-employee-status.md  →  "users employee status"
      005-tenant-fe-onboarding-flow.md →  "tenant onboarding flow"
    """
    # From filename: strip leading number, replace hyphens, drop -be/-fe suffixes
    slug = task_file.stem  # e.g. "001-users-be-employee-status"
    parts = [p for p in slug.split("-") if not p.isdigit() and p not in ("be", "fe")]
    keywords = " ".join(parts)

    # Also grab first meaningful line from task body (usually the main topic)
    for line in task_content.splitlines():
        line = line.strip().lstrip("#").strip()
        if len(line) > 10 and not line.startswith("|") and not line.startswith("---"):
            keywords = f"{keywords} {line[:60]}"
            break

    return keywords.strip()


def _find_graph_json(working_dir: Path) -> Optional[Path]:
    """Find graph.json produced by graphify git hooks or a previous skill run."""
    candidates = [
        working_dir / "graphify-out" / "graph.json",
        working_dir / "graph.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _build_graph(working_dir: Path) -> bool:
    """Build/update graphify knowledge graph using the Python API.

    Equivalent to what the post-commit git hook does — uses SHA256 cache
    so only changed files are re-processed on subsequent runs.
    """
    try:
        from graphify.watch import _rebuild_code
        log.info("Building graphify knowledge graph (cwd=%s)", working_dir)
        result = _rebuild_code(working_dir)
        if result:
            log.info("graphify graph built successfully")
        else:
            log.warning("graphify _rebuild_code returned False")
        return bool(result)
    except Exception as exc:
        log.warning("graphify build failed: %s", exc)
        return False


def _run_graphify_cli(
    working_dir: Path,
    task_file: Path,
    task_content: str,
    context_output: Path,
    graphify_cmd: str,
    timeout: int,
) -> bool:
    """Query a graphify knowledge graph for task-relevant context.

    If graph.json doesn't exist yet, builds it first using the Python API
    (same as what the post-commit git hook does).

    For automatic graph updates on every commit/checkout, run once in the repo:
        graphify hook install
    """
    graph_path = _find_graph_json(working_dir)
    if not graph_path:
        log.info("graphify: no graph.json found — building initial graph")
        if not _build_graph(working_dir):
            return False
        graph_path = _find_graph_json(working_dir)
        if not graph_path:
            log.warning("graphify: graph.json still not found after build")
            return False

    log.info("graphify graph found: %s", graph_path)
    parts = []

    # Query graph for task-specific context (BFS traversal, token-capped)
    keywords = _extract_task_keywords(task_file, task_content)
    if keywords:
        log.info("Querying graphify: %r (budget=1500 tokens)", keywords)
        query = subprocess.run(
            [graphify_cmd, "query", keywords,
             "--budget", "1500",
             "--graph", str(graph_path)],
            cwd=str(working_dir),
            capture_output=True, text=True, encoding="utf-8",
            timeout=60,
        )
        if query.returncode == 0 and query.stdout.strip():
            parts.append(
                f"## Relevant Code Relationships\n"
                f"*(graphify query: {keywords!r})*\n\n"
                f"{query.stdout.strip()}"
            )
        else:
            log.warning("graphify query returned no output (exit=%d): %s",
                        query.returncode, query.stderr.strip()[:200])

    # Include GRAPH_REPORT.md for high-level cluster overview
    report_path = graph_path.parent / "GRAPH_REPORT.md"
    if report_path.exists():
        report = report_path.read_text(encoding="utf-8").strip()
        if report:
            parts.append(f"## Knowledge Graph Overview\n\n{report[:2000]}")

    if not parts:
        log.warning("graphify: graph exists but produced no usable output")
        return False

    context = "\n\n---\n\n".join(parts)
    context_output.write_text(
        f"## Graphify Context Briefing\n\n{context}\n",
        encoding="utf-8",
    )
    log.info("Graphify context written to %s (%d chars)", context_output, len(context))
    return True


def _run_claude_context_builder(
    working_dir: Path,
    task_content: str,
    context_output: Path,
    agent_cmd: str,
    timeout: int,
) -> bool:
    """Fallback: ask Claude Haiku to produce a context briefing from the repo.

    Used when the graphify CLI is not installed.
    Install the real tool with: pip install graphifyy && graphify install
    """
    prompt = (
        "You are a context builder. Analyze this task and the current repository. "
        "Produce a concise briefing of the relevant code structure, key files, "
        "important interfaces, and architectural patterns the agent will need. "
        "Focus only on what is directly relevant to this specific task. "
        "Output ONLY the briefing, no preamble.\n\n"
        f"TASK:\n{task_content}"
    )
    try:
        proc = subprocess.run(
            [agent_cmd, "-p", "--model", "claude-haiku-4-5"],
            input=prompt,
            cwd=str(working_dir),
            capture_output=True, text=True, encoding="utf-8",
            timeout=timeout,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            context_output.write_text(
                f"## Context Briefing (Claude fallback — install graphifyy for graph-based context)\n\n"
                f"{proc.stdout.strip()}\n",
                encoding="utf-8",
            )
            log.info("Claude context builder wrote %d chars to %s",
                     len(proc.stdout), context_output)
            return True
        log.warning("Claude context builder returned no output (exit=%d)", proc.returncode)
        return False
    except subprocess.TimeoutExpired:
        log.warning("Claude context builder timed out after %ds", timeout)
        return False
    except FileNotFoundError:
        log.warning("Agent command not found: %s", agent_cmd)
        return False


def run_graphify(
    working_dir: Path,
    task_file: Path,
    context_output: Path,
    agent_cmd: str = "claude",
    timeout: int = 300,
    graphify_cmd: Optional[str] = None,
) -> bool:
    """Build a knowledge graph context briefing and write it to context_output.

    Tries the real graphify CLI first (pip install graphifyy).
    Falls back to a Claude Haiku-based context builder if CLI is not installed.

    graphify_cmd: explicit path to the graphify executable. If not provided,
    auto-discovered via shutil.which(). Set this in config.yml when the daemon
    runs outside the virtualenv where graphify is installed:
        hooks:
          pre_task:
            - name: graphify
              command: "C:/Python312/Scripts/graphify.exe"

    The output is prepended to every agent run, providing targeted codebase context
    while using far fewer tokens than passing raw files.
    """
    import shutil
    context_output.parent.mkdir(parents=True, exist_ok=True)
    task_content = task_file.read_text(encoding="utf-8")

    if not graphify_cmd:
        graphify_cmd = shutil.which("graphify")
    if graphify_cmd:
        success = _run_graphify_cli(
            working_dir, task_file, task_content, context_output, graphify_cmd, timeout,
        )
        if success:
            return True
        log.warning("graphify CLI failed — falling back to Claude context builder")

    else:
        log.info(
            "graphify CLI not found — using Claude fallback "
            "(install real tool: pip install graphifyy && graphify install)"
        )

    return _run_claude_context_builder(
        working_dir, task_content, context_output, "claude", timeout,
    )


# ── Built-in hook: Update CLAUDE.md (post_merge) ────────────────────────────

def run_update_claude_md(
    working_dir: Path,
    work_branch: str,
    target_branch: str,
    agent_cmd: str = "claude",
    model: str = "claude-haiku-4-5",
    timeout: int = 300,
) -> bool:
    """After merge, update CLAUDE.md if the codebase changed significantly.

    1. Gets the diff of what changed in the task
    2. Checks if changes are significant (not just config/docs)
    3. Runs a low-tier agent to update CLAUDE.md
    4. Auto-commits the change
    """
    # Get diff of merged changes
    try:
        diff_result = subprocess.run(
            ["git", "diff", f"{target_branch}~1..{target_branch}", "--stat"],
            cwd=str(working_dir),
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )
        diff_stat = diff_result.stdout.strip()
    except Exception as e:
        log.warning("Could not get diff for CLAUDE.md update: %s", e)
        return False

    if not diff_stat:
        log.debug("No diff found, skipping CLAUDE.md update")
        return True

    # Check if changes are significant (not just .agent/ or docs/)
    significant_patterns = [
        "src/", "backend/", "frontend/", "lib/", "app/", "pkg/",
        "Modules/", "Services/", "Controllers/", "Components/",
        "*.cs", "*.ts", "*.py", "*.go", "*.rs", "*.java",
    ]
    diff_lower = diff_stat.lower()
    is_significant = any(p.lower().rstrip("*") in diff_lower for p in significant_patterns)

    if not is_significant:
        log.debug("Changes not significant enough for CLAUDE.md update")
        return True

    # Get the full diff for context
    try:
        full_diff = subprocess.run(
            ["git", "diff", f"{target_branch}~1..{target_branch}",
             "--no-color", "--unified=3"],
            cwd=str(working_dir),
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )
        diff_content = full_diff.stdout[:8000]  # Limit to save tokens
    except Exception:
        diff_content = diff_stat

    # Read current PROJECT.md (shared knowledge) — this is the source of truth
    agent_dir = working_dir / ".agent"
    project_md = agent_dir / "PROJECT.md"
    current_content = ""
    if project_md.exists():
        current_content = project_md.read_text(encoding="utf-8")
    elif (working_dir / "CLAUDE.md").exists():
        # Fallback: no PROJECT.md yet, use CLAUDE.md as seed
        current_content = (working_dir / "CLAUDE.md").read_text(encoding="utf-8")

    prompt = (
        "You are maintaining PROJECT.md — the shared knowledge base for all AI agents "
        "working on this repository (Claude, Gemini, Codex, Aider).\n"
        "Review the diff below and decide if PROJECT.md needs updating.\n\n"
        "Rules:\n"
        "- Only update if there are NEW architectural patterns, modules, endpoints, "
        "or conventions that aren't already covered\n"
        "- Do NOT add file listings or code patterns that can be discovered by reading code\n"
        "- Do NOT repeat what's already in PROJECT.md\n"
        "- Keep the content agent-agnostic — no Claude-specific or Gemini-specific instructions\n"
        "- If no update is needed, output ONLY the text: NO_UPDATE_NEEDED\n"
        "- If update is needed, output the COMPLETE updated PROJECT.md content\n\n"
        f"CURRENT PROJECT.md:\n```\n{current_content}\n```\n\n"
        f"DIFF:\n```\n{diff_content}\n```"
    )

    try:
        proc = subprocess.run(
            [agent_cmd, "-p", "--model", model],
            input=prompt,
            cwd=str(working_dir),
            capture_output=True, text=True, encoding='utf-8',
            timeout=timeout,
        )

        output = proc.stdout.strip()
        if proc.returncode != 0 or not output:
            log.warning("PROJECT.md update agent failed (exit=%d)", proc.returncode)
            return False

        if "NO_UPDATE_NEEDED" in output:
            log.info("PROJECT.md — no update needed")
            return True

        # Write updated PROJECT.md
        agent_dir.mkdir(parents=True, exist_ok=True)
        project_md.write_text(output, encoding="utf-8")

        # Auto-commit
        subprocess.run(
            ["git", "add", str(project_md)],
            cwd=str(working_dir), capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "commit", "-m", "docs: auto-update PROJECT.md after task merge"],
            cwd=str(working_dir), capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "push"],
            cwd=str(working_dir), capture_output=True, timeout=30,
        )

        log.info("PROJECT.md updated and committed")
        return True

    except subprocess.TimeoutExpired:
        log.warning("PROJECT.md update timed out after %ds", timeout)
        return False
    except FileNotFoundError:
        log.warning("Agent command not found: %s", agent_cmd)
        return False


# ── Built-in hook: Sync agent docs (post_merge) ─────────────────────────────

# Maps agent name → the native file it reads automatically
AGENT_DOC_FILES = {
    "claude": "CLAUDE.md",
    "codex": "AGENTS.md",
    "gemini": "GEMINI.md",
}

# Header injected into native files so humans know it's auto-managed
_SYNC_HEADER = (
    "<!-- AUTO-SYNCED from .agent/PROJECT.md by Agent Runner. "
    "Edit PROJECT.md, not this file. -->\n\n"
)


def run_sync_agent_docs(working_dir: Path, agent_dir: Optional[Path] = None) -> bool:
    """Sync .agent/PROJECT.md content into each agent's native doc file.

    Creates/overwrites CLAUDE.md, AGENTS.md, GEMINI.md in the repo root
    so that every agent gets the same project knowledge through its native
    mechanism, even when invoked outside the orchestrator.
    """
    if agent_dir is None:
        agent_dir = working_dir / ".agent"

    project_md = agent_dir / "PROJECT.md"
    if not project_md.exists():
        log.debug("No PROJECT.md found, skipping sync")
        return True

    content = project_md.read_text(encoding="utf-8").strip()
    if not content:
        return True

    synced = []
    for agent_name, filename in AGENT_DOC_FILES.items():
        target = working_dir / filename
        try:
            # Preserve any existing content that's NOT from sync
            existing = ""
            if target.exists():
                existing = target.read_text(encoding="utf-8")
                # If file was previously synced, replace everything
                if "AUTO-SYNCED from .agent/PROJECT.md" in existing:
                    existing = ""
                else:
                    # Existing manual content — append PROJECT.md below it
                    existing = existing.rstrip() + "\n\n---\n\n"

            new_content = existing + _SYNC_HEADER + content + "\n"
            target.write_text(new_content, encoding="utf-8")
            synced.append(filename)
        except Exception as e:
            log.warning("Failed to sync %s: %s", filename, e)

    if synced:
        # Auto-commit the synced files
        try:
            subprocess.run(
                ["git", "add"] + [AGENT_DOC_FILES[a] for a in AGENT_DOC_FILES],
                cwd=str(working_dir), capture_output=True, timeout=10,
            )
            # Only commit if there are actual changes
            status = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=str(working_dir), capture_output=True, timeout=10,
            )
            if status.returncode != 0:  # there are staged changes
                subprocess.run(
                    ["git", "commit", "-m",
                     "docs: sync PROJECT.md to agent doc files"],
                    cwd=str(working_dir), capture_output=True, timeout=10,
                )
                subprocess.run(
                    ["git", "push"],
                    cwd=str(working_dir), capture_output=True, timeout=30,
                )
                log.info("Synced PROJECT.md to: %s", ", ".join(synced))
            else:
                log.debug("Agent doc files already in sync")
        except Exception as e:
            log.warning("Failed to commit synced docs: %s", e)

    return True


# ── Generic hook runner ──────────────────────────────────────────────────────

def run_custom_hook(
    command: str,
    working_dir: Path,
    timeout: int = 300,
    env_extra: Optional[dict] = None,
) -> bool:
    """Run a custom shell command as a hook."""
    import os
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)

    log.info("Running custom hook: %s", command)
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=timeout,
            env=env,
        )
        if result.returncode != 0:
            log.warning("Custom hook failed (exit=%d): %s",
                        result.returncode, result.stderr.strip()[:200])
            return False
        return True
    except subprocess.TimeoutExpired:
        log.warning("Custom hook timed out after %ds: %s", timeout, command)
        return False


# ── Hook dispatcher ──────────────────────────────────────────────────────────

BUILTIN_HOOKS = {"graphify", "update_claude_md", "sync_agent_docs"}


def execute_hooks(
    hooks: list,
    phase: str,
    working_dir: Path,
    task_id: str = "",
    task_file: Optional[Path] = None,
    context_dir: Optional[Path] = None,
    work_branch: str = "",
    target_branch: str = "",
    agent_cmd: str = "claude",
    error_message: str = "",
) -> bool:
    """Execute all hooks for a given phase.

    Returns True if all required hooks passed.
    """
    if not hooks:
        return True

    all_ok = True
    env_extra = {
        "AGENT_TASK_ID": task_id,
        "AGENT_PHASE": phase,
        "AGENT_WORK_BRANCH": work_branch,
        "AGENT_TARGET_BRANCH": target_branch,
        "AGENT_ERROR": error_message,
    }

    for hook in hooks:
        if not hook.get("enabled", True):
            continue

        name = hook.get("name", "unnamed")
        command = hook.get("command", "")
        required = hook.get("required", False)
        timeout = hook.get("timeout", 300)

        log.info("[%s] Running hook: %s", phase, name)

        success = False

        if name == "graphify" and phase == "pre_task":
            if context_dir and task_file:
                context_output = context_dir / f"{task_id}.md"
                # `command` field optionally overrides auto-discovery of graphify executable
                explicit_cmd = hook.get("command", "") or None
                success = run_graphify(
                    working_dir, task_file, context_output,
                    agent_cmd=agent_cmd, timeout=timeout,
                    graphify_cmd=explicit_cmd,
                )
            else:
                log.warning("Graphify hook: missing context_dir or task_file")
                success = False

        elif name == "update_claude_md" and phase == "post_merge":
            success = run_update_claude_md(
                working_dir, work_branch, target_branch,
                agent_cmd=agent_cmd, timeout=timeout,
            )

        elif name == "sync_agent_docs" and phase == "post_merge":
            success = run_sync_agent_docs(working_dir)

        elif command:
            success = run_custom_hook(
                command, working_dir, timeout=timeout, env_extra=env_extra,
            )

        else:
            log.warning("Hook %s has no command and is not a built-in for phase %s",
                        name, phase)
            success = True  # Skip gracefully

        if not success:
            log.warning("[%s] Hook failed: %s (required=%s)", phase, name, required)
            if required:
                all_ok = False
        else:
            log.info("[%s] Hook passed: %s", phase, name)

    return all_ok
