---
phase: "29"
slug: "logical-commit-folding-and-the-shared-jev-ladder"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-05"
---

# Phase 29 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| checkpoint JSON → engine | adapter-built input drives ref rewrites | shas, unit and ref names (validated) |
| repo state → engine guards | branch, index, merges and refs decide whether a rewrite is safe | local git state |
| engine → git refs | the only write: one backup tag and one compare-and-swap ref update | refs |
| adapter / plan files → candidates | PLAN.md and superpowers plan text are parsed into the fold range | local plan text |
| repo history → jev item | commit subjects and path names leave the fold process for the ladder | summaries only, length-capped |
| jev answer → grouping | an advisory answer may be wrong or malformed | partition proposal (validated) |
| caller items → ladder → client child | summaries from any classifying skill; the client may send them to a consented remote | summaries; secret-shaped fields rejected |
| host skills dirs → hooks and goal-prompt | a `jev_review.py` found in a user skills dir is run | scrubbed env, bounded timeout |
| GSD CLI process → command module | `ai-kit-fold.cjs` runs inside gsd-tools | phase number (pattern-checked) |
| SKILL.md / policy text → agents | consent ask, remote-send rules and folding rules are agent-followed text | instructions |
| repo text → external judge lane | skill text and tests go to referee models | public repo content only |
| future changes → black-box rules | later edits could reopen cross-skill reaches or backend detail | source text (arch and text tests) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-29-01 | Tampering | fold_engine build/swap | high | mitigate | segment and final tree proofs before any ref write; backup tag; `update-ref` compare-and-swap; tag deleted on failure only when created (`fold_engine.py` 303-327, 439-441) | closed |
| T-29-02 | Tampering | fold_engine main/merged guards | high | mitigate | `rev-list --count --not` each local/origin base ref and each merged ref; refusal tests assert branch, status and tags unchanged | closed |
| T-29-03 | Tampering | git argv from checkpoint fields | medium | mitigate | `load_checkpoint` sha/unit/ref regexes; argv lists only; NUL-split path output; shell-true arch rule covers the skill | closed |
| T-29-04 | Information disclosure | jev_ladder `child_env` | high | mitigate | JEV_* and GSD_PATH_JEV* control vars scrubbed; `test_ladder_child_env_scrubbed` | closed |
| T-29-05 | Information disclosure | jev_ladder item validation | high | mitigate | fences, key shapes, MAX_FIELD_CHARS; leaky-client and unsafe-id tests | closed |
| T-29-06 | Elevation of privilege | `--client` override | medium | mitigate | `client_ok` protocol-line check gates every run path | closed |
| T-29-07 | Spoofing | `find_client` host-root branch | low | accept | checkout copy first; scrubbed env and never-created config home | closed |
| T-29-08 | Denial of service | probe through a found client | low | mitigate | bounded probe timeout, fail-open; jev-absent gives empty | closed |
| T-29-09 | Information disclosure | judge prompt contents | low | accept | prompts name only `skills/` and `tests/` paths | closed |
| T-29-10 | Tampering | judge lane writes | low | mitigate | review mode, output under `tmp/p29/judge/`, `AI_KIT_REFUSE_REAL_HOME=1`, `tree=clean` per lane | closed |
| T-29-11 | Information disclosure | `fold_group.jev_item` | high | mitigate | subject, paths and titles only; context capped at 1400 chars, titles at 200; ladder guard rejects key shapes | closed |
| T-29-12 | Tampering | jev answer → commits | medium | mitigate | `validate_partition` with rules fallback; both tree proofs still guard the swap | closed |
| T-29-13 | Denial of service | jev calls in the fold | low | mitigate | per-call bound, stop at first non-answer, one call per commit, rules always finish. The plan said 40 s; review fix WR-07 raised the bound to 130 s (`JEV_TIMEOUT_SECONDS = 130`) | closed |
| T-29-14 | Spoofing | `find_jev` in gp_host | low | accept | only `detect` runs, with timeout; output reduced to booleans and fixed reasons | closed |
| T-29-15 | Information disclosure | consent flow in jev SKILL.md | high | mitigate | ask names backend and host, summaries only, revoke command, grant only after yes; eval `edge-remote-consent` | closed |
| T-29-16 | Elevation of privilege | `ai-kit-fold.cjs` | medium | mitigate | node built-ins only; `spawnSync` fixed argv, no shell; phase checked against `^\d+(\.\d+)?$` | closed |
| T-29-17 | Spoofing | capability install approval | medium | mitigate | project scope only, `--yes` only after the owner's yes; install-without-yes refusal test | closed |
| T-29-18 | Tampering | e2e run vs real GSD state | high | mitigate | temp HOME/GSD_HOME, `AI_KIT_REFUSE_REAL_HOME=1`, temp project copy, nulled git config (`test_ai_kit_commit_fold_e2e.py`) | closed |
| T-29-19 | Information disclosure | spec-discuss items to jev | medium | mitigate | NEVER rule (summaries only); the skill grants nothing | closed |
| T-29-20 | Tampering | FOLD_BASE recorded wrong | medium | mitigate | FOLD_BASE stored before the first task; base-branch guard; pre-plan commit keeps its sha in the fixture | closed |
| T-29-21 | Tampering | finishing step pushing an unfolded branch | medium | mitigate | fold step before the finishing step; refusal stops the run; no merge/push/PR through the finishing step | closed |
| T-29-22 | Tampering | cross-skill allowlist growth | medium | mitigate | `_CROSS_SKILL_FROZEN` literal; stale-entry and new-entry tests | closed |
| T-29-23 | Repudiation | vacuous structural or text tests | low | mitigate | non-vacuity case per form and per forbidden term; scanner proven on jev's real text | closed |
| T-29-24 | Tampering | edits driven by judge findings | low | mitigate | two re-judge rounds (cap three); fixes pass the skill tests | closed |
| T-29-25 | Tampering | policy rule dropped or restated | medium | mitigate | `missing_policy_rules` names each removed rule; AGENTS.md is pointer-only | closed |
| T-29-26 | Tampering | merge-back and replay | high | mitigate | foreign merges refused; segment proof before replay; final proof before any ref write | closed |
| T-29-27 | Tampering | adapter range detection | high | mitigate | `plan_not_contiguous` refusal; folded commits skipped by trailer; both proofs on every checkpoint | closed |
| T-29-28 | Information disclosure | eval input files | low | mitigate | `MACHINE_PATH_RE` shape test; synthetic inputs | closed |
| T-29-SC (x16) | Tampering | package installs | low | accept | no `uv.lock` or `package.json` change; `pyproject.toml` change is a pyright `extraPaths` entry; stdlib and `node:` modules only | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-29-01 | T-29-07 | host skills dirs are the user's own, the same set the old lookup searched; checkout copy first; scrubbed env | plan 29-04 threat model | 2026-11-05 |
| AR-29-02 | T-29-09 | only public skill text and tests go to the judges | plan 29-05 threat model | 2026-11-05 |
| AR-29-03 | T-29-14 | only `detect` runs; output reduced to booleans and fixed reasons | plan 29-07 threat model | 2026-11-05 |
| AR-29-04 | T-29-SC | no package install in any plan; stdlib and node built-ins only | every plan's threat model | 2026-11-05 |

---

## Audit Notes (non-blocking)

- The sequential two-plan adapter test does not assert each segment's tree (only the worktree two-plan test does). The engine's segment proof still runs on every checkpoint, so this is a test-coverage gap, not a missing mitigation.
- `base_branch` in a checkpoint is checked as a non-empty string only. It is always used behind a `refs/heads/` or `refs/remotes/origin/` prefix inside `rev-parse --verify`, so it cannot be read as a git option.
- The T-29-18 one-time "no `.gsd/`" clean check lived in a plan scratch script that no longer exists. The gitignored repo-root `.gsd/` holds only GSD's own dispatch sentinel, with no capability install files.
- The Phase 47 policy drift test named in T-29-25 is future work and was not checked.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-05 | 44 | 44 | 0 | gsd-security-auditor (opus), ASVS L1, block_on high |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-05
