# Phase 24: Spec-and-discuss chain skill — Specification

**Created:** 2026-10-14
**Ambiguity score:** 0.12 (gate: ≤ 0.20)
**Requirements:** 13 locked

## Goal

ai-kit ships `ai-kit-gsd-spec-discuss`, an installable Agent Skill. It takes a range of GSD
phases through `/gsd-spec-phase N --auto` and then an assumptions-mode `/gsd-discuss-phase`, one
phase at a time:
- gray areas go through an optional, detected decision ladder (local Laya, then TypeSafe
  direct, then the main model's own reasoning);
- every decision is logged;
- non-blocking low-confidence decisions go to a ledger;
- the chain stops only on a blocking question it cannot resolve with high confidence.

## Background

This SPEC encodes what was learned in the tools-installer run of 2026-10-13/14 (session
`0a994334`) and in this milestone's own spec/discuss pass over Phases 16.1–23 on 2026-10-14.
- **The user's flags:** spec `/gsd-spec-phase N --auto`; discuss `/gsd-discuss-phase --analyze
  --all --batch --assumptions N`, "use jev skill and take the approach of best over easy, use
  codegraph to explore current code if needed".
- **The `--assumptions` routing quirk.** In gsd-core 1.16 the literal flag routes to
  `list-phase-assumptions.md`, which writes no files. The user's intent, and what both runs
  actually did, is the assumptions-mode workflow `discuss-phase-assumptions.md` (spawning
  `gsd-assumptions-analyzer`), producing `NN-CONTEXT.md` and `NN-DISCUSSION-LOG.md`.
- **What the ladder looks like in practice.**
  - Laya is often low-confidence (`needs_fallback`).
  - TypeSafe usually settles those.
  - When both are low, the main model's own reasoning against the docs is the deciding rung,
    and the most important one.
  - A high-confidence Laya answer that contradicts verified evidence gets a TypeSafe second
    opinion before it is overridden (Phase 17 K01/K08, Phase 18.1 T2: TypeSafe agreed each
    time).
  - An item with an empty `context` made the whole TypeSafe batch fail with `invalid_input`
    (Phase 18.1).
- **Deferral rule (user, 2026-10-14).** A low-confidence decision that blocks nothing is decided
  provisionally and goes to a ledger, shown at the end, or together with a critical stop.
  Preconditions owned by the user, such as a branch land-or-shelve decision, go there too.
- **Cross-phase amendments are routine.** A live fact found while specifying a later phase
  amended earlier phases in the same commit: `resolve_model_ids: "omit"` (19 → 17, 18) and the
  pi registry (22 → 17).
- **Existing CONTEXT files** from an earlier interactive discuss keep the user's locked
  decisions; only what new facts change is amended, dated.
- **CodeGraph.** In a git worktree, codegraph may resolve to the main checkout's index. Run
  `codegraph sync <worktree>` (or `codegraph init` when `.codegraph/` is missing) first, or treat
  results as hints.
- **Backends:**
  - Laya (local): `JEV_API_URL=http://127.0.0.1:8010/v1/systemone`, `JEV_MODEL=jev-1`,
    `JEV_RESPONSE_MODEL=laya-rl-agent`.
  - TypeSafe: `https://api.typesafe.ai/v1/systemone`, `jev-latest` → `jev-1.13.0`.
    (owner note 2026-10-15, not researched: per the Jev 1.14 notes `jev-latest` moves to
    `jev-1.14.0` about a week after release, so an exact `jev-1.13.0` response-model check would
    start failing; pin `jev-1.13.0` or accept both.)
  - The jev client script ships with the `jev-fast-decision` skill.
- **The prototype** `jev_ladder.py` (session scratchpad) hardcoded a key-file path; the shipped
  script must not.
- `workflow.mvp_mode` lives in `.planning/config.json` (the user said "settings.json"); it is
  unset in ai-kit.

## Requirements

1. **Skill identity**.
   - Current: none.
   - Target: `skills/ai-kit-gsd-spec-discuss/` follows the Agent Skills standard (`SKILL.md` with `name` and a trigger-rich `description`, plus `scripts/` and `references/`). Host-specific steps (subagent spawning) are written host-agnostically, with Claude Code named only as an example, and any gap is flagged.
   - Acceptance: the installer links it with no script change, and `/skill-judge` passes (R13).

2. **Range selection** (SDC-01).
   - Current: none.
   - Target:
     - The skill accepts `--from N --to M` or a list.
     - With neither, it reads ROADMAP and STATE and proposes the not-yet-discussed range: phases with no CONTEXT, or a SPEC newer than the CONTEXT.
     - It asks once. That single question also carries the remote-backend consent (R6) when consent is not already recorded.
   - Acceptance: fixtures for an explicit range, a list, and none (the proposal matches the rule), with exactly one question.

3. **Spec step** (SDC-01).
   - Current: manual.
   - Target:
     - Per phase, `/gsd-spec-phase N --auto` runs. An existing SPEC is reused, as the workflow does.
     - The edge-coverage floor is computed with gsd-core's `edge-probe.cjs` over the SPEC's requirements and never hand-written. `unclassified` rows stay ⚠ UNRESOLVED.
     - Open interview items go through the ladder (R5).
   - Acceptance: a dry-run transcript on a fixture project shows the engine call, and the SPEC's Edge Coverage rows equal the engine floor plus any rows the author added, each marked as added.

4. **Discuss step** (SDC-01).
   - Current: manual.
   - Target:
     - Per phase, the assumptions-mode discuss runs `discuss-phase-assumptions.md` with the analyze/all/batch behavior and writes `NN-CONTEXT.md` and `NN-DISCUSSION-LOG.md`. It never takes the literal `--assumptions` route, which writes no files.
     - An existing CONTEXT keeps every user-locked decision; changes are dated amendments.
     - Each discuss is committed through `gsd-tools query commit`, followed by `state.record-session`.
   - Acceptance: on a fixture with a prior CONTEXT, the locked decisions survive verbatim and the amendments are dated. Both files exist after the run.

5. **Decision ladder script** (SDC-02).
   - Current: an untracked prototype.
   - Target: `scripts/decide.py` (stdlib only) does the whole ladder:
     - it detects the backends: Laya by a TCP reachability check of a configured local URL (an env variable; no default URL is probed, because the jev skill has no health endpoint and its built-in default is remote Zen; 18 D-36); TypeSafe by a key present by name (`JEV_API_KEY`, or a key file named by an env variable or ai-kit's secrets file); the jev skill by its install;
     - it validates every item (non-empty `instructions`, `context`, 2+ criteria);
     - it sends one item per call to Laya, and batches `needs_fallback` or errored items to TypeSafe;
     - a `--second-opinion` mode sends chosen items to TypeSafe directly;
     - it calls the installed jev client script and never copies its protocol;
     - it prints one JSON result with each backend's choice, top probability and fallback flag.
   - Acceptance: tests with a fake jev client cover each detection combination, the validation error, the batch fallback, the second-opinion mode, and that no key value ever appears in output.

6. **Consent and data** (SDC-02).
   - Current: n/a.
   - Target: a remote backend is called only with standing consent, recorded once (R2) or already present. Items carry summaries only, never source code, secrets or file contents. With no backend, every decision falls to the main model's reasoning and the chain still completes.
   - Acceptance: a no-backend fixture completes with "own reasoning" in every row, and a test asserts that no remote call happens without consent.

7. **Decision logging** (SDC-03).
   - Current: manual.
   - Target:
     - Each decision row records one column per backend used, the locked decision and its reason. This applies in the SPEC Interview Log and in the DISCUSSION-LOG.
     - A model answer contradicted by the docs or by verified evidence is overridden, and the override is logged with its evidence. A high-confidence contradicting Laya answer first gets a TypeSafe second opinion.
   - Acceptance: SKILL.md's table format matches the rows this milestone produced. A worked example shows an override and a second opinion.

8. **Ledger and stop rule** (SDC-03).
   - Current: manual.
   - Target:
     - A low-confidence decision that blocks nothing is decided provisionally and appended to a run ledger, together with user-owned preconditions.
     - The chain stops only on a decision that blocks others and cannot be resolved with high confidence. It shows that question together with the ledger.
     - At the end it prints the ledger.
   - Acceptance: the SKILL.md decision table covers blocking/non-blocking × high/low confidence. A fixture shows a provisional item reaching the end-of-run ledger.

9. **Quality rule** (SDC-04).
   - Current: n/a.
   - Target:
     - Without `workflow.mvp_mode: true`, the best design wins over the smallest diff.
     - With it, the simpler design wins as long as it does not lower what reaches the product's user.
     - Ponytail findings inform how code is written, not which design wins.
     - The rule goes into every analyzer brief.
   - Acceptance: SKILL.md reads `workflow.mvp_mode` through `gsd-tools config-get` and states both branches. The analyzer brief template contains the rule.
   - *Amended 2026-10-14 (24 D-16):* the mode is read through the engine's `gsd-tools query phase.mvp-mode <N>` (flag, then ROADMAP `**Mode:** mvp`, then `workflow.mvp_mode`, then false), with `config-get workflow.mvp_mode --default false --raw` as the fallback; a bare `config-get` exits "Key not found" when unset.

10. **CodeGraph in every brief**.
    - Current: manual.
    - Target: every spawned subagent prompt says it can use CodeGraph:
      - `codegraph sync <path>`, or `codegraph init <path>` when `.codegraph/` is missing;
      - then `codegraph explore` or the `codegraph_explore` MCP tool;
      - in a worktree, index the worktree first or treat results as hints.

      The paragraph is omitted when the `codegraph` binary is absent.
    - Acceptance: the brief template has the paragraph behind a presence check.

11. **Live facts and cross-phase amendments**.
    - Current: manual.
    - Target: claims a decision depends on are live-verified first (installed tools, configs in a scratch dir). A fact that contradicts an earlier phase's SPEC, CONTEXT, REQUIREMENTS or ROADMAP amends them in the same commit, dated. A coupling found during one phase is handed to the coupled phase's discuss.
    - Acceptance: SKILL.md has the amendment step, with this milestone's two examples as references.

12. **Pacing**.
    - Current: manual.
    - Target: the next phase's analyzer may run in the background while the current SPEC is written, when the coupling is low; the brief names any coupling. No result is used before its notification arrives.
    - Acceptance: SKILL.md states the rule and the coupling note.

13. **Registration and gates** (SDC-04).
    - Current: none.
    - Target: there is a README row. `scripts/decide.py` is in every gate (tests, pyright, vulture, pylint, per 16.1's regexes). `/skill-judge` ≥ 96/120 with no Critical/Important finding. `make test` and `make validate` are green.
    - Acceptance: all of these pass. The skill-judge evidence file is committed.

## Boundaries

**In scope:**
- The skill, its ladder script, the brief template, the references (log formats, decision table, worked examples), its tests and registration

**Out of scope:**
- Changing gsd-core's `--assumptions` routing (upstream); the skill works around it
- Running plan/execute phases
- Installing jev-fast-decision, Laya or any backend (the user's machine setup)

## Constraints

- Runtime code is stdlib-only, with no hardcoded machine paths.
- No secret value in any output, log or ledger; keys are checked by name.
- Portable across Agent Skills hosts; host-specific gaps are flagged, not silently degraded.
- (owner note 2026-10-15, not researched) Jev is no longer text-only. Images are accepted with
  the `TypeSafe-Danger-Zone-Images: true` header and an `assets` map; 1.14 adds a `box` type and
  long context; `confidence` is not claimed calibrated. This phase's ladder stays text-only;
  required reading before extending it: [Jev 1.14 release notes](https://typesafe.ai/blog/jev-1-14), [Primitives](https://docs.typesafe.ai/primitives), [Images](https://docs.typesafe.ai/images), [Confidence](https://docs.typesafe.ai/confidence).

## Acceptance Criteria

- [ ] The skill links with no installer change and passes `/skill-judge` ≥ 96/120
- [ ] Range selection works for an explicit range, a list and none, with one question
- [ ] The spec step uses the engine floor for Edge Coverage
- [ ] The discuss step writes CONTEXT and DISCUSSION-LOG and keeps locked decisions
- [ ] `decide.py` detection, validation, fallback and second opinion are tested; no key in output
- [ ] No remote call without consent; a no-backend run completes
- [ ] Decision rows carry the backend columns, overrides and second opinions
- [ ] Provisional items reach the end-of-run ledger; stops happen only on blocking unresolvable items
- [ ] The quality rule reads `workflow.mvp_mode`
- [ ] The CodeGraph paragraph appears only when codegraph is present
- [ ] `make test` and `make validate` are green
- [ ] MUST NOT: no source code, secret or file content is sent to a decision backend
- [ ] MUST NOT: the chain never stops on a non-blocking question

## Edge Coverage

**Coverage:** 39/40 applicable edges resolved · 1 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| empty | R1 | ✅ covered | A SKILL.md without a trigger-rich description fails skill-judge's description check |
| encoding | R1 | 🧪 backstop | SKILL.md frontmatter is plain YAML per the standard |
| adjacency | R2 | ✅ covered | A phase whose SPEC and CONTEXT share a timestamp counts as discussed |
| empty | R2 | ✅ covered | Nothing left to discuss: the skill says so and stops without asking |
| ordering | R2 | ✅ covered | Phases run in ROADMAP order, decimals in numeric order (16.1 after 16) |
| adjacency | R3 | ✅ covered | An existing SPEC is reused, never regenerated, in auto mode |
| empty | R3 | ✅ covered | A SPEC with zero applicable edges triggers the engine's warning, which is recorded |
| ordering | R3 | ✅ covered | The engine runs after the ambiguity gate, as in the workflow |
| adjacency | R4 | ✅ covered | An amendment that touches a locked decision is dated and marked as a refinement, never a replacement |
| empty | R4 | ✅ covered | No prior CONTEXT: a new one is written |
| ordering | R4 | ✅ covered | CONTEXT and LOG are committed before `state.record-session` |
| concurrency | R4 | 🧪 backstop | One phase at a time; a background analyzer for the next phase writes nothing |
| adjacency | R5 | ✅ covered | An errored Laya answer goes to the TypeSafe batch like `needs_fallback` |
| empty | R5 | ✅ covered | An item with an empty `context` is rejected before any call |
| encoding | R5 | ✅ covered | Output is JSON; keys never appear (asserted) |
| ordering | R5 | ✅ covered | Laya runs before TypeSafe, one item per Laya call |
| concurrency | R5 | 🧪 backstop | Calls are sequential |
| adjacency | R6 | ✅ covered | Consent for TypeSafe does not imply consent for another remote backend |
| empty | R6 | ✅ covered | No backend: every row says own reasoning, and the chain completes |
| ordering | R6 | ✅ covered | Consent is asked in the single range question, before any remote call |
| concurrency | R6 | 🧪 backstop | No parallel remote calls |
| adjacency | R7 | ✅ covered | A second opinion that agrees with Laya is logged as confirmation, not override |
| empty | R7 | ✅ covered | A decision with no backend shows dashes in the backend columns |
| ordering | R7 | 🧪 backstop | Rows follow the order items were decided |
| adjacency | R8 | ✅ covered | A low-confidence item that blocks exactly one later item counts as blocking |
| empty | R8 | ✅ covered | An empty ledger prints 'no deferred items' |
| ordering | R8 | ✅ covered | The ledger is printed after the last phase, or with the critical stop |
| adjacency | R9 | ✅ covered | `mvp_mode: false` behaves like unset |
| empty | R9 | ✅ covered | An absent config key means the best-design branch |
| ordering | R9 | 🧪 backstop | The rule is in the brief before the analysis points |
| adjacency | R10 | ✅ covered | `.codegraph/` present but stale: `sync`, not `init` |
| empty | R10 | ✅ covered | No codegraph binary: the paragraph is omitted |
| ordering | R10 | ✅ covered | Index first, then explore |
| unclassified | R11 | ⚠ UNRESOLVED | No shape cue; the amendment step is specified with examples |
| empty | R12 | ✅ covered | No next phase: no background analyzer |
| encoding | R12 | 🧪 backstop | Brief text is plain English Markdown |
| adjacency | R13 | ✅ covered | `decide.py` is matched by the gates' regexes, with no per-file list |
| empty | R13 | ✅ covered | Without the jev skill installed, tests still pass (fake client) |
| ordering | R13 | 🧪 backstop | skill-judge runs after the last SKILL.md edit |
| concurrency | R13 | 🧪 backstop | Tests run under the parallel runner, one module per process |

## Prohibitions (must-NOT)

**Coverage:** 3/3 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT send source code, secrets or file contents to a decision backend | R5, R6 | resolved | test (payload schema rejects non-summary fields) and judgment |
| MUST NOT call a remote backend without standing consent | R6 | resolved | test |
| MUST NOT print or log a key value | R5 | resolved | test |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.92  | 0.75 | ✓      | One skill, one script |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | No upstream changes, no installs |
| Constraint Clarity | 0.85  | 0.65 | ✓      | Consent, summaries, no paths |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | 13 pass/fail criteria |
| **Ambiguity**      | 0.12  | ≤0.20| ✓      | Initial 0.18; one round |

## Interview Log

`--auto`, one round. jev-fast-decision screened the open items (Laya first; `needs_fallback` to TypeSafe direct). Summaries only, advisory. Rule: best design over the smallest diff.

| Round | Perspective | Question summary | Laya (advisory) | TypeSafe (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Simplifier | The skill's name? | ai-kit-gsd-phase-prep 0.46 (fb) | ai-kit-gsd-spec-discuss 0.89 | `ai-kit-gsd-spec-discuss` (R1) |
| 1 | Boundary Keeper | How is the ladder implemented? | prose_only 0.44 (fb) | wrapper_script 0.98 | R5: a stdlib wrapper that calls the installed jev client |
| 1 | Researcher | How is TypeSafe detected without a machine path? | – | – | By name: `JEV_API_KEY`, an env-named key file or ai-kit's secrets file (consistent with 18 R11) |
| 1 | Failure Analyst | Consent for remote calls? | – | – | Recorded once, inside the single range question (R2, R6) |

---

*Phase: 24-spec-and-discuss-chain-skill*
*Spec created: 2026-10-14*
*Next step: /gsd-discuss-phase 24 — implementation decisions (how to build what's specified above)*
