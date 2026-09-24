# Build Observatory Refresh Prompt

Use this prompt for the recurring build-status analysis.

## Scope

Repository: `dominik-scherrer/public-ai-challenge`

**Hard scope rule:** inspect and modify only `pipeline/`. You may read repository-wide pull-request/commit metadata when needed to understand dependencies, but never edit files outside `pipeline/`.

## Task

Act as the information orchestrator for the ingestion-pipeline build.

1. Inspect the current state of `pipeline/`.
2. Inspect open pull requests and recent commits that affect `pipeline/`.
3. Compare the current state with:
   - `pipeline/BUILD_PLAN.md`
   - `pipeline/ARCHITECTURE.md`
   - `pipeline/SEMANTIC_COMPILER.md` when present
   - `pipeline/EVALS.md`
4. Distinguish clearly between:
   - implemented and evidenced
   - designed/documented
   - in progress
   - blocked
   - deferred
5. Update:
   - `pipeline/observatory/state.json`
   - `pipeline/observatory/history.jsonl`
   - the embedded state in `pipeline/observatory/index.html`
6. Preserve history. Add a history event only when something materially changed.
7. Do not manufacture progress. If a module exists only in documentation, mark it `designed`, not `implemented`.
8. Surface:
   - where we are
   - what changed
   - what is next
   - open questions
   - blockers
   - status of each module
   - active PRs relevant to pipeline
9. Keep the dashboard readable to a teammate who has not followed the whole conversation.

## Status vocabulary

Use only:

- `not_started`
- `designed`
- `in_progress`
- `implemented`
- `blocked`
- `deferred`

## Update policy

Prefer one small status commit only when the state materially changed. Avoid churn caused solely by timestamps.

Commit message:

`chore(pipeline): refresh build observatory`
