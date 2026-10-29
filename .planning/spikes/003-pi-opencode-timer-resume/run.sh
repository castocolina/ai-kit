#!/usr/bin/env bash
# Spike 003: the same timer re-entry for pi (--session-id) and opencode (run --session), on the
# owner's router lane router-env/my-coding. Throwaway sessions in a scratch cwd; no config edits.
set -uo pipefail
OUT="${1:?usage: run.sh <log dir>}"; mkdir -p "$OUT"
S=$(mktemp -d); echo "scratch=$S" > "$OUT/env.txt"
PI=$(command -v pi); OC=$(command -v opencode); M=router-env/my-coding
clean=(env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u PI_CODING_AGENT -u OPENCODE)
cd "$S" || exit 2
PSID=$(python3 -c 'import uuid; print(uuid.uuid4())'); echo "pi_sid=$PSID" >> "$OUT/env.txt"
"${clean[@]}" "$PI" -p --model "$M" --session-id "$PSID" --no-skills --no-extensions \
  "Remember the word LOQUAT. Reply with OK only." < /dev/null > "$OUT/pi-seed.txt" 2> "$OUT/pi-seed.err"
echo "pi_seed_rc=$?" >> "$OUT/env.txt"
"${clean[@]}" "$OC" run --model "$M" --format json "Remember the word MEDLAR. Reply with OK only." \
  < /dev/null > "$OUT/oc-seed.jsonl" 2> "$OUT/oc-seed.err"; echo "oc_seed_rc=$?" >> "$OUT/env.txt"
OSID=$(python3 -c '
import json,sys
for l in open(sys.argv[1]):
    try: e=json.loads(l)
    except ValueError: continue
    s=e.get("sessionID") or (e.get("part") or {}).get("sessionID")
    if s: print(s); break' "$OUT/oc-seed.jsonl"); echo "oc_sid=$OSID" >> "$OUT/env.txt"
Q='What word did I ask you to remember? Reply with the word only.'
systemd-run --user --quiet --unit="aikit-spike26c-pi-$$" --on-active=10 --working-directory="$S" \
  /bin/sh -c "'$PI' -p --model '$M' --session-id '$PSID' --no-skills --no-extensions '$Q' < /dev/null > '$OUT/pi-timer.txt' 2> '$OUT/pi-timer.err'; echo \$? > '$OUT/pi-timer.rc'"
systemd-run --user --quiet --unit="aikit-spike26c-oc-$$" --on-active=10 --working-directory="$S" \
  /bin/sh -c "'$OC' run --model '$M' --format json --session '$OSID' '$Q' < /dev/null > '$OUT/oc-timer.jsonl' 2> '$OUT/oc-timer.err'; echo \$? > '$OUT/oc-timer.rc'"
for _ in $(seq 1 60); do [ -f "$OUT/pi-timer.rc" ] && [ -f "$OUT/oc-timer.rc" ] && break; sleep 3; done
echo "pi_timer_rc=$(cat "$OUT/pi-timer.rc" 2>/dev/null || echo missing) oc_timer_rc=$(cat "$OUT/oc-timer.rc" 2>/dev/null || echo missing)" >> "$OUT/env.txt"
