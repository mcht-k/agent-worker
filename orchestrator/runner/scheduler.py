"""Main scheduler — picks tasks, runs agents, handles results."""

import time
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

from .config import Config, load_config, resolve_model_for_agent
from .models import TaskStatus, RunResult, RETRYABLE_RESULTS, QueueEntry
from .queue_manager import (
    load_queue, update_entry_status, find_runnable_tasks,
    find_resumable_tasks, all_tasks_terminal,
)
from .state_manager import (
    load_state, save_state, create_initial_state,
    record_attempt, mark_completed, mark_failed,
    mark_waiting, mark_review,
)
from .task_parser import parse_task_file
from .git_ops import (
    setup_task_branch, finalize_task_branch, is_repo_clean, push,
)
from .validators import run_validations
from .lock import acquire_task_lock, release_task_lock, acquire_lock, release_lock
from .notify import send_notification, NotifyEvent
from .hooks import execute_hooks
from .rotation import (
    get_available_agent, mark_agent_limited, clear_agent_limit,
    is_agent_limited,
)
from .agents.base import BaseAgent
from .agents.claude import ClaudeAgent
from .agents.codex import CodexAgent
from .agents.gemini import GeminiAgent
from .agents.aider import AiderAgent

log = logging.getLogger(__name__)

AGENTS = {
    "claude": ClaudeAgent,
    "codex": CodexAgent,
    "gemini": GeminiAgent,
    "aider": AiderAgent,
}

_shutdown_requested = False


def _handle_signal(signum, frame):
    global _shutdown_requested
    log.info("Shutdown signal received (%s), finishing current task...", signum)
    _shutdown_requested = True


def get_agent(name: str) -> BaseAgent:
    cls = AGENTS.get(name)
    if cls is None:
        raise ValueError(f"Unknown agent: {name}. Available: {list(AGENTS.keys())}")
    return cls()


def _resolve_task_params(entry: QueueEntry, config: Config, agent_dir_path: Path = None, repo_path: Path = None) -> dict:
    """Merge queue entry values with config defaults and task file metadata.

    If rotation is enabled, swaps to an available agent when the preferred one
    is rate-limited. If smart_tiering is enabled, uses an LLM to decide the model tier.
    """
    preferred_agent = config.agents.default if entry.agent in ("—", "") else entry.agent
    base = entry.base_branch if entry.base_branch not in ("—", "") else config.git.default_base_branch
    target = entry.target_branch if entry.target_branch not in ("—", "") else config.git.default_target_branch
    model_tier = entry.model if entry.model not in ("—", "") else "auto"
    timeout = config.runner.task_timeout_seconds
    work = entry.effective_work_branch()

    # Try to read task file metadata for overrides
    agent_dir = agent_dir_path or Path(".agent")
    task_path = agent_dir / entry.task_file
    if task_path.exists():
        meta, _ = parse_task_file(task_path)
        if meta.agent:
            preferred_agent = meta.agent
        if meta.base_branch:
            base = meta.base_branch
        if meta.target_branch:
            target = meta.target_branch
        if meta.model:
            model_tier = meta.model
        if meta.timeout > 0:
            timeout = meta.timeout

    # 1. Rotation: swap agent if preferred is rate-limited
    actual_agent = preferred_agent
    if config.agents.rotation.enabled and agent_dir:
        state_dir = agent_dir / "state"
        from .rotation import get_available_agent
        available = get_available_agent(
            state_dir, preferred_agent,
            config.agents.rotation.order,
            config.runner.limit_retry_wait_seconds,
        )
        if available:
            if available != preferred_agent:
                log.info("Rotation: %s -> %s for task %s", preferred_agent, available, entry.id)
            actual_agent = available
        else:
            actual_agent = None  # All agents limited

    # 2. Smart Tiering: if auto, use LLM to classify complexity
    resolved_tier = model_tier
    if model_tier == "auto" and config.agents.smart_tiering.enabled and agent_dir and repo_path:
        # First check if pattern rules match (cheap/free)
        models = config.agents.models
        tier_map = {"high": models.high, "medium": models.medium, "low": models.low}
        matched_by_pattern = False
        for rule in config.agents.auto_rules:
            patterns = [p.strip() for p in rule.pattern.split("|")]
            for pattern in patterns:
                import re
                regex = "^" + pattern.replace("*", ".*") + "$"
                if re.match(regex, entry.id):
                    resolved_tier = rule.model
                    matched_by_pattern = True
                    break
            if matched_by_pattern: break
        
        if not matched_by_pattern:
            from .classifier import classify_task_tier
            resolved_tier = classify_task_tier(
                repo_path=repo_path,
                agent_dir=agent_dir,
                config=config,
                task_id=entry.id,
                task_file=task_path
            )

    # 3. Final model resolution based on the ACTUAL agent being used
    # Ensures rotated agent gets a compatible provider model.
    model = resolve_model_for_agent(config, entry.id, resolved_tier, actual_agent)

    return {
        "agent_name": actual_agent,
        "preferred_agent": preferred_agent,
        "model": model,
        "base_branch": base,
        "target_branch": target,
        "work_branch": work,
        "timeout": timeout,
    }


def _hook_kwargs(entry, config, agent_dir, params, working_dir=None, error_message=""):
    """Build common kwargs for execute_hooks calls."""
    return dict(
        task_id=entry.id,
        task_file=agent_dir / entry.task_file,
        context_dir=agent_dir / "context",
        work_branch=params["work_branch"],
        target_branch=params["target_branch"],
        agent_cmd=params["agent_name"],
        working_dir=working_dir or agent_dir,
        error_message=error_message,
    )


def _commit_work(working_dir: Path, task_id: str, task_slug: str, phase: str) -> bool:
    """Commit any uncommitted changes on the current (feature) branch.

    Called twice per task:
      phase='agent'  — after the agent finishes, captures its work
      phase='hooks'  — after post-task hooks (lint/format fixes)

    Returns True if a commit was made.
    """
    from .git_ops import is_repo_clean, commit_all
    if is_repo_clean(working_dir):
        log.debug("Nothing to commit after %s phase for task %s", phase, task_id)
        return False

    if phase == "agent":
        msg = f"feat({task_id}): {task_slug}"
    else:
        msg = f"fix({task_id}): post-task hook changes"

    committed = commit_all(working_dir, msg)
    if committed:
        log.info("Committed %s work to feature branch: %s", phase, msg)
    return committed


def execute_task(
    entry: QueueEntry,
    config: Config,
    repo_root: Path,
    agent_dir: Path,
    resume: bool = False,
) -> None:
    """Execute a single task: hooks → branch → agent → hooks → merge → hooks."""
    params = _resolve_task_params(entry, config, agent_dir, repo_root)

    # Rotation: all agents limited → skip this task for now
    if params["agent_name"] is None:
        log.info("Task %s: all agents rate-limited, skipping for now", entry.id)
        return

    agent = get_agent(params["agent_name"])
    state_dir = agent_dir / "state"
    locks_dir = agent_dir / "locks"
    logs_dir = agent_dir / "logs"
    transcripts_dir = agent_dir / "transcripts"
    context_dir = agent_dir / "context"

    task_file = agent_dir / entry.task_file
    log_file = logs_dir / f"task-{entry.id}.log"
    transcript_file = transcripts_dir / f"task-{entry.id}.txt"
    context_file = context_dir / f"{entry.id}.md"

    # Acquire task lock
    if not acquire_task_lock(locks_dir, entry.id):
        log.warning("Task %s is locked by another process, skipping", entry.id)
        return

    try:
        # Load or create runtime state
        state = load_state(state_dir, entry.id)
        if state is None:
            state = create_initial_state(
                task_id=entry.id,
                agent=params["agent_name"],
                model=params["model"],
                work_branch=params["work_branch"],
                max_attempts=config.runner.max_attempts,
                log_file=str(log_file),
                transcript_file=str(transcript_file),
            )

        # Check max attempts
        if state.attempts >= state.max_attempts:
            log.error("Task %s exceeded max attempts (%d)", entry.id, state.max_attempts)
            mark_failed(state, "max attempts exceeded")
            save_state(state_dir, state)
            update_entry_status(agent_dir / "queue.md", entry.id, TaskStatus.FAILED, state.attempts)
            send_notification(config.notifications, NotifyEvent(
                "task_failed", entry.id, params["agent_name"], "failed",
                f"Task {entry.id} exceeded max attempts",
            ))
            return

        # Update queue status
        update_entry_status(
            agent_dir / "queue.md", entry.id, TaskStatus.IN_PROGRESS,
            state.attempts, params["work_branch"],
        )
        state.status = "in_progress"
        save_state(state_dir, state)

        send_notification(config.notifications, NotifyEvent(
            "task_started", entry.id, params["agent_name"], "in_progress",
            f"Task {entry.id} started (model={params['model']}, attempt={state.attempts + 1})",
        ))

        # Set up branch
        worktree_dir = agent_dir / "worktrees" if config.git.use_worktrees else None
        working_dir = setup_task_branch(
            repo_root,
            params["work_branch"],
            params["base_branch"],
            use_worktrees=config.git.use_worktrees,
            worktree_dir=worktree_dir,
        )

        # ── PRE-TASK HOOKS (graphify context, env setup) ─────────────────
        hk = _hook_kwargs(entry, config, agent_dir, params, working_dir)
        pre_ok = execute_hooks(config.hooks.pre_task, "pre_task", **hk)
        if not pre_ok:
            log.warning("Task %s: required pre_task hook failed, aborting", entry.id)
            mark_failed(state, "pre_task hook failed")
            save_state(state_dir, state)
            update_entry_status(agent_dir / "queue.md", entry.id, TaskStatus.FAILED, state.attempts)
            return

        # ── RUN AGENT ────────────────────────────────────────────────────
        ctx = context_file if context_file.exists() else None
        if resume and state.attempts > 0:
            log.info("Resuming task %s (attempt %d, agent=%s, model=%s)",
                     entry.id, state.attempts + 1, params["agent_name"], params["model"])
            result = agent.resume(
                task_file, working_dir, params["model"],
                log_file, transcript_file, params["timeout"],
                context_file=ctx,
            )
        else:
            log.info("Running task %s (attempt %d, agent=%s, model=%s)",
                     entry.id, state.attempts + 1, params["agent_name"], params["model"])
            result = agent.run(
                task_file, working_dir, params["model"],
                log_file, transcript_file, params["timeout"],
                context_file=ctx,
            )

        # Record attempt
        record_attempt(state, result.result.value, result.error_message)
        state.token_usage = result.token_usage or {}

        # Handle result
        if result.result == RunResult.SUCCESS:
            # Agent succeeded — clear any limit marker for this agent
            clear_agent_limit(agent_dir / "state", params["agent_name"])

            # ── COMMIT AGENT WORK to feature branch ──────────────────────
            task_slug = entry.task_file.replace("tasks/", "").replace(".md", "")
            _commit_work(working_dir, entry.id, task_slug, phase="agent")

            # ── POST-TASK HOOKS (lint, format) ───────────────────────────
            post_ok = execute_hooks(config.hooks.post_task, "post_task", **hk)
            if not post_ok:
                log.warning("Task %s: required post_task hook failed", entry.id)
                mark_review(state, "post_task hook failed")
                save_state(state_dir, state)
                update_entry_status(agent_dir / "queue.md", entry.id,
                                    TaskStatus.REVIEW_REQUIRED, state.attempts)
                return

            # ── COMMIT HOOK CHANGES (lint fixes, formatting) ─────────────
            _commit_work(working_dir, entry.id, task_slug, phase="hooks")

            _handle_success(entry, state, config, repo_root, agent_dir, params, working_dir)
        elif result.result == RunResult.LIMIT_HIT:
            # Mark this agent as limited globally
            mark_agent_limited(agent_dir / "state", params["agent_name"])
            _handle_limit_hit(entry, state, config, agent_dir, params)
        elif result.result in RETRYABLE_RESULTS:
            _handle_retryable(entry, state, config, agent_dir, params, result)
        elif result.result == RunResult.NO_CHANGES:
            _handle_no_changes(entry, state, config, agent_dir, params)
        else:
            # ── ON-FAILURE HOOKS (cleanup, extra notifications) ──────────
            hk_fail = _hook_kwargs(entry, config, agent_dir, params,
                                   working_dir, result.error_message)
            execute_hooks(config.hooks.on_failure, "on_failure", **hk_fail)
            _handle_hard_error(entry, state, config, agent_dir, params, result)

        save_state(state_dir, state)

    finally:
        release_task_lock(locks_dir, entry.id)


def _handle_success(entry, state, config, repo_root, agent_dir, params, working_dir):
    """Agent succeeded — validate, merge, mark complete."""
    # Run validations
    valid, failures = run_validations(config.validation, working_dir)
    if not valid:
        log.warning("Task %s: validation failed: %s", entry.id, failures)
        mark_review(state, f"Validation failed: {'; '.join(failures)}")
        update_entry_status(
            agent_dir / "queue.md", entry.id,
            TaskStatus.REVIEW_REQUIRED, state.attempts,
        )
        send_notification(config.notifications, NotifyEvent(
            "review_required", entry.id, params["agent_name"], "review_required",
            f"Task {entry.id} validation failed: {failures[0]}",
        ))
        return

    # Merge branch
    merged, merge_err = finalize_task_branch(
        repo_root,
        params["work_branch"],
        params["target_branch"],
        merge_mode=config.git.merge_mode,
        auto_push=config.git.auto_push,
        delete_after=config.git.delete_work_branch_after_merge,
        working_dir=working_dir if config.git.use_worktrees else None,
    )

    if not merged:
        log.error("Task %s: merge failed: %s", entry.id, merge_err)
        if config.git.on_conflict == "review_required":
            mark_review(state, f"Merge conflict: {merge_err}")
            update_entry_status(
                agent_dir / "queue.md", entry.id,
                TaskStatus.REVIEW_REQUIRED, state.attempts,
            )
        else:
            mark_failed(state, f"Merge failed: {merge_err}")
            update_entry_status(
                agent_dir / "queue.md", entry.id,
                TaskStatus.FAILED, state.attempts,
            )
        send_notification(config.notifications, NotifyEvent(
            "task_failed", entry.id, params["agent_name"], "merge_failed",
            f"Task {entry.id} merge failed: {merge_err[:100]}",
        ))
        return

    # ── POST-MERGE HOOKS (update_claude_md, rebuild, etc.) ─────────
    hk = _hook_kwargs(entry, config, agent_dir, params, working_dir)
    execute_hooks(config.hooks.post_merge, "post_merge", **hk)

    mark_completed(state)
    update_entry_status(
        agent_dir / "queue.md", entry.id,
        TaskStatus.COMPLETED, state.attempts,
    )
    send_notification(config.notifications, NotifyEvent(
        "task_completed", entry.id, params["agent_name"], "completed",
        f"Task {entry.id} completed and merged to {params['target_branch']}",
    ))
    log.info("Task %s completed successfully", entry.id)


def _handle_limit_hit(entry, state, config, agent_dir, params):
    rotation = config.agents.rotation

    if rotation.enabled:
        # Rotation enabled: re-queue immediately so next cycle picks another agent
        state.status = "queued"
        update_entry_status(
            agent_dir / "queue.md", entry.id,
            TaskStatus.QUEUED, state.attempts,
        )
        send_notification(config.notifications, NotifyEvent(
            "limit_hit", entry.id, params["agent_name"], "rotating",
            f"Task {entry.id}: {params['agent_name']} hit limit, re-queued for rotation",
        ))
        log.info("Task %s: %s hit limit, re-queued for rotation to next agent",
                 entry.id, params["agent_name"])
    else:
        # No rotation: wait for cooldown
        mark_waiting(state)
        update_entry_status(
            agent_dir / "queue.md", entry.id,
            TaskStatus.WAITING_FOR_LIMIT, state.attempts,
        )
        send_notification(config.notifications, NotifyEvent(
            "limit_hit", entry.id, params["agent_name"], "waiting_for_limit_reset",
            f"Task {entry.id} hit rate limit (attempt {state.attempts}), "
            f"retry in {config.runner.limit_retry_wait_seconds}s",
        ))
    log.info("Task %s hit rate limit, will retry later", entry.id)


def _handle_retryable(entry, state, config, agent_dir, params, result):
    if state.consecutive_same_failures >= 2:
        mark_review(state, f"Same error repeated: {result.error_message}")
        update_entry_status(
            agent_dir / "queue.md", entry.id,
            TaskStatus.REVIEW_REQUIRED, state.attempts,
        )
        send_notification(config.notifications, NotifyEvent(
            "review_required", entry.id, params["agent_name"], "review_required",
            f"Task {entry.id} same error repeated twice: {result.error_message[:100]}",
        ))
    else:
        update_entry_status(
            agent_dir / "queue.md", entry.id,
            TaskStatus.QUEUED, state.attempts,
        )
        state.status = "queued"
        log.info("Task %s transient error, re-queued for retry", entry.id)


def _handle_no_changes(entry, state, config, agent_dir, params):
    mark_review(state, "Agent made no changes to the repository")
    update_entry_status(
        agent_dir / "queue.md", entry.id,
        TaskStatus.REVIEW_REQUIRED, state.attempts,
    )
    send_notification(config.notifications, NotifyEvent(
        "review_required", entry.id, params["agent_name"], "review_required",
        f"Task {entry.id} completed but made no repo changes",
    ))


def _handle_hard_error(entry, state, config, agent_dir, params, result):
    mark_failed(state, result.error_message)
    update_entry_status(
        agent_dir / "queue.md", entry.id,
        TaskStatus.FAILED, state.attempts,
    )
    send_notification(config.notifications, NotifyEvent(
        "task_failed", entry.id, params["agent_name"], "failed",
        f"Task {entry.id} hard error: {result.error_message[:100]}",
    ))
    log.error("Task %s failed: %s", entry.id, result.error_message)


# ── Scheduler loop ───────────────────────────────────────────────────────────

def run_once(repo_root: Path, agent_dir: Path, config: Config) -> bool:
    """Run one scheduler cycle. Returns True if work was done."""
    queue_path = agent_dir / "queue.md"
    entries = load_queue(queue_path)

    if not entries:
        log.info("Queue is empty")
        return False

    if all_tasks_terminal(entries):
        log.info("All tasks are in terminal state")
        send_notification(config.notifications, NotifyEvent(
            "queue_empty", message="All tasks completed or failed",
        ))
        return False

    # Priority 1: resumable tasks (in_progress, waiting_for_limit past retry window)
    resumable = find_resumable_tasks(entries)
    for entry in resumable:
        if entry.status == TaskStatus.WAITING_FOR_LIMIT:
            state = load_state(agent_dir / "state", entry.id)
            if state and state.updated_at:
                from datetime import datetime, timezone
                try:
                    updated = datetime.strptime(state.updated_at, "%Y-%m-%d %H:%M:%S")
                    elapsed = (datetime.now(timezone.utc).replace(tzinfo=None) - updated).total_seconds()
                    if elapsed < config.runner.limit_retry_wait_seconds:
                        log.debug("Task %s waiting for limit reset (%ds remaining)",
                                  entry.id, config.runner.limit_retry_wait_seconds - elapsed)
                        continue
                except ValueError:
                    pass

        execute_task(entry, config, repo_root, agent_dir, resume=True)
        return True

    # Priority 2: runnable tasks (queued with satisfied deps)
    runnable = find_runnable_tasks(entries)
    if runnable:
        entry = runnable[0]
        execute_task(entry, config, repo_root, agent_dir, resume=False)
        return True

    # Explain why nothing ran
    review = [e for e in entries if e.status == TaskStatus.REVIEW_REQUIRED]
    waiting = [e for e in entries if e.status == TaskStatus.WAITING_FOR_LIMIT]
    blocked = [e for e in entries if e.status == TaskStatus.QUEUED and
               not all(dep in {x.id for x in entries if x.status == TaskStatus.COMPLETED}
                       for dep in e.depends_on)]
    parts = []
    if review:
        parts.append(f"{len(review)} task(s) need review: {[e.id for e in review]}")
    if waiting:
        parts.append(f"{len(waiting)} waiting for rate-limit reset")
    if blocked:
        parts.append(f"{len(blocked)} blocked by unfinished dependencies")
    reason = "; ".join(parts) if parts else "unknown"
    log.info("No tasks ready to run — %s", reason)
    return False


def run_daemon(repo_root: Path, agent_dir: Path, config: Config) -> None:
    """Run the scheduler in a loop until all tasks are done or interrupted."""
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    global_lock = agent_dir / "locks" / "scheduler.lock"
    if not acquire_lock(global_lock):
        log.error("Another scheduler instance is already running")
        sys.exit(1)

    log.info("Scheduler daemon started (poll=%ds)", config.runner.poll_interval_seconds)

    try:
        while not _shutdown_requested:
            try:
                did_work = run_once(repo_root, agent_dir, config)
            except Exception as e:
                log.exception("Scheduler cycle error: %s", e)
                did_work = False

            if not did_work:
                # Check if we're done
                entries = load_queue(agent_dir / "queue.md")
                if entries and all_tasks_terminal(entries):
                    log.info("All tasks finished. Scheduler exiting.")
                    break
                log.debug("Sleeping %ds...", config.runner.poll_interval_seconds)
                time.sleep(config.runner.poll_interval_seconds)
    finally:
        release_lock(global_lock)
        log.info("Scheduler daemon stopped")
