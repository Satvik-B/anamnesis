# Sprint System Reference

## Sprint Cadence

Sprints are **2-week cycles starting on Monday** (configurable via `schedule.sprint_start_day` and `schedule.sprint_length_weeks` in config). Each sprint gets its own file in `sprints/`.

## Sprint File Format: `sprints/YYYY-MM-DD.md`

```markdown
# Sprint: YYYY-MM-DD to YYYY-MM-DD

## Sprint Meta
- **Working Days**: X (total weekdays minus vacation/holidays)
- **Vacation/OOO**: <dates and reason, if any>

## Sprint Goals
1. <Goal 1 - outcome-focused, maps to quarter items>
2. <Goal 2>
3. <Goal 3>

## Sprint Tasks

*All task details (status, priority, estimate, actual, DoD, activities) live in [active-tasks.md](../active-tasks.md). This list defines which tasks belong to this sprint.*

- [#1 Task title](../active-tasks.md#task-1)
- [#2 Task title](../active-tasks.md#task-2)

*Mid-sprint additions are appended with a note (e.g., "added mid-sprint, manager ask 02/24").*

### Standing Commitments
- **Code Reviews**: ~1d across sprint (ongoing, tracked in ad hoc)
- **Ad hoc tasks**: Buffer ~1d across sprint (logged as they come)

### Capacity Note
- **Available**: X working days
- **Standing commitments**: ~2d (code reviews + ad hoc buffer)
- **Effective capacity**: ~Xd
- **Estimated planned total**: ~Xd

## Dependencies Summary

| Task | Dependency | Status |
|------|-----------|--------|
| #N | <what it depends on> | Open / Resolved |

## Risks & Blockers

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|

## Ad Hoc / Unplanned Work

| # | Task | Source | Effort | Date | Notes |
|---|------|--------|--------|------|-------|

## Daily Log

### YYYY-MM-DD (Day N)
- <What was worked on, progress made, blockers hit>
- <Ad hoc items that came up>

## Sprint Review

### Delivery Summary

| Task | Planned Estimate | Actual Effort | Status | Notes |
|------|-----------------|---------------|--------|-------|

### Metrics
- **Planned tasks completed**: X / Y
- **Unplanned tasks handled**: Z
- **Estimate accuracy**: (total planned estimate vs total actual effort)
- **Effective working days**: X out of Y available
- **Carry-overs**: <tasks that spilled into next sprint>

### Efficiency Analysis
- What went well
- What could have been done better
- Time sinks and distractions
- Suggestions for next sprint

### Manager-Ready Summary
<2-4 bullet points suitable for sharing with managers — concise, outcome-focused>
```

## Sprint Rules

1. **Sprint boundaries**: A new sprint file is created on the Monday it begins. The previous sprint's review section is filled out.
2. **`current-sprint.md`**: Always points to the latest sprint. When a new sprint starts, replace the old one.
3. **Daily log**: Every time the user reports progress or context, append to that day's entry. If it's a new day, create a new day heading.
4. **Ad hoc capture**: When the user shares Slack links, meeting notes, or mentions unplanned work, log it in the "Ad Hoc / Unplanned Work" table AND in the daily log. If an ad hoc item has follow-ups, recurs, or exceeds ~0.25d — promote it to an active-task and add a sprint task reference.
5. **Estimate tracking**: All estimates and actuals live in `active-tasks.md`. Track actual effort as reported.
6. **Vacation/OOO**: Record in Sprint Meta and adjust working days. Factor into efficiency analysis.
7. **Carry-overs**: Tasks not completed get marked "CARRIED_OVER" in active-tasks and appear in the next sprint.
8. **Sprint review**: At sprint end, fill out Sprint Review with honest efficiency analysis.
9. **Sprint task list is append-only after freeze**: Once frozen via "Start and Finalize sprint plan", never remove items. New tasks can be added, but nothing removed.
10. **Single source of truth**: Sprint file NEVER duplicates status, priority, estimate, or actual from active-tasks. These fields live ONLY in `active-tasks.md`.

## Sprint <-> Active Tasks Invariant (STRICT)

Every sprint task reference MUST have a corresponding entry in `active-tasks.md`, and every active-task assigned to the current sprint MUST appear in the sprint task list. No orphans in either direction.

- When adding a new task: create the active-tasks entry FIRST, then add the sprint reference.
- Assert this invariant during morning check-in and sprint post-mortem.
- If violation found: fix immediately and flag to user.

## Sprint Lifecycle

### "Start and Finalize sprint plan"
1. Review the draft sprint plan together
2. Make any final adjustments
3. **Freeze the plan** — from this point, no removals, only additions
4. Mark the sprint as active

### "Sprint Post-mortem"
1. **Assert invariant** (MANDATORY, do FIRST)
2. Fill out Sprint Review completely:
   - Delivery Summary: every task with planned estimate vs actual
   - Metrics: completion rate, unplanned work, estimate accuracy
   - PR Review Metrics (if github_reviews enabled): total reviews, avg turnaround, stale count
   - Efficiency Analysis: honest assessment
   - Learnings: specific insights
   - Manager-Ready Summary: 2-4 bullets
3. Update `active-tasks.md`: status, actual effort, last updated dates
4. Move DONE tasks to `archive/`
5. Mark incomplete tasks as CARRIED_OVER
6. Update `quarter-items.md`
7. Capture ideas from daily logs into `ideas.md` (if ideas module enabled)
8. Prepare next sprint file with carry-overs
9. Compare against previous post-mortems for trends
