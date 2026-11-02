# In-session skill-judge, execute side (plan 18.1-22)

The executing agent applied `tmp/judge/rubric.md` (the installed skill-judge
rubric, copied read-only) to each skill, comparing the whole skill directory at
`a8e24c3` (BASELINE) with the working tree (CURRENT). Pass rule: (`CRITICAL 0`
and `IMPORTANT 0`) or `CURRENT >= 96`, and `CURRENT >= BASELINE`.

## ai-kit-spec-execute-superpowers

Digest judged: `a4578575c8fd0103`.

| Dimension | BASELINE | CURRENT | Notes |
|---|---:|---:|---|
| D1 Knowledge Delta | 17 | 18 | Both are repo-specific dispatch knowledge. CURRENT adds the native-versus-subprocess and session-default distinction. |
| D2 Mindset + Procedures | 13 | 13 | The "never persist the working exclusion union" framing transfers judgment; the procedures are domain-specific. |
| D3 Anti-Pattern Quality | 14 | 14 | Each NEVER item names the concrete failure it prevents. |
| D4 Specification Compliance | 14 | 14 | Valid frontmatter; description states WHAT, WHEN and the `executing-plans` exclusion. |
| D5 Progressive Disclosure | 12 | 12 | Mandatory reference triggers are present; design notes stay conditional. |
| D6 Freedom Calibration | 12 | 11 | Exact commands constrain fragile state handling; CURRENT leaves the rounds 4-5 native bump to hosts it says cannot select a model. |
| D7 Pattern Recognition | 9 | 9 | Resolve, inject, classify, hand back. |
| D8 Practical Usability | 12 | 12 | Quota, trust and report-preservation branches are executable as written. |
| Total | 103 | 103 | |

CURRENT findings: Important — non-Claude native execution has no actionable rounds 4-5 path (`SKILL.md:181-187`). Minor — the non-quota stop list calls `capacity` and `git_timeout` things waiting never fixes (`SKILL.md:155-163`). No Critical.

BASELINE 103/120
CURRENT 103/120
CRITICAL 0
IMPORTANT 1

## ai-kit-spec-execute-gsd

Digest judged: `06975d43903c03bb`.

| Dimension | BASELINE | CURRENT | Notes |
|---|---:|---:|---|
| D1 Knowledge Delta | 16 | 17 | CURRENT adds runner rendering, the unsafe-hook-token rule and the glob guard. |
| D2 Mindset + Procedures | 13 | 13 | "Resolve fresh every run" and the opt-in check shape the decision. |
| D3 Anti-Pattern Quality | 13 | 14 | Never hand-edit, never trust without consent, never a raw vendor string. |
| D4 Specification Compliance | 4 | 15 | BASELINE's unquoted description holds `cross_ai: true` and is invalid YAML; CURRENT quotes it. |
| D5 Progressive Disclosure | 12 | 11 | History stays in the reference, but the body grew with the recipes. |
| D6 Freedom Calibration | 11 | 12 | Recipes now check each mutation's status and stop on a failed cleanup. |
| D7 Pattern Recognition | 8 | 8 | Resolve, act, hand off. |
| D8 Practical Usability | 9 | 12 | Step 1 prints every field later steps need; the scratch file stays under `tmp/`. |
| Total | 86 | 102 | |

CURRENT findings: Important — a phase file that already carries the older single marker keeps its stale guidance beside the new block (`SKILL.md:334-344`). Minor — runner setup and confinement are repeated between the body and `references/dispatch-notes.md`. No Critical.

BASELINE 86/120
CURRENT 102/120
CRITICAL 0
IMPORTANT 1

## ai-kit-gsd-curated-config

Digest judged: `0e768ddecc55f010`.

| Dimension | BASELINE | CURRENT | Notes |
|---|---:|---:|---|
| D1 Knowledge Delta | 18 | 18 | Ownership, workstreams, the runner template and the v1/v2 split are all repo-specific. |
| D2 Mindset + Procedures | 13 | 14 | CURRENT adds "readiness is the JSON, not the `.new` file". |
| D3 Anti-Pattern Quality | 14 | 14 | Concrete prohibitions: never hand-edit, never retry a refusal blindly. |
| D4 Specification Compliance | 15 | 15 | Valid frontmatter; description states WHAT and WHEN. |
| D5 Progressive Disclosure | 13 | 12 | No `references/` directory; the full v1 path stays in the body. |
| D6 Freedom Calibration | 14 | 14 | Exact subcommand flags with the exit-code table. |
| D7 Pattern Recognition | 9 | 9 | Inventory, recommend, plan, apply. |
| D8 Practical Usability | 13 | 14 | Exit 0 on `apply-execution` now requires reading `degraded_reason` before claiming success. |
| Total | 109 | 110 | |

CURRENT findings: Minor — the `ensure-runner` table row repeats the upgrade rules given in the runner section; the v1 path is always loaded. No Critical, no Important.

BASELINE 109/120
CURRENT 110/120
CRITICAL 0
IMPORTANT 0
