Judge: my-referee-two
Reviewed-sha256: 81ba60cd25342e7aec8d9f47ce81a9a00d606a7368cec6fe570a688701372eef
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=288s out=385635 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 110
Critical: 0
Important: 1

# Skill Evaluation Report: `ai-kit-spec-config`

**Scope reviewed**: `skills/ai-kit-spec-config/SKILL.md` (493 lines), `references/cli-model-selection.md` (344 lines), the `ai-kit-spec.py` subcommands it drives (all 16 named subcommands verified present), the sibling `cli-profiles/` it points at, the canonical `ai-kit-cross-ai` policy it must defer to, and the Phase 25.1 diff (`35a0368~1..HEAD` — exactly one hunk: the new delegation pointer at SKILL.md:241–243).

**Phase 25.1 posture — verified sound.** The single pointer line (SKILL.md:241–243) meets the pinned contract in `tests/test_cross_ai_skill_text.py:207–215` exactly: one mention, correct relative path, scoped to runtime/model dispatch, no restated retry/hard-tier/exit-code rules. Its claims are accurate against the policy (`subprocess-quota-policy.md`: one `--runtime` per call with `--prefer` aliasing its first entry; bare model id refused with a grammar-naming message — "the runner refuses a model id its runtime's grammar disallows"). The skill never switches harness, provider or model: the ladder is user-ordered at registration/resolution time (SKILL.md:364–371), the codegraph-alternative check is explicitly informational with "never silently substitute the CLI" (reference:314–319), and never-switch is delegated rather than duplicated. `timeout_tiers` (Step 2.8) is not stale — it is the Python dispatch layer's knob (`runner_dispatch.py:620–655`, `cli.py:794`), distinct from the runner-internal ladder.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 18 | 20 | Nearly all live-verified expert knowledge (codex bare-id vs effort suffix, cursor ids encoding effort/fast/context, flat-key `timeout_tiers` because `extra` is derived at read time, `heuristic_confirmed` provenance, `canonical_key` re-derivation after provider correction); minimal redundancy |
| D2: Mindset + Procedures | 14 | 15 | Opening Step 2 judgment calls (quota reliability vs ladder position, purpose-weighted fit, "a config the user can predict the fallback behavior of at a glance") + strictly domain-specific 8-item catalog procedure |
| D3: Anti-Pattern Quality | 13 | 15 | 13-item NEVER list, each specific with a reason; several embedded never-statements with dated live evidence |
| D4: Spec Compliance / Description | 15 | 15 | WHAT + WHEN + trigger keywords including the cross-skill activation hook ("when ai-kit-spec-review warns no config exists") and all three flag keywords |
| D5: Progressive Disclosure | 14 | 15 | MANDATORY read trigger embedded at the exact decision point, explicit "Do NOT load" for the no-CLI case, per-runtime profile gating; body sits at 493/500 lines |
| D6: Freedom Calibration | 14 | 15 | Rigid where bytes break (exact JSON shapes, `--replace` gating, trust consent), advisory where judgment belongs (roster, ordering) |
| D7: Pattern Recognition | 9 | 10 | Self-aware Process-with-Tool-rigor hybrid; "I want to… → Go to" navigation table |
| D8: Practical Usability | 12 | 15 | All commands verified real; strong failure paths (exit≠0, WARNING scan, untrusted-config relay); docked for the copilot drift below and one timeout framing gap |

**Total: 110/120 (91.7%, Grade A)** — production-ready; the remaining findings are 25.1 follow-through, not design flaws.

## Findings

1. **Important — Phase 25.1 drift: the new `copilot` runtime is absent from every runtime enumeration, leaving three statements subtly wrong.** `detection.py:117–118` adds `copilot` (`runner=True`, unverified rows, no `list_argv`, no `cli-profiles/copilot.md`), but: (a) SKILL.md:88–89 says models lists are carried by "pi, opencode, cursor, codex and claude… grok never does" — copilot also never does, so the exhaustive framing misleads a copilot-registering run; (b) SKILL.md:231–232 says of profile-less runtimes "(pi has none today)" — post-25.1 the set is {pi, copilot}; (c) `references/cli-model-selection.md:25–27` enumerates single-provider CLIs as "pi, codex, claude and grok" (copilot missing), and line 72 routes no-`models` CLIs as "grok always; codex or pi when its listing failed" (copilot is always in that bucket, so its candidates must flow through `--extra-candidate`). Behavior stays safe in each case (the generic rules still fire), but the prose describes the pre-25.1 six-CLI world. **Fix**: add copilot to all four enumerations, flagged as `runner rows: unverified` per `detection.py:117`, and note a copilot candidate always takes the `--extra-candidate` path.

2. **Minor — Step 2.8's "the worst case is their sum (60 minutes)" (SKILL.md:381–384) is true of the `timeout_tiers` layer alone and now understates end-to-end worst case**, since each tier's attempt runs the 25.1 runner with its own internal soft waits. The delegation pointer covers the rule, but this numeric claim stands alone. **Fix**: one clause, phrased to respect the text pin that forbids restating runner rules — e.g. "per dispatch attempt; the runner's own internal waits add on top (see the linked cross-AI skill)".

3. **Minor — 493/500-line body is at the ceiling; Step 2.8's timeout rationale (SKILL.md:380–391) is reference-grade detail** (TOML-writer dict-branch internals, per-entry override mechanics). **Fix**: move that block to a small `references/` file with the same MANDATORY trigger style used for `cli-model-selection.md`.

4. **Minor — the description omits the hard dependency on the sibling `ai-kit-spec-review` install**, which Step 0 discovers and handles with a clean stop (SKILL.md:54–57). **Fix (optional)**: append "requires the ai-kit-spec-review skill's ai-kit-spec.py" to the description so activation doesn't happen on hosts where the run can only stop.

Skipped: no live execution of the wizard or its test suite (read-only mandate; subcommand existence and pin compliance were verified statically). Risk: flag-level claims (e.g. `probe-quota --quota-path`) rest on the pinned dispatch docs and tests, not on running them.

DIGEST 81ba60cd25342e7a
CURRENT 110/120
CRITICAL 0 IMPORTANT 1

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=288s out=385635 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
