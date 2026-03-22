---
name: anamnesis
description: "Memory lifecycle management — init, sync, and health checks. Use when the user says: /anamnesis, /anamnesis init, /anamnesis sync, /anamnesis status, initialize memory, memory health, set up anamnesis, check memory status."
disable-model-invocation: true
---

# Anamnesis — Memory Lifecycle Skill

Manages the structured memory system lifecycle: initialization, sync, and health monitoring.

> **Daily memory updates happen automatically** via `memory-rule.md`. This skill
> handles setup and maintenance — not everyday saving.

## Subcommands

Parse the user's input to determine which subcommand to run:
- `/anamnesis init` (or just `/anamnesis`) → Init
- `/anamnesis sync` → Sync
- `/anamnesis status` → Status

If the input includes `--auto` or `auto`, set AUTO_MODE=true (skip confirmation prompts).

---

## `/anamnesis init` — Idempotent Setup

Safe to re-run. Creates the memory structure and imports existing auto-memories.

### Step 1: Detect current state

```python
project_root = # walk up from cwd to find .git directory
claude_dir = project_root / ".claude"
memory_dir = claude_dir / "memory"
version_file = claude_dir / ".anamnesis-version"
rule_file = claude_dir / "rules" / "memory-rule.md"
```

Check what exists:
- `memory_dir` exists?
- `memory_dir / "INDEX.md"` exists?
- `version_file` exists? What version?
- `rule_file` exists? Has it been user-modified?

### Step 2: Backup

Before making ANY changes, create a backup:

```
cp -r .claude/ .claude.anamnesis-backup-<YYYYMMDD-HHMMSS>/
```

Tell the user: "Backed up .claude/ to .claude.anamnesis-backup-&lt;timestamp&gt;/"

### Step 3: Create directory structure

Create these directories if missing:
```
.claude/memory/
.claude/memory/knowledge/
.claude/memory/contexts/
.claude/memory/tasks/
.claude/memory/reflections/
.claude/memory/archive/
.claude/memory/slack/
```

### Step 4: Create INDEX.md if missing

Only if `.claude/memory/INDEX.md` does NOT exist, create it with empty tables:

```markdown
# Memory Index (Complete Catalog)

> **Cold index** — loaded on demand for task lookups and knowledge retrieval.
> For the always-loaded hot pointers, see `MEMORY.md` (auto-memory).
> For the boundary rule, see `.claude/rules/memory-rule.md`.

## Quick Facts
- Memory root: `.claude/memory/`
- Auto-memory root: `~/.claude/projects/<project>/memory/`

---

## Task Memories (runbooks)

| Task | File | Tags | Last Accessed |
|------|------|------|---------------|

---

## Knowledge Base (facts, patterns, conventions)

| Topic | File | Tags | Status |
|-------|------|------|--------|

---

## Reflections (lessons learned)

| File | Content |
|------|---------|

---

## Project Contexts

| Project | File | Status | Last Accessed |
|---------|------|--------|---------------|

---

## Slack Conversations

| Project | File | Date | Topic |
|---------|------|------|-------|

---

## Archive

Stale memories (>90 days without access) move to `archive/YYYY-MM/`.
```

### Step 5: Install/update memory-rule.md

If `rule_file` does not exist, copy it from the skeleton.

If it exists, check if it was user-modified (compare against skeleton version):
- If modified and NOT in auto mode: ask "memory-rule.md has been customized. Overwrite with latest? (Backup at .claude.anamnesis-backup-*/)"
- If modified and in auto mode: overwrite silently
- If unmodified: overwrite silently

### Step 6: Auto-memory import

Scan the auto-memory directory for existing `.md` files:

```python
# Auto-memory location:
# project_root = /Users/alice/myproject
# sanitized = -Users-alice-myproject
auto_memory_dir = ~/.claude/projects/<sanitized-project-path>/memory/
```

Find all `.md` files EXCEPT `MEMORY.md` (the hot index is system-managed).

For each file found:
1. Read its content
2. Categorize by content/filename:
   - Contains "task", "runbook", "how to" → `tasks/`
   - Contains "context", "project" → `contexts/`
   - Contains "mistake", "lesson", "reflection" → `reflections/`
   - Default → `knowledge/`
3. Check if a file with the same name already exists in the target directory
   - If yes: skip (already imported)
   - If no: queue for import

If AUTO_MODE:
- Import all queued files without prompting
Else:
- Present the list to the user with categories
- Ask: "Import these N files? (Y/n/select individually)"

For each imported file:
- If it already has YAML frontmatter, preserve it and add missing fields
- If it lacks frontmatter, wrap it:
  ```yaml
  ---
  type: <category>
  tags: []
  created: <today>
  last_accessed: <today>
  access_count: 1
  importance: medium
  source: import
  ---
  ```
- Copy to the appropriate `.claude/memory/<type>/` directory
- Add an entry to INDEX.md in the matching table

### Step 7: Report summary

```
Anamnesis initialized successfully!

  Backup:        .claude.anamnesis-backup-20260322-143052/
  Directories:   6 created (or already existed)
  INDEX.md:      created (or already existed)
  Rule file:     installed (or updated / already current)
  Auto-memories: imported 5, skipped 2 duplicates

  Next: Claude will automatically save memories on every conversation.
  Run /anamnesis status to check health anytime.
```

### Step 8: Warn about parallel sessions

```
Note: If other Claude Code sessions are open for this project,
they'll pick up the new memory structure on their next turn.
```

---

## `/anamnesis sync` — Catch-up Import

For importing auto-memories that Claude's continuous updates missed (e.g., from
other sessions or pre-install memories).

### Step 1: Locate auto-memory directory

Same path logic as init Step 6.

### Step 2: Scan for unsynced files

Find `.md` files in auto-memory dir (except MEMORY.md). For each:
- Check if a corresponding file exists in `.claude/memory/` (by filename match)
- If not found → mark as "new, unsynced"

### Step 3: Categorize and present

Same categorization logic as init Step 6.

If AUTO_MODE:
- Import all without prompting
Else:
- Present list with categories and ask user to confirm

### Step 4: Import

Same import logic as init Step 6 (add frontmatter, copy, update INDEX.md).

### Step 5: Report

```
Sync complete!
  Imported: 3 new memories
  Skipped:  7 already synced
  Categories: 2 knowledge, 1 context
```

---

## `/anamnesis status` — Health Dashboard

Read-only health check of the memory system.

### Checks to perform:

1. **MEMORY.md line count**
   ```python
   auto_memory_dir = ~/.claude/projects/<sanitized>/memory/
   memory_md = auto_memory_dir / "MEMORY.md"
   line_count = len(memory_md.read_text().splitlines())
   ```
   Display with zone:
   - Green (< 150): "MEMORY.md: {n} lines (healthy)"
   - Yellow (150-179): "MEMORY.md: {n} lines (approaching limit, consider consolidating)"
   - Red (180-199): "MEMORY.md: {n} lines (CRITICAL — consolidate now)"
   - Overflow (200+): "MEMORY.md: {n} lines (OVERFLOW — content is being silently truncated!)"

2. **INDEX.md line count** vs 150 soft cap

3. **Memory counts by type** — count `.md` files in each subdirectory:
   knowledge/, tasks/, contexts/, reflections/, slack/, archive/

4. **Stale memories** — scan for `last_accessed:` in frontmatter, flag >30 days

5. **Oversized files** — flag any memory file >80 lines

6. **Unsynced auto-memories** — count `.md` files in auto-memory dir without
   a corresponding file in `.claude/memory/`

7. **Rule file status** — check `.claude/rules/memory-rule.md` exists

8. **Version check** — read `.claude/.anamnesis-version`

### Output format:

```
Anamnesis Health Dashboard
==========================

MEMORY.md:    42 lines   [GREEN]
INDEX.md:     67 lines   (soft cap: 150)
Version:      1.0.0      (current)
Rule file:    installed   (current)

Memory Inventory:
  knowledge/    8 files
  tasks/        3 files
  contexts/     4 files
  reflections/  2 files
  slack/        1 file
  archive/      0 files
  ─────────────────────
  Total:       18 memories

Warnings:
  - 2 stale memories (not accessed in 30+ days)
  - 1 oversized file (contexts/big-project.md: 142 lines)
  - 3 unsynced auto-memories

Suggestions:
  - Run /anamnesis sync to import 3 unsynced auto-memories
  - Review stale memories: knowledge/old-api.md, tasks/deprecated-flow.md
  - Split oversized file: contexts/big-project.md (142 lines > 80 line guideline)
```

---

## Memory File Format Reference

When creating or importing memory files, use this frontmatter:

```yaml
---
type: knowledge | task | context | reflection | feedback
tags: [tag1, tag2]
created: YYYY-MM-DD
last_accessed: YYYY-MM-DD
access_count: 1
importance: high | medium | low
source: learned | manual | session | import
references:
  - url: https://example.com
    label: Description
---
```

## Directory Layout

```
.claude/memory/
├── INDEX.md               # Cold catalog (on demand, 150-line soft cap)
├── knowledge/             # Facts, patterns, conventions
├── tasks/                 # Procedural runbooks ("how to X")
├── contexts/              # Project state snapshots
├── reflections/           # Lessons learned, mistakes
├── slack/                 # Conversation summaries
└── archive/               # Stale memories (>90 days)
```

MEMORY.md (hot index) lives in the auto-memory dir:
`~/.claude/projects/<sanitized-project-path>/memory/MEMORY.md`
