# Anamnesis Pilot Test Checklist

Manual testing guide for pilot testers. Work through each section in order.

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
  - [ ] `.claude/memory/INDEX.md`
  - [ ] `.claude/rules/memory-rule.md`
  - [ ] `.claude/skills/anamnesis/SKILL.md`
  - [ ] `.claude/.anamnesis-version`
  - [ ] `.claude/memory/knowledge/` (empty dir)
  - [ ] `.claude/memory/contexts/` (empty dir)
  - [ ] `.claude/memory/tasks/` (empty dir)
  - [ ] `.claude/memory/reflections/` (empty dir)

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

## 6. Claude Code — /anamnesis status

Open Claude Code in the same repo, then type:

```
/anamnesis status
```

- [ ] Skill triggers (recognized by Claude)
- [ ] Shows MEMORY.md line count with zone indicator
- [ ] Shows INDEX.md line count
- [ ] Shows memory counts by type (knowledge, tasks, contexts, etc.)
- [ ] Shows version info

## 7. Claude Code — /anamnesis init

```
/anamnesis init
```

- [ ] Skill triggers
- [ ] Detects existing structure (already initialized)
- [ ] If you have auto-memories (files in `~/.claude/projects/<project>/memory/`),
      it should offer to import them
- [ ] Creates backup before making changes

## 8. Claude Code — Auto-memory

Have a normal conversation with Claude where you learn something. After the
conversation, check:

- [ ] Claude saved a memory file to `.claude/memory/knowledge/` (or appropriate dir)
- [ ] File has proper YAML frontmatter (type, tags, created, etc.)
- [ ] INDEX.md was updated with a new entry

## 9. Sync — CLI

```bash
anamnesis sync
```

- [ ] Reports total sessions and unprocessed count
- [ ] Lists unprocessed session IDs with file sizes
- [ ] Directs user to run `/memory sync` in Claude Code

## 10. Sync — Claude Code

Open Claude Code and type:

```
/memory sync
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
/memory sync thread
```

- [ ] Claude analyzes the current conversation
- [ ] Identifies gotchas, knowledge, tasks, or reflections
- [ ] Presents candidates for approval
- [ ] Writes approved memories with proper frontmatter

## 12. Compact — CLI

```bash
anamnesis compact
```

- [ ] Reports total memory count
- [ ] Identifies duplicate groups (if any) with similarity scores
- [ ] Identifies stale memories (>90 days, or use `--days 30`)
- [ ] Directs user to `/memory compact` for semantic merging

## 13. Compact — Claude Code

```
/memory compact
```

- [ ] Claude reviews all memories for duplicates
- [ ] Proposes merge/archive actions
- [ ] Protects high-importance memories from auto-archive
- [ ] Executes approved actions (merge duplicates, archive stale)

## 14. Memory Commands — Claude Code

Test the full `/memory` skill:

- [ ] `/memory` → shows status dashboard
- [ ] `/memory search <term>` → searches memories by keyword
- [ ] `/memory add knowledge <title>` → creates a new memory interactively
- [ ] `/memory list` → lists all memories from INDEX.md
- [ ] `/memory list knowledge` → filters by type
- [ ] `/memory review` → flags stale memories for review
- [ ] `/memory stats` → shows system statistics

## 15. Edge cases

- [ ] Run `anamnesis init` outside a git repo → should show error
- [ ] Run `anamnesis init --auto` with existing config → skips prompts
- [ ] Create a large INDEX.md (>150 lines) → doctor should warn
- [ ] `anamnesis compact --days 30` → uses 30-day staleness threshold
- [ ] `anamnesis doctor` → reports unprocessed sessions count
- [ ] Add `.claude/` to `.gitignore` (optional — depends on your preference)

## Feedback

After testing, please share:

1. **What worked well?**
2. **What was confusing or broken?**
3. **Output of `anamnesis doctor`**
4. **Output of `/memory` in Claude Code**
5. **Any errors or unexpected behavior**
