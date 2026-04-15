"""Abstract base for agent adapters."""

import logging
import shutil
import subprocess
import sys
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Tuple

from ..models import RunResult
from ..env import build_agent_env

log = logging.getLogger(__name__)


@dataclass
class AgentRunResult:
    result: RunResult
    exit_code: int = 0
    output_file: Optional[str] = None
    error_message: str = ""
    token_usage: dict = None

    def __post_init__(self):
        if self.token_usage is None:
            self.token_usage = {}


class BaseAgent(ABC):
    """Interface that all agent adapters must implement."""

    name: str = "base"
    _env_cache: Optional[Dict[str, str]] = None

    def get_env(self, working_dir: Path) -> Dict[str, str]:
        """Get environment variables for subprocess, loading .agent/.env once."""
        if self._env_cache is not None:
            return self._env_cache

        # Look for .agent/ relative to working_dir
        agent_dir = working_dir / ".agent"
        if not agent_dir.exists():
            agent_dir = working_dir.parent / ".agent"

        self._env_cache = build_agent_env(agent_dir)
        return self._env_cache

    @abstractmethod
    def run(
        self,
        task_file: Path,
        working_dir: Path,
        model: str,
        log_file: Path,
        transcript_file: Path,
        timeout: int = 3600,
        context_file: Optional[Path] = None,
    ) -> AgentRunResult:
        """Execute the agent on a task file. First run."""
        ...

    @abstractmethod
    def resume(
        self,
        task_file: Path,
        working_dir: Path,
        model: str,
        log_file: Path,
        transcript_file: Path,
        timeout: int = 3600,
        context_file: Optional[Path] = None,
    ) -> AgentRunResult:
        """Resume a previously interrupted run."""
        ...

    def _build_input(self, task_file: Path, context_file: Optional[Path] = None) -> str:
        """Build agent input: PROJECT.md + graphify context + task content.

        Layer order:
          1. PROJECT.md  — shared project knowledge (architecture, conventions)
          2. context_file — per-task context from graphify hook
          3. task_file    — the actual task instructions
        """
        parts = []

        # Layer 1: shared project knowledge
        project_md = self._find_project_md(task_file)
        if project_md and project_md.exists():
            proj = project_md.read_text(encoding="utf-8").strip()
            if proj:
                parts.append(proj)
                parts.append("\n---\n")
                log.info("Prepending PROJECT.md (%d chars)", len(proj))

        # Layer 2: per-task context (graphify output)
        if context_file and context_file.exists():
            ctx = context_file.read_text(encoding="utf-8").strip()
            if ctx:
                parts.append(ctx)
                parts.append("\n---\n")
                log.info("Prepending context from %s (%d chars)", context_file, len(ctx))

        # Layer 3: task instructions
        parts.append(task_file.read_text(encoding="utf-8"))
        return "\n".join(parts)

    @staticmethod
    def _find_project_md(task_file: Path) -> Optional[Path]:
        """Locate .agent/PROJECT.md relative to the task file."""
        # task_file is typically .agent/tasks/foo.md → parent.parent = .agent/
        agent_dir = task_file.parent.parent
        candidate = agent_dir / "PROJECT.md"
        if candidate.exists():
            return candidate
        # Also check one level up (if task_file path is different)
        candidate2 = agent_dir.parent / ".agent" / "PROJECT.md"
        if candidate2.exists():
            return candidate2
        return None

    def _run_subprocess(
        self,
        cmd: list,
        input_text: str,
        cwd: Path,
        log_file: Path,
        transcript_file: Path,
        timeout: int,
        env: Dict[str, str],
    ) -> Tuple[str, str, int]:
        """Run a subprocess with real-time streaming to log_file.

        stdout and stderr are written to log_file as they arrive, so
        `tail -f .agent/logs/task-NNN.log` shows live agent output.
        stdout is also saved to transcript_file after completion.

        Returns (stdout, stderr, returncode).
        Raises subprocess.TimeoutExpired on timeout (caller must handle).
        Raises FileNotFoundError if the executable is not found.
        """
        log_file.parent.mkdir(parents=True, exist_ok=True)
        transcript_file.parent.mkdir(parents=True, exist_ok=True)

        # On Windows, .cmd and .bat wrappers (e.g. npm-installed CLIs like codex, gemini)
        # cannot be executed directly by CreateProcess — they require cmd.exe /c.
        # Detect this and wrap transparently so callers always use plain command names.
        if sys.platform == "win32" and cmd:
            resolved = shutil.which(cmd[0], path=env.get("PATH") if env else None)
            if resolved and resolved.lower().endswith((".cmd", ".bat")):
                log.debug("Wrapping .cmd for Windows: %s -> cmd.exe /c %s", cmd[0], resolved)
                cmd = ["cmd.exe", "/c", resolved] + list(cmd[1:])

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd),
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        stdout_chunks: list = []
        stderr_chunks: list = []

        def _stream(stream, chunks, log_f):
            for line in stream:
                chunks.append(line)
                log_f.write(line)
                log_f.flush()

        with open(log_file, "a", encoding="utf-8", errors="replace") as lf:
            t_out = threading.Thread(target=_stream, args=(proc.stdout, stdout_chunks, lf))
            t_err = threading.Thread(target=_stream, args=(proc.stderr, stderr_chunks, lf))
            t_out.start()
            t_err.start()

            try:
                proc.stdin.write(input_text)
                proc.stdin.close()
            except BrokenPipeError:
                pass

            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                t_out.join(timeout=5)
                t_err.join(timeout=5)
                raise

            t_out.join()
            t_err.join()

        stdout = "".join(stdout_chunks)
        stderr = "".join(stderr_chunks)

        with open(transcript_file, "w", encoding="utf-8", errors="replace") as tf:
            tf.write(stdout)

        return stdout, stderr, proc.returncode

    def detect_limit_hit(self, output: str) -> bool:
        """Check if the output indicates a rate/token limit."""
        limit_phrases = [
            "you've hit your limit",
            "rate limit",
            "quota exceeded",
            "429",
            "too many requests",
            "token limit",
            "usage limit",
            "credit limit",
            "billing limit",
        ]
        output_lower = output.lower()
        return any(phrase in output_lower for phrase in limit_phrases)

    def detect_success(self, output: str, exit_code: int) -> bool:
        """Check if the agent run was successful."""
        return exit_code == 0
