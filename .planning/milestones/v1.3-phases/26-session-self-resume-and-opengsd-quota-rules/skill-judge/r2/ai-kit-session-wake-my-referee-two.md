Judge: my-referee-two
Reviewed-sha256: a28223d21d64c262e99b7c9a3c004c8bbf89381ba6819f6d1f38f2b3fd4c0823
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=204s out=230169 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 109
Critical: 0
Important: 0

# Skill Evaluation Report: ai-kit-session-wake

## Summary
- **Total Score**: 109/120 (91%)
- **Grade**: A
- **Pattern**: Tool (decision-table style, exact commands, low freedom for a fragile OS operation)
- **Knowledge Ratio**: E:A:R ≈ 75:22:3
- **Verdict**: A dense, expert-grade operational skill whose factual claims match the shipped code everywhere I could check; only minor imprecisions remain.

Every load-bearing claim I verified against the repository holds: sibling dependency + exit 2 naming it (`ai-kit-session-wake.py:19-28`); the `AI_KIT_CROSS_AI_CHILD` / `cross-ai.mjs` refusal (`arm.py:169-180`, `liveness.py:143-149`); `CLAUDE_CODE_SESSION_ID`/`CLAUDE_PID`, `CODEX_THREAD_ID`, pi/opencode `session_env=None` (`hosts.py:41-81`); exit codes 0/2/3 and their causes (`cli.py:22-24,130-135`, `arm.py:185-195,294,548-557`); `not armed; nothing refreshed` exit 0 (`arm.py:205-212`); every relay line quoted in the skill is printed verbatim by `_report_arm` (`arm.py:479-535`), including the companion line citing spike 004; reset + 60 s (`reset_parse.py:19`); `done`/`disarm` semantics and the exact "a wake resume is running" message (`fire.py:207-251`); status/matrix behavior (`cli.py:125-129,170-189`, `matrix.py:6`); StopFailure hook opt-in/experimental/unverified (`tools/setup.py:1820-1821`, `tools/hooks/README.md:10`); executor arming and the `refreshed`-means-not-yours ownership rule (`ai-kit-spec-execute-gsd/SKILL.md:346-381`, `ai-kit-spec-execute-superpowers/SKILL.md:102-133`); cross-AI hard-tier cycle/due_at continue rule (`ai-kit-cross-ai/SKILL.md:130-145`, mirrored in the resume prompt at `fire.py:29-36`).

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Nearly pure expert content: shim contracts, per-host pitfalls, ownership traps, honest "Unverified" ledger |
| D2: Mindset + Procedures | 14 | 15 | "Never fail the run on the wake" mindset plus exact domain procedures Claude cannot know |
| D3: Anti-Pattern Quality | 15 | 15 | Seven specific NEVERs, each with reason; residual risks stated rather than hidden |
| D4: Specification Compliance | 14 | 15 | Description has WHAT/WHEN/KEYWORDS + scope boundary; one imprecise cross-skill claim (finding 2) |
| D5: Progressive Disclosure | 14 | 15 | 174 self-contained lines; defers to executor skills and code output rather than duplicating |
| D6: Freedom Calibration | 15 | 15 | Exact commands for fragile systemd/pid operations, judgment left only where judgment is safe |
| D7: Pattern Recognition | 9 | 10 | Clean Tool pattern with exit-code decision table |
| D8: Practical Usability | 10 | 15 | Covers hosts, refusals, companions, teardown; two small gaps (findings 1, 4) |

## Findings

1. **Minor — `SKILL.md:35`** — "(the same order the executor skills use)" is not true: the executors resolve one sibling path, not this four-candidate loop (`ai-kit-spec-execute-gsd/SKILL.md:359`, `ai-kit-spec-execute-superpowers/SKILL.md:117`). The loop's first candidate is that same sibling dir, so behavior is unaffected. Fix: drop the parenthetical or say "candidate 1 is where the executors look".
2. **Minor — `SKILL.md:3`** — "The ai-kit-spec-execute-* executors already arm one for multi-plan runs": true for the GSD executor (≥2 plan files), but the superpowers executor arms on ≥2 *tasks* in one plan (`ai-kit-spec-execute-superpowers/SKILL.md:104-105`). Fix: "for multi-plan or multi-task runs".
3. **Minor — `SKILL.md:3`** — Trigger "when an AGENTS.md rule says to arm the session wake": no AGENTS.md in this repo contains such a rule (verified by grep). Presumably aimed at machine-level AGENTS.md files; harmless, but the trigger is unverifiable in-repo. Fix: none needed if the rule exists on target machines; otherwise reword to "when an executor or owner instruction says to arm".
4. **Minor — `SKILL.md:153`** — `status` with exactly one of `--host`/`--session-id` refuses with exit 2 ("status requires both --host and --session-id", `cli.py:172-174`); the skill states only "both … or neither". Fix: add "one without the other is refused".

## Top 3 Improvements
1. Correct the two cross-references (findings 1–2) so a cross-checking agent trusts the rest without re-verifying.
2. State the one-flag `status` refusal (finding 4).
3. Optionally note where `arm`'s exit-2 refusal for an unverifiable session store (`hosts.py:141-151`, opencode listing) fits the existing exit-2 list, since that is the likeliest live refusal on this host.
