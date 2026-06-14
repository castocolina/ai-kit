#!/usr/bin/env bash
#
# ai-kit installer — fetch the kit and wire it into Claude Code.
#
#   curl -fsSL https://raw.githubusercontent.com/castocolina/ai-kit/main/tools/install.sh | bash
#   wget -qO-  https://raw.githubusercontent.com/castocolina/ai-kit/main/tools/install.sh | bash
#
# What it does (idempotent — safe to re-run as an updater):
#   1. fetch    clone or pull the repo into INSTALL_DIR (tarball fallback when git is absent)
#   2. verify   enumerate skills/commands/agents and validate their shape
#   3. link     symlink each entry into ~/.claude/<category>/ (never clobbers real files)
#   4. prune    remove broken symlinks under ~/.claude that point into INSTALL_DIR
#   5. statusline  point ~/.claude/settings.json at the bundled status-line.py
#
# Flags:  --dry-run   show what would change, mutate nothing
#         --uninstall remove every ai-kit symlink + statusLine, keep INSTALL_DIR
#         --help
#
# Env overrides (used by the test suite too):
#   AI_KIT_REPO        owner/name           (default: castocolina/ai-kit)
#   AI_KIT_BRANCH      branch               (default: main)
#   AI_KIT_DIR         install location     (default: ${XDG_DATA_HOME:-~/.local/share}/ai-kit)
#   CLAUDE_CONFIG_DIR  Claude config dir    (default: ~/.claude)
#   AI_KIT_SKIP_FETCH  =1 to skip step 1 (INSTALL_DIR must already exist)

set -euo pipefail
shopt -s nullglob

REPO_SLUG="${AI_KIT_REPO:-castocolina/ai-kit}"
REPO_BRANCH="${AI_KIT_BRANCH:-main}"
INSTALL_DIR="${AI_KIT_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/ai-kit}"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SETTINGS="$CLAUDE_DIR/settings.json"
CATEGORIES=(agents commands skills)

DRY_RUN=0
ACTION=install

# --- output -----------------------------------------------------------------
if [ -t 1 ]; then
  C_RESET=$'\033[0m'; C_DIM=$'\033[2m'; C_RED=$'\033[31m'
  C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_BLUE=$'\033[34m'
else
  C_RESET=''; C_DIM=''; C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''
fi
info() { printf '%s==>%s %s\n' "$C_BLUE" "$C_RESET" "$*"; }
ok()   { printf '%s  ok%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '%swarn%s %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; }
die()  { printf '%serr%s  %s\n' "$C_RED" "$C_RESET" "$*" >&2; exit 1; }

# Run a mutating command, or just describe it under --dry-run.
run() {
  if [ "$DRY_RUN" = 1 ]; then printf '%swould%s %s\n' "$C_DIM" "$C_RESET" "$*"; else "$@"; fi
}

have() { command -v "$1" >/dev/null 2>&1; }

# counters
n_linked=0; n_relinked=0; n_pruned=0; n_skip_foreign=0; n_skip_real=0; n_invalid=0

usage() {
  sed -n '3,30p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

# --- args -------------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)   DRY_RUN=1 ;;
    --uninstall) ACTION=uninstall ;;
    -h|--help)   usage ;;
    *)           die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

# Is $1 the same path as, or nested under, $2? (string test on absolute paths)
is_inside() {
  case "$1" in
    "$2"|"$2"/*) return 0 ;;
    *)           return 1 ;;
  esac
}

# --- fetch ------------------------------------------------------------------
fetch_repo() {
  if [ "${AI_KIT_SKIP_FETCH:-0}" = 1 ]; then
    [ -d "$INSTALL_DIR" ] || die "AI_KIT_SKIP_FETCH=1 but $INSTALL_DIR does not exist"
    info "skipping fetch (AI_KIT_SKIP_FETCH=1)"
    return
  fi
  local url="https://github.com/${REPO_SLUG}.git"
  local tarball="https://github.com/${REPO_SLUG}/archive/refs/heads/${REPO_BRANCH}.tar.gz"
  if [ -d "$INSTALL_DIR/.git" ]; then
    info "updating $INSTALL_DIR"
    run git -C "$INSTALL_DIR" pull --ff-only
  elif have git; then
    info "cloning $REPO_SLUG into $INSTALL_DIR"
    run git clone --branch "$REPO_BRANCH" --depth 1 "$url" "$INSTALL_DIR"
  elif have curl || have wget; then
    info "downloading tarball into $INSTALL_DIR (git not found)"
    run mkdir -p "$INSTALL_DIR"
    if have curl; then
      run bash -c "curl -fsSL '$tarball' | tar xz --strip-components=1 -C '$INSTALL_DIR'"
    else
      run bash -c "wget -qO- '$tarball' | tar xz --strip-components=1 -C '$INSTALL_DIR'"
    fi
  else
    die "need git, curl, or wget to fetch the repo"
  fi
}

# Refuse to operate on a dangerous or wrong INSTALL_DIR.
safety_check() {
  local real=""
  if ! real="$(cd "$INSTALL_DIR" 2>/dev/null && pwd -P)"; then
    die "INSTALL_DIR does not exist: $INSTALL_DIR"
  fi
  if [ "$real" = "/" ] || [ "$real" = "$HOME" ]; then
    die "refusing to use unsafe INSTALL_DIR: $real"
  fi
}

# Does this entry look like a valid skill/command/agent?
validate_entry() {
  local cat="$1" path="$2"
  case "$cat" in
    skills)
      [ -d "$path" ] && [ -f "$path/SKILL.md" ]
      ;;
    commands|agents)
      [ -f "$path" ] && [ "${path##*.}" = "md" ] && head -1 "$path" | grep -q '^---'
      ;;
    *) return 1 ;;
  esac
}

# Create or refresh one symlink, never clobbering real files or foreign links.
link_one() {
  local link="$1" target="$2"
  if [ -L "$link" ]; then
    local cur; cur="$(readlink "$link")"
    if [ "$cur" = "$target" ]; then
      return 0                                   # already correct
    elif is_inside "$cur" "$INSTALL_DIR"; then
      run ln -sfn "$target" "$link"; n_relinked=$((n_relinked + 1))
    else
      warn "$link points outside ai-kit ($cur) — leaving it alone"
      n_skip_foreign=$((n_skip_foreign + 1))
    fi
  elif [ -e "$link" ]; then
    warn "$link exists and is not a symlink — leaving it alone"
    n_skip_real=$((n_skip_real + 1))
  else
    run ln -s "$target" "$link"; n_linked=$((n_linked + 1))
  fi
}

# Link every valid entry of one category into ~/.claude/<category>/.
link_category() {
  local cat="$1" src="$INSTALL_DIR/$1" dest="$CLAUDE_DIR/$1"
  [ -d "$src" ] || return 0
  run mkdir -p "$dest"
  local entry name
  for entry in "$src"/*; do
    name="$(basename "$entry")"
    if ! validate_entry "$cat" "$entry"; then
      warn "skipping malformed $cat/$name"; n_invalid=$((n_invalid + 1)); continue
    fi
    link_one "$dest/$name" "$entry"
  done
}

# Remove broken symlinks under ~/.claude/<category>/ that point into INSTALL_DIR.
prune_category() {
  local dest="$CLAUDE_DIR/$1"
  [ -d "$dest" ] || return 0
  local link tgt
  for link in "$dest"/*; do
    [ -L "$link" ] || continue
    tgt="$(readlink "$link")"
    if is_inside "$tgt" "$INSTALL_DIR" && [ ! -e "$link" ]; then
      info "pruning stale symlink $link"
      run rm -f "$link"; n_pruned=$((n_pruned + 1))
    fi
  done
}

# Point settings.json at the bundled status line (preserves all other keys).
update_statusline() {
  local sl="$INSTALL_DIR/tools/status-line.py"
  [ -f "$sl" ] || { warn "no tools/status-line.py — skipping statusline"; return; }
  have python3 || { warn "python3 not found — skipping statusline"; return; }
  if [ "$DRY_RUN" = 1 ]; then
    printf '%swould%s set statusLine -> python3 %s\n' "$C_DIM" "$C_RESET" "$sl"; return
  fi
  [ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.bak"
  python3 - "$SETTINGS" "$sl" <<'PY'
import json, os, sys
path, statusline = sys.argv[1], sys.argv[2]
data = {}
if os.path.isfile(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        data = {}
if not isinstance(data, dict):
    data = {}
data["statusLine"] = {"type": "command", "command": "python3 " + statusline}
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
  ok "statusLine -> python3 $sl"
}

# --- uninstall --------------------------------------------------------------
do_uninstall() {
  info "removing ai-kit symlinks pointing into $INSTALL_DIR"
  local cat dest link tgt
  for cat in "${CATEGORIES[@]}"; do
    dest="$CLAUDE_DIR/$cat"
    [ -d "$dest" ] || continue
    for link in "$dest"/*; do
      [ -L "$link" ] || continue
      tgt="$(readlink "$link")"
      if is_inside "$tgt" "$INSTALL_DIR"; then
        run rm -f "$link"; n_pruned=$((n_pruned + 1))
      fi
    done
  done
  if [ -f "$SETTINGS" ] && have python3; then
    if [ "$DRY_RUN" = 1 ]; then
      printf '%swould%s clear statusLine if it points into %s\n' "$C_DIM" "$C_RESET" "$INSTALL_DIR"
    else
      cp "$SETTINGS" "$SETTINGS.bak"
      python3 - "$SETTINGS" "$INSTALL_DIR" <<'PY'
import json, os, sys
path, idir = sys.argv[1], sys.argv[2]
try:
    with open(path) as f:
        data = json.load(f)
except Exception:
    sys.exit(0)
sl = data.get("statusLine")
if isinstance(sl, dict) and idir in str(sl.get("command", "")):
    data.pop("statusLine", None)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
PY
    fi
  fi
  ok "removed $n_pruned symlink(s). INSTALL_DIR left in place: $INSTALL_DIR"
}

# --- main -------------------------------------------------------------------
main() {
  if [ "$ACTION" = uninstall ]; then
    safety_check
    do_uninstall
    return
  fi

  fetch_repo
  [ "$DRY_RUN" = 1 ] && [ ! -d "$INSTALL_DIR" ] && { info "(dry-run, nothing fetched — stopping)"; return; }
  safety_check

  local cat
  for cat in "${CATEGORIES[@]}"; do
    [ -d "$INSTALL_DIR/$cat" ] && info "linking $cat"
    link_category "$cat"
    prune_category "$cat"
  done

  update_statusline

  info "summary: ${n_linked} linked, ${n_relinked} relinked, ${n_pruned} pruned, ${n_skip_foreign} foreign-skipped, ${n_skip_real} real-skipped, ${n_invalid} invalid"
  ok "ai-kit installed at $INSTALL_DIR"
  if [ "$DRY_RUN" = 1 ]; then info "(dry-run — no changes were made)"; fi
}

main "$@"
