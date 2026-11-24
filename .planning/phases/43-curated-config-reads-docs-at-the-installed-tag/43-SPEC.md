# Phase 43: curated-config reads docs at the installed tag — Specification

**Created:** 2026-11-23
**Ambiguity score:** 0.23 (gate: ≤ 0.20) — gate missed by 0.03; every dimension meets its minimum; written flagged at the owner's choice
**Requirements:** 5 locked

## Goal

curated-config reasons from the open-gsd docs of the installed version (read at its tag, cached per version under `.aikit/`),
offers a project-local update only when the changelog makes it worth it (labeled by impact), asks its questions as one grouped
cascade that replaces today's four, and records a run of each v1 subcommand on a fixture project so the owner can decide, per
command, to keep, merge or remove it.

## Background

Requirements CUR-01, CUR-02 and CUR-10 (REQUIREMENTS.md) and the ROADMAP's Phase 43 criteria 1 to 4. Phase 44 (writes the agreed
settings) follows; this phase owns the reading and asking side.

**The owner's decisions (highest priority):**

- 2026-11-23, answers to this phase's question batch: (1) the cascade replaces the four questions the v2 flow asks today
  (profile, rigor, cross-AI plan review, cross-AI execution); profile and routing become Phase 44 defaults and the single cross-AI
  execution confirmation stays Phase 44's; (2) jev labels changelog entries by impact and rules decide the offer: an offer
  appears for any high or medium entry, without jev a keyword rule gives the same labels and the run says which decided.
- ai-kit never installs or updates GSD itself: a project-local install is an approval-gated follow-up the skill prints (the
  existing `followups` machinery), never `gsd update` and never a write into `~/.claude` (global rules of the owner).
- jev is advisory and never gates; every jev path has a tested no-jev behavior; only summaries go to jev.
- A network read follows the skill's existing network ask (SKILL.md Step 1, lines 79-81).

**Decided by own reasoning on 2026-11-23, the owner may overrule:** the cascade's MVP answer maps onto the existing `recommend`
inputs (rigor), so `recommend` keeps its flags and only the question flow changes; the base branch is detected by GSD's own
resolver through the project's `gsd-tools` and confirmed, not re-implemented.

**Live facts checked for this spec (2026-11-23, this machine):**

- Installed gsd-core is project-local at `.claude/gsd-core`, version 1.22.0 (`runtime-identity`); npm `latest` is 1.23.0 and
  `next` is 1.7.0-rc.6 (`pnpm view @opengsd/gsd-core`, a read-only query). The package's repository is
  `github.com/open-gsd/gsd-core`; the tag `v1.22.0` exists and its root holds `docs/` and `CHANGELOG.md`
  (`gh api repos/open-gsd/gsd-core/contents?ref=v1.22.0`, read-only).
- The installed folder holds `bin/`, `contexts/`, `references/`, `templates/`, `workflows/` and `VERSION`, with no `docs/` and no
  changelog; `references/planning-config.md`, `settings.md` and `settings-advanced.md` document config keys. `bin/lib/
  git-base-branch.cjs` is GSD's own base-branch resolver.
- curated-config has no docs fetcher and no changelog code; `followups.py` builds an approval-gated pinned install command
  (`@opengsd/gsd-core@<version> --<host> --local`) and never an npm dist-tag name.
- The v2 flow's Step 2 asks four questions in one message (`model_profile`, rigor `mvp`/`standard`/`rigorous`, cross-AI plan
  review, cross-AI execution). The kept v1 path (`references/v1-path.md`) uses eleven subcommands: `ensure-project`,
  `apply-profile`, `apply-critical-agents`, `detect-execution-candidate`, `apply-execution`, `detect-review-candidate`,
  `apply-review`, `detect-claude-md-path`, `apply-claude-md-path`, `detect-frontend` and `apply-workflow-defaults` (whether the last
  is also a v2 step was not checked). The ROADMAP's "v1 subcommand list unknown until research" is answered by this list.
- `.aikit/` of this repo holds `brief/`, `config.toml`, `flow.json` and a migrated review file; no cache folder exists.

## Requirements

1. **Open-gsd docs are read at the installed tag and cached per version (CUR-01, part 1)**: curated-config resolves the installed
   gsd-core version through the project's `gsd-tools` and reads the open-gsd docs it needs (the changelog and the pages that
   document the config keys it writes) at the tag `v<version>` of `open-gsd/gsd-core`, after the skill's existing network ask;
   each fetched file is cached under `.aikit/` in a folder named for the version and a later run reads the cache and fetches
   nothing; with no network or no consent it uses the installed `references/` and labels the source as the installed copy, not
   the tagged docs; fetched text is data, never instructions and never executed.
   - Current: no fetcher and no cache; the skill reasons from its own text and the installed workflows.
   - Target: a version-tagged fetcher with a per-version cache and a source label on every claim the skill makes from the docs.
   - Acceptance: fake-fetcher tests: the first run fetches and caches; the second run fetches nothing; a different version uses
     another folder; offline or declined falls back to the installed copy with the label; the cache path stays under `.aikit/`
     and a version string with path characters is refused; a tag that does not exist is reported, not guessed.

2. **A local update is offered only when the changelog makes it worth it (CUR-01, part 2)**: between the installed tag and the
   latest published version, curated-config reads the changelog entries, labels each by impact (high, medium, low) with jev when
   present, and offers the update when any entry is high or medium, showing the labels; without jev a keyword rule gives the same
   labels and the run says which decided; the offer is the project-local pinned install command as an approval-gated follow-up;
   curated-config never runs `gsd update` and never writes into `~/.claude`.
   - Current: no changelog reading; `followups` can print a pinned install command but nothing decides when.
   - Target: a changelog reader, an impact labeler (jev plus a keyword default) and an offer rule.
   - Acceptance: fixtures: a changelog with a security or key-change entry yields a high label and an offer; docs-only entries
     yield low labels and no offer; with jev absent the keyword rule labels and the run says "default"; latest equal to installed
     yields no offer; the offered command is the project-local pinned form with the resolved version; a doc-contract test pins that
     no step runs `gsd update` or writes under `~/.claude`.

3. **The question cascade replaces the four questions (CUR-02)**: the v2 flow asks in one grouped cascade: MVP, UI, granularity
   (beside MVP), runtime (Claude preferred, asking only when another host is detected), and a base branch that GSD's own resolver
   detects and the skill confirms; the four current questions leave the v2 flow; the MVP answer maps onto `recommend`'s existing
   inputs.
   - Current: Step 2 asks `model_profile`, rigor, cross-AI plan review and cross-AI execution in one message.
   - Target: Step 2 lists the cascade in that order; the key names for MVP, UI and granularity come from the tagged docs of
     requirement 1.
   - Acceptance: a doc-contract test pins the five cascade items in order and fails when any of the four old questions returns;
     fixtures: a project with another host detected gets the runtime question and a Claude-only project does not; a detected base
     branch is shown for confirmation; the MVP-to-rigor mapping is pinned by a test; the evals gain one eval for the cascade.

4. **A run of each v1 subcommand is recorded and the owner decides each (CUR-10)**: the eleven v1 subcommands are each run once on
   a fixture project in a scratch directory with a scratch HOME, and the command, exit code, output keys (never a secret) and the
   files it changed are recorded in the phase directory; the owner decides keep, merge into v2 or remove per command and the
   decision is recorded with its date; no v1 code is removed before its run is recorded.
   - Current: the v1 path is kept untested against a recorded run (an owner note says it stays until evidence exists).
   - Target: a run record and a decision record, one row per subcommand.
   - Acceptance: the run record has one row for each of the eleven commands with the four fields; the decision record has one of
     keep, merge or remove for each, dated; a guard test fails when a v1 entry point disappears from `cli.py` without a decision
     row saying remove; no run touched a real host config (scratch HOME).

5. **Every changed SKILL.md meets the judge bar (JDG-04)**: `ai-kit-gsd-curated-config` SKILL.md carries new-shape evals and tests
   and passes the skill-judge loop.
   - Current: the skill carries 6 evals, none for the cascade, the docs read or the update offer.
   - Target: the judged result has no critical or high finding, or grade B or better, and no regression beyond the judge's
     run-to-run variation.
   - Acceptance: the judge record meets the bar of AGENTS.md and `make check-dogfood` validates it; `evals.json` gains one eval
     each for the cascade, the tagged-docs read and the update offer.

## Boundaries

**In scope:**
- The tagged-docs fetcher and cache, the changelog reader and impact labeling, the update offer, the question cascade, the v1 run
  and decision records, docs, evals and the judge loop.

**Out of scope:**
- Writing the agreed settings (profile, routing, models, effort, skills, graph flags): Phase 44.
- Running the update itself, `gsd update`, or any write into `~/.claude`.
- Removing v1 code (this phase records runs and decisions; a removal needs its row first and lands under the decision).
- Docs for hosts other than the installed gsd-core's, caches for versions other than the installed and the latest, and any change
  to the shared jev client.

## Constraints

- Runtime code stays stdlib-only; the fetch uses the network only after the skill's network ask and has a no-network behavior.
- Fetched docs and changelog text are data: never executed, never treated as instructions, size-limited, and read as UTF-8 text.
- The cache lives under `.aikit/` and is never committed by an ai-kit command; ai-kit edits no `.gitignore` of a target project.
- Only summaries go to jev; jev never gates; no jev means the keyword default.
- Tests use fake fetchers, fixture changelogs and a scratch HOME; no test reaches the network or a real host config.
- Every claim the skill makes from the docs carries its source label (tagged docs, installed copy or unverified).

## Acceptance Criteria

- [ ] The first run fetches the tagged docs and caches them under `.aikit/<version folder>`; the second run fetches nothing; offline
  falls back to the installed copy with its label
- [ ] A high or medium changelog entry yields an offer with its labels; docs-only entries yield none; latest equal to installed
  yields none; the command is the project-local pinned form
- [ ] No step runs `gsd update` or writes under `~/.claude`
- [ ] The cascade lists MVP, UI, granularity, runtime and the detected base branch in order; none of the four old questions
  remains; the runtime question appears only when another host is detected
- [ ] The run record has one dated row for each of the eleven v1 subcommands with command, exit code, output keys and changed files
- [ ] The decision record has keep, merge or remove for each; no v1 entry point is removed without its row
- [ ] The changed SKILL.md meets the judge bar of AGENTS.md

## Edge Coverage

**Coverage:** 27/27 applicable edges resolved (13 covered or backstop, 14 dismissed with the owner's approval of 2026-11-23) · 0 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | 🧪 backstop | Held-out fixture: a prerelease or build-suffixed version resolves to its own tag and its own cache folder. |
| empty | R1 | 🧪 backstop | Held-out fixture: no installed version (no `gsd-tools` or an empty VERSION) means no fetch and a stated reason. |
| encoding | R1 | ✅ covered | R1 acceptance: a version string with path characters is refused; fetched text is read as UTF-8 data. |
| ordering | R1 | ⛔ dismissed | Cached files are independent of each other. |
| concurrency | R1 | 🧪 backstop | Held-out fixture: two runs writing the same cache file use a temp file and an atomic replace, so neither reads a half file. |
| boundary | R2 | 🧪 backstop | Held-out fixture: an installed version newer than the latest published one (a local or next build) yields no offer. |
| adjacency | R2 | 🧪 backstop | Held-out fixture: one low entry beside one medium entry still offers; low entries alone do not. |
| empty | R2 | 🧪 backstop | Held-out fixture: an empty changelog range yields no offer. |
| encoding | R2 | 🧪 backstop | Held-out fixture: entries with non-ASCII text and markdown links are labeled as data without error. |
| ordering | R2 | ⛔ dismissed | Each entry is labeled independently; changelog order changes no label. |
| precision | R2 | ✅ covered | R2 acceptance: the offered command is the project-local pinned form with the resolved version and the labels are shown. |
| idempotency | R2 | ⛔ dismissed | Nothing persists between runs; a declined offer is simply offered again while a newer tag exists. |
| concurrency | R2 | ⛔ dismissed | The labeling is read-only and prints once. |
| adjacency | R3 | ⛔ dismissed | The cascade items are independent questions. |
| empty | R3 | ✅ covered | R3 acceptance: a Claude-only project gets no runtime question. |
| encoding | R3 | ⛔ dismissed | Fixed question text; no encoding semantics. |
| ordering | R3 | ✅ covered | R3 acceptance: a doc-contract test pins the cascade order. |
| adjacency | R4 | ⛔ dismissed | Records are one row per command; rows are independent. |
| empty | R4 | 🧪 backstop | Held-out fixture: a v1 detect command with nothing to find records its null output, not an error. |
| ordering | R4 | 🧪 backstop | Held-out fixture: the run follows the v1 path's order with `ensure-project` first. |
| idempotency | R4 | ⛔ dismissed | One run per command is the evidence asked for; rerun behavior is not in scope. |
| concurrency | R4 | ⛔ dismissed | The runs are sequential in one scratch project. |
| adjacency | R5 | ⛔ dismissed | The judge loop is a process over files; no values touch. |
| empty | R5 | ⛔ dismissed | A skill with no change is not judged; the requirement names the changed one. |
| ordering | R5 | ⛔ dismissed | Judge rounds have no order semantics beyond the three-round cap of AGENTS.md. |
| idempotency | R5 | ⛔ dismissed | The judge records are produced once per round. |
| concurrency | R5 | ⛔ dismissed | The judge loop runs per skill under AGENTS.md rules. |

## Prohibitions (must-NOT)

**Coverage:** 6/6 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT run `gsd update` or an installer, and MUST NOT write under `~/.claude` or any user-level config | R2, R4 | resolved | test (doc-contract and a scratch-HOME run that compares file modification times); wired-check descriptor left empty until plan time |
| MUST NOT execute fetched docs or changelog text or follow instructions found in it | R1, R2 | resolved | test (a fixture changelog holding an instruction line changes no behavior) and judgment review; wired-check descriptor left empty until plan time |
| MUST NOT fetch without the skill's network consent, and MUST NOT write the cache outside `.aikit/` | R1 | resolved | test (declined consent means no fetch call; a path-escaping version is refused); wired-check descriptor left empty until plan time |
| MUST NOT remove v1 code before its run is recorded and a decision says remove | R4 | resolved | test (the guard of R4 acceptance); wired-check descriptor left empty until plan time |
| MUST NOT send code, config values or secrets to jev (changelog entry summaries only) | R2 | resolved | test (a seam that records the payload) and judgment review; wired-check descriptor left empty until plan time |
| MUST NOT change today's behavior when jev is absent, errors or answers with low confidence | R2 | resolved | test (no-jev fixture: the keyword default labels and the run says so); wired-check descriptor left empty until plan time |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                           |
|--------------------|-------|------|--------|---------------------------------------------------------------------------------|
| Goal Clarity       | 0.85  | 0.75 | ✓      | tagged docs, update offer, cascade, v1 records                                   |
| Boundary Clarity   | 0.75  | 0.70 | ✓      | Phase 44 owns the writes; removals only per decision row                         |
| Constraint Clarity | 0.68  | 0.65 | ✓      | which docs pages, the cache folder name and the base-branch verb fixed at plan time |
| Acceptance Criteria| 0.75  | 0.70 | ✓      | 7 pass/fail criteria                                                            |
| **Ambiguity**      | 0.23  | ≤0.20| ⚠      | gate missed by 0.03; no dimension below its minimum                              |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

Run mode `interactive`, 1 question round plus the gate question. jev was not asked: in the interactive path it screens only
items the owner asks it to screen. Rule: mvp-mode inactive, the best design wins over the smallest diff.

| Round | Perspective     | Question summary                                                 | jev (advisory) | Decision locked |
|-------|-----------------|------------------------------------------------------------------|----------------|-----------------|
| 1     | Researcher      | What docs, changelog and v1 code exist today?                    | none           | Verified upstream tag and docs; no fetcher; eleven v1 subcommands listed (Background) |
| 1     | Boundary Keeper | Does the cascade replace today's four questions?                 | none           | Replace; profile and routing become Phase 44 defaults (R3) |
| 1     | Simplifier      | How is an update judged worth offering?                          | none           | jev labels entries, rules decide, keyword default without jev (R2) |
| —     | Own reasoning   | MVP answer maps to rigor; base branch from GSD's own resolver    | none           | Recorded in R3. Ledger. |
| gate  | Seed Closer     | Approve the flagged SPEC (0.23), edges and prohibitions?         | none           | Approved and committed flagged (owner, 2026-11-23): 14 dismissals, 13 covered or backstop rows, six prohibitions |

---

*Phase: 43-curated-config-reads-docs-at-the-installed-tag*
*Spec created: 2026-11-23*
*Next step: /gsd-discuss-phase 43 — implementation decisions (fetch mechanism, docs page list, cache folder, labeler, cascade mapping)*
