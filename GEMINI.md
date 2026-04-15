# Agent Runner (Orchestrator) - Project Overview

Universal AI task orchestrator for managing a queue of tasks across multiple AI agents (Claude, Gemini, Codex, Aider). It handles rate limits, automatic agent rotation, branching, merging, and lifecycle notifications.

## 🚀 Getting Started

### Installation (Development)

```bash
cd orchestrator
pip install -e .
```

This installs `agent-runner` as a global CLI command in your environment.

### Project Setup

1.  **Initialize a repo:** `agent-runner init /path/to/repo`
2.  **Configure API keys:** Copy `.agent/.env.example` to `.agent/.env` and add your keys.
3.  **Define Shared Knowledge:** Update `.agent/PROJECT.md` with project conventions and architecture.
4.  **Add Tasks:** Use `agent-runner new-task my-feature` and `agent-runner add tasks/my-feature.md`.
5.  **Run:** Execute `agent-runner run` (single cycle) or `agent-runner daemon` (loop).

## 🏗️ Architecture

The orchestrator operates on a **Research -> Strategy -> Execution** loop:

1.  **Read Queue:** Scans `.agent/queue.md` for runnable tasks (dependencies resolved).
- **Pick Agent**: Selects the preferred agent (or rotates to a fallback if rate-limited).
- **Smart Tiering**: If enabled, uses a cheap/fast LLM (e.g., Gemini Flash) to analyze the task content and assign the appropriate model tier (`low`, `medium`, `high`) based on complexity.
- **Build Context**: Prepends `PROJECT.md` and optional `graphify` context to the task.

4.  **Execute:** Runs the agent in an isolated feature branch (`agent/NNN-task-name`).
5.  **Validate:** Runs pre-configured build/test commands before merging.
6.  **Merge:** Performs a non-fast-forward merge into the target branch and pushes to remote.
7.  **Sync Docs:** Updates `PROJECT.md` and syncs it to agent-specific docs (`CLAUDE.md`, `GEMINI.md`).

### Key Components

- **`orchestrator/runner/cli.py`**: Entry point for all `agent-runner` commands.
- **`orchestrator/runner/scheduler.py`**: Core loop logic and dependency resolution.
- **`orchestrator/runner/agents/`**: Adapters for various AI agent CLIs.
- **`orchestrator/runner/hooks.py`**: Extensible lifecycle hooks (pre-task, post-task, post-merge, on-failure).
- **`.agent/`**: Directory containing queue, state, logs, and task definitions (in target repo).

## 🛠️ Development Conventions

- **Language**: Core logic is in Python 3.8+.
- **Task Definitions**: Markdown-based with optional YAML frontmatter for metadata (agent, model, etc.).
- **Branching**: Each task uses an isolated feature branch created from the base branch.
- **Shared Knowledge**: `PROJECT.md` is the single source of truth for all agents.
- **Error Handling**: Distinguishes between `LIMIT_HIT`, `TRANSIENT_ERROR` (retryable), and `HARD_ERROR`.

### Commands Reference

| Command | Description |
| :--- | :--- |
| `agent-runner init [path]` | Initialize `.agent/` directory in a repository. |
| `agent-runner run` | Run one cycle of the scheduler. |
| `agent-runner daemon` | Run the scheduler loop continuously. |
| `agent-runner status` | Show the current queue status and agent rotation state. |
| `agent-runner add [file]` | Add a task file to the queue. |
| `agent-runner new-task [name]`| Create a new task file from a template. |
| `agent-runner generate-task [desc]` | AI-generated task from description + interactive add. |
| `agent-runner retry [id]` | Re-queue a failed task for execution. |

## 🧪 Testing

- **TODO**: Implement a formal test suite (e.g., using `pytest`) to verify scheduler logic and agent adapters.

## 📝 Important Notes

- **Git Integrity**: Always ensure the repo is clean before running the scheduler.
- **API Limits**: The system is designed to gracefully handle and rotate agents upon hitting rate limits.
- **Context Management**: Use the `graphify` hook to manage large context windows for complex tasks.
