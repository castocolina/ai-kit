---
phase: "18"
slug: "cross-ai-skills-apply-pipeline"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-15"
---

# Phase 18 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| plan.json / inventory.json -> `plan-set`/`apply`/`followups` | Hand-editable files drive config writes; validated at every load (`validate_plan`, `check_plan_inventory`, digest, host, destination binding) | plan, inventory (high) |
| rendered `cross-ai.mjs` -> model CLIs | The runner launches CLIs unattended with full permissions (locked D-10) | prompts, repo edits (high, accepted) |
| ai-kit -> project `.planning/config.json` | Every config key goes through gsd-tools `config-set`/`config-new-project`; the only direct writes are the runner script and backup restores | config (high) |
| secrets env / JEV endpoint -> inventory | Presence-only checks plus a TCP reachability probe; no value read or printed | key names, host:port (high) |
| global / plugin skill roots -> plan | Symlinked roots resolved with realpath; trusted roots `~/`-relative and approved per entry | skill paths (medium) |
| follow-ups -> `npx @opengsd/gsd-core@<semver>` | Runs only after a grouped `--approve` bound by fingerprint | installer (high) |

---

## Threat Register

Audit at HEAD 72fd95d by gsd-security-auditor (xhigh). Result: SECURED, 74/74 closed.
Mitigate 70, accept 4, transfer 0. Abbreviations: `cc/` = `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/`, `spec/` = `skills/ai-kit-spec-review/ai_kit_spec/`, `runner` = `skills/ai-kit-spec-review/references/cross-ai.mjs`.

| Threat ID | Disposition | Status | Evidence |
|-----------|-------------|--------|----------|
| T-18-01 | mitigate | closed | `spec/detection.py:278-342` strict pi parse; residual RecursionError contained by subprocess refresh |
| T-18-02 | mitigate | closed | `spec/gsd_tools.py:152-246` strict encoder, no spawn after refusal |
| T-18-03 | mitigate | closed | `spec/local_secrets.py:32-34` bool only; sentinel tests |
| T-18-04 | mitigate | closed | `cc/gsd_catalog.py:181-197` lane whitelist; binary never run |
| T-18-05 | accept | closed | 18-02 rationale; plan stores only `~/` roots |
| T-18-06 | mitigate | closed | `cc/skill_scan.py:240-242` plugin `skills/` only (shortcut documented) |
| T-18-07 | mitigate | closed | `cc/skill_scan.py:326-331` presence only |
| T-18-08 | mitigate | closed | `cc/skill_scan.py:290-346` host/port only |
| T-18-09 | mitigate | closed | `cc/skill_scan.py:306-339` 1.5 s bounded probe, no default URL |
| T-18-10 | mitigate | closed | `cc/recommend.py:874-884` constant command |
| T-18-11 | mitigate | closed | `cc/cross_ai.py:17-22,107-114` runner allowlist + host skip |
| T-18-12 | mitigate | closed | `cc/cross_ai.py:136-142` 1800 s floor |
| T-18-13 | mitigate | closed | `cc/recommend.py:789,1160-1185` accepted keys only |
| T-18-14 | mitigate | closed | `cc/skills.py:314-351`, `cc/plan_io.py:675-699` |
| T-18-15 | mitigate | closed | `cc/skills.py:60-90,237-246` affinity validation |
| T-18-16 | mitigate | closed | `runner:357-366,735-745` stderr-only classification (A-CR-01) |
| T-18-17 | mitigate | closed | `runner:623-655` temp-index tree id (see U-3) |
| T-18-18 | mitigate | closed | `runner:469-544` group kill, bounded drain |
| T-18-19 | accept | closed | locked D-10; host signals scrubbed `runner:657-662` |
| T-18-20 | mitigate | closed | `runner:393-411` workstream guard, deadline only lowered |
| T-18-21 | mitigate | closed | `runner:777-808` enumerated flags, no shell |
| T-18-22 | mitigate | closed | `cc/cross_ai_script.py:175-190` pristine-only replace |
| T-18-23 | mitigate | closed | `cc/cross_ai_script.py:90-108` json.dumps CONFIG |
| T-18-24 | mitigate | closed | `cc/plan_edit.py:514-525`, `cc/plan_io.py:551-569`, `cc/apply.py:263-299` |
| T-18-25 | mitigate | closed | `cc/plan_edit.py:44-106,168-171` |
| T-18-26 | mitigate | closed | `cc/plan_io.py:458-496`, `cc/cli.py:521-563` |
| T-18-27 | mitigate | closed | `cc/config_backup.py:49-54,148-153`, `spec/cache.py:27-42` |
| T-18-28 | mitigate | closed | `cc/config_backup.py:173-204`, `cc/apply.py:534-538,747-760` |
| T-18-29 | mitigate | closed | `cc/config_backup.py:57-71,126-130` |
| T-18-30 | mitigate | closed | `cc/config_backup.py:64,121-129` |
| T-18-31 | mitigate | closed | `cc/cli.py:784`, `cc/plan_io.py:458-478`, `cc/apply.py:906-910` |
| T-18-32 | mitigate | closed | `cc/apply.py:235-260`, `cc/gsd_catalog.py:149-178` |
| T-18-33 | mitigate | closed | `cc/apply.py:190-206,505-509` |
| T-18-34 | mitigate | closed | `cc/apply.py:548-565,725-736`; AST test |
| T-18-35 | mitigate | closed | `cc/apply.py:732-735,854-873`; e2e |
| T-18-36 | mitigate | closed | `cc/apply.py:414-433,813`; e2e |
| T-18-37 | mitigate | closed | `cc/followups.py:21,47-48,163-176` exact semver (see U-2) |
| T-18-38 | mitigate | closed | `cc/cli.py:654-659` only caller after `--approve` |
| T-18-39 | mitigate | closed | `cc/followups.py:174-175` |
| T-18-40 | mitigate | closed | SKILL.md trust/permission text; drift tests |
| T-18-41 | mitigate | closed | `runner:816-832,1341-1366` hermetic self-test env |
| T-18-42 | mitigate | closed | `runner:2321-2336,608-619` |
| T-18-43 | mitigate | closed | `cc/plan_edit.py:330-343`, `cc/plan_io.py:783-793` |
| T-18-44 | accept | closed | 18-20 rationale; `cc/host.py:21-26` |
| T-18-45 | mitigate | closed | dated 18-22 amendments in 18-SPEC.md, REQUIREMENTS.md |
| T-18-46 | mitigate | closed | `cc/skill_scan.py:28,99`, `cc/skills.py:379-417` |
| T-18-47 | mitigate | closed | `cc/plan_io.py:198-232` |
| T-18-48 | accept | closed | 18-02 rationale; scope label |
| T-18-49 | mitigate | closed | `cc/skill_scan.py:110-132,254-257` (C-CR-1, D-31 amended) |
| T-18-50 | mitigate | closed | `cc/skills.py:186-201,327-351`, `cc/plan_io.py:696-698` |
| T-18-51 | mitigate | closed | `cc/skills.py:136-143` |
| T-18-52 | mitigate | closed | `runner:144,623-640` GIT_CAP_MS |
| T-18-53 | mitigate | closed | `runner:2361-2423` git failure -> unverified |
| T-18-54 | mitigate | closed | `runner:608-611,2367` |
| T-18-55 | mitigate | closed | `runner:756-763,2399-2412` |
| T-18-56 | mitigate | closed | `runner:136-143,669-689` |
| T-18-57 | mitigate | closed | `cc/cross_ai_script.py:200-218` re-read, divert to `.new` |
| T-18-58 | mitigate | closed | `cc/plan_io.py` validate_plan; TestPlanValidator |
| T-18-59 | mitigate | closed | `cc/plan_io.py:551-577`, `cc/cli.py:558` |
| T-18-60 | mitigate | closed | `cc/config_backup.py:173-185` os.link marker; 8-thread race test |
| T-18-61 | mitigate | closed | `cc/config_backup.py:97-120` bytes + mode |
| T-18-62 | mitigate | closed | `cc/apply.py:179-206` |
| T-18-63 | mitigate | closed | `cc/apply.py:555-563,699-713`; e2e |
| T-18-64 | mitigate | closed | `cc/apply.py:548-574` |
| T-18-65 | mitigate | closed | `cc/followups.py:85-98,257-271` |
| T-18-66 | mitigate | closed | `cc/apply.py:885-897`, `cc/followups.py:325-356` |
| T-18-67 | mitigate | closed | `cc/apply.py:519-531` |
| T-18-68 | mitigate | closed | `runner:187-226,488-513` single finalize |
| T-18-69 | mitigate | closed | `runner:423-433` review never resumes |
| T-18-70 | mitigate | closed | `cc/config_backup.py:213-288` recovery_text |
| T-18-71 | mitigate | closed | `cc/config_backup.py:173-175`, `cc/apply.py:406-411,859` |
| T-18-72 | mitigate | closed | `cc/apply.py:577-643` commit point |
| T-18-73 | mitigate | closed | `cc/cli.py:629-638` resolve_target |
| T-18-SC | mitigate | closed | no dependency manifest touched; stdlib/`node:` only |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-18-05 | Inventory stores real skill paths locally; the plan keeps only `~/` roots | 18-02 plan | 2026-10-15 |
| AR-02 | T-18-19 | Runner CLIs run unattended with full permissions and the user's env (locked D-10) | 18-CONTEXT D-10 | 2026-10-15 |
| AR-03 | T-18-44 | Project-local gsd-core roots are trusted as part of the checkout | 18-20 plan | 2026-10-15 |
| AR-04 | T-18-48 | Inventory scope label is informational | 18-02 plan | 2026-10-15 |

---

## Unregistered Flags (found by the audit, no plan modeled them)

| ID | Severity | Surface | Disposition |
|----|----------|---------|-------------|
| U-1 | medium | Other command-valued gsd-core keys (`workflow.plan_bounce_script`, `workflow.code_review_command`) settable via `plan-set` without the D-44 disclosure | fix in the post-audit pass |
| U-2 | medium | Follow-up `npx` runs in the target cwd, so a project `.npmrc` can redirect the registry; not disclosed | fix in the post-audit pass |
| U-3 | medium | Tree snapshot skips gitignored files, so edits there read `tree=clean` | fix in the post-audit pass |
| U-4 | low | Model ids not restricted to a safe character set (dash-prefixed id read as an option) | fix in the post-audit pass |
| U-5 | low | SKILL.md trust text omits the `.pi`/`.opencode` gsd-core roots tried first; empty PATH segment = cwd (POSIX, informational) | fix in the post-audit pass |

Out of scope: `tests/e2e/docker/Dockerfile:24` unpinned `curl | sh` uv install (Phase 01.1); A-IN-12 full-tree rehash (fails safe to `unverified`).

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-15 | 74 | 74 | 0 | gsd-security-auditor (xhigh), HEAD 72fd95d |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-15
