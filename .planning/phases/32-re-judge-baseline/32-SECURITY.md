---
phase: "32"
slug: "re-judge-baseline"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-07"
---

# Phase 32 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Register source: the `<threat_model>` blocks of 32-01 to 32-09 (authored at plan time) and the
SUMMARY `## Threat Flags` sections (none beyond the plans' models). ASVS level 1, block on high:
every threat was classified at grep depth against the tree at the close-out (after the code-review
fixes 1e4f96e..78f0efc); all mitigations are present, so the auditor short-circuit applies (no
open threat). Evidence script: `tmp/auto/p32-close/sec_l1.py` (31 patterns, 0 missing).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| lane output -> ingest | a judge's reply, possibly steered by the judged skill, becomes a record | untrusted text, parsed as JSON data only |
| skill name / finding path -> filesystem | argument and judge-written paths reach git and file reads | paths, confined under the repo root |
| installed skill-judge -> prompt | third-party files are copied into prompts | rubric and spec text |
| ROADMAP text -> check-dogfood | planning prose decides a push gate result | Markdown read with fixed regexes |
| skill text and references -> hosts | shipped Markdown reaches every host the installer links | skill instructions |
| skill frontmatter -> host parsers | malformed frontmatter makes a host skip the skill | YAML subset |
| tool -> jev client | an item leaves the process, possibly to a consented remote backend | fixed text and word bands only |
| probe lane output -> pool | untrusted lane text decides pool membership | one-word answer and status line |
| inputs.json -> git | a recorded base commit reaches a git argv | commit id, regex-gated |
| committed records -> report and push gate | records decide what REJUDGE.md states and whether a push passes | verdict JSON |
| repo -> external judge lanes; owner HOME and host configs | read-only review lanes read the tree through a host CLI | repository text; no host config writes |
| scratch records -> committed records | lane-derived data enters the repository | verdict JSON, status lines, repo-relative paths |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-32-01 | Tampering | `ingest` (verdict JSON from a lane) | high | mitigate | `validate_verdict` (judge_loop.py:448), `_refuse_mismatch` (:509), `lane_ok` needs status ok, exit 0, tree clean (:356); verdict is `json.loads` data, never executed | closed |
| T-32-02 | Information disclosure | `finding_path_errors`, `skill_files` | medium | mitigate | finding paths resolved and checked with `is_relative_to` (:497); `SAFE_SKILL.fullmatch` (:144); git argv lists with `--` before pathspecs (:146) | closed |
| T-32-03 | Repudiation | records | medium | mitigate | "a verdict is already recorded for this round" refusal (:560); attempts appended (:589); atomic writes through `os.replace` (:476) | closed |
| T-32-SC | Tampering | package installs | low | accept | no package install; `tools/judge_loop.py` imports stdlib modules only | closed |
| T-32-04 | Tampering | `check_jdg04_citations` | low | mitigate | read-only scan with fixed regexes, missing file or section is a named note (check_dogfood.py:553) | closed |
| T-32-05 | Denial of service | `stray_test_modules` | low | accept | one `os.walk` of the repo's own `tests/`, no content read (test_gate_scope.py:136) | closed |
| T-32-06 | Tampering | SKILL.md text edits | medium | mitigate | edits are moves into trailing `## Evidence` sections (e.g. curated-config SKILL.md:406); code review re-read every move (32-REVIEW.md: meaning kept); the baseline run judged the edited text | closed |
| T-32-07 | Repudiation | provenance | low | mitigate | dates, versions and run logs kept in `## Evidence` sections (e.g. spec-config SKILL.md:465) | closed |
| T-32-08 | Information disclosure | `jev_item`, `ask_jev` | high | mitigate | fixed item text and word bands (`jev_item`, :1371), pinned by `test_jev_item_is_pinned_to_fixed_words` | closed |
| T-32-09 | Spoofing | `probe_result` | medium | mitigate | usable only on a clean status and the exact sentinel echo ("answer is not the sentinel", :1226) | closed |
| T-32-10 | Tampering | `numstat` | low | mitigate | `BASE_RE.fullmatch(base)` before any git call (:1443); argv list with `--` | closed |
| T-32-11 | Tampering | reference text edits | low | mitigate | placeholder or pointer removals, pinned by `tests/test_skill_text_history.py` | closed |
| T-32-12 | Information disclosure | shipped Markdown | low | mitigate | `REFEREE_RE` in `tests/test_skill_text_history.py:73`, run on every push | closed |
| T-32-13 | Denial of service | skill discovery on hosts | medium | mitigate | strict frontmatter gate (duplicate keys, tabs, plain `: `; test_skill_frontmatter.py) with the PyYAML cross-check (test_skill_frontmatter_pyyaml.py) | closed |
| T-32-14 | Tampering | npx cache read | low | accept | the one-time npm `yaml` comparison only read an existing package; nothing installed | closed |
| T-32-15 | Tampering | `REJUDGE.md`, verdict records | high | mitigate | `check` re-validates every record, refuses a record missing `RECORD_KEYS` (:700) and compares a fresh render byte for byte (:1168); `check_judge_records` runs it in check-dogfood on every push (check_dogfood.py:589) | closed |
| T-32-16 | Repudiation | judge substitution | medium | mitigate | exact-string judge match ("is not in the judge list", :1046); `judge_order` (:753); substitute reasons rendered from records | closed |
| T-32-17 | Elevation of privilege | refutations | medium | mitigate | `REFUTATION_FIELDS` finding, location, command, output all required (:612), only for that judge's own finding ids | closed |
| T-32-18 | Tampering | external lanes | high | mitigate | lanes ran with `--mode review`; ingest counts only `tree=clean` (`lane_ok`); 31/31 lane status lines in REJUDGE.md read `tree=clean`; HEAD and tracked tree verified unchanged (32-08 SUMMARY) | closed |
| T-32-19 | Elevation of privilege | native lanes | medium | mitigate | `agents/ai-kit-judge.md` has `tools: Read, Grep, Glob` only; replies validated by `ingest` | closed |
| T-32-20 | Information disclosure | host configs and HOME | high | mitigate | `AI_KIT_REFUSE_REAL_HOME=1` for every child; effort env printed set/unset only; metadata-only mtime audit found no host config change in the lane window (32-VERIFICATION.md addendum) | closed |
| T-32-21 | Repudiation | substitutes | medium | mitigate | every substitute is a native lane ingested with `--replaces` and `--reason` (:1644); 5 substitutes recorded with reasons in REJUDGE.md | closed |
| T-32-22 | Tampering | publish step | high | mitigate | byte-for-byte publish (32-09 `compare-publish-w5.py`); `check --require-current` (:72) exits 0 on the committed records at close-out | closed |
| T-32-23 | Information disclosure | committed records | low | mitigate | records hold verdict JSON, status lines and repo-relative paths; the only home-like path in `.planning/judge/` is a judge quoting the judged skill's own sample file (`/home/user-zero/...`), not a real path | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-32-01 | T-32-SC | No package install in this phase; the tools are stdlib-only and PyYAML was already locked in `uv.lock` | plan threat model (32-01..32-09) | 2026-11-07 |
| AR-32-02 | T-32-05 | The stray-module guard walks only the repo's own `tests/` folder and reads no file content | plan threat model (32-02) | 2026-11-07 |
| AR-32-03 | T-32-14 | The one-time npm `yaml` comparison read an existing cached package and wrote only under `tmp/` | plan threat model (32-06) | 2026-11-07 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-07 | 24 | 24 | 0 | orchestrator (gsd-secure-phase, ASVS 1 grep-depth short-circuit) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-07
