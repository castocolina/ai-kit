---
phase: 02
reviewers: [opencode]
reviewed_at: 2026-09-09T20:17:42Z
plans_reviewed: [02-01-PLAN.md, 02-02-PLAN.md]
models:
  opencode: "router-env/my-plan-review (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 02

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts

(none)
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

I'll verify the plans' claims against the actual repo before writing findings.
Pre-commit config, Makefile, and `config_io.py` claims check out. Now verifying the remaining referenced files:
Core precedent files verified. Checking the remaining referenced artifacts (ROADMAP criteria, ONESHOT-RULES, `.aikit/review-spec.toml`, e2e run.sh preflight):
All source claims verified. Here is the cycle-3 review.

---

# Phase 02 Cross-AI Plan Review — Cycle 3

Verification basis: I read every in-repo artifact the plans cite — `Makefile`, `.pre-commit-config.yaml`, `skills/ai-kit-spec-review/ai_kit_spec/{cli,cache,config_io,model_catalog}.py`, `tools/setup.py`, `tests/test_ai_kit_spec.py`, `tests/e2e/docker/{run.sh,fixtures/README.md}`, `.dockerignore`, `README.md`, `.aikit/review-spec.toml` — and traced each plan claim against the actual code. Line citations below are from those reads.

## 02-01

**Summary.** A thorough, well-grounded tracer-first plan for the phase's only novel logic (the four-state JSONC scanner), with two review cycles already folded in and every repo-level precedent claim verified true. The remaining defect is one internal specification tension around `significant_indices`'s exact semantics that will surface as a contradictory TDD pin, plus two minor robustness gaps. Execution-ready.

**Strengths.**

- **Every precedent claim verified true.** `write_toml_preserving` is exactly `mkstemp(dir=...)` + `os.replace` + unlink-on-`OSError` with **no `chmod`** (`tools/setup.py:442-463`), so RESEARCH Pitfall 2's gap is real and Task 1 step 4's `stat.S_IMODE` + `os.chmod` closure is justified. The CLI dispatch shape (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:482-490`), the 7-line entrypoint shim (`skills/ai-kit-spec-review/ai-kit-spec.py:1-7`), the `sys.path.insert` test header (`tests/test_ai_kit_spec.py:13`), the XDG cache convention (`ai_kit_spec/cache.py:7-10`), and `cfg_local_path` (`ai_kit_spec/config_io.py:16-18`) all match the plan's descriptions exactly.
- **Wiring gaps are real and the fixes land in the right places.** `Makefile:34` is an explicit module list; `.pre-commit-config.yaml:53` (unittest hook) is a second explicit list; the `ruff` (line 21) and `py-compile` (line 48) `files:` regexes indeed omit the new skill. The plan's bogus-alternative observation is also confirmed: `skills/ai-kit-spec-review/ai-kit-spec-review.py` does not exist on disk (the real shim is `ai-kit-spec.py`), so that regex alternative is dead — and the plan correctly leaves it alone per ONESHOT-RULES Rule 4.
- **Tracer methodology is genuinely non-circular.** The hand-authored `opencode-expected-remove-beta.jsonc` (Task 1 step 2, authored before any scanner code, forbidden from regeneration) plus the "no expected value from `jsonc_edit` locators" rule and the length-reconciliation assertion close the self-consistency hole round 1 found.
- **Cycle-2 fixes verified present:** `run_cli(*args, cwd, env=None)` with three machine gates (sole call site, `cwd=`/`stdin=` pinning, AST signature check); the neutral-seed invariant for `significant_indices` (seeded once at the `provider` opening brace, AST-enforced single call, `,`-decoy in the fixture, `strip_jsonc_comments` cross-check); and the skip-but-report non-object depth-1 value (`non_object_provider_keys` from the same walk, distinct `cmd_remove` message, `note:` line in `list`).
- **Comma case split is complete and comment-preservation semantics are decided, not emergent** — first/middle/last/sole positions each get a fixture, and "comments are never consumed; removal is two disjoint deletions" is pinned in both directions (forward by the expected fixture, backward by Task 2's `gamma-router` case).
- **T-02-06's symlink mechanism is now stated correctly** (`rename(2)` replaces the symlink itself; `realpath` first writes through the link), and `TestSymlinkedConfig` pins it.

**Concerns.**

- **MEDIUM — `significant_indices`'s definition is internally tension-ridden between Task 2 and Task 3.** Task 2 step 3 defines it as "positions that are neither whitespace nor comment bytes" — which **includes non-whitespace positions inside string literals** — and `TestWalkerSeeding`'s cross-check pins exactly that definition (in-string non-whitespace characters are left unchanged by `strip_jsonc_comments`, so they belong to the cross-check set; the two sets are equal only under this definition). But Task 3 step 1's `strip_trailing_commas`, implemented as a pure lookup into that list ("replace every `,` whose next significant character is `}` or `]`"), would then **replace a `,` inside a quoted string whose next list-adjacent significant char is an in-string `}`** — directly violating Task 3's own behavior bullet ("a `,}` sequence inside a quoted string value is left untouched") and corrupting e.g. a `baseURL` of `"http://h/,}"`. The parenthetical "(outside strings and comments)" in Task 3 step 1 quietly requires string-state awareness that a bare position list does not carry, and the "reuse `significant_indices` rather than writing a regex" rationale misattributes the safety to the list when it actually comes from state. This fails loudly under TDD (good), but an executor who "fixes" it by excluding in-string positions from `significant_indices` will instead fail `TestWalkerSeeding` as worded. One clarifying sentence fixes it: the list keeps the Task-2 definition (in-string non-whitespace included), and `strip_trailing_commas` considers only commas/braces at **code state** (walker state, not list membership alone).
- **LOW — `UnicodeDecodeError` escapes the `except OSError` read guard.** Task 2 step 6 wraps `cmd_remove`'s config read in `except OSError`, but `open(path, encoding="utf-8")` on a non-UTF-8 or corrupted file raises `UnicodeDecodeError` (a `ValueError`), surfacing as the raw traceback the plan's own must_haves say never happens. Use `except (OSError, UnicodeDecodeError)` on the read (the write side is unaffected — it writes back text it already decoded).
- **LOW — a nested `"provider"` key is not covered by Pitfall 4.** Pitfall 4 anchors the *id* search to depth 1, but `find_provider_object` itself must anchor the *`"provider"` key* to depth 0 (a hand-edited file could contain a `"provider"` key inside some other top-level object before the real one). Implied by "walk from offset 0" but never stated; one sentence in Task 1 step 3 would pin it.
- **LOW — tracer test output becomes machine-dependent after Plan 02-02 lands.** 02-01's tracer invokes `run_cli` without `env=`, and 02-02 Task 1 step 5 rewrites `cmd_remove` to call `collect_references`, which scans `XDG_CONFIG_HOME`/`XDG_CACHE_HOME` — so on a configured dev box the tracer's captured stdout will include `cross-reference:` audit lines naming real host paths. Pass/fail stays deterministic (warnings are non-blocking; the assertions don't touch stdout), but passing a scoped `env` in the tracer and no-op tests too would make the whole module hermetic, matching the spirit of 02-02's key_link.

**Suggestions.**

- Add the `significant_indices`/`strip_trailing_commas` state-clarification sentence (Task 3 step 1) before execution — it is the one place an executor can be led down a wrong path by the plan's own wording.
- Widen the read guard to `(OSError, UnicodeDecodeError)` in Task 2 step 6 and mirror it in `cmd_list` (Task 3 step 3).
- State the depth-0 anchoring requirement for the `"provider"` key in Task 1 step 3.
- Optionally have the tracer/no-op tests pass a scratch-scoped `env` so no test's *captured output* (as opposed to result) varies by machine.

**Risk Assessment.** **LOW.** All precedent claims verified against source; the scanner design handles every enumerated pitfall with fixtures that make each failure mode loud; the one MEDIUM is a specification ambiguity that TDD will surface as a failing test rather than a silent corruption, and the byte-preservation invariants (hand-authored ground truth, disjoint-deletion rule) make the worst-case failure mode a visible diff, not data loss.

## 02-02

**Summary.** A complete, honest-by-construction cross-reference plan whose two superset decisions (scanning the global review-spec tier; reporting-with-qualifier under `local-only`) are both verified correct against `config_io.cfg_resolve`'s actual code. All cycle-2 fixes are present with enforcement gates. Remaining concerns are minor over-match cosmetics in the scan itself and one small robustness nit.

**Strengths.**

- **The `local-only` semantics mirror the real code exactly.** `cfg_resolve` returns without loading the global tier when `strategy == "local-only"` (`ai_kit_spec/config_io.py:73-76`), defaults to `global-merge` when the key is absent (line 73), and falls back to global-only when there is no local file at all (lines 69-72) — the plan's three statuses (`scanned` / `absent` / `scanned-inactive`) and the "no local file ⇒ global active" behavior bullet (Task 1) match all three branches. Reporting-with-qualifier rather than dropping the tier is the right call for a non-blocking warning, and the rejected alternative is reasoned, not asserted.
- **The catalog schema claim is verified.** `merge_catalog_entry` writes `catalog[model_id] = entry` (`ai_kit_spec/model_catalog.py:154,158`), so the flat `{model_id: entry}` iteration in `scan_catalog` is correct; mandatory `provider`/`runtimes.<cli>.model_id` fields confirmed (`model_catalog.py:12,37`).
- **The scratch-tree requirement is real, not precautionary.** `.dockerignore` excludes `.aikit` verbatim, and `tests/e2e/docker/run.sh:11-18` asserts `~/.config/opencode` (among others) is absent preflight — so any test reading the repo's `.aikit/review-spec.toml` or the host's real ai-kit config would pass locally and fail (or silently vary) in the clean room. The cycle-2 env-scoping fix (copy-then-override `dict(os.environ)`, `run_cli(..., env=env)`, `ENV_SCOPED` AST gate, and the audit-path-not-under-`~` assertion) is exactly the right mechanism-evidence, not intention.
- **The `.aikit`-literal gate is now machine-evaluable** (exactly one non-comment literal, not anchored to `dirname(__file__)`), with the residual judgment honestly moved to a `<human-check>` — this was cycle-1's finding and it is properly resolved.
- **README disposition is correct.** `README.md:405` does send opencode users to `~/.opencode/skills/ai-kit`, matching neither documented opencode skill directory; deferring it per ONESHOT-RULES Rule 4 with the one-insertion acceptance criterion as the guard is the right treatment, and the observation is durably recorded in `<notes>` for a future docs phase.
- **SKILL.md task is unusually well-specified**: host-neutral five-candidate resolution (with grep gates for the `opencode/skills` and `agents/skills` candidates), all three exit codes gated, `## Edge cases` gated by keyword, synthetic-value sentinel grep (`20128`), and a human-check that example output matches the real CLI.

**Concerns.**

- **LOW — `str()` coercion in `scan_catalog` can both over-match and leak structure.** Task 1 step 2 coerces every scanned value with `str()` before the substring test. A dict-valued field (hand-edited catalog) would be stringified into something that can contain the id *and* would be printed verbatim as the `Reference.value` — technically violating T-02-07's "never widen to dump the whole entry" in a corner case. Simpler and safer: substring-test only `isinstance(v, str)` values and skip non-strings (a non-string `provider`/`model_id` field is schema-invalid per `model_catalog.py`'s own type table anyway, so skipping loses nothing).
- **LOW — substring matching on `cli` over-warns for generic ids.** A user who names a custom provider `opencode` (or `codex`) makes every reviewer's `cli = "opencode"` field a hit. Non-blocking and the safe direction per D-04, so acceptable — but the SKILL.md cross-reference section could carry one sentence noting matches are substring-based and informational, so a user flooded with `cli`-field warnings understands why.
- **LOW — no exit-code/status contract for `collect_references` failure modes is needed, and none is claimed** — malformed sources degrade to zero references with an `absent`/`scanned` audit row, which the behavior bullets already pin. No action required; noted only to confirm I looked for a gap here and found none.

**Suggestions.**

- Replace the `str()` coercion with an `isinstance(v, str)` filter in `scan_catalog` (Task 1 step 2) — one line, removes both the over-match and the structure-leak corner.
- Add the one "matches are substring-based and informational" sentence to SKILL.md's warning section (Task 2 item 6).

**Risk Assessment.** **LOW.** Every data-shape and resolution-order claim verified against live source; the threat model's honesty requirements (audit trail, `scanned-inactive` qualifier, redaction allowlist) are each pinned by a behavioral assertion; the only findings are cosmetic over-warning corners in a warning that is by design non-blocking.

## Cross-Plan Comparison

- **Dependency ordering is sound and shared invariants are enforced from both sides.** 02-02 (wave 2) modifies `cmd_remove` and `cross_reference.py` that 02-01 (wave 1) creates; the `run_cli` contract (sole `subprocess.run` site, required `cwd=`, optional `env=`) is introduced in 02-01 with AST/grep gates and consumed in 02-02 with its own `ENV_SCOPED` gate — the cross-plan inconsistency cycle 1 found is now closed symmetrically. `SCRATCH_REVIEW_SPEC_RELPATH` is introduced in 02-01 and is what makes 02-02's exactly-one-`.aikit`-literal gate satisfiable.
- **One asymmetry worth noting (LOW):** 02-01's tracer test predates 02-02's `collect_references` rewrite and passes no `env=`, so after wave 2 its captured stdout references host paths (see 02-01 concern 4). Pass/fail determinism is preserved; only output cosmetics vary. Cheapest fix is in 02-01 (scoped `env` in the tracer), not 02-02.
- **Combined scope matches the phase goal exactly** — SC-1/2/3 in 02-01, SC-4 plus docs and gates in 02-02, with both superset decisions (global tier scan; both-tiers audit) explicitly reasoned rather than silent scope creep.

## Cycle-2 Concern Resolution Status

All four cycle-2 items are accounted for in the current plan text:

1. **`run_cli` env passthrough** — RESOLVED (02-01 Task 1 step 9 + three machine gates; 02-02 Task 1 step 6 + `ENV_SCOPED` gate + audit-path assertion).
2. **`significant_indices` seeding** — RESOLVED (02-01 Task 2 step 3: single neutral-seeded call, AST-enforced, `TestWalkerSeeding` cross-check, `,`-decoy fixture).
3. **Non-object depth-1 provider value** — RESOLVED (02-01 Task 2 step 7 mechanism + tests; 02-02 Task 2 item 8 documentation with its own gate).
4. **`README.md:405` inaccuracy** — correctly DISPOSITIONED as out-of-scope per the cycle-2 reviewer's own recommendation: verified still present at `README.md:405`, recorded in 02-02's `<notes>`, and guarded by the one-insertion acceptance criterion.

## Overall Risk Assessment

**LOW — approve for execution.** Both plans' factual claims survived source verification without a single miss; the phase's core hazard (silent corruption of a secret-bearing config) is defended by layered, independently-grounded pins (hand-authored expected fixture, disjoint-deletion rule, atomic-write failure test, mode/symlink preservation, clean-room gate). The one MEDIUM finding (the `significant_indices` / `strip_trailing_commas` state-semantics tension in 02-01 Task 3) is a spec ambiguity that TDD converts into a loud test failure rather than a silent bug, so it does not block execution — but folding in the one-sentence clarification (code-state check for the trailing-comma stripper, list definition unchanged) before dispatching will save the executor a confusing red cycle. The three LOW items (UnicodeDecodeError guard, depth-0 `"provider"` key anchoring, tracer-test env scoping) are cheap, optional hardening.

---

## Consensus Summary

Single-reviewer cycle (opencode only): 0 HIGH findings, 1 MEDIUM (a spec-ambiguity tension between Task 2's `significant_indices` definition and Task 3's `strip_trailing_commas` in 02-01), and 5 actionable LOW findings across the two plans. All four cycle-2 concerns are confirmed resolved in-plan (three fixed, one — the README.md doc inaccuracy — correctly left as a deliberate out-of-scope disposition per the cycle-2 reviewer's own recommendation). Overall risk assessed LOW; reviewer recommends approval for execution, optionally folding in the one MEDIUM clarification first.

### Agreed Strengths
(single-reviewer cycle — no cross-reviewer agreement to synthesize)

### Agreed Concerns
(single-reviewer cycle — no cross-reviewer agreement to synthesize)

### Divergent Views
(single-reviewer cycle — no divergent views to report)
