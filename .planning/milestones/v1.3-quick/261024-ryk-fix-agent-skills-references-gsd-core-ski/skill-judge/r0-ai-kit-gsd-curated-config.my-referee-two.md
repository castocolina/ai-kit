# Skill Evaluation: ai-kit-gsd-curated-config

**Pattern:** Tool (decision tables, exact commands, refusal matrices, low freedom) · **SKILL.md:** 337 lines · **References:** runner.md (64), v1-path.md (47), both with conditional load triggers · **Knowledge ratio:** E:A:R ≈ 85:12:3

## Focus check: the 5b4ec21..HEAD change

The claim "the skill references only agent_skills entries gsd-core will actually resolve" **holds, verified against the real gsd-core source**:

- gsd-core skips an escaping `global:<name>` unless a trusted root covers it — confirmed in `.claude/gsd-core/bin/lib/init.cjs` (`buildAgentSkillsBlock`, ~line 3710: `failed path check (symlink escape?) — skipping`).
- Trusted-root semantics claimed by SKILL.md are exact: `.claude/gsd-core/bin/lib/security.cjs:166-176` drops non-existent roots ("a non-existent root is not trustworthy"), rejects non-absolute-after-expansion, filesystem root, and homedir itself, and canonicalizes via `realpathSync`. The Python mirror (`skill_scan.py:123-131`) realpaths both sides, and `skills.py:186-201` (`covered`) skips the same too-broad roots.
- Enforcement is a closed loop, force-immune at every gate: recommend wires only resolvable refs (`skills.py:255-267`), `plan-set`/`plan-unset` refuse edits leaving a skipped ref (`plan_edit.py:182-192`, called unconditionally after force handling), and `apply` + `apply --dry-run` refuse before any write (`apply.py:907-909`, shared `prepare()` used by both, `cli.py:669`). All pinned by tests (`test_curated_config_plan_edit.py:1071,1103,1238,1263`; `test_curated_config_apply.py:681` — the latter proves a hand-edited plan is refused with the tree byte-identical).
- Plugin skills can't leak the gate: plugin rows only exist when `host_name == "claude"` (`skill_scan.py:280-284`), matching gsd-core's claude-only directive path.
- Not-installed names excluded from this gate are refused by `skill_value` instead (`apply.py:92-101`) — no hole.

## Dimension scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 18 | 20 | Nearly pure expert-only content (gsd-core skip semantics, marker recovery, `.new`/template floors). Minor redundancy: "redirect to a file" mistake row, entrypoint-resolution boilerplate. |
| D2 Mindset + Procedures | 13 | 15 | "Ask yourself" trust-model frame + non-obvious procedures (dry-run in a separate turn, fingerprint-bound approvals). Largely procedural gating rather than broader decision philosophy — right for the pattern. |
| D3 Anti-Pattern Quality | 14 | 15 | Specific NEVER list with non-obvious WHY (full-permissions command keys, v1-after-v2 clobbering, `.new` as active) + failure-signature mistake table. |
| D4 Specification Compliance | 15 | 15 | Valid name; description has WHAT/WHEN/KEYWORDS with quoted trigger phrases and explicit positioning vs `gsd-settings`/`gsd-config`. |
| D5 Progressive Disclosure | 13 | 15 | 337 lines (over the <300 ideal); references carry scenario-conditional triggers ("read only when…"), but no explicit "Do NOT load" line. |
| D6 Freedom Calibration | 15 | 15 | Fragile config/trust operation → exact commands, verbatim relay rules, unchanged-approval-string requirement. Freedom granted exactly where safe (the four questions, candidate choice). |
| D7 Pattern Recognition | 9 | 10 | Masterful Tool-pattern application; slightly over the pattern's nominal size. |
| D8 Practical Usability | 13 | 15 | Exit-code table, failure states, refusal messages that print their own fix commands, eval scenarios pinned by tests. Deductions for the findings below. |

## Findings

**Critical:** none.

**Important:** none.

**Minor**

1. `plan_io.py:626-631` (`_skip_message` keep-fix) — the printed `plan-set agent_skills.<agent> '["…"]'` remediation reduces every kept item to its last `[:/]` segment, so a kept `global:<name>` ref becomes a bare name that apply re-resolves project-first (`skills.py:147-153`), silently wiring a project copy where the config named the global one. Only reachable via the `plan-unset`-of-a-keep-entry refusal, plan-set's bare-name domain makes ref-preservation inexpressible, and the dry run shows the resolved refs — but the refusal text itself doesn't flag the change. Fix: when any kept item contains `:` or `/`, append one clause to the refusal noting kept references re-resolve by name.
2. `SKILL.md:35` — the v2 exit-2 row enumerates refusal causes but omits the new "apply refused: gsd-core would skip …" class (only the Skills section documents it). Fix: add "skipped `agent_skills` reference" to that enumeration.
3. `SKILL.md:308-310` duplicates `references/v1-path.md:3-5` (v1-overwrites-v2-runner warning) nearly verbatim; the SKILL.md NEVER line could reference the file instead. Keeps SKILL.md nearer the 300-line ideal.

Skipped: runtime execution of the pipeline (read-only mandate) — correctness of the enforcement chain rests on code reading plus its tests. Residual risk: the trusted-root path is verified at inventory time; if the install dir vanishes before apply, gsd-core drops the root at use and the skills skip silently (inherent TOCTOU, digest-gated window).

DIGEST fb2186c9cbe3f86b
CURRENT 110/120
CRITICAL 0 IMPORTANT 0
