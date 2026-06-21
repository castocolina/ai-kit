# Status-line Render Refactor + Engineering-Standards — PRD

> **Scope.** Lives on its own branch (`refactor/status-line-render`, forked off `feat/e7-loop`
> because it builds on E7's code). It restructures `tools/status-line.py`, normalizes icon→text
> spacing, and adds a real validation gate. It is behavior-preserving **except** FR-R.2 (makes
> `slowest` truthful) and FR-R.5 (corrects collapsed icon spacing). The branch-icon tweak and the
> `install.sh` branch-pointing flags are handled separately and immediately on `feat/e7-loop`, so
> they are **out of scope here**.
>
> **Clarified via the requirements-clarity / brainstorming flow:** FR-R.2 attribution = **A**
> (de-share + TTL cache); `make validate` baseline = **fix-to-clean, split across phases** (a
> report-only ruleset/triage spike first — FR-R.0 — then structure-independent fixes in Phase 1 and
> the final zero-sweep after the restructure, to avoid suppression litter); pre-commit included;
> icon-spacing normalization added as **FR-R.5** (shared `_icon` helper + VS16 force-wide).

## Requirements Description

### Background
- **Business problem.** `tools/status-line.py` grew feature-by-feature (E4–E7) into a large single
  file. Two concrete symptoms surfaced in review:
  1. The `slowest` segment reports microseconds while `render_time` reports tens of milliseconds —
     ~1000× apart — because they measure different phases. The diagnostic meant to answer "which
     segment dominated render time?" never names the real cost (FR-R.2).
  2. The build/measure path is split across `build_data` (shared probes, once) and `pack_line`
     (per-line builders), with timing bolted onto the second phase only. There is no single,
     legible "for each segment: gated, measured, built" pass. Type hints are missing/loose; there
     is no static analysis beyond `shellcheck` + `py_compile`.
- **Target users.** ai-kit maintainers (legibility, safe change) and end users (a trustworthy
  `slowest` readout to tune their line).
- **Value.** A render path that reads like intentional engineering, a truthful diagnostic, and a
  `make validate` + pre-commit gate that keeps it that way.

### Feature Overview
- **FR-R.0** — Report-only lint **ruleset & triage spike**: decide the enforced rule set (with a
  justification per `ignore`/`disable`) and triage every current finding as *fix-now
  (structure-independent)* · *fixed-by-refactor* · *legitimately-suppress*, so fix-to-clean is a
  deliberate decision rather than a mechanical sweep that breeds suppressions.
- **FR-R.1** — Unify the build path behind one explicit segment contract and a single measured pass.
- **FR-R.2** — Make `slowest` measure the true per-segment cost (incl. work hidden in `build_data`)
  so it is consistent with `render_time`. **Attribution = de-share + TTL cache (option A).**
- **FR-R.3** — Two-pass render: measure everything first, then assemble lines, placing `render_time`
  and `slowest` in their layout position (lets `slowest` sit next to `render_time`).
- **FR-R.4** — `make validate` (ruff + pylint + pyright + vulture) + a pre-commit config, with the
  two tool modules cleaned to zero violations and type-hinted. **Baseline = fix-to-clean, split:**
  tooling + ruleset + structure-independent fixes in Phase 1; the final zero-sweep after the Phase 2
  restructure (so structural violations are erased by the refactor, not suppressed on doomed code).
- **FR-R.5** — Normalize icon→text spacing so no segment renders its glyph flush against its text;
  one rule encoded once, width-correct.
- **Boundaries.** No change to the output a correct config produces, except FR-R.2 (truthful
  numbers). Status line stays **stdlib-only at runtime**; validators/pre-commit are dev-only.
  **Out of scope:** the `branch` icon and `install.sh` flags (done on `feat/e7-loop`).

### The contract (today — to be made explicit, not invented)
- Built-in segment: `seg_<name>(data, avail, theme)` in `BUILDERS` (`status-line.py:1144`); default
  on/off in `SEGMENTS[name]` (`:33`); referenced by `name` in `LAYOUT` lines (`:58`); gated by
  `cfg.segments.get(name, False)`.
- External segment: a provider file discovered by `discover_external` (`:423`), keyed by header
  `id=`, **default-ON** (`seg_defaults.setdefault(s.id, True)`, `:262`), disabled via
  `[segments] <id> = false` or `CC_AI_KIT_SEGMENT_<ID>=0`. `_builders_for(cfg)` (`:1165`) merges
  built-in + external into one `name -> builder` map; `safe_build(key, …)` (`:1577`) is the single
  guarded build entry (sets the `failed` set on a raise; preserves the never-blank invariant).
- So a unified builder map and a single guarded build call **already exist**. What's missing: the
  expensive work doesn't all flow through them, and measurement sits in the wrong phase.

### Detailed Requirements

#### FR-R.0 — Lint ruleset & triage spike (report-only) · **DECIDED**
- **Why.** Fix-to-clean on the current monolithic `status-line.py` would surface a large share of
  findings that are **artifacts of the structure FR-R.1/2/3 deletes** (`too-many-branches`/
  `too-many-locals` in `pack_line`, `build_data` complexity, vulture "unused" on the shared-probe
  split). Fixing those now means doing the restructure twice; silencing them means a `# noqa` /
  `# pylint: disable` carpet. The spike prevents both.
- **Deliverable (no production code):** run ruff + pylint + pyright + vulture **report-only** over
  `tools/` (+ `tests/`) and produce (a) the **enforced ruleset** — what's on, with a one-line
  justification for every `ignore`/`disable`; (b) a **triaged finding inventory** tagging each as
  *fix-now (structure-independent)* · *fixed-by-refactor* · *legitimately-suppress (justified)*.
- **Acceptance.** The ruleset and the triaged inventory exist and are reviewed before any
  fix-to-clean edit; the *legitimately-suppress* list is short and each entry carries a reason.

#### FR-R.1 — One segment contract, one measured pass · **DECIDED**
- **Target shape:** an outer loop over `LAYOUT` lines, an inner loop over each line's components.
  Per component: gate on `cfg.segments.get(name, False)` (built-in **or** external — same gate);
  only if active, **measure** the build via `safe_build` and track the running max `(name, ns)` in
  one place (a single helper, not scattered conditionals). `slowest` and `render_time` are the only
  segments excluded from the measured loop.
- **Legibility goals:** the contract (built-in + external gate, `seg_<name>`, `LAYOUT` names,
  `safe_build`, `failed`-set crash isolation) is documented in-file; no per-segment special cases
  in the loop body.

#### FR-R.2 — Truthful `slowest` via de-share + TTL cache (option A) · **DECIDED**
- **Problem.** `render_time` (`:1047`) spans the whole render; `slowest` (`:1056`) times only the
  `pack_line` `safe_build` bracket (`:1622`) — formatting + cache-hit external calls (µs). The
  dominant ms (git status, transcript parse, RSS, cache-miss provider exec) live in `build_data`
  (`:1766`), unmeasured per-segment. Hence the ~1000× mismatch.
- **Decision (A).** Stop pre-gathering shared inputs in a separate `build_data` phase. Each segment
  gathers the data it needs **inside its own measured build**, so the cost is captured by the same
  `safe_build` timing bracket. The shared probes keep their TTL/cache (`git_snapshot`'s cache,
  `run_external`'s TTL cache), so the 2nd/3rd consumer of the same probe is a cache hit (cheap) and
  the **first** consumer is credited with the real cost. Net effect: `slowest` names a segment whose
  time is the same order of magnitude as the dominant render cost.
- **Caveats to handle in design:** (a) the git probe is shared by branch/dirty/worktree — confirm
  the cache key + TTL make repeat calls within one render free (they read from the just-written
  cache); (b) first-caller attribution skew is acceptable and should be noted in-code; (c) preserve
  the "disabled segment costs nothing to compute" property (the gate must still short-circuit the
  probe when its segment is off).
- **Acceptance.** On a render where `render_time` is N ms, `slowest` names a real contributor of the
  same order of magnitude (no µs-vs-ms mismatch); a test asserts the relationship on a
  representative render.

#### FR-R.3 — Two-pass render; `slowest` next to `render_time` · **DECIDED**
- After the measured pass populates the max and timings, a **second** traversal assembles the output
  lines, inserting `render_time` and `slowest` at their `LAYOUT` positions. Removes the current
  "`slowest` must be last on its line" constraint (a T3.4 workaround needed only because timing
  happens during assembly today). Default layout then places **`slowest` adjacent to `render_time`**.

#### FR-R.4 — `make validate` + pre-commit + type hints (fix-to-clean) · **DECIDED**
- Add a `validate` make target running **ruff**, **pylint**, **pyright**, **vulture** over `tools/`
  and `tests/`, and a `.pre-commit-config.yaml` running the same set (plus the existing
  `shellcheck`/`py_compile`). **Baseline = fix-to-clean, split (per FR-R.0):** the enforced rule set
  comes from the FR-R.0 spike (sensible defaults; justify any `ignore`). In **Phase 1**, apply only
  the *structure-independent* fixes and type hints; defer the *fixed-by-refactor* findings. In
  **Phase 2**, after the restructure erases those structural violations, run the **final zero-sweep**
  so `tools/status-line.py` and `tools/setup.py` reach **zero** violations — by removal, not
  suppression — and enforce green on every run / commit thereafter. Runtime stays stdlib-only;
  tooling is dev-only and documented next to `make test`/`make lint`.

#### FR-R.5 — Icon→text spacing normalization · **DECIDED**
- **Problem.** Five iconed segments emit the glyph flush against the value — `seg_clock`
  (`⏰{clock}`), `seg_lines` (`📃{…}`), `seg_cost` (`🪙${…}`), `seg_total_time` (`💬{…}`),
  `seg_api_time` (`📡{…}`) — while the rest use `glyph + " "`. The icon visually "collapses" into
  the text. `seg_todo` additionally hand-pads `⏸  ` with two spaces because `⏸` (U+23F8) renders
  **narrow** on many terminals though our width model treats it as wide.
- **Decision (shared helper + VS16 force-wide):**
  - Add `_icon(glyph, text)` that every iconed segment routes through, emitting the glyph + exactly
    **one** space. No per-segment spacing literals remain.
  - The glyphs we model as wide (`_WIDE_BMP`) but that render **narrow** bare — `⏱` (EAW=N),
    `⏸` (N), `⚡` (A); `⏰` is already EAW=W — get the **VS16 emoji-presentation selector**
    (`U+FE0F`) appended so they render wide everywhere and the single-space gap is one clean column.
    Curated set: `_ICON_VS16 = {"⏱", "⏸", "⚡"}`.
- **Required companion fix.** `char_width` currently returns **1** for `U+FE0F`, so `glyph+VS16`
  would measure as **3** cells and inflate the width budget (premature truncation/hide). Extend
  `char_width` to count variation selectors `U+FE00..U+FE0F` as **0** — a latent-correctness fix in
  its own right. After it, `visible_width("⏸️ x") == 4` (2+0+1+1).
- **Scope.** Stdlib-only preserved (VS16 is just a codepoint). Non-iconed segments (`path`,
  `branch`, `dirty`, `model`, `dimensions`) unchanged. External drop-in segments format themselves
  and are unaffected; documenting `_icon` as their convention is **out of scope** here.
- **Sequencing.** Lands in **Phase 1** (small, self-contained, reviewed under the new gate) so the
  Phase 2 golden snapshot captures already-corrected output and the restructure stays
  behavior-preserving against it.
- **Acceptance.** No `seg_*` icon output places a non-space immediately after its glyph (a test
  asserts the separator); `char_width("️") == 0`; golden-output test green against the
  post-FR-R.5 baseline.

### Design Decisions
- **Stdlib-only runtime preserved**; the refactor restructures, adds no runtime deps.
- **Behavior-preserving except FR-R.2 and FR-R.5.** A **golden-output test** (same input → same
  line) guards every other segment against accidental change during the restructure. The golden
  baseline is snapshotted **after** FR-R.5 so it captures corrected icon spacing.
- **`safe_build` stays the single guarded entry**; never-blank + per-segment crash isolation (the
  `failed` set + doctor) must survive the refactor.
- **Order of work:** the ruleset/triage spike (FR-R.0) **first**; then in Phase 1 the validators +
  pre-commit + structure-independent fixes land *with* the icon-spacing fix (FR-R.5), so the
  refactor diff is reviewed under the new gate and the golden baseline is already correct; then the
  measured-pass restructure (FR-R.1/2/3) behind the golden test; then the **final** fix-to-clean
  zero-sweep on the restructured code, so structural violations are erased by the refactor rather
  than suppressed.

### Risk Assessment
- **Technical:** de-sharing the git probe (A) could regress the single-probe win if the cache key/
  TTL don't make repeat in-render reads free — mitigated by a test asserting one git subprocess per
  render. The restructure could change output — mitigated by the golden-output test.
- **Dependency:** ruff/pylint/pyright/vulture are dev-only; pin versions in the pre-commit config.
- **Schedule:** fix-to-clean is more upfront work than a ratchet; contained by the FR-R.0 spike +
  split (structure-independent fixes in Phase 1, the rest erased by the restructure and swept clean
  in Phase 2) so it isn't entangled and doesn't breed suppressions on doomed code.
- **Suppression litter (FR-R.0/R.4):** turning the linters on the pre-refactor monolith could
  pressure `# noqa`/`disable` carpets — mitigated by triaging structural findings as
  *fixed-by-refactor* and deferring them to the Phase 2 zero-sweep rather than silencing them.

## Acceptance Criteria

### Functional Acceptance
- [ ] FR-R.0: enforced ruleset (with justified ignores) + triaged finding inventory exist and are
      reviewed before any fix-to-clean edit.
- [ ] FR-R.1: one legible measured pass; the contract is explicit and documented in-file; no
      per-segment special cases in the loop body.
- [ ] FR-R.2: `slowest` and `render_time` are consistent (same order of magnitude on a
      representative render); a test asserts no µs-vs-ms mismatch; one git subprocess per render.
- [ ] FR-R.3: `slowest` renders adjacent to `render_time` by default; layout no longer forces it last.
- [ ] FR-R.5: no `seg_*` icon output places a non-space immediately after its glyph (test asserts
      the separator); `char_width("️") == 0`; the five collapsers and `seg_todo`'s ad-hoc pad are
      replaced by `_icon(...)`.

### Quality Standards
- [ ] `make validate` (ruff + pylint + pyright + vulture) green; type hints filled on touched
      modules; `.pre-commit-config.yaml` runs the same set; `make test` + `make lint` still green;
      `--doctor` exit 0; never-blank holds.
- [ ] Golden-output test proves no unintended segment-output change.

### User Acceptance
- [ ] `make validate`/pre-commit documented alongside `make test`/`make lint` (README + Makefile).

## Execution Phases

### Phase 0: Ruleset & triage spike (FR-R.0)
- [ ] Run ruff + pylint + pyright + vulture **report-only** over `tools/` (+ `tests/`).
- [ ] Decide the enforced ruleset (justify each `ignore`/`disable`); produce the triaged finding
      inventory (*fix-now* · *fixed-by-refactor* · *legitimately-suppress*).
- [ ] **Deliverable:** reviewed ruleset + inventory; no production-code edits yet.

### Phase 1: Validation gate + icon spacing (FR-R.4-partial + FR-R.5)
- [ ] Add `make validate` (ruff, pylint, pyright, vulture) + `.pre-commit-config.yaml` (pinned),
      using the FR-R.0 ruleset.
- [ ] FR-R.5: add `_icon(...)` + `_ICON_VS16`, route all iconed segments through it, replace the
      five collapsers and `seg_todo`'s ad-hoc pad; extend `char_width` to treat `U+FE00..U+FE0F`
      as zero-width.
- [ ] Apply only the **structure-independent** fixes from the inventory (type hints, imports,
      naming, real dead code); fill type hints on touched code.
- [ ] Document the gate; CI/local parity. **Deliverable:** `make validate` green except for the
      explicitly-deferred *fixed-by-refactor* findings; icon spacing corrected.

### Phase 2: Measured-pass restructure + final cleanup (FR-R.1 + FR-R.2 + FR-R.3 + FR-R.4-final)
- [ ] Land the golden-output test first (snapshot output — already icon-corrected — for
      representative inputs).
- [ ] Restructure to the outer/inner measured loop; move data-gathering into segment builds
      (option A), keeping caches; single max-tracking helper; exclude `slowest`/`render_time`.
- [ ] Two-pass assembly; place `slowest` next to `render_time`; drop the "last on line" workaround.
- [ ] Final fix-to-clean **zero-sweep** on the restructured code (the *fixed-by-refactor* findings
      should now be gone, not suppressed); `make validate` fully green.
- [ ] Use `/simplify` + `/reducing-entropy`. **Deliverable:** truthful `slowest`, golden test green,
      zero violations with a short, justified suppression list.

### Phase 3: Verify
- [ ] Full sweep (`make test`/`lint`/`validate`/`--doctor`/never-blank) + a fresh holistic review
      (the E7-loop discipline). **Deliverable:** branch ready to finish.

---

**Document Version**: 1.1
**Created**: 2026-06-20
**Updated**: 2026-06-20 (brainstorming: added FR-R.0 ruleset/triage spike + FR-R.5 icon-spacing
normalization; split fix-to-clean across phases to avoid suppression litter)
**Clarification Rounds**: 2 (requirements-clarity: attribution=A, baseline=fix-to-clean,
pre-commit=yes · brainstorming: icon helper+VS16, FR-R.0 spike, split cleanup)
**Quality Score**: 92/100
