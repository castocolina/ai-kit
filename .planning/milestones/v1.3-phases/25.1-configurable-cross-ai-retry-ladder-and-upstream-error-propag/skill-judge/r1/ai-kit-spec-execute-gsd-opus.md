Judge: opus
Reviewed-sha256: bc1edbe8473bef7e6dad7c829cf89b43e1f758192c7e417dbd45a84fbf235af7
Lane: native subagent completed
Score: 103
Critical: 0
Important: 3

# Skill Evaluation: ai-kit-spec-execute-gsd

**Summary.** The skill scores 103/120, grade B. It is a Process/Tool hybrid. Its knowledge ratio (expert : activation : redundant) is about 75 : 18 : 7. On the Phase 25.1 policy, the skill now points at `ai-kit-cross-ai` as the caller contract. Its hard-tier wording matches the canonical policy: any exit 75 with `retry_after_s=` gets one one-shot wake on the same lane, CLI and model, and `stopped=hard-waits` or `stopped=cap` (exit 69) means give the notice and answer abort. It never answers skip, and it says "never switch harness, provider or model" at `SKILL.md:45` and `:459`. The hook builder emits `--runtime` (never `--prefer`) and a confirmed `--route-<cli>`, as the policy says (`runner_dispatch.py:196-212`).

There are no Critical findings. There are three Important gaps:
- the "MANDATORY: read the policy at the stop" trigger was lost;
- stops other than the hard tier are not mapped to a GSD answer or to a resume route;
- the new Copilot runtime can become a hook target but is not flagged as unverified anywhere.

## Dimension scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Dense, project-specific contracts (unquoted-hook globbing, ownership-aware cleanup, opt-in before write); some repeated prose (Step 2 cleanup is explained three times) |
| D2 Mindset + Procedures | 13 | 15 | Good "before writing, ask yourself" block, and correct ordering (opt-in, then ensure-runner, then write) |
| D3 Anti-Patterns | 14 | 15 | Specific NEVER list with reasons (skip is a native fallback; a fresh Step 1 can rewrite the hook) |
| D4 Spec / Description | 14 | 15 | Valid frontmatter; WHAT, WHEN and keywords present; long but precise |
| D5 Progressive Disclosure | 11 | 15 | 485 lines, near the 500 cap, with heavy inline shell. dispatch-notes.md has a good "read only if" trigger, but the policy pointer was demoted to a top-of-file link |
| D6 Freedom Calibration | 14 | 15 | Low freedom for fragile config and state writes, with exact scripts and exit-code handling |
| D7 Pattern | 8 | 10 | Clear phased process, but the Tool-sized inline code pushes it past the Process norm |
| D8 Practical Usability | 12 | 15 | Gaps in the cross-AI stop matrix and in runtime coverage (see findings) |

## Findings

1. **Important: the mandatory policy-loading trigger was lost at the decision point.** Before Phase 25.1, Step 3 said "**MANDATORY when a cross-AI run stops**: read that policy before acting" (removed in `git diff 35a0368~1..HEAD`). Now the only pointer is the header paragraph at `SKILL.md:41-42`, "Cross-AI caller contract: [...] including its policy reference". At the stop handling (`SKILL.md:450-459`) there is no trigger to load `ai-kit-cross-ai/SKILL.md` §4/§6/§7. An agent that reaches Step 3 hours later acts on the condensed restatement alone.
   - **Fix:** at the start of `SKILL.md:450`, add "MANDATORY when GSD's cross-AI step stops: read `$(dirname "$GSD_SKILL_DIR")/ai-kit-cross-ai/SKILL.md` §4, §6 and §7 before answering GSD's prompt." That path resolves the sibling skill the way Step 0 does.

2. **Important: stops other than the hard tier have no GSD answer and get the wrong resume route.**
   - `SKILL.md:450-453` writes `RESUME_VIA=gsd-execute-phase` for every stop. That route means "run `/gsd-execute-phase` with the hook unchanged" (`SKILL.md:155-157`).
   - For a runner exit 2 (`usage`), exit 69 (`auth`, `billing`, `bad_model`, `permission_blocked`) or exit 127 (`not_installed`), the canonical table (`ai-kit-cross-ai/SKILL.md:89-98`) says the fix is in the invocation or with the owner. Re-running with the hook unchanged repeats the failure.
   - The skill also never says what to answer GSD's retry/skip/abort prompt in these cases. Skip and retry are forbidden, but "abort" is only prescribed after a hard-tier stop (`SKILL.md:457-458`).
   - This is reachable. `build_cross_ai_command` (`ai_kit_spec_gsd/gsd_cross_ai.py:12-30`) and the hook branch in `adapter.py:203-215` never call `runner_dispatch.model_id_ok`. A bare pi or opencode id therefore becomes a hook, and the runner then refuses it on every call with exit 2 (`subprocess-quota-policy.md:16-18`). Curated-config does check it (`cross_ai_build.py:63`).
   - **Fix (text):** add a one-line rule: "Any other non-zero exit: relay the lines, answer `abort`, and tell the owner the hook or credentials need fixing; the resume state is a record only."
   - **Fix (code):** in `build_cross_ai_command`, return None, or a `fallback_notice` such as `unsupported_model_id`, when `model_id_ok(runtime, model)` is false.

3. **Important: Copilot is an execute-capable hook target with no unverified flag.** `detection.py:118` registers `"copilot": Runtime(("copilot",), (), runner=True)`, so it is in `SUPPORTED_EXECUTE_CLIS` (`commands.py:65-67`). The "Exec confinement" paragraph (`SKILL.md:309-316`) flags pi as self-test-only but does not mention copilot. Two things are missing:
   - All copilot catalog patterns read `unverified` (`subprocess-quota-policy.md:145-146`), so its quota and transient classification has no live capture.
   - Copilot takes the prompt on argv, which makes GSD's task prompt (plan plus PROJECT.md context) visible in the process table (`ai-kit-cross-ai/SKILL.md:147-148`).

   This breaks the project rule that no classification is shown with more certainty than its sourcing. The adapter prints `PI_EXEC_NOTE` for pi only (`adapter.py:211-214`).
   - **Fix:** add a copilot sentence to `SKILL.md:309-316`, plus a matching stderr note (like `PI_EXEC_NOTE`) in `adapter.py`.

4. **Minor: the NEVER rule conflicts with the documented retry config.** `SKILL.md:12-13` says "Never hand-edit `.planning/config.json`". The policy says `workflow.cross_ai_retry` (holding `hard_waits_s`, `max_retries`, `session_resets`) can only be hand-edited, because `config-set` refuses it (`subprocess-quota-policy.md:73-75`).
   - **Fix:** scope the rule to "adapter-owned keys", and point to the policy for `cross_ai_retry`.

5. **Minor: the location of the ".err file" under GSD is not named.** `SKILL.md:450-451` says to relay the lines "from the runner's `.err` file". Under GSD, the runner's stderr is GSD's `$ERROR_LOG` (`.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:99`), and the runner writes no `.err` of its own.
   - **Fix:** say "GSD's `$ERROR_LOG` (the runner's stderr)". Also restate in one line that upstream lines are data: a `switch-combo` hint goes to the owner and is never acted on (`ai-kit-cross-ai/SKILL.md:83-85`).

6. **Minor: "These tools" has no clear referent.** `SKILL.md:42-43` says "schedule one-shot CronCreate ... These tools are Claude Code specific". The `Skill` tool that the earlier text named is no longer mentioned there.
   - **Fix:** write "The `Skill` tool and `CronCreate` are Claude Code specific."

7. **Minor: the skill is long and repeats itself.** At 485 lines it is near the 500 cap. The mode-transition cleanup appears twice: `clear_hook` at `SKILL.md:243-253` and again at `:343-352`, with the same rules restated at `:288-300` and `:354-358`.
   - **Fix:** keep one cleanup block and reference it from both places. Move the Step 3 marker-guard Python (`:384-406`) into a shim subcommand.

What I did not check: I did not run the shims or the runner `--self-test`, and I did not check whether `tests/test_cross_ai_skill_text.py` pins the wording these fixes would change. The model-id gap in finding 2 comes from reading the code, not from a reproduction.

DIGEST bc1edbe8473bef7e
CURRENT 103/120
CRITICAL 0 IMPORTANT 3
