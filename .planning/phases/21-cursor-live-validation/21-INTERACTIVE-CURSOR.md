# Interactive Cursor Run — EVAL-07

This run is the SPEC R1 (EVAL-07 interactive) acceptance evidence; the headless run in
[21-SMOKE-CURSOR.md](21-SMOKE-CURSOR.md) only prepared it. Only your own cursor TUI run counts;
return the artifacts and observations listed below.

## Before you start

- Open a terminal at the root of the checkout carrying the Phase 21 harness: branch
  `gsd/v1.3-curated-config-v2`, found with `git rev-parse --show-toplevel` inside it, or `main`
  once this branch is merged. The main checkout before the merge lacks `matrix --host cursor`
  and `tmp/p21`; an old harness there is not valid.
- Confirm `git status --porcelain` is empty and `node` is on `PATH`.
- The smoke finds the installer copy itself. Pass `--installer-dir <dir>` only if it reports
  `no cached @opengsd/gsd-core`.
- Nothing here edits your global config: the smoke installs only in scratch projects under a
  throwaway HOME and checks your `~/.cursor`, `~/.codex`, `~/.config/opencode`, `~/.claude` and
  `~/.gsd` allowlist before and after. The `~/.cursor` protected entries are
  `cli-config.json` (a strict byte entry), `hooks.json` (a strict byte entry) and the
  `agents`/`skills` name listings (names only, never contents).
- Cursor rewrites `~/.cursor/cli-config.json` during a session (`selectedModel`,
  `modelSelectionHistory`, `privacyCache`, `authInfo`), so that one strict entry is checked
  differently here: steps 3 and 4 pass `--host-rewrite '<home>/.cursor/cli-config.json'`,
  which reports a byte change of that one file instead of failing on it, and step 2 records a
  sha256 of the three user-owned keys (`modelParameters`, `subagentModels`,
  `exploreSubagentModel`; never `authInfo`) that step 4 compares again. Every other protected
  entry stays strict.
- What that pair proves, and no more: an equal digest shows the three user-owned keys kept
  their values, and `snapshot ok` shows every other protected entry is unchanged within its
  documented hash, listing or normalization scope. It does not prove the rest of
  `cli-config.json` untouched (cursor rewrites those keys), and it does not say who wrote a
  reported byte change — a `changed (host-rewrite)` line is reported, not attributed.
- Always start cursor as `command cursor-agent --model <id>`: `command` runs the PATH binary
  and skips your shell function (which injects `--model gpt-5.6-sol-high` when no `--model` is
  given), and the explicit flag keeps cursor's stored `selectedModel` out of the choice.
- This run supports the default config dir only: the snapshot protects
  `~/.cursor/cli-config.json` and the digest reads the same file, so a non-default
  `CURSOR_CONFIG_DIR` is rejected by step 2.

## Steps

1. REQUIRED — **Start cursor-agent at the checkout root**

```text
Start cursor as: command cursor-agent --model composer-2.5
(any non-fast id you prefer; `command` and the explicit --model are what matter), then use its
shell tool for the commands below exactly as written. Never print environment variable values.
```

expect: cursor is running in the checkout identified by `git rev-parse --show-toplevel`.

2. REQUIRED — **Fresh baseline, names-only env list, user-keys digest**

```text
Run exactly: test "${CURSOR_CONFIG_DIR:-$HOME/.cursor}" = "$HOME/.cursor" || { echo 'non-default CURSOR_CONFIG_DIR: unsupported by this run'; false; } && mkdir -p tmp/p21/interactive && python3 tests/gsd_curated_eval.py snapshot --out tmp/p21/interactive/cursor-before.json && env | cut -d= -f1 | grep -E '^(CODEX|OPENCODE|AI_AGENT|AGENT|CLAUDE|PI_|CURSOR_|GROK_)' | sort > tmp/p21/interactive/cursor-env-names.txt && python3 -c 'import json, hashlib, os; p = os.path.join(os.path.expanduser("~"), ".cursor", "cli-config.json"); d = json.load(open(p, encoding="utf-8")); s = {k: d.get(k) for k in ("modelParameters", "subagentModels", "exploreSubagentModel")}; print(hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest())' > tmp/p21/interactive/cursor-userkeys-before.txt && printf 'Names only:\n' && cat tmp/p21/interactive/cursor-env-names.txt && cat tmp/p21/interactive/cursor-userkeys-before.txt. Never print an environment value.
```

(The first test is the default-config-dir guard: the snapshot and the digest both read
`~/.cursor/cli-config.json`, so a custom `CURSOR_CONFIG_DIR` would make the two checks protect
different files; its message, if printed, is sent back and the run stops there.)

expect: no `non-default CURSOR_CONFIG_DIR` line (if it appears, nothing after the guard ran: no
`tmp/p21/interactive/cursor-before.json` exists, and the run stops there), then `snapshot
written`, the recorded headless names from `21-SMOKE-CURSOR.md ## Env names` —
`AGENT_TRANSCRIPTS`, `CLAUDE_CODE_BRIDGE_SESSION_ID`, `CLAUDE_CODE_CHILD_SESSION`,
`CLAUDE_CODE_EXECPATH`, `CLAUDE_CODE_MESSAGING_SOCKET`, `CLAUDE_CODE_MESSAGING_TOKEN`,
`CLAUDE_CODE_SESSION_ATTENDED`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_EFFORT`, `CLAUDE_JOB_DIR`,
`CLAUDE_PID`, `CURSOR_AGENT`, `CURSOR_CONFIG_DIR`, `CURSOR_CONVERSATION_ID`,
`CURSOR_INVOKED_AS`, `CURSOR_REQUEST_ID`, `CURSOR_RIPGREP_PATH`, `PI_MODEL`, `PI_OFFLINE`,
`PI_PROVIDER`, `PI_REASONING_LEVEL`, `PI_SESSION_FILE`, `PI_SESSION_ID`, `PI_SKIP_VERSION_CHECK`
— listed inline (with `CURSOR_AGENT` named explicitly as the one that decides the label), and a
64-hex digest (a key-integrity reference for step 4, nothing more). The baseline follows TUI
startup so a startup rewrite is not mistaken for a regression. Report any name difference; it
drives the `_LABEL_CURSOR` TUI confirmation.

3. REQUIRED — **Run the smoke and retain its artifacts**

```text
Run exactly: TMPDIR=/tmp python3 tests/gsd_curated_eval.py smoke --evidence-out tmp/p21/interactive/cursor-smoke.md --artifacts-out tmp/p21/interactive/cursor-artifacts --host-rewrite '<home>/.cursor/cli-config.json' > tmp/p21/interactive/cursor-smoke.log 2>&1; rc=$?; echo "smoke exit=$rc" >> tmp/p21/interactive/cursor-smoke.log; then print the log and the evidence file, and report the value of rc.
```

(`TMPDIR=/tmp` because the smoke refuses a work dir inside the repo; `--host-rewrite` because
cursor may rewrite its own config while the smoke runs; `rc` is the smoke's own status, the
same form 21-04's `run-smoke.sh` uses.)

expect: `smoke exit=0` as the LAST line of the log,
`host cursor (detected)`, both scratch roots under `.cursor/gsd-core`, the `resolve-model only`
line per project (the cursor installer bakes no model line), `matrix ran: 420 checks`,
`protected set unchanged` `pass` (a `changed (host-rewrite) <home>/.cursor/cli-config.json`
detail is a reported rewrite of cursor's own file, not attributed to a writer, and is fine; any
other label in that detail is a failure; the evidence `## Protected set` shows `- unchanged` or
`- changed (host-rewrite): <home>/.cursor/cli-config.json`, never a plain `- changed:` line);
artifacts at `cursor-artifacts/<label>/{plan.json,config.json,resolve-model.json,baked.json}`;
the log's `scratch work dir: <path> (deleted)` line, whose path step 4 needs.

4. REQUIRED — **Check the baseline and the user-keys digest**

```text
Run exactly: python3 tests/gsd_curated_eval.py snapshot --check tmp/p21/interactive/cursor-before.json --scratch-root <the step-3 work dir path> --host-rewrite '<home>/.cursor/cli-config.json'
then run the step-2 digest one-liner again with its output redirected to
tmp/p21/interactive/cursor-userkeys-after.txt, then:
cmp tmp/p21/interactive/cursor-userkeys-before.txt tmp/p21/interactive/cursor-userkeys-after.txt && echo user-keys unchanged
```

expect: `snapshot ok` as the last line of the check (possibly preceded by one
`changed (host-rewrite) <home>/.cursor/cli-config.json` line: a byte change of cursor's own
file, reported by the exemption and not failed) AND `user-keys unchanged`. That pair is the
pass, and it means exactly this: your three user-owned keys kept their values and every other
protected entry is unchanged within its documented hash, listing or normalization scope; it does
not prove the rest of `cli-config.json` untouched, and it does not say who wrote a reported
change. A `changed` line for any other label, a missing `snapshot ok`, or a digest difference
is returned verbatim as a guard failure to analyse, never dismissed.

5. OPTIONAL — **Native per-call model selection (ROADMAP SC5)**

From your own shell, not inside the TUI, and only after step 4: the probe runs under your real
HOME and rewrites cursor's config, so it stays outside the checked window. One paste, three
lines:

```sh
W=$(mktemp -d) && P0=$(pgrep -f 'index.js worker-server' | sort); AIKIT_P21_PROBE=1 command cursor-agent -p --trust --model composer-2.5 --output-format stream-json --workspace "$W" "Use the Task tool with subagent_type generalPurpose and model grok-4.7-medium to reply with the single word PONG, then reply PONG." > "$W/probe.jsonl"; echo "cursor exit=$?"
python3 -c 'import json, sys; hits = []; walk = lambda o: (hits.append(o.get("model")) if isinstance(o, dict) and "subagentType" in o else None, [walk(v) for v in (o.values() if isinstance(o, dict) else o if isinstance(o, list) else [])]); [walk(json.loads(l)) for l in open(sys.argv[1]) if l.strip().startswith("{")]; print("Task call model:", hits or "no Task call found")' "$W/probe.jsonl"; rm -rf "$W"
for p in $(comm -13 <(printf '%s\n' "$P0") <(pgrep -f 'index.js worker-server' | sort)); do if tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null | grep -qx 'AIKIT_P21_PROBE=1'; then o=probe-owned; else o=unidentified; fi; ps -o pid=,etimes=,args= -p "$p" | sed "s/^/$o /"; done
```

(`command` runs the PATH binary, never your shell function; explicit `--model`; a scratch
workspace so no project agents load; the stream goes to a file so the CLI's own exit status is
what `cursor exit=` prints; the python reads `model` only from the stream-json object carrying
`subagentType`, the Task call as the D-01 spike recorded it; the last line LISTS the
`worker-server` processes that appeared while the probe ran — pid, age in seconds, args — and
kills nothing.)

expect: `cursor exit=0`, `Task call model: ['grok-4.7-medium']` (the Task call
honoured the per-call model) or `no Task call found`, and a listing that is empty or whose lines
start with `probe-owned` or `unidentified`: a `probe-owned` pid is the probe's leftover (its
environment carries the probe's marker `AIKIT_P21_PROBE=1` — that environ match is the
ownership proof, never age) and you may kill it by pid from your own shell; an `unidentified`
pid is a candidate this script cannot attribute (a concurrent cursor session's worker looks
the same) — leave it alone unless you know it is yours. Why optional: SC5 is an OR; the
session-default-only branch is already pinned by `native_selectors == ()` and its unit test
(21-01). A positive result can only upgrade the label later, through its own one-module change.

## Send back

Return `cursor-env-names.txt`, `cursor-userkeys-before.txt` and `cursor-userkeys-after.txt`
(digests only), `cursor-smoke.md`, `cursor-smoke.log`, the full `cursor-artifacts/` directory,
the `snapshot --check` output, and (if run) the step-5 `Task call model` line and worker
listing.

## What happens next

The artifacts (plan, resulting config, resolve-model output, baked output) and log will be
analysed, and `21-SMOKE-CURSOR.md` will receive the interactive result.
EVAL-07's interactive confirmation (SPEC R1) is checked off only when steps 1-4 return green.
The TUI names confirm or revise the cursor env-signal label: `TUI confirmation pending` in
`skills/ai-kit-spec-review/ai_kit_spec/detection.py` becomes the TUI outcome (one product
module plus its table test, in-phase under R8). A name absent from the TUI list is dropped;
any name added or dropped updates every mirror and `tests/test_ai_kit_spec_runtimes_table.py`
in one commit. The SKILL.md cursor row's `pending` interactive note is removed in the same
commit as the result.
