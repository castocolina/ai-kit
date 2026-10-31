Judge: my-referee-two
Reviewed-sha256: 65138f8de4f47675096c37ffb13c17825c9e169b25e92c6aa10238a6bf2dbd82
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=210s out=170747 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 105
Critical: 0
Important: 0

# Skill Evaluation Report: ai-kit-project-rules-all

**File**: `skills/ai-kit-project-rules-all/SKILL.md` (181 lines, no references dir; entry code `ai-kit-project-rules-all.py` + `ai_kit_project_rules_all/{cli,dispatch,aggregate}.py` shipped beside it)
**Pattern**: Navigation/orchestrator · **Knowledge ratio**: E:A:R ≈ 85:13:2 · **Grade**: B (87.5%)
**Verdict**: A tight, honest orchestrator skill whose every checkable claim matches the shipped code; only cosmetic wording tensions remain.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1 Knowledge Delta | 17 | 20 | Near-pure project-specific delta (family contract, dispatch semantics, tie-break, failure isolation); the field-preservation contract is stated twice (l.12–17, l.136–139) |
| D2 Mindset + Procedures | 13 | 15 | Domain procedures (resolve→run→act) plus a real thinking trap ("nothing forces reading all four lists", l.161–162) |
| D3 Anti-Pattern Quality | 14 | 15 | Five specific NEVERs, each with a mechanism-level reason (l.166–176) |
| D4 Specification Compliance | 13 | 15 | Valid frontmatter; description has WHAT/WHEN/KEYWORDS plus explicit negative routing; slight overclaim (finding 1) |
| D5 Progressive Disclosure | 13 | 15 | Single 181-line file; MANDATORY on-demand trigger to the sibling's Wrap mechanism embedded at the decision point (l.127–129); no "Do NOT load" for the other five sibling bodies |
| D6 Freedom Calibration | 13 | 15 | Correctly low-freedom for a fragile aggregation: exact commands, pinned semantics, never-reclassify/never-auto-apply fences |
| D7 Pattern Recognition | 9 | 10 | Clean Navigation pattern: minimal own logic, routes to six sub-skills |
| D8 Practical Usability | 13 | 15 | Four-list decision tree, two complete example payloads, failure isolation, trust note; placeholder-path gap (finding 2) |

## Factual claims — all verified against the repository

- Usage string, exit 0 on help, `unknown subcommand:` on stderr exit 2, `repo_root` default `.` (SKILL.md l.65–67) → `ai_kit_project_rules_all/cli.py:38–51`
- `check`/`remediate` byte-identical four-key shape (l.74–76) → `cli.py:22–34` (`remediate` returns `check(...)`), pinned by `tests/test_ai_kit_project_rules_all.py:176`
- Global ascending criticality sort of `remediate`/`blocked`, `notices` in domain order unsorted (l.78–90) → `aggregate.py:37–47`
- `failed` shapes, four failure modes, pass-through of remediate-less JSON, no double-listing (l.83–87) → `dispatch.py:95–139`, `aggregate.py:39–44`
- `hand_off` added only to `workflow`-kind remediate entries (l.13–15) → `aggregate.py:49–51`
- Sequential dispatch, 30 s per-domain timeout (l.143–145) → `dispatch.py:25,40,104–110,142–147`
- 5-candidate resolution, checkout-first, `<name>/<name>.py`, never `$PATH`, failed-not-silent-skip (l.51–56) → `dispatch.py:43–80,95–101`
- Tie-break order agents→makefile→precommit→arch→docker→cicd (l.158–160) → `dispatch.py:25` + stable sort `aggregate.py:46–47`
- Broken-link findings not carried; sibling reports them only via `check` (`links`) and `-all` calls sibling `remediate` (l.155–157) → `dispatch.py:105`; `ai_kit_project_rules_agents/cli.py:196,199–217`; agents SKILL.md:39
- Trust note: gsd-tools `runtime-identity` runs only when `.planning/` exists, path printed to stderr, stderr captured (l.69–72) → `ai_kit_project_rules_agents/cli.py:161–175`; `dispatch.py:104–110` (`capture_output=True`)
- Wrap mechanism with Steps A–D, near-miss confirmation, `verbatim: true` insertion, signals preservation, single `/agent-md-refactor` invocation, re-check (l.127–132) → `skills/ai-kit-project-rules-agents/SKILL.md:56–70`
- Example findings are real: R01 signals (l.104) → `rules.py:55`; arch example text including the literal `'test''s recipe` and "No language-stack marker file" phrasing (l.117) → `arch_checker.py:145–155`, `canonical_tools.py:60`
- All six siblings exist with `check|remediate [repo_root]` CLIs the fan-out depends on → each sibling `cli.py` (makefile:93, precommit:126, arch:32, docker:33, cicd:31, agents:223)

## Findings

1. **Minor** — `SKILL.md:3` — The description says it "merges their `check`/`remediate` findings", but Limits #5 (`SKILL.md:155–157`) states check-only findings (broken `links`) are never carried, and `dispatch.py:105` only ever invokes sibling `remediate`. Fix: say "merges their `remediate` findings" (the sibling `remediate` already subsumes its `check`), or add "(check-only `links` findings excepted)".
2. **Minor** — `SKILL.md:39,48–49` — The resolve snippet's first candidate is `dirname "<absolute path to THIS SKILL.md>"`; on a host that injects the skill body without exposing its file path, that candidate cannot be formed and only the doc's "stop and report not installed" fallback remains, even though a checkout copy exists that `dispatch.py`'s own from-realpath walk would have found. Fix: add one line — "if the host gives no path, fall back to the candidate list from the other four locations".
3. **Minor** — `SKILL.md:12–17` vs `136–139` — The never-overwrite/never-reclassify contract is stated twice in near-identical words; ~4 lines of token cost. Fix: state it once in Scope and reference it from "Act on the report".
4. **Minor** — `SKILL.md:127–132` — Only the agents sibling's SKILL.md is gated as a mandatory on-demand read; no "do NOT load the other five siblings' SKILL.md bodies" guidance, so an agent could pull five unrelated documents into context. Fix: one sentence: "Do not load any other sibling's SKILL.md in this flow; the payloads carry everything."

Not checked: runtime behavior of the six siblings' checker logic itself (only their CLI surface and the cited strings), and host-specific activation behavior of the description on non-Claude runtimes.
