"""Data models and enums for Agent Runner."""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict


class TaskStatus(str, Enum):
    QUEUED = "queued"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_LIMIT = "waiting_for_limit_reset"
    REVIEW_REQUIRED = "review_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def is_terminal(cls, status: "TaskStatus") -> bool:
        return status in (cls.COMPLETED, cls.FAILED, cls.CANCELLED)

    @classmethod
    def is_runnable(cls, status: "TaskStatus") -> bool:
        return status in (cls.QUEUED, cls.WAITING_FOR_LIMIT)


class RunResult(str, Enum):
    SUCCESS = "success"
    LIMIT_HIT = "limit_hit"
    TRANSIENT_ERROR = "transient_error"
    HARD_ERROR = "hard_error"
    TIMEOUT = "timeout"
    NO_CHANGES = "no_changes"
    MANUAL_REVIEW = "manual_review_needed"


RETRYABLE_RESULTS = {RunResult.LIMIT_HIT, RunResult.TRANSIENT_ERROR, RunResult.TIMEOUT}


@dataclass
class QueueEntry:
    id: str
    task_file: str
    status: TaskStatus
    depends_on: List[str]
    agent: str
    model: str
    base_branch: str
    work_branch: str
    target_branch: str
    attempts: int = 0

    def effective_work_branch(self) -> str:
        if self.work_branch and self.work_branch != "—":
            return self.work_branch
        slug = self.task_file.replace("tasks/", "").replace(".md", "")
        return f"agent/{self.id}-{slug}"


@dataclass
class TaskMeta:
    """YAML frontmatter parsed from a task file."""
    id: str = ""
    agent: str = ""
    model: str = ""
    base_branch: str = ""
    target_branch: str = ""
    depends_on: List[str] = field(default_factory=list)
    priority: str = "normal"
    allow_parallel: bool = False
    timeout: int = 0


@dataclass
class RuntimeState:
    """Per-task runtime state stored as JSON."""
    task_id: str
    status: str = "queued"
    agent: str = "claude"
    model: str = "auto"
    attempts: int = 0
    max_attempts: int = 5
    resume_strategy: str = "continue"
    last_result: str = ""
    last_error: str = ""
    started_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    work_branch: str = ""
    worktree_path: str = ""
    log_file: str = ""
    transcript_file: str = ""
    token_usage: Dict = field(default_factory=dict)
    consecutive_same_failures: int = 0
