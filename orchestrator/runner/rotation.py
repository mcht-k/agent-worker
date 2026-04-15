"""Agent rotation — switch agents on rate limit instead of waiting.

Tracks per-agent cooldown globally. When an agent hits a limit, the scheduler
picks the next available agent from the rotation order instead of sleeping.

State file: .agent/state/_agent_limits.json
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List

log = logging.getLogger(__name__)

LIMITS_FILE = "_agent_limits.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _parse_ts(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")


def _load_limits(state_dir: Path) -> dict:
    path = state_dir / LIMITS_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_limits(state_dir: Path, limits: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / LIMITS_FILE
    path.write_text(json.dumps(limits, indent=2), encoding="utf-8")


def is_agent_limited(state_dir: Path, agent: str, cooldown_seconds: int) -> bool:
    """Check if an agent is currently in cooldown from a rate limit."""
    limits = _load_limits(state_dir)
    entry = limits.get(agent)
    if not entry:
        return False

    limited_at = entry.get("limited_at", "")
    if not limited_at:
        return False

    try:
        elapsed = (datetime.now(timezone.utc).replace(tzinfo=None) - _parse_ts(limited_at)).total_seconds()
        if elapsed >= cooldown_seconds:
            # Cooldown expired — clear it
            clear_agent_limit(state_dir, agent)
            return False
        return True
    except ValueError:
        return False


def remaining_cooldown(state_dir: Path, agent: str, cooldown_seconds: int) -> int:
    """Seconds remaining in cooldown. 0 if not limited."""
    limits = _load_limits(state_dir)
    entry = limits.get(agent)
    if not entry or not entry.get("limited_at"):
        return 0
    try:
        elapsed = (datetime.now(timezone.utc).replace(tzinfo=None) - _parse_ts(entry["limited_at"])).total_seconds()
        remaining = cooldown_seconds - elapsed
        return max(0, int(remaining))
    except ValueError:
        return 0


def mark_agent_limited(state_dir: Path, agent: str) -> None:
    """Record that an agent hit its rate limit."""
    limits = _load_limits(state_dir)
    limits[agent] = {"limited_at": _now()}
    _save_limits(state_dir, limits)
    log.info("Marked agent '%s' as rate-limited at %s", agent, _now())


def clear_agent_limit(state_dir: Path, agent: str) -> None:
    """Clear an agent's rate limit (e.g. after successful run)."""
    limits = _load_limits(state_dir)
    if agent in limits:
        del limits[agent]
        _save_limits(state_dir, limits)
        log.debug("Cleared rate limit for agent '%s'", agent)


def get_available_agent(
    state_dir: Path,
    preferred: str,
    rotation_order: List[str],
    cooldown_seconds: int,
) -> Optional[str]:
    """Get the best available agent, preferring `preferred` if not limited.

    Returns None if all agents in rotation are currently limited.
    """
    # Try preferred first
    if not is_agent_limited(state_dir, preferred, cooldown_seconds):
        return preferred

    log.info("Preferred agent '%s' is rate-limited, checking rotation...", preferred)

    # Try rotation order
    for agent in rotation_order:
        if agent == preferred:
            continue
        if not is_agent_limited(state_dir, agent, cooldown_seconds):
            log.info("Rotating to agent '%s'", agent)
            return agent

    # All limited — find the one with shortest remaining cooldown
    shortest_agent = preferred
    shortest_remaining = cooldown_seconds
    for agent in rotation_order:
        r = remaining_cooldown(state_dir, agent, cooldown_seconds)
        if r < shortest_remaining:
            shortest_remaining = r
            shortest_agent = agent

    log.warning("All agents rate-limited. Shortest wait: %s (%ds remaining)",
                shortest_agent, shortest_remaining)
    return None


def get_rotation_status(state_dir: Path, rotation_order: List[str], cooldown_seconds: int) -> list:
    """Get status of all agents in rotation. For CLI display."""
    result = []
    for agent in rotation_order:
        limited = is_agent_limited(state_dir, agent, cooldown_seconds)
        remaining = remaining_cooldown(state_dir, agent, cooldown_seconds)
        result.append({
            "agent": agent,
            "limited": limited,
            "remaining_seconds": remaining,
        })
    return result
