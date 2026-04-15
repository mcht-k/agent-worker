"""Task file parser — handles YAML frontmatter + markdown body."""

import re
from pathlib import Path
from typing import Tuple

from .models import TaskMeta

try:
    import yaml
except ImportError:
    yaml = None

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_task_file(task_path: Path) -> Tuple[TaskMeta, str]:
    """Parse a task file into metadata and markdown body.

    Supports two formats:
    1. YAML frontmatter (---) at the top → parsed into TaskMeta
    2. Legacy format (no frontmatter) → empty TaskMeta, full file as body
    """
    content = task_path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(content)

    if match and yaml is not None:
        try:
            raw = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            # Malformed frontmatter (e.g. template placeholders) — treat as legacy
            return TaskMeta(), content
        body = content[match.end():]
        deps = raw.get("dependsOn", raw.get("depends_on", []))
        if isinstance(deps, str):
            deps = [d.strip() for d in deps.split(",") if d.strip()]
        meta = TaskMeta(
            id=str(raw.get("id", "")),
            agent=raw.get("agent", ""),
            model=raw.get("model", ""),
            base_branch=raw.get("baseBranch", raw.get("base_branch", "")),
            target_branch=raw.get("targetBranch", raw.get("target_branch", "")),
            depends_on=deps,
            priority=raw.get("priority", "normal"),
            allow_parallel=raw.get("allowParallel", raw.get("allow_parallel", False)),
            timeout=int(raw.get("timeout", 0)),
        )
        return meta, body

    # Legacy format — no frontmatter
    return TaskMeta(), content


def get_task_body_for_agent(task_path: Path) -> str:
    """Return the full task file content for piping to the agent.

    Agents receive the entire file including frontmatter so they can
    see metadata context. The frontmatter is just YAML comments to them.
    """
    return task_path.read_text(encoding="utf-8")
