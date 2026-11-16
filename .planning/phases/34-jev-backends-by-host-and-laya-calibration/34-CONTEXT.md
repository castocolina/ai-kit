# Phase 34: jev backends by host and Laya calibration - Context

**Gathered:** 2026-11-14 (owner-led, after 34-SPEC.md)
**Status:** Ready for planning (after Phase 33 lands its `config.toml` reader)

<domain>
## Phase Boundary

jev-fast-decision reads its settings from ai-kit's `config.toml` `[jev]` table, finds Laya at the configured address,
learns which version runs there and what that version can do (fetching Laya's published notes once when that is
unknown), notices new TypeSafe models and features through the official skill's doc flow, measures Laya against its
floor on the owner's version, and can be switched off for every skill. It upgrades nothing and delegates nothing.
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**9 requirements are locked.** See `34-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `34-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope:** backend choice from `[jev]` (R1); Laya version and fingerprint (R2); capability records fetched once
when unknown (R3); TypeSafe model and feature awareness (R4); calibration on the running version (R5); the stated
limit (R6); the knob (R7); the two decision-path records (R8); the no-Zen, no-delegation guard and the judge bar (R9).

**Out of scope:** Laya's install, upgrade and server (`llm-env`); the official skill's install; images and box
(Phase 54); the four-file marker block (Phase 54).
</spec_lock>

<decisions>
## Implementation Decisions

### Settings and reader (SPEC R1, R7)

- **D-01: `[jev]` keys:** `laya_url` (string), `laya_version` (optional string, set by the user when the server does
  not expose one), `enabled` (bool). Project over user per key; the environment variables (`JEV_LAYA_URL`,
  `AI_KIT_LAYA_URL`, `GSD_PATH_JEV`) stay session overrides above both. Owner's words (any address; nothing assumed
  about localhost).
- **D-02: The skill copies Phase 33's layered reader** (33 D-22) into its scripts with a parity test, so the skill stays
  self-contained; writes go through a copy of 33's splicer limited to the `[jev]` table.
- **D-03: The first-run question is the agent's, not the script's.** Scripts run non-interactively under agents: the
  probe reports `needs_answer: laya_url` (or `enabled`) and SKILL.md tells the agent to ask the user once through its
  host's question tool and save the answer with `jev_review.py config set <key> <value>`. A declined Laya records
  `laya_url = ""` (no Laya) so it is not asked again; non-interactive runs with `enabled` absent default to on and say
  so in the probe.

### Version, fingerprint and capability records (SPEC R2, R3)

- **D-04: Version source order:** a package-version field from the server (none today), then `[jev] laya_version`, then
  "not exposed". The fingerprint is the sha256 of the canonical JSON of `/openapi.json` `info` plus its sorted route
  and method list, plus `/health` `loaded` and `revisions`. The probe row shows version, version source and the first
  12 hex characters of the fingerprint.
- **D-05: Records live in `${XDG_STATE_HOME:-~/.local/state}/ai-kit/jev/`:** `laya-capabilities.json` keyed by version
  (or `fp:<fingerprint>` when the version is not exposed) and `typesafe-models.json` keyed by model id. Each entry:
  `checked_at`, source URLs, the fetched notes (text, trimmed), and `features_documented` (names found in the notes).
  Written atomically; never committed.
- **D-06: Laya sources, fetched once per unknown key:** PyPI JSON `https://pypi.org/pypi/laya/json` (`info.version`,
  release list and the README's "What's new" section) and the project README on GitHub; 5-second timeout each; no key,
  no header beyond a plain user agent. When the version is "not exposed", the entry records the latest upstream release
  and notes that the running one may differ. A failed fetch keeps the previous entry and prints one notice.
- **D-07: How jev uses what it learns is the agent's call.** The script records and reports ("new Laya features
  documented upstream: …, not verified here"); SKILL.md tells the agent to read the record when the probe says `new`
  and decide whether an item type or option could now go to Laya; a capability cell turns verified only through a
  recorded live run, as today.
- **D-08: `--check-updates` stays as the on-demand refresh** of both records (it re-fetches the current keys); the
  fixed 24-hour and 7-day caches of the 2026-11-07 wording are dropped: a key's record stays valid until the key
  changes.

### TypeSafe (SPEC R4)

- **D-09: A new model id triggers the official doc flow once:** docs.typesafe.ai `llms.txt`, then `changelog.md` and
  `models.md`; when the `typesafe-ai` skill is installed, SKILL.md points the agent at its doc flow for item design as
  JEV-08 already does. The record notes which of our features the change could serve (box, images, long context,
  batching). The check runs after an answer is logged, never before or during a call.

### Calibration and text (SPEC R5, R6)

- **D-10: Calibration** uses `scripts/eval_cases.py calibrate` against the configured Laya, records confident-answer
  accuracy, the floor, the version (or fingerprint) and the checkpoint revision in `backends/laya.md` with the date;
  the raw run stays under `tmp/`; a how-to section goes in `reference.md`. The opencode judge lane is re-judged in the
  same loop. No upgrade step (owner, 2026-11-14).
- **D-11: The limit sentence** ("a confident Laya answer is not proven accurate") goes in SKILL.md's result recipe and
  `backends/laya.md` with the latest numbers; a doc-contract test pins both.

### Records, guard and judging (SPEC R8, R9)

- **D-12: `backends/laya.md` records the MCP decision** with its reason; the shared-state spike is a dated record in
  `reference.md` (method, cases, result).
- **D-13: Guard test `tests/test_jev_fast_decision_guard.py`** scans the skill tree (scripts, SKILL.md, references,
  backends, evals) and fails on Zen, on `opencode` used as a backend name (the host-folder lines are allowed), and on
  any step that hands Laya's or the official skill's install or upgrade to tools-installer or another repo.
- **D-14: Loop `34` judges `jev-fast-decision`** (its SKILL.md changes materially: settings, probe and records).
  Judges referee-one and referee-two; referee-three replaces one that fails; one usable referee is accepted with the
  reason recorded; never native opus.

### Planning artifacts

- **D-15: REQUIREMENTS amendments in this phase's commit:** JEV-03 (no upgrade step; calibrate the running version),
  JEV-10 (version-keyed fetch once, replacing the fixed caches), new JEV-12 (TypeSafe awareness) and JEV-13 (no Zen,
  no delegation guard); ROADMAP Phase 34 criteria follow.

### Claude's Discretion

- Function names, the exact notice wording, and the trimming length of stored notes.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/34-jev-backends-by-host-and-laya-calibration/34-SPEC.md`
- `.planning/phases/33-one-config-design/33-CONTEXT.md` (D-03 `[jev]` place, D-22 reusable reader)
- `.planning/research/2026-11-07-jev-vs-typesafe-ai.md` (§6 Laya discovery, §8 skill stack)
- `skills/jev-fast-decision/scripts/jev_review.py` (`LAYA_DEFAULT_URL`, `_laya_url`, `_backend_choice`,
  `_typesafe_key_sources`, `probe_report`, `_laya_probe`, `_get_probe`, `TABLE`), `jev_ladder.py`,
  `scripts/eval_cases.py` (`calibrate`, `_run_calibration`), `backends/laya.md`, `reference.md`, `SKILL.md`
</canonical_refs>

<deferred>
## Deferred Ideas

- Asking upstream Laya to expose its package version over HTTP (owner's call; the fingerprint covers the gap).
</deferred>
