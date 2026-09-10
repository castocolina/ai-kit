# ONESHOT PLAYBOOK — ai-kit Claude Code Autonomous Run

**Phase 1.1 has exercised this playbook's Rule 2 (plan-review convergence) and Rule 6 (clean-room E2E gate) for real while closing itself — see `01.1-REVIEWS.md` and this phase's own `make e2e-docker` run. Phases 1.2 through 5 have not yet run under this playbook; treat those sections as reviewed-but-unexercised until each phase actually closes.** General, phase-agnostic execution rules for any
autonomous `/gsd-autonomous` run in this repository (adapted from the `wezterm-setup`
playbook's structure, not its content — ai-kit's highest-risk surface is real AI-CLI
config corruption, not GUI/input-injection, so the rules below are grounded in this
project's own `AGENTS.md` and `.planning/PROJECT.md` constraints, not copied wholesale).
Phase-specific scope (which phases, which decisions are locked) lives in each phase's
own `{N}-CONTEXT.md` and in `.planning/ONESHOT-AUTONOMOUS.md`'s entry-prompt — this file
states the rules that apply regardless of which phase is currently running. Do not treat
any specific number, path, or finding below as final until reviewed. Read this in full
at the start of the run and again at the start of every turn.

## Starting Point

Determine the working phase at invocation time, not from a hardcoded number: read
`.planning/ROADMAP.md` and `.planning/STATE.md` and use the earliest phase that is not
`phase_complete`. `gsd-autonomous`'s own resume gates already reconcile a
partially-finished phase — do not hand-run a phase's closeout; let the Per-Phase
Checklist below apply to whichever phase is earliest-incomplete, up to whatever stop
point the entry prompt names. Execution order is `1.1 → 1.2 → 2 → 3 → 4 → 5`
(`.planning/ROADMAP.md` §Progress) — Phase 1.1 must close before Phase 1.2 is planned,
since it wires the cross-AI routes this whole run depends on (Rule 2).

## Per-Phase Checklist

For every phase this run touches, confirm all of these before advancing — do not assume
any ran just because the previous one did:

1. **Discuss** — `{N}-CONTEXT.md` exists and reflects the phase. Phases 1.2-5 already have
   one from prior sessions (`has_context: true`) — do not re-run discuss-phase and do not
   second-guess their locked decisions. Phase 1.1 is infrastructure-only and may skip a
   full discuss-phase cycle per its own `ROADMAP.md` entry, but still needs a plan.
2. **Plan** — `PLAN.md` file(s) exist for every wave, and carry `cross_ai: true` in
   frontmatter when cross-AI execution delegation is intended for that plan (Rule 2).
   Every plan, regardless of `cross_ai`, goes through plan-review convergence (Rule 2) —
   `workflow.plan_review_convergence: true` is unconditional in this project's
   `.planning/config.json`, not opt-in per plan.
3. **Plan-review convergence** — run planning through `--converge` with
   `review.default_reviewers`/`review.models` (`.planning/config.json`). 0 unresolved
   HIGH concerns before execution. This is mandatory for every plan in this milestone —
   unlike GSD's own default (opt-in via config), this project's `config.json` has
   `plan_review_convergence: true` set unconditionally (Phase 1.1's own success
   criterion #1) — never skip it because a plan "looks simple."
4. **Execute** — every wave's `SUMMARY.md` exists, tree is clean, `make test` green.
   Record whether cross-AI execution fired (`workflow.cross_ai_execution`) or fell back
   to a local `gsd-executor` — either is acceptable, but note which happened and why.
5. **Code review** — `REVIEW.md` shows clean or all findings fixed.
6. **Clean-room E2E gate** — for any plan touching `tools/*.py`, `tools/install.sh`,
   or a `skills/*/SKILL.md` that reads/writes a runtime config file, `make e2e-docker`
   must pass in addition to local `make test` before the phase can close (Rule 6). Pure
   planning/documentation-only plans may skip this gate.
7. **Verify-work** — `VERIFICATION.md` shows `passed`, backed by REAL command output
   (Rule 1). Never accept a delegate's or subagent's unverified claim.
8. **Real-machine-mutation review** — confirm no step in this phase ran
   `tools/install.sh`, the wizard, or any config-doctor apply against uz's actual
   `~/.claude`, `~/.cursor`, `~/.config/opencode`, or `~/.codex` (Rule 5). This applies
   to every phase, not just Phase 4 (Config Doctor) — Phase 2 (opencode provider
   surgery) and Phase 3 (hook wiring) touch the same class of real files.
9. Only close a phase and advance once every applicable item above is evidenced.

This repository IS `.codegraph/`-indexed — use `codegraph_explore` before any
Grep/Read loop, per `AGENTS.md`'s Code Exploration section, throughout this run.

## Non-Negotiable Rules

1. **Never trust a self-reported "passed."** `.planning/PROJECT.md`'s core value is
   explicit: ai-kit must never claim more certainty than it has verified. This applies to
   this run's own agents and delegates exactly as it applies to the product itself —
   "should work", "tests pass", "looks right" are not evidence; the actual output of the
   verifying command, with its exit code, is. Whichever agent or delegate ran execution,
   the orchestrator itself re-runs the real verification commands (`make test`,
   `make lint`, `make e2e-docker` where applicable) afterward before advancing.

2. **Cross-AI delegation contract — plans declare it, and each role has a defined
   fallback.** `.planning/config.json` carries two independent cross-AI routes,
   live-verified reachable on this machine before this run started:
   - **Plan-review convergence** — PRIMARY: opencode `router-env/my-plan-review`
     (`review.default_reviewers`/`review.models`). FALLBACK if the primary route is
     unreachable, errors, or times out: `opencode run --model openai/gpt-5.6-sol` at high
     reasoning effort. Record which path actually ran.
   - **Execution delegation** — PRIMARY: opencode `router-env/my-coding`
     (`workflow.cross_ai_command`). FALLBACK: `opencode run --model xai/grok-4.6`.
     Record which path actually ran.
   - Every generated `PLAN.md` whose execution should delegate to cross-AI must carry
     `cross_ai: true` in its frontmatter — that field is what makes `execute-phase.md`
     delegate to `workflow.cross_ai_command` instead of a local `gsd-executor`. Add it if
     a planner omits it when cross-AI execution is intended for that plan.
   - Never substitute one role's model for the other's — plan-review and execution are
     different jobs; a fallback for one is not a fallback for the other.
   - Do not assume a configured route is reachable just because it's present in
     `.planning/config.json` — a config entry records intent, not a live-tested
     connection. This run's FIRST cross-AI call for a given role is that role's actual
     confirmation; apply that role's fallback before treating a failure as Rule 7's
     circuit breaker, and do not invent a third model on the fly.

3. **Config-safety is absolute, not phase-scoped.** Mirrors `AGENTS.md`'s own
   Non-Negotiable Rules — every write this run makes to any runtime config file (real or
   fixture) is atomic (`tempfile.mkstemp()` + `os.replace()`); a JSONC surgical edit
   preserves every other byte untouched; no diagnostic/detection/catalog result is ever
   presented with more certainty than its actual sourcing. A phase's plan or code review
   that ships a non-atomic config write is a blocking finding, not a style note.

4. **Respect phase boundaries — never modify another phase's already-locked scope from
   within the current one.** Before editing a shared file (a cross-cutting module, a
   shared config schema, another phase's already-written `SKILL.md`), check whether an
   earlier phase's `{N}-CONTEXT.md` already locked decisions about it. If live
   verification during a later phase genuinely contradicts an earlier phase's
   `CONTEXT.md`/`REQUIREMENTS.md`/`ROADMAP.md` wording, amend those files formally with a
   dated note (the pattern already used this milestone — see `03-CONTEXT.md` D-09/D-10,
   `04-CONTEXT.md`'s Cursor-scope expansion, `05-CONTEXT.md` D-10) rather than either
   silently reinterpreting it or silently leaving the contradiction unresolved.

5. **Never mutate uz's real AI-CLI configuration during this run — no exceptions, no
   phase-by-phase judgment call.** Unlike a project where "does this legitimately need to
   touch the real machine" is a per-phase decision, ai-kit's own core value (never corrupt
   uz's AI-CLI configuration) makes this an absolute for verification during an autonomous
   run: never run `tools/install.sh`, `tools/setup.py`'s interactive wizard, or any Phase 4
   config-doctor apply action against the real `~/.claude`, `~/.cursor`,
   `~/.config/opencode`, or `~/.codex`. Every verification exercising install/wizard/apply
   behavior uses either a scratch `HOME`/`CLAUDE_CONFIG_DIR`/`AI_KIT_DIR` (the pattern
   `tests/test_wizard_pty.py` already establishes) or the `make e2e-docker` clean-room
   container (Rule 6). If a phase's own `{N}-CONTEXT.md` ever appears to call for a
   real-machine effect, treat that as a Rule 7 stop condition and surface it to uz — do not
   resolve the apparent conflict by running against the real machine anyway.

6. **Clean-room E2E is a real gate, not optional polish.** `make e2e-docker`
   (`tests/e2e/docker/`) builds a container with no cached `uv`/`textual` and no
   pre-existing `~/.claude`/`~/.cursor`/`~/.config/opencode`/`~/.codex`, then runs the full
   `make test`+`make lint` suite inside it — this is what actually proves the installer
   and wizard work on a machine that has never seen ai-kit before, not just on this
   already-provisioned dev box. Required before closing any phase whose plan touched
   `tools/*.py`, `tools/install.sh`, or a runtime-config-writing `SKILL.md` (Per-Phase
   Checklist item 6). If `docker`/`podman` is unavailable in the run's environment, that is
   a Rule 7 circuit breaker — record as `human_verification`, do not skip the gate
   silently and do not substitute a host-machine run as equivalent evidence.

7. **Circuit breaker — halt, do not guess past these:**
   - A cross-AI route (plan-review or execution) is unreachable AND its Rule 2 fallback
     also fails — do not silently proceed with zero reviewers/executors, and do not invent
     a third model on the fly.
   - `docker`/`podman` is unavailable, so Rule 6's clean-room gate cannot run for a phase
     that needs it.
   - A permission-granting step (sudo password, OS credential prompt, opencode/CLI
     re-authentication) requires interaction this session's account cannot complete
     non-interactively — record as `human_verification`, do not fake success.
   - Any tool/auth failure repeats with zero progress after a genuine retry.
   - A phase's locked decisions appear to require a real-machine mutation (Rule 5) — stop
     and surface it, do not resolve it unilaterally.

8. **Treat verification as a convergence loop, not a single check.** Any failing test,
   review finding, divergent behavior, or gap report must be planned, fixed, re-tested,
   and independently re-verified until clean. Do not halt merely because a previous
   corrective attempt failed — halt only for a Rule 7 condition or a demonstrated repeated
   zero-progress tool failure. If a `gaps_found` verification result appears, choose "Run
   gap closure" and continue this loop yourself.

9. **Stay within this project's stdlib-only / dev-only dependency discipline in every
   change this run produces.** `AGENTS.md`'s Architecture and Tools-and-Stack sections are
   binding here exactly as in normal work: `tools/status-line.py`,
   `tools/statusline-doctor.py`, and `tools/setup.py`'s non-wizard paths stay
   stdlib-only; a new dependency is dev/wizard-only and only after checking whether an
   existing stdlib-only approach already covers the need. Do not let autonomous-run
   pressure justify a shortcut here.

10. **English only, always, in everything this run writes** — `AGENTS.md`'s Non-Negotiable
    Rules apply unmodified: documentation, planning artifacts, commit messages, code
    comments. Translate any non-English input faithfully rather than leaving it verbatim.

11. **This run is an explicit, scoped exception to any "wait for an explicit go-ahead
    before committing" default.** uz's request for an autonomous run is the explicit
    authorization for unattended commit, for the exact scope named in
    `.planning/ONESHOT-AUTONOMOUS.md`'s entry prompt — `commit_docs: true` already governs
    GSD's own per-step commits. This exception does not carry forward to any work outside
    that named scope, and never authorizes a force-push or a destructive git operation
    (`git reset --hard`, `git clean -f`, force-push) without a separate, explicit
    confirmation from uz.

12. **Every new detection/config-write code path ships with test coverage in the same
    commit.** Mirrors `AGENTS.md`'s Testing section: a new runtime-detection branch, a new
    JSONC surgical-edit path, or a new config-doctor check must land with its own test
    (and, per Rule 6, exercised in the clean-room container before the phase closes), not
    as untested glue.

## Cross-AI Execution — Confirm Reachability Before Relying On It

Both routes were live-verified reachable from this machine immediately before this
playbook was written (`opencode auth list` showed OpenAI/xAI credentials present;
`opencode models` listed both fallback models; `router-env`'s `my-coding`/`my-plan-review`
combos are declared in `~/.config/opencode/opencode.jsonc`) — but a config entry still only
records intent, not a live-tested connection for THIS run. The run's FIRST cross-AI call
for a given role is that role's actual confirmation. If the PRIMARY route fails, apply
that role's Rule 2 fallback before treating it as Rule 7's circuit breaker — do not retry
the same failing route indefinitely, and do not invent a model outside the two defined
fallbacks without surfacing that first.

## Phase/Milestone Close

At the end of whatever scope this run targets (or at any Rule 7 halt), consolidate
everything a human needs to see into a single end-of-run report — real command
output/exit codes (Rule 1), which cross-AI route actually ran for each role (Rule 2),
`make e2e-docker` evidence for every phase that required it (Rule 6), and any
`human_verification` items recorded along the way — so the one review pass after this run
has everything in one place, never a mid-run stop to ask for it.
