Judge: opus
Reviewed-sha256: 65138f8de4f47675096c37ffb13c17825c9e169b25e92c6aa10238a6bf2dbd82
Lane: native subagent completed
Score: 96
Critical: 0
Important: 2

Evaluation report: ai-kit-project-rules-all (package file `skills/ai-kit-project-rules-all/SKILL.md`, 181 lines; the package text matches the on-disk file exactly)

Summary: Grade B (96/120, which is the threshold). Pattern is Process with Tool elements. Knowledge ratio is about E:A:R = 75:20:5. The skill is a well-sourced orchestrator for this repository's own rules checkers: almost every factual claim checks out against the code. Two gaps hurt usability. The edit boundary for a check-only request is not clear, and the skill never mentions the host's command timeout.

Claims verified against the repository:
- **Four-key shape and identical subcommands:** `cli.py:22-34` returns `{remediate, blocked, failed, notices}`, and `check` and `remediate` give the same output.
- **Usage and exit codes:** usage with exit 0 and an unknown subcommand with exit 2 are at `cli.py:38-51`.
- **Merge and tie-break:** sorting is a stable sort over the `DOMAIN_ORDER` concatenation (`aggregate.py:41-50`, `dispatch.py:25`), so the fixed-order tie-break (Limit 6) holds.
- **`hand_off`:** only `remediate` entries of `workflow` kind get it (`aggregate.py:49-51`).
- **`failed` entries:** the failure shapes and the pass-through of payloads with no `remediate` key are at `aggregate.py:37-44` and `dispatch.py:95-139`.
- **Dispatch:** the 30s budget and sequential runs are at `dispatch.py:40` and `dispatch.py:142-146`.
- **Sibling resolution:** five candidates, checkout first, no `$PATH` search (`dispatch.py:43-80`).
- **Trust note:** stderr is captured (`dispatch.py:104-110`), which matches the agents sibling's Trust note (`ai-kit-project-rules-agents/SKILL.md:104`).
- **Workflow example:** the R01 fields match `rules.py:51-60` and `remediation.py:111-122`.
- **Arch example:** the fields match `arch_checker.py:142-159` and `canonical_tools.py:59-63`, with `CRITICALITY_HIGH = 2`.
- **Wrap mechanism:** Steps A-D exist at `ai-kit-project-rules-agents/SKILL.md:56-70`.
- **Broken links not carried (Limit 5):** confirmed at `ai-kit-project-rules-agents/SKILL.md:39`.
- **Where `blocked` comes from:** only makefile and precommit have `cache-update`. arch, docker and cicd never fill `blocked` (their SKILL.md files: arch 79-84, docker 77-78, cicd 103-104), so routing step 3 is consistent.

## Dimension Scores

- **D1 Knowledge Delta: 15/20.** Nearly all of it is project-specific: the shape contract, the failure isolation, the `(kind, id, issue)` identity rule, and the missing broken-link findings. There is some developer-facing commentary that an agent does not need to act on: Limit 1's rationale ("zero completion-order non-determinism") and Limit 2 on cost.
- **D2 Mindset + Procedures: 11/15.** The procedures are clear: resolve the entrypoint, run, then act per list. There is little framework for deciding whether to act at all (see finding 1).
- **D3 Anti-Patterns: 12/15.** The NEVER list is specific and gives reasons (a clean summary while `failed` or `notices` is non-empty, ignoring `auto_apply`, acting on a `hand_off` alone). It has no NEVER item about edits the user did not ask for.
- **D4 Specification: 14/15.** The frontmatter is valid. The description has WHAT, WHEN, keywords and a route away for single-domain questions. It is long and front-loads the "never" clause.
- **D5 Progressive Disclosure: 13/15.** The file is self-contained with a size that fits. The one load trigger, MANDATORY on the sibling's Wrap mechanism, is embedded in the workflow, but it gives no path.
- **D6 Freedom Calibration: 12/15.** Freedom is low where it should be: entrypoint resolution and the report-only domains. The step that edits AGENTS.md has no gate tied to what the user asked for.
- **D7 Pattern: 8/10.** It follows a clear Process pattern (resolve, run, act, limits, NEVER). The Limits section mixes behaviour facts with design rationale.
- **D8 Usability: 11/15.** Good error and edge coverage (`failed`, `notices`, ids that repeat across domains). It is missing the timeout guidance, and the edit intent is ambiguous.

## Findings

**1. Important: `SKILL.md:780`, `SKILL.md:831-832`, `SKILL.md:844`, `SKILL.md:897-902`, `SKILL.md:938-939`**
- Line 780 says the skill "never edits the target repo". Act step 2 then makes the agents Wrap mechanism MANDATORY, and that mechanism invokes `/agent-md-refactor` on AGENTS.md. Lines 938-939 confirm the hand-off is the one exception to report-only.
- Because `check` and `remediate` are byte-identical, nothing records whether the user asked only to check.
- Under Wrap Step A, `auto_apply: true` entries need no confirmation. So a plain "check everything" request can end in a full AGENTS.md refactor the user never asked for.
- **Fix:**
  - Reword line 780 to say the script never edits, and that the only edit path is the agents Wrap mechanism.
  - Add a gate to step 2: run the Wrap steps only when the user asked to fix or remediate. Otherwise, report the `hand_off` entries and offer the hand-off.
  - Add a matching NEVER item.
  - State which subcommand to run, or say they are interchangeable.

**2. Important: `SKILL.md:830-833`, `SKILL.md:913-915`**
- The skill states a worst case of about 180s (6 x 30s), but it never tells the agent to give the command a host tool timeout above that.
- A common host default for a shell tool is around 120s, which is shorter. The repo's own e2e test uses `timeout=240` (`tests/test_ai_kit_project_rules_all_e2e.py:103`).
- If the host kills the call, no JSON comes back at all. That loses every domain's results, which is exactly what the "never abort the whole run" rule (lines 943-944) exists to prevent.
- **Fix:** under "Run the check", add: "Give this command a tool timeout of at least ~200s (or run it in the background). On a host kill, report it as a whole-run failure, never as a clean run."

**3. Minor: `SKILL.md:898`.** "read the Wrap mechanism section of `ai-kit-project-rules-agents/SKILL.md`" gives no location. **Fix:** say it sits next to the resolved entrypoint's skill directory (`$(dirname "$ENTRYPOINT")/../ai-kit-project-rules-agents/SKILL.md`), or that the agent can load that sibling skill by name.

**4. Minor: `SKILL.md:855-856`.** A payload passed through as-is into `failed` has no `domain` key (`aggregate.py:44`), so step 1 cannot name which domain went unchecked. **Fix:** either say so (name the domain as "unknown"), or have `aggregate` add `domain` to these entries.

**5. Minor: `SKILL.md:818-819`.** The instruction to substitute the SKILL.md directory comes after the stop condition. **Fix:** put the substitution sentence before the snippet.

**6. Minor: `SKILL.md:913-918`.** Limits 1 and 2 justify design choices to a maintainer rather than guide the agent. **Fix:** trim each to the operational fact (the time budget, and the fact that runs are not cached).

I did not run the skill's scripts or the test suite, and I read no host-installed copies. I verified installation-location behaviour only from `dispatch.py`'s source. The 120s host-timeout figure is general host knowledge and is unverified inside this repository.
