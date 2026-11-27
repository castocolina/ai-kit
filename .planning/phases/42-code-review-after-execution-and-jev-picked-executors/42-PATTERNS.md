# Phase 42: Code review after execution and jev-picked executors - Pattern Map

**Mapped:** 2026-11-26
**Scope:** 10 brief items. Line numbers are as of this commit; all paths are git-tracked and repo-relative.
**Not read in full (time box):** `42-SPEC.md` was not re-read; CONTEXT.md D-01..D-09 drove the mapping.

## File Classification

| New or changed file | Role | Data flow | Closest analog | Match |
|---|---|---|---|---|
| `skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py` or beside it (`pick_executor`) | service | request-response (jev) | `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:pick_session_model` (l.208-238) + `skill_classify.py:classify` | exact |
| `skills/ai-kit-spec-review/ai_kit_spec/jev_review.py` (2 classifiers) | service | request-response (jev) | same file: `finding_item` / `route_for` / `classify_disagreements` (l.182-239), `sizing_items` / `size_review` (l.305-359) | exact |
| code-review loop driver (new module) | service | event-driven rounds | `lane_ping.py:ping_lanes`, `reviewer_dispatch.py:dispatch_reviewer`, `lane_switch.py:fallback_outcome`, `review_log.py`, `review_reports.py` | role-match |
| `task_classification.py` public frontend tuple | utility | transform | `lens_delivery.py:UI_EXTENSIONS` (l.20) + pin test | exact |
| transport chooser (new module next to `runner_dispatch.py`) | service | CRUD (JSON record) | `lane_ping.py` seams, `herdr_source.py`, `cache.py` atomic write | role-match |
| `lane_settings.py` `interactive` setting | config | request-response | `_bool_setting`, `lane_escalation` (l.98-125) | exact |
| `ai_kit_spec_superpowers/cli.py` new subcommands | controller | request-response, JSON on stdout | `_cmd_executor_fallback` (l.642-660), `_add_fallback_parser`, `_COMMANDS` (l.817) | exact |
| `references/code-review.md` + SKILL.md pointer | doc | n/a | `references/fold-step.md`, `references/start-step.md` | exact |
| `.planning/phases/42-.../spike/` script and `42-SPIKE.md` | spike | file-I/O | `.planning/phases/38-runner-hardening-and-run-safety/38-SPIKE.md`, `.planning/spikes/002-claude-resume-while-alive/run.sh` | role-match |
| `skills/ai-kit-spec-execute-superpowers/evals/evals.json` | test data | n/a | same file; `tests/test_skill_evals_shape.py` | exact |

## Pattern Assignments

### 1. `pick_executor(candidates, ...)` (jev pick, no-jev default, sentinel, log line)

**Analog:** `dispatch_injection.py:pick_session_model` (l.208-238), the closest single-item jev pick; the
multi-item pattern is `skill_classify.py:classify` (l.112-131) and `jev_review.py:sizing_items`.

```python
entry = jev_names.find_jev(env)
if entry is None:
    return "", "jev absent"
item = {"id": "k0", "type": "choice", "instructions": PICK_QUESTION,
        "context": summary[: jev_names.CONTEXT_CHARS],
        "criteria": {pick: pick for pick in SESSION_PICKS}}
choice, top, reason = jev_names.ask_items(entry, [item], env, run, strict=True).get(
    "k0", (None, None, "no answer"))
confident = top is not None and top >= lane_order.STABLE_TOP
if reason == "" and choice in SESSION_PICKS and confident:
    return choice, f"jev {choice} ({top:.2f})"
return "", "jev low: session model kept"
```

Conventions:
- Sentinel for no answer is the tuple `(None, None, "no answer")` from `answers.get(id, ...)`; "confident" is
  `reason == "" and choice is not None and top >= STABLE_TOP` (`jev_review.py:_confident`, l.194). Reuse
  `_confident` semantics; `STABLE_TOP = 0.80` lives in `lane_order.py:14`.
- Criteria keys must be opaque tokens (`p1`, `p2`, ... as `sizing_items` l.314 does), mapped back to lane keys;
  never put keys, paths or model ids that look like secrets in the payload. `jev_review._label(value, allowed)`
  (l.301) is the "other" bucket pattern for free text.
- Insert point (D-04): after `resolve_execute_candidates` (`execute_selection.py:114`) and before
  `candidates_to_ladder` (l.153); both operate on lists of dicts with `key`, `context_limit`, `task_affinity`.
  `execute_selection.py` imports only `detection`; if jev is imported there, check `tests/test_arch.py`
  dependency rules first, else put `pick_executor` in a sibling module (as `jev_review.py` sits beside the review code).
- The result is a reorder of the same candidate list, never a change of harness/provider/model; unanswered
  keeps the input order (default).
- Log line "executor pick: <key> (jev, <confidence>)" or "default": stderr line like `_NO_NODE_LINE` style
  in `runner_dispatch.py` l.59, or a JSON event via `review_log.append_event`.
- Tests: copy `tests/test_jev_review.py` seam `answers_run(table, calls)` (l.64-73, fake `run` that records
  `{"payload": ..., "cwd": ...}` and answers `{"items": {id: {"decided_by": "fake", "fake": {"choice":..., "top":...}}}}`),
  and `jev_root(self)` for the entry; no-jev test = `find_jev` returns None (root with no jev entry). Also
  `tests/test_catalog_jev_names.py` for jev_names fakes. Extend `tests/test_ai_kit_spec_superpowers.py`
  only for the adapter side.

### 2. Two jev classifiers in `jev_review.py`

**Analog:** the same file. Structure to copy per classifier:
`QUESTION` constant + `CLASSES`/criteria dict (l.28-36) -> `*_item(index, NamedTuple) -> dict` (l.182-191) ->
route/apply function with a default when `not _confident` (l.199-213, l.324-342) -> `classify_*(items, env, run=subprocess.run, *, own_root=None)`
that returns `Classified("absent"|"asked"|"not needed", routes)` (l.216-239).

```python
def finding_item(index: int, finding: Finding) -> dict:
    reason = _summary_text(finding.reason, REASON_CHARS) or "none"
    title = _summary_text(finding.title, TITLE_CHARS)
    return {"id": f"d{index}", "type": "choice", "instructions": CLASSIFY_QUESTION,
            "context": (f"Severity: {finding.severity}. Finding: {title}. "
                        f"Fixer: {reason}. Source: {finding.source}."),
            "criteria": dict(CLASSES)}
```

Conventions:
- Severity guard: only `SKIPPABLE = ("MEDIUM", "LOW")` may be routed away from the owner (l.38, l.205);
  CRITICAL/HIGH always reach the owner (D-03/D-08 keep the exception). The new finding-fit classifier must
  reuse `SKIPPABLE`, not a new list.
- Defaults without jev: execute result -> the runner's outcome; review -> the reviewer's own severity; the
  run log says which decided (`Route.note`/`_entry` `"reason"` pattern l.242-247, JSON `jev` field `absent|asked|not needed`).
- Summaries only: build contexts from numbers, labels and `_summary_text` (strips quoted spans, paths,
  tokens via `_SPAN_RE`, `_UNSAFE_TOKEN_RE`, l.54-55). Add each new item to the payload-recording tests.
- Wiring: new command = `register_parsers(sub)` entry (l.403) + `COMMANDS` dict entry (l.438) + `cmd_*(args, deps)`
  using `deps.env_fn()` and `functools.partial(deps.run_fn, cwd=args.cwd)` (l.263-266); exit 2 plus a stderr
  line on `OSError`.
- Payload-recording seam that proves summaries only: `tests/test_jev_review.py:test_payload_holds_summaries_only`
  (l.338-385: `shape` regex via `re.fullmatch` on each item context, `banned` substrings, `assertNotIn(... json.dumps(payload))`)
  and `test_sizing_payload_holds_numbers_tokens_and_labels_only` (l.717). Copy both for each new classifier.

### 3. Capped code-review loop driver

**Analogs:** (a) `lane_ping.py:ping_lanes(run: PingRun, seams: PingSeams | None) -> PingOutcome` (l.198) with
`PingSeams` NamedTuple of fns (l.22-28: `probe_fn`, `now_fn`, `route_fn`, `clock_fn`, `read_fn`) and consts
`PING_TIMEOUT_S`, `PING_EXIT_NO_LANE` (l.17-19); (b) `reviewer_dispatch.py:ReviewerSeams`/`ReviewerDispatchSpec`/`dispatch_reviewer`
(l.35-95); (c) `lane_switch.py:fallback_outcome` (l.204), `flagged_lane` (l.183), `replacement_row` (l.234), `write_rows` (l.243);
(d) `review_log.py:lane_event`, `append_event` (atomic single `os.write` with `O_APPEND`, 0o600), `LANE_STATES` (l.9-30);
(e) `review_reports.py:report_status`, `parse_findings`, `merge_findings`, `render_merged_report` (severity headings
`CRITICAL|HIGH|MEDIUM|LOW|Cross-Document Consistency`, l.5-21).

```python
def lane_event(round_no, key, state, at, reason=None, cause=None, by=None) -> dict:
    return {"round": round_no, "key": key, "state": state, "reason": reason, "cause": cause,
            "by": by, "at": at}
```

Conventions:
- Round counter and cap are plain ints passed in (`--iteration`, `--cap` in `jev_review.register_parsers` l.415-416;
  `route_for` checks `iteration < cap`, l.208). There is no module-level cap constant today: add one named
  constant (cap 3 per D-01) beside the driver, as `lane_ping.PING_*` do.
- Pass rule: "no CRITICAL or HIGH open" = filter `parse_findings` severities (`review_reports.py:47`); `Status`
  line is never trusted alone (see `summary_bullets` docstring in `jev_review.py` l.125).
- Seams: every external effect is a NamedTuple field defaulting to the real fn (`ReviewerSeams`, `PingSeams`,
  `cli.py:CliDeps` l.95-119 with `clock_fn`, `run_fn`, `env_fn`); tests pass fakes (see `tests/test_lane_ping.py` l.90-127:
  `PingSeams(probe_fn=probe, now_fn=lambda: 1000.0)`, `clock_fn=lambda: state["t"]`).
- Flagged lane switch only (never an unflagged one): call `lane_switch.fallback_outcome`; partial report on a
  failed lane: `review_log.record_merge` (l.104) + `review_outcome`/`judged_line` (l.75-100).
- Review lane prompt/diff shape is a plan-time check on `reviewer_dispatch._reviewer_full_prompt` (l.65) and
  `ReviewerDispatchSpec.files`.
- Adapter module location: `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/` is a separate
  package; `tests/test_arch.py` has frozen import lists for it (l.1311 `_PHASE25_LADDER_PKGS`, l.1610-1661
  cli.py/dispatch_injection.py entries). Check them before adding an import across the two packages.

### 4. Lens loading for a diff; public frontend tuple

**Analogs:** `lens_delivery.py:lens_set(table_host, files, role="review_lens", ...)` (l.73-90, UI detection via
`str(f).lower().endswith(UI_EXTENSIONS)`, role `UI_ROLE = "ui_lens"`), `plan_lenses(lenses, base_bytes, window, ...)` (l.199),
`LENS_NOTES` (l.17: `built_in_no_file`, `over_window`, `path_rejected`, `not_present`, `host_cannot_load`).

Important finding (differs from the CONTEXT wording): the tuple is ALREADY duplicated on purpose.
`task_classification.py:15` has `_FRONTEND_EXTENSIONS = (".tsx", ".jsx", ".css", ".vue", ".scss")` and
`lens_delivery.py:19-20` says "no import either way: tests/test_arch.py frozen allowlist", pinned by
`tests/test_lens_delivery.py:TestPins.test_ui_extensions_match_the_adapter` (l.164-171), which AST-reads
the private name `_FRONTEND_EXTENSIONS` and compares it to `UI_EXTENSIONS`.

```python
values = [ast.literal_eval(node.value) for node in tree.body
          if isinstance(node, ast.Assign)
          and any(isinstance(t, ast.Name) and t.id == "_FRONTEND_EXTENSIONS" for t in node.targets)]
self.assertEqual(values, [UI_EXTENSIONS])
```

Conventions for making it public (D-02 "one source"): rename to `FRONTEND_EXTENSIONS` in `task_classification.py`
(used at l.26 inside `classify_task`), then update the pin test's `target.id` string in the same commit; `rg "_FRONTEND_EXTENSIONS"`
shows only these importers (tests/test_lens_delivery.py:169, task_classification.py:15,26, the lens_delivery.py:19 comment).
The adapter may import its own tuple; it may not import `lens_delivery` unless the arch allowlist is extended (with a non-vacuity counterpart).

### 5. Transport chooser seam and per-plan record

**Analogs:** NamedTuple decision + seams: `runner_dispatch.py:RunnerSpec` (l.69), `RunnerSeams` (l.298), named constants
(l.33-52, e.g. `RUNNER_OUTER_MARGIN_S = 30`, `PREVIEW_TIMEOUT_S = 30`); atomic JSON write:
`skills/ai-kit-spec-review/ai_kit_spec/cache.py:cache_write_json` and `cache_read_json` (atomic binary write, mkstemp in the target dir
at l.28-32), already used by `cli.py:CliDeps.cache_write_json_fn`; herdr: `herdr_source.py:herdr_available(env, which_fn)` (l.25),
`_herdr(binary, args, env, run_fn)` (l.55, timeout 60, `(OSError, TimeoutExpired)` -> None), `read_interactive_names(...)` (l.100),
constant `LABEL = "interactive view, unverified"` (l.19). Also `lane_switch.write_rows` for a small JSON file writer.

```python
def _herdr(binary, args, env, run_fn):
    try:
        return run_fn([binary, *args], capture_output=True, text=True, env=env,
                      timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
```

Conventions:
- Reuse `cache_write_json` rather than a new mkstemp block (AGENTS.md: reuse `_atomic_write_json`-class helpers).
- "Verified label" gate: a transport is offered only when its label is verified for the recorded host version
  (`herdr_source.LABEL` is the unverified marker pattern; the spike record is the source).
- Herdr availability is `HERDR_ENV=1` plus a binary on PATH, never a call (`cross-ai.mjs` l.4645); `--sweep` at `cross-ai.mjs:49`/`4333`.
- Tests: `tests/herdr_fakes.py:write_herdr_fake(bin_dir, answers, log_path)` (exact-argv table, JSON-lines call log) and
  `herdr_calls(log_path)`; fake clock by `clock_fn=lambda: state["t"]` as in `tests/test_lane_ping.py:126`. Note there is no
  `tests/test_herdr_source.py`; herdr-related tests are `tests/test_catalog_herdr.py` and `tests/test_config_herdr_identity.py`.
- Renewal count: one named constant (e.g. `TRANSPORT_RENEW_ROUNDS = N`), tested at the boundary like `PING_*`.

### 6. `interactive` lane setting

**Analog reader** (`lane_settings.py`):

```python
LANE_FLAG_KEYS = ("escalate_runtime", "escalate_model", "usage_limited")   # l.11
MODEL_BOUND = ("effort", ..., "usage_limited", ..., "escalate_runtime", "escalate_model", ...)  # l.15
def _bool_setting(entry, name):                                              # l.98
    value = entry.get(name, False)
    if not isinstance(value, bool):
        raise LaneSettingError(f"{entry.get('key', '<unknown>')}: '{name}' must be a boolean")
    return value
def lane_escalation(entry) -> Escalation:                                    # l.121
    return Escalation(_bool_setting(entry, "escalate_runtime"), _bool_setting(entry, "escalate_model"))
```

Conventions:
- Add `"interactive"` to `LANE_FLAG_KEYS` (so `normalise_lane_settings` l.30-42 drops `false`: "written only when true")
  and to `MODEL_BOUND` (dropped on a pair change unless restated), and add one reader `lane_interactive(entry) -> bool`
  using `_bool_setting`.
- Pin tests in `tests/test_lane_settings.py` (l.231-270): `FLAGS` is derived from `LANE_FLAG_KEYS` automatically, so no flag string literal may
  appear in any scanned module outside `lane_settings.py` (`_flag_literal_lines`), and the new reader name must be added to `READERS`
  (l.239) and to `ALLOWED_READERS` for the module that calls it (e.g. the chooser file name). Update `_SETTING_FLAGS`/runner tables only if the
  runner must see the flag (`runner_dispatch.py:212`; golden `tests/fixtures/runner_describe_golden.json`, `tests/test_runner_flags.py`).
- Writer: spec-config has no Python writer; it is prose the host follows: `skills/ai-kit-spec-config/references/wizard-flow.md`,
  `references/config-file.md`, `SKILL.md`, pinned by `tests/test_spec_config_flow_text.py` and `tests/test_spec_config_lane_json.py`.
  Mirror how `escalate_runtime`/`usage_limited` appear there (write the key only when true). spec-config SKILL.md change triggers the skill-judge loop.

### 7. New shim subcommands in `ai_kit_spec_superpowers/cli.py`

**Analog:** `_cmd_executor_fallback` (l.642-660) with `_load_fallback_inputs` (l.624) and `_add_fallback_parser` (l.676-692); `_COMMANDS` dict (l.817-828).

```python
def _cmd_executor_fallback(args: argparse.Namespace, deps: CliDeps) -> int:
    loaded = _load_fallback_inputs(args, deps)
    if loaded is None:
        return 2
    ...
    if new:
        deps.stdout.write(json.dumps({"switched": True, "key": new, "exclude": sorted(held - {new})}))
        return 0
    deps.stdout.write(json.dumps({"switched": False, "reason": why}))
    return 1
```

Conventions:
- Shape: handler `_cmd_x(args, deps) -> int`; JSON via `deps.stdout.write(json.dumps(...))`; exit 0 ok, 1 a
  defined negative result, 2 bad input/ConfigError (`main()` l.840 turns `ConfigError` into exit 2 with a stderr line; `_read_json_input` for
  file reads with a stderr message). `escalation-gate` uses exit 3 for an empty key (l.807). Add each new fn as a `*_fn` field to `CliDeps` (l.95)
  so tests inject fakes; add the parser in `_build_parser` (l.695) and the handler in `_COMMANDS`.
- Config load: `cfg_resolve_quiet(args.cwd, deps.env_fn())`. Roster: `_execute_roster(config)` (l.638).
- Tests: `tests/test_ai_kit_spec_superpowers.py` `TestCliSubcommandHandlers` (l.1169), `TestCliResumeExclusions` (l.2423), `TestCliWriteResumableState` (l.2445);
  assert `CliDeps` fields with `main([...], stdout=io.StringIO(), ...)` overrides.
- Lite-file writer: use `cache_write_json` for JSON or a temp+`os.replace` text write; the plan-writer rail is `.aikit/brief/SKILL.md` (fold tool stays untouched).

### 8. `references/code-review.md` and SKILL.md pointer

**Analog:** `skills/ai-kit-spec-execute-superpowers/references/fold-step.md` (65 lines): title `# <step name> (Step N)`, then
`MANDATORY: read this file in full before running its block; do NOT load it at any other point.`, a short purpose paragraph, `## The block`
with one fenced `bash` block that reads `$SCALARS`, validates placeholders (`for n in SKILL_DIR PLAN_FILE ... ; do case "${!n}" in ""|"<"*)`) and
resolves the sibling skill path through candidate dirs. SKILL.md pointer style: `**MANDATORY: read [`references/x.md`](references/x.md) in full ...**`
(SKILL.md l.101-103, 135). Step order test: `tests/test_ai_kit_spec_superpowers.py:test_step_five_sits_between_step_four_and_close_the_session_wake`
(l.~3090) uses `text.index("## Step 4:") < text.index("## Step 5: ...")`; a new step between the last task review and the fold step needs this
test and the step numbering updated together (renumbering fold to Step 6 touches `TestFoldStep` text, `tests/test_lane_failure_text.py:46,165,245` "check-fold-step", and
`tests/test_spec_chain_text.py:232`).
Doc-contract tests that read a reference: `TestFoldStep` (l.3002), `TestStartStep` (l.3104: `re.search(r"```bash\n(.*?)```")` extraction), l.3085 (normalized
whitespace `assertIn`). Copy that: pin the cap 3, "no CRITICAL or HIGH open", and the no-jev path as `assertIn` on whitespace-normalized text.
SKILL.md edit means skill-judge loop (AGENTS.md); SKILL.md stays under its current size discipline (293 lines now).

### 9. Spike script and dated spike record

**Analogs (tracked):**
- Record: `.planning/phases/38-runner-hardening-and-run-safety/38-SPIKE.md` (title `# Phase 38 spike record (D-23)`, one-line machine rows, `## Host output timing` with
  `- claude -> not probed (no ledger consent line), unverified`, `## Not probed by design`, `## Real config audit`, `## Cleanup` listing leftovers/removed);
  also `.planning/phases/37-shared-runner-options-and-session-ids/37-SPIKE.md`.
- Script: `.planning/spikes/002-claude-resume-while-alive/run.sh` (scratch dir `S=$(mktemp -d)`, `env -u CLAUDECODE ...` clean env, session id read from `--output-format json`,
  `--resume "$SID"` headless resume) and `.planning/spikes/CONVENTIONS.md` + `.planning/spikes/MANIFEST.md`.
- Phase-folder script precedent: `.planning/milestones/v1.3-phases/21.2-.../spike/s1_laya.py`.
Conventions: scratch HOME and dir only, no real config read (AGENTS.md), runs only after the owner's consent line (ledger), one row per installed host (version, date,
session id source, headless resume result, label), cleanup section. Scripts go under the phase's `spike/`; scratch output under `tmp/`. Note `tests/` must not read `.planning/`.

### 10. `evals/evals.json` (four new evals)

**Analog:** `skills/ai-kit-spec-execute-superpowers/evals/evals.json`; shape enforced by `tests/test_skill_evals_shape.py` (`EVAL_KEYS = {id, prompt, expected_output, files, assertions}`;
`ID_RE ^(casual|precise|edge)-[a-z0-9-]+$`; at least 5 evals, at least one of each prefix; each eval 2+ assertions of 20+ chars; no machine paths matching
`/var/home|/home/[A-Za-z]|/Users/|~/`; `files` is a list of skill-relative paths such as `evals/files/plan-two-features.md`).

```json
{ "id": "casual-run-superpowers-plan", "prompt": "...", "expected_output": "...",
  "files": ["evals/files/plan-two-features.md"], "assertions": ["...20+ chars...", "..."] }
```

Files rule: every listed file must exist under `evals/files/` (tracked; existing examples `evals/files/<case>/project/aikit/config.toml`, `fold-refused-report.txt`).
Add per-case fixtures there (a roster config for the executor pick, a plan for the lite block, a config with an interactive lane for the transport choice). Also keep
`evals/trigger-queries.json` unchanged unless the description changes.

## Shared Patterns

### jev advisory contract
**Source:** `jev_review.py` module docstring + `jev_names.py:find_jev`/`ask_items(strict=True)`. Summaries only; no jev, an error or a low answer keeps today's path;
CRITICAL/HIGH always reach the owner; each path has a tested no-jev branch.

### Seams as NamedTuples with real defaults
**Source:** `PingSeams` (`lane_ping.py:22`), `ReviewerSeams` (`reviewer_dispatch.py:35`), `RunnerSeams` (`runner_dispatch.py:298`), `CliDeps` (`cli.py:95`). New modules follow it;
tests replace one field with a lambda or recorder.

### Subcommand registration
**Source:** `jev_review.py:register_parsers(sub)` + `COMMANDS` (l.403, 438); `lane_ping.py` l.280-294; `lane_switch.py` l.312-323. Handlers are `cmd_*(args, deps) -> int`;
errors to stderr with the command name prefix and exit 2. Find where `COMMANDS` dicts are merged (`rg "register_parsers"` in `skills/ai-kit-spec-review/`) to wire a new module.

### Banner blocks
The AGENTS.md rule on banner-delimited blocks and role-prefixed functions applies to the status-line family only (`tests/test_arch.py`); `ai_kit_spec` modules here use plain module
docstrings and `# ──` section comments (`review_reports.py:3`). No banner needed.

### Test registration and gates
- A new `tests/test_*.py` joins the `unit` group automatically. Exceptions only through the commented frozensets in `tools/run_unittest_parallel.py`: `ARCH_MODULES` (l.92),
  `UNIT_UV_MODULES` (l.96), `INTEGRATION_MODULES` (l.102), `E2E_MODULES`, `SHARED_MACHINERY` (l.229); `EXPLICIT_GROUPS` (l.233).
- `python3 tools/gen_test_groups.py` exists: run it after adding or moving a module; `tests/test_gate_scope.py` fails on a stale Makefile/`.pre-commit-config.yaml` listing.
- Tripwire: tests may not spawn a host CLI by absolute path (arch rule); use `tests/host_fakes.py` and `tests/herdr_fakes.py`. No test reads `.planning/` (archive fixtures under `tests/fixtures/archived/`).
- Runtime code stays stdlib-only; atomic config writes via `cache.py` helpers; never a hardcoded absolute path.
- Any SKILL.md change (adapter, spec-config) goes through the skill-judge loop.

## No Analog Found

| File | Role | Data flow | Reason |
|---|---|---|---|
| code-review loop driver as one unit | service | event-driven rounds | No code-review loop exists; spec review's rounds are driven by the SKILL.md prose with Python helpers per step, so the driver is composed from `lane_ping`, `reviewer_dispatch`, `lane_switch`, `review_log`, `review_reports` |
| a module-level round cap constant | config | n/a | the iteration cap is passed as `--cap` today; define one named constant |
| `tests/test_herdr_source.py` | test | n/a | does not exist; herdr tests are `test_catalog_herdr.py`, `test_config_herdr_identity.py`, helper `herdr_fakes.py` |
| spec-config writer for a lane flag | writer | n/a | prose in `wizard-flow.md`/`config-file.md`, pinned by text tests; no Python writer |

## Metadata

**Analog search scope:** `skills/ai-kit-spec-review/ai_kit_spec/`, `skills/ai-kit-spec-execute-superpowers/`, `skills/ai-kit-spec-config/`, `tests/`, `tools/run_unittest_parallel.py`, `tools/gen_test_groups.py`, `.planning/spikes`, phase 37/38 spike records.
**Method:** `rg` and direct reads (codebase-memory-mcp not used this run). **Not verified:** exact `E2E_MODULES` contents; where the `register_parsers` modules are merged; `tests/test_arch.py` allowlist semantics for the new cross-package imports (check before planning).
