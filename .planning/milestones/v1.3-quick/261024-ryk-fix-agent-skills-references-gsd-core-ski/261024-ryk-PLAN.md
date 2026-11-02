---
phase: quick-261024-ryk
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/config.json
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skill_scan.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py
  - skills/ai-kit-gsd-curated-config/SKILL.md
  - tests/test_curated_config_skills.py
  - tests/test_curated_config_plan_edit.py
  - tests/test_curated_config_apply.py
  - tests/test_curated_config_golden.py
  - tests/fixtures/curated_config_v2/golden/*.json
  - .planning/REQUIREMENTS.md
  - .planning/milestones/v1.3-phases/18-cross-ai-skills-apply-pipeline/18-CONTEXT.md
  - skills/ai-kit-gsd-spec-discuss/SKILL.md
  - skills/ai-kit-gsd-spec-discuss/references/analyzer-brief.md
  - tests/test_ai_kit_gsd_spec_discuss.py
autonomous: true
requirements: [SKL-03, SKL-04]

estimate:
  tokens: 185000
  raw_tokens: 185000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "In this repo, `gsd-tools query agent-skills` for gsd-assumptions-analyzer and gsd-advisor-researcher prints no `[agent-skills] WARNING` and emits `@skills/jev-fast-decision/SKILL.md`"
    - "curated-config recommend wires a skill only through a reference gsd-core resolves: a contained project copy, a global skill inside the host's global skills dir, a global skill an already-configured trusted root covers, or a global skill linked from an ai-kit install or checkout paired with a needs_choice trusted root for that install's skills dir in ~/ form whose why says machine-specific"
    - "Any other escaping global skill is not wired and gets a skill_unwired note naming the cause and the fix"
    - "No plan-set or plan-unset leaves an agent_skills entry gsd-core would skip, and apply / apply --dry-run refuse such a plan (hand-edited included), --force or not; configured roots are still never dropped (C-W8)"
    - "ai-kit-gsd-spec-discuss setup checks `query agent-skills` for gsd-assumptions-analyzer and gsd-advisor-researcher, reports each WARNING line with cause and fix, and never edits config; the analyzer brief says the analyzer never calls jev even when jev-fast-decision is wired into it"
  artifacts:
    - path: ".planning/config.json"
      provides: "agent_skills for both agents = [\"skills/jev-fast-decision\"]"
    - path: "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skill_scan.py"
      provides: "per-row ai_kit_skills_dir (ai-kit install detection)"
    - path: "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py"
      provides: "skip_reason, needed_root, global_ref_skip_reason; resolvable-only unwired_reason and trusted_roots"
    - path: "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py"
      provides: "effective_trusted_roots, skipped_skill_problem"
  key_links:
    - from: "skill_scan.scan_root row ai_kit_skills_dir"
      to: "skills.needed_root -> skills.trusted_roots -> recommend._skills_layer needs_choice"
      via: "inventory.json skills rows"
    - from: "plan_io.skipped_skill_problem"
      to: "plan_edit.plan_set / plan_unset (post-edit) and apply.prepare (before any write)"
      via: "direct call"
---

<objective>
Stop GSD agents from silently running without their configured skills. gsd-core skips a
`global:<name>` entry whose SKILL.md realpath is outside the runtime's global skills dir unless
`agent_skills_security.trusted_global_roots` covers it (live: `[agent-skills] WARNING: Global
skill "jev-fast-decision" failed path check (symlink escape?)`). Fix it in three places, per the
owner decisions of 2026-10-24 (OD-1..OD-3 below):

- OD-1: this repo's `.planning/config.json` references `skills/jev-fast-decision` (a contained
  project path) for both agents.
- OD-2: `ai-kit-gsd-curated-config` recommends only references gsd-core resolves, and never writes
  or keeps a `global:` entry gsd-core skips.
- OD-3: `ai-kit-gsd-spec-discuss` reports skipped entries at setup, and its analyzer never calls
  jev even when the skill is wired into it.

Planner choice for OD-2 case (c) (stated as the owner asked): the ai-kit-install trusted root
**stays a `needs_choice` approval**. It widens gsd-core's trust to every skill in that dir, so it
needs explicit consent. It is skipped (no entry, skill wired directly) only when an
already-configured root covers the skill's real dir (`skills.covered()`); that is the only
evidence the code has that the install dir is already trusted. This amends 18 D-34 (per-skill-dir
roots) and SKL-03, and the decline semantics of D-41.

Output: three commits (config chore, curated-config feature with tests and docs, spec-discuss
docs with a doc-pin test).
</objective>

<execution_context>
@.claude/gsd-core/workflows/execute-plan.md
@.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@AGENTS.md
@skills/ai-kit-gsd-curated-config/SKILL.md
@skills/ai-kit-gsd-spec-discuss/SKILL.md
@skills/ai-kit-gsd-spec-discuss/references/analyzer-brief.md
@.planning/milestones/v1.3-phases/18-cross-ai-skills-apply-pipeline/18-CONTEXT.md (D-02, D-31..D-36, D-41 only)

Live-verified by the planner (2026-10-24, scratch HOME, cleaned up):
- gsd-core `buildAgentSkillsBlock` (`.claude/gsd-core/bin/lib/init.cjs` ~3646-3770): `global:<n>`
  is accepted when `tryWithinRoot(<global dir>/<n>/SKILL.md, globalSkillsBase)` holds, or when a
  `loadTrustedGlobalRoots` entry (`security.cjs` ~177: `~/` expanded, non-absolute or missing
  dropped, realpath'd) contains it. A synthetic `~/.claude/skills/fake -> ~/ai-kit/skills/fake`
  link is skipped with no root, and accepted (`NOTE: ... accepted via trusted_global_roots`) with
  root `~/ai-kit/skills`. A project-relative entry must pass `tryWithinRoot(path, projectRoot)`
  and have a SKILL.md. The query exits 0 in every case: warnings go to stderr only.
- `query config-set agent_skills.<agent> '<json list>'` is accepted (dynamic key) and changes only
  that value: on a scratch copy of this repo's config the diff was exactly the one line.
- Baseline: the literal `gsd-core skips it` appears in `skills/ai-kit-gsd-curated-config/SKILL.md`,
  `.../ai_kit_gsd_curated_config/skills.py` and the three `golden/claude-*-adaptive.json`; the word
  `machine-specific` appears nowhere under `skills/ai-kit-gsd-curated-config/`; `query agent-skills`
  appears nowhere under `skills/ai-kit-gsd-spec-discuss/`. All targeted test modules pass at HEAD.

Interfaces the executor works against (current signatures):
- `skill_scan.scan_root(root, root_kind, label, home, plugin=None) -> list[dict]`; rows carry
  `name, root_kind, root, plugin, real_dir, real_dir_home, escapes_root, addressable, description`.
  Helpers `_real`, `_inside`, `_home_rel(real_dir, home)`. `scan_skills` overwrites
  `escapes_root` for project rows with `_escapes_project`.
- `skills.locate(name, inv)` (project > global > plugin, escaping project copies dropped),
  `reference_for(entry)`, `existing_roots(inv)`, `covered(value, real_dir, roots)`,
  `_has_usable_project_copy`, `unwired_reason(name, inv)` (None = wire, "" = not installed, text =
  note), `trusted_roots(wired, inv)`, `trusted_roots_candidate(candidates, inv)`,
  `merged_trusted_roots_why(candidates, inv)`, `_TRUSTED_ROOTS_WHY_TAIL`, `proposals`, `_wire_agent`.
- `plan_io`: `entry_effective_value(entry)` (set -> value, keep -> existing), `_plan_entry`,
  `home_relative_root(root)`, `_skill_value_problem(entry, where)`, `load_plan_and_inventory`
  (do NOT add the new check there: plan edits load through it, and a plan that cannot load cannot
  be fixed).
- `plan_edit.plan_set(call, key, raw)`, `plan_unset(call, key)`, `EditCall(plan, inv, force, encode)`,
  `PlanEditError`, `_check_agent_skills(inv, key, value)`, `_check_trusted_roots` (C-W8, unchanged).
- `apply.prepare(inputs, deps, encode)`: "the one validator path for dry run and apply"; refuses
  open `needs_choice` first.
- `cli._run_plan_edit` runs `plan_io.validate_plan(edited)` (plan only, no inventory) after every
  edit.
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Tracer: this repo's agents load jev-fast-decision through a project path (OD-1)</name>
  <files>.planning/config.json</files>
  <read_first>.planning/config.json</read_first>
  <precondition>`node .claude/gsd-core/bin/gsd-tools.cjs query agent-skills gsd-assumptions-analyzer` prints the "failed path check (symlink escape?)" WARNING, and `skills/jev-fast-decision/SKILL.md` exists in the checkout.</precondition>
  <action>Per OD-1, from the checkout root run gsd-tools `query config-set` twice, once per agent:
  key `agent_skills.gsd-assumptions-analyzer`, then key `agent_skills.gsd-advisor-researcher`. Pass
  the JSON list value `["skills/jev-fast-decision"]` in single quotes, through
  `node .claude/gsd-core/bin/gsd-tools.cjs`. Never hand-edit the file. Before committing,
  `git diff --numstat -- .planning/config.json` must print `2 2`: only the two list items change,
  and every other byte stays as it was. Then commit only that file:
  `chore(config): load jev-fast-decision by project path for the analyzer and advisor agents`.
  Let the pre-commit hooks run.</action>
  <verify>
    <automated>for a in gsd-assumptions-analyzer gsd-advisor-researcher; do out=$(node .claude/gsd-core/bin/gsd-tools.cjs query agent-skills "$a" 2>&1); { ! printf '%s\n' "$out" | grep -qF '[agent-skills] WARNING'; } && printf '%s\n' "$out" | grep -qF '@skills/jev-fast-decision/SKILL.md' || { echo "FAIL $a"; exit 1; }; done && python3 -c "import json; c=json.load(open('.planning/config.json')); assert c['agent_skills']=={'gsd-assumptions-analyzer':['skills/jev-fast-decision'],'gsd-advisor-researcher':['skills/jev-fast-decision']}, c['agent_skills']"</automated>
  </verify>
  <done>Both agents' agent-skills blocks include `@skills/jev-fast-decision/SKILL.md` with no WARNING; config diff is the two list items only; committed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: curated-config wires only skill references gsd-core resolves (OD-2)</name>
  <files>skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skill_scan.py, skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py, skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py, skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py, skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py, skills/ai-kit-gsd-curated-config/SKILL.md, tests/test_curated_config_skills.py, tests/test_curated_config_plan_edit.py, tests/test_curated_config_apply.py, tests/test_curated_config_golden.py, tests/fixtures/curated_config_v2/golden/*.json, .planning/REQUIREMENTS.md, .planning/milestones/v1.3-phases/18-cross-ai-skills-apply-pipeline/18-CONTEXT.md</files>
  <read_first>skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py, skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skill_scan.py (scan_root, _home_rel, scan_skills), skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py (_skill_value_problem, entry_effective_value, _validate_trusted_roots), skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py (plan_set, plan_unset, _check_agent_skills, _check_trusted_roots), skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py (prepare), skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py (_skills_layer), tests/test_curated_config_skills.py (_skill_row, _escaping_global, TestTrustedRoots), tests/test_curated_config_golden.py (build_golden_inventory), tests/test_curated_config_plan_edit.py (_write_pair and the trusted-roots tests)</read_first>
  <precondition>`git status --porcelain -- skills/ai-kit-gsd-curated-config tests/test_curated_config_skills.py tests/test_curated_config_plan_edit.py tests/test_curated_config_apply.py tests/test_curated_config_golden.py tests/fixtures/curated_config_v2/golden .planning/REQUIREMENTS.md` is empty. Another agent's Phase 25 work had uncommitted edits here at planning time, and this task must not mix with it: halt and report if any remain.</precondition>
  <behavior>
    - scan: a `~/.claude/skills/<n>` link into `<home>/.local/share/ai-kit/skills/<n>`, whose parent also holds `ai-kit-gsd-curated-config/SKILL.md` and `ai-kit-spec-review/SKILL.md`, yields `ai_kit_skills_dir == "~/.local/share/ai-kit/skills"`; without those two marker dirs, for a non-escaping row, for a project or plugin row, and for a parent outside home, it yields None
    - recommend: an escaping global skill with `ai_kit_skills_dir` is wired, and one `needs_choice` trusted-roots entry carries a single candidate whose value is the configured roots followed by the ai-kit dir, its `skills` lists every skill under that dir (two skills, one root), and its why and the entry why contain `machine-specific`
    - recommend: an escaping global skill already covered by a configured root is wired with no trusted-roots entry
    - recommend: an escaping global skill with no `ai_kit_skills_dir` and no covering root is not wired, no root is proposed, and its `skill_unwired` note names the cause (no trusted root covers it, or outside the home directory) and the fix (project `skills/<n>` copy, real dir in the host's global skills dir, or a configured trusted root, then re-run inventory and recommend)
    - plan-unset of the trusted-roots entry while agents hold a skill that needs it exits 2, names each agent, and prints a runnable `plan-set agent_skills.<agent> '<list without it>'`; after running those, the plan-unset succeeds
    - plan-set of a trusted-roots list that keeps the configured roots but lacks the needed ai-kit root is refused the same way, also with `--force`
    - plan-set `agent_skills.<agent>` with a skill whose root was declined is refused, and the refusal names the `plan-set agent_skills_security.trusted_global_roots '<list>'` that would admit it
    - plan-unset `agent_skills.<agent>` whose existing config value holds `global:<n>` that escapes uncovered (or has no global row) is refused with the fix
    - apply --dry-run and apply on a hand-edited plan holding a skipped reference exit 2 before any write
    - C-W8 drop refusal and the open-needs_choice apply refusal are unchanged
  </behavior>
  <action>Per OD-2. Write the failing tests first, from the behavior list above, in the existing
  modules. Use synthetic trees under `tempfile` only, with no absolute machine path, and never a
  real home. Then implement:

  (1) `skill_scan.py`: add the module constant `_AI_KIT_MARKERS = ("ai-kit-gsd-curated-config",
  "ai-kit-spec-review")` and a helper `_ai_kit_skills_dir(real_dir, home) -> str | None`. The helper
  takes the parent of `real_dir`. It returns `_home_rel(parent, home)` when every marker has
  `<parent>/<marker>/SKILL.md` as a file and the result is not `~/.`, and None otherwise. This one
  rule detects both the `curl | bash` install (`${AI_KIT_DIR:-${XDG_DATA_HOME:-~/.local/share}/ai-kit}`,
  `tools/install.sh`) and the checkout the install links point to: both are full ai-kit trees. In
  `scan_root`, every row gains `ai_kit_skills_dir`, computed only when `root_kind == "global"` and
  the row escapes its root, and None otherwise. Update the module docstring.

  (2) `plan_io._skill_value_problem`: validate `ai_kit_skills_dir` as None or a
  `home_relative_root` string, the way `real_dir_home` is checked. Rows from older inventories,
  which lack the key, read as None.

  (3) `skills.py`. Keep the existing phrases "outside the project", "outside the home directory"
  and "not installed": `tests/test_curated_config_plan_edit.py::test_agent_skill_check_matches_recommend`
  greps for them. Add these functions:
  - `_global_skip(row, roots) -> str | None`: None when the row does not escape, or when
    `covered(row real_dir_home or "", row real_dir or "", roots)` holds. Otherwise return the cause,
    naming the real dir in `~/` form, or saying "outside the home directory" when it has none.
  - `skip_reason(name, inv, roots) -> str | None`: the reference recommend writes resolves in
    gsd-core under `roots`. No located row means "not installed" or "project copy outside the
    project". A project or plugin row resolves (plugin behavior unchanged, D-32). A global row goes
    through `_global_skip`.
  - `needed_root(name, inv) -> str | None`: the located row's `ai_kit_skills_dir`, when that row is
    an escaping global row.
  - `global_ref_skip_reason(name, inv, roots)`: for an existing `global:<name>` config value. No
    addressable global row means gsd-core finds nothing; otherwise use `_global_skip`.

  Then change the existing functions:
  - `unwired_reason` returns None when `skip_reason(name, inv, existing_roots(inv))` is None, or
    when `needed_root` is set (case c). For a missing skill it keeps the current None / "" results.
    Otherwise it returns `not wired: <name>: <cause>, so gsd-core would skip global:<name>; fix: ...`
    with the fix list from the behavior block.
  - `trusted_roots`: one item per distinct `needed_root` of the wired skills that
    `skip_reason(..., existing_roots)` still skips. Each item is
    `{"value": root, "skills": [sorted names], "why": ...}`, so several skills under one install
    give one root.
  - `trusted_roots_candidate`: keeps the configured roots first (C-W8). Its why says it adds the
    skills dir of the ai-kit install the wired skills link to, and that the path is
    machine-specific: it is where ai-kit lives on this machine, and gsd-core drops it where the path
    does not exist.
  - `_TRUSTED_ROOTS_WHY_TAIL`: drop the sentence saying a declined root keeps the skill wired.
    Replace it with: declining (plan-unset) is refused while agent_skills entries still hold the
    skills it covers, so first run the plan-set commands the refusal prints. Add the
    machine-specific flag.
  - Check `recommend._skills_layer` against the new item shape; it should need no change.

  (4) `plan_io.py`: add two functions.
  - `effective_trusted_roots(plan, inv)`: with no entry, the configured roots. With an open
    `needs_choice` entry, its first candidate's `value` (the pending approval; apply refuses an open
    choice anyway). Otherwise `entry_effective_value`, keeping strings only (None becomes []).
  - `skipped_skill_problem(plan, inv, keys=None) -> str | None`: walk every `agent_skills.*` entry
    (only those in `keys` when keys is given) that is not `needs_choice`. For op `set`, check each
    bare name with `skills_mod.skip_reason`. For op `keep`, check each existing `global:<n>`
    single-segment ref (a string value counts as a one-item list) with
    `global_ref_skip_reason`. Return None when nothing is skipped. Otherwise return one message per
    entry: the skipped items, the cause, and the fix. When `needed_root` gives a root missing from
    the effective roots, the fix is `plan-set agent_skills_security.trusted_global_roots '<roots +
    root>'`. Always add the drop alternative `plan-set agent_skills.<agent> '<remaining bare
    names>'`; for keep entries, a ref's bare name is its last `:` / `/` segment. Quote JSON with
    `shlex.quote(json.dumps(..., separators=(",", ":")))`, as `merged_trusted_roots_why` does.
    Stay inside the pylint limits (max-branches 12, max-returns 6) by splitting helpers.

  (5) `plan_edit.py`: at the end of both `plan_set` and `plan_unset`, on the edited plan, call
  `plan_io.skipped_skill_problem(plan, call.inv, ...)`. Pass `keys=None` when the key is the
  trusted-roots key, and `keys={key}` when the key starts with `agent_skills.`. Raise
  `PlanEditError` with the message. This refusal is force-immune: say so in a one-line comment.
  Leave `_check_agent_skills` and `_check_trusted_roots` as they are, apart from docstrings.

  (6) `apply.prepare`: right after the open-needs_choice refusal, return
  `None, None, "apply refused: " + problem` when `plan_io.skipped_skill_problem(inputs.plan,
  inputs.inv)` reports one. This covers apply and dry run, hand-edited plans included.

  (7) Golden tree (`tests/test_curated_config_golden.py::build_golden_inventory`): add
  `<home>/.local/share/ai-kit/skills/`. Put a described `react-dev` there, plus the two marker
  skills with no description (no description means no proposal notes), and point the
  `~/.claude/skills/react-dev` link at that copy. Keep the real `~/.agents/skills/react-dev`
  (codex's root), so other hosts keep their wiring. Regenerate with
  `UPDATE_GOLDEN=1 python3 -m unittest tests.test_curated_config_golden -k TestGoldenPlans`, then
  re-run without the variable. Expected drift: `inventory_digest` in every golden (rows gained a
  key). The three `claude-*-adaptive` trusted-roots entries also change: candidate value
  `~/.local/share/ai-kit/skills` and the new why texts. Investigate any other change. Update the
  plan-edit tests' literal `~/.agents/skills/react-dev` where it means the golden candidate. Update
  the `TestTrustedRoots` cases: their `_escaping_global` helper gains an `ai_kit_skills_dir`
  parameter, the mechanics tests (merge, quoting, coverage) use ai-kit rows, and per-skill-dir
  proposals are now asserted as not wired.

  (8) Docs, in the same commit:
  - `SKILL.md` §Skills: replace the "Not wired" and "Trusted-root approval" bullets with the
    resolvable-only rule (cases a-c, everything else not wired with a cause-and-fix note), the
    machine-specific `~/` install root that stays a `needs_choice`, the refused decline and how to
    drop dependents first, and apply refusing a skipped reference even with `--force`. In step 3,
    point the "Trusted roots" bullet at that decline rule.
  - `.planning/REQUIREMENTS.md` SKL-03 and `18-CONTEXT.md` D-34 (D-41's decline): add one dated
    `*(amended 2026-10-24, quick 261024-ryk, owner decision)*` sentence each. Keep the original
    text.

  Commit everything as one change: `feat(curated-config): wire only skill references gsd-core
  resolves`. Stage only these paths.</action>
  <verify>
    <automated>python3 tools/run_unittest_parallel.py tests.test_curated_config_skills tests.test_curated_config_plan_edit tests.test_curated_config_golden tests.test_curated_config_recommend tests.test_curated_config_apply tests.test_curated_config_inventory tests.test_curated_config_followups tests.test_gsd_curated_eval tests.test_curated_config_e2e tests.test_curated_config_apply_e2e tests.test_ai_kit_gsd_curated_config && ! grep -qF 'gsd-core skips it' skills/ai-kit-gsd-curated-config/SKILL.md skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py tests/fixtures/curated_config_v2/golden/*.json && grep -qF 'machine-specific' skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py && grep -qF 'machine-specific' skills/ai-kit-gsd-curated-config/SKILL.md && grep -qF 'ai_kit_skills_dir' skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skill_scan.py</automated>
  </verify>
  <done>Every behavior bullet has a passing test; goldens were regenerated with only the expected drift; no path in the plan flow can write or keep a `global:` entry gsd-core skips; SKILL.md, SKL-03 and D-34 match the code; one commit.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: spec-discuss reports skipped agent skills at setup; the analyzer never calls jev (OD-3)</name>
  <files>skills/ai-kit-gsd-spec-discuss/SKILL.md, skills/ai-kit-gsd-spec-discuss/references/analyzer-brief.md, tests/test_ai_kit_gsd_spec_discuss.py</files>
  <read_first>skills/ai-kit-gsd-spec-discuss/SKILL.md (§0 steps 2-3, §2 analyzer paragraph), skills/ai-kit-gsd-spec-discuss/references/analyzer-brief.md, tests/test_ai_kit_gsd_spec_discuss.py (the doc-pin class near line 1040)</read_first>
  <behavior>
    - SKILL.md contains `query agent-skills`, both agent names, the literal `[agent-skills] WARNING`, `ai-kit-gsd-curated-config` as the fix, and says the skill never edits config itself
    - analyzer-brief.md tells the analyzer it never calls jev even when `jev-fast-decision` is among its agent skills, and that the ladder, consent and the log belong to the orchestrator
  </behavior>
  <action>Per OD-3. First add the doc-pin test to the existing doc class in
  `tests/test_ai_kit_gsd_spec_discuss.py`, covering the behavior bullets. Normalize whitespace the
  way the neighbouring tests do, and watch it fail. Then edit, without renumbering any §0 step
  (later steps cite "step 6" and "step 7"):

  - SKILL.md §0 step 3 (Detect backends): append the wiring check. It is one portable loop over
    `gsd-assumptions-analyzer gsd-advisor-researcher` that runs `gsd_run query agent-skills "$a"`
    and keeps stderr lines matching `[agent-skills] WARNING`. Say that gsd-core exits 0 and only
    drops the skipped entry from that agent's prompt, so every line is reported verbatim with its
    cause:
    - "failed path check (symlink escape?)": the skill's real path is outside the host's global
      skills dir and no `agent_skills_security.trusted_global_roots` entry covers it;
    - "not found": nothing is at that path.

    The fix is to re-run `ai-kit-gsd-curated-config`, which wires only references gsd-core
    resolves (a project copy such as `skills/<name>`, or a trusted ai-kit install). The skill never
    edits config itself, and the run continues without that skill.
  - SKILL.md §2: the analyzer sentence becomes: it returns "Jev question" lines and never calls jev,
    even when `jev-fast-decision` is wired into it (SKL-04); the ladder, consent and the answer log
    belong to the orchestrator (this skill), through the shared client.
  - analyzer-brief.md: extend the existing "Do NOT call jev, Laya or TypeSafe yourself" line in the
    template with the same even-when-wired rule. Extend the "No jev" why-bullet: the wired skill
    shapes the question format only.

  Commit as one change: `docs(spec-discuss): check agent-skills wiring at setup; analyzer never
  calls jev`. Finally, list in the SUMMARY the materially changed skill docs for the
  orchestrator's skill-judge loop, and do not run the judge yourself:
  `skills/ai-kit-gsd-curated-config/SKILL.md`, `skills/ai-kit-gsd-spec-discuss/SKILL.md`,
  `skills/ai-kit-gsd-spec-discuss/references/analyzer-brief.md`.</action>
  <verify>
    <automated>python3 tools/run_unittest_parallel.py tests.test_ai_kit_gsd_spec_discuss && grep -qF 'query agent-skills' skills/ai-kit-gsd-spec-discuss/SKILL.md && grep -qF 'gsd-advisor-researcher' skills/ai-kit-gsd-spec-discuss/SKILL.md</automated>
  </verify>
  <done>Setup check and analyzer rule documented and pinned by a test; one commit; the SUMMARY names the three skill docs for the orchestrator's skill-judge run.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| filesystem -> inventory | Skill trees and symlinks under HOME, or a checkout, decide which trusted root is offered |
| plan.json -> apply | A hand-edited plan reaches the config writer |
| project config -> gsd-core | A trusted root widens which SKILL.md files every agent prompt includes |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-ryk-01 | Elevation of Privilege | skills.trusted_roots (install skills dir as root) | medium | mitigate | Stays a `needs_choice` approval unless a configured root already covers it. Both ai-kit marker skills must exist. The value must pass `home_relative_root` (a `~/` path inside HOME). C-W8 never drops configured roots |
| T-ryk-02 | Tampering | plan.json hand edits -> apply | medium | mitigate | `apply.prepare` refuses any plan with a reference gsd-core would skip, before writing, force-immune |
| T-ryk-03 | Information Disclosure | machine-specific `~/` root in a committed config | low | accept | Flagged machine-specific in the why. Only a home-relative path, never absolute. gsd-core drops it where it does not exist |
| T-ryk-04 | Tampering | .planning/config.json edit (Task 1) | low | mitigate | gsd-tools config-set only (live-verified to change only the target value), then the `git diff --numstat` check |
| T-ryk-SC | Tampering | npm/pip/cargo installs | low | accept | This plan installs no packages |
</threat_model>

<verification>
- Task verifies above, then `make validate` and `make test` from the checkout root (AGENTS.md: the
  Python suite alone does not cover installer behavior).
- `git status --short` shows no file this plan created or changed left uncommitted; unrelated
  dirty work is untouched.
- `git log --oneline -3` shows exactly the three commits, hooks run (never `--no-verify`).
</verification>

<success_criteria>
- This repo's two agents load jev-fast-decision (no WARNING).
- curated-config: OD-2 cases (a)-(c) wire. Everything else is a cause-and-fix note. No edit path or
  apply writes or keeps a skipped `global:` entry.
- spec-discuss: setup reports skipped entries; the analyzer never calls jev.
- `make validate` and `make test` green. The skill-judge loop on the listed docs is left to the
  orchestrator.
</success_criteria>

<output>
Create `.planning/quick/261024-ryk-fix-agent-skills-references-gsd-core-ski/261024-ryk-SUMMARY.md` when done
</output>
