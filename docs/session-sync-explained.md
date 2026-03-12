# Session Sync Explained

How `claude-memory sync` bridges auto-memories and your curated memory system.

## Background

When you use Claude Code, it writes auto-memory files to a platform-specific
directory:

```
~/.claude/projects/<project-hash>/memory/
```

These files contain notes Claude wrote during your sessions -- things it
learned about you, your project, or your preferences. But they're ephemeral:
scattered across sessions, not organized, and not part of your version-controlled
memory system.

**Session sync** merges these auto-memories into your curated `.claude/memory/`
directory.

## How It Works

### Step 1: Discovery

`claude-memory sync` finds your auto-memory directory by:
1. Detecting your OS (macOS, Linux, or Windows)
2. Resolving the Claude Code project path
3. Scanning for `.md` files in the auto-memory directory

### Step 2: Parsing

Each auto-memory file is parsed for:
- **Frontmatter:** type, tags, description (if present)
- **Content:** the actual memory text
- **Topic:** inferred from filename and content

### Step 3: Matching

Each auto-memory is compared against your existing INDEX.md:
- **New topic:** No existing memory matches -> propose creating a new file
- **Existing topic:** A memory with similar tags/content exists -> propose merging

### Step 4: Interactive Review

For each auto-memory, you're shown:
- The auto-memory content
- Whether it's new or matches an existing memory
- A proposed action (create or merge)

You choose:
- **Accept:** Write the memory to `.claude/memory/` and update INDEX.md
- **Skip:** Ignore this auto-memory
- **Edit:** Modify before saving

### Step 5: Cleanup

After review, accepted memories are:
- Written to the appropriate subdirectory
- Added to INDEX.md (and optionally MEMORY.md for high-priority items)
- The auto-memory source files remain untouched (they're Claude Code's files)

## Usage

Basic sync:

```bash
claude-memory sync
```

This scans for auto-memories and walks you through each one interactively.

## What Gets Synced

Auto-memories typically contain:
- User preferences Claude learned during a session
- Project facts discovered while reading code
- Behavioral corrections you gave Claude
- Debugging insights and solutions

## What Doesn't Get Synced

Session sync is intentionally conservative:
- Ephemeral task details (what you were working on in that specific session)
- Duplicate information already in your memory system
- Low-value observations

## Tips

- Run sync after intensive work sessions where Claude learned a lot
- Don't sync after every session -- weekly or biweekly is usually enough
- Review proposed merges carefully; auto-memories can be noisy
- Use `claude-memory compact` afterward to clean up any redundancy
