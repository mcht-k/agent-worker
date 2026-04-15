"""Post-execution validation — run commands to verify task success."""

import logging
import subprocess
from pathlib import Path
from typing import List, Tuple

from .config import ValidationRule

log = logging.getLogger(__name__)


def run_validations(
    rules: List[ValidationRule],
    working_dir: Path,
) -> Tuple[bool, List[str]]:
    """Run all validation rules. Returns (all_passed, list_of_failure_messages)."""
    if not rules:
        return True, []

    failures = []
    for rule in rules:
        if not rule.command:
            continue
        log.info("Running validation: %s → %s", rule.name, rule.command)
        try:
            result = subprocess.run(
                rule.command,
                shell=True,
                cwd=str(working_dir),
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=300,
            )
            if result.returncode != 0:
                msg = f"{rule.name}: exit {result.returncode} — {result.stderr.strip()[:200]}"
                if rule.required:
                    failures.append(msg)
                    log.error("Validation FAILED (required): %s", msg)
                else:
                    log.warning("Validation FAILED (optional): %s", msg)
            else:
                log.info("Validation passed: %s", rule.name)
        except subprocess.TimeoutExpired:
            msg = f"{rule.name}: timed out after 300s"
            if rule.required:
                failures.append(msg)
            log.error("Validation timeout: %s", rule.name)
        except Exception as e:
            msg = f"{rule.name}: {e}"
            if rule.required:
                failures.append(msg)
            log.error("Validation error: %s", msg)

    all_passed = len(failures) == 0
    return all_passed, failures
