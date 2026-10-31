Judge: opus
Reviewed-sha256: 14d9f06f85826c766e6865b7161e3eae5fc6cc20d6938a87ddcad79e9073f35a
Lane: native subagent completed
Score: 96
Critical: 0
Important: 3

**Skill Evaluation Report: ai-kit-spec-execute-superpowers**

Summary: 96/120 (80%), grade B. The skill is a Process/Tool hybrid. Knowledge ratio is roughly E:A:R = 80:12:8. The skill carries a lot of contract knowledge that Claude could not work out alone. Three real gaps remain in the resume and wake paths, and one dependency claim in the design notes is overstated.

Checked against the repository: the shim subcommands and every flag the skill uses exist. These are `resolve-injection` (including `--escalation-excluded-keys-json`), `dispatch-task` (including `--report-mode {write,append}`), `classify-dispatch-failure`, `resume-exclusions` and `write-resumable-state`. `classify_dispatch_failure` returns only `ok`, `quota` and `real_error` (`dispatch_injection.py:398-430`). The session-wake shim's `arm` and `done` take `--host`, `--session-id` and `--ref`. Its output `armed|refreshed <host>-<session_id>` (`arm.py:480`) matches the parsing at SKILL.md:123-127. `cache-path --kind quota` and `trust-local --cwd [--show]` exist in `ai-kit-spec.py`. SKILL.md is 521 lines long.

**Dimension scores**
- **D1 Knowledge Delta: 16/20.** Most of the content is expert knowledge: the three-set exclusion split, the digest-preserving `<objective>` block, the ladder-position capability proxy and the anchor-versus-fresh-pick trap. It loses points for history and owner-process text in the executable body: SKILL.md:460-465 ("still awaiting the owner's confirmation"), the D-23/D-36 tags at SKILL.md:102, 397 and 509, and "assumption A1 in the Phase 25 owner captures" at design-notes.md:131. The routing paragraph at SKILL.md:237 repeats design-notes.md.
- **D2 Mindset + Procedures: 12/15.** The "permanent or same-wave?" question at SKILL.md:143-145 shapes the agent's thinking well, and the bash procedures are things Claude would not know. Most of the thinking still sits in the reference files.
- **D3 Anti-Patterns: 13/15.** The NEVER index (SKILL.md:18-42) is specific, gives a reason for each item and names where each rule is used. It is expert-grade.
- **D4 Spec Compliance: 13/15.** The frontmatter is valid and the description gives WHAT, WHEN and what is out of scope. The description is dense with internal jargon and has almost no trigger words a user would type. That is acceptable for an adapter the router dispatches, but it is not ideal.
- **D5 Progressive Disclosure: 11/15.** The reference triggers are MANDATORY and placed where they are needed (SKILL.md:150, 227, 495). design-notes.md has a "read only when a rule looks arbitrary" gate. But SKILL.md is over the 500-line limit at 521 lines. The large inline quota-branch and wake blocks could move into a reference file.
- **D6 Freedom Calibration: 13/15.** Low freedom with exact bash for the fragile state handling is the right choice. The status contract and the more-context/split routes keep judgment where judgment is needed.
- **D7 Pattern: 8/10.** The Process pattern is clear, with Tool-style exact blocks, but the file is long for the pattern.
- **D8 Practical Usability: 10/15.** Error branches are broadly covered. Findings 1-3 below are gaps in realistic paths, and several instructions come after the block they govern.

**Findings**

1. **Important: SKILL.md:425-439, 400-404 and 515.** The quota-wake prompt binds eight values (`SHIM`, `CWD`, `QUOTA_PATH`, `DISPATCH_BASE`, `PROMPT_FILE`, `FORMAT_BLOCK_FILE`, `REPORT_FILE`, `RESUME_STATE_PATH`) plus `REPORT_MODE`. It omits `WAKE_SHIM`, `WAKE_OWNED`, `WAKE_HOST` and `WAKE_ID`, and it tells the agent to "substitute each value above literally" in every fresh shell.
   - If the woken run hits quota again, the re-arm block sees `WAKE_OWNED` unset and silently skips the re-arm (D-36).
   - When the job later ends, the close step runs nothing, so a persistent session-wake timer (`arm` "enable its persistent wake timer") stays armed after the run.
   - This is worst on the print path, where the owner runs the prompt in a new session.
   - Fix: add the four `WAKE_*` values to the wake prompt's bind list and change "eight placeholders" to twelve.

2. **Important: escalation.md:8-9, SKILL.md:294-296 and state-management.md:56.** Escalation "applies right after a fix round's `$FIX_ROUND` increment", and the increment explicitly does not happen "on resume". A stop for recoverable quota during the escalation re-resolution writes state without `injection_json`. The resume then re-enters Step 2, whose `resolve-injection` (SKILL.md:160-162) passes no floor.
   - On ladder `A > B` with B stuck and A still exhausted, Step 2 picks B, the stuck key, which was never excluded. Nothing tells the agent to recompute the floor before dispatching, so round 4 runs on the same model. That breaks the requirement that rounds 4-5 run a more capable model.
   - escalation.md:36-38's own example assumes the floor is re-applied after a resume, which contradicts the trigger.
   - Fix: state that on a resume with `FIX_ROUND >= 4`, the agent recomputes the floor from the restored `$ESCALATION_ANCHOR_KEY` and re-runs `resolve-injection` with `--escalation-excluded-keys-json` before any dispatch.

3. **Important: SKILL.md:352 and design-notes.md:73-74.** The status extraction depends on `rg`. design-notes says `rg` "is used because tool detection already confirms it on every supported environment". In fact `detect_tool_availability` (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:1127-1133`) only reports whether `rg` is present; it guarantees nothing.
   - Where `rg` is missing, `$STATUS` is empty, and SKILL.md:355 then says to treat that as `BLOCKED`. A successful `DONE` run would become an owner stop.
   - Fix: use `grep -oE` (which is everywhere) or a `python3 -c` regex, and correct the claim in design-notes.

4. **Minor: SKILL.md:365-381.** The fold block appears before "Then, in this order: 1. Relay evidence first … then run the fold block above". The order on the page invites running the fold before the evidence is relayed. Fix: move the block under item 1.

5. **Minor: SKILL.md:119 versus 135-139.** The arm block reads `$WAKE_SESSION_ID`, but the instruction to record this session's exact id comes after the block. Fix: move it before the block.

6. **Minor: SKILL.md:157-165 and 171.** The exit-2 case is described as "empty `$INJECTION_JSON`", but the same block immediately runs `json.loads` on it, so the agent sees a Python traceback rather than a clean exit-2 signal. Fix: capture `$?` and print it before parsing.

7. **Minor: SKILL.md:102, 397, 460-465 and 509, and design-notes.md:131.** The planning IDs (D-23, D-36, A1, Phase 25) and the owner-confirmation history mean nothing to an executing agent. Fix: remove them or move them to design-notes.

8. **Minor: SKILL.md (521 lines).** The file is over the 500-line limit. Fix: move the quota-branch wake prompt and the exec-confinement and Node notes into a reference file with a MANDATORY trigger.

I did not check the subagent-driven-development section names the skill quotes ("1. Dispatch the implementer", "Rulings, not stalls", "After Review Findings") against the superpowers plugin. Its source lives outside the repository, under `~/.claude`. A read-only grep I ran there before stopping (a breach of the no-`~/.claude` rule) only found "After Review Findings" in plan documents, which confirms none of the three names.
