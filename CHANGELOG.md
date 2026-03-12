# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-12

### Added

- `anamnesis init` command to scaffold the memory system in any project
- Two-tier memory architecture (hot MEMORY.md / cold INDEX.md)
- `anamnesis sync` to merge Claude Code auto-memories into the curated system
- `anamnesis compact` to deduplicate and consolidate memories
- Memory rule file that teaches Claude Code how to use the memory system
- Skeleton directory with memory structure, archive, and Slack integration
- Friday morning check-in skill for weekly context review
- Platform detection for macOS, Linux, and Windows
- Memory file format with YAML frontmatter and structured sections
- Truncation guards to prevent silent data loss at the 200-line MEMORY.md cap
- Archive system for retired memories (never delete, always mark done)

[1.0.0]: https://github.com/anthropics/anamnesis/releases/tag/v1.0.0
