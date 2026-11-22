# 38-07 Summary: the runner's guard hits rewritten, its baseline entry gone

Status: complete. Commit 908a670 (`fix(38-07): rewrite the runner's model literals the guard read as models and drop its baseline entry`), touching only `skills/ai-kit-spec-review/references/cross-ai.mjs` and `tests/fixtures/no_hardcoded_models_baseline.json`. Executed through one cross-AI lane (pi router-env/my-coding) for both tasks, status=ok on its first run (291 s).

## What changed

- Runtime text (output bytes unchanged): the pi row comment and the floor comment say "the model flag"; the `--model` floor error is built from `${a}`; the "--model wins" note is a string concatenation with a one-line comment.
- Self-test text (every case keeps its outcome): `evidence-member-402-inferred` uses `fake/my-coding`; `pure-catalog-route-provider` proves the same three `providerAdmits` properties with `fake` / `fake/coding-5` / `placeholder-model-1`; `model-and-alias` asserts the same stderr text via a concatenation; `model-unusual-pi-bare` uses `fake-bare`; `model-opencode-colon` builds its two-slash, colon-tagged id from invented parts and now checks the id reaches the preview argv; `pure-model-grammar` uses `fake/my-coding:high`; the `no-second-cli-` rows carry `token:` instead of `model:`.
- The runner's whole entry (14 hits, `cleaned_by` 37) is removed from the shrink-only baseline.

## Verification (run by the chunk agent)

- `--self-test-list` byte-equal to the previous commit (628 lines); cases pure-classify-evidence-member-402-inferred, pure-catalog-route-provider, model-flag-each, model-and-alias, model-unusual-pi-bare, model-opencode-colon, pure-model-grammar, no-second-cli-transient, no-second-cli-hard-waits, model-floor-refuses-0/1, model-config-floor-refuses, model-pi-colon-id, ok: `self-test ok`.
- `--print-argv` (pi exec and review, opencode exec, claude review, cursor exec, pi with `--model-pi`, a refused model) byte-equal to the previous commit.
- No `cross-ai.mjs` entry left in the baseline; no `router-env/`, `zai-coding-cn`, `'--model', 'glm'`, `'--model', 'or/meta`, `model: 'event400'` in the runner; `row.token || row.mode` twice, `row.model || row.mode` gone; no grok text.
- tests.test_arch_hardcoded_models, tests.test_runner_flags, tests.test_cross_ai_render_sync, tests.test_cross_ai_docs_text pass; the lane ran the eight self-test shards and the four gates (10/10 modules, exit 0); the hook passed 129/129.

## Deviations

- One commit for both tasks (the chunk's lane prompt), so the baseline entry was deleted whole instead of in two steps.
- Two acceptance counts of the plan were wrong at HEAD, not the code: `Error(`${a} must match` counts 2, not 1 (the `--model-<cli>` branch at line 6232 already used `${a}`); `glm-5\.3` still matches once, in the stderr fixture `[zai/glm-5.3-flash] [429]: ...` of a classifier case (line 2522), which is not one of the 14 guard hits and passes the guard. Left untouched, open for code review.
