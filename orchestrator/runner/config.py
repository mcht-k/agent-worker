"""YAML configuration loader and model tier resolution."""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class RunnerConfig:
    max_parallel: int = 1
    poll_interval_seconds: int = 30
    task_timeout_seconds: int = 3600
    max_attempts: int = 5
    limit_retry_wait_seconds: int = 1800
    store_artifacts: bool = True


@dataclass
class GitConfig:
    default_base_branch: str = "main"
    default_target_branch: str = "main"
    merge_mode: str = "direct"
    on_conflict: str = "review_required"
    delete_work_branch_after_merge: bool = False
    use_worktrees: bool = False
    auto_push: bool = True
    post_merge_validation: str = ""


@dataclass
class AgentModelConfig:
    high: str = "claude-opus-4-6"
    medium: str = "claude-sonnet-4-6"
    low: str = "claude-haiku-4-5"


@dataclass
class ModelAutoRule:
    pattern: str
    model: str


@dataclass
class RotationConfig:
    enabled: bool = False
    strategy: str = "on_limit"  # on_limit = switch agent when current hits limit
    order: List[str] = field(default_factory=lambda: ["claude", "gemini", "codex", "aider"])


@dataclass
class SmartTieringConfig:
    enabled: bool = False
    classifier_agent: str = "gemini"
    classifier_model: str = "low"  # Usually flash or haiku
    timeout: int = 60


@dataclass
class AgentsConfig:
    default: str = "claude"
    allowed: List[str] = field(default_factory=lambda: ["claude", "codex", "gemini", "aider"])
    models: AgentModelConfig = field(default_factory=AgentModelConfig)
    agent_models: Dict[str, AgentModelConfig] = field(default_factory=dict)
    auto_rules: List[ModelAutoRule] = field(default_factory=list)
    default_model_tier: str = "medium"
    rotation: RotationConfig = field(default_factory=RotationConfig)
    smart_tiering: SmartTieringConfig = field(default_factory=SmartTieringConfig)


@dataclass
class NotificationsConfig:
    ntfy_enabled: bool = False
    ntfy_url: str = ""
    ntfy_topic: str = ""
    events: List[str] = field(default_factory=lambda: [
        "task_started", "task_completed", "task_failed",
        "limit_hit", "queue_empty", "review_required",
    ])


@dataclass
class ValidationRule:
    name: str = ""
    command: str = ""
    required: bool = True


@dataclass
class HooksConfig:
    """Hook definitions per lifecycle phase.

    Each phase contains a list of hook dicts with keys:
      name, enabled, command, required, timeout
    Built-in hooks (name only, no command): graphify, update_claude_md
    """
    pre_task: List[Dict] = field(default_factory=list)
    post_task: List[Dict] = field(default_factory=list)
    post_merge: List[Dict] = field(default_factory=list)
    on_failure: List[Dict] = field(default_factory=list)


@dataclass
class Config:
    runner: RunnerConfig = field(default_factory=RunnerConfig)
    git: GitConfig = field(default_factory=GitConfig)
    agents: AgentsConfig = field(default_factory=AgentsConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    validation: List[ValidationRule] = field(default_factory=list)
    hooks: HooksConfig = field(default_factory=HooksConfig)


def _load_yaml(path: Path) -> dict:
    if yaml is None:
        raise ImportError(
            "PyYAML is required. Install it with: pip install pyyaml"
        )
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_config(config_path: Path) -> Config:
    if not config_path.exists():
        return Config()

    raw = _load_yaml(config_path)
    config = Config()

    if "runner" in raw:
        r = raw["runner"]
        config.runner = RunnerConfig(**{
            k: r[k] for k in RunnerConfig.__dataclass_fields__ if k in r
        })

    if "git" in raw:
        g = raw["git"]
        config.git = GitConfig(**{
            k: g[k] for k in GitConfig.__dataclass_fields__ if k in g
        })

    if "agents" in raw:
        a = raw["agents"]
        models_raw = a.get("models", {})
        models = AgentModelConfig(**{
            k: models_raw[k]
            for k in AgentModelConfig.__dataclass_fields__
            if k in models_raw
        })
        auto_rules = [
            ModelAutoRule(pattern=r.get("pattern", ""), model=r.get("model", "medium"))
            for r in a.get("auto_rules", [])
        ]
        agent_models_raw = a.get("agent_models", {}) or {}
        agent_models: Dict[str, AgentModelConfig] = {}
        for agent_name, model_map in agent_models_raw.items():
            if not isinstance(model_map, dict):
                continue
            agent_models[str(agent_name)] = AgentModelConfig(**{
                k: model_map[k]
                for k in AgentModelConfig.__dataclass_fields__
                if k in model_map
            })
        rot_raw = a.get("rotation", {})
        rotation = RotationConfig(
            enabled=rot_raw.get("enabled", False),
            strategy=rot_raw.get("strategy", "on_limit"),
            order=rot_raw.get("order", ["claude", "gemini", "codex", "aider"]),
        )
        st_raw = a.get("smart_tiering", {})
        smart_tiering = SmartTieringConfig(
            enabled=st_raw.get("enabled", False),
            classifier_agent=st_raw.get("classifier_agent", "gemini"),
            classifier_model=st_raw.get("classifier_model", "low"),
            timeout=st_raw.get("timeout", 60),
        )
        config.agents = AgentsConfig(
            default=a.get("default", "claude"),
            allowed=a.get("allowed", ["claude", "codex", "gemini", "aider"]),
            models=models,
            agent_models=agent_models,
            auto_rules=auto_rules,
            default_model_tier=a.get("default_model_tier", "medium"),
            rotation=rotation,
            smart_tiering=smart_tiering,
        )

    if "notifications" in raw:
        n = raw["notifications"]
        config.notifications = NotificationsConfig(**{
            k: n[k]
            for k in NotificationsConfig.__dataclass_fields__
            if k in n
        })

    if "validation" in raw:
        for v in raw["validation"]:
            config.validation.append(ValidationRule(
                name=v.get("name", ""),
                command=v.get("command", ""),
                required=v.get("required", True),
            ))

    if "hooks" in raw:
        h = raw["hooks"]
        config.hooks = HooksConfig(
            pre_task=h.get("pre_task", []) or [],
            post_task=h.get("post_task", []) or [],
            post_merge=h.get("post_merge", []) or [],
            on_failure=h.get("on_failure", []) or [],
        )

    return config


def resolve_model(config: Config, task_id: str, task_model: str) -> str:
    """Resolve a model tier name (high/medium/low/auto) to an actual model ID."""
    models = config.agents.models
    tier_map = {"high": models.high, "medium": models.medium, "low": models.low}

    # Already an explicit model name
    if task_model and task_model not in ("auto", "high", "medium", "low", ""):
        return task_model

    # Explicit tier
    if task_model in tier_map:
        return tier_map[task_model]

    # Auto — match against rules
    for rule in config.agents.auto_rules:
        patterns = [p.strip() for p in rule.pattern.split("|")]
        for pattern in patterns:
            regex = "^" + pattern.replace("*", ".*") + "$"
            if re.match(regex, task_id):
                return tier_map.get(rule.model, rule.model)

    # Fallback to default tier
    return tier_map.get(config.agents.default_model_tier, models.medium)


def resolve_model_for_agent(config: Config, task_id: str, task_model: str, agent_name: Optional[str]) -> str:
    """Resolve model and ensure it is compatible with the selected agent.

    Backward-compatible behavior:
    - keeps existing global tier mapping for Claude-only setups
    - allows optional per-agent tier maps under agents.agent_models
    """
    resolved = resolve_model(config, task_id, task_model)
    if not agent_name:
        return resolved

    tier = task_model if task_model in ("high", "medium", "low") else None
    if task_model in ("", "auto", None):
        # Infer tier from rules/default to preserve intent across rotated agents.
        for rule in config.agents.auto_rules:
            patterns = [p.strip() for p in rule.pattern.split("|")]
            for pattern in patterns:
                regex = "^" + pattern.replace("*", ".*") + "$"
                if re.match(regex, task_id):
                    tier = rule.model
                    break
            if tier:
                break
        if not tier:
            tier = config.agents.default_model_tier

    provider_prefix = {
        "claude": ("claude",),
        "gemini": ("gemini",),
        "codex": ("gpt-", "o1", "o3", "o4", "codex"),
    }

    # Keep explicit/custom model IDs when they already match provider.
    lower = (resolved or "").lower()
    expected = provider_prefix.get(agent_name, tuple())
    if expected and any(lower.startswith(prefix) for prefix in expected):
        return resolved

    # If model is incompatible, fall back to per-agent tier mapping.
    by_agent = config.agents.agent_models.get(agent_name)
    if by_agent:
        tier_map = {"high": by_agent.high, "medium": by_agent.medium, "low": by_agent.low}
        return tier_map.get(tier or "medium", by_agent.medium)

    if agent_name == "claude":
        return resolved

    # Safe defaults when no per-agent config is provided.
    fallback_defaults = {
        "codex": {
            "high": "gpt-5.4",
            "medium": "gpt-5.4-mini",
            "low": "gpt-5.4-mini",
        },
        "gemini": {
            "high": "gemini-2.5-pro",
            "medium": "gemini-2.5-flash",
            "low": "gemini-2.5-flash-lite",
        },
    }
    if agent_name in fallback_defaults:
        return fallback_defaults[agent_name].get(tier or "medium", fallback_defaults[agent_name]["medium"])

    return resolved
