# Phase 27: One-shot goal and loop prompt skill - Context

**Gathered:** 2026-10-14 (assumptions mode, `--analyze --all --batch`, jev screening, best over easy)
**Status:** Ready for planning (after Phase 26 executes; D-06)

<domain>
## Phase Boundary

ai-kit ships `skills/ai-kit-spec-goal-prompt/`. The skill turns a set of GSD phases or
superpowers plans into one committable `.md` file. The file holds one paste-ready block per
ranked strategy, plus the rails, both quota directives, and an e2e-centred definition of done.

The WHAT is locked in `27-SPEC.md` (R1–R8, amended 2026-10-14 by this file); this file locks the
HOW. The skill never runs the prompt it generates.
</domain>

<decisions>
## Implementation Decisions

### Skill shape
- **D-01: The skill is named `ai-kit-spec-goal-prompt`.** The `spec-` family covers both GSD
  and superpowers (`detect_framework.py`). The description opens with its trigger words (goal,
  `/goal`, loop, one-shot, autonomous run prompt) because the wizard cuts descriptions at 200
  characters (`tools/setup.py:516`). Laya goal_prompt 0.55 (fb), TypeSafe spec_goal_prompt
  0.84.
- **D-02: The layout follows Phase 24.**
  - `SKILL.md`: about 300 lines at most, with a NEVER list and MANDATORY read-before-step
    triggers.
  - `references/`: loaded on demand.
  - `scripts/`: stdlib only.
  - `assets/`: holds the prompt-and-rails template. The script renders it and SKILL.md marks it
    "Do NOT load".

  Analyzer: Confident.
- **D-03: The skill is self-contained at run time.**
  - It reuses other skills only through their CLIs, never through `_shared` imports, which
    break copy installs (07 D-02, 24 D-09):
    - `ai-kit-spec-review detect-current-runtime` / `detect-runtimes`;
    - `ai-kit-session-wake matrix --json`;
    - `ai-kit-gsd-spec-discuss decide.py`.
  - Small helpers are copied, each with a parity test: `phase_key`, the Makefile target regex
    and package-script reading.
  - Laya cli_boundary_and_copies 0.47 (fb), TypeSafe 0.97.

### Questions and detection (R1)
- **D-04: The agent asks; the script never prompts.** SKILL.md asks the four questions in one
  batch, using the host's question tool or plain text. The scripts are non-interactive JSON CLIs
  (Phase 24 precedent). Analyzer: Confident.
- **D-05: `scripts/goal_prompt.py` has two subcommands, `detect` and `render`.**
  - `detect` reads the repo plus JSON the agent captured from `gsd_run` (`roadmap analyze`,
    `runtime-identity`), in the style of `phase_range.py`'s `--roadmap <file>`. The agent
    passes the tools it can see with `--tools CronCreate,ScheduleWakeup,…`. A deferred tool the
    agent cannot see is "unverified (not seen)", never "absent".
  - `render --answers <json>` writes the file and prints the path, each condition's length and
    the strategies. It never prints absolute paths from probes: `decide.py detect` and
    `--print-argv` output stay out of the file.
  - Laya agent_reports 0.36 (fb), TypeSafe agent_reports 0.99.
- **D-06: Phase 26's survival matrix is read through `ai-kit-session-wake matrix --json`.**
  - When the sibling skill is missing, every primitive is unverified and the file says so.
  - The contract (fields and kinds) is recorded in 26-CONTEXT D-02 (refined).
  - **Build order:** Phase 26 executes before Phase 27 is planned, so the ROADMAP's "Depends on
    Phases 25 and 26" stands.
  - Laya owner_cli_json 0.46 (fb), TypeSafe 0.82.
- **D-07: Each primitive carries two labels**: availability here (version or feature probe)
  and usage source (official docs, live, third-party). Examples:
  - Claude Code `/goal`: available (2.1.299 ≥ 2.1.139); usage from official docs.
  - codex: `goals stable true` from `codex features list`; usage unverified (third-party).
  - opencode, pi and cursor-agent: no primitive in `--help`.
  - A non-current target host: unverified everywhere.

  Laya one_label 0.57 (fb), TypeSafe two_labels 0.96.
- **D-24: Phase state is built from three sources, with OpenGSD detected exactly.**
  - The sources are `roadmap analyze` (order, `disk_status`, `has_context`, `plan_count`), a
    `*-SPEC.md` glob (no `has_spec` field exists), and `init phase-op` for `has_reviews` and
    `has_verification`.
  - Order uses the copied `phase_key` (16 < 16.1 < 17).
  - OpenGSD means exactly `packageName == "@opengsd/gsd-core"` (26 D-18/D-19). A
    `.planning/` without proven identity is reported as GSD, identity unverified.
  - Analyzer: Confident.

### Strategy matrix (R2)
- **D-10: The matrix is a Python tuple of row dicts with plain-value predicates** (`RULES`
  precedent): scope kind, required primitive kind, must-outlive, provable.
  - It returns one to three strategies ranked by fit; ties keep matrix order and exactly one is
    recommended.
  - There is one test per row. No markdown copy exists; `detect`/`render` print the matched
    rows with their reasons.
  - Laya python_constant 0.68 (fb), TypeSafe 0.91.
- **D-11: "Must outlive" and "provable" are derived, not asked**, then shown in the file and
  open to override in the work-set answer.
  - Outlive is true for more than one phase or plan, or for unattended work.
  - Provable is true when e2e commands are detected and no mockup is involved; a mockup means
    human review.
  - Laya always_true 0.59 (fb), TypeSafe derive_and_show 0.95.
- **D-12: The `/gsd-autonomous` line carries flags only (`--from/--to/--only/--converge`), and a
  test pins this.** The workflow greps all of `$ARGUMENTS` for flags (`autonomous.md:21-62`).
  The prior-art `ONESHOT-ENTRY-PROMPT.md` has exactly this defect. A `/goal` wrapper guards on
  `gsd-tools query verification.status <phase dir> --pick status` printing `passed` for every
  phase in scope. Analyzer: Confident.
- **D-13: The file has one paste-ready block per ranked strategy, with the recommended one first
  and marked.** Each `/goal` block is checked against the 4,000-code-point cap.
  - **Own reasoning** (Laya block_per_strategy 0.60 (fb), TypeSafe block_per_strategy 0.57
    (fb)): a user whose host lacks an unverified primitive still has a block to paste. Ledger.

### Prompt file (R3)
- **D-14: The template is in `assets/`, rendered by a `string.Template` subclass.** It uses a
  rare delimiter and strict `substitute()`, so a missing key fails generation. A test asserts
  that no delimiter remains in any rendered scenario. The rails contain `$?`,
  `${PIPESTATUS[0]}` and JSON braces. Laya code_sections 0.41 (fb), TypeSafe
  custom_delimiter_strict 0.82.
- **D-15: The file is committable, in a dated `goals/` subfolder.**
  - GSD writes to `.planning/goals/YYYY-MM-DD-<scope-slug>.md`; superpowers writes to
    `docs/superpowers/goals/`, never under `plans/`, which `detect_framework.py` would read as a
    plan.
  - Projects with neither framework are asked, defaulting to `tmp/`, checked with
    `git check-ignore`.
  - A name collision adds `-2`.
  - The file uses the prior art's `▼▼▼ COPY FROM HERE ▼▼▼` / `▲▲▲ COPY TO HERE ▲▲▲` markers.
    The prompt names `§Rails` by repo-relative path and skills by name. The absolute-path check
    runs per input field, plus a whole-text scan for the home directory and secrets (never a
    leading-slash scan, since `/goal` starts with `/`).
  - SPEC R3 amended.
  - **Own reasoning** (Laya dated_goals_subdir 0.43 (fb), TypeSafe ignored_tmp 0.68 (fb)): a run
    that creates a new worktree cannot see ignored files. Ledger.

### Superpowers and OpenGSD (R4, R5)
- **D-08: Dependencies come from an optional `**Depends on:**` line.**
  - A backticked plan filename becomes an edge.
  - Free text is asked about inside the work-set question (still four questions).
  - No line means the plan is independent.
  - Ties keep filename (date) order.
  - writing-plans 6.4.1 has no dependency field; 3 of uz's 38 plans use the line.

  SPEC R4 amended. Laya depends_on_line_plus_ask 0.55 (fb), TypeSafe 0.99.
- **D-09: Execution per plan is provisional, pending research.** GSD's workflow says Claude Code
  subagents cannot spawn subagents (`plan-review-convergence.md:171`, not live-verified).
  - Where nesting is unavailable, the orchestrator dispatches each plan's tasks itself, one plan
    at a time. This keeps `ai-kit-spec-execute-superpowers`' per-task cross-AI injection
    reachable.
  - Where nesting works, a fresh subagent runs each plan.
  - Research item 3 decides.
  - TypeSafe orchestrator_runs_task_dispatch 0.82, Laya inline_in_plan_subagent 0.44 (fb).
    **Ledger for uz:** the no-nesting branch changes the SPEC's literal "one subagent per plan".
  - **Refined 2026-10-14 (uz):** the orchestrator is the user-facing session (the one that got
    the first prompt), and it can launch subagents, so no nesting is needed. The prompt tells
    the orchestrator to dispatch plan work to subagents and to decide by its own judgment
    whether to reuse a subagent or start a fresh one. Research item 3 no longer decides D-09.
- **D-16: The readiness check proves three things without calling any model.**
  - The runner: `workflow.cross_ai_execution` is true, `cross_ai_command` is set, and its
    executable and script exist.
  - An external CLI: for ai-kit's runner, `--print-argv` exits 0 and lists at least one CLI
    (127 means none). This is labelled "installed, not quota- or auth-verified"; other runners
    are labelled "usability unverified".
  - The reviewers: `workflow.plan_review_convergence` is true and the `review.default_reviewers`
    CLIs are found by `detect-runtimes`.

  It runs at generation and again as the prompt's first step. Phase 18's curated-config
  generator is not built yet, so it is not reused. Laya runner_cli_and_reviewers 0.41 (fb),
  TypeSafe 0.97.
- **D-17: "Declared in each plan" has two parts.** Each PLAN.md carries frontmatter
  `cross_ai: true` (AND-ed with config, `execute-phase.md:415`; GSD's plan template lacks it).
  The phase also has a `REVIEWS.md` from `--converge`. When native execution is chosen, plans
  omit `cross_ai: true` and the prompt says so plainly. SPEC R5 amended. Analyzer: Confident.

### E2E as done (R6)
- **D-18: E2E commands are found from several signals.**
  - Makefile `e2e*` targets, all of them.
  - `package.json` scripts `e2e`, `e2e:*` and `*:e2e`, or scripts that run playwright or
    cypress, using the runner given by the lockfile.
  - `playwright.config.*` and `cypress.config.*`.
  - PTY drivers (test files importing pty, pexpect, ptyprocess or node-pty), mapped to the
    target whose recipe runs them, otherwise listed as inferred.

  Textual-pilot tests are integration, not e2e. Done checks run lint and unit first, then e2e.
  No e2e detection exists in ai-kit today. Laya multi_signal 0.81.
- **D-19: "Zero tests ran" is checked against a labelled table of count lines and zero-test
  markers per runner.**
  - Verified here: unittest exits 5 with `NO TESTS RAN`, and the shell harness prints
    `0 passed`.
  - Other runners stay unverified until researched.
  - The prompt makes every e2e command print its count. Exit 0 with a zero count is not green.
  - Laya generic_wording 0.67 (fb), TypeSafe marker_table_plus_count 0.96.
- **D-20: Cleanup is shown in the transcript, not just promised.** Every long-lived e2e process
  starts in its own process group and its group ID goes into a scratch file. After the run the
  agent kills those groups and prints a process listing that shows none remain. Laya
  plain_instruction 0.52 (fb), TypeSafe groups_and_printed_proof 0.95.

### jev (R7)
- **D-21: The jev step is included only when `decide.py detect` shows a usable backend.** That
  means consent is already on file, or Laya runs on loopback.
  - It runs through `decide.py ladder` as one `choice` item (objectives all, mostly, partly or
    not met), with the objectives and one result line each as context.
  - The answer appears under "Advisory (not a gate)".
  - Otherwise the step is omitted, with the reason stated.
  - Mockups go to e2e screenshots plus a human-review list, never to jev.
  - Tests assert that every jev mention says "advisory" and that jev appears in no done or
    stop-if section.
  - Laya consented_guarded_route 0.57 (fb), TypeSafe 1.00.

### Tests and gates (R8)
- **D-22: Tests:**
  - property checks over every rendered fixture scenario: the cap at 4,000 and 4,001, all
    sections present, no `--no-verify`, no absolute or home path, the sentinel key absent, jev
    advisory only, the `/gsd-autonomous` line flags-only;
  - one committed golden file for the recommended OpenGSD case;
  - a dogfood `detect` on this repo, which must find `e2e-test` and `e2e-docker`;
  - an e2e-tier subprocess test of the real CLI on a temp git repo, with fake `node`/gsd-tools
    on PATH;
  - a parity test showing the quota sections satisfy Phase 26's R18 and R19 signals through
    `check_rules`;
  - seams bundled in a NamedTuple, to stay within `max-args=5`.

  Laya properties_plus_one_golden 0.36 (fb), TypeSafe 0.76.
- **D-23: Gate wiring uses explicit entries, as in Phase 24.**
  - Lint and type checks: ruff, pylint, py-compile, pyright, vulture.
  - Test runs: the unittest hook, `make test-unit`, `make e2e-test`, `make lint`.
  - Docs: a README row.
  - Skill-judge evidence is committed as `27-SKILL-JUDGE.md`.

  Analyzer: Confident.

### Added 2026-10-14 (uz feedback on the hand-written v1.3 prompt)
- **D-25: The generated file stays short.** uz found the first hand-written v1.3 prompt too
  long. Budget: the paste block at most about 1,500 characters; the rails at most about 60
  lines, one line per rule; anything AGENTS.md or a phase's SPEC/CONTEXT already says is
  referenced, never restated. A test pins both budgets. The hand-written reference is
  `.planning/goals/2026-10-14-v1.3-phases-16-27.md` (second version).
- **D-26: The generated rails end with a cleanup step:** stray files committed, ignored or
  removed; finished backlog items cleared; the branch merged into the main checkout (never
  pushed); every intermediate worktree removed after archiving unmerged work as a tag.

### Claude's Discretion
- The delimiter character, the exact question wording, the slug rules, and the golden case's
  inputs.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/27-one-shot-goal-and-loop-prompt-skill/27-SPEC.md`: the locked WHAT.
- `.planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-CONTEXT.md`: D-02 (the
  `matrix --json` contract), D-18 and D-19 (identity), D-22 (the R18/R19 signals).
- `.planning/phases/25-quota-aware-cross-ai-subprocess-supervision/25-CONTEXT.md`: D-23 (the
  policy reference the prompt quotes).
- `.planning/phases/24-spec-and-discuss-chain-skill/24-CONTEXT.md`: the skill patterns,
  D-07/D-10/D-11 (`decide.py`).
- `.planning/ONESHOT-ENTRY-PROMPT.md`, `.planning/ONESHOT-RULES.md` (deleted 2026-10-14 as stale v1.2 artifacts; read them from git history) and
  `docs/superpowers/LOOP-GUIDE-e7.md`: uz's prior art.
- `~/.claude/gsd-core/workflows/autonomous.md`, `execute-phase.md:415` and
  `plan-review-convergence.md:171`: upstream, read-only.
</canonical_refs>

<code_context>
## Existing Code Insights

- `skills/ai-kit-spec-execute/detect_framework.py`: routes the two frameworks, and its
  `docs/superpowers/plans/` substring match decides D-15.
- `skills/_shared/ai_kit_rules_common/makefile_parse.py` and
  `ai-kit-project-rules-cicd/package_scripts.py`: the sources for D-18's copied helpers.
- `.planning/scripts/cross-ai.mjs --print-argv` works offline (exit 0, lists pi, cursor and
  opencode) but prints absolute binary paths.
</code_context>

<specifics>
## Specific Ideas

- The copy markers and the "AGENTS.md first" rail come from uz's own one-shot prompt.
</specifics>

<deferred>
## Deferred Ideas

Research questions for `gsd-phase-researcher`:
1. Is `/goal` text also the agent's instruction? Can it invoke a slash command? Is the cap
   counted in characters?
2. Does the whole multi-paragraph rest of a message become `$ARGUMENTS`? What are the other
   hosts' equivalents?
3. ~~Is the Agent tool unavailable at depth 1 in Claude Code 2.1.299? This decides D-09.~~ *(moot 2026-10-14, D-09 refined)*
4. What are codex 0.162.1's `/goal` syntax and its loop or schedule primitives?
5. Does original GSD have `/gsd-autonomous`, `runtime-identity` and `verification.status`?
6. What do pytest, jest, vitest, Playwright, Cypress, `go test` and `cargo test` print or
   return when no tests run?
7. How can a session list its deferred-but-available tools reliably?
8. Do opencode, pi and cursor-agent have native goal, loop or schedule support?
9. Is `gsd-tools review-lane plan` read-only?
</deferred>
