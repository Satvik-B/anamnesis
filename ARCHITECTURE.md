# Architecture

System design document for anamnesis contributors.

## Overview

anamnesis is a file-based memory system that gives Claude Code persistent
context across sessions. It works by injecting a rule file into Claude Code's
`.claude/rules/` directory, which instructs the agent to read and write a
structured set of Markdown files.

There is no runtime daemon, no database, and no API. The "system" is a
convention: a directory layout, a set of Markdown formats, and a rule file
that teaches Claude how to use them.

## Design Principles

1. **Human-curated over automatic** -- The user decides what gets remembered.
   Automatic capture (session sync) is a convenience, not a replacement for
   curation.

2. **Plain text over databases** -- Markdown files are readable, editable,
   diffable, and version-controllable. No lock-in, no migration paths.

3. **Two tiers over flat** -- Cognitive science shows that working memory is
   limited (~7 items). The hot/cold split mirrors this: a small, always-loaded
   index for high-frequency facts, and a larger catalog for everything else.

4. **Convention over configuration** -- The system works by teaching Claude a
   set of conventions via the rule file. No config files, no environment
   variables, no setup beyond `init`.

## Two-Tier Index Design

### Why Two Tiers?

Claude Code has a finite context window. Loading all memories into every
session wastes tokens and dilutes attention. But loading none means Claude
starts from zero every time.

The two-tier design solves this by splitting memories into:

- **MEMORY.md (hot tier):** Always loaded. Contains the 10-15 most important
  facts: who the user is, active behavioral corrections, and key repo pointers.
  Hard cap: 200 lines (enforced by Claude's context loading -- lines beyond
  200 are silently truncated).

- **INDEX.md (cold tier):** Loaded on demand. A structured catalog of all
  memories organized by type. Claude reads this when it needs to look something
  up. Soft cap: 150 lines (attention degrades in large context blocks).

### Promotion and Demotion

Memories move between tiers based on access frequency:

```
  New memory
      |
      v
  INDEX.md (cold)  ----[frequent access]---->  MEMORY.md (hot)
      ^                                             |
      |                                             |
      +--------[infrequent / stale]<----------------+
```

The rule file includes decision criteria:
- "Is this needed in >50% of conversations?" -> hot
- "Is this a task runbook or domain knowledge?" -> cold
- "Is this user feedback or behavioral correction?" -> hot
- Unsure? -> cold (promote later if needed)

## Memory Types

### Tasks
Procedural knowledge: how to do X. Database migrations, deployment steps,
PR workflows, debugging runbooks.

```
.claude/memory/tasks/db-migration.md
.claude/memory/tasks/deploy-staging.md
```

### Knowledge
Facts and patterns learned during work. Architecture decisions, API quirks,
library gotchas, team conventions.

```
.claude/memory/knowledge/auth-flow.md
.claude/memory/knowledge/api-rate-limits.md
```

### Contexts
Ongoing project state: who is doing what, why, and by when. These decay
quickly and need regular updates.

```
.claude/memory/contexts/auth-rewrite.md
.claude/memory/contexts/q1-migration.md
```

### Reflections
Lessons from mistakes. What went wrong, why, and what to do differently.

```
.claude/memory/reflections/mistakes.md
```

### Slack (optional)
Summaries of relevant Slack conversations linked to project contexts.

```
.claude/memory/slack/auth-rewrite-2026-03-01.md
```

## Memory File Format

All memory files use a consistent frontmatter format:

```markdown
---
type: task | knowledge | context | reflection
tags: [tag1, tag2]
created: YYYY-MM-DD
last_accessed: YYYY-MM-DD
access_count: 1
importance: high | medium | low
source: learned | wiki | docs | slack | manual
---

# Title

## Quick Reference
<1-3 line summary for scanning>

## Content
<detailed content>

## Gotchas
<common pitfalls>

## Links
<relevant URLs>
```

## Session Sync Pipeline

Claude Code writes auto-memories to `~/.claude/projects/<project>/memory/`.
These are ephemeral notes that accumulate during sessions but aren't part of
the curated memory system.

`anamnesis sync` bridges this gap:

```
~/.claude/projects/<project>/memory/
  (auto-generated, ephemeral)
         |
         | anamnesis sync
         v
.claude/memory/
  (curated, version-controlled)
```

The sync pipeline:
1. Reads all auto-memory files from the platform-specific path
2. Parses frontmatter and content
3. Matches against existing INDEX.md entries (by topic/tags)
4. For new topics: proposes a new memory file (user confirms)
5. For existing topics: proposes a merge (user confirms)
6. Updates INDEX.md and optionally MEMORY.md

Sync is always interactive -- nothing is written without user confirmation.

## Safety Mechanisms

### Truncation Guards

MEMORY.md has a hard 200-line cap. The rule file instructs Claude to:
- Check line count before writing
- Enter "yellow zone" warnings at 150 lines
- Require consolidation at 180+ lines
- Refuse to append at 200+ lines until consolidated

### File Size Limits

Individual memory files should stay under 80 lines. Oversized files are split
into a summary (under 80 lines) and a detail file.

### Archive, Don't Delete

The system is append-only for action items and decisions. Completed items are
marked done, not deleted. Old memories are archived to `.claude/memory/archive/`,
not removed.

### Note Compaction

`anamnesis compact` handles memory hygiene:
- Deduplicates entries across MEMORY.md and INDEX.md
- Consolidates related entries
- Archives stale memories (configurable threshold)
- Reports on oversized files

## Extensibility

### Custom Memory Types

The type taxonomy (task, knowledge, context, reflection) is a convention, not
a hard constraint. Teams can add custom types by:
1. Creating a new subdirectory under `.claude/memory/`
2. Adding entries to INDEX.md with the new type
3. Updating the rule file to teach Claude about the new type

### Skills Integration

The skeleton includes a `/friday` skill for weekly check-ins. Additional skills
can be added to `.claude/skills/` to create memory-aware workflows.

### Platform Support

anamnesis detects the OS and uses the appropriate auto-memory path:
- macOS: `~/.claude/projects/<project>/memory/`
- Linux: `~/.claude/projects/<project>/memory/`
- Windows: `%USERPROFILE%\.claude\projects\<project>\memory\`

## Scope

### v1.0 (current)

- `init` command with skeleton scaffolding
- `sync` command for auto-memory integration
- `compact` command for memory hygiene
- Single-user, per-project memory
- Platform detection (macOS, Linux, Windows)

### v1.1 (planned)

- Team-shared memory layer
- Memory templates for common project types
- Integration with CI/CD for automated context updates
- Cross-project memory references
