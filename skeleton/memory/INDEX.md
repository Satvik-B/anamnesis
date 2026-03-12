# Memory Index (Complete Catalog)

> **Cold index** — loaded on demand for task lookups and knowledge retrieval.
> For the always-loaded hot pointers, see `MEMORY.md` (auto-memory).
> For the boundary rule between the two indexes, see `.claude/rules/memory-rule.md`.

## Quick Facts
- GitHub: <org>/<repo> | Team: <your-team>
- Services: `src/`
- Memory root: `.claude/memory/`
- Auto-memory root: `~/.claude/projects/<project>/memory/` (managed by system prompt)
- Architecture doc: `friday/memory-architecture.md`

---

## Task Memories (runbooks — "how do I do X?")

| Task | File | Tags | Last Accessed |
|------|------|------|---------------|
| DB Schema Migration | tasks/db-schema-migration.md | db, migration, orm | YYYY-MM-DD |
| Deploy Service | tasks/deploy-service.md | deploy, dev-cluster | YYYY-MM-DD |
| Debug gRPC Errors | tasks/debug-grpc-errors.md | grpc, debug, timeout | YYYY-MM-DD |
| _Add your runbooks here_ | | | |

---

## Knowledge Base (facts, patterns, conventions)

| Topic | File | Tags | Status |
|-------|------|------|--------|
| Bazel Go Testing | knowledge/bazel-go-testing.md | bazel, go, test | Active |
| _Add domain knowledge here_ | | | |

---

## People & Team

| File | Content |
|------|---------|
| people/team-directory.md | Team members, roles, expertise areas |

---

## Reflections (lessons learned)

| File | Content |
|------|---------|
| reflections/mistakes.md | Things that went wrong and what was learned |
| reflections/patterns.md | Recurring patterns observed across tasks |
| reflections/decisions.md | Key technical decisions and rationale |

---

## Project Contexts (load with `/memory context <name>`)

| Project | File | Status | Last Accessed |
|---------|------|--------|---------------|
| _Add active projects here_ | contexts/<project>.md | in-progress | YYYY-MM-DD |

---

## Slack Conversations

Relevant Slack threads linked to projects. See `slack/README.md` for tracked channels.

| Project | File | Date | Topic |
|---------|------|------|-------|
| _Add relevant threads here_ | slack/<project>-<date>-<topic>.md | YYYY-MM-DD | Description |

---

## Working Context

_Current session scratchpad — updated during active work._

**Active task**: _None_
**Last session**: _Not yet initialized_

---

## Auto-Memory Detail Files

Files in `~/.claude/projects/<project>/memory/` (linked from MEMORY.md, managed
by the auto-memory system). Listed here for completeness — do not move these.

| Topic | File (relative to auto-memory root) | Tags |
|-------|-------------------------------------|------|
| _Add auto-memory files here_ | | |

---

## Archive

Stale memories (>90 days without access) move to `archive/YYYY-MM/`.
Still searchable via grep but not listed here.
