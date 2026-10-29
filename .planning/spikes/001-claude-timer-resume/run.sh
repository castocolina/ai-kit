#!/usr/bin/env bash
# Spike 001: does `claude -p --resume <id>`, fired by a transient systemd user timer, re-enter the
# recorded session in its directory? Throwaway session, cheapest model, scratch cwd; no CLI config
# is edited and no unit file is written (systemd-run --user transient units live in the runtime dir).
set -uo pipefail
OUT="${1:?usage: run.sh <log dir>}"; mkdir -p "$OUT"
S=$(mktemp -d); echo "scratch=$S" > "$OUT/env.txt"
CLAUDE=$(command -v claude)
clean=(env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_SSE_PORT -u CLAUDE_CODE_SESSION_ID)
cd "$S" || exit 2
# 1. seed a throwaway session that remembers a word
"${clean[@]}" "$CLAUDE" -p "Remember the word KUMQUAT. Reply with OK only." --model haiku --output-format json \
  > "$OUT/seed.json" 2> "$OUT/seed.err"; echo "seed_rc=$?" >> "$OUT/env.txt"
SID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["session_id"])' "$OUT/seed.json")
echo "sid=$SID" >> "$OUT/env.txt"
# 2. resume it from a transient user timer in the same directory
UNIT="aikit-spike26-$$"
systemd-run --user --quiet --unit="$UNIT" --on-active=15 --working-directory="$S" \
  /bin/sh -c "'$CLAUDE' -p --resume '$SID' 'What word did I ask you to remember? Reply with the word only.' --model haiku --output-format json > '$OUT/timer.json' 2> '$OUT/timer.err'; echo \$? > '$OUT/timer.rc'"
echo "unit=$UNIT" >> "$OUT/env.txt"
# 3. control: resume the same id from a different directory, in the foreground
D=$(mktemp -d)
( cd "$D" && "${clean[@]}" "$CLAUDE" -p --resume "$SID" 'What word did I ask you to remember? Reply with the word only.' --model haiku --output-format json \
  > "$OUT/otherdir.json" 2> "$OUT/otherdir.err"; echo $? > "$OUT/otherdir.rc" )
for _ in $(seq 1 30); do [ -f "$OUT/timer.rc" ] && break; sleep 3; done
echo "timer_rc=$(cat "$OUT/timer.rc" 2>/dev/null || echo missing)" >> "$OUT/env.txt"
systemctl --user is-active "$UNIT.timer" "$UNIT.service" >> "$OUT/env.txt" 2>&1 || true
rmdir "$D" 2>/dev/null || true
