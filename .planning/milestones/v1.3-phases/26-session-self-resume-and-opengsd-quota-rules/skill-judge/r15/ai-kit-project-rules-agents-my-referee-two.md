Judge: my-referee-two
Reviewed-sha256: 60db9a1a8f05bffe2dafe21132a78e4812cf7f3e66a557df61682947ebc3f475
Lane: AIKIT-XAI status=ok cli=pi model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=311s out=7392 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 93
Critical: 1
Important: 2

# Skill Evaluation Report: ai-kit-project-rules-agents

## Summary
- **Total Score**: 93/120 (78%)
- **Grade**: C
- **Pattern**: Process
- **Knowledge Ratio**: E:A:R ≈ 75:15:10
- **Verdict**: A dense, mostly accurate house-rule wrap procedure, but the unattended restore path it mandates will destroy a dirty AGENTS.md, and Step C's phrase thresholds are stated as if they applied to every rule.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 17 | 20 | Classifier thresholds, trust gate, R20 rewrite, and false-present short signals are genuine engine knowledge |
| D2: Mindset + Procedures | 13 | 15 | Ordered A–D workflow the model would not invent; little "ask yourself" framing, which this fragile op does not need |
| D3: Anti-Pattern Quality | 13 | 15 | Seven specific NEVERs with reasons; two of them are contradicted by the procedure itself |
| D4: Specification Compliance | 14 | 15 | name valid; description has WHAT, WHEN, keywords, and the all-skill handoff |
| D5: Progressive Disclosure | 11 | 15 | 157 lines, self-contained, but the body re-explains output keys the JSON already carries |
| D6: Freedom Calibration | 12 | 15 | Low freedom matches a substring classifier; the unattended restore branch is the wrong constraint |
| D7: Pattern Recognition | 8 | 10 | Clear Process pattern; Step C is three overlapping cases rather than one decision tree |
| D8: Practical Usability | 5 | 15 | Unattended restore is destructive; phrase-threshold text mis-classifies R19/R20; check-only vs "reach refactor" conflict |

## Critical Issues

1. Unattended Step D restores a dirty file from git HEAD and throws away the user's uncommitted content. SKILL.md:135 says that if the diff shows anything outside the Step B clauses, restore every `FILES` entry with `git restore` for a `clean` file. `clean` is defined at SKILL.md:104 as tracked and unmodified at backup time, so `git diff` is against HEAD and includes every uncommitted edit already in the file. An unattended run that also inserts a clause, or that rewrites an R20 line, will see those prior edits as "outside Step B" and `git restore` them. The backup script at SKILL.md:97–101 never copied that file.

## Important Issues

2. SKILL.md:115 states phrase thresholds as a universal insertion rule ("a flat list needs all its phrases, or at least half rounded up when it has three or more; a list of lists needs one phrase from each inner list"). `classification.py` applies the half-of-three rule only inside `_classify_flat`. R19's signals are plain groups of 1–2 phrases (`rules.py` R19), so one phrase from a two-phrase group is enough and "at least half of a flat list" does not apply; R20's generic groups are checked by `_classify_plain_groups`, then overridden by `_stack_form_status` and `hardcoded_worker_counts`. An agent following line 115 can under-insert R19 or believe the generic sentence alone makes R20 `present`.

3. SKILL.md:71 says a check-only request reports and stops, and that Steps A–D "reach `/agent-md-refactor` only when the Step B list is non-empty." SKILL.md:93 says an empty Step B list with broken `links` still backs up and edits by direct edit, then runs Step D. An audit that also has broken links gets edited on the first reading and not on the second.

## Top 3 Improvements

1. Change SKILL.md:135 so unattended restore uses only the pre-flight copies, and so a `clean` file is restored from `HEAD` only when HEAD itself was snapshotted (or stop calling a dirty worktree file `clean`).
2. Rewrite SKILL.md:115 per signal shape: flat → `_classify_flat`; plain groups including R19 → one phrase per inner list; R20 → generic groups plus every selected `PARALLEL_TEST_FORMS` row signal plus zero `hardcoded_counts`.
3. Reconcile SKILL.md:71 with SKILL.md:93: check-only never edits, including link repair; link repair is a fix-path Step B branch only.

## Detailed Analysis

### D1 Knowledge Delta — 17/20
Scope (line 9), the candidate loop (lines 19–28), the GSD trust gate (line 37), the one-hop/20-link/fence rules (line 49), R20's generic sentence (line 85, matches `PARALLEL_TEST_GENERIC` in `tool_catalog.py:861`), and the short-signal false-present warning (line 143: `rg`, `bat`, `kill`, `tmp/`) are things the model cannot infer. Some payload-key narration (lines 53–56) restates fields the JSON example already shows.

Checked against the repo and held: AGENTS.md wins over CLAUDE.md (`cli.py:174–180`); remediate drops links (`remediation.py` never reads `links`); `blocked` is empty for this skill (`STRUCTURAL_KINDS` has no workflow); R02 category is `makefile` while signals are non-empty (`rules.py` R02; `classification.py` `check_rules` filters on signals); R18/R19/R20 are `verbatim: True`; sibling-missing probe reason matches `gsd_identity.py`; launcher order matches `gsd_tools.py:86–93` and `project_root` does `git rev-parse`.

### D2 — 13/15
Steps A–D are a real domain procedure: confirm near-misses before any refactor, one whole-file pass, re-check, keep-or-restore. The "why not the contradiction phase" note (line 87) is the right expert distinction.

### D3 — 13/15
The NEVER list is specific and reasoned (substring matching, no semantic credit, one refactor pass, category does not route). It loses points because line 143's "read the matching line before calling it compliant" fights line 71's check-only stop, and the restore command at line 135 is itself an anti-pattern.

### D4 — 14/15
Frontmatter name is lowercase and within 64 characters. Description states the audit and the fix, names AGENTS.md, CLAUDE.md, house rules, workflow rules, broken links, and routes "check everything" to `ai-kit-project-rules-all` (that skill exists). Slightly buried WHEN, not missing.

### D5 — 11/15
No references directory; 157 lines is acceptable for a process skill. There is no "read rules.py now / do not read tool_catalog unless R20" trigger, and the output-shape section duplicates the example JSON.

### D6 — 12/15
Exact scripts and verbatim insertion are right for a literal matcher. Freedom is mis-set on the unattended branch: any unexpected diff triggers a full restore, including of content the backup never saved.

### D7 — 8/10
Process pattern is recognizable (phased, checkpointed, medium-low freedom). Step C's three cases (lines 123–127) overlap: "skill not found" and "no dispatch mechanism" are not mutually exclusive as written, and line 110 says "direct edit by default" while the bullets prefer the refactor whenever it is installed.

### D8 — 5/15
Common attended path is usable: check, remediate, confirm, one pass, re-check. The unattended and R19/R20 paths are not safe to follow literally (findings 1–2). Minor extra gaps that did not each become findings: line 37 says the probe "never appears" with the flag and "prints nothing" when siblings or gsd-tools are missing, but `cli.py:216–217` prints `ai-kit: gsd identity probe ran <path>` whenever `tools_path` is set, including the "node not on PATH" return that happens before the node process runs (`gsd_identity.py:96–102`); and line 49's "every rule whose condition is met reports missing" is true only when the root file is absent — a missing file plus linked-file text is not what `_resolve` returns (`cli.py:184–196`).
