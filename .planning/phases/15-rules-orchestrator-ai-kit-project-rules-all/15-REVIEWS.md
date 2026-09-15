---
phase: 15
reviewers: [claude]
reviewed_at: 2026-09-15T01:13:36Z
plans_reviewed: [15-01-PLAN.md, 15-02-PLAN.md]
models:
  claude: "unknown"
model_sources:
  claude: "unknown"
---

# Cross-AI Plan Review — Phase 15

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
(none)
<!-- gsd:plan-revision-conflicts:end -->

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

## Consensus Summary

Single-reviewer pass (claude lane only — this project's default reviewer, opencode/xai-grok-4.6, is billing-blocked at 403 spending-limit, and the codex fallback has an expired OAuth token with a 401 refresh_token_reused error, both confirmed genuine external-account failures rather than repo issues). No cross-reviewer agreement to synthesize; findings below are the claude lane's own.

### Agreed Strengths
N/A — single reviewer. Notable strengths (see full review above): D-04's `remediate()`-calls-`check()` contract is verified against live source for all 6 siblings; the `dispatch_all()`/`aggregate()` split genuinely supports stub-based testing (SC4); `DOMAIN_ORDER` is the single source of truth for ordering; Task 1 of 15-01 dogfoods against all 6 real sibling checkers; the `NAMING_VERDICT` fail-closed mechanism in 15-02 is a hard-asserted control, not aspirational prose.

### Agreed Concerns
N/A — single reviewer. Notable concerns (see full review above):
- **HIGH (15-02):** `SKILL-SHAPE-OK`'s floor (`>=8` limits) and `JUDGE-GATE-OK`'s ceiling (`LIMIT_COUNT_FINAL==8`) contradict each other; the family's own history (Phase 13: 7→8, Phase 14: →11) shows limit counts routinely grow past the initial estimate during honest documentation, so this gate is likely to trigger a false failure or force an illegitimate limit-softening to pass. Fix: change `lc==8` to `lc>=8` (or `>=` the count Task 1 actually shipped).
- **MEDIUM (15-01):** Task 1's `<precondition>` smoke-tests all 6 siblings' `check` subcommand, but D-04 locks the orchestrator's real dispatch path to `remediate`. A sibling could pass the precondition while still failing under `remediate()`. Fix: precondition should invoke `remediate`, not `check`.
- **LOW/MEDIUM (15-02):** `15-RESEARCH.md` Pitfall 4 swaps the `pyproject.toml` line-to-tool mapping (pyright vs vulture); does not propagate into a plan bug since Task 1's own text is correct, but worth a research-doc amendment.
- **LOW (15-01):** `DOMAIN_TIMEOUT_SECONDS` monkeypatch could silently no-op if `run_domain` binds the timeout as a function-default parameter instead of reading the module global live.
- **LOW (15-01):** Python translation of the `$CLAUDE_PLUGIN_ROOT` candidate path needs explicit empty-string handling to avoid a bogus `/skills/<name>` path.
- **LOW (15-02):** `SKILL-SHAPE-OK`'s deeply-nested lambda verify script is fragile/hard to debug if section-extraction regex misbehaves on real heading text.

### Divergent Views
N/A — single reviewer.
