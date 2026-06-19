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
# Env overrides:
#   AI_KIT_REPO       owner/name        (default: castocolina/ai-kit)
#   AI_KIT_BRANCH     branch            (default: main)
#   AI_KIT_DIR        install location  (default: ${XDG_DATA_HOME:-~/.local/share}/ai-kit)
#   CLAUDE_CONFIG_DIR Claude config dir (default: ~/.claude)
#   AI_KIT_SKIP_FETCH =1 forces LOCAL mode (skip fetch; INSTALL_DIR must exist)

set -euo pipefail

REPO_SLUG="${AI_KIT_REPO:-castocolina/ai-kit}"
REPO_BRANCH="${AI_KIT_BRANCH:-main}"
INSTALL_DIR="${AI_KIT_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/ai-kit}"

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
# expects. --dry-run and a bare subcommand pass through untouched. Result in ARGS.
normalize_args() {
  ARGS=()
  local a
  for a in "$@"; do
    case "$a" in
      --doctor)      ARGS+=(doctor) ;;
      --check)       ARGS+=(check) ;;
      --reconfigure) ARGS+=(reconfigure) ;;
      --uninstall)   ARGS+=(uninstall) ;;
      *)             ARGS+=("$a") ;;
    esac
  done
}

# --- fetch (convergent) -----------------------------------------------------
fetch_repo() {
  local url="https://github.com/${REPO_SLUG}.git"
  local tarball="https://github.com/${REPO_SLUG}/archive/refs/heads/${REPO_BRANCH}.tar.gz"
  if [ -d "$INSTALL_DIR/.git" ]; then
    info "updating $INSTALL_DIR"
    git -C "$INSTALL_DIR" pull --ff-only
  elif have git; then
    info "cloning $REPO_SLUG into $INSTALL_DIR"
    git clone --branch "$REPO_BRANCH" --depth 1 "$url" "$INSTALL_DIR"
  elif have curl || have wget; then
    info "downloading tarball into $INSTALL_DIR (git not found)"
    # Stage into a temp dir ADJACENT to the target so the final swap is a
    # same-filesystem rename (a cross-fs mv degrades to copy-then-delete and can
    # fail partway). Move the old tree aside first so a failure is recoverable.
    local parent; parent="$(dirname "$INSTALL_DIR")"
    mkdir -p "$parent"
    local tmp; tmp="$(mktemp -d "$parent/.ai-kit.XXXXXX")"
    if have curl; then
      curl -fsSL "$tarball" | tar xz --strip-components=1 -C "$tmp"
    else
      wget -qO- "$tarball" | tar xz --strip-components=1 -C "$tmp"
    fi
    # atomic swap so deletions upstream propagate (no orphan files linger).
    local bak=""
    if [ -e "$INSTALL_DIR" ]; then
      bak="$INSTALL_DIR.bak.$$"
      mv "$INSTALL_DIR" "$bak"
    fi
    if mv "$tmp" "$INSTALL_DIR"; then
      [ -n "$bak" ] && rm -rf "$bak"
    else
      # restore the previous tree on failure, then surface the error.
      [ -n "$bak" ] && mv "$bak" "$INSTALL_DIR"
      rm -rf "$tmp"
      die "failed to swap fetched tarball into $INSTALL_DIR"
    fi
  else
    die "need git, curl, or wget to fetch the repo"
  fi
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
  detect_mode
  if [ "$MODE" = bootstrap ]; then
    fetch_repo
  else
    info "local checkout — skipping fetch ($INSTALL_DIR)"
  fi
  [ -f "$INSTALL_DIR/tools/setup.py" ] || die "tools/setup.py missing under $INSTALL_DIR"
  ensure_python
  # Hand the resolved location to setup.py so its resolve_paths() finds
  # status-line.py / the sample under the SAME checkout we just resolved —
  # critical for a LOCAL clone, where INSTALL_DIR isn't the ~/.local/share default.
  export AI_KIT_DIR="$INSTALL_DIR"
  normalize_args "$@"
  exec python3 "$INSTALL_DIR/tools/setup.py" ${ARGS[@]+"${ARGS[@]}"}
}

main "$@"
