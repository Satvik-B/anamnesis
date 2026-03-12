# Contributing

Thank you for your interest in contributing to claude-memory.

## Development Setup

### Prerequisites

- Python 3.9+
- git

### Clone and Install

```bash
git clone https://github.com/anthropics/claude-memory.git
cd claude-memory
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=claude_memory --cov-report=html
```

## Project Structure

```
claude-memory/
  src/claude_memory/      # Python package
    __init__.py           # Version
    cli.py                # CLI entry point
    init_cmd.py           # `claude-memory init` implementation
    sync_cmd.py           # `claude-memory sync` implementation
    compact_cmd.py        # `claude-memory compact` implementation
    platform.py           # OS detection utilities
  skeleton/               # Template files copied by `init`
    rules/
    memory/
    skills/
  tests/                  # Test suite
  docs/                   # Documentation
  examples/               # Example configurations
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feat/team-memory` for new features
- `fix/sync-duplicate-detection` for bug fixes
- `docs/faq-update` for documentation changes

### Code Style

- Follow PEP 8
- Use type hints for function signatures
- Keep functions focused and under 50 lines where practical
- Write docstrings for public functions

### Testing

- Write tests for new functionality
- Ensure existing tests pass before submitting
- Test on at least one platform (macOS, Linux, or Windows)
- Aim for test coverage on new code

### Commit Messages

Write clear, descriptive commit messages:

```
Add duplicate detection to sync command

The sync pipeline now checks for existing memories with similar
content before proposing a new memory file. This reduces noise
when running sync frequently.
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes with tests
4. Ensure `pytest` passes
5. Submit a pull request with a clear description

### Pull Request Guidelines

- Keep PRs focused on a single change
- Include a description of what and why
- Reference any related issues
- Update documentation if behavior changes
- Add a CHANGELOG entry for user-facing changes

## Areas for Contribution

### Good First Issues

Look for issues labeled `good-first-issue` on GitHub. These are typically:
- Documentation improvements
- Small bug fixes
- Test coverage improvements

### Feature Ideas

If you have an idea for a new feature, please open an issue first to discuss
the design before implementing. This helps ensure alignment and prevents
wasted effort.

### Documentation

Documentation improvements are always welcome:
- Fix typos or unclear explanations
- Add examples for common workflows
- Improve the FAQ based on real user questions

## Code of Conduct

Be kind, be respectful, be constructive. We're all here to make developer
tools better.

## License

By contributing to claude-memory, you agree that your contributions will be
licensed under the MIT License.
