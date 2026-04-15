"""File-based locking with stale PID detection."""

import os
import signal
from pathlib import Path


def _pid_alive(pid: int) -> bool:
    """Check if a process with given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def acquire_lock(lock_path: Path) -> bool:
    """Try to acquire a lock file. Returns True if acquired."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if lock_path.exists():
        try:
            existing_pid = int(lock_path.read_text().strip())
            if _pid_alive(existing_pid):
                return False
            # Stale lock — previous process died
        except (ValueError, OSError):
            pass

    lock_path.write_text(str(os.getpid()))
    return True


def release_lock(lock_path: Path) -> None:
    """Release a lock file if we own it."""
    try:
        if lock_path.exists():
            pid = int(lock_path.read_text().strip())
            if pid == os.getpid():
                lock_path.unlink()
    except (ValueError, OSError):
        pass


def acquire_task_lock(locks_dir: Path, task_id: str) -> bool:
    return acquire_lock(locks_dir / f"{task_id}.lock")


def release_task_lock(locks_dir: Path, task_id: str) -> None:
    release_lock(locks_dir / f"{task_id}.lock")
