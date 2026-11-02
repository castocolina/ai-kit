Judge: opus
Reviewed-sha256: 411587b8f417a8eb0de78907e5d6d76d8cefb15986499f215ef374e04749bfde
Lane: native subagent completed
Score: 102
Critical: 0
Important: 0

# Skill Evaluation Report: ai-kit-project-rules-agents

## Summary
- **Total score**: 102/120 (85%), grade B
- **Pattern**: Process. A phased check, then confirm, assemble, hand off and re-check, with checkpoints.
- **Knowledge ratio (E:A:R)**: about 75:20:5
- **Verdict**: A tightly sourced wrapper skill. Nearly every factual claim matches the code. What is left are small usability gaps in edge paths, not wrong guidance.

## Verification against the repository
The package file matches `skills/ai-kit-project-rules-agents/SKILL.md` byte for byte, apart from a trailing newline. It is 112 lines.

- **"20-rule ruleset"** (SKILL.md:3, :10, :112): verified. `rules.py` defines R01 to R20, and its docstring at rules.py:1 says "20-rule".
- **Root file selection** (SKILL.md:37): verified at `cli.py` `_resolve`. AGENTS.md wins, CLAUDE.md is the fallback. Links are followed one hop, only inside the repo (realpath containment), capped at `_MAX_LINKS = 20`, with fenced code dropped (`_without_fenced_code`). Image links, the `#` and `?` stripping, and skipping anchor-only, absolute and URL-scheme targets are all verified in `_parse_link_target` and `_LINK_RE`.
- **check and remediate shapes** (SKILL.md:39): verified.
  - `check` returns `{"workflow", "links"}` (cli.py `check`).
  - `build_remediation` drops `links`.
  - `blocked` stays empty because no structural kinds are present.
  - `notices` collects the `unverified` findings (`_shared/ai_kit_rules_common/remediation.py`).
  - `signals`, `verbatim`, `stacks`, `unverified_stacks` and `hardcoded_counts` are carried through by `_CARRIED_WORKFLOW_KEYS`.
- **Example JSON** (SKILL.md:41-54): consistent with the code. R05 with only "rtk" matched is 1 of 3 phrases, below ceil(3/2)=2, so `near_miss`. `auto_apply` equals `status == "missing"`.
- **Step C thresholds** (SKILL.md:66): exactly match `_classify_flat` (all phrases, or at least ceil(n/2) when n >= 3), `_classify_plain_groups` and `_classify_tool_scoped_groups`.
- **"R01, R12 fail on their own summary"**: verified.
  - R01's summary contains only "english-only", so it is `near_miss`.
  - R12's summary says "absolute filesystem paths" and "repo-root-relative resolution", neither of which is a signal phrase, so it is `missing`.
- **Verbatim rules**: verified. R18, R19 and R20 carry `verbatim: True`, and the R18 and R19 summaries contain their own signals.
- **R20 near_miss whenever counts exist**: verified at `_stack_form_status`.
- **R02 category anti-pattern** (SKILL.md:94-100): verified. `check_rules` filters on non-empty `signals`, and R02 has `category: "makefile"`.
- **Entrypoint import guard** (SKILL.md:28): verified. `ai_kit_project_rules_agents/__init__.py` raises `ImportError` when `_shared/ai_kit_rules_common` is missing beside the realpath-resolved skill directory.
- **/agent-md-refactor phase names and confirmation gate** (SKILL.md:58): unverified. That skill is not in this repository.
- **Stale counts outside the package**: `rule_checker.py:9` still says "17-rule `RULES` tuple". The installed copy's description, shown in this session's skill listing, also says 17. Both are outside the package, but the stale docstring is a repository defect worth fixing alongside this skill.

## Dimension scores
- **D1 Knowledge Delta: 17/20.** The expert content is real:
  - classification by substring matching, with exact thresholds;
  - why the hand-off is a single invocation;
  - the trap where R02's category does not decide whether it is checked;
  - the blind spots (rules two links deep or inside a code fence are invisible to the check).

  Small redundancy: the single-invocation reasoning appears at :58, :66 and again at :87-89, and :68 is long on invocation mechanics.
- **D2 Mindset and Procedures: 12/15.** The procedures are domain-specific and in a non-obvious order: confirm before the refactor, one pass, re-check with direct edits only. There is less "ask yourself" framing, for example how to judge whether a near-miss is already intentionally covered.
- **D3 Anti-Patterns: 13/15.** Five specific NEVERs, each with a reason. One cites real evidence ("9 false-'missing' findings"). Two of them repeat body text.
- **D4 Specification and Description: 14/15.** The frontmatter is valid. The description covers what it does and when to use it, has good keywords (AGENTS.md, CLAUDE.md, audit, missing workflow rules, broken relative links), names the wrap, and routes whole-repo requests to `ai-kit-project-rules-all`.
- **D5 Progressive Disclosure: 13/15.** At 112 lines it is self-contained and points at `rules.py` instead of restating the rules. Some paragraphs are long and dense (:58, :62, :66).
- **D6 Freedom Calibration: 13/15.** Low freedom where it matters (verbatim blocks, signal thresholds, a single pass) and medium freedom for paraphrasing. Step A's hard STOP has no stated behavior for unattended runs.
- **D7 Pattern: 8/10.** A clear Process shape with checkpoints. The Scope section and the Ruleset reference section partly overlap.
- **D8 Practical Usability: 12/15.** It handles no importable install, no root file, unverified notices, broken links and stacks with no verified form. The edge-path gaps are listed below.

## Findings (all minor; none count toward Critical or Important)
1. **Minor, SKILL.md:16-34.** Line 16 says to record the entrypoint as a literal absolute path, but the run block uses `"$ENTRYPOINT"`, and shell state does not persist between calls. Fix: write `python3 <ENTRYPOINT> check <repo_root>`, or say "substitute the recorded path".
2. **Minor, SKILL.md:66.** For tool-scoped signals (R06) it says "one phrase for each installed tool". The `remediate` entry does not carry `missing_tools` (`_CARRIED_WORKFLOW_KEYS`), so the agent cannot tell which tools are installed and may write advice for tools that are absent. Fix: point at `check`'s `workflow[].missing_tools` for R06, or add `missing_tools` to the carried keys.
3. **Minor, SKILL.md:62.** The `hardcoded_counts` lines are stripped text from the root file plus every linked file, with no source file attached. Step A says to rewrite "those lines" without saying where they live. Fix: "search the root file and its linked files for each line".
4. **Minor, SKILL.md:58 and :64.** When `remediate` is empty but `links` is not, the flow stops at Step B, so Step D's link repair never runs. Fix: "if only `links` is non-empty, fix them directly and re-run `check`". Also, "payload is non-empty" at :58 should read "`remediate` list is non-empty", because the payload is always a dict.
5. **Minor, SKILL.md:104.** "the project's own gsd-tools" is slightly overstated. The resolver (`skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py`, `gsd_core_roots`/`resolve_gsd_tools`, docstring at :5) checks the project-local copies first, then host-home installs and PATH. So it may run a user-level gsd-tools. Fix: "the gsd-tools that GSD's own launcher order resolves for this project (project-local first)".
6. **Minor, SKILL.md:37.** "every always-on rule reports `missing`" understates what happens. Rules gated on tool presence or a detected stack also report `missing` when their condition is met. Fix: "every rule whose condition is met".
7. **Minor, SKILL.md:62.** No rule for runs with no user to ask (unattended or autonomous). Fix: one line saying to treat near-misses as declined and list them as skipped.
8. **Minor, SKILL.md:62 and :66.** A verbatim near-miss (R18 or R19 partly present) gets the full block inserted, which can duplicate the partial text already there. Fix: "replace the partial clause with the block".

## Top 3 improvements
1. Give R06 its installed-tool list (finding 2).
2. Close the links-only path and the unattended Step A path (findings 4 and 7).
3. Make the entrypoint placeholder unambiguous, and say where `hardcoded_counts` lines live (findings 1 and 3).

Not checked: `/agent-md-refactor`'s actual phases (outside the repository, so unverified), and whether `PARALLEL_TEST_GENERIC` itself contains R20's signal groups (I relied on the repo tests). I ran no commands that change state.
