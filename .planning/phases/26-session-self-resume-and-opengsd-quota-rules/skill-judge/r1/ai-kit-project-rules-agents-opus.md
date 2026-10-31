Judge: opus
Reviewed-sha256: 06ef499ae59c57f92188a9ec3fb8005423d08d836e3a9264f0f476c404604eeb
Lane: native subagent completed
Score: 89
Critical: 1
Important: 3

# Skill Evaluation Report: ai-kit-project-rules-agents

## Summary
- **Total score**: 89/120 (74%), grade C
- **Pattern**: Process. It runs the checker, confirms near-misses, then hands off once to `/agent-md-refactor`.
- **Knowledge ratio (E:A:R)**: about 70:20:10
- **Verdict**: The skill carries real knowledge specific to this project: substring-signal matching, routing by signals and not by category, a single-invocation hand-off and the verbatim R18/R19/R20 rules. But Step C tells the agent to paraphrase rule summaries it has no signal list for. It never re-runs the check afterwards. So an agent that follows it exactly can report a remediation as done while the checker still flags the rules.

Claims I checked and found true:
- 20 rules: `rules.py:1`, `:49-305`
- R18, R19 and R20 have `verbatim: True`: `rules.py:278`, `:292`, `:303`
- R02 has category `makefile`: `rules.py:64`
- Rules are filtered by signals, not by category: `classification.py` `check_rules`
- `notices` come from `unverified` findings: `remediation.py` `build_remediation`
- The stderr path print: `cli.py` `_opengsd_presence`
- The realpath-based `ImportError`: `ai_kit_project_rules_agents/__init__.py:11-23`
- Image links are matched and anchor-only links are skipped: `cli.py` `_LINK_RE`, `_parse_link_target`

## Dimension Scores
- **D1 Knowledge Delta: 15/20.** The substring-matching trap, category versus signals, and why `/agent-md-refactor` must run only once are all knowledge the model would not have. Points lost to internal decision IDs (D-05) and a wrap explanation that is longer than it needs to be (line 53).
- **D2 Mindset + Procedures: 11/15.** The A/B/C sequence and the named injection point are good. There is no verify step after the refactor.
- **D3 Anti-Patterns: 12/15.** The NEVER rules are specific and give reasons. The first one (lines 67-76) is undercut by Step C (line 61) and states its threshold wrongly.
- **D4 Specification: 12/15.** The frontmatter is valid and the description has a "Use when" and a quoted trigger phrase. It is thin on keywords (no "broken links", "remediate", "house rules audit"). It does not route whole-repo requests to `ai-kit-project-rules-all`.
- **D5 Progressive Disclosure: 12/15.** At 106 lines it is self-contained. Line 106 points at `rules.py` but never tells the agent when it must read it, which is to get the signals before writing any content.
- **D6 Freedom Calibration: 10/15.** Freedom is low where it should be (one invocation, verbatim blocks). It is high where the content is fragile: line 61 lets the agent paraphrase text that is matched by literal substrings.
- **D7 Pattern: 8/10.** A clear Process pattern with checkpoints.
- **D8 Practical Usability: 9/15.** There is no re-check loop, R20's extra fields are not handled, the one-hop link scope is not stated, there is no fallback when the import fails, and the example payload is inaccurate.

## Findings

1. **Critical. SKILL.md:61 (with :72 and :106).** Step C says "Every other entry's summary is paraphrased". The `remediate` payload does not carry a rule's signals; `missing` entries have `matched_signals: []` (`remediation.py`). Most summaries do not contain enough of their own signals to pass.
   - I ran each summary unchanged through `check_rules` against its own rule, with conditions met. These came back `near_miss`: R01, R02, R03, R08, R14 and R17. R12, a criticality-1 rule, came back `missing` (`rules.py:199-204`).
   - So inserting the summary word for word already fails, and paraphrasing it only makes that worse. The anti-pattern at lines 67-76 says the signal phrases must appear verbatim, but nothing tells the agent where to find them.
   - **Fix:** In Step C, before the hand-off, read `rules.py` and take each entry's `signals`. Require each inserted clause to contain enough of them to classify as `present`. Alternatively, have `build_remediation` carry `signals` forward the way it already carries `verbatim`. Then reword line 61 to "paraphrase freely, but keep the signal phrases".

2. **Important. SKILL.md:55-63.** Nothing is checked after the `/agent-md-refactor` pass. The agent is never told to run `check` again and confirm that every Step B entry is now `present` and `links` is empty. Finding 1 would be caught by that one step, and so would links broken by the refactor's file split.
   - **Fix:** Add a Step D. Run `check` again, list every Step B id that is still `missing` or `near_miss`, and fix them by direct edit. Do not run a second refactor pass, which keeps the once-per-run rule from line 81.

3. **Important. SKILL.md:61.** R20 entries carry `hardcoded_counts`, `stacks` and `unverified_stacks` (`remediation.py:35`).
   - Any hardcoded count forces R20 to `near_miss` (`classification.py:255-256`). Inserting the verbatim block does not remove the existing offending lines, so R20 stays a near-miss for good.
   - The skill never mentions these fields.
   - **Fix:** For R20, show the user the `hardcoded_counts` lines in Step A. On confirmation, replace each one with the CPU-share form along with the inserted block. Say that a clause for an unverified stack is inserted as given and labelled unverified.

4. **Important. SKILL.md:37 and :61.** Rule signals are matched against the root file plus one hop of linked files.
   - The linked files must be same-repo relative links, at most 20 of them, and links inside fenced code do not count (`cli.py:25`, `:82-127`, `:130-158`).
   - When both files exist, `AGENTS.md` is read and `CLAUDE.md` is ignored (`cli.py:137-144`).
   - `/agent-md-refactor` exists to split content into linked files. A rule it moves two hops deep, or behind link 21, will be reported `missing` again.
   - **Fix:** Add one line to Step C: house-rule clauses must stay in the root file or in a file the root links to directly, and they must not sit inside code fences.

### Minor
5. **SKILL.md:72.** "≥50%-of-signals threshold" holds only for flat rules with three or more signals (`classification.py:115`). Grouped rules R04, R19 and R20 need every group to match. Reword it.
6. **SKILL.md:39-49.** The "trimmed" example leaves out the `notices` key that line 37 says is always returned. It also shows R05 with `criticality: 2`, while `rules.py:108` gives it 3 (MEDIUM). Add `"notices": []` and change the value to 3.
7. **SKILL.md:17-28.** The loop stops at the first candidate that exists. If that is a copy-install that fails to import, it never falls through to a working symlink. Say: on `ImportError`, try the next candidate or run `tools/setup.py`. Also, the claim at line 28 that copies fail "by design" is too broad. A symlink in the opencode or `~/.agents` directory resolves through realpath and imports fine.
8. **SKILL.md:59 and :100.** "D-05" is an internal planning ID that means nothing to an executing agent. Drop it.
9. **SKILL.md:3.** The description could add "broken links" and "CLAUDE.md audit" as keywords. It should also say that whole-repo "check everything" requests go to `ai-kit-project-rules-all`.

## Top 3 Improvements
1. Give the agent the signal list and make keeping it intact a hard requirement in Step C (finding 1).
2. Add a re-check step after the hand-off (finding 2).
3. Handle R20's `hardcoded_counts` and state the one-hop link scope (findings 3 and 4).

I evaluated only SKILL.md, the listed package file. I did not run the CLI against a real repository. The "summary fails its own check" result comes from calling `check_rules` directly on each summary with all conditions met; R06 and R20 were left out of that run.
