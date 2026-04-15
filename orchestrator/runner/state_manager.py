"""Per-task runtime state management (JSON files)."""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from .models import RuntimeState

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def state_path(state_dir: Path, task_id: str) -> Path:
    return state_dir / f"{task_id}.json"


def load_state(state_dir: Path, task_id: str) -> Optional[RuntimeState]:
    path = state_path(state_dir, task_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return RuntimeState(**{
            k: data[k] for k in RuntimeState.__dataclass_fields__ if k in data
        })
    except Exception as e:
        log.warning("Failed to load state for %s: %s", task_id, e)
        return None


def save_state(state_dir: Path, state: RuntimeState) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    state.updated_at = _now()
    path = state_path(state_dir, state.task_id)
    data = {}
    for k in RuntimeState.__dataclass_fields__:
        data[k] = getattr(state, k)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def create_initial_state(
    task_id: str,
    agent: str,
    model: str,
    work_branch: str,
    max_attempts: int,
    log_file: str = "",
    transcript_file: str = "",
) -> RuntimeState:
    return RuntimeState(
        task_id=task_id,
        status="in_progress",
        agent=agent,
        model=model,
        attempts=0,
        max_attempts=max_attempts,
        resume_strategy="continue",
        started_at=_now(),
        updated_at=_now(),
        work_branch=work_branch,
        log_file=log_file,
        transcript_file=transcript_file,
    )


def record_attempt(state: RuntimeState, result: str, error: str = "") -> None:
    state.attempts += 1
    state.last_result = result
    state.last_error = error
    state.updated_at = _now()

    if error and state.last_error == error:
        state.consecutive_same_failures += 1
    else:
        state.consecutive_same_failures = 1 if error else 0


def mark_completed(state: RuntimeState) -> None:
    state.status = "completed"
    state.completed_at = _now()
    state.updated_at = _now()


def mark_failed(state: RuntimeState, reason: str = "") -> None:
    state.status = "failed"
    state.last_error = reason
    state.updated_at = _now()


def mark_waiting(state: RuntimeState) -> None:
    state.status = "waiting_for_limit_reset"
    state.updated_at = _now()


def mark_review(state: RuntimeState, reason: str = "") -> None:
    state.status = "review_required"
    state.last_error = reason
    state.updated_at = _now()
