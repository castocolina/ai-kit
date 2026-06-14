#!/usr/bin/env bash
#
# Tests for tools/install.sh — runs offline against a local fixture repo,
# in a throwaway HOME, asserting link / prune / safety behavior.
#
#   bash tests/test_install.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_SH="$SCRIPT_DIR/tools/install.sh"

pass=0; fail=0
check() { # check "desc" <test-command...>
  local desc="$1"; shift
  if "$@"; then printf 'ok   - %s\n' "$desc"; pass=$((pass + 1))
  else printf 'FAIL - %s\n' "$desc"; fail=$((fail + 1)); fi
}
is_link_to() { [ -L "$1" ] && [ "$(readlink "$1")" = "$2" ]; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

FIXTURE="$WORK/ai-kit"        # stand-in for INSTALL_DIR
CLAUDE="$WORK/.claude"

# --- build a fixture "repo" -------------------------------------------------
mkdir -p "$FIXTURE/skills/alpha" "$FIXTURE/skills/beta" \
         "$FIXTURE/commands" "$FIXTURE/agents" "$FIXTURE/tools"
printf -- '---\nname: alpha\n---\nbody\n' > "$FIXTURE/skills/alpha/SKILL.md"
printf -- '---\nname: beta\n---\nbody\n'  > "$FIXTURE/skills/beta/SKILL.md"
printf -- '---\nname: doit\n---\nbody\n'  > "$FIXTURE/commands/doit.md"
printf -- '---\nname: helper\n---\nbody\n' > "$FIXTURE/agents/helper.md"
mkdir -p "$FIXTURE/skills/nope"           # malformed: no SKILL.md
printf 'print("sl")\n' > "$FIXTURE/tools/status-line.py"

run_install() { env -i HOME="$WORK" PATH="$PATH" \
  AI_KIT_DIR="$FIXTURE" CLAUDE_CONFIG_DIR="$CLAUDE" AI_KIT_SKIP_FETCH=1 \
  bash "$INSTALL_SH" "$@" >/dev/null 2>&1; }

# --- 1. first install -------------------------------------------------------
run_install
check "skill alpha linked"        is_link_to "$CLAUDE/skills/alpha"  "$FIXTURE/skills/alpha"
check "skill beta linked"         is_link_to "$CLAUDE/skills/beta"   "$FIXTURE/skills/beta"
check "command linked"            is_link_to "$CLAUDE/commands/doit.md" "$FIXTURE/commands/doit.md"
check "agent linked"              is_link_to "$CLAUDE/agents/helper.md" "$FIXTURE/agents/helper.md"
check "malformed skill NOT linked" bash -c '! [ -e "'"$CLAUDE"'/skills/nope" ]'
check "statusLine points at fixture" \
  bash -c 'grep -q "'"$FIXTURE"'/tools/status-line.py" "'"$CLAUDE"'/settings.json"'

# --- 2. idempotent re-run ---------------------------------------------------
run_install
check "re-run keeps alpha link"   is_link_to "$CLAUDE/skills/alpha"  "$FIXTURE/skills/alpha"

# --- 3. foreign symlink + real file are left alone --------------------------
ln -s /tmp/somewhere-else "$CLAUDE/skills/foreign"
mkdir -p "$CLAUDE/skills/realdir"
run_install
check "foreign symlink untouched" is_link_to "$CLAUDE/skills/foreign" "/tmp/somewhere-else"
check "real dir not clobbered"    bash -c '[ -d "'"$CLAUDE"'/skills/realdir" ] && ! [ -L "'"$CLAUDE"'/skills/realdir" ]'

# --- 4. prune: remove a skill from the repo, re-run, link must vanish --------
rm -rf "$FIXTURE/skills/beta"
run_install
check "removed skill is pruned"   bash -c '! [ -e "'"$CLAUDE"'/skills/beta" ] && ! [ -L "'"$CLAUDE"'/skills/beta" ]'
check "alpha survives prune"      is_link_to "$CLAUDE/skills/alpha"  "$FIXTURE/skills/alpha"
check "foreign survives prune"    is_link_to "$CLAUDE/skills/foreign" "/tmp/somewhere-else"

# --- 5. dry-run mutates nothing ---------------------------------------------
rm -rf "$FIXTURE/skills/alpha"          # would be pruned on a real run
run_install --dry-run
check "dry-run does not prune"    is_link_to "$CLAUDE/skills/alpha"  "$FIXTURE/skills/alpha"
mkdir -p "$FIXTURE/skills/alpha"        # restore fixture for uninstall test
printf -- '---\nname: alpha\n---\n' > "$FIXTURE/skills/alpha/SKILL.md"

# --- 6. uninstall removes ai-kit links, keeps foreign + INSTALL_DIR ---------
run_install
run_install --uninstall
check "uninstall removes alpha"   bash -c '! [ -e "'"$CLAUDE"'/skills/alpha" ]'
check "uninstall removes command" bash -c '! [ -e "'"$CLAUDE"'/commands/doit.md" ]'
check "uninstall keeps foreign"   is_link_to "$CLAUDE/skills/foreign" "/tmp/somewhere-else"
check "uninstall keeps INSTALL_DIR" bash -c '[ -d "'"$FIXTURE"'" ]'
check "uninstall clears statusLine" \
  bash -c '! grep -q "status-line.py" "'"$CLAUDE"'/settings.json"'

# --- report -----------------------------------------------------------------
printf '\n%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
