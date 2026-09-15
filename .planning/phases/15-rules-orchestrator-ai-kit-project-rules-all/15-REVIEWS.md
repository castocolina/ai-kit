---
phase: 15
reviewers: [claude]
reviewed_at: 2026-09-14T21:28:00Z
plans_reviewed: [15-01-PLAN.md, 15-02-PLAN.md]
models:
  claude: "unknown"
model_sources:
  claude: "unknown"
cycles:
  - cycle: 1
    reviewers: [claude]
    reviewed_at: 2026-09-15T01:13:36Z
  - cycle: 2
    reviewers: [claude]
    reviewed_at: 2026-09-14T21:28:00Z
    note: >-
      Default reviewer (opencode/xai-grok-4.6) remains billing-blocked (403 spending-limit);
      codex fallback remains OAuth-expired. Both confirmed genuine external-account failures,
      not repo issues. Claude CLI lane used as the working lane, per explicit instruction.
---

# Cross-AI Plan Review — Phase 15

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
(none)
<!-- gsd:plan-revision-conflicts:end -->

# Cycle 1 (2026-09-15T01:13:36Z)

## Claude Review

# Cross-AI Plan Review: Phase 15 (Rules Orchestrator, `ai-kit-project-rules-all`)

Verification performed by reading live source: `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/cli.py`, its entry script, `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py` + `SKILL.md`, `skills/_shared/ai_kit_rules_common/{remediation.py,criticality.py}`, a sibling `__init__.py`'s `sys.path` guard, `Makefile:45-47`, `.pre-commit-config.yaml:1-58`, `pyproject.toml:85-97`, `README.md:38-46`, `.planning/REQUIREMENTS.md:82`, `.planning/ROADMAP.md:426-444`, and `.planning/phases/14-.../14-SKILL-JUDGE.md` in full (the precedent both plans build on).

## 15-01

### Summary
This plan builds the orchestrator's functional core (subprocess fan-out, D-02/D-05 failure isolation, and a pure cross-domain criticality merge) without shipping `SKILL.md`, deliberately keeping it uninstalled. Every CLI-contract claim it relies on checks out against the live source: `cli.py:remediate()` really is `build_remediation(check(repo_root))` in every sibling (verified in `cicd/cli.py:23-26` and `agents/cli.py:88-91`), `build_remediation()` really does return a domain-agnostic `{"remediate": [...], "blocked": [...]}` shape keyed only by `kind`/`id`/`criticality` (verified in `remediation.py:76-122`), and the criticality vocabulary is exactly `1/2/3/4` ascending-most-severe (verified in `criticality.py:23-26`). D-04's resolution of the `check` vs `remediate` subcommand ambiguity — always subprocess-invoke `remediate`, and define the orchestrator's own `remediate` as identical to `check` — is architecturally sound and consistent with `constraints.md`'s "Cross-skill remediation merging ownership" protocol, which explicitly reserves per-domain classification to `remediation.py`.

### Strengths
- D-04's reasoning is directly supported by source: since `remediate()` in every sibling literally calls that sibling's own `check()` first (`cicd/cli.py:23-26`, `agents/cli.py:88-91`), SC1's "invokes all 6 checkers' `check`" is genuinely true one layer down without the orchestrator re-deriving `auto_apply`/near-miss branching — exactly what the Don't-Hand-Roll guidance in `15-RESEARCH.md` argues for.
- The `dispatch_all()`/`aggregate()` split is real, not just a diagram: `aggregate()` is specified to import only `DOMAIN_ORDER` from `dispatch.py` and never `subprocess`, which is what actually makes SC4's "stub all 6, no real checker logic" test achievable.
- `DOMAIN_ORDER` is named as the single source of truth for both dispatch iteration and the tie-break order in `aggregate()`'s stable sort — correctly prevents the non-deterministic-ordering pitfall `15-RESEARCH.md` calls out.
- Task 1's tracer dogfoods against all 6 real, already-shipped sibling checkers in this repo (confirmed: `skills/ai-kit-project-rules-{agents,makefile,precommit,arch,docker,cicd}/` all exist with the exact directory-name-matches-domain convention the precondition assumes) — an unusually strong integration proof for a first pass rather than a mocked one.
- D-05's failure schema (`status: "failed"`, distinct from any real payload's `remediate`/`blocked` keys) is a clean, cheap way to distinguish "couldn't check" from "checked, clean" — directly satisfies the confidence-labeling Core Value in `PROJECT.md`.
- Security posture matches the family's own unbroken pattern: `subprocess.run([...], shell=False)` with `repo_root` as a list element, never string-interpolated — verified as the pattern every sibling already uses (no `shell=True` anywhere in the family).

### Concerns
- **MEDIUM — precondition gap: only smoke-tests `check`, but `dispatch_all()` always calls `remediate`.** Task 1's `<precondition>` runs `python3 skills/.../<skill>.py check .` for all 6 siblings, but D-04 locks that the orchestrator's real dispatch path calls `remediate`, not `check`. A sibling could pass this precondition (its `check()` runs cleanly) while still failing under `remediate()` — e.g. a `build_remediation()` field-access bug specific to that domain's finding shape (`finding["criticality"]`/`finding["summary"]` `KeyError`s if a checker ever omits one) would not be caught before this plan starts executing against it. The precondition should invoke `remediate`, not `check`, since that's the actual code path this plan builds on.
- **LOW — `DOMAIN_TIMEOUT_SECONDS` monkeypatch fragility in Task 2's Test 3.** The plan tells the executor to monkeypatch `DOMAIN_TIMEOUT_SECONDS` down to ~1s for the timeout test, but doesn't warn that if `run_domain`'s implementation captures the timeout as a function-default-parameter value (`def run_domain(domain, repo_root, timeout=DOMAIN_TIMEOUT_SECONDS)`) rather than reading the module global live at call time, the patch silently no-ops and the test either takes the full 30s or never actually exercises the timeout branch. TDD discipline should surface this (the test would need the full budget to pass, which is itself a signal), but the plan could save a debugging cycle by saying explicitly "read the timeout from the module namespace at call time, not as a bound default."
- **LOW — Python `$CLAUDE_PLUGIN_ROOT` candidate needs explicit empty-string handling.** The bash pattern this task generalizes (`"${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/<name>}"`, verified in `agents/SKILL.md:17`) only includes that candidate when the var is set and non-empty. The plan's Python description ("`$CLAUDE_PLUGIN_ROOT` joined with `skills/<name>`") doesn't spell out that an unset/empty `CLAUDE_PLUGIN_ROOT` must skip the candidate entirely rather than join to produce a bogus `/skills/<name>` path — a minor but real translation gap from bash to Python.

### Suggestions
- Change Task 1's `<precondition>` loop to invoke `remediate` (with a discarded repo_root or `.`) instead of `check`, matching the actual dispatch contract this plan builds against.
- Add one sentence to Task 2's `<read_first>` or `<action>` instructing that any timeout value used inside `run_domain` must be read from the module's live global at call time (never bound as a function-default), so the monkeypatch test is guaranteed effective rather than accidentally inert.

### Risk Assessment: LOW
The architecture is sound, heavily grounded in verified source, and the one functional gap (precondition testing the wrong subcommand) is cheap to fix and unlikely to hide a real defect given the shared `build_remediation()` code path is already exercised by every sibling's own test suite.

## 15-02

### Summary
This plan turns the working-but-uninstalled code from 15-01 into an installable skill: `SKILL.md` with the Step A/B/C hand-off cross-reference, registration across `README.md`/`.pre-commit-config.yaml`/`pyproject.toml`, a `/skill-judge` gate with reproducible evidence, and a `/naming-analyzer` confirmation with a fail-closed rename guard. The evidence-file shape it specifies (`JUDGED_PATH`/`JUDGED_COMMIT`/`BASELINE`/`SCORE`/`CRITICAL`/`IMPORTANT`/`FIX_ITERATIONS_USED`/`LIMIT_COUNT_FINAL`/`CONCISION_TENSION`) is not invented — it matches, field-for-field, the precedent already shipped in `14-SKILL-JUDGE.md` (verified by direct read), including the no-baseline verification method (`git log --all --follow` + `git log --all --diff-filter=A`) and the "code review must re-run skill-judge if `SKILL.md` changes again" pointer. The Step A/B/C hand-off text this plan cross-references is verified accurate against `agents/SKILL.md`'s actual "Wrap mechanism" section.

### Strengths
- The `NAMING_VERDICT: confirmed | rename-proposed` fail-closed mechanism (Task 3) is a genuinely enforced control, not aspirational prose: the `<verify>` command hard-asserts `verdict == 'confirmed'`, so an autonomous executor cannot silently apply or silently swallow a rename proposal — this directly closes the exact loophole T-15-13 names.
- The append-only `15-CONTEXT.md` correction requirement is mechanically checked via `git diff --unified=0 <sha>^..<sha>` asserting zero removed lines — stronger than a prose instruction, and matches this project's own `AGENTS.md` Workflow rule about amending stale docs rather than rewriting them.
- Registration claims were independently verified against the live files: `.pre-commit-config.yaml` really does have exactly the 3 hook surfaces described (`ruff` `files:` at line 21, `py-compile` `files:` at line 50, `unittest` `entry:` at line 55), and `pyproject.toml` really does have both `[tool.vulture] paths` and `[tool.pyright] include` lists ending in the same 9-skill sequence.
- Task 1's own action text correctly attributes `[tool.pyright]``include` vs `[tool.vulture]``paths` — the plan is internally correct even though the upstream `15-RESEARCH.md` Pitfall 4 swapped which line number belongs to which tool (see Concerns). The "Registration reference (re-read live, do not assume line numbers)" framing insulates the plan from that upstream inaccuracy.
- D-10's "no baseline, absolute bar" reasoning for a brand-new `SKILL.md` matches the exact precedent 14-SKILL-JUDGE.md already established and the `AGENTS.md`/`PROJECT.md` skill-quality-gate constraint.

### Concerns
- **HIGH — Task 1's floor (`>=8` limits) and Task 2's ceiling (`LIMIT_COUNT_FINAL==8`) directly contradict each other, and the contradiction is exactly the failure mode every prior sibling phase's real history demonstrates will occur.** Task 1's `SKILL-SHAPE-OK` verify only requires `len(nums)>=8` (a floor). Task 2's `JUDGE-GATE-OK` verify requires `lc==8` exactly (`assert lc==8, ('the shipped limits section no longer carries 8 statements', lc)`) — an exact-match ceiling. D-07 mandates that the document describe the *shipped* code honestly, discovered live rather than composed in advance ("the code wins over the SUMMARY"). But every prior sibling in this exact family organically discovered *more* real limits than initially planned during that same honest-description process: Phase 13's docker skill went from "seven required" to eight with a conditional ninth; Phase 14's cicd skill shipped **eleven** limits against a presumably similar initial plan, explicitly called out in its own evidence file as "three more than the Phase 13 sibling's eight" (`14-SKILL-JUDGE.md:84-86`). If Task 1's honest-documentation process for this orchestrator surfaces a genuine 9th limit (plausible — e.g. "each of the 6 subprocess calls spawns a fresh `python3` interpreter, so wall-clock cost includes 6x interpreter startup, not just rule-check time" is a real, undocumented-so-far characteristic of this specific skill), Task 2's gate has exactly two ways to resolve: drop the real 9th limit to hit exactly 8 (a live violation of D-11's own "no fix may soften a limit" rule, dressed up as a count constraint instead of a content edit), or fail the gate outright. Neither is the outcome the plan actually wants. This should be `>=8` in both places, with `LIMIT_COUNT_FINAL` checked as a floor (`>= the count Task 1 shipped`) rather than hardcoded to the literal integer 8.
- **LOW/MEDIUM — `15-RESEARCH.md`'s Pitfall 4 mislabels the `pyproject.toml` line-to-tool mapping (upstream inaccuracy, not a plan defect).** Research claims line 88 belongs to `[tool.pyright]`'s `paths` and line 94 to `[tool.vulture]`'s `paths`/`include`. Live file shows the reverse: line 86 is `[tool.vulture]`, line 88 is its `paths` list; line 92 is `[tool.pyright]`, line 94 is its `include` list. This doesn't propagate into a plan bug because Task 1's actual `<action>` text names the tools correctly and the plan explicitly instructs re-reading live rather than trusting line numbers — but it's worth noting so a future amendment to `15-RESEARCH.md` isn't skipped as "already correct."
- **LOW — Task 1's mechanical `SKILL-SHAPE-OK` verify script is fragile, deeply-nested lambda Python embedded directly as the enforced gate command.** Functionally plausible but harder to debug than a plain function if the section-extraction regex misbehaves on real heading text (e.g. a `## Hand-off mechanism (SC3):` heading with a colon, or nested `###` subheadings inside `## Limits`) — not a correctness blocker, but a maintainability/debuggability risk for whoever has to fix it if it misfires.

### Suggestions
- Change Task 2's `JUDGE-GATE-OK` assertion from `lc==8` to `lc>=8` (or, more precisely, `lc>=<the count Task 1's SKILL-SHAPE-OK actually observed>`), so a limit honestly discovered during Task 1's writing process is never structurally punished by Task 2's gate. This is a one-line fix that removes the plan's only real internal contradiction.
- Optionally amend `15-RESEARCH.md`'s Pitfall 4 to correct the pyright/vulture line-number swap, for the benefit of whichever future phase next re-reads that research doc as precedent (this phase's own plan is already correct and doesn't need the fix to execute safely).

### Risk Assessment: MEDIUM
The plan is otherwise exceptionally well-grounded (registration claims, evidence-file shape, and hand-off cross-reference all independently verified against live source and precedent), but the `LIMIT_COUNT_FINAL==8` vs `>=8` contradiction is a concrete, likely-to-trigger gate failure given the family's own documented history of limit counts growing during honest documentation — it should be fixed before execution rather than discovered mid-phase.

## Cross-Plan Assessment

Both plans are unusually well-sourced: nearly every load-bearing claim (CLI contracts, `remediation.py`'s exact branching, the Step A/B/C hand-off text, registration file line contents, the skill-judge evidence-file shape) traces to a real, verified read rather than an assumption, and the two genuine ambiguities left by `15-RESEARCH.md` (`check` vs `remediate` invocation, D-02's failure schema) are resolved with explicit, well-reasoned decisions (D-04/D-05) rather than left implicit. The dependency ordering (15-02 depends on 15-01; SKILL.md deliberately deferred to keep the code uninstalled and gated-but-not-installed during 15-01) is correct and matches the family's own established two-wave pattern.

The two real findings — the precondition testing `check` instead of `remediate` in 15-01, and the `>=8` vs `==8` contradiction between 15-01→15-02's own gates in 15-02 — are both small, mechanical fixes, not design-level problems. Neither invalidates the overall approach.

**Overall Risk: MEDIUM**, driven entirely by the 15-02 `LIMIT_COUNT_FINAL` gate contradiction, which is concrete and likely to trigger given this exact family's demonstrated history of limit counts growing organically during honest documentation (Phase 13: 7→8; Phase 14: →11). Fixing that one assertion (`==8` → `>=8`) would bring both plans to LOW risk.

---

### Consensus Summary (Cycle 1)

Single-reviewer pass (claude lane only — this project's default reviewer, opencode/xai-grok-4.6, is billing-blocked at 403 spending-limit, and the codex fallback has an expired OAuth token with a 401 refresh_token_reused error, both confirmed genuine external-account failures rather than repo issues). No cross-reviewer agreement to synthesize; findings below are the claude lane's own.

#### Agreed Strengths
N/A — single reviewer. Notable strengths (see full review above): D-04's `remediate()`-calls-`check()` contract is verified against live source for all 6 siblings; the `dispatch_all()`/`aggregate()` split genuinely supports stub-based testing (SC4); `DOMAIN_ORDER` is the single source of truth for ordering; Task 1 of 15-01 dogfoods against all 6 real sibling checkers; the `NAMING_VERDICT` fail-closed mechanism in 15-02 is a hard-asserted control, not aspirational prose.

#### Agreed Concerns
N/A — single reviewer. Notable concerns (see full review above):
- **HIGH (15-02):** `SKILL-SHAPE-OK`'s floor (`>=8` limits) and `JUDGE-GATE-OK`'s ceiling (`LIMIT_COUNT_FINAL==8`) contradict each other; the family's own history (Phase 13: 7→8, Phase 14: →11) shows limit counts routinely grow past the initial estimate during honest documentation, so this gate is likely to trigger a false failure or force an illegitimate limit-softening to pass. Fix: change `lc==8` to `lc>=8` (or `>=` the count Task 1 actually shipped).
- **MEDIUM (15-01):** Task 1's `<precondition>` smoke-tests all 6 siblings' `check` subcommand, but D-04 locks the orchestrator's real dispatch path to `remediate`. A sibling could pass the precondition while still failing under `remediate()`. Fix: precondition should invoke `remediate`, not `check`.
- **LOW/MEDIUM (15-02):** `15-RESEARCH.md` Pitfall 4 swaps the `pyproject.toml` line-to-tool mapping (pyright vs vulture); does not propagate into a plan bug since Task 1's own text is correct, but worth a research-doc amendment.
- **LOW (15-01):** `DOMAIN_TIMEOUT_SECONDS` monkeypatch could silently no-op if `run_domain` binds the timeout as a function-default parameter instead of reading the module global live.
- **LOW (15-01):** Python translation of the `$CLAUDE_PLUGIN_ROOT` candidate path needs explicit empty-string handling to avoid a bogus `/skills/<name>` path.
- **LOW (15-02):** `SKILL-SHAPE-OK`'s deeply-nested lambda verify script is fragile/hard to debug if section-extraction regex misbehaves on real heading text.

#### Divergent Views
N/A — single reviewer.

**Disposition:** All six Cycle 1 findings (1 HIGH, 1 LOW/MEDIUM, 4 LOW across both plans) were addressed via a replan committed at `a8b9e9b`. See the Review Dispositions Ledger at the bottom of `15-01-PLAN.md` and `15-02-PLAN.md` for exactly what changed. Cycle 2 below independently re-verifies each disposition against live source.

# Cycle 2 (2026-09-14T21:28:00Z)

**Reviewer:** claude CLI lane (explicit `--claude`). This project's default reviewer (opencode/xai-grok-4.6) remains billing-blocked (403 spending-limit) and the codex fallback remains OAuth-expired — both confirmed genuine external-account failures, not repo issues, so the claude CLI lane is the working lane for this cycle.

**Scope:** Independent re-verification, against live source, of whether the 6 Cycle 1 dispositions genuinely hold — not just formally present in the plan text — plus a fresh independent review pass of both plans.

## Claude Review

# Cross-AI Plan Review — Cycle 2: Phase 15 Rules Orchestrator (ai-kit-project-rules-all)

## Summary

Both plans are well-grounded in live source and the Cycle 1 fixes genuinely hold — I independently re-verified every claim in the Review Dispositions Ledger against the actual repository (not just the plan text) and found all three findings against 15-01 and all three findings against 15-02 correctly and completely fixed, with no regressions introduced by the fixes themselves. The architecture (subprocess fan-out → pure aggregate() → SKILL.md-level hand-off cross-reference) is sound, matches every sibling's real CLI contract byte-for-byte, and the D-04/D-05/D-06 decisions this replan made are internally consistent. I found one new LOW-severity gap during independent review (a monkeypatch-fragility class matching the one Cycle 1 already caught for `DOMAIN_TIMEOUT_SECONDS`, this time applying to how `cli.py` should reference `dispatch.dispatch_all`) — it is very likely already handled correctly by the plan's own phrasing, but is not spelled out as an explicit rule the way the timeout lesson was.

## 15-01

### Strengths
- Every CLI-contract claim checks out verbatim against live source. `cicd/cli.py:23-26` and `agents/cli.py:88-91` both confirm `remediate(repo_root)` is exactly `build_remediation(check(repo_root))` — D-04's reasoning ("check is still literally invoked, one layer down") is not a plausible-sounding rationalization, it's mechanically true.
- `remediation.py:76-122` confirms `build_remediation()` really does the field access the plan assumes: `finding["criticality"]`, `finding["summary"]` (required, `KeyError`s if absent), `finding.get("target", finding.get("category"))` for identifier, `finding.get("issue")`. The plan's precondition fix (see disposition verification below) is the right target for catching a shape mismatch here.
- `criticality.py:23-26` confirms the exact `1/2/3/4` ascending vocabulary the plan's `DOMAIN_ORDER`/tie-break design relies on.
- The `dispatch_all()`/`aggregate()` separation is real and enforceable: `aggregate.py` is specified to import only `DOMAIN_ORDER` from `.dispatch`, never `subprocess` — this is what makes SC4's "stub all 6, no real checker logic" test structurally achievable rather than just described as achievable.
- `agents/SKILL.md:17`'s literal bash `${CLAUDE_PLUGIN_ROOT:+...}` pattern is correctly generalized; the Python translation directive (skip the candidate entirely on empty/unset, never join an empty string) matches bash's own semantics precisely.

### Concerns
- **LOW — a new, Cycle-1-adjacent monkeypatch-fragility risk in `cli.py`'s reference to `dispatch.dispatch_all`.** Task 3's Test 5 (`TestCLI`) requires `dispatch.dispatch_all` to be monkeypatchable so `cli.check()`/`cli.remediate()` can be tested against a fixed stub without real subprocess calls. This only works if `cli.py` calls `dispatch.dispatch_all(repo_root)` via a qualified module reference (`from . import dispatch` then `dispatch.dispatch_all(...)`) rather than importing the name directly (`from .dispatch import dispatch_all`) — the latter binds a local name once at import time and a later `dispatch.dispatch_all = stub` patch would silently not affect `cli.py`'s own call site. This is the exact same class of bug Cycle 1's L40 finding caught for `DOMAIN_TIMEOUT_SECONDS`. The plan's own wording ("`check(repo_root)` returns `aggregate.aggregate(dispatch.dispatch_all(repo_root))`") already uses qualified-attribute phrasing, which is the safe form — but unlike the timeout case, the plan never states this as an explicit rule the way it now does for `DOMAIN_TIMEOUT_SECONDS`. Low risk because TDD discipline (Test 5 written first, confirmed to fail for the right reason) would likely surface a name-import mistake immediately, but a one-sentence explicit rule (mirroring the timeout fix) would close the gap the same way Cycle 1 closed it for the timeout.
- **LOW — worst-case runtime not reconciled with the per-task commit verify budget.** D-06 documents ~180s worst case (6 × 30s timeout). Task 1's `<verify>` command uses `timeout=240` for the subprocess call, which comfortably covers that — no actual defect, just noting the numbers are consistent (240 > 180 with margin), confirming this was accounted for correctly.

### Suggestions
- Add one sentence to Task 1's `<action>` for `cli.py` (mirroring the `DOMAIN_TIMEOUT_SECONDS` rule already added for `dispatch.py`): "`dispatch.dispatch_all` and `aggregate.aggregate` MUST be called via qualified module-attribute access, never imported by name into `cli.py`'s own namespace, so Task 3's Test 5 monkeypatch is guaranteed effective."

### Risk Assessment: LOW
The architecture is sound and heavily grounded in verified source. All three Cycle 1 findings are genuinely fixed with no regressions. The one new finding is low-severity, almost certainly already covered by the plan's existing phrasing, and cheap to make airtight with one added sentence.

## 15-02

### Strengths
- The `NAMING_VERDICT: confirmed | rename-proposed` fail-closed mechanism (Task 3) is a real enforced control — the `<verify>` command's `assert verdict=='confirmed'` genuinely makes a `rename-proposed` outcome fail the task, not just document a preference.
- The append-only `15-CONTEXT.md` correction check (`git diff --unified=0 <sha>^..<sha>` asserting zero removed lines) is mechanically sound: it scopes to the commit's *own* diff, so it correctly wouldn't be fooled by pre-existing history, and I confirmed live that `15-CONTEXT.md`'s stale header/Phase-Boundary text is still fully present and unmodified in the current tree (Phase 15 hasn't executed yet), which is exactly the starting state this check assumes.
- Registration claims are independently verified accurate against live files: `.pre-commit-config.yaml` ruff `files:` at line 21, py-compile `files:` at line 50, unittest `entry:` at line 55 — all confirmed exact via direct read. `pyproject.toml` `[tool.vulture]`/`paths` at lines 86/88 and `[tool.pyright]`/`include` at lines 93/94 — also confirmed exact. `README.md`'s skill table has the `cicd` row at line 44 exactly where Task 1(b) says to insert after.
- The evidence-file schema (`JUDGED_PATH`/`JUDGED_COMMIT`/`BASELINE`/`SCORE`/`CRITICAL`/`IMPORTANT`/`FIX_ITERATIONS_USED`/`LIMIT_COUNT_FINAL`/`CONCISION_TENSION`) and the Step A/B/C hand-off text it cross-references both check out against `agents/SKILL.md`'s real "Wrap mechanism" section, read in full — Step A (near-miss confirmation owned by the wrapping skill), Step B (assemble one ordered list), Step C (invoke `/agent-md-refactor` exactly once) are quoted accurately.

### Concerns
- None rising above LOW remain. The one HIGH finding from Cycle 1 (the floor/ceiling contradiction) is fully resolved — see disposition verification below.
- **LOW — residual note, not a defect.** The corrected `15-RESEARCH.md` Pitfall 4 text is now itself accurate (independently re-verified: line 86 `[tool.vulture]`, line 88 its `paths`; line 93 `[tool.pyright]`, line 94 its `include`), so this is fully closed with no remaining gap.

### Suggestions
- None beyond what Cycle 1 already prompted and what was applied. The plan is ready to execute as written.

### Risk Assessment: LOW (downgraded from Cycle 1's MEDIUM)
The one concrete, likely-to-trigger contradiction (`LIMIT_COUNT_FINAL==8` vs the family's own documented history of limit counts growing during honest documentation) is genuinely fixed at the root — reconciled to a floor in both the verify script and the fix-loop rules, with the rationale (citing Phase 13→14's real 7→8→11 growth) now explicit in D-08. Nothing else found rises above LOW.

## Cycle 1 Disposition Verification

| Finding | Plan | Disposition Claim | Verdict | Evidence |
|---|---|---|---|---|
| L39 — precondition smoke-tests `check`, but `dispatch_all()` calls `remediate` | 15-01 | Precondition loop changed to invoke `remediate` | **VERIFIED** | Live diff `d93c902..a8b9e9b` on `15-01-PLAN.md` shows the precondition's `for d in agents makefile precommit arch docker cicd; do python3 ... $d.py check . ...` changed to `... remediate . ...`, with the HALT rationale extended to explain why `check`-only would miss a `build_remediation()` field-access bug. Cross-checked against `remediation.py:76-122`'s real field access (`finding["criticality"]`, `finding["summary"]` required) — the gap being closed is real, not hypothetical. |
| L40 — `DOMAIN_TIMEOUT_SECONDS` monkeypatch could silently no-op if bound as a function-default | 15-01 | Explicit rule added: must be read from module namespace live, never bound as default | **VERIFIED** | Diff confirms new text in Task 1's `<action>` ("`DOMAIN_TIMEOUT_SECONDS` MUST be referenced by its module-level name directly inside `run_domain`'s body... NEVER bound as a function-default parameter") plus matching reinforcement in Task 2's `<read_first>` and Test 3's `<behavior>` bullet with an explicit tell for a wrong binding. This is correct Python semantics: a module-global read at call time (`dispatch.DOMAIN_TIMEOUT_SECONDS`) picks up a test's `dispatch.DOMAIN_TIMEOUT_SECONDS = 1` patch; a bound default parameter would not. |
| L41 — Python translation of `${CLAUDE_PLUGIN_ROOT:+...}` needs explicit empty-string skip | 15-01 | Explicit rule added: skip the candidate on unset/empty via `os.environ.get` truthiness | **VERIFIED** | Diff confirms the added sentence citing `agents/SKILL.md:17` by name. I independently re-read `agents/SKILL.md:17` and confirmed the bash pattern (`"${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-project-rules-agents}"`) is exactly what the fix claims to mirror. |
| L63 — Task 1's `>=8` floor contradicts Task 2's `lc==8` ceiling | 15-02 | Task 2's check changed to `lc>=8`; D-08 rewritten as a floor with Phase 13/14 precedent cited | **VERIFIED** | Diff confirms the assertion literally changed from `assert lc==8, (...)` to `assert lc>=8, (...)` in the `JUDGE-GATE-OK` command, D-08 rewritten with "AT LEAST 8... MINIMUM... never a target count," a new third fix-loop rule in Task 2 forbidding trimming an honest 9th+ limit, and matching `<done>`/`<fails_when>` text updates in both tasks. No trace of the old `==8`/ceiling language remains anywhere in either task. This closes a genuine, high-likelihood gate-failure mode given this family's own real history (Phase 14's cicd skill shipped 11 limits, cited accurately by the reviewer). |
| L64 — `15-RESEARCH.md` Pitfall 4 swaps the pyright/vulture line mapping | 15-02 (research doc) | Corrected to line 88=`[tool.vulture]` `paths`, line 94=`[tool.pyright]` `include` | **VERIFIED** | Live read of `pyproject.toml` confirms exactly: line 86 `[tool.vulture]`, line 88 its `paths`; line 93 `[tool.pyright]`, line 94 its `include`. `15-RESEARCH.md`'s current text (post-fix) matches this precisely, including an honest note about the earlier swap and that it never propagated into the plan (which I also confirmed — Task 1's actual `<action>` text in `15-02-PLAN.md` never had the swap and already said "re-read live"). |
| L65 — fragile deeply-nested lambda in `SKILL-SHAPE-OK`'s section extractor | 15-02 | Rewritten as a single-pass list-comprehension + dict, normalizing headings and excluding `###` subheadings | **VERIFIED** | Diff confirms the lambda-chain replaced with `heads=[(m.group(1).split(':')[0].split('(')[0].strip(), m.end()) for m in re.finditer(r'^##[ \t]+(.+?)[ \t]*$', t, re.M)]` plus `bounds`/`sections`. I independently traced the regex semantics by hand: `^##[ \t]+` requires whitespace immediately after exactly two `#` characters, so a `###` line's third `#` fails that match and the h3 heading is correctly *not* treated as a section boundary — the numbered items after it stay inside the enclosing `## Limits` section's sliced body, exactly as claimed. The heading-normalization chain (`split(':')[0].split('(')[0].strip()`) correctly reduces `"Hand-off mechanism (SC3):"` to `"Hand-off mechanism"`. Both edge cases the finding named are genuinely handled, not just described as handled. |

All six Cycle 1 findings (1 HIGH, 1 LOW/MEDIUM, 4 LOW across both plans) are confirmed fixed against live source, not merely reworded in the plan text. No fix introduced a new regression. One new LOW finding surfaced during independent review of 15-01 (see above), of the same general class as an already-fixed Cycle 1 finding but very likely already safe given the plan's existing phrasing.

## Overall Risk Assessment: LOW

Both plans are ready to execute. The architecture is unusually well-grounded — nearly every non-trivial claim (CLI contracts, shared builder field access, criticality vocabulary, hand-off text, registration line numbers) was independently checked against live source in this review and held up exactly as described, not just as plausible-sounding. The single HIGH finding from Cycle 1 is genuinely resolved at the root (a floor, not an averaged compromise), and the remaining suggestion (explicit qualified-attribute-access rule for `dispatch.dispatch_all` in `cli.py`) is optional polish, not a blocker.

---

## Consensus Summary (Cycle 2)

Single-reviewer pass (claude lane only, explicit `--claude`; opencode/xai-grok-4.6 remains billing-blocked, codex fallback remains OAuth-expired — both confirmed genuine external-account failures). No cross-reviewer agreement to synthesize; findings below are the claude lane's own.

### Agreed Strengths
N/A — single reviewer. See "Strengths" under 15-01 and 15-02 above; notably all Cycle 1 CLI-contract, registration, and hand-off-text claims re-verified byte-for-byte against live source.

### Agreed Concerns
N/A — single reviewer. Only unresolved item is:
- **LOW (15-01, new in Cycle 2):** `cli.py` should state explicitly that `dispatch.dispatch_all` and `aggregate.aggregate` must be called via qualified module-attribute access (never imported by name), mirroring the existing `DOMAIN_TIMEOUT_SECONDS` rule, so Task 3's Test 5 monkeypatch is guaranteed effective. Not yet incorporated into either PLAN.md and not explicitly deferred/rejected.

### Divergent Views
N/A — single reviewer.

**Disposition:** All 6 Cycle 1 findings verified genuinely fixed against live source. 0 HIGH concerns remain. 1 new LOW concern surfaced (see above), not yet incorporated into PLAN.md.
