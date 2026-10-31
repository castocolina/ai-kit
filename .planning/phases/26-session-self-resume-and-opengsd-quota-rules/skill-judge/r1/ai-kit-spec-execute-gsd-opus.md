Judge: opus
Reviewed-sha256: 7a8c37b5cbcbe91d4d4326f05113ce1aa111481093e50b9afa9606b85192cf02
Lane: native subagent completed
Score: 97
Critical: 0
Important: 3

# Skill Evaluation Report: ai-kit-spec-execute-gsd

The package text matches the repository copy (`skills/ai-kit-spec-execute-gsd/SKILL.md`, 543 lines; `references/dispatch-notes.md`, 63 lines). Line numbers below are file line numbers. For SKILL.md, file line = prompt line − 770.

## Summary
- **Total Score**: 97/120 (81%), Grade B
- **Pattern**: Process/Tool hybrid (a phased workflow with low-freedom shell blocks)
- **Knowledge Ratio**: E:A:R ≈ 75:15:10
- **Verdict**: The skill carries dense, project-specific knowledge: hook quoting, ownership-aware cleanup, and retry/skip/abort discipline. Three things cost it: it overclaims how far the guidance reaches, the session-wake id breaks under its own fresh-shell model, and too much inline code sits in the body.

## Dimension Scores
- D1 Knowledge Delta: 16/20. Almost all of the content is expert, repo-specific knowledge Claude could not derive: the unquoted-hook allowlist, the timeout floor ownership, the exit-75 `retry_after_s` rule, and the trust model of the first `gsd-tools.cjs` found. Some of it is padding: the repeated explanations of "why cleanup runs" (lines 192-194 and 333-339), and the history kept in the body (lines 432-435).
- D2 Mindset + Procedures: 12/15. It has a "Mindset before writing anything here" block (lines 188-194) and domain sequences Claude would not know, such as checking the opt-in before `ensure-runner` and running the producer before anything is written.
- D3 Anti-Patterns: 13/15. The NEVER list (lines 8-30) is specific and gives reasons: why `skip` is never answered, why Step 1 is never re-run after a stop, why a custom entry never becomes a hook.
- D4 Specification: 14/15. The name is valid. The description covers WHAT, three numbered WHEN triggers, and keywords (`.planning/`, `cross_ai: true`, `model_profile_overrides`, `/gsd-execute-phase`). It is long and heavy on internals.
- D5 Progressive Disclosure: 10/15. At 543 lines it is over the 500-line ceiling. The single reference has good "read only if you need to know why" guidance at lines 233-236 and 433-435, which does the job of a Do-NOT-Load note. The weight comes from inline code that belongs in shim subcommands.
- D6 Freedom Calibration: 13/15. Fragile config writes get low freedom (exact blocks, exit-code tables). Judgment calls (trust-local, owner decisions) are left to the owner.
- D7 Pattern: 8/10. It is a clear phased process with checkpoints, deviating toward a Tool-pattern bulk of code.
- D8 Practical Usability: 11/15. Error handling is thorough: write_failed, revert_failed, malformed markers, a missing GSD skill. It has the gaps in findings 1-3.

Checks against the repository:
- These hold: the subcommands and flags (`skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py:400-454`), the exit codes (cli.py:160-184, 245, 264), and the `failed`/`revert_failed` fields (`gsd_config.py:64-73`).
- The reason codes hold (`adapter.py:240-313`), as do the `ensure-runner` exits 0/1/2 and `--guidance-file -` (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:218-241`).
- The `armed`/`refreshed <host>-<id>` output holds (`skills/ai-kit-session-wake/ai_kit_session_wake/arm.py:480`), as do the claude aliases (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:113`).
- The gsd-core search order holds (`skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:92-100`), and so do the ai-kit-cross-ai sections 4 and 6-8.

## Findings

1. **Important. SKILL.md:427-430.** The skill says the tooling guidance written into the phase file "reaches GSD's own execution regardless of which dispatch mode Step 2 chose". That is false for cross-AI mode. GSD builds the delegated prompt only from the plan's `<objective>`/`<tasks>` (`.claude/gsd-core/workflows/execute-phase.md:419`), and the skill's own `references/dispatch-notes.md:38-41` concedes this.
   - Writing into a tracked plan file also dirties the tree, and GSD warns about a dirty tree right before the cross-AI run (same line 419).
   - **Fix:** limit the claim to the native executor. State that cross-AI tooling guidance travels in `.planning/scripts/cross-ai-guidance.md`. Mention the dirty-tree side effect, or skip the append in `cross_ai_hook` mode.

2. **Important. SKILL.md:452.** `${WAKE_SESSION_ID:+--session-id "$WAKE_SESSION_ID"}` depends on a shell variable that persists. Step 0 (lines 82-85) says every Bash call starts a fresh shell and every `$VAR` is a literal re-substituted by hand. No step records `WAKE_SESSION_ID`.
   - On pi and opencode, which are primary hosts, the expansion is always empty. `arm` then refuses with exit 2 (`skills/ai-kit-session-wake/SKILL.md:49-52`), and every multi-plan run silently goes without a wake.
   - **Fix:** use a literal placeholder such as `--session-id "<this session's exact id, from the owner or the host's output>"` on pi and opencode, and omit it on claude. Add a printf capture step, as Step 0 does for the shim paths.

3. **Important. SKILL.md:101-119, 241-285, 368-417.** About 120 lines of fragile inline code must be transcribed with up to seven hand-substituted literals per block:
   - nine `python3 -c` JSON field extractions;
   - a 45-line hook-setup block;
   - a 35-line inline Python marker editor.

   One wrong substitution of `$RESULT_CROSS_AI_COMMAND` or `$RUN_ID` writes a wrong hook or breaks ownership tracking. This is also what pushes the file past 500 lines.
   - **Fix:** add shim subcommands. One prints the Step 1 fields as `KEY=value` lines. One runs hook setup (guidance → ensure-runner → write, or clear). One writes the marker-guarded guidance. The body then calls each one in a single line.

4. Minor. SKILL.md:174-179. The list of permanent reasons is a garbled parenthetical ("… `unsupported_model_id` — see Step 2, `no_usable_dispatch` — no candidate has …"). **Fix:** list the five reasons plainly and give each a short cause.

5. Minor. SKILL.md:147-151 vs 328-331. The Step 1 `quota_exhausted` case says to STOP with no mention of cleanup. Step 2 says every `fallback_notice` runs the mode-transition cleanup. **Fix:** say explicitly whether the quota stop runs the cleanup.

6. Minor. SKILL.md:105. `[ $? -eq 2 ] && exit 2` lets a Python crash that exits 1 with no JSON reach the parsers. **Fix:** treat a non-zero exit with empty stdout as a STOP.

7. Minor. SKILL.md:452-455. The arm block does not tell the agent to act on the `companion:` one-shot line, which ai-kit-session-wake requires (`skills/ai-kit-session-wake/SKILL.md:66-73`).

8. Minor. SKILL.md:55-58. If no candidate directory exists, `GSD_SHIM` becomes `/ai-kit-spec-gsd.py` and nothing stops the run. **Fix:** STOP when any of the three directories is unset.

9. Minor. SKILL.md:490-496 and 533-540. On an `abort` stop the wake is re-armed with the state file and then closed at once. **Fix:** re-arm only on the exit-75 `retry_after_s` branch.

I did not run the shim, `ensure-runner` or the session-wake commands; every check was done by reading code. I also did not check whether the codex `workspace-write` `.git` caveat is still open.
