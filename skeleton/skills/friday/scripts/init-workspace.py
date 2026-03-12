#!/usr/bin/env python3
"""Generate the friday workspace from ~/.claude-memory.yaml.

Reads config to determine enabled modules, then creates workspace files
at <repo-root>/friday/. Skips files that already exist unless --force is passed.

Usage:
    init-workspace.py [--force] [--keep-data]

Options:
    --force      Overwrite all files including CLAUDE.md
    --keep-data  Regenerate CLAUDE.md and references.md but keep data files
                 (active-tasks.md, sprints/, journal.md, etc.)
"""
import os
import sys
import yaml
from datetime import datetime, timedelta
from pathlib import Path

CONFIG_PATH = os.path.expanduser("~/.claude-memory.yaml")


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def module_enabled(cfg, name):
    return cfg.get("modules", {}).get(name, False)


def find_repo_root():
    """Find repository root. REPO_ROOT env var takes priority (for testing)."""
    env = os.environ.get("REPO_ROOT")
    if env:
        return Path(env)
    # Walk up from this script to find repo root (contains .git/)
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / ".git").exists():
            return parent
    print("ERROR: Cannot find repository root. Set REPO_ROOT env var.", file=sys.stderr)
    sys.exit(1)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def write_if_missing(path, content, force=False):
    """Write file only if it doesn't exist (or force=True)."""
    if os.path.exists(path) and not force:
        return False
    with open(path, "w") as f:
        f.write(content)
    return True


def git_exclude(root, entry="/friday/"):
    """Add entry to .git/info/exclude if not already present."""
    exclude = root / ".git" / "info" / "exclude"
    if exclude.exists():
        content = exclude.read_text()
        if entry not in content:
            with open(exclude, "a") as f:
                f.write(f"\n{entry}\n")
    else:
        ensure_dir(exclude.parent)
        exclude.write_text(f"{entry}\n")


# --- Template generators ---

def gen_claude_md(cfg):
    """Generate workspace CLAUDE.md based on enabled modules."""
    name = cfg.get("identity", {}).get("assistant_name", "Friday")
    lines = [f"# {name} — Personal Assistant Workspace\n"]

    # Directory structure
    lines.append("## Directory Structure\n")
    lines.append("```")
    lines.append("friday/")
    lines.append("  CLAUDE.md              # This file")
    if module_enabled(cfg, "sprint_tracking"):
        lines.append("  active-tasks.md        # Task dashboard (single source of truth)")
        lines.append("  quarter-items.md       # Quarter-level work items")
        lines.append("  sprints/               # Per-sprint log files")
        lines.append("    current-sprint.md    # Active sprint")
        lines.append("  archive/               # Completed tasks")
    lines.append("  references.md          # Links, queries, team info")
    if module_enabled(cfg, "daily_rituals"):
        lines.append("  routines.md            # Periodic tasks and checklists")
    if module_enabled(cfg, "calendar"):
        lines.append("  calendar.md            # Synced calendar events")
    if module_enabled(cfg, "github_reviews"):
        lines.append("  pr-reviews.md          # PR review backlog")
        lines.append("  people.md              # People directory")
    if module_enabled(cfg, "slack") and not module_enabled(cfg, "github_reviews"):
        lines.append("  people.md              # People directory")
    if module_enabled(cfg, "jira"):
        lines.append("  jiras/                 # JIRA ticket detail files")
    if module_enabled(cfg, "personal"):
        lines.append("  personal.md            # Personal life tracker")
    if module_enabled(cfg, "journal"):
        lines.append("  journal.md             # Personal journal")
    if module_enabled(cfg, "ideas"):
        lines.append("  ideas.md               # Idea bank")
    lines.append("```\n")

    # File relationships
    lines.append("## File Relationships\n")
    if module_enabled(cfg, "sprint_tracking"):
        lines.append("- **active-tasks.md**: Single source of truth for ALL task metadata.")
        lines.append("- **Sprint plan**: References active-tasks via links. Does NOT duplicate status/estimates.")
        lines.append("- **archive/**: Completed tasks moved here after sprint review.\n")

    # Operational rules
    lines.append("## Operational Rules\n")
    lines.append("1. **Read before write**: Re-read files before modifying to avoid clobbering.")
    lines.append("2. **Update on every interaction**: When user reports progress, update ALL relevant files.")
    lines.append("3. **Capture everything**: Slack links, ad hoc asks, meeting context — all logged.")
    if module_enabled(cfg, "sprint_tracking"):
        lines.append("4. **Honest efficiency reviews**: Flag over/under-estimates. Be constructive.")
        lines.append("5. **Manager-ready outputs**: Sprint review summaries should be copy-pasteable.")
    lines.append("6. **Cross-reference**: Link JIRAs to tasks, tasks to sprint entries.")
    lines.append("7. **Never delete context** without being asked.")
    lines.append("8. **Never make up progress** — only record what user reports.\n")

    # Module-specific sections — point to skill reference docs
    skill_dir = "<skill_dir>"  # Claude resolves this at runtime
    note = f"*Full procedures in the friday skill's reference docs.*\n"

    if module_enabled(cfg, "sprint_tracking"):
        lines.append("## Sprint System\n")
        lines.append(f"Read `{skill_dir}/references/sprint-system.md` for sprint lifecycle, templates, and rules.\n")

        lines.append("## Task Tracking\n")
        lines.append(f"Read `{skill_dir}/references/task-tracking.md` for task format and status values.\n")

    if module_enabled(cfg, "daily_rituals"):
        lines.append("## Daily Rituals\n")
        lines.append(f"Read `{skill_dir}/references/daily-rituals.md` for morning/evening check-in procedures.")
        lines.append("Steps are tagged with required modules — skip steps whose module is disabled.\n")

    if module_enabled(cfg, "calendar"):
        lines.append("## Calendar Integration\n")
        lines.append("Calendar events synced to `calendar.md` (via cron or morning check-in).")
        lines.append(f"Timezone: {cfg.get('calendar', {}).get('timezone', cfg.get('schedule', {}).get('timezone', 'UTC'))}\n")

    if module_enabled(cfg, "slack"):
        slack_id = cfg.get("slack", {}).get("user_id", "")
        lines.append("## Slack Integration\n")
        lines.append(f"Slack user ID: `{slack_id}`")
        lines.append("Search patterns in `references.md`.\n")

    if module_enabled(cfg, "jira"):
        components = cfg.get("jira", {}).get("components", [])
        lines.append("## JIRA Integration\n")
        lines.append(f"Components: {', '.join(components)}")
        lines.append("Saved JQL queries in `references.md`.\n")

    if module_enabled(cfg, "github_reviews"):
        gh_user = cfg.get("github_reviews", {}).get("github_username", "")
        lines.append("## GitHub PR Reviews\n")
        lines.append(f"GitHub username: `{gh_user}`")
        lines.append("PR review backlog tracked in `pr-reviews.md`.\n")

    if module_enabled(cfg, "personal"):
        lines.append("## Personal Tracking\n")
        lines.append("Personal life tracked in `personal.md`. NEVER mix into sprint plan.\n")

    if module_enabled(cfg, "journal"):
        lines.append("## Journal\n")
        lines.append("Freeform journal in `journal.md`. Record faithfully, no unsolicited advice.\n")

    if module_enabled(cfg, "ideas"):
        lines.append("## Ideas\n")
        lines.append("Idea bank in `ideas.md`. Tag with freeform labels.\n")

    return "\n".join(lines)


def gen_references_md(cfg):
    """Generate references.md with personalized queries."""
    lines = ["# References\n", f"*Generated {datetime.now().strftime('%Y-%m-%d')}*\n"]

    if module_enabled(cfg, "slack"):
        slack_id = cfg.get("slack", {}).get("user_id", "")
        slack_name = cfg.get("slack", {}).get("display_name", "")
        lines.append("## Slack Queries\n")
        lines.append(f"- Messages sent: `from:@{slack_name}`")
        lines.append(f"- Messages tagged: `<@{slack_id}>`\n")

    if module_enabled(cfg, "jira"):
        components = cfg.get("jira", {}).get("components", [])
        comp_jql = " OR ".join([f'component = "{c}"' for c in components])
        lines.append("## JIRA Queries\n")
        lines.append(f"- Updated today: `({comp_jql}) AND updated >= -1d ORDER BY updated DESC`")
        lines.append(f"- Assigned to me: `assignee = currentUser() AND ({comp_jql}) AND status != Done ORDER BY priority`\n")

    if module_enabled(cfg, "github_reviews"):
        gh_user = cfg.get("github_reviews", {}).get("github_username", "")
        team = cfg.get("github_reviews", {}).get("team_members", [])
        lines.append("## GitHub Queries\n")
        lines.append(f"- Pending reviews: `gh pr list --repo <org>/<repo> --search 'review-requested:{gh_user}' --state open`")
        lines.append(f"- My open PRs: `gh pr list --repo <org>/<repo> --author {gh_user} --state open`")
        if team:
            lines.append(f"\n### Team Members (for PR priority scoring)")
            for t in team:
                lines.append(f"- {t}")
        lines.append("")

    # Release timeline placeholder
    lines.append("## Release Timeline\n")
    lines.append("| Release | Feature Cut | Code Complete | GA |")
    lines.append("|---------|-----------|--------------|-----|")
    lines.append("| (add release info here) | | | |\n")

    return "\n".join(lines)


def gen_routines_md(cfg):
    """Generate routines.md based on enabled modules."""
    lines = ["# Periodic Routines & Recurring Tasks\n"]
    lines.append(f"*Generated {datetime.now().strftime('%Y-%m-%d')}*\n")
    lines.append("---\n")

    lines.append("## Weekly\n")
    lines.append("| Day | Task | Tag | Notes |")
    lines.append("|-----|------|-----|-------|")

    if module_enabled(cfg, "sprint_tracking"):
        lines.append("| Monday | Sprint kickoff — review planned work, set daily priorities | `#work` | Start of sprint week |")
    if module_enabled(cfg, "personal"):
        gym_days = cfg.get("personal", {}).get("gym_days", [])
        for day in gym_days:
            lines.append(f"| {day} | Gym | `#health` | |")
    if module_enabled(cfg, "sprint_tracking"):
        lines.append("| Friday | **Send manager summary** (sprint progress update) | `#work` | Compile from sprint daily log |")
    lines.append("")

    if module_enabled(cfg, "sprint_tracking"):
        lines.append("## Biweekly (Sprint Cadence)\n")
        lines.append("| When | Task | Tag | Notes |")
        lines.append("|------|------|-----|-------|")
        lines.append("| Sprint start (Monday) | Create new sprint file, carry over incomplete tasks | `#work` | |")
        lines.append("| Sprint start (Monday) | Review backlog — move DONE tasks to archive | `#work` | |")
        lines.append("| Sprint end (Friday) | Fill out Sprint Review | `#work` | |")
        lines.append("| Sprint end (Friday) | Write Manager-Ready Summary | `#work` | |")
        lines.append("| Sprint end (Friday) | Tag carried-over items, prep next sprint | `#work` | |")
        lines.append("")

    lines.append("## Monthly\n")
    lines.append("| When | Task | Tag | Notes |")
    lines.append("|------|------|-----|-------|")
    if module_enabled(cfg, "sprint_tracking"):
        lines.append("| 1st of month | Review quarter-items.md | `#work` | Are we on track? |")
    if module_enabled(cfg, "personal"):
        lines.append("| 1st of month | Review personal.md progress | `#personal` | |")
    lines.append("")

    # End-of-day questions reference
    if module_enabled(cfg, "daily_rituals"):
        lines.append("---\n")
        lines.append("## End-of-Day Review Questions\n")
        lines.append("*See friday skill's `references/end-of-day-questions.md` for the full Q&A template.*\n")

    # Friday checklist
    if module_enabled(cfg, "sprint_tracking"):
        lines.append("---\n")
        lines.append("## Checklist: Friday Routine\n")
        lines.append("- [ ] Update sprint daily log")
        lines.append("- [ ] Compile manager summary from the week's daily log entries")
        lines.append("- [ ] Send manager summary")
        lines.append("- [ ] Review next week's priorities\n")

    return "\n".join(lines)


def gen_active_tasks_md():
    return """# Active Tasks

*Single source of truth for all task metadata. Sprint plans reference tasks by link only.*

<!-- Add tasks using the format from references/task-tracking.md -->
"""


def gen_quarter_items_md():
    return f"""# Quarter Items

*Last updated: {datetime.now().strftime('%Y-%m-%d')}*

<!-- Add quarter-level work items and priorities here -->
"""


def gen_sprint_file(cfg):
    """Generate initial sprint file."""
    length = cfg.get("schedule", {}).get("sprint_length_weeks", 2)
    today = datetime.now()
    # Find nearest past Monday
    days_since_monday = today.weekday()
    start = today - timedelta(days=days_since_monday)
    end = start + timedelta(weeks=length) - timedelta(days=1)
    # Skip weekends for end date
    if end.weekday() >= 5:
        end -= timedelta(days=end.weekday() - 4)

    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    return f"""# Sprint: {start_str} to {end_str}

## Sprint Meta
- **Working Days**: (calculate based on calendar)
- **Vacation/OOO**: None

## Sprint Goals
1. (set goals)

## Sprint Tasks

*All task details live in [active-tasks.md](../active-tasks.md).*

### Standing Commitments
- **Code Reviews**: ~1d across sprint
- **Ad hoc tasks**: Buffer ~1d

### Capacity Note
- **Available**: TBD working days
- **Standing commitments**: ~2d
- **Effective capacity**: TBD

## Dependencies Summary

| Task | Dependency | Status |
|------|-----------|--------|

## Risks & Blockers

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|

## Ad Hoc / Unplanned Work

| # | Task | Source | Effort | Date | Notes |
|---|------|--------|--------|------|-------|

## Daily Log

### {today.strftime('%Y-%m-%d')} (Day 1)
- Friday workspace initialized
""", start_str


def gen_personal_md(cfg):
    gym_days = cfg.get("personal", {}).get("gym_days", [])
    lines = ["# Personal Tracker\n"]
    lines.append(f"*Generated {datetime.now().strftime('%Y-%m-%d')}*\n")

    if gym_days:
        lines.append("## Weekly Schedule\n")
        lines.append("| Day | WFH/Office | Gym |")
        lines.append("|-----|-----------|-----|")
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        wfh = cfg.get("schedule", {}).get("wfh_days", [])
        office = cfg.get("schedule", {}).get("office_days", [])
        for d in day_names:
            loc = "WFH" if d in wfh else ("Office" if d in office else "—")
            gym = "Yes" if d in gym_days else "—"
            lines.append(f"| {d} | {loc} | {gym} |")
        lines.append("")

        lines.append("### Gym Routine\n")
        cols = ["Week"] + [d[:3] for d in gym_days] + ["Total"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        lines.append("")

    lines.append("## Shopping / Errands\n")
    lines.append("- (add items here)\n")

    return "\n".join(lines)


def gen_simple_file(title, description=""):
    content = f"# {title}\n\n"
    if description:
        content += f"{description}\n\n"
    content += f"*Created {datetime.now().strftime('%Y-%m-%d')}*\n"
    return content


def main():
    force = "--force" in sys.argv
    keep_data = "--keep-data" in sys.argv

    if not os.path.exists(CONFIG_PATH):
        print(f"ERROR: Config not found at {CONFIG_PATH}", file=sys.stderr)
        print("Run /friday setup first.", file=sys.stderr)
        sys.exit(1)

    cfg = load_config()
    root = find_repo_root()
    workspace = root / "friday"
    ensure_dir(workspace)

    # Always regenerate CLAUDE.md and references.md
    claude_md = gen_claude_md(cfg)
    # Replace <skill_dir> placeholder with actual path
    skill_dir = Path(__file__).resolve().parent.parent
    claude_md = claude_md.replace("<skill_dir>", str(skill_dir))
    write_if_missing(workspace / "CLAUDE.md", claude_md, force=True)
    print(f"  CLAUDE.md: written ({len(claude_md)} chars)")

    refs = gen_references_md(cfg)
    write_if_missing(workspace / "references.md", refs, force=(force or keep_data))
    print(f"  references.md: written")

    # Sprint tracking files
    if module_enabled(cfg, "sprint_tracking"):
        if write_if_missing(workspace / "active-tasks.md", gen_active_tasks_md(), force=force):
            print("  active-tasks.md: created")
        if write_if_missing(workspace / "quarter-items.md", gen_quarter_items_md(), force=force):
            print("  quarter-items.md: created")
        ensure_dir(workspace / "sprints")
        ensure_dir(workspace / "archive")
        sprint_content, start_str = gen_sprint_file(cfg)
        sprint_file = workspace / "sprints" / f"{start_str}.md"
        if write_if_missing(sprint_file, sprint_content, force=force):
            print(f"  sprints/{start_str}.md: created")
        # current-sprint.md points to latest sprint
        current = workspace / "sprints" / "current-sprint.md"
        write_if_missing(current, f"<!-- Current sprint: {start_str} -->\n", force=True)
        print(f"  sprints/current-sprint.md: updated")

    # Daily rituals
    if module_enabled(cfg, "daily_rituals"):
        routines = gen_routines_md(cfg)
        if write_if_missing(workspace / "routines.md", routines, force=(force or keep_data)):
            print("  routines.md: written")

    # Calendar
    if module_enabled(cfg, "calendar"):
        if write_if_missing(workspace / "calendar.md", gen_simple_file("Calendar", "Synced via cron or morning check-in."), force=force):
            print("  calendar.md: created")

    # GitHub reviews
    if module_enabled(cfg, "github_reviews"):
        if write_if_missing(workspace / "pr-reviews.md", gen_simple_file("PR Review Backlog", "Refreshed every morning, auto-updated every evening."), force=force):
            print("  pr-reviews.md: created")

    # People directory (github_reviews or slack)
    if module_enabled(cfg, "github_reviews") or module_enabled(cfg, "slack"):
        if write_if_missing(workspace / "people.md", gen_simple_file("People Directory", "People you work with, their roles, and context."), force=force):
            print("  people.md: created")

    # JIRA
    if module_enabled(cfg, "jira"):
        ensure_dir(workspace / "jiras")
        print("  jiras/: created")

    # Personal
    if module_enabled(cfg, "personal"):
        personal = gen_personal_md(cfg)
        if write_if_missing(workspace / "personal.md", personal, force=force):
            print("  personal.md: created")

    # Journal
    if module_enabled(cfg, "journal"):
        if write_if_missing(workspace / "journal.md", gen_simple_file("Journal"), force=force):
            print("  journal.md: created")

    # Ideas
    if module_enabled(cfg, "ideas"):
        if write_if_missing(workspace / "ideas.md", gen_simple_file("Ideas"), force=force):
            print("  ideas.md: created")

    # Git exclude
    git_exclude(root)
    print("  .git/info/exclude: friday/ added")

    print(f"\nWorkspace ready at {workspace}")


if __name__ == "__main__":
    main()
