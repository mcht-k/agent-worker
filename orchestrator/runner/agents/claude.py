"""Claude Code agent adapter."""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from .base import BaseAgent, AgentRunResult
from ..models import RunResult

log = logging.getLogger(__name__)


class ClaudeAgent(BaseAgent):
    name = "claude"

    def _build_cmd(self, model: str, resume: bool = False) -> list:
        cmd = ["claude", "-p", "--dangerously-skip-permissions"]
        if resume:
            cmd.append("--continue")
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
        resume: bool = False,
        context_file: Optional[Path] = None,
    ) -> AgentRunResult:
        cmd = self._build_cmd(model, resume=resume)
        task_content = self._build_input(task_file, context_file)

        log.info("Running: %s (cwd=%s, resume=%s, context=%s)",
                 " ".join(cmd), working_dir, resume,
                 context_file if context_file and context_file.exists() else "none")

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
                error_message=f"Agent timed out after {timeout}s",
            )
        except FileNotFoundError:
            return AgentRunResult(
                result=RunResult.HARD_ERROR,
                exit_code=-1,
                error_message="Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code",
            )

        combined = stdout + "\n" + stderr

        if self.detect_limit_hit(combined):
            return AgentRunResult(
                result=RunResult.LIMIT_HIT,
                exit_code=returncode,
                output_file=str(transcript_file),
                error_message="Token/rate limit hit",
            )

        if returncode != 0:
            stderr_lower = stderr.lower()
            transient_signals = ["network", "connection", "econnreset", "timeout", "503", "502"]
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
        return self._execute(task_file, working_dir, model, log_file, transcript_file,
                             timeout, resume=False, context_file=context_file)

    def resume(self, task_file, working_dir, model, log_file, transcript_file,
               timeout=3600, context_file=None):
        return self._execute(task_file, working_dir, model, log_file, transcript_file,
                             timeout, resume=True, context_file=context_file)
