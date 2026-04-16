"""OpenAI Codex CLI agent adapter."""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from .base import BaseAgent, AgentRunResult
from ..models import RunResult

log = logging.getLogger(__name__)


class CodexAgent(BaseAgent):
    name = "codex"

    def _execute(
        self,
        task_file: Path,
        working_dir: Path,
        model: str,
        log_file: Path,
        transcript_file: Path,
        timeout: int,
        context_file: Optional[Path] = None,
    ) -> AgentRunResult:
        task_content = self._build_input(task_file, context_file)

        # Use non-interactive mode and read the prompt from stdin ("-").
        # This avoids Windows command-line length limits for large task payloads.
        cmd = ["codex", "exec", "--full-auto", "-"]
        if model:
            cmd.extend(["--model", model])

        log.info("Running codex: %s (cwd=%s)", " ".join(cmd), working_dir)

        try:
            stdout, stderr, returncode = self._run_subprocess(
                cmd, task_content, working_dir,
                log_file, transcript_file, timeout,
                self.get_env(working_dir),
            )
        except subprocess.TimeoutExpired:
            return AgentRunResult(
                result=RunResult.TIMEOUT,
                exit_code=-1,
                error_message=f"Codex timed out after {timeout}s",
            )
        except FileNotFoundError:
            return AgentRunResult(
                result=RunResult.LIMIT_HIT,
                exit_code=-1,
                error_message="Codex CLI not found — rotating to next agent. Install with: npm install -g @openai/codex",
            )

        combined = stdout + "\n" + stderr

        if self.detect_limit_hit(combined):
            return AgentRunResult(
                result=RunResult.LIMIT_HIT,
                exit_code=returncode,
                error_message="Rate limit hit",
            )

        if returncode != 0:
            return AgentRunResult(
                result=RunResult.HARD_ERROR,
                exit_code=returncode,
                error_message=stderr.strip()[:500],
            )

        return AgentRunResult(
            result=RunResult.SUCCESS,
            exit_code=0,
            output_file=str(transcript_file),
        )

    def run(self, task_file, working_dir, model, log_file, transcript_file,
            timeout=3600, context_file=None):
        return self._execute(task_file, working_dir, model, log_file,
                             transcript_file, timeout, context_file)

    def resume(self, task_file, working_dir, model, log_file, transcript_file,
               timeout=3600, context_file=None):
        log.info("Codex has no native resume; re-running task")
        return self._execute(task_file, working_dir, model, log_file,
                             transcript_file, timeout, context_file)
