# ai-kit-spec-execute-gsd — skill-judge report (native Opus subagent, clean context)

Round 5 (evidence round), skill digest `0a5d05b298c07ee8`, judged at commit e2bb140. Rubric: the skill-judge skill (120 points).

**Skill-judge report: `skills/ai-kit-spec-execute-gsd/`**

Files scored: `SKILL.md` (499 lines), `references/dispatch-notes.md` (66 lines) and the linked `skills/ai-kit-spec-review/references/subprocess-quota-policy.md`. It follows the Process pattern, written in a low-freedom, script-heavy style. Roughly 70% of the content is expert knowledge, 20% is reminders, and 10% is redundant or repeated.

I checked the Phase 25 claims against the code, and they hold:
- **Route flags:** `--route-<cli> router|unknown` comes from a catalog `fallback_quota` value the user confirmed (`runner_dispatch.py:182-226`, `gsd_cross_ai.py:28`). The runner's order is flag, then `routerBacked`, then `router-inferred` (`cross-ai.mjs:1604-1614`).
- **Exit 75 and 69:** an early re-entry is refused with exit 75 and `retry_after_s=<left>`. A lane past the cap is refused with exit 69 until its last attempt is more than 4 hours old. A used-up transient ladder exits 75 with no `retry_after_s=` (`cross-ai.mjs:813, 2409-2467`).
- **Exit codes reach GSD:** GSD's `run-with-timeout` passes the runner's exit code through unchanged (`gsd-tools.cjs:4895-4903`).
- **Timeout:** the 1800-second floor works with the runner's own deadline (`cross-ai.mjs:1727-1808`).
- **No switching:** the skill never switches harness, provider or model on its own. The NEVER list at `SKILL.md:23-33` forbids re-resolving, GSD's `skip` and rewriting the hook.

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 15 | 20 | Strong GSD and runner knowledge. Rationale is repeated (opt-in stated 3 times, custom-entry note stated twice). |
| D2 Mindset + Procedures | 12 | 15 | Has a "Mindset before writing" block and non-obvious ordering (check opt-in, then ensure-runner, then write). |
| D3 Anti-Patterns | 13 | 15 | Specific NEVER list with reasons. One bullet is garbled. |
| D4 Spec / Description | 13 | 15 | Valid, 836 characters, says what it does and when. Missing user-phrased triggers ("run GSD phase N on codex"). |
| D5 Progressive Disclosure | 11 | 15 | 499 lines, right at the limit. The policy link has a MANDATORY trigger and the notes have "read only if" triggers. No "do not load" guidance. Policy rules are copied inline. |
| D6 Freedom Calibration | 13 | 15 | Exact scripts suit fragile config writes. The main "stop, don't go native" gate is prose only. |
| D7 Pattern | 8 | 10 | Clear Process pattern, but heavy for it. |
| D8 Usability | 11 | 15 | Mismatches in the state-file and exit-code handling, listed below. |

**Findings**

1. **Important.** The block never prints `RESUME_STATE_PATH=`, but the skill tells the agent to report and reuse it. `SKILL.md:152-153` and `:488-489` both refer to that line. The block at `:161-171` only prints `{"written": true, "path": ...}` (`ai_kit_spec_gsd/cli.py:392`). Because every shell call starts fresh, the wake prompt's `<RESUME_STATE_PATH>` has no recorded source. **Fix:** add `printf 'RESUME_STATE_PATH=%s\n' "$RESUME_STATE_PATH"` to the block and exit non-zero if `write-resumable-state` fails.

2. **Important.** One state file carries two opposite resume instructions.
   - `SKILL.md:156-160` says the caller re-invokes this skill from the file's contents.
   - `:466-474` writes the same file, at the same `PROJECT_KEY`/`PHASE_ID` path, after a router stop. There, re-invoking the skill is forbidden, because it re-runs Step 1 and can rewrite the hook.
   - The JSON has no field that tells the two cases apart, and nothing in the repo reads it (no `gsd-resume` consumer).
   **Fix:** add `"resume_via": "skill"|"gsd-execute-phase"` (or a stage field) to the state JSON in both writes, and reword `:156` to scope its instruction to that value.

3. **Important.** The Step 2 block exits 0 even when nothing was written. If the runner is not ready or guidance is missing and the cleanup succeeds, the block prints `RESULT_MODE=fallback_notice` and exits 0 (`SKILL.md:256-286`). Yet `:295` says "Exit 0 of the block writes the hook". The stop-before-native-executor rule then rests on the agent re-reading `RESULT_MODE`. **Fix:** `exit 3` after a successful `clear_hook` on both failure branches, and document "exit 3 = nothing written, STOP".

4. **Minor.** The MANDATORY policy pointer uses `$REVIEW_SPEC_SKILL_DIR` (`SKILL.md:452-454`), but Step 0 prints and records only three values (`:76`, `:79`). **Fix:** add `REVIEW_SPEC_SKILL_DIR` to the Step 0 `printf`, or write the path as `$(dirname "$TOOLS_PY")/references/...`.

5. **Minor.** The policy says "A skill links here; it does not copy the rules" (`subprocess-quota-policy.md:3-5`). The skill copies the route resolution, cap refusal and bare-75 rules anyway (`SKILL.md:460-464`, `:489-493`). They are accurate today but will drift. **Fix:** keep only the GSD-specific parts (pending prompt, wake text, never re-run Step 1) and defer the rest to the policy.

6. **Minor.** The plan opt-in check is all-or-nothing (`SKILL.md:211-216`). A phase that mixes `cross_ai: true` plans with native plans can never run, although GSD supports that mix (`elaboration.md:63-68`). **Fix:** stop only when no plan opts in, and list the plans that don't so the owner can confirm they run natively.

7. **Minor.** The wake prompt (`SKILL.md:476-481`) doesn't point back to Step 3's rules on the result: relay the evidence lines, never `skip`, schedule the next one-shot. After context compaction those rules are lost. **Fix:** add the line "Then apply ai-kit-spec-execute-gsd Step 3's stop rules to the result."

8. **Minor.** A stop with no `AIKIT-XAI` line is not covered. Examples are GSD's `run-with-timeout` exit 124, 126 or 127, or the runner not launching. **Fix:** one sentence: "no AIKIT-XAI line: relay GSD's exit code and error log, STOP, owner decides."

9. **Minor.** Wording and repetition:
   - The NEVER bullet at `SKILL.md:29-31` reads as "never answer retry except … answer nothing". Reword it to "only the scheduled wake answers retry".
   - The custom-entry note (`:16-20`, repeated at `dispatch-notes.md:57-60`) and the codex confinement note (`:309-316`, repeated at `dispatch-notes.md:23-32`) appear twice. Keep each once.
   - The opt-in rationale appears three times (`:191-195`, `:211-216`, `:325-328`). Keep one.
   - The Step 3 lookup (`:443-444`) skips `<project>/.claude/skills/gsd-execute-phase/SKILL.md`.

What I skipped: I did not run the runner's `--self-test` or any shim command (read-only task), and I did not verify `cache_write_json` atomicity. Risk: findings 1-3 are on the resume and stop path, so a router-quota wake can go wrong even though the runner itself behaves correctly.

DIGEST 0a5d05b298c07ee8
CURRENT 96/120
CRITICAL 0 IMPORTANT 3
