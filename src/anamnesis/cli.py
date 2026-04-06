"""CLI entry point for anamnesis."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from anamnesis import __version__


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize anamnesis in the current (or specified) project."""
    from anamnesis.config import collect_config_interactive, save_config, load_config, CONFIG_PATH
    from anamnesis.installer import install, backup_claude_dir, cleanup_stale_backups
    from anamnesis.project import find_project_root

    project_dir = Path(args.project_dir) if args.project_dir else None
    auto = getattr(args, "auto", False)

    if project_dir is None:
        project_dir = find_project_root()
    if project_dir is None:
        print("Error: not inside a git repository. Use --project-dir or cd into a repo.", file=sys.stderr)
        return 1

    print(f"Initializing anamnesis in: {project_dir}")
    print()

    # Backup existing .claude/ directory
    backup_path = backup_claude_dir(project_dir)
    if backup_path:
        print(f"Backed up .claude/ to {backup_path.name}/")
        print()

    # Collect or load config
    if auto and CONFIG_PATH.exists():
        config = load_config()
        print(f"Using existing config from: {CONFIG_PATH}")
    else:
        config = collect_config_interactive()
        save_config(config)
        print(f"Config saved to: {CONFIG_PATH}")
    print()

    # Install skeleton files
    created = install(project_dir, config)
    if created:
        print(f"Created {len(created)} files:")
        for f in created:
            print(f"  .claude/{f}")
    else:
        print("All files already exist, nothing to create.")

    # Clean up backups older than 30 days
    removed = cleanup_stale_backups(project_dir)
    if removed:
        print(f"Cleaned up {len(removed)} stale backup(s) (>30 days old):")
        for r in removed:
            print(f"  {r.name}/")

    # Check for unprocessed sessions
    try:
        from anamnesis.sync import list_sessions
        sessions = list_sessions(project_dir)
        if sessions:
            print(f"Found {len(sessions)} past sessions. Run /anamnesis sync in Claude Code to extract memories.")
            print()
    except Exception:
        pass

    print("Done! Claude Code will pick up the new memory system on next conversation.")
    if auto:
        print("(Auto mode: interactive prompts were skipped)")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    """Update rule/skill files without touching user data."""
    from anamnesis.installer import update
    from anamnesis.project import find_project_root

    project_dir = Path(args.project_dir) if args.project_dir else None

    if project_dir is None:
        project_dir = find_project_root()
    if project_dir is None:
        print("Error: not inside a git repository. Use --project-dir or cd into a repo.", file=sys.stderr)
        return 1

    updated, skipped = update(project_dir)

    if updated:
        print(f"Updated {len(updated)} files:")
        for f in updated:
            print(f"  .claude/{f}")
    else:
        print("Nothing to update.")

    if skipped:
        print(f"Skipped {len(skipped)} user-data files (not overwritten):")
        for f in skipped:
            print(f"  .claude/{f}")

    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Check memory system health."""
    from anamnesis.project import find_project_root, get_auto_memory_dir
    from anamnesis.config import load_config, CONFIG_PATH

    project_dir = Path(args.project_dir) if args.project_dir else None

    if project_dir is None:
        project_dir = find_project_root()
    if project_dir is None:
        print("Error: not inside a git repository.", file=sys.stderr)
        return 1

    issues: list[str] = []
    warnings: list[str] = []
    ok: list[str] = []

    # Check config
    if CONFIG_PATH.exists():
        config = load_config()
        errors = config.validate()
        if errors:
            for err in errors:
                issues.append(f"Config: {err}")
        else:
            ok.append(f"Config: {CONFIG_PATH} is valid")
    else:
        warnings.append(f"Config: {CONFIG_PATH} not found (run 'anamnesis init')")

    # Check .claude directory
    claude_dir = project_dir / ".claude"
    if not claude_dir.exists():
        issues.append(f".claude/ directory not found in {project_dir}")
    else:
        ok.append(f".claude/ directory exists")

    # Check version file
    version_file = claude_dir / ".anamnesis-version"
    if version_file.exists():
        installed_version = version_file.read_text().strip()
        if installed_version != __version__:
            warnings.append(
                f"Installed version ({installed_version}) differs from "
                f"current ({__version__}). Run 'anamnesis update'."
            )
        else:
            ok.append(f"Version: {installed_version}")
    else:
        warnings.append("No version file found (run 'anamnesis init')")

    # Check memory directory and key files
    memory_dir = claude_dir / "memory"
    if memory_dir.exists():
        ok.append("memory/ directory exists")

        index_file = memory_dir / "INDEX.md"
        if index_file.exists():
            line_count = len(index_file.read_text().splitlines())
            if line_count > 150:
                warnings.append(f"INDEX.md has {line_count} lines (soft cap: 150)")
            else:
                ok.append(f"INDEX.md: {line_count} lines (under 150 cap)")
        else:
            warnings.append("INDEX.md not found in memory/")
    else:
        warnings.append("memory/ directory not found under .claude/")

    # Check auto-memory MEMORY.md
    try:
        auto_memory_dir = get_auto_memory_dir(project_dir)
        memory_md = auto_memory_dir / "MEMORY.md"
        if memory_md.exists():
            line_count = len(memory_md.read_text().splitlines())
            if line_count > 200:
                issues.append(f"MEMORY.md has {line_count} lines (hard cap: 200, content is being truncated!)")
            elif line_count > 150:
                warnings.append(f"MEMORY.md has {line_count} lines (approaching 200-line hard cap)")
            else:
                ok.append(f"MEMORY.md: {line_count} lines (under 200 cap)")
        else:
            warnings.append(f"Auto-memory MEMORY.md not found at {memory_md}")
    except FileNotFoundError:
        warnings.append("Could not determine auto-memory path")

    # Check rules directory
    rules_dir = claude_dir / "rules"
    if rules_dir.exists():
        rule_count = len(list(rules_dir.glob("*.md")))
        ok.append(f"rules/: {rule_count} rule files")
    else:
        warnings.append("rules/ directory not found under .claude/")

    # Check session sync status
    try:
        from anamnesis.sync import list_sessions, list_unprocessed
        all_sessions = list_sessions(project_dir)
        if all_sessions:
            unprocessed = list_unprocessed(project_dir, memory_dir)
            if unprocessed:
                warnings.append(f"{len(unprocessed)} unprocessed sessions (run /anamnesis sync)")
            else:
                ok.append(f"All {len(all_sessions)} sessions processed")
    except Exception:
        pass  # Session check is best-effort

    # Print results
    print(f"anamnesis doctor ({project_dir})")
    print("=" * 50)

    if ok:
        for msg in ok:
            print(f"  OK: {msg}")

    if warnings:
        print()
        for msg in warnings:
            print(f"  WARN: {msg}")

    if issues:
        print()
        for msg in issues:
            print(f"  ERROR: {msg}")

    print()
    total = len(ok) + len(warnings) + len(issues)
    print(f"{len(ok)}/{total} checks passed, {len(warnings)} warnings, {len(issues)} errors")

    return 1 if issues else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="anamnesis",
        description="Persistent, human-curated memory for Claude Code",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize anamnesis in a project")
    init_parser.add_argument("--project-dir", help="Project directory (default: auto-detect git root)")
    init_parser.add_argument("--auto", action="store_true", help="Skip interactive prompts during init")

    # update
    update_parser = subparsers.add_parser("update", help="Update rules/skills without touching user data")
    update_parser.add_argument("--project-dir", help="Project directory (default: auto-detect git root)")

    # doctor
    doctor_parser = subparsers.add_parser("doctor", help="Check memory system health")
    doctor_parser.add_argument("--project-dir", help="Project directory (default: auto-detect git root)")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "init": cmd_init,
        "update": cmd_update,
        "doctor": cmd_doctor,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
