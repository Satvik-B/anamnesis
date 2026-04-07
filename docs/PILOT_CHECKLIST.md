# Anamnesis Pilot Test Checklist

## What is Anamnesis?

Every Claude Code session starts from zero. Your agent doesn't remember the debugging pattern you discovered yesterday, the team convention you explained last week, or the deployment gotcha that cost you an hour. You repeat yourself constantly.

**Anamnesis fixes this.** It's a persistent memory system that gives Claude Code structured, searchable memory across sessions — stored as plain Markdown files you can read, edit, and version control.

### How it works

1. **`anamnesis init`** — one-time setup, scaffolds `.claude/memory/` in your project
2. **`/anamnesis sync`** — Claude reads your past sessions and extracts knowledge, gotchas, tasks, and lessons into structured memory files with your approval
3. **`/anamnesis compact`** — Claude finds duplicates and stale memories, proposes merges and archives
4. Claude's built-in rules (`memory-rule.md`) automatically save new memories during normal conversations

### What you get

- **Gotchas remembered**: "Don't mock the database — prod migration broke last time" stays across sessions
- **Procedures saved**: Step-by-step runbooks extracted from past work, reusable forever
- **Corrections stick**: Tell Claude once to use snake_case — it remembers
- **Zero infrastructure**: Plain Markdown, no databases, no cloud, no API keys
- **Full control**: Every memory is a file you can read with `cat`, edit with vim, and track with git

### Architecture (30-second version)

```
~/.claude/projects/<project>/memory/MEMORY.md   ← hot index (auto-loaded, 200-line cap)
<project>/.claude/memory/INDEX.md                ← cold catalog (loaded on demand)
<project>/.claude/memory/knowledge/              ← facts, conventions, gotchas
<project>/.claude/memory/tasks/                  ← step-by-step procedures
<project>/.claude/memory/reflections/            ← lessons from mistakes
<project>/.claude/memory/contexts/               ← project state snapshots
```

---

## Prerequisites

- Python 3.9+
- Claude Code installed and working
- A git repository to test in

## 1. Installation

```bash
pip install git+https://github.com/Satvik-B/anamnesis.git
```

- [ ] Command completes without errors
- [ ] `anamnesis --version` prints a version number

## 2. Init (first run)

```bash
cd <your-git-repo>
anamnesis init
```

- [ ] Prompts for name and role
- [ ] Creates `.claude/` directory
- [ ] Reports files created
- [ ] Verify these exist:
  - [ ] `.claude/anamnesis/INDEX.md`
  - [ ] `.claude/rules/anamnesis-rule.md`
  - [ ] `.claude/skills/anamnesis/SKILL.md`
  - [ ] `.claude/.anamnesis-version`
  - [ ] `.claude/anamnesis/knowledge/` (empty dir)
  - [ ] `.claude/anamnesis/contexts/` (empty dir)
  - [ ] `.claude/anamnesis/tasks/` (empty dir)
  - [ ] `.claude/anamnesis/reflections/` (empty dir)

## 3. Doctor

```bash
anamnesis doctor
```

- [ ] Shows OK for all checks
- [ ] No ERROR lines
- [ ] Exit code is 0

## 4. Re-init (idempotency + backup)

```bash
anamnesis init
```

- [ ] Creates `.claude.anamnesis-backup-<timestamp>/` directory
- [ ] Does NOT overwrite existing files (reports "nothing to create" or "already exist")
- [ ] Backup directory contains a copy of your `.claude/` structure

## 5. Update

```bash
anamnesis update
```

- [ ] Updates rule and skill files
- [ ] Reports which files were updated
- [ ] Reports which user-data files were skipped

## 6. Claude Code — /anamnesis (status)

Open Claude Code in the same repo, then type:

```
/anamnesis
```

- [ ] Skill triggers (recognized by Claude)
- [ ] Shows MEMORY.md line count with zone indicator
- [ ] Shows INDEX.md line count
- [ ] Shows memory counts by type (knowledge, tasks, contexts, etc.)
- [ ] Shows unprocessed sessions count

## 7. Claude Code — /anamnesis add

```
/anamnesis add knowledge "test topic"
```

- [ ] Skill triggers
- [ ] Asks for content, tags, importance
- [ ] Creates file in `.claude/anamnesis/knowledge/`
- [ ] Updates INDEX.md with new entry

## 8. Claude Code — Auto-memory

Have a normal conversation with Claude where you learn something. After the
conversation, check:

- [ ] Claude saved a memory file to `.claude/anamnesis/knowledge/` (or appropriate dir)
- [ ] File has proper YAML frontmatter (type, tags, created, etc.)
- [ ] INDEX.md was updated with a new entry

## 9. Sync — Claude Code

Open Claude Code and type:

```
/anamnesis sync
```

- [ ] Claude finds unprocessed session JSONL files
- [ ] Claude reads sessions and extracts memory candidates
- [ ] Presents candidates with type, title, confidence, and conflict info
- [ ] Asks for approval before writing each memory
- [ ] Updates the session ledger after processing
- [ ] Report shows counts of created/merged/skipped memories

## 11. Thread Sync — Claude Code

Have a conversation where you discover a gotcha or learn something, then:

```
/anamnesis sync thread
```

- [ ] Claude analyzes the current conversation
- [ ] Identifies gotchas, knowledge, tasks, or reflections
- [ ] Presents candidates for approval
- [ ] Writes approved memories with proper frontmatter

## 12. Compact — Claude Code

```
/anamnesis compact
```

- [ ] Claude reviews all memories for duplicates
- [ ] Proposes merge/archive actions
- [ ] Protects high-importance memories from auto-archive
- [ ] Executes approved actions (merge duplicates, archive stale)

## 14. Memory Commands — Claude Code

Test the full `/anamnesis` skill:

- [ ] `/anamnesis` → shows status dashboard
- [ ] `/anamnesis search <term>` → searches memories by keyword
- [ ] `/anamnesis add knowledge <title>` → creates a new memory interactively
- [ ] `/anamnesis list` → lists all memories from INDEX.md
- [ ] `/anamnesis list knowledge` → filters by type
- [ ] `/anamnesis review` → flags stale memories for review
- [ ] `/anamnesis stats` → shows system statistics

## 15. Edge cases

- [ ] Run `anamnesis init` outside a git repo → should show error
- [ ] Run `anamnesis init --auto` with existing config → skips prompts
- [ ] Create a large INDEX.md (>150 lines) → doctor should warn
- [ ] `anamnesis doctor` → reports unprocessed sessions count
- [ ] Add `.claude/` to `.gitignore` (optional — depends on your preference)

## Feedback

After testing, please share:

1. **What worked well?**
2. **What was confusing or broken?**
3. **Output of `anamnesis doctor`**
4. **Output of `/anamnesis` in Claude Code**
5. **Any errors or unexpected behavior**
