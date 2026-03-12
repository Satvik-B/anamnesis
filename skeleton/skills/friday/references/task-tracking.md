# Task Tracking Reference

## active-tasks.md Format

The central dashboard for all in-flight work, independent of sprints.

```markdown
## <Short Title> [STATUS] {#task-N}

- **JIRA**: <JIRA-ID> (link if available)
- **Sprint**: <sprint start date>
- **Priority**: P0 / P1 / P2 / P3
- **Branch**: <branch name, if any>
- **Estimate**: <original estimate>
- **Actual**: <actual effort so far>
- **Started**: <date>
- **Last Updated**: <date>

### Summary
One-liner on what this task is about.

### Breakdown
- [x] Sub-task 1 (completed)
- [ ] Sub-task 2 (in progress)
- [ ] Sub-task 3 (pending)

### Notes
Freeform notes, blockers, decisions, links.
Dated entries use bold date prefix: `**Mar 12**: ...`
When Notes exceeds 10 dated entries, older entries are compacted
into a `> **Prior activity (date range):**` summary block.
See `session-sync.md` Step 5a for compaction rules.
```

## STATUS Values

| Status | Meaning |
|--------|---------|
| `ACTIVE` | Currently being worked on |
| `BLOCKED` | Waiting on something external |
| `REVIEW` | In code review / waiting for feedback |
| `DONE` | Completed |
| `PAUSED` | Temporarily set aside |
| `NOT_STARTED` | Planned but not yet started |
| `CARRIED_OVER` | Spilled from previous sprint |

When a task reaches `DONE`, move it to `archive/` after a session or two.

## JIRA Files (jiras/<JIRA-ID>.md)

Created when user shares a JIRA link or ID. Use JIRA MCP tools to pull details.

```markdown
# <JIRA-ID>: <Title>

- **Type**: Bug / Task / Story / Epic
- **Priority**: P0-P3
- **Component**: <component name>
- **Assignee**: <name>
- **Status**: <JIRA status>
- **Created**: <date>
- **Link**: <URL>

## Description
<JIRA description, summarized or copied>

## Acceptance Criteria
<if available>

## Technical Notes
<Analysis, relevant code paths, architecture notes>

## Related Files
- `src/<service>/...`

## History
- <date>: Created from JIRA link
- <date>: <update notes>
```

## Operational Rules

1. **Read before write**: Always re-read files before modifying to avoid clobbering recent changes.
2. **Update on every interaction**: When user reports progress, updates, blockers — update ALL relevant files (active-tasks, sprint daily log, jira file if applicable).
3. **Capture everything**: Slack links, rough context, ad hoc asks, meeting mentions — all go into the sprint log.
4. **Honest efficiency reviews**: Flag over-estimates, under-estimates, context switching, scope creep. Be constructive.
5. **Manager-ready outputs**: Sprint review summaries should be copy-pasteable for status emails.
6. **Cross-reference**: Link JIRAs to tasks, tasks to sprint entries. Keep things connected.
