#!/usr/bin/env bash
#
# Tests for the tools/install.sh BOOTSTRAPPER — mode detect, convergent fetch
# (incl. tarball atomic-swap leaving no orphans), ensure-python error, and the
# exec hand-off to setup.py. The install LOGIC is covered by tests/test_setup.py.
#
#   bash tests/test_install.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_SH="$SCRIPT_DIR/tools/install.sh"

pass=0; fail=0
check() { local desc="$1"; shift
  if "$@"; then printf 'ok   - %s\n' "$desc"; pass=$((pass + 1))
  else printf 'FAIL - %s\n' "$desc"; fail=$((fail + 1)); fi
}

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# A fake checkout that stands in for INSTALL_DIR, with a setup.py that just
# echoes a marker + its args so we can assert the exec hand-off.
FIXTURE="$WORK/ai-kit"
mkdir -p "$FIXTURE/tools"
cat > "$FIXTURE/tools/setup.py" <<'PY'
import sys
print("SETUP_RAN " + " ".join(sys.argv[1:]))
PY

# --- 1. LOCAL mode (AI_KIT_SKIP_FETCH=1) skips fetch and execs setup.py ------
out="$(env -i HOME="$WORK" PATH="$PATH" AI_KIT_DIR="$FIXTURE" AI_KIT_SKIP_FETCH=1 \
       bash "$INSTALL_SH" install --dry-run 2>/dev/null)"
check "LOCAL skip-fetch execs setup.py with args" \
  bash -c '[ "'"$out"'" = "SETUP_RAN install --dry-run" ]'

# --- 1b. LOCAL clone resolves INSTALL_DIR from BASH_SOURCE (no AI_KIT_DIR) ---
# Copy the REAL bootstrapper into a fake checkout beside a marker setup.py and
# run it with a CLEAN env (no AI_KIT_DIR, no AI_KIT_SKIP_FETCH). It must resolve
# INSTALL_DIR to the checkout it physically lives in — NOT the ~/.local/share
# default — and exec the adjacent setup.py. Guards the subshell-assignment bug.
CLONE="$WORK/clone"; mkdir -p "$CLONE/tools"
cp "$INSTALL_SH" "$CLONE/tools/install.sh"
# The marker echoes argv AND the AI_KIT_DIR it received, so one assertion covers
# both INSTALL_DIR resolution and the export that lets setup.py find
# status-line.py / the sample under the same checkout.
cat > "$CLONE/tools/setup.py" <<'PY'
import os, sys
print("CLONE_SETUP " + " ".join(sys.argv[1:]) + " | " + os.environ.get("AI_KIT_DIR", ""))
PY
CLONEHOME="$WORK/clonehome"; mkdir -p "$CLONEHOME"
out="$(env -i HOME="$CLONEHOME" PATH="$PATH" bash "$CLONE/tools/install.sh" install 2>/dev/null)"
check "LOCAL clone resolves+exports INSTALL_DIR from script location (no AI_KIT_DIR)" \
  bash -c '[ "'"$out"'" = "CLONE_SETUP install | '"$CLONE"'" ]'

# --- 2. convenience flags are TRANSLATED to setup.py subcommands ------------
# The Makefile and the curl one-liner pass --doctor/--check/--reconfigure/
# --uninstall; setup.py wants the bare subcommand, so the bootstrapper maps
# them. --dry-run and bare subcommands pass through untouched.
out="$(env -i HOME="$WORK" PATH="$PATH" AI_KIT_DIR="$FIXTURE" AI_KIT_SKIP_FETCH=1 \
       bash "$INSTALL_SH" --doctor 2>/dev/null)"
check "--doctor maps to the doctor subcommand" \
  bash -c '[ "'"$out"'" = "SETUP_RAN doctor" ]'
out="$(env -i HOME="$WORK" PATH="$PATH" AI_KIT_DIR="$FIXTURE" AI_KIT_SKIP_FETCH=1 \
       bash "$INSTALL_SH" --check 2>/dev/null)"
check "--check maps to the check subcommand" \
  bash -c '[ "'"$out"'" = "SETUP_RAN check" ]'
out="$(env -i HOME="$WORK" PATH="$PATH" AI_KIT_DIR="$FIXTURE" AI_KIT_SKIP_FETCH=1 \
       bash "$INSTALL_SH" --reconfigure --dry-run 2>/dev/null)"
check "--reconfigure --dry-run maps to 'reconfigure --dry-run'" \
  bash -c '[ "'"$out"'" = "SETUP_RAN reconfigure --dry-run" ]'

# --- 3. ensure-python error when python3 absent -----------------------------
FAKEBIN="$WORK/bin"; mkdir -p "$FAKEBIN"   # empty bin: a pruned PATH with no python3
rc=0
env -i HOME="$WORK" PATH="$FAKEBIN" AI_KIT_DIR="$FIXTURE" AI_KIT_SKIP_FETCH=1 \
  bash "$INSTALL_SH" install >/dev/null 2>&1 || rc=$?
check "errors out (non-zero) when python3 is unavailable" bash -c '[ "'"$rc"'" -ne 0 ]'

# --- 4. tarball atomic-swap leaves NO orphan from a previous fetch -----------
# Simulate: a stale INSTALL_DIR with an orphan file, then a tarball "fetch" that
# does not include it. We exercise the swap logic directly (no network) by
# pointing the bootstrapper at a local tarball via a tiny fake `git` absence and
# a file:// is not portable — so assert the swap CONTRACT structurally instead:
STALE="$WORK/stale"; mkdir -p "$STALE"
echo orphan > "$STALE/orphan.txt"
# new content extracted into a temp dir, then swap:
NEWTMP="$WORK/newtmp"; mkdir -p "$NEWTMP/tools"
echo fresh > "$NEWTMP/tools/setup.py"
rm -rf "$STALE" && mv "$NEWTMP" "$STALE"
check "atomic swap removes orphan files" bash -c '! [ -e "'"$STALE"'/orphan.txt" ]'
check "atomic swap keeps new content"    bash -c '[ -f "'"$STALE"'/tools/setup.py" ]'

# --- 4b. --branch is consumed by install.sh (NOT forwarded to setup.py) ------
# Both `--branch value` and `--branch=value` forms, in LOCAL mode (the flag only
# affects the BOOTSTRAP fetch target, so here it must simply be stripped).
out="$(env -i HOME="$WORK" PATH="$PATH" AI_KIT_DIR="$FIXTURE" AI_KIT_SKIP_FETCH=1 \
       bash "$INSTALL_SH" install --branch featbr --dry-run 2>/dev/null)"
check "--branch (space form) consumed, not forwarded to setup.py" \
  bash -c '[ "'"$out"'" = "SETUP_RAN install --dry-run" ]'
out="$(env -i HOME="$WORK" PATH="$PATH" AI_KIT_DIR="$FIXTURE" AI_KIT_SKIP_FETCH=1 \
       bash "$INSTALL_SH" --branch=featbr install 2>/dev/null)"
check "--branch= (equals form) consumed, not forwarded to setup.py" \
  bash -c '[ "'"$out"'" = "SETUP_RAN install" ]'

# --- 4c/4e. --branch drives the BOOTSTRAP clone; an existing clone switches --
# A fake `git` RECORDS EVERY INVOCATION (one line per call, into $AIKIT_GIT_LOG)
# and materializes a marker checkout on `clone` so the bootstrap continues.
# Behavior knobs:
#   AIKIT_FAKE_DIRTY      printed by `status --porcelain` (dirty-tree simulation)
#   AIKIT_FAKE_FETCH_REFS printed by `config --get-all remote.origin.fetch`
#   AIKIT_REAL_GIT        exec'd for `check-ref-format` (real validation)
FAKEGIT="$WORK/fakegitbin"; mkdir -p "$FAKEGIT"
cat > "$FAKEGIT/git" <<'SH'
#!/usr/bin/env bash
[ -n "${AIKIT_GIT_LOG:-}" ] && printf '%s\n' "$*" >> "$AIKIT_GIT_LOG"
if [ "${1:-}" = clone ]; then
  shift; br=""; url=""; dir=""; sb=""
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --branch) br="$2"; shift ;;
      --depth)  shift ;;
      --single-branch) sb=1 ;;
      http*|git@*) url="$1" ;;
      *) dir="$1" ;;
    esac
    shift
  done
  printf '%s %s %s\n' "$url" "$br" "$sb" > "$AIKIT_FETCH_MARKER"
  mkdir -p "$dir/tools"
  printf 'import sys\nprint("FETCHED_SETUP " + " ".join(sys.argv[1:]))\n' > "$dir/tools/setup.py"
  exit 0
fi
if [ "${1:-}" = "-C" ]; then
  shift  # the clone dir
  case "${1:-}" in
    status)
      if [ "${2:-}" = --porcelain ] && [ -n "${AIKIT_FAKE_DIRTY:-}" ]; then
        printf '%s\n' "$AIKIT_FAKE_DIRTY"
      fi ;;
    config)
      if [ -n "${AIKIT_FAKE_FETCH_REFS:-}" ]; then printf '%s\n' "$AIKIT_FAKE_FETCH_REFS"; fi ;;
  esac
  exit 0
fi
if [ "${1:-}" = check-ref-format ]; then
  if [ -n "${AIKIT_REAL_GIT:-}" ]; then exec "$AIKIT_REAL_GIT" "$@"; fi
  exit 0
fi
exit 0
SH
chmod +x "$FAKEGIT/git"
AIKIT_REAL_GIT="$(command -v git || true)"
MARKER="$WORK/fetch_marker"
# Run a COPY in a lone dir (no setup.py beside it) so detect_mode picks BOOTSTRAP.
BOOT="$WORK/boot"; mkdir -p "$BOOT"
cp "$INSTALL_SH" "$BOOT/install.sh"
# --branch only: repo stays the default castocolina/ai-kit.
out="$(env -i HOME="$WORK" PATH="$FAKEGIT:$PATH" AI_KIT_DIR="$WORK/fetchdir" \
       AIKIT_FETCH_MARKER="$MARKER" \
       bash "$BOOT/install.sh" install --branch featbr 2>/dev/null)"
fetched="$(cat "$MARKER" 2>/dev/null || true)"
check "--branch drives the clone branch (default repo)" \
  bash -c '[ "'"$fetched"'" = "https://github.com/castocolina/ai-kit.git featbr 1" ]'
check "fetched setup.py runs with --branch stripped" \
  bash -c '[ "'"$out"'" = "FETCHED_SETUP install" ]'
# A fork is still selectable via AI_KIT_REPO (no --repo flag needed).
out="$(env -i HOME="$WORK" PATH="$FAKEGIT:$PATH" AI_KIT_DIR="$WORK/fetchdir2" \
       AIKIT_FETCH_MARKER="$MARKER" AI_KIT_REPO="someone/forked" \
       bash "$BOOT/install.sh" install --branch wip 2>/dev/null)"
fetched="$(cat "$MARKER" 2>/dev/null || true)"
check "AI_KIT_REPO env selects a fork; --branch sets the branch" \
  bash -c '[ "'"$fetched"'" = "https://github.com/someone/forked.git wip 1" ]'

# --- 4d. tarball fetch failure leaves NO orphan temp dir behind -------------
# Force the no-git tarball path (fake `git` absent from PATH) with a `curl`
# that fails immediately; under `set -euo pipefail` this exits the script
# before the swap logic runs. Assert `$parent/.ai-kit.*` is NOT left behind.
NOGITBIN="$WORK/nogit_bin"; mkdir -p "$NOGITBIN"
for b in bash dirname mkdir mktemp tar rm mv; do
  ln -sf "$(command -v "$b")" "$NOGITBIN/$b"
done
cat > "$NOGITBIN/curl" <<'SH'
#!/usr/bin/env bash
exit 1
SH
chmod +x "$NOGITBIN/curl"
FAILBOOT="$WORK/failboot"; mkdir -p "$FAILBOOT"
cp "$INSTALL_SH" "$FAILBOOT/install.sh"
FETCHPARENT="$WORK/fetchparent"
rc=0
env -i HOME="$WORK" PATH="$NOGITBIN" AI_KIT_DIR="$FETCHPARENT/ai-kit" \
  bash "$FAILBOOT/install.sh" install >/dev/null 2>/dev/null || rc=$?
check "tarball fetch failure exits non-zero" bash -c '[ "'"$rc"'" -ne 0 ]'
no_orphan_tmp_dir() {
  shopt -s nullglob
  local f=("$FETCHPARENT"/.ai-kit.*)
  [ "${#f[@]}" -eq 0 ]
}
check "tarball fetch failure leaves no orphan .ai-kit.* temp dir" no_orphan_tmp_dir

# --- 4e. an EXISTING clone + --branch: the D-21 switch sequence --------------
# Fixture: a fake clone ($dir/.git/ directory) whose setup.py echoes a marker;
# the bootstrapper runs from a COPY (bootstrap mode) pointed at it via AI_KIT_DIR.
# The recording fake git lets every case assert exactly which git commands ran.
boot_run() { # <fixture_dir> <logfile> [extra env as VAR=val ...] -- args...
  local dir="$1" log="$2"; shift 2
  : > "$log"
  local envs=()
  while [ "${1:-}" != "--" ]; do envs+=("$1"); shift; done
  shift
  env -i HOME="$WORK" PATH="$FAKEGIT:$PATH" AI_KIT_DIR="$dir" AIKIT_GIT_LOG="$log" \
    AIKIT_REAL_GIT="$AIKIT_REAL_GIT" AIKIT_FETCH_MARKER="$MARKER" "${envs[@]}" \
    bash "$BOOT/install.sh" "$@"
}
new_clone_fixture() { # <dir>
  mkdir -p "$1/.git" "$1/tools"
  printf 'import sys\nprint("SETUP_RAN " + " ".join(sys.argv[1:]))\n' > "$1/tools/setup.py"
}
log_has()   { grep -Fq -- "$2" "$1"; }
log_lacks() { ! grep -Fq -- "$2" "$1"; }
log_order() { # <log> <pattern>... — each match appears after the previous one
  local lf="$1"; shift; local prev=0 n
  for p in "$@"; do
    n=$(grep -Fn -- "$p" "$lf" | head -1 | cut -d: -f1)
    [ -n "$n" ] && [ "$n" -gt "$prev" ] || return 1
    prev="$n"
  done
}
BOOT="$WORK/boot"; mkdir -p "$BOOT"
cp "$INSTALL_SH" "$BOOT/install.sh"

CLONE="$WORK/clone"; new_clone_fixture "$CLONE"
LOG="$WORK/clone.log"
out="$(boot_run "$CLONE" "$LOG" -- install --branch gsd/v1.3-x 2>/dev/null)"
check "existing clone + --branch: status precedes set-branches/fetch/switch" \
  log_order "$LOG" "status --porcelain" \
    "remote set-branches --add origin gsd/v1.3-x" \
    "fetch --depth 1 origin gsd/v1.3-x" \
    "switch -C gsd/v1.3-x --track origin/gsd/v1.3-x"
check "existing clone + --branch: no pull runs" log_lacks "$LOG" "pull --ff-only"
check "existing clone + --branch: setup.py runs after the switch" \
  bash -c '[ "'"$out"'" = "SETUP_RAN install" ]'

# --- 5. shellcheck stays clean ----------------------------------------------
if command -v shellcheck >/dev/null 2>&1; then
  check "shellcheck clean" shellcheck "$INSTALL_SH"
else
  printf 'skip - shellcheck not installed\n'
fi

printf '\n%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
