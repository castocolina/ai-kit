Native Opus (clean context), ai-kit-gsd-spec-discuss, 2026-10-24 r1. 105/120. D1 18 D2 13 D3 14 D4 14 D5 13 D6 13 D7 9 D8 11.
1. Important: a forced column never becomes decided_by (decide.py:524 picks only fallback False), so decision-table rows 2/4/5 cannot apply a forced answer as written (row 5 matches own_reasoning literally). Fix: before row 1, "when any column is forced, ignore decided_by and apply this note first"; add tie-break: forced local consistent with evidence vs high remote disagreeing -> evidence decides, both logged; still split -> own reasoning, ledgered.
2. Important: setup check passes configured_empty (init.cjs:3851; its warning is a direct stderr write, not in JSON warnings[]) and never names configured_unresolved (:3866). Fix: success = reason == "resolved" and warnings empty; bullets for configured_empty and configured_unresolved.
3. Important: the advisor no-jev instruction points at analyzer-brief.md, which the interactive path may never load; the brief's passage (analyzer-brief.md:47-50) now sits inside the analyzer's text prompt with orchestrator-only text. Fix: put the exact one-sentence advisor instruction inline in SKILL.md §2; keep the brief's prompt to the analyzer-facing sentence; move the advisor note to "Why each block exists".
4. Minor: GSD="$GSD_TOOLS" then node "$GSD" breaks on the resolver's PATH-shim branch (gsd-run-resolver.md:7); later steps still say gsd_run. Fix: shim branch runs "$GSD" directly; use the resolved GSD command throughout.
5. Minor: log-formats.md:46 attribution lacks (forced). Fix: 0.NN[ (fb)| (forced)].
6. Minor: the || text fallback is dead (gsd-core supports --json, exits 0); GSD_WS is never set by this skill; the advisor is checked on the auto path where it never runs. Fix: drop fallback, say GSD_WS comes from --ws passthrough, check the advisor only on the interactive path.
7. Minor: "any other WARNING ... same fix" is false for runtime-caused warnings (init.cjs:3701,3707). Fix: re-running curated-config fixes only path and wiring causes.
DIGEST fd393fba782b5b56
CURRENT 105/120
CRITICAL 0 IMPORTANT 3
