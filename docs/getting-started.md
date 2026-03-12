# Getting Started

A step-by-step guide to setting up claude-memory in your project.

## Prerequisites

- Python 3.9 or later
- A project directory (any language -- claude-memory is language-agnostic)
- [Claude Code](https://claude.ai/code) installed and working

## Installation

```bash
pip install claude-memory
```

Verify the installation:

```bash
claude-memory --version
```

## Initialize Memory

Navigate to your project root and run:

```bash
cd your-project
claude-memory init
```

This creates the following structure:

```
your-project/
  .claude/
    rules/
      memory-rule.md      # Instructions for Claude Code
    memory/
      MEMORY.md           # Hot index (always loaded)
      INDEX.md            # Cold index (loaded on demand)
      archive/            # For retired memories
      slack/              # For Slack conversation summaries
    skills/
      friday/             # Weekly check-in skill (optional)
```

## Verify It Works

Start a Claude Code session in your project:

```bash
claude
```

Ask Claude: "What do you know about me?" or "Check your memory system."

Claude should acknowledge the memory system and note that it's empty. This
confirms the rule file is being loaded.

## Add Your First Memory

The easiest way to start is to tell Claude something about yourself:

> "Remember that I'm a backend engineer working primarily in Go. I prefer
> concise explanations and don't need basic concepts explained."

Claude will save this to MEMORY.md. You can verify by reading the file:

```bash
cat .claude/memory/MEMORY.md
```

## Understanding the Two Tiers

### Hot Tier: MEMORY.md

This file is loaded into **every** Claude Code session. It should contain:

- Your role and preferences
- Active behavioral corrections ("don't mock the database")
- Key repo facts referenced frequently

**Hard cap: 200 lines.** Keep it focused on what matters most.

### Cold Tier: INDEX.md

This is a catalog of all your memories. Claude reads it when it needs to look
something up -- like a table of contents for your knowledge base.

Each entry in INDEX.md points to a detailed memory file:

```
| File | Type | Tags | Description |
|------|------|------|-------------|
| tasks/deploy.md | task | deploy, staging | How to deploy to staging |
| knowledge/auth.md | knowledge | auth, oauth | OAuth flow quirks |
```

## Session Sync

Claude Code writes auto-memories to a platform-specific directory during
sessions. These are ephemeral notes that don't automatically become part of
your curated memory.

To merge them in:

```bash
claude-memory sync
```

This will:
1. Find auto-memories from recent sessions
2. Show you each one and ask whether to save it
3. Merge confirmed memories into your `.claude/memory/` system
4. Update INDEX.md accordingly

## Memory Hygiene

Over time, memories accumulate. Run compaction periodically:

```bash
claude-memory compact
```

This deduplicates entries, flags oversized files, and suggests archiving
stale memories.

## Git Integration

The `.claude/memory/` directory is designed to be committed to git:

```bash
git add .claude/
git commit -m "Initialize claude-memory system"
```

This means:
- Memory is versioned alongside your code
- Team members benefit from shared knowledge (when committed)
- You can review memory changes in PRs

## Next Steps

- Read [Concepts](concepts.md) to understand memory types and lifecycle
- Read [Session Sync Explained](session-sync-explained.md) for sync details
- Check [FAQ](faq.md) if you have questions
