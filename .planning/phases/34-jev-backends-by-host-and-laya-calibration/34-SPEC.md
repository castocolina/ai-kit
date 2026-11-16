# Phase 34: jev backends by host and Laya calibration — Specification

**Created:** 2026-11-14
**Ambiguity score:** 0.13 (gate: ≤ 0.20)
**Requirements:** 9 locked

## Goal

jev-fast-decision picks its backend per host from ai-kit's `config.toml` (`[jev]`), with Laya at whatever address the
user configures and the home-file key strictly last; before relying on a Laya it learns which version runs at that
address and what that version can do, fetching Laya's published capabilities or changelog once when that is not yet
known; it uses TypeSafe remotely the way the official `typesafe-ai` skill teaches, aware of what the remote can do;
Laya's accuracy is measured against its floor on the version the owner runs; and a knob turns jev off for every skill.

## Background

Requirements JEV-01, JEV-03, JEV-07, JEV-10, JEV-11 (REQUIREMENTS.md "jev"), plus JEV-12 and JEV-13 added for this
spec. Phase 33 provides the layered `config.toml` reader and the reserved `[jev]` table (33 D-03, D-22).

**The owner's decisions (2026-11-14, highest priority):**

- Learn from the official `typesafe-ai` skill's remote usage and apply that kind of use in our skill: be aware of what
  can be done.
- Before jev itself is involved, for Laya: find Laya's information and capabilities on its page; an initial web fetch
  of the page where Laya publishes its capabilities or changelog is cheap.
- Nothing is delegated to tools-installer. The owner already upgraded Laya to the next version in the `llm-env`
  repository; this phase does not upgrade Laya. What matters to the skill is to check which version the Laya it talks
  to runs. Laya is on localhost today but may live at another address, so: at this address there is this version; if
  what it can do is not known at that point, consult it and its changelog, and see how it can help from there.
- Remove the Zen fallback if the skill still mentions it.

**From the 2026-11-07 transcript (kept unless contradicted above):** probe before calling with a cache and a warning
on change; the Laya MCP server stays out of the decision path; the skill states that a confident Laya answer is not
proven accurate; our skill owns the decision ladder, consent, one item per call, receipts and the GSD integration,
while the official skill owns the docs flow and question writing (JEV-08, JEV-09 done in Phase 32.1). Superseded by the
owner's words: "upgrade Laya 0.4.2 → 0.4.27 before calibrating" (JEV-03) and the fixed 24-hour cache with a separate
7-day `--check-updates` (JEV-10) become the version-keyed "unknown → fetch once" flow below.

Live facts checked for this spec (2026-11-14):

- **Laya over HTTP** (`http://127.0.0.1:8010`, after the owner's upgrade): `/openapi.json` reports `laya-serve`
  version `0.1.0` (the serve API, not the package) and routes `/health`, `/v1/route`, `/v1/systemone`,
  `/v1/systemone/batch`; `/health` returns `status`, `loaded`, `revisions`, `device` and idle fields and no version;
  `/version`, `/v1/version`, `/v1/models` are 404. The package version is not exposed over HTTP; on 2026-11-07 it was
  read only inside the container (`pip show laya`).
- **Where Laya publishes**: PyPI `laya` (Convai Innovations; release notes in its JSON and README) and the GitHub
  repository `NandhaKishorM/laya` (README "What's new"); no official Laya agent skill exists (research 2026-11-07,
  `.planning/research/2026-11-07-jev-vs-typesafe-ai.md`).
- **Today's probe** (`_laya_probe`/`_get_probe`, `jev_review.py`) checks that `/health` answers 200 and discards the
  body; the Laya URL comes from `JEV_LAYA_URL`/`AI_KIT_LAYA_URL` or `LAYA_DEFAULT_URL`; the capability `TABLE` cells
  cite a fixed Laya version.
- **Zen**: the skill has no Zen or OpenCode backend left (JEV-02, Phase 32.1): its `TABLE` lists `laya` and
  `typesafe`; the remaining "opencode" strings name the host's skill folder only.
- **The official skill's doc flow**: docs.typesafe.ai `llms.txt`, then `changelog.md` and `models.md`; TypeSafe answers
  log the versioned model id (`jev-1.14.0`).

## Requirements

1. **Backend per host from ai-kit's config (JEV-01)**: the probe picks Laya first at the URL in `[jev] laya_url` (any host and port), TypeSafe from the environment, and the home-file key last, and shows which it picked on each host.
   - Current: the Laya URL comes from environment variables or a fixed default; no config file holds it.
   - Target: `[jev] laya_url` (project over user) wins over the environment variables, which still work as overrides for a session; with no URL configured and no Laya answering at the default, the first run asks once and saves the answer; the probe names a missing key source and the multiplexer hint without printing a value; the home-file fallback is removed once a test shows agent shells inherit the key, or kept with a recorded reason.
   - Acceptance: scratch-home tests cover a configured remote URL, an environment override, the first-run question (answered and declined), a missing key source and the home-file fallback order; no test prints a key.

2. **Laya version at the configured address (JEV-10, owner 2026-11-14)**: before the first call to a Laya in a session, the skill determines which version runs at that address.
   - Current: the probe discards the `/health` body; the version is never known.
   - Target: the version is taken from what the server exposes (a package version field if a later Laya adds one), else from `[jev] laya_version` the user sets, else it is labelled "not exposed"; the probe also records a fingerprint of the server (the `/openapi.json` info and route list, and the `/health` loaded checkpoints with their revisions); the result is shown in the probe row.
   - Acceptance: fake-server tests cover a server that exposes a version, one that does not (version from config, then "not exposed"), a changed route list and a changed checkpoint revision.

3. **What that version can do, fetched once when unknown (JEV-10, owner 2026-11-14)**: the skill keeps a capability record keyed by the Laya version (or by the fingerprint when the version is not exposed); when the record for the current key does not exist, it fetches Laya's published capabilities or changelog once and records what this version can do and how jev can use it.
   - Current: capability facts are fixed text in the skill, dated to one Laya version.
   - Target: the record lives in ai-kit's state directory with the key, the fetch time and the source URLs; the fetch uses public requests only (PyPI JSON and the project's README or changelog), no key and no question, with a short timeout; a fetch failure keeps the last record and says so; a known key never fetches again; a new capability found this way is reported as "documented upstream, not verified here" and never turns a capability cell to verified; the record can be refreshed on demand.
   - Acceptance: fake-server tests cover an unknown key (one fetch, record written), a known key (no fetch), a failed fetch (old record kept, notice), a new feature in the changelog (reported, cell unchanged) and an on-demand refresh.

4. **TypeSafe used the way the official skill teaches (JEV-12, owner 2026-11-14)**: when the remote TypeSafe backend answers, the skill knows what that remote can do and follows the official skill's doc flow when it meets something new.
   - Current: the skill points to the official doc flow for item design (JEV-08) but never notices a new model id or feature.
   - Target: the model id each TypeSafe answer reports is compared with the recorded one; a new id, or a primitive or option the skill does not know, triggers the same "unknown → fetch once" step through the official skill's doc flow (its `llms.txt`, `changelog.md`, `models.md`; the installed `typesafe-ai` skill's pointers when present), recording what changed and which of our features it could serve (box, images, long context, batching); public requests only; the record is keyed by model id.
   - Acceptance: fake-server tests cover a known model id (no fetch), a new one (one fetch, record and report), and a failed fetch; a doc-contract test pins the SKILL.md pointer.

5. **Laya calibration on the owner's version (JEV-03, amended 2026-11-14)**: a calibration run measures Laya's accuracy against its floor on the version running at the configured address, with no upgrade step in this phase.
   - Current: no calibration has run since the 32-case run (about half right when confident).
   - Target: the run records confident-answer accuracy with the Laya version or fingerprint and the checkpoint revision; the opencode judge lane is re-judged; the calibration script has a documented how-to; the Laya upgrade stays the owner's job in `llm-env`.
   - Acceptance: the calibration record exists with those fields; the how-to is linked from the skill's reference.

6. **The skill states Laya's limits (JEV-03)**: SKILL.md's result recipe and `backends/laya.md` say that a confident Laya answer is not proven accurate, citing the latest calibration.
   - Current: the text cites the older run only in research notes.
   - Target: both texts state it with the calibration's numbers and date.
   - Acceptance: a doc-contract test pins the sentence in both files.

7. **The jev knob (JEV-07)**: `[jev] enabled` in ai-kit's config turns jev classification on or off for every skill; it is asked once when absent.
   - Current: jev is switched by the `GSD_PATH_JEV` environment variable.
   - Target: with the knob off every skill behaves exactly as if jev were not installed; the environment variable stays a session override.
   - Acceptance: scratch-home tests with the knob on, off and absent (asked once).

8. **Two decision-path records (JEV-11)**: Laya's official MCP server stays outside jev's decision path, with the reason, and a spike records whether several questions over one shared state answer better on TypeSafe than merged contexts.
   - Current: neither is recorded in the skill.
   - Target: the reason (it would bypass one item per call, the size guard, thresholds, receipts and the answer log) is in `backends/laya.md`; the spike result is a dated record.
   - Acceptance: a doc-contract test pins the MCP sentence; the spike record exists.

9. **No Zen, no delegation, and the judge bar (JEV-13, JDG-04)**: the skill has no Zen or other removed backend path and delegates nothing to another repository's tooling; its SKILL.md meets the judge bar.
   - Current: Zen is gone (JEV-02); no guard keeps it out; the 2026-11-07 notes mention a tools-installer task.
   - Target: a guard test fails when the backend table, scripts or skill text name Zen, `opencode` as a backend, or a step that hands Laya or the official skill's install or upgrade to tools-installer or another repo; the Laya server's lifecycle is the owner's `llm-env`; every SKILL.md this phase materially changes meets the judge bar (referee-one and referee-two, referee-three as fallback, one usable referee accepted with the reason, never native opus).
   - Acceptance: the guard test passes; 34-VERIFICATION.md lists the loop `34` result for `jev-fast-decision`.

## Boundaries

**In scope:**
- jev-fast-decision's probe, backend choice, capability records, fetch-once steps, calibration, knob, skill text and
  guard tests (R1-R9); the `[jev]` keys in ai-kit's config.

**Out of scope:**
- Upgrading, installing or configuring Laya or its server (`llm-env`, the owner's).
- Installing or updating the official `typesafe-ai` skill (never ai-kit's; JEV-08).
- Image and box answers (JEV-05, Phase 54); the four-file jev marker block (JEV-04, Phase 54).
- Phase 33's reader itself (reused through a parity-tested copy).

## Constraints

- The skill stays self-contained and stdlib-only; it copies Phase 33's layered reader with a parity test.
- Network fetches are public, keyless, short-timeout and never on the per-item answer path; tests use fake servers.
- Never print a key; consent rules for remote backends are unchanged.
- Tests run in a scratch HOME with `AI_KIT_REFUSE_REAL_HOME=1` and read no `.planning/` path.
- English only; no machine-specific absolute path in source, tests or docs.

## Acceptance Criteria

- [ ] The probe picks Laya from `[jev] laya_url` at any address, then TypeSafe, then the home-file key; the first-run question works (R1).
- [ ] The probe shows the Laya version (exposed, configured or "not exposed") and the server fingerprint (R2).
- [ ] An unknown version or fingerprint triggers one public fetch and a record; a known one never fetches (R3).
- [ ] A new TypeSafe model id triggers one doc-flow fetch and a record (R4).
- [ ] The calibration record carries the Laya version or fingerprint and revision; the how-to exists; no upgrade step (R5).
- [ ] SKILL.md and `backends/laya.md` state the confident-answer limit with the calibration's numbers (R6).
- [ ] The knob on, off and absent behave as specified (R7).
- [ ] The MCP record and the shared-state spike record exist (R8).
- [ ] The no-Zen, no-delegation guard passes; loop `34` meets the bar for `jev-fast-decision` (R9).
- [ ] `make test` passes.

## Edge Coverage

**Coverage:** 28/29 applicable edges resolved · 1 unresolved (29 engine rows from `edge_floor.py floor`, 1
unclassified)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | A configured URL equal to the default is treated as configured (no first-run question) |
| empty | R1 | ✅ covered | No URL, no Laya at the default: asked once; a declined answer records "no Laya" and the ladder starts at TypeSafe |
| encoding | R1 | ✅ covered | The URL is parsed with `urllib.parse`; a malformed one is a probe error naming the key, never a crash |
| ordering | R1 | ✅ covered | Per key: environment override for the session, then project config, then user config, then the default |
| concurrency | R1 | ✅ covered | The first-run answer is saved through Phase 33's atomic writer; two sessions asking at once keep one answer |
| adjacency | R2 | ✅ covered | Same version, different route list or revision: a new fingerprint, so R3 treats it as unknown |
| empty | R2 | ✅ covered | `/health` or `/openapi.json` unreachable: version "unknown", no fingerprint, the probe says so and the ladder falls through as today |
| ordering | R2 | ✅ covered | Version source order: server field, then `[jev] laya_version`, then "not exposed" |
| empty | R3 | ✅ covered | An upstream page with no changelog entry for the version records "no published notes" for that key |
| encoding | R3 | ✅ covered | Fetched text is decoded as UTF-8 with replacement and stored as text; never executed or rendered |
| concurrency | R3 | ✅ covered | The record is written atomically; a parallel fetch for the same key is harmless (same content, last write wins) |
| adjacency | R4 | ✅ covered | An alias that resolves to a known versioned id counts as known |
| empty | R4 | ✅ covered | An answer with no model id records nothing and fetches nothing |
| ordering | R4 | 🧪 backstop | One record per model id; no ordering involved |
| concurrency | R4 | 🧪 backstop | Same atomic record write as R3 |
| unclassified | R5 | ⚠ UNRESOLVED | engine row; reviewed: the calibration runs once per Laya version and records its inputs; no upgrade step |
| empty | R6 | ✅ covered | With no new calibration yet, the text cites the 32-case run with its date |
| encoding | R6 | 🧪 backstop | Plain Markdown text |
| concurrency | R6 | 🧪 backstop | Static docs |
| adjacency | R7 | ✅ covered | Knob off in the project and on for the user: the project value wins |
| empty | R7 | ✅ covered | Knob absent: asked once, the answer saved; non-interactive runs default to on and say so |
| ordering | R7 | ✅ covered | Session environment override, then project, then user, then the question |
| adjacency | R8 | 🧪 backstop | Records only |
| empty | R8 | 🧪 backstop | Records only |
| ordering | R8 | 🧪 backstop | Records only |
| adjacency | R9 | ✅ covered | The word "opencode" naming the host's skill folder is allowed; as a backend name it fails the guard |
| empty | R9 | ✅ covered | A skill tree with no backend text still passes the guard |
| encoding | R9 | 🧪 backstop | ASCII names |
| ordering | R9 | 🧪 backstop | Guard order does not matter |

## Prohibitions (must-NOT)

**Coverage:** 4/4 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT print or log an API key or send one with a capability fetch | R1, R3, R4 | resolved | verification: test — fetch fakes assert no auth header and probe output holds no key |
| MUST NOT turn a capability cell to verified from upstream text alone | R3, R4 | resolved | verification: test — the R3 new-feature case keeps the cell's status |
| MUST NOT upgrade, install or restart Laya or install the official skill | R5, R9 | resolved | verification: test — the R9 guard; no code path calls a package manager or container tool |
| MUST NOT fetch anything on the per-item answer path | R3, R4 | resolved | verification: test — an answer run with a fake fetcher that fails on call |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Owner decisions of 2026-11-14 fix the version and capability flow |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | Laya lifecycle and the official skill's install fenced out |
| Constraint Clarity | 0.85  | 0.65 | ✓      | Self-contained, keyless short fetches off the answer path, fakes |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | Nine checks tied to tests or records |
| **Ambiguity**      | 0.13  | ≤0.20| ✓      | 1 − (0.35×0.90 + 0.25×0.88 + 0.20×0.85 + 0.20×0.82) |

## Interview Log

Owner-led (2026-11-14). Order of authority: the owner's words of 2026-11-14, then the 2026-11-07 transcript, then
jev, then the owner on low confidence. Rule: `mvp-mode` inactive, so the best design wins over the smallest diff.

| Round | Perspective | Question summary | jev (advisory) | Decision locked |
|-------|-------------|------------------|----------------|-----------------|
| 1 | Researcher | What does the upgraded Laya expose about its version? | none | Live: no package version over HTTP; serve API 0.1.0, four routes, checkpoint revisions in `/health` (Background) |
| 1 | Owner | Upgrade Laya before calibrating? | none | No: the owner upgraded it in `llm-env`; the skill checks the version at the configured address (R2, R5) |
| 1 | Owner | Fixed 24-hour cache and a 7-day `--check-updates`, or fetch when unknown? | none | Fetch Laya's capabilities or changelog once when the version or fingerprint is unknown; keep an on-demand refresh (R3) |
| 1 | Owner | What does "learn from typesafe-ai" mean for our skill? | none | The same unknown-to-fetch step for TypeSafe model ids and features through the official doc flow (R4) |
| 1 | Simplifier | Where does the version come from when the server does not expose it? | none; own reasoning | Server field, then `[jev] laya_version`, then "not exposed", with a fingerprint as the cache key (R2) |
| 1 | Owner | Zen and tools-installer | none | Zen stays out with a guard test; nothing delegated to another repo (R9) |

---

*Phase: 34-jev-backends-by-host-and-laya-calibration*
*Spec created: 2026-11-14*
