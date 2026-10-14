# Phase 27: One-shot goal and loop prompt skill — Specification

**Created:** 2026-10-14
**Ambiguity score:** 0.16 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

The user names a set of GSD phases or superpowers plans and gets a file with a ready-to-paste
prompt for a separate agent session. The prompt carries everything needed to finish the work:
- the execution strategy chosen for the host;
- the rails;
- both quota directives;
- a definition of done that requires the project's real e2e tests to pass, with evidence printed
  in the transcript.

## Background

- **Source:** todo `2026-10-14-agents-md-quota-schedule-rules-and-goal-prompt-skill.md`, part 2,
  plus uz's clarifications:
  - choose one to three strategies with a selection matrix, not a single template;
  - e2e is the core of done;
  - jev cannot judge whether a UI is good (2026-10-14).
- **Live facts on this machine (2026-10-14):**
  - **Claude Code 2.1.299.** `/goal` needs 2.1.139 or later (official docs). It is
    transcript-judged, its condition is capped at 4,000 characters, and it runs headless via
    `claude -p "/goal …"`. The in-session primitives are `CronCreate`, `ScheduleWakeup`/`/loop`
    and `Monitor`;
  - **codex-cli 0.162.1.** `codex features list` reports `goals stable true`. The `/goal` usage
    itself comes from third-party docs only;
  - **opencode and pi.** No native goal or loop found; there are community wrappers only
    (unverified);
  - **`/gsd-autonomous` (OpenGSD 1.16.0 workflow).**
    - Flags: `--from N`, `--to N`, `--only N`, `--interactive`, `--converge` (alias
      `--cross-ai`), reviewer selectors and `--max-cycles N`.
    - A step that fails three "Fix and retry" attempts halts as `needs_human`. Every stop
      prints a `Resume with: /gsd-autonomous --from …` line;
  - **ai-kit e2e.** The repository's own e2e tier is `make e2e-test`: real git worktrees, the
    PTY-spawned wizard and `tests/test_install.sh`.
- **Inputs from earlier phases:**
  - Phase 25 subprocess-quota policy (mechanism B);
  - Phase 26 session wake, its survival matrix and the OpenGSD identity check (mechanism A);
  - Phase 24 skill patterns: `decide.py detect`, references loaded on demand, and the
    skill-judge loop;
  - the rules skill's R04 (cross-AI review and execution declared in every plan).
- **jev** (`jev-fast-decision`, Laya, TypeSafe) answers typed questions about supplied text. It
  cannot see a rendered UI, so it never judges UI quality or mockup fidelity.

## Requirements

1. **Detection** (GPS-01).
   - Current: none.
   - Target: the skill asks at most four questions:
     - the work set;
     - the target host, defaulting to the current one;
     - native execution allowed or not;
     - mockups, if any.

     It then detects three things:
     - the host's goal, loop and schedule primitives, as tools as well as slash commands, each
       labelled `verified` or `unverified` (reusing Phase 26's survival matrix);
     - GSD or OpenGSD (Phase 26's identity check), and per phase whether SPEC, CONTEXT and PLAN
       files exist;
     - superpowers plans and their declared dependencies.

     Primitives for a host that is not running here are labelled unverified.
   - Acceptance: fixture projects for OpenGSD with mixed phase states, for original GSD, for
     superpowers plans only, and for neither. A non-current target host's primitives come out
     unverified.
   - *Amended 2026-10-14 (27 D-04..D-07):* tool primitives are reported by the agent (only it sees its tool list; deferred tools unseen are "unverified", never "absent"); each primitive carries two labels, availability here and usage source; Phase 26's matrix is read through its `matrix --json` CLI, all-unverified when missing.

2. **Strategy matrix** (GPS-01).
   - Current: none.
   - Target: a data table maps the inputs to one to three ranked strategies, each with its
     reason and one marked recommended. The inputs are:
     - the host's primitives;
     - the scope kind;
     - whether the work must outlive the session or a quota stall;
     - whether the end state can be proven in the transcript.

     The strategies are:
     - `/goal`;
     - schedule or `/loop` (Phase 26's survival rule picks the primitive);
     - `/gsd-autonomous --from/--to [--converge]`, optionally wrapped in `/goal` to guard on
       VERIFICATION.md.
   - Acceptance: one table test per row. A host with no goal primitive never gets `/goal`. An
     OpenGSD phase range always offers `/gsd-autonomous`.
   - *Amended 2026-10-14 (27 D-10, D-12):* `/gsd-autonomous` greps all of its arguments for flags (`autonomous.md:21-62`), so its line carries flags only and the rails live in the file. "Must outlive" and "provable" are derived and shown, never asked.

3. **Prompt and rails file** (GPS-02).
   - Current: none.
   - Target: the output is one `.md` file in two parts.
     - **The paste-ready prompt.** For `/goal` it is a short, measurable condition of at most
       4,000 characters. It names the rails file and the evidence the agent must print.
     - **The rails.** Read AGENTS.md first; read candidate skills only when relevant; never skip
       pre-commit (`--no-verify` is forbidden); the done checks; the stop-if rules (the same
       failure three times, a turn cap, a blocking decision); quota mechanisms A and B as
       separate directives; and the final summary.

     The file goes in the planning directory when one exists. Otherwise it goes where the user
     says, defaulting to an ignored scratch directory. Paths in the prompt are repo-relative.
   - *Amended 2026-10-14 (27 D-15):* the file is committable in a dated `goals/` subfolder (`.planning/goals/` for GSD, `docs/superpowers/goals/` for superpowers, never under `plans/`), because a run that creates a new worktree cannot see ignored files.
   - Acceptance: a test checks that the generated condition is at most 4,000 characters and
     that every rails section is present. No absolute path and no secret appears in the file.

4. **Superpowers plans** (GPS-02).
   - Current: none.
   - Target: the prompt runs one fresh subagent per plan, one at a time in dependency order,
     and the orchestrator verifies each plan's done checks. A failed plan stops only the plans
     that depend on it; the rest continue. The orchestrator owns AGENTS.md compliance.
   - Acceptance: a fixture with a dependency chain and an independent plan yields an order and
     stop-scope that match.
   - *Amended 2026-10-14 (27 D-08, D-09):* superpowers plans have no dependency field; ai-kit reads an optional `**Depends on:**` line (backticked plan files become edges; free text is asked inside the work-set question). Whether a per-plan subagent can itself dispatch per-task subagents is open research; where it cannot, the orchestrator dispatches each plan's tasks itself, plan by plan (provisional, ledgered for uz).

5. **OpenGSD cross-AI** (GPS-02).
   - Current: none.
   - Target: the prompt makes cross-AI review (plan-review convergence) and cross-AI execution
     declared in each plan, not only in settings. Its first step is a cross-AI readiness check:
     a runner command exists and an external CLI is usable. On failure it stops before
     execution and reports what to fix, unless native execution was chosen when the prompt was
     generated; the prompt then says so plainly.
   - Acceptance: fixtures for a ready setup, a missing runner and native execution chosen.
   - *Amended 2026-10-14 (27 D-16, D-17):* "declared in each plan" is PLAN.md frontmatter `cross_ai: true` (AND-ed with config, `execute-phase.md:415`; absent from GSD's plan template) and a phase `REVIEWS.md` from `--converge`. Readiness proves the runner exists, `--print-argv` lists an installed CLI, and the reviewer CLIs are installed, labelled "installed, not quota- or auth-verified".

6. **E2E is the core of done** (GPS-03).
   - Current: none.
   - Target: the skill detects the project's real e2e commands:
     - Makefile `e2e*` targets;
     - package scripts;
     - Playwright or browser configs;
     - PTY/TUI test drivers.

     The prompt requires them green before done. The agent prints the evidence into the
     transcript: the command, its exit code and the tail of its output; the paths of
     screenshots or TUI text snapshots. Unit tests alone never count as done. With no e2e suite,
     creating one is the first task. The prompt also requires killing every process the e2e run
     started.
   - Acceptance: fixtures with Makefile e2e, package-script e2e, Playwright, and no e2e (the
     create-first task appears). The done section names the detected commands.

7. **jev is advisory and text-only** (GPS-04).
   - Current: none.
   - Target: the prompt may run one advisory jev check at the end: how close the delivered work
     is to the stated objectives, from text summaries only. The result is reported and never
     gates. When a mockup is supplied, the prompt routes fidelity to e2e screenshots plus human
     review, never to jev.
   - Acceptance: no generated prompt uses jev as a gate or for UI or mockup judgment (test on
     the generated text).

8. **Skill quality** (GPS-04).
   - Current: none.
   - Target: a new skill under `skills/` follows the Agent Skills standard. Its generator code
     is stdlib-only with tests, and it is wired into the gates the way Phase 24's skill was. Its
     SKILL.md passes `/skill-judge`.
   - Acceptance: skill-judge evidence is committed; `make test` and `make validate` are green.

## Boundaries

**In scope:**
- Detection, the strategy matrix, the prompt and rails file
- Superpowers and OpenGSD specifics, e2e as done, advisory jev, the skill itself

**Out of scope:**
- Running the generated prompt (the user pastes it into a separate session)
- Building the session wake or the subprocess policy (Phases 26 and 25; this skill only emits
  their directives)
- Judging UI quality or mockup fidelity automatically
- Native goal or loop support for hosts that lack one

## Constraints

- Generator code is stdlib-only; the prompt contains no secret and no machine-specific path.
- Unverified host primitives are labelled unverified in the prompt.
- jev receives summaries only, never source code or secrets.
- The prompt never instructs `--no-verify` or skipping a test tier.

## Acceptance Criteria

- [ ] Detection works on the four fixture project kinds and labels non-current hosts unverified
- [ ] The strategy matrix yields one to three ranked strategies with one recommended
- [ ] The `/goal` condition is at most 4,000 characters and names the rails file
- [ ] Every rails section is present; quota A and B appear as separate directives
- [ ] Superpowers: one subagent per plan, dependency order, failure stops only dependents
- [ ] OpenGSD: cross-AI declared per plan; the readiness gate stops unless native was chosen
- [ ] E2E commands are detected and required green with printed evidence; no suite means
  create one first
- [ ] jev is advisory and text-only in every generated prompt
- [ ] SKILL.md passes `/skill-judge`; `make test` and `make validate` are green
- [ ] MUST NOT: a generated prompt never declares done on unit tests alone
- [ ] MUST NOT: a generated prompt never uses jev as a gate or a UI judge

## Edge Coverage

**Coverage:** 34/35 applicable edges resolved · 1 unresolved (floor recomputed 2026-10-14 after the R1/R2/R4 amendments)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | A project with both `.planning/` and superpowers plans asks which work set is meant; it never merges them |
| empty | R1 | ✅ covered | No GSD and no superpowers plans: the skill reports that and asks for the work set as free text |
| ordering | R1 | 🧪 backstop | Phases are listed in roadmap numeric order (handles `16.1`) |
| concurrency | R1 | 🧪 backstop | Detection is read-only; it never writes to the project |
| encoding | R1 | ✅ covered | Agent-reported tool names are matched exactly against the matrix's primitive names; an unknown name is listed as unrecognized (added after the 2026-10-14 amendment) |
| adjacency | R2 | ✅ covered | Two strategies of equal rank keep matrix order; exactly one is marked recommended |
| empty | R2 | ✅ covered | A host with no goal, loop or schedule primitive gets a plain prompt plus the OS-timer wake, flagged |
| ordering | R2 | ✅ covered | At most three strategies, ranked by fit, pinned by a test |
| concurrency | R2 | 🧪 backstop | Strategy selection is a pure function of the detection result and the answers (added after the 2026-10-14 amendment) |
| boundary | R3 | ✅ covered | A condition of exactly 4,000 characters passes; 4,001 fails generation with a clear error |
| adjacency | R3 | ✅ covered | Quota A and B are two separate sections even when both apply |
| empty | R3 | ✅ covered | No candidate skills: the section says "none" rather than being omitted |
| encoding | R3 | ✅ covered | The cap counts characters (code points), not bytes |
| ordering | R3 | 🧪 backstop | AGENTS.md is always the first rails step |
| precision | R3 | ✅ covered | Paths are repo-relative; a home or absolute path in any field fails generation |
| concurrency | R3 | ✅ covered | An existing prompt file with the same name is never overwritten; a numbered suffix is added |
| adjacency | R4 | ✅ covered | An independent plan after a failed one still runs |
| empty | R4 | ✅ covered | One plan: one subagent, no ordering section |
| ordering | R4 | ✅ covered | Ties in dependency order keep the plan files' numeric order |
| encoding | R4 | ✅ covered | A `**Depends on:**` entry links only an exact backticked plan filename; anything else is free text asked about (added after the 2026-10-14 amendment) |
| concurrency | R4 | ✅ covered | Plans run one at a time; no two plan subagents share the working tree at once (added after the 2026-10-14 amendment) |
| adjacency | R5 | ✅ covered | A plan that already declares cross-AI is left as is; only missing declarations are required |
| empty | R5 | ✅ covered | No cross-AI runner and native not chosen: the readiness gate stops the run before execution |
| ordering | R5 | 🧪 backstop | The readiness check runs before any plan is executed |
| boundary | R6 | ✅ covered | An e2e command that exits 0 but reports zero tests run does not count as green |
| adjacency | R6 | ✅ covered | A target named `e2e` and one named `e2e-test` are both listed; neither is guessed away |
| empty | R6 | ✅ covered | No e2e suite: creating one is the first task, before any feature plan |
| encoding | R6 | 🧪 backstop | Printed output tails are plain text; ANSI codes are stripped |
| ordering | R6 | 🧪 backstop | E2E runs after the unit and lint gates in the done checks |
| precision | R6 | ✅ covered | Evidence includes the exact exit code, not a paraphrase |
| idempotency | R6 | ✅ covered | Re-running the done checks repeats the same commands |
| concurrency | R6 | ✅ covered | The prompt requires killing every process the e2e run started |
| empty | R7 | ✅ covered | With jev not installed, the advisory check is omitted and the prompt says so |
| encoding | R7 | 🧪 backstop | The jev input is a text summary of objectives and results, never code or images |
| unclassified | R8 | ⚠ UNRESOLVED | No shape cue; skill quality is specified by the skill-judge loop and the gates |

## Prohibitions (must-NOT)

**Coverage:** 4/4 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT declare done on unit tests alone | R6 | resolved | test on generated text |
| MUST NOT use jev as a gate or a UI or mockup judge | R7 | resolved | test on generated text |
| MUST NOT emit `--no-verify` or a skipped test tier | R3 | resolved | test on generated text |
| MUST NOT put a secret or an absolute path in the prompt file | R3 | resolved | test (sentinel key and home path absent) |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | One file, one paste-ready prompt, e2e as done |
| Boundary Clarity   | 0.84  | 0.70 | ✓      | Emits Phase 25/26 directives; never runs the prompt |
| Constraint Clarity | 0.82  | 0.65 | ✓      | Cap, no secrets, unverified labels, jev text-only |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 11 pass/fail criteria over generated text and fixtures |
| **Ambiguity**      | 0.16  | ≤0.20| ✓      | Initial 0.29; one round |

## Interview Log

`--auto`, one round. The open items went through `ai-kit-gsd-spec-discuss`'s ladder (`decide.py`: Laya per item, `needs_fallback` to TypeSafe). Summaries only, advisory. Rule: best design over the smallest diff.

| Round | Perspective | Question summary | Laya (advisory) | TypeSafe (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Simplifier | Rails longer than the 4,000-char goal cap? | condition_plus_file 0.58 (fb) | condition_plus_file 0.97 | Short condition naming a rails file (R3) |
| 1 | Boundary Keeper | Where does the prompt file go? | planning_dir_else_ask 0.53 (fb) | planning_dir_else_ask 1.00 | Planning dir; else ask, default scratch (R3) |
| 1 | Failure Analyst | Cross-AI setup incomplete? | readiness_gate 0.81 | — | Readiness gate stops unless native was chosen (R5) |
| 1 | Researcher | Which host's primitives? | ask_default_current 0.43 (fb) | ask_default_current 0.90 | Ask, default current; others unverified (R1) |
| 1 | Seed Closer | Plan scheduling? | dependency_order_sequential 0.56 (fb) | dependency_order_sequential 0.77 | One at a time in dependency order; failure stops dependents only (R4) |

---

*Phase: 27-one-shot-goal-and-loop-prompt-skill*
*Spec created: 2026-10-14*
*Next step: /gsd-discuss-phase 27 — implementation decisions (how to build what's specified above)*
