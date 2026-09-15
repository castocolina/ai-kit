# 14-04 Task 2: `/skill-judge` evidence

Date: 2026-09-14

JUDGED_PATH: skills/ai-kit-project-rules-cicd/SKILL.md
JUDGED_COMMIT: 66ed063f270918a987bc644c5a6af066400696d8
BASELINE: none (new skill, no prior SKILL.md -- verified by history search, see below)
SCORE: 103/120
CRITICAL: 0
IMPORTANT: 0
FIX_ITERATIONS_USED: 0/3
LIMIT_COUNT_FINAL: 11
CONCISION_TENSION: none -- the score clears the 96/120 alternative pass bar (103 >= 96) and
carries zero Critical/Important findings on the first pass, so no fix iteration ran and no
finding ever pushed toward shortening the Limits section. This is recorded explicitly, not left
to silence, per D-C26's requirement that the question be answered whether or not tension arose.

## Method

This is a brand-new skill: no `SKILL.md` existed for `ai-kit-project-rules-cicd` before Task 1 of
this plan wrote one. There is nothing to regress against. No synthetic baseline was constructed,
no sibling skill's score (`ai-kit-project-rules-agents` 102/120, `ai-kit-project-rules-makefile`
103/120, `ai-kit-project-rules-precommit` 103/120, `ai-kit-project-rules-arch` 100/120,
`ai-kit-project-rules-docker` 103/120) is reused as a stand-in, and the design spec's own
historical figures for a different skill are not cited as if they applied here. The pass bar is
therefore absolute rather than comparative: zero Critical and zero Important findings, or a score
of at least 96/120.

Performed by this executor, running the installed `/skill-judge` skill's rubric, against
`skills/ai-kit-project-rules-cicd/SKILL.md` at its committed path, as this plan's commit
`033dcae` (Task 1).

### No-baseline claim, verified rather than asserted

Two commands run against the full repository history, both confirming no `SKILL.md` for this
domain ever existed before Task 1's own commit:

```
/usr/bin/git log --all --follow --oneline -- skills/ai-kit-project-rules-cicd/SKILL.md
```
Output: exactly one line, `033dcae feat(14-04): write SKILL.md for ai-kit-project-rules-cicd and
register in README` -- Task 1's own commit, and nothing before it.

```
/usr/bin/git log --all --diff-filter=A --name-only --pretty=format:%H -- '**/SKILL.md'
```
(filtered for any added path containing "cicd") -- output: exactly
`skills/ai-kit-project-rules-cicd/SKILL.md`, added once, by commit `033dcae` (this task's own
preceding commit). No earlier name for this domain ever carried a `SKILL.md` either -- the CI/CD
reuse-checking domain is new content this milestone's family-split design spec introduces; no
pre-split combined skill (traced in Phase 9's, Phase 10's, Phase 11's, Phase 12's and Phase 13's
evidence files) ever covered it.

### Step 1 -- installed rubric, read in full before scoring

`/home/bazzite/.claude/skills/skill-judge/SKILL.md` was read in full before scoring. Its
8-dimension, 120-point rubric is UNCHANGED from what Phase 9's `09-SKILL-JUDGE.md`, Phase 10's
`10-SKILL-JUDGE.md`, Phase 11's `11-SKILL-JUDGE.md`, Phase 12's `12-SKILL-JUDGE.md`, and Phase
13's `13-SKILL-JUDGE.md` all recorded: D1 Knowledge Delta (20), D2 Mindset + Appropriate
Procedures (15), D3 Anti-Pattern Quality (15), D4 Specification Compliance -- Especially
Description (15), D5 Progressive Disclosure (15), D6 Freedom Calibration (15), D7 Pattern
Recognition (10), D8 Practical Usability (15). No difference from any prior phase's recorded
rubric to report.

### Step 2 -- packaging precondition, confirmed mechanically

```
basename: ai-kit-project-rules-cicd
frontmatter name: ai-kit-project-rules-cicd
PACKAGING-MATCH-OK
```

Re-confirming Phases 9-13's own finding: the installed rubric has no dimension that reads the
containing directory at all (D4 checks `name:` format and description quality; nothing in D4 or
any other dimension compares `name:` against the parent directory's basename). Stated as a
factual finding, not worked around -- no packaging/naming-consistency dimension score is reported
because the installed skill does not produce one.

### Step 3 -- scored

299 lines, no `references/` directory. Follows the "Tool" pattern (decision structure over the
applicability gate and the four reuse surfaces, worked JSON code examples pulled from real runs,
low freedom throughout), sized at the top of the family's own 150-300-line range and above the
Phase 13 sibling's 251 lines -- proportionate to this being the densest skill in the family:
eleven honesty-about-limits statements (three more than the Phase 13 sibling's eight), four
pinned hyphenated tokens, two CI platforms, four reuse surfaces, and an eight-row pinned plugin
table, against that sibling's five finding categories and one platform.

**Second pass, after commit `033dcae` (295 lines).** While assembling this plan's SUMMARY, a real
content gap was found and fixed (Rule 2, commit `66ed063`, 299 lines): the document showed only
the flagging (SC1) case in its worked `check`/`remediate` examples, never the fully-compliant
(SC2) case -- a reader had no worked confirmation that a CI job already calling the reuse command
produces zero findings. One sentence was added, confirmed against a real run
(`{"cicd": []}` for a `.gitlab-ci.yml` job running `make ruff` instead of `ruff check .`), and the
document stayed inside the 150-300-line range. This is a purely additive, non-controversial
change: it does not touch any Limits statement, any pinned token, the description, the Scope
section, or any dimension's evidence citation below -- so the per-dimension scores and the 103/120
total are RE-AFFIRMED rather than re-derived from scratch, and `JUDGED_COMMIT` is updated to
`66ed063` per this evidence file's own code-review-pointer rule (any `SKILL.md` change requires
re-running the gate and updating this file in step). D8's existing 1-point deduction (no worked
JSON for the `SURFACE_ORDER` collision case) is UNCHANGED by this addition, since the new example
demonstrates the zero-finding case, not the collision case -- a distinct gap, still open, not
claimed as closed by this fix.

## Per-dimension scores

| Dimension | Score | Max | Evidence |
|---|---|---|---|
| D1 Knowledge Delta | 18 | 20 | Dense expert content: the dual-clause root-scoped applicability gate; the reuse-source-driven scope decision (a CI tool with no matching reuse source anywhere produces NO finding -- a genuinely non-obvious design choice a naive reader would expect this skill to flag as "missing tooling"); the `SURFACE_ORDER` first-wins collision rule (a repo with the same tool covered by three surfaces at once collapses to exactly one finding, naming the first surface only); the two-token-then-one-token command-key computation; and the eleven Limits, each a genuine engine quirk from real implementation experience -- GitLab `include:` never followed even for `local:` (the limit the reader is warned they are MOST likely to hit, since ai-kit's own pipeline is include-composed), `${{ }}`/`defaults.run` left unevaluated, the single-tool shape exclusion of two-line targets whose lines compute different keys, the unrecognized-tool silent-failure mode, the plugin-table's comment-mention over-admission, and the `jscpdReport`-beside-`jscpd` declared-task-identity gap (a purpose-named task is never a reuse source for the tool it wraps). No "what is CI" or "what is YAML" tutorial content anywhere. Docked 2 points relative to a perfect score for the same reason the Phase 13 sibling was docked: the "Resolve the entrypoint" block and the check/remediate JSON-shape boilerplate repeat a structural pattern shared verbatim across all five sibling `SKILL.md` files -- Expert content for a first-time reader of the family, Activation-tier for a reader who has already read a sibling. |
| D2 Mindset + Procedures | 9 | 15 | Has domain-specific procedures Claude would not otherwise know (the entrypoint-resolution candidate-list ordering and its honest `ImportError` note; the fixed `SURFACE_ORDER` precedence a reader must know to predict which of several matching surfaces gets named; the "what a user does with the output" section's read-and-replace procedure naming the exact `reuse_command` field to substitute). Does not have an explicit "before doing X, ask yourself" decision framework, because -- like the Phase 12 and Phase 13 siblings -- this skill has no branch point requiring judgment by design: every check is deterministic once the CI text and the reuse inventory are read, and its whole knowledge surface is hardcoded with no research dispatch (stated explicitly in "Run the check"). This is an honest reflection of the skill's actual shape rather than an omission to fix; inventing a framework for a branch point that does not exist would be the kind of padding D1's red flags penalize. Scored in the same band as the Phase 12/13 siblings' 9/15 for the same structural reason. |
| D3 Anti-Pattern Quality | 12 | 15 | 8 anti-patterns, each with a non-obvious WHY -- one more than the Phase 13 sibling's 7. The strongest is "NEVER present this skill's silence as proof that a repo's CI is clean," which names the include-composed case concretely (ai-kit's own `.gitlab-ci.yml`) rather than stating a generic caveat, and "NEVER ask a build tool to enumerate its own tasks," which points directly at the plugin-table blind spot (Limit 10) and states the actual mechanism (text/regex read, never an invocation). Docked 3 points relative to a perfect score for three entries ("NEVER run, execute, or shell-expand...", "NEVER fetch... a `uses:` step's referenced action...", "NEVER edit the target repo's CI file...") that substantially restate content already stated in full in the Scope section's opening paragraph, rather than surfacing a new landmine specific to this skill's own domain -- one more restatement than the Phase 13 sibling's two, proportionate to this skill having more boundary clauses to restate from (four never-clauses in Scope's own second sentence, against that sibling's shorter equivalent). |
| D4 Specification Compliance (description) | 14 | 15 | Single-skill-scope description naming only this skill's own subject (direct tool invocations duplicating a Makefile target, a pre-commit hook, a `package.json` script, or a Gradle build task) in the words a host routes on, with three concrete "or when asked" trigger phrasings and no sibling-domain bleed. Comprehensive WHAT (the exact four reuse surfaces named) and WHEN (three trigger-phrase examples) with searchable keywords (`.github/workflows/*.yml`, `.gitlab-ci.yml`, Makefile, pre-commit, `package.json`, Gradle). Additionally resolves the family's hardest routing ambiguity for THIS skill explicitly -- the two siblings that also read the Makefile and the pre-commit config -- naming the split with the pinned `command-vocabulary` clause rather than leaving a host to guess among three skills on a genuinely overlapping keyword. Docked 1 point relative to a perfect score for being one dense multi-clause sentence rather than the more scannable numbered-list structure the rubric's own "excellent description" example uses -- the same gap the Phase 13 sibling's evidence recorded, present here too and, if anything, slightly more pronounced given the extra disambiguation clause this description carries that the Phase 13 sibling's did not need. |
| D5 Progressive Disclosure | 13 | 15 | No `references/` directory; the entire document is 295 lines, comfortably under the 500-line hard cap and close to the ~300-line Tool-pattern target -- appropriately sized for the family's densest scope (eleven Limits against the Phase 13 sibling's eight, four reuse surfaces against that sibling's five finding categories over a narrower mechanism). Self-contained: every section a reader needs to operate the skill is inline, with nothing orphaned and no Research Step block to extract (unlike the Phase 10/11 siblings' own recorded D5 findings). Docked 2 points for the same "no references-directory calibration ceiling" reason the Phase 12/13 siblings' evidence applied to a self-contained skill under this dimension's scoring band, rather than for any identified structural flaw. |
| D6 Freedom Calibration | 14 | 15 | Low freedom throughout, matching the task's fragility: the entrypoint-resolution candidate list (one wrong byte breaks the import), the exact output-key names for both subcommands (verified against real runs, not asserted), the four surfaces' exact recommendation-string forms, and the eight-row pinned plugin table transcribed verbatim from the shipped `PLUGIN_TASK_TABLE`. No high- or medium-freedom judgment call exists in this skill's own scope for the document to mis-calibrate, since every check is deterministic once the CI text and the reuse inventory are read. Docked 1 point relative to a perfect score because "What a user does with the output" says to read the `remediate` list "in criticality order" without noting that every one of this skill's findings shares the SAME fixed criticality (MEDIUM) -- so a reader is left to infer, rather than being told, that this skill's own list carries no meaningful criticality ordering among its own entries (only relative to a DIFFERENT domain's findings in an aggregated multi-skill report, which is Phase 15's concern, not this document's). A minor freedom gap, real but narrow. |
| D7 Pattern Recognition | 9 | 10 | Clear "Tool" pattern: the applicability-gate decision, the four-surface enumeration read as a decision structure over what gets evaluated and in what precedence, worked JSON code examples pulled from real runs (the `check` finding, the `remediate` entry, the `bogus`-subcommand exit-2 case -- one more worked example than the Phase 13 sibling's own document shows), low freedom throughout. At 295 lines this sits at the top of the Tool pattern's own ~300-line target, proportionate to this skill's four-surface, two-platform, eleven-limit scope -- denser than every prior family member's own document. |
| D8 Practical Usability | 14 | 15 | Working code examples throughout, EVERY ONE pulled from a real invocation of the shipped `ai-kit-project-rules-cicd.py` against a real fixture repo (a Makefile `ruff` target beside a `.gitlab-ci.yml` job running `ruff check .` directly) rather than composed -- the `check` finding, the `remediate` entry, and the `bogus`-subcommand exit code, all three confirmed live during Task 1 (see `14-04-SUMMARY.md`). Explicit degradation behavior (an absent or unreadable Makefile, `.pre-commit-config.yaml`, `package.json`, or Gradle build script simply contributes no reuse sources from that surface, never a crash). Edge cases are first-class content -- the eleven Limits ARE this skill's edge-case documentation, each stating both which form is unread/unresolved AND what the user will actually see instead, following the same "say both halves" discipline the Phase 13 sibling established. Docked 1 point for showing only the single-finding collision-free case in the worked JSON examples -- a reader does not see a worked example of the `SURFACE_ORDER` collision-resolution case (two matching surfaces, one finding, naming only the first) actually rendered as JSON, only described in prose under "What it checks." |
| **Total** | **103** | **120** | Grade: 103/120 = 85.8% = B. |

## Findings against `skills/ai-kit-project-rules-cicd/SKILL.md`

**No Critical or Important findings.** The two dimensions scoring furthest below their ceiling
(D2 at 9/15, D3 at 12/15) reflect real, but non-blocking, characteristics of this specific skill
-- D2's score reflects an honest absence of a decision-framework need (this skill genuinely has no
branch point, by design, matching the Phase 12/13 siblings' own recorded rationale), not a hidden
judgment call the document fails to guide; D3's 3-point deduction is a real but Minor gap (three
anti-patterns restate Scope-section content rather than surfacing a wholly new landmine) that does
not affect correctness, does not misdocument the code's real behavior, and does not weaken any of
the family-wide scope-boundary, finding-category, or Limits content. Because the score (103/120)
already clears the 96/120 alternative pass bar with room to spare, and because Critical/Important
count is zero either way, **no fix-loop iteration was needed (0 of the 3-iteration cap used)**.

No finding at any dimension pushed toward shortening the Limits section specifically -- D5's own
2-point deduction is the "no references directory" structural characteristic every self-contained
sibling in this family carries, not a size critique of the Limits section, and no dimension's
evidence column above names the Limits section, or any individual limit statement, as a target for
trimming. **`CONCISION_TENSION: none`** is therefore the honest answer, not a default filled in
because the loop never ran -- the loop never ran BECAUSE no concision-flavoured finding arose to
trigger it, and that absence was checked deliberately (re-reading every dimension's evidence above
for the words "concise"/"shorten"/"trim"/"redundant" against the Limits section specifically, per
T-14-44's warning) rather than assumed.

The fix loop's binding constraints (Task 1's `SKILL-SHAPE-OK`/`SURFACES-DOCUMENTED-OK` must still
pass; the documented output shapes must still match the code; every honesty-about-limits statement
must survive; the two-subcommand statement must survive) were therefore never exercised in this
task, since no fix was made. All were re-confirmed unchanged after this review -- see the
acceptance-criteria re-runs below.

### Acceptance criteria re-runs (Task 1's verify chain, re-confirmed after this review)

- `SKILL-SHAPE-OK` -- re-run verbatim: prints `SKILL-SHAPE-OK 10 11 11` and exits 0 (unchanged
  from Task 1).
- `SURFACES-DOCUMENTED-OK` -- re-run verbatim: prints `SURFACES-DOCUMENTED-OK ['cicd'] ['blocked',
  'remediate']` and exits 0 (unchanged from Task 1).
- All eleven Limits statements (`## Limits`, the committed document's own numbered list) were
  re-read and confirmed present, unmodified, and each still actionable as its own standalone
  sentence -- no judge-driven pressure to remove or dilute any of them arose during scoring, since
  none was identified as a finding.
- The two-subcommand statement (`## Run the check`: "This skill has exactly two subcommands,
  `check` and `remediate`... There is no research step and no per-stack cache...") was re-read and
  confirmed present, unmodified, and still explains the difference from the Phase 10/11 siblings by
  name -- no judge-driven pressure to remove it arose during scoring.

**Necessary-but-not-sufficient axis, stated explicitly (per D-C23/T-14-34).** `SKILL-SHAPE-OK` is a
keyword-presence check -- one pinned token per limit at minimum -- and proves only that a limit was
not DELETED, never that its sentence still states something a reader would act on. Since this task
made no edit to any Limits sentence (no fix-loop iteration ran), there is no before/after wording
to compare; the verbatim quotation this control exists to enable is satisfied trivially here
because the text is identical to what Task 1 committed. `14-04-SUMMARY.md` additionally quotes the
full Limits section verbatim as it stands after this task, per this plan's `<output>` requirement.

## Verbatim Limits section (as it stands after this task -- no iteration edited it)

1. **The applicability gate is root-scoped, and CI platforms outside GitLab CI and GitHub Actions
   are ignored entirely.** A repo using CircleCI, Jenkins, Azure Pipelines, Travis, or any other
   CI platform gets an empty report, not a warning that it was skipped.
2. **The CI readers are text readers, not a YAML implementation.** Both the GitLab CI and GitHub
   Actions readers are stdlib-only, indentation-aware text scans, never a YAML library. A
   tab-indented file (YAML forbids tabs) may have a block mis-attributed rather than raise, and
   anchors, aliases, merge keys, and GitLab's `!reference` are never resolved -- a command site
   using one may be read incompletely.
3. **A `uses:` step's action, and a `jobs.<id>.uses` reusable workflow, are never fetched.** A
   tool invoked inside a third-party or composite GitHub Action, or inside a called reusable
   workflow, is invisible to this reader -- only a step's own `run:` text is ever read.
4. **GitLab `include:` is never followed, in ANY form -- `local:` included.** `include:`'s
   children (`local:`, `template:`, `project:`, `remote:`, `component:`) are all skipped
   uniformly as a reserved non-job key; none is ever resolved or opened. A pipeline composed from
   included files can run a tool this reader never sees, so a zero-finding result on such a repo
   is not evidence its CI is clean -- and this is the limit the first repo a user points this
   skill at is most likely to hit, since ai-kit's own `.gitlab-ci.yml` is itself include-composed.
5. **Unresolved expressions and unevaluated execution context.** `${{ }}` expressions are never
   resolved, so a step whose command is entirely an expression has no classifiable tool token;
   matrix expansion, `if:` conditions, and `working-directory:` are not evaluated, so a command
   that would never actually run on this platform is still read; `defaults.run` is not evaluated
   either, at workflow or job level, so a `shell:`/`working-directory:` default that changes how
   every `run:` in the file actually executes contributes nothing to the command text this reader
   sees.
6. **The scope is reuse-source-driven: a duplicate with no existing equivalent is never
   flagged.** A CI step running a tool directly that the repo has no Makefile target, hook,
   script, or task for produces no finding -- this skill never recommends creating a new reuse
   source, only reusing one that already exists.
7. **The single-tool shape requirement excludes several real target/script/task shapes.** An
   identity is extracted only from a Makefile target with at most two real recipe lines (and, for
   two lines, only when both compute the same command key), a pre-commit hook entry or
   `package.json` script with no top-level `&&`/`||`/`;`, and a Gradle task whose bare name is the
   identity. Aggregate Makefile targets, a two-line target whose lines compute different keys,
   aggregate hook entries and scripts, multi-segment hook entries, and Gradle's own lifecycle
   task names (`check`, `build`, `test`, `assemble`) never become reuse sources, even when one of
   the tools they run would otherwise match a CI line.
8. **The unrecognized-tool case is silent: when neither the catalog nor a qualified-name match
   can answer an identity, it is silently unusable.** An identity the shared tool catalog does not
   resolve, that is not an out-of-taxonomy marker, and that was not derived from a command body
   naming itself, admits no reuse source -- with no error or warning saying so. A `clean: rm -rf
   dist` target, for example, is never a reuse source for anything.
9. **`package.json` is read root-and-`scripts`-only, with workspace members unread.** Only the
   repository root's `package.json` is read, and only its `scripts` object; a workspace member's
   own `package.json`, and every other top-level field (`bin`, `config`, and so on), are never
   read as a command to reuse.
10. **Gradle is read root-and-text-only, with a plugin-table blind spot.** Only root
    `build.gradle`/`build.gradle.kts` are read (a subproject's build script and
    `settings.gradle`'s project list are not); this skill never invokes the build tool to
    enumerate its own real task set, so a task contributed by a plugin outside the pinned table
    above is invisible; the plugin-id evidence check is a plain containment test against the
    build-script TEXT, so a comment merely mentioning a plugin id counts as evidence too (an
    accepted over-admission -- nobody comments out a plugin they never applied); and a declared
    task's identity is its NAME with no command body behind it, so a task named for its purpose
    rather than its tool (`tasks.register("jscpdReport")` beside a `jscpd` invocation elsewhere in
    CI) is not a reuse source for that tool -- this family's match rule never does suffix
    stripping to recover one.
11. **The command-segmentation scope leaves pipelines' downstream stages, subshells, and
    heredocs unanalyzed.** Only a command line's own top-level segments (split on `&&`/`||`/`;`,
    truncated at an unquoted pipe) are classified; a line containing a heredoc (`<<`) is skipped
    rather than mis-parsed, and nothing inside a subshell or piped into a later stage is read as
    its own command.

No before-text is shown beside any statement because no iteration reworded any of them -- the text
above is byte-identical to what Task 1 committed.

## Code-review pointer (for this phase's CODE REVIEW gate)

If the phase's code-review step changes `skills/ai-kit-project-rules-cicd/SKILL.md` at all,
`/skill-judge` MUST be re-run against the changed file and THIS file (`14-SKILL-JUDGE.md`)
updated in the same commit, and Task 1's `SKILL-SHAPE-OK`/`SURFACES-DOCUMENTED-OK` verify chain
MUST be re-run against the changed file. Otherwise, code review should confirm byte-identity with
the file this task scored via:

```
/usr/bin/git diff --quiet 66ed063f270918a987bc644c5a6af066400696d8 -- skills/ai-kit-project-rules-cicd/SKILL.md
```

- Evidence file: `.planning/phases/14-ci-cd-rules-checker-ai-kit-project-rules-cicd/14-SKILL-JUDGE.md`
- `JUDGED_PATH`: `skills/ai-kit-project-rules-cicd/SKILL.md`
- `JUDGED_COMMIT`: `66ed063f270918a987bc644c5a6af066400696d8`
- Score: 103/120, 0 Critical, 0 Important, 0/3 fix iterations used.

## Naming-analyzer verdict

Date: 2026-09-14

NAMING_VERDICT: confirmed

`ai-kit-project-rules-cicd` is kept as-is; no rename is applied.

`/naming-analyzer` was run against the skill directory name `ai-kit-project-rules-cicd`, as the
project's established skill-authoring pipeline step (scaffold, then judge, then name -- the same
order Phases 9-13 recorded). Prompt context given to the analyzer: the five sibling names already
in the family (`ai-kit-project-rules-agents`, `-makefile`, `-precommit`, `-arch`, `-docker`), this
skill's actual scope (CI-config reuse-duplication checking across GitLab CI and GitHub Actions,
against four reuse surfaces -- Makefile targets, pre-commit hooks, `package.json` scripts, Gradle
build tasks -- never general CI/CD pipeline security, deployment correctness, or build-tool
enumeration), and the fact that the `ai-kit-project-rules-<domain>` family scheme is user-decided
rather than open for this task to redesign. Applying the analyzer's own decision framework
(vagueness, misleading-name, abbreviation, convention, and length checks) to a package/directory
name rather than a variable:

- **Not vague**: "cicd" is a precise, industry-standard abbreviation (Continuous
  Integration/Continuous Delivery) with no ambiguity in this position -- next to
  `agents`/`makefile`/`precommit`/`arch`/`docker`, "cicd" can only mean the CI/CD pipeline-config
  domain, not an unrelated sense of the term.
- **Misleading-name tension noted, but not severe enough to warrant a rename**: the skill's own
  scope is narrower than "cicd" alone might suggest -- it checks REUSE DUPLICATION only (does a CI
  step call a tool directly when an equivalent command already exists elsewhere in the repo) and
  explicitly does NOT run a CI job, does NOT evaluate pipeline security, does NOT check deployment
  correctness, and does NOT enumerate a build tool's own tasks. A reader who sees only the word
  "cicd" and never reads the description or the Limits section could over-infer a broader
  CI/CD-quality or pipeline-security tool. This is the same shape of naming tension the `docker`
  sibling's own evidence file recorded for "docker" (local-dev Compose conventions only, not
  general Docker security) and the `arch` sibling's for "arch" (form/convention only, not full
  dependency-direction enforcement) -- the family's own convention names skills by DOMAIN, not by
  SCOPE DEPTH within that domain, and the `description` frontmatter field plus the `SKILL.md`
  body's own Scope/Limits sections are where scope-depth is correctly communicated, not the
  directory name.
- **Not mis-abbreviated**: "cicd" is the industry-standard abbreviation for the domain this skill
  checks, in the same acceptable-abbreviation category `naming-analyzer`'s own guidance names for
  `html`/`api`/`url` -- well-known enough that spelling it out
  (`ai-kit-project-rules-continuous-integration-continuous-delivery`) would harm readability
  rather than help it, and no sibling in this family spells out its own domain word further than
  its common industry form either.
- **Family-convention match**: exact match to the `ai-kit-project-rules-<domain>` pattern all
  five sibling checkers already use -- a single-word (here, single-abbreviation) domain segment,
  same as `agents`/`makefile`/`precommit`/`arch`/`docker`, none of which qualify their own scope
  depth in the name either.
- **Length**: 25 characters (`ai-kit-project-rules-cicd`), tied with `-arch` (25) for
  shortest-or-tied among the six family members, shorter than every other sibling
  (`-agents` 27, `-docker` 27, `-makefile` 29, `-precommit` 30), comfortably under the
  64-character frontmatter `name:` limit `skill-judge`'s own D4 dimension checks.

**Alternative considered and rejected during this analysis**: a scope-qualified form (e.g.
`ai-kit-project-rules-cicd-reuse` or `ai-kit-project-rules-ci-command-reuse`) was considered and
rejected -- none of the five existing siblings qualify their own scope depth in the name (`docker`
does not become `docker-local-dev`; `arch` does not become `arch-form-only`), and doing so here
alone would break the family's own established naming symmetry for a distinction the description
and Limits section already carry, while also lengthening the name well past every sibling for no
routing benefit (a host routes on `description`, per D4/rubric guidance, not on name length). No
alternative is proposed.

**The four live name-dependency sites, re-verified live rather than assumed, during this
incorporation:**

1. `.planning/REQUIREMENTS.md` line 81 -- the `REQ-rules-cicd` bullet: "A new skill
   `ai-kit-project-rules-cicd` checks that CI config reuses existing
   Makefile/pre-commit/package.json/Gradle commands rather than duplicating tool invocations
   inline." Re-read live; names the skill by this exact string.
2. `.planning/ROADMAP.md` line 407 -- Phase 14's Goal line: "A new skill
   `ai-kit-project-rules-cicd` checks that CI config reuses existing
   Makefile/pre-commit/`package.json`/Gradle commands rather than duplicating tool invocations
   inline in CI YAML." Re-read live; names the skill by this exact string.
3. `.planning/ROADMAP.md` line 429 -- Phase 15's "Depends on" note: "Phase 14 (needs all 5 new
   domain checkers -- makefile, precommit, arch, docker, cicd -- plus the Phase 9-pruned agents
   checker -- to exist before it can invoke and aggregate them)." Re-read live; names this skill's
   domain word (`cicd`) in the enumerated list.
4. `.planning/ROADMAP.md` line 433 -- Phase 15's Success Criterion 1: "Running the orchestrator
   against a target repo invokes all 6 checkers' `check` (agents, makefile, precommit, arch,
   docker, cicd), and the aggregated report contains findings from every domain that has any, with
   none silently dropped." Re-read live; enumerates this skill's domain word by exact name.

Per this task's instruction, the name is NOT this task's to change even where the verdict is
"confirmed": `ai-kit-project-rules-cicd` is fixed by `REQUIREMENTS.md`'s `REQ-rules-cicd`, by
`.planning/ROADMAP.md` Phase 14's goal line and Phase 15's dependency note, and by Phase 15's own
Success Criterion 1, which enumerates the six checkers this orchestrator must invoke by this exact
family naming scheme. Since the verdict is a confirmation rather than a proposed alternative,
there is no rename-propagation blast radius to name here beyond stating these four downstream
dependencies explicitly -- the confirmation simply closes this pipeline step with no open question
for the user.
