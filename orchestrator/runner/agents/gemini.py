"""Google Gemini CLI agent adapter."""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from .base import BaseAgent, AgentRunResult
from ..models import RunResult

log = logging.getLogger(__name__)


class GeminiAgent(BaseAgent):
    name = "gemini"

    def _build_cmd(self, model: str, sandbox: bool = True) -> list:
        cmd = ["gemini"]
        if sandbox:
            cmd.append("--sandbox")
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
        cmd = self._build_cmd(model)
        task_content = self._build_input(task_file, context_file)

        log.info("Running gemini: %s (cwd=%s)", " ".join(cmd), working_dir)

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
                error_message=f"Gemini timed out after {timeout}s",
            )
        except FileNotFoundError:
            return AgentRunResult(
                result=RunResult.LIMIT_HIT,
                exit_code=-1,
                error_message="Gemini CLI not found — rotating to next agent. Install with: npm install -g @google/gemini-cli",
            )

        combined = stdout + "\n" + stderr

        if self.detect_limit_hit(combined):
            return AgentRunResult(
                result=RunResult.LIMIT_HIT,
                exit_code=returncode,
                output_file=str(transcript_file),
                error_message="Gemini rate limit hit",
            )

        if returncode != 0:
            stderr_lower = stderr.lower()
            transient_signals = ["network", "connection", "timeout", "503", "502", "unavailable"]
            if any(sig in stderr_lower for sig in transient_signals):
                return AgentRunResult(
                    result=RunResult.TRANSIENT_ERROR,
                    exit_code=returncode,
                    output_file=str(transcript_file),
                    error_message=stderr.strip()[:500],
                )
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
        log.info("Gemini has no native resume; re-running task")
        return self._execute(task_file, working_dir, model, log_file,
                             transcript_file, timeout, context_file)
