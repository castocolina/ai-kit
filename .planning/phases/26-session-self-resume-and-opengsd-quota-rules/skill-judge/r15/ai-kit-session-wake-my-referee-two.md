Judge: my-referee-two
Reviewed-sha256: ff755e6e941bbca160be84bde69dafff453deefcd912422586aa38db87fd4ff2
Lane: AIKIT-XAI status=ok cli=pi model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=65s out=9486 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 108
Critical: 0
Important: 0

# Skill Evaluation Report: ai-kit-session-wake

## Summary
- **Total Score**: 108/120 (90%)
- **Grade**: A
- **Pattern**: Tool (precise CLI operations, low freedom, decision tables)
- **Knowledge Ratio**: E:A:R ≈ 85:12:3
- **Verdict**: A production-grade operational skill: host-specific session rules, exit-code routing, and load triggers match the implementation, and the residual risks it cannot encode are stated instead of implied.

Line numbers below are those of `skills/ai-kit-session-wake/SKILL.md` and the reference files as packaged. Claims checked against `ai-kit-session-wake.py`, `ai_kit_session_wake/{cli,arm,hosts,fire,liveness,state,reset_parse,units}.py`, `tools/setup.py`, and the executor wake blocks.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 19 | 20 | Host table, cap, companion-vs-timer, reset inference are all repo-specific |
| D2: Mindset vs Mechanics | 14 | 15 | Ownership thinking plus procedures the model cannot invent |
| D3: Anti-Pattern Quality | 14 | 15 | NEVER list is specific, reasoned, and honest about the subagent hole |
| D4: Specification Compliance | 14 | 15 | Valid frontmatter; WHAT/WHEN/keywords and an explicit negative trigger |
| D5: Progressive Disclosure | 15 | 15 | Every reference has a mandatory trigger and a Do-NOT-load clause |
| D6: Freedom Calibration | 14 | 15 | Exact commands and exit actions; judgment left where the code cannot decide |
| D7: Pattern Recognition | 9 | 10 | Clean Tool pattern; slightly denser than the ideal body |
| D8: Practical Usability | 14 | 15 | Exit table, relay list, and fallbacks cover the real failure modes |

## Critical Issues

None. The load-bearing claims hold in the code:

- Sibling `ai-kit-spec-review` missing exits 2 and names it (`ai-kit-session-wake.py:21-28`).
- `arm` refuses when `AI_KIT_CROSS_AI_CHILD` is anything other than `""` or `"0"`, and only when a `cross-ai.mjs` ancestor does not itself contain that marker (`arm.py:169-180`, `liveness.py:143-162`).
- Claude reads `CLAUDE_CODE_SESSION_ID` / `CLAUDE_PID`; pi and opencode have `session_env=None`; codex reads `CODEX_THREAD_ID` and is `verified=False` (`hosts.py:41-81`). Resume env scrubs `CODEX_THREAD_ID` (`hosts.py:85-92`, `child_env` at `hosts.py:124-129`).
- Exit 0 / 2 / 3, `not armed; nothing refreshed`, `reset refused: …; the hourly wake stands`, companion lines, linger wording (`arm.py:185-212, 520-560`).
- Cap 24, hourly calendar, count-before-liveness, early fires not counted, 14400 s resume timeout, `gave up` notice (`state.py:22`, `units.py:75`, `fire.py:37, 275-296, 315-328, 157-165`).
- `done` / `disarm` messages and in-fire marker-only behavior (`fire.py:207-275`).
- State dir `${XDG_STATE_HOME:-$HOME/.local/state}/ai-kit/session-wake` (`state.py:57-60`).
- StopFailure hook is opt-in, `arm --only-if-armed`, payload unverified (`tools/setup.py:1764-1821`, `tools/hooks/claude_session_wake.py:2-5`).
- Resume prompt forbids cycle-0 restart and harness/provider/model switches (`fire.py:29-36`).

## Top 3 Improvements

1. **`references/arm-exit-codes.md:10-13`** — the "nothing after the failure, on a first arm" row cannot match real stderr. `_finish_arm` always appends `; previous wake restored` on a failed refresh and, on a failed first arm, either the bare failure or `; rollback failed: …` (`arm.py:684-689`). An agent matching the table literally will drop a first-arm `systemctl … failed` into "anything else" and continue, which happens to be the right action, but the row as written is unreachable. Fix: say a first-arm failure is the bare `systemctl … failed` line with no `; previous wake restored` and no `; rollback failed`.
2. **`SKILL.md:86-88`** — "the printed in-session fallback dies with the process" is true only when exit 3 is the no-systemd path that prints the fallback (`arm.py:548-557`). The cursor path prints only `no surviving primitive for cursor` and returns 3 (`arm.py:185-187`, `cli.py:130-132`) with no fallback line. Fix: "when it also prints `fall back to the in-session primitive`".
3. **`SKILL.md:32-39`** — candidate 1 is a placeholder the agent must rewrite before the loop is valid. The executor skills resolve the shim from their own directory (`skills/ai-kit-spec-execute-superpowers/SKILL.md:149`), so a hand arm has no prior path. Fix: one sentence that the absolute path is the directory of the SKILL.md just loaded, substituted before the call.

## Detailed Analysis

### D1 (19/20)
Almost every paragraph is knowledge this repository invented: one wake per session id, executor ownership versus a manual arm that is never closed (`SKILL.md:44-46`), the 24-count hard stop including live-host log-only fires (`SKILL.md:94-99`), and the split between a dead host (timer resumes) and a live stall (companion only, and only when reset-timed) (`SKILL.md:101-106`). Redundancy is limited to the short definition of a systemd user timer, which an agent needs in order to know what it is arming. No "what is a rate limit" tutorial.

### D2 (14/15)
The thinking pattern is who owns the wake and what must not be guessed (session id, pid, "most recent", harness route). The procedures are non-obvious: pass nothing on claude, pass `--session-id` on pi/opencode, let codex fall through to an unverified env var (`SKILL.md:50-57`); relay lines at the certainty printed; treat exit 3 as not a wake. Generic file operations are absent.

### D3 (14/15)
The NEVER list (`SKILL.md:14-31`) names the failure each rule prevents, and it is honest that subagent `done` is enforced by text alone and disarms early without causing a wrong resume (`SKILL.md:17-20`). That matches the code: the cross-AI check is on `arm` only (`arm.py:169-180`); `done` and `disarm` have no subagent detection (`fire.py:207-231`). Companion.md repeats the one-shot rule with the spike-004 reason. Nothing vague ("be careful").

### D4 (14/15)
`name` is lowercase, hyphenated, and under 64 characters. The description states WHAT (arm, check, disarm a per-session systemd user timer), WHEN (usage/rate limit, AGENTS.md rule, host reset time, inspect or remove), keywords (`systemd`, `session id`, `ai-kit-spec-execute-*`), and a negative trigger (not ai-kit-cross-ai's hard tier). One point off because "checks" is vague next to the concrete verbs `status` and `matrix`, which would help triggering.

### D5 (15/15)
Body is 139 lines. Six references, each with a condition embedded in the step that needs it and an explicit Do-NOT-load: exit 2 only (`SKILL.md:82-85`), arm options only for the named flags (`SKILL.md:62-64`), companion only on the create line (`SKILL.md:108-112`), reset-time only when a reset is reported (`SKILL.md:114-118`), wake-cap only to explain a count (`SKILL.md:99`), unverified only before claiming those items work (`SKILL.md:145-147`).

### D6 (14/15)
Fragile systemd and session-id operations are low freedom: exact bash, exact subcommands, one action per exit-2 row. Judgment is left where it belongs (whether the owner gave the session id; whether a scheduler job already exists). The residual freedom in companion creation when the host cannot list jobs is bounded by `armed` versus `refreshed` (`references/companion.md:14-16`).

### D7 (9/10)
This is the Tool pattern: decision tables, exact commands, low freedom, references for the long branches. Minor deviation is density — the body carries both the relay checklist and the ownership narrative — not enough to break the pattern.

### D8 (14/15)
An agent can act immediately: resolve shim, pick a host row, arm, map the exit code, load one reference. Error handling covers shim missing, exit 2, exit 3, reset refused, linger off, and the 24-hour give-up. The companion prompt (`references/companion.md:23-28`) matches the resume prompt's cross-AI rule. The two wording mismatches in the Top 3 are usability nits, not wrong actions.

## Minor findings (not scored as Important)

1. **`SKILL.md:125-126`** — "A first `arm` clears a stale done marker" is true only when no state file exists (`arm.py:561-564`). A refresh does not unlink `.done`. Harmless in practice: `done` writes no marker when nothing is armed (`fire.py:259-267`), so a stale marker and a live state do not coexist. Fix: "a first `arm`, when no state file exists".
2. **`SKILL.md:16`** — "Only the orchestrating session arms its wake" overclaims. Code refuses `arm` for a cross-AI child; `done` and `disarm` are text-only, which the next bullet admits. Fix: move "only the orchestrating session" to the `done`/`disarm` bullet.
3. **`references/arm-exit-codes.md:16`** — "files deleted, but the timer may still be enabled" describes the intended rollback, but `_rollback_first_arm` still unlinks unit files and the wants symlink even when `disable --now` fails (`arm.py:573-596`). The prescribed `disarm` is still the right follow-up. Fix: "rollback also failed; units may be gone while systemd still has the timer enabled or the daemon state stale".
4. **`references/wake-cap.md:16`** — "session is no longer found" is specifically `session_exists` status `missing`; status `unknown` logs and does not give up (`fire.py:409-414`). Fix: "when the session probe reports missing".
5. **`SKILL.md:129`** — "both only write the marker" is accurate for the effect, but `disarm` inside a fire prints a different line than `done` (`fire.py:216-219` versus `fire.py:242-243`). No action change.
