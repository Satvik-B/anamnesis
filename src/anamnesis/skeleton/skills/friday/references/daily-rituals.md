# Daily Rituals Reference

Each step below is tagged with its required module. **Skip steps whose module is disabled in the user's config.**

## Always Check Date/Time First

Before responding to ANY planner interaction, run `date` to get the current date and time. Never assume the date.

---

## Morning Check-in

When the user says good morning or asks about the day's plan:

### 1. Read workspace files `[sprint_tracking]`
Read `sprints/current-sprint.md` and `active-tasks.md`.

### 1a. Assert Sprint <-> Active Tasks invariant `[sprint_tracking]`
- Every task in sprint task list has matching entry in `active-tasks.md`
- Every active-task for current sprint appears in sprint task list
- Fix violations immediately and flag to user

### 2. Fetch calendar events `[calendar]`
Use `mcp__google-calendar__list_events` (primary calendar, today's date range). Update `calendar.md`.

### 3. Process Slack inbox `[slack]`
The Slack inbox fetcher runs every 15 min via launchd, writing raw messages to
`.claude/memory/slack/inbox/YYYY-MM-DD.jsonl`. Each line is a JSON message with
fields: id, ts, iso_time, user, text, channel_id, channel_name, permalink, direction.

**Classification step** (Claude does this during check-in):
1. Read today's inbox file: `.claude/memory/slack/inbox/<today>.jsonl`
2. Also search for any new messages via MCP (to catch what fetcher may have missed)
3. **CRITICAL: For any message that is part of a thread** (`thread_ts` is set),
   fetch the FULL thread via `mcp__slack__get_thread_replies` before classifying.
   A single message in isolation often looks like FYI, but the thread may contain
   an implicit ask, assignment, or follow-up directed at you. Classify based on
   the full thread context, not just the captured message.
4. Classify each message into:
   - :red_circle: **ACTION** — I need to do something (someone asked me, assigned me, etc.)
   - :yellow_circle: **COMMITMENT** — I promised to do something ("I'll look into it", "will review")
   - :blue_circle: **ASK** — Someone asked me a question that needs a reply
   - :white_circle: **FYI** — Informational, no action needed
   Watch for implicit asks: 3rd-person mentions like "Alice can help with this"
   or "Alice did this before" often mean someone wants you to do it again.
5. For ACTION/COMMITMENT/ASK items, include the Slack permalink
6. Update `.claude/memory/slack/action-items.md` with new items

### 3a. Link Slack to memory `[slack]`
If `.claude/memory/contexts/` has active project contexts:
- For each classified ACTION/COMMITMENT/ASK, check if it relates to an active project
- Ask user: "This about <topic> looks relevant to <project>. Save to memory?"
- If yes: save to `.claude/memory/slack/<project>-<date>-<slug>.md`
- Update project context's `slack_threads` list
- Track new channels in `.claude/memory/slack/README.md`

### 4. Query JIRA `[jira]`
Query for issues updated since last working day using saved JQL from `references.md`.

### 4a. Refresh PR review backlog `[github_reviews]`
```bash
# Pending review requests
gh pr list --repo <org>/<repo> --search "review-requested:<github_username>" --state open --json number,title,author,updatedAt,createdAt
# PRs user has reviewed (still open)
gh api search/issues -f q='is:pr is:open reviewed-by:<github_username> repo:<org>/<repo> sort:updated-desc' -f per_page=20
# User's own open PRs
gh pr list --repo <org>/<repo> --author <github_username> --state open --json number,title,updatedAt,reviewDecision
```
For each reviewed PR, check if author pushed commits after user's last review (= re-review needed).
Categorize: Re-review Needed, Pending First Review, Watching, My Open PRs.
Priority: team PRs first, then cross-team, then bulk-tagged. Sort LIFO within each category.
Write to `pr-reviews.md`.

### 5. Read personal + routines `[personal]` `[daily_rituals]`
Read `personal.md` and `routines.md`.

### 5a. Load working context from memory `[daily_rituals]`
Read `.claude/memory/INDEX.md` working context section.
If a project context was active yesterday, offer to reload it:
- "Yesterday you were working on <project>. Load that context?"
- If yes: read the context file to inform today's plan

### 6. Present day plan
Cover (only for enabled modules):
- **Calendar**: Today's meetings with times, prep needed, talking points `[calendar]`
- **PR Reviews Hour**: Top 3-5 PRs from backlog, re-reviews flagged `[github_reviews]`
- **Focus blocks**: Time blocks between meetings for deep work `[calendar]`
- **Work items**: Sprint tasks to focus on today `[sprint_tracking]`
- **Memory context**: Active project context + any saved Slack threads needing response `[daily_rituals]`
- **Personal items**: Gym, errands, deadlines `[personal]`
- **Routines**: Periodic tasks due today `[daily_rituals]`
- **Context**: WFH vs office day `[schedule config]`

### 7. Wait for feedback
User may reprioritize, defer items, or add new ones. Adjust accordingly.

---

## Evening Check-in

When user reports end-of-day updates:

### 0. Session sync (auto-infer progress) `[session_sync]`
Run the session sync procedure from `references/session-sync.md`.
This auto-detects what was worked on during the current session by introspecting:
- Files edited/created in this conversation
- Git commits made
- PRs and JIRAs mentioned
- Blockers encountered or resolved

Cross-reference detected signals against `active-tasks.md` and each task's memory
context file (`.claude/memory/contexts/<task>.md`), sprint daily log entries, and
git branch history.

Present inferred progress to the user: "Based on this session, here's what I think
you did — confirm or adjust?"

Use confirmed results to pre-populate answers for Step 3 (end-of-day questions),
reducing the number of questions the user needs to answer manually.

### 1. Gather full context (BEFORE asking questions)

Do all of these for enabled modules:
- **Fetch calendar events** for the day `[calendar]`
- **Fetch Slack messages sent** by user for the day `[slack]`
- **Fetch Slack messages tagging** user for the day `[slack]`
- **Read sprint plan + active-tasks** for context `[sprint_tracking]`
- **Query JIRA** for issues updated that day `[jira]`
- **Run GitHub diff** (AUTO, no input needed) `[github_reviews]`:
  - Read morning `pr-reviews.md` snapshot
  - Fetch fresh GitHub state: reviews submitted today, comments posted, PRs approved
  - Diff against morning snapshot
  - Auto-update `pr-reviews.md`
  - Auto-log code review effort in ad hoc table

### 2. Present day summary
Build and present from gathered data:
- Meetings attended `[calendar]`
- Channels and threads active in `[slack]`
- Requests/escalations received `[slack]`
- PRs reviewed today (auto-detected) `[github_reviews]`
- Planned sprint tasks for context `[sprint_tracking]`

### 3. Ask end-of-day questions
If session sync ran in Step 0, skip questions whose answers are already known
from the sync results. Only ask about items not covered by session inference.

Ask questions **one by one** from `references/end-of-day-questions.md`. Wait for answer before asking next. Skip questions for disabled modules.

### 4. Memory reflect `[daily_rituals]`
Run the memory reflection routine (inspired by Reflexion paper):
1. Ask: "Did you learn any new procedures today worth saving as a task memory?"
   - If yes → create `.claude/memory/tasks/<name>.md` and update INDEX.md
2. Ask: "Any mistakes or gotchas worth noting?"
   - If yes → append to `.claude/memory/reflections/mistakes.md`
3. If a project context is active, ask: "Update <project> context status?"
   - If yes → update the context file's status, next steps, and timeline
4. Check Slack memories saved today → confirm they're linked to correct projects
5. Update `.claude/memory/INDEX.md` working context with today's summary

### 5. Update files

**First, acquire the sync lock** (see session-sync.md "Concurrent Session Safety" for full protocol):

On **macOS**:
```bash
exec 9>friday/.sync.lock && lockf -s -t 30 9
```

On **Linux**:
```bash
exec 9>friday/.sync.lock && flock -w 30 9
```

If the lock fails, another session is writing — wait 5 seconds and retry once.

**With lock held**, re-read then update each file:
- **Sprint daily log**: from answers + auto-detected data `[sprint_tracking]`
- **active-tasks.md**: merge session sync updates (if run) with manually reported progress; check off activities, update status, update actual effort. **Run note compaction** (session-sync.md Step 5a) on any task whose Notes section exceeds 10 dated entries. `[session_sync]` `[sprint_tracking]`
- **Ad hoc table**: from unplanned work answers + auto-detected code reviews `[sprint_tracking]`
- **pr-reviews.md**: already updated in step 1 `[github_reviews]`
- **JIRA files**: if relevant context shared `[jira]`
- **personal.md**: gym, personal tasks `[personal]`
- **Risks & Blockers table**: from blocker answers `[sprint_tracking]`
- **Memory files**: already updated in step 4 `[daily_rituals]`

**Release the lock** after all writes complete:
```bash
exec 9>&-
```

---

## Backfilling Daily Logs

When backfilling retros for past days (missed evening check-ins), gather ALL data sources for each day before drafting:

1. Google Calendar events `[calendar]`
2. Slack sent messages `[slack]`
3. Slack tagged messages `[slack]`
4. GitHub activity `[github_reviews]`:
   ```bash
   gh search prs --repo <org>/<repo> --reviewed-by <username> --updated "YYYY-MM-DD..YYYY-MM-DD"
   gh search prs --repo <org>/<repo> --commenter <username> --updated "YYYY-MM-DD..YYYY-MM-DD"
   gh search prs --repo <org>/<repo> --author <username> --updated "YYYY-MM-DD..YYYY-MM-DD"
   ```
5. JIRA issues updated that day `[jira]`
6. Sprint plan + active-tasks context `[sprint_tracking]`

Present reconstructed day for review before writing.

---

## GitHub PR Review Backlog Management `[github_reviews]`

### Priority Scoring (within each category, sort LIFO after priority)
1. Team PRs (from `github_reviews.team_members` config)
2. Cross-team PRs tagged for current release
3. Cross-team PRs
4. Bulk-tagged / unfamiliar — suggest declining review

### Stale PR Alerts
If user reviewed a PR >5 business days ago and author hasn't pushed, flag in morning check-in. Suggest pinging author or dropping from watching list.

### Decline Suggestions
For bulk-tagged PRs outside team scope, suggest declining review to reduce noise.

---

## Calendar Integration `[calendar]`

### Sprint Planning
At sprint start, fetch all events for the sprint window. Estimate total meeting load per week. Factor into capacity note.

### Daily Planning
Fetch today's events. Update `calendar.md`. Suggest time-blocked schedule with focus blocks between meetings.

### Meeting Prep
For each meeting, suggest: talking points based on sprint context, related tasks, prior context. Flag if slides/doc review needed.

---

## JIRA Integration `[jira]`

### Morning Check-in
Query JIRA for issues updated since last check-in using saved JQL from `references.md`.

### Sprint Planning
At sprint start, query all assigned issues in relevant components. Cross-reference with sprint tasks.

### Sprint Review
Query issues resolved/updated during the sprint for delivery summary accuracy.

---

## Journal `[journal]`

When the user uses the assistant conversationally — venting, thinking aloud, reflecting — capture in `journal.md`:

```markdown
## YYYY-MM-DD

<Freeform entry. Capture tone and content faithfully.>
```

No judgment, no unsolicited advice in the journal itself.

---

## Ideas `[ideas]`

```markdown
## <Idea Title>
**Added**: <date>
**Tags**: #performance #api #tooling

<Description, context, links>
```
