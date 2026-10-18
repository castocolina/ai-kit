# Interactive Codex Run — EVAL-04

This run is the EVAL-04 evidence; the headless runs in [20-SMOKE-CODEX.md](20-SMOKE-CODEX.md) only prepared it.
Only your own Codex TUI run counts; return the artifacts and observations listed below.

## Before you start

- Open a terminal at the root of the checkout carrying the Phase 20 harness: branch `gsd/v1.3-curated-config-v2`, found with `git rev-parse --show-toplevel` inside it, or `main` once this branch is merged. The main checkout before merge lacks these smoke flags and `tmp/p20`; an old harness there is not valid.
- Confirm `git status --porcelain` is empty and `node` is on `PATH`.
- The smoke finds the installer copy itself. Pass `--installer-dir <dir>` only if it reports `no cached @opengsd/gsd-core`.
- Nothing here edits global config. The smoke installs only in scratch projects under a throwaway HOME and checks the `~/.codex`, `~/.config/opencode`, and `~/.gsd` allowlist before and after.

## Steps

1. REQUIRED — **Start Codex at the checkout root**

```text
Start the Codex TUI in this checkout root, then use its shell tool for the following commands exactly as written. Do not print environment variable values.
```

expect: Codex is running in the branch checkout (or merged `main`) identified by `git rev-parse --show-toplevel`.

2. REQUIRED — **Fresh baseline and names-only environment list**

```text
Run exactly: mkdir -p tmp/p20/interactive && python3 tests/gsd_curated_eval.py snapshot --out tmp/p20/interactive/codex-before.json && env | cut -d= -f1 | grep -E '^(CODEX|OPENCODE|AI_AGENT|AGENT|CLAUDE|PI_|CURSOR_|GROK_)' | sort > tmp/p20/interactive/codex-env-names.txt && printf 'Names only:\n' && cat tmp/p20/interactive/codex-env-names.txt. Never print an environment value.
```

expect: `snapshot written`, then the recorded headless Codex names `CODEX_APPLY_PATCH_PRESERVE_LINE_ENDINGS`, `CODEX_CI`, `CODEX_SANDBOX_NETWORK_DISABLED`, `CODEX_SESSION_ID`, `CODEX_THREAD_ID`, and `CODEX_VERSION` (plus any other matching names). The baseline follows TUI startup so a project-trust write is not mistaken for a regression. Report any difference; it triggers the D-04 follow-up. Names only.

3. REQUIRED — **Run smoke and retain its artifacts**

```text
Run exactly: python3 tests/gsd_curated_eval.py smoke --evidence-out tmp/p20/interactive/codex-smoke.md --artifacts-out tmp/p20/interactive/codex-artifacts > tmp/p20/interactive/codex-smoke.log 2>&1; echo "smoke exit=$?" >> tmp/p20/interactive/codex-smoke.log; then print the log and evidence file.
```

expect: `smoke exit=0`, `host codex (detected)`, `scope: local`, `all equal`, `matrix ran: 420 checks`, and `protected set unchanged: pass`; artifacts exist at `codex-artifacts/<label>/{plan.json,config.json,resolve-model.json,baked.json}`. The log includes `scratch work dir: <path> (deleted)` for Step 4.

4. REQUIRED — **Check the baseline**

```sh
python3 tests/gsd_curated_eval.py snapshot --check tmp/p20/interactive/codex-before.json --scratch-root <the work-dir path printed by step 3>
```

expect: `snapshot ok`. Return any `changed` line verbatim as a guard failure; do not dismiss it.

5. REQUIRED — **Codex trust note**

```text
If Codex asked to trust a scratch directory, report that fact. Do not print or modify any config contents.
```

expect: trust prompt reported if it occurred; the harness ignores only this run's `projects."<scratch>"` trust tables in the Codex TOML by design (D-10).

6. OPTIONAL — **Native per-call model selection (ROADMAP SC3)**

```text
Ask Codex to spawn a subagent that must run on model <id> and have it reply with the model it is running on. Return the reply text only.
```

Why optional: SC3 is an OR; the session-default branch is already pinned by `native_selectors == ()` and its unit test (20-06). This probe can only upgrade the label later.

## Send back

Return `codex-env-names.txt`, `codex-smoke.md`, `codex-smoke.log`, the full `codex-artifacts/` directory, the `snapshot --check` result, the trust note, and (if run) the optional probe reply.

## What happens next

The artifacts (plan, resulting config, resolve-model output, baked output) and log will be analyzed, and `20-SMOKE-CODEX.md` will receive the interactive result. EVAL-04 is checked off only when Steps 1–5 return green. The TUI names confirm or revise the headless signal list under D-04: update the Codex labels in `skills/ai-kit-spec-review/ai_kit_spec/detection.py` and its docstring from `TUI confirmation pending` to the TUI outcome. A signal absent from the TUI names is dropped; any name added or dropped must update all mirrors and `tests/test_ai_kit_spec_runtimes_table.py` in one in-phase commit (one Python module threshold, D-04). The `CODEX_VERSION` labels are explicitly pending TUI confirmation until then.
