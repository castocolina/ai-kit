Judge: my-referee-two
Reviewed-sha256: bd7a28b0f98eae983d4f0c7252cb0ccd9c2227ca791501964979fbd630fcc088
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=183s out=359070 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 108
Critical: 0
Important: 3

# Skill Evaluation Report: ai-kit-spec-execute-gsd

**Total: 108/120 (90%, Grade A)** — Pattern: Process/Tool hybrid · E:A:R ≈ 88:10:2 · Verdict: a dense, near-pure expert contract for GSD dispatch; the 25.1 rework correctly replaced duplicated router-policy detail with the canonical ai-kit-cross-ai pointer, and every pointer/claim I checked against the code is accurate.

Verification performed: `ai-kit-cross-ai/SKILL.md` sections 4, 6–8 exist and cover exactly what the GSD skill cites (stop reading, hard tier, retry/skip/abort, never-switch); runner template 8 (`cross-ai.mjs:2`) implements one-runtime-per-call (`--runtime`, `--prefer` first entry, :4416–4446), caller-owned `hard_waits_s` (:3036, :3167), redacted upstream passthrough (:1250–1259), copilot (:1436); `runner_dispatch.py:76–182` has `model_id_ok`/`model_id_src`/`EXEC_NOTES` incl. copilot; all seven CLI subcommands the SKILL.md invokes exist in `ai_kit_spec_gsd/cli.py`; adapter reasons `unsupported_model_id`/`unsafe_hook_token` match; description is 820 chars (under the 1024 cap); anchor links resolve. The skill never switches harness/provider/model itself — re-resolution after failure is explicitly forbidden (SKILL.md:20–24, 45, 459).

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 19 | 20 | GSD hook word-split/glob semantics, adapter-owned keys, exit-code contract, gsd-core trust model — none derivable; −1 for restating the stop ladder the canonical policy also carries |
| D2 Mindset + Procedures | 13 | 15 | Explicit "Mindset" block with WHY; 25.1 dropped the plan-opt-in thinking bullet, leaving enforcement inline only |
| D3 Anti-Pattern Quality | 14 | 15 | NEVER list is specific with non-obvious reasons (skip = silent harness switch; re-resolve rewrites the hook; exit 2 = no JSON exists) |
| D4 Spec Compliance | 15 | 15 | Valid name; 820-char description with WHAT + three WHEN scenarios + keywords (`.planning/config.json`, `cross_ai: true`, `model_profile_overrides`) |
| D5 Progressive Disclosure | 12 | 15 | Good conditional triggers (MANDATORY sibling read at the stop point; "read only if you need the why" + anchors), but 487-line body with big inline code blocks |
| D6 Freedom Calibration | 14 | 15 | Low freedom exactly where config corruption is possible; owner kept as decision-maker |
| D7 Pattern Recognition | 8 | 10 | Clear Process pattern with Tool-grade scripts; size (~2× the pattern's norm) is the deviation |
| D8 Practical Usability | 13 | 15 | Every mode, reason, exit code, marker pathology, scheduler-less host covered; density itself is the hazard |

## Findings

1. **Important** — `skills/ai-kit-spec-execute-gsd/SKILL.md:449-450`: the mandatory read is pinned by *section numbers* ("sections 4 and 6-8") into a sibling skill. A renumbered ai-kit-cross-ai silently misdirects the safety read that governs answering GSD's prompt. **Fix:** cite heading titles alongside numbers: "sections 4 (Read the result) and 6–8 (Hard tier and notice / GSD retry, skip, abort / Never switch)".
2. **Important** — `SKILL.md:174-179`: the permanent-reason list is one sentence whose parenthetical interleaves four reason codes with a definition of only `no_usable_dispatch`; a loaded reader can misattribute that definition (or miss that `quota_exhausted` alone is resumable). **Fix:** one bullet per reason, marked `permanent` / `resumable`, definitions out of the parentheses.
3. **Important** — `SKILL.md:383-417`: the marker-guarded guidance insertion is a ~35-line Python heredoc the agent must transcribe byte-perfect each run, while the equally delicate `write-resumable-state` got a CLI subcommand — inconsistent, and quoting/indent transcription is the most likely failure mode in this skill. **Fix:** add a `prepare-tooling-insert` subcommand to `ai_kit_spec_gsd/cli.py` and reduce Step 3 to one call.
4. **Minor** — `SKILL.md:461-472`: "whose prompt is exactly this text" precedes a template containing `<PHASE_ID>` and `<RESUME_STATE_PATH>` placeholders — substitution is implied, never stated. **Fix:** "…with `<PHASE_ID>` and `<RESUME_STATE_PATH>` substituted, otherwise verbatim."
5. **Minor** — `SKILL.md:188-194`: the 25.1 diff deleted the plan-opt-in "ask yourself" bullet; the check survives only inline at :209-212/:324-327. **Fix:** restore one mindset bullet ("before any cross-AI write, confirm the plan's own `cross_ai: true` — a workflow-level write alone never delegates").
6. **Minor** — `references/dispatch-notes.md:43-52`: the History section narrates two superseded designs at near-body length; it is correctly labeled optional, but could compress to the last paragraph only.

DIGEST bd7a28b0f98eae98
CURRENT 108/120
CRITICAL 0 IMPORTANT 3

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=183s out=359070 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
