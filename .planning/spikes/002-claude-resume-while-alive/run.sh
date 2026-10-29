#!/usr/bin/env bash
# Spike 002: what does `claude -p --resume <id>` do while another process still runs that session?
# A throwaway session runs a 40 s tool call; a timer-fired resume of the same id starts 10 s in.
set -uo pipefail
OUT="${1:?usage: run.sh <log dir>}"; mkdir -p "$OUT"
S=$(mktemp -d); echo "scratch=$S" > "$OUT/env.txt"
CLAUDE=$(command -v claude)
clean=(env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_SSE_PORT -u CLAUDE_CODE_SESSION_ID)
cd "$S" || exit 2
"${clean[@]}" "$CLAUDE" -p "Remember the word PERSIMMON. Reply with OK only." --model haiku --output-format json \
  < /dev/null > "$OUT/seed.json" 2> "$OUT/seed.err"
SID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["session_id"])' "$OUT/seed.json")
echo "sid=$SID" >> "$OUT/env.txt"
# the "original" process: busy for about 40 s inside the session
( "${clean[@]}" "$CLAUDE" -p --resume "$SID" "Run the shell command: sleep 40. Then reply with BUSY-DONE only." \
    --model haiku --output-format json --allowedTools "Bash(sleep:*)" \
    < /dev/null > "$OUT/busy.json" 2> "$OUT/busy.err"; echo $? > "$OUT/busy.rc"; date +%s > "$OUT/busy.end" ) &
date +%s > "$OUT/busy.start"
UNIT="aikit-spike26b-$$"
systemd-run --user --quiet --unit="$UNIT" --on-active=10 --working-directory="$S" \
  /bin/sh -c "date +%s > '$OUT/wake.start'; '$CLAUDE' -p --resume '$SID' 'What word did I ask you to remember? Reply with the word only.' --model haiku --output-format json < /dev/null > '$OUT/wake.json' 2> '$OUT/wake.err'; echo \$? > '$OUT/wake.rc'; date +%s > '$OUT/wake.end'"
wait
for _ in $(seq 1 40); do [ -f "$OUT/wake.rc" ] && break; sleep 3; done
# what the session holds afterwards: one more resume asks for the last two replies it remembers
"${clean[@]}" "$CLAUDE" -p --resume "$SID" "List, in order, the replies you gave in this conversation, one per line." \
  --model haiku --output-format json < /dev/null > "$OUT/after.json" 2> "$OUT/after.err"
