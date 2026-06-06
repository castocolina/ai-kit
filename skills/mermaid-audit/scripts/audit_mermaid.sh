#!/usr/bin/env bash
# Convenience wrapper / fallback for the mermaid-audit skill.
# Recommended path is audit_mermaid.py (stdlib, line-accurate). This wrapper runs
# it when python3 is available; otherwise it does a minimal awk + mmdc pass
# (no line mapping) so the skill still works without Python.
#
# Usage: audit_mermaid.sh [--keep-png] [--out DIR] [--pptr FILE] <target.md | dir>
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$HERE/audit_mermaid.py" "$@"
fi

# ---- no-Python fallback (awk extraction, no per-block line numbers) ----
TARGET="${!#}"   # last arg
OUT="/tmp/mermaid-audit-$$"; mkdir -p "$OUT"
command -v mmdc >/dev/null 2>&1 || { echo "mmdc not found; install @mermaid-js/mermaid-cli" >&2; exit 2; }
PPTR="$OUT/pptr.json"; printf '{ "args": ["--no-sandbox","--disable-setuid-sandbox"] }\n' > "$PPTR"
mapfile -t MDS < <(if [ -d "$TARGET" ]; then find "$TARGET" -name '*.md'; else echo "$TARGET"; fi)
nok=0
for md in "${MDS[@]}"; do
  awk '/^```mermaid/{f=1;n++;next} /^```/{if(f)f=0} f{print > ("'"$OUT"'/b_" n ".mmd")}' "$md"
  for b in "$OUT"/b_*.mmd; do
    [ -e "$b" ] || continue
    if err=$(mmdc -p "$PPTR" -i "$b" -o "$b.png" 2>&1); then echo "$md  OK"; else echo "$md  SYNTAX  $(echo "$err" | grep -iE 'error|got ' | head -1)"; nok=$((nok+1)); fi
    rm -f "$b" "$b.png"
  done
done
[ "$nok" -gt 0 ] && exit 1 || exit 0
