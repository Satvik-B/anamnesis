# Frequently Asked Questions

## General

### What is claude-memory?

A tool that gives Claude Code persistent, file-based memory across sessions.
Instead of starting from zero every time, Claude remembers who you are, what
you're working on, and what corrections you've given it.

### Does this send my data anywhere?

No. Everything stays in local Markdown files in your project directory. There
are no API calls, no cloud storage, no telemetry, no analytics. Your memories
never leave your machine (unless you git push them).

### What languages/frameworks does this work with?

All of them. claude-memory is language-agnostic. It works with any project
that uses Claude Code, regardless of tech stack.

### Do I need to pay for anything?

No. claude-memory is free and open source under the MIT license. You do need
a Claude Code subscription, but that's separate.

## Setup

### What does `claude-memory init` actually do?

It creates a `.claude/` directory in your project with:
- A rule file that teaches Claude how to use the memory system
- An empty memory structure (MEMORY.md, INDEX.md, subdirectories)
- Optional skills (like the Friday check-in)

It never modifies existing files. If `.claude/` already exists, it only adds
missing files.

### Can I use this alongside an existing `.claude/` directory?

Yes. `claude-memory init` is additive. It won't overwrite existing rule files
or settings. It creates only the memory-specific files that don't already exist.

### Does this work on Windows?

Yes. claude-memory detects your OS and uses the appropriate paths. The memory
files themselves are plain Markdown and work on any platform.

## Usage

### Will this slow down Claude Code?

No measurable impact. Claude Code already reads `.claude/rules/` files on
startup. The memory rule adds a few hundred tokens of instructions. Individual
memory files are only read when Claude determines they're relevant.

### What happens if MEMORY.md exceeds 200 lines?

Lines beyond 200 are silently truncated -- Claude never sees them. The memory
rule instructs Claude to consolidate aggressively and refuse to append when
near the limit. You can also run `claude-memory compact` to trim manually.

### How do I delete a memory?

Edit or delete the memory file directly. They're plain Markdown files. Then
remove the corresponding entry from INDEX.md (and MEMORY.md if it was in the
hot tier).

Alternatively, tell Claude: "Forget that I prefer tabs over spaces." Claude
will find and remove the relevant memory.

### Can Claude create memories automatically?

Yes, with your permission. The memory rule instructs Claude to:
- Offer to save new procedures after completing them successfully
- Ask before saving Slack conversation summaries
- Propose memory updates when it learns something new

You always have the final say on what gets saved.

### How often should I run `claude-memory sync`?

After intensive work sessions where Claude learned a lot about your project.
Weekly or biweekly is typical. You don't need to sync after every session --
most auto-memories are ephemeral and not worth curating.

### How often should I run `claude-memory compact`?

Monthly is a good cadence, or whenever you notice MEMORY.md or INDEX.md
getting long. Compaction deduplicates entries, flags oversized files, and
suggests archiving stale memories.

## Architecture

### Why plain Markdown instead of a database?

Simplicity, transparency, and portability:
- You can read and edit memories with any text editor
- Memories are diffable and version-controllable with git
- No database to set up, migrate, or back up
- No risk of data lock-in

### Why two tiers instead of one?

Claude's context window is finite. Loading all memories into every session
wastes tokens and dilutes attention. The two-tier design mirrors how human
memory works: a small working memory (hot tier) for constant-access facts,
and a larger long-term store (cold tier) for everything else.

### How is this different from RAG or vector stores?

claude-memory is deliberately simple:
- No embeddings or vector databases
- No retrieval pipelines or similarity search
- No infrastructure to maintain

The tradeoff: you curate memories manually instead of relying on automatic
retrieval. This is intentional -- human curation produces higher-quality
context than automated systems, especially for the kind of nuanced preferences
and corrections that matter most.

### Can I use this with other AI coding tools?

The memory files are plain Markdown and could theoretically be used with any
tool that reads project files. However, the rule file (`.claude/rules/memory-rule.md`)
is written specifically for Claude Code's conventions. Adapting it to other
tools would require rewriting the rule file for that tool's instruction format.
