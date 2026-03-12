# anamnesis

Persistent, human-curated memory for Claude Code.

[![PyPI version](https://img.shields.io/pypi/v/anamnesis)](https://pypi.org/project/anamnesis/)
[![CI](https://img.shields.io/github/actions/workflow/status/anthropics/anamnesis/ci.yml?branch=main&label=CI)](https://github.com/anthropics/anamnesis/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/anamnesis)](https://pypi.org/project/anamnesis/)

---

## The Problem

Claude Code is stateless. Every session starts from zero -- no memory of who you
are, what you're working on, what mistakes were made last time, or what
conventions your team follows.

This means:
- You repeat the same corrections ("don't mock the database", "use snake_case here")
- Context about ongoing projects is lost between sessions
- Lessons from debugging sessions evaporate
- New team members get no benefit from months of prior Claude interactions

## The Solution

**anamnesis** gives your Claude Code agent persistent, file-based memory
that survives across sessions. It's:

- **Human-curated** -- you control what gets remembered, not an opaque embedding store
- **File-based** -- plain Markdown files in your repo, versioned with git
- **Two-tier** -- hot memories load every session; cold memories load on demand
- **Transparent** -- read, edit, and delete memories with any text editor

## Quick Start (5 minutes)

```bash
pip install anamnesis
cd your-project
anamnesis init
```

That's it. `anamnesis init` creates a `.claude/` directory in your project with:

```
.claude/
  rules/
    memory-rule.md      # Instructions for Claude to use the memory system
  memory/
    MEMORY.md           # Hot index (auto-loaded every session, 200-line cap)
    INDEX.md            # Cold index (loaded on demand)
    archive/            # Archived memories
    slack/              # Slack conversation summaries (optional)
```

Claude Code automatically reads `.claude/rules/` files, so memory works
immediately -- no configuration needed.

## How It Works

```
                    Session Start
                         |
                         v
               +-------------------+
               |  MEMORY.md (hot)  |   <-- Always loaded (200-line cap)
               |  - User profile   |       Identity, preferences, active
               |  - Feedback       |       corrections, key repo facts
               |  - Key facts      |
               +--------+----------+
                        |
                        | references
                        v
               +-------------------+
               |  INDEX.md (cold)  |   <-- Loaded on demand
               |  - Tasks          |       Procedures, knowledge articles,
               |  - Knowledge      |       project contexts, reflections
               |  - Contexts       |
               |  - Reflections    |
               +--------+----------+
                        |
                        | links to
                        v
               +-------------------+
               |  Memory files     |   <-- Individual .md files
               |  tasks/           |       Detailed content, runbooks,
               |  knowledge/       |       research notes, context docs
               |  contexts/        |
               |  reflections/     |
               +-------------------+
```

**Hot tier (MEMORY.md):** Loaded into every conversation. Contains your
identity, behavioral corrections, and high-frequency facts. Hard cap of 200
lines -- anything beyond is silently truncated.

**Cold tier (INDEX.md):** A catalog of all memories. Claude reads this when it
needs to look up a procedure, recall project context, or find domain knowledge.
Individual memory files are read on demand.

## Features

- **Two-tier memory** -- hot index for always-on context, cold index for deep knowledge
- **Session sync** -- `anamnesis sync` merges auto-memories into your curated system
- **Note compaction** -- `anamnesis compact` deduplicates and consolidates memories
- **Sprint tracking** -- optional Friday morning check-in skill surfaces what matters
- **Human-curated** -- memories are plain Markdown; edit them with any tool
- **Git-friendly** -- memory files live in your repo and version naturally

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Detailed setup walkthrough |
| [Concepts](docs/concepts.md) | Memory types, tiers, and lifecycle |
| [Session Sync](docs/session-sync-explained.md) | How session sync works |
| [Architecture](ARCHITECTURE.md) | System design for contributors |
| [FAQ](docs/faq.md) | Common questions answered |
| [Team Usage](docs/team-usage.md) | Using memory across a team (v1.1) |

## FAQ

**Q: Does this send my data anywhere?**
No. Everything stays in local Markdown files in your repo. There are no API
calls, no cloud storage, no telemetry.

**Q: Will this slow down Claude Code?**
No. Claude Code already reads `.claude/rules/` files on startup. The memory
rule file adds a few hundred tokens of instructions. Individual memory files
are only read when relevant.

**Q: Can I use this with a team?**
The memory system is per-project today. Team-shared memory (shared conventions,
onboarding context) is planned for v1.1. For now, commit your `.claude/memory/`
directory and team members benefit from shared knowledge.

**Q: What if MEMORY.md gets too long?**
The 200-line hard cap is enforced by Claude's context window. The memory rule
instructs Claude to consolidate aggressively. You can also run
`anamnesis compact` to automatically deduplicate and trim.

**Q: How is this different from RAG or vector stores?**
anamnesis is deliberately simple: plain text files, human-readable, human-editable.
No embeddings, no databases, no retrieval pipelines. You see exactly what Claude
remembers and can change it with a text editor.

## Contributing

See [docs/contributing.md](docs/contributing.md) for development setup and guidelines.

## License

[MIT](LICENSE)
