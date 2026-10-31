# Resumable state file

`SKILL.md` Step 1 (a probe-time `quota_exhausted` stop) and Step 3 (a cross-AI stop) send you
here to write the durable record the owner resumes from.

**Who reads that file.** This skill never reads it back. Its `resume_via` field says how to
resume: `skill` (Step 1's `quota_exhausted`, `RESUME_VIA=skill`) means the caller re-invokes
this skill with `cwd` from `project_path`, `phase_id` from `phase_id` and the prompt file from
`phase_prompt_file`; `gsd-execute-phase` (Step 3's cross-AI stop) means the owner runs
`/gsd-execute-phase <phase_id>` with the hook unchanged (after a hard-tier stop, first deleting
the state file the runner named) and never re-invokes this skill.

Run as one `Bash` call, with `$GSD_SHIM`, `$TOOLS_PY`, `$CWD`, `$GSD_CONFIG_PATH`, `$PHASE_ID`
and `$PHASE_PROMPT_FILE` replaced by the literal values Steps 0 and 1 printed. Replace the
first line's placeholder with the one value for the stop you are on:

- Step 1's probe-time `quota_exhausted` stop: `RESUME_VIA=skill`
- Step 3's cross-AI stop: `RESUME_VIA=gsd-execute-phase`

The guard on the second line exits 2 before anything is written when the placeholder is still
there (or any other value), so a verbatim copy cannot record the wrong `resume_via`.

```bash
RESUME_VIA="<replace with skill or gsd-execute-phase>"
case "$RESUME_VIA" in skill|gsd-execute-phase) ;; *)
  echo "ai-kit-spec-execute-gsd: set RESUME_VIA to skill or gsd-execute-phase; nothing written"
  exit 2;; esac
PROJECT_KEY="$(python3 -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:12])" "$CWD")"
QUOTA_PATH="$(python3 "$TOOLS_PY" cache-path --kind quota)" || exit 2  # else dirname yields "."
RESUME_STATE_PATH="$(dirname "$QUOTA_PATH")/gsd-resume-${PROJECT_KEY}-${PHASE_ID}.json"
STATE_JSON="$(python3 -c '
import json, sys
print(json.dumps({"framework": "gsd", "project_path": sys.argv[1],
                   "config_path": sys.argv[2], "phase_id": sys.argv[3],
                   "phase_prompt_file": sys.argv[4], "resume_via": sys.argv[5]}))' \
  "$CWD" "$GSD_CONFIG_PATH" "$PHASE_ID" "$PHASE_PROMPT_FILE" "$RESUME_VIA")"
python3 "$GSD_SHIM" write-resumable-state --path "$RESUME_STATE_PATH" --state-json "$STATE_JSON" >/dev/null || exit 1
printf 'RESUME_STATE_PATH=%s\n' "$RESUME_STATE_PATH"
```

Record the printed `RESUME_STATE_PATH` as a literal value: Step 3's re-arm and the quota-wake
prompt use it.
