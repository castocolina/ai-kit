#!/usr/bin/env bash
#
# ai-kit bootstrapper — fetch the kit (when needed) and hand off to the setup wizard.
#
#   curl -fsSL https://raw.githubusercontent.com/castocolina/ai-kit/main/tools/install.sh | bash
#   wget -qO-  https://raw.githubusercontent.com/castocolina/ai-kit/main/tools/install.sh | bash
#
# What it does:
#   1. detect mode — LOCAL (a clone: tools/setup.py resolvable next to me) skips fetch;
#                    BOOTSTRAP (piped from curl) fetches the repo first.
#   2. fetch (BOOTSTRAP only) — git clone/pull, or a tarball extracted into a temp dir
#                    then ATOMICALLY SWAPPED into place so deletions propagate.
#   3. ensure python3 is present (clear error + per-OS hint if absent).
#   4. exec python3 "$INSTALL_DIR/tools/setup.py" "$@"  — the wizard does the rest.
#
# Subcommands map to setup.py; the --doctor/--check/--reconfigure/--uninstall
# convenience flags are translated to the bare subcommand, --dry-run passes through:
#   (none)/install · reconfigure · uninstall · doctor · check · --dry-run · --help
#   e.g.  curl … | bash -s -- --doctor      curl … | bash -s -- reconfigure
#
# Fetch-target flag (BOOTSTRAP only, new or existing clone at INSTALL_DIR; consumed
# here, not passed to setup.py; a LOCAL checkout ignores it with a note) —
#   --branch name       (or --branch=name)       override the branch to fetch
#   e.g.  curl … feat/x/tools/install.sh | bash -s -- --branch feat/x
#   (a fork is selected via the AI_KIT_REPO env override below.)
# On an EXISTING clone an explicit branch (flag or AI_KIT_BRANCH — the default
# `main` never counts) validates the name with `git check-ref-format --branch`,
# refuses when the tree is dirty, an index.lock is present, or the local branch
# holds commits no origin ref has (no auto-recovery), refuses a branch missing
# on origin (`ls-remote`), then runs: remote set-branches --add origin B →
# fetch --depth 1 origin B → switch -C B --track origin/B, removing the refspec
# it added if the fetch or switch fails. Without an explicit branch an existing
# clone runs `pull --ff-only origin <current branch>` (explicit, so a leftover
# refspec for a since-deleted branch cannot break it). --dry-run prints the
# planned git commands and runs no fetch, pull, switch, set-branches, clone or
# tarball download.
#
# Env overrides (--branch takes precedence over AI_KIT_BRANCH):
#   AI_KIT_REPO       owner/name        (default: castocolina/ai-kit)
#   AI_KIT_BRANCH     branch            (default: main)
#   AI_KIT_DIR        install location  (default: ${XDG_DATA_HOME:-~/.local/share}/ai-kit)
#   CLAUDE_CONFIG_DIR Claude config dir (default: ~/.claude)
#   AI_KIT_SKIP_FETCH =1 forces LOCAL mode (skip fetch; INSTALL_DIR must exist)

set -euo pipefail

REPO_SLUG="${AI_KIT_REPO:-castocolina/ai-kit}"
REPO_BRANCH="${AI_KIT_BRANCH:-main}"
INSTALL_DIR="${AI_KIT_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/ai-kit}"
# An explicit branch request (env now, or --branch in normalize_args) is the ONLY
# thing that switches an existing clone; the default `main` does not count (D-21).
BRANCH_EXPLICIT=0
[ -n "${AI_KIT_BRANCH:-}" ] && BRANCH_EXPLICIT=1
DRY_RUN=0

if [ -t 2 ]; then
  C_RESET=$'\033[0m'; C_RED=$'\033[31m'; C_BLUE=$'\033[34m'
else
  C_RESET=''; C_RED=''; C_BLUE=''
fi
info() { printf '%s==>%s %s\n' "$C_BLUE" "$C_RESET" "$*" >&2; }
die()  { printf '%serr%s  %s\n' "$C_RED" "$C_RESET" "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

# --- mode detect ------------------------------------------------------------
# LOCAL when this script lives inside a real checkout (tools/setup.py resolvable
# next to it) OR AI_KIT_SKIP_FETCH=1; else BOOTSTRAP (piped from curl).
MODE=""
detect_mode() {
  # Sets globals MODE and (for a real checkout) INSTALL_DIR. MUST be called
  # directly — NOT in a $() command substitution — or the INSTALL_DIR assignment
  # is lost in the subshell and a LOCAL clone resolves the wrong directory.
  if [ "${AI_KIT_SKIP_FETCH:-0}" = 1 ]; then
    MODE=local; return
  fi
  local src="${BASH_SOURCE[0]:-}"
  if [ -n "$src" ] && [ -f "$src" ]; then
    local here; here="$(cd "$(dirname "$src")" >/dev/null 2>&1 && pwd -P)"
    if [ -f "$here/setup.py" ]; then
      INSTALL_DIR="$(cd "$here/.." && pwd -P)"
      MODE=local; return
    fi
  fi
  MODE=bootstrap
}

# Translate the convenience flags the Makefile and curl one-liner use
# (--doctor/--check/--reconfigure/--uninstall) into the bare subcommand setup.py
# expects. --dry-run and a bare subcommand pass through untouched. The bootstrap
# fetch-branch flag (--branch, both `--branch name` and `--branch=name`) is
# CONSUMED here — it sets REPO_BRANCH and is NOT forwarded to setup.py. Result in
# ARGS. Must run BEFORE fetch so the override takes effect. (Fork selection stays
# on the AI_KIT_REPO env var.)
normalize_args() {
  ARGS=()
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --doctor)      ARGS+=(doctor) ;;
      --check)       ARGS+=(check) ;;
      --reconfigure) ARGS+=(reconfigure) ;;
      --uninstall)   ARGS+=(uninstall) ;;
      --branch)      REPO_BRANCH="${2:?--branch needs a value}"; BRANCH_EXPLICIT=1; shift ;;
      --branch=*)    REPO_BRANCH="${1#*=}"; BRANCH_EXPLICIT=1 ;;
      --dry-run)     DRY_RUN=1; ARGS+=("$1") ;;
      *)             ARGS+=("$1") ;;
    esac
    shift
  done
}

# --- fetch (convergent) -----------------------------------------------------
fetch_repo() {
  local url="https://github.com/${REPO_SLUG}.git"
  local tarball="https://github.com/${REPO_SLUG}/archive/refs/heads/${REPO_BRANCH}.tar.gz"
  if [ -d "$INSTALL_DIR/.git" ]; then
    if [ "$BRANCH_EXPLICIT" = 1 ]; then
      switch_branch
    else
      update_current_branch
    fi
  elif [ "$DRY_RUN" = 1 ]; then
    # A non-git INSTALL_DIR (a previous tarball install) would be re-downloaded and
    # swapped; --dry-run must mutate nothing on every path (B-CR-02).
    info "dry run: would fetch ${REPO_SLUG}@${REPO_BRANCH} into $INSTALL_DIR (not a git checkout)"
  elif have git; then
    info "cloning $REPO_SLUG into $INSTALL_DIR"
    # --depth 1 already implies --single-branch (git-scm.com/docs/git-clone) unless
    # --no-single-branch is given. The explicit flag keeps that property from silently
    # depending on an unstated default a future edit could break (e.g. adding
    # --no-single-branch, or dropping --depth 1 for a --full-history debug flag).
    git clone --single-branch --branch "$REPO_BRANCH" --depth 1 "$url" "$INSTALL_DIR"
  elif have curl || have wget; then
    info "downloading tarball into $INSTALL_DIR (git not found)"
    # Stage into a temp dir ADJACENT to the target so the final swap is a
    # same-filesystem rename (a cross-fs mv degrades to copy-then-delete and can
    # fail partway). Move the old tree aside first so a failure is recoverable.
    local parent; parent="$(dirname "$INSTALL_DIR")"
    mkdir -p "$parent"
    # NOT `local`: a curl|tar or wget|tar failure here exits the whole script
    # immediately via `set -e` (pipefail), before the swap logic below ever
    # runs -- a RETURN trap would NOT fire in that case (set -e unwinds past a
    # failing function body without running its pending RETURN traps), so this
    # must be an EXIT trap. Confirmed empirically that bash also drops a
    # FUNCTION-LOCAL variable's binding before running an EXIT trap that fires
    # this way (the trap body sees $tmp as unbound under `set -u`) -- so `tmp`
    # is deliberately function-global here, unset once the trap is cleared, so
    # the cleanup trap reliably has the path it must remove. No other trap is
    # registered anywhere else in this script, so scoping it to just the fetch
    # (cleared right after a successful extract, before the swap) is safe.
    tmp="$(mktemp -d "$parent/.ai-kit.XXXXXX")"
    trap 'rm -rf "$tmp"' EXIT
    if have curl; then
      curl -fsSL "$tarball" | tar xz --strip-components=1 -C "$tmp"
    else
      wget -qO- "$tarball" | tar xz --strip-components=1 -C "$tmp"
    fi
    trap - EXIT
    # atomic swap so deletions upstream propagate (no orphan files linger).
    local bak=""
    if [ -e "$INSTALL_DIR" ]; then
      bak="$INSTALL_DIR.bak.$$"
      mv "$INSTALL_DIR" "$bak"
    fi
    if mv "$tmp" "$INSTALL_DIR"; then
      [ -n "$bak" ] && rm -rf "$bak"
      unset tmp
    else
      # restore the previous tree on failure, then surface the error.
      [ -n "$bak" ] && mv "$bak" "$INSTALL_DIR"
      rm -rf "$tmp"
      unset tmp
      die "failed to swap fetched tarball into $INSTALL_DIR"
    fi
  else
    die "need git, curl, or wget to fetch the repo"
  fi
}

switch_branch() {
  # Reject option-like / malformed names BEFORE any inspection or mutation
  # (T-16.1-11); the checks up to the dry-run return are read-only.
  git check-ref-format --branch "$REPO_BRANCH" >/dev/null 2>&1 \
    || die "invalid branch name: $REPO_BRANCH"
  refuse_if_dirty
  refuse_if_unpushed
  if [ -n "${AI_KIT_REPO:-}" ]; then
    info "note: AI_KIT_REPO is ignored for an existing clone; it fetches from its own origin"
  fi
  if [ "$DRY_RUN" = 1 ]; then
    info "dry run: would run: git -C $INSTALL_DIR ls-remote --exit-code --heads origin $REPO_BRANCH"
    info "dry run: would run: git -C $INSTALL_DIR remote set-branches --add origin $REPO_BRANCH"
    info "dry run: would run: git -C $INSTALL_DIR fetch --depth 1 origin $REPO_BRANCH"
    info "dry run: would run: git -C $INSTALL_DIR switch -C $REPO_BRANCH --track origin/$REPO_BRANCH"
    return
  fi
  # Refuse an unknown branch before persisting a refspec for it (B-CR-01).
  git -C "$INSTALL_DIR" ls-remote --exit-code --heads origin "$REPO_BRANCH" >/dev/null \
    || die "branch not found on origin: $REPO_BRANCH"
  # set-branches only when the refspec is not already listed (idempotent rerun,
  # RUN-11); the match is exact-line (-Fxq), never a partial/refspec-prefix hit.
  local refspec="+refs/heads/$REPO_BRANCH:refs/remotes/origin/$REPO_BRANCH" added=0
  if ! git -C "$INSTALL_DIR" config --get-all remote.origin.fetch 2>/dev/null \
    | grep -Fxq -- "$refspec"; then
    git -C "$INSTALL_DIR" remote set-branches --add origin "$REPO_BRANCH"
    added=1
  fi
  if ! { git -C "$INSTALL_DIR" fetch --depth 1 origin "$REPO_BRANCH" \
    && git -C "$INSTALL_DIR" switch -C "$REPO_BRANCH" --track "origin/$REPO_BRANCH"; }; then
    if [ "$added" = 1 ]; then
      git -C "$INSTALL_DIR" config --fixed-value --unset remote.origin.fetch "$refspec" || true
    fi
    die "could not switch $INSTALL_DIR to $REPO_BRANCH"
  fi
}

update_current_branch() {
  # Fetch the current branch explicitly: a plain `pull` also fetches every
  # configured refspec and dies on one whose branch was deleted upstream (B-CR-01).
  local cur
  cur="$(git -C "$INSTALL_DIR" symbolic-ref --short -q HEAD)" \
    || die "$INSTALL_DIR is not on a branch; inspect it with: git -C $INSTALL_DIR status"
  info "updating $INSTALL_DIR"
  if [ "$DRY_RUN" = 1 ]; then
    info "dry run: would run: git -C $INSTALL_DIR pull --ff-only origin $cur"
    return
  fi
  git -C "$INSTALL_DIR" pull --ff-only origin "$cur"
}

refuse_if_dirty() {
  # R14 / RUN-11: a dirty tree or a leftover index.lock (an interrupted run)
  # refuses the switch and never auto-recovers — the user resolves it. A failing
  # `git status` (e.g. dubious ownership) refuses too instead of reading as clean.
  local msg="$INSTALL_DIR has local changes or an unfinished git operation; inspect it with: git -C $INSTALL_DIR status"
  local st
  if [ -e "$INSTALL_DIR/.git/index.lock" ]; then die "$msg"; fi
  st="$(git -C "$INSTALL_DIR" --no-optional-locks status --porcelain)" || die "$msg"
  [ -z "$st" ] || die "$msg"
}

refuse_if_unpushed() {
  # B-WR-01: `switch -C` force-resets an existing local branch, so refuse when it
  # holds commits no origin ref has. Checked BEFORE the shallow fetch, which cuts
  # the old history and would make an up-to-date branch look ahead.
  git -C "$INSTALL_DIR" rev-parse --verify -q "refs/heads/$REPO_BRANCH" >/dev/null || return 0
  local n
  n="$(git -C "$INSTALL_DIR" rev-list --count "refs/heads/$REPO_BRANCH" --not --remotes=origin)" \
    || die "cannot inspect branch $REPO_BRANCH in $INSTALL_DIR"
  [ "${n:-0}" = 0 ] \
    || die "$REPO_BRANCH has $n commit(s) not on origin in $INSTALL_DIR; push or move them first"
}

# --- ensure python3 ---------------------------------------------------------
ensure_python() {
  if have python3; then return; fi
  local hint="install python3 with your package manager"
  case "$(uname -s)" in
    Darwin) hint="brew install python3" ;;
    Linux)
      if have apt-get; then hint="sudo apt-get install -y python3"
      elif have dnf; then hint="sudo dnf install -y python3"
      elif have pacman; then hint="sudo pacman -S python"
      fi ;;
  esac
  die "python3 is required but was not found — $hint"
}

main() {
  # Parse args FIRST: --branch must override REPO_BRANCH before fetch_repo runs
  # (the rest land in ARGS for setup.py).
  normalize_args "$@"
  detect_mode
  if [ "$MODE" = bootstrap ]; then
    if [ "$DRY_RUN" = 1 ] && [ ! -f "$INSTALL_DIR/tools/setup.py" ]; then
      info "dry run: no checkout at $INSTALL_DIR yet; stopping before setup.py"
      exit 0
    fi
    fetch_repo
  else
    info "local checkout — skipping fetch ($INSTALL_DIR)"
    if [ "$BRANCH_EXPLICIT" = 1 ]; then
      info "note: --branch/AI_KIT_BRANCH is ignored in a local checkout (no fetch)"
    fi
  fi
  [ -f "$INSTALL_DIR/tools/setup.py" ] || die "tools/setup.py missing under $INSTALL_DIR"
  ensure_python
  # Hand the resolved location to setup.py so its resolve_paths() finds
  # status-line.py / the sample under the SAME checkout we just resolved —
  # critical for a LOCAL clone, where INSTALL_DIR isn't the ~/.local/share default.
  export AI_KIT_DIR="$INSTALL_DIR"
  exec python3 "$INSTALL_DIR/tools/setup.py" ${ARGS[@]+"${ARGS[@]}"}
}

main "$@"
