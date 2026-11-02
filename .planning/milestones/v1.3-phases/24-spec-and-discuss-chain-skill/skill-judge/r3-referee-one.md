DIGEST 7fc3f03ffb2fb714
# Skill evaluation: `ai-kit-gsd-spec-discuss`

**Score: 101/120 (B, 84%).** The skill provides substantial GSD-specific judgment and operational knowledge. Its main weakness is coordination: a few instructions conflict with the artifacts and timing the workflow requires. The 257-line `SKILL.md` uses a **Process** pattern; the four references are conditionally loaded. Estimated knowledge mix: **75% expert, 20% activation, 5% redundant**.

| Dimension | Score | Evidence |
|---|---:|---|
| D1 Knowledge Delta | 17/20 | The workflow distinctions and edge-floor rules are specific, useful knowledge ([SKILL.md:91–106](skills/ai-kit-gsd-spec-discuss/SKILL.md#L91-L106)). |
| D2 Mindset + Procedures | 13/15 | “You are the decider” is paired with a concrete evidence-first decision ladder ([SKILL.md:16–20](skills/ai-kit-gsd-spec-discuss/SKILL.md#L16-L20); [decision-table.md:22–43](skills/ai-kit-gsd-spec-discuss/references/decision-table.md#L22-L43)). |
| D3 Anti-Patterns | 13/15 | The NEVER list names consequential mistakes and explains several of them ([SKILL.md:219–238](skills/ai-kit-gsd-spec-discuss/SKILL.md#L219-L238)). |
| D4 Specification | 15/15 | Valid name and a description covering purpose, triggers, keywords, and exclusions ([SKILL.md:1–4](skills/ai-kit-gsd-spec-discuss/SKILL.md#L1-L4)). |
| D5 Progressive Disclosure | 14/15 | Mandatory reads sit at workflow triggers, with conditional example loading and “Do NOT load” guidance ([SKILL.md:77](skills/ai-kit-gsd-spec-discuss/SKILL.md#L77); [SKILL.md:247–257](skills/ai-kit-gsd-spec-discuss/SKILL.md#L247-L257)). |
| D6 Freedom Calibration | 12/15 | Fragile operations have precise guards; decisions remain evidence-led, though some pacing instructions are too rigid ([SKILL.md:180–193](skills/ai-kit-gsd-spec-discuss/SKILL.md#L180-L193); [SKILL.md:210–217](skills/ai-kit-gsd-spec-discuss/SKILL.md#L210-L217)). |
| D7 Pattern Recognition | 8/10 | A clear phased Process pattern, weakened by inconsistent commit and checkpoint language ([SKILL.md:79–145](skills/ai-kit-gsd-spec-discuss/SKILL.md#L79-L145)). |
| D8 Practical Usability | 9/15 | Decision cases and log templates are actionable, but the timing and recovery gaps below can mislead an agent ([decision-table.md:52–63](skills/ai-kit-gsd-spec-discuss/references/decision-table.md#L52-L63); [log-formats.md:63–104](skills/ai-kit-gsd-spec-discuss/references/log-formats.md#L63-L104)). |

## Findings

**Critical: none.**

1. **Important — The commit promise contradicts the procedure.** The description promises “one commit per phase” ([SKILL.md:3](skills/ai-kit-gsd-spec-discuss/SKILL.md#L3)), but the spec workflow commits the SPEC, the discuss step makes another phase commit, and the run makes a separate state commit ([SKILL.md:98](skills/ai-kit-gsd-spec-discuss/SKILL.md#L98); [SKILL.md:112–117](skills/ai-kit-gsd-spec-discuss/SKILL.md#L112-L117); [SKILL.md:142–143](skills/ai-kit-gsd-spec-discuss/SKILL.md#L142-L143)). State the intended commit unit accurately rather than giving agents incompatible targets.
2. **Important — Analyzer concurrency has an unmet dependency.** The skill permits starting the analyzer while writing the same phase’s CONTEXT ([SKILL.md:212–216](skills/ai-kit-gsd-spec-discuss/SKILL.md#L212-L216)), although its alternatives and questions feed that phase’s decisions ([SKILL.md:122–140](skills/ai-kit-gsd-spec-discuss/SKILL.md#L122-L140); [analyzer-brief.md:42–48](skills/ai-kit-gsd-spec-discuss/references/analyzer-brief.md#L42-L48)). Require its completed result before finalizing or committing analyzer-dependent decisions.
3. **Important — An early stop leaves the state checkpoint unspecified.** Blocking, unresolved items stop the run ([SKILL.md:192–193](skills/ai-kit-gsd-spec-discuss/SKILL.md#L192-L193)), while `state.record-session` is prescribed only “After the range” ([SKILL.md:142–143](skills/ai-kit-gsd-spec-discuss/SKILL.md#L142-L143)). Specify how to record the stopping point without misrepresenting unfinished phases.
4. **Minor — A forced high-confidence result looks like a low-confidence fallback in logs.** Forced `fallback: true` can count as high ([decision-table.md:16–20](skills/ai-kit-gsd-spec-discuss/references/decision-table.md#L16-L20)), but the prescribed `(fb)` cell covers both below-threshold and size-cap cases ([log-formats.md:8–10](skills/ai-kit-gsd-spec-discuss/references/log-formats.md#L8-L10)). Add a distinct forced-result notation or reason to preserve the audit trail.

**Top fixes:** reconcile the commit contract; put an explicit wait before analyzer-dependent CONTEXT decisions; define the stopped-run state checkpoint.

Read-only review; I did not execute GSD workflows or test live backends, so runtime behavior remains unverified.

CURRENT 101/120
CRITICAL 0
IMPORTANT 3
