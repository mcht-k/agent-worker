# How to Write Tasks for Agent Runner

This guide is both human documentation and a prompt you can hand to an AI to generate tasks.

---

## Task file format

Every task is a markdown file in `.agent/tasks/` with an optional YAML frontmatter header.

```markdown
---
id: add-user-profile
agent: claude
model: auto
baseBranch: main
targetBranch: develop
dependsOn:
  - setup-db
priority: normal
allowParallel: false
timeout: 3600
---

## Task

<one sentence: what to build and why>

## Context

<brief architectural context the agent needs to understand before starting>

## Files to Read

<explicit list of files/directories the agent should read first>

## Steps

<numbered, concrete steps>

## Post-Execution

<git and infra commands to run after the task>

## Acceptance Criteria

<checkboxes — the agent marks these as it completes each one>
```

---

## Frontmatter fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `id` | yes | — | Unique slug, used as branch suffix and state filename. Use kebab-case: `add-user-profile`, `fix-cors-headers`. |
| `agent` | no | from config | `claude` or `codex`. |
| `model` | no | `auto` | Model tier: `high` (opus), `medium` (sonnet), `low` (haiku), `auto` (config rules decide), or an explicit model ID. |
| `baseBranch` | no | from config | Branch to fork from. |
| `targetBranch` | no | from config | Branch to merge into after completion. |
| `dependsOn` | no | `[]` | List of task IDs that must complete before this one starts. |
| `priority` | no | `normal` | For future use. `normal` or `high`. |
| `allowParallel` | no | `false` | If true, this task can run concurrently with others (requires worktrees). |
| `timeout` | no | from config | Max seconds for agent execution. |

---

## How to choose the model tier

| Tier | When to use | Examples |
|------|-------------|---------|
| `high` (opus) | Architecture decisions, complex integrations, security reviews, multi-module refactors | Stripe Connect flow, multi-tenant middleware, security audit |
| `medium` (sonnet) | Typical features, bug fixes, CRUD endpoints, tests | Add API endpoints, write unit tests, fix validation |
| `low` (haiku) | Docs, config changes, simple updates, formatting | Update README, change env vars, reorder fields |

If unsure, use `auto` — the config's `auto_rules` patterns will assign the right tier based on the task ID.

---

## Writing each section

### ## Task

One sentence. State **what** and **why**, not how.

Good:
```
Implement Stripe webhook handler for payment confirmation to complete the purchase flow.
```

Bad:
```
We need webhooks. Create a file and add some code.
```

### ## Context

Give the agent architectural knowledge it needs but can't easily discover by reading a single file. This is where you describe how this task fits into the bigger picture.

Good:
```
The system uses a modulith architecture with CQRS. Orders module publishes
domain events (OrderPaid) that the Vouchers module subscribes to. The Stripe
webhook must verify signatures using the secret from config, then dispatch
to MediatR handlers. All webhook endpoints are public (no JWT) but require
Stripe signature verification.
```

Skip this section if the task is self-contained (e.g., "update the README").

### ## Files to Read

Explicit paths. The agent reads these **before** writing any code. This is critical for context — without it the agent guesses at project structure.

```markdown
- backend/Modules/Vouchify.Modules.Orders/
- backend/Modules/Vouchify.Modules.Tenants/Entities/Tenant.cs
- backend/Vouchify.Infrastructure/AppDbContext.cs
```

Rules:
- List directories for broad context, specific files for targeted changes
- Include related modules the agent needs to understand (not just the one it's changing)
- Include config files if relevant (e.g., `docker-compose.dev.yml`, `appsettings.json`)

### ## Steps

Numbered, concrete, imperative. Each step = one unit of work the agent can verify.

Good:
```markdown
1. Create entity `Voucher` with fields: Id, TenantId, OrderId, Code (string, unique),
   Status (enum: Active, Used, Expired), ValidUntil (DateOnly), UsedAt (nullable), CreatedAt
2. Register in AppDbContext with Global Query Filter on TenantId
3. Add migration: `AddVoucherEntity`
4. Create handler for `OrderPaid` event that generates a unique 12-char alphanumeric code
5. Create endpoint `POST /api/vouchers/verify` (requires JWT, role Owner or Employee)
6. Add error constants `VoucherErrors` (VoucherNotFound, AlreadyUsed, Expired)
```

Bad:
```markdown
1. Create the voucher stuff
2. Make it work
3. Add some endpoints
```

Rules:
- **Be specific about field names, types, and constraints** — the agent shouldn't guess
- **Name the entities, commands, endpoints, and error codes** — decisions already made
- **Include business rules inline** — e.g., "only Active vouchers can be redeemed"
- **Don't over-prescribe implementation** — say "create a handler for OrderPaid" not "create a file called OrderPaidHandler.cs in folder X and inherit from INotificationHandler"

### ## Post-Execution

Git commands and infrastructure rebuilds. The agent runs these after all steps are done.

```markdown
cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Vouchers/ backend/Vouchify.Infrastructure/
git commit -m "feat(vouchers): voucher entity, code generation, verify endpoint"
git push
docker compose -f docker-compose.dev.yml up -d --build api worker
```

**Note**: When using `agent-runner`, omit all git commands here — the runner handles the full git flow automatically:
1. Creates `agent/<id>-<slug>` branch from base
2. Commits agent changes after the run
3. Commits any lint/format changes from post-task hooks
4. Pushes the feature branch to remote
5. Merges `--no-ff` into target branch and pushes

Post-Execution in this context is **only for infrastructure commands** (docker rebuild, cache clear, etc.).

### ## Acceptance Criteria

Checkboxes. Each one is a **verifiable** statement about the end state.

Good:
```markdown
- [ ] `POST /api/vouchers/verify` returns voucher details for valid code
- [ ] `POST /api/vouchers/verify` returns 404 for invalid code
- [ ] Unique constraint on Voucher.Code in database
- [ ] Hangfire job `ExpireVouchersJob` visible in dashboard
```

Bad:
```markdown
- [ ] Code works
- [ ] Tests pass
- [ ] Everything is good
```

Rules:
- Each criterion should be independently testable
- Include error cases, not just happy path
- 3-6 criteria is ideal — too many splits focus, too few is vague

---

## Task sizing guidelines

### Right size (one task)
- One module or feature area
- 1-10 files created/modified
- Clear single responsibility
- Can be verified in isolation

### Too large (split into multiple tasks)
- Spans multiple unrelated modules
- Requires building on work that doesn't exist yet
- More than ~15 steps
- Has distinct phases (entities → endpoints → frontend)

### Too small (merge with another task)
- Single config change
- Renaming one variable
- Adding one field to one file

### Splitting example

Instead of one task "Build the voucher system":

```
001 vouchers-be-entities    → entity, migration, owned types
002 vouchers-be-endpoints   → CRUD commands, REST endpoints      (depends: 001)
003 vouchers-be-pdf         → PDF generation with QuestPDF        (depends: 001)
004 vouchers-fe-panel       → admin panel UI                      (depends: 002)
005 vouchers-fe-public      → public verification page            (depends: 002)
```

Each task has a clear scope and can be verified independently.

---

## Dependency patterns

### Linear chain
```
setup → entities → endpoints → frontend
```

### Fan-out (parallel after base)
```
         ┌→ orders-fe-panel
entities →  orders-fe-public
         └→ orders-be-stripe
```

### Fan-in (multiple deps)
```
catalog-endpoints ──┐
                    ├→ orders-fe-public
orders-be-stripe  ──┘
```

Set dependencies using the `dependsOn` frontmatter field or `--depends-on` flag when adding to queue.

---

## Naming conventions

Task ID (and filename) should follow: `<scope>-<area>-<what>`

Examples:
```
tenants-be-entities        # backend entity for tenants module
tenants-fe-onboarding      # frontend onboarding flow
catalog-be-endpoints       # backend REST endpoints
orders-be-stripe           # stripe integration for orders
vouchers-fe-verification   # frontend verification page
hardening-rate-limiting    # cross-cutting hardening
fix-cors-headers           # bug fix
add-tests                  # testing
write-documentation        # docs
```

This pattern helps auto_rules match the right model tier.

---

## Prompt for AI task generation

Use this prompt to have an AI break down a project plan into tasks:

```
I need you to break down this work into tasks for an AI agent orchestrator.

Each task must be a markdown file following this structure:
- YAML frontmatter with: id, agent, model, baseBranch, targetBranch, dependsOn
- ## Task (one sentence)
- ## Context (architectural background)
- ## Files to Read (explicit paths)
- ## Steps (numbered, concrete, with field names and types)
- ## Post-Execution (infra commands only, git is handled by runner)
- ## Acceptance Criteria (verifiable checkboxes, 3-6 items)

Rules:
- Each task = one module or feature area, 1-10 files
- Name tasks as: <scope>-<area>-<what> in kebab-case
- Specify entity field names, types, enums, and constraints explicitly
- Include business rules in Steps, not just "implement X"
- Set model tier: high for architecture/security, medium for features, low for docs
- Set dependencies between tasks correctly (entity tasks before endpoint tasks, etc.)
- Steps should be imperative and concrete, not vague
- Acceptance criteria should be independently verifiable

Here is the work to break down:
<describe the project/feature>

Here is the current project structure:
<paste tree or relevant paths>
```

---

## Common mistakes

| Mistake | Why it fails | Fix |
|---------|-------------|-----|
| No Files to Read section | Agent guesses at structure, makes wrong assumptions | Always list relevant files and directories |
| Vague steps ("add the feature") | Agent interprets differently each attempt, non-deterministic | Name every entity, field, endpoint, enum value |
| Too many responsibilities in one task | Agent loses context, forgets earlier steps | Split by module boundary or frontend/backend |
| No error cases in acceptance criteria | Agent only builds happy path | Add criteria for validation errors, edge cases |
| Hardcoded paths in Post-Execution that don't exist | Agent fails on commit step | Verify paths match actual project structure |
| Missing dependencies | Task tries to import entities that don't exist yet | Map the dependency graph before writing tasks |
| Using `high` model for documentation | Wastes tokens, same quality from `low` | Match model tier to actual complexity |
