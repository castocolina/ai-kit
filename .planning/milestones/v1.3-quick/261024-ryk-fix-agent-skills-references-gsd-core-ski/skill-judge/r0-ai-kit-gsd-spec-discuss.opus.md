Native Opus (clean context), ai-kit-gsd-spec-discuss, 2026-10-24 r0.
106/120 (B). D1 17, D2 13, D3 14, D4 14, D5 14, D6 13, D7 9, D8 12.
1. Important: the never-calls-jev rule covers only gsd-assumptions-analyzer, but SKL-04 also wires jev into gsd-advisor-researcher, which the interactive discuss path spawns with AGENT_SKILLS_ADVISOR (discuss-phase.md:121); SKILL.md:152-155 and analyzer-brief.md:47-48,58-59 forbid jev only for the analyzer. Fix: say neither agent calls jev; add the no-jev line to the advisor's spawn prompt.
2. Minor: "(SKL-04)" at SKILL.md:153 is an ai-kit-internal id meaningless in other projects. Fix: drop it.
3. Minor: the cause list covers 2 of about 9 gsd-core warning shapes (init.cjs:3663,3701,3707,3740,3765,3861) and silence is not defined. Fix: a catch-all bullet and "no output = wiring clean".
4. Minor: the loop drops --ws, so inside a GSD workstream it reads a different config than discuss-phase(-assumptions).md:71/121. Fix: append ${GSD_WS:+--ws=${GSD_WS##* }}.
DIGEST 4c33bda55ff6ed04
CURRENT 106/120
CRITICAL 0 IMPORTANT 1
