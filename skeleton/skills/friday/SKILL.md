---
name: friday
description: Personal assistant workspace for engineers — sprint tracking, daily rituals, calendar sync, PR review backlog, JIRA integration, session sync, and more. All features are opt-in modules. Use when the user says "/friday", "/friday setup", "/friday sync", "good morning" (triggers morning check-in if workspace exists), "end of day" (triggers evening check-in), "sync session", "update tasks from session", or asks about sprint planning, task tracking, or daily routines. Also triggers on "sprint post-mortem", "start and finalize sprint plan", or references to the friday workspace.
---

# Friday — Personal Assistant Skill

An engineer's personal assistant workspace. Tracks sprints, runs daily rituals, syncs calendars, manages PR review backlogs, and more. All features are opt-in modules configured during setup.

## Quick Reference

- **Config**: `~/.claude-memory.yaml`
- **Workspace**: `<repo-root>/friday/`
- **Modules**: sprint_tracking, daily_rituals, calendar, slack, jira, github_reviews, personal, statusline, journal, ideas, session_sync

## Setup Flow (`/friday setup`)

### Step 1: Check existing state

```python
# Check what already exists
config_exists = os.path.exists(os.path.expanduser("~/.claude-memory.yaml"))
workspace_exists = os.path.exists("<repo-root>/friday/")
```

If config exists, ask: "Config already exists. Update or keep?"
If workspace exists, ask: "Workspace exists with data. Reinitialize (keeps data files) or keep as-is?"

### Step 2: Collect identity

Use AskUserQuestion to collect:
1. **Name** (optional) — for sprint file headers
2. **Email** (required) — used in config
3. **Assistant name** (default: "Friday") — how the assistant refers to itself

### Step 3: Select feature modules

Use AskUserQuestion (multi-select) to let the user choose modules:

| Module | Description | Default |
|--------|-------------|---------|
| sprint_tracking | 2-week sprint cycles, task tracking, delivery metrics | ON |
| daily_rituals | Morning/evening check-in procedures (adapts to enabled modules) | ON |
| calendar | Google Calendar sync, meeting prep, time blocking | OFF |
| slack | Search sent/tagged Slack messages, surface action items | OFF |
| jira | JIRA issue tracking, JQL queries, sprint cross-reference | OFF |
| github_reviews | PR review backlog, LIFO priority queue, re-review detection | OFF |
| personal | Gym, errands, personal life tracker (separate from work) | OFF |
| statusline | Live 2-line display at bottom of Claude Code | OFF |
| journal | Freeform journal entries | OFF |
| ideas | Idea bank for loose thoughts | OFF |
| session_sync | Auto-infer task progress from current session context | OFF |

**Module dependencies**: `daily_rituals` requires `sprint_tracking`. `statusline` requires `sprint_tracking`. `session_sync` requires `sprint_tracking`. If a dependency is off, warn and auto-enable it.

### Step 4: Collect module-specific config

Only ask for modules the user enabled:

- **calendar**: Timezone (IANA, default UTC). Set up hourly cron? (y/n)
- **slack**: Slack user ID (required — tell user: "Open Slack → Profile → ... → Copy member ID")
- **jira**: JIRA components (comma-separated, e.g. "Backend, API Gateway")
- **github_reviews**: GitHub username (required). Team member usernames (optional, for priority scoring)
- **personal**: Gym days (multi-select Mon-Sun)
- **schedule**: WFH days, office days (optional, used by statusline + daily rituals)
- **work**: Team name, manager name (optional, for manager summaries)
- **session_sync**: No additional config needed. Note: session_sync uses memory context files from `.claude/memory/contexts/` — these should exist for active tasks for best results.

If **statusline** is enabled:
1. Ask which components (multi-select, all on by default): sprint_progress, next_meeting, active_task, oncall, release_countdown, git_branch, location, gym
2. Auto-disable components whose module dependency is off (next_meeting → calendar, gym → personal, active_task → sprint_tracking)
3. Ask for release_label (e.g. "v2.1 FC"), oncall_keywords, skip_events

### Step 5: Check MCP prerequisites

| Module | Required | Check |
|--------|----------|-------|
| calendar | google-calendar MCP OR cron-only | Try `mcp__google-calendar__list_events` |
| slack | slack MCP | Try `mcp__slack__search_messages` |
| jira | jira MCP | Try `mcp__jira__get_jira_issue_summary` |
| github_reviews | `gh` CLI or github MCP | Try `gh auth status` or `mcp__github__get_pull_request_info` |

If missing, warn: "(a) disable the module, or (b) set up via `/setup` first."

### Step 6: Write config

Write `~/.claude-memory.yaml` with all collected values. See `assets/claude-memory.conf.example.yaml` for full schema.

### Step 7: Generate workspace

Run: `python3 <skill_dir>/scripts/init-workspace.py`

The script reads `~/.claude-memory.yaml` and generates the workspace at `<repo-root>/friday/` with only files for enabled modules.

### Step 8: Calendar cron (if calendar + cron opted in)

```bash
# Install cron
(crontab -l 2>/dev/null; echo "0 * * * * <skill_dir>/scripts/calendar-sync.sh") | crontab -

# Verify OAuth token
test -f ~/.gcalendar-mcp-token.json || echo "WARNING: No OAuth token. Run google-calendar MCP setup first."

# Test fetch
python3 <skill_dir>/scripts/fetch-calendar.py /tmp/friday-cal-test.json --date $(date +%Y-%m-%d)
```

### Step 9: Statusline (if enabled)

1. Copy parameterized scripts to stable paths:
   - `<skill_dir>/scripts/statusline.sh` → `~/.claude/friday-statusline.sh`
   - `<skill_dir>/scripts/statusline-cache-update.sh` → `~/.claude/friday-statusline-cache-update.sh`
2. Read `~/.claude/settings.json` for existing statusline
3. If different statusline exists, ask: replace or skip
4. Update `~/.claude/settings.json`:
   ```json
   {"statusLine": {"type": "command", "command": "<home>/.claude/friday-statusline.sh", "padding": 1}}
   ```
5. Test: run cache updater, verify `/tmp/claude-statusline-cache.json`

### Step 10: Verify + summary

Test connectivity for each enabled module. Show summary:
```
Friday setup complete!
  Workspace: <repo-root>/friday/
  Config: ~/.claude-memory.yaml
  Modules: sprint_tracking, daily_rituals, calendar, jira
  Calendar cron: installed (hourly)
  Statusline: not enabled
  Say "good morning" to start your first morning check-in.
```

---

## Runtime Behavior

### Config Loading

On every interaction in the friday workspace, read `~/.claude-memory.yaml` to determine enabled modules. This drives which procedures to follow.

### Trigger Detection

| Trigger | Action |
|---------|--------|
| "good morning" / asks about day plan | Morning check-in → read `references/daily-rituals.md` |
| "end of day" / reports progress | Evening check-in → read `references/daily-rituals.md` |
| Sprint boundary (new sprint) | Read `references/sprint-system.md` |
| "sprint post-mortem" | Read `references/sprint-system.md` |
| Task updates | Read `references/task-tracking.md` |
| `/friday setup` | Run setup flow above |
| `/friday` (no args) | Show status: current sprint day, active task, next meeting |
| "/friday sync" / "sync session" / "update tasks from session" | Session sync → read `references/session-sync.md` |

### Module-Aware Procedures

The reference docs contain full procedures. When following them, **skip steps for disabled modules**. The morning check-in in `references/daily-rituals.md` lists each step with its required module — if that module is off in the user's config, skip the step entirely.

When `session_sync` is enabled, session sync is also invoked as Step 0 of the evening check-in — before logging progress, auto-infer task updates from the current session context. See `references/session-sync.md` for details.

### Validation (on every interaction)

1. Config file exists and is parseable
2. Workspace directory exists
3. If sprint_tracking: active sprint file exists and current date is within range
4. If calendar + statusline.next_meeting: warn if `calendar.md` missing or >24h old
5. If statusline enabled: warn if `~/.claude/settings.json` doesn't point to friday's statusline
