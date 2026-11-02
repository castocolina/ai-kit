Judge: opus
Reviewed-sha256: 5d18a6276c145c97dbc38991579989c8c093267004f9a4428d4de651c5e0bd1e
Lane: native subagent completed
Score: 96
Critical: 0
Important: 3

Skill-judge report: `skills/ai-kit-cross-ai/`

**Scope.** I read `SKILL.md` (163 lines), `references/subprocess-quota-policy.md` (175) and `references/launch-and-wait.md` (113), plus the Phase 25.1 diff (`35a0368~1..HEAD`, 3 files, all new). I checked their claims against the runner template `skills/ai-kit-spec-review/references/cross-ai.mjs` and the checkout-local `.claude/gsd-core/workflows/execute-phase.md`.

**What I verified.**
- **Runtime choice:** one runtime per call; `--prefer` keeps only its first entry and prints a notice (cross-ai.mjs:24, :4258-4274).
- **Exit codes:** the table in SKILL.md matches `STATUS_TABLE` (cross-ai.mjs:1159-1180), and signal exits are 128+n (:3532).
- **Retry config:** the defaults and the `capS` 14400 clamp match (:2906-2954), and the reference's CONFIG block matches the template's `retry` object byte for byte (:83-92).
- **Bare exit 75:** happens when the state file cannot be written (:3850).
- **Upstream fields:** the allowlist matches (:1827).
- **Copilot:** the prompt goes on argv, stdin is ignored, the review profile is set and `COPILOT_ALLOW_ALL` is cleared (:1433-1452, :3267).
- **GSD "skip":** it falls back to the normal executor (execute-phase.md:419), so "never answer skip" is correct.
- **Pointers:** all six sibling skills point to `ai-kit-cross-ai`.
- **Never switch:** the rule is stated clearly (SKILL.md:139-143, policy:19-20).

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 16 | 20 | Dense runner-specific facts (exit table, hard-tier mechanics, the trap behind GSD's skip). Some waste: five near-identical per-host blocks, decision-ID jargon |
| D2 Mindset + Procedures | 12 | 15 | Clear launch, wait, read, chain, hard tier and GSD-answer procedures. Little "before acting, ask..." framing |
| D3 Anti-Patterns | 12 | 15 | Specific NEVERs with reasons (skip = harness switch, upstream text is data, kill by PID, the dirty-tree stop). Undercut by the §1 wording (finding 1) |
| D4 Spec Compliance | 13 | 15 | Valid frontmatter. WHAT/WHEN and the not-for routing are good. Lacks keywords such as `AIKIT-XAI`, `exit 75`, `retry_after_s` |
| D5 Progressive Disclosure | 11 | 15 | References are linked inline in §2-§4. No "MANDATORY read" or "Do NOT load" guidance, and SKILL.md §4 and §6 partly repeat the policy file |
| D6 Freedom Calibration | 13 | 15 | Low freedom where it matters (exact wait, same lane, abort). The launch examples themselves are faulty (findings 2, 3) |
| D7 Pattern | 8 | 10 | Clear Process pattern with a Tool-style exit table. The per-host reference is padded |
| D8 Practical Usability | 11 | 15 | Good error and stop coverage. A reader is told to read artifacts the examples never produce, and the Claude Code example defeats its own completion notice |

## Findings

**1. Important. §1 wording allows a runtime switch after a failure.** SKILL.md:33-34 says: "Changing the runtime is a config edit done by the agent (the project hook or the plan), never a choice the runner makes after a failure." This reads as permission for the agent to change the runtime after a failure, which contradicts §8 (SKILL.md:141, "Never switch ... in the runner or in a caller") and the core policy.
- **Fix:** "The runtime is the owner's choice, set in the project hook or the plan before a run. Neither the runner nor a caller changes it in response to a failure; a failure ends in §6-§8."

**2. Important. The skill tells the reader to read a "status file" and the exit code that nothing produces.** SKILL.md:58, :64 and :104, and launch-and-wait.md:8, refer to a per-lane "status file". The runner writes none (no status-file logic in cross-ai.mjs). Every launch example writes only `lane.out`, `lane.err` and `lane.pid`, and `cmd & echo $! > lane.pid` throws away the exit code, which §4 says to read first.
- **Fix:** either name the `exit=` field of the last `AIKIT-XAI` line in `lane.err` as the exit-code source and drop "status file", or add `; echo $? > lane.rc` (foreground) or `wait $pid; echo $? > lane.rc` to every example and call that the status file.

**3. Important. The Claude Code launch pattern breaks the completion notice it relies on.** launch-and-wait.md:14-21 says to read the status "only after the notice arrives", but the example ends the node command with `&` and then `echo $! > lane.pid`. Under the host's background Bash, that shell exits at once, so the notice fires immediately while the lane is still running. The pi, opencode, cursor, codex and copilot blocks (:43-99) also use `& ... wait`, which is just a foreground run spelled the long way, and pi's prose says "the command blocks".
- **Fix:** for Claude Code, run the plain command (no `&`) as the background Bash call, write `$$` or a wrapper PID if a PID is needed, and append `; echo $? > lane.rc`. For foreground hosts, use the plain command. Then fold the five identical blocks into one block plus a runtime list.

**4. Minor. The timeout description is ambiguous and incomplete.** SKILL.md:53-55 says "`--outer-timeout` replaces it". The runner says it replaces the GSD lookup and the CONFIG cap (cross-ai.mjs:36-37). The skill also leaves out that the default outer deadline is `min(CONFIG.outerTimeoutS 1800, GSD value or 300)` (:2885-2887), and that `--timeout` can only lower the inner deadline, never raise it (:35, :2890).
- **Fix:** state the min() rule and the lowering-only rule in one sentence each.

**5. Minor. A refusal is not documented.** SKILL.md:29-31 and policy:152-153 do not say that `--mode review` refuses `--tools-profile exec` (cross-ai.mjs:9750, "review mode allows only the review or none tools profile").
- **Fix:** add that sentence to policy §Review-mode argv checks.

**6. Minor. Internal decision IDs leak into a portable skill.** "(D-10)", "(D-02)" and "(D-03)" appear at policy:46, :75 and :83. They mean nothing to an agent on another host.
- **Fix:** delete them.

**7. Minor. The success example does not look like a real exec lane.** The "ok" line at launch-and-wait.md:26 shows `cli=- model=- attempts=0`.
- **Fix:** use a self-test ok line that shows `cli=pi model=fake/ok attempts=1`.

**8. Minor. The description misses the strings agents will search for.** SKILL.md:3-9 never contains `AIKIT-XAI`, `exit 75`, `retry_after_s` or `cross-ai.mjs`.
- **Fix:** add them to the description's trigger clause.

**9. Minor. The references have no loading guidance.** SKILL.md:158-163 lists them, but nothing says when they are mandatory.
- **Fix:** make the policy file a required read in §6 (hard tier) and §4 (classification questions). Add "Do NOT load `launch-and-wait.md` when GSD runs the command (§7)."

What I skipped: I did not run `--self-test`. I did not check the self-test quotes beyond their format, did not check the overlay or catalog semantics line by line against `cross-ai-errors.json`, and did not confirm `CronCreate` exists on this host.

Main risk: findings 2 and 3 (the launch pattern and the reference to a nonexistent status file) affect how every caller reads results.

DIGEST 5d18a6276c145c97
CURRENT 96/120
CRITICAL 0 IMPORTANT 3
