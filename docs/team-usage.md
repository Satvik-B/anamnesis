# Team Usage

> **Note:** Team-shared memory is planned for v1.1. This document describes the
> current single-user workflow and outlines the planned team features.

## Current State (v1.0)

In v1.0, claude-memory is a per-user, per-project system. Each developer has
their own `.claude/memory/` directory with their own memories.

### Sharing via Git

You can share memories by committing `.claude/memory/` to your repository:

```bash
git add .claude/memory/
git commit -m "Add shared project conventions to memory"
```

This works well for:
- **Shared knowledge:** API conventions, architecture decisions, team patterns
- **Onboarding context:** project history, key decisions, common gotchas
- **Task runbooks:** deployment procedures, migration steps

It works less well for:
- **Personal preferences:** Each developer has different experience levels and
  interaction styles
- **Active project contexts:** These change too frequently for git to be practical

### Recommended Approach

Split your memory into shared and personal:

```
.claude/memory/
  MEMORY.md             # Personal (gitignored or per-developer)
  INDEX.md              # Shared catalog
  knowledge/            # Shared knowledge (committed)
  tasks/                # Shared runbooks (committed)
  contexts/             # Mixed (some shared, some personal)
  reflections/          # Personal (gitignored)
```

## Planned: v1.1 Team Features

The v1.1 release will add first-class team support:

- **Shared memory layer:** A team-wide memory directory alongside personal memory
- **Memory templates:** Pre-built memory structures for common project types
  (web app, microservices, data pipeline, etc.)
- **Conflict resolution:** Tooling to merge memory changes from multiple developers
- **Onboarding mode:** New team members automatically get shared context

These features are under active development. If you have specific team needs,
please open an issue on GitHub.
