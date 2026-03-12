# Session Sync Reference

Sync coding session activity into task tracking. Extracts signals from the current conversation, matches them to active tasks, and proposes updates.

**Trigger**: `/friday sync`, "sync session", "update tasks from session"

---

## Step 1: Extract session signals `[session_sync]`

Introspect the current conversation for work signals. Collect every signal into a structured list.

**Signal types:**

| Type | Source | Example |
|------|--------|---------|
| `file_edit` | Files edited or created via tools | `src/auth/handler.go` |
| `commit` | Git commits made during session | `abc123 "Add token refresh logic"` |
| `pr_mention` | PRs referenced, opened, or updated | `#1234`, `PR 5678` |
| `jira_mention` | JIRA IDs referenced or queried | `PROJ-1234` |
| `blocker` | Blockers hit or resolved | "dependency not installed" |
| `test_result` | Test/build outcomes | `go test ./src/auth/... PASSED` |
| `discussion` | Decisions made, questions answered | "decided to use JWT refresh tokens" |

**How to extract:**
- Scan tool calls: `Edit`, `Write`, `Read` (file paths), `Bash` (git commands, test runs)
- Scan conversation text: PR numbers, JIRA IDs, blocker mentions, decision language
- Deduplicate: multiple edits to the same file = one `file_edit` signal

**Output**: A flat list of `(type, value, detail)` tuples.

---

## Step 2: Match signals to tasks `[session_sync]` `[sprint_tracking]`

Read `active-tasks.md`. For each signal, attempt to match it against a task.

### Matching heuristics

| Signal type | Match strategy | Confidence |
|-------------|---------------|------------|
| `pr_mention` | PR number appears in task Breakdown | **HIGH** |
| `jira_mention` | JIRA ID matches task's JIRA field | **HIGH** |
| `commit` | Commit on task's Branch | **HIGH** |
| `file_edit` | File path shares prefix with task's known paths or Branch | **MEDIUM** |
| `blocker` | Keyword overlap with task Notes/Breakdown | **MEDIUM** |
| `test_result` | Test target relates to task's code area | **MEDIUM** |
| `discussion` | Fuzzy keyword match on task Summary | **LOW** |

### Good matching vs bad matching

**Good**: Signal `pr_mention #1234` matches task "Auth Service" because `#1234` appears in its Breakdown line. Confidence: HIGH.

**Bad**: Signal `file_edit src/auth/config.go` matches task "Auth Service" because path contains "auth". But user also has "OAuth Migration" and "API Gateway" touching auth code. Confidence: MEDIUM at best -- present both candidates.

**Rule**: When a signal matches multiple tasks at the same confidence level, list all candidates. Do not pick one silently.

---

## Step 3a: Load history per candidate task `[session_sync]` `[sprint_tracking]`

For each task that matched at MEDIUM or HIGH confidence:

1. **Memory context**: If task has a `Memory` field (e.g., `.claude/memory/contexts/auth-service.md`), read it
2. **Sprint daily log**: Read `sprints/current-sprint.md` (or dated file), scan for prior entries mentioning this task
3. **Current state**: Note the task's current Breakdown checkboxes, status, last-known blockers from both sources

This history is needed to write incremental, non-redundant updates in the next step.

---

## Step 3b: Synthesize updates from history + session signals `[session_sync]`

Combine what the session did (signals) with what was already known (history) to produce proposed updates.

### Rules for synthesizing

**Breakdown items** -- only check off items the session *actually progressed*, not just touched:
- Good: Session created PR #5678 -> check off "Implementation" if PR covers that sub-task
- Bad: Session read a file related to "E2E testing" -> do NOT check off "Final E2E testing"

**Notes** -- incremental, dated, referencing prior context:
- Good: `**Mar 12**: Continued auth service work. Addressed review comments on PR #1234. Pushed fixes for token validation and error handling feedback.`
- Bad: `Worked on auth service.` (too vague, no date, no specifics)

**Blocker resolution** -- if history shows blocker X, and session shows X was resolved:
- Propose status change (e.g., BLOCKED -> ACTIVE)
- Note the resolution: `Blocker resolved: found missing dependency in task memory`

**Status transitions** -- conservative, evidence-based only:

| Transition | Required evidence |
|------------|-------------------|
| BLOCKED -> ACTIVE | Clear signal that the blocker was addressed |
| ACTIVE -> REVIEW | PR was created or updated during session |
| NOT_STARTED -> ACTIVE | Work was started (commits, file edits) |
| * -> DONE | Do not propose -- user must confirm |

Do NOT change status without evidence. When in doubt, leave status unchanged and note the activity.

**New breakdown items**: If session revealed work not captured in the existing breakdown, propose adding it as a new line item.

**New blockers**: If session hit a new blocker (build failure, missing dependency, waiting on someone), propose adding to Notes.

---

## Step 4: Present proposed updates as a diff `[session_sync]`

Show the user a per-task summary of proposed changes. Group by confidence level.

### Format for HIGH/MEDIUM confidence matches

```
### <Task Name> [CURRENT_STATUS -> PROPOSED_STATUS]

**Confidence**: HIGH | MEDIUM
**Matched signals**: file_edit (3 files), commit (2), pr_mention (#1234)

**Breakdown changes**:
- [x] ~~[ ]~~ Address review comments / update diffs

**Notes to append**:
> **Mar 12**: Addressed reviewer feedback on PR #1234. Fixed token validation
> in handler.go, updated error wrapping per team convention.

**New items to add**:
- [ ] Fix lint warning in auth/middleware.go
```

### Format for LOW confidence matches

```
### Also possibly related:
- **API Gateway** — keyword "auth" in file path (LOW confidence)
  Signals: file_edit src/auth/config.go
  → Include? [y/n]
```

### User actions
- **Confirm all**: Apply all proposed updates
- **Reject individual items**: Remove specific changes before applying
- **Edit**: Modify proposed text before applying
- **Skip entirely**: Abort without changes

---

## Step 5: Write confirmed updates `[session_sync]` `[sprint_tracking]`

After user confirms, apply changes under the file lock (see **Concurrent Session Safety** below):

### 5a. Acquire the sync lock

Before writing ANY friday workspace file, acquire an exclusive lock.

**Platform-adaptive locking:**

On **macOS** (using `lockf`):
```bash
exec 9>friday/.sync.lock && lockf -s -t 30 9
```

On **Linux** (using `flock`):
```bash
exec 9>friday/.sync.lock && flock -w 30 9
```

- Opens the lock file on file descriptor 9
- Acquires an exclusive advisory lock with 30-second timeout
- Lock is held until fd 9 is explicitly closed

**If the lock times out** (exit code 75 on macOS / 1 on Linux): notify the user that another session is writing and suggest retrying in a few seconds. Do NOT proceed with writes.

### 5b. Read-then-write under lock

With the lock held, perform all writes:

1. **active-tasks.md**: Re-read, then update Breakdown checkboxes, Notes, Status, Last Updated date for each modified task
2. **Sprint daily log** (`sprints/current-sprint.md`): Re-read, then add today's entry with per-task progress summary
3. **Memory context file**: If task has a Memory field and the file exists, re-read, then append to its notes/status section
4. **Last Updated**: Set to today's date on every modified task

**Read-before-write**: Re-read each file immediately before editing to avoid clobbering changes made by other tools or sessions. The lock ensures no other Claude session is writing concurrently, but manual edits or other tools may have changed files since last read.

### 5c. Validate writes

After writing, re-read `active-tasks.md` and verify that:
- Modified tasks still have valid markdown structure (headers, checkboxes)
- No task sections were accidentally duplicated or truncated
- Last Updated dates were set correctly

### 5d. Release the sync lock

```bash
exec 9>&-
```

This closes fd 9, which releases the advisory lock. Other sessions waiting on the lock will now proceed.

---

## Step 5a: Compact Notes if needed `[session_sync]`

After writing updates in Step 5, check each modified task's Notes section. If it
contains **more than 10 dated entries**, run the compaction pass described below.

**Locking**: If the sync lock was released in Step 5d, re-acquire it before writing compaction changes. Release after compaction writes are done. Alternatively, delay the lock release in Step 5d until after compaction completes.

### Why compact

Notes sections are append-only journals. After many sessions they accumulate
redundant progress updates ("continued work on X", "addressed more comments")
that dilute the useful signal — decisions, blockers, dates, and milestones.
Compaction applies *tiered retention*: keep recent entries at full resolution,
summarize older entries into a digest, and archive raw detail to the task's
memory context file.

### Compaction rules

1. **Count dated entries.** A dated entry is any line or paragraph starting with
   a bold date marker (`**Mon DD**:` or `**YYYY-MM-DD**:`). Undated prose at the
   top of Notes (initial context) is never compacted — it stays as-is.

2. **If ≤ 10 dated entries, stop.** No compaction needed.

3. **If > 10 dated entries**, split into two groups:
   - **Recent window**: the 10 most recent dated entries — keep verbatim.
   - **Older entries**: everything before the recent window — compact into a
     **Prior activity** summary block.

4. **Build the Prior activity block.** Scan older entries and extract:

   | Always preserve (move to summary) | OK to compress |
   |-----------------------------------|----------------|
   | Decisions made and their rationale | "Continued work on X" |
   | Blockers encountered and how/when resolved | "Addressed review comments" |
   | Key dates (started, shipped, deployed, migrated) | "Pushed latest changes" |
   | Status transitions (BLOCKED→ACTIVE, etc.) | "Worked on Y today" |
   | External dependencies (waiting on person/team) | Incremental file-edit descriptions |
   | Milestone completions (PR merged, migration applied) | Repeated mentions of the same PR/branch |

   Format the block as:
   ```
   > **Prior activity (Feb 15 – Mar 2):**
   > - Feb 15: Started implementation. Decided on token-based auth strategy.
   > - Feb 28: Hit blocker — missing dependency. Resolved Mar 1 via task memory.
   > - Mar 1: DB migration M0156 applied on dev cluster (renumbered from M0155 due to collision).
   > - Mar 2: 3 PRs created (#1234-#1236). Entered REVIEW.
   ```

   Rules for the summary:
   - **One line per significant event**, not per original entry.
   - **Merge consecutive days** with the same activity into one line
     (e.g., three days of "addressed review comments" → one line).
   - **Preserve ALL dates** for decisions, blockers, and milestones.
   - **When in doubt, keep more.** A slightly long summary is better than lost context.

5. **Archive raw detail to memory context file.** If the task has a `Memory`
   field pointing to a context file (e.g., `.claude/memory/contexts/auth-service.md`):
   - Append a `## Session History (archived)` section (or append to it if it exists).
   - Copy the full text of the compacted older entries there, grouped by date.
   - This preserves the raw detail for deep-dive retrieval while keeping
     `active-tasks.md` lean.

   If the task has no Memory field, skip this step — the Prior activity block
   in Notes is the only record.

6. **Replace in active-tasks.md.** The Notes section becomes:
   ```
   ### Notes
   <undated initial context, unchanged>
   > **Prior activity (Feb 15 – Mar 2):**
   > - Feb 15: Started implementation. Decided on token-based auth strategy.
   > - Feb 28: Hit blocker — missing dependency. Resolved Mar 1.
   > - Mar 1: DB migration M0156 applied on dev cluster.
   > - Mar 2: 3 PRs created. Entered REVIEW.
   **Mar 3**: First round of review feedback received. ...
   **Mar 4**: ...
   ... (up to 10 recent dated entries)
   ```

### Good compaction vs bad compaction

**Good** — preserves decisions and dates, merges redundant updates:
```
> **Prior activity (Feb 15 – Mar 5):**
> - Feb 15: Started implementation. Chose token-based strategy over session cookies.
> - Feb 28: Blocked on missing dependency. Resolved Mar 1 via task memory runbook.
> - Mar 1: DB migration M0156 applied (renumbered from M0155 collision).
> - Mar 2: 3 PRs created (#1234-#1236).
> - Mar 3-5: Addressed review comments across PRs. Fixed token validation,
>   error wrapping, and refresh logic bug.
```

**Bad** — loses dates, drops decisions, too vague:
```
> **Prior activity:**
> Worked on auth service implementation and PRs. Had some blockers
> that were resolved. Did a DB migration. Addressed review comments.
```

**Bad** — no compression at all, just re-lists everything:
```
> **Prior activity (Feb 15 – Mar 5):**
> - Feb 15: Started work on auth service.
> - Feb 16: Continued work on auth service.
> - Feb 17: Continued work on auth service.
> - Feb 18: Made more progress on auth service.
> ... (20 lines that say essentially the same thing)
```

### When compaction runs

Compaction runs during:
- **Session sync** (this step, after Step 5 writes)
- **Evening check-in** (daily-rituals.md Step 5, after updating active-tasks.md)

It does NOT run during morning check-in (read-only) or sprint review (snapshot).

---

## Concurrent Session Safety

Multiple Claude Code sessions may run simultaneously (e.g., main session + background research agents). The friday workspace files — especially `active-tasks.md` and `sprints/current-sprint.md` — are shared mutable state. Without coordination, concurrent writes can clobber each other.

### Lock protocol

All write paths that modify friday workspace files **must** acquire an exclusive lock first.

**Lock file**: `friday/.sync.lock`

**Acquire** (file-descriptor form, holds lock across multiple tool calls):

On **macOS** (using `lockf(1)`, which wraps `flock(2)` advisory locking):
```bash
exec 9>friday/.sync.lock && lockf -s -t 30 9
```

On **Linux** (using `flock(1)`):
```bash
exec 9>friday/.sync.lock && flock -w 30 9
```

- Opens the lock file on file descriptor 9
- Acquires an exclusive advisory lock with 30-second timeout
- Lock is held until fd 9 is explicitly closed

**Check result**: If the lock command fails (exit code 75 on macOS, 1 on Linux), another session holds the lock.
- Notify user: "Another session is currently writing to friday workspace. Retrying in 5 seconds..."
- Retry once after 5 seconds. If still locked, ask user whether to wait or abort.

**Release** (after all writes are done):
```bash
exec 9>&-
```

### Why advisory locks and not a PID-based lock file

- **Auto-cleanup**: `flock(2)` advisory locks are released when the process exits, even on crash. No stale lock files to detect or clean up.
- **Atomic**: Lock acquisition is atomic at the kernel level. No race between checking and acquiring.
- **Timeout support**: Built-in timeout flag avoids indefinite blocking.
- **Cross-platform**: `lockf` ships with macOS; `flock` ships with Linux. Both wrap the same `flock(2)` syscall.

A PID-based approach (e.g., `shlock`) would require stale-lock detection (PID reuse, zombie processes) and manual cleanup. Advisory locks avoid all of this.

### Where locking is required

| Write path | File(s) modified | Lock required? |
|------------|-----------------|----------------|
| Session sync Step 5 | active-tasks.md, sprint log, memory contexts | **Yes** |
| Evening check-in Step 5 | active-tasks.md, sprint log, ad hoc table, pr-reviews, memory | **Yes** |
| Morning check-in | Read-only | No |
| Sprint planning | sprint file (new), active-tasks.md | **Yes** |
| Manual task edits | active-tasks.md | **Yes** (if via Friday skill) |

### Lock scope

The lock protects the **entire write transaction** — from the first re-read through the last write. This ensures:
1. No partial writes (e.g., active-tasks.md updated but sprint log not)
2. Re-reads under the lock see a consistent state
3. Other sessions' writes are fully visible before our re-read

Keep the lock held for as short as possible. Do all synthesis, user prompting, and confirmation **before** acquiring the lock. Only acquire it for the actual read-write-validate cycle.

### What the lock does NOT protect against

- Manual edits to files via text editor (advisory locks are invisible to editors)
- Git operations (checkout, merge, rebase) that modify friday/ files
- Claude sessions that don't follow this protocol (e.g., direct file edits outside the Friday skill)

For these cases, the existing **read-before-write** rule remains the safety net.

---

## Examples

### Full sync flow

Session context: User edited auth handler files, made 2 commits on `auth-feature-branch`, mentioned PR #1234, and hit a build failure in `go test ./src/auth/...`.

**Extracted signals:**
1. `file_edit` src/auth/handler.go
2. `file_edit` src/auth/handler_test.go
3. `commit` abc123 "Fix nil-check in auth handler"
4. `commit` def456 "Add token refresh tests"
5. `pr_mention` #1234
6. `test_result` `go test ./src/auth/...` FAILED

**Matched task**: Auth Service {#task-3} -- HIGH confidence (PR #1234 in Breakdown, commits on matching branch)

**History loaded**: Task is REVIEW status. Last note: "Two commits accidentally merged during rebase." Memory context shows 3 stacked PRs.

**Proposed update**:
- Status: REVIEW (unchanged -- PR update doesn't change review status)
- Check off: "Address review comments / update diffs"
- New blocker note: `Test failure in auth package -- needs investigation`
- Notes: `**Mar 12**: Fixed nil-check in auth handler, added token refresh tests. Test failure in auth package needs investigation before merge.`
