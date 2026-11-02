# Spec-discuss run modes and jev in every skill: research

Read-only research, 2026-11-02. Local GSD install is gsd-core 1.18.0
(`.claude/gsd-core/VERSION`); the online `next` branch is 1.19.0. Helper scripts in this folder:
`diff_gsd_next.sh` (fetches `next` with `gh api` into `gsd-next/` and diffs it against the local
install), `jev_mentions.sh` (counts jev mentions per skill).

## 1. What the spec-discuss skill does today

File: `skills/ai-kit-gsd-spec-discuss/SKILL.md`.

- It never calls the `/gsd-spec-phase` or `/gsd-discuss-phase` commands. It reads the workflow
  files directly ("do not delegate to another skill", lines 103-105). So the command's routing
  logic, where `--assumptions` is handled, never runs. The "flags" below are the arguments it
  hands to the workflow files.
- Run mode is picked once (lines 78-85). The skill's own `--auto` flag means the auto path.
  Without it, the skill asks once and recommends auto when the project `mode` is `yolo` or the
  phase's MVP mode is active. Otherwise it recommends interactive. It never flips config keys.
- **Auto path**
  - Spec: `spec-phase.md` with `N --auto` (line 103).
  - Discuss: `discuss-phase-assumptions.md` with plain `N`. It never passes `--assumptions` or
    `--auto` (lines 126-130, NEVER list lines 257-261).
  - The skill applies the intent of `--analyze --all --batch` itself (lines 146-154): every area
    in one pass, 2-3 alternatives per Likely or Unclear item, all of a phase's questions in one
    ladder run, and fixed pre-answers to the workflow's prompts.
  - It skips the workflow's `auto_advance` step (lines 133-135), so it never starts plan-phase.
- **Interactive path**
  - Spec: plain `N` (lines 103-104).
  - Discuss: `discuss-phase.md` in standard mode, with no flags named, and the user answers
    (lines 13-14, 81-84, 129-130). The ladder screens only the items the user asks it to screen
    (lines 142-144).
- **How it reaches jev**
  - Everything goes through `python3 "$S/decide.py"`: `detect` (lines 46-52), `consent grant` and
    `consent revoke` (lines 65-71), and `ladder` / `ladder --second-opinion` (lines 179-214).
    decide.py runs the shared `jev-fast-decision` client.
  - With no client found (`no_client` or `incompatible_client`) it falls back to own reasoning
    only (lines 50-52).
  - The analyzer and advisor subagents are forbidden to call jev themselves (lines 165-173).
- The description trigger quotes `"--analyze --all --batch --assumptions"` (line 3). It is
  written as a trigger phrase, not as the flags the skill passes.
- This design was a recorded decision: Phase 24 CONTEXT decision D-01 ("The discuss step never
  passes `--assumptions`; the skill encodes the flags' intent"),
  `.planning/milestones/v1.3-phases/24-spec-and-discuss-chain-skill/24-CONTEXT.md:19` and
  `24-SPEC.md:25-26,89`.

## 2. What each flag does in the project-local GSD

Command files: `.claude/commands/gsd-spec-phase.md` and `gsd-discuss-phase.md`. Workflows are
under `.claude/gsd-core/workflows/`.

- **spec-phase** accepts only `--auto` and `--text` (command line 4; lines 27-28).
  - `--auto` skips the interview and picks the recommended defaults (spec-phase.md:188).
  - It reuses an existing SPEC as-is (lines 82-86).
  - It skips the interview entirely when the first ambiguity score is 0.20 or lower (line 133).
  - It never auto-dismisses edge or prohibition rows (lines 462-467, 547-548).
  - It does not chain into discuss.
- **`--assumptions`** (discuss command, lines 56-58): if it appears anywhere in the arguments,
  the command runs `list-phase-assumptions.md` and stops. That workflow is conversational only
  ("No file output", list-phase-assumptions.md:6). It runs before every other check, so
  `--auto`, `--analyze` and the rest are dropped. The real assumptions workflow
  (`discuss-phase-assumptions.md`) is reached only when `workflow.discuss_mode` is
  `assumptions` (command lines 60-61). That setting is `discuss` in this project.
- **`--all`** (discuss-phase/modes/all.md): selects every gray area automatically. The user
  still answers every question. It does not auto-advance.
- **`--batch`** (modes/batch.md): groups 2-5 questions into one turn, 4 by default
  (`--batch=N` is clamped to 2-5).
- **`--analyze`** (modes/analyze.md): shows a trade-off table with a recommendation before each
  question or batch.
- **`--auto` in standard mode** (modes/auto.md, discuss-phase.md:28,153):
  - selects all areas, takes the recommended option for every question with no prompt, and
    folds todos that score 0.4 or more;
  - after writing CONTEXT it **auto-advances into plan-phase and then execute-phase** through
    chain.md, and writes `workflow._auto_chain_active=true` to config (chain.md:46-53).
- **Combining `--auto` with the overlays** is valid but mostly redundant:
  - `--auto --batch` and `--auto --text` do nothing (auto.md:48-49).
  - With `--all --auto`, `--auto` wins (all.md:25-26).
  - `--auto --analyze` only adds trade-off tables to the audit trail (auto.md:50-51).
- **`--auto` in assumptions mode** (discuss-phase-assumptions.md):
  - It is the only flag that workflow parses (line 71). It never reads `--analyze`, `--all` or
    `--batch`, because it already analyzes every area in one pass.
  - With `--auto`, Unclear items get the recommended default (lines 383-388) and the run then
    starts `gsd-plan-phase N --auto` (steps/auto-advance-dispatch.md:10).
- **So, for wish A's auto discuss (`--auto --assumptions`)**:
  - Passed as typed to the command, it **writes no CONTEXT and no log**: `--assumptions` routes
    to the listing workflow and `--auto` is ignored. This holds in both 1.18.0 and `next`.
  - If the intent is "assumptions mode, automatic", nothing is lost by dropping
    `--analyze --all --batch`, because that workflow ignores them anyway. GSD's own `--auto`
    would add two things the skill avoids today: Unclear items settled by GSD's default instead
    of the jev ladder, and a chain into plan-phase and execute-phase.
- **Wish A's interactive discuss (`--analyze --all --batch`)** is a valid and useful combination
  for `discuss-phase.md`: every area, batched questions, a trade-off table per batch. Today the
  skill's interactive path runs plain standard mode, so this part of wish A is a real change.
  The skill reads `discuss-phase.md` directly, so it works even when a project sets
  `discuss_mode=assumptions`.
- **Upstream `next` (1.19.0) compared with local 1.18.0** (from `diff_gsd_next.sh`):
  - The four mode overlay files and both commands' argument lists are identical, and
    `--assumptions` still routes to the listing workflow.
  - The real changes:
    - init now returns `has_spec` and `spec_path`;
    - `discuss-phase-assumptions.md` gains a `check_spec` step that passes the locked SPEC
      requirements into the analyzer prompt. In 1.18.0 the assumptions workflow never reads the
      SPEC; the skill's analyzer brief supplies it.
    - `/gsd:` command names in the source become `/gsd-` in the install, which is the
      installer's renaming.
  - None of this changes the flag analysis.

## 3. Wish A compared with the memory note

`memory/feedback_spec_discuss_with_jev.md`:

- Line 9: spec runs with `--auto`. Line 10: discuss runs with
  `--analyze --all --batch --assumptions N` (the auto, unattended chain from tools-installer).
- **Difference 1.** In the memory note, `--analyze --all --batch` belong to the auto run. Wish A
  moves them to the interactive default, and gives auto discuss `--auto --assumptions` instead.
- **Difference 2.** The memory note has no `--auto` on discuss. Wish A adds it. In GSD that means
  auto-advancing into plan-phase and execute-phase plus GSD's default answers for Unclear items.
  The skill's NEVER rule (lines 259-261) forbids exactly that.
- **Shared problem.** Both rely on the literal `--assumptions` flag, which writes nothing (see
  section 2). The memory note dates from gsd-core 1.16, where the agent read the flags as intent.
- **A further contradiction inside the memory note.** Line 10 says the analyzer "gets jev
  through `agent_skills`", but the skill forbids the analyzer to call jev (SKILL.md:165-168). The
  same line names TypeSafe as the next rung and never mentions Zen.

## 4. jev-fast-decision (read only its SKILL.md and its documented reference.md)

- **Location.**
  - It lives in this repo at `skills/jev-fast-decision/`, is tracked by ai-kit git, and was last
    changed in commit e9b7ee9.
  - `~/.claude/skills/jev-fast-decision` is a symlink to it. There is no copy in
    `~/.agents/skills`.
  - llm-env holds only patches and notes (`tmp/ai-kit-lite-executor-patches/JEV-NOTES.md`), not
    the skill.
- **Fallback ladder.** It is already documented inside the skill (SKILL.md:10-20, 38):
  - `auto` probes `laya` (local) first, then the consented remotes `typesafe` and `opencode`
    (Zen), in table order.
  - Without consent, auto uses Laya only.
  - `JEV_BACKEND=<name>` picks one backend and never falls back.
  - The last rung is `needs_fallback: true`, which means "you decide that item with your own
    reasoning". That is the "native model" rung of wish B, though the skill does not name a model.
- **Consent.** Remotes need a recorded `consent grant <backend>` after the user says yes, or a
  session `JEV_ALLOW_REMOTE` set only after a yes. "The key is set" is not consent
  (SKILL.md:20, 46, 53; reference.md Consent record).
- **Kill switch.** `GSD_PATH_JEV=1` and `GSD_PATH_JEV_TIMEOUT_SECONDS` are required. Without them
  the status is `disabled` and you reason it out yourself (SKILL.md:25; reference.md:45).
- **When no backend works**, every case means "reason it yourself, never retry blindly"
  (reference.md:41-51):
  - status `unavailable` with reasons such as `no_backend_available`, `network_error`,
    `deadline` or `unauthorized`;
  - `consent_required_for_remote`, which means ask the user first;
  - per-item `needs_fallback: true`.
- **Zen.** The skill still lists Zen as a backend: in its description (SKILL.md:3), its intro
  (line 8), its backend table (line 18) and the reference's `JEV_OPENCODE_*` and
  `OPENCODE_ZEN_API_KEY` variables. The owner says Zen is being removed. That conflicts with
  backlog 999.9, which keeps Zen "gated, not deleted" because the owner was undecided on
  2026-10-24.
- **Memory notes.**
  - `reference_jev_backends.md` still describes the old variables `JEV_API_URL`, `JEV_MODEL` and
    `JEV_RESPONSE_MODEL`. reference.md marks them deprecated: `JEV_API_URL` survives only as a
    loopback Laya alias. That makes the note stale.
  - `feedback_jev_every_decision_point.md` says to use spec-discuss's `decide.py ladder` at every
    decision point. That ties callers to spec-discuss's wrapper rather than to the jev skill
    itself.

## 5. ai-kit skills and jev today

Mention jev:

- `ai-kit-gsd-spec-discuss`: the core user. It runs the ladder through its own `decide.py`
  wrapper and its prose names Laya, TypeSafe, OpenCode Zen, consent, the probe statuses and
  key-source details.
- `ai-kit-spec-goal-prompt`: an optional advisory check through spec-discuss's decide CLI. It is
  skipped when there is no `decide.py` or no usable backend, and "the file never depends on jev"
  (SKILL.md:151, 190, 193).
- `ai-kit-gsd-curated-config`: detects a "System One backend" for agent-skills wiring with a TCP
  check on `JEV_API_URL` or the presence of `JEV_API_KEY` (SKILL.md:78, 321;
  `ai_kit_gsd_curated_config/skill_scan.py:345-365`). That reads the old variables only. It never
  looks at `TYPESAFE_API_KEY`, the documented key, or at the default Laya URL, so its detection
  is probably stale.

Do not mention jev:

- ai-kit-cross-ai
- ai-kit-opencode-providers
- the seven ai-kit-project-rules-* skills
- ai-kit-session-wake
- ai-kit-spec-config
- ai-kit-spec-execute, -gsd and -superpowers
- ai-kit-spec-review, -checklist and -fixer
- ai-kit-usage-metrics
- the general skills cst-refactor, markdown-to-pdf and mermaid-audit

Working without a backend:

- spec-discuss and goal-prompt both claim it.
- The live check "Phase 24 chain with no decision backend installed, on a fixture project" is
  still open (`.planning/milestones/NEXT-MILESTONE-INPUTS.md:184`).
- Wish B must keep this property for every skill. jev is advisory, and with `disabled`,
  `unavailable` or `needs_fallback` the skill's own rule-based default or the agent's reasoning
  decides.

## 6. Planning items that already cover A or B, and the contradictions

**Wish A**

- No planning item covers it. Backlog 999.11 (spec-discuss polish, ROADMAP.md:266) covers
  different findings.
- Contradiction 1: 999.11's judge set lists "native Opus". Memory says there have been no native
  Opus judges since 2026-10-30.
- Contradiction 2: Phase 24 decision D-01 and the skill's NEVER rules forbid passing
  `--assumptions` and `--auto` to discuss, and wish A asks for both.

**Wish B, the fallback inside jev**

- Backlog 999.9 (ROADMAP.md:206) covers it: Laya first with a configurable URL and a first-run
  question, then TypeSafe from the environment, then Zen gated by host.
- Contradiction: 999.9 keeps Zen, and the owner now says Zen is being removed.
- Backlog 999.10 covers the key sources.

**Wish B, jev in every skill's prose**

- Partial cover:
  - todo `2026-10-29-unify-review-execute-lane-toml-effort-escalation-and-jev-classification.md`
    (jev classifies the input and output of review and execute, never as a hard dependency; it
    still names Zen);
  - backlog 999.17 (lite or strong executor through jev);
  - todo `2026-10-14-wire-jev-fast-decision-cross-host-discovery-scaffolding.md` (a marker block
    in the global instruction files, not per-skill prose);
  - memory `feedback_jev_every_decision_point.md`.
- **Black-box contradiction.** Backlog 999.17 (ROADMAP.md:394) states the owner's hard rule:
  ai-kit text says only "ask that skill, follow its own SKILL.md, the answer is advisory, and
  `needs_fallback` or no answer means the rule-based default decides". It must say nothing about
  local versus remote, consent, TypeSafe, environment variables or probes. Today's
  `ai-kit-gsd-spec-discuss` prose and `decide.py`, and `ai-kit-gsd-curated-config`, break that
  rule. `ai-kit-spec-goal-prompt` depends on spec-discuss's `decide.py` instead of on the jev
  skill.
- **Ownership contradiction.** NEXT-MILESTONE-INPUTS.md:47-48 lists a stale planning path in the
  jev skill's Laya backend note as something to fix. Under the black-box rule ai-kit should not
  edit that skill, yet the skill's source lives in ai-kit's own `skills/` folder.

## Open questions for the owner

1. **Auto discuss.**
   - Do you want `--auto --assumptions` passed to the discuss command exactly as typed? That
     writes no CONTEXT, in both 1.18.0 and `next`.
   - Or do you mean "assumptions mode, decided automatically"? The skill does that today by
     running the assumptions workflow directly.
2. **Plan-phase chaining and Unclear items.** GSD's own `--auto` on discuss continues into
   plan-phase and execute-phase and settles Unclear items with its own default.
   - Should the auto run keep stopping after discuss?
   - Should Unclear items keep going through the jev ladder?
3. **Interactive default.**
   - Is `--analyze --all --batch` the new interactive default, with every area, trade-off tables
     and batches of 2-5 questions?
   - Is the batch size of 4 fine?
4. **Memory note.** Should the spec-discuss memory note be updated to the new split? It records
   the opposite split today.
5. **Who owns jev-fast-decision?** Its source is in ai-kit's `skills/` folder.
   - Should it move out of the repo (to llm-env?), or stay in ai-kit with a "do not edit from
     ai-kit work" rule?
   - Who fixes its stale planning path and removes Zen from it?
6. **Zen removal.** Should Zen be dropped from the jev skill and from backlog 999.9 now, or stay
   gated until you decide?
7. **Scope of "every skill".**
   - Should jev reach every ai-kit skill, including the detect-only project-rules checkers and
     usage-metrics, or only skills that make choices (spec-discuss, spec-review, spec-execute,
     curated-config, goal-prompt)?
   - Should the general skills (cst-refactor, markdown-to-pdf, mermaid-audit) be left out?
8. **Black-box rewrite.** Should spec-discuss's prose and `decide.py` be rewritten to the
   black-box wording, without backend names, consent or probes? Should goal-prompt call the jev
   skill instead of spec-discuss's `decide.py`?
9. **The "native" rung.** Is the jev skill's "needs_fallback means you decide yourself" enough,
   or do you want a named non-fast model for that rung?
10. **Kill switch.** jev answers only with `GSD_PATH_JEV=1` set. Should skills set it for their
    own calls, or rely on your environment, where an unset switch silently means "no jev"?
11. **Curated-config detection.** It checks only the deprecated `JEV_API_URL` and `JEV_API_KEY`.
    Should fixing it be part of wish B?
