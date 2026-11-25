# Phase 40: Resilient review sized by jev - Pattern Map

**Mapped:** 2026-11-25
**Files analyzed:** 22 (9 new, 13 modified)
**Analogs found:** 20 / 22
**Source:** CONTEXT.md and SPEC.md (RESEARCH.md was not available). All paths are repo-relative and git-tracked
(`git ls-files` checked on the analogs below; no gitignored mirror paths). Modules live under
`skills/ai-kit-spec-review/ai_kit_spec/`, written `ai_kit_spec/` below.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `ai_kit_spec/error_classifier.py` (M: extend `REASONS`) | config/constant | transform | itself, lines 16-26 | exact |
| `ai_kit_spec/lane_ping.py` (N, name at plan time; D-02) | service | batch, concurrent | `quota.py:refresh_quota_cache` + `ProbeSeams` | role-match |
| `ai_kit_spec/lane_switch.py` (N; D-04) | utility | request-response (pure) | `lane_settings.py:lane_fallback` / `escalation_target` | exact |
| `ai_kit_spec/blocked_status.py` or inside the switch (N; D-05) | utility | file-I/O via runner subprocess | `quota.py:_run_probe` + `reviewer_dispatch._dispatch_runtime` (seam style) | partial |
| `ai_kit_spec/review_jev.py` (N; D-06: `classify_disagreements`, `size_review`) | service | request-response (jev) | `skill_classify.py` + `jev_names.ask_items` | exact |
| `ai_kit_spec/review_signals.py` (N; D-07 `security/data/irreversible`) | utility | transform | `lane_data_use.py` / `skill_table.py` (text scan, no I/O seams) | role-match |
| fold-step check script (N; D-08), in `skills/ai-kit-spec-review/` | utility/script | transform, CLI | `skills/ai-kit-commit-fold/scripts/fold_group.py` (script style) | partial |
| `ai_kit_spec/review_reports.py` (M: partial status, judged-lanes line) | utility | transform | itself `render_merged_report`, lines 104-140 | exact |
| `ai_kit_spec/quota.py`, `routing.py`, `reviewer_dispatch.py` (M: ping seam, `--pool`) | service | request-response | themselves | exact |
| `ai_kit_spec/runner_dispatch.py` (M: carry `pool` in `RunnerSpec`/argv) | service | request-response | `RunnerSpec` lines 69-89 | exact |
| `ai_kit_spec/cli.py`, `commands.py` (M: register subcommands) | controller | request-response | `skill_classify.register_parsers` + `COMMANDS` | exact |
| `references/lane-failure.md` (N; D-09) | doc | n/a | `references/loop-diagram.md`, `apply-findings.md` | role-match |
| `SKILL.md`, `references/apply-findings.md`, `references/loop-diagram.md`, `evals/evals.json` (M) | doc/eval | n/a | themselves | exact |
| `skills/ai-kit-spec-review-fixer/SKILL.md` (line 48), `skills/ai-kit-spec-review-checklist/` (M) | doc | n/a | themselves | exact |
| New tests: `tests/test_lane_ping.py`, `test_lane_switch.py`, `test_review_jev.py`, `test_review_signals.py`, `test_fold_step_check.py` (N) | test | n/a | `tests/test_ai_kit_spec.py` (`TestProbeReviewerQuota`, 3271+) | exact |
| Extended tests: `tests/test_ai_kit_spec.py:3485`, `tests/test_ai_kit_spec_runtimes_table.py:775`, `tests/test_quota_policy_text.py`, `test_cross_ai_docs_text.py`, `test_role_orders.py` (M) | test | n/a | themselves | exact |

## Pattern Assignments

### `error_classifier.py` (extend `REASONS`, D-01)

Closed tuple, comment per member; append review-level reasons in the same form (lines 16-26):
```python
REASONS = (
    "quota",               # usage or rate limit, already retried by the runner on a router lane
    ...
    "git_timeout",         # runner git work-tree check timed out, not the CLI
)
```
Constraints: `STATUS_TO_REASON` (line 30) values must stay None or a `REASONS` member; new review-level names
(`replaced`, `never_resolved`, `no_lane_left`) get no status key. Locks to extend: `tests/test_ai_kit_spec.py:3485`
(`set(REASONS)`), `tests/test_ai_kit_spec_runtimes_table.py:775` (`known = set(REASONS)`);
`tests/test_quota_policy_text.py:28` reads `error_classifier.py` as text (`CLASSIFIER`; `wake_lines` must stay empty), so no
"wake" wording in the new comments. Other readers: `quota.py:entry_reason`, superpowers `dispatch_injection.classify_dispatch_failure`.

### Ping module (D-02) - analog `quota.py`

Seam type to reuse (lines 208-214) and the probe (271-287); the stale rule is `refresh_quota_cache` (299-306):
```python
class ProbeSeams(NamedTuple):
    runner_fn: Callable[..., RunnerResult] = run_runner
    custom_fn: Callable[..., RunnerResult] = run_custom_command
    env_fn: Callable[[], dict] = lambda: dict(os.environ)
    print_fn: Callable[[str], None] | None = None
...
        current = updated.get(key)
        if current is not None and now - current.get("checked_at", 0) < ttl_seconds:
            continue
        entry = _reviewer_by_key(reviewers, key)
        updated[key] = probe_reviewer_quota(to_resolved(entry), seams=seams)
```
Copy: take `seams: ProbeSeams | None` and a `clock` callable (the file calls `time.time()` directly, so the new
function needs its own `now_fn=time.time` seam for the fake clock); fan out with
`concurrent.futures.ThreadPoolExecutor` (stdlib only); return `{key: entry}` using the probe's own dict shape
(`available/checked_at/reason/detail/answered`, line 220-223). A native entry is never probed (line 278). Skip lanes
marked fresh from the previous round. A probe `ValueError` already maps to reason `configuration` (284-286).
Note: `_probe_call` hardcodes `review_spec(..., 30, ...)` (line 253); the per-ping timeout default must become a
parameter there or be passed through a new seam (default stays 30).

### Flagged switch (D-04) - analog `lane_settings.py`

Pure, list-in/key-out reader style (lines 103-107, 129-154):
```python
def lane_usage_limit(entry: dict) -> UsageLimit:
    note = entry.get("usage_limit_note", "")
    return UsageLimit(_bool_setting(entry, "usage_limited"), ...)

def _flagged(lane: dict) -> bool:
    return lane.get("usage_limited") is True

def lane_fallback(role_lanes: list, key: str) -> str | None:
    lanes = _keyed(role_lanes)
    base = next((lane for lane in lanes if lane["key"] == key), None)
    return _fallback_from(base, lanes) if base is not None else None
```
New function shape: `replacement_for(result_reason, lane_entry, role_lanes, order) -> str | None`; returns a key only
when reason == `"quota"` and `lane_usage_limit(entry).limited`; every other input returns None. `lane_usage_limit` raises
`LaneSettingError` on a non-bool flag: catch it and return None (a missing or bad record never blocks). Import with
`from ai_kit_spec import lane_settings` (module style used in `skill_classify.py:15`). `lane_fallback` already works on
the whole lane list; for review use `selectable_lanes("review", lanes, order)` (lines 139-147) to honor the owner's
order. Result keys from dispatch: `reviewer_dispatch._result_dict` (61-65) gives `reason`, `status`, `returncode`.
Gap: `RunnerSpec` (`runner_dispatch.py:69-89`) has no pool field and no `--pool` argv anywhere in Python
(`rg pool` finds nothing there); D-04's `--pool <provider>:free` needs a new optional field plus argv emission in the
runner argv builder, with a test in `tests/test_runner_flags.py` style. Runner flags exist in
`references/cross-ai.mjs:6336` (`SUPERVISION_FLAGS` includes `--blocked-status`, `--pool`) and 6722 (value must match
`<provider>:free`; `--blocked-status` cannot combine with other modes, line 6782).

### Blocked-until read (D-05)

No Python analog: it is a new thin subprocess wrapper. Copy only the seam habit from `ReviewerSeams`
(`reviewer_dispatch.py:35-40`: injected `*_fn` callables with real defaults) and the "no node, bad record reads as none"
rule from CONTEXT. Parse output `blocked_until=<time|-> failures=<n>`; any OSError, nonzero exit or unparsable line
returns None. PROVISIONAL per D-05.

### jev adapter (D-06) - analog `skill_classify.py` over `jev_names.ask_items`

Core call pattern (`skill_classify.py:121-130`):
```python
entry = jev_names.find_jev(env, own_root)
if entry is None:
    out["jev"] = "absent"
    return out
items = [role_item(index, name, path, roots) for index, (name, path, _) in enumerate(pending)]
answers = jev_names.ask_items(entry, items, env, functools.partial(run, cwd=cwd), strict=True)
```
Item shape (`jev_names.py:96-103`): `{"id", "type": "choice", "instructions", "context", "criteria": {name: hint}}`.
Answer shape (`_column_answer`, 121-137): `(choice, top, reason)`; `reason == ""` is a usable answer, `"low"`,
`"no answer"`, `"timeout"`, `"old"`, `"failed"` mean take today's path. Proposal filter (`skill_classify.py:103-109`):
`if reason == "" and choice in PROPOSABLE`. Use `strict=True`. Context is summaries only: bound the string
(`_clean`, `CONTEXT_CHARS = 600`, `NAME_CHARS = 80`) and run `secret_shapes.redact`. For `classify_disagreements` the
classes are `owner_decision`, `mechanical`, `reviewer_wrong`; force CRITICAL/HIGH to `owner_decision` in code before
trusting the answer. `size_review` returns a sentinel (None) on no answer; the caller keeps today's default.
Import `jev_names` (do not copy its lookup tables again: `jev_names.py` is itself in `tests/test_arch.py` `LOOKUP_COPIES`,
line 1697, and the compare test fails for an uncompared lookup copy). Registration: module exposes `register_parsers(sub)`
and `COMMANDS = {...}` with `cmd_*` handlers taking `(args, deps)` (`skill_classify.py:134,197-220`); wire in `cli.py` at
line 512 (`skill_classify.register_parsers(sub)`) and line 1462 (`**skill_classify.COMMANDS`); add the import near
`cli.py:19-30`. `deps.env_fn()` and `deps.run_fn` are the seams (`cli.py` ~186 shows `score_judge_fn`-style injected judges).
A module that imports `cli` is forbidden: "this module never imports cli".

### Deterministic signals (D-07)

One function, `signals(plan_files: list[str], plan_text: str) -> dict[str, bool]` with keys `security`, `data`,
`irreversible`; plain `re`, no I/O, stdlib. Tests per trigger and with none, plus held-out fixtures under
`tests/fixtures/` (not `tests/fixtures/archived/`, and no reads of `.planning/`). Any true signal forces two lanes before
jev is asked (jev only sizes up from there or confirms; a no-jev run uses the same deterministic floor).

### Fold-step check script (D-08)

Place in `skills/ai-kit-spec-review/` (no `scripts/` folder exists there today; the module dir `ai_kit_spec/` plus the
entry `ai-kit-spec.py` is the convention, so a function plus subcommand is the closest fit; a standalone script would
follow `skills/ai-kit-commit-fold/scripts/fold_group.py`). Detection target: a superpowers plan (glob
`docs/superpowers/plans/*.md`, see `references/frameworks/superpowers.md:14` in the checklist skill) lacking the fold step
that `skills/ai-kit-spec-execute-superpowers/references/fold-step.md` documents (commands:
`fold.py checkpoint --plan "$PLAN_FILE" --base "$FOLD_BASE" --final`, then `fold.py ready --plan "$PLAN_FILE"`; SKILL.md:290).
Output merges via `review_reports.merge_findings`; finding line shape in the checklist skill
(`ai-kit-spec-review-checklist/SKILL.md:273`):
`- **<title>** — Location: <section/lines>. Required: <verifiable outcome>. Why: <reason>.`
Fixture pair: one plan with the step, one without (paired fixtures in `tests/fixtures/`).

### `review_reports.py` (partial status, judged-lanes line)

`render_merged_report(findings, doc_paths, any_source_issues=False)` (104-140) builds `lines = ["## Review: ...",
"### Document Type", "cross-ai merged"]` then a status line. Add optional keyword parameters with defaults
(`judged`, `other_lanes` = `[(key, reason)]`) so existing callers and tests stay byte-identical; emit `Approved (partial)`
when any lane is replaced, failed or unresolved, and `not reviewed` with no judged lane. `report_status`
(line 31) must still parse the new status (add a test for "Approved (partial)" and "not reviewed").

### Tests (new modules)

Analog: `tests/test_ai_kit_spec.py:3271-3311`. Fake lane via seam, no real call:
```python
def fake_runner(spec, prompt, seams):
    return _probe_result(None, "ok")   # helper at ~3260: RunnerResult(0|1, "", {"status":..}, reason, False, [...], tail)
result = probe_reviewer_quota(self._codex(), seams=ProbeSeams(runner_fn=fake_runner))
self.assertEqual(seen["spec"].timeout_s, 30)
```
Also `tests/test_ai_kit_spec_runner_dispatch.py:811` (`seams=quota.ProbeSeams(runner_fn=fake)`),
`tests/test_ai_kit_spec_routing.py:121`, `tests/test_role_orders.py:290-329` (probe and usage-limited lane).
For jev adapters pass `run=` a fake subprocess (see how `skill_classify.classify(env, cwd, run=...)` takes it). Use
`unittest.TestCase`; a new `tests/test_*.py` joins the `unit` group automatically; the module that needs uv/PTY/Textual
goes to an exception set in `tools/run_unittest_parallel.py` (not needed here); `tests/test_gate_scope.py` enforces it.
Use model names only as `fake-*`, `placeholder-model-N` or `router-env/...` (see below).

## Shared Patterns

### Stdlib-only runtime
`ai_kit_spec/*` is runtime: no third-party imports (AGENTS.md). `concurrent.futures`, `re`, `json`, `subprocess` only.

### Imports
Package style `from ai_kit_spec import a, b` (`skill_classify.py:15`); `cli.py` imports each module in one sorted block
(lines 19-30); modules never import `cli`.

### Seams, advisory jev, missing record reads as none
Every external call is an injected `*_fn`/`run` parameter with a real default (`ProbeSeams`, `ReviewerSeams`,
`ask_items(..., run=subprocess.run)`); jev answers are advisory and a no answer takes today's path.

### Arch rules a new module must satisfy (`tests/test_arch.py`)
- `LOOKUP_COPIES` (1688-1698): never copy `SKILLS_ROOTS`/`JEV_ENTRY_REL`; call `jev_names.find_jev`. Adding another copy
  would need an entry and a compare test.
- `test_host_importers` (2250), `test_rule1_host_prefix_literals_stay_in_host` (2225), `test_rule10_retired_literals_only_in_allowlist`
  (2326): no host-family literals or retired literals in the new modules.
- `test_no_test_calls_a_host_cli` (2405): tests must not name a host CLI as the spawned program; fake via seams.
- Tripwire: the harness puts host-CLI stubs first on PATH; a test that spawns the runner or node for `--blocked-status`
  must inject a fake, never call real `node`, outside `e2e` modules.
- No test reads `.planning/` (arch rule, archived data under `tests/fixtures/archived/`).
- `tests/test_arch_hardcoded_models.py`: position-based guard over `skills/ tools/ tests/ docs/ README.md AGENTS.md`
  with `tests/fixtures/no_hardcoded_models_baseline.json` (baseline only shrinks). Allowed names (line 48):
  `router-env/...`, `placeholder-model-N`, `placeholder-alias-N`, `fake-...`; a marker `model-example:` (line 39) exempts a
  doc example. New docs (`lane-failure.md`, evals) and tests must use these forms, never real provider/model names.
- Pre-commit/pylint limits for new code: `max-args=5`, `max-locals=15`, `max-branches=12`, `max-returns=6`; ruff line length
  100; pyright `basic`; vulture min_confidence 80 flags unused new functions, so every new function needs a caller or a test
  reference that vulture sees (`tests/` is scanned).

### Skills and docs
Any changed `SKILL.md` (`ai-kit-spec-review`, `-fixer`, `-checklist`) goes through the `skill-judge` loop (AGENTS.md, max 3
rounds, `fixes.md` for <=3 findings). `make check-dogfood` requires phases after 32 that name a SKILL.md to cite JDG-04.
`tests/test_cross_ai_docs_text.py` and `tests/test_quota_policy_text.py` pin text in the quota policy and classifier; run
them after editing `skills/ai-kit-cross-ai/references/subprocess-quota-policy.md` or SKILL.md hard rules (lines 398, 419, 540).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| blocked-until reader wrapper (D-05) | utility | subprocess | Python never reads the record today; only `cross-ai.mjs` does. Use the seam style above plus the runner doc |
| `--pool` argv emission | service | request-response | `RunnerSpec` has no pool field; extend `runner_dispatch.py` (no Python precedent) |
| concurrent fan-out (D-02) | service | concurrent | No `concurrent.futures` use in `ai_kit_spec/` was found in this scan; use the stdlib directly, with a fake-clock seam |

## Metadata

**Analog search scope:** `skills/ai-kit-spec-review/ai_kit_spec/`, `skills/ai-kit-spec-execute-superpowers/`,
`skills/ai-kit-spec-review-checklist/`, `tests/` (test_arch, test_ai_kit_spec, test_quota_policy_text, hardcoded-model guard)
**Tools:** codebase-memory-mcp symbol checks plus rg and direct reads (graph marks the skill tree as partly not indexed)
**Pattern extraction date:** 2026-11-25
