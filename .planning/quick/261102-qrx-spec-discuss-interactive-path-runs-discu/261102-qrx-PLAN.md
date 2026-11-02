---
phase: quick-261102-qrx
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - skills/ai-kit-gsd-spec-discuss/SKILL.md
  - skills/ai-kit-gsd-spec-discuss/references/log-formats.md
  - tests/test_ai_kit_gsd_spec_discuss.py
  - README.md
autonomous: true
requirements: [quick-261102-qrx]

estimate:
  tokens: 35000
  raw_tokens: 35000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "On the interactive path the skill executes `<workflows>/discuss-phase.md` with arguments `N --analyze --all --batch`: every gray area auto-selected, 2-5 questions per turn, a trade-off table before each group, the user answering"
    - "The auto path is unchanged: spec `N --auto`, discuss through `discuss-phase-assumptions.md` with argument `N`, never `--assumptions`, never `--auto` on discuss"
    - "Every place that describes the interactive mode (SKILL.md intro, step 7, section 2, the NEVER rule, the log-formats Mode and title lines, the root README row) names the same three flags"
    - "The skill's text tests pin the new wording and reject the old flag-less wording"
    - "SKILL.md stays under 500 lines and does not grow materially (baseline 294 lines)"
  artifacts:
    - path: skills/ai-kit-gsd-spec-discuss/SKILL.md
      provides: "Interactive path runs discuss-phase.md with `N --analyze --all --batch`"
      contains: "with arguments `N --analyze --all --batch`"
    - path: skills/ai-kit-gsd-spec-discuss/references/log-formats.md
      provides: "DISCUSSION-LOG Mode line names the interactive flags"
      contains: "standard discuss mode (`--analyze --all --batch`)"
    - path: tests/test_ai_kit_gsd_spec_discuss.py
      provides: "Text pins for the new interactive wording and the unchanged auto path"
    - path: README.md
      provides: "Skill row describes both run modes"
      contains: "`--analyze --all --batch`"
  key_links:
    - from: skills/ai-kit-gsd-spec-discuss/SKILL.md (section 2, interactive path)
      to: .claude/gsd-core/workflows/discuss-phase.md
      via: "$ARGUMENTS flags `--analyze`, `--all`, `--batch` load the analyze, all and batch overlays in `workflows/discuss-phase/modes/`"
      pattern: "N --analyze --all --batch"
---

<objective>
The `ai-kit-gsd-spec-discuss` interactive path runs discuss-phase with `--analyze --all --batch`
(all gray areas, grouped questions, trade-off tables) instead of the flag-less standard mode.
The auto path stays exactly as it is.

Purpose: the owner wants the interactive discuss to cover every gray area in grouped turns with
trade-off tables, the same intent the auto path already encodes for assumptions mode.
Output: updated SKILL.md, log-formats.md, the root README row, and text tests that pin the new
wording. One logical commit.

Owner decision 2026-11-02: this SKILL.md change is accepted without a skill-judge round, because
the next milestone re-judges every skill. The SUMMARY must record this waiver of the AGENTS.md
skill-judge rule.
</objective>

<execution_context>
@.claude/gsd-core/workflows/execute-plan.md
@.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@AGENTS.md
@skills/ai-kit-gsd-spec-discuss/SKILL.md
@tests/test_ai_kit_gsd_spec_discuss.py

Verified facts (do not re-research):
- The skill reads and executes the workflow file itself; it never runs the slash command. So
  the arguments the skill passes when it executes `discuss-phase.md` are the `$ARGUMENTS` that
  workflow parses. `.claude/gsd-core/workflows/discuss-phase.md` reads `modes/all.md` before
  `present_gray_areas` (auto-selects every gray area, discussion stays interactive, no
  auto-advance), `modes/batch.md` before `discuss_areas` (2-5 questions per turn) and
  `modes/analyze.md` before `discuss_areas` (trade-off table before each question). Overlays
  stack in the fixed order analyze, batch, text, so `--analyze --all --batch` is valid on
  standard discuss mode.
- Baseline at HEAD: `python3 -m unittest tests.test_ai_kit_gsd_spec_discuss` passes (72 tests);
  `python3 tools/run_unittest_parallel.py --group arch` passes; SKILL.md is 294 lines;
  the literal `N --analyze --all --batch` occurs 0 times in SKILL.md; `analyze --all --batch`
  occurs 0 times in README.md.
- Existing pins that must keep passing (do not reword these phrases):
  `The **interactive path** runs `<workflows>/discuss-phase.md` instead`,
  `with the user answering its prompts`,
  `arguments `N --auto` (auto path) or plain `N` (interactive path)`,
  `**interactive path** otherwise`, `NEVER pass `--auto` to discuss in assumptions mode`,
  and in log-formats.md `<run mode: Assumptions Mode for the auto path`.
- No `skills/ai-kit-gsd-spec-discuss/README.md` exists. The only README mention is the skill's
  row in the root `README.md` (the line containing `skills/ai-kit-gsd-spec-discuss/SKILL.md`);
  it still describes only the auto chain, so it is stale and gets updated.
- Tests compare SKILL.md text after collapsing whitespace, so line wrapping is free; keep the
  file's existing wrap width (about 95-100 columns).
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Interactive discuss runs with `N --analyze --all --batch` (section 2 + its pin)</name>
  <files>tests/test_ai_kit_gsd_spec_discuss.py, skills/ai-kit-gsd-spec-discuss/SKILL.md</files>
  <behavior>
    - The whitespace-collapsed SKILL.md contains "with arguments `N --analyze --all --batch`" in section 2.
    - The existing pins "The **interactive path** runs `<workflows>/discuss-phase.md` instead" and "with the user answering its prompts" still hold.
    - The auto path is pinned unchanged: the collapsed SKILL.md contains "read and execute `<workflows>/discuss-phase-assumptions.md` with argument `N` — **never** pass `--assumptions`".
  </behavior>
  <action>
    RED: in `tests/test_ai_kit_gsd_spec_discuss.py`, inside `test_auto_flag_and_recommendation_rule`,
    under the "per-phase steps follow the picked mode" comment, add assertIn checks on the
    collapsed `skill` string for the three behaviour lines above. Add a one-line comment naming
    the owner decision of 2026-11-02 (interactive discuss runs all gray areas, grouped questions,
    trade-off tables). Run the module filtered to that test and confirm it fails only on the new
    section 2 assertion.

    GREEN: in `skills/ai-kit-gsd-spec-discuss/SKILL.md` section "## 2. Per phase: discuss", change
    the sentence that starts "The **interactive path** runs `<workflows>/discuss-phase.md`
    instead" so it reads: The **interactive path** runs `<workflows>/discuss-phase.md` instead,
    with arguments `N --analyze --all --batch` (every gray area, 2–5 questions per turn, a
    trade-off table before each group) and with the user answering its prompts.
    Keep both pinned phrases verbatim. Do not touch the auto-path sentence before it, the
    "**Auto path only**" paragraph, or any other section in this task. Add no other discuss flag
    (the skill already skips `auto_advance`, and the all overlay does not auto-advance).
    Do not commit yet; Task 2 makes the single commit.
  </action>
  <verify>
    <automated>python3 -m unittest tests.test_ai_kit_gsd_spec_discuss -k test_auto_flag_and_recommendation_rule</automated>
  </verify>
  <done>The filtered test fails before the SKILL.md edit and passes after it; `grep -c 'N --analyze --all --batch' skills/ai-kit-gsd-spec-discuss/SKILL.md` returns 1 (baseline 0).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Same flags in every other mode description, README row, verify, one commit</name>
  <files>tests/test_ai_kit_gsd_spec_discuss.py, skills/ai-kit-gsd-spec-discuss/SKILL.md, skills/ai-kit-gsd-spec-discuss/references/log-formats.md, README.md</files>
  <behavior>
    - Collapsed SKILL.md contains "discuss in standard mode with `--analyze --all --batch`, the user answering" (intro paragraph).
    - Collapsed SKILL.md contains "discuss-phase with `--analyze --all --batch`, the user answering" (section 0 step 7).
    - Collapsed SKILL.md contains "runs standard discuss mode with `--analyze --all --batch` instead" (NEVER rule on `--auto`).
    - Collapsed SKILL.md no longer contains the old flag-less phrase "its standard discuss mode with the user answering" (assertNotIn).
    - Collapsed log-formats.md contains "standard discuss mode (`--analyze --all --batch`) with the user" and still contains "<run mode: Assumptions Mode for the auto path".
    - The root README line containing `skills/ai-kit-gsd-spec-discuss/SKILL.md` contains "interactive (discuss with `--analyze --all --batch`".
  </behavior>
  <action>
    RED: add the SKILL.md assertions to `test_auto_flag_and_recommendation_rule`; add the
    log-formats assertion next to the existing `<run mode: Assumptions Mode for the auto path`
    check (collapse whitespace for the new one, since the template wraps); in
    `test_readme_registers_the_skill`, pick the README line that contains
    `skills/ai-kit-gsd-spec-discuss/SKILL.md` and assert the README behaviour line on it. Run the
    module and confirm only the new assertions fail.

    GREEN, in `skills/ai-kit-gsd-spec-discuss/SKILL.md` (rewrap to the existing width, add at most
    two lines in total):
    - Intro paragraph (around lines 13-14): the interactive parenthetical becomes "spec without
      `--auto`, discuss in standard mode with `--analyze --all --batch`, the user answering".
    - Section 0 step 7 (around lines 83-84): the "interactive = ..." parenthetical becomes
      "interactive = spec-phase without `--auto`, discuss-phase with `--analyze --all --batch`,
      the user answering". Keep "**interactive path** otherwise" and "Never flip config keys to
      pick a path" verbatim.
    - NEVER list (around line 261): the trailing parenthetical of the `--auto` rule becomes "(the
      interactive path runs standard discuss mode with `--analyze --all --batch` instead)".
    - Leave the description frontmatter, the auto path, the "**Auto path only**" paragraph and
      the "Rules that hold in both paths" bullets unchanged.

    In `skills/ai-kit-gsd-spec-discuss/references/log-formats.md`, DISCUSSION-LOG (new) template:
    the title line's "standard discuss mode for the interactive path" becomes "standard discuss
    mode (`--analyze --all --batch`) for the interactive path" (keep the `# ` prefix on the
    wrapped continuation line), and the **Mode:** line's "interactive path: standard discuss mode
    with the user" becomes "interactive path: standard discuss mode (`--analyze --all --batch`)
    with the user". Keep "<run mode: Assumptions Mode for the auto path" verbatim.

    In `README.md`, the skill's table row: replace the opening clause "Chains GSD
    `/gsd-spec-phase --auto` then assumptions-mode discuss over a phase range," with "Chains GSD
    `/gsd-spec-phase` then `/gsd-discuss-phase` over a phase range in one of two run modes, auto
    (spec `--auto`, assumptions-mode discuss) or interactive (discuss with `--analyze --all
    --batch`, the user answering)," and leave the rest of the row as is.

    VERIFY then COMMIT: run the module, the arch group and `make validate`; check
    `wc -l < skills/ai-kit-gsd-spec-discuss/SKILL.md` is at most 296. Review `git status` and
    `git diff` (only the four files above). Make ONE commit with the four files, message
    "feat(spec-discuss): interactive path discusses with --analyze --all --batch" and a one-line
    body naming the owner's 2026-11-02 skill-judge waiver. Let pre-commit run; never use
    `--no-verify`. If a hook fails, fix the cause and commit again (a new commit is not needed
    when the commit never landed).
  </action>
  <verify>
    <automated>python3 -m unittest tests.test_ai_kit_gsd_spec_discuss && python3 tools/run_unittest_parallel.py --group arch && make validate && test "$(wc -l < skills/ai-kit-gsd-spec-discuss/SKILL.md)" -le 296 && grep -c 'analyze --all --batch' README.md</automated>
  </verify>
  <done>All 72+ tests in the module pass, the arch group passes, `make validate` passes, SKILL.md is at most 296 lines, README.md has 1 match for `analyze --all --batch` (baseline 0), and one commit with the four files exists on the branch with pre-commit hooks having run.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| skill text to executing agent | SKILL.md decides which flags the agent passes to the GSD discuss workflow |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qrx-01 | Tampering | SKILL.md section 2 interactive arguments | medium | mitigate | Only `--analyze --all --batch` are added; the all overlay does not auto-advance, the skill keeps skipping `auto_advance`, and the NEVER rule against `--auto` stays; Task 2 tests pin the auto path unchanged |
| T-qrx-02 | Repudiation | Skipped skill-judge round | low | accept | Owner decision 2026-11-02 recorded in the commit body and the SUMMARY; the next milestone re-judges every skill |
</threat_model>

<verification>
- `python3 -m unittest tests.test_ai_kit_gsd_spec_discuss` passes.
- `python3 tools/run_unittest_parallel.py --group arch` passes.
- `make validate` passes and the commit's pre-commit hooks ran (no `--no-verify`).
- SKILL.md at most 296 lines (baseline 294, limit 500).
- `git status` shows no leftover files from this task besides the quick-task PLAN/SUMMARY the
  orchestrator commits.
</verification>

<success_criteria>
- The interactive path executes `discuss-phase.md` with `N --analyze --all --batch`, and every
  description of the interactive mode says so.
- The auto path text is byte-for-byte unchanged outside the NEVER rule's interactive parenthetical.
- One logical commit holds the SKILL.md, log-formats.md, README.md and test changes.
- The SUMMARY records: "Owner decision 2026-11-02: accepted without a skill-judge round, because
  the next milestone re-judges every skill."
</success_criteria>

<output>
Create `.planning/quick/261102-qrx-spec-discuss-interactive-path-runs-discu/261102-qrx-SUMMARY.md`
when done. Include the owner's skill-judge waiver (2026-11-02) under decisions.
</output>
