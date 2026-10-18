# Phase 21: Cursor Live Validation - Research

**Researched:** 2026-10-18
**Domain:** live validation of an existing Python/Node skill on a third host (cursor-agent 2026.10.14-941492e), host detection hardening, two static subagent files
**Confidence:** MEDIUM-HIGH (static bundle reading and local code reads are HIGH; everything that needs a live cursor session is explicitly open)

Notation: `<home>` = the user's home, `<worktree>` = this checkout, `<bundle>` = `<home>/.local/share/cursor-agent/versions/2026.10.14-941492e`. The bundle's `index.js` is one minified line (line 414), so bundle citations give the **character offset** into the file (`index.js@N`). No live cursor-agent/codex/opencode/pi/claude probe was run; the only commands run were the gsd-core installer and Python/Node reads, all under `<worktree>/tmp/p21/`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01 outcome (2026-10-18): the CLI ignores user-level agents. R6/R7 and D-02..D-05 move to Phase 21.1 (AGT-02). Not planned here.
- D-06: the frontmatter test ports the bundle's own line parser, not YAML: a `^---\s*\n...\n---` block is required; lines split at the first `:`; keys lowercased and values raw-trimmed (quotes and comments stay); only `name`, `description`, `model`, `force-default-model`, `readonly`, `background`/`is_background`, `tools` are read; an empty body drops the file silently; `model` is unvalidated client-side. Shipped files use unquoted single-line scalars.
- D-07: name-collision test: static rule (not `gsd-*`, name equals filename stem) plus an optional live cross-check against `gsd_catalog.query_agent_catalog`, `skipUnless` node and gsd-core are present. Real `~/.claude/agents` is never read.
- D-08: non-fast pins: each pinned id is in the captured `models` fixture and does not end in `-fast`. (The live R7 proof and dashboard check belong to 21.1.)
- D-09: resolver over `RUNTIMES["cursor"].binaries`: `cursor-agent` accepted as found; `agent` accepted only when some PATH entry's realpath basename is `cursor-agent`, scanning every PATH entry; two names resolving to one real file reported once; `runtimes.json` records `real_path` next to `path`; enumeration runs the PATH hit. Tests use real temp-dir symlinks with `functools.partial(shutil.which, path=tmpbin)`; "no shell" asserted via the injected `run_fn`. Provisional (on the ledger).
- D-10: `parse_cursor_models(stdout)` pure + thin `detect_cursor_models`, like codex; token-based, not `" - "`-based; a nameless model such as `auto (current, default)` is kept; ANSI stripped; output gated on returncode 0; fixture `tests/fixtures/cursor_models.txt` captured from an authed session; the unauthenticated `Authentication required` exit 1 is the failure fixture.
- SPEC R1, R2, R3, R4, R5, R8 as in `21-SPEC.md` (R6, R7 moved). MUST NOT: execute the user's shell wrapper; ship a `-fast` or config-dependent bare-id pin.
- Constraints: always pass `--model` explicitly to cursor subprocesses; ask before any write to `~/.cursor` beyond selected links; pins are explicit non-fast ids.
- 20 D-04 fix policy: small local fixes (one module) in-phase with a regression test; anything touching more than one module or changing a CONTEXT decision becomes a decimal phase.

### Claude's Discretion
Helper names; the agent bodies' wording (short, for already-planned tasks).

### Deferred Ideas (OUT OF SCOPE)
Overriding Cursor's built-in explore subagent model (`cli-config.json` user setting). Linking, wizard row, `--cursor-agents`, live delegation proof and dashboard check (Phase 21.1, AGT-02).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-07 | Live cursor smoke, 5x35 matrix with `GSD_RUNTIME=cursor`, label lifted | Findings 3, 4, 6, 7 (harness gaps G1-G5, installer behavior, runner dispatch, label sites) |
| SPEC-06 | cursor found and enumerated without running the wrapper | Finding 1 (D-09/D-10 deltas against existing `detection.py`), fixtures in Validation Architecture |
| AGT-01 | Two pinned `cursor-agents/*.md` files and their tests (files only) | Finding 2 (parser, collisions), models fixture facts |
</phase_requirements>

## Project Constraints (from AGENTS.md)

English only; runtime code stays stdlib-only; atomic config writes (not touched here); no result shown with more certainty than its sourcing (cursor env-signal label stays `source-inspected-only` unless live evidence upgrades it); any changed `SKILL.md` passes `skill-judge` (no Critical/Important left, no regression vs baseline); one coherent commit per logical change with tests+docs, never `--no-verify`; never use real `~/.claude`/`~/.cursor`/`~/.config/opencode` as a fixture; no absolute machine paths in plans or source; failing tests get fixed, not deflected; `tests/test_arch.py` and `tests/test_gate_scope.py` rules apply to any new module (new test modules are registered through `tools/gen_test_groups.py` output in `Makefile`/`.pre-commit-config.yaml`); `make test` and `make validate` green before done; update README/docs with the change; scratch under `./tmp/`; CodeGraph before grep loops.

## Summary

Phase 21 is mostly a re-run of the Phase 20 playbook (headless runner dispatch for the smoke, an interactive script for the user, matrix class, evidence file, label lift in the same commit), plus two independent code deliverables: hardening cursor detection (SPEC-06) and two static agent files (AGT-01). Most of D-09 already exists from Phase 18.1: `resolve_runtime_binary` is a guarded first-hit resolver and `detect_cursor_agent_models` exists; what is missing is scan-all-PATH, `real_path` in `runtimes.json`, a public pure `parse_cursor_models`, ANSI/nameless-line tolerance and an empty-account case.

The bundle still matches D-06 and D-10 in 2026.10.14, with renamed symbols (`Hs` is now `Ks`) and three details D-06 does not mention: the regex carries the `m` flag, a missing `name` falls back to the filename stem, and a new `allowExternalAgentSymlinks`/containment check skips symlinked **directories** outside the workspace but still follows symlinked **files** (consistent with the D-01 spike). The invalid-`model` behavior is not decidable from the bundle: the value is forwarded in a protobuf field with no client validation (server behavior open).

The biggest planning risk is not in the listed deliverables: the existing smoke/matrix harness has cursor-specific gaps that will fail a first cursor run. (1) `host.py` has no `.cursor` first-root, so inventory in a cursor-installed scratch project resolves the worktree's `.claude/gsd-core` and the smoke's own `gsd-core mismatch` check raises (reproduced, Finding 3). (2) `~/.cursor/cli-config.json` is in the **strict** protected set, but `cursor-agent` itself rewrites it, so any live cursor session fails the guard unless the cursor comparison becomes semantic. (3) gsd-core 1.17.0's cursor installer bakes **no** `model:` line (it keeps only `name` and `description`), so "planned == baked" must be recorded as "resolve-model only" for cursor, as D-08 did for codex. (4) the matrix module's collection pin (27 tests, three host classes) and `matrix --host` choices need a fourth class.

**Primary recommendation:** plan in four waves: (W1, parallel) `cursor-agents/` files + models fixture + new test module, and detection hardening; (W2) harness cursor support (host root, protected-set semantics, baked-chain cursor branch, generated paths, matrix class); (W3) headless smoke through the cross-AI runner, with explicit `--model-cursor composer-2.5` and a process-group reap; (W4) user interactive script, then the label lift + skill-judge + README in one evidence commit.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| cursor binary resolution, models listing, `runtimes.json` | Shared lib `ai_kit_spec/detection.py` | Runner template (`cross-ai.mjs` `resolveBin`) | Single source of truth for runtimes; the JS runner re-implements the same guard |
| Host detection (`CURSOR_AGENT`) | `detection.py` env table | Cursor bundle (injects the var) | Var is set by cursor's shell tool, not by the user's shell [VERIFIED: index.js@4531580, @4688829, @4714029] |
| Local gsd-core discovery per host | `ai_kit_gsd_curated_config/host.py` | `ai_kit_spec/gsd_tools.py` roots | Gap G1 sits here |
| Smoke, matrix, protected-set guard | Dev harness `tests/gsd_curated_eval.py` | `tests/test_ai_kit_gsd_curated_config_matrix.py` | Dev-only, host-agnostic by design but has per-host branches |
| Subagent files | Static data `cursor-agents/*.md` | Test module parsing them | Consumed by cursor-agent only in 21.1 |
| Label lift | `SKILL.md`, `README.md` | `tests/test_curated_config_apply.py` pin | Same commit as evidence (R3) |

## Standard Stack

No new packages. Everything needed is already in the repo or on this machine: `unittest` (stdlib), `uv`-managed dev env, Node (for the `node -e` parity oracle and gsd-core). Package Legitimacy Audit: not applicable (no install step; the gsd-core 1.17.0 installer is run from the existing npx cache, never fetched, per the Phase 20 rule).

| Item | Version | Provenance |
|------|---------|-----------|
| gsd-core installer (cached) | 1.17.0 | [VERIFIED: ran it; printed `GSD Core v1.17.0`] |
| Node | v24.21.0 | [VERIFIED: `node --version`] |
| Python | 3.14.7 | [VERIFIED: `python3 --version`] |
| cursor-agent bundle | 2026.10.14-941492e | [VERIFIED: directory name under `<home>/.local/share/cursor-agent/versions/`] |
| pi (for the pi judge) | 1.3.0 | [VERIFIED: `pi --version`]; model availability not probed |

## Research Answers to the Open Questions

### 1. Do `Hs` (frontmatter) and the models formatter still match 2026.10.14?

**Frontmatter parser: yes, renamed `Ks`.** [VERIFIED: `<bundle>/index.js@4363300-4363700`, read this session] Verbatim:

```text
function Ks(e){const t=e.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$/m);if(!t)return null;const r=t[1]??"",n=(t[2]??"").trim();if(0===n.length)return null;const s={};for(const e of r.split("\n")){const t=e.trim();if(0===t.length||t.startsWith("#"))continue;const r=t.indexOf(":");if(-1===r)continue;const n=t.slice(0,r).trim().toLowerCase(),i=t.slice(r+1).trim();0!==n.length&&(s[n]=i)}const i=s.name??"",o=s.description,a=s.model,c=Vs(s["force-default-model"]),u="true"===(s.readonly??"").trim().toLowerCase()?cr.b$.READONLY:cr.b$.DEFAULT,l=Vs(s.background??s.is_background),d=s.tools;return{name:i,...
```

Differences/additions the port must carry (D-06 text is right but incomplete):
- The regex has the **`m` flag** (`^` matches any line start), so the `---` block need not start at byte 0. Port it verbatim (`re.M`), do not "improve" it to `\A`.
- Lines starting `#` are skipped; empty-body (after `.trim()`) returns null (file dropped silently). `Vs(x)` is `"true" === (x??"").trim().toLowerCase()`.
- Loader (`class ti`, `index.js@4363857-4365300`): `name: n.name || Zs(basename)` where `Zs` replaces `[\s_]+` with `-` on the stem; `model: n.model ?? "inherit"` (so `model:` with an empty value is `""`, not `inherit`); extensions `.md`, `.mdc`, `.markdown` (`Xs`).
- Dirs (`computeAgentsDirs`, `@4364396`): `<workspace>/.cursor/agents`, then `.claude/agents` and `.grok/agents` only when third-party extensibility is on. No home root.
- NEW vs the 2026.10.01 reading: `ti` takes `allowExternalAgentSymlinks=false`; the directory walk `ds` (`@4328505`) realpaths each **directory** and skips it if outside the workspace; a symlinked **file** is followed via `stat` (so per-file links work, directory links outside the workspace do not). Depth cap 10; dot-directories skipped. Plugin agents are re-created with `model:"inherit"` (`stripModel`, `@4367034`).
- `force-default-model` is read and forwarded; its server-side effect is not in the bundle.

**Models formatter: yes, same shape, new location.** [VERIFIED: `<bundle>/6436.index.js@~900-1500`, module `./src/commands/models.ts`] Function `v({models,defaultModelId,currentModelId})`: prints dim `Available models`, a blank line, then per model `` `${id}${name ? " - " + name : ""}${flags ? " (current, default)" : ""}` `` where `flags` are `current` and/or `default` (e.g. `auto - Auto (default)` in the capture), a blank line and a `Tip: use --model <id> ...` line. Empty list prints `No models available for this account.` with **exit 0**. `b` (`@1520`) exits 1 with `Authentication failed...` or `Failed to load models: ...` on stderr, exit 0 otherwise. A nameless model renders as `id` or `id (default)`; hence D-10's token rule (first whitespace token) is correct.

Parser rules to pin (derived from the formatter plus the capture [VERIFIED: `tmp/p21/cursor-models-2026.10.14.txt`, 267 non-empty lines]): skip the header, blank lines and any `Tip:` line; strip ANSI first; id = first token; `No models available for this account.` is a **successful empty list** (`[]`), not `None`. The capture yields 265 unique ids, 79 ending `-fast`, no id outside `[A-Za-z0-9._-]`; `composer-2.5` and `grok-4.7-medium` are present and each has a `-fast` twin; labels (not ids) carry U+200B (`grok-4.7-medium-fast - Grok 4.7  Medium Fast<U+200B><U+200B>`), which a first-token parse never sees. The current `_parse_cursor_models` (`detection.py:281-297`) requires `" - "`, so a nameless line is "unrecognized" and an empty-account message returns `None`; that is the delta.

### 2. Server-side behavior of an invalid frontmatter `model`

**Not decidable from the bundle.** [VERIFIED: bundle read] The value goes untouched into protobuf `CustomSubagent` (`index.js@5376952`: `|5 model 9|...`, plus `forceDefaultModel`); `grep` for client-side "invalid/unknown model ... subagent" messages found nothing. Error versus silent inherit is therefore **OPEN**, tagged `[ASSUMED]` if anyone claims either. It does not block this phase: the shipped pins are validated against the captured listing (D-08). A one-agent live check is a 21.1/user-run item, and per the hard rules this research did not run one.
Related open item: whether `grok-4.7-medium` exists on other accounts (the listing is per account). The test pins the ids against the **captured** fixture only.

### 3. Runner dispatch of cursor, host detection, `GSD_RUNTIME=cursor`

- Argv today [VERIFIED: `skills/ai-kit-spec-review/references/cross-ai.mjs:257-262`]:
  `exec`: `['-p','--output-format','json','--model',m,'--trust','--force','--sandbox','disabled','--approve-mcps','--workspace',c.cwd]`; `review` swaps `--force/--sandbox/--approve-mcps` for `--mode ask|plan`; resume appends `--resume <sid>`. Every flag still exists in 2026.10.14 [VERIFIED: option definitions `index.js@1668424-1673381`: `-p/--print`, `--output-format`, `--mode`, `--resume`, `--model`, `-f/--force`, `--sandbox <enabled|disabled>`, `--approve-mcps`, `--trust`, `--workspace`].
- `--model-cursor` is validated by `CURSOR_MODEL_ID` (`cross-ai.mjs:914`) and listed via `cursor-agent models` first (the template self-test asserts the `models` call precedes the run, `:1779-1780`). The repo's rendered runner config has `models.cursor = "auto"` and `prefer = [pi, cursor, opencode]` [VERIFIED: `.planning/scripts/cross-ai.mjs:60-90`]; the smoke dispatch must pass `--prefer cursor --model-cursor composer-2.5` (D: always an explicit, non-fast id; `auto` is the account default and not a pin).
- Binary: `resolveBin` (`cross-ai.mjs:415-430`) is first PATH hit per name with the `agent` basename guard, spawned with `shell:false`-style argv; the user's shell function is never reached (PATH lookup only). Mirror of the Python guard: any D-09 scan-all change must be mirrored here or the gap recorded (see Open Question 2).
- Host detection: the **cursor bundle** injects `CURSOR_AGENT=1` into the env of its shell/terminal tool in three places [VERIFIED: `index.js@4531580`, `@4688829`, `@4714029`], so a smoke started by cursor's shell tool (headless `-p` or the TUI) sees `CURSOR_AGENT`; `detect_current_runtime` then returns `cursor` unless a higher-precedence signal (`PI_CODING_AGENT`, `OPENCODE`) leaks; the runner scrubs `CURSOR_AGENT` (and all `HOST_SIGNAL_ENV_VARS`) from the children it spawns (`.planning/scripts/cross-ai.mjs` CONFIG `scrubEnv`). The cursor label in `detection.py:48-51` stays `source-inspected-only` unless the smoke's names-only env dump shows the var from a live cursor shell; then upgrade it exactly like Phase 20 did for codex (`test_ai_kit_spec.py:1334-1354` pins pi/codex bullets only, so a cursor bullet change needs its own assertion).
- `GSD_RUNTIME=cursor`: `KNOWN_RUNTIMES` contains `cursor` but its `runtimeTierDefaults` are all `null`, so `RUNTIME_PROFILE_MAP` has no `cursor` row [VERIFIED: `model-catalog.json` `runtimeTierDefaults.cursor = {"opus":null,"sonnet":null,"haiku":null}`; `model-catalog.cjs:85-96`]. Observed: in a cursor-installed scratch project under a throwaway HOME, `GSD_RUNTIME=cursor resolve-model gsd-planner --raw` prints an empty string (the installer wrote `resolve_model_ids: "omit"`), while `GSD_RUNTIME=claude` prints `opus` [VERIFIED: ran it]. The oracle `_host_model` (`gsd_curated_eval.py:522-542`) therefore needs `model_profile_overrides.cursor.<tier>` entries in the plan or `resolve_model_ids == omit`, else it raises `no host model for cursor/<tier>`; `recommend` emits the per-tier slots for every non-claude/non-pi host from the host's candidates (`recommend.py:329-345`), so on a cursor host the plan carries them. Whether the unmodified matrix passes with `host="cursor"` was **not executed** (see Environment Availability: the harness needs the real HOME).
- Orphan `worker-server`: cursor-agent spawns `process.execPath index.js worker-server` with `detached:false, stdio:"ignore"` (`index.js@2222514`; the hidden command is registered at `@1718947`; a stale-server reaper keyed on `<home>/.cursor-server/private-worker-servers` pid files exists in `3548.index.js@10558`). With `detached:false` it inherits the dispatcher's process group (runner spawns cursor-agent `detached:true`, so the pgid is cursor-agent's pid, `cross-ai.mjs:584`). [ASSUMED] consequence: the runner's group kill on timeout reaches it, but a **normal exit** does not (the runner only `killGroup`s on timeout/signal, `:559-563`), and the spike saw it reparented to PID 1 after `models`. Mitigation using what exists: pass `--child-pgid-file <file>` (records `spawn <pid>` per detached child, `cross-ai.mjs:36,495-505`) and have the smoke wrapper run `kill -KILL -- -<pid>` when the group still has members after the runner returns; verify membership once with `ps -o pid,pgid,args` during execution (read-only on the process table).

### 4. gsd-core 1.17.0 `--cursor --local`

Supported [VERIFIED: ran `node <installer>/bin/install.js --cursor --local --no-legacy-cleanup` under a throwaway HOME and a scratch git project, env built with `env -i`]. Wrote under `<project>/.cursor/`: `agents/` (64 files: 35 `gsd-<x>.md` plus 29 `.compact.md`), `gsd-core/` (with `bin/gsd-tools.cjs` and a `.gsd-runtime` marker `cursor`), `hooks/`, `hooks.json`, `scripts/`, `skills/`, `gsd-file-manifest.json`, `gsd-install-state.json`, `.gsd-profile`, `.gsd-staging`. It also printed `Set resolve_model_ids: "omit" in ~/.gsd/defaults.json` and `Set runtime: "cursor"`; both landed in the **throwaway** `<scratch-home>/.gsd/defaults.json` (so the Phase 20 D-09 throwaway-HOME rule applies unchanged; the allowlisted `TMPDIR` must exist or the installer dies with `mkdtemp ENOENT`). **No agent file carries a `model:` line** (`grep -l "^model:"` returned 0 of 64); the converter keeps only `name` and `description` [VERIFIED: `install.js:2640-2652`, `convertClaudeAgentToCursorAgent`]. Consequences:
- "planned == baked" for cursor is vacuous: record the chain as plan -> project-local `resolve-model` only, plus an assertion that baked files carry no model (label it "resolve-model only", like D-08 for codex).
- Whether Cursor-side GSD workflows pass the `resolve-model` result to a Task call is not shown by anything read here; report it as unverified, never imply the planned models take effect inside cursor agents.
- The 64 installed `gsd-*` agents become project subagents of any cursor session in that project (`.cursor/agents` is scanned), which is the reason D-07 forbids `gsd-*` names.
- Smoke generated paths for cursor are `.cursor/{gsd-core/, agents/gsd-*, skills/gsd-*, hooks/, hooks.json, scripts/, gsd-*.json, .gsd-*}`; `_generated_paths` (`gsd_curated_eval.py:4296-4306`) only knows `gsd-core`, `plugins/gsd-core.js`, and `agents|commands|skills` `gsd-*`. `hooks.json` is a merged, possibly user-owned file (codex `config.toml` analogue): report it, never commit it.

### 5. Where the "not live-validated" label lives

[VERIFIED by search this session] `skills/ai-kit-gsd-curated-config/SKILL.md:251` is the only skill text: the table row `| cursor / pi hosts | **not live-validated** |` (heading "Limits (as of 2026-10-18)", `:248`). Other sites: `README.md:45` ("cursor/pi not live-validated"); `tests/test_curated_config_apply.py:2378` pins the literal `"not live-validated"` in `test_required_statements` (still satisfied by a pi-only row, but should become `"pi hosts"`-style or keep the literal for pi); `.planning/REQUIREMENTS.md:66`, `ROADMAP.md:302,514`. Not a label: `detection.py:48-51` `_LABEL_CURSOR` (env-signal certainty, a different claim) and `detection.py:435,506` (pi). R3 edit = split the row to `| pi hosts | **not live-validated** |`, update README, add a cursor evidence pointer, all in the commit that adds `21-SMOKE-CURSOR.md`. Skill-judge floors from Phase 20: in-session 109/120, pi 116/120 [CITED: `20-SKILL-JUDGE.md`]; judges per the project memory: in-session Opus plus pi `openai/gpt-6.1-sol` xhigh only.

## Architecture Patterns

### Data flow for the smoke (R1/R2)

```
user cursor TUI or runner dispatch (cursor-agent -p --model composer-2.5 --trust --force ...)
  -> cursor shell tool (env: CURSOR_AGENT=1)            [host signal]
     -> python3 tests/gsd_curated_eval.py smoke --evidence-out ... --artifacts-out ...
         step 1  ai-kit: inventory, recommend, dry run only   (repo byte-identical)
         step 2  scratch project (a) = copy of repo config:  node install.js --cursor --local   (throwaway HOME)
         steps 3-7  inventory (needs G1 fix) -> recommend -> dry run -> apply -> 2nd apply -> forced-failure restore
                    -> post-apply reinstall -> chain: plan -> resolve-model (no baked model for cursor)
         step 8  scratch project (b) = empty
         step 9  matrix 5x35, GSD_RUNTIME=cursor
         step 10 protected-set snapshot before/after  (needs G2 fix)
  -> evidence markdown (placeholders only) -> 21-SMOKE-CURSOR.md
```

### Harness gaps a first cursor run will hit (all [VERIFIED by reading unless marked)

| # | Gap | Evidence | Fix (module) |
|---|-----|----------|--------------|
| G1 | No `.cursor` local root: inventory resolves `<worktree>/.claude/gsd-core`; the smoke then raises `gsd-core mismatch` | `host.py:21-26` `_HOST_FIRST_ROOT` has only pi/opencode; `gsd_tools.py:85-93` roots lack `.cursor`; reproduced: `resolve_gsd_core(<cursor-installed scratch>, "cursor")` returned scope local, root `.claude/gsd-core`; the check is `gsd_curated_eval.py:4151-4162` | add `"cursor": ".cursor"` to `_HOST_FIRST_ROOT` (one product module: `host.py`) + regression test |
| G2 | `~/.cursor/cli-config.json` is strict, but cursor rewrites it (`models` rewrites `privacyCache`, per `detection.py:303-304`; schema also holds `selectedModel`, `modelSelectionHistory`, `authInfo` with email/name, caches: `index.js@3721184` zod object) | `gsd_curated_eval.py:206-209` | for cursor runs compare a **semantic** digest limited to the user-owned keys `modelParameters`, `subagentModels`, `exploreSubagentModel`; never read or print `authInfo` (hash only the allowlisted subset); add `~/.cursor/{agents,hooks.json,skills}` listings to the strict set (T-21-02) |
| G3 | `_baked_chain` reads `model:` from `.cursor/agents/gsd-*.md`, which never has one | `gsd_curated_eval.py:4276-4345` vs `install.js:2640-2652` | cursor branch: promised map is all `None` for baked files; keep the `resolve-model` comparison; label "resolve-model only" |
| G4 | `_generated_paths` misses cursor's `hooks/`, `hooks.json`, `scripts/`, `.gsd-*` | `:4296-4306` | add cursor prefixes (report-only) |
| G5 | Matrix: `--host` choices lack cursor; module pinned to three host classes (27 tests) | `gsd_curated_eval.py:4894-4899`; matrix test classes `:102-108`; `TestMatrixModuleCollection` pin from 20-REVIEW-FIX (WR-02) | add `TestResolveModelMatrixCursor`, widen choices, update the pin to 36 and the superseded counts in new evidence |
| G6 | No cursor follow-ups: `HOST_DIRS` and `EFFORT_SYNC_HOSTS` list claude/codex/opencode; `_maybe_installer` returns None for cursor | `followups.py:18-19,285-286,310-312` | none needed for cursor models (installer bakes none); the existing `_no_effort_host_note` already reports it; confirm text is honest in the evidence |

R8 threshold: G1 is one product module. G2-G5 are dev-harness/test files (`tests/`), not shipped product modules; recommended reading is that the harness is scaffolding for the evidence, so they stay in-phase (Open Question 1).

### Recommended structure for new files

```
cursor-agents/composer-worker.md   # model: composer-2.5
cursor-agents/grok-worker.md       # model: grok-4.7-medium
tests/fixtures/cursor_models.txt   # copy of the 2026.10.14 capture (keep zero-width chars)
tests/fixtures/cursor_models_empty.txt  # "No models available for this account."
tests/test_cursor_agents.py        # new module: parser port, collisions, non-fast pins (+ node parity oracle)
```

Agent file shape (unquoted single-line scalars, non-empty body):

```markdown
---
name: composer-worker
description: Executes one already-planned task end to end on a pinned non-fast model
model: composer-2.5
---
<short body: read the task, do exactly it, run its verify command, reply with a short summary>
```

### Anti-Patterns to Avoid
- **YAML-parsing the agent files in the test.** The bundle's line parser is the contract (D-06).
- **Putting the files in `agents/`** (links into `~/.claude/agents`; Claude would load an unrunnable pin).
- **Relying on `--model auto` or the runner's configured `models.cursor`.** Pass the explicit id.
- **Reading or hashing `auth.json`/`authInfo`.** Allowlist keys before any hashing; never print values.
- **Counting the cursor shell function as a binary.** Detection must stay a PATH lookup and `subprocess` with a list argv, never `shell=True`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Frontmatter semantics | A YAML reader | A Python port of `Ks` plus a `skipUnless(node)` parity test that runs the **same JS** (`node -e`) on both shipped files | Cheap oracle against the bundle's regex/`m`-flag quirks |
| Models parsing | Another regex family | One public `parse_cursor_models` used by the Python detector; the JS runner keeps `parseCursorListingIds` (ids only) | Three parsers drift (Python, runner JS, fixtures) |
| Smoke/matrix | A cursor-only script | `tests/gsd_curated_eval.py smoke` with the G1-G5 fixes | Same oracle as Phases 19/20 |
| Dispatch | A direct `cursor-agent` call | `.planning/scripts/cross-ai.mjs --prefer cursor --model-cursor composer-2.5 --mode exec --no-preamble --child-pgid-file ...` | Timeouts, `AIKIT-XAI` line, env scrub, tree-state classification already built |
| Evidence masking | Hand-edited paths | The harness placeholder pass and `secret-scan` subcommand | Phase 20 WR-09 showed hand copies are lossy |

## Common Pitfalls

1. **Porting the regex without `re.M`** or anchoring at file start: files with leading text before `---` parse in the bundle and fail in the port (or the reverse). Use the parity oracle.
2. **Fast-id heuristics on the whole list.** Some listed ids legitimately contain `fast` only as a suffix twin; the rule is `not id.endswith("-fast")` and `id in fixture` (D-08), not substring matching.
3. **Strict `cli-config.json` guard** fails every honest cursor run (G2). It is the likeliest first red.
4. **Smoke work dir inside the repo** (T-20-05): `TMPDIR` must point outside `<worktree>`; the harness refuses otherwise. Keep `tmp/p21` for research scratch only; the smoke itself uses `mkdtemp` outside the repo.
5. **Installer without `TMPDIR`** crashes with `mkdtemp ENOENT` (seen); the harness's `INSTALL_ENV_KEEP` already passes `TMPDIR`.
6. **Runner `no_change` outcomes.** Phase 20 saw 4 of 6 codex dispatches end `no_change` without running the command; `status=no_change cli_rc=0` is healthy only when the host-written evidence file proves the smoke ran. Judge success from `smoke exit=0` plus the evidence, never from the runner status alone.
7. **Orphaned `worker-server`** (finding 3). Reap by recorded pgid; check `ps` before and after.
8. **Zero-width characters in labels** are harmless for first-token ids but break `endswith` on labels; never parse labels for ids.
9. **Template edits are version events.** Any byte change to `cross-ai.mjs` moves its stamped `sha256` and requires re-rendering `.planning/scripts/cross-ai.mjs` (20-REVIEW-FIX, IN-02 note).
10. **Stale counts from Phase 20** ("Ran 36 tests", 20-06 branch-consistency verify) are superseded; do not copy them into Phase 21 verify strings.

## Code Examples

Parser port (derived from the verbatim `Ks`; the planner may rename):

```python
import re

_FM = re.compile(r"^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$", re.M)  # JS /m flag

def parse_agent(text: str):
    """Mirror of the cursor-agent 2026.10.14 line parser; None = file dropped."""
    m = _FM.search(text)
    if not m or not m.group(2).strip():
        return None
    fields = {}
    for raw in m.group(1).split("\n"):
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        if key.strip():
            fields[key.strip().lower()] = value.strip()
    return fields
```

Models parser skeleton (token based; pure):

```python
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

def parse_cursor_models(stdout: str) -> list[str] | None:
    ids, saw_empty_notice = [], False
    for raw in _ANSI.sub("", stdout).splitlines():
        line = raw.strip()
        if not line or line == "Available models" or line.startswith("Tip:"):
            continue
        if line == "No models available for this account.":
            saw_empty_notice = True
            continue
        ids.append(line.split()[0])
    return ids if ids or saw_empty_notice else None
```

Resolver delta (scan all PATH entries; `which` has no "all" mode, so iterate directories):

```python
def _path_hits(name, path_env, which_fn):
    for d in path_env.split(os.pathsep):
        hit = which_fn(name, path=d) if d else None   # functools.partial(shutil.which, path=...) seam
        if hit:
            yield hit
```

Keep `cursor-agent` first-found; for `agent` accept the first hit whose `realpath` basename is `cursor-agent`; record `real_path` beside `path`; if both names resolve to one real file, report once (the current "cursor-agent wins" order already does). `RUNTIMES_SCHEMA_VERSION` (currently 5, `detection.py:28`) must bump when `real_path` is added (its own comment requires it); the bump makes existing snapshots re-detect, which runs `<binary> models` once (a `~/.cursor/cli-config.json` rewrite by the CLI itself, an accepted side effect; document it).

SC5 (native per-call model selection from cursor): the Task tool's `TaskArgs` carries an optional `model` string (`index.js@5026551`: `|3 subagent_type #0|4 model 9?|5 resume ...`), and the todo records one live run where a per-call `model` was honored on 2026.10.01 [CITED: `.planning/todos/pending/2026-10-13-add-cursor-subagents-...md`]. `host_can_select` is built on a fixed `native_selectors` alias tuple (`routing.py:44-58`, claude-only), so cursor stays session-default-only unless a design change (listing-based selection) is adopted. Recommendation: take the ROADMAP SC5 "keeps the session-default-only label" branch, extend `test_non_claude_hosts_have_no_native_selectors` (`test_ai_kit_spec_runtimes_table.py:96-104`) to cursor, and make the optional live check an OPTIONAL step in the interactive script that reads a Task call's `model` from `--output-format stream-json`. Do not build listing-based selection in this phase.

## Runtime State Inventory

Not a rename/refactor phase; one migration-like item: the `runtimes.json` schema bump. Stored data: users' cached `runtimes.json` (v5) is treated stale and re-detected, so the first run after the bump runs `cursor-agent models`. Live service/OS/secret state: none. Build artifacts: none (the stamped `.planning/scripts/cross-ai.mjs` changes only if the runner template is edited).

## State of the Art

| Old (Phase 18.1 / 2026.10.01) | Now | Impact |
|---|---|---|
| parser `Hs` | `Ks` (same logic) | cite by behavior, not symbol |
| first-hit guarded `agent` resolution | D-09 scan-all + `real_path` | closes the grok-before-cursor PATH-order case |
| symlink "followed wherever it points" | files followed, directories outside workspace skipped | per-file links only (already D-01) |
| cursor installer assumed to bake models | bakes none | chain is resolve-model only |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `worker-server` stays in cursor-agent's process group (`detached:false`), so a post-exit `kill -- -<pgid>` reaps it | Answer 3 | Orphans stay; need pid-file/`ps`-based reap |
| A2 | A normal `-p` exit also leaves the server (observed only after `models`) | Answer 3 | Reap step is harmless but unnecessary |
| A3 | Invalid frontmatter `model` behavior (error vs inherit) is server-side | Answer 2 | Only matters for non-validated pins |
| A4 | `grok-4.7-medium` exists on other accounts | Answer 2 | Pin invalid elsewhere; test cannot detect it |
| A5 | Per-call Task `model` is honored on 2026.10.14 (verified only on 2026.10.01) | SC5 | SC5 label branch unaffected (keeps session-default-only) |
| A6 | The cursor cli-config user-owned key allowlist (`modelParameters`, `subagentModels`, `exploreSubagentModel`) is complete for "ai-kit never writes" | G2 | A missed user key goes unprotected |
| A7 | The unmodified matrix passes with `host="cursor"` | G5 | Extra fixes in recommend/apply for cursor (not run: harness needs the real HOME) |
| A8 | GSD workflows inside cursor honor `resolve-model` results | Answer 4 | Label text must stay "resolve-model only" |
| A9 | A headless runner dispatch of cursor-agent with the `exec` argv works under the user's real login on 2026.10.14 | Answer 3 | Dispatch fallbacks; not probed per hard rules |

## Open Questions

1. **R8 module-count rule for harness changes.** G2-G5 touch `tests/gsd_curated_eval.py` and test files; G1 touches `host.py`. Recommendation: count shipped product modules only, so G1 plus detection hardening (`detection.py`) are separate one-module fixes in-phase; the harness is evidence scaffolding. If the planner reads "module" as any Python file, split the harness work into Phase 21.x. Decide before planning.
2. **Mirror D-09 into the runner template?** `resolveBin` in `cross-ai.mjs` is first-hit; scan-all there is a template-version event (re-render, stamped sha, template self-test). Best-over-easy says mirror it; it is a separate task with its own render step. Record the choice.
3. **Cursor env-signal label.** Upgrade `_LABEL_CURSOR` only if the smoke's names-only env dump from cursor's shell shows `CURSOR_AGENT`; otherwise leave `source-inspected-only` (certainty rule).
4. **Dispatch HOME.** The runner/cursor needs the user's login. Phase 20 ran the hosts under the real HOME with a before/after guard. Alternative proven in the D-01 spike: scratch HOME plus a symlinked `auth.json`. Recommendation: real HOME with the semantic guard (G2) for the dispatch; scratch HOME + symlink for any extra probe.
5. **Unauthenticated failure fixture** (`Authentication required`, exit 1): the bundle's own text is `Authentication failed: ...`/`Failed to load models: ...` (`6436.index.js@1520`); the fixture should be synthesized from those strings, and labeled synthetic, unless the user supplies a captured one.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| node | gsd-core, parity oracle, matrix | yes | v24.21.0 | none |
| python3 / uv / git / shellcheck | gates | yes | 3.14.7 / 0.11.28 / 2.55.0 / present | none |
| gsd-core 1.17.0 installer (npx cache) | smoke local install | yes | 1.17.0 (two cached copies; a 1.13.0 copy also exists, pin selects 1.17.0) | `--installer-dir` |
| cursor-agent 2026.10.14 | R1 dispatch, R4 | yes (not executed here) | 2026.10.14-941492e | none |
| pi | skill-judge second judge | yes (model access unprobed) | 1.3.0 | native Opus only, recorded as a gap |
| real HOME for matrix/snapshot | matrix, protected set (19 D-08) | n/a here | A scratch-HOME attempt failed even for `host="claude"` with `config-path failed` (this machine's Node is a version-manager shim that needs the real HOME) | executor runs the matrix and snapshot as the Phase 20 tests do |

Missing with no fallback: none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` via `tools/run_unittest_parallel.py` (groups: unit, unit-uv, integration, e2e, arch) |
| Config file | `Makefile`, `.pre-commit-config.yaml` (group lists generated by `tools/gen_test_groups.py`, pinned by `tests/test_gate_scope.py`) |
| Quick run | `python3 tools/run_unittest_parallel.py --group unit -- tests.test_cursor_agents tests.test_ai_kit_spec_runtimes_table` |
| Full suite | `make test` then `make validate` |

### Phase Requirements -> Test Map
| Req | Behavior | Type | Command | Exists? |
|-----|----------|------|---------|---------|
| SPEC-06 | `agent` only (cursor symlink), only `cursor-agent`, both (one report), grok-first PATH then cursor later, shell function invisible | unit | `python3 -m unittest tests.test_ai_kit_spec_runtimes_table -k Guarded` | extend existing class (`:195-240`), Wave 0 |
| SPEC-06 | no shell spawned: `run_fn` called with a list argv, `shell` not truthy, env without `BASH_ENV` | unit | same module | Wave 0 |
| SPEC-06 | `real_path` recorded; schema bump re-detects | unit | `python3 -m unittest tests.test_ai_kit_spec -k runtimes` | Wave 0 |
| SPEC-06 | `parse_cursor_models`: capture, nameless `auto (current, default)`, ANSI, empty-account notice, exit 1 -> `None` | unit | `tests.test_ai_kit_spec` | Wave 0 (needs `tests/fixtures/cursor_models*.txt`) |
| AGT-01 | both files parse with the ported parser, fields only from the bundle list, non-empty body | unit | `tests.test_cursor_agents` | Wave 0 |
| AGT-01 | pins in the captured fixture and not `-fast`; names not `gsd-*` and equal to stems; live cross-check `skipUnless(node)` | unit | same | Wave 0 |
| AGT-01 | parity: the same JS regex via `node -e` agrees on both files | unit (skipUnless node) | same | Wave 0 |
| EVAL-07 | matrix cursor class, 5x35, `GSD_RUNTIME=cursor`, no `-fast` pick | e2e | `python3 tools/run_unittest_parallel.py --group e2e -- tests.test_ai_kit_gsd_curated_config_matrix` | extend (G5) |
| EVAL-07 | G1 regression (cursor first-root), G2 semantic guard (rewrite of `privacyCache` passes, change of `modelParameters` fails), G3/G4 cursor branches | unit | `tests.test_curated_config_inventory`, `tests.test_gsd_curated_eval` | Wave 0 |
| EVAL-07 | smoke evidence + label lift | manual-only (live) | runner dispatch and user script; evidence file | `21-SMOKE-CURSOR.md` |
| EVAL-07 | label test: SKILL.md has no cursor "not live-validated", still has pi's; README matches | unit | `tests.test_curated_config_apply -k required_statements` | update |
| SC5 | cursor `native_selectors == ()`; `host_can_select("cursor", ...)` False | unit | `tests.test_ai_kit_spec_runtimes_table` | extend |
| R8 | `make test`, `make validate` | gate | per Makefile | existing |

### Sampling Rate
Per task: the quick command for the touched module. Per wave: the full `unit` and `arch` groups. Phase gate: `make test` and `make validate` green, `tests.test_gate_scope` passing after regenerating group lists, then `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/fixtures/cursor_models.txt` (copy of the capture), `cursor_models_empty.txt`, a synthesized failure fixture
- [ ] `tests/test_cursor_agents.py` (and its registration through `tools/gen_test_groups.py`)
- [ ] `cursor-agents/*.md`
- [ ] A cursor fixture-free hermetic variant of the smoke exists (the seeded `tests/fixtures/curated_config_v2/runtimes.json` already carries 16 cursor models incl. `composer-2.5-fast`)

## Security Domain

### Applicable ASVS Categories
| ASVS | Applies | Control |
|------|---------|---------|
| V5 Input validation | yes | parsers treat listing/agent text as untrusted: bounded, first-token ids, regex-validated model ids (`CURSOR_MODEL_ID`) |
| V12 Files/resources | yes | per-file symlink reasoning (no directory links), scratch dirs outside the repo (T-20-05) |
| V14 Configuration | yes | protected-set guard for `~/.cursor`, `~/.gsd`; no writes to `cli-config.json` |
| V2/V3/V4/V6 | no | no authentication, session, access-control or crypto code is written |

### Threat Model

| ID | Threat | STRIDE | Mitigation | Verification |
|----|--------|--------|------------|--------------|
| T-21-01 | Detection executes the user's `cursor-agent` shell function or an interactive shell | Elevation | PATH lookup + `subprocess` list argv, no `shell=True`, `run_fn` seam asserted | unit test on argv/`shell` |
| T-21-02 | A live cursor run rewrites `~/.cursor/cli-config.json` and the guard either false-fails or hides a real ai-kit write | Tampering | semantic digest over user-owned keys; listings for `agents/`, `skills/`, `hooks.json` | G2 tests, before/after snapshot in evidence |
| T-21-03 | Credentials or PII (`authInfo` email/name) enter evidence | Info disclosure | never open `auth.json`; hash allowlisted keys only; `secret-scan` over evidence; placeholders for paths | `gsd_curated_eval.py secret-scan <evidence>` |
| T-21-04 | Headless cursor runs with `--force --sandbox disabled --approve-mcps` (full permissions) | Elevation | fixed prompt, scratch work dir outside the repo, no network-dependent steps, tree-state (`clean`) classification by the runner | runner `AIKIT-XAI` line, snapshot check |
| T-21-05 | Orphaned `worker-server` processes after dispatch | DoS | `--child-pgid-file` + group reap; `ps` check before/after | evidence records none left |
| T-21-06 | Installer writes global `~/.gsd/defaults.json` (`runtime: cursor`, `resolve_model_ids: omit`) | Tampering | throwaway HOME seeded by copy (20 D-09); `~/.gsd` in strict listing | allowlist check in evidence |
| T-21-07 | A shipped agent pins a `-fast` or config-dependent id | Tampering (cost) | D-08 test against the captured listing | `tests.test_cursor_agents` |
| T-21-08 | A shipped agent name collides with a `gsd-*` agent or another project agent (first-wins per root) | Spoofing | D-07 rule + optional live catalog cross-check | same |
| T-21-09 | Supply chain: smoke fetches an unpinned gsd-core | Tampering | cached installer only, version pinned to 1.17.0 (`_pinned_version`), never npx in the smoke | harness refusal text |

## Sources

### Primary (HIGH)
- Cursor bundle, read statically: `<bundle>/index.js` (offsets above), `6436.index.js`, `3548.index.js`, `1623.index.js`.
- gsd-core 1.17.0 cached installer source and an actual `--cursor --local` run under `<worktree>/tmp/p21/inst/`.
- Repo files read this session: `detection.py`, `routing.py`, `host.py`, `followups.py`, `recommend.py`, `gsd_curated_eval.py`, `cross-ai.mjs` (template and rendered), matrix test, runtimes-table tests, `SKILL.md`, `README.md`, Phase 20 CONTEXT/REVIEW-FIX/SMOKE/INTERACTIVE/SKILL-JUDGE, Phase 21 CONTEXT/SPEC/SPIKE.

### Secondary (MEDIUM)
- `.planning/todos/pending/2026-10-13-add-cursor-subagents-...md` (live runs on 2026.10.01; not re-verified on .14).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (nothing new).
- Architecture / harness gaps: HIGH for G1 (reproduced) and G3 (installer run), MEDIUM for G2/G5 (read, not run).
- Pitfalls: MEDIUM (process-group and dispatch behavior need the live run).

**Research date:** 2026-10-18 · **Valid until:** until cursor-agent or gsd-core updates (bundle symbols are minified and change per release; re-grep before relying on offsets).

## RESEARCH COMPLETE
