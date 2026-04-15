"""Task generator — creates full task files from short descriptions using AI agents."""

import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from .models import QueueEntry, TaskStatus
from .queue_manager import load_queue
from .scheduler import get_agent
from .config import resolve_model

log = logging.getLogger(__name__)

GENERATE_PROMPT = """You are a senior software architect. Your task is to generate a detailed, actionable task file (Markdown) based on a short description, the current project state (PROJECT.md), and a template.

### Input Description
{description}

### Template
{template}

### Instructions
1. Expand the short description into a full task file using the provided template.
2. The task should be written in Polish if the project uses Polish for tasks (check PROJECT.md or existing tasks), otherwise English.
3. Be specific and technical in the "Steps" section.
4. Include relevant "Files to Read".
5. Set realistic "Acceptance Criteria".
6. In the frontmatter (YAML):
   - Keep `id: {{ID}}` (placeholder).
   - Set `agent: {agent}`.
   - Set `model: {model_tier}`.
   - Set `baseBranch` and `targetBranch` to reasonable defaults (e.g., main or develop).
   - `dependsOn`: {suggested_deps} (if applicable).

Output ONLY the markdown content, no preamble or postamble.
"""

def suggest_dependencies(queue_path: Path) -> List[str]:
    """Suggest dependencies based on currently active or pending tasks."""
    if not queue_path.exists():
        return []
    
    entries = load_queue(queue_path)
    # Suggest tasks that are in_progress or waiting (active)
    active = [e.id for e in entries if e.status in (TaskStatus.IN_PROGRESS, TaskStatus.WAITING_FOR_LIMIT)]
    # Or just the last few tasks in the queue
    pending = [e.id for e in entries if e.status == TaskStatus.QUEUED]
    
    # Heuristic: suggest the last non-completed task as a dependency
    last_task = None
    for e in reversed(entries):
        if e.status != TaskStatus.COMPLETED:
            last_task = e.id
            break
            
    suggestions = []
    if last_task:
        suggestions.append(last_task)
    
    return suggestions

def generate_task_markdown(
    repo_path: Path,
    description: str,
    agent_name: str,
    model_tier: str,
    template_path: Path,
) -> str:
    """Use an agent to generate the task markdown."""
    agent = get_agent(agent_name)
    template = template_path.read_text(encoding="utf-8")
    
    agent_dir = repo_path / ".agent"
    queue_path = agent_dir / "queue.md"
    suggested_deps = suggest_dependencies(queue_path)
    
    # Build the prompt
    prompt = GENERATE_PROMPT.format(
        description=description,
        template=template,
        agent=agent_name,
        model_tier=model_tier,
        suggested_deps=suggested_deps
    )
    
    # We need a temporary "task file" to run the agent
    temp_task = agent_dir / "state" / "temp_generate_task.md"
    temp_task.parent.mkdir(parents=True, exist_ok=True)
    temp_task.write_text(prompt, encoding="utf-8")
    
    log_file = agent_dir / "logs" / "generate_task.log"
    transcript_file = agent_dir / "transcripts" / "generate_task.txt"
    
    # Resolve model ID
    from .config import load_config
    config = load_config(agent_dir / "config.yml")
    model_id = resolve_model(config, "GEN", model_tier)
    
    print(f"Generating task using {agent_name} ({model_id})...")
    
    # Run the agent. We use the agent's run method directly.
    # Note: This requires the agent CLI to be installed and configured.
    result = agent.run(
        task_file=temp_task,
        working_dir=repo_path,
        model=model_id,
        log_file=log_file,
        transcript_file=transcript_file,
        timeout=300
    )
    
    if result.result.value != "completed" and result.result.value != "success":
        # Check if result.result is an Enum (models.RunResult)
        from .models import RunResult
        if result.result != RunResult.SUCCESS:
            print(f"Error generating task: {result.error_message}")
            if result.output_file and Path(result.output_file).exists():
                print("Agent output:")
                print(Path(result.output_file).read_text(encoding="utf-8"))
            sys.exit(1)
            
    # The transcript file contains the agent's output (the markdown)
    content = transcript_file.read_text(encoding="utf-8").strip()
    
    # Clean up markdown code blocks if the agent wrapped the output
    if content.startswith("```markdown"):
        content = content[len("```markdown"):].strip()
    elif content.startswith("```"):
        content = content[len("```"):].strip()
    if content.endswith("```"):
        content = content[:-len("```")].strip()
        
    return content
