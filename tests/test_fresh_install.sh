#!/usr/bin/env bash
# test_fresh_install.sh — Validates anamnesis installs and works from a clean venv.
#
# Usage:
#   ./tests/test_fresh_install.sh                    # install from local checkout
#   ./tests/test_fresh_install.sh --from-git          # install from GitHub
#
# Exit codes: 0 = all checks passed, 1 = failure

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

PASS=0
FAIL=0
REPO_URL="https://github.com/Satvik-B/anamnesis.git"

log_pass() { echo -e "  ${GREEN}PASS${NC}: $1"; PASS=$((PASS + 1)); }
log_fail() { echo -e "  ${RED}FAIL${NC}: $1"; FAIL=$((FAIL + 1)); }
log_info() { echo -e "  ${YELLOW}INFO${NC}: $1"; }

# --- Setup ---
WORKDIR=$(mktemp -d)
VENV="$WORKDIR/venv"
PROJECT="$WORKDIR/test-project"

cleanup() {
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

echo "=== Anamnesis Fresh Install Test ==="
echo "Workdir: $WORKDIR"
echo

# --- Create venv ---
echo "1. Creating virtual environment..."
python3 -m venv "$VENV"
source "$VENV/bin/activate"

# --- Install ---
echo "2. Installing anamnesis..."
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "${1:-}" == "--from-git" ]]; then
    log_info "Installing from GitHub: $REPO_URL"
    pip install "git+$REPO_URL" --quiet 2>&1
else
    log_info "Installing from local: $SCRIPT_DIR"
    pip install "$SCRIPT_DIR" --quiet 2>&1
fi

# --- Check CLI is available ---
echo "3. Checking CLI..."
if command -v anamnesis &>/dev/null; then
    log_pass "anamnesis command found in PATH"
else
    log_fail "anamnesis command not found"
    echo "Test aborted."
    exit 1
fi

# --- Version ---
VERSION_OUTPUT=$(anamnesis --version 2>&1)
if echo "$VERSION_OUTPUT" | grep -q "anamnesis"; then
    log_pass "anamnesis --version works: $VERSION_OUTPUT"
else
    log_fail "anamnesis --version failed"
fi

# --- Create test project ---
echo "4. Creating test project..."
mkdir -p "$PROJECT"
git -C "$PROJECT" init --quiet

# Pre-create config so --auto can skip interactive prompts
mkdir -p "$HOME"
cat > "$HOME/.anamnesis.yaml" << 'YAML'
user_name: TestUser
user_role: developer
modules:
  - memory
YAML

# --- Init ---
echo "5. Running anamnesis init..."
anamnesis init --project-dir "$PROJECT" --auto 2>&1 || true

if [ -d "$PROJECT/.claude" ]; then
    log_pass ".claude/ directory created"
else
    log_fail ".claude/ directory not created"
fi

if [ -f "$PROJECT/.claude/memory/INDEX.md" ]; then
    log_pass "INDEX.md created"
else
    log_fail "INDEX.md not created"
fi

if [ -f "$PROJECT/.claude/rules/memory-rule.md" ]; then
    log_pass "memory-rule.md installed"
else
    log_fail "memory-rule.md not installed"
fi

if [ -f "$PROJECT/.claude/skills/anamnesis/SKILL.md" ]; then
    log_pass "SKILL.md installed"
else
    log_fail "SKILL.md not installed"
fi

if [ -f "$PROJECT/.claude/.anamnesis-version" ]; then
    log_pass "Version file created"
else
    log_fail "Version file not created"
fi

# Check memory subdirectories created by the skeleton
# Note: knowledge/, contexts/, tasks/, reflections/ are created by the
# /anamnesis init skill inside Claude Code, not by the CLI installer.
for dir in archive slack; do
    if [ -d "$PROJECT/.claude/memory/$dir" ]; then
        log_pass "memory/$dir/ exists"
    else
        log_fail "memory/$dir/ missing"
    fi
done

# --- Doctor ---
echo "6. Running anamnesis doctor..."
DOCTOR_OUTPUT=$(anamnesis doctor --project-dir "$PROJECT" 2>&1)
DOCTOR_EXIT=$?

if [ $DOCTOR_EXIT -eq 0 ]; then
    log_pass "doctor passed (exit 0)"
else
    log_fail "doctor failed (exit $DOCTOR_EXIT)"
fi

if echo "$DOCTOR_OUTPUT" | grep -q "ERROR"; then
    log_fail "doctor reported errors"
else
    log_pass "doctor reported no errors"
fi

# --- Update (idempotency) ---
echo "7. Running anamnesis update..."
UPDATE_OUTPUT=$(anamnesis update --project-dir "$PROJECT" 2>&1)

if echo "$UPDATE_OUTPUT" | grep -qi "updated\|nothing"; then
    log_pass "update ran without errors"
else
    log_fail "update produced unexpected output"
fi

# --- Re-init (idempotency + backup) ---
echo "8. Re-running init (idempotency + backup test)..."
anamnesis init --project-dir "$PROJECT" --auto > /dev/null 2>&1

BACKUP_COUNT=$(find "$PROJECT" -maxdepth 1 -name ".claude.anamnesis-backup-*" -type d | wc -l | tr -d ' ')
if [ "$BACKUP_COUNT" -ge 1 ]; then
    log_pass "Backup directory created on re-init ($BACKUP_COUNT found)"
else
    log_fail "No backup directory found after re-init"
fi

# --- Summary ---
echo
echo "=== Results ==="
TOTAL=$((PASS + FAIL))
echo -e "${GREEN}$PASS${NC} passed, ${RED}$FAIL${NC} failed out of $TOTAL checks"

if [ $FAIL -gt 0 ]; then
    exit 1
fi
exit 0
