# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

This is **not** a source code repository. It is a **task orchestration workspace** for an autonomous Claude Code agent that builds the [Vouchify](~/projects/vouchify-mono) SaaS project. The actual application code lives at `~/projects/vouchify-mono` — **all git operations and code modifications target that directory, not this workspace**.

This workspace contains:
- **Task queue and definitions**: `.agent/queue.md` (dependency graph) + `.agent/tasks/*.md` (individual tasks)
- **Shell-based orchestrator**: `.agent/run.sh`, `.agent/run-queue.sh`, `.agent/status.sh` (legacy system, currently active)
- **Python-based orchestrator** (newer): `orchestrator/` directory with agent-runner CLI (alternative system for future use)

## Two Orchestration Systems

### 1. Shell-Based (Current)

Simple, transparent, readable scripts:
- `.agent/run.sh` — runs a single task with automatic rate-limit retry (30 min backoff, max 48 retries)
- `.agent/run-queue.sh` — loop that picks the next eligible task, runs it, evaluates completion via checkbox inspection
- `.agent/status.sh` — dashboard showing queue state and last result
- Lock file (`/tmp/vouchify-queue.lock`) prevents concurrent runs
- Notifications via ntfy.sh (if `NOTIFY_URL` set in `~/.bashrc`)

**Use this system when:**
- Running on a VPS with simple automation needs
- Tasks are Polish-language markdown files
- You want full visibility into orchestration logic

### 2. Python-Based (orchestrator/) — **Active on Vouchify**

Sophisticated multi-agent scheduler with agent rotation, hooks, and state tracking:
- CLI: `agent-runner init|run|daemon|add|status|retry|cancel|new-task`
- Supports multiple agents (Claude, Gemini, Codex, Aider) with automatic rotation on rate limits
- Pre/post-task hooks (graphify context, lint, update docs, rebuild)
- Per-task state tracking (attempts, model used, token usage)
- Built-in retry logic; `FileNotFoundError` for missing CLIs triggers agent rotation (treats as `LIMIT_HIT`) — the task is re-queued and the next available agent is tried instead of failing the task

**Git flow per task:**
```
develop → agent/NNN-task-name (feature branch)
           ├── agent commits here
           ├── post-task hook commits (lint/format)
           ├── pushed to remote         ← visible on GitHub before merge
           └── merged --no-ff → develop → pushed to remote
```

**Running the daemon (Windows PowerShell):**
```powershell
agent-runner daemon --repo C:\Dev\vouchify-monorepo
# or background:
Start-Process agent-runner -ArgumentList "daemon","--repo","C:\Dev\vouchify-monorepo" -NoNewWindow
```

**Monitoring:**
```powershell
# Queue status + rotation state
agent-runner status --repo C:\Dev\vouchify-monorepo

# Live agent output while a task is running (PowerShell)
Get-Content C:\Dev\vouchify-monorepo\.agent\logs\task-007.log -Wait

# Or in bash/Git Bash
tail -f /c/Dev/vouchify-monorepo/.agent/logs/task-007.log
```

See `orchestrator/README.md` for full documentation.

## Running the Agent (Shell-Based)

```bash
# Start queue processing (backgrounded, loops until all tasks done)
nohup .agent/run-queue.sh > .agent/agent.log 2>&1 &

# Run a single task
bash .agent/run.sh .agent/tasks/<task-name>.md

# Resume an interrupted task (continues from where it left off)
bash .agent/run.sh .agent/tasks/<task-name>.md continue

# Check queue status and last result
bash .agent/status.sh

# View live logs
tail -f .agent/agent.log
```

## Task Lifecycle

Task statuses: `pending` → `in_progress` → `completed` | `needs_continuation` | `failed`

- **Completion detection**: `run-queue.sh` scans the task file's `## _STATUS` section for unchecked `- [ ]` checkboxes. If any exist, the task becomes `needs_continuation` and is automatically resumed with `--continue`.
- **Dependencies**: Each queue row specifies dependencies (comma-separated task numbers). A task only starts when all its dependencies are `completed`.
- **Rate-limit handling**: If "You've hit your limit" is detected, `run.sh` waits 30 minutes (configurable: `RETRY_WAIT`), then retries. After 48 retries, the task fails.
- **Notifications**: If `NOTIFY_URL` is set in `~/.bashrc`, status updates are posted (useful for ntfy.sh push notifications).

## Task File Format

```markdown
## ZADANIE
Description of what to do (in Polish)

## PLIKI DO PRZECZYTANIA
Which files to read before starting

## CO ZROBIĆ
Numbered steps to complete

## PO WYKONANIU
Git commands and docker rebuild steps

## DEFINICJA UKOŃCZENIA
- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2

## _STATUS
Auto-managed by run-queue.sh:
- stan: pending | in_progress | completed | needs_continuation | failed
- timestamp: auto-updated
- notatka: notes about the task state
```

The `## _STATUS` section is auto-populated by the orchestrator — do not edit it manually.

## Target Project: Vouchify

The agent builds a multi-tenant voucher/gift-card SaaS platform at `~/projects/vouchify-mono`:

**Backend** (.NET 10 Minimal API modulith at `backend/`):
- Modules: Identity, Tenants, Catalog, Orders, Vouchers, Notifications
- Pattern: CQRS with EF Core + PostgreSQL
- Infrastructure: Redis, Hangfire (job scheduling), Stripe Connect, Resend email, RazorLight templates

**Frontend** (Angular 21 at `frontend/`):
- Admin panel, public storefront, onboarding flows
- Tenant-aware routing

**Dev Environment** (`docker-compose.dev.yml`):
- api (port 5200) — backend
- worker (Hangfire job runner)
- frontend (port 4200) — development server
- db (PostgreSQL 16)
- redis (port 7)
- seq (port 8081) — structured logging
- nginx-proxy (external network `dev_internal`)

**Dev URLs**:
- Frontend: `https://dev.vouchify.mtlabs.pl`
- API: `https://api.dev.vouchify.mtlabs.pl`

**VPS**: Shared with Plannify project. **Never** modify `nginx-proxy` or `plannify-*` containers — they are shared infrastructure.

## Important Conventions

- **Language**: Task files are written in Polish (`ZADANIE`, `CO ZROBIĆ`, etc.)
- **Working directory**: All `git` and code modifications target `~/projects/vouchify-mono`, not this workspace
- **Backend rebuild**: After completing backend tasks, run:
  ```bash
  docker compose -f docker-compose.dev.yml up -d --build api worker
  ```
- **Network setup**: The `dev_internal` docker network connects containers to the nginx-proxy reverse proxy. It's declared as `external` — don't recreate it
- **Log location**: `.agent/agent.log` contains all task runs. Use `tail -f` to watch live progress

## Debugging and Troubleshooting

### Python Runner (agent-runner)

**Check queue and task state:**
```powershell
agent-runner status --repo C:\Dev\vouchify-monorepo
```

**Observe live agent output (while task is running):**
```powershell
# Replace 007 with the task ID shown in `agent-runner status`
Get-Content C:\Dev\vouchify-monorepo\.agent\logs\task-007.log -Wait
```

**Task stuck in `review_required`:**
- Look at `.agent/state/<id>.json` for `last_result` and `error_message`
- Fix the issue, then re-queue: `agent-runner retry <id> --repo C:\Dev\vouchify-monorepo`

**Merge conflict → `review_required`:**
- Feature branch was pushed to remote — resolve the conflict manually on that branch
- Then: `agent-runner retry <id>`

**Agent CLI not found:**
- The missing agent is marked as rate-limited and rotation kicks in automatically — the next agent in the rotation order is tried
- If ALL agents are missing/limited, tasks are skipped temporarily until a cooldown expires
- After installing the missing CLI, the cooldown (~30 min) will expire and the agent will be retried automatically

**queue.md gets out of sync / Windows CRLF issues:**
- The runner writes `queue.md` with LF endings; if you see parse errors, check for mixed CRLF
- `git config core.autocrlf false` in the repo prevents git from converting

**Daemon already running:**
- Delete stale lock: `.agent/locks/scheduler.lock`

### Shell Runner (legacy)

**Task is stuck or not progressing:**
1. Check `.agent/agent.log` for error messages
2. View the task file's `## _STATUS` section — look for `needs_continuation` status
3. Manually resume: `bash .agent/run.sh .agent/tasks/<task-name>.md continue`

**Queue not advancing:**
- Check `.agent/status.sh` output for blocked dependencies
- Verify lock file: `ls -l /tmp/vouchify-queue.lock` — if stale, remove it: `rm -f /tmp/vouchify-queue.lock`

**Container issues (docker-compose):**
- Verify containers are running: `docker ps | grep vouchify`
- Check logs: `docker compose -f docker-compose.dev.yml logs api`
- Rebuild if needed: `docker compose -f docker-compose.dev.yml up -d --build`
