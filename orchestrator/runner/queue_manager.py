"""Queue.md parser and writer — the declarative task list."""

import re
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from .models import QueueEntry, TaskStatus

log = logging.getLogger(__name__)

# Matches a queue table row:  | Id | TaskFile | Status | DependsOn | Agent | Model | BaseBranch | WorkBranch | TargetBranch | Attempts |
ROW_RE = re.compile(
    r"^\|\s*(\S+)\s*\|"       # id
    r"\s*(\S+)\s*\|"           # task_file
    r"\s*(\S+)\s*\|"           # status
    r"\s*([^|]*?)\s*\|"        # depends_on
    r"\s*(\S+)\s*\|"           # agent
    r"\s*(\S+)\s*\|"           # model
    r"\s*(\S+)\s*\|"           # base_branch
    r"\s*(\S+)\s*\|"           # work_branch
    r"\s*(\S+)\s*\|"           # target_branch
    r"\s*(\S+)\s*\|"           # attempts
)

HEADER_FIELDS = ["Id", "TaskFile", "Status", "DependsOn", "Agent", "Model",
                 "BaseBranch", "WorkBranch", "TargetBranch", "Attempts"]


def _parse_depends(raw: str) -> List[str]:
    raw = raw.strip()
    if not raw or raw in ("—", "-", "none", "None"):
        return []
    return [d.strip() for d in raw.split(",") if d.strip()]


def _format_depends(deps: List[str]) -> str:
    return ", ".join(deps) if deps else "—"


def _safe_status(raw: str) -> TaskStatus:
    try:
        return TaskStatus(raw)
    except ValueError:
        return TaskStatus.QUEUED


def load_queue(queue_path: Path) -> List[QueueEntry]:
    if not queue_path.exists():
        return []
    entries = []
    for line in queue_path.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        id_val = m.group(1)
        # Skip header / separator rows
        if id_val in ("Id", "---", "----") or id_val.startswith("-"):
            continue
        entries.append(QueueEntry(
            id=id_val,
            task_file=m.group(2),
            status=_safe_status(m.group(3)),
            depends_on=_parse_depends(m.group(4)),
            agent=m.group(5),
            model=m.group(6),
            base_branch=m.group(7),
            work_branch=m.group(8),
            target_branch=m.group(9),
            attempts=int(m.group(10)) if m.group(10).isdigit() else 0,
        ))
    return entries


def save_queue(queue_path: Path, entries: List[QueueEntry]) -> None:
    """Write queue entries back to queue.md, preserving the table format."""
    # Calculate column widths
    widths = [len(h) for h in HEADER_FIELDS]
    rows = []
    for e in entries:
        row = [
            e.id,
            e.task_file,
            e.status.value,
            _format_depends(e.depends_on),
            e.agent,
            e.model,
            e.base_branch,
            e.work_branch if e.work_branch else "—",
            e.target_branch,
            str(e.attempts),
        ]
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
        rows.append(row)

    def fmt_row(cells):
        parts = [f" {cells[i]:<{widths[i]}} " for i in range(len(cells))]
        return "|" + "|".join(parts) + "|"

    lines = [
        "# Task Queue",
        "",
        fmt_row(HEADER_FIELDS),
        "|" + "|".join("-" * (w + 2) for w in widths) + "|",
    ]
    for row in rows:
        lines.append(fmt_row(row))
    lines.append("")

    with open(queue_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def update_entry_status(
    queue_path: Path,
    task_id: str,
    new_status: TaskStatus,
    attempts: Optional[int] = None,
    work_branch: Optional[str] = None,
) -> None:
    """Update a single entry in queue.md without rewriting the whole file."""
    entries = load_queue(queue_path)
    for e in entries:
        if e.id == task_id:
            e.status = new_status
            if attempts is not None:
                e.attempts = attempts
            if work_branch is not None:
                e.work_branch = work_branch
            break
    save_queue(queue_path, entries)


def find_runnable_tasks(entries: List[QueueEntry]) -> List[QueueEntry]:
    """Return tasks whose dependencies are all completed and status is runnable."""
    completed_ids = {e.id for e in entries if e.status == TaskStatus.COMPLETED}
    runnable = []
    for e in entries:
        if not TaskStatus.is_runnable(e.status):
            continue
        if all(dep in completed_ids for dep in e.depends_on):
            runnable.append(e)
    return runnable


def find_resumable_tasks(entries: List[QueueEntry]) -> List[QueueEntry]:
    """Return tasks that need resumption (in_progress or waiting_for_limit)."""
    return [
        e for e in entries
        if e.status in (TaskStatus.IN_PROGRESS, TaskStatus.WAITING_FOR_LIMIT)
    ]


def all_tasks_terminal(entries: List[QueueEntry]) -> bool:
    return all(TaskStatus.is_terminal(e.status) for e in entries)


def add_entry(
    queue_path: Path,
    task_file: str,
    agent: str = "claude",
    model: str = "auto",
    depends_on: Optional[List[str]] = None,
    base_branch: str = "",
    target_branch: str = "",
) -> QueueEntry:
    """Add a new entry to the queue. Auto-assigns the next ID."""
    entries = load_queue(queue_path)
    max_id = 0
    for e in entries:
        try:
            max_id = max(max_id, int(e.id))
        except ValueError:
            pass

    new_id = str(max_id + 1).zfill(3)
    slug = task_file.replace("tasks/", "").replace(".md", "")
    entry = QueueEntry(
        id=new_id,
        task_file=task_file,
        status=TaskStatus.QUEUED,
        depends_on=depends_on or [],
        agent=agent,
        model=model,
        base_branch=base_branch or "main",
        work_branch=f"agent/{new_id}-{slug}",
        target_branch=target_branch or "main",
        attempts=0,
    )
    entries.append(entry)
    save_queue(queue_path, entries)
    return entry
