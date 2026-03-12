#!/bin/bash
# Friday Statusline Cache Updater
# Reads workspace files + config to build cache JSON.
# Called by statusline.sh when cache is stale (>5 min).

CONFIG_FILE="$HOME/.anamnesis.yaml"
CACHE_FILE="/tmp/claude-statusline-cache.json"

# --- Find repository root ---
find_repo_root() {
    if [ -n "${REPO_ROOT:-}" ]; then
        echo "$REPO_ROOT"
        return
    fi
    local dir
    dir="$(cd "$(dirname "$0")" && pwd)"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.git" ]; then
            echo "$dir"
            return
        fi
        dir="$(dirname "$dir")"
    done
    echo ""
}

REPO_ROOT="$(find_repo_root)"
PLANNER_DIR="${REPO_ROOT:+$REPO_ROOT/friday}"

# --- Read config helpers ---
read_config_list() {
    local key="$1"
    if [ -f "$CONFIG_FILE" ]; then
        python3 -c "
import yaml
with open('$CONFIG_FILE') as f:
    cfg = yaml.safe_load(f) or {}
keys = '$key'.split('.')
v = cfg
for k in keys:
    v = v.get(k, {}) if isinstance(v, dict) else {}
if isinstance(v, list):
    print(' '.join(str(x) for x in v))
" 2>/dev/null
    fi
}

read_config_str() {
    local key="$1" default="$2"
    if [ -f "$CONFIG_FILE" ]; then
        python3 -c "
import yaml
with open('$CONFIG_FILE') as f:
    cfg = yaml.safe_load(f) or {}
keys = '$key'.split('.')
v = cfg
for k in keys:
    v = v.get(k, {}) if isinstance(v, dict) else {}
print(v if isinstance(v, str) else '$default')
" 2>/dev/null || echo "$default"
    else
        echo "$default"
    fi
}

# --- Sprint Info ---
SPRINT_DAY=0
SPRINT_TOTAL_DAYS=0

if [ -n "$PLANNER_DIR" ] && [ -f "$PLANNER_DIR/sprints/current-sprint.md" ]; then
    SPRINT_REF=$(grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' "$PLANNER_DIR/sprints/current-sprint.md" 2>/dev/null | head -1)
    SPRINT_FILE=""
    if [ -n "$SPRINT_REF" ] && [ -f "$PLANNER_DIR/sprints/${SPRINT_REF}.md" ]; then
        SPRINT_FILE="$PLANNER_DIR/sprints/${SPRINT_REF}.md"
    fi

    if [ -n "$SPRINT_FILE" ]; then
        SPRINT_LINE=$(head -1 "$SPRINT_FILE")
        SPRINT_START=$(echo "$SPRINT_LINE" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)
        SPRINT_END=$(echo "$SPRINT_LINE" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | tail -1)

        if [ -n "$SPRINT_START" ] && [ -n "$SPRINT_END" ]; then
            TODAY=$(date +%Y-%m-%d)
            if [ "$(uname)" = "Darwin" ]; then
                START_SEC=$(date -j -f "%Y-%m-%d" "$SPRINT_START" +%s 2>/dev/null)
                END_SEC=$(date -j -f "%Y-%m-%d" "$SPRINT_END" +%s 2>/dev/null)
                TODAY_SEC=$(date -j -f "%Y-%m-%d" "$TODAY" +%s 2>/dev/null)
            else
                START_SEC=$(date -d "$SPRINT_START" +%s 2>/dev/null)
                END_SEC=$(date -d "$SPRINT_END" +%s 2>/dev/null)
                TODAY_SEC=$(date -d "$TODAY" +%s 2>/dev/null)
            fi

            if [ -n "$START_SEC" ] && [ -n "$TODAY_SEC" ]; then
                SPRINT_DAY=0
                CHECK_SEC=$START_SEC
                while [ "$CHECK_SEC" -le "$TODAY_SEC" ] && [ "$CHECK_SEC" -le "$END_SEC" ]; do
                    if [ "$(uname)" = "Darwin" ]; then
                        DOW=$(date -j -f "%s" "$CHECK_SEC" +%u 2>/dev/null)
                    else
                        DOW=$(date -d "@$CHECK_SEC" +%u 2>/dev/null)
                    fi
                    if [ "$DOW" -le 5 ]; then
                        SPRINT_DAY=$((SPRINT_DAY + 1))
                    fi
                    CHECK_SEC=$((CHECK_SEC + 86400))
                done

                SPRINT_TOTAL_DAYS=0
                CHECK_SEC=$START_SEC
                while [ "$CHECK_SEC" -le "$END_SEC" ]; do
                    if [ "$(uname)" = "Darwin" ]; then
                        DOW=$(date -j -f "%s" "$CHECK_SEC" +%u 2>/dev/null)
                    else
                        DOW=$(date -d "@$CHECK_SEC" +%u 2>/dev/null)
                    fi
                    if [ "$DOW" -le 5 ]; then
                        SPRINT_TOTAL_DAYS=$((SPRINT_TOTAL_DAYS + 1))
                    fi
                    CHECK_SEC=$((CHECK_SEC + 86400))
                done
            fi
        fi
    fi
fi

# --- Active Task ---
ACTIVE_TASK=""
ACTIVE_TASK_NUM=""
if [ -n "$PLANNER_DIR" ] && [ -f "$PLANNER_DIR/active-tasks.md" ]; then
    ACTIVE_TASK=$(grep -E '## .+ \[IN_PROGRESS\]' "$PLANNER_DIR/active-tasks.md" | head -1 | sed 's/## \(.*\) \[IN_PROGRESS\].*/\1/' | head -c 50)
    ACTIVE_TASK_NUM=$(grep -E '## .+ \[IN_PROGRESS\]' "$PLANNER_DIR/active-tasks.md" | head -1 | grep -oE 'task-[0-9]+' | sed 's/task-//')
fi

# --- Oncall Status ---
ONCALL=""
ONCALL_KEYWORDS=$(read_config_list "statusline.oncall_keywords")
if [ -n "$SPRINT_FILE" ] && [ -n "$ONCALL_KEYWORDS" ]; then
    for keyword in $ONCALL_KEYWORDS; do
        if grep -qi "$keyword" "$SPRINT_FILE" 2>/dev/null; then
            if [ -n "$ONCALL" ]; then
                ONCALL="$ONCALL + $keyword"
            else
                ONCALL="$keyword"
            fi
        fi
    done
fi

# --- Next Meeting ---
NEXT_MEETING=""
NEXT_MEETING_TIME=""
NEXT_MEETING_ROOM=""
SKIP_EVENTS=$(read_config_list "statusline.skip_events")

if [ -n "$PLANNER_DIR" ] && [ -f "$PLANNER_DIR/calendar.md" ]; then
    TODAY=$(date +%Y-%m-%d)
    NOW_HHMM=$(date +%H:%M)

    if grep -q "^## $TODAY" "$PLANNER_DIR/calendar.md"; then
        IN_TODAY=false
        while IFS= read -r line; do
            if echo "$line" | grep -q "^## $TODAY"; then
                IN_TODAY=true
                continue
            fi
            if [ "$IN_TODAY" = true ] && echo "$line" | grep -q "^##"; then
                break
            fi
            if [ "$IN_TODAY" = true ]; then
                MEETING_START=$(echo "$line" | grep -oE '[0-9]{1,2}:[0-9]{2}-[0-9]{1,2}:[0-9]{2}' | head -1 | cut -d'-' -f1)
                if [ -n "$MEETING_START" ]; then
                    if [[ "$MEETING_START" > "$NOW_HHMM" ]] || [[ "$MEETING_START" == "$NOW_HHMM" ]]; then
                        MEETING_NAME=$(echo "$line" | awk -F'|' '{print $4}' | sed 's/^ *//;s/ *$//')
                        # Check skip list
                        SKIP=false
                        if [ -n "$MEETING_NAME" ] && [ -n "$SKIP_EVENTS" ]; then
                            for skip in $SKIP_EVENTS; do
                                if echo "$MEETING_NAME" | grep -qi "$skip"; then
                                    SKIP=true
                                    break
                                fi
                            done
                        fi
                        if [ -n "$MEETING_NAME" ] && [ "$SKIP" = false ]; then
                            NEXT_MEETING="$MEETING_NAME"
                            NEXT_MEETING_TIME="$MEETING_START"
                            NEXT_MEETING_ROOM=$(echo "$line" | awk -F'|' '{print $7}' | sed 's/^ *//;s/ *$//')
                            if [ -n "$NEXT_MEETING_ROOM" ] && [ ${#NEXT_MEETING_ROOM} -gt 25 ]; then
                                NEXT_MEETING_ROOM="${NEXT_MEETING_ROOM:0:22}..."
                            fi
                            break
                        fi
                    fi
                fi
            fi
        done < "$PLANNER_DIR/calendar.md"
    else
        NEXT_MEETING="Calendar not synced"
    fi
fi

# --- Release Countdown ---
RELEASE_COUNTDOWN=""
if [ -n "$PLANNER_DIR" ] && [ -f "$PLANNER_DIR/references.md" ]; then
    FC_FULL_DATE=$(grep -oE '[0-9]+/[0-9]+/[0-9]{4}' "$PLANNER_DIR/references.md" | head -1)
    if [ -n "$FC_FULL_DATE" ]; then
        FC_MONTH=$(echo "$FC_FULL_DATE" | cut -d'/' -f1)
        FC_DAY=$(echo "$FC_FULL_DATE" | cut -d'/' -f2)
        FC_YEAR=$(echo "$FC_FULL_DATE" | cut -d'/' -f3)
        FC_ISO="${FC_YEAR}-$(printf '%02d' "$FC_MONTH")-$(printf '%02d' "$FC_DAY")"
        if [ "$(uname)" = "Darwin" ]; then
            FC_SEC=$(date -j -f "%Y-%m-%d" "$FC_ISO" +%s 2>/dev/null)
            TODAY_SEC=$(date -j -f "%Y-%m-%d" "$(date +%Y-%m-%d)" +%s 2>/dev/null)
        else
            FC_SEC=$(date -d "$FC_ISO" +%s 2>/dev/null)
            TODAY_SEC=$(date -d "$(date +%Y-%m-%d)" +%s 2>/dev/null)
        fi
        if [ -n "$FC_SEC" ] && [ -n "$TODAY_SEC" ]; then
            DAYS_LEFT=$(( (FC_SEC - TODAY_SEC) / 86400 ))
            if [ "$DAYS_LEFT" -ge 0 ]; then
                RELEASE_COUNTDOWN="${DAYS_LEFT}d"
            else
                RELEASE_COUNTDOWN="PAST"
            fi
        fi
    fi
fi

# --- WFH/Office (from config) ---
LOCATION=""
WFH_DAYS=$(read_config_list "schedule.wfh_days")
OFFICE_DAYS=$(read_config_list "schedule.office_days")
TODAY_DAY_NAME=$(date +%A)

if [ -n "$WFH_DAYS" ] || [ -n "$OFFICE_DAYS" ]; then
    DOW=$(date +%u)
    if [ "$DOW" -eq 6 ] || [ "$DOW" -eq 7 ]; then
        LOCATION="Weekend"
    elif echo "$WFH_DAYS" | grep -qi "$TODAY_DAY_NAME"; then
        LOCATION="WFH"
    elif echo "$OFFICE_DAYS" | grep -qi "$TODAY_DAY_NAME"; then
        LOCATION="Office"
    fi
fi

# --- Gym Status (from config) ---
GYM_DAY="false"
GYM_DONE="false"
GYM_DAYS=$(read_config_list "personal.gym_days")

if [ -n "$GYM_DAYS" ] && echo "$GYM_DAYS" | grep -qi "$TODAY_DAY_NAME"; then
    GYM_DAY="true"
fi

if [ "$GYM_DAY" = "true" ] && [ -n "$PLANNER_DIR" ] && [ -f "$PLANNER_DIR/personal.md" ]; then
    TODAY_SHORT_DATE=$(date +%m/%d)
    TODAY_DOW_NAME=$(date +%a)

    IN_TRACKER=false
    while IFS= read -r line; do
        if echo "$line" | grep -q "^### Gym Routine"; then
            IN_TRACKER=true
            continue
        fi
        if [ "$IN_TRACKER" = true ] && echo "$line" | grep -q "^###\|^## "; then
            break
        fi
        if [ "$IN_TRACKER" = true ] && echo "$line" | grep -q "^|"; then
            WEEK_DATE=$(echo "$line" | grep -oE '[0-9]{2}/[0-9]{2}' | head -1)
            if [ -n "$WEEK_DATE" ]; then
                WEEK_M=$(echo "$WEEK_DATE" | cut -d'/' -f1)
                WEEK_D=$(echo "$WEEK_DATE" | cut -d'/' -f2)
                if [ "$(uname)" = "Darwin" ]; then
                    WEEK_SEC=$(date -j -f "%Y-%m-%d" "$(date +%Y)-${WEEK_M}-${WEEK_D}" +%s 2>/dev/null)
                else
                    WEEK_SEC=$(date -d "$(date +%Y)-${WEEK_M}-${WEEK_D}" +%s 2>/dev/null)
                fi
                TODAY_SEC_GYM=$(date +%s)
                if [ -n "$WEEK_SEC" ]; then
                    WEEK_END_SEC=$((WEEK_SEC + 6 * 86400))
                    if [ "$TODAY_SEC_GYM" -ge "$WEEK_SEC" ] && [ "$TODAY_SEC_GYM" -le "$WEEK_END_SEC" ]; then
                        # Find column for today
                        # Parse gym days from config to determine column mapping
                        COL=0
                        IDX=2
                        for gd in $GYM_DAYS; do
                            GD_SHORT=$(echo "$gd" | head -c 3)
                            if [ "$GD_SHORT" = "$TODAY_DOW_NAME" ]; then
                                COL=$IDX
                                break
                            fi
                            IDX=$((IDX + 1))
                        done
                        if [ "$COL" -gt 0 ]; then
                            CELL=$(echo "$line" | awk -F'|' -v c=$((COL)) '{print $c}' | sed 's/^ *//;s/ *$//')
                            if echo "$CELL" | grep -qi "done\|✓"; then
                                GYM_DONE="true"
                            fi
                        fi
                        break
                    fi
                fi
            fi
        fi
    done < "$PLANNER_DIR/personal.md"
fi

# --- Git Branch ---
GIT_BRANCH=""
if [ -n "$REPO_ROOT" ] && [ -d "$REPO_ROOT/.git" ]; then
    GIT_BRANCH=$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null)
fi

# --- Write Cache ---
cat > "$CACHE_FILE" << ENDJSON
{
  "sprint_day": ${SPRINT_DAY:-0},
  "sprint_total_days": ${SPRINT_TOTAL_DAYS:-0},
  "active_task": "$(echo "$ACTIVE_TASK" | sed 's/"/\\"/g')",
  "active_task_num": "${ACTIVE_TASK_NUM}",
  "oncall": "${ONCALL}",
  "next_meeting": "$(echo "$NEXT_MEETING" | sed 's/"/\\"/g')",
  "next_meeting_time": "${NEXT_MEETING_TIME}",
  "next_meeting_room": "$(echo "$NEXT_MEETING_ROOM" | sed 's/"/\\"/g')",
  "release_countdown": "${RELEASE_COUNTDOWN}",
  "location": "${LOCATION}",
  "gym_day": ${GYM_DAY},
  "gym_done": ${GYM_DONE},
  "git_branch": "${GIT_BRANCH}",
  "updated": "$(date +%H:%M)"
}
ENDJSON
