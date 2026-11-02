Judge: my-referee-two
Reviewed-sha256: a43a86648745ab18e0923768b17e9200870d4419896a30a1a68ed97d6cb13631
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=317s out=277899 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 110
Critical: 0
Important: 0

# Skill Evaluation Report: ai-kit-session-wake

## Summary
- **Total Score**: 110/120 (92%) — Grade A
- **Pattern**: Tool (right-sized to 139 lines instead of ~300)
- **Knowledge Ratio**: E:A:R ≈ 85:15:0
- **Verdict**: An unusually accurate, honesty-labelled operation manual for a fragile systemd mechanism; every factual claim I could check against the repository's source verified, and the residual defects are minor and self-healing via the tool's own output.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 19 | 20 | Nearly every line is repo-specific: exit codes, refusal conditions, per-host session-id provenance, relay-line contract, evidence labels. Only activation-level content is the fresh-shell reminder (SKILL.md:42). |
| D2: Mindset + Procedures | 13 | 15 | Non-obvious ordering (resolve shim once → find session id → arm → relay → companion → done); per-host id-sourcing decision list (SKILL.md:46-54). Less "ask yourself" framing, acceptable for a Tool pattern. |
| D3: Anti-Pattern Quality | 14 | 15 | Six specific NEVERs with reasons, including a candid enforcement-gap disclosure (SKILL.md:17-20: subagent rule is "enforced by this text alone… stated residual risk"). "Never guess a session id… do not take the newest session file" (SKILL.md:22) is genuine landmine knowledge. |
| D4: Specification Compliance | 15 | 15 | Description has WHAT + four explicit WHEN triggers + keywords (systemd user-timer, usage-limit reset, GSD phase, superpowers plan, AGENTS.md) + negative scope ("Not for cross-AI subprocess limits"). |
| D5: Progressive Disclosure | 15 | 15 | 139 lines, self-contained; the payload is an executable script with a mandatory resolution step (SKILL.md:26-42); nothing else exists to over-load. Honesty labels kept inline, no dump. |
| D6: Freedom Calibration | 14 | 15 | Low freedom exactly where fragile (exact commands, exact relay lines, "never hand-edit", one-shot-only companion); judgment freedom only where real (id sourcing, "short resume prompt"). Matches the consequence: a wrong arm writes systemd units and resumes a session. |
| D7: Pattern Recognition | 9 | 10 | Clean Tool pattern; deliberately mirrors the sibling executor skills' Step-0 resolution (verified: `ai-kit-spec-execute-gsd/SKILL.md:55-57`). |
| D8: Practical Usability | 12 | 15 | Per-host decision list, exit-code table, exact relay lines, reset-refusal fallback ("the hourly wake stands"), STOP-on-missing-shim. Gaps are the minor findings below. |

## Claim Verification (all passed)

- Cross-AI child refusal via `AI_KIT_CROSS_AI_CHILD` env + `cross-ai.mjs` ancestor: `ai_kit_session_wake/arm.py:169-180` (SKILL.md:14-16).
- Exit codes 0/2/3 incl. cursor / no-systemd → 3: `cli.py:22-24`, `arm.py:118`, `arm.py:185-187`, `arm.py:548-557` (SKILL.md:65-67).
- pi/opencode have no session env var; claude reads `CLAUDE_CODE_SESSION_ID`/`CLAUDE_PID`; codex unverified: `hosts.py:41-80` (SKILL.md:48-54).
- Every relayed output line exists verbatim: `armed/refreshed`, `wrote`, `systemctl creates`, `permission_mode`, `warning: linger is off`, `primitive`, `companion: create one one-shot…`: `arm.py:479-533` (SKILL.md:61-63, 71).
- "A fire inside the usage limit is lost (spike 004)": `arm.py:521-524`, `matrix.py:65-66`, `.planning/spikes/MANIFEST.md:21` (VALIDATED).
- Reset flags and refusal semantics ("refused… the hourly wake stands", "inferred, D-30", epoch/ISO-with-offset): `cli.py:86-93`, `arm.py:558-560`, `reset_parse.py:261-276` (SKILL.md:81-85).
- StopFailure hook opt-in, rate_limit matcher, default off: `tools/setup.py:1820-1821` (SKILL.md:87-91).
- `done` marker-only inside a resumed wake: `fire.py:231-243` (SKILL.md:103).
- Exactly six subcommands: `cli.py:61-72` (SKILL.md:108).
- `matrix --json` as the Phase 27 contract with evidence labels: `matrix.py:1,205-210`, `.planning/phases/27-…/27-CONTEXT.md:39,58` (SKILL.md:119).
- Cross-AI hard-tier continuation (cycle/due_at, never cycle 0): `fire.py:32-35` (RESUME_PROMPT), `ai-kit-cross-ai/SKILL.md:134-145` (SKILL.md:137-139).
- Nothing in the code detects a subagent, exactly as SKILL.md:18 admits — the honesty claim itself is accurate.

## Findings (all minor)

1. **Minor — SKILL.md:95**: `done` is described as "so the next wake removes itself", but `fire.py:240-249` disarms immediately whenever no resume holds the lock; marker-only semantics apply only inside a fire child (correctly stated at SKILL.md:103). Harmless in every path, but imprecise. **Fix**: "run `done`… it removes the wake at once unless a resume is running".
2. **Minor — SKILL.md:56-58**: `arm`'s `--permission-mode`, `--pid` and `--only-if-armed` flags are undocumented, yet arm's own output says "pass --permission-mode to change it" (`arm.py:500-501`) and exit 0's "(or nothing to do)" (SKILL.md:65) is reachable only via `--only-if-armed` (`arm.py:200-201`). **Fix**: one line naming the three flags.
3. **Minor — SKILL.md:53-54**: omits that `arm` silently defaults to `CODEX_THREAD_ID` from the env (`hosts.py:68-70`, `arm.py:191`) on the one host the text itself labels unverified. **Fix**: add "the shim will read `CODEX_THREAD_ID` if set" to the codex bullet.
4. **Minor — SKILL.md:10, 26-39, 66**: the shim hard-depends on the sibling `ai-kit-spec-review` skill (`ai-kit-session-wake.py:19-28`, exit 2 "sibling skill is missing"); the text never mentions the dependency and the exit-2 examples don't include it. Low cost because the error names its cause, and sanctioned installs (symlinks back to the checkout, `README.md:57`) always carry the sibling. **Fix**: one clause at SKILL.md:10.
5. **Minor — SKILL.md:14-15**: "refuses `arm` when `AI_KIT_CROSS_AI_CHILD` is set" — values `""` and `"0"` do not refuse (`arm.py:169-170`). **Fix**: "set to a non-zero value".
6. **Minor — SKILL.md:115**: `status` requires both or neither of `--host`/`--session-id` (`cli.py:172-174`); the both-or-neither rule is undocumented. **Fix**: note it beside the synopsis.

## Top 3 Improvements
1. Add the three undocumented `arm` flags (finding 2) — the output already advertises one of them.
2. Correct the `done`-semantics sentence (finding 1) — it is the one statement a reader would predict wrongly.
3. Name the `ai-kit-spec-review` sibling dependency once (finding 4) so a partial install's exit 2 is anticipated rather than discovered.
