Judge: opus
Reviewed-sha256: 8cef3656bbba9bfa154bbdb15d0361b359afc2e99b349e069b4e8405506056b2
Lane: native subagent completed
Score: 97
Critical: 0
Important: 1

# Skill Evaluation Report: ai-kit-spec-execute-gsd

## Summary
- **Total Score**: 97/120 (81%)
- **Grade**: B
- **Pattern**: Process, with Tool-style low-freedom blocks (a phased Step 0-3 workflow and exact shell blocks)
- **Knowledge Ratio**: E:A:R = about 75:17:8
- **Verdict**: A dense, mostly expert adapter whose GSD-specific claims check out against the repo. The main defect is that a persistent session wake can be left armed on paths the close step does not cover.

**What I checked in the repo (all hold):**
- **GSD hook mechanics.** The hook is expanded unquoted as `-- ${CROSS_AI_CMD}`, stderr goes to `$ERROR_LOG`, and a dirty tree only warns (`.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:73,92,99`). Choosing `skip` falls back to the normal executor, the prompt is built only from the plan's `<objective>`/`<tasks>`, and a plan is delegated only when its `cross_ai: true` agrees with `workflow.cross_ai_execution` (`.claude/gsd-core/workflows/execute-phase.md:417-419`).
- **gsd-core search order.** `<root>/gsd-core`, then `.claude/gsd-core`, then `.codex/gsd-core` (`skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:92-93`), with the banner at `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py:110`.
- **Every shim subcommand and flag the package uses exists.**
  - The GSD adapter's subcommands and flags: `ai_kit_spec_gsd/cli.py:448-505`.
  - `cache-path --kind` and `trust-local --show`: `ai_kit_spec/cli.py:142,266-269`.
  - `ensure-runner --guidance-file`: `ai_kit_gsd_curated_config/cli.py:783-785`.
  - The session-wake `arm`/`done` options `--host`, `--session-id` and `--ref`: `ai_kit_session_wake/cli.py:61-83`.
- **`clear-workflow-keys` output.** `kept` is a dict of key to value, which is what the `USER_HOOK` parser expects (`cli.py:263-267`).
- **Session-wake arm output.** `arm` prints `armed|refreshed <host>-<id>` (`ai_kit_session_wake/arm.py:480`). That matches the `WAKE_OWNED` and `WAKE_HOST`/`WAKE_ID` split.
- **Cross-references.** The cross-AI skill's sections 4 and 6-8 exist and agree on the exit-code handling (`skills/ai-kit-cross-ai/SKILL.md:75,128,158,168`). The session-wake heading "When `arm` prints a companion time" exists (`skills/ai-kit-session-wake/SKILL.md:95`).
- **Unverified:** the "Node 24 (GSD's declared floor)" claim. I found no `engines` field in the project-local gsd-core.

## Dimension Scores

- **D1, Knowledge Delta: 15/20.** It carries real expert knowledge: GSD word-splits and globs the unquoted hook, so cursor `[effort=...]` brackets become glob classes; `skip` silently becomes a harness switch; the timeout floor and its ownership; delegated plans never see the phase-file block. It loses points for repetition. The unquoted-hook rationale appears four times (SKILL.md:1007-1011, 1024-1026; dispatch-notes.md:1321-1332, 1360-1362), and the codex `.git` unverified note appears twice.
- **D2, Mindset + Procedures: 12/15.** The "Mindset before writing anything here" bullets (SKILL.md:970-976) are real thinking patterns, and the procedures are ones Claude would not know (gating on opt-in before any write, mode-transition cleanup, resume_via routing). It is mostly procedure, with little "ask yourself" framing.
- **D3, Anti-Patterns: 13/15.** The NEVER list (SKILL.md:778-800) is specific, and most items give a reason that is not obvious: skip falls back to the native executor; re-resolving can rewrite the hook to another pair; never parse an empty result on exit 2. A few items have no reason ("never ask twice in one wave").
- **D4, Specification: 13/15.** The frontmatter is valid and the name is fine. The description gives WHAT and three numbered WHEN cases with keywords (`.planning/`, `model_profile_overrides`, `workflow.cross_ai_command`, `cross_ai true`). It is long and implementation-heavy, and it lacks user-phrasing triggers ("execute phase N with model X"). That is acceptable for a skill reached through a router.
- **D5, Progressive Disclosure: 12/15.** There is a MANDATORY full-read trigger for `cross-ai-hook-setup.md` inside the `cross_ai_hook` branch (SKILL.md:1001), "read only if you need the history" guidance for dispatch-notes (SKILL.md:1112-1114, dispatch-notes.md:1313-1314), and a MANDATORY sibling read at the stop handling (SKILL.md:1169). But the body is 459 lines, well over the ideal of 300. The Exec confinement, Node and history paragraphs could move to references.
- **D6, Freedom Calibration: 13/15.** Low freedom fits the fragile config writes and owner-stop rules. Exact blocks, literal re-substitution across fresh shells, and "never hand-edit" are right here. Plan-frontmatter inspection is left as prose with no command (SKILL.md:989, 994).
- **D7, Pattern: 8/10.** A clear Process pattern with checkpoints and stops. It drifts toward a Tool-pattern length.
- **D8, Practical Usability: 11/15.** Exit codes, fallbacks and stops are thorough. There are gaps in session-wake lifecycle coverage and plan discovery (findings 1, 3 and 6 below).

## Findings

**1. Important. SKILL.md:1116-1149 with 1213-1217 and 1219-1229: the session wake can be left armed after the job ends.**
- The wake is armed before the run checks that `gsd-execute-phase` resolves (SKILL.md:1161-1165).
- The Skill-resolution failure STOP (1213-1217) says "STOP, do not retry, and report" and never runs `done`.
- The close step only fires when "the phase completed, or a stop answered `abort`" (1219-1220).
- Other job ends are not covered either: GSD's native executor stopping at a checkpoint, a verification gap, or a non-cross-AI failure.
- Result: a persistent OS-timer wake can stay armed and later resume a session whose job is already over.
- **Fix:** resolve and confirm the GSD skill name before the arm block. Make the close step run on every end of this skill's job except the exit-75 `retry_after_s=` branch, and name the resolution-failure STOP explicitly.

**2. Minor. SKILL.md:1161-1165 and 1215-1217: the lookup for GSD's skill misses some per-project installs.** It checks `<project>/.claude/commands/gsd-execute-phase.md` (this repo's real location, verified), then `$HOME/.claude/skills/...`. It skips project-local `.claude/skills/gsd-execute-phase/SKILL.md` and the project install dirs of non-Claude hosts. Line 813-815 partly covers other hosts. **Fix:** add the project skills path, and say that a global path is only a last fallback.

**3. Minor. SKILL.md:989, 994-998 vs 1127: "Every plan file covering this phase" is never defined.** The wake block counts `*-PLAN.md` next to `$PHASE_PROMPT_FILE`, but the opt-in check gives no command. "If any plan lacks it" also blocks a phase whose already-completed plans lack `cross_ai: true`, even though GSD only delegates incomplete, ready plans. **Fix:** give one discovery command, and limit the check to plans with no SUMMARY.

**4. Minor. cross-ai-hook-setup.md:1299-1300: exit 2 is described too narrowly.** It says "gsd-tools could not be resolved", but `write-workflow-keys` and `clear-workflow-keys` also exit 2 on a malformed config and on a bad `--set`/`--min` spec (`ai_kit_spec_gsd/cli.py:226-240, 254-257`). **Fix:** list those causes as well.

**5. Minor. SKILL.md:980-983: the `native_tier` branches are keyed on a value Step 1 never prints.** They use `written=False/True`, but Step 1's extraction (888-890) does not print `written`, so the agent has to infer it from `provenance`. **Fix:** key the branches on `RESULT_PROVENANCE`, or extract `written`.

**6. Minor. SKILL.md:1186-1188: the exit-75 re-arm passes no `--reset-at`.** No time is tied to `retry_after_s`, so the OS-timer wake's timing has no relation to the retry delay, and its resume prompt is not the quota-wake text. **Fix:** pass `--reset-at` (now + `retry_after_s`), or say that the CronCreate job is the only retry trigger.

**7. Minor. SKILL.md:1007-1011, 1024-1026, 1028-1036; dispatch-notes.md:1321-1362: token waste.** The quoting rationale is repeated, the history section is a long narrative, and the Exec confinement and Node paragraphs sit in the body. **Fix:** keep one sentence plus a link in SKILL.md, and move the per-runtime confinement notes to a reference.

**8. Minor. SKILL.md:1051-1052 and cross-ai-hook-setup.md:1303-1305: a lowered user timeout is lost on cleanup.** A user `cross_ai_timeout` below 1800 that gets raised is deleted on cleanup, not restored, so GSD falls back to its default of 300s. The text discloses this and points to the backup, but does not say the user's lower value is gone after cleanup. **Fix:** say that explicitly, or restore the value from the backup.

## Top 3 Improvements
1. Close the session wake on every end of the job except the exit-75 branch, and confirm the GSD skill resolves before arming (finding 1).
2. Define plan discovery with one command, and limit the opt-in check to plans that still need to run (finding 3).
3. Cut the body toward 300 lines by moving the confinement, Node and history prose to references and keeping a single statement of the quoting rationale (finding 7).

Not checked: I did not run any shell block, so their runtime behaviour is unverified, and the Node 24 floor is unverified. I also did not look at how a session-wake refresh merges `--ref` values.
