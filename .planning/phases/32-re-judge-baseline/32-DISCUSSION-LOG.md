# Phase 32: Re-judge baseline - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-07
**Phase:** 32-re-judge-baseline
**Mode:** assumptions (`--analyze --all --batch`), jev screening, best design over the smallest diff (`mvp-mode` inactive), CodeGraph
**Areas analyzed:** the judge-loop tool, report and records, the judge run, the judge prompt, text gates and AGENTS.md, the JDG-04 citation guard

## Assumptions Presented

The analyzer was `gsd-assumptions-analyzer` (opus), with 90 tool calls. It read the code and the recorded phase
files and re-ran the orchestrator's spike script; it ran no judge lane, no jev call, no host CLI and no npm `yaml`
check. It ran in the background after the SPEC commit (205ba88), while the orchestrator drafted the cross-phase
amendments.

| Assumption | Confidence | Evidence |
|---|---|---|
| One stdlib tool with prompt, ingest, count, check and report subcommands; root from `git rev-parse` in the working directory | Likely | phase 27 `check_verdicts.py` (digest relative to cwd), `tools/check_dogfood.py` exit codes |
| One JSON record per loop, skill, round and judge, joining a build manifest with the lane output | Likely | 29 `judge/parse.py`, SPEC R2/R6 edges, the never-overwrite prohibition |
| Rounds counted per skill within a phase's loop | Unclear | SPEC R6, R7 refresh by batches; phase 27 counted per phase folder |
| Refutations as a structured list keyed by skill, round, judge and finding id | Likely | skill-judge `SKILL.md` (ids unique per verdict) |
| Judge count: pure function; the tool builds a numbers-only `score` item and calls the jev ladder through its own lookup copy | Likely | 29 D-12/D-13, `tests/test_arch.py` lookup drift test, jev `reference.md` |
| Report and records in a milestone-level `.planning/judge/`, report generated from records | Likely | `complete-milestone.md` moves phase folders; `research/`, `lens-brief/` survive |
| Lanes: one prompt per skill, serial per judge, judges in parallel; 600 s probe, 3600 s outer timeout | Likely | 29-JUDGE.md (retry ~200 s, quota stop), the runner's review mode |
| No tracked change or HEAD move while lanes run | Confident | `cross-ai.mjs` `treeState`, `.gitignore` |
| `effort: xhigh` added to `agents/ai-kit-judge.md`; prompt passed by file path | Likely | `model-profiles.md` (frontmatter is the effort channel) |
| Plan order: checks and tools, then judging, then report | Confident | SPEC R7, digest rule |
| The builder embeds the judge files and replaces the Read steps | Confident | skill-judge `SKILL.md` protocol step 1 |
| Module list from the staged mapper's covering set | Likely | `tools/staged_mapper.py`; spike counts 1-59 per skill |
| Runnable-code definition (tracked code files under `scripts/` or at the root, or a package) | Confident | `git ls-files` per skill: 11 with code, 5 without |
| R1 guard in `tests/test_gate_scope.py` | Confident | its rule plus non-vacuity pattern |
| Frontmatter: stdlib strict-subset validator in the unit group | Likely | AGENTS.md hand-rolled precedent; PyYAML only transitive, YAML 1.1, duplicate keys accepted |
| History test rules (tool-list versions, narrow run-log phrases, `## Evidence` last) | Likely | `tmp/p32-spec/text_scan.py` hits |
| Decision ids counted as pointers | Unclear | SPEC Background lists "(D-07)"; R9's list did not |
| Exact text fixes per kept skill | Confident | scan output checked against the files |
| AGENTS.md lines in the Non-Negotiable skill-judge bullet | Likely | `tests/test_rules_docs.py` pins AGENTS.md |
| R10 guard parses `## Phase Details`, keeps phases above 32, skips `## Backlog` | Confident | ROADMAP structure; `jdg04_scan.py` |

## jev screening

One jev request for the discuss step (13 items, one per Likely or Unclear item, sized under the TypeSafe row's
8,000-character state guard after the spec step's request overflowed it); each item gets one advisory answer, and
`needs_fallback` items are decided by own reasoning. Summaries only. Laya answered first, one item per call; the
consented TypeSafe row answered the items Laya left low.

| Item | jev | Outcome |
|---|---|---|
| Packaging of checker and builder | low 0.37 (laya), low 0.75 (typesafe) one_module | **Own reasoning:** one module; shared digest and root code would drift as copies (D-01, ledger) |
| Shape of a stored judge result | choice 0.98 record (typesafe) | D-02 |
| Span of the three-round cap | low 0.60 (laya), low 0.78 (typesafe) lifetime | **Own reasoning:** per loop; a lifetime count caps the batch phases after one fix round, and SPEC R6 says per judge loop; the evidence contradicts the answer (D-03, ledger) |
| Where refutations are recorded | choice 0.72 structured (laya) | D-04 |
| How the judge count gets jev's score | choice 0.93 tool_calls (typesafe) | D-05 (word bands added by own reasoning: Jev's weak spots include arithmetic and counting) |
| Where the report lives | low 0.39 (laya), low 0.76 (typesafe) phase_folder | **Own reasoning:** milestone-level `.planning/judge/`; milestone close moves phase folders while batches refresh the report (D-06, ledger) |
| Lane scheduling | choice 0.81 per_skill_serial (typesafe) | D-08 |
| Native judge effort | choice 0.87 agent_frontmatter (laya) | D-10 |
| Test-module rule | low 0.60 manual (laya), low 0.68 selector (typesafe) | **Own reasoning:** the selector's covering set; SPEC R2 requires a rule computed from the tree (D-14, ledger) |
| Frontmatter parser | choice 0.82 both (laya) | D-17: the stdlib validator gates; PyYAML in `unit-uv` cross-checks (the analyzer missed that `tests/test_framework_profiles.py` already uses PyYAML there) |
| Version recognition | low 0.51 any_number (laya), low 0.75 tool_list (typesafe) | **Own reasoning:** tool list plus constraint words; thresholds such as 0.74 are not versions (D-18, ledger) |
| Decision ids as pointers | low 0.70 yes (laya), low 0.67 no (typesafe) | **Own reasoning:** yes, placeholders pass; SPEC R9 amended (D-18, ledger) |
| Placement of the AGENTS.md lines | choice 0.86 one_bullet (laya) | D-20 |

Not asked (evidence or a Confident analyzer item settled them): D-07 (check-dogfood runs the checker), D-09 (frozen
tree during lanes), D-11 (plan order; corrects the analyzer's `check --gate`, since a baseline holds unmet bars),
D-12 (baseline as the new base; needs confirmation), D-13, D-15, D-16, D-19, D-21, D-22.

## Corrections Made

No user corrections (auto path). Orchestrator corrections to the analyzer: the baseline's acceptance is `check` in
default mode, not `--gate` (D-11); PyYAML is already a direct test dependency in practice through
`tests/test_framework_profiles.py`, which supports the cross-check layer (D-17); the jev item sends word bands, not
raw numbers (D-05).

## Live facts that changed the plan

- The test runner (`discover_modules`) and the staged mapper only see `tests/test_*.py` directly under `tests/`; in a
  scratch tree a module in `tests/skills/demo-skill/` ran in no group and was never selected, and the gate-scope test
  did not notice. This turned the test-location question into a guard requirement (SPEC R1), because the judge
  rubric's own fix text points authors to `tests/skills/<name>/`.
- All 23 SKILL.md frontmatters already parse with the `yaml` package and the regex the cached `skills` CLI 1.5.20
  uses; JDG-07's work is a stricter guard, not fixes. PyYAML 6.0.3 imports under `uv run`.
- `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` was deleted in Phase 29 (29 D-14); Phase 34's and Phase 32.4's
  code anchors still named it (amended in this commit). The run used jev's own `jev_review.py ladder`, as the skill
  says.
- The TypeSafe row's state guard is 8,000 characters and its batch merges every item's context into one state: the
  spec step's ten-item request (about 13,000 characters) came back forced on every remote answer. The discuss step's
  request was sized under the guard and got usable answers.
- The phase 27 checker's digest uses `git ls-files` relative to the working directory; run from `tools/` it lists no
  file (checked live).
- A wider scan found history pointers outside `references/`: jev's `backends/laya.md` names a Phase 21.1 results file
  and `backends/typesafe.md` cites a decision id; SPEC R9 is amended (D-18) and its floor re-checked (58 rows, ok).
- The runner's review mode stops a lane with `contract_violation tree=dirty` when the tree changes, so lane output
  must land in a wholly ignored folder (`tmp/`) (D-09).
- The embedded judge package is about 92 KB, roughly 23,000 tokens per judge call (D-10).
- The unit start ran `codegraph sync` and `graphify update .`; the codegraph MCP server reported its own auto-sync
  disabled by a WAL size guard, so its answers were re-read from disk where they mattered.

## External Research

None run. Open items for the phase researcher: whether Claude Code honours `effort:` in a user-level agent file
(D-10); the context limits of the router-backed judges for a 92 KB prompt; the npm `yaml` package's behaviour on the
duplicate-key and tab fixtures (to be run once and recorded, SPEC R8).
