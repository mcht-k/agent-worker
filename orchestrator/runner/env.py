"""Environment variable loader — reads .agent/.env and merges with system env.

File format (standard dotenv):
  KEY=value
  KEY="quoted value"
  KEY='single quoted'
  # comment
  export KEY=value    (export prefix stripped)

Loaded once at scheduler start, injected into every agent subprocess.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict

log = logging.getLogger(__name__)

LINE_RE = re.compile(
    r"^\s*(?:export\s+)?"      # optional export
    r"([A-Za-z_][A-Za-z0-9_]*)"  # key
    r"\s*=\s*"                 # =
    r"(.*?)\s*$"               # value
)


def parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a .env file into a dict. Returns empty dict if file missing."""
    if not path.exists():
        return {}

    result = {}
    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        m = LINE_RE.match(line)
        if not m:
            log.debug(".env line %d skipped: %s", lineno, raw_line[:60])
            continue

        key = m.group(1)
        value = m.group(2)

        # Strip surrounding quotes
        if len(value) >= 2:
            if (value[0] == '"' and value[-1] == '"') or \
               (value[0] == "'" and value[-1] == "'"):
                value = value[1:-1]

        result[key] = value

    if result:
        log.info("Loaded %d env vars from %s", len(result), path)

    return result


def build_agent_env(agent_dir: Path) -> Dict[str, str]:
    """Build the environment for agent subprocesses.

    Merge order (later wins):
      1. System environment (os.environ)
      2. .agent/.env file
    """
    env = os.environ.copy()

    dotenv_path = agent_dir / ".env"
    dotenv_vars = parse_env_file(dotenv_path)
    env.update(dotenv_vars)

    return env
