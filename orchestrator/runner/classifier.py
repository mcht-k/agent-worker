"""Smart model tier classifier — uses a cheap agent to analyze task complexity."""

import logging
from pathlib import Path
from typing import Optional

from .models import QueueEntry
from .config import Config, resolve_model
from .scheduler import get_agent

log = logging.getLogger(__name__)

CLASSIFY_PROMPT = """You are a senior software architect. Your task is to classify the complexity of a software development task into one of three tiers: low, medium, or high.

### Task Content
{task_content}

### Context
{project_context}

### Classification Criteria:
- **low**: Documentation updates, configuration changes, simple text/CSS edits, basic entity creation with no logic, or minor bug fixes in a single file.
- **medium**: Typical feature implementation, bug fixes involving multiple files, refactoring of non-critical components, or adding unit tests.
- **high**: Critical architectural changes, complex security-related fixes (auth, crypto), database migrations for core entities, complex multi-step refactoring, or third-party integrations (e.g., Stripe, OAuth).

Analyze the task carefully. Consider the number of files likely affected and the technical risk.

Respond ONLY with one of the following words: low, medium, high.
"""

def classify_task_tier(
    repo_path: Path,
    agent_dir: Path,
    config: Config,
    task_id: str,
    task_file: Path,
) -> str:
    """Use a fast/cheap agent to classify the task into a model tier."""
    st_config = config.agents.smart_tiering
    if not st_config.enabled:
        return config.agents.default_model_tier

    agent_name = st_config.classifier_agent
    model_tier = st_config.classifier_model
    
    try:
        agent = get_agent(agent_name)
    except Exception as e:
        log.warning("Could not load classifier agent %s: %s", agent_name, e)
        return config.agents.default_model_tier

    # Resolve model ID for classification
    model_id = resolve_model(config, "CLASSIFY", model_tier)
    
    # Read task content
    if not task_file.exists():
        return config.agents.default_model_tier
    
    from .task_parser import parse_task_file
    _, task_body = parse_task_file(task_file)
    
    # Read project context
    project_md = agent_dir / "PROJECT.md"
    project_context = project_md.read_text(encoding="utf-8") if project_md.exists() else ""
    
    prompt = CLASSIFY_PROMPT.format(
        task_content=task_body,
        project_context=project_context[:5000] # Limit context size for classification
    )
    
    # Use a temp file for the prompt
    temp_file = agent_dir / "state" / f"classify_{task_id}.md"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file.write_text(prompt, encoding="utf-8")
    
    log_file = agent_dir / "logs" / f"classify_{task_id}.log"
    transcript_file = agent_dir / "transcripts" / f"classify_{task_id}.txt"
    
    log.info("Classifying task %s complexity using %s (%s)...", task_id, agent_name, model_id)
    
    result = agent.run(
        task_file=temp_file,
        working_dir=repo_path,
        model=model_id,
        log_file=log_file,
        transcript_file=transcript_file,
        timeout=st_config.timeout
    )
    
    from .models import RunResult
    if result.result != RunResult.SUCCESS:
        log.warning("Task classification failed for %s: %s", task_id, result.error_message)
        return config.agents.default_model_tier
    
    tier = transcript_file.read_text(encoding="utf-8").strip().lower()
    
    # Validate result
    if tier in ("low", "medium", "high"):
        log.info("Task %s classified as: %s", task_id, tier)
        return tier
    
    # Cleanup if agent returned more than one word
    for word in ("high", "medium", "low"):
        if word in tier:
            log.info("Task %s classified as: %s (extracted from output)", task_id, word)
            return word
            
    log.warning("Agent returned invalid tier for %s: %s", task_id, tier)
    return config.agents.default_model_tier
