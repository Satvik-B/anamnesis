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

## 9. Claude Code — /anamnesis sync

```
/anamnesis sync
```

- [ ] Reports how many auto-memories are unsynced
- [ ] Offers to import new ones (or reports none to import)

## 10. Edge cases

- [ ] Run `anamnesis init` outside a git repo → should show error
- [ ] Run `anamnesis init --auto` with existing config → skips prompts
- [ ] Create a large INDEX.md (>150 lines) → doctor should warn
- [ ] Add `.claude/` to `.gitignore` (optional — depends on your preference)

## Feedback

After testing, please share:

1. **What worked well?**
2. **What was confusing or broken?**
3. **Output of `anamnesis doctor`**
4. **Output of `/anamnesis status` in Claude Code**
5. **Any errors or unexpected behavior**
