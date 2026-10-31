Judge: my-referee-two
Reviewed-sha256: ccbcea9bd76c22984a64850e1c56edc67e19d8f89daa963c012d71735e036195
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=499s out=422710 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 108
Critical: 0
Important: 0

# Skill Evaluation Report: ai-kit-spec-execute-superpowers

## Summary
- **Total Score**: 108/120 (90%) — Grade A
- **Pattern**: Process (phased Step 0–4 workflow with checkpoints) carrying Tool-pattern exact bash blocks
- **Knowledge Ratio**: E:A:R ≈ 85:13:2
- **Verdict**: An expert-grade orchestration adapter whose every checkable factual claim matches the repository code; the remaining gaps are cosmetic (relay instructions for evidence lines that pre-spawn refusals never produce, one script/prose ordering wrinkle in escalation.md, and SKILL.md sitting at the 500-line ceiling).

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Three-set exclusion state machine, pinned-injection re-dispatch, anchor-vs-fresh-pick escalation floor, objective-digest session-reuse invariant — none of this is model prior knowledge; only cost is the deliberate NEVER-index duplication |
| D2: Mindset + Procedures | 14 | 15 | "Ask: permanent or same-wave?" shapes classification; non-obvious orderings are stated as such (relay before fold, mode before key, increment before escalation check) |
| D3: Anti-Pattern Quality | 15 | 15 | Nine NEVERs, each with its non-obvious mechanism (runtime id ≠ ladder key excludes nothing; omitted reasons-json → `no_usable_dispatch`; escalation set never joins exclusions) |
| D4: Specification Compliance | 14 | 15 | Valid frontmatter; description has WHAT, WHEN, keywords and explicit negative scope ("not for superpowers:executing-plans"); docked 1 for a single ~100-word sentence that is hard to scan |
| D5: Progressive Disclosure | 12 | 15 | Four references, each with a MANDATORY trigger embedded at its exact workflow point; design-notes has a conditional trigger; no explicit "Do NOT load" guidance, and SKILL.md is 498 of the 500-line budget |
| D6: Freedom Calibration | 14 | 15 | Exact pinned bash for fragile state/protocol steps, prose judgment only where the host harness owns the decision; delegation boundary (Step 4 "unaffected") is explicit |
| D7: Pattern Recognition | 9 | 10 | Clean Process pattern with STOP checkpoints and decision trees; heavier than the ~200-line canonical form |
| D8: Practical Usability | 13 | 15 | Every mode/classification/scheduler branch has runnable bash plus fallbacks (no-scheduler print path, single-task plan, missing wake skill, resumed partial report); small gaps in findings 1–2 |

## Factual verification against the repository (claims checked, all confirmed)

- Six subcommands and flags: `ai_kit_spec_superpowers/cli.py:471-478`; `--heartbeat-interval` required (cli.py:427) yet unused by dispatch (cli.py:345-354) — matches SKILL.md:338.
- Payload shapes: native/external_cli carry `key`/`runtime` (+`effort`/`service_tier` external only, dispatch_injection.py:294-307; `ladder_keys` added cli.py:253); `quota_exhausted` (cli.py:141-149) and `no_candidate` (cli.py:192-196) carry neither — matches SKILL.md NEVER #3 and design-notes.md; `ladder_keys` in every mode — escalation.md:53 confirmed.
- Reason taxonomy incl. `capacity`/`billing_or_access`/`git_timeout`: `ai_kit_spec/error_classifier.py:16-26`; route names: `ai_kit_spec/routing.py:35-37`; `no_usable_dispatch` fallback for reason-less excluded keys: cli.py:133-134 — matches SKILL.md:211-216.
- `any_quota_recoverable` is the any-"quota" gate: dispatch_injection.py:87-90; `resume-exclusions` drops quota keys: dispatch_injection.py:148-162; `implementer-status` counts declaration lines only, BLOCKED on none/conflict: dispatch_injection.py:398-419; `classify-dispatch-failure` ok/quota/real_error with exit 69/75 and nested-`status` tokens: dispatch_injection.py:422-454 (tokens parsed from the AIKIT-XAI line at `runner_dispatch.py:539`).
- Report-file preservation (before/after compare, marker line, never overwrites a CLI-written file): cli.py:62-65, 336-342 — matches SKILL.md:341-344 and design-notes.md.
- Exit-2 cases: ConfigError → 2 (superpowers cli.py:490-497); `purpose="execute"` custom command / claude / grok → ExecuteSelectionError (`execute_selection.py:74-108`) — matches SKILL.md:173-176.
- Runner claims: `<objective>`-only task digest and digest-match session reuse (`references/cross-ai.mjs:3259-3265, 4069`); `<files>` gating of changed-tree retries (cross-ai.mjs:4312-4346); codex `--codex-sandbox workspace-write` → codex `--sandbox workspace-write`, /tmp+TMPDIR allowed (runner_dispatch.py:214-215, cross-ai.mjs:42, 1471-1475); `ai-kit-spec: subprocess dispatch needs Node` (runner_dispatch.py:66); `ai-kit-spec: dispatching <key> unverified` (routing.py:229-231); evidence lines `cross-ai: report`/`upstream`/`lane stopped=` (`ai-kit-cross-ai/SKILL.md` §4/§6; cross-ai.mjs:3854); whole-minute rounding / under-60 s / no-scheduler print path (ai-kit-cross-ai/SKILL.md:151-156); "never switch" (§8, :168-172).
- Sibling tools: `cache-path --kind quota` and `trust-local --show` with `<prompt>` redaction (`ai_kit_spec/cli.py:142-143, 815`); `ignoring untrusted project-local config` stderr (config_io.py:410); claude review-only with fable/opus/sonnet/haiku native selectors (detection.py:113-114); only Claude Code selects per call (routing.py:45-57).
- Session wake: `armed <host>-<session_id>` / `refreshed` output (ai_kit_session_wake/arm.py:479-480); no-session-id refusal exit 2 on pi (arm.py:193-195, cli.py:48) — matches SKILL.md:106-111.
- Honest-uncertainty claims verified as such: `strength` unread by any resolution code (absent from `ai_kit_spec`); `timeout_tiers` not plumbed into this adapter (`assemble_candidates` at dispatch_injection.py:165-189 carries no such key; `resolve_timeout_tiers` exists only on the review path, config_io.py:643 / review cli.py:767); the 1800 s curated floor is corroborated by repo docs (REQUIREMENTS.md:42; phase verification pinning `ai-kit-gsd-curated-config/cross_ai.py:47`), not re-derived here.

**Unverifiable in this repository (external anchors, no defect claimed):** all `superpowers:subagent-driven-development` structure quotes (SKILL.md:8-13, 96-100, 244-246, 285, 302-303, 353, 363-366, 481-482; design-notes.md:5-8), `superpowers:executing-plans` running inline, and Claude Code `Agent`/`CronCreate` behavior. They are internally consistent and mirrored by the sibling `ai-kit-spec-execute-gsd` skill.

## Numbered Findings

1. **Minor** — SKILL.md:372-374 and SKILL.md:430-432. "Relay evidence first" (quota point 1) and the `real_error` branch instruct relaying `cross-ai: report` / `cross-ai: upstream` / `AIKIT-XAI` lines verbatim, but a pre-spawn refusal — e.g. a model id outside the runner grammar (`reason="configuration"`, runner_dispatch.py:185-193) or missing Node (runner_dispatch.py:591) — emits none of those lines, only an `ai-kit-spec:` stderr line. An agent may stall or report "no evidence" instead of relaying what exists. **Fix:** add one sentence to both spots: "when no `AIKIT-XAI` line exists, relay the `ai-kit-spec:` line from `$DISPATCH_BASE.err` verbatim instead."
2. **Minor** — references/escalation.md:44-49 vs :58-63. The floor script's not-found fallback (`idx = len(ladder)` at :47) produces a valid-looking permissive floor (exclude only the stuck key) when `$ESCALATION_ANCHOR_KEY` is missing from `ladder_keys`, but the rule that such an anchor must STOP and ask (:58-63) appears five paragraphs after the script. An agent executing blocks in document order can compute the floor and re-run `resolve-injection` before meeting the STOP rule. **Fix:** branch inside the script (print STOP when the anchor is empty or not in `$LADDER_KEYS_JSON`) or move the STOP rule above the bash block.
3. **Minor** — SKILL.md:18-43 (with :498 total lines). The NEVER index restates all nine rules that are each repeated at their point of use, and the confinement/Node prose (SKILL.md:449-464) duplicates design-notes.md's parallel sections; the file sits at 498 of the 500-line budget the format itself sets. **Fix:** cut the index to one line per rule (name + step pointer) and reduce the Step 3 prose to a pointer plus the one operational sentence.
4. **Minor** — SKILL.md:3. The description packs WHAT, WHEN, keywords and negative scope into a single ~100-word sentence; complete for activation matching but hard to scan. **Fix:** split into two sentences: one WHAT clause, then "Use when … ; not for …".

## Top 3 Improvements
1. Fix finding 1 (both evidence-relay spots) — it is the only place an agent can be left without an actionable instruction on a real path.
2. Fix finding 2 by putting the unknown-anchor STOP inside the escalation bash, so the safety rule cannot be sequenced away.
3. Trim per finding 3 to pull SKILL.md comfortably under 300 lines; every cut candidate is a verbatim duplicate, so no knowledge is lost.

## Verification limits
Only the two `python3 -c` snippets and the Step 0/3 bash blocks were desk-checked against the named code; no block was executed (read-only mandate). External superpowers/Claude Code claims listed above remain unverified by anything in this repository.
