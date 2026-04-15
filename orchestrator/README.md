# Agent Runner

Universal AI task orchestrator. Manages a queue of tasks, runs AI agents (Claude, Gemini, Codex, Aider), handles rate limits with automatic agent rotation, branches, merges, and notifications — all driven by markdown files in your repo.

## Installation

```bash
# From local checkout
cd orchestrator
pip install .

# Or directly from git
pip install git+https://github.com/<user>/<repo>.git#subdirectory=orchestrator

# For development (editable)
pip install -e .
```

This installs `agent-runner` as a global CLI command. Dependencies (PyYAML) are pulled automatically.

**Alternative** (no pip): `bash setup.sh` + optional `bash setup.sh --link ~/.local/bin`.

Requirements: Python 3.8+, git, curl (for ntfy notifications).

## Quick Start

### 1. Initialize a repo

```bash
agent-runner init /path/to/your-repo
```

This creates:

```
your-repo/
├── .gitignore              # updated with .agent/ runtime entries
└── .agent/
    ├── config.yml          # runner configuration
    ├── queue.md            # task queue (declarative)
    ├── PROJECT.md          # shared knowledge for all agents
    ├── .env.example        # API key template
    ├── tasks/              # task definition files
    ├── state/              # runtime state JSON (gitignored)
    ├── logs/               # execution logs (gitignored)
    ├── transcripts/        # agent output (gitignored)
    ├── context/            # graphify hook output (gitignored)
    ├── results/            # summaries (gitignored)
    └── locks/              # process locks (gitignored)
```

### 2. Set up API keys

```bash
cp .agent/.env.example .agent/.env
nano .agent/.env
```

```bash
# Fill in keys for the agents you'll use:
ANTHROPIC_API_KEY=sk-ant-...      # Claude (not needed for Max/Pro subscriptions)
OPENAI_API_KEY=sk-...             # Codex
GOOGLE_API_KEY=AIza...            # Gemini
DEEPSEEK_API_KEY=sk-...           # Aider + DeepSeek
```

`.agent/.env` is gitignored. Keys are loaded once and injected into every agent subprocess.
Claude Code on Max/Pro doesn't need an API key — auth lives in `~/.claude/`.

### 3. Edit config

```bash
nano .agent/config.yml
```

Key settings:
- `git.default_base_branch` / `git.default_target_branch` — branching strategy
- `agents.default` — primary agent (`claude`, `gemini`, `codex`, `aider`)
- `agents.models` — model IDs for each tier (high/medium/low)
- `agents.rotation` — auto-switch agents on rate limit
- `hooks` — lifecycle hooks (graphify, auto-update docs, rebuild)
- `notifications.ntfy_url` — push notifications

### 4. Fill in shared project knowledge

```bash
nano .agent/PROJECT.md
```

Describe your project's architecture, tech stack, conventions, and active decisions.
This file is automatically prepended to every agent run — all agents (Claude, Gemini, Codex, Aider) start with the same context.

### 5. Create a task

```bash
# Manual (empty template)
agent-runner new-task my-feature --repo /path/to/your-repo

# AI-generated from short description (interactive)
agent-runner generate-task "Add CORS middleware to the backend" --agent gemini
```

AI generation expanded short descriptions into full task files using your `PROJECT.md` context and templates. It will show you the result and ask for confirmation before adding it to the queue.

See **[`templates/TASK_GUIDE.md`](templates/TASK_GUIDE.md)** for the full guide on writing effective tasks.

### 6. Add task to queue

```bash
agent-runner add tasks/my-feature.md --repo /path/to/your-repo

# With options:
agent-runner add tasks/my-feature.md \
  --agent claude \
  --model high \
  --depends-on 001,002 \
  --target-branch develop
```

### 7. Run

```bash
# Single cycle (process one task)
agent-runner run

# Continuous daemon (loop until all tasks done)
agent-runner daemon

# Background daemon on VPS
nohup agent-runner daemon > .agent/logs/daemon.log 2>&1 &
```

### 8. Monitor

```bash
# Queue status + rotation state
agent-runner status

# Live agent output (while a task is running)
tail -f .agent/logs/task-007.log

# PowerShell equivalent
Get-Content .agent\logs\task-007.log -Wait
```

Shows queue, active tasks, and agent rotation status (which agents are available, which are rate-limited).

The log file receives output in real-time — every line the agent prints appears immediately, so you can watch it work as if you ran it manually.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CLI (cli.py)                      │
├─────────────────────────────────────────────────────┤
│                Scheduler (scheduler.py)              │
│  load queue → resolve deps → pick task → execute    │
├──────────┬──────────┬───────────┬───────────────────┤
│  Queue   │  State   │  Config   │   Notifications   │
│ (.md)    │ (.json)  │ (.yml)    │   (ntfy.sh)       │
├──────────┴──────────┴───────────┴───────────────────┤
│               Hooks (hooks.py)                      │
│  pre_task → post_task → post_merge → on_failure     │
│  Built-in: graphify, update_claude_md,              │
│            sync_agent_docs                          │
├─────────────────────────────────────────────────────┤
│         Agent Adapters + Rotation (agents/)         │
│    ┌────────┐ ┌────────┐ ┌────────┐ ┌───────┐     │
│    │ Claude │ │ Gemini │ │ Codex  │ │ Aider │     │
│    └────────┘ └────────┘ └────────┘ └───────┘     │
│         ↕ rotation on limit_hit ↕                   │
├─────────────────────────────────────────────────────┤
│          Env (.env) + Git Ops (git_ops.py)          │
│  .env loader → branch → worktree → merge → push    │
├─────────────────────────────────────────────────────┤
│            Validators (validators.py)               │
│  build check → test check → custom commands         │
└─────────────────────────────────────────────────────┘
```

## Agents

Four agents are supported out of the box:

| Agent | CLI | Type | Best for | Resume |
|-------|-----|------|----------|--------|
| **Claude Code** | `claude -p` | Autonomous agent | Complex tasks, debugging, shell access | `--continue` (native) |
| **Gemini CLI** | `gemini --sandbox` | Autonomous agent | Fallback, large context (1M), generous free tier | Re-run |
| **Codex CLI** | `codex --approval-mode full-auto` | Autonomous agent | OpenAI ecosystem, different rate limits | Re-run |
| **Aider** | `aider --yes-always` | Code editor | Simple edits, cheap (DeepSeek/Grok backend) | Re-run |

Claude, Gemini, and Codex are **full autonomous agents** (shell access, debugging, iteration).
Aider is a **code editor** — best for entity creation, refactoring, docs, but cannot run docker or debug runtime.

## Agent Rotation

When an agent hits a rate limit, the scheduler switches to the next available agent instead of waiting 30 minutes.

```yaml
agents:
  rotation:
    enabled: true
    strategy: on_limit
    order:
      - claude          # primary
      - gemini          # fallback 1
      - codex           # fallback 2
      - aider           # fallback 3 (code-only tasks)
```

Flow:
```
Task → Claude
         ↓ limit_hit (mark claude as limited)
         re-queue task
         ↓ next cycle
Task → Gemini (first available in rotation order)
         ↓ limit_hit
Task → Codex → Aider → ... → Claude (cooldown expired)
```

`agent-runner status` shows which agents are available and which are in cooldown:
```
Agent rotation: enabled
  claude     LIMITED (24m30s remaining)
  gemini     available
  codex      LIMITED (12m15s remaining)
  aider      available
```

## Shared Knowledge (PROJECT.md)

All agents share a single knowledge base: `.agent/PROJECT.md`.

```
                    .agent/PROJECT.md
                    (single source of truth)
                           │
              ┌────────────┼────────────┐
              ↓            ↓            ↓
         CLAUDE.md     AGENTS.md    GEMINI.md
         (auto-sync)   (auto-sync)  (auto-sync)
```

**How it works:**
1. Every agent run gets PROJECT.md prepended automatically (via `_build_input`)
2. The `update_claude_md` hook updates PROJECT.md after significant code changes
3. The `sync_agent_docs` hook copies PROJECT.md to CLAUDE.md, AGENTS.md, GEMINI.md
4. Each agent's native doc file stays in sync — even when invoked outside the orchestrator

**Input layers** (prepended in order):
```
1. PROJECT.md          → shared project knowledge
2. context/<id>.md     → per-task context from graphify hook
3. tasks/<id>.md       → task instructions
```

## Authentication

API keys are stored in `.agent/.env` (gitignored):

```bash
ANTHROPIC_API_KEY=sk-ant-...    # Claude API tier
OPENAI_API_KEY=sk-...           # Codex
GOOGLE_API_KEY=AIza...          # Gemini
DEEPSEEK_API_KEY=sk-...         # Aider + DeepSeek
```

The orchestrator loads `.env` once and injects all keys into every agent subprocess.
Each CLI ignores keys it doesn't need. Claude on Max/Pro needs no key at all.

## Model Tiers

Save tokens by matching model capability to task complexity:

```yaml
agents:
  models:
    high: claude-opus-4-6        # complex architecture, security
    medium: claude-sonnet-4-6    # typical features, bug fixes
    low: claude-haiku-4-5        # docs, formatting, config
  auto_rules:
    - pattern: "*-doc*|write-*|update-readme*|update-config*"
      model: low
    - pattern: "*-security*|*-architecture*|*-stripe*"
      model: high
```

Set per task (`model: high`) or let auto-rules decide (`model: auto`).

## Task Lifecycle

```
queued → in_progress → completed
                     → failed
                     → review_required
                     → waiting_for_limit_reset → (retry / rotate)
```

| Status | Description |
|--------|-------------|
| `queued` | Ready to run (or waiting for dependencies) |
| `in_progress` | Agent is currently executing |
| `waiting_for_limit_reset` | Rate limited, will auto-retry (or rotate if enabled) |
| `review_required` | Needs human attention (validation failed, merge conflict, repeated errors) |
| `completed` | Done and merged |
| `failed` | Max retries exceeded or hard error |
| `cancelled` | Manually cancelled |

## Branch Lifecycle

Each task runs on an isolated feature branch. After completion, the feature branch is pushed to remote and then merged into the target:

```
develop (base)
  └── agent/003-my-feature  (work branch, created from base)
        │ ← agent commits here
        │ ← post-task hooks commit here (lint/format)
        │ ← pushed to remote  (visible on GitHub/GitLab before merge)
        └── merge --no-ff → develop (target branch)
                              └── pushed to remote
```

`agent-runner status` shows the resolved model for every task — not just "auto":
```
Id     Task                           Status                   Agent    Model                  Att Target
------ ------------------------------ ------------------------ -------- ---------------------- --- ------------
006    001-users-be-employee-status   [+] completed            claude   claude-sonnet-4-6        1 develop
007    002-employees-fullstack-list   [>] in_progress          gemini   gemini-2.5-pro           1 develop
```

## Lifecycle Hooks

```
pre_task    → before agent runs (build context)
post_task   → after agent succeeds, before merge (lint, format)
post_merge  → after merge (update docs, rebuild)
on_failure  → when task fails (cleanup)
```

### Built-in hooks

| Hook | Phase | Description |
|------|-------|-------------|
| `graphify` | pre_task | Generates context briefing from knowledge graph, prepended to agent input |
| `update_claude_md` | post_merge | Updates PROJECT.md when significant code changes |
| `sync_agent_docs` | post_merge | Syncs PROJECT.md → CLAUDE.md, AGENTS.md, GEMINI.md |

### Execution flow

```
1.  pre_task hooks     (graphify — build context briefing)
2.  agent runs         (PROJECT.md + context + task)
3.  commit             (agent changes → feature branch)
4.  post_task hooks    (lint, format)
5.  commit             (hook changes → feature branch)
6.  validation         (build, test)
7.  push               (feature branch → remote)
8.  merge --no-ff      (feature branch → target, local)
9.  push               (target branch → remote)
10. post_merge hooks   (update_claude_md, sync_agent_docs, rebuild)
```

### Custom hooks

Any shell command. Receives env vars: `AGENT_TASK_ID`, `AGENT_PHASE`, `AGENT_WORK_BRANCH`, `AGENT_TARGET_BRANCH`, `AGENT_ERROR`.

```yaml
hooks:
  post_merge:
    - name: rebuild
      command: "docker compose -f docker-compose.dev.yml up -d --build api"
      required: false
```

## Retry Strategy

- **Rate limit** + rotation enabled: Switch to next agent immediately
- **Rate limit** + rotation disabled: Wait `limit_retry_wait_seconds` (default 30 min)
- **Transient errors** (network, 502/503): Re-queued for retry
- **Same error twice**: Escalated to `review_required`
- **Max attempts exceeded**: Marked `failed`

## CLI Reference

```
agent-runner init [path]          Initialize .agent/ in a repo
agent-runner run [--repo PATH]    Run one scheduler cycle
agent-runner daemon [--repo PATH] Run continuous scheduler loop
agent-runner status [--repo PATH] Show queue + rotation status
agent-runner add TASK_FILE        Add task to queue
agent-runner cancel TASK_ID       Cancel a task
agent-runner retry TASK_ID        Re-queue a failed task
agent-runner new-task NAME        Create task file from template
agent-runner generate-task DESC   Generate task from description (AI)
```

## File Reference

| File | Committed | Purpose |
|------|-----------|---------|
| `.agent/config.yml` | yes | Runner configuration |
| `.agent/queue.md` | yes | Task queue with dependencies |
| `.agent/PROJECT.md` | yes | Shared knowledge for all agents |
| `.agent/tasks/*.md` | yes | Task definitions |
| `.agent/.env.example` | yes | API key template |
| `.agent/.env` | **no** | API keys (gitignored) |
| `.agent/state/*.json` | no | Per-task runtime state |
| `.agent/logs/` | no | Execution logs |
| `.agent/transcripts/` | no | Agent output |
| `.agent/context/` | no | Graphify context briefings |
| `.agent/locks/` | no | Process locks |

## Migrating from the old system

If you have an existing `.agent/` with `run.sh` / `run-queue.sh`:

1. Run `agent-runner init --force` to add config and new directory structure
2. Your existing `tasks/*.md` files work as-is (legacy format without frontmatter is supported)
3. Copy your existing CLAUDE.md content into `.agent/PROJECT.md`
4. Add tasks to the new `queue.md` format using `agent-runner add`
5. Set up `.agent/.env` with your API keys
6. The old scripts can coexist — they don't conflict

## Extending

### Adding a new agent

Create `runner/agents/myagent.py`:

```python
from .base import BaseAgent, AgentRunResult
from ..models import RunResult

class MyAgent(BaseAgent):
    name = "myagent"

    def run(self, task_file, working_dir, model, log_file, transcript_file,
            timeout=3600, context_file=None):
        task_content = self._build_input(task_file, context_file)
        env = self.get_env(working_dir)
        # subprocess.run([...], env=env, input=task_content, ...)
        ...

    def resume(self, task_file, working_dir, model, log_file, transcript_file,
               timeout=3600, context_file=None):
        ...
```

Register in `runner/scheduler.py`:

```python
from .agents.myagent import MyAgent
AGENTS["myagent"] = MyAgent
```
