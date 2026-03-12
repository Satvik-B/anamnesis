---
type: knowledge
tags: [testing, conventions]
created: 2026-01-20
last_accessed: 2026-03-01
access_count: 5
importance: high
source: manual
---

# Testing Conventions

## Quick Reference
Use pytest with fixtures from conftest.py. All tests should use tmp_path.

## Content
- Tests live in `tests/` at the project root
- Use `pytest.skip()` for modules not yet implemented
- Fixture files go in `tests/fixtures/`
- Memory file fixtures must have valid frontmatter

## Gotchas
- Always use `yaml.safe_load()`, never `yaml.load()`
- Mock platform detection when testing cross-platform behavior
