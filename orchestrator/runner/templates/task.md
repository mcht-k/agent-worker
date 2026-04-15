---
id: {{ID}}
agent: claude
model: auto
baseBranch: main
targetBranch: main
dependsOn: []
priority: normal
allowParallel: false
timeout: 3600
---

## Task

One sentence: what to build and why.

## Context

Architectural background the agent needs. How this fits into the bigger picture.
Skip this section if the task is self-contained.

## Files to Read

- path/to/module/
- path/to/specific/file.ext

## Steps

1. Create entity `X` with fields: Id, Name (string), Status (enum: Draft, Active), CreatedAt
2. Register in DbContext
3. Add migration: `AddXEntity`
4. Create endpoint `GET /api/x` — requires authentication
5. Add error constants `XErrors` (NotFound, InvalidStatus)

## Post-Execution

```bash
# Infrastructure commands (git is handled by runner)
docker compose -f docker-compose.dev.yml up -d --build api
```

## Acceptance Criteria

- [ ] Entity persists to database
- [ ] GET endpoint returns expected data
- [ ] Validation rejects invalid input with correct error code
