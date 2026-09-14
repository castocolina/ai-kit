# Phase 12: Architecture Rules Checker (ai-kit-project-rules-arch) - Context

**Gathered:** 2026-09-13
**Status:** Ready for planning — BLOCKED on Phases 9, 10, and 11 landing first (see Phase Boundary)

<domain>
## Phase Boundary

New skill `ai-kit-project-rules-arch` verifies a repo has an `arch-test`-
shaped Makefile target, chained into `test`, and (where the backing test
file is discoverable) that it is AST-only — never importing/executing the
modules it architecturally checks. Carries hardcoded baseline per-stack
canonical-tool knowledge (Python: import-linter, Node/TS: dependency-
cruiser, Java: ArchUnit; Rust/Go: explicitly flagged known gap, no false
canonical choice asserted) without attempting real dependency-direction/
layering-boundary enforcement itself. This phase **promotes and resolves**
`.planning/ROADMAP.md`'s Backlog "Phase 999.3: Architecture-layer test
suite" entry at this scoped-down, form/convention-only ambition — the
backlog stub's fuller ambition (real layering/dependency-direction
enforcement across the whole `tools/`/`skills/` tree) remains an
explicitly-flagged known gap, not built here. The backlog stub itself
stays unchanged in ROADMAP.md; this phase is its resolution, not a
second, separate item — this phase's own PLAN/SUMMARY must record that
resolution note (ROADMAP Success Criterion 5).

**Hard prerequisite — this phase cannot be planned or executed before
Phases 9, 10, and 11 actually land.** `.planning/ROADMAP.md`'s "Depends
on" line for Phase 12 names Phase 11 directly; Phase 11 itself depends on
Phase 10, which depends on Phase 9. As of this discussion, NONE of Phases
9-11 have a plan or execution yet (each has only a CONTEXT.md). This
CONTEXT.md captures vision-level decisions now so they aren't lost, but
the researcher/planner for Phase 12 MUST verify all three prior phases are
actually merged before grounding any plan against "what currently exists."

</domain>

<decisions>
## Implementation Decisions

### AST-only check scope (the one real gray area this phase surfaced)
- **D-01:** The AST-only check is **target-aware**, not a file-level
  blanket scan. It flags a backing architecture-test file only when THAT
  FILE imports or executes the SPECIFIC module it is architecturally
  checking (the arch-test's own subject) — not any import/`exec_module`
  call anywhere in the file for unrelated purposes. Discovered during
  scouting: ai-kit's own `tests/test_arch.py` (the exact file Success
  Criterion 1 requires to produce no existence/chaining finding) calls
  `importlib.util.spec_from_file_location` + `exec_module` to load
  `tools/setup.py` for incidental inventory-test helpers, while its actual
  architecture-fitness checks (`check_config_env_in_cfg`,
  `check_role_prefix_integrity`, etc.) parse `tools/status-line.py` —
  the real checked target — via pure `ast.parse`, never importing it. A
  file-level blanket scan would misfire on this exact real file, directly
  undercutting the design spec's own framing of `tests/test_arch.py` as
  the project's best-practice reference example. ROADMAP Success
  Criterion 3's own wording ("a check file that `importlib.import_module`s
  **its target**") already implies target-awareness; D-01 makes that
  implicit requirement explicit so the planner doesn't implement the
  simpler, incorrect blanket version.
  — **Reversibility:** costly — a blanket implementation shipped first
  would need a retrofit once the false-positive against ai-kit's own repo
  surfaces, not a config tweak.

  Scouting claim corrected by Phase 12: D-01's DECISION (target-aware
  correlation, not a blanket scan) stands and was implemented faithfully
  -- confirmed by plan 12-02's live re-verification. Live evidence: the
  file's architecture-fitness check calls `_parse("status-line.py")` at
  `tests/test_arch.py:374` (a parser-helper function reaching
  `ast.parse`), correctly parsing `tools/status-line.py` -- the real
  checked target -- exactly as this decision describes, and the unrelated
  `tools/setup.py` load this decision also names is correctly NOT
  flagged. But the SAME FILE additionally contains
  `TestSegmentInventory._sl` at `tests/test_arch.py:605-611`, which
  separately loads that SAME module (`tools/status-line.py`) via
  `importlib.util.spec_from_file_location` + `exec_module`, for unrelated
  segment-inventory test helpers. This decision's supporting claim that
  the file "never import[s]" its checked target is therefore not accurate
  against the live tree: the file's architecture-fitness METHODS are
  AST-only, but the FILE as a whole is not. Consequence, per plan 12-02's
  recorded re-verification: running the finished checker against this
  repository DOES produce one `arch-test-ast-only` finding
  (`backing_file_executes_checked_target`) -- a true, correctly-
  implemented result of the target-aware design this decision specified,
  not a checker defect. ROADMAP Success Criterion 1 is unaffected -- it
  is scoped to target-existence and chaining findings only, neither of
  which fires here.
- **D-02:** Identifying "the specific module being architecturally
  checked" (D-01's target) is resolved by name/path correlation — e.g. the
  module path(s) passed to `ast.parse`/the file(s) the backing test's own
  assertions are grounded against — left to the planner/implementer for
  exact mechanism, but the principle (correlate import/exec calls against
  the actual checked-target path, not a blanket scan) is locked.

### Everything else — already locked by ROADMAP + design spec
- **D-03:** The 5 ROADMAP success criteria (target existence, chaining as
  a distinct finding from existence, AST-only-ness per D-01/D-02, the
  exact canonical-tool-per-stack remediation text, and the backlog-
  resolution PLAN/SUMMARY note) are accepted as written — no scope
  changes surfaced during this discussion.

### Claude's Discretion
- Exact heuristic for locating "the backing test file" for a given
  `arch-test` target in an arbitrary fixture repo (ROADMAP says "where
  discoverable" — implying a best-effort lookup, not a hard requirement
  to always find it).
- Exact correlation mechanism for D-02 (by imported module's `__name__`,
  by comparing the checked file path against import statement targets,
  etc.).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design spec, roadmap, and backlog
- `docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`
  §"`ai-kit-project-rules-arch` (new, form/convention scope)" — the
  authoritative scope statement, per-stack canonical-tool table, and the
  note confirming ai-kit's own `tests/test_arch.py` already follows the
  "tests, not a side lint pass" best practice (NOT a claim that it's
  AST-only — see D-01's scouting finding for why that distinction matters)
- `.planning/ROADMAP.md` §"Phase 12: Architecture Rules Checker
  (ai-kit-project-rules-arch)" — goal (including the explicit backlog-
  resolution framing), the Phase-11 dependency note, and the 5 fixture-
  provable success criteria
- `.planning/ROADMAP.md` §"Phase 999.3: Architecture-layer test suite
  (BACKLOG)" — the original backlog stub this phase resolves at a scoped-
  down ambition; read its dated 2026-09-13 resolution note for the exact
  framing to echo in this phase's own PLAN/SUMMARY (Success Criterion 5)
- `.planning/REQUIREMENTS.md` — `REQ-rules-arch` (Traceability table,
  v1.2 section)
- `docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`
  §"Open gap, explicitly flagged (not silently dropped)" — the Rust/Go
  known-gap language this skill's remediation output must echo verbatim,
  not paper over

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/test_arch.py` (640 lines) — ai-kit's own backing file for its
  `arch-test` Makefile target; the concrete example this phase's checker
  must correctly classify as AST-only (per D-01/D-02) despite containing
  an `importlib.util`-based module load
- `Makefile:61` (`arch-test:` target), `Makefile:66` (`test: test-unit
  test-integration e2e-test arch-test`) — the exact existence/chaining
  shape Success Criterion 1 requires the new skill to recognize with no
  finding

### Established Patterns
- `tests/test_arch.py:35-39` — the specific `importlib.util.
  spec_from_file_location` + `module_from_spec` + `exec_module` pattern
  that D-01's target-aware check must NOT conflate with "this file
  imports the module it architecturally checks" — confirmed this load is
  for `tools/setup.py` (inventory-test helpers), unrelated to the file's
  actual architecture-fitness checks against `tools/status-line.py`
- `tests/test_arch.py:87-369` — the file's real architecture checks
  (`check_config_env_in_cfg`, `check_no_typed_model_subscript`,
  `check_bookkeeping_readers`, `check_seg_signature`,
  `check_defaults_data_only`, `check_role_prefix_integrity`,
  `check_no_doctor_symbols`) all operate on an `ast`-parsed tree
  (`_parse(name)` at line 87), never on an imported/executed module —
  this is the part of the file that IS correctly AST-only and must not be
  penalized for the unrelated setup.py load elsewhere in the same file

### Integration Points
- None yet — this skill has no shared-package dependency beyond the
  skill-authoring pipeline; unlike Phases 10/11, no convergence decision
  was needed here since no other skill in the family needs architecture-
  fitness tool knowledge

</code_context>

<specifics>
## Specific Ideas

None beyond the AST-only-scope discovery above — the rest of this phase
is already fully specified by the design spec and ROADMAP success
criteria, leaving little open for vision-level discussion.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 12's scope. The backlog stub's
fuller dependency-direction/layering-boundary enforcement ambition is
explicitly NOT deferred to a future phase by this discussion (it was
already explicitly flagged as an accepted known gap by the design spec
and ROADMAP, not a TODO this milestone owes a future phase).

### Reviewed Todos (not folded)
None — `cross_reference_todos` found the same 3 historical todos
(`resolves_phase: 6/7/8`) already confirmed not live candidates during
Phases 9-11's discussions.

</deferred>

---

*Phase: 12-Architecture Rules Checker (ai-kit-project-rules-arch)*
*Context gathered: 2026-09-13*
