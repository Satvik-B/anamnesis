#!/bin/bash
# Calendar Sync — Fetches Google Calendar events via direct API, formats into calendar.md.
#
# Reads config from ~/.claude-memory.yaml for timezone and workspace path.
# Uses OAuth token from ~/.gcalendar-mcp-token.json with automatic refresh.
#
# Usage:
#   calendar-sync.sh              # Run sync
#   calendar-sync.sh --install    # Install cron entry
#   calendar-sync.sh --uninstall  # Remove cron entry

set -uo pipefail

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Find repository root ---
find_repo_root() {
    if [ -n "${REPO_ROOT:-}" ]; then
        echo "$REPO_ROOT"
        return
    fi
    # Walk up from script dir to find .git
    local dir="$SCRIPT_DIR"
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
if [ -z "$REPO_ROOT" ]; then
    echo "ERROR: Cannot find repository root. Set REPO_ROOT env var." >&2
    exit 1
fi

CALENDAR_FILE="$REPO_ROOT/friday/calendar.md"
LOG_FILE="/tmp/claude-calendar-sync.log"
LOCK_FILE="/tmp/claude-calendar-sync.lock"
RAW_JSON="/tmp/calendar-raw.json"
TEMP_OUTPUT="/tmp/calendar-sync-output.md"

# --- Read timezone from config ---
read_config_timezone() {
    local config="$HOME/.claude-memory.yaml"
    if [ -f "$config" ]; then
        python3 -c "
import yaml, sys
with open('$config') as f:
    cfg = yaml.safe_load(f) or {}
tz = cfg.get('calendar', {}).get('timezone') or cfg.get('schedule', {}).get('timezone') or 'UTC'
print(tz)
" 2>/dev/null || echo "UTC"
    else
        echo "UTC"
    fi
}

TIMEZONE="$(read_config_timezone)"

# --- Handle --install / --uninstall ---
if [ "${1:-}" = "--install" ]; then
    CRON_CMD="0 * * * * $SCRIPT_DIR/calendar-sync.sh"
    if crontab -l 2>/dev/null | grep -qF "calendar-sync.sh"; then
        echo "Cron entry already exists. Updating..."
        crontab -l 2>/dev/null | grep -vF "calendar-sync.sh" | { cat; echo "$CRON_CMD"; } | crontab -
    else
        (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    fi
    echo "Cron installed: $CRON_CMD"
    exit 0
fi

if [ "${1:-}" = "--uninstall" ]; then
    crontab -l 2>/dev/null | grep -vF "calendar-sync.sh" | crontab -
    echo "Cron entry removed."
    exit 0
fi

# --- Logging ---
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

cleanup() {
    local exit_code=$?
    rm -f "$LOCK_FILE" "$TEMP_OUTPUT"
    log "Cleanup: done (exit code: $exit_code)"
}

trap cleanup EXIT INT TERM HUP PIPE

# --- Lock file handling ---
STALE_LOCK_THRESHOLD=120
if [ -f "$LOCK_FILE" ]; then
    LOCK_AGE=$(( $(date +%s) - $(stat -f %m "$LOCK_FILE" 2>/dev/null || stat -c %Y "$LOCK_FILE" 2>/dev/null) ))
    if [ "$LOCK_AGE" -lt "$STALE_LOCK_THRESHOLD" ]; then
        log "Sync already running (lock age: ${LOCK_AGE}s), skipping"
        trap - EXIT
        exit 0
    fi
    log "WARNING: Stale lock (age: ${LOCK_AGE}s), removing"
    rm -f "$LOCK_FILE"
fi
touch "$LOCK_FILE"

rm -f "$RAW_JSON" "$TEMP_OUTPUT"

TODAY=$(date +%Y-%m-%d)
DAY_NAME=$(date +%A)
SYNC_TIME=$(date '+%Y-%m-%d %H:%M')

log "=== Calendar sync starting ($TODAY $DAY_NAME, tz=$TIMEZONE) ==="

# --- Phase 1: Fetch ---
log "Phase 1: Fetching calendar..."
START_TIME=$(date +%s)

if ! python3 "$SCRIPT_DIR/fetch-calendar.py" "$RAW_JSON" --date "$TODAY" >> "$LOG_FILE" 2>&1; then
    log "=== Calendar sync FAILED (fetch error) ==="
    exit 1
fi

ELAPSED=$(( $(date +%s) - START_TIME ))

if [ ! -f "$RAW_JSON" ]; then
    log "=== Calendar sync FAILED (no raw JSON after ${ELAPSED}s) ==="
    exit 1
fi

RAW_SIZE=$(wc -c < "$RAW_JSON")
log "Phase 1 done in ${ELAPSED}s — raw JSON: ${RAW_SIZE} bytes"

# --- Phase 2: Format ---
log "Phase 2: Formatting..."

if python3 "$SCRIPT_DIR/format-calendar.py" "$RAW_JSON" "$TEMP_OUTPUT" "$SYNC_TIME" "$TIMEZONE" >> "$LOG_FILE" 2>&1; then
    if grep -q "^## $TODAY" "$TEMP_OUTPUT"; then
        # Ensure workspace dir exists
        mkdir -p "$(dirname "$CALENDAR_FILE")"
        mv "$TEMP_OUTPUT" "$CALENDAR_FILE"
        TOTAL_ELAPSED=$(( $(date +%s) - START_TIME ))
        log "calendar.md: $(wc -c < "$CALENDAR_FILE") bytes"
        log "=== Calendar sync completed (${TOTAL_ELAPSED}s) ==="
    else
        log "WARNING: output missing today's date ($TODAY)"
        log "=== Calendar sync FAILED (bad format) ==="
        exit 1
    fi
else
    log "Phase 2 FAILED"
    log "=== Calendar sync FAILED ==="
    exit 1
fi
