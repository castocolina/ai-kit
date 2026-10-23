# Pi GSD Agent Model Spike

Date: 2026-10-23

## Run conditions

- pi version: `1.3.0`; gsd-core installer package: `1.17.0`.
- Scratch HOME and PI_CODING_AGENT_DIR; models.json contains only the literal dummy key `dummy-not-a-key`.
- pi ran under `env -i`, with the scratch project extension trusted for this run using `--approve`.
- Requests went only to a localhost mock provider; no real credential or model call was used (ruling Q1).

## L2 (localhost mock)

| Arm | Project config | Trust path | pi exit | Selection | Wire model | Result |
|---|---|---|---:|---|---|---|
| A | `pi.sonnet=steered-id` | `--approve` | 0 | selected | steered-id | pass |
| B | `pi.opus=opus-id` | `--approve` | 0 | selected | selected | pass |
| C | no override (`model_profile=balanced`) | `--approve` | 0 | selected | selected | pass |
| D | `pi.sonnet=steered-id` | none (no `--approve`) | 0 | selected | selected | observed: extension skipped; observation only |

A-C each sent one request to its own localhost mock process, stopped before the next arm. A's initial `PI_OFFLINE=1` run reached the mock, so no suppression rerun was needed. Logs contain only request path and wire model, not headers.

## L0 (static)

- Registry pi entry, `<checkout>/.claude/gsd-core/bin/lib/capability-registry.cjs:3167-3218`: `namedDispatch=false` and `nested=false` (3210-3211), `maxDepth=0` (3212), `subagentToolkit=undocumented` (3215), `installSurface=profile-marker-only` (3202), `pluginOnlyInstall=true` (3232).
- `<installer>/pi/gsd.cjs:233`: handler default tier `sonnet`.
- `<installer>/pi/gsd.cjs:386`: registers `before_provider_request` with no tier argument.
- `<installer>/pi/gsd.cjs:217-224`: upstream `ASSUMPTION` comment says payload field name `model` needs live verification.
- `<installer>/pi/gsd.cjs:254-263, 268, 272-274`: fail-open for undefined/null/empty and resolution errors; returns payload with the verbatim resolved model.
- `<pi-pkg>/dist/core/extensions/runner.js:1066-1093`: `emitBeforeProviderRequest` awaits handlers, adopts non-undefined payloads, catches errors and returns the current payload.
- SHA-256 `<installer>/pi/gsd.cjs`: `fbb3c3d34903f355f37ba1ffa455cb7280912e55cf470328fc7f091451cfea`.

## L1 (fake ExtensionAPI)

A scratch CommonJS probe loaded the installed extension with `registerCommand`/`registerTool` no-ops and captured its event handler. Each config was written to the scratch project's `.planning/config.json`; the handler received payload `{model:"sel",x:1}`.

| Config under `model_profile_overrides.pi` | Returned payload | Steers |
|---|---|---|
| `{}` | `undefined` | no |
| `{"opus":"o1"}` | `undefined` | no |
| `{"haiku":"h1"}` | `undefined` | no |
| `{"sonnet":"s1"}` | `{"model":"s1","x":1}` | yes |
| `{"sonnet":""}` | `undefined` | no |
| `{"sonnet":"router-env/my-coding"}` | `{"model":"router-env/my-coding","x":1}` | yes, verbatim |

Only the sonnet key steers; the qualified id passes unchanged (D-05 and ruling Q6).

## L3 (owner)

| Arm | Status |
|---|---|
| L3a | not run (owner): one tiny real call, direct provider, `pi.sonnet` set, `-ne -e .pi/extensions/gsd.js`; staged in `22-INTERACTIVE-PI.md` (22-06); approval required (D-03, Q3). |
| L3b | not run (owner): one tiny real call, direct provider, no override; staged in `22-INTERACTIVE-PI.md` (22-06); approval required (D-03, Q3). |
| L3c | not run (owner): one tiny real call using `--approve` rather than `-e`; staged in `22-INTERACTIVE-PI.md` (22-06); approval required (D-03, Q3). |

## Findings (R7)

- `skills-root pi` on the scratch install printed `{"skills_root":"<scratch-home>/.pi/agent/skills"}`. pi 1.3.0 `docs/skills.md:61` also documents `~/.agents/skills/` and `.agents/skills/`. **No fix needed in this phase:** upstream gsd-core behavior, and `agent_skills` is inert on pi (D-06).
- With `resolve_model_ids: "omit"`, `runtime: "pi"`, and `pi.sonnet` set, `resolve-model gsd-planner` returned an empty model result while the L1/L2 hook steered the wire. Thus `resolve-model` is not an oracle on pi; the 22-04 matrix checks the wire through the hook instead (D-03). **No fix needed in this phase.**

## Verdict

verdict: session-steer (static + mock evidence)

- pi.sonnet: steers every request of a trusted project's pi session (L1, L2 wire).
- pi.opus, pi.haiku: inert (L1; ruling Q6).
- model_overrides.*: no effect (no named dispatch, L0).
- agent_skills.*: no effect on pi (no GSD agent files installed, L0; L3 confirms later, D-06).
