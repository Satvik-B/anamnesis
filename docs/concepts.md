# Concepts

Core concepts behind the claude-memory system.

## Memory Tiers

### Hot Tier (MEMORY.md)

The hot tier is a single file -- `MEMORY.md` -- that Claude Code loads into
every conversation. Think of it as working memory: the handful of facts Claude
needs to be effective from the first message.

**What belongs here:**
- User identity: role, expertise, preferences
- Behavioral feedback: corrections that apply to most sessions
- Key repo facts: main language, critical paths, team conventions

**Constraints:**
- Hard cap of 200 lines (lines beyond 200 are silently truncated)
- Each entry should be 1-2 lines max
- Link to detail files for anything longer
- Target: 10-15 high-value entries

### Cold Tier (INDEX.md)

The cold tier is a structured catalog of all memories. Claude reads INDEX.md
when it needs to look something up -- a procedure, project context, or domain
knowledge.

**What belongs here:**
- Everything that doesn't need to be in every conversation
- Task runbooks, knowledge articles, project contexts, reflections
- Organized into tables by category

**Constraints:**
- Soft cap of 150 lines (attention degrades in large context blocks)
- Each row is a pointer to a memory file with tags and last-accessed date
- Archive stale entries to keep the index scannable

### Promotion and Demotion

Memories move between tiers:

- **Promote to hot:** When a cold memory is referenced in >50% of conversations
- **Demote to cold:** When a hot memory hasn't been useful in recent sessions
- **Archive:** When a memory is stale or the project it relates to is done

## Memory Types

### Tasks

Procedural knowledge: step-by-step instructions for recurring operations.

**Examples:** database migrations, deployment procedures, PR creation workflows,
debugging runbooks.

**When to create:** After successfully completing a multi-step procedure for
the first time. Save it so you (and Claude) don't have to figure it out again.

**Location:** `.claude/memory/tasks/`

### Knowledge

Facts, patterns, and conventions discovered during work.

**Examples:** API quirks, library gotchas, architecture decisions, team
conventions that aren't documented elsewhere.

**When to create:** When you learn something that would be useful in future
sessions but isn't obvious from the code alone.

**Location:** `.claude/memory/knowledge/`

### Contexts

Ongoing project state: what's happening, who's involved, what's the deadline.

**Examples:** "Auth rewrite targeting March 15", "Migration blocked on DBA
approval", "Alice owns the frontend, Bob owns the API".

**When to create:** When you start working on a project or initiative that
spans multiple sessions.

**Decay:** Contexts go stale quickly. Review and update them regularly.

**Location:** `.claude/memory/contexts/`

### Reflections

Lessons from mistakes. What went wrong, why, and what to do differently.

**Examples:** "Mocked tests passed but prod migration failed -- always test
against real DB", "Forgot to regenerate BUILD files after renaming -- run
bazel regeneration after file operations".

**When to create:** Whenever Claude (or you) makes a mistake that's likely
to recur.

**Location:** `.claude/memory/reflections/`

### Slack (optional)

Summaries of Slack conversations relevant to project contexts.

**When to create:** When a Slack thread contains decisions, commitments, or
context that would be lost otherwise.

**Location:** `.claude/memory/slack/`

## Memory Lifecycle

```
  1. Create          2. Use            3. Update         4. Archive
  --------          -----             -------           --------
  New fact or   ->  Claude reads  ->  Update when   ->  Mark done or
  procedure         on demand         things change     move to archive/
  discovered
```

### Creation

Memories can be created in three ways:
1. **Directly:** Tell Claude "remember that..." or create a file manually
2. **After procedures:** Claude offers to save successful multi-step procedures
3. **Via sync:** `claude-memory sync` imports auto-memories from sessions

### Usage

Claude uses memories by:
1. Reading MEMORY.md at session start (automatic)
2. Checking INDEX.md when a lookup is needed
3. Reading individual memory files for detail

### Updates

Memories should be updated when:
- The information changes (new API version, team member change)
- Additional context is learned
- The importance shifts (promote or demote)

### Archival

Memories are archived, never deleted:
- Completed projects -> archive the context file
- Outdated procedures -> mark done, note the replacement
- Stale entries (>90 days without access) -> archive

## File Format

All memory files use YAML frontmatter followed by Markdown content:

```markdown
---
type: task
tags: [deploy, staging]
created: 2026-01-15
last_accessed: 2026-03-01
access_count: 12
importance: high
source: learned
---

# Deploy to Staging

## Quick Reference
Run `make deploy-staging` from the repo root. Takes ~5 minutes.

## Content
<detailed steps>

## Gotchas
- Must be on VPN
- Requires DEPLOY_TOKEN env var

## Links
- Internal wiki: <url>
```

The frontmatter fields:
- **type:** task, knowledge, context, reflection, or custom
- **tags:** free-form labels for search and categorization
- **created / last_accessed:** dates for staleness tracking
- **access_count:** how often this memory has been read
- **importance:** high, medium, or low priority
- **source:** where the information came from
