Judge: opus
Reviewed-sha256: 17fb505e590c611cce964ad027ce5e245a132d8a946bb0735ced163ef76155d8
Lane: native subagent completed
Score: 101
Critical: 0
Important: 2

**Skill evaluation: ai-kit-spec-execute-gsd (round r4)**

I scored `skills/ai-kit-spec-execute-gsd/` against `tmp/p251/14/rubric.md`. I read SKILL.md (488 lines), `references/dispatch-notes.md` (67 lines) and the Phase 25.1 diff. I checked the skill's claims against these files:
- `skills/ai-kit-cross-ai/SKILL.md` and `skills/ai-kit-cross-ai/references/subprocess-quota-policy.md`
- `ai_kit_spec/runner_dispatch.py`: `EXEC_NOTES`, `project_runner_command` and `runner_flags`. The hook passes `--runtime`, not `--prefer`.
- GSD's `execute-phase/detail/elaboration.md` (the `cross_ai_delegation` step)

The skill follows the Process pattern, and its total is 101/120 (grade B). The 25.1 changes are described correctly:
- one runtime per call
- exit 75 with `retry_after_s=` gets one one-shot wake on the same lane, CLI and model
- `stopped=hard-waits` or `stopped=cap` (exit 69) leads to a notice and an `abort` answer
- the `cross-ai: upstream` lines are relayed
- `unsupported_model_id` matches the runner's model grammar
- the Copilot exec note matches `COPILOT_EXEC_NOTE`
- "Never switch harness, provider or model" is stated twice (SKILL.md:45 and :462)

Nothing in the skill switches harness, provider or model on its own.

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 16 | 20 | Expert content: unquoted hook expansion, ownership and backups, trust gate, wake semantics. The `cross_ai: true` opt-in rule is stated four times (:14, :191-195, :211-216, :328-331). |
| D2 Mindset + Procedures | 13 | 15 | A "Mindset before writing" block plus GSD-specific procedures Claude would not know. |
| D3 Anti-Patterns | 13 | 15 | A specific NEVER list with reasons (skip is a native fallback; re-resolving can rewrite the hook). |
| D4 Spec / Description | 14 | 15 | Valid frontmatter. WHAT and WHEN are clear, but trigger words for the quota and retry wake are missing. |
| D5 Progressive Disclosure | 11 | 15 | 488 lines, close to the 500 limit. The one reference has good "read only if" triggers. The canonical policy is linked only in the preamble, with no MANDATORY trigger. |
| D6 Freedom Calibration | 14 | 15 | Low freedom with exact shim calls for fragile config writes, which fits. |
| D7 Pattern | 8 | 10 | Clear Process pattern, but about 2.5x the typical length because of inline bash and Python. |
| D8 Usability | 12 | 15 | Strong exit and error handling. Gaps in how to answer GSD's prompt after stops that are not hard-tier, and in where the evidence lives. |

**Findings**

1. **Important: the canonical policy is not linked where the decision is made.**
   - Evidence: SKILL.md:41-45 links `../ai-kit-cross-ai/SKILL.md` only in the preamble. The stop-handling text at SKILL.md:453-482 never names it or requires reading it. The diff removed the old "**MANDATORY when a cross-AI run stops**: read that policy before acting."
   - Fix: at SKILL.md:453, add "**MANDATORY on any cross-AI stop:** read [`../ai-kit-cross-ai/SKILL.md`](../ai-kit-cross-ai/SKILL.md) sections 4, 6-8 before answering GSD's prompt."

2. **Important: no answer to GSD's retry/skip/abort prompt is given for the other stops.**
   - Evidence: SKILL.md:453-456 covers relaying and the state file for every stop. Only a bare exit 75 is said to schedule nothing, and SKILL.md:461 rules `abort` only for hard-tier exit 69. Exits 1, 2, 124, 127, 69 for auth, billing or permission, and a bare 75 leave the prompt unanswered.
   - Why it matters: the NEVER list forbids `skip` and lets only the wake answer `retry`. An executor can therefore leave GSD hanging or guess. The policy's table (ai-kit-cross-ai/SKILL.md:94-103) says only "owner stop".
   - Fix: add one sentence: "Every other stop (no `retry_after_s=`): relay, write the state file, answer `abort`, schedule nothing."

3. **Minor: the evidence location is ambiguous under GSD.**
   - Evidence: SKILL.md:453-454 says to relay the lines "from the runner's `.err` file". Under the hook, GSD redirects the runner's stderr to `$ERROR_LOG` (elaboration.md:99), and no lane `.err` file exists.
   - Fix: say "from GSD's `$ERROR_LOG` (the hook's stderr, the runner's `.err` evidence channel), read in full, not a truncated tail."

4. **Minor: resuming after a hard-tier stop is a dead end as written.**
   - Evidence: SKILL.md:466-468 and the `resume_via=gsd-execute-phase` text (:156-157) tell the owner to rerun `/gsd-execute-phase` with the hook unchanged. After `stopped=hard-waits` or `stopped=cap`, the runner refuses that lane with exit 69 until the owner deletes the named state file (subprocess-quota-policy.md "Hard tier").
   - Fix: at SKILL.md:482, add "the owner restarts the episode only by deleting the state file the runner names."

5. **Minor: "These tools" has no referent.**
   - Evidence: SKILL.md:43 says "These tools are Claude Code specific" after naming only CronCreate. The `Skill` tool mention was dropped in the diff.
   - Fix: write "CronCreate and the `Skill` tool (Step 3) are Claude Code specific."

6. **Minor: the reference duplicates SKILL.md and is now out of date.**
   - Evidence: dispatch-notes.md:24-33 restates SKILL.md:311-317 almost word for word and has no Copilot note (SKILL.md:318-319).
   - Fix: trim the reference section to its rationale only (`.git` writability under workspace-write) and point to SKILL.md for the current list of runtime notes.

7. **Minor: low-value bulk in SKILL.md.**
   - Evidence: the four-times-repeated opt-in rule (see D1), and a 40-line inline Python marker editor (SKILL.md:387-421).
   - Fix: state the opt-in rule once, at the Step 2 `cross_ai_hook` bullet, and move the marker edit into a shim subcommand (for example `write-phase-guidance`). That frees room for findings 1 and 2.

I did not run the test suite (read-only rail) and did not check whether the skill's text is pinned by tests. All judgements come from reading the source.

DIGEST 17fb505e590c611c
CURRENT 101/120
CRITICAL 0 IMPORTANT 2
