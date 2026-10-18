# Interactive Opencode Run — EVAL-05

This run is the EVAL-05 evidence; the headless runs in [20-SMOKE-OPENCODE.md](20-SMOKE-OPENCODE.md) only prepared it.
Only your own Opencode TUI run counts; return the artifacts and observations listed below.

## Before you start

- Open a terminal at the root of the checkout carrying the Phase 20 harness: branch `gsd/v1.3-curated-config-v2`, found with `git rev-parse --show-toplevel` inside it, or `main` once this branch is merged. The main checkout before merge lacks these smoke flags and `tmp/p20`; an old harness there is not valid.
- Confirm `git status --porcelain` is empty and `node` is on `PATH`.
- The smoke finds the installer copy itself. Pass `--installer-dir <dir>` only if it reports `no cached @opengsd/gsd-core`.
- Nothing here edits global config. The smoke installs only in scratch projects under a throwaway HOME and checks the `~/.codex`, `~/.config/opencode`, and `~/.gsd` allowlist before and after.

## Steps

1. REQUIRED — **Start Opencode at the checkout root**

```text
Start the Opencode TUI in this checkout root, then use its shell tool for the following commands exactly as written. Do not print environment variable values.
```

expect: Opencode is running in the branch checkout (or merged `main`) identified by `git rev-parse --show-toplevel`.

2. REQUIRED — **Fresh baseline and names-only environment list**

```text
Run exactly: mkdir -p tmp/p20/interactive && python3 tests/gsd_curated_eval.py snapshot --out tmp/p20/interactive/opencode-before.json && env | cut -d= -f1 | grep -E '^(CODEX|OPENCODE|AI_AGENT|AGENT|CLAUDE|PI_|CURSOR_|GROK_)' | sort > tmp/p20/interactive/opencode-env-names.txt && printf 'Names only:\n' && cat tmp/p20/interactive/opencode-env-names.txt. Never print an environment value.
```

expect: `snapshot written`, then the recorded headless names including `AGENT`, `AI_AGENT`, `OPENCODE`, and `OPENCODE_SESSION_ID` (plus other matching names). The baseline follows TUI startup. Report any difference under D-04. Names only.

3. REQUIRED — **Run smoke and retain its artifacts**

```text
Run exactly: python3 tests/gsd_curated_eval.py smoke --evidence-out tmp/p20/interactive/opencode-smoke.md --artifacts-out tmp/p20/interactive/opencode-artifacts > tmp/p20/interactive/opencode-smoke.log 2>&1; echo "smoke exit=$?" >> tmp/p20/interactive/opencode-smoke.log; then print the log and evidence file.
```

expect: `smoke exit=0`, `host opencode (detected)`, `scope: local`, `all equal`, `matrix ran: 420 checks`, and `protected set unchanged: pass`; artifacts exist at `opencode-artifacts/<label>/{plan.json,config.json,resolve-model.json,baked.json}`. The log includes `scratch work dir: <path> (deleted)`.

4. REQUIRED — **Check the baseline**

```sh
python3 tests/gsd_curated_eval.py snapshot --check tmp/p20/interactive/opencode-before.json --scratch-root <the work-dir path printed by step 3>
```

expect: `snapshot ok`. Return any `changed` line verbatim as a guard failure; do not dismiss it.

5. OPTIONAL — **Native per-call model selection (ROADMAP SC3)**

```text
Ask Opencode to spawn a subagent that must run on model <id> and have it reply with the model it is running on. Return the reply text only.
```

Why optional: SC3 is an OR; the session-default branch is already pinned by `native_selectors == ()` and its unit test (20-06). This probe can only upgrade the label later.

6. REQUIRED — **Opencode review-lane mechanics (D-11; two trials per route)**

(a) From your shell at the checkout root, set a persistent output path, then run the keep-scratch smoke:

```sh
OUT="$PWD/tmp/p20/interactive"; mkdir -p "$OUT"; python3 tests/gsd_curated_eval.py smoke --host opencode --keep-scratch --evidence-out "$OUT/opencode-keep.md"
```

expect: a kept `scratch work dir: <path> (kept)`; `$DIR/project-a` contains the project-local GSD install and baked agents for Steps 6–7. Save its printed work-dir path in your shell as `DIR`.

(b) Make the kept project reviewable for phase 20. This copies project metadata and all phase plans there:

```sh
cp .planning/PROJECT.md .planning/ROADMAP.md .planning/STATE.md "$DIR/project-a/.planning/" && mkdir -p "$DIR/project-a/.planning/phases/20-live-validation-on-codex-opencode" && cp .planning/phases/20-live-validation-on-codex-opencode/20-0*-PLAN.md "$DIR/project-a/.planning/phases/20-live-validation-on-codex-opencode/"
```

expect: project metadata and phase plan files are present in the kept project.

(c) Route 1, two trials. From `$DIR/project-a`, start a dedicated TUI with `opencode --standalone`, then run `/gsd-review --phase 20 --opencode` twice. Do not use plain `opencode`: that may attach to the managed shared service and miss scratch commands. If `/gsd-review` is unknown, record `blocked (prerequisite: /gsd-review not loaded)`. After each trial return `ran`, `skipped (<the self-skip line>)`, or `blocked (prerequisite: <message>)`, plus the `AIKIT-XAI`/review-lane status lines verbatim. A blocked trial is not an outcome: copy the specifically missing init file from this checkout to the same relative path under `$DIR/project-a/.planning/`, then repeat until there is no blocked result.

(d) Route 2, two trials. In `$DIR/project-a/.planning/config.json`, set `review.default_reviewers` to `["opencode"]`, run `/gsd-review --phase 20` twice in the same standalone TUI, and return the same outcome/status lines. Restore the key afterward. Any blocked trial must be fixed and repeated, not counted; return four unblocked outcomes total. The kept scratch project can be deleted after Step 7.

The project needs an Opencode-local install and a phase with at least one plan. If the kept project cannot be made reviewable, use your own GSD project with `.opencode/gsd-core` and a phase `N` containing a plan, substituting `--phase N` in all four trials. The review verdict is immaterial; report lane mechanics. Why interactive: gsd-core's self-skip is LLM-judged (`auto`) on Opencode, so every trial is a model call from your session. The policy half (recommendation excludes the host; plan editing refuses it) is already enforced and tested; a user-owned manual `review.reviewer_instances` route is distinct from these mechanics trials. A lane that runs against its host's own session is the D-11 finding, not a product failure.

expect: four unblocked `ran`/`skipped (...)` outcomes with status lines; no blocked result remains.

7. REQUIRED — **R5 loader precedence from the kept scratch project**

Use the kept `$DIR/project-a` from Step 6 and keep `$OUT` set. This is an actual loader observation for `gsd-planner`, not model self-report.

(a) Read its baked line:

```sh
grep -m1 '^model:' "$DIR/project-a/.opencode/agents/gsd-planner.md"
```

(b) First observation, loader JSON events. Check whether this installed command supports `--agent`, then run it from the project. Preserve the output under `$OUT` even though the working directory changes:

```sh
opencode run --help | grep -c -- '--agent'
```

If the number is greater than zero:

```sh
cd "$DIR/project-a" && opencode run --standalone --agent gsd-planner --format json "reply with the single word ok" > "$OUT/opencode-agent-run.jsonl" 2>&1; cd -
grep -oE '"(providerID|modelID|provider|model)" *: *"[^"]*"' "$OUT/opencode-agent-run.jsonl" | sort -u
```

The event field format is unverified until observed. If exactly one distinct model id is present (provider and model fields together identify one model), compare it with the baked `model:` line: equal means `precedence proved (run --agent)`; different means `precedence contradicted (<loader model> vs <baked>)`. Several distinct ids mean `precedence pending (multiple model fields)`; return all of them. If no field appears, record `loader field not observed in run --format json` and take the second form.

Second form, only when no loader model field appeared: `opencode debug agents` is a listing without `--standalone`, so this reads the already-running shared service, which serves its boot-time config. Save the result and return it marked `listing via shared service`:

```sh
opencode debug agents > "$OUT/opencode-debug-agents.txt" 2>&1
```

Compare each listed model for a `gsd-*` agent with the kept project's own `.opencode/agents/gsd-*.md` `model:` lines. Report `listing via shared service: <N> agents match, <M> differ`; if it omits `gsd-planner`, also report `listing does not reflect the kept project (shared service booted elsewhere)`. A shared-service listing is supporting information only, never proof the kept project loaded; outcome is `precedence pending (shared-service listing only)`.

The agent's answer to “which model are you?” is never evidence and is not requested.

(c) Optional, user-owned same-named-global shadow case (SPEC R5 adjacency):

```sh
test -f ~/.config/opencode/agents/gsd-planner.md && echo global-agent-present || echo no-global-agent
```

If present, the project/global shadow case is observed in Step 7(b); return both `model:` lines. If absent, only if you choose, create that global file yourself with a different `model:` line, repeat Step 7(b), and delete only the file you created. Why opt-in: this phase never writes your global Opencode config (SPEC must-not).

(d) Remove the kept smoke work directory when finished:

```sh
rm -rf "${DIR:?set DIR to the kept smoke work directory first}"
```

expect: exactly one outcome: `precedence proved (run --agent)`, `precedence contradicted (<loader model> vs <baked>)`, or `precedence pending (<reason>)` for no loader field, multiple fields, or shared-service listing only.

## Send back

Return `opencode-env-names.txt`, `opencode-smoke.md`, `opencode-smoke.log`, the full `opencode-artifacts/` directory, `snapshot --check` output, the four Step 6 outcomes and status lines, Step 7 JSON/listing files and outcome, and the shadow result if attempted.

## What happens next

Analyze the artifacts (plan, resulting config, resolve-model output, baked output) and smoke log; add the interactive result to `20-SMOKE-OPENCODE.md`, including D-11 and R5 outcomes. EVAL-05 and SPEC R5 remain pending unless Steps 1–4 are green, Step 6 has four unblocked outcomes, and Step 7 says `precedence proved (...)`. A pending or contradicted result keeps EVAL-05 and R5 pending with the missing or contrary observation named in the smoke evidence. The global alternative—editing `~/.gsd/defaults.json` and reinstalling globally—would change every Opencode project; it is explained here, never run by the phase.
