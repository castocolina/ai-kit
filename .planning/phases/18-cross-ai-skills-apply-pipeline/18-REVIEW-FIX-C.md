---
phase: 18
fixed_at: 2026-10-15
review_path: .planning/phases/18-cross-ai-skills-apply-pipeline/18-REVIEW.md
scope: "Batch C (CR-01, WR-01..14, IN-01..11) + independent skill-judge (I1..I7, M1..M7) + ponytail PT-08, PT-09, PT-10, PT-13, PT-14, PT-16 + batch B hand-offs (C-W7 text, C-W8 proposal side, PT-12 skill_scan, SKILL.md docs)"
iteration: 1
findings_in_scope: 47
fixed: 45
skipped: 2
status: partial
---
# Phase 18 Batch C: Code Review Fix Report

**Source review:** `18-REVIEW.md`: "# Batch C", "# Independent skill-judge (SKILL.md)", and the listed "# Ponytail review" items. Hand-offs from `18-REVIEW-FIX-B.md`.
**Commit range:** `1faeb29..afdaf08` (29 commits on `gsd/v1.3-curated-config-v2`, after `efdd14d`), plus this report.
**Where verification ran:** in this checkout (`.claude/worktrees/v13-curated-config-v2`). No separate review-fix worktree was used.

**Counts:** 47 in scope. 43 fixed in this batch, 2 already fixed by batch B (C-W1, C-W9), 2 skipped (both live in `cross_ai.py`, a batch A file).

**Verification (final tree):**
- `make test-unit`: 37/37 modules plus 1/1 uv module pass.
- `make e2e-test`: 7/7 Python e2e modules and 45/45 installer checks pass.
- `make arch-test`: pass. `make ruff pylint pyright vulture`: all pass.
- Every behavior change got a failing test first, confirmed red against the unfixed source. The C-W13 tests were also mutation-checked (deleting the `when` gate or the install check now fails them).

**Broken window to know about:** `7467c4f` (C-W8) changed the trusted-root candidate to a list, and the apply e2e helper `_decide_all_choices` still wrapped it in a list. The seven real-node apply e2e tests failed from `7467c4f` until `a4947bb` fixed the helper. The unit tier was green throughout. `3132215` also failed pyright (pre-push only) until `afdaf08`.

**Requires human verification** (logic, not just tests): C-CR-1, C-W3, C-W8, C-W12, PT-08.

## Fixed

### C-CR-1: project-skill escape used `<project>/skills` as the root
**Fixed in** `1faeb29` (requires human verification).
- Project rows now use gsd-core's rule: the skill directory's realpath must stay inside the project root's realpath; `SKILL.md` is not resolved. Global rows keep the `SKILL.md` rule.
- Tests: a symlinked `skills/` pointing outside the project escapes and is not wired; `skills/foo -> <project>/vendor/foo` and an in-project `SKILL.md` link are wired as `skills/foo`.
- D-31 amended in 18-CONTEXT.

### C-W1: dropped `connect_fn`
**Already fixed by batch B** in `a2604bd`.

### C-W2: YAML block scalars (`>-`, `|-`, ...) parsed as the literal
**Fixed in** `b60e4f4`. This repo's `markdown-to-pdf` and `mermaid-audit` descriptions now parse.

### C-W3: an absolute trusted root that covers an outside-home skill was ignored
**Fixed in** `cbcff11` (requires human verification).
- The outside-home refusal now consults `covered()` first. Recommend still never proposes an absolute root.
- The wire decision moved into a side-effect-free `skills.unwired_reason()`, reused by C-W5, C-W6 and PT-08.

### C-W4: a dangling `SKILL.md` symlink was inventoried
**Fixed in** `694c8f0`.

### C-W5: drop-agent notes named uninstalled skills
**Fixed in** `69c1f49`.
- The note fires only when a family skill would wire.
- Family ids `ponytail-review` and `ponytail-debt` became `ponytail-reviewers` and `ponytail-verifier`. `validate_affinity` rejects a family id equal to a skill name.
- Claude goldens change only in the family id inside `why`.

### C-W6: proposals for unwireable skills, once per root
**Fixed in** `ebf4759`. Proposals come from distinct names that `unwired_reason()` accepts.

### C-W7: proposal text led to a refused `plan-set`
**Fixed in** `78ade0e` (the refusal side was batch B's `8fb6bdd`). The text shows the shell-quoted JSON list and says the value is the agent's whole list.

### C-W8: approving the candidate dropped configured trusted roots
**Fixed in** `7467c4f`, test helper `a4947bb` (validator side: batch B's `bbe91d5`). Requires human verification.
- The `needs_choice` entry holds one candidate whose `value` is the configured roots followed by the new ones, with the skills it covers.
- `plan_edit._candidate_values` admits each element of a list candidate, so a subset is still accepted (batch B refuses one that drops a configured root).
- D-41 amended in 18-CONTEXT.

### C-W9: approval command not shell-quoted
**Already fixed by batch B** in `7198f17`.

### C-W10: inventory `skills[]` validation skipped consumed fields
**Fixed in** `0375e37`. Rows need string `root`/`real_dir`/`description`, a known `root_kind`, a null or `~/` `real_dir_home`, and a valid `name` and `plugin` when addressable. A non-addressable row may still carry a bad plugin name (real inventories do).

### C-W11: unverified facts reached plan entries at full confidence
**Fixed in** `e2d778e`. `agent_skills.<agent>` entries carry an `effect` when a wired skill is a plugin row (layering unverified) and when jev rests on `url_reachable` alone. Claude goldens gain the plugin effect.

### C-W12: failed and empty model listings collapsed into a ceiling reason
**Fixed in** `3132215`, pyright fix `afdaf08` (requires human verification).
- Inventory records `runtime_enumeration` (`failed`/`empty`/`ok` per installed runtime; optional and validated when present).
- `recommend._exec_targets` replaces the why of a target with an empty pool: "no <runtime> models enumerated (listing failed|empty)". The pick itself stays in `cross_ai.py` (batch A); only its why is overridden.
- `_no_lane_reason` tests for an installed non-host lane binary.

### C-W13: vacuous negative jev tests
**Fixed in** `680d93a`.
- Both jev tests and `test_missing_skill_never_named` declare the family agents and assert the positive counterpart wires.
- `make_inventory` now copies `agent_to_phase_type`: tests that added agents were mutating the shared `TABLES`.

### C-W14 and skill-judge I1..I7, M1..M7: SKILL.md vs the CLI
**Fixed in** `0bb9caf`.
- I1: one message with four questions (profile, rigor with what each level changes, cross-AI review y/n/default, execution y/n/default); placeholders, never fixed values.
- I2: an exit-code table per path; v2 exit 2 is a refusal you fix and re-run.
- I3: inventory redirected into a scratch dir outside `.planning/`; `recommend --out` refusal and the sibling `inventory.json` default documented. Also states that shell variables do not persist between tool calls (record `$ENTRYPOINT`/`$WORK` literally), a gap the review did not list.
- I4: no `--force` in any example; a NEVER item says what it bypasses.
- I5: NEVER run v1 `apply-execution`/`apply-review` on a v2-configured project.
- I6: the machine-specific ponytail bullet is replaced by `ponytail_visibility` guidance (D-35 amended). "This maintainer's machine" removed from Limits.
- I7: v1 safeguards restored (`ensure-project` first, detect output passed through, skip a null `claude_md_path`, `--model <detected model>`).
- M1 `"$ENTRYPOINT"` everywhere; M4 System One defined; M5 runner pseudo-keys; M6 v2 trigger phrases in the description; M7 Why column.
- M2 and M3: the suggested wordings were wrong against the code, so the true behavior is documented instead. The runner uses the **smaller** of the live and baked timeouts (`Math.min` in `cross-ai.mjs`), and `apply --dry-run` does not check the marker (the next `apply` refuses with exit 2 and prints the recovery steps).
- Batch B hand-off: `predicted` dry-run rows, `--fingerprint` in `approve_with`, and the trusted-root drop refusal are documented.
- C-W14 item 4: README and SKILL.md now say config keys go only through gsd-tools and a failed apply restores the backup bytes directly.
- The drift test reads `"$ENTRYPOINT"` lines, fills choice placeholders with valid values, strips a stdout redirect, and pins the new statements, no `--force` in examples and no machine-specific claims.
- **Skill-judge result:** 106/120 (B), self-scored with the skill-judge rubric after the fixes; no Critical or Important finding left. D1 17/20, D2 13/15, D3 13/15, D4 14/15, D5 12/15, D6 14/15, D7 9/10, D8 14/15. Baseline 104, so no regression. SKILL.md is 280 lines (the drift test pins no line budget). This is not an independent score: no other reviewer was run in this unattended batch, so a cross-AI re-score is still worth doing.

### C-IN-01: `re.match` with `$` accepted a trailing newline
**Fixed in** `f4563ac`.

### C-IN-02: the purity test skipped the skills layer
**Fixed in** `11acbe9`.

### C-IN-03 / PT-13: dead and redundant code in `skills.py`
**Fixed in** `0bfdb42`. `trusted_roots` returns the candidates only; `existing_roots` uses `presets.get_dotted`; `_escaping_project_only` is gone.

### C-IN-04: `ponytail_visibility` used `home=""`
**Fixed in** `42f6947`. Took the "document it" option: the field covers each host's global skills root only, and it now gets the real home.

### C-IN-05: `_tcp_reachable` caught only `OSError`
**Fixed in** `4531f32`. Catches `(OSError, ValueError)` rather than `Exception`: that covers the IDNA `UnicodeError` without a broad-except allowlist entry in arch rule 9. The slow-connect fake returns a closable socket.

### C-IN-06: `test_empty_agent_no_entry` asserted an impossible outcome
**Fixed in** `dad1ed2`.

### C-IN-07: hardcoded runtime list in the node query; silent null host root
**Fixed in** `61b3b86`. `GsdCorePaths.skills_hosts` carries `host.HOSTS` (passed in, since `host` imports `gsd_catalog`) as `argv[5]`; inventory warns when the current host's root is null. The real-node e2e query passes.

### C-IN-08: a `/` root covered everything
**Fixed in** `46b1d41`. `/`, `~` and the home dir (inferred from the row's `real_dir_home`/`real_dir`) never cover, as in gsd-core's `loadTrustedGlobalRoots`.

### C-IN-10: inventory's TCP probe undocumented
**Fixed in** `0bb9caf` (SKILL.md trust-model section).

### C-IN-11: unset HOME read a cwd-relative secrets file
**Fixed in** `2c9066b`. Took the "skip the file" option: falling back to `expanduser` would make the unit tests read the real home's `~/.config/ai-kit/secrets.env`.

### PT-08: three skill-name regexes and a copy of `locate`
**Fixed in** `4fdcbad` (requires human verification). `plan_io` uses `skill_scan.SKILL_NAME_RE`; `plan-set` admits a skill only when `skills.unwired_reason()` would wire it. That also refuses an uncovered outside-home global skill, which recommend never wires and gsd-core skips.

### PT-09: two candidate lists for the same runner choice
**Fixed in** `569baa3`. `plan_edit.runtime_candidates` uses `roles.choice_candidates` under the plan rigor's price ceiling, like recommend.

### PT-12 (batch B hand-off): `skill_scan._read_json`
**Fixed in** `d79534f`, partly. It cannot reuse `plan_io.read_json_object`: `plan_io` now imports `skill_scan` (PT-08), so that would be an import cycle. It keeps its own six lines but now also treats a `RecursionError` as a bad file.

### PT-14: cross-AI targets computed up to five times
**Fixed in** `7d10a48`. `PlanCtx` carries `targets` and `answers`; the two no-lane branches merged. Goldens unchanged.

### PT-16: duplicated test helpers
**Fixed in** `55789a7`.

## Skipped

### C-IN-09: rigorous review with no vendor-different second lane gets no note
**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py` (`select_lanes`)
**Reason:** batch A file; this batch was told not to touch it. The fix is still open: add the "only one eligible review lane" note when `second_ranked` is empty.

### PT-10: the declared-router filter written twice
**File:** `cross_ai.py:46-55` and `cross_ai.py:210-220`
**Reason:** batch A file, left for that batch.

## Files outside the batch C list touched
- `plan_io.py`: C-W10 row validation, C-W12 `runtime_enumeration` validation, PT-08 shared regex.
- `plan_edit.py`: C-W8 list candidates, PT-08 (beyond the PT-09-only allowance; both are those findings' own fix sites).
- Tests: `test_curated_config_{apply,apply_e2e,followups,plan_edit,inventory,recommend,e2e}.py`, and the three claude goldens.
- `18-CONTEXT.md`: D-31, D-35 and D-41 amendments. `README.md`: the curated-config row.

No batch A file was touched: `references/cross-ai.mjs`, `cross_ai.py`, `cross_ai_script.py` and `ai_kit_spec/detection.py` are unchanged.

## Handed to batch A
- C-IN-09 and PT-10 in `cross_ai.py`.
- Optional: the C-W12 cause override in `recommend._exec_targets` could move into `cross_ai._pick_for_runner` once batch A owns that file.

---

_Fixed: 2026-10-15_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
