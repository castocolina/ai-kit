Judge: my-referee-two
Reviewed-sha256: a0d23c0d4767515f02cdee66fc698a9a5a7f81ecc093893a8f36966bc4321852
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=391s out=146946 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 99
Critical: 0
Important: 2

# Skill Evaluation Report: ai-kit-project-rules-all

**Grade: B** (99/120, 82.5%) · **Pattern**: Tool/orchestrator · **Knowledge ratio**: E:A:R ≈ 85:10:5 — nearly everything is repo-specific orchestration knowledge; the redundancy is repetition of the same expert point, not beginner filler. All load-bearing factual claims I could check against the repository verified true (log at the end).

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 16 | 20 | Pure orchestration delta (fan-out contract, D-04/D-05 semantics, tie-break, hand-off), diluted ~10% by a 4×-repeated invariant |
| D2: Mindset + Procedures | 12 | 15 | Checkout-first resolution order, failure-degradation contract, hand-off sequence — all non-generic; little "how to think" framing |
| D3: Anti-Pattern Quality | 13 | 15 | Five mechanism-grounded NEVERs (dispatch-order stability, no re-implementation, host-neutral paths); two overlap the repetition problem |
| D4: Spec Compliance | 15→11 | 15 | Excellent WHAT/WHEN/KEYWORDS + routing-away guidance, but the unquoted `: ` makes the description invalid YAML under strict parsers (Finding 1) |
| D5: Progressive Disclosure | 12 | 15 | 221 lines, self-contained, no orphan references; repetition is the only layering sin |
| D6: Freedom Calibration | 13 | 15 | Copy-paste-exact where fragile (resolution snippet, subcommands), principles where flexible (reporting); well matched |
| D7: Pattern Recognition | 9 | 10 | Clean Tool pattern, consistent with the 7-skill family |
| D8: Practical Usability | 13 | 15 | Commands verified live; both JSON examples verbatim-real; docked for unexplained D-xx/SC-x codes |

## Findings

1. **Important — SKILL.md:3**: The `description:` plain scalar contains `: ` ("…never a single-domain question: this skill subprocess-fans-out…"). YAML 1.2 §7.3.3 forbids `": "` inside a plain scalar in block context; strict parsers (PyYAML, Go `yaml.v3`, js-yaml) raise "mapping values are not allowed here", so on a conformant host the whole skill fails to load — the Invisible Skill failure. Mitigating, verified context: five sibling SKILL.mds in this repo share the pattern and the repo's own tooling hand-parses frontmatter line-wise (`tools/setup.py`, description extractor) rather than YAML-parsing it, so the hosts uz uses evidently tolerate it. **Fix**: wrap the value in double quotes (escaping the inner `"check everything"`-style quotes) or use a `>-` block scalar.
2. **Important — SKILL.md:10-17, 83-88, 192-196, 211-213**: The "zero re-derivation / fields arrive exactly as the sibling produced them / only `hand_off` is added" invariant is stated four times (Scope, Run-the-check prose, Limit 8, NEVER #4), plus a fifth related statement at 153-156. ~20 lines of a 221-line file re-say one fact; four copies must be kept in sync or a future editor updates one and drifts the rest. **Fix**: state it once in Scope; elsewhere reference it ("per Scope, no field is re-derived") or delete.
3. Minor — SKILL.md:66, 75, 78, 83, 129, 166: Plan/test codes (D-02, D-04, D-05, D-06, SC2, SC3, SC4) are used as if meaningful, with no in-file legend; each is only rescued by appositional prose. Drop the codes or define them once.
4. Minor — SKILL.md:137-147: Claims the sibling's Wrap-mechanism section is pointed at "BY NAME rather than restating it", then restates Step A/B/C anyway. Keep one of the two.
5. Minor — SKILL.md:62-63: `<repo_root>` reads as required, but the CLI defaults to `"."` (`ai_kit_project_rules_all/cli.py:43,47`). Harmless; note the default.

## Claims verified against the repository

- Six sibling skills exist with the stated names/kinds (`skills/` listing; `DOMAIN_ORDER`, `dispatch.py:25`).
- `check`/`remediate` four-key shape, notices unsorted concat, global criticality sort, `failed` mutually exclusive — `aggregate.py:37-53`; D-04 byte-identical — `cli.py:26-34`; D-05 shape — `dispatch.py:95-139`; 30 s sequential timeout — `dispatch.py:40,108,146`; 5-candidate checkout-first resolution, never `$PATH` — `dispatch.py:50-80`; `hand_off` set only on `workflow` `remediate` entries — `aggregate.py:49-51`.
- CLI usage/exit codes — `cli.py:38-40,50-51` exactly as SKILL.md:120-122 claims.
- Both example findings are real: R01 summary verbatim in `ai_kit_project_rules_agents/rules.py:51-60` (criticality 1 = `CRITICALITY_CRITICAL`), arch entry verbatim in `ai_kit_project_rules_arch/arch_checker.py:145-160` (criticality 2 = `CRITICALITY_HIGH`, `criticality.py`); `id` mapping via `shared remediation.py:120-129`.
- Hand-off Steps A/B/C cross-reference — `ai-kit-project-rules-agents/SKILL.md:51,57,59,61`; `(kind, id, issue)` is the shared builder's documented rule — `skills/_shared/ai_kit_rules_common/remediation.py:75`; a sibling `cache-update` subcommand does exist (precommit `cli.py:1,59`), grounding the no-caching limit.
- Live read-only `check` run against this repo: exit 0, four keys, entries from several domains (workflow/makefile/precommit/arch + blocked), global sort correct, `hand_off` present on workflow entries only — confirms SKILL.md:126-131.

**Verdict**: a factually accurate, well-calibrated orchestrator skill whose only real defects are an encoding-level frontmatter risk and internal repetition — both cheap fixes.
