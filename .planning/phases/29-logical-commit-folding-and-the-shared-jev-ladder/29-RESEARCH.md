# Phase 29: Logical-commit folding and the shared jev ladder - Research

**Researched:** 2026-11-04
**Domain:** git plumbing fold engine, GSD 1.20.0 capability hook, shared jev ladder move, structural/text tests
**Confidence:** HIGH on spike, fold plumbing and inventory (all run or read this session); MEDIUM on judge procedure

<user_constraints>
## User Constraints (from CONTEXT.md)

D-01..D-16 and the 10 SPEC requirements are locked; read `29-CONTEXT.md` and `29-SPEC.md`. Not restated here.
Key ones for the planner: D-01 temporary `ai-kit-commit-fold` skill (stdlib script + policy in `references/`);
D-02 GSD hook at `execute:wave:post`, **spiked first, FAIL returns to owner, no silent fallback**; D-03 superpowers
adapter step; D-10 plumbing mechanics; D-12 `jev_review.py` gains `ladder`/`detect` plus a new module beside it;
D-13 per-caller lookup copy + drift test; D-14 `decide.py` deleted same change; D-16 judge bar for 5 SKILL.md files.
Deferred (ignore): branches/pushes/PRs (29.1), playbook (47), advisory-hook reminder (49), Zen removal (32.1).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FLOW-01 | Fold each plan into logical-feature commits | Spike (hook form), fold plumbing prototype, input checkpoint shape, adapters |
| JEV-06 | Shared home for the jev ladder client | decide.py inventory, caller list, lookup drift test, text/structural tests |
</phase_requirements>

## SPIKE: PASS - `ref.command` (a gsd-tools command family shipped by the capability)

Run on gsd-core **1.20.0** (`.claude/gsd-core/VERSION` = `1.20.0`, [VERIFIED: file read]) in a scratch project and
scratch HOME. Scripts and sources are in the gitignored `tmp/plan-29/spike/` (`setup.sh`, `install.sh`, `src/fold-*`).
Environment: `AI_KIT_REFUSE_REAL_HOME=1`, `HOME` and `GSD_HOME` set to `tmp/plan-29/spike/home`.

**Setup facts**
- A project-local gsd-core copy needs **`.claude/scripts/`** beside `.claude/gsd-core/` (`bin/lib/command-roster.cjs`
  requires `../../../scripts/fix-slash-commands.cjs`; without it every command crashes with `MODULE_NOT_FOUND`).
  A scratch fixture must copy both dirs. [VERIFIED: observed failure and fix]
- Third-party capability bundle lives at `<bundle>/capability.json` and installs to
  `<project>/.gsd/capabilities/<id>/` (project scope) with a ledger `<project>/.gsd-capabilities.json`; consent
  records go under `$GSD_HOME/.gsd/consent.json`. [VERIFIED: `find` output; `capability-loader.cjs:12-13`]

**Working manifest (the form that passes)** `capability.json`, validated by `validateCapability`
(required: `id` kebab = folder name, `role:"feature"`, `version` semver, `title`, `description`, `tier`, `requires`,
`skills`, `agents`, `config`, `steps`, `contributions`, `gates`; `engines.gsd` and `runtimeCompat` as below):
```json
{"id":"fold-cmd","role":"feature","version":"0.1.0","title":"Fold cmd","description":"spike command step","tier":"full","requires":[],
 "engines":{"gsd":">=1.6.0"},"runtimeCompat":{"supported":["*"],"unsupported":[]},
 "skills":[],"agents":[],"hooks":[],"config":{},
 "commands":[{"family":"fold-cmd","module":"fold-cmd.cjs","router":"route"}],
 "steps":[{"point":"execute:wave:post","ref":{"command":"fold-cmd run"},"produces":[],"consumes":[],"onError":"skip"}],
 "contributions":[],"gates":[]}
```
`fold-cmd.cjs` sits **at the bundle root** (module must match `/^[A-Za-z0-9._-]+\.cjs$/`, no path) and exports
`route({args, cwd, raw, error})` synchronously (a Promise is rejected). [VERIFIED: `capability-validator.cjs:439-470`;
`gsd-tools.cjs:565-650`; install blocked until the file existed at the bundle root]

**Install commands** (run with the project-local `gsd-tools.cjs`):
- `node .claude/gsd-core/bin/gsd-tools.cjs capability install <bundle-dir> --scope project` -> for a command module this
  **aborts** (exit 1, `requiresConsent`) and prints "command modules (1): require()'d into the GSD CLI process".
- Same plus `--yes` -> `{"status":"installed"}`. [VERIFIED: observed]

**Observed dispatch** `gsd-tools loop render-hooks execute:wave:post --raw` returns for the installed capability:
`{"capId":"fold-cmd","kind":"step","ref":{"command":"fold-cmd run"},"onError":"skip"}` (plus first-party drift/ui gates).
`execute-phase.md` step 5.75 (lines 979-1000) dispatches it **after worktree merge-back, post-merge tests and the
tracking updates**, as prose via `loop-hook-dispatch.md`: validate `ref.command` in-context against
`^[a-z][a-z0-9-]*( [a-z][a-z0-9-]*)*$`, then run `gsd_run ${ref.command} --phase "${PHASE_NUMBER}" --raw`.
Running `gsd-tools fold-cmd run --phase 7 --raw` reached the module with
`args = ["fold-cmd","run","--phase","7"]`, `cwd` = project root; the module spawned `python3` (argv list, no shell) and
its stdout came through. [VERIFIED: observed]

**What the hook receives:** the **phase number and the project cwd only**. No wave number, no plan ids, no tested tip.
The fold command must derive the wave's plans itself (plans with a SUMMARY in the phase dir whose commits are not yet
folded; commits scoped `({phase}-{plan})`) and take the current branch tip after the post-merge tests as the tested tip.

**Why not the other forms (not proven to work, do not use)**
- `ref.agent` and `ref.skill` install and render (`{"ref":{"agent":"ai-kit-commit-fold"}}` /
  `{"ref":{"skill":"commit-fold"}}`), but `capability install` + `capability set --on --runtime claude --scope project`
  wrote **no** `.claude/agents/*` or `.claude/skills/*` file; the agent/skill bodies stay in
  `.gsd/capabilities/<id>/{agents,skills}/`. `surface.cjs:254-257` says third-party capability agents are not surfaced
  ("agents are a follow-up"). A step dispatching a subagent type or `gsd-<stem>` skill that no host file defines has
  nothing to run. Whether `gsd install` later materializes capability skills was **not** tested. [VERIFIED: tree listing;
  CITED: surface.cjs comment]
- A `contribution` (inline text injected into the orchestrator at `execute:wave:post`) is a fourth form, not tested.
  It is prose the orchestrator may paraphrase; `ref.command` is deterministic. [ASSUMED]

**Residual risks the plan must carry (D-02 says no silent fallback, so these are tasks/verifications, not escapes)**
1. Dispatch is LLM-executed prose and "advisory by construction": a skipped or failed step never blocks the wave. The tree
   proof makes a missed fold safe (nothing moves), but the plan's UAT must state that a missed fold leaves plan commits
   unfolded. Phase verification should run `fold` check over the phase range as a backstop (inline fallback = the same
   command run by hand).
2. Project-scope install creates untracked `.gsd/capabilities/` and `.gsd-capabilities.json`; the fold's dirty-tree guard
   would refuse. They must be committed or gitignored in the target project. A fresh clone needs `--yes` re-consent
   (consent lives in `$GSD_HOME`, not the repo). [VERIFIED: file locations; consent behaviour inferred from
   `capability-command-router.cjs:263-290` - ASSUMED for the fresh-clone case]
3. Global scope would write `~/.gsd`; the project rules forbid user-level GSD state. Use `--scope project` only.
4. The command module is a node `require()` inside the GSD CLI process (consent-gated). Keep it ~20 lines: find the
   installed fold script by the D-13 lookup (a JS copy of the lookup -> the drift test must cover the JS copy too) and
   `execFileSync("python3", [script, ...fixedArgs])`. Do not copy the Python script into the bundle (drifts).
5. Who runs `capability install --yes` is undecided (see Open Questions).

## Summary

The GSD hook works through a **command family**: a tiny node module in a capability bundle that runs the stdlib Python
fold script after each wave. The fold engine itself is straightforward git plumbing; a prototype folded a 4-commit,
two-feature plan in **0.05 s** wall (including building the synthetic repo), with the tree proof and tag. The jev
ladder move is mostly mechanical (decide.py 649 lines -> a module beside `jev_review.py`), but three things are not
mechanical: jev's SKILL.md does not yet document the lookup order D-13 requires it to; goal-prompt has two other
cross-skill CLI paths that a literal R9 structural rule would flag; and 4 of the 5 SKILL.md judge baselines are old-rubric.

**Primary recommendation:** build in vertical slices: (1) fold engine + policy + tests, (2) GSD capability command +
superpowers step, (3) ladder move + callers + structural/text tests, (4) judge loop. Use `ref.command`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fold engine (plumbing, guards, tag, report) | stdlib Python script in `ai-kit-commit-fold` | - | pure git, no host; callers call it directly (D-01) |
| GSD trigger | GSD capability command module (node) | fold script | only deterministic `execute:wave:post` form |
| superpowers trigger | `ai-kit-spec-execute-superpowers` SKILL.md step | fold script | agent follows SKILL.md (D-03) |
| Grouping proposal | `jev-fast-decision` ladder entry point | rule-based grouping in fold script | advisory only (D-07) |
| Ladder client | `skills/jev-fast-decision/scripts/` | - | single owner (D-12) |
| Installed-skill lookup | each code caller (small copy) | drift test | copy installs must work (D-13, DIST-03) |

## Standard Stack

stdlib Python (project target py312; `python3` resolves to 3.14.7 on this machine), `git` plumbing, node (v24.21.0 here)
only for the capability command module. **No external packages are installed by this phase** -> Package Legitimacy
Audit not applicable. Dev tools already pinned in `uv.lock` (ruff, pylint, pyright, vulture). [VERIFIED: AGENTS.md
Tools and Stack; `node --version`]

## Architecture Patterns

### System Architecture Diagram
```
GSD:  execute-phase wave N done -> merge-back -> post-merge tests -> tracking updates
        -> render-hooks execute:wave:post -> orchestrator runs `gsd-tools fold-cmd run --phase N`
        -> fold-cmd.cjs --(lookup)--> fold.py checkpoint(GSD adapter: plans of phase N, in plan order)
superpowers: last task review passes -> adapter step -> fold.py checkpoint(superpowers adapter)
                                   |
checkpoint JSON --> guards (clean tree, branch==tested tip, no commit reachable from main/merged, no foreign merge)
   --> group (rule-based from candidates; jev item per commit via jev ladder, advisory) --> validate partition
   --> build commits in temp index (GIT_INDEX_FILE) --> compare tree ids --> tag backup --> update-ref new old
   --> <=5 line report (subagent or inline)
```

### Recommended Project Structure
```
skills/ai-kit-commit-fold/
  SKILL.md                      # judge bar; points to the policy, restates nothing
  references/folding-policy.md  # the one policy text (D-11), phrases pinned by doc-contract test
  scripts/fold.py               # CLI: fold <checkpoint.json> | adapt-gsd | adapt-superpowers ; report renderer
  scripts/fold_git.py (optional)# plumbing helpers; keep stdlib-only, top-level role-prefixed names
  gsd-capability/{capability.json,fold-cmd.cjs}   # bundle installed with `capability install`
  evals/ (evals.json, trigger-queries.json, files/)  # new-shape evals (goal-prompt shape)
skills/jev-fast-decision/scripts/jev_review.py (+ `ladder`, `detect`) and a new ladder module beside it
```

### Fold engine mechanics (prototype `tmp/plan-29/fold_proto.py`, run OK)
Sequence confirmed against a synthetic repo (init -> base -> 4 commits on a plan branch -> fold):
1. Guards before any write: `git status --porcelain` empty; `rev-parse <ref>` == tested tip (else "branch moved");
   every commit of `rev-list base..tip`: `git merge-base --is-ancestor <c> <main>` exit 0 -> refuse (exit 1 = not an
   ancestor = fine, exit >1 = error; **do not treat exit 1 as failure**, the first prototype did and crashed);
   merge commits in range: allow only subject `chore: merge executor worktree (<branch>)` (the exact
   `git merge --no-ff --no-edit -m` message in `bin/lib/worktree-safety.cjs`, D-05) - re-read that file to quote it
   verbatim in the plan; unresolved main/base branch -> refuse with a reason; empty range / single commit -> "nothing to fold".
2. Per-path final state: `git diff --name-status -z --no-renames base tip` (NUL-split: UTF-8 and odd paths survive).
3. Temp index: `GIT_INDEX_FILE=<tempfile> git read-tree base`; per feature, for each path claimed by that feature:
   deleted -> `update-index --force-remove -- path`; else `update-index --add --cacheinfo mode,sha,path` with
   mode/sha from `git ls-tree tip -- path`; `write-tree`; `commit-tree <tree> -p <parent> -F -` with the message on stdin
   **encoded UTF-8 bytes** (passing `str` as `input=` raises TypeError; `-F -` keeps multi-line and non-ASCII exact).
   The last feature also takes every unclaimed path (this is where D-08 docs changes land). Delete the temp index in `finally`.
4. Proof: `rev-parse <folded>^{tree}` == `rev-parse <tip>^{tree}`; mismatch -> refuse, no tag, ref untouched.
5. `git tag ai-kit-fold/<unit>/<old-short-sha> <tip>` then `git update-ref <ref> <new> <tip>` (third arg = expected old;
   fails if the ref moved). Tag before ref move, delete the tag if `update-ref` fails (SPEC: no tag left behind on refusal).
6. Working tree/index are never touched; after `update-ref` the checked-out branch's worktree matches the new tip's tree
   (equal trees), so `git status` stays clean. Confirm in the real test (prototype did not assert it).
7. Environment for fixture repos: `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null` and explicit
   `GIT_AUTHOR_*`/`GIT_COMMITTER_*`; run with `AI_KIT_REFUSE_REAL_HOME=1`. The runner keeps `GIT_EXEC_PATH` only
   (`tools/run_unittest_parallel.py` `GIT_KEPT_VARS`). Folded commits should keep the original author of the feature's
   first commit via `GIT_AUTHOR_*` taken from `git log` (planner decision; the prototype used fixed identity).

**Shared-path rule (D-09):** a path changed by two candidate features cannot be split by this plumbing (the prototype
put `a.py` whole into the first claimant, which would make the second commit's tree not the feature's own change).
Apply union-find over candidates by shared paths *before* building (D-06 already merges tasks sharing files) and, when a
jev partition separates them, merge them and put the reason in the report line. This is exactly the "fold always
finishes, never an unbuildable commit" rule.

**Ordering:** features ordered by first original commit (SPEC ordering edge). **Idempotency (recommendation):** add a
trailer `Ai-Kit-Fold: <unit>` to folded commit messages and skip commits carrying it, so a re-run (the hook may fire
again) reports "nothing to fold". Folded subjects must not reuse the `({phase}-{plan})` scope alone, else re-detection
is ambiguous. [ASSUMED design]

**Timings:** prototype end-to-end 0.05 s for 4 commits; ~12 git subprocess calls. Tests: build fixtures with a single
helper per test class (`setUpClass` repo + `git clone`/`worktree`-free copies), no sleeps. Expect <0.3 s per test.

### Input checkpoint shape (framework-neutral, for 29.1 R1)
```json
{"schema": 1, "unit": "29-01", "base": "<sha>", "range": "<base>..<tip>", "tip": "<tested tip sha>",
 "ref": "refs/heads/<branch>", "base_branch": "main",
 "own_merge_subjects": ["chore: merge executor worktree ("],
 "candidates": [{"id": "t1", "title": "feature name", "files": ["a.py","tests/test_a.py"], "summary": "task text"}],
 "docs_paths": [".planning/phases/..", ".planning/STATE.md"]}
```
The engine reads only this JSON (names no framework). `own_merge_subjects` is how the GSD adapter declares its own
merge-back; the engine's default is "any merge refuses". 29.1 R1 lists: unit id and kind, target branch, branch name,
checkpoint range and tested tip - the shape above is a strict subset, so 29.1 can add fields without breaking it.
- **GSD adapter:** range = commits whose subject scope is `({phase}-{plan})` plus its `docs({phase}-{plan})` commit plus
  that plan's merge-back (`chore: merge executor worktree (<branch>)`), `base` = parent of the first; plans of a wave in
  plan order so the later plan's `base` is the earlier folded tip. Candidates from each PLAN.md task's files
  (`<files>` element / task `files` field - read a real PLAN.md to pin the exact tag before writing the parser; not
  verified this session). Docs changes (SUMMARY, STATE, ROADMAP, REQUIREMENTS) = `docs_paths`, go to the last feature (D-08).
- **superpowers adapter:** range = `git merge-base HEAD <base-branch>`..tip; candidates from `### Task N: <heading>` and
  its `Files:` lines under `docs/superpowers/plans/*.md` (verify the heading/`Files` convention against a real plan in
  `docs/superpowers/plans/` before parsing; not verified this session).
- A commit that matches no candidate joins the feature whose files it touches (D-06).

### Jev grouping item (D-07)
One `choice` item per commit; `instructions`/`context` carry the subject, path names and task summary only; options =
candidate ids. The existing ladder guard rejects fences and key shapes (decide.py `_SECRET_RE`, `MAX_FIELD_CHARS = 1500`).
Accept the partition only if every commit is placed exactly once and no code path is separated from its test path
(path-pair rule: `x.py`<->`tests/test_x.py` and same-candidate files); else rule-based decides; log source
(`jev|rules`) in the report/log line.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic ref move | `reset --hard`, checkout | `update-ref <ref> <new> <old>` | compare-and-swap, no worktree touch |
| Temp commit assembly | working-tree commits | `GIT_INDEX_FILE` + `commit-tree` | working tree never touched |
| Ladder validation/scrub | a new client in each caller | the moved `decide.py` code (`item_error`, `partition`, `child_env`, allowlists) | moves as-is (CONTEXT) |
| JSONC/JSON config writes | n/a here | `_atomic_write_json` already exists | AGENTS.md rule if any config write is added |

## Runtime State Inventory (move/delete phase: decide.py)

| Category | Items Found | Action |
|----------|-------------|--------|
| Stored data | jev consent file `.../ai-kit/jev-consent.json` and answer log (owned by `jev_review.py`) | none: format and path unchanged by the move; keep `_CONSENT_FILE_TAIL` behaviour |
| Live service config | none in git; Laya `127.0.0.1:8010`, TypeSafe env (not touched) | none |
| OS-registered state | `~/.claude/skills/*` and `~/.pi/agent/skills/jev-fast-decision` are symlinks into the main checkout (SPEC background) | none for jev; **new skill `ai-kit-commit-fold` needs linking** by the installer (`tools/install.sh` scans `skills/`; pi mirroring via `PI_SKILLS` in `tools/setup.py:48`) |
| Secrets/env vars | `JEV_BACKEND`, `JEV_ALLOW_REMOTE`, `JEV_MIN_CONFIDENCE`, `GSD_PATH_JEV*` scrubbed by `child_env` | keep the scrub list verbatim |
| Build artifacts | `pyproject.toml:111,137` list `skills/ai-kit-gsd-spec-discuss` and `.../scripts` (tool paths, probably pyright/pylint roots) | after deleting `decide.py` the dir still exists (`phase_range.py`, `edge_floor.py`); add `skills/ai-kit-commit-fold/scripts` and the jev scripts dir if not covered; re-run `make validate` |

## jev ladder inventory (task 4)

**decide.py (649 lines)** [VERIFIED: read]: constants (`CLIENT_REL`, `CALL_TIMEOUT_SECONDS = 30`, `CLIENT_PROTOCOL_RE`
requiring the text line `CLIENT_PROTOCOL = 2`, `_CONTROL_NAMES`/`_CONTROL_PREFIXES`, `ITEM_KEYS`, `ITEM_TYPES`,
`MAX_FIELD_CHARS = 1500`, `_SECRET_RE`, closed vocabularies `_STATUS_CODES`, `_KEY_SOURCES`, `_KEY_CHECKS`, shape regexes);
`Seams`/`real_seams`; lookup `client_candidates(env, override)` (override, `AI_KIT_JEV_CLIENT`, then roots: own skills root,
`CLAUDE_CONFIG_DIR|~/.claude`/skills, `~/.agents/skills`, `$XDG_CONFIG_HOME|~/.config`/opencode/skills,
`CURSOR_CONFIG_DIR|~/.cursor`/skills, `PI_CODING_AGENT_DIR|~/.pi/agent`/skills), `find_client`, `client_ok`; validation
`item_error`, `partition`; public mappers `public_backends`, `public_consent_used`, `public_remote_available`,
`public_consent`, `public_consent_grant`; `child_env`, `reviewed_head`, `call_client`, `closed_status`, `typed_answer`,
`fill_columns`, `run_ladder`, `detect`, `consent`, `build_parser` (`detect`, `ladder [--second-opinion]`,
`consent grant|revoke|show <backend>`, `--client`), `main` (exit 2 on unusable stdin).
**Design note:** decide.py runs the client in a *child process* with a scrubbed env and a protocol-text check. After the
move, `jev_review.py ladder` should keep running the client as a child (the same file) so the scrub, one-subprocess
count and fake-client tests carry over unchanged; the `own root` lookup step becomes trivial (itself) but `--client` and
`AI_KIT_JEV_CLIENT` overrides must keep working for tests. `jev_review.py` today: `build_parser` at line ~2010 has
`--probe`, `--skip-local`, subcommand `consent` and a default stdin call; add `ladder` and `detect` as sibling subparsers
(sub must stay non-required). `CLIENT_PROTOCOL = 2` line must stay (comment at line 43 says decide.py reads it).

**Tests to move** from `tests/test_ai_kit_gsd_spec_discuss.py` (1285+ lines) to `tests/test_jev_fast_decision.py` and
re-point `SCRIPTS / "decide.py"` to the jev entry: `_TmpHome` (155), `TestItemError`, `TestPartitionIds`, `TestTypedAnswer`,
`TestFindClient`, `TestLadderCli` (350-770; includes the leaky-client, scrubbed env, one-subprocess, consent, second-opinion,
TypeSafe-not-OpenCode tests). **Stay** in the spec-discuss test: `TestPhaseRange`, `TestEdgeFloor`, `TestSkillContract`
(but update the assertions that expect backend/consent text in SKILL.md/decision-table: `test_setup_checks_agent_skills_wiring...`
1077, `test_analyzer_never_calls_jev...` 1102, `test_decision_table_covers_blocking_by_confidence` 1126,
`test_orchestrator_does_not_copy_client_limits` 1132, `test_forced_fallback_rule_stated_once_in_decision_table` 1217,
`test_worked_example_two_owns_the_low_second_opinion` 1243, `test_ladder_call_count_and_prose_minors` 1252 - read each
before editing; they pin text that D-14/D-15 removes). E2E: `tests.test_ai_kit_gsd_spec_discuss_e2e`,
`tests.test_jev_skill_install_e2e` must be re-read for `decide.py` use.

**Callers that must change**
- `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` -> delete. `SKILL.md` lines 28-29 (locates `decide.py`), 46, 68-69
  (detect, consent grant/revoke), 183-184 (ladder), 197, 267, 275; `references/decision-table.md` 18, 29; also
  `analyzer-brief.md`, `log-formats.md`, `worked-examples.md` mention jev/Laya/backends (grep hit) -> reduce to the single
  black-box instruction (D-14, D-15; consent ask moves to jev SKILL.md flow).
- `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py:30` `DECIDE_CLI`, `:466-490` `jev_status` ("decide.py missing"
  reason string, runs `... detect`), `goal_prompt.py:474`; `gp_sections.py:349,395` text; `SKILL.md:190` table row;
  `README.md`; goldens `tests/fixtures/goal_prompt/golden/opengsd-goal-pointer.md` (56,137) and `opengsd-recommended.md`
  (50) must be regenerated; tests: `test_ai_kit_spec_goal_prompt_{host:708-752,golden:51,cli:29,render:286,variants:211}`.
- `tools/hooks/precompact_core.py:77-84 find_client` (checkout-relative `skills/jev-fast-decision/scripts/jev_review.py`
  plus `CLIENT_ENV` override) and `tools/hooks/claude_decision_probe.py:59` (calls `core.find_client`). The hooks call
  `jev_review.py` directly (`--probe`, classification calls), not decide.py: they only need the installed-skill lookup in
  place of the checkout path (the hook may be installed where `skills/` is not beside it). Fixtures
  `tests/fixtures/precompact/stub_client.py`, tests `test_precompact_core.py`, `test_claude_precompact.py`,
  `test_decision_probe.py`.
- Also name jev/Laya/TypeSafe/Zen outside `skills/jev-fast-decision/` (grep hits, check each for R10 text-test scope):
  `README.md`, `skills/ai-kit-gsd-curated-config/**` (`recommend.py`, `skills.py`, `skill_affinity.json`, `SKILL.md`,
  `evals/01-claude-rigorous-cross-ai.md`), `skills/ai-kit-session-wake/.../state.py`, `skills/ai-kit-spec-review/**`
  (`config_io.py`, `references/cross-ai.mjs`, `cross-ai-errors.json`), `tools/setup.py:48,1762`, `tests/test_arch.py`,
  `tests/gsd_curated_eval.py`. SPEC R10 text test covers "every caller's SKILL.md, references and generated prompt text"
  (the five callers) - define the file set explicitly in the test; do not scan the whole tree.
- `jev-fast-decision/SKILL.md` (62 lines) **does not yet document the lookup order** that D-13/R9 pin; add it (and the
  `ladder`/`detect` commands, the consent flow of D-15, and the "older skill without the entry point" update message).
  Keep it small (progressive disclosure: put the lookup table and consent steps in `reference.md`).

## Structural and text tests (task 5)

- `tests/test_arch.py` (AST only, no import/exec): `TestArchitecture` (1355) asserts live-tree rules; `TestArchNonVacuity`
  (1818) proves each rule flags a synthetic violation; rule helpers are module-level `check_*` functions taking
  `(relpath, tree)`; examples to copy: `check_no_planning_reader` + `test_planning_reader_*` (948 / 2175), `_WAKE_SKILL`/
  isolation rules (1103-1110, 2308), `check_no_shell_true`. Add: `check_no_cross_skill_jev_path` (forms: `import`/`from`
  of another skill, `sys.path` insert to a sibling skill, a string constant naming `jev-fast-decision/scripts` or
  `jev_review.py` outside jev's folder and outside the lookup helper, a `decide.py` name anywhere), `check_no_reset_hard`
  over fold script text + SKILL.md + policy (SPEC R4), and a **lookup drift test** comparing every copy's ordered
  roots (parse each copy's literals via `ast`, including the JS copy by regex) to the order in jev's `reference.md`/SKILL.md.
  Each gets a `TestArchNonVacuity` case per violation form (SPEC R9: "a non-vacuity case for each form").
- Black-box text test (R10): new module, reads only `skills/<caller>/SKILL.md`, `references/*.md`, goal-prompt generated
  text (call the `gp_sections` builders, no host CLI), case-insensitive regex for `laya|typesafe|opencode zen|zen\b|consent|probe status`
  vocabulary; exempt only `skills/jev-fast-decision/`; non-vacuity: a synthetic text with each name fails.
  Reading `skills/` and `tools/` is allowed; reading `.planning/` is **forbidden** in tests (`test_no_test_reads_planning`,
  `PLANNING_READER_EXCEPTIONS` is empty and pinned) so the doc-contract test reads the policy under `skills/`, never `.planning/`.
- Runner groups (`tools/run_unittest_parallel.py`): any new `tests/test_*.py` joins `unit` automatically; fold-engine and
  doc-contract tests are unit (real `git` on a temp repo is fine in unit, ~0.05-0.3 s). `tests.test_arch` is the only
  `arch` module (add rules inside it, not a new module). A node-run of the capability command module belongs in a new
  e2e module added to `E2E_MODULES` **and** `E2E_RECORDED_SECS` (an unrecorded e2e module is treated as over budget and
  deferred to push; `tests/test_gate_scope.py` `recorded_secs_errors` enforces consistency). Tests must not call a host
  CLI (`HOST_CLI_NAMES`), nor use real home vars (`HOME_OVERRIDE_VARS`); gsd-core node runs against the checkout-local
  `.claude/gsd-core` are accepted in e2e only (the e2e tier already does this).
- Because `.claude/gsd-core` needs `.claude/scripts/` beside it, the e2e fixture copies both (spike finding).

## Superpowers adapter (task 6)

`skills/ai-kit-spec-execute-superpowers/SKILL.md` (289 lines) sections: NEVER (18), Step 0 resolve shim (50), Step 1 load
plan under subagent-driven-development unmodified (100), Task paths (107), Arm session wake (130), Step 2 resolve injection
(137), Step 3 dispatch implementer (209), Step 4 task review/fix/final review unaffected (278), Close the session wake
(285). Place the fold as **Step 5, after Step 4's final review passes and before "Close the session wake" / superpowers'
finishing step**, and add to Step 1 a pre-execution check: if the plan lacks a final "Fold commits" task, append that task
to the in-memory task list (do not rewrite the plan file) - the step text is "run `python3 <fold.py found by lookup> ...
adapt-superpowers`". The step hands over per the D-03 refinement (no merge/push/PR through superpowers' finishing step).
The adapter text must not name backends (R10 does not cover it, but D-16 judge does for size). The SKILL.md is already
289 lines: keep the addition to a few lines and push detail into a `references/` file (progressive disclosure) to avoid
a D5 regression. Test: `tests/test_ai_kit_spec_superpowers.py`.

## JDG-04 judge bar (task 7)

Procedure (skill-judge at `~/.claude/skills/skill-judge`, read-only reference): rubric v4, 125 points, 8 dimensions D1-D8,
grade by percent (A >= 90, B 80-89.9, C 70-79.9, D 60-69.9, F < 60); output a verdict JSON line. Per the owner memory
`feedback_skill_judge_in_code_review`: run in code review with referee-one and referee-two (router-env via pi), referee-three
only as fallback, native opus xhigh only if referees are down; prompts embed `references/rubric.md` (build.py only embeds
SKILL.md). Prior art: `.planning/research/2026-11-02-next-milestone/p27-judge-scripts/build_report.py`,
`tests/fixtures/archived/26/skill-judge/check_verdicts.py.txt`. Judge noise is about +-8 points on the old scale.
**Baselines** (source: `.planning/research/2026-11-02-next-milestone/15-skills-vs-new-judge.md` rows 108-128):
- `ai-kit-spec-goal-prompt`: new rubric referee-one 118/125 (94.4% A), referee-three 109/125 (87.2% B), UNRESOLVED vs its own
  base 90.4 (2026-11-02, phase 27 round 7). Has new-shape evals (`evals/evals.json` 10 + `trigger-queries.json` 20 + `files/`)
  and `tests/test_ai_kit_spec_goal_prompt_evals.py` as the checker to copy.
- `jev-fast-decision`: old rubric only (Opus 107/120, opencode 101/120, 2026-10-23); `evals/cases.jsonl` are backend
  calibration, not skill evals -> needs new-shape evals (`evals.json`, `trigger-queries.json`) first.
- `ai-kit-gsd-spec-discuss`: old only (106/114/109 per judge, round 4, 2026-10-24); no evals.
- `ai-kit-spec-execute-superpowers`: old 86/120 (71.7%) FAIL, owner accepted and deferred (SJ-2); noise-limited; no evals.
  D-16 now requires it to meet the bar this phase: first obtain a fresh new-rubric baseline *before* editing, then edit.
- `ai-kit-commit-fold`: new, no baseline; build evals with the skill.
Old /120 scores are not comparable to the new percent bands; "no regression" for the four existing skills means: judge the
unchanged SKILL.md with the new rubric first (baseline), then the changed one, and compare within judge variation.

## Docs to update (task 8)

`AGENTS.md` Workflow folding sentence (line ~293) -> pointer to `skills/ai-kit-commit-fold/references/folding-policy.md`;
`README.md` skill table (add `ai-kit-commit-fold` row; update rows 49 and 52 text for spec-discuss/jev; README line ~536
mirrors `jev-fast-decision` for pi); `skills/ai-kit-spec-goal-prompt/README.md`; `tools/setup.py:48` `PI_SKILLS` (decide whether
the fold skill mirrors to pi - pi is a primary host); `tools/install.sh` (verify it scans `skills/` generically; grep found no
per-skill list, so likely no change - confirm with `bash tests/test_install.sh`); `pyproject.toml` tool roots (111, 137);
REQUIREMENTS/ROADMAP already amended for FLOW-01/RULE-17 per CONTEXT (verify, per AGENTS.md Workflow rule).

## Common Pitfalls

1. **`merge-base --is-ancestor` exit 1 is a normal answer**, not an error (prototype crashed on it). Handle 0/1/other.
2. **`commit-tree -F -` needs bytes** (UTF-8) from Python subprocess; `str` input raises.
3. **Hook receives only `--phase`**; do not design around wave/plan ids being passed.
4. **Dirty tree from capability install files** (`.gsd/`, `.gsd-capabilities.json`) trips the guard in the target project.
5. **Project-local gsd-core copy without `.claude/scripts/`** crashes every command (fixtures).
6. **Shared path across features** cannot be split by path partition; merge candidates up front (D-09).
7. **Literal R9 structural rule vs existing refs**: `gp_host.py:28-29` (`WAKE_CLI`, `SPEC_CLI`) and
   `skills/ai-kit-session-wake/ai-kit-session-wake.py:19` (`sys.path` to `ai-kit-spec-review`) name sibling skill paths
   today; `gp_common.py:6` mentions `phase_range.py` in a docstring. See Open Question 2.
8. **Goldens**: goal-prompt golden files contain the `decide.py` text; regenerate and keep `test_..._golden` green.
9. **E2E table**: a new e2e module without `E2E_RECORDED_SECS` entry silently defers to push.
10. **Old `jev_review.py` copies** installed elsewhere lack `ladder`: callers must treat "unknown subcommand / non-JSON
    output" as no backend and print the update command (SPEC R8 adjacency).

## Code Examples

Plumbing core: see Fold engine mechanics and `tmp/plan-29/fold_proto.py` (gitignored throwaway; port into the skill with
tests). Capability command module (spike-proven shape):
```js
'use strict';
const { execFileSync } = require('node:child_process');
function route({ args, cwd }) {            // args = ['fold-cmd','run','--phase','7']
  const out = execFileSync('python3', [/* script found by lookup */, 'gsd-wave', ...args.slice(2)], { cwd, encoding: 'utf8' });
  process.stdout.write(out);
}
module.exports = { route };
```

## State of the Art

| Old | Current | Impact |
|-----|---------|--------|
| CONTEXT says gsd-core 1.18.0 | checkout is **1.20.0** | facts re-verified on 1.20.0; no per-plan lifecycle point still; `execute:wave:post` unchanged |
| step hooks assumed `ref.agent`/`ref.skill` usable | third-party agents/skills not surfaced by capability install | only `ref.command` verified |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A `contribution` at `execute:wave:post` would be paraphrasable prose | Spike | low, not used |
| A2 | Fresh clone needs `--yes` re-consent (consent in `$GSD_HOME`) | Spike risk 2 | install step doc wording |
| A3 | `Ai-Kit-Fold:` trailer idempotency design | Fold mechanics | alternative marker works equally |
| A4 | PLAN.md task `files` tag and superpowers `### Task N` / `Files:` conventions | Adapters | parser must be pinned against a real file first (Wave 0) |
| A5 | `tools/install.sh` has no per-skill list | Docs | one extra edit |

## Open Questions

1. **Who runs `capability install --yes` for the fold bundle in a target project?** ai-kit's scope (memory: GSD install
   belongs to tools-installer; GSD config helpers belong to ai-kit). Candidates: a documented command in the fold skill
   SKILL.md, or `ai-kit-gsd-curated-config` apply step (Phase 44 CUR). Not decidable by research; the planner needs an
   owner call. Suggested default: document the command in the fold skill + provide the bundle; no automatic installer yet.
2. **R9 structural rule scope.** Literal SPEC wording ("a path inside another skill's folder") also flags `gp_host.py`
   `WAKE_CLI`/`SPEC_CLI` and session-wake's `sys.path` insert (not jev). jev ladder call: `a` (scope to jev/`decide.py`
   paths, no allowlist), probability 0.87, confidence 0.44, backend laya, advisory; checked against grep (those references
   exist and are outside this phase's five callers). Needs owner confirmation; the alternative is a frozen non-growing
   allowlist of those references with a non-vacuity case.
3. **Hook completeness backstop.** Dispatch is advisory/best-effort. Should phase verification fail when plan commits
   remain unfolded? (Recommend yes as a verification step, not a gate on execution.)
4. **Tested tip** for the GSD hook is "branch tip after post-merge tests" - confirm there is no later commit by
   `execute-phase` between step 5.75 and the next wave (read steps 5.8+ when writing the adapter).
5. Authorship of folded commits (first-commit author vs fixed) - minor, planner choice.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git | fold engine, fixtures | yes | system git (plumbing used worked) | - |
| python3 | scripts, tests | yes | 3.14.7 (linuxbrew `python3`); target py312 | - |
| node | capability command, e2e | yes | v24.21.0 | - |
| project-local gsd-core 1.20.0 | spike, e2e | yes | 1.20.0 (+ `.claude/scripts/`) | - |
| Laya (jev local) | optional jev calls | yes (answered a choice) | - | rule-based grouping |
| uv / pre-commit | `make validate` | not checked this session | - | - |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib `unittest`, run through `tools/run_unittest_parallel.py` (one subprocess per module) |
| Config file | `tools/run_unittest_parallel.py` group sets; `tests/test_gate_scope.py` enforces membership |
| Quick run command | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold tests.test_jev_fast_decision` |
| Full suite command | `make test` (~120 s per Phase 28) |

### Phase Requirements -> Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| R1 policy | each rule phrase present; fails if removed; fold refuses with no policy | unit (doc-contract) | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold_policy` | Wave 0 |
| R2 GSD fold | two-feature GSD fixture -> 2 commits, every path once, UTF-8 | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold` | Wave 0 |
| R3 superpowers fold | same checks on superpowers fixture; single commit = no rewrite | unit | same | Wave 0 |
| R4 tree proof/tag | one-byte-different refused, no tag, tree equal on success, `reset --hard` structural | unit + arch | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold tests.test_arch` | Wave 0 / extend |
| R5 guards | commit on main refused; pushed-unmerged folds; foreign merge refused; own merge-back folded; dirty tree | unit | `tests.test_ai_kit_commit_fold` | Wave 0 |
| R6 report | <=5 lines for success and every refusal; no colour codes; inline note | unit | `tests.test_ai_kit_commit_fold` | Wave 0 |
| R7 jev grouping | jev absent / no backend / fake answer same result; mixed grouping overridden; missing/duplicate commit rejected | unit (fake client, no host CLI) | `tests.test_ai_kit_commit_fold` | Wave 0 |
| R8 ladder home | all former decide.py behaviours at jev entry; `ladder`/`detect` in scratch HOME; empty items exit 0 | unit + subprocess | `python3 tools/run_unittest_parallel.py tests.test_jev_fast_decision` | exists (extend, moved tests) |
| R9 callers black box | each of 5 callers finishes with jev absent; lookup drift; structural forms | unit + arch | `tests.test_ai_kit_gsd_spec_discuss tests.test_ai_kit_spec_goal_prompt_host tests.test_precompact_core tests.test_decision_probe tests.test_arch` | exists (update) |
| R10 text | no backend/consent/probe text in caller texts; non-vacuity | unit | `tests.test_ai_kit_caller_text` | Wave 0 |
| GSD hook | render-hooks lists the step; `gsd-tools fold-cmd run` reaches fold script | e2e (node, scratch) | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold_e2e` | Wave 0 |
| JDG-04 | judge verdicts for 5 SKILL.md; evals checker per skill | unit (structure) + manual judge run | `tests.test_ai_kit_commit_fold_evals tests.test_jev_fast_decision` | Wave 0 |

### Sampling Rate
- Per task commit: the module(s) the task touched (staged mapper runs only covering modules).
- Per wave merge: `python3 tools/run_unittest_parallel.py --group unit --group arch`.
- Phase gate: `make test` and `make validate` green.

### Wave 0 Gaps
- [ ] `tests/test_ai_kit_commit_fold.py`, `..._policy.py`, `..._evals.py`, `..._e2e.py` (+ `E2E_MODULES` and `E2E_RECORDED_SECS`)
- [ ] `tests/test_ai_kit_caller_text.py` (R10) and arch rules + non-vacuity cases in `tests/test_arch.py`
- [ ] shared fixture helper for temp git repos (`tests/` helper; a helper covering 2+ modules triggers the full unit group at commit)
- [ ] real PLAN.md and `docs/superpowers/plans/*.md` format check to pin adapter parsers (A4)
- [ ] new-shape evals for jev, spec-discuss, superpowers, commit-fold; judge baselines taken before editing
- Fast-test notes: no sleeps; each fold test < 0.3 s; fixtures built once per class; no `.planning/` reads; no host CLI.

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input validation | yes | moved ladder validation (`item_error`, closed vocabularies); checkpoint JSON schema check; `ref.command` regex |
| V12 Files/paths | yes | NUL-split git output; refuse paths escaping repo; no absolute paths in source |
| V14 Config | yes | atomic writes only if any config is written |
| V2/V3/V4/V6 | no | no auth/session/crypto |

| Threat | STRIDE | Mitigation |
|--------|--------|-----------|
| Command injection via capability manifest/args | Tampering | `execFileSync`/argv lists, never a shell; keep `ref.command` `^[a-z][a-z0-9-]*( [a-z][a-z0-9-]*)*$` |
| Secrets/code to a remote backend | Info disclosure | grouping items carry subjects/paths/summaries only; ladder rejects fences and key shapes; consent flow stays in jev |
| Branch rewrite data loss | Tampering | tree proof, backup tag, `update-ref` expected-old, main/merged guard |
| Untrusted third-party hook consent | Elevation | project scope + explicit `--yes`; command module is `require()`'d in-process |

## Sources

### Primary (HIGH)
- Read this session: `29-SPEC.md`, `29-CONTEXT.md`, `.claude/gsd-core/references/loop-hook-dispatch.md`,
  `workflows/execute-phase.md` (979-1000), `bin/lib/capability-{validator,command-router,loader,writer,source}.cjs`,
  `bin/gsd-tools.cjs` (565-650), `bin/lib/surface.cjs` (230-262), `decide.py`, `jev_review.py` CLI, `jev-fast-decision/SKILL.md`,
  `tools/run_unittest_parallel.py`, `tests/test_arch.py` structure, caller sources.
- Executed: spike scripts (`tmp/plan-29/spike/`), `tmp/plan-29/fold_proto.py`.
### Secondary (MEDIUM)
- `15-skills-vs-new-judge.md` baselines; `~/.claude/skills/skill-judge/README.md` rubric summary; owner memory notes.
### Not read this session (LOW; pin before use)
- `bin/lib/worktree-safety.cjs` exact merge message; `execute-plan.md` docs commit; a real PLAN.md; a real superpowers plan;
  `29.1-SPEC.md` R1 beyond line 84.

jev call log: `c1` (R9 rule scope) -> answer `a`, confidence 0.4399 (p 0.869), checked with grep of the cross-skill
references, kept as a recommendation and escalated as Open Question 2 (low confidence).

## Metadata

**Confidence:** spike HIGH (executed); fold plumbing HIGH (executed); inventory HIGH (read); judge procedure MEDIUM.
**Research date:** 2026-11-04. **Valid until:** gsd-core changes (re-run `tmp/plan-29/spike/setup.sh` + `install.sh`).
