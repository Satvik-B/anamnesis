---
name: anamnesis
description: "Memory lifecycle — sync sessions, search, add, review, compact, and manage persistent memories. Use when the user says /anamnesis, /anamnesis sync, /anamnesis compact, /anamnesis search, /anamnesis add, /anamnesis list, /anamnesis review, /anamnesis stats."
disable-model-invocation: true
---

# /anamnesis — Memory System

## Path Discovery

Before running any command, determine these paths:

1. **Project root**: Your current working directory (cwd)
2. **Memory dir**: `<cwd>/.claude/memory/`
3. **Sessions dir**: `~/.claude/projects/<slug>/` where `<slug>` is the cwd
   with `/` replaced by `-` (e.g. `/Users/alice/myproject` → `-Users-alice-myproject`)

All scripts take these as explicit `--sessions-dir` and `--memory-dir` arguments.

## Script Location

Scripts are at `<skill_dir>/scripts/`. Replace `<skill_dir>` with the actual
path to this skill's directory (the directory containing this SKILL.md file).

---

## Commands

### `/anamnesis` (no args) — Status dashboard

1. Run: `python3 <skill_dir>/scripts/list-sessions.py --sessions-dir <sessions_dir> --memory-dir <memory_dir>`
2. Read `INDEX.md` from the memory dir
3. Count `.md` files in each subdirectory (knowledge/, tasks/, contexts/, reflections/)
4. Display:
   - Total memories by type
   - Unprocessed sessions count (from script output)
   - Last 3 accessed memories (by `last_accessed` frontmatter)
   - Stale memories (>30 days since last access)
   - MEMORY.md line count with zone (green <150, yellow 150-179, red 180+)

---

### `/anamnesis sync` — Session sync

Read past Claude Code sessions, extract memories, present for approval.

#### Step 1: Discover unprocessed sessions
Run:
```
python3 <skill_dir>/scripts/list-sessions.py --sessions-dir <sessions_dir> --memory-dir <memory_dir>
```
Parse the JSON output. If `unprocessed` is empty, report "All sessions processed."
Otherwise, show the list and ask which sessions to process (or all).

#### Step 2: Read each session
For each selected session, read the `.jsonl` file directly.
Each line is JSON. Extract messages where `entry.message.role` is `"user"` or `"assistant"`.
Skip tool results, system messages, and permission entries.
Build a conversation transcript.

#### Step 3: Extract memories (YOU do the understanding)
Read the conversation and identify memory-worthy content:

- **Gotchas**: errors, workarounds, "watch out for X", API quirks
- **Knowledge**: facts, conventions, architecture decisions, "TIL", "turns out"
- **Tasks**: procedures, step-by-step workflows, deployment steps
- **Reflections**: mistakes, lessons, "should have done X instead"

For each candidate, determine: type, title, content (synthesized, not raw), tags, importance.

#### Step 4: Check conflicts
For each candidate memory, run:
```
echo "<content>" | python3 <skill_dir>/scripts/check-conflicts.py --memory-dir <memory_dir> --title "<title>" --tags "<tag1,tag2>" --type "<type>"
```
Parse JSON output. If conflicts found:
- similarity >0.8 → suggest SKIP (already exists)
- similarity 0.6-0.8 → suggest MERGE
- similarity 0.4-0.6 → suggest ASK user

#### Step 5: Present for approval
Show each candidate:
```
Memory #1 [knowledge] (confidence: high)
  Title: API rate limits require exponential backoff
  Tags: [api, rate-limiting]
  Content: The external API enforces 100 req/min...
  Conflict: MERGE with knowledge/api-limits.md (72% overlap)

  [Save] [Merge] [Skip] [Edit]
```
Wait for user approval on each memory before writing.

#### Step 6: Write approved memories
For each approved memory, write the file directly to `<memory_dir>/<type>s/<slug>.md`
(use `knowledge/` not `knowledges/`, `tasks/` not `task/`):
```yaml
---
type: <type>
tags: [<tags>]
created: <today>
last_accessed: <today>
access_count: 1
importance: <importance>
source: sync
---

# <Title>

## Quick Reference
<1-3 line summary>

## Content
<detailed content>
```
Add entry to `INDEX.md` in the appropriate table.

#### Step 7: Update ledger
After processing each session, run:
```
python3 <skill_dir>/scripts/mark-processed.py --memory-dir <memory_dir> --session-id <id> --memories-created <count>
```

#### Step 8: Report
```
Sync complete!
  Sessions processed: 3
  Memories created: 5 (2 knowledge, 1 gotcha, 1 task, 1 reflection)
  Memories merged: 2
  Memories skipped: 1 (already known)
```

---

### `/anamnesis sync thread` — Current thread sync

Analyze the CURRENT conversation for memory-worthy content.

1. Review the conversation history in this session
2. Apply the same extraction logic as Step 3 above
3. Check conflicts (Step 4)
4. Present candidates for approval (Step 5)
5. Write approved memories (Step 6)
6. Do NOT update the session ledger (this session is still active)

---

### `/anamnesis compact` — Deduplicate and archive

#### Step 1: Find duplicates
Run:
```
python3 <skill_dir>/scripts/find-duplicates.py --memory-dir <memory_dir>
```

#### Step 2: Find stale memories
Run:
```
python3 <skill_dir>/scripts/decay-report.py --memory-dir <memory_dir> [--days 90]
```

#### Step 3: Present findings
Show duplicate groups and stale memories. For each:
- Duplicates → propose MERGE (combine content, union tags)
- Stale low-importance → propose ARCHIVE (move to archive/YYYY-MM/)
- Stale high-importance → KEEP but flag for review

#### Step 4: Execute approved actions
- **Merge**: Combine content, union tags, keep older `created` date,
  update `last_accessed`, delete the duplicate file, update INDEX.md
- **Archive**: Move file to `archive/YYYY-MM/`, remove from INDEX.md
- **Keep**: Update `last_accessed` to today (resets the clock)

---

### `/anamnesis search <query>` — Search memories
1. Read `INDEX.md` — scan for matching entries by name/tags
2. If not found, grep across all memory files
3. Show: file path, title, tags, last_accessed
4. Update `last_accessed` and `access_count` on any file read

---

### `/anamnesis add <type> <title>` — Create a new memory
Types: `knowledge`, `task`, `context`, `reflection`

1. Ask user for content, tags, importance
2. Check conflicts (Step 4 from sync)
3. Write the memory file with frontmatter
4. Add entry to INDEX.md

---

### `/anamnesis list [type]` — List memories
Read INDEX.md, display the relevant table. Highlight stale entries (>30 days).

---

### `/anamnesis review` — Review stale memories
1. Run: `python3 <skill_dir>/scripts/decay-report.py --memory-dir <memory_dir> --days 30`
2. For each stale memory, ask: keep, update, or archive?
3. Execute approved actions

---

### `/anamnesis stats` — System statistics
1. Run: `python3 <skill_dir>/scripts/list-sessions.py --sessions-dir <sessions_dir> --memory-dir <memory_dir>`
2. Run: `python3 <skill_dir>/scripts/decay-report.py --memory-dir <memory_dir>`
3. Run: `python3 <skill_dir>/scripts/find-duplicates.py --memory-dir <memory_dir>`
4. Count files by type, report MEMORY.md/INDEX.md line counts
5. Show most accessed memories, total processed sessions

---

## Important Rules
- ALWAYS update `last_accessed` and `access_count` when reading a memory file
- ALWAYS verify memory against current code (memory is guidance, not gospel)
- ALWAYS check for conflicts before writing new memories
- ALWAYS present candidates for user approval before writing
- Keep INDEX.md under 150 lines — archive when approaching
- Keep individual memory files under 80 lines — split when larger
- Use canonical directory names: `knowledge/`, `tasks/`, `contexts/`, `reflections/`
