# 09-02 Task 2: `/skill-judge` evidence

Date: 2026-09-13

BASELINE_SOURCE: cc922e4f06219571192e77053efb24d171c3c1ab:skills/ai-kit-agents-md-rules-checker/SKILL.md
BASELINE_JUDGED_PATH: ./tmp/ai-kit-agents-md-rules-checker/SKILL.md
BASELINE_SCORE: 100/120
PRUNED_SCORE: 102/120
PRUNED_CRITICAL: 0
PRUNED_IMPORTANT: 0

## Method

Both runs were performed by the same judge (this executor, running the installed
`/skill-judge` skill's rubric) in one session, against two documents:

- **Baseline**: the pre-phase `SKILL.md` blob recovered with
  `git show cc922e4f06219571192e77053efb24d171c3c1ab:skills/ai-kit-agents-md-rules-checker/SKILL.md`
  (the parent of `9d672b9`, plan 09-01's rename commit — the last commit in which
  this skill still carried its old directory name). Written to
  `./tmp/ai-kit-agents-md-rules-checker/SKILL.md` — a directory whose basename
  (`ai-kit-agents-md-rules-checker`) was confirmed, before judging, to equal the
  recovered blob's own frontmatter `name:` (`name: ai-kit-agents-md-rules-checker`).
- **Pruned**: the current `skills/ai-kit-project-rules-agents/SKILL.md`, at Task 1's
  commit (`11e4791`).

### Packaging/naming dimension check (required by this task before Step 2)

The installed `/skill-judge` SKILL.md (`/home/bazzite/.claude/skills/skill-judge/SKILL.md`)
was read in full before scoring either document. Its 8-dimension, 120-point rubric
(D1 Knowledge Delta, D2 Mindset+Procedures, D3 Anti-Pattern Quality, D4 Specification
Compliance, D5 Progressive Disclosure, D6 Freedom Calibration, D7 Pattern Recognition,
D8 Practical Usability) does **not** contain a distinct dimension that compares a
`SKILL.md`'s frontmatter `name:` against its containing directory's basename. D4
("Specification Compliance — Especially Description") checks `name:` format
(lowercase, alphanumeric+hyphens, ≤64 chars) and description quality (WHAT/WHEN/
KEYWORDS), but nothing in D4 or any other dimension reads or scores the parent
directory at all. Confirmed by reading the full rubric text and grepping it for
"directory"/"packaging"/"consistency" — the only "directory" hits are about a
skill's own `references/` subdirectory (D5), unrelated to packaging/naming.

This is recorded here as a factual finding, not worked around: no "both runs'
packaging/naming dimension score" can be reported because the installed skill does
not produce one. The directory-correct layout from Step 1
(`./tmp/<old-skill-dir-name>/SKILL.md`, basename == blob's own `name:`) was still
followed exactly as specified, since it is harmless and is what the Task 2 gate's
`git`-derived layout check (`BASELINE_JUDGED_PATH` vs `BASELINE_SOURCE`'s `name:`)
verifies regardless of whether the installed rubric itself rewards it.

## Per-dimension scores

| Dimension | Baseline | Pruned | Max | Note |
|---|---|---|---|---|
| D1 Knowledge Delta | 18 | 18 | 20 | Dense expert content in both; pruned drops no knowledge-delta, just scope. |
| D2 Mindset + Procedures | 13 | 12 | 15 | Baseline's "Deciding Step D's option 1 vs 2" section was a standalone context-dependent decision framework; its removal (the branch point itself left with Step D) costs one point of explicit mindset-framework content even though the remaining Step A/B/C procedures are unchanged and still carry real judgment (Step A's confirm/decline, named evidence). |
| D3 Anti-Pattern Quality | 13 | 12 | 15 | Baseline has 5 anti-patterns; pruned has 4 (the Step-D-guarding "no bare tool-name guess" bullet correctly left with Step D). All remaining bullets in both are specific and reasoned; the R02 rewrite in pruned is, if anything, more precise (names `check_workflow_rules`, `signals`, `category` explicitly). |
| D4 Specification Compliance (description) | 13 | 14 | 15 | Baseline's description tries to cover two routing surfaces (AGENTS.md rules AND Makefile/pre-commit target shape) in one compound WHEN clause -- exactly the two-owner ambiguity this phase exists to close, and a docked point for diluted WHEN clarity. Pruned's description is single-scope, crisp, unambiguous. |
| D5 Progressive Disclosure | 10 | 13 | 15 | Baseline inlines Step D's full research-dispatch protocol (`ALL_TOOLING_KEYS`, provenance format, JSON example, cache-update invocation) in the main body -- exactly the kind of heavy, occasionally-needed detail progressive disclosure says should be loaded on demand, not always-inline. Pruned has no such orphaned heavy content. |
| D6 Freedom Calibration | 12 | 12 | 15 | Unchanged -- both calibrate low-freedom exact mechanics (entrypoint resolution, JSON shapes) against medium-freedom judgment (Step A's per-entry confirm/decline) appropriately for their own scope. |
| D7 Pattern Recognition | 8 | 8 | 10 | Both clearly follow the "Tool" pattern (decision trees + code examples + low freedom); pruned is proportionately shorter for its narrower scope, which is expected, not a deviation. |
| D8 Practical Usability | 13 | 13 | 15 | Decision trees, code examples, and error handling (stop-and-report, `ImportError` explanation) are all retained in pruned; no usability gap opened by the prune. |
| **Total** | **100** | **102** | **120** | Pruned does not regress; it scores 2 points higher, driven by a crisper single-scope description (D4) and no orphaned heavy-research content diluting progressive disclosure (D5), offsetting a small, scope-correct dip in D2/D3 from the branch-point and its guarding anti-pattern leaving with Step D. |

Grades: baseline 100/120 = 83.3% = B. Pruned 102/120 = 85.0% = B.

## Findings against the pruned file

No Critical or Important findings. The pruned `SKILL.md` fully preserves the Steps
A/B/C hand-off mechanism, the entrypoint-resolution section, the inline-reporting
rule, and the ruleset pointer; its documented `check`/`remediate` shapes match
`cli.py`'s real return values (`check` returns `{"workflow": [...]}`;
`remediate`'s `blocked` key stays documented as always-empty for this skill rather
than silently dropped). No fix-loop iteration was needed (0 of the 3-iteration cap
used).

## Step 6 cleanup

`./tmp/ai-kit-agents-md-rules-checker/` held exactly one file (`SKILL.md`, the blob
Step 1 wrote there) before removal -- confirmed by listing it. Removed with
`rm -rf ./tmp/ai-kit-agents-md-rules-checker` and confirmed gone with
`test ! -e ./tmp/ai-kit-agents-md-rules-checker`.

Deviation note: this task ran inside a git worktree
(`.claude/worktrees/agent-a792e4f680d95ae02`). `tmp/` is gitignored, and gitignored
paths are NOT shared between a worktree and the main checkout -- each worktree gets
its own untracked-file state on disk. `./tmp/` in this worktree was therefore empty
before this task ran (confirmed with `ls -la ./tmp/`): there was no pre-existing
scratch research JSON, ingest manifest, or unrelated scratch subdirectory to
preserve here. After the guarded removal, `./tmp/` is empty again, matching its
state before this task started -- nothing outside the one named, guarded removal
was touched. The three-pre-existing-entries check in the plan's acceptance criteria
assumes those entries exist in the execution environment; in this isolated
worktree they did not, so "0 of 0 preserved" is the honest report, not a failure
to preserve them.

## Code-review pointer (for this phase's CODE REVIEW gate)

If the phase's code-review step changes `skills/ai-kit-project-rules-agents/SKILL.md`
at all, `/skill-judge` MUST be re-run against the changed file and this file
(`09-SKILL-JUDGE.md`) updated in the same commit, and Task 1's banned-literal verify
chain MUST be re-run against the changed file. Otherwise, code review should confirm
byte-identity with the file this task scored via
`git diff --quiet 11e4791 -- skills/ai-kit-project-rules-agents/SKILL.md`.

- Evidence file: `.planning/phases/09-agents-md-checker-prune-ai-kit-project-rules-agents/09-SKILL-JUDGE.md`
- `BASELINE_SOURCE`: `cc922e4f06219571192e77053efb24d171c3c1ab:skills/ai-kit-agents-md-rules-checker/SKILL.md`
- `BASELINE_JUDGED_PATH`: `./tmp/ai-kit-agents-md-rules-checker/SKILL.md` (deleted after measurement; reproducible from `BASELINE_SOURCE`)
- Scores: baseline 100/120, pruned 102/120 -- no regression, zero Critical/Important findings.
