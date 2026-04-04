---
name: memory
description: "Agent memory system — sync sessions, search, add, review, compact, load project context, and manage persistent memories across sessions. Use when the user says /memory, /memory sync, /memory compact, /memory search, /memory add, /memory context, /memory list, /memory review, /memory stats, or wants to save/recall knowledge."
disable-model-invocation: true
---

# /memory — Agent Memory System

## Memory Root
`.claude/memory/` — all paths below are relative to this root unless noted.

## Session Data Location
Claude Code sessions are stored as JSONL files at:
`~/.claude/projects/<sanitized-project-path>/<session-id>.jsonl`

The session ledger tracking processed sessions is at:
`.claude/memory/.sessions-ledger.yaml`

---

## Commands

Parse the user's input to determine which subcommand to run.

---

### `/memory` (no args) — Show status
Read `INDEX.md` and `.sessions-ledger.yaml`, then display:
- Total memories by type (tasks, knowledge, reflections, contexts)
- Last 3 accessed memories (by `last_accessed` frontmatter)
- Any stale memories (`last_accessed` > 30 days ago)
- Unprocessed sessions count (JSONL files not in ledger)
- MEMORY.md line count with zone indicator (green <150, yellow 150-179, red 180+)
- Current working context if set

---

### `/memory sync` — Session sync (Claude-driven extraction)

Read past Claude Code sessions, understand them, and extract memories.

#### Step 1: Find unprocessed sessions
```
sessions_dir = ~/.claude/projects/<sanitized-project-path>/
ledger = .claude/memory/.sessions-ledger.yaml
```

1. List all `*.jsonl` files in `sessions_dir`
2. Read the ledger (YAML file with `sessions:` mapping session_id → metadata)
3. Filter to sessions NOT in the ledger → these are unprocessed
4. If none: "All sessions processed. Nothing to sync."
5. Show the list: session ID, file size, and ask user which to process (or all)

#### Step 2: Read each unprocessed session

For each selected session:
1. Read the `.jsonl` file line by line
2. Each line is a JSON object. Extract messages where:
   - `entry.message.role` is `"user"` or `"assistant"`
   - `entry.message.content` is a string (or extract `text` from content array)
3. Build a conversation transcript
4. Skip tool results, system messages, and permission entries

#### Step 3: Extract memories (YOU do the understanding)

Read the conversation and identify memory-worthy content:

**Gotchas** — things that caused problems or need special attention:
- Error patterns and workarounds discovered
- API quirks, edge cases, unexpected behavior
- "Watch out for X", "Don't forget Y" moments

**Knowledge** — facts, conventions, architecture decisions:
- How systems work, design choices and rationale
- Patterns, conventions, and best practices established
- Technical discoveries ("TIL", "turns out")

**Tasks** — procedures that were followed:
- Step-by-step workflows that were executed
- Deployment procedures, migration steps
- Debugging processes that resolved issues

**Reflections** — lessons from mistakes:
- Wrong approaches that were tried and abandoned
- Better alternatives discovered
- "Next time, do X instead of Y"

For each candidate memory, determine:
- **Type**: gotcha / knowledge / task / reflection
- **Title**: Short, descriptive title
- **Content**: The key information (not raw transcript — synthesize)
- **Tags**: Relevant technical tags
- **Importance**: high / medium / low
- **Confidence**: How sure you are this is worth saving

#### Step 4: Check for conflicts

For each candidate, search existing memory files:
1. Scan `.claude/memory/{knowledge,tasks,contexts,reflections}/*.md`
2. Compare title and content for overlap
3. If high overlap (>80%): suggest SKIP (already know this)
4. If moderate overlap (60-80%): suggest MERGE (update existing)
5. If low overlap: proceed as new memory

#### Step 5: Present for approval

Show each candidate to the user:
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

For each approved memory:
1. Create the file at `.claude/memory/<type>s/<title-slug>.md` with frontmatter:
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
   ```
2. Add entry to `INDEX.md` in the appropriate table
3. For merged memories: read the existing file, append new content under
   `## Updated <date>`, update tags (union), update `last_accessed`

#### Step 7: Update ledger

After processing each session:
1. Read the ledger YAML
2. Add an entry:
   ```yaml
   sessions:
     <session-id>:
       processed_date: <today>
       memories_created: <count>
       content_hash: <sha256 of session file>
   ```
3. Write the ledger back

#### Step 8: Report
```
Sync complete!
  Sessions processed: 3
  Memories created: 5 (2 knowledge, 1 gotcha, 1 task, 1 reflection)
  Memories merged: 2
  Memories skipped: 1 (already known)
```

---

### `/memory sync thread` — Current thread sync

Analyze the CURRENT conversation for memory-worthy content.

1. Review the conversation history in this session
2. Apply the same extraction logic as session sync (Step 3 above)
3. Present candidates for approval
4. Write approved memories
5. Do NOT update the session ledger (this session is still active)

---

### `/memory compact` — Deduplicate and archive

#### Step 1: Find duplicates
1. Read all memory files from knowledge/, tasks/, contexts/, reflections/
2. Compare every pair for title + content similarity
3. Group near-duplicates (>60% overlap)

#### Step 2: Find stale memories
1. Check `last_accessed` frontmatter on all memory files
2. Flag memories not accessed in >90 days (or user-specified threshold)
3. Protect high-importance memories from auto-archive

#### Step 3: Present findings
```
Compact Report
==============
Duplicates found: 2 groups
  1. knowledge/api-auth.md + knowledge/jwt-tokens.md (78% overlap)
     Suggestion: MERGE into knowledge/api-auth.md
  2. tasks/deploy-prod.md + tasks/deployment.md (85% overlap)
     Suggestion: MERGE into tasks/deploy-prod.md

Stale memories: 3
  1. knowledge/old-api.md (120 days stale, importance: low)
     Suggestion: ARCHIVE
  2. tasks/deprecated-flow.md (95 days stale, importance: medium)
     Suggestion: REVIEW
  3. knowledge/legacy-auth.md (200 days stale, importance: high)
     Suggestion: KEEP (high importance) — review manually

[Merge all duplicates] [Archive stale] [Review individually]
```

#### Step 4: Execute
- **Merge**: Combine content, union tags, keep the older `created` date,
  update `last_accessed` to today, delete the duplicate file
- **Archive**: Move to `archive/YYYY-MM/`, remove from `INDEX.md`
- **Keep**: Update `last_accessed` to today (resets the clock)

---

### `/memory search <query>` — Search all memories
1. Read `INDEX.md` — scan for matching entries by name/tags
2. If not found in index, search across all memory files:
   ```
   Grep pattern="<query>" path=".claude/memory/"
   ```
3. For each match, show: file path, quick reference line, tags, last_accessed
4. Offer to open/read the most relevant match
5. Update `last_accessed` and `access_count` on any file that is read

---

### `/memory add <type> <title>` — Create a new memory
Types: `task`, `knowledge`, `context`, `reflection`

1. Ask the user what content to include (steps, facts, links, gotchas)
2. Create the file at `.claude/memory/<type>s/<title-slug>.md` with frontmatter
3. Add the entry to `INDEX.md` in the appropriate table
4. Confirm creation with file path

---

### `/memory context <name>` — Load project context

**If the context file exists** (`contexts/<name>.md`):
1. Read the context file
2. Read all files listed in its `related_memories` frontmatter
3. Read all files listed in its `key_files` frontmatter (codebase files)
4. Summarize the loaded context to the user:
   - What this project is about
   - Current status / where things left off
   - Key decisions made
   - Open questions / next steps
5. Update `last_accessed`
6. Say: "Context loaded. Ask me anything about <name>."

**If the context file does NOT exist**:
1. Search all memory files for the query term
2. Search the codebase for related files
3. Present findings and offer to create the context file

---

### `/memory context save <name>` — Save current project context
Create or update a context file at `.claude/memory/contexts/<name>.md`.
Ask the user for: description, status, key decisions, open questions, next steps.

---

### `/memory list [type]` — List memories
Types: `tasks`, `knowledge`, `contexts`, `reflections`, or `all` (default)

Read `INDEX.md` and display the relevant table. Highlight stale entries (>30 days).

---

### `/memory review` — Review and maintain memories
1. Scan all memory files for `last_accessed` dates
2. Flag stale memories (>30 days since last access)
3. For each stale memory, ask: keep, update, or archive?
4. Move archived memories to `archive/YYYY-MM/`
5. Remove archived entries from `INDEX.md`
6. Report: X memories reviewed, Y archived, Z kept

---

### `/memory stats` — Memory system statistics
Read all memory files and report:
- Total files by type
- MEMORY.md line count (with zone)
- INDEX.md line count
- Most accessed memories (by access_count)
- Stale memories (>30 days)
- Unprocessed sessions count
- Total processed sessions and memories created via sync

---

## Important Rules
- ALWAYS update `last_accessed` date when reading a memory file
- ALWAYS update `access_count` when reading a memory file
- ALWAYS verify memory content against current code (memory is guidance, not gospel)
- ALWAYS check for conflicts before writing new memories
- ALWAYS present candidates for user approval before writing (sync and add)
- Knowledge and reflection updates during normal work can be done silently
- Keep INDEX.md under 150 lines — archive when approaching
- Keep individual memory files under 80 lines — split when larger
