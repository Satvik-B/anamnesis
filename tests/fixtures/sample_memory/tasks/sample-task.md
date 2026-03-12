---
type: task
tags: [db-migration, runbook]
created: 2026-02-15
last_accessed: 2026-03-01
access_count: 3
importance: medium
source: learned
---

# DB Schema Migration

## Quick Reference
Run migrations with `claude-memory migrate` after updating schema files.

## Content
1. Create a new migration file in `.claude/memory/migrations/`
2. Name it with the next sequential number: `NNN_description.sql`
3. Run the migration command
4. Verify with `claude-memory doctor`

## Gotchas
- Duplicate migration numbers silently fail
- Always back up INDEX.md before migrating

## Links
- Internal docs: see ARCHITECTURE.md
