# Interactive pi Run — EVAL-08

This is the owner-run acceptance half of Phase 22; the headless half is recorded in
[22-SMOKE-PI.md](22-SMOKE-PI.md). Only your own pi session counts for interactive acceptance.

## Results

Allowed Result values: `pass`, `fail (<observed>)`, `inconclusive (<reason>)` and, for L3 rows
only, `not run (owner declined)`; `not run (<reason>)` fails a required row; `pending (owner)`.

| Row | Step | Date | pi version | Observed | Result |
|---|---|---|---|---|---|
| C1 | Capture and trim the real RPC model list | - | - | - | pending (owner) |
| S1 | Start pi with the curated-config skill loaded | - | - | - | pending (owner) |
| S2 | Record session environment variable names | - | - | - | pending (owner) |
| S3 | Run the pi smoke from the session | - | - | - | pending (owner) |
| S4 | Check the protected-state snapshot | - | - | - | pending (owner) |
| S5 | Run inventory, recommend and dry run on ai-kit | - | - | - | pending (owner) |
| D9 | Confirm PI_CODING_AGENT in the session | - | - | - | pending (owner) |
| L3a | Real provider with pi.sonnet override and explicit extension | - | - | - | pending (owner) |
| L3b | Real provider without the override | - | - | - | pending (owner) |
| L3c | Real provider with one-shot --approve trust | - | - | - | pending (owner) |

## Before you start

- Open a terminal at the root of the checkout carrying Phase 22, confirmed with
  `git rev-parse --show-toplevel`; require a clean tree and `node` and `pi` on `PATH`.
- Every step uses the default pi agent directory only. Run this guard before each step:
  `test "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}" = "$HOME/.pi/agent" || { echo 'non-default PI_CODING_AGENT_DIR: unsupported'; false; }`.
  The snapshot protects the default directory only.
- The snapshot protects pi's `settings.json` and `trust.json` hashes and the `agents`,
  `extensions`, `skills` and `gsd-core` trees. It never reads, hashes or copies `auth.json`,
  `models.json`, `models-store.json` or `sessions/`. Pass `--host-rewrite` only for pi's own
  `settings.json` and `trust.json`; those lines report pi's own rewrites without failing.
- Pick a model you have credentials for before anything else: the old `openai-codex` default
  login is gone (D-10). The project-trust prompt is your consent; record your answer and whether
  it persisted.
- Print environment variable names only, never values. The raw RPC capture holds router base
  URLs and never leaves `tmp/`: trim it into the fixture and delete the raw file immediately.
  Do not commit or send the raw capture.

## Steps

### C1 (REQUIRED) — Capture the real RPC model list

Your own shell, before pi starts (D-04, ruling Q2, SPEC R1 acceptance and ROADMAP SC3):

```bash
test "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}" = "$HOME/.pi/agent" || { echo 'non-default PI_CODING_AGENT_DIR: unsupported'; false; }
mkdir -p tmp/p22/interactive
python3 tests/gsd_curated_eval.py snapshot --out tmp/p22/interactive/c1-before.json
printf '{"id":"1","type":"get_available_models"}\n' | pi --mode rpc --offline --no-session --no-extensions --no-skills --no-context-files --no-mcp > tmp/p22/interactive/rpc-raw.json
python3 .planning/phases/22-pi-live-validation/live/trim_pi_capture.py tmp/p22/interactive/rpc-raw.json tests/fixtures/pi_rpc_get_available_models_real.json --pi-version "$(pi --version)"
rm tmp/p22/interactive/rpc-raw.json
python3 -m unittest tests.test_ai_kit_spec -k trimmed_real_capture
python3 tests/gsd_curated_eval.py snapshot --check tmp/p22/interactive/c1-before.json --host-rewrite '<home>/.pi/agent/settings.json'
```

expect: `trimmed <n> models (...)`; record today's provider split (the SPEC's 2026-10-14
historical split was anthropic 17, opencode-go 31, radius 29, router-env 4, xai 4). The test
must report `OK` with no skip and the snapshot must end `snapshot ok`. Leave the trimmed fixture
uncommitted for the close-out.

### S1 (REQUIRED) — Start pi with the skill loaded

At the checkout root, after choosing a credentialed model:

```text
pi --skill skills/ai-kit-gsd-curated-config --model <provider>/<id>
```

Record pi's version and whether a project-trust prompt appeared, what you answered, and whether
the decision persisted (RESEARCH OQ4). Your answer is the consent action. In the bash tool, run
the default-agent-dir guard, take the S1 snapshot at
`tmp/p22/interactive/pi-before.json` (the same baseline S2 uses), and check it after the smoke
and the S5 dry run as directed in S4/S5.

expect: pi starts in the Phase 22 checkout with the curated-config skill available.

### S2 (REQUIRED) — Record session environment names

In pi's bash tool, run the guard first, then:

```bash
test "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}" = "$HOME/.pi/agent" || { echo 'non-default PI_CODING_AGENT_DIR: unsupported'; false; }
python3 tests/gsd_curated_eval.py snapshot --out tmp/p22/interactive/pi-before.json
env | cut -d= -f1 | grep -E '^(PI_|AI_AGENT|CLAUDE|CODEX|OPENCODE|CURSOR_|GROK_)' | sort > tmp/p22/interactive/pi-env-names.txt
printf 'Environment names only:\n'
cat tmp/p22/interactive/pi-env-names.txt
```

expect: `PI_CODING_AGENT` is listed (the D9 evidence), along with `PI_PROVIDER` and `PI_MODEL`
(RESEARCH A1). Never print environment values.

### S3 (REQUIRED) — Run the pi smoke from the session

In the pi bash tool, run the guard and then:

```bash
test "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}" = "$HOME/.pi/agent" || { echo 'non-default PI_CODING_AGENT_DIR: unsupported'; false; }
TMPDIR=/tmp python3 tests/gsd_curated_eval.py smoke --evidence-out tmp/p22/interactive/pi-smoke.md --artifacts-out tmp/p22/interactive/pi-artifacts --host-rewrite '<home>/.pi/agent/settings.json' --host-rewrite '<home>/.pi/agent/trust.json' > tmp/p22/interactive/pi-smoke.log 2>&1; rc=$?; echo "smoke exit=$rc" >> tmp/p22/interactive/pi-smoke.log
```

Do not pass `--host`: detecting pi from the session is evidence. Inspect the log and evidence.

expect: last line `smoke exit=0`; `host pi (detected)`; both scratch roots under `.pi/gsd-core`;
the pi chain line; `matrix ran: <n> checks, 5 hook probes`; protected state unchanged except
host-rewrite lines for pi's two files; and the log's `scratch work dir:` path for S4. Require
`seed: copied`: this is a read-only copy of `~/.gsd/defaults.json` into scratch HOME, not a
snapshot/hash read.

### S4 (REQUIRED) — Check the protected-state snapshot

Use the scratch work dir reported by S3:

```bash
test "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}" = "$HOME/.pi/agent" || { echo 'non-default PI_CODING_AGENT_DIR: unsupported'; false; }
python3 tests/gsd_curated_eval.py snapshot --check tmp/p22/interactive/pi-before.json --scratch-root <S3-work-dir> --host-rewrite '<home>/.pi/agent/settings.json' --host-rewrite '<home>/.pi/agent/trust.json'
```

expect: the final line is `snapshot ok`.

### S5 (REQUIRED) — Run inventory and a dry run on ai-kit

Ask pi exactly:

> Use the ai-kit-gsd-curated-config skill on this checkout: run inventory and recommend with profile adaptive and rigor standard and no cross-AI, show me the model_profile_overrides.pi.sonnet entry with its candidates, then plan-unset it and show the apply dry run. Do not run a real apply.

Then in the bash tool run the guard, inspect the results, and:

```bash
test "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}" = "$HOME/.pi/agent" || { echo 'non-default PI_CODING_AGENT_DIR: unsupported'; false; }
git status --porcelain
python3 tests/gsd_curated_eval.py snapshot --check tmp/p22/interactive/pi-before.json --scratch-root <S3-work-dir> --host-rewrite '<home>/.pi/agent/settings.json' --host-rewrite '<home>/.pi/agent/trust.json'
```

expect: inventory says `pi` detected; `pi.sonnet` candidates are bare ids served by the session's
real provider (no `provider/` prefix); the dry run lists its rows; `git status --porcelain`
prints nothing and the snapshot ends `snapshot ok`. This inventory refreshes ai-kit's own caches
and runs pi's RPC listing on the real agent dir, as the skill does on any pi host.

### D9 (REQUIRED) — Confirm the pi session marker

Use S2's names-only environment output.

expect: `PI_CODING_AGENT` is present; record its presence in this row. Do not record variable
values.

### L3a (OPTIONAL) — Override enabled, explicit extension

Each L3 arm is optional and spends one tiny real call; running it is your approval (D-03, ruling
Q3). Prefer a direct provider such as anthropic or xai (RESEARCH OQ3). In your own shell, use a
scratch project and throwaway HOME. Resolve node before changing HOME, and use the existing cached
installer found by the 22-01 lookup one-liner:

```bash
P=$(mktemp -d)
git init -q "$P"
NODE=$(node -p process.execPath)
# Set INSTALLER to the existing cached installer path found by the 22-01 lookup one-liner.
mkdir -p "$P/.home"
(cd "$P" && env -i PATH="$(dirname "$NODE"):$PATH" HOME="$P/.home" "$NODE" "<installer>/bin/install.js" --pi --local --no-legacy-cleanup)
```

In `$P`, use the installed `gsd-tools` flow to create `.planning/config.json` with
`model_profile_overrides.pi.sonnet` set to a second bare id from the same provider. Do not hand-edit
the config. Take a snapshot before the run. Then run:

```bash
pi --mode json -p --no-session -ne -e .pi/extensions/gsd.js --model <provider>/<selected> "Reply with the single word ok." > "$P/l3a.jsonl"
```

Immediately before invoking pi, run the default-agent-dir guard and
`python3 tests/gsd_curated_eval.py snapshot --out "$P/pi-before.json"`. The pi invocation for
this optional real-provider arm uses the owner's normal pi agent dir for credentials; it does not
copy or inspect credential files. Print only the `model` and `responseModel` fields from message
events using a short Python reader; then run
`python3 tests/gsd_curated_eval.py snapshot --check "$P/pi-before.json" --host-rewrite '<home>/.pi/agent/settings.json' --host-rewrite '<home>/.pi/agent/trust.json'`
and remove `$P`.

expect: `pass` when `responseModel` names the steered id; `inconclusive (provider does not echo the served model)` when it is absent; `fail (served model unchanged with the override)` when the provider echoes the selected id.

### L3b (OPTIONAL) — Override absent

Use a fresh scratch project and throwaway HOME as above; set up the same provider and selected
id but leave `pi.sonnet` unset. Immediately before invoking pi, run the default-agent-dir guard
and `python3 tests/gsd_curated_eval.py snapshot --out "$P/pi-before.json"`. Run the same JSON
command as L3a, print only the two message fields, then run
`python3 tests/gsd_curated_eval.py snapshot --check "$P/pi-before.json" --host-rewrite '<home>/.pi/agent/settings.json' --host-rewrite '<home>/.pi/agent/trust.json'`
and remove the scratch project.

expect: `pass` when no `responseModel` differs from the selection. An observed different served
model is `fail (<observed>)`; an absent echo is inconclusive rather than proof of no change.

### L3c (OPTIONAL) — Override with one-shot approval

Use another fresh scratch project and throwaway HOME. Restore the same `pi.sonnet` override,
then immediately before invoking pi run the default-agent-dir guard and
`python3 tests/gsd_curated_eval.py snapshot --out "$P/pi-before.json"`. Run the call with one-shot
extension approval instead of explicit extension loading:

```bash
pi --mode json -p --no-session --approve --model <provider>/<selected> "Reply with the single word ok." > "$P/l3c.jsonl"
```

Print only `model` and `responseModel` from message events, then run
`python3 tests/gsd_curated_eval.py snapshot --check "$P/pi-before.json" --host-rewrite '<home>/.pi/agent/settings.json' --host-rewrite '<home>/.pi/agent/trust.json'`
and remove `$P`.

expect: `pass` when `responseModel` names the steered id; `inconclusive (provider does not echo the served model)` when absent; `fail (served model unchanged with the override)` when it echoes the selected id.

## Send back

Return the C1 trimmer line and test output, `pi-env-names.txt`, the last 20 lines of the S3 log and
`pi-smoke.md`, S4 and S5 outputs, the S5 `pi.sonnet` entry and candidates, and the L3 model fields.
Before sending, run:

```bash
python3 tests/gsd_curated_eval.py secret-scan tmp/p22/interactive
```

Do not return the raw RPC capture. The snapshot is the only reader that hashes or prints protected
real-home contents.

## Orchestrator close-out

1. Fill `## Results` from the returned artifacts; every required row must be exactly `pass`, and
every L3 row must be resolved as `pass`, `inconclusive (...)`, `fail (...)` or
`not run (owner declined)`.
2. Record the interactive results in `22-SMOKE-PI.md` under `## Interactive run (owner)`.
3. When C1, S1-S5 and D9 pass, plan and execute the close-out through `/gsd-plan-phase 22 --gaps`:
   - Commit the trimmed fixture with its now-running test.
   - Lift the SKILL.md pi row to `validated from the user's interactive pi <version> session (22-INTERACTIVE-PI.md)`, retaining the verdict sentence; update the README row and test pins in that same commit.
   - Upgrade `_LABEL_PI` and the `detect_current_runtime` docstring to `live-verified (Phase 22) ...`, with the runtimes-table label test.
   - Change the verdict to `session-steer (live L3 on <provider>)` only when an override-enabled L3 arm passed (L3a or L3c). L3b runs without the override, so a pass there is a baseline, not steering evidence.
   - Re-run skill-judge on the new digest; check off EVAL-08 in `.planning/REQUIREMENTS.md` and the ROADMAP Phase 22 criteria.
4. An L3 `fail` refutes D-02: open a decimal phase, never a close-out edit (SPEC R7).
5. Run `make test && make validate`.
6. Confirm `python3 .planning/phases/22-pi-live-validation/live/check_pi_live.py .planning/phases/22-pi-live-validation/22-INTERACTIVE-PI.md` exits 0.
7. Run `/gsd-verify-work 22`.
