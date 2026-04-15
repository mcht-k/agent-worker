"""Aider agent adapter — code editor with multi-model support."""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from .base import BaseAgent, AgentRunResult
from ..models import RunResult

log = logging.getLogger(__name__)


class AiderAgent(BaseAgent):
    name = "aider"

    def _build_cmd(self, model: str) -> list:
        cmd = [
            "aider",
            "--yes-always",        # auto-approve all changes
            "--no-auto-commits",   # orchestrator handles git
            "--no-git",            # don't let aider manage git
            "--no-pretty",         # clean output for parsing
        ]
        if model:
            cmd.extend(["--model", model])
        return cmd

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
        cmd = self._build_cmd(model)
        cmd.extend(["--message", task_content])

        log.info("Running aider: model=%s (cwd=%s)", model or "default", working_dir)

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
                error_message=f"Aider timed out after {timeout}s",
            )
        except FileNotFoundError:
            return AgentRunResult(
                result=RunResult.LIMIT_HIT,
                exit_code=-1,
                error_message="Aider not found — rotating to next agent. Install with: pip install aider-chat",
            )

        combined = stdout + "\n" + stderr

        if self.detect_limit_hit(combined):
            return AgentRunResult(
                result=RunResult.LIMIT_HIT,
                exit_code=returncode,
                output_file=str(transcript_file),
                error_message="Aider rate limit hit",
            )

        if returncode != 0:
            return AgentRunResult(
                result=RunResult.HARD_ERROR,
                exit_code=returncode,
                output_file=str(transcript_file),
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
        log.info("Aider has no resume; re-running task")
        return self._execute(task_file, working_dir, model, log_file,
                             transcript_file, timeout, context_file)
