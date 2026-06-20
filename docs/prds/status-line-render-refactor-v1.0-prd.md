# Status-line Render Refactor + Engineering-Standards — PRD

> **Scope.** Lives on its own branch (`refactor/status-line-render`, forked off `feat/e7-loop`
> because it builds on E7's code). It restructures `tools/status-line.py` and adds a real
> validation gate. It is behavior-preserving **except** FR-R.2 (makes `slowest` truthful). The
> branch-icon tweak and the `install.sh` branch-pointing flags are handled separately and
> immediately on `feat/e7-loop`, so they are **out of scope here**.
>
> **Clarified via the requirements-clarity flow (3 decisions locked):** FR-R.2 attribution = **A**
> (de-share + TTL cache); `make validate` baseline = **fix-to-clean first**; pre-commit included.

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
- **FR-R.1** — Unify the build path behind one explicit segment contract and a single measured pass.
- **FR-R.2** — Make `slowest` measure the true per-segment cost (incl. work hidden in `build_data`)
  so it is consistent with `render_time`. **Attribution = de-share + TTL cache (option A).**
- **FR-R.3** — Two-pass render: measure everything first, then assemble lines, placing `render_time`
  and `slowest` in their layout position (lets `slowest` sit next to `render_time`).
- **FR-R.4** — `make validate` (ruff + pylint + pyright + vulture) + a pre-commit config, with the
  two tool modules cleaned to zero violations and type-hinted. **Baseline = fix-to-clean first.**
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
  `shellcheck`/`py_compile`). **Baseline = fix-to-clean:** bring `tools/status-line.py` and
  `tools/setup.py` to **zero** violations and fill the missing/loose type hints first, then enforce
  green on every run / commit. Decide the enforced rule set (sensible defaults; justify any
  `ignore`). Runtime stays stdlib-only; tooling is dev-only and documented next to
  `make test`/`make lint`.

### Design Decisions
- **Stdlib-only runtime preserved**; the refactor restructures, adds no runtime deps.
- **Behavior-preserving except FR-R.2.** A **golden-output test** (same input → same line) guards
  every other segment against accidental change during the restructure.
- **`safe_build` stays the single guarded entry**; never-blank + per-segment crash isolation (the
  `failed` set + doctor) must survive the refactor.
- **Order of work:** validators land **first** (FR-R.4) so the refactor diff is reviewed under the
  new gate, then the measured-pass restructure (FR-R.1/2/3) behind the golden test.

### Risk Assessment
- **Technical:** de-sharing the git probe (A) could regress the single-probe win if the cache key/
  TTL don't make repeat in-render reads free — mitigated by a test asserting one git subprocess per
  render. The restructure could change output — mitigated by the golden-output test.
- **Dependency:** ruff/pylint/pyright/vulture are dev-only; pin versions in the pre-commit config.
- **Schedule:** fix-to-clean is more upfront work than a ratchet; contained by doing it before the
  restructure so it isn't entangled.

## Acceptance Criteria

### Functional Acceptance
- [ ] FR-R.1: one legible measured pass; the contract is explicit and documented in-file; no
      per-segment special cases in the loop body.
- [ ] FR-R.2: `slowest` and `render_time` are consistent (same order of magnitude on a
      representative render); a test asserts no µs-vs-ms mismatch; one git subprocess per render.
- [ ] FR-R.3: `slowest` renders adjacent to `render_time` by default; layout no longer forces it last.

### Quality Standards
- [ ] `make validate` (ruff + pylint + pyright + vulture) green; type hints filled on touched
      modules; `.pre-commit-config.yaml` runs the same set; `make test` + `make lint` still green;
      `--doctor` exit 0; never-blank holds.
- [ ] Golden-output test proves no unintended segment-output change.

### User Acceptance
- [ ] `make validate`/pre-commit documented alongside `make test`/`make lint` (README + Makefile).

## Execution Phases

### Phase 1: Validation gate (FR-R.4)
- [ ] Add `make validate` (ruff, pylint, pyright, vulture) + `.pre-commit-config.yaml` (pinned).
- [ ] Fix `tools/status-line.py` + `tools/setup.py` to zero violations; fill type hints.
- [ ] Document the gate; CI/local parity. **Deliverable:** green `make validate` on a clean tree.

### Phase 2: Measured-pass restructure (FR-R.1 + FR-R.2 + FR-R.3)
- [ ] Land the golden-output test first (snapshot current output for representative inputs).
- [ ] Restructure to the outer/inner measured loop; move data-gathering into segment builds
      (option A), keeping caches; single max-tracking helper; exclude `slowest`/`render_time`.
- [ ] Two-pass assembly; place `slowest` next to `render_time`; drop the "last on line" workaround.
- [ ] Use `/simplify` + `/reducing-entropy`. **Deliverable:** truthful `slowest`, golden test green.

### Phase 3: Verify
- [ ] Full sweep (`make test`/`lint`/`validate`/`--doctor`/never-blank) + a fresh holistic review
      (the E7-loop discipline). **Deliverable:** branch ready to finish.

---

**Document Version**: 1.0
**Created**: 2026-06-20
**Clarification Rounds**: 1 (requirements-clarity: attribution=A, baseline=fix-to-clean, pre-commit=yes)
**Quality Score**: 92/100
