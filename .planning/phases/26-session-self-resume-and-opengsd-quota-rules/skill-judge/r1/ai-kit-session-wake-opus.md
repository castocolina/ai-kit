Judge: opus
Reviewed-sha256: a43a86648745ab18e0923768b17e9200870d4419896a30a1a68ed97d6cb13631
Lane: native subagent completed
Score: 95
Critical: 0
Important: 3

# Skill Evaluation Report: ai-kit-session-wake

## Summary
- **Total Score**: 95/120 (79%)
- **Grade**: C (the top of the band)
- **Pattern**: Tool. The skill is a shim with subcommands, exit codes and low-freedom bash blocks.
- **Knowledge Ratio**: E:A:R is about 75:20:5
- **Verdict**: A compact, mostly accurate skill. Its NEVER list is strong. But it misstates what `done` does, it leaves certainty-labelled output lines out of the relay list, and it gives no guidance on what to do when `arm` fails.

I checked the package against the repository. `skills/ai-kit-session-wake/SKILL.md` (139 lines) is identical to the package text. I read `ai_kit_session_wake/cli.py`, `arm.py`, `hosts.py` and `fire.py`, plus `tools/setup.py:1764-1821`, `skills/ai-kit-spec-execute-gsd/SKILL.md:436-472` and `skills/ai-kit-cross-ai/SKILL.md`.

Claims that hold:
- The six subcommands are right (`cli.py:61-68`).
- Exit codes 0, 2 and 3 are right (`cli.py:22-24`, `arm.py:185-187`, `arm.py:548-557`).
- `arm` refuses when `AI_KIT_CROSS_AI_CHILD` is set or a `cross-ai.mjs` ancestor exists (`arm.py:169-180`).
- On claude the shim reads `CLAUDE_CODE_SESSION_ID` and `CLAUDE_PID` (`hosts.py:42-45`).
- pi refuses without `--session-id` (`arm.py:192-193`).
- `--reset-text` and `--reset-at` are mutually exclusive, and a refused reset leaves the hourly wake in place (`cli.py:85-93`, `arm.py:339-340`, `arm.py:560`).
- The companion line appears only for a reset-inferred wake (`arm.py:519-529`).
- The StopFailure hook is opt-in for claude, with matcher `rate_limit` (`tools/setup.py:1820-1821`).
- The shim resolution order matches the executor skills (`ai-kit-spec-execute-gsd/SKILL.md:55-56`).

## Dimension Scores
- **D1 Knowledge Delta: 15/20.** Almost everything is shim-specific knowledge Claude cannot have: the exit codes, the per-host session-id sources, the companion rule and the spike 004 lesson. Some internal jargon (D-30, spike 004, Phase 27) costs tokens without helping a portable reader.
- **D2 Mindset + Procedures: 11/15.** The domain procedures are good (resolve the shim, arm, done). There is little decision framing, for example when to arm by hand versus letting the executor skills arm on their own.
- **D3 Anti-Patterns: 12/15.** The NEVER list is specific, and the subagent `done` rule states its own residual risk. "Never switch harness, provider or model" and "never hand-edit units" give no reason.
- **D4 Specification: 14/15.** The frontmatter is valid. The description has WHAT, WHEN, keywords and a "Not for" boundary. One more trigger keyword ("usage limit", "resume after rate limit") would help.
- **D5 Progressive Disclosure: 13/15.** The file is self-contained at 139 lines with no references, and the sections are compact.
- **D6 Freedom Calibration: 12/15.** The shim block and the commands are suitably low-freedom. The failure paths are left open where this fragile operation needs low freedom.
- **D7 Pattern: 8/10.** A clear Tool pattern. The "Unverified" and "Relation" sections are fine but read slightly like notes.
- **D8 Practical Usability: 10/15.** The common path is clear. The `done` lifecycle is misstated, the relay list is incomplete, and there is no fallback guidance per exit code.

## Findings

1. **Important. SKILL.md:95-96, also :128. The skill misstates what `done` does.**
   - The skill says `done` makes "the next wake remove itself", and that only `disarm` removes a wake "at once".
   - The code says otherwise (`fire.py:231-252`). Outside a fire child, `done` takes the session lock without blocking. If no resume holds the lock, it removes every owned file right away. Only when a resume is running does it defer to that resume.
   - The real difference is in `disarm` (`fire.py:207-228`): it blocks on the lock and waits for a running resume to finish.
   - So the "Unverified" item "That the timer removes itself after `done`" (`:128`) describes a path that is not the common one.
   - Fix: say that `done` removes the wake now, or after the running resume exits if one holds the lock, and never blocks. Say that `disarm` waits for a running resume and then removes everything. Reword `:128` to match.

2. **Important. SKILL.md:61-63. The relay list leaves out the lines that carry certainty labels.**
   - `arm` also prints:
     - `resume argv: ... (verified|unverified: <evidence>)` (`arm.py:487`)
     - `host pid: ... (unverified: nearest ancestor ...)` (`arm.py:488-491`)
     - `reset: <time> (inferred); next wake ...` (`arm.py:511-516`)
     - `reset refused: <reason>; the hourly wake stands` (`arm.py:560`)
   - A refused reset still exits 0. An agent that relays only the listed lines can tell the user the wake lands after the reset when only the hourly wake exists.
   - It also drops the verified and unverified labels that the project's certainty rule requires (codex resume is `verified=False`, `hosts.py:77-78`).
   - Fix: add these four lines to the relay list. Add that exit 0 with `reset refused:` means no reset-timed wake.

3. **Important. SKILL.md:63-67. There is no guidance on what to do for each exit code, and `--pid` is not documented.**
   - pi, opencode and codex have no `pid_env` (`hosts.py:49-79`), so `arm` falls back to an ancestor scan it labels as unverified (`arm.py:246-249`).
   - When that scan finds nothing, `arm` refuses with "cannot resolve the {host} host process; pass --pid" (`arm.py:294`). The skill never mentions `--pid`, and it gives no rule against guessing a pid.
   - On exit 3, `arm` prints a "fall back to the in-session primitive ..." line (`arm.py:551-556`). The skill does not say whether to act on it.
   - The skill also never states the rule the executor follows: "Never fail the run on the wake" (`ai-kit-spec-execute-gsd/SKILL.md:441`).
   - Fix: add one line per exit code:
     - 2: relay the cause and continue without a wake; pass `--pid` only with the host's verified pid.
     - 3: relay it and continue; the in-session fallback dies with the process.
     - Neither code blocks the run.

## Minor findings (not counted)
4. **SKILL.md:53.** codex does have a default session variable, `CODEX_THREAD_ID` (`hosts.py:73`), which `arm` reads when `--session-id` is absent. Say so, and say it is unverified.
5. **SKILL.md:115.** `status` needs both `--host` and `--session-id`, or neither (`cli.py:172-174`). The brackets suggest either flag works alone.
6. **SKILL.md:74, :81, :119.** Internal planning references (spike 004, D-30, "Phase 27") mean nothing to a reader outside the project. Replace each with a short reason.
7. **Description, SKILL.md:3.** It says "Use before a multi-plan GSD phase", but `ai-kit-spec-execute-gsd` already arms on its own. If an agent arms by hand first, the executor sees `refreshed`, treats the wake as not its own (`WAKE_OWNED=0`) and never closes it. Say that a manual arm makes the caller own the `done`.
8. `--permission-mode` and `--only-if-armed` are not documented (`cli.py:74-81`). That is acceptable, but the claude permission copy from the host command line (`arm.py:498-501`) is worth one line.

## Top 3 Improvements
1. Correct the `done`/`disarm` lifecycle text (finding 1).
2. Complete the relay list, including the case where a refused reset still exits 0 (finding 2).
3. Add an outcome for each exit code, document `--pid`, and add "never fail the run on the wake" (finding 3).

I did not run the shim or the tests. Every behavioural check comes from reading the code, so the systemd and resume paths are still not checked live.
