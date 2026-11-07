# Distribution, evals and tests: facts and plan (input for the phase 32 spec)

*The 2026-11-07 fact sheet: how ai-kit's skills, evals and tests are laid out and installed today; input for phases 32, 52 and 53.*

Gathered 2026-11-07, read-only, from code on `main` (973448c). Nothing was run against a HOME.

## 1. Today's layout (verified in the tree)

- Tests: all flat under `tests/test_*.py` (about 140 modules) plus `tests/test_install.sh`. No test file
  exists inside any `skills/<name>/` folder (`find skills -name 'test_*'` is empty). There is no
  `tests/skills/<name>/` folder.
- Evals: 11 skills have `skills/<name>/evals/`.
  - New shape (`evals/evals.json` + `evals/trigger-queries.json`, inputs under `evals/files/`): 8 skills
    (ai-kit-commit-fold, ai-kit-gsd-curated-config, ai-kit-gsd-spec-discuss, ai-kit-spec-config,
    ai-kit-spec-execute, ai-kit-spec-execute-superpowers, ai-kit-spec-goal-prompt, jev-fast-decision;
    jev also has `cases.jsonl`, backend calibration data).
  - Old shape (Markdown scenarios only): ai-kit-spec-review (`01..04-*.md`), ai-kit-spec-review-checklist
    (`test-scenarios.md`, `orchestrator-integration.md`, `fixtures/`), ai-kit-spec-review-fixer
    (`test-scenarios.md`); ai-kit-gsd-curated-config also keeps four `.md` scenarios.
  - No evals: cst-refactor, markdown-to-pdf, ai-kit-cross-ai, ai-kit-session-wake, ai-kit-usage-metrics and
    the seven ai-kit-project-rules-* skills.
  - `tests/test_skill_evals_shape.py:23-25` globs `skills/*/evals/evals.json` and checks the shape;
    tests that read evals by path: test_jev_fast_decision, gsd_curated_eval + test_gsd_curated_eval,
    test_ai_kit_spec_goal_prompt_evals, test_ai_kit_spec_check_providers, test_arch.
- `scripts/` folders: 5 skills (markdown-to-pdf, ai-kit-gsd-spec-discuss, jev-fast-decision,
  ai-kit-spec-goal-prompt, ai-kit-commit-fold). The other code skills use a top-level `ai-kit-*.py` entry plus
  a package folder (for example `ai_kit_spec/`, `ai_kit_session_wake/`).
- Shared code: `skills/_shared/ai_kit_rules_common/` (no SKILL.md, so it is never linked). The six rules
  skills find it from their real (symlink-resolved) path, `<skills root>/_shared`
  (`skills/ai-kit-project-rules-*/ai_kit_project_rules_*/__init__.py:9-15`), and raise ImportError on a
  copy install; their SKILL.md files say so (`ai-kit-project-rules-agents/SKILL.md:27-32`).
- Frozen cross-skill allowlist: `tests/test_arch.py:1564-1630` (`CROSS_SKILL_ALLOWLIST`, 15 keys) checked
  against the literal `_CROSS_SKILL_FROZEN` (`:1632-1669`, "may only shrink"). Every entry is a reach into
  `ai-kit-spec-review` (`ai_kit_spec` imports or sys.path shims from curated-config, session-wake,
  execute-superpowers, goal-prompt's gp_host) or into `ai-kit-session-wake` (goal-prompt, and
  `tools/hooks/claude_session_wake.py`). `_shared` is out of this rule (`:1397`, "DIST-03's, Phase 52").
  Backlog 999.19 (remove the allowlist) is marked ABSORBED 2026-11-07 (`ROADMAP.md:1227`).

## 2. What `curl ... | bash` does today (read in code)

1. `tools/install.sh` parses args (`--branch`, `--dry-run`, convenience flags; `:98-113`), then picks
   BOOTSTRAP mode because no `setup.py` sits beside the piped script (`:73-89`).
2. Fetch into `INSTALL_DIR = ${AI_KIT_DIR:-${XDG_DATA_HOME:-~/.local/share}/ai-kit}` (`:53`):
   new dir -> `git clone --single-branch --branch main --depth 1` (`:135`); no git -> GitHub tarball
   extracted to a sibling temp dir and swapped in atomically (`:136-177`); existing clone ->
   `git pull --ff-only origin <current branch>` (`:220-232`), or a guarded branch switch with `--branch`.
   The whole repo lands there: skills with their evals, tests/, tools/, docs, .planning.
3. Requires python3, exports `AI_KIT_DIR`, `exec python3 tools/setup.py` (`:289-299`), the Textual wizard
   (or `install --headless`).
4. `setup.py` enumerates `skills/`, `agents/`, `commands/`; a skill is any dir with SKILL.md
   (`setup.py:949-978`), so `_shared` is skipped. It symlinks each selected whole folder:
   `~/.claude/skills/<name> -> <INSTALL_DIR>/skills/<name>` (`CLAUDE_CONFIG_DIR` honoured), agents into
   `~/.claude/agents/`. `PI_SKILLS` (`setup.py:49-50`: ai-kit-cross-ai, jev-fast-decision,
   ai-kit-session-wake, ai-kit-commit-fold) are also linked into `${PI_CODING_AGENT_DIR:-~/.pi/agent}/skills`
   when that dir exists. opencode reads `~/.claude/skills`; nothing goes to `~/.agents/skills`; codex and
   cursor get no skill links (README.md:58). Hook scripts are linked into pi `extensions/` and opencode
   `plugins/` (`setup.py:4676-4683`), Claude/Cursor hooks and status line are written into config JSON.
5. Because links point at whole folders, `evals/`, `evals/files/` and runtime `__pycache__/` ride along into
   every host; nothing is excluded. Real dirs or foreign symlinks at a link path are left alone (or backed
   up with consent / `--replace-existing`). Stale links into the install dir are pruned.
6. Updates: re-run the one-liner (pull) or `git -C ~/.local/share/ai-kit pull`; the symlinks make every
   host see the new code at once, no re-copy.
- Stale docs: README.md:20 says "symlinks every skill ... into ~/.claude/" (omits pi);
  `.claude-plugin/plugin.json` still says "a one-line installer that symlinks them into Claude Code";
  there is no `marketplace.json`.

## 3. The Agent Skills standard (pinned copy, sha 69ef37e9..., in the installed skill-judge)

- `references/agentskills/specification.md:8-19`: a skill is a dir with `SKILL.md`; optional `scripts/`,
  `references/`, `assets/`, and "any additional files or directories".
- `evaluating-skills.md:19,57-63`: test cases live in `evals/evals.json` inside the skill dir, inputs in
  `evals/files/`; run results go to a sibling `<skill>-workspace/`, not into the skill.
- `optimizing-descriptions.md`: trigger queries as a JSON list; names no fixed file.
- skill-judge rubric (`references/rubric.md:129-134,169`): output evals and `evals/trigger-queries.json`
  live in the skill's `evals/`; the script test lives in the repo's `tests/skills/<name>/`, "not in the
  skill (it is not shipped with it)"; 5/5/5 split with `scripts/`, 8/7 without.
- `npx skills` (research `.planning/research/2026-11-02-next-milestone/14-dist-layout-and-install.md`,
  skills@1.7.5 read in code): copies the whole skill folder except `.git`, `__pycache__`, `__pypackages__`,
  `metadata.json`; skips symlinks leaving the folder; strict YAML frontmatter; so `evals/` ships unless the
  source is a trimmed dist. `--copy` writes into each agent dir; pi and codex share `~/.agents/skills`.

## 4. The plan (ROADMAP / REQUIREMENTS)

- JDG-01 (`REQUIREMENTS.md:~124`): the judge prompt states one reading of the flat `tests/test_*.py`
  layout and of skills without `scripts/`, the same for every skill (Phase 32 criterion 1). So tests stay
  flat; the judge is told where they are.
- JDG-03 (32.4): every kept skill has `evals/evals.json`, ~20 trigger queries and tests; batches 32.1-32.4
  each add `evals/evals.json`, trigger queries and unit-tier tests per skill.
- DIST-01 (Phase 52): committed `dist/skills/<name>/` generated from `skills/` without evals and tests, with
  a rebuild-and-diff drift check. So evals stay in source `skills/<name>/evals/` and do not ship.
- DIST-03 / ARCH-02 (52): code-sharing skills install as a group or vendor the code; JSONC scanner and atomic
  writer get one copy-install-safe home. DIST-05: orphan scripts adopted, merged or deleted. ARCH-01:
  whole-tree layering test.
- DIST-02/04/06/07 (Phase 53): setup syncs each selected host with one pinned
  `npx skills add ... -a <host> -g --copy -y` after a dry run, migrates ai-kit symlinks to copies, removes
  only ai-kit's own copies; README documents plugin and `npx skills` installs; each host lists every skill
  once, pi keeps its own list; ai-kit installs only its own skills.
- 32.3 criterion 3: the shared secret scanner's home must survive copy installs.

## 5. Open questions for the phase 32 spec

1. Tests location: confirm the flat `tests/test_<skill>_*.py` layout stays (JDG-01's "one reading"), or
   move script tests to `tests/skills/<name>/` as the rubric names. Moving touches the parallel runner,
   `test_gate_scope.py`, the staged mapper and `E2E_RECORDED_SECS`.
2. Old Markdown eval scenarios (spec-review, checklist, fixer, curated-config): convert, keep beside
   `evals.json`, or delete in the batch phases.
3. The curl one-liner's end state is not written down: after Phase 53, does it still clone to
   `~/.local/share/ai-kit` and then run `npx skills add <clone>/dist/skills --copy`, or does it copy from a
   fetched dist only? Does the clone keep tests/evals/.planning (only dist reaches hosts)?
4. Updates under copies: symlinks auto-update today on `git pull`; with copies a pull changes nothing until a
   re-sync. Does the one-liner always re-sync, and is drift detected (`npx skills check/update` on a
   local-path source is unverified per research 14)?
5. Until Phase 52/53 land, every skill improved in 32.x still ships its `evals/` into hosts through the
   symlink; acceptable interim, or should setup exclude anything earlier?
6. Hooks: `tools/hooks/*` stay linked from the clone into pi/opencode and reach into
   `skills/ai-kit-session-wake` (allowlist entry). Phase 53 copies skills only; hooks keep needing the clone.
7. Public `npx skills add castocolina/ai-kit` finds `skills/` before `dist/` (research 14 section 1), so it
   would ship source plus evals; the README route must point into `dist/skills` (tree URL to a container
   is unverified) or add a manifest / `skills.sh.json`.
8. Shared code: vendor `ai_kit_rules_common` (moot if the seven rules skills are replaced first, Phase
   47.1) and decide vendor vs group for `ai_kit_spec` (spike flagged in research 14 section 4b).
9. Phase 32 counts "15 kept skills", but the batches 32.1-32.4 list 15 names without ai-kit-commit-fold;
   confirm whether commit-fold is in scope of the re-judge (it already has new-shape evals).
