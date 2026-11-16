# Phase 34: jev backends by host and Laya calibration - Research

**Researched:** 2026-11-15
**Domain:** stdlib-only Python skill (`skills/jev-fast-decision/`): config reader copy, version/fingerprint probe, fetch-once records, calibration, knob, guard tests, judge loop
**Confidence:** HIGH for the code map, network shapes and test infrastructure (all read or fetched this session); MEDIUM for the knob and fingerprint designs (two real conflicts found, see Open Questions)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01: `[jev]` keys:** `laya_url` (string), `laya_version` (optional string, set by the user when the server does
  not expose one), `enabled` (bool). Project over user per key; the environment variables (`JEV_LAYA_URL`,
  `AI_KIT_LAYA_URL`, `GSD_PATH_JEV`) stay session overrides above both. Owner's words (any address; nothing assumed
  about localhost).
- **D-02: The skill copies Phase 33's layered reader** (33 D-22) into its scripts with a parity test, so the skill stays
  self-contained; writes go through a copy of 33's splicer limited to the `[jev]` table.
- **D-03: The first-run question is the agent's, not the script's.** Scripts run non-interactively under agents: the
  probe reports `needs_answer: laya_url` (or `enabled`) and SKILL.md tells the agent to ask the user once through its
  host's question tool and save the answer with `jev_review.py config set <key> <value>`. A declined Laya records
  `laya_url = ""` (no Laya) so it is not asked again; non-interactive runs with `enabled` absent default to on and say
  so in the probe.
- **D-04: Version source order:** a package-version field from the server (none today), then `[jev] laya_version`, then
  "not exposed". The fingerprint is the sha256 of the canonical JSON of `/openapi.json` `info` plus its sorted route
  and method list, plus `/health` `loaded` and `revisions`. The probe row shows version, version source and the first
  12 hex characters of the fingerprint.
- **D-05: Records live in `${XDG_STATE_HOME:-~/.local/state}/ai-kit/jev/`:** `laya-capabilities.json` keyed by version
  (or `fp:<fingerprint>` when the version is not exposed) and `typesafe-models.json` keyed by model id. Each entry:
  `checked_at`, source URLs, the fetched notes (text, trimmed), and `features_documented` (names found in the notes).
  Written atomically; never committed.
- **D-06: Laya sources, fetched once per unknown key:** PyPI JSON `https://pypi.org/pypi/laya/json` (`info.version`,
  release list and the README's "What's new" section) and the project README on GitHub; 5-second timeout each; no key,
  no header beyond a plain user agent. When the version is "not exposed", the entry records the latest upstream release
  and notes that the running one may differ. A failed fetch keeps the previous entry and prints one notice.
- **D-07: How jev uses what it learns is the agent's call.** The script records and reports ("new Laya features
  documented upstream: ..., not verified here"); SKILL.md tells the agent to read the record when the probe says `new`
  and decide whether an item type or option could now go to Laya; a capability cell turns verified only through a
  recorded live run, as today.
- **D-08: `--check-updates` stays as the on-demand refresh** of both records (it re-fetches the current keys); the
  fixed 24-hour and 7-day caches of the 2026-11-07 wording are dropped: a key's record stays valid until the key
  changes.
- **D-09: A new model id triggers the official doc flow once:** docs.typesafe.ai `llms.txt`, then `changelog.md` and
  `models.md`; when the `typesafe-ai` skill is installed, SKILL.md points the agent at its doc flow for item design as
  JEV-08 already does. The record notes which of our features the change could serve (box, images, long context,
  batching). The check runs after an answer is logged, never before or during a call.
- **D-10: Calibration** uses `scripts/eval_cases.py calibrate` against the configured Laya, records confident-answer
  accuracy, the floor, the version (or fingerprint) and the checkpoint revision in `backends/laya.md` with the date;
  the raw run stays under `tmp/`; a how-to section goes in `reference.md`. The opencode judge lane is re-judged in the
  same loop. No upgrade step (owner, 2026-11-14).
- **D-11: The limit sentence** ("a confident Laya answer is not proven accurate") goes in SKILL.md's result recipe and
  `backends/laya.md` with the latest numbers; a doc-contract test pins both.
- **D-12: `backends/laya.md` records the MCP decision** with its reason; the shared-state spike is a dated record in
  `reference.md` (method, cases, result).
- **D-13: Guard test `tests/test_jev_fast_decision_guard.py`** scans the skill tree (scripts, SKILL.md, references,
  backends, evals) and fails on Zen, on `opencode` used as a backend name (the host-folder lines are allowed), and on
  any step that hands Laya's or the official skill's install or upgrade to tools-installer or another repo.
- **D-14: Loop `34` judges `jev-fast-decision`** (its SKILL.md changes materially: settings, probe and records).
  Judges referee-one and referee-two; referee-three replaces one that fails; one usable referee is accepted with the
  reason recorded; never native opus.
- **D-15: REQUIREMENTS amendments in this phase's commit:** JEV-03 (no upgrade step; calibrate the running version),
  JEV-10 (version-keyed fetch once, replacing the fixed caches), new JEV-12 (TypeSafe awareness) and JEV-13 (no Zen,
  no delegation guard); ROADMAP Phase 34 criteria follow.

### Claude's Discretion

- Function names, the exact notice wording, and the trimming length of stored notes.

### Deferred Ideas (OUT OF SCOPE)

- Asking upstream Laya to expose its package version over HTTP (owner's call; the fingerprint covers the gap).

(Out of scope per CONTEXT: Laya's install, upgrade and server (`llm-env`); the official skill's install; images and box (Phase 54); the four-file marker block (Phase 54).)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| JEV-01 | Backend per host: Laya first at `[jev] laya_url`, TypeSafe from env, home-file key strictly last; probe names missing key source and multiplexer hint; first-run question | Code map section 1; found a mis-ordered `key_expected` label list (Pitfall 4); `[jev]` reader copy (section 3); the loopback rule that D-01 supersedes (Pitfall 1) |
| JEV-03 | Calibrate Laya on the running version; state the confident-answer limit; no upgrade | `eval_cases.py` has `--record`/`--calibrate`, not a `calibrate` subcommand (Pitfall 6); live `/health` shape; bounded calibration step design |
| JEV-07 | `[jev] enabled` knob for every skill, asked once | All consumers of `GSD_PATH_JEV` listed; the callers force `GSD_PATH_JEV=1`, which defeats a naive env-over-config order (Open Question 1) |
| JEV-10 | Version at the configured address; fetch Laya notes once when unknown; `--check-updates` refresh | Live shapes of `/health`, `/openapi.json`, PyPI per-version JSON, README heading; fingerprint idle flap (Pitfall 2) |
| JEV-11 | MCP decision record and shared-state spike record | `backends/laya.md` and `reference.md` homes; doc-contract pattern from `TestDocs` |
| JEV-12 | TypeSafe new model id / feature triggers the doc flow once | docs.typesafe.ai shapes; pending-note design that keeps the answer path fetch-free (Pattern 4) |
| JEV-13 | Guard test: no Zen, no opencode backend, no delegation | Guard scan design; allowed host-folder lines found by rg (section 8) |
</phase_requirements>

## Summary

The skill today is a 2017-line `jev_review.py` plus `jev_ladder.py` (663 lines), `eval_cases.py`, `secret_shapes.py`, one 3692-line test module and docs. Nothing reads `config.toml`; the Laya URL comes from env vars or the fixed default; the probe discards the `/health` body; there is no `--check-updates`, no multiplexer hint, no `needs_answer`. Phase 33 left a ready reader (`cfg_layered_table`, 9 definitions, 83 lines) and splicer (`set_table` + `publish`, 42 definitions, 348 lines plus `cache_write_bytes`) to copy. The design fits the existing seams: new Laya-aware code goes in new sibling modules loaded by path (the `_load_secret_shapes` precedent) or in `_laya_*` adapter functions, because `tests/test_jev_fast_decision.py::TestSeam` fails any other module-level function in `jev_review.py` that holds the string `laya` or `typesafe`.

Four facts shape the plans and are not in CONTEXT or SPEC. (1) `SKILL.md` has 487 body words and `test_doc_body_words` caps it at fewer than 500, so the first-run question, the limit sentence, the knob and the records handling must mostly live in `reference.md`. (2) Every caller (`jev_ladder.child_env`, `tools/judge_loop.py:1746`, `tools/hooks/precompact_core.py:121`) forces `GSD_PATH_JEV=1` into the child env, so "the environment overrides the config" would make the knob useless; this needs an owner-level decision before the knob plan is written. (3) The live Laya unloads its checkpoint after 600 s idle and then reports `loaded: []`, `revisions: {}`, so D-04's fingerprint flips between idle and loaded. (4) The existing test `test_probe_reports_mycreds_fallback_and_expected_sources` pins the wrong label order (`file:~/.mycreds` before `state`) while the real resolution order puts the state file first; JEV-01 "home-file key strictly last" needs both the code list and that test fixed.

Network shapes were fetched live and saved under `tmp/auto/r325/research34/`. The most useful discovery: `https://pypi.org/pypi/laya/<version>/json` returns that release's own README (with its `## What's new in <version>` heading) and no `releases` key, so notes for the running version are one keyless GET away once the version is known.

**Primary recommendation:** Build three new stdlib sibling modules under `skills/jev-fast-decision/scripts/` (`jev_config.py` reader+splicer copy, `jev_learn.py` version/fingerprint/records/fetch, optionally `jev_knob.py` folded into `jev_config.py`), wire them into `jev_review.py` only through `_laya_*` adapters and `probe_report`/`main`, keep every public fetch out of `screen()`/`ladder`, move prose to `reference.md`, and ask the owner the two flagged questions first.

## Project Constraints (from CLAUDE.md / AGENTS.md)

- Runtime code under `skills/jev-fast-decision/scripts/` stays stdlib-only; atomic writes use `tempfile.mkstemp` plus `os.replace`; no real config files as fixtures (AGENTS.md "Non-Negotiable Rules", "Testing").
- No diagnostic result shown with more certainty than its sourcing: upstream notes are "documented upstream, not verified here"; a capability cell never turns `verified-live` from text (SPEC prohibition, AGENTS.md).
- Any materially changed SKILL.md passes the `skill-judge` loop (D-14); judge loop stops after three rounds; disputed findings only refuted by a recorded run.
- Never hardcode an absolute path in source, tests or docs; English only.
- Tests run in a scratch HOME with `AI_KIT_REFUSE_REAL_HOME=1`; no test reads `.planning/` (`tests/test_arch.py::test_no_test_reads_planning`, line 2249); a stub for each host CLI sits on PATH.
- New `tests/test_*.py` joins the `unit` group automatically; the generated listings in `Makefile` and `.pre-commit-config.yaml` must be regenerated in the same commit (`python3 tools/gen_test_groups.py`; `tests/test_gate_scope.py` fails while stale).
- Docs (`docs/config/design.md`, READMEs, `reference.md`) are updated in the same change; stale docs are a defect.
- Rails (`tmp/auto/r325/rails.md`): haiku-executable plans, exact paths and commands, one simple shell command per call, no `cd`, no heredocs, no command substitution; tell every subagent the shell rules verbatim; ponytail lens; reviewers from `.planning/config.json` only.
- Ponytail: reuse `_state_dir`, `write_consent`'s atomic pattern, `_exchange`, `_read_body`, `_Deadline`, `JevStub`; no speculative abstraction.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Read `[jev]` layers, write `config set` | Skill script (`jev_config.py`) | docs/config/design.md (record) | Self-contained copy of Phase 33's reader/splicer (D-02) |
| First-run question | Agent via SKILL.md | Script reports `needs_answer` | D-03: scripts are non-interactive |
| Backend choice and probe | `jev_review.py` (`probe_report`, table rows) | `jev_ladder.py detect` | Existing seam; one probe per row |
| Laya version and fingerprint | `_laya_*` adapter + `jev_learn.py` | state dir record | Local GETs (`/health`, `/openapi.json`), no key |
| Capability records, upstream fetch | `jev_learn.py` (probe path only) | `--check-updates` | Never on the answer path (SPEC prohibition) |
| TypeSafe model-id awareness | `screen()` writes a local pending note; probe/`--check-updates` fetch | official `typesafe-ai` skill doc flow | Keeps the answer path network-free |
| Knob (`enabled`) | jev client (single evaluation point) | callers (`jev_ladder`, `judge_loop`, hooks) | All callers reach jev through the client |
| Calibration | `eval_cases.py` (record + calibrate) | orchestrator step, `tmp/` raw run | Needs live Laya; degrades with a recorded reason |
| Doc contracts and guard | `tests/` | skill docs | Pins sentences; scans the tree |
| Judge bar | `tools/judge_loop.py` + loop 34 records | `.planning/judge/` | Existing loop machinery |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`tomllib`, `urllib`, `http.server` in tests, `hashlib`, `json`, `tempfile`) | python3 on this machine | everything | AGENTS.md: runtime code stays stdlib-only |
| Phase 33 reader/splicer (copied) | `config_io.py` (959 lines), `toml_splice.py` (792 lines) at HEAD | layered `[jev]` read and `config set` write | D-02 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unittest` + `JevStub` (`tests/test_jev_fast_decision.py:132`) | repo | fake Laya | New tests import it (precedent: `from tests.test_jev_fast_decision import JevStub`) |
| `tools/judge_loop.py` | repo | loop 34 | D-14 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| AST-sliced splicer copy (348 lines) | a 3-key hand writer | D-02 is locked ("a copy of 33's splicer"); a hand writer would also drop comment preservation that AGENTS.md requires for config edits |
| New sibling modules | grow `jev_review.py` | `jev_review.py` is already 2017 lines and its seam test forbids backend names outside `_laya_*`/`_typesafe_*` functions |

**Installation:** none. No third-party package is added.

**Version verification:** no packages recommended; PyPI `laya` is queried as data only, never installed (guard test forbids it).

## Package Legitimacy Audit

No external package is installed by this phase (stdlib only). `laya` and `typesafe-ai` are read as public web data, never installed or upgraded; the guard test enforces that.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | - | - | - | - | - | - |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
agent runs: GSD_PATH_JEV=1 jev_review.py --probe          (once per session; hooks run it with a short deadline)
   |
   v
probe_report()
   |-- jev_config.layered_jev(cwd, env)  --> project .aikit/config.toml over user config.toml  (laya_url, laya_version, enabled)
   |        |-- env JEV_LAYA_URL / AI_KIT_LAYA_URL override per key
   |        '-- absent key -> needs_answer: laya_url | enabled   (agent asks once, then `config set`)
   |-- per row: _row_probe -> GET /health (0.7 s, no proxy for Laya)       [existing]
   |-- Laya row: GET /health body + GET /openapi.json  (same origin, capped read) --> version source + fingerprint
   |-- key = version | "fp:<12+ hex>"  --> state dir  laya-capabilities.json
   |        |-- known key: no fetch
   |        '-- unknown key: (deadline permitting) GET PyPI per-version JSON (+ README raw) --> trimmed notes + features_documented
   |                         failure: keep old entry, one notice
   |-- typesafe-models.json: pending notes from earlier answers -> docs.typesafe.ai llms.txt, changelog.md, models.md (once per id)
   '-- report: selected backend, laya row {version, version_source, fp12, record: known|new|unknown|skipped}, key_expected (home file last), multiplexer hint

answer path (screen / ladder):  kill switch + knob -> _selection (GET /health only) -> POST per item -> append answer log
   '-- on a TypeSafe answer: compare reported model id with typesafe-models.json; an unseen id becomes a LOCAL pending note (no network)
```

### Recommended Project Structure

```
skills/jev-fast-decision/
  SKILL.md                      # body < 500 words (test_doc_body_words); pointers only
  reference.md                  # + ## Settings (config), ## Records and learning, ## Calibration how-to, ## Decision records (MCP, spike)
  backends/laya.md              # + calibration record, limit sentence, MCP decision; loopback wording replaced
  scripts/jev_review.py         # thin wiring: probe row fields, config subcommand, --check-updates, knob gate
  scripts/jev_config.py         # NEW: reader copy (83 lines) + splicer copy (348 lines) + publish; AST-parity-tested
  scripts/jev_learn.py          # NEW: version, fingerprint, records, public fetch, features_documented
tests/
  test_jev_config.py            # reader/splicer behaviour, config set, knob
  test_jev_config_parity.py     # AST equality of the copied definitions with config_io / toml_splice
  test_jev_learn.py             # fake servers: version, fingerprint, fetch-once, failure, refresh
  test_jev_typesafe_models.py   # model-id record cases
  test_jev_fast_decision_guard.py  # D-13
  test_jev_doc_contract.py      # R6 sentence, R8 MCP sentence, SKILL pointer (or fold into the guard module)
```

### Pattern 1: Sibling module loaded by path
**What:** `jev_ladder.py` loads `secret_shapes.py` with `importlib.util.spec_from_file_location` because the module is itself loaded by path in tests.
**When to use:** every new sibling the client needs.
**Example:**
```python
# Source: skills/jev-fast-decision/scripts/jev_ladder.py:61-73 (read this session)
def _load_secret_shapes() -> Any:
    path = Path(__file__).resolve().parent / "secret_shapes.py"
    spec = importlib.util.spec_from_file_location("jev_secret_shapes", path)
```
A copy-install test already exists for the sibling case: `tests/test_secret_shapes_copy_install.py` (a script copied without its sibling fails with `ImportError`). Add the new siblings to it or add an install check to `tests/test_jev_skill_install_e2e.py`.

### Pattern 2: Atomic record write (reuse, do not add a third copy)
`write_consent` (`jev_review.py:1013-1027`) is `tempfile.mkstemp(dir=..., prefix=".jev-consent-")` + `os.replace`, 0600 from mkstemp. Generalize it into one `_write_json_atomic(path, data)` and call it from `write_consent` and the records writers. The state dir helper is already there: `_state_dir()` at `jev_review.py:1604` returns `<XDG_STATE_HOME or $HOME/.local/state>/ai-kit`; records go in `os.path.join(_state_dir(), "jev")`. No other ai-kit helper is reusable (each of `tools/global_rules.py:188`, `tools/config_doctor_appliers.py:431`, `ai_kit_session_wake/state.py:59` is its own copy).

### Pattern 3: Fetch seam
One module function `fetch_public(url, timeout)` (urllib, plain `User-Agent`, no `Authorization`, capped `_read_body`, `_exchange(deadline, timeout, remote=True)` so a corporate proxy still works for public hosts). Tests patch the module-level URL constants to a local `http.server` stub or patch `fetch_public` to a recorder; the answer-path test patches it to a function that raises.

### Pattern 4: TypeSafe answer-path rule
SPEC prohibits any fetch on the per-item answer path and D-09 says the check runs "after an answer is logged". These agree only if the answer path does a local write: after `_log_run(run)` in `screen()`, compare each TypeSafe answer's reported id (already extracted by `_JEV_RESPONSE`, `jev_review.py:832`) with `typesafe-models.json`; an unseen id writes `{"status": "pending", "first_seen": ts}` locally; the doc-flow fetch runs from `--probe` or `--check-updates` (and the probe reports `new`). [ASSUMED: this reconciliation is my reading; it changes neither locked text.]

### Anti-Patterns to Avoid
- **Fetching inside `_selection` or `_laya_probe`:** both run on every `screen()` call (`jev_review.py:1212`, `1955`); a fetch there violates the SPEC prohibition and the "answer run with a failing fetcher" test.
- **Naming `laya`/`typesafe` in new module-level `jev_review.py` functions or string literals** outside `_laya_*`/`_typesafe_*` adapters and the `TABLE` literal: `TestSeam.test_seam_ast_rule_accepts_the_real_client` fails (regex `(?:^|[^a-z])laya(?:[^a-z]|$)` also matches `"laya_url"`).
- **A broad `except Exception` in new fetch code:** `tests/test_arch.py::test_rule9_broad_except_only_in_listed_backstops` (line 2284) allows only listed backstops; catch `OSError`, `ValueError`, `http.client.HTTPException`, `UnicodeError`.
- **Reading cwd implicitly in tests:** the runner's cwd is the repo root; a future `.aikit/config.toml` there would leak into tests. Every test passes or patches `cwd` to a temp dir.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Layered TOML read | own parser/merge | AST-identical copy of `cfg_layered_table` + deps | D-02; parity test catches drift |
| `[jev]` write preserving comments | string replace | copy of `set_table` + `publish` | AGENTS.md: preserve every other byte; `set_table` re-parses and refuses mismatches |
| Atomic JSON | new writer | generalize `write_consent` | already tested (`test_consent_record_shape_and_mode`) |
| Bounded HTTP read with deadline | raw `urlopen().read()` | `_exchange` + `_read_body` + `_Deadline` | trickle-server and watchdog cases are already handled |
| Fake Laya | new server class | `JevStub` (extend with `/openapi.json` and a `health_body` option) | existing precedent |
| Judge loop | new driver | copy `tmp/judge-33/*` drivers as 33-12 did | proven path |

**Key insight:** every hard part (atomic write, deadline-bounded read, layered read, splice with re-parse verification) already exists in the repo; the phase is wiring, records and docs.

## Common Pitfalls

### Pitfall 1: The loopback rule contradicts D-01 and existing tests pin it
**What goes wrong:** `_laya_url` returns `(None, "non_loopback_url")` for any non-loopback `JEV_LAYA_URL`/`AI_KIT_LAYA_URL` (`jev_review.py:573-578`); `tests/test_jev_fast_decision.py::test_probe_laya_url_sources` (428) and `test_probe_non_loopback_laya` (466) assert it; `reference.md:110`, `backends/laya.md:10-12` and `docs/config/design.md:175` document it.
**Why:** D-01 says "any address; nothing assumed about localhost".
**How to avoid:** the plan amends the function, both tests and the three docs together. Security consequence in Open Question 2 (a project `.aikit/config.toml` could name an arbitrary host and the Laya row has `remote: False`, so no consent applies).

### Pitfall 2: The fingerprint flips when Laya idles
**What goes wrong:** live `/health` on 2026-11-15 returned `"loaded":[],"revisions":{}` with `idle_seconds` 1806 and `idle_unload_seconds` 600.0 ([VERIFIED: live GET, `tmp/auto/r325/research34/laya-health.json`]). D-04 hashes `loaded` and `revisions`, so the key differs between unloaded and loaded states and each new key triggers a fetch and a "new" report. `idle_seconds` itself must not enter the hash.
**How to avoid:** see Open Question 3; at minimum exclude every `/health` field except `loaded` and `revisions`, and treat `loaded == []` as "no checkpoint loaded" rather than as a revision change. Records written under both keys are harmless (two small entries, then no more fetches).

### Pitfall 3: Fetches on the hook path
**What goes wrong:** `tools/hooks/precompact_core.py:40` caps the probe at `PROBE_CAP_SECONDS = 3.0` and `client_env` sets `GSD_PATH_JEV_DEADLINE_SECONDS` equal to it (lines 122-123); `claude_decision_probe.py` runs the same probe at SessionStart. Two 5 s public fetches inside `--probe` would be killed or exceed the hook budget.
**How to avoid:** `--probe` fetches only when no deadline is set or `deadline.left()` covers the fetch budget; otherwise it reports `record: "skipped_deadline"`. Also: `client_env` replaces `XDG_CONFIG_HOME` with a never-created dir, so hooks never see the user layer's `laya_url`/`enabled` (project layer only, via cwd). State that in the docs; hooks keep using the default loopback Laya (`pick_local_backend` accepts only `_LOCAL_HOSTS`, `precompact_core.py:68`).

### Pitfall 4: `key_expected` lists the wrong order
**What goes wrong:** `_typesafe_key_sources()` ends `expected += ["file:secrets.env", "file:~/.mycreds", "state"]` (`jev_review.py:759`) but `_typesafe_key` resolves `secrets.env`, then `state`, then `~/.mycreds` (`jev_review.py:790-794`); `test_probe_reports_mycreds_fallback_and_expected_sources` (1247-1249) pins the wrong list.
**How to avoid:** fix the label list to `[..., "file:secrets.env", "state", "file:~/.mycreds"]` and update that test; this is the JEV-01 "strictly last" probe fact. Keep the home-file fallback with a recorded reason (long-lived multiplexers and hosts started before the export keep an old environment; a test cannot show every agent shell inherits the key) [ASSUMED: owner may prefer removal; JEV-01 allows either with the stated condition].

### Pitfall 5: SKILL.md word budget
**What goes wrong:** body is 487 words; `test_doc_body_words` requires fewer than 500 ([VERIFIED: `tmp/auto/r325/research34/count_words.py` output "body words: 487 | description chars: 453"]); `test_doc_frontmatter` caps the description at 500 chars and pins "Laya (local), TypeSafe (remote, consent required)".
**How to avoid:** add about 60 words to SKILL.md at most: the `needs_answer` instruction, the limit sentence, one pointer line to `reference.md` sections. Everything else goes in `reference.md`. Do not raise the cap to fit prose (the judge rubric also rewards a lean body).

### Pitfall 6: `calibrate` is not a subcommand
**What goes wrong:** CONTEXT D-10 and ROADMAP say `scripts/eval_cases.py calibrate`. The script has flags: no flag runs 32 live cases and prints metrics; `--record PATH` saves per-case results; `--calibrate PATH` reads that file, proposes thresholds and REWRITES `min_confidence` in `jev_review.py` when a threshold qualifies (`eval_cases.py:199-220`). The run needs `GSD_PATH_JEV=1` and `GSD_PATH_JEV_TIMEOUT_SECONDS`, and prints nothing useful with the knob off; `report["n"] != 32` returns 1.
**How to avoid:** document the real invocation in the how-to; run `--record` first, inspect the proposal, and treat a `--calibrate` rewrite of `min_confidence` as a code change needing its own test/review (the 2026-10-23 run proposed null, so nothing was rewritten). The recorded fields (version or fingerprint, checkpoint revision, date) are not written by the script today: add them as metadata in the `--record` file (cheap) or write them by hand into `backends/laya.md` (D-10 names that file).

### Pitfall 7: Existing tests that must change
`test_probe_laya_up` (413-426) pins the exact Laya entry dict; `test_probe_uses_get_health_and_never_posts` (480-487) pins `[("GET","/health")]` as the only request; both change when the probe adds `GET /openapi.json` and new row fields. `JevStub.do_GET` answers every path with `{"status":"ok"}` (line 169-172); the new code must treat a body without `info` as "no fingerprint" (that is also the "unreachable `/openapi.json`" edge).

### Pitfall 8: Line-number cites in `docs/config/design.md`
The record cites `jev_review.py:984`, `:1613`, etc. (lines 110, 160-183, 248). Moving code shifts them; the design-record fitness test checks labels, not line numbers (`tests/test_config_design_record.py`), so nothing fails, but the record becomes wrong. Update the cites in the same commit.

## Code Examples

### The Phase 33 reader to copy (definitions, verified closure)
```python
# Source: skills/ai-kit-spec-review/ai_kit_spec/config_io.py:262-355, 540-558 (read this session)
# cfg_layered_table closure = ConfigError, _table_at, cfg_config_base, cfg_global_path,
# cfg_layered_table, cfg_load_layers, cfg_load_toml, cfg_local_path, cfg_parse_toml_bytes (83 lines)
def cfg_layered_table(cwd: str, env: dict, *table_path: str) -> dict:
    project, user = cfg_load_layers(cwd, env)
    return {**_table_at(user, table_path), **_table_at(project, table_path)}
```
Plus the `try: import tomllib` guard at lines 8-13.

### The splicer entry to copy
```python
# Source: skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py:429-448, 780-792
# closure of set_table + publish = 42 definitions, 348 lines (computed by tmp/auto/r325/research34/closure.py)
# publish() calls ai_kit_spec.cache.cache_write_bytes (mkstemp + chmod + fsync + os.replace + folder fsync, ~25 lines): copy it too.
new_text = set_table(text, ("jev",), {"laya_url": "http://host:8010"})
publish(path, new_text)
```
`config set` accepts only `laya_url`, `laya_version`, `enabled` (the "limited to `[jev]`" of D-02), writes the project layer when `./.aikit/` exists or the user layer otherwise [ASSUMED: layer choice is not in D-03; ask or follow `ai-kit-spec-config`'s default of "announce the exact path"], and refuses a link out of `.aikit/` the way `cfg_confine_project_file` does (`config_io.py:466-480`; add to the copy only if the project layer is writable here).

### Version, fingerprint, record key
```python
# D-04, D-05. idle_seconds and every other /health field are excluded from the hash.
doc = {"info": openapi["info"],
       "routes": sorted(f"{method.upper()} {path}" for path, ops in openapi["paths"].items() for method in ops),
       "loaded": health.get("loaded"), "revisions": health.get("revisions")}
fp = hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
key = version if version else f"fp:{fp}"      # probe shows version, source, fp[:12]
```
Server version field: none exists today; accept the first string among `/health` keys `version`, `package_version`, `laya_version` [ASSUMED: field name is a guess; no live server exposes one]; the `/openapi.json` `info.version` is the serve API ("0.1.0"), not the package, and must NOT be used as the version.

### Notes fetch for a known version
```
GET https://pypi.org/pypi/laya/<version>/json        -> info.description is that release's README
section = text from the line "## What's new in <version>" to the next "## " heading
no such heading -> record "no published notes" for the key (SPEC empty edge)
unknown version ("fp:" key) -> GET https://pypi.org/pypi/laya/json (latest), record latest release, note "running one may differ"
README: https://raw.githubusercontent.com/NandhaKishorM/laya/main/README.md (heading "## What's new in <latest>" at line 267)
```

## Network Shapes (read-only, fetched 2026-11-15; samples in `tmp/auto/r325/research34/`)

| Source | Result | Shape [VERIFIED: live GET, 2026-11-15] |
|--------|--------|----------------------------------------|
| `http://127.0.0.1:8010/health` | 200, 179 bytes | keys `status`, `loaded`, `revisions`, `device`, `device_is_preference`, `checkpoint_devices`, `cpu_fallbacks`, `idle_unload_seconds`, `idle_seconds`; no version field; `loaded: []` and `revisions: {}` when idle-unloaded |
| `http://127.0.0.1:8010/openapi.json` | 200, 2725 bytes | `openapi: 3.1.0`; `info`: `title: laya-serve`, `summary`, `version: 0.1.0`; paths `/health` (get), `/v1/route`, `/v1/systemone`, `/v1/systemone/batch` (post) |
| `https://pypi.org/pypi/laya/json` | 200, 255 KB | top keys `info`, `last_serial`, `ownership`, `releases`, `urls`, `vulnerabilities`; `info.version` = `0.4.34`; `info.description` (136,865 chars, markdown) holds the latest README; `releases` keys are version strings with file lists and `upload_time_iso_8601` |
| `https://pypi.org/pypi/laya/0.4.27/json` | 200 | top keys `info`, `last_serial`, `ownership`, `urls`, `vulnerabilities` (NO `releases`); `info.version` `0.4.27`; description contains `## What's new in 0.4.27`; upload 2026-11-06 |
| `https://raw.githubusercontent.com/NandhaKishorM/laya/main/README.md` | 200, 137 KB | `## What's new in 0.4.34` at line 267 (only the latest release has a section; older notes appear as `From 0.4.32:` bullet blocks); `master` branch not needed |
| `https://docs.typesafe.ai/llms.txt` | 200, 21.9 KB, `text/plain` | markdown link list `- [Title](https://docs.typesafe.ai/<path>.md): summary` |
| `https://docs.typesafe.ai/changelog.md` | 200, 1.2 KB, `text/markdown` | `**Jev 1.14**`, a date line, then bullets starting `Model ID \`jev-1.14.0\`.` |
| `https://docs.typesafe.ai/models.md` | 200, 8.2 KB | table row `Model ID` with `` `jev-1.14.0` `` and `` `jev-1.13.0` ``; question types row `Choice, Score, Noul, Box`; sections "Context length", "Long context" |

Notes: the upgraded owner Laya's package version is not exposed over HTTP (confirmed again). The `info.version` of `/openapi.json` is `0.1.0` (serve API). One extra `/health` GET and two extra README/PyPI GETs were made beyond "once each" to record heading shapes; all read-only, keyless, plain user agent. No POST was sent anywhere.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed 24 h cache + 7 d `--check-updates` (2026-11-07 wording) | Version/fingerprint-keyed record, fetched once when unknown, `--check-updates` on demand | 2026-11-14 owner decision | No time-based expiry code |
| "Upgrade Laya 0.4.2 to 0.4.27 before calibrating" | Calibrate the running version, no upgrade step | 2026-11-14 | Owner already upgraded in `llm-env` |
| Loopback-only Laya URL | Any address from `[jev] laya_url` | D-01 | Pitfall 1 and Open Question 2 |

**Deprecated/outdated:** the capability `TABLE` cells cite "laya 0.4.2 server source" (`jev_review.py:858-862`) and `backends/laya.md` says the checkpoint window is 512/1024 tokens; Laya is now at least 0.4.27 and its README advertises 8,192-token long documents for `laya-multilingual`. The cells stay `unsupported` until a recorded live run (D-07); the new records only report "documented upstream, not verified here".

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The answer path writes a local pending note and the doc-flow fetch runs from `--probe`/`--check-updates` | Pattern 4 | If the owner wants the fetch right after the answer in the same process, the "fetcher fails on call" test must be reworded |
| A2 | Server version field names `version`/`package_version`/`laya_version` in `/health` | Code Examples | A future Laya may use another key; the fake-server tests define the contract meanwhile |
| A3 | `config set` default layer (project if `./.aikit/` exists, else user) | Code Examples | Wrong layer for a user who wants the answer global |
| A4 | Keep the `~/.mycreds` fallback with a recorded reason | Pitfall 4 | Owner may want it removed |
| A5 | Multiplexer detection env names `TMUX`, `STY`, `ZELLIJ`, `HERDR_ENV` | JEV-01 hint | A hint that never fires; harmless if the hint is shown whenever the key source is not `env` |
| A6 | TypeSafe "unknown primitive or option" is detected from an answer whose `type` is outside the known set | JEV-12 | Needs a fake-server case; real TypeSafe behaviour not observed |

## Open Questions

1. **How does the knob compose with callers that force `GSD_PATH_JEV=1`?**
   - What we know: `screen()` (`jev_review.py:1944`) and `_send` (`1420`) return `disabled` unless `GSD_PATH_JEV == "1"`; SKILL.md's documented commands hard-code `GSD_PATH_JEV=1`; `jev_ladder.child_env` (443), `judge_loop.ask_jev` (1746) and `precompact_core.client_env` (121) force it in the child env. D-01 puts the env above both config layers, so `[jev] enabled = false` would never take effect for any of them. SPEC R7 requires "with the knob off every skill behaves exactly as if jev were not installed".
   - What's unclear: whether `GSD_PATH_JEV=1` stays "this call may run" (callers' permission, `enabled=false` still wins) or becomes a user override above the config.
   - Recommendation: the client evaluates one gate: run only when `GSD_PATH_JEV == "1"` AND the layered `enabled` is not `false`; a user turns jev off for one session by unsetting the variable (today's behaviour) and permanently with `enabled = false`; absent `enabled` reports `needs_answer: enabled` and defaults to on. This keeps D-01's per-key order for the URL and satisfies R7 for every caller. Needs the owner's confirmation because it narrows D-01's "session override above both" for this one key. Test per consumer: with `enabled=false` the client prints `{"status": "disabled"}` before reading stdin; each caller's existing no-client outcome equals its outcome on `disabled` (to verify per caller in plan tests: `jev_ladder` `_STATUS_CODES` already includes `disabled`; the other callers' handling was not read this session).
2. **Consent for a non-loopback Laya.** The Laya row is `remote: False`, so a remote Laya needs no consent and no https. A project-layer `.aikit/config.toml` (checked into a cloned repo) could name an arbitrary host and send item context there. Recommendation: reuse the existing consent record keyed by host (`record_consent` already binds a grant to `_row_host`), required whenever the Laya host is not loopback; or accept `laya_url` non-loopback only from the user layer or env. Security gate: confirm with the owner.
3. **Fingerprint stability (Pitfall 2).** Recommendation: hash `info`, routes, and `loaded`/`revisions` only when `loaded` is non-empty; when empty, key on the openapi part and reuse the last recorded fingerprint whose openapi part matches. D-04 as written flips at every idle unload.
4. **`--check-updates` shape.** Flag on `--probe` or its own subcommand; D-08 only says it re-fetches the current keys. Recommendation: `jev_review.py --check-updates` as a top-level flag beside `--probe` (parser has `--probe` and `--skip-local` flags, `jev_review.py:1976-1979`); it prints a JSON report and exits 0.
5. **Where do hooks get the knob?** Hooks scrub env and swap `XDG_CONFIG_HOME`; only the project layer reaches them. Decide whether the knob must also gate the hooks (they run `--probe` through the client, which would report `disabled` under the Question 1 gate, so the hooks inherit it only for project-layer settings).
6. **Orchestrator-owned calibration step.** Laya is up now (`/health` 200). The run is 32 sequential single-item calls (about 12 ms each once loaded; the first call loads the checkpoint after an idle unload), so it is short, but it writes outside the repo (`tmp/`) and needs the real server: mark it an orchestrator step that degrades to "calibration not run: Laya unreachable at <host>" in `backends/laya.md` (R6 empty edge keeps citing the 2026-10-23 run).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 stdlib `tomllib` | reader/splicer | yes (config_io already imports it) | system python3 | n/a |
| Live Laya `127.0.0.1:8010` | calibration step only | yes on 2026-11-15 (GET /health 200) | package version not exposed | record "not run" with reason |
| Network to pypi.org, raw.githubusercontent.com, docs.typesafe.ai | fetch step (never tests) | yes (all 200) | n/a | failed fetch keeps old record, one notice |
| `node` | `.claude/gsd-core` tools | yes (roadmap query ran) | n/a | n/a |
| Judge referees via `node .planning/scripts/cross-ai.mjs` | loop 34 | probed by the orchestrator (not by me) | n/a | referee-three replaces, one usable accepted |

**Missing dependencies with no fallback:** none found.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib `unittest`, one subprocess per module, `tools/run_unittest_parallel.py --group unit` |
| Config file | none; `Makefile`/`.pre-commit-config.yaml` generated listings |
| Quick run command | `python3 -m unittest tests.test_jev_fast_decision tests.test_jev_config tests.test_jev_learn tests.test_jev_typesafe_models tests.test_jev_fast_decision_guard tests.test_jev_config_parity` |
| Full suite command | `make test` |

### Phase Requirements to Test Map

| Req | Behavior | Test type | Automated command | File exists? |
|-----|----------|-----------|-------------------|-------------|
| R1 | configured remote URL wins; env override; first-run `needs_answer` (answered via `config set`, declined `""`); missing key source + multiplexer hint; home-file last; no key printed | unit, scratch HOME, `JevStub` | `python3 -m unittest tests.test_jev_config tests.test_jev_fast_decision -k probe` | new: `tests/test_jev_config.py`; amend `tests/test_jev_fast_decision.py` (tests 413-520, 1114-1260) |
| R2 | server exposes version; config version; "not exposed"; changed route list; changed revision | unit with extended `JevStub` (`/openapi.json`, `health_body`) | `python3 -m unittest tests.test_jev_learn` | new |
| R3 | unknown key one fetch + record; known key none; failed fetch keeps old + notice; new feature reported, cell unchanged; refresh | unit, patched `fetch_public`/local stub | same | new |
| R4 | known id no fetch; new id one fetch + record; failed fetch; alias known; no id records nothing; pending note on answer, no network | unit | `python3 -m unittest tests.test_jev_typesafe_models` | new |
| R5 | calibration record fields; how-to linked from reference | doc-contract + manual orchestrator run | `python3 -m unittest tests.test_jev_doc_contract` | new; the live run is an orchestrator step |
| R6 | the limit sentence in SKILL.md and `backends/laya.md` with numbers and date | doc-contract | same | new |
| R7 | knob on, off, absent (asked once); project over user; per-consumer "as if not installed" | unit, scratch HOME | `python3 -m unittest tests.test_jev_config -k knob` | new; consumers: `jev_ladder`, `judge_loop`, `precompact_core`, `claude_decision_probe`, `ai-kit-gsd-spec-discuss`, `ai-kit-spec-goal-prompt`, `ai-kit-commit-fold` (existing module tests extended where they already fake a client: `tests/test_judge_loop.py`, `tests/test_precompact_core.py`, `tests/test_decision_probe.py`) |
| R8 | MCP sentence pinned; spike record exists (dated, method, cases, result) | doc-contract | same | new |
| R9 | guard: no Zen, no `opencode` as a backend, no delegation step; loop 34 result in 34-VERIFICATION.md | unit scan + loop | `python3 -m unittest tests.test_jev_fast_decision_guard` | new |

### Edge Coverage and Prohibitions to Tests

| SPEC row | Test location |
|----------|---------------|
| adjacency R1 (configured equals default counts as configured) | `test_jev_config.py` |
| empty R1 (no URL, nothing at default: asked once; decline records `""`, ladder starts at TypeSafe) | `test_jev_config.py` + probe test |
| encoding R1 (malformed URL = probe error naming the key) | `test_jev_config.py` |
| ordering R1 / R7 (env, project, user, default) | `test_jev_config.py` per-key table |
| concurrency R1 (two `config set` keep one answer) | `test_jev_config.py` (two writers via `publish`, last write wins, file parses) |
| adjacency/empty/ordering R2 | `test_jev_learn.py` (changed route/revision; unreachable endpoints; source order) |
| empty/encoding/concurrency R3 | `test_jev_learn.py` (no heading -> "no published notes"; UTF-8 replace; parallel write) |
| adjacency/empty R4 | `test_jev_typesafe_models.py` |
| empty/adjacency R6, R7, R9 | doc-contract and guard modules (cite the 32-case run when no new calibration; project value wins; host-folder `opencode` allowed) |
| backstops (ordering/concurrency R4, encoding R6, R8 rows, ordering/encoding R9) | none required |
| Prohibition: no key printed or sent on a capability fetch | fetch fake asserts no `Authorization` header; probe output grepped for a sentinel key |
| Prohibition: no cell to verified from upstream text | R3 new-feature case asserts `TABLE[...]["cells"]` unchanged |
| Prohibition: no upgrade/install/restart | guard scan: no `pip`, `uv`, `docker`, `systemctl`, `llm-env` command in scripts |
| Prohibition: no fetch on the answer path | screen/ladder run with `fetch_public` patched to raise |

### Sampling Rate
- **Per task commit:** the module the task touched plus `tests.test_jev_fast_decision`.
- **Per wave merge:** `make test-unit` and `make arch-test`.
- **Phase gate:** `make test` green, `make check-dogfood` ok, loop 34 recorded.

### Wave 0 Gaps
- [ ] `tests/test_jev_config.py`, `test_jev_config_parity.py`, `test_jev_learn.py`, `test_jev_typesafe_models.py`, `test_jev_fast_decision_guard.py`, `test_jev_doc_contract.py`
- [ ] `JevStub` options: serve `/openapi.json` and a configurable `/health` body (currently every GET returns `{"status":"ok"}`, `tests/test_jev_fast_decision.py:169-172`); build the fakes from the saved samples (`laya-health.json`, `laya-openapi.json`, `pypi-laya-0.4.27.shape.json`, trimmed typesafe pages)
- [ ] `python3 tools/gen_test_groups.py` and commit the regenerated `Makefile` (lines 11-12 area) and `.pre-commit-config.yaml` (lines 14-15 and the unit hook entry at line 71) in the same commit; `tests/test_gate_scope.py` enforces it
- [ ] `tests/test_config_dir_parity.py`: add a method for the new `cfg_config_base` copy in `jev_config.py` (the file's docstring lists every copy of the user-dir rule)

## Test Infrastructure Facts

- **Existing jev test modules:** `tests/test_jev_fast_decision.py` (3692 lines; `JevStub` at 132, `_ClientCase` at 313 clears env with HOME/XDG_* in a temp dir and `JEV_LAYA_URL` on a bound-never-listening port), `tests/test_jev_skill_install_e2e.py` (real `setup.py` under a temp HOME), `tests/test_secret_shapes_copy_install.py` (sibling copy), consumers: `test_judge_loop.py`, `test_precompact_core.py`, `test_decision_probe.py`, `test_curated_config_skills.py`, `test_check_dogfood.py`, `test_config_dir_parity.py`, `test_config_design_record.py`.
- **HTTP fakes:** in-process `http.server.ThreadingHTTPServer` on `127.0.0.1:0` (`JevStub.__enter__`, line 206). No test touches the network. `closed_port_url()` (line 82) gives a refused port.
- **Isolation:** `_ClientCase.setUp` patches `os.environ` with `clear=True`; the runner adds tripwire PATH stubs and a baseline env (`AI_KIT_REFUSE_REAL_HOME=1`).
- **Arch rules that bite new code:** rule 9 (no broad `except`), rule 8 (no `shell=True`), rule 12 (`if __name__ == "__main__"` last statement), `no_test_reads_planning` (line 2249), `no_test_calls_a_host_cli` (2270), cross-skill reach allowlist (2324; copy the reader, do not import `ai_kit_spec`), key-shape list rule (2376; no key-shaped literal in new scripts), `TestSeam` (1262) for `jev_review.py` names.
- **Staged mapper:** a staged `.md` selects only test modules whose code names it; make the new doc-contract module name `SKILL.md`, `reference.md` and `backends/laya.md` by path, and make the new tests name `jev_config.py`/`jev_learn.py` so they run at commit.
- **Runner registration:** a new unit module needs nothing in `run_unittest_parallel.py` (only e2e modules need `E2E_RECORDED_SECS`); `tests.test_jev_fast_decision` has a hook time entry (line 204, value 18), optional to refresh.
- **Files a new module forces to change:** `Makefile`, `.pre-commit-config.yaml` (via `gen_test_groups.py`).
- **Judge-adjacent docs that cite jev behaviour and must follow the knob change:** `skills/ai-kit-gsd-curated-config/SKILL.md:324` and `ai_kit_gsd_curated_config/recommend.py:1094-1095` ("jev-fast-decision is inert unless the agent session sets GSD_PATH_JEV=1 and ..."); editing curated-config's SKILL.md makes it materially changed (judge loop scope); a text-only change in `recommend.py` has golden/recommend tests (`tests/test_curated_config_recommend.py`).

## D-14 Judge Loop Template (from plan 33-12 and the 33 drivers)

- Tool interface (`tools/judge_loop.py`, `AI_KIT_REFUSE_REAL_HOME=1`): `prompt --probe --judge ID --out DIR`; `pool --loop 34 --judges referee-one referee-two referee-three --probe-dir DIR --records DIR` (no `--native`); `count --loop 34 --records DIR --skill jev-fast-decision`; `prompt --loop 34 --round N --judge ID --skill jev-fast-decision --out DIR`; `ingest --lane-dir DIR --records DIR [--replaces ID --reason TEXT]`; `report .planning/judge`; `check .planning/judge [--skills jev-fast-decision --require-current --gate]`.
- Drivers: copy `tmp/judge-33/{lanes,stage,publish,check,bar_table,loop_record_check,verdict_facts}.py` replacing `33` by `34` as `33-12-PLAN.md` Task 1 step 2 does (they are untracked scratch on this machine; recreate path is 33-12's copy_drivers step). Judged set: `skills.r1.txt` holds only `jev-fast-decision`; `judged.py` BASE is the last commit before Phase 34 code (HEAD is `12a8315`, planning only) and exits 1 when a changed skill is outside the judged and fact-only sets. Likely fact-only: any skill whose SKILL.md changes only by a name or path.
- Records: `.planning/judge/loops/34.json`, `.planning/judge/verdicts/34/jev-fast-decision/r<N>/<judge slug>.json`, optional `.planning/judge/refutations/34.json`, regenerated `REJUDGE.md` and `facts.json`, one commit per round touching only `.planning/judge/`.
- Prior base for the regression clause: `jev-fast-decision` loop 32.1, lowest valid percent 86.4, grade B, 0 critical, 0 high (`.planning/judge/REJUDGE.md:19`); `bar_with_base` computes the clause, never by hand. Max three rounds; judges referee-one and referee-two (`.planning/config.json` `review.reviewer_instances`), referee-three only as a `--replaces` substitute; never native; external retry ladder from the rails.
- Closing: `check .planning/judge` exit 0 and the `--skills ... --require-current --gate` form exit 0; `make check-dogfood` prints `check-dogfood: ok`.
- The "opencode judge lane" re-judge (JEV-03) is satisfied by this loop: the configured referees run through the `opencode` CLI (`opencode:router-env/my-referee-two` rows in `REJUDGE.md:42`).

## Consumers of `GSD_PATH_JEV` (JEV-07 reach)

| Consumer | Where | Behaviour today | Knob-off test |
|----------|-------|-----------------|---------------|
| jev client | `jev_review.py:1420, 1944` | `disabled` unless `== "1"` | client returns `{"status":"disabled"}` before stdin |
| `jev_ladder` (spec-discuss, curated-config callers) | `jev_ladder.py:443` | forces `"1"` in child env | ladder result for `disabled` equals its no-client result |
| `tools/judge_loop.py` `ask_jev` | line 1746 | forces `"1"` | `JevUnavailable`-equivalent path on `disabled` (to confirm in `tests/test_judge_loop.py`) |
| `precompact_core.client_env` / `claude_decision_probe` | `precompact_core.py:121`, hook | forces `"1"`, scrubs, swaps `XDG_CONFIG_HOME` | hook fails open as with no client |
| `ai-kit-commit-fold`, `ai-kit-spec-goal-prompt` | `fold_group.py`, `gp_host.py` (`JEV_ENTRY_REL`) | find the client by lookup only | not verified this session which status each treats as "no jev" |
| docs only | `docs/config/design.md:173`, `reference.md:78,104`, curated-config SKILL/recommend text | describe the env switch | update with the gate wording |

`.claude/gsd-core` local installs and `skills/` grep found no other reader of the variable.

## REQUIREMENTS / ROADMAP amendments (D-15)

Verified already amended (commit 12a8315): JEV-03 (`REQUIREMENTS.md:641-648`, "no upgrade step"), JEV-10 (`:674-683`, version-keyed fetch once), JEV-12 (`:688-692`), JEV-13 (`:693-695`); traceability rows for JEV-12/13 exist (`:1012-1013`); ROADMAP Phase 34 already carries criteria 2, 5, 8, 9 amended and the requirement list including JEV-12/13.
Remaining:
- ROADMAP criterion 6 says the text cites "the 32-case run that measured about half right when confident"; D-11 and SPEC R6 want the latest calibration's numbers (with the 32-case run only when no new run exists): amend.
- ROADMAP criterion 1 and JEV-01 do not yet say the Laya URL may be any address nor that env vars stay session overrides: add one clause each (JEV-01 text at `:634-639`).
- JEV-07 (`:659-661`) and ROADMAP criterion 4: add the `[jev] enabled` key and the chosen gate once Open Question 1 is answered.
- `docs/config/design.md`: `[jev]` table text (line 53: "Not read in" this phase), Environment-only list (173-183, "loopback only"), State and caches (231-248) for the new `jev/` records, plus the shifted `jev_review.py:NNN` cites.
- README/skill docs naming the loopback rule: `reference.md:110`, `backends/laya.md:10-12`.

## Security Domain

`security_enforcement` is true in `.planning/config.json`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (keys already handled; unchanged) | existing 0600 key-file rules, labels only |
| V4 Access Control | yes | consent bound to host; Open Question 2 for a remote Laya |
| V5 Input Validation | yes | `urllib.parse` for `laya_url`; capped `_read_body`; fetched text decoded UTF-8 with replacement and stored as text only; `tomllib` parse of config; `set_table` re-parse verification |
| V6 Cryptography | no | `hashlib.sha256` only for the fingerprint |
| V12 Files and resources | yes | atomic 0600 writes; refuse a project config that is a link out of `.aikit/` |
| V13 API | yes | public GET only, plain user agent, no `Authorization` header, short timeouts |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A cloned repo's `.aikit/config.toml` redirects item text to an attacker host (`laya_url`) | Information disclosure | consent for non-loopback Laya or user-layer-only (Open Question 2); the probe prints host, never a key |
| Upstream notes with prompt-injection text reach the agent via "read the record" | Tampering | store trimmed text, label "documented upstream, not verified here", SKILL.md tells the agent the text is data; never executed or rendered; cap the stored length |
| Oversized or trickling upstream response | Denial of service | `_MAX_RESPONSE_BYTES` cap, `_Deadline` watchdog, 5 s per fetch, skipped under a short hook deadline |
| A key in a fetch header or in the record | Information disclosure | fetch seam sends only `User-Agent`; tests assert no `Authorization` and grep outputs for a sentinel |
| Config symlink plants lanes in the user layer | Tampering | copy `cfg_confine_project_file`'s refusal for project-layer writes |

## Sources

### Primary (HIGH confidence)
- Read this session: `skills/jev-fast-decision/**` (SKILL.md, reference.md, backends/laya.md, scripts/jev_review.py, jev_ladder.py, eval_cases.py), `tests/test_jev_fast_decision.py`, `tests/test_config_dir_parity.py`, `tests/test_config_design_record.py`, `tests/test_arch.py` (rule names and cited ranges), `skills/ai-kit-spec-review/ai_kit_spec/config_io.py` and `toml_splice.py` and `cache.py`, `docs/config/design.md`, `.planning/REQUIREMENTS.md:632-697`, `.planning/judge/REJUDGE.md`, `33-12-PLAN.md`, `tools/gen_test_groups.py`, `tools/hooks/precompact_core.py`, `tools/judge_loop.py:1743-1758`.
- Live fetches 2026-11-15 saved under `tmp/auto/r325/research34/` (Laya `/health`, `/openapi.json`, PyPI JSON latest and `0.4.27`, GitHub README headings, docs.typesafe.ai `llms.txt`, `changelog.md`, `models.md`).
- Roadmap section via `gsd-tools.cjs query roadmap.get-phase 34 --pick section`.

### Secondary (MEDIUM confidence)
- Counts and closures computed by `tmp/auto/r325/research34/closure.py` and `count_words.py`.

### Tertiary (LOW confidence)
- Multiplexer env names, server version field names (A2, A5).

Not used: the `research-plan`/`research-store` seam and Context7 (no library documentation was needed; the work is repo-internal and public-page shapes). Code exploration used `rg` and `Read` (codebase-memory hooks reported the files indexed; no index query was needed beyond them). `.planning/` is not indexed, so it was read directly.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (stdlib; closures computed from the real files)
- Architecture: HIGH for seams and constraints, MEDIUM for the knob and fingerprint (Open Questions 1 and 3)
- Pitfalls: HIGH (each cites a file and line read this session)

**Research date:** 2026-11-15
**Valid until:** 2026-11-22 for the Laya/TypeSafe network shapes (fast-moving; a new Laya or Jev release changes the pages); 30 days for the code map unless Phases 32.5/33 follow-up commits touch `jev_review.py`.

## Resolved Open Questions (run coordinator, 2026-11-15)

Decided by the plan-convergence coordinator before planning. jev was asked (advisory); every item came back
`needs_fallback`, so each is the coordinator's own reasoning against the locked decisions, with jev's lean noted.
These bind the planner like CONTEXT decisions unless a later owner message says otherwise.

1. **Knob and `GSD_PATH_JEV` (Open Question 1): the environment variable becomes a true session override in both
   directions, as D-01 states.** The client resolves "run or not" in this order: an explicit `GSD_PATH_JEV` that the
   user set (`1` runs, any other set value such as `0` is off), then `[jev] enabled` (project over user), then the
   asked-once default (on, reported as `needs_answer: enabled` and "defaulted to on" in the probe). Because a
   forced `1` would defeat `enabled = false`, the internal callers stop forcing it: `jev_ladder.child_env`,
   `tools/judge_loop.py` (`ask_jev`), `tools/hooks/precompact_core.py` (`client_env`) and every other caller found
   in the consumer table forward the parent's `GSD_PATH_JEV` only when it is set, and SKILL.md / reference.md
   commands drop the hard-coded `GSD_PATH_JEV=1` prefix. With `enabled = false` and no user env value the client
   prints `{"status": "disabled"}` before reading stdin, so each caller takes its existing no-jev path. Tests: per
   consumer, knob off gives the caller's no-jev outcome; knob on and absent run; a user `GSD_PATH_JEV=0` turns off a
   knob-on config and `GSD_PATH_JEV=1` turns on a knob-off config for that session. Rejected: the AND gate (it
   narrows D-01's "session override above both"). jev lean: `forward_override` (both backends, low confidence).
2. **Non-loopback Laya (Open Question 2): any address from any layer, but a non-loopback Laya host counts as a
   remote backend.** Sending items to it requires the existing consent record bound to that host (the same
   `record_consent` / `_row_host` mechanism TypeSafe uses); without that grant the Laya row reports
   `needs_consent` with the host and the ladder falls through as for an unusable backend. Loopback stays
   consent-free. The probe names the host and never a key. This keeps SPEC's "consent rules for remote backends are
   unchanged" and closes the cloned-repo redirect threat. jev lean: `consent_by_host` (typesafe 0.51; laya leaned
   `user_layer_only`).
3. **Fingerprint and idle unload (Open Question 3): keep D-04's full fingerprint when checkpoints are loaded; when
   `/health` reports `loaded == []`, the probe reuses the last recorded fingerprint whose OpenAPI part matches and
   shows the server as idle.** With no matching record it reports the fingerprint as pending (idle) and does not
   fetch until a loaded fingerprint exists. `idle_seconds`, `idle_unload_seconds` and every other `/health` field
   stay out of the hash. A real revision change while loaded still yields a new fingerprint (R2 acceptance). jev
   lean: `reuse_last` (typesafe 0.66).
4. **`--check-updates` shape (Open Question 4):** a top-level flag of `jev_review.py` beside `--probe`; it re-fetches
   the current Laya key and the current TypeSafe model id, prints a JSON report and exits 0 (own reasoning; matches
   the parser's existing flag style).
5. **Hooks and the knob (Open Question 5):** hooks need no extra wiring; they run the client, which applies the
   question-1 order with the layers the hook can see (project layer only, since hooks swap `XDG_CONFIG_HOME`).
   reference.md states this limit. Hook probes never fetch under their short deadline (Pitfall 3).
6. **Calibration (Open Question 6):** the live calibration is a task marked for the orchestrator (live Laya at the
   configured address); when Laya is unreachable it records "calibration not run: Laya unreachable at <host>" with
   the date, and the R6 text keeps citing the 2026-10-23 32-case run (SPEC R6 empty edge).
