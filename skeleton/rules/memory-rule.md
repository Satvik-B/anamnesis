# Agent Memory System

A personal memory system exists at `.claude/memory/`. Use it as follows:

## Index Boundary Rule: MEMORY.md vs INDEX.md

The memory system has two index files with distinct roles. Never duplicate
content across them — each entry lives in exactly one place.

### MEMORY.md (Hot Index — always loaded)

Location: `~/.claude/projects/<project>/memory/MEMORY.md`
Loaded: **automatically into every conversation context** (200-line hard cap).

**What belongs here** (must pass the ">50% of conversations" bar):
- User identity, role, and interaction preferences
- Active behavioral feedback (corrections that shape every response)
- Repo-wide facts needed constantly (repo name, key paths)
- Pointer to INDEX.md and the extended memory system

**Format**: Each entry is 1-2 lines max. Link to a detail file for anything
longer. Never inline multi-line content — MEMORY.md is a pointer file.

**Max entries**: 10-15 high-value items. When adding a new entry, consider
whether an existing one can be demoted to INDEX.md.

### INDEX.md (Cold Index — loaded on demand)

Location: `.claude/memory/INDEX.md`
Loaded: **only when a procedural task or knowledge lookup is needed**.

**What belongs here**: The complete catalog of all memories — tasks, knowledge,
reflections, project contexts, Slack threads, people, archive. Everything that
doesn't need to be in every conversation but must be findable.

**Format**: Structured tables grouped by category. Each row is a pointer to a
memory file with tags and last-accessed date.

### Decision Flow: Where Does a New Entry Go?

1. Is this needed in >50% of conversations? → MEMORY.md (hot)
2. Is this a task runbook, knowledge article, or project context? → INDEX.md (cold)
3. Is this user feedback or a behavioral correction? → MEMORY.md (hot)
4. Is this detailed domain knowledge? → INDEX.md (cold), with an optional
   1-line summary in MEMORY.md only if referenced very frequently
5. Unsure? → INDEX.md (cold). Promote to MEMORY.md later if it proves essential.

### Keeping Them in Sync

- When creating a new memory file, add it to INDEX.md (always) and MEMORY.md
  (only if it meets the hot-index criteria above).
- When demoting an entry from MEMORY.md, ensure it exists in INDEX.md before
  removing it from MEMORY.md.
- Never duplicate the same content in both — MEMORY.md may contain a 1-line
  pointer to a topic that INDEX.md catalogs in detail, but the pointer and the
  catalog entry are different things.

---

## Continuous Memory Updates

Claude writes directly to the Anamnesis memory structure on every conversation
where something worth remembering is learned. No separate sync step is needed
for daily use.

### After every conversation where you learn something worth remembering:

1. **Determine the memory type**:
   - `knowledge` — facts, patterns, conventions, gotchas
   - `task` — procedural runbooks ("how to do X")
   - `context` — project state snapshots, active work
   - `reflection` — lessons learned, mistakes, corrections
   - `feedback` — user corrections about your behavior

2. **Write directly** to `.claude/memory/<type>/<descriptive-name>.md`
   using the standard frontmatter format (see "File Format for New Memories" below)

3. **Update INDEX.md** — add a row to the matching table in `.claude/memory/INDEX.md`

4. **Update MEMORY.md** — only if the memory is high-importance and needed in
   >50% of conversations (see the Index Boundary Rule above)

### When to prompt vs. auto-save:

- **Auto-save without asking**: knowledge, reflections, feedback
- **Ask first**: context-type memories (project snapshots) — these are larger
  and the user should confirm the scope and framing
- **Auto-save tasks**: only after the user confirms the procedure worked

### References

When a memory is created in the context of a specific JIRA ticket, PR, design
doc, Slack thread, or other external resource, include it in the frontmatter:

```yaml
references:
  - url: https://example.atlassian.net/browse/PROJ-123
    label: JIRA ticket
  - url: https://github.com/org/repo/pull/42
    label: PR
```

This links memories to their source of truth for future verification.

---

## Size Discipline: Truncation Guards

The memory system has hard limits. Exceeding them causes **silent data loss** —
no warning, no error, just missing memories. These rules prevent that.

### MEMORY.md Line Budget (Hard Cap: 200 lines)

MEMORY.md is the auto-memory file at `~/.claude/projects/<project>/memory/MEMORY.md`.
Only the first 200 lines are loaded into conversation context. Everything past
line 200 is silently dropped — the agent has no way to know content was lost.

**Before every MEMORY.md write:**

1. **Count**: Check current line count of MEMORY.md before writing.
2. **Green zone (under 150 lines)**: Write normally.
3. **Yellow zone (150-179 lines)**: Write is allowed, but review whether any
   existing entries can be demoted to topic files or INDEX.md.
4. **Red zone (180-199 lines)**: **Stop and consolidate first.** Before adding
   new content, move at least 20 lines of lower-priority content to topic files.
   Then write.
5. **Overflow (200+ lines)**: If MEMORY.md is already at or above 200 lines,
   **do not append**. First run the consolidation procedure below, then write.

**Consolidation procedure** (when MEMORY.md exceeds 150 lines):
- Identify entries that don't meet the ">50% of conversations" bar
- Move their content to topic files (e.g., `api_research.md`)
- Replace the entry in MEMORY.md with a 1-line pointer or remove it entirely
- Target: bring MEMORY.md back under 120 lines after consolidation

### INDEX.md Line Budget (Soft Cap: 150 lines)

INDEX.md at `.claude/memory/INDEX.md` has no system-enforced truncation but
faces attention degradation — LLMs retrieve information less reliably from
large context blocks (the "Lost in the Middle" effect). Cap at 150 lines.

**When INDEX.md approaches 150 lines:**
- Archive inactive project contexts (status: completed/abandoned) to `archive/`
- Archive stale entries (>90 days without access) to `archive/YYYY-MM/`
- Merge related knowledge entries where possible
- Collapse completed task rows into a single "Archived N tasks" summary line

### Per-File Size Limit (80 lines guidance)

Individual memory files (knowledge articles, task runbooks, context files)
should stay under ~80 lines. This keeps them scannable and within a single
tool-read response.

**When a memory file exceeds 80 lines:**
- Split into a summary file (under 80 lines) and a detail file
- Example: `api-research.md` (summary) links to
  `api-research-detail.md` (full research)
- The summary file goes in the normal location; the detail file goes in
  `archive/detail/` or alongside it with a `-detail` suffix

**Auto-memory topic files** (in `~/.claude/projects/<project>/memory/`) follow
the same 80-line guidance. These are read on demand so they're less critical,
but oversized files waste context when loaded.

### Archive Structure

```
.claude/memory/archive/
├── README.md              # Explains archive purpose and process
├── YYYY-MM/              # Monthly archive directories
│   └── <archived-file>.md
└── detail/               # Split-off detail files
    └── <topic>-detail.md
```

Archived files are removed from INDEX.md's active tables but remain searchable
via grep. They keep their original frontmatter for provenance.

---

## CRITICAL: Memory is guidance, not gospel

Memory files may be outdated. **Always verify memory against current code.**
If memory says "do X" but the code has changed, trust the code. Update the
memory file to reflect the new reality. Never blindly follow a memory file
without checking that it still applies.

## Before Procedural Tasks

When the user asks "how do I do X?" or you need to perform a multi-step
procedure (DB migration, service deployment, PR creation, pipeline debugging,
CI job setup, etc.):

1. Check `.claude/memory/INDEX.md` for a matching task memory
2. **If found**, read the task file — use it as a starting point, but verify
   key steps still work against the current codebase
3. **If not found**, proceed normally (search codebase, docs, web)
4. **After completing** a new procedure successfully, offer to save it:
   "Want me to save this as a task memory for next time?"

## When Learning Something New

When you discover a useful fact, pattern, convention, or gotcha during work:

1. Check if a related knowledge file exists in `.claude/memory/knowledge/`
2. If yes — update it (merge new info, bump the `last_accessed` date)
3. If no — create a new knowledge file with the standard frontmatter
4. Update `.claude/memory/INDEX.md` with the new entry

## When Making Mistakes

When a task fails, a wrong approach is taken, or the user corrects you:

1. Log the lesson in `.claude/memory/reflections/mistakes.md`
2. Format: `### YYYY-MM-DD: <title>` + what went wrong + what to do instead

## File Format for New Memories

```markdown
---
type: task | knowledge | reflection
tags: [tag1, tag2]
created: YYYY-MM-DD
last_accessed: YYYY-MM-DD
access_count: 1
importance: high | medium | low
source: learned | wiki | confluence | slack | manual
---

# Title

## Quick Reference
<1-3 line summary>

## Content
<detailed content>

## Gotchas
<common pitfalls>

## Links
<relevant URLs>
```

## Slack → Memory Integration

When processing Slack messages (during `/friday` morning check-in, or any Slack
search/fetch), link relevant conversations to project contexts:

1. After fetching Slack messages, check `.claude/memory/contexts/` for active projects
2. For each message that relates to a project (mentions the project topic, a related
   PR, JIRA, team member, or technical term), ask the user:
   "This message about <topic> looks relevant to your <project-name> context. Save it?"
3. If yes, save to `.claude/memory/slack/<project>-<date>-<topic-slug>.md`:
   ```markdown
   ---
   type: slack
   project: <project-name>
   channel: <channel-name>
   date: YYYY-MM-DD
   participants: [user1, user2]
   thread_ts: <thread timestamp if applicable>
   ---

   # <Topic>

   ## Key Points
   <summarized key points, not raw message dump>

   ## Action Items
   - <any commitments or asks>

   ## Context
   <why this conversation matters for the project>
   ```
4. Update the project context file's `slack_threads` list
5. Add the channel to `slack/README.md` tracked channels if new

### When the user asks about a project or needs to reply
If the user asks about a project context and there are saved Slack conversations:
- Surface relevant Slack memories alongside other project context
- Help formulate replies based on the conversation history and project state

## NEVER Delete — Always Mark

**Action items, next steps, and decisions are append-only.** When updating memory:
- **Done items**: Mark with `[x]` or `~~strikethrough~~`, keep the text
- **Not relevant**: Add a note explaining WHY it's not relevant, then mark done
- **Superseded**: Add "Superseded by: <new item>" and mark done
- **NEVER delete lines** from next steps, action items, or decisions sections
- Context is permanent — losing it means losing the "why" behind decisions

## Do NOT

- Do not save session-specific or temporary context as memories
- Do not create duplicate memories — always check INDEX.md first
- Do not save speculative or unverified information
- Do not automatically save without offering — let the user decide for task memories
- Do not follow memory blindly — always cross-check against current code state
- Do not let memory lookup slow down simple tasks — skip memory for trivial questions
- Do not delete completed/outdated items — mark them done with context
