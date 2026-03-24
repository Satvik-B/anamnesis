#!/bin/bash
# Friday Statusline Renderer
# Reads JSON from stdin (Claude session data) + cache file (planner data)
# Outputs 2-line statusline with color.
# Components are opt-in via ~/.anamnesis.yaml.

CONFIG_FILE="$HOME/.anamnesis.yaml"
CACHE_FILE="/tmp/claude-statusline-cache.json"
CACHE_UPDATER="$HOME/.claude/friday-statusline-cache-update.sh"

# --- Read enabled components from config ---
read_config_bool() {
    local key="$1" default="$2"
    if [ -f "$CONFIG_FILE" ]; then
        local val
        val=$(python3 -c "
import yaml
with open('$CONFIG_FILE') as f:
    cfg = yaml.safe_load(f) or {}
keys = '$key'.split('.')
v = cfg
for k in keys:
    v = v.get(k, {}) if isinstance(v, dict) else {}
print(str(v).lower() if v not in ({}, None) else '$default')
" 2>/dev/null)
        echo "${val:-$default}"
    else
        echo "$default"
    fi
}

read_config_str() {
    local key="$1" default="$2"
    if [ -f "$CONFIG_FILE" ]; then
        local val
        val=$(python3 -c "
import yaml
with open('$CONFIG_FILE') as f:
    cfg = yaml.safe_load(f) or {}
keys = '$key'.split('.')
v = cfg
for k in keys:
    v = v.get(k, {}) if isinstance(v, dict) else {}
print(v if isinstance(v, str) else '$default')
" 2>/dev/null)
        echo "${val:-$default}"
    else
        echo "$default"
    fi
}

# Check if statusline is enabled
SL_ENABLED=$(read_config_bool "modules.statusline" "false")
if [ "$SL_ENABLED" != "true" ]; then
    # Minimal output — just session info
    INPUT=$(cat)
    MODEL=$(echo "$INPUT" | jq -r '.model.display_name // "?"')
    COST=$(echo "$INPUT" | jq -r '.cost.total_cost_usd // 0')
    COST_FMT=$(printf '$%.2f' "$COST")
    PCT=$(echo "$INPUT" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
    echo -e "\033[2m[\033[0m\033[1m${MODEL}\033[0m\033[2m]\033[0m ${PCT}% \033[2m|\033[0m ${COST_FMT}"
    exit 0
fi

# Component flags
C_SPRINT=$(read_config_bool "statusline.components.sprint_progress" "true")
C_MEETING=$(read_config_bool "statusline.components.next_meeting" "true")
C_TASK=$(read_config_bool "statusline.components.active_task" "true")
C_ONCALL=$(read_config_bool "statusline.components.oncall" "true")
C_RELEASE=$(read_config_bool "statusline.components.release_countdown" "true")
C_BRANCH=$(read_config_bool "statusline.components.git_branch" "true")
C_LOCATION=$(read_config_bool "statusline.components.location" "true")
C_GYM=$(read_config_bool "statusline.components.gym" "true")
RELEASE_LABEL=$(read_config_str "statusline.release_label" "")

# --- Refresh cache if stale (>5 min) or missing ---
if [ ! -f "$CACHE_FILE" ]; then
    "$CACHE_UPDATER" 2>/dev/null
elif [ "$(uname)" = "Darwin" ]; then
    CACHE_AGE=$(( $(date +%s) - $(stat -f %m "$CACHE_FILE") ))
    if [ "$CACHE_AGE" -gt 300 ]; then
        "$CACHE_UPDATER" 2>/dev/null
    fi
else
    CACHE_AGE=$(( $(date +%s) - $(stat -c %Y "$CACHE_FILE") ))
    if [ "$CACHE_AGE" -gt 300 ]; then
        "$CACHE_UPDATER" 2>/dev/null
    fi
fi

# --- Parse session data from stdin ---
INPUT=$(cat)
MODEL=$(echo "$INPUT" | jq -r '.model.display_name // "?"')
COST=$(echo "$INPUT" | jq -r '.cost.total_cost_usd // 0')
COST_FMT=$(printf '$%.2f' "$COST")
PCT=$(echo "$INPUT" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
LINES_ADD=$(echo "$INPUT" | jq -r '.cost.total_lines_added // 0')
LINES_REM=$(echo "$INPUT" | jq -r '.cost.total_lines_removed // 0')

# --- Colors ---
if [ "$PCT" -lt 50 ]; then
    CTX_COLOR="\033[32m"
elif [ "$PCT" -lt 80 ]; then
    CTX_COLOR="\033[33m"
else
    CTX_COLOR="\033[31m"
fi
RESET="\033[0m"
DIM="\033[2m"
CYAN="\033[36m"
YELLOW="\033[33m"
GREEN="\033[32m"
RED="\033[31m"
MAGENTA="\033[35m"
BOLD="\033[1m"

# --- Read cache ---
SPRINT_DAY="?"
SPRINT_TOTAL="?"
ACTIVE_TASK=""
ACTIVE_TASK_NUM=""
ONCALL=""
NEXT_MEETING=""
NEXT_MEETING_TIME=""
NEXT_MEETING_ROOM=""
RELEASE_CD=""
LOCATION=""
GYM_DAY="false"
GYM_DONE="false"
GIT_BRANCH=""

if [ -f "$CACHE_FILE" ]; then
    SPRINT_DAY=$(jq -r '.sprint_day // "?"' "$CACHE_FILE")
    SPRINT_TOTAL=$(jq -r '.sprint_total_days // "?"' "$CACHE_FILE")
    ACTIVE_TASK=$(jq -r '.active_task // ""' "$CACHE_FILE")
    ACTIVE_TASK_NUM=$(jq -r '.active_task_num // ""' "$CACHE_FILE")
    ONCALL=$(jq -r '.oncall // ""' "$CACHE_FILE")
    NEXT_MEETING=$(jq -r '.next_meeting // ""' "$CACHE_FILE")
    NEXT_MEETING_TIME=$(jq -r '.next_meeting_time // ""' "$CACHE_FILE")
    NEXT_MEETING_ROOM=$(jq -r '.next_meeting_room // ""' "$CACHE_FILE")
    RELEASE_CD=$(jq -r '.release_countdown // ""' "$CACHE_FILE")
    LOCATION=$(jq -r '.location // ""' "$CACHE_FILE")
    GYM_DAY=$(jq -r '.gym_day // false' "$CACHE_FILE")
    GYM_DONE=$(jq -r '.gym_done // false' "$CACHE_FILE")
    GIT_BRANCH=$(jq -r '.git_branch // ""' "$CACHE_FILE")
fi

# --- Meeting countdown ---
MEETING_IN=""
if [ -n "$NEXT_MEETING_TIME" ] && [ "$NEXT_MEETING_TIME" != "null" ]; then
    NOW_MIN=$(( $(date +%H) * 60 + $(date +%M) ))
    MEET_H=$(echo "$NEXT_MEETING_TIME" | cut -d: -f1)
    MEET_M=$(echo "$NEXT_MEETING_TIME" | cut -d: -f2)
    MEET_MIN=$(( MEET_H * 60 + MEET_M ))
    DIFF=$(( MEET_MIN - NOW_MIN ))
    if [ "$DIFF" -gt 0 ]; then
        if [ "$DIFF" -ge 60 ]; then
            MEETING_IN="in $((DIFF / 60))h$((DIFF % 60))m"
        else
            MEETING_IN="in ${DIFF}m"
        fi
    fi
fi

# --- Build Line 1: Session + Sprint ---
LINE1=""
LINE1="${LINE1}${DIM}[${RESET}${BOLD}${MODEL}${RESET}${DIM}]${RESET}"
LINE1="${LINE1} ${CTX_COLOR}${PCT}%${RESET}"
LINE1="${LINE1} ${DIM}|${RESET} ${COST_FMT}"
LINE1="${LINE1} ${DIM}|${RESET} ${GREEN}+${LINES_ADD}${RESET}/${RED}-${LINES_REM}${RESET}"

if [ "$C_SPRINT" = "true" ]; then
    LINE1="${LINE1} ${DIM}|${RESET} ${CYAN}Day ${SPRINT_DAY}/${SPRINT_TOTAL}${RESET}"
fi

if [ "$C_MEETING" = "true" ] && [ -n "$NEXT_MEETING" ] && [ "$NEXT_MEETING" != "null" ]; then
    MTG_TITLE="$NEXT_MEETING"
    if [ ${#MTG_TITLE} -gt 30 ]; then
        MTG_TITLE="${MTG_TITLE:0:28}…"
    fi
    TIME_SUFFIX="@ ${NEXT_MEETING_TIME}"
    if [ -n "$MEETING_IN" ]; then
        TIME_SUFFIX="@ ${NEXT_MEETING_TIME} (${MEETING_IN})"
    fi
    ROOM_SUFFIX=""
    if [ -n "$NEXT_MEETING_ROOM" ] && [ "$NEXT_MEETING_ROOM" != "null" ]; then
        ROOM_SUFFIX=" ${DIM}[${NEXT_MEETING_ROOM}]${RESET}"
    fi
    LINE1="${LINE1} ${DIM}|${RESET} ${YELLOW}${MTG_TITLE} ${TIME_SUFFIX}${RESET}${ROOM_SUFFIX}"
fi

# --- Build Line 2: Task + Context ---
LINE2=""

if [ "$C_TASK" = "true" ] && [ -n "$ACTIVE_TASK_NUM" ] && [ "$ACTIVE_TASK_NUM" != "null" ] && [ -n "$ACTIVE_TASK" ] && [ "$ACTIVE_TASK" != "null" ]; then
    LINE2="${LINE2}${MAGENTA}#${ACTIVE_TASK_NUM}${RESET} ${ACTIVE_TASK}"
fi

if [ "$C_ONCALL" = "true" ] && [ -n "$ONCALL" ] && [ "$ONCALL" != "null" ]; then
    [ -n "$LINE2" ] && LINE2="${LINE2} ${DIM}|${RESET} "
    LINE2="${LINE2}${RED}${BOLD}${ONCALL}${RESET}"
fi

if [ "$C_RELEASE" = "true" ] && [ -n "$RELEASE_CD" ] && [ "$RELEASE_CD" != "null" ] && [ "$RELEASE_CD" != "" ]; then
    [ -n "$LINE2" ] && LINE2="${LINE2} ${DIM}|${RESET} "
    if [ "$RELEASE_CD" = "PAST" ]; then
        LINE2="${LINE2}${RED}${RELEASE_LABEL} PAST${RESET}"
    else
        LINE2="${LINE2}${YELLOW}${RELEASE_LABEL} ${RELEASE_CD}${RESET}"
    fi
fi

if [ "$C_BRANCH" = "true" ] && [ -n "$GIT_BRANCH" ] && [ "$GIT_BRANCH" != "null" ] && [ "$GIT_BRANCH" != "master" ]; then
    [ -n "$LINE2" ] && LINE2="${LINE2} ${DIM}|${RESET} "
    LINE2="${LINE2}${CYAN}${GIT_BRANCH}${RESET}"
fi

if [ "$C_LOCATION" = "true" ] && [ -n "$LOCATION" ] && [ "$LOCATION" != "null" ]; then
    [ -n "$LINE2" ] && LINE2="${LINE2} ${DIM}|${RESET} "
    LINE2="${LINE2}${DIM}${LOCATION}${RESET}"
fi

if [ "$C_GYM" = "true" ] && [ "$GYM_DAY" = "true" ]; then
    [ -n "$LINE2" ] && LINE2="${LINE2} ${DIM}|${RESET} "
    if [ "$GYM_DONE" = "true" ]; then
        LINE2="${LINE2}${GREEN}Gym done${RESET}"
    else
        LINE2="${LINE2}${DIM}Gym pending${RESET}"
    fi
fi

# --- Output ---
echo -e "$LINE1"
[ -n "$LINE2" ] && echo -e "$LINE2"
