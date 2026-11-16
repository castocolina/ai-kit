# Loop 33, round 3, ai-kit-spec-config: fixes under the 3-or-fewer rule

Round 3 left 2 findings of severity critical, important or high across both judges (referee-one D8-1 and
D8-2, both high), so they were fixed in the skill's own files with no further judge round (AGENTS.md
skill-judge rule, 2026-11-16). The fix commit is the commit that adds this file:
`git log --format=%h -1 -- .planning/judge/verdicts/33/ai-kit-spec-config/r3/fixes.md`.

The skill's digest is stale by design until its next judge loop; `judge_loop.py check` prints a
stale-digest note for it.

Fixed:

- referee-one D8-1 (high): `references/check-only.md` asked the write-risk question over the raw target
  file's entries only; it now lists the merged probe set with the same resolve and route calls
  `probe-quota` makes, and asks over exactly that set.
- referee-one D8-2 (high): `references/cli-model-selection.md` set `CATALOG_JSON` and
  `FILTERED_RUNTIMES_JSON` in one shell and read them in later ones; both are now literal paths.
- referee-one D8-3 (medium): SKILL.md Step 2.7 now states the writer's real default (no `purpose` goes to
  `[[lanes.review]]` only).
- referee-one D7-1 and referee-two D7-1 (medium): four unrelated negative trigger queries replaced with
  near-misses.
- referee-one D7-2 (medium): the global-write eval now has an existing global roster and asserts
  replacement consent.
- referee-two D6-1 (medium): the NEVER bullet no longer reads `--global`/`--local` as consent to replace.
- referee-two D8-1 (medium): Step 2.1 says a migrate-only request reports `migration pending`.
- referee-two D8-2 (low): Step 3 quotes Step 2.1's "replace the global roster" option.

Left for the next loop: referee-one D4-1 (description rewrite), referee-two D2-1 (inline filter
template), referee-two D5-1 (split cli-model-selection.md), referee-two D7-2 (artifact-graded evals),
and the low findings referee-one D1-1, referee-two D1-1, D3-1 and D4-1.
