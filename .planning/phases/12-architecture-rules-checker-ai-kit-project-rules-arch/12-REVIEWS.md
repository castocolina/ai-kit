---
phase: 12
reviewers: [opencode]
reviewed_at: 2026-09-14T11:41:16Z
plans_reviewed: [12-01-PLAN.md, 12-02-PLAN.md, 12-03-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 12

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
(none)
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

Reviewing the three Phase 12 plans against the live tree. Loading review guidance and checking the files they cite.
Using writing-clearly-and-concisely for the review. Verifying plan claims against the live tree.
Checking Makefile targets, `tests/test_arch.py` (D-01), sibling `__init__` pattern, and ROADMAP SC1.
Checking one more load-bearing gap: whether the 12-02 tracer actually exercises the `sl_path` name-resolution shape from the live file.
Using writing-clearly-and-concisely. Claims below are checked against the live tree, not the plan text.

## 12-01

**Summary.** Solid wiring plan. It stands up the skill on the real shared parsers (`makefile_parse.py:19-112`), grows `STRUCTURAL_KINDS` additively (`remediation.py:20`), copies the precommit `__init__.py`/`cli.py` pattern, and splits existence vs chaining the way ROADMAP SC2 requires. The tracer's positive fixture matches `Makefile:61`/`Makefile:66`. Main risks are TDD-in-one-huge-commit and a non-vacuity protocol that can no-op if the matcher uses `re.fullmatch`.

**Strengths**
- Shared parsers are the right primitive. `parse_makefile_targets` returns `set()` for a missing file (`makefile_parse.py:26-27`); `recipe_mentions_target` is already both-ends token-bounded (`makefile_parse.py:111`), which is why `arch-test` will not match inside `arch-test-integration`.
- `STRUCTURAL_KINDS = ("makefile", "precommit")` at `remediation.py:20`; appending `"arch"` matches the comment at `remediation.py:17-19`. Identifier logic at `remediation.py:86` really does prefer `target` over `category`, so D-A3's two categories are load-bearing.
- D-A1 is fully anchored. Live Makefile targets that match it: only `arch-test` (confirmed against every header). `archive`/`check`/`test` do not match. Bare `arch` would, and the plan already forces declaration-order determinism because `parse_makefile_targets` returns a set (`makefile_parse.py:19`).
- D-A2's three chaining clauses match how this repo actually wires `test` (prereqs only, empty recipe at `Makefile:66`) and how other repos invoke `$(MAKE) <target>`.
- D-A4 + D-A6 are correct: no cache in this skill; Phase 10/11 CLIs really do have `cache-update` (`ai_kit_project_rules_precommit/cli.py:119`).
- Gate surfaces are real and counted right: `Makefile:46`/`Makefile:70`, `.pre-commit-config.yaml:21,50,55`, `pyproject.toml:88,94`. `TestGateRegistration` at `tests/test_ai_kit_project_rules_precommit.py:867` is a copyable shape.
- Skill dir does not exist yet; Phase 11 `SKILL.md` does. Precondition is honest.
- No `SKILL.md` this wave — installer still requires it (`README.md:48`).

**Concerns**
- **MEDIUM — Task 2 non-vacuity vs `fullmatch`.** D-A1 says `fullmatch` or `^…$`. Task 2 says "drop the trailing `$`" to prove `archive` fails. `re.fullmatch(r'^(arch|…)?', 'archive')` still fails because leftover `ive` is not consumed. An executor who followed D-A1 can "confirm" a no-op mutation. Mutate `fullmatch`→`match` (or drop both `$` and `fullmatch`).
- **MEDIUM — do not put `target:` on these findings.** `build_remediation` at `remediation.py:86` uses `finding.get("target", finding.get("category"))`. Makefile findings use `target` (`makefile_checker.py:463`). Copying that onto both arch findings would collapse remediate `id`s. D-A3 lists fields without `target`; say that prohibition in the finding schema, not only in the rationale.
- **LOW — depth 8, no breadth cap.** T-12-01 mitigates cycles; a bushy prerequisite graph is still attacker-shaped input. A node cap (or a cap on `len(visited)`) would match the threat better than depth alone.
- **LOW — Task 1 is the whole skill in one commit.** Tracer is good, but "tests first, then implement, one commit" is easy to invert under that size.

**Suggestions**
- Pin finding fields as exactly `{category, issue, criticality, summary, recommendation, needs_research}` — no `target` key.
- For declaration order, scan `_TARGET_HEADER_RE.finditer` (already ordered at `makefile_parse.py:16`) rather than iterating the set.
- Non-vacuity: switch `fullmatch` to `match`, revert, report.

**Risk Assessment:** LOW–MEDIUM. Scope is right; the matcher/schema pins need one extra sentence each so a cheap executor cannot silently get them wrong.

## 12-02

**Summary.** This is the load-bearing plan. The D-01 correction is true against the live file, SC1 scoping is true against `ROADMAP.md:369`, and refusing to tune the checker until ai-kit is clean is the right honesty rule. The tracer can still go green without the name-resolution that the live `_sl` load requires, and the D-A4 "both checks only when the target exists" sentence contradicts SC4 (canonical-tool text belongs on the missing-target finding).

**Strengths**
- Live D-01 correction is accurate:
  - unrelated load: `tests/test_arch.py:34-40` (`setup.py`)
  - parse helper: `tests/test_arch.py:87-96` (`ast.parse(source, filename=name)`)
  - subjects: `tests/test_arch.py:374-375` (`status-line.py`, `statusline-doctor.py`)
  - on-target load: `tests/test_arch.py:605-611` (`spec_from_file_location` + `exec_module` of `status-line.py`)
- ROADMAP SC1 is existence/chaining only (`ROADMAP.md:369`). An `arch-test-ast-only` finding on this repo does not break SC1.
- D-A7's dotted-token rule (`tests.test_arch` → `tests/test_arch.py`) matches `Makefile:62`.
- D-A8's parser-helper fixed point is required: `_parse` does not put a path string in the `ast.parse` call (`test_arch.py:96`); subjects only appear at `_parse("status-line.py")`. The CLEAN/DIRTY tracer uses that wrapper shape.
- Canonical-tool keys match `stack_detect.py:15-26` (`go`/`python`/`node`/`java`/`rust`). Rust/Go as known gap, not a fake tool, matches SC4 (`ROADMAP.md:372`).
- `advisory: True` is required: `auto_apply = not finding.get("advisory", False)` at `remediation.py:96`. Criticality 4 alone would still auto-apply.
- Path containment + "parse, never import the backing file" are the right trust-boundary answers.
- Explicit ban on narrowing correlation so this repo goes clean.

**Concerns**
- **HIGH — tracer does not exercise the live `_sl` name-resolution shape.** Live load is:

```605:611:tests/test_arch.py
    def _sl(self):
        sl_path = os.path.join(_TOOLS, "status-line.py")
        spec = importlib.util.spec_from_file_location("status_line_inv", sl_path)
        ...
        spec.loader.exec_module(mod)
```

  The path string is on the assignment; the call's second arg is a `Name`. The AST-ONLY-OK CLEAN fixture puts `"helper_mod.py"` *inside* the `spec_from_file_location` argument expression (`os.path.join(SRC,"helper_mod.py")`), so string-in-call collection suffices and name resolution is never tested. `status_line_inv` normalizes to `status-line-inv`, not `status-line`. Without one-level local resolution, the live intersection is empty, the expected self-finding never appears, and Task 3's human check / D-01 correction become a false story. Add a fixture that assigns the path to a name and passes that name in, modeled on `_sl`.
- **MEDIUM — D-A4 gating text vs SC4.** Must-haves say both new checks run only when a target was found. Canonical-tool text is attached to the *missing-target* finding (absent branch). Task 2's action is correct; the must-have is not. An executor following the must-have would hide SC4 behind D-A4.
- **MEDIUM — not-verifiable `reason` enum is unpinned.** Action asks for a machine-readable field; AST-ONLY-OK only requires four distinct JSON dumps, which summary-only text satisfies. Pin values (e.g. `not_discoverable` / `not_python` / `unparseable` / `no_parse_call`) so 12-03's SKILL.md and the tests name the same tokens.
- **LOW — normalization and two-level helper are acceptance-only**, not in AST-ONLY-OK. Cheap to add to the tracer.
- **LOW — containment should copy the agents skill's `realpath + os.sep` guard** (`ai_kit_project_rules_agents/cli.py:66-68`), not a bare `startswith(repo_root)` which accepts `/tmp/repo-evil` for `/tmp/repo`.

**Suggestions**
- Add an `_sl`-shaped fixture to Task 1's tracer: `p = os.path.join(SRC, "target_mod.py"); spec_from_file_location(..., p)` plus `_parse("target_mod.py")` → must flag; same with `helper_mod.py` on the name → must not.
- Rewrite the D-A4 sentence: AST-only is gated on target-found; canonical-tool text is gated on target-missing.
- Pin the four reason tokens in D-A9.

**Risk Assessment:** MEDIUM. Right decision, real live evidence, but the tracer can pass a correlation that will not see `tests/test_arch.py:605-611`.

## 12-03

**Summary.** Documentation/closeout plan is well sequenced after working code, copies facts from SUMMARYs instead of re-deriving them, and mechanically discharges SC5 without touching the Phase 999.3 stub. House-style correction for D-01 matches existing precedents. Residual risk is judge-loop pressure on the three honesty limits, which the plan already treats as non-negotiable.

**Strengths**
- Wave 3 after code exists; `SKILL.md` is what makes the dir installable (`README.md:48`).
- Two-subcommand documentation vs Phase 10/11's `cache-update` is the right anti-copy rule (`cli.py` siblings really have four).
- SC5 byte-compare against `42c8f8e` is a real object (`42c8f8e docs(11): independent verification report…`). Phase 999.3 stub is at `ROADMAP.md:494-519` and already carries the 2026-09-13 note; this plan correctly leaves it untouched.
- Correction form `Scouting claim corrected by Phase 12:` matches `ROADMAP.md:326` / `REQUIREMENTS.md:76-77` (`<what was wrong> corrected by Phase N:`). Landing it inside the D-01 bullet after Reversibility (`12-CONTEXT.md:60-62`) before D-02 (`12-CONTEXT.md:63`) is the right place.
- Naming frozen: Phases 13–15 name this scheme (`ROADMAP.md:383+`). Escalation not rename is correct.
- README siblings are `README.md:39-41`; one added row, zero removals is the right assertion.
- SUMMARY-INPUTS-PRESENT-OK as a hard halt (do not reconstruct from plan prose) is the right discipline.

**Concerns**
- **MEDIUM — judge loop vs three limits.** T-12-17 is real. Keep the "record disagreement, do not concede" rule; a brevity-optimized rubric will try to cut the form-only paragraph, which is also how SC5's unresolved ambition reaches a user.
- **LOW — `git log -3` for `NO-ROADMAP-EDIT-OK`.** Parallel commits can put `ROADMAP.md` in that window. Prefer `git diff 42c8f8e HEAD -- .planning/ROADMAP.md` restricted to this phase's commits, or `git log --name-only` over the plan's own SHAs.
- **LOW — description-length ≥ 120** can pad the routing string. Bound it by sibling-boundary content, not character count.
- **LOW — Task 1 verify forbids `cache-update` in SKILL.md.** A "this skill has no cache-update (unlike siblings)" sentence would trip that scan. Allow the token in a negation, or say "no research/cache step" without the sibling subcommand name. The current `cache-update not in low` check fights the "answer the four-subcommand expectation" instruction.

**Suggestions**
- Soften the `cache-update` absence check to "not documented as a subcommand this skill runs" (e.g. not in a usage line).
- Quote the limits section in 12-03-SUMMARY as already required — that is the judge-loop backstop.

**Risk Assessment:** LOW. Process-heavy, correctly so; no code surface.

---

## Cross-plan

Wave order 01→02→03 matches the dependency graph and the install boundary. SC1/SC2 (01), SC3/SC4 (02), SC5 (03) are not split. Shared-package edit is isolated to 12-01. The phase will achieve the ROADMAP goal if 12-02 adds the `_sl`-shaped fixture and clarifies that canonical-tool text lives on the missing-target branch.

**Phase risk:** MEDIUM, driven by 12-02's correlation vs live `tests/test_arch.py:605-611`, not by scope creep. The self-finding on this repo is a true statement to disclose, not a criterion failure.

---

## Consensus Summary

Single-reviewer cycle (opencode only) — no cross-reviewer consensus to synthesize. All findings below are from the single opencode (xai/grok-4.6, reasoning=high) pass, which verified claims against the live repository tree with file:line citations for essentially every strength and concern.

### Agreed Strengths
N/A — single reviewer.

### Agreed Concerns
N/A — single reviewer.

### Divergent Views
N/A — single reviewer.
