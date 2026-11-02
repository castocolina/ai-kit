Judge: my-referee-two
Reviewed-sha256: 683e3a0c9be177ab0ff81ec767451f1e17a1d6cb7e81730e143ef8ee71fd8e58
Lane: AIKIT-XAI status=ok cli=pi model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=99s out=6049 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
The package is a process skill with real domain knowledge, but several of its load-bearing recipes contradict the code and sibling skills they name. Those are the findings that decide the score.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 17 | 20 | Almost entirely repo-specific exclusion/resume/escalation rules an agent would not invent. Some rationale is duplicated into design-notes. |
| D2: Mindset + Procedures | 13 | 15 | Strong "ask permanent vs same-wave" framing plus exact bash. Native dispatch and prompt composition stay prose, not scripts. |
| D3: Anti-Pattern Quality | 14 | 15 | The NEVER list is specific and each item has a non-obvious failure mode. |
| D4: Specification Compliance | 14 | 15 | Frontmatter valid; description has WHAT, WHEN, and a negative trigger. Name is 32 chars. |
| D5: Progressive Disclosure | 12 | 15 | SKILL.md is 384 lines with mandatory load points, but no "Do NOT Load" and one trigger is buried in a sentence. |
| D6: Freedom Calibration | 12 | 15 | Low freedom is right for state writes; a few exact bash blocks are themselves wrong. |
| D7: Pattern Recognition | 8 | 10 | Clear Process pattern with checkpoints; heavier and more cross-referential than the ~200-line ideal. |
| D8: Practical Usability | 8 | 15 | Decision trees exist, but several executable steps mis-handle real CLI output and would stop or skip the wake. |

## Findings

1. **Important** — `references/dispatch-external-cli.md:116-124` and `:148-156`. `classify-dispatch-failure` writes a bare word (`cli.py:357-360`), and `implementer-status` does the same (`cli.py:363-366`). Both bash blocks assign that word with `$(...)` and then `printf` it, so the command substitution strips the trailing newline and the tool prints nothing. The agent sees an empty `CLASSIFICATION`/`STATUS` and cannot take the `"ok"` / `"quota"` / `"real_error"` branch the rest of the file is built on. Print with a format that keeps a newline, e.g. `printf '%s\n' "$CLASSIFICATION"`.

2. **Important** — `SKILL.md:112-118` and `references/dispatch-external-cli.md:143`. The arm block only sets `WAKE_OWNED=1` when stdout contains a line matching `^armed `. The implementation prints `armed <host>-<id>` on a first arm and `refreshed <host>-<id>` on every later arm of a live session (`arm.py:480`). The skill treats any `refreshed` as "a wake that existed before this run" and forces `WAKE_OWNED=0`. Re-arming the same session — the normal case if the owner already armed, or if this plan is re-entered — therefore never records `WAKE_HOST`/`WAKE_ID`. The Schedule-or-stop re-arm (`if [ "$WAKE_OWNED" = 1 ]`) and "Close the session wake" then call nothing, so the quota companion and the `done` marker are skipped for a wake this run is actually using. Own the wake when this run's arm exits 0 with either `armed` or `refreshed`, and parse the host/id off that line; reserve `WAKE_OWNED=0` for exit 2/3 and a missing shim.

3. **Important** — `references/quota-wake.md:11-31`. The prompt says it substitutes fourteen placeholders, then step 2 tells the woken agent to bind `PLAN_FILE` and `TASK_N` from the state file. Neither name appears in the fourteen, and step 1 does not bind `RUN_DIR` or `SCALARS` either. The task-paths block (`SKILL.md:87-101`) refuses to run unless `PLAN_FILE` and `TASK_N` are already filled, and the scalar loader needs `SCALARS` before any other call. A woken run following this prompt literally stops at the placeholder guard, or pastes `<PLAN_FILE>` into the command. Add `PLAN_FILE`, `TASK_N`, `RUN_DIR` and `SCALARS` to the bound list (18 placeholders), and say the state file is only a check, not the source of those two.

4. **Important** — `references/state-management.md:254-279`. The replacement recipe writes `ESCALATION_EXCLUDE_JSON` to every ladder key except the owner's, then says to run escalation.md's re-resolve block unchanged. That block always passes `--escalation-excluded-keys-json` (`escalation.md:96-110`). Rounds 1–3 and any resume below round 4 are supposed to keep the injection and never apply the capability floor (`SKILL.md:296-301`, `escalation.md:7-16`). After an owner names a pair on round 2, the floor excludes every other candidate and, if the named key is below the stuck key, the re-resolution returns `quota_exhausted`/`no_candidate` and the recipe stops without dispatching the pair the owner just named. Split the recipe: below round 4, call `resolve-injection` without the escalation argument; pass the floor file only when `$FIX_ROUND >= 4`.

5. **Minor** — `SKILL.md:347-348`. "The runner fails closed as `dispatch_unavailable` only when `node` is absent" overstates the sibling note. The gsd skill says that without Node the launch never reaches the runner's `dispatch_unavailable` path (`ai-kit-spec-execute-gsd/references/cross-ai-hook-setup.md:92-94`). An agent that treats a missing `node` as that classified reason will wait for a stop shape that is not produced. Point at the gsd note and say a missing node fails before classification.

6. **Minor** — `references/dispatch-external-cli.md:130-146`. The `"quota"` branch lists Relay, then Read tokens, then Write state, then Schedule-or-stop, but the wait predicate (return code 75 plus whole-number `retry_after_s` and `cycle`) is only stated at Schedule-or-stop. Write state runs unconditionally, so a tokenless 69/75 or a `reason == "quota"` at any other code — all of which this file itself calls owner stops — still persists `injection_json`. Say which classes write the pinned file and which only relay and stop.

7. **Minor** — `SKILL.md:52-55` vs `references/escalation.md:69-74`. Escalation is "read only before computing the floor", while the anchor-empty case says do not re-run `resolve-injection` at all. An agent that loads escalation.md only after deciding to compute the floor misses the stop. Put the empty-anchor stop in SKILL.md Step 3, next to the round-4 trigger.

Score: 98
Critical: 0
Important: 4
