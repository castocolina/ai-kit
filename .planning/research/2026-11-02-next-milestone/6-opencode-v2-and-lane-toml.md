# opencode 2.x model listing, and the review/execute lane config

Research date 2026-11-02. Read-only; probe scripts sit next to this file
(`6-probe-api-model.py`, `6-probe-serve-banner.py`, `6-probe-run-events.py`). No key or auth
file content was printed.

## 1. opencode 2.x: what is true on this machine

### Live facts (opencode v2.0.31)

- `opencode --version` prints `opencode v2.0.31`.
- `opencode models --help`: the only flags are `--standalone` and `--server <url>`. It takes no
  positional argument (`opencode models openai` gives "Unexpected positional argument", exit 1).
  `--verbose` and `--refresh` are rejected (exit 1, "Unrecognized flag").
- `opencode models` prints 41 lines, one `provider/model` id per line, no metadata, no variants.
  Providers: openai 16, opencode 8, xai 8, router-env 6, zai-coding-plan 3. Example ids:
  `openai/gpt-5.5`, `opencode/big-pickle`, `router-env/my-coding`,
  `router-env/llama-cpp/ornith-15-9b` (a model id can contain a slash).
- Config-only providers do show up. The only provider in `opencode.jsonc` is `router-env`
  (`@ai-sdk/openai-compatible`, 6 models); all 6 appear in the listing.
- `opencode models` and `opencode models --standalone` return the same 41 ids.
- `opencode run --help`: `--model provider/model#variant`, `--agent`, `--format default|json`,
  `--auto`, `--standalone`, `--session`, `--continue`, `--fork`, `--file`, `--title`,
  `--thinking`. No `--variant` and no `--dir`. `opencode run --variant high` fails with
  "Unrecognized flag: --variant".
- Effort is now a model-id suffix (`#low`, `#high` ...). The model API lists the valid variants
  per model: `opencode api --standalone GET /api/model` returns `{location, data[41]}`. Each
  item has `providerID`, `id` (the listed id), `modelID` (the upstream id, differs for 8
  `-fast` aliases), `capabilities.input` (a list), and `variants` (a list of `{id, settings}`).
  Variant ids per provider: openai none/low/medium/high/xhigh/max; opencode also minimal;
  xai none..xhigh; zai-coding-plan low/high/max; router-env low/medium/high. 6 models have no
  variants.
- `opencode serve --hostname 127.0.0.1 --port 0` still prints `server listening on
  http://127.0.0.1:<port>` and a `server password ...` line, so ai-kit's banner parser still
  matches.
- `opencode run --model M --agent plan --format json --standalone`, with the prompt on stdin
  the way the runner sends it, returned exit 0 and JSON lines `step_start` then
  `text` (`part.text`, `part.id`, `part.messageID`, `sessionID`). That is the shape the runner's
  `parseOpencode` expects. If you pass the prompt as an argument and leave stdin open, the
  command hangs (killed after 120 s): opencode reads stdin even when you give it a message.

### Official docs and changelog

- The page https://opencode.ai/docs/cli still documents the 1.x commands:
  `opencode models [provider]`, `--refresh`, `--verbose`, and `run --variant`. The installed
  2.0.31 rejects all four. The page only says "OpenCode v2 is now available" (installed with
  `opencode upgrade --major`). https://opencode.ai/docs/v2/ returns 404.
- GitHub releases (`sst/opencode`): the release marked "Latest" is still v1.19.5
  (2026-10-28). 2.x releases start at v2.2.0 (2026-10-27) and run to v2.2.5 (2026-10-30). No
  2.0.x or 2.1.x release is published, so the installed 2.0.31 has no public changelog. 2.2.x
  notes mention "Let model-list API requests filter by type", custom models with a model type,
  and plugin-provided model variants. None of them changes the CLI listing.
- Most likely source of the suspected invented claims: an agent that read the docs page, or
  remembered it, gets the 1.x commands. Only `--help` on the installed binary is reliable for
  2.x.

### What ai-kit assumes, compared with the installed version

Correct for 2.0.31 (no change needed):
- `skills/ai-kit-spec-review/ai_kit_spec/detection.py:86-93`: listing argv is `("models",)`;
  the model suffix pattern is `#[^#/]+$`.
- `detection.py:297-313` (`detect_opencode_models`): one id per non-blank line. Matches.
- `detection.py:674-676, 690-706, 918-934`: the image-capability check is gated on the
  version. 2.x uses the `serve` plus `GET /api/model` probe; `parse_opencode_api_models`
  (`:709-737`) reads `capabilities.input` as a list and uses `id`, both correct live. 1.x uses
  `models --verbose`.
- `.planning/scripts/cross-ai.mjs:1373-1386` (copy at `skills/ai-kit-spec-review/references/cross-ai.mjs`):
  the exec/review argv (`run --model M [--auto | --agent plan] --format json --standalone`),
  the `#variant` suffix, the JSON event parser (`:1506-1519`) and the listing parser
  (`:3509-3513`) all match.
- `tests/test_ai_kit_spec.py:137`: the `models --verbose` fixture is labelled opencode 1.18.32,
  so it pins the 1.x path only. That is fine.

Wrong or stale:
1. `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:402` writes
   `review.effort.opencode = "high"` into a target project's GSD config. gsd-core renders that
   as `--variant high` (`.claude/gsd-core/bin/lib/model-catalog.cjs:230-236`), and opencode 2.x
   rejects that flag, so every opencode review lane fails at once. This repo's
   `.planning/config.json` was fixed by hand to `inherit` (commit ef03875, which states this
   exact cause), but the skill still writes the broken value into any other project. This is a
   live bug.
2. `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py:256-263`
   (`lane_effort`) returns the lane's `default_effort` (`high` for opencode) or `xhigh`. That
   is the same failure on the reviewer lane path. On opencode 2.x the effort has to go into the
   model id (`model#high`), and only when the API lists that variant, or the lane has to be set
   to `inherit`.
3. `.planning/scripts/cross-ai.mjs:1371-1372`, and the same text in
   `skills/ai-kit-gsd-curated-config/references/runner.md:23-26`, say that `opencode models`
   "has no such flag" (`--standalone`) and therefore still reaches the shared service. 2.0.31
   does accept `opencode models --standalone`. Sending listing calls to the shared service is a
   choice, not something the CLI forces.
4. `detection.py:769-808` (`_probe_env`, `_run_opencode`): the private working directory and
   the `OPENCODE_DISABLE_PROJECT_CONFIG` guard assume the subprocess loads config itself. On
   2.x, plain `opencode models` asks the background service (`opencode serve --service` was
   running), and that service loaded its config when it started. The guard probably does
   nothing for the listing call (not verified). Adding `--standalone` would make the guard
   apply as intended.
5. `skills/ai-kit-spec-review/references/cli-profiles/opencode.md`:
   - `:7-10` gives `last_verified: 2026-08-28`, a 1.x smoke test, and the provider
     `local-llm-env/my-plan-review`, which no longer exists.
   - `:15-22` lists `opencode-go/*` and `ollama-cloud/*` as live providers. Neither is in the
     2.0.31 listing; today's providers are openai, opencode, xai, router-env and
     zai-coding-plan.
   - `:31-35` says the `#variant` suffix "is not validated". It can now be checked against
     `variants` in `/api/model`.
6. `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:27`: the frozen legacy template is
   `opencode run -m {model}`. It is only used to recognise old stored commands, so it is
   harmless, but it is 1.x wording.
7. Both real config files (see section 2) still name `router-env/my-plan-review` as the
   `opencode-local-plan` reviewer. That model is not in the live listing; the current router
   reviewers are `router-env/my-referee-one`, `-two` and `-three`.
8. Simpler option (not a bug): `opencode api --standalone GET /api/model` returns the same
   payload as the `serve` + banner + password + HTTP probe (`detection.py:864-930`), and it
   also lists variants. It would let ai-kit drop the banner parsing and password handling. Only
   checked by hand, on 2.0.31.
9. open-gsd itself (not ai-kit code, but the shared runner depends on it): the opencode
   capability manifest is pinned to `"version": "1.18.0"`
   (`.claude/gsd-core/bin/lib/capability-registry.cjs:2915`). Its reviewer lane is
   `opencode run {{model}} {{effort}} --format json -` (`:3056-3090`). The `--variant` effort
   form is broken on 2.x. Whether the trailing `-` is sent as a literal message on 2.x was not
   verified.

## 2. The lane TOML: what separates reviewers from executors

### The schema as written

- The writer is `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:453-580`
  (`render-toml`). It writes one `[policy]` table (`mode` single|double, `ladder` = an ordered
  list of entry keys, `timeout_tiers`, default `[600, 1200, 1800]`, `:18`) and one
  `[[reviewers]]` array. Each entry has `key`, plus either `runtime`+`model` (a pair), or
  `command` (a custom entry), or neither (the session default), plus optional flat fields:
  `vendor`, `purpose` (`review` | `execute` | `both`, checked at `:531-534`), `is_router`,
  `fallback_quota`, `strength`, `effort`, `service_tier`, `cursor_mode`. Nested tables are
  refused (`:519-525`), so all knobs are flat. Unknown fields are collected into `extra`
  (`quota.py:50`).
- `.aikit/review-spec.toml` (this repo): `policy.mode=single`, 5-entry ladder, 5
  `[[reviewers]]` with only legacy fields (`cli`, `command`, `key`, `model`, `strength`,
  `vendor`). No `purpose`, no `runtime`, no `effort`.
- `~/.config/ai-kit/review-spec.toml`: same layout, 7 entries. Two have `purpose`
  (`cursor-agent-auto` = review, `cursor-agent-composer` = execute); the rest have none. Also
  legacy fields only, no `runtime`, no `effort`.

### How each consumer decides who reviews and who executes

- ai-kit-spec-review: `quota.py:103-135` (`_filter_ladder_by_purpose`) narrows the ladder to purpose in {review, both,
  unset}. If that leaves nothing, it falls back to the whole ladder (there is a test for this).
  It then picks along the ladder using quota and vendor (`resolve_ladder_pick`) and dispatches
  through `reviewer_dispatch.py` / `runner_dispatch.review_spec` (`runner_dispatch.py:100-107`;
  effort comes from `extra.effort`).
- ai-kit-spec-execute-gsd and ai-kit-spec-execute-superpowers both go through
  `execute_selection.py:115-152`. It filters to purpose in {execute, both, unset}
  (`:20-36`; falls back to all entries if that leaves nothing), then by task affinity and
  context, ranks, and feeds `candidates_to_ladder` into the same quota ladder walk.
  `screen_execute_clis` (`:78-112`) refuses an entry that says `purpose = "execute"` on a CLI
  that cannot execute. `execute_dispatch.py:99-103` reads top-level `effort` and `service_tier`.
- curated-config runner rendering does not read this TOML at all. It picks from the inventory
  and model catalog: executors via `cross_ai.py:104-150` (`exec_targets`, a router whose name
  declares execute, else the best "execution" score), review lanes via `cross_ai.py:204-330`
  (gsd-core review lanes, written as `review.models.*` / `review.reviewer_instances.*` in
  `.planning/config.json`). The executor result goes into the runner's `CONFIG` block
  (`.planning/scripts/cross-ai.mjs:74-120`: one `runtime`, one model per runtime in `models`,
  `effort` per runtime).

So the owner is right in practice, with one correction: a distinction exists, but it is the
optional `purpose` field. When `purpose` is unset, the entry counts as both. Both real files
leave it unset on almost every entry, and both consumers fall back to the whole ladder when the
filter leaves nothing. In effect, one shared list serves both roles. There is also one shared
`ladder`, so review order and execute order cannot differ.

### Effort, runtime escalation, model escalation today

- Effort: a flat `effort` per entry exists, but only codex turns it into a flag
  (`--codex-effort`, `runner_dispatch.py:208-212`). Cursor takes effort inside the model id
  (`model[effort=high]`, `commands.py:80-107`), opencode as a `#variant` suffix, and pi as a
  `:level` suffix or `CONFIG.effort.pi`. There is no single `--effort` flag, and nothing checks
  whether the model supports the effort level (except the curated-config `exec_effort` clamp
  against catalog `reasoning_modes`, `cross_ai.py:92-101`).
- Model escalation: only implicit, as the order of `policy.ladder` checked against quota. It
  is one list across all runtimes. There is no "step up within the same runtime" flag.
- Runtime escalation: none, by design. The runner runs one runtime per call ("A list is never
  walked", `cross-ai.mjs:4461-4475`; `--prefer` only uses its first entry, header `:23-25`).
  Retries stay on the same session or start a new session on the same runtime and model
  (`CONFIG.sameSessionRetries` / `newSessionRetries`).

### The open todo compared with the newer wish

The todo `.planning/todos/pending/2026-10-29-unify-review-execute-lane-toml-effort-escalation-and-jev-classification.md`
already covers:
- one table with a role field versus two tables (left as an open design question);
- effort per model, detected before it is passed;
- the caller passing role + runtime + model + effort together;
- runtime escalation as an opt-in flag that follows the declared order, off by default;
- model escalation inside one runtime as a separate flag;
- jev classification of input and output, with an optional, switchable backend kept as a TOML
  setting.

The owner's newer wish adds:
- **One shared runner script used by both callers**: GSD's cross-AI execute
  (`workflow.cross_ai_command`) and review lanes, and ai-kit's own spec-review and spec-execute.
  The todo only says "adjust the scripts". It does not make open-gsd review a consumer.
- **Escalation moves into the runner.** The runner takes runtime, provider/model, effort, a
  runtime escalation list and a model escalation list as inputs. Today the runner refuses to
  walk any list, and escalation is the caller's ladder in Python. This reverses the runner's
  one-runtime-per-call rule, so the owner has to decide it explicitly against the "never switch
  harness, provider or model on failure" rule.
- **Effort is translated per runtime in one place** (opencode `#variant` checked against
  `/api/model`, cursor bracket, pi `:level`, codex `-c model_reasoning_effort`, claude
  `--effort`), instead of codex-only flags plus suffixes in model ids.
- Also needed, not in either: separate review and execute orders (two ladders or one ladder per
  role), not one shared `policy.ladder`.

## 3. open-gsd cross-AI compared with ai-kit's runner

How open-gsd calls external CLIs:
- Execute: `execute-phase/detail/elaboration.md:73-99` reads `workflow.cross_ai_command` and
  `workflow.cross_ai_timeout` (default 300), then runs
  `echo "$TASK_PROMPT" | gsd_run run-with-timeout $T -- $CROSS_AI_CMD`. The command string is
  split into words without a shell, and stdout becomes the candidate SUMMARY. GSD knows nothing
  about runtime or model here: it runs one opaque command. This repo sets it to
  `node .planning/scripts/cross-ai.mjs` with timeout 1800.
- Review: `review.md:~355-366` plus the lane manifests in
  `bin/lib/capability-registry.cjs` (one `reviewer` block per CLI: binary, argv template with
  `{{model}}`/`{{effort}}`, prompt channel, timeout floor, config keys) and
  `review-lane-invocation.cjs` / `model-catalog.cjs` `EFFORT_ARGV` (claude `--effort`,
  opencode `--variant`, codex `-c model_reasoning_effort=`). Config keys: `review.models.<slug>`,
  `review.effort.<slug>` (`inherit` means no flag), `review.timeouts.<slug>`,
  `review.reviewer_instances.<name>.{cli,model}`, `review.default_reviewers`,
  `review.parallel_lanes`. GSD runs the CLIs itself; it does not go through
  `cross_ai_command`.

What overlaps with `cross-ai.mjs`:
- Both build per-CLI argv from a table: model, effort, prompt on stdin, JSON output, timeouts.
- Both deal with the opencode effort form. GSD's (`--variant`) is broken on 2.x; the runner's
  (`#variant`) works.
- Both classify empty or failed output (GSD: empty output becomes a stub with stderr; the
  runner: an error/quota catalog, the `AIKIT-XAI` status line, tree-state checks).
- ai-kit's spec-review/execute already run the runner (`runner_dispatch.py`) in `review` or
  `exec` mode. Only GSD's review lanes bypass it.

What a single shared runner would need to serve both:
1. Accept a full lane spec per call: role (review|exec), runtime, provider/model, effort, and
   optional ordered escalation lists for runtimes and models. Escalation stays off unless the
   caller asks for it.
2. Own the effort translation per runtime, checked against what the model supports (opencode
   `/api/model` variants, catalog `reasoning_modes`). Never pass an effort the CLI or model
   rejects.
3. A way in for GSD review. GSD's review lanes are manifest-driven and do not use
   `cross_ai_command`. Either gsd-core gets a "custom command" reviewer lane that points at the
   runner (an upstream change, or a project-local lane if the registry allows one, not
   verified), or ai-kit keeps GSD review on its native lanes and only fixes the effort settings
   it writes (item 1 in section 1).
4. Keep the current contract: prompt on stdin, answer on stdout, one final status line on
   stderr, word-split flags with no spaces (GSD's no-shell split), quota and auth stops instead
   of retries, `--child-pgid-file` cleanup.
5. Read lane config from one source. Today that is three: `review-spec.toml`, `.planning/config.json`
   `review.*`, and the runner's `CONFIG` block. The runner could read the TOML lane by key
   (`--lane <key>`), or callers keep passing flags. Either way, one schema needs `role`, an
   `effort` per entry, and a ladder per role.

---
Not checked: the trailing `-` in GSD's opencode lane on 2.x; whether the background service
applies the project-config guard; 2.0.x/2.1.x changelogs (not published). Risk: curated-config
still writes `review.effort.opencode = "high"`, which breaks opencode review in any project it
configures.
