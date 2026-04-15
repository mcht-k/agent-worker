# Agent Runner — How It Works

## What it is

A scheduler that reads a queue of tasks, assigns them to AI agents, and merges the results into a codebase. It runs unattended on a VPS until the queue is empty.

## The loop

The system repeats one cycle:

```
read queue → pick a task → pick an agent → run → evaluate → act on result
```

Then sleeps and repeats. Each cycle makes a series of decisions.

## Decisions

### 1. What to work on

The queue is a markdown table with dependencies. The scheduler scans it and asks:

- Is any task already in progress or waiting for resume? → **resume it first**
- Otherwise, which queued tasks have all dependencies completed? → **pick the first one**
- Are all tasks in a terminal state? → **stop**

### 2. Who does the work

Each task has a preferred agent (Claude, Gemini, Codex, Aider). The scheduler checks:

- Is the preferred agent rate-limited right now? → **rotate to the next available agent**
- Are all agents rate-limited? → **skip this cycle, wait**
- Is the agent available? → **use it**

### 3. What the agent knows

Before the agent sees the task, the system builds its input by stacking three layers:

```
PROJECT.md        — what this project is, how it works, what conventions to follow
context/<id>.md   — task-specific context built by a pre-task hook (optional)
tasks/<id>.md     — the actual instructions
```

The agent receives this as a single stream. It doesn't know the layers exist.

### 4. What model to use

Each task declares a model tier (high, medium, low, auto). The scheduler resolves it:

- Explicit tier → map to configured model ID
- Auto → match task name against pattern rules → fall back to default tier
- Task metadata override → takes precedence over queue

### 5. Where the work happens

Each task gets its own git branch (`agent/<id>-<slug>`). The scheduler:

- Creates the branch from the base (e.g. `develop`)
- Points the agent's working directory at it
- Commits the agent's changes to the feature branch after the run
- Commits any post-task hook changes (lint/format) in a second commit
- Optionally uses a git worktree for parallel isolation

### 6. What happened

After the agent finishes, the scheduler classifies the result:

| Result | Decision |
|--------|----------|
| Success | commit (agent) → post-task hooks → commit (hooks) → validate → push feature branch → merge → push target → post-merge hooks → mark completed |
| Rate limit | Mark agent as limited → re-queue task (rotation) or wait (no rotation) |
| Transient error | Re-queue for retry. If same error repeats twice → escalate to review |
| Hard error | Mark failed immediately |
| Not installed | Agent CLI not found → HARD_ERROR with install instructions |
| Timeout | Treat as transient |
| Max attempts reached | Mark failed, stop retrying |

### 7. Whether the result is good enough

Before merging, the scheduler optionally runs validation commands (build, test). If validation fails, the task is not merged — it's marked for human review.

### 8. What to update after success

Post-merge hooks fire in order:

- **update_claude_md** — diffs the merged changes, decides if the shared knowledge file needs updating. If yes, runs a cheap agent to rewrite it.
- **sync_agent_docs** — copies the shared knowledge to each agent's native doc file (CLAUDE.md, AGENTS.md, GEMINI.md) so the knowledge persists even outside the orchestrator.
- **custom hooks** — rebuild containers, clear caches, notify external systems.

### 9. What to do when things fail

On failure, the scheduler runs on_failure hooks (cleanup, alerts) and records the error. The same error twice in a row triggers escalation to human review — the system doesn't burn tokens on a loop.

## State

The system keeps two layers of state:

- **queue.md** — the plan. What to do, in what order, with what dependencies. Declarative. Committed to the repo.
- **state/*.json** — the runtime. Attempt count, last result, timestamps, which agent ran, token usage. Ephemeral. Gitignored.

Queue is what should happen. State is what did happen.

## Authentication

API keys live in `.agent/.env` (gitignored). Loaded once, injected into every subprocess. Each agent CLI reads the keys it needs and ignores the rest.

## Knowledge sharing

All agents read from the same knowledge base (`PROJECT.md`). When one agent changes the codebase and the knowledge becomes stale, a hook updates it. The next agent — regardless of which one — starts with current knowledge.
