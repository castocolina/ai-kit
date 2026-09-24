---
phase: 14-ci-cd-rules-checker-ai-kit-project-rules-cicd
plan: 03
subsystem: cicd-rules-checker
tags: [gradle, package-json, lockfile-resolution, plugin-table, python, static-analysis]

requires:
  - phase: 14-01
    provides: the applicability gate, the command-key match rule (D-C5), the tool-shaped identity gate (D-C4) as one function, the Makefile reuse surface, and the reuse-invocation table
  - phase: 14-02
    provides: the GitHub Actions reader, the pre-commit-hook reuse surface, and D-C16's four-surface order constant (already naming package-json and gradle)
provides:
  - the package.json script reuse surface (D-C18) with lockfile-driven runner resolution (D-C18b)
  - the Gradle task reuse surface (D-C19) -- declared-task text extraction and a pinned plugin table gated on real plugin-id evidence
  - D-C19b's fourth admission route inside the shared tool-shaped gate, as an explicit off-by-default caller-passed parameter
  - D-C20's wrapper-vs-bare Gradle invocation resolution
  - ROADMAP Phase 14 SC3 in full (all four command surfaces, each with a paired fixture, audited by AST) and SC2's remaining half
affects: [15-rules-orchestrator-ai-kit-project-rules-all]

actuals:
  tokens: 18631
  tasks: 3
  commits: 5
  plan_head_before: f79b424a43a11acc4ff27a60e7db4fb91853a7b0

tech-stack:
  added: []
  patterns:
    - "Reuse-source surface module pattern: a small, root-scoped, fully-degrading reader module (package_scripts.py, gradle_tasks.py) that exposes pure primitives; reuse_sources.py owns the gate calls, key computation, and record assembly for every surface."
    - "Gate-widening via explicit caller-passed parameter, never a membership test inside the gate itself (D-C19b) -- the pattern any future fifth surface with its own private admission table should follow."

key-files:
  created:
    - skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/package_scripts.py
    - skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/gradle_tasks.py
  modified:
    - skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/reuse_sources.py
    - tests/test_ai_kit_project_rules_cicd.py

key-decisions:
  - "D-C18/D-C18b/D-C19/D-C19b/D-C20/D-C21 implemented exactly as the plan specified; no architectural deviation."
  - "package_scripts.py's docstring corrected (Rule 1) to remove a misleading claim that `prepare`-named scripts are excluded -- they are read like any other `scripts` entry, since no <behavior> case required special-casing by name."
  - "22 ruff E501 line-length violations across gradle_tasks.py and the test file, discovered by `make validate`, fixed via `ruff format` plus two manual wraps -- committed as their own small fix commits, kept out of Task 1/2/3's task-scoped commits."

patterns-established:
  - "AST-discovered paired-fixture audit: a test class that walks the suite's own AST, keyed on each surface's canonical config filename (not a hand-maintained test-name list), to make a 'paired fixture per surface' requirement mechanically measurable rather than claimed."

requirements-completed: [REQ-rules-cicd]

coverage:
  - id: D1
    description: "package.json script reuse surface (D-C18): a root scripts entry covers a matching CI line through the same command-key machinery every surface uses; an aggregate (&&/||/;) script has no identity."
    requirement: "REQ-rules-cicd"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestPackageJsonReuseSurface"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestPackageJsonDegradation"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-C18b lockfile-driven package-manager runner resolution: pnpm-lock.yaml > yarn.lock > bun.lockb/bun.lock > npm (default), deterministic first-match precedence."
    requirement: "REQ-rules-cicd"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestPackageScriptsModuleDirect.test_resolve_package_manager_runner_precedence"
        status: pass
    human_judgment: false
  - id: D3
    description: "Gradle task reuse surface (D-C19): a task declared in the root build script (either DSL, five declaration forms) or contributed by a pinned plugin-table row whose plugin id is present in the build script; lifecycle tasks excluded; Route 1's jscpd/jscpdReport name-identity limit pinned as a required negative fixture."
    requirement: "REQ-rules-cicd"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestGradleDeclaredTaskExtraction"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestGradlePluginTableEvidence"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestGradleRoute1NameIdentityLimit"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-C19b: the tool-shaped gate gains a fourth admission route as an explicit off-by-default caller-passed parameter (never a membership test); the three prior routes and surfaces are unaffected, proven by NO-GATE-LEAK-OK's three non-Gradle negatives plus a dedicated mutation."
    requirement: "REQ-rules-cicd"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestGradleNoGateLeak"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestGradlePriorSurfacesUnaffected"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-C20 wrapper-aware Gradle invocation (./gradlew <task> vs gradle <task>)."
    requirement: "REQ-rules-cicd"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestGradlePluginTableEvidence.test_plugin_present_without_wrapper_uses_bare_gradle"
        status: pass
    human_judgment: false
  - id: D6
    description: "ROADMAP SC3 in full: all four command surfaces each covered by at least one paired triggering/non-triggering fixture, discovered mechanically from the suite's own AST rather than a hand-maintained list."
    requirement: "REQ-rules-cicd"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestSC3PairedFixtureAudit.test_every_surface_has_a_triggering_and_a_non_triggering_fixture"
        status: pass
    human_judgment: false
  - id: D7
    description: "Four-surface integration fixture: all four surfaces fire at once, with one tool covered by three surfaces collapsing to a single Makefile finding (D-C16)."
    requirement: "REQ-rules-cicd"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_cicd.py#TestIntegrationAllFourSurfaces"
        status: pass
    human_judgment: false

duration: 95min
completed: 2026-09-14
status: complete
---

# Phase 14 Plan 3: package.json and Gradle Reuse Surfaces Summary

**Completed `ai-kit-project-rules-cicd`'s reuse-source inventory with lockfile-aware `package.json` scripts (D-C18/D-C18b) and a pinned-plugin-table Gradle task surface (D-C19/D-C19b/D-C20), widening the shared tool-shaped gate by exactly one caller-scoped route and closing ROADMAP Phase 14 SC3 in full.**

## Performance

- **Duration:** 95 min
- **Started:** 2026-09-14T00:00:00Z (approx, worktree fast-forwarded to main before execution)
- **Completed:** 2026-09-14
- **Tasks:** 3
- **Files modified:** 4 (2 created, 2 modified) across 5 commits

## Accomplishments

- `package_scripts.py`: root `package.json` script reader with a total degradation contract (`(OSError, UnicodeDecodeError, ValueError)` only, AST-verified narrow) and D-C18b's deterministic lockfile-driven runner precedence (pnpm > yarn > bun > npm default).
- `gradle_tasks.py`: root `build.gradle`/`build.gradle.kts` reader with Route 1 (five declaration-form text extraction: `task <name>`, `task("<name>")`, `tasks.register("<name>")`/`tasks.register<Type>("<name>")`, `tasks.named("<name>")`, Kotlin `val <name> by tasks.registering`/`by tasks.creating`) and Route 2 (an 8-row pinned plugin table gated on real plugin-id text evidence), plus D-C20's wrapper-aware invocation.
- `reuse_sources.py`: `is_tool_shaped_identity` gained D-C19b's fourth admission route as an explicit `from_plugin_table: bool = False` parameter passed only by the Gradle surface's Route 2 loop -- never a membership test the gate performs itself. Gate now has 5 callers (makefile, precommit, package-json, and Gradle's two routes).
- All four command surfaces named in REQ-rules-cicd are now live in one repo at once; ROADMAP Phase 14 SC3 is measured (not claimed) by an AST-discovered paired-fixture audit class.
- Four required non-vacuity mutations applied, observed failing on exactly their expected methods, and reverted -- see "Task 3's four mutations" below.

## Task Commits

Each task was committed atomically:

1. **Task 1: package.json script reuse surface** - `91f3a8f` (feat)
2. **Task 2: Gradle task reuse surface + gate widening** - `3a7e391` (feat)
3. **Task 3: SC3 audit, integration fixture, limits, mutations** - `cdb6d68` (test)

**Deviation fix-up commits** (kept separate from the task commits above so each task's `git show --stat` stays scoped to its own `<files>`):

- `a8deba7` (docs) - corrected `package_scripts.py`'s scripts-only limit wording
- `8a9d1cf` (style) - wrapped `gradle_tasks.py`'s declaration regexes under ruff's line-length limit

## Files Created/Modified

- `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/package_scripts.py` - root `package.json` script reader, D-C18b lockfile-driven runner resolution
- `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/gradle_tasks.py` - root build-script task-declaration reader (Route 1), pinned plugin-task table (Route 2), D-C20 wrapper resolution
- `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/reuse_sources.py` - inventory builder extended with both new surfaces at D-C16's declared positions; `is_tool_shaped_identity` gained D-C19b's fourth route
- `tests/test_ai_kit_project_rules_cicd.py` - paired fixtures for both new surfaces, the SC3 AST audit, the four-surface integration fixture, and the limits-pinning class

## Decisions Made

### The catalog answers re-verified live (Task 2 precondition)

`resolve_tool_category`: `spotless` -> `formatting`, `checkstyle` -> `linting`, `PMD` -> `linting`, `SpotBugs` -> `security` (all resolve through the existing three gate routes); `ktlint`, `detekt`, `dependency-check` -> `None` (these three plugin-table rows depend on D-C19b's new fourth route -- confirmed by the `PLUGIN-TABLE-OK` command's printed per-row catalog answers). No catalog growth since planning; the route's necessity is unchanged.

### The pinned Gradle plugin table, row by row

| Task name | Plugin-id fragment | Tool identity | Route needed |
|---|---|---|---|
| `spotlessCheck` | `com.diffplug.spotless` | `spotless` | existing (Route 1 via catalog) |
| `spotlessApply` | `com.diffplug.spotless` | `spotless` | existing |
| `checkstyleMain` | `checkstyle` | `checkstyle` | existing |
| `pmdMain` | `pmd` | `PMD` | existing |
| `spotbugsMain` | `spotbugs` | `SpotBugs` | existing |
| `detekt` | `io.gitlab.arturbosch.detekt` | `detekt` | D-C19b (new route 4) |
| `ktlintCheck` | `org.jlleitschuh.gradle.ktlint` | `ktlint` | D-C19b (new route 4) |
| `dependencyCheckAnalyze` | `org.owasp.dependencycheck` | `dependency-check` | D-C19b (new route 4) |

This table is the exact content D-C19's Route 2 paragraph in the plan already locked (task names, plugin-id fragments, and tool identities transcribed verbatim from the plan text).

### Gradle documentation source -- disclosed gap, not silently absorbed

The plan requires citing "the Gradle documentation source and date for the declaration forms and plugin-application forms... do not answer this from memory." **Neither the Context7 MCP tool nor the `ctx7` CLI fallback was available in this execution environment** (verified: no `context7`-namespaced tool was offered to this agent, and `command -v ctx7` exited 1). Per the documentation-lookup policy, `npx --yes` auto-install of an unverified package was correctly avoided. The declaration-form syntax (`task <name>`, `task("<name>")`, `tasks.register("<name>")`/`tasks.register<Type>("<name>")`, `tasks.named("<name>")`, Kotlin `val <name> by tasks.registering`/`by tasks.creating`) and the plugin-id table are therefore the plan's own already-researched, cross-AI-reviewed D-C19 content, transcribed verbatim rather than independently re-verified against a live fetch during this execution. This is a disclosed divergence from the `<read_first>` instruction's letter (not its spirit -- the content itself is unchanged from what the plan locked), reported here rather than silently treated as satisfied.

### D-C18b's lockfile precedence as implemented, and the runners fixtures resolved to

`resolve_package_manager_runner`: first of `pnpm-lock.yaml` -> `pnpm`, `yarn.lock` -> `yarn`, `bun.lockb`/`bun.lock` -> `bun`, else `npm`. Fixture results: no lockfile -> `npm run lint`; `pnpm-lock.yaml` present -> `pnpm run lint`; `yarn.lock` present -> `yarn run lint`; both `pnpm-lock.yaml` and `yarn.lock` present -> `pnpm run lint` (pnpm wins, first in precedence).

**Verification-command defect discovered and worked around, not silently absorbed:** the plan's own `PACKAGE-SCRIPTS-OK` `<verify>` command asserts `'npm run lint' not in pnpm[0]['recommendation']`. This assertion is mathematically unsatisfiable for ANY correct implementation: `"pnpm run lint"` literally contains `"npm run lint"` as a substring (`"pnpm"` = `"p"` + `"npm"`), and the recommendation text format (`_build_finding` in `cicd_checker.py`, inherited unchanged from plan 14-01) always quotes the resolved `reuse_command` verbatim. Confirmed via `python3 -c "print('npm run lint' in 'pnpm run lint')"` -> `True`. I ran the command as literally written (it fails on that one assertion, as it must for ANY implementation), then re-verified D-C18b's actual intent with the correct instrument: exact-equality assertions (`pnpm[0]['reuse_command'] == 'pnpm run lint'`, never `== 'npm run lint'`) and a quoted-form containment check (`"'npm run lint'"` -- with quotes -- not present), both of which pass and are also pinned as real `unittest` methods (`TestPackageJsonReuseSurface.test_pnpm_lockfile_recommends_pnpm_runner`, `test_both_pnpm_and_yarn_lockfiles_recommends_pnpm_first`). No code changed because of this; it is a defect in the plan's own literal verification snippet, not in the implementation.

### D-C19b's fourth route as implemented

Signature: `is_tool_shaped_identity(identity: str, source_name: str, derived_from_command_body: bool, from_plugin_table: bool = False) -> bool`. The parameter defaults to `False`; the ONLY call site that ever passes `from_plugin_table=True` is `build_gradle_reuse_records`'s Route 2 loop in `reuse_sources.py`, and only after `gradle_tasks.plugin_table_matches` has already confirmed the plugin-id evidence is present in the build-script text. The gate performs **no membership test of its own** -- confirmed by inspection (the added branch is `if from_plugin_table: return True`, nothing else) and by the gate-scoping mutation below.

`NO-GATE-LEAK-OK` result: `0 0 0 1` -- the three non-Gradle negatives (entry-less `ktlint` pre-commit hook, `detekt` package.json script, `dependency-check` Makefile target) each return zero findings, and the Gradle positive (ktlint plugin applied) returns one. For each negative, the route that WOULD have admitted it if the gate leaked: Route 1 (catalog) refuses all three (`resolve_tool_category` returns `None` for each, re-verified live); Route 2 (out-of-taxonomy marker) refuses all three (none are test-runner or pre-commit-hygiene markers); Route 3 (name-equality) is structurally closed to the hook (entry-less, `derived_from_command_body=False`) and would have been the admitting route for the `detekt`/`dependency-check` fixtures had they been spelled naively (`{"detekt": "detekt"}`, a `dependency-check:` target) -- which is exactly why those two fixtures were deliberately spelled `{"lint": "detekt"}` and `lint:` running `dependency-check`, so Route 3 cannot legitimately admit them either.

Confirmation the three existing routes are unchanged: plan 14-01's `TRACER-OK` and `IDENTITY-GATE-OK`, plan 14-02's `GH-READER-OK` and `PRECOMMIT-SURFACE-OK`, and this plan's own `PACKAGE-SCRIPTS-OK` all re-ran clean after Task 2 landed and again after Task 3.

### Route 1's identity rule as it landed

Positive: `tasks.register("jscpd")` + CI `jscpd .` -> one finding, `reuse_surface: gradle`. Negative: `tasks.register("jscpdReport")` + the same CI line -> zero findings, and no finding anywhere names `jscpdReport`. The limit sentence in `gradle_tasks.py`'s docstring, verbatim:

> "A declared task's (Route 1) identity is its NAME with no command body behind it. `is_tool_shaped_identity`'s Route 3 (name-equality) is therefore CLOSED to a Route-1 identity -- a declared task must be catalog-answerable, an out-of-taxonomy marker, or come through Route 2's plugin table. Concretely: `tasks.register("jscpd")` covers a CI `jscpd .` line (the name IS the tool name, and the shared catalog answers it), while `tasks.register("jscpdReport")` covers NOTHING -- the catalog cannot answer `jscpdReport`, and even if it could, this family's match rule (D-C5) never does substring matching or suffix stripping. This is a genuine, accepted gap: `<tool><Purpose>` task names are ordinary Gradle convention, and the alternative (stripping a suffix to recover the tool name) is the exact mechanism that would make a `ruff format` call match a `ruff` linter target elsewhere in this family."

### Both new modules' limits, quoted verbatim

`package_scripts.py`:
> "ROOT file only. A workspace member's `package.json` is not read."
> "`scripts` only. Any OTHER top-level `package.json` field -- `bin`, `config`, and so on -- is never read as a command to reuse. A `scripts` entry named for an npm lifecycle hook (e.g. `prepare`) is read exactly like any other `scripts` entry -- through the SAME aggregate check and command-key machinery, no special-casing by name -- since it lives inside `scripts`, not outside it."

`gradle_tasks.py`:
> "ROOT build scripts only. A subproject's `build.gradle` and `settings.gradle`'s project list are not read."
> "No Gradle execution of any kind. `gradle tasks` is never run, so a task contributed by a plugin outside the pinned `PLUGIN_TASK_TABLE` is invisible to this reader."
> "The plugin-id evidence check is a plain containment test against the build-script TEXT, not a parse of the `plugins {}` block -- both `plugins { id "com.diffplug.spotless" }` and `apply plugin: "com.diffplug.spotless"` count, and a comment mentioning the plugin id counts too. This is an accepted over-admission: nobody comments out a plugin they never applied, so the recommendation is for a task the repo probably does have."

### Task 3's four mutations, by name

All four were applied to already-committed, clean source files via `Edit`, run against the FULL `test_ai_kit_project_rules_cicd` suite (plus sibling suites where relevant), observed failing on exactly the expected methods, then reverted with `git checkout -- <file>` (each file was clean/committed before its mutation, so this reverts to the exact prior commit state -- confirmed by re-running the full suite green after each revert).

1. **Plugin-evidence mutation (a).** Edit: `gradle_tasks.plugin_table_matches` changed to admit every `PLUGIN_TASK_TABLE` row unconditionally whenever ANY build-script text exists (dropping the per-row `plugin_fragment in build_script_text` containment check, while still requiring `build_script_text.strip()` to be non-empty so the mutation is scoped to "the containment check is gone" rather than "the surface fires with no gradle file at all"). Result: **exactly** `TestGradlePluginTableEvidence.test_plugin_absent_yields_zero_findings_and_never_names_the_task` failed. Nothing else failed -- confirming no other check leans on this same rule.

2. **Gate-scoping mutation (a2), the most important one.** Edit: `is_tool_shaped_identity`'s D-C19b branch changed from `if from_plugin_table: return True` to a plain membership test, `if identity in {t[2] for t in gradle_tasks.PLUGIN_TASK_TABLE}: return True`, ignoring the caller-passed flag entirely. Result: **exactly** the three `TestGradleNoGateLeak` negatives failed (`test_entry_less_ktlint_hook_is_never_a_reuse_source`, `test_detekt_named_package_json_script_is_never_a_reuse_source`, `test_dependency_check_named_makefile_target_is_never_a_reuse_source`), and **every** `TestGradle*` method stayed green (40 passing Gradle-named test methods, confirmed by count). This proves the Gradle surface's own correctness does not actually depend on the caller-passed flag being read correctly -- only the OTHER three surfaces' safety does, which is exactly T-14-26b's threat.

3. **Aggregate-script mutation (b).** Edit: removed the `if len(split_top_level_segments(command)) > 1: continue` guard from `build_package_json_reuse_records`. Result: **exactly** `TestPackageJsonReuseSurface.test_aggregate_script_covers_nothing` failed.

4. **Route-1 suffix-stripping mutation (b2).** Edit: added a "try progressively shorter prefixes until the catalog resolves" fallback to the Route 1 identity computation, LOCAL to `build_gradle_reuse_records`'s declared-task loop only (not touching `keys_match`/`compute_command_key`/D-C5 at the shared level). Result: **exactly two** methods failed -- `TestGradleRoute1NameIdentityLimit.test_jscpd_report_negative_yields_zero_findings` and its cross-reference pin `TestStatedLimitsPackageJsonAndGradle.test_gradle_route1_name_identity_limit_cross_reference` -- and **zero** D-C5 methods from plan 14-01's suite broke (confirmed by running the full sibling-suite batch: 801 tests, 0 failures besides the two Gradle ones). This is the "local" branch of the plan's own conditional ("so should at least one D-C5 method ... IF the stripping is implemented at the key level rather than locally") -- because the mutation was deliberately scoped to the Gradle surface's own loop rather than the shared match rule, no sibling surface's D-C5 test could be affected. This is disclosed rather than treated as automatically satisfying the plan's stronger "and so should ... a D-C5 method" clause: that clause is conditional on a DIFFERENT (key-level) implementation choice, which this mutation deliberately did not make, precisely so a future maintainer reading this SUMMARY understands the two possible "fixes" and which one this repo's own test suite would catch.

### SC3 audit class's own discrimination check

Used the **gradle** surface (fewest non-triggering matches: 8, vs. 34/9/11 for the other three). Filtered the discovered method list to exclude all 8 of gradle's currently-detected non-triggering methods (`test_jscpd_report_negative_yields_zero_findings`, `test_plugin_absent_yields_zero_findings_and_never_names_the_task`, `test_check_task_is_never_a_reuse_source`, `test_build_test_assemble_are_never_reuse_sources`, `test_empty_build_script_leaves_inventory_usable`, `test_unreadable_binary_build_script_does_not_raise`, `test_gradle_task_from_an_unpinned_plugin_is_invisible`, `test_gradle_route1_name_identity_limit_cross_reference`) and re-ran the classification logic standalone: gradle's `non_triggering` count dropped from 8 to 0 while every other surface stayed unaffected (`makefile: 34/34`, `precommit: 9/9`, `package-json: 9/11`), which is exactly the shape that would fail the `assertTrue(non_triggering, ...)` subTest for gradle alone. **Disclosure:** because the audit's discovery mechanism is intentionally generous (any method referencing a surface's config filename plus an empty-list assertion counts, favoring false negatives over false positives), a SINGLE method's deletion does not flip any surface given the suite's redundant coverage today -- the genuine discrimination proof is "remove ALL currently-discovered non-triggering evidence for one surface", not "remove one arbitrarily chosen method", and this is reported explicitly rather than glossed over as the literal "delete one method" phrasing.

### The four-surface integration fixture's complete finding list, as implemented

In D-C13 order (`.gitlab-ci.yml` first, then `.github/workflows/a.yml`, then `.github/workflows/b.yml`; `eslint` deliberately covered by makefile+precommit+package-json, NOT gradle, to isolate the three-surface-collision proof from the fourth surface):

1. `.gitlab-ci.yml` / `gl-job` / `eslint .` -> `reuse_surface: makefile`, `reuse_command: make lint` (three-surface collision resolves to the first surface in `SURFACE_ORDER`, per D-C16)
2. `.gitlab-ci.yml` / `gl-job` / `jscpd .` -> `reuse_surface: gradle`, `reuse_command: ./gradlew jscpd`
3. `.github/workflows/a.yml` / `j` / `mypy .` -> `reuse_surface: makefile`, `reuse_command: make mypy`
4. `.github/workflows/b.yml` / `j` / `black .` -> `reuse_surface: precommit`, `reuse_command: pre-commit run black --all-files`
5. `.github/workflows/b.yml` / `j` / `tsc --noEmit` -> `reuse_surface: package-json`, `reuse_command: pnpm run typecheck` (repo carries a `pnpm-lock.yaml`)

`remediate()` over the same fixture: 5 entries, every `kind == "cicd"`, every `id == "cicd-command-reuse"`, every `auto_apply is True`, `blocked == []`.

### Registration surfaces confirmed to cover new modules by glob

`grep -c "ai_kit_project_rules_cicd/\*\.py" Makefile` -> `1`. The py-compile line already globs the whole package directory (plan 14-01's registration), so `package_scripts.py` and `gradle_tasks.py` needed no gate edit. `make lint` exits 0 including these two new files. No surface names cicd modules individually.

### Confirmation of scope discipline

This plan edited **no file under `skills/_shared/`** (`git log --stat --format= f79b424..HEAD -- skills/_shared` prints nothing), added **no dependency** (stdlib `json`, `os`, `re` only), ran **no external command** (`gradle`, `npm`, `pnpm`, `yarn`, `bun` are never invoked -- confirmed by inspection of both new modules, which only ever `open()`/read text), and changed **none** of the inherited rules -- the applicability gate, the CI readers, the match rule, the reuse-invocation table, the identifier discipline, the finding vocabulary, and the ordering rule are all byte-identical to how plans 14-01/14-02 left them, proven by re-running every one of their own acceptance commands after each of this plan's three tasks.

### Divergences from D-C18 through D-C21

1. **Documentation-source gap (disclosed above).** No live Context7/`ctx7` lookup was possible in this environment; the Gradle declaration-form syntax and plugin-id table were transcribed verbatim from D-C19's own already-locked, cross-AI-reviewed plan text rather than independently re-verified against a fresh fetch.
2. **`package_scripts.py`'s docstring correction.** The original wording ("lifecycle hooks such as `prepare` are not treated as commands to reuse") was inaccurate given the actual, spec-compliant implementation (a `prepare`-named script IS read like any other `scripts` entry). Corrected in a standalone `docs` commit (`a8deba7`) rather than silently left wrong.
3. **22 ruff E501 violations, fixed via `ruff format` + 2 manual wraps.** `make validate` surfaced these across `gradle_tasks.py` and the test file after Task 3's additions; fixed in standalone `style` commits (`8a9d1cf` for the source file, folded into Task 3's own commit for the test file since `ruff format` ran before Task 3's commit) rather than left broken.
4. **This plan's own `PACKAGE-SCRIPTS-OK` `<verify>` command has an unsatisfiable assertion** (see "D-C18b's lockfile precedence" above) -- worked around with an equivalent, correct instrument (exact-equality + quoted-form containment) rather than silently skipped.

None of these divergences change D-C18/D-C18b/D-C19/D-C19b/D-C20/D-C21's substance; all are documentation, formatting, or verification-tooling corrections.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `package_scripts.py`'s scripts-only docstring wording was inaccurate**
- **Found during:** Task 3 (writing the limits-pinning tests)
- **Issue:** Docstring implied a `prepare`-named `scripts` entry is excluded; no such exclusion is implemented or required.
- **Fix:** Reworded to state precisely what IS true -- fields OUTSIDE `scripts` are never read; entries inside `scripts` (any name) are read uniformly.
- **Files modified:** `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/package_scripts.py`
- **Verification:** Full suite green; no behavior change, docstring-only.
- **Committed in:** `a8deba7`

**2. [Rule 1 - Bug] 22 ruff E501 line-length violations blocking `make validate`**
- **Found during:** Task 3 (running `make validate` as an acceptance criterion)
- **Issue:** `gradle_tasks.py`'s Kotlin declaration-form regex and 21 lines in the test file's fixture literals exceeded ruff's 100-column limit.
- **Fix:** `ruff format` on both files (fixed 19 of 22), plus 2 manual wraps for lines `ruff format` couldn't reflow (a regex literal split across two adjacent string literals; a dict-literal fixture split across lines).
- **Files modified:** `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/gradle_tasks.py`, `tests/test_ai_kit_project_rules_cicd.py`
- **Verification:** `uv run ruff check` and `uv run ruff format --check` both exit 0 on both files; full suite still green (207 tests).
- **Committed in:** `8a9d1cf` (source file, standalone); folded into `cdb6d68` (test file, since it landed inside Task 3's own working tree before that commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 -- documentation accuracy and lint compliance)
**Impact on plan:** No behavior change to D-C18/D-C18b/D-C19/D-C19b/D-C20/D-C21. No scope creep.

## Issues Encountered

- **The `PACKAGE-SCRIPTS-OK` `<verify>` command in this plan's own text contains an assertion (`'npm run lint' not in pnpm[0]['recommendation']`) that is mathematically unsatisfiable for any correct implementation**, because `"pnpm run lint"` always contains `"npm run lint"` as a literal substring. Resolved by running the command as written (documented as failing on that one line, as it must), then independently re-verifying D-C18b's actual intent with a correct instrument (exact-equality assertions, already pinned as real `unittest` methods). No source code changed because of this -- it is a defect in the plan's verification snippet, not the implementation. Fully detailed above under "D-C18b's lockfile precedence as implemented."
- **`make test`'s full four-tier run has one pre-existing, unrelated failure**: `tests.test_markdown_to_pdf.TestRenderRealMmdc.test_real_render_produces_image`, caused by a missing/broken pnpm-global `@mermaid-js/mermaid-cli` module in this execution environment. Entirely outside this plan's scope (`ai-kit-project-rules-cicd` touches nothing related to markdown-to-pdf or mermaid rendering) -- reported as an environment gap per the plan's own instruction for the `uv`-unavailable case, not treated as a passed tier and not auto-fixed (out of scope per the SCOPE BOUNDARY rule).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All four of REQ-rules-cicd's command surfaces (Makefile, pre-commit, `package.json`, Gradle) are live, reuse the same gate/match-rule/inventory machinery, and are proven non-vacuous by 4 mutations across all three checker-side plans (2 from 14-01, 2 from 14-02, 4 from this plan -- 8 total).
- `ai-kit-project-rules-cicd` is fully feature-complete for reuse-source recognition; only `SKILL.md`, the README row, and the `/skill-judge` gate remain, deferred to plan 14-04 as scoped.
- No open blockers. The skill correctly remains uninstallable (`test ! -e skills/ai-kit-project-rules-cicd/SKILL.md` succeeds) until plan 14-04 adds it.

---
*Phase: 14-ci-cd-rules-checker-ai-kit-project-rules-cicd*
*Completed: 2026-09-14*

## Self-Check: PASSED

All created/modified files confirmed present on disk; all 5 commit hashes (`91f3a8f`, `3a7e391`, `a8deba7`, `8a9d1cf`, `cdb6d68`) confirmed present in `git log --oneline --all`.
