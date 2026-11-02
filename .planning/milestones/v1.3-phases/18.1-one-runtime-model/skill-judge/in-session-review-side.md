# In-session skill-judge, review side (plan 18.1-21)

Executing agent, same rubric as the pi judges (`tmp/judge/rubric.md`, 120
points, D1–D8). Baseline is the whole skill directory at `a8e24c3`; current is
the working tree. Digest is DIGEST_CMD over `SKILL.md` plus `references/`.

## ai-kit-spec-review

Digest judged: `f87405ed2efe9722`.

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| D1 Knowledge Delta (20) | 17 | 17 | Routes, runner argv, trust consent, fail-closed merge |
| D2 Mindset + Procedures (15) | 13 | 13 | Step 0.7 routing and verbatim prompts unchanged in kind |
| D3 Anti-Pattern Quality (15) | 14 | 14 | NEVER list kept, each with a reason |
| D4 Specification Compliance (15) | 14 | 14 | Frontmatter names the trigger and the flags |
| D5 Progressive Disclosure (15) | 11 | 11 | Body still long; dispatch detail already offloaded |
| D6 Freedom Calibration (15) | 14 | 14 | Exact subcommands; judgment left to the user |
| D7 Pattern Recognition (10) | 9 | 9 | Process loop with reference offload |
| D8 Practical Usability (15) | 13 | 13 | One-runtime wording; the failure table stays |
| **Total** | **105/120** | **105/120** | No regression |

The rewrite is a terminology and dispatch-model change (pairs, routes, the
runner) over a skill whose procedure was already strong. Findings are the same
class as the baseline's: body length, and host-tool names (`Skill`, `Agent`)
that the skill has always required.

BASELINE 105/120
CURRENT 105/120
CRITICAL 0
IMPORTANT 0

## ai-kit-spec-config

Digest judged: `f47c9994e0c7474c`.

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| D1 Knowledge Delta (20) | 17 | 17 | Landmines kept: bare codex id, cursor ids, `purpose` |
| D2 Mindset + Procedures (15) | 12 | 12 | Quota and strength fit first; factory-first stays |
| D3 Anti-Pattern Quality (15) | 13 | 13 | NEVER list rewritten to the new terms, reasons intact |
| D4 Specification Compliance (15) | 13 | 13 | Description covers WHAT, WHEN and the flags |
| D5 Progressive Disclosure (15) | 13 | 13 | Ranking stays in the reference; body grew |
| D6 Freedom Calibration (15) | 14 | 14 | Fragile writes stay behind the factory subcommands |
| D7 Pattern Recognition (10) | 9 | 9 | Process + Tool rigor, applied consistently |
| D8 Practical Usability (15) | 13 | 13 | Session-default versus alias split, used everywhere |
| **Total** | **104/120** | **104/120** | Matches the recorded D-16 baseline; no regression |

BASELINE 104/120
CURRENT 104/120
CRITICAL 0
IMPORTANT 0

## ai-kit-opencode-providers

Digest judged: `222394e99469f32d`.

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| D1 Knowledge Delta (20) | 18 | 18 | Config/auth split, inactive tiers, non-object values |
| D2 Mindset + Procedures (15) | 14 | 14 | Identify the provider kind, then let the helper act |
| D3 Anti-Pattern Quality (15) | 14 | 15 | Warning now names `runtime`, legacy `cli`, `model` |
| D4 Specification Compliance (15) | 15 | 15 | Frontmatter: capability, triggers, exclusions |
| D5 Progressive Disclosure (15) | 13 | 13 | Compact; the non-object rule repeats a little |
| D6 Freedom Calibration (15) | 12 | 12 | JSONC edits stay inside the bundled CLI |
| D7 Pattern Recognition (10) | 9 | 9 | Tool pattern: scope, resolution, commands, interpretation |
| D8 Practical Usability (15) | 12 | 12 | Exit codes and the no-op cases are concrete |
| **Total** | **107/120** | **108/120** | One-line accuracy fix; no regression |

BASELINE 107/120
CURRENT 108/120
CRITICAL 0
IMPORTANT 0
