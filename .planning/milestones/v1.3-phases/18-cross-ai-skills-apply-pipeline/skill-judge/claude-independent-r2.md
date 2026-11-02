# Skill-judge (independent, R2): ai-kit-gsd-curated-config/SKILL.md

- Target: `skills/ai-kit-gsd-curated-config/SKILL.md` at HEAD 72fd95d (282 lines, no `references/`; the runner template it describes is `skills/ai-kit-spec-review/references/cross-ai.mjs`, loaded by `cross_ai_script.load_template()`, not by the agent)
- Baseline: the same file at d164697 (194 lines, v1-only flow)
- Not read before scoring: 18-SKILL-JUDGE.md, 18-REVIEW-FIX-C.md
- Method: skill-judge 8 dimensions; every command, flag and behavior claim checked offline against `cli.py` (argparse + handlers), `apply.py`, `plan_edit.py`, `plan_io.py`, `followups.py`, `config_backup.py`, `presets.py`, `cross_ai.py`, `skills.py`, `skill_scan.py`, `host.py` and `references/cross-ai.mjs`. No live CLI run.

## Claim verification (HEAD)

All checked claims hold:

- Subcommands and flags match argparse exactly: `inventory --project-dir [--host {HOSTS}] [--refresh]`; `recommend --inventory --profile --rigor --out [--cross-ai-review y|n] [--cross-ai-exec y|n]`; `plan-set key value --plan [--inventory] [--force]`; `plan-unset key --plan [--inventory]`; `apply --plan --inventory --project-dir [--dry-run]`; `followups --plan --inventory --project-dir [--approve --require --fingerprint]`; the v1 required/optional flags (`apply-execution` `--cli/--model` optional, `apply-review` required; the `detect-*-candidate` pair takes no flags).
- Rigor text matches `presets.py`: PRICE_PERCENTILE 0.40 / 0.75 / None, SKILL_CAPS 2/3/5, PHASE_SHIFTS mvp research+verification on haiku and rigorous planning on opus, `cross_ai.REVIEW_COUNT` rigorous = 2. An omitted `--cross-ai-*` flag gives `defaulted: True` (`recommend.cross_ai_answers`).
- `--out` refusal inside `.planning/` and onto input/config files (`plan_io.out_path_problem`). `plan-set`/`plan-unset` fall back to the sibling `inventory.json` (`plan_io.sibling_inventory_path`).
- Value parsing (`plan_edit.parse_value`): `agent_skills.*`, `review.default_reviewers` and trusted roots need a JSON string list; bool/int follow the current value; strings are bare text.
- Script pseudo-keys `script:cross-ai.model.<runner>` / `script:cross-ai.prefer`. Unsetting a runner model reopens `choices.<runner>`. Effort is pinned through `cross_ai.exec_effort` (target `medium`, clamped to the model's modes, pi/codex only). The runner passes `--thinking` / `-c model_reasoning_effort=`.
- Trusted-roots drop refusal prints a merged `plan-set` payload. `--force` bypasses exactly the candidate check, the trusted-root drop refusal and the `workflow.cross_ai_command` full-permissions guard.
- Apply refuses while `needs_choice` remains and on a digest mismatch. The dry run lists predicted `remove` rows only when no config exists, and does not check the marker (`prepare()` never reads it). A held marker makes the real apply return 2 with `recovery_text`. Marker/snapshot suffixes are `.ai-kit-apply-marker` / `.ai-kit-apply-backup`. A failed rollback reports `restore_error` with exit 1. Committed cleanup failures are only warnings, with exit 0.
- `followups`: `approve_with` is `shlex.join` starting at the subcommand. It carries `--require <comma ids>` and `--fingerprint` (sha256 over id/argv/cwd). A mismatched fingerprint or a held marker returns 2. A failed command returns 1. Effort sync is suppressed for workstream configs.
- Runner: one last-line `AIKIT-XAI status=…`. Bare profile: pi `--no-skills --no-extensions`, opencode `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`. Codex exec uses `--dangerously-bypass-approvals-and-sandbox`, and opencode exec uses `--auto`. The live timeout is `Math.min(CONFIG.outerTimeoutS, liveOuterTimeoutS())` with the GSD_WORKSTREAM ladder. Other details: `extraArgs` per CLI, `--print-argv`, and status `unverified` when git fails.
- Inventory: one TCP connect to the `JEV_API_URL` host (`socket.create_connection`). Jev is also detected by `JEV_API_KEY`. The host-detection failure message tells the user to pass `--host`. The "not wired" skill rules match `skills.unwired_reason`.

No false claim found. A few omissions are listed under Minor.

## Scores

HEAD (72fd95d):

- D1 Knowledge Delta: 18/20. Nearly all content is non-derivable CLI and failure-state knowledge: committed-with-warnings vs. `restore_error`, `.new` not active, a v1 `apply-execution` silently orphaning the runner, `approve_with` needing the entrypoint prefix, and predicted remove rows. Small deductions for internal IDs an installed agent cannot resolve (`D-21`, "Phase 20", "System One") and the low-value `ponytail_visibility` bullet.
- D2 Mindset + Procedures: 13/15. The "Before the first command, ask yourself" block (trusted checkout? last written by v1? where do the inputs live?) plus the exact domain pipeline. Thinking framing is thinner past step 1.
- D3 Anti-Patterns: 14/15. The NEVER list is specific and each item has a reason (habitual `--force`, v1-over-v2, marker deletion, `.new`), and the common-mistakes table gives a "why" for each row.
- D4 Spec / Description: 14/15. Valid name. The description covers what, when, trigger phrases and a "not a replacement" boundary. Small deduction: pipeline jargon ("v2 flow — inventory → recommend …") spends description budget that trigger terms such as "GSD model profile" or "rigor" could use.
- D5 Progressive Disclosure: 12/15. 282 self-contained lines with no `references/`. The secondary v1 path (~27 lines) and the Limits table are always loaded, though they are needed only in narrow cases.
- D6 Freedom Calibration: 14/15. Low freedom where mistakes are costly (verbatim `approve_with`, never restore after a committed apply, `--force` only on an explicit user choice). Medium freedom for the user Q&A.
- D7 Pattern: 9/10. A clean Process/Tool hybrid: phased flow, then subcommand reference, NEVER list, common mistakes and reporting rule.
- D8 Practical Usability: 13/15. Exit-code table, failure states, fallbacks and drift-tested commands. Gaps are listed under Minor findings M1-M3.

**HEAD total: 107/120 (89%, grade B+).**

Baseline (d164697):

- D1 15/20: accurate v1 knowledge (silent sparse-config footgun, ladder semantics), but the same footgun is explained three times in long prose.
- D2 12/15: has "ask yourself" framing, with a strict detect → show → apply order.
- D3 13/15: good NEVER list. The "never ask more than one question" item is policy more than hard-won knowledge.
- D4 14/15: rich description, accurate for v1.
- D5 11/15: 194 lines, no references, with heavy duplication between prose and table.
- D6 14/15: appropriate low freedom.
- D7 9/10: clear Process pattern.
- D8 12/15: correct for v1. However, `inventory`/`recommend` already existed in that commit's `cli.py` and are undocumented.

**Baseline total: 100/120** (an earlier independent judge gave 104). HEAD is above both figures, so there is no regression.

## Findings

Critical: none.
Important: none.

Minor (each with fix text):

- **M1, empty follow-ups not covered** (`followups.build_followups`). Problem: `approve_with` is `""` when `required` is empty, and the `recommended` block (for example `/gsd-map-codebase`) is never mentioned. If `_attach_followups` raised, the report has no `followups` block, only a warning. Fix, appended to step 6: "If `required` is empty, ask nothing and skip approval. Always relay `recommended` items as suggestions. If the report has no `followups` block (warning 'follow-ups could not be listed'), run the listing command above."
- **M2, how `workflow.cross_ai_command` / `artifact:` needs_choice clears.** Problem: step 3 says "resolve with `plan-set` or decline with `plan-unset`". For these two rows, `plan-unset workflow.cross_ai_command` is refused while execution is on. They clear only when every runner in `artifacts[0].choices` has a model. Fix, a bullet under step 3: "`workflow.cross_ai_command` and `artifact:.planning/scripts/cross-ai.mjs` stay open until every runner in `artifacts[0].choices` has a model. To drop a runner, `plan-set script:cross-ai.prefer` without it. To drop execution, `plan-set workflow.cross_ai_execution false`."
- **M3, the trusted-roots refusal prints a partial command** (`plan_edit._check_trusted_roots`). Problem: the printed command lacks the entrypoint and `--plan`. Fix: change "the refusal prints the merged command" to "the refusal prints the merged list; re-run `plan-set` with it (add `--plan`)".
- **M4, v1 exit-2 cause missing.** Problem: `apply-execution`/`apply-review` also return 2 on an unrecognized `--cli`, before any write. The baseline documented this; HEAD dropped it. Fix: add "or an unrecognized `--cli`" to the v1 exit-2 cell.
- **M5, internal identifiers.** Problem: `D-21`, "until Phase 20" and "System One" mean nothing to a portable installed skill. Fix: drop `(D-21)`, write "unverified" without the phase number, and write "the jev backend" instead of "System One".
- **M6, D5 polish (optional).** Fix: move the v1 path and the Limits table to `references/v1-and-limits.md`. Load it only when the user explicitly asks for v1 or a limit row applies, and do NOT load it for a normal v2 run.

## Verdict

**PASS.** No Critical or Important finding remains, HEAD scores 107/120 (≥ 96), and there is no regression against the baseline (100 by this judge, 104 by the earlier judge).
