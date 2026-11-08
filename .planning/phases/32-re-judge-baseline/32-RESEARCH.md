# Phase 32: Re-judge baseline - Research

**Researched:** 2026-11-07
**Domain:** stdlib Python tooling (judge-prompt builder, verdict checker, judge-count rule), YAML frontmatter and text gates over `skills/`, a cross-AI judge run, `check-dogfood` wiring
**Confidence:** HIGH for in-repo shapes and the effort answer; MEDIUM for the 92 KB prompt answer (one lane proven by precedent, two unproven)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

CONTEXT.md `## Implementation Decisions` D-01 to D-22 are locked, and `32-SPEC.md` R1-R10 are locked requirements. Read both before planning; they are not repeated here. In one line each:

- D-01 one stdlib module `tools/judge_loop.py` with subcommands `prompt`, `pool`, `count`, `ingest`, `check`, `report`; one repo-root resolver (`git rev-parse --show-toplevel`, `--root` override, never `__file__`); one skill lister `git -C <root> ls-files -z -- skills/<name>/`; exit codes 0 ok, 1 invalid/missing/mis-pinned verdict (with `--gate` also unmet bar or loop over cap), 2 usage.
- D-02 one JSON record per (loop, skill, round, judge); `prompt` writes a manifest; `ingest` joins manifest + last `AIKIT-XAI ` line + verbatim verdict line; never overwrites a valid verdict record.
- D-03 rounds count per skill within one judge loop; cap of three per loop.
- D-04 refutations in `refutations/<loop>.json`; a refuted finding leaves the bar only when finding id, `path:line`, command and observed output are all non-empty.
- D-05 `count` is a pure function; jev asked only when the deterministic triggers give one judge; fixed word bands, no skill text sent.
- D-06 records and report in `.planning/judge/` (`REJUDGE.md` generated, `verdicts/<loop>/<skill>/r<N>/<judge>.json`, `refutations/<loop>.json`, `inputs.json`); `check` regenerates the report and compares bytes; no `.planning` default in the tool.
- D-07 `make check-dogfood` runs the checker in default mode (stale digest is a note).
- D-08 the judge run is a plan task following `ai-kit-cross-ai`, not tool code; probe each judge with a one-word prompt; `pool` turns status lines into the pool.
- D-09 nothing tracked changes and HEAD does not move while lanes run; outputs under `tmp/` until all lanes end, then one commit into `.planning/judge/`.
- D-10 native substitute is `agents/ai-kit-judge.md` with `effort: xhigh` added to its frontmatter; prompt passed by file path.
- D-11 plan order: Wave 1 parallel (R1+R8 checks; R9 test + text fixes + AGENTS.md lines; R10 guard; tool + tests + judge-agent effort line), Wave 2 the judge run, Wave 3 ingest, report, `check` in default mode.
- D-12 the baseline verdict becomes each skill's base for later regression checks (owner-confirmed 2026-11-07).
- D-13 builder embeds the skill-judge package byte for byte (SKILL.md, rubric, spec files from the `source` column in table order, verdict schema).
- D-14 module list = `staged_mapper.covering_modules(build_index(root), "skills/<name>/SKILL.md")`, sorted, or "no script test found".
- D-15 "ships runnable code" = a tracked `.py/.mjs/.cjs/.js/.sh` under `scripts/` or at the skill root, or a top-level folder holding `__init__.py`.
- D-16 R1 guard in `tests/test_gate_scope.py`. D-17 two-layer frontmatter check (stdlib strict-subset gate in `tests/test_skill_frontmatter.py`; PyYAML cross-check in the `unit-uv` set). D-18 `tests/test_skill_text_history.py` rules. D-19 text fixes (moves into a trailing `## Evidence` or rewordings; no instruction changes). D-20 AGENTS.md takes three lines inside the skill-judge bullet, pinned in `tests/test_rules_docs.py`. D-21 `check_jdg04_citations(root) -> (problems, notes)` in `tools/check_dogfood.py`. D-22 ROADMAP/REQUIREMENTS already amended.

### Claude's Discretion

- The tool's final name, flag spellings, the probe prompt's wording and the four score levels' wording.
- The exact word bands of D-05 and the record field names of D-02, as long as the checker reproduces every number.
- How `report` lays out `REJUDGE.md`, as long as it carries every SPEC R7 field.

### Deferred Ideas (OUT OF SCOPE)

- jev callers not knowing the TypeSafe batch guard (handed to 32.1 JEV-09 and 32.4).
- Whether Claude Code honours `effort:` in a user-level agent file (answered below, item 1).
- Context limits of router-backed judges for a 92 KB prompt (answered below, item 2).
- Not folded: eight other todo keyword matches; the low-risk review notes (batch phases 32.1-32.4 and Phases 45-46).
- Out of scope per SPEC: bringing any skill to the bar, evals, moving tests into `tests/skills/<name>/`, converting Markdown evals, trimming evals from the shipped copy, judging commit-fold and the rules skills, a judge-list config file, vendoring skill-judge, code comments/docstrings in the history check.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| JDG-01 | One current-judge report for the 15 judged skills | Prompt-size evidence (item 2), judge-count inputs, verdict history table, lane run mechanics, report determinism |
| JDG-02 | Tracked verdict checker, lists as arguments, no referee name, root resolved itself, round count | Exact shapes of the phase 27 and `tmp/judge-30` checkers, digest algorithm, path-confinement pitfall |
| JDG-04 | Judge bar recorded per skill; later phases cite it | `check_jdg04_citations` scan (tree passes today), bar-boundary rule |
| JDG-05 | History-free skill text | Read-only scan of 16 kept skills (hits table, three additions to D-19) |
| JDG-06 | Judge count by deterministic signals plus jev's score | `jev_review.py ladder` CLI and score answer shape, band arithmetic, recorded inputs with sources |
| JDG-07 | Strict frontmatter check | Parser comparison (npm `yaml` 2.9.0 vs PyYAML 6.0.3), tree frontmatter shapes, existing guard tests to replace |
| JDG-08 | Round cap and refute-by-running in AGENTS.md and the checker | AGENTS.md bullet location, `test_rules_docs.py` clause-pin pattern, refutation record design |
</phase_requirements>

## Summary

Phase 32 is almost entirely in-repo work on tools and tests that already have close precedents: the phase 27 checker (219 lines) supplies the verdict validator, grade function, status-line parser and digest idea; `tmp/judge-30/round3/check_verdicts.py` (gitignored, present) supplies three extra checks; `tools/check_dogfood.py` supplies the only-`.planning`-reader pattern; `tests/test_rules_docs.py` supplies the AGENTS.md clause-pin pattern. The new code is the prompt builder, the count rule with its jev item, the pool/ingest/report plumbing and two text gates. Nothing needs a new dependency: runtime stays stdlib, and the PyYAML cross-check reuses PyYAML 6.0.3, already importable under `uv run` (transitive via pre-commit).

The two open research items are settled enough to plan on. **Item 1 (effort):** the current Claude Code subagent docs list `effort` as a supported frontmatter field (`low`, `medium`, `high`, `xhigh`, `max`, model-dependent), with no distinction between `~/.claude/agents/` and `.claude/agents/`; 33 GSD agent files in this repo carry `effort:` and GSD's own reference says frontmatter is its channel. What cannot be shown cheaply is a behavioural proof; record it as "documented", not "observed". **Item 2 (92 KB prompt):** the real package measures 91,927 bytes (about 92 KB, SKILL.md under judgment excluded). `referee-one` demonstrably returned full reviews for inline prompts of roughly 120 to 190 KB in phase 30 (computed from file sizes), but `referee-two` and `referee-three` have no recorded large-prompt run (both were unavailable), so only the referee-one precedent exists. Plan an early sentinel spike per lane (recipe below); a lane that fails it is not counted.

Three findings change the plan: (1) SPEC and CONTEXT say the referees are opencode lanes, which `.planning/config.json` confirms, but phase 29 ran them through pi, so the judge id must always be built from the run's given list; (2) the history scan finds three hits D-19 misses (a fenced ISO date in `ai-kit-cross-ai/SKILL.md`, a `999.2` in spec-discuss's `worked-examples.md`, and more decision-id forms in spec-discuss references); (3) the recorded commits for the two skills that reach the jev step (`16153d6`, `d2855bc`) are not ancestors of HEAD (folded away; they survive only under `archive/phase-29.1-raw` and `archive/phase-29-raw`), so `count` must treat an unresolvable base commit as "jev input absent".

**Primary recommendation:** Build `tools/judge_loop.py` as pure functions plus thin subcommands (fixture-testable with `--root`, `--judge-dir`, `--no-jev`), land the text gates and edits before any lane runs, run a sentinel size probe per judge before the baseline, and treat `effort: xhigh` as documented-not-observed in the report.

## Open Item 1: Does Claude Code honour `effort:` in a subagent file?

**Answer: documented yes. Not behaviourally observable from inside a session; label it "documented", not "verified".**

| Evidence | Source | Tag |
|----------|--------|-----|
| The sub-agents page lists `effort` in the frontmatter table: "Effort level when this subagent is active. Overrides the session effort level, but not the `CLAUDE_CODE_EFFORT_LEVEL` environment variable. Options: `low`, `medium`, `high`, `xhigh`, `max`; available levels depend on the model." | code.claude.com/docs/en/sub-agents (fetched this session) | [CITED: code.claude.com/docs/en/sub-agents] |
| The page's scope table gives `.claude/agents/` priority 3 and `~/.claude/agents/` priority 4 and says nothing different about effort per scope; the only precedence note is the env var | same | [CITED: code.claude.com/docs/en/sub-agents] |
| Models that support `xhigh`: Opus 5.5, Sonnet 5.5, Haiku 5.5, Opus 5, Sonnet 5, Opus 4.8, Opus 4.7, Fable 5/5.1; "If you set a level the active model does not support, Claude Code falls back to the highest supported level at or below the one you set (`xhigh` runs as `high` on Opus 4.6)". Opus 5.5 defaults to `medium` | code.claude.com/docs/en/model-config | [CITED: code.claude.com/docs/en/model-config] |
| 33 files under `.claude/agents/gsd-*.md` carry an `effort:` line (for example `gsd-planner.md:12` `effort: xhigh`, `gsd-phase-researcher.md:12` `effort: medium`) | `rg "^effort:" .claude/agents` (33 lines) | [VERIFIED: rg .claude/agents] |
| GSD's reference: "`effort` (claude runtime) ... is baked at install time into the `effort:` frontmatter key of ... `gsd-*.md` - Claude Code's Agent tool has no per-spawn effort parameter, so per-agent frontmatter is the only channel." | `.claude/gsd-core/references/model-profiles.md:232-238` (Read) | [VERIFIED: model-profiles.md:232-238] |
| A web search reports v2.1.292 added an `effort` parameter to the Agent tool and `CLAUDE_CODE_SUBAGENT_EFFORT` in v2.1.316, and that a GitHub issue (Sep 2026) said the frontmatter field was implemented before the docs listed it. Sources were blogs and an issue tracker, not the official changelog; the issue page itself could not be fetched | WebSearch | [ASSUMED] (LOW; do not plan on the Agent-tool parameter, and the GSD sentence above may now be stale) |

Facts that bear on D-10:
- `agents/ai-kit-judge.md` today has frontmatter `name`, `description`, `tools: Read, Grep, Glob`, `model: opus` (`agents/ai-kit-judge.md:1-6`, Read). `~/.claude/agents/ai-kit-judge.md` is a symlink into the checkout (`ls -la`: `... -> /var/home/.../ai-kit/agents/ai-kit-judge.md`), so the edit reaches the user-level agents folder with no install step.
- The docs say Claude Code watches both agents folders and picks up edits "within a few seconds ... with no restart needed", with exceptions for directories that did not exist at session start and `--add-dir` directories. Whether the watcher notices an edit made to a symlink's target is not documented [ASSUMED]. Mitigation: commit the effort line in Wave 1 and start the judging session after it, so the question never arises.
- `CLAUDE_CODE_EFFORT_LEVEL`, `CLAUDE_CODE_SUBAGENT_EFFORT` and `CLAUDE_CODE_AUTO_COMPACT_WINDOW` are all unset in this research shell (`printenv` exit 1) [VERIFIED: printenv]. The judging task should repeat that check, since the env var overrides the frontmatter.
- `model: opus` is an alias; which concrete model it resolves to on the day is not pinned, and an unsupported `xhigh` silently drops to a lower level. So the report line should read "native, xhigh (frontmatter, documented; not observed)".
- Cheap observable check if one is wanted: none found. A subagent cannot reliably report its own effort level. Do not make a task depend on observing it; make a task record the label and the env-var check.
- README line 51 describes `ai-kit-judge` ("Opus; Read, Grep and Glob only"); update it in the same commit as the effort line (AGENTS.md: stale docs are a defect). `tests/test_setup.py:5591` and `tests/test_wizard_app_1.py:131-140` only check the component title, so the new key breaks nothing.

## Open Item 2: Can the router-backed judges take a prompt of about 92 KB?

**Measured size.** Installed skill-judge at `~/.agents/skills/skill-judge` (`~/.claude/skills/skill-judge` links to it), sizes from `find -printf "%s"`:

| Embedded file (D-13 order) | Bytes |
|----------------------------|-------|
| `SKILL.md` | 9,870 |
| `references/rubric.md` | 15,466 |
| `references/agentskills/best-practices.md` | 14,713 |
| `references/agentskills/specification.md` | 7,271 |
| `references/agentskills/optimizing-descriptions.md` | 13,256 |
| `references/agentskills/evaluating-skills.md` | 16,860 |
| `references/agentskills/using-scripts.md` | 12,510 |
| `references/verdict.schema.json` | 1,981 |
| **Total** | **91,927** (about 22.4k tokens at 4 bytes/token [ASSUMED ratio]) |

The order and the file set follow the rubric's `source` column read this session (`rubric.md:10-17`): first-appearance order is best-practices, specification, optimizing-descriptions, evaluating-skills, using-scripts [VERIFIED: rubric.md:8-17]. The judged `SKILL.md` is read by the judge's own tools (largest today: `ai-kit-spec-review` 39,040 bytes), so it is not part of the 92 KB; the builder's own wording (readings, module list) adds a few KB. If the builder ever inlines the judged skill too, the worst case is about 131 KB. `rubric_version: 4` and `spec_sha: 69ef37e9424c0a7ea9dd2293b559e43ec8176379` are lines 1-2 of the rubric (Read).

**Transport.** `cross-ai.mjs` sends the prompt on stdin for every runtime except copilot: the header says "The prompt arrives on stdin" (`.planning/scripts/cross-ai.mjs:13`), opencode's formulas are `['run', '--model', m, '--agent', 'plan', '--format', 'json', '--standalone']` with no prompt element (`:1380`), and only copilot sets `argvPrompt: true` (`:1461`) with `ARGV_PROMPT_MAX = 102400` (`:3271`) [VERIFIED: cross-ai.mjs, Read]. So there is no argv limit on the opencode lane; copilot would sit near its limit and is not a judge here.

**Lane-level evidence.**
- `.planning/config.json:52-76` configures `referee-one|two|three` as `"cli": "opencode"` with models `router-env/my-referee-one|two|three`, `default_reviewers: ["referee-two"]` [VERIFIED: config.json:52-69 (Read)]. Phase 29 ran the same referees through pi (`--runtime pi --route-pi router`), so never write a runtime into code.
- Phase 30's plan review sent `referee-one` three batches through the opencode lane. Each inlined PROJECT.md (80 lines), a ROADMAP section, `30-SPEC.md`, `30-CONTEXT.md` and the batch's plans (`30-REVIEWS.md:23-35`), and "Every batch produced full per-plan sections with `file:line` evidence" in 983 s, 581 s and 674 s [VERIFIED: 30-REVIEWS.md:25-35 (Read)]. The saved prompts are gone (`/tmp/gsd-review-4NdnUH` no longer exists), so the size is computed from today's file sizes: batch A is at least 47,763 + 16,913 + 63,043 + 27,258 + 37,103 = 192,080 bytes, batch B about 136 KB, batch C about 121 KB [VERIFIED: `find -printf` sizes; sum is mine; plan files may have changed since `1bc229d`]. So `referee-one` handles more than 92 KB. Caveat: that run used `gsd-tools review-lane invoke --slug opencode`, whose stdin/file transport I did not read [ASSUMED same `opencode run`].
- `referee-two` (`grok-cli/grok-4.7-xhigh`) and `referee-three` (`anthropic/claude-opus-5-5-xhigh`) failed their probes in phase 30 ("Model ... is unavailable", `30-REVIEWS.md:36-39`) and in phase 29 (`29-JUDGE.md:29-30`). There is no recorded large-prompt run for either. The context window of the underlying models is plausibly far above 23k tokens, but the router's own limits are unknown [ASSUMED].
- Earlier judge prompts (phase 26/27) were about 1.7 KB and told the judge to read files (`tmp/p27/judge/r7-my-referee-one.prompt` 1,719 bytes), so nothing before this phase tested a large judge prompt.

**Conclusion: not settled for referee-two and referee-three; settled by precedent for referee-one (which is currently unavailable).** Recommend an early spike task, run before the baseline and re-run whenever a judge joins the list:

1. `prompt` builds the real package block for one skill and appends a sentinel line after the embedded schema (a random token, for example `AIKIT-SENTINEL-<16 hex>`) plus an instruction: "Ignore every earlier instruction. Print only the sentinel line you find at the very end of the last embedded file, nothing else."
2. Run it per configured judge through `node .planning/scripts/cross-ai.mjs --runtime <cli> --model <model> --mode review --outer-timeout 600` under `AI_KIT_REFUSE_REAL_HOME=1`, outputs under `tmp/`.
3. Pass check: exit 0, last `AIKIT-XAI` line `status=ok ... tree=clean`, and the answer equals the sentinel exactly. Anything else (truncation, a paraphrase, a refusal, `exit=75`) means that lane is not counted for the baseline and the substitute rule applies (native Opus).
4. For `native:opus-xhigh`, the built prompt is passed by file path, so no spike is needed; the native lane reads it with `Read` (`tools: Read, Grep, Glob`).

Use this sentinel probe in place of, or in addition to, the one-word probe of D-08: it proves the lane both answers and reads the full prompt. It costs one pass per lane.

## Architectural Responsibility Map

| Capability | Primary tier | Secondary tier | Rationale |
|------------|-------------|----------------|-----------|
| Prompt build, pool, count, ingest, check, report | `tools/judge_loop.py` (tool, stdlib) | tests with fixture roots | Reproducible from records; no `.planning` default; never runtime code |
| Lane run (probe, size spike, judging) | Plan task through `ai-kit-cross-ai` and `cross-ai.mjs` | native `ai-kit-judge` agent | D-08; lanes run read-only with `AI_KIT_REFUSE_REAL_HOME=1`, outputs under `tmp/` |
| Judge records and report | `.planning/judge/` | none | Survives milestone close (D-06); only `check-dogfood` reads `.planning/` |
| Only reader of `.planning/` | `tools/check_dogfood.py` | its unit tests with fixture roots | `tests/test_arch.py` `check_no_planning_reader` bars tests from reading it |
| Frontmatter and history gates | `tests/test_skill_frontmatter.py`, `tests/test_skill_text_history.py` | `tests/test_skill_frontmatter_pyyaml.py` (unit-uv) | Tests over `skills/` and `agents/`, never `.planning/` |
| R1 stray-module guard | `tests/test_gate_scope.py` | none | Sits beside the discovery rules it protects |
| Judge count with jev | `count` subcommand | `jev_review.py ladder` as a child process | Advisory only; numbers and fixed text sent, never skill text |

## Standard Stack

### Core
| Library | Version | Purpose | Why standard |
|---------|---------|---------|--------------|
| Python stdlib (`argparse`, `hashlib`, `json`, `re`, `subprocess`, `pathlib`) | system `python3` 3.14.7; code must stay py312-compatible (ruff target `py312`) | the whole tool and both stdlib tests | AGENTS.md: tools stay stdlib-only |
| `unittest` through `tools/run_unittest_parallel.py` | repo runner | all tests | AGENTS.md Testing |
| `tools/staged_mapper.py` | in repo | module lists (D-14) | `build_index(root: Path) -> Index`, `covering_modules(index, path) -> frozenset[str]` |

### Supporting
| Library | Version | Purpose | When to use |
|---------|---------|---------|-------------|
| PyYAML | 6.0.3 | `unit-uv` cross-check of frontmatter fixtures and tree | `uv run python -c "import yaml"` printed `6.0.3` [VERIFIED: uv run]; it is not a direct `pyproject.toml` dependency (no `yaml` line), only pre-commit's; `tests/test_framework_profiles.py:9` already imports it under `unit-uv` |
| npm `yaml` | 2.9.0 | one-time comparison recorded in the verification (SPEC R8) | found in the `skills` CLI's npx cache (`skills` 1.5.20) [VERIFIED: node require]; discover the path at run time, never write it into code or plans |
| `node` | v24.21.0 | the comparison script and the runner | present |

### Alternatives Considered
| Instead of | Could use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled strict-subset validator as the gate | PyYAML as the gate | PyYAML is not on the system-python `unit` path and its `safe_load` accepts duplicate keys (shown below), so D-17's two layers stand |
| `git ls-files` digest | walking the directory | Untracked or ignored files would enter the digest; `ls-files -z` also survives spaces in paths |

**Installation:** none. No package is installed by this phase.

**Version verification:** `uv run python -c "import yaml; print(yaml.__version__)"` returned `6.0.3`; `node -e` on the cached packages returned `yaml 2.9.0`, `skills 1.5.20`. [VERIFIED: tool output this session]

## Package Legitimacy Audit

No external package is installed or added to `pyproject.toml` or `uv.lock` by this phase (PyYAML is already locked as a pre-commit dependency; `yaml` and `skills` are only read from an existing npx cache for a one-time comparison). Audit table: not applicable. If the planner decides to declare PyYAML directly in the dev group, that is a new dev dependency and needs the AGENTS.md check first (the transitive reuse already serves `tests/test_framework_profiles.py`).

## Architecture Patterns

### System Architecture Diagram

```
                          INPUTS (read-only)
 installed skill-judge --(skills-roots lookup, --judge-dir in tests)--+
 skills/<name>/ tracked files --(git ls-files -z)--+                   |
 tests/*.py --(staged_mapper index)--> module list per skill           |
                                                                       v
 judge list (argument) --> [pool] <-- probe status lines     [prompt] -> tmp/<run>/<skill>.<judge>.prompt
                              |  first two usable, else 1+native,        + manifest (digest, pin, sha256s, modules)
                              |  else native alone; reason per substitute         |
                              v                                                   v
 recorded inputs.json --> [count] -- deterministic triggers --> 2 judges      LANE RUN (plan task, Wave 2)
   (last v4 percent,        |  else numbers->word bands --> jev ladder           cross-ai.mjs --mode review (opencode lanes)
    high/crit counts,       |  (advisory; error/needs_fallback => stay 1)        native ai-kit-judge (file path prompt)
    base commit)            v                                                    -> lane stdout + last AIKIT-XAI line
                      count record                                                          |
                                                                                            v
                                          [ingest] manifest + status line + verbatim verdict line
                                            refuses: judge != lane, pin != manifest; failed lane = status, no verdict
                                                         |
                                                         v
                     .planning/judge/verdicts/<loop>/<skill>/r<N>/<judge>.json  (+ refutations/<loop>.json, inputs.json)
                                                         |
                                  [report] --> REJUDGE.md (deterministic) <--bytes compared-- [check]
                                                                                   |
 make check-dogfood -> tools/check_dogfood.py main() -> judge_loop.check (default mode) + check_jdg04_citations(ROADMAP)
```

### Recommended Project Structure
```
tools/
  judge_loop.py            # six subcommands, pure functions first (D-01)
  check_dogfood.py         # + check_jdg04_citations(root), + a judge-records check
tests/
  test_judge_loop_prompt.py    # R2 (+ pool/R3 if kept together)
  test_judge_loop_count.py     # R4, jev item pinned to numbers and fixed words
  test_judge_loop_check.py     # R5, R6 (digest, schema, arithmetic, pin, stale, rounds, cap, refutation)
  test_judge_loop_report.py    # R7 (fixture records -> byte-equal report)
  test_skill_frontmatter.py    # R8 stdlib gate (unit)
  test_skill_frontmatter_pyyaml.py  # R8 cross-check (unit-uv)
  test_skill_text_history.py   # R9 (unit)
  test_gate_scope.py           # R1 guard + non-vacuity (edited)
  test_rules_docs.py           # AGENTS.md pins (edited)
  test_check_dogfood.py        # R10 fixture roadmaps (edited)
.planning/judge/               # created by Wave 3 only
```
Splitting by concern is a recommendation, not a decision: each module runs as one parallel subprocess, and a split keeps the commit-stage selection narrow. A single `tests/test_judge_loop.py` is also valid.

### Pattern 1: Pure function plus thin CLI, root passed in
**What:** every subcommand body is a function taking `root: Path` and explicit paths; `main(argv)` only parses and prints. **Why:** unit tests run in a temporary HOME with cwd = repo root and no installed skill-judge, so everything that touches the installed skill or jev takes an injected path or runner (`--judge-dir`, `--client`, `--no-jev`). [VERIFIED: `tools/run_unittest_parallel.py:51-53` baseline env]
**Example:** `check_edge_floors(root, run=_run_floor, which=shutil.which) -> tuple[list[str], list[str]]` is the shape to copy (injected `run` and `which`; returns `(problems, notes)`) [VERIFIED: tools/check_dogfood.py:478-508].

### Pattern 2: Digest (promote with fixes)
The phase 27 copy: `sha256` over `"".join(sha256(file bytes).hexdigest() + "  " + path + "\n" for path in sorted(files))` with files from `git ls-files -- skills/<SKILL>` split on whitespace and read relative to the cwd (`check_verdicts.py:101-107`). Fixes the phase must make: trailing-slash pathspec so `ai-kit-spec-review` does not swallow `ai-kit-spec-review-fixer`; `-z` splitting; `git -C <root>` and paths joined to `<root>`; paths in the digest stay POSIX and root-relative [VERIFIED: check_verdicts.py:101-107 (Read), SPEC R5 encoding/adjacency rows].

### Pattern 3: Verdict validation (promote)
`validate_verdict(v, rubric)`: exact key set, `scores`/`max` exactly `D1..D8` integers, integer `total`/`max_total`/`rubric_version`, `spec_sha` 40 hex, pin equals the rubric pair, sums match, score <= max, `percent == round(total / max_total * 100, 1)`, `grade == grade_of(pct)`, finding shape. `grade_of`: A >= 90, B >= 80, C >= 70, D >= 60, else F (rubric line 23: "Grade: A at 90 or more, B at 80, C at 70, D at 60, otherwise F") [VERIFIED: check_verdicts.py:37-79 (Read); rubric.md:23]. Add from `tmp/judge-30/round3/check_verdicts.py` (exists, 48 lines): unique finding ids, `file` exists and `line <= line count`, a finding for every dimension scored below max [VERIFIED: Read]. Drop its hard-coded `SHA`, its three skill names and the `D4`/`line == 3` description check.

### Pattern 4: Gate bar
`rule = (crit == 0 and high == 0) or pct >= 80` (phase 27 line 200) with the worst judge deciding (min percent, max counts). Name the clause: "no critical or high finding", "grade B or better", or "not met". A worst judge at exactly 80.0 with a high finding meets it through "grade B or better" (SPEC edge row) [VERIFIED: check_verdicts.py:189-200; SPEC R7 boundary].

### Pattern 5: Count rule
Deterministic first (no verdict, critical or high in the last verdict, or last percent within 7.0 of 80), jev only when that gives one. Compare percents as integer tenths (`abs(round(p * 10) - 800) <= 70`) to avoid float edge noise at 73.0 and 87.0. Today's recorded inputs give 13 skills two judges (8 with no v4 verdict, plus spec-config 77.6, spec-execute 80.8 with 1 high, execute-superpowers 83.2, curated-config 84.0 with 1 high, jev 85.6) and leave `ai-kit-gsd-spec-discuss` (88.0) and `ai-kit-spec-goal-prompt` (88.8) for jev [VERIFIED: recorded values below; arithmetic mine].

### Anti-Patterns to Avoid
- **`__file__`-relative roots or `os.getcwd()` file reads:** breaks the sub-folder digest test and fixture repos (D-01).
- **Trusting a finding's `file` path:** `tmp/judge-30/round3/check_verdicts.py:34-37` does `ROOT / f["file"]` and reads it; a judge-written `../../x` escapes the repo. Resolve and require the path to stay under the root; reject otherwise.
- **Parsing `git ls-files` with `.split()`:** breaks on spaces; use `-z`.
- **Running `git commit` in a fixture repo without `-c user.name=... -c user.email=...`:** the test baseline gives a temp HOME with no git identity.
- **A host CLI named as the program of a spawn in a test:** `tests/test_arch.py` forbids it (tripwire rule); fake the lane output, never run a lane.
- **Reading `.planning/` from a test:** only `tools/check_dogfood.py` may.

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---------|-------------|-------------|-----|
| Module list per skill | a name-prefix rule or hand-kept table | `staged_mapper.covering_modules(build_index(root), "skills/<name>/SKILL.md")` | D-14; it is the set the commit hook runs; a prefix rule finds nothing for spec-review, execute-superpowers and cross-ai |
| Status-line parsing | a new regex | the phase 27 `parse_status_line` (`AIKIT-XAI ` prefix, `key=value` tokens) | proven shape; last line of the lane's stderr |
| Verdict extraction from lane output | a Markdown parser | `build_report.py`'s scan: lines starting `AIKIT-XAI ` and stripped lines starting `{"skill"` | the contract is one JSON object per line, no fence |
| YAML parsing in the runtime tool | a YAML parser | none needed; the strict-subset validator is test code, PyYAML only in `unit-uv` | the subset is small and already enumerated by tree shapes |
| Installed-skill lookup | a new root order | a copy of `jev_ladder.py`'s `SKILLS_ROOTS` literal, added to `LOOKUP_COPIES` | the drift test compares copies against `jev-fast-decision/reference.md` rows 2-6 |
| Test grouping | hand edits to `Makefile` or `.pre-commit-config.yaml` listings | `python3 tools/gen_test_groups.py` | `test_generated_listings_name_every_discovered_module` fails on a stale listing |
| Hook for the dogfood run | a new hook | the existing `check-dogfood` hook (`pass_filenames: false`, `always_run: true`, pre-push, verbose) | `.pre-commit-config.yaml:88-95` |

**Key insight:** every number in the report must be recomputable from raw records the checker reads, so the tool regenerates the report and compares bytes; nothing the report states may come from a hand edit.

## Exact Current Shapes of the Reusable Code

| Item | Shape (read this session) |
|------|---------------------------|
| Phase 27 checker | `.planning/milestones/v1.3-phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/check_verdicts.py`, 219 lines. Constants `SKILL = "ai-kit-spec-goal-prompt"` (line 17), `KEYS`, `FINDING_KEYS`, `SEVERITIES`, `JUDGES` dict of three `router-env/my-referee-*` names (lines 23-26). Functions `parse_status_line(line)`, `grade_of(pct)`, `validate_verdict(v, rubric)` (rubric is a `(version, spec_sha)` tuple), `self_test()`, `pkg()`, `verdict_of(r)` (regex `^Verdict: (\{.*\})$`), `lane_ok`, `finished`, `main(argv)`. Hardcodes the `27-SKILL-JUDGE.md` header (`^Rubric: version (\d+), spec_sha ...`) and "rounds must be r1..r<=7" (line 162). Promote: the validator, grade, status parser and digest idea; drop the rest (D-01). |
| `tmp/judge-30/round3/check_verdicts.py` | Present (gitignored scratch), 48 lines; loops over three hardcoded names, reads ` ```json ` blocks, adds unique ids, file/line range, below-max finding coverage, and the first-line summary `VERDICT: {total}/125, {pct} {grade}, critical=.., high=..`. Promote the three checks only. |
| p27 scripts | `.planning/research/2026-11-02-next-milestone/p27-judge-scripts/`: `build_report.py` (args: `<judge> <lane-output-file...> --sha <sha256> --out <path>`; scans `AIKIT-XAI ` lines and `{"skill"` lines; writes `Judge:`, `Lane:`, `Reviewed-sha256:`, `Score:`... header), `digest.py` (imports the phase 27 checker and prints `pkg()`), `gates.sh` (cd + unit/arch + `make validate`), plus `prompt-template-r7.txt` and run helpers. |
| `staged_mapper` | `build_index(root: Path) -> Index` (reads `root/tests/*.py`, flat glob; raises `MapperError`); `covering_modules(index: Index, path: str) -> frozenset[str]` returns `tests.<stem>` names; skill paths use `_skill_forms` (bare folder token, except `TIGHT_SKILL_FOLDERS = {"ai-kit-spec-review"}`, which needs a path form) [VERIFIED: tools/staged_mapper.py:46-232]. |
| `run_unittest_parallel` | `discover_modules(tests_dir=TESTS_DIR) -> list[str]` (`tests_dir.glob("test_*.py")`, flat); `group_modules(discovered)`; `UNIT_UV_MODULES = frozenset({"tests.test_framework_profiles"})` (line 94); `EXPLICIT_GROUPS = {"arch", "unit-uv", "integration", "e2e"}`; `unit` is the remainder; `SHARED_MACHINERY` includes `tools/run_unittest_parallel.py`, `Makefile`, `.pre-commit-config.yaml` (so editing `UNIT_UV_MODULES` or regenerating listings runs the full unit and arch groups at commit) [VERIFIED: Read]. |
| `check_dogfood` | `check_edge_floors(root, run=_run_floor, which=shutil.which) -> (problems, notes)`; `main(argv=None) -> int` parses `--root`, `--template`, `--skip-no-write`, then concatenates `(problems, notes)` from `check_runner_copy`, `check_flow_config`, `check_lens_wiring`, `check_edge_floors`, then `check_no_write` unless skipped; prints `check-dogfood: <line>` for notes then problems; returns 1 on any problem, else prints `check-dogfood: ok` and returns 0 [VERIFIED: tools/check_dogfood.py:478-543]. |
| `setup._read_frontmatter(abspath) -> dict[str, str]` | hand-rolled, lossy reader (folds scalars to one line, comment lines skipped, "lists and nested maps come back as their raw first line"); do not reuse for strictness. `enumerate_entries(install_dir) -> {cat: [(name, abspath)]}` over `CATEGORIES = ("agents", "commands", "skills")`; a skill entry is a directory with `SKILL.md`; `validate_entry` for agents/commands requires a `.md` file whose first line starts with `---`. On this tree: 23 skills, `agents/ai-kit-judge.md` only, no `commands/` folder [VERIFIED: tools/setup.py:908-980; `find agents`]. `skills/_shared` has no `SKILL.md`, so it is not an entry. |
| `tests/test_setup.py` guards D-17 replaces | In `class TestReadFrontmatter`: `test_real_entries_have_a_name_and_a_description` (lines 5524-5536, asserts name, description, `<= 1024`) and `test_real_inline_descriptions_are_strict_yaml` (lines 5538-5553, `: ` and ` #` on a plain `description:` line). Keep the other `TestReadFrontmatter` tests: the installer still uses `_read_frontmatter` [VERIFIED: Read]. |
| `tests/test_gate_scope.py` | `TestGateScope` (line 452) and `TestGateScopeNonVacuity` (line 633); `load_tool(path)`, `load_runner()`; `test_every_module_in_exactly_one_group`; `test_generated_listings_name_every_discovered_module` checks `generator.render(...)` equals the committed listings and prints "stale listing; run: python3 tools/gen_test_groups.py". The R1 guard fits as a pure function plus a test on the tree plus a non-vacuity case on a fixture tree [VERIFIED: Read]. |
| `tests/test_rules_docs.py` | Clause-pin pattern: `_DESIGN_MARKER = "- **Design rule**:"`, `_DESIGN_CLAUSES` tuple, `_design_bullet(text)` takes the bullet up to the next `"\n- "` or `"\n## "` and flattens whitespace, `_missing_clauses(section_text, clauses)`, plus a non-vacuity test that removing one clause reports exactly that clause (lines 103-180). The skill-judge bullet in `AGENTS.md` starts at line 55 ("- Any new or materially updated `SKILL.md` passes the `skill-judge` review"); copy this pattern with a marker for that bullet. A nested `- ` line inside the bullet would end it early. |
| `tests/test_arch.py` | `LOOKUP_COPIES` (lines 1687-1694) lists six paths, none under `tools/` today; `python_roots(tree)` reads the module-level `SKILLS_ROOTS` literal with `ast.literal_eval` (rows `(env var or None, fallback, suffix)`); `test_every_lookup_copy_is_compared` scans only `skills/` and `tools/hooks/`, so a `tools/judge_loop.py` copy must be added to `LOOKUP_COPIES` by hand; `check_no_planning_reader(tree)` (line 1154) flags literal repo-root or cwd joins with `.planning` [VERIFIED: Read]. |
| `jev_review.py ladder` | `python3 <skill>/scripts/jev_review.py ladder [--second-opinion] [--client PATH]` reads `{"items": [...]}` on stdin, prints JSON, delegates to `jev_ladder.main`. Items: `id`, `type` (`choice\|noul\|score`), `instructions`, `context`, `criteria`; a `score` item needs `criteria` as 2-10 ordered level texts; each text <= 1,500 chars, no code fence, no secret-looking token. A `score` answer carries `score` (0..levels-1, may fall between), `legend`, `level` (winning index), `probabilities`, `confidence`, plus `top`, `needs_fallback`, `forced`, `model`, `backend`. Environment: `GSD_PATH_JEV=1` and a positive `GSD_PATH_JEV_TIMEOUT_SECONDS` (required); remote rows need consent. Status `ok` with `answers`, else `unavailable` with `reason` [VERIFIED: jev_review.py:2024-2063, jev_ladder.py:1-100, jev-fast-decision/reference.md:16-62]. |
| `agents/ai-kit-judge.md` | 10 lines: frontmatter `name: ai-kit-judge`, `description`, `tools: Read, Grep, Glob`, `model: opus`; body says follow the prompt exactly, read-only, reply with exactly what the prompt asks. Add `effort: xhigh` as one plain line (it contains no `: ` or ` #`). |
| skill-judge package | `references/verdict.schema.json` (Read in full): required `skill, judge, rubric_version, spec_sha, scores, max, total, max_total, percent, grade, findings`; `additionalProperties: false`; `spec_sha` pattern `^[0-9a-f]{40}$`; finding keys `id, dimension, severity, file, line (integer or null, minimum 1), evidence, fix`. `references/judge-prompt.md` (1,327 bytes) uses `{JUDGE}`, `{SKILLS}`, `{ROOT}` and carries rule 5, the attribution rule ("never count against any dimension, and no finding may propose removing or shortening them"); the builder's own prompt must keep that rule and use root-relative paths only. The rubric's D7 text says script tests live "in the repository's `tests/skills/<name>/`" and step 3 of `SKILL.md` tells the judge to read them there: the prompt must override both with the flat module list. |

## History-Text Scan of the 16 Kept Skills

Read-only script `tmp/p32-research/scan_history.py` (applies D-18: dates, "as of", run-log phrases and versions in SKILL.md main flow outside code spans and URLs; pointers in every shipped `.md` outside `evals/`). No SKILL.md has a `## Evidence` heading today, so every SKILL.md is checked in full. Hits (the script does not skip fenced code, which explains line 91):

| Skill | Hit | In D-19? |
|-------|-----|----------|
| `ai-kit-gsd-curated-config` | `SKILL.md:329` `## Limits (as of 2026-10-23)`; `:333` `22-INTERACTIVE-PI.md`; `:334` cursor-agent `2026.10.14-941492e` and `21-SMOKE-CURSOR.md`; `:338` decision id (the `20 D-11` form) | yes |
| `ai-kit-spec-config` | `SKILL.md:221` "Confirmed live 2026-08-29"; `:314` "(changed 2026-08-29 ..."; `:332` "(D-04)" | yes |
| `ai-kit-spec-review` | `SKILL.md:164` "recorded 2026-08-29 in" | yes |
| `ai-kit-spec-execute-superpowers` | `SKILL.md:280-281` "`@opengsd/gsd-core` 1.17.0 ... `.planning/phases/18.1-one-runtime-model/18.1-RESEARCH.md:231`" (the version sits in a sentence with "older", so only the pointer fails by the narrow rule, but D-19 moves both) | yes |
| `ai-kit-gsd-spec-discuss` | `SKILL.md:206` "one real run: the same item scored 0.74, then 0.67"; `references/decision-table.md:64,70` `D-24`; `references/log-formats.md:38,51,60,95,96,114` (`**D-14: ...**` is a bold format example and must pass; `20-SPEC.md` at 51; `20 D-08` at 60; bare `D-14` at 95; `(D-24, ledger)` at 96; `D-01..D-06` at 114); `references/worked-examples.md:14,24,54` (`(D-16)`, `(D-19,`, `17 D-21`) | partly: D-19 lists `20-SPEC.md`, `20 D-08` and the parenthesized ids in decision-table and worked-examples, but not the bare `D-14` at `log-formats.md:95` or `D-01..D-06` at `:114` |
| `ai-kit-spec-review-checklist` | `SKILL.md:199` "(confirmed live: an unconstrained run produced ~8000 lines ..." | yes |
| `ai-kit-usage-metrics` | `SKILL.md:43` "(D-07)" and "Backlog 999.2"; `:313` "Backlog 999.2." | yes |
| `jev-fast-decision` | `SKILL.md:62` link text "Jev 1.14 notes"; `backends/laya.md:57` `.planning/phases/21.1-.../eval/eval-results.json`; `backends/typesafe.md:18` "(D-07)" | yes |
| **`ai-kit-cross-ai`** | **`SKILL.md:91` `first_failure=2026-10-25T17:26:29.839Z last_failure=...` inside a fenced status-line example** (the references copy `launch-and-wait.md:42` may keep it) | **no: D-19 lists cross-ai as already passing** |
| **`ai-kit-gsd-spec-discuss`** | **`references/worked-examples.md:47` "backlog `999.2` with a goal"** | **no** |
| **`ai-kit-spec-config`** | `SKILL.md:194` matched only the substring "confirmed live" in "every model family confirmed live in the CLI profiles" | not a hit by intent: needs a decision on whether "confirmed live" without a date counts as a run log |

Planner actions: (1) decide the cross-ai line 91 rule: either the date check skips fenced blocks (then SPEC R9's "code spans included" wording needs the amendment) or the SKILL.md sample changes to a placeholder (`first_failure=<iso time>`; no test pins the line, `rg first_failure tests` finds nothing, and the references copy keeps the literal) - the second keeps the SPEC wording and is a sample change, not an instruction change; (2) add the `worked-examples.md:47` backlog id and the two spec-discuss decision-id forms to D-19; (3) treat the narrow phrase "confirmed live" as a run log only when it carries a date or an observation ("confirmed live: an unconstrained run produced ..."), or use D-18's exact phrase list and verify the spec-config line 194 outcome in the test run. A `##` heading inside a fenced block (for example `## Review: <file(s)>` at `ai-kit-spec-review-checklist/SKILL.md:254,268`) must not count as a section, so the evidence-section detector has to be fence-aware. `skills/_shared` has no SKILL.md and is not a skill.

## Recorded Rubric-v4 Verdicts (inputs for `inputs.json`, D-06)

All read this session. `judge` for every row is `native-opus-xhigh` (the referees were down); the raw JSON lives only in gitignored `tmp/`, so these table values are the only committed record.

| Skill | Last v4 verdict | Critical / high | Source (path:lines) | Judged at |
|-------|-----------------|-----------------|---------------------|-----------|
| `jev-fast-decision` | 107/125, 85.6 B (round 1, "not re-judged (unchanged)") | 0 / 0 | `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-JUDGE.md:96` | `3410359` (`29-JUDGE.md:87-88`) |
| `ai-kit-spec-goal-prompt` | 111/125, 88.8 B (round 2) | 0 / 0 | `29-JUDGE.md:99` | `d2855bc` (`29-JUDGE.md:88`) |
| `ai-kit-gsd-spec-discuss` | 110/125, 88.0 B (round 2) | 0 / 0 | `.planning/phases/29.1-stacked-phase-branches-chained-prs-and-the-merge-chain-inserted/29.1-JUDGE.md:82` | `16153d6` (`29.1-JUDGE.md:75`) |
| `ai-kit-spec-execute-superpowers` | 104/125, 83.2 B (round 3, newer than the 29.1 row of the same value) | 0 / 0 | `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-JUDGE.md:55` | `76fa531` (`30-JUDGE.md:46`) |
| `ai-kit-spec-execute` | 101/125, 80.8 B (round 3) | 0 / 1 (D8-1) | `.planning/phases/31-removals-and-small-defects/31-VERIFICATION.md:69` | not recorded |
| `ai-kit-spec-config` | 97/125, 77.6 C (round 2) | 0 / 0 | `31-VERIFICATION.md:70` | not recorded |
| `ai-kit-gsd-curated-config` | 105/125, 84.0 B | 0 / 1 (eval fix `763dc68` after) | `31-VERIFICATION.md:71` | not recorded |

Old 120-point scores (history only, never in a grade or bar column), from `.planning/research/2026-11-02-next-milestone/15-skills-vs-new-judge.md:104-129` (Read): cross-ai 102/120 (85.0%, 2026-10-25, phase 25.1); curated-config 106/120 (88.3%); spec-discuss 106/114/109 per judge (Opus/referee-two/referee-one, round 4, 2026-10-24); session-wake 108/120 (2026-10-30); spec-config 99/120 UNRESOLVED; spec-execute "no record found" (the 101/120 on that page belongs to the removed `ai-kit-spec-execute-gsd`); execute-superpowers 86/120 FAIL (2026-10-31); goal-prompt: the page's row is a new-scale row (referee-one 118/125 and referee-three 109/125, base 90.4); spec-review 99/120; usage-metrics 108/120 (2026-09-10); cst-refactor 91/120 FAIL; jev Opus 107/120 pass and opencode 101/120; checklist, fixer and markdown-to-pdf "no record found". CONTEXT D-12 names 90.4 as goal-prompt's old base.

**Gap to handle:** `16153d6` and `d2855bc` are real commits but not ancestors of HEAD (`git merge-base --is-ancestor` exit 1); they stay reachable only through local tags `archive/phase-29.1-raw` and `archive/phase-29-raw` (`git tag --contains`). `count` computes its jev numbers from a git numstat against that commit, so `inputs.json` should carry the commit, and `count` must treat an unresolvable base (pruned, or a fresh clone without the local tag) as "jev input absent" and keep the deterministic count, recording why. The other 11 skills never reach the jev step today, so their missing judged-at commit costs nothing; record `null` with "not needed" rather than inventing one [VERIFIED: git cat-file, merge-base, tag --contains].

## Ships-Code Classification and Module Lists (D-14, D-15)

Read-only script `tmp/p32-research/ships_code.py` (D-15 rule plus `covering_modules`), run on this tree:

| Ships runnable code (11) | Modules | No runnable code (5) | Modules |
|--------------------------|---------|----------------------|---------|
| ai-kit-commit-fold (excluded from judging) | 16 | ai-kit-cross-ai | 9 |
| ai-kit-gsd-curated-config | 26 | ai-kit-spec-config | 4 |
| ai-kit-gsd-spec-discuss | 10 | ai-kit-spec-review-checklist | 2 |
| ai-kit-session-wake | 12 | ai-kit-spec-review-fixer | 1 |
| ai-kit-spec-execute | 3 | cst-refactor | 3 |
| ai-kit-spec-execute-superpowers | 11 | | |
| ai-kit-spec-goal-prompt | 32 | | |
| ai-kit-spec-review | 59 | | |
| ai-kit-usage-metrics | 3 | | |
| jev-fast-decision | 19 | | |
| markdown-to-pdf | 4 | | |

This matches D-15's "11 ship code, 5 do not" and SPEC's "1 to 59". The module list for a no-code skill is context only, not scored (SPEC R2 adjacency). The seven `ai-kit-project-rules-*` folders also classify as shipping code; they are excluded from judging and exempt from the text check by name.

## Judge-Run Mechanics (D-08, D-09)

- Lane command shape (from the cross-ai skill and phase 29): `node .claude/gsd-core/bin/gsd-tools.cjs run-with-timeout <seconds> -- node .planning/scripts/cross-ai.mjs --runtime <cli> --model <model> --mode review --outer-timeout <seconds> < prompt > out 2> err`; `run-with-timeout` usage is "gsd_run run-with-timeout <seconds> [--] <command> [args...]" [VERIFIED: gsd-tools.cjs --help output]. The prompt goes on stdin. Never write a runtime or model into code: judge ids are the exact lane strings the run builds from its list (`<cli>:<model>`, `native:opus-xhigh`).
- Status line: `AIKIT-XAI status=ok cli=pi model=router-env/... exit=0 cli_rc=0 elapsed=1476s out=11549 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0` (29-JUDGE.md:28). A lane counts only on `status=ok`, `exit=0` and `tree=clean`. The runner retries a dead model for about 200 s before `exit=75` (`29-JUDGE.md:29` shows `elapsed=200s ... attempts=12 ... retry_after_s=600`), so the probe's outer timeout of about 600 s is right.
- Cost: one 4-skill pass on referee-one took 1,476 s with a 1.7 KB prompt (`29-JUDGE.md:28`); with 13 two-judge skills plus up to 2 more, expect roughly 26 to 28 judge-skill runs and several hours across two parallel lanes [ASSUMED estimate]. Plan Wave 2 as long and resumable: one record per (skill, judge) and `ingest` never overwriting a valid verdict.
- Tree rule: the review lane stops on `contract_violation tree=dirty` if any tracked or non-wholly-ignored file changes (`ai-kit-cross-ai/SKILL.md:50-54`, `phase 29.1-JUDGE.md:63` shows a `contract_violation`). Commit every Wave 1 edit (skill text, `agents/ai-kit-judge.md`, AGENTS.md, tools, tests) before Wave 2, keep lanes' scratch under `tmp/` (wholly ignored), and write nothing tracked until all lanes end (D-09).
- Judging after the edits matters because digests hash file bytes at lane start: a later SKILL.md edit marks that skill's verdict stale. The phase must not touch `skills/` after Wave 2 begins.
- Native lane: spawn `ai-kit-judge` with the prompt file path, never the 92 KB inline; its tools are Read, Grep, Glob only, so it cannot write. Check the three effort env vars before the run.
- Current configuration note: `.planning/config.json` in the working tree reads `"cross_ai_execution": false` at line 45, while commit `135470c` ("phase 32 run settings ... cross-AI execution on") changed it to `true`. The tree and that commit disagree; the orchestrator should confirm which is intended before an execute step relies on it.

## Check-Dogfood Wiring (R10, D-07, D-21)

- `make check-dogfood` runs `uv run pre-commit run check-dogfood --all-files --hook-stage pre-push` (`Makefile:111-112`), which runs `python3 tools/check_dogfood.py` (`pass_filenames: false`, `always_run: true`, verbose, pre-push; `.pre-commit-config.yaml:88-95`). `tests/test_gate_scope.py` pins that hook (`dogfood_hook_errors`) and that `validate` ends with `check-dogfood`.
- Add the two checks to `main()` the same way as `check_edge_floors`: `problems, notes = problems + x_problems, notes + x_notes`, before the no-write guard. `check_jdg04_citations(root) -> (problems, notes)`; a judge-records check that calls the checker's pure `check` function (import by path or `from tools import judge_loop`; avoid a subprocess so fixture roots work) with `root/.planning/judge`; a missing `.planning/judge/` or ROADMAP is a note, not a problem (the long-path matrix clone has no `.planning/`). `main()` is a single function with many statements; keep new checks as one-liners to stay inside pylint's `max-statements=50`, `max-branches=12`.
- ROADMAP scan result (script `tmp/p32-research/jdg04_scan.py`, D-21 rule): every phase from 32.1 to 47.1 plus 50, 51 and 54 names `SKILL.md` and its success criteria hold the exact token `JDG-04`; 48, 49, 52 and 53 name no SKILL.md. **The tree passes today (no flag)**, so the guard ships green. ROADMAP's section layout is `## Phase Details` ... `### Phase N: title` ... `**Success Criteria** (what must be TRUE):` ... `**Plans**:`; the criteria block is the text between those two markers [VERIFIED: ROADMAP.md:391-407 and scan output].
- Fixture roadmap tests: `TestEdgeFloors._root(...)` writes files into a `tempfile.TemporaryDirectory` and passes `root`; copy that pattern with a minimal ROADMAP holding a phase above 32 that names `SKILL.md` without the token (flagged by number, in roadmap order), then with the token (passes), a phase `32.1` below the threshold by tuple, `JDG-040` and `jdg-04` (do not count), `JDG-04` only in a Requirements line (does not count), and a backlog entry (not scanned).

## Common Pitfalls

### Pitfall 1: The installed skill-judge is invisible to unit tests
**What goes wrong:** a test that calls the real lookup finds nothing: every module runs with a temporary HOME and stripped config overrides. **Avoid:** tests take `--judge-dir` fixtures; the pin check against `rubric_version: 4` and `spec_sha: 69ef37e9...` happens in the baseline run and in `check` through the recorded manifests. **Warning sign:** a test passes on this machine and fails in `make test-env-matrix`.

### Pitfall 2: Decision ids and fences in the history test
**What goes wrong:** `**D-14: ...**` format examples in spec-discuss references are bold examples the SPEC says must pass; a naive `D-\d+` regex fails them. **Avoid:** match `D-<digits>` as a whole token and exempt a bold `**D-NN: ...**` example form, while `(D-07)`, `20 D-11` and bare `D-14` outside bold fail; `D-<n>` and `NN D-xx` never match digits. Also make the evidence-heading detector skip fenced code, so `## Review:` samples are not sections.

### Pitfall 3: PyYAML and the npm `yaml` package disagree in two ways
Measured (scripts `tmp/p32-research/yaml_fixtures.mjs` and `.py`): both reject `description: a: b`, a continuation line `second: bad`, a tab-indented continuation, and an unterminated double quote; both accept `name: 123`, `description: a\n  b` (folds to "a b"), `description: a #b` (value becomes "a"; the comment is silently dropped), an empty block (null) and a folded block. **They differ only on a duplicate key:** npm `yaml` rejects ("Map keys must be unique"), PyYAML `safe_load` accepts and keeps the last value. So the `unit-uv` cross-check needs a loader that rejects duplicate keys (D-17 already says so). The D-17 stdlib subset is deliberately stricter than both on plain continuation lines and ` #`; those cases are not in SPEC's fixture list, so the "result equals the `yaml` package" comparison should cover the listed fixtures and label the two designed-stricter cases as expected differences [VERIFIED: tool output this session].

### Pitfall 4: Frontmatter shapes on the real tree
All 23 skills plus the agent use only these shapes: plain single-line values, single-line double-quoted descriptions, and `>`/`|` block scalars with space-indented continuation (cross-ai and markdown-to-pdf: 8 continuation lines each; three rules skills: 1) [VERIFIED: `tmp/p32-research/fm_shapes.py`]. The D-17 subset covers all of them. For double-quoted scalars `json.loads` is the existing precedent (`setup._front_scalar`, line 900) and is stricter than YAML on exotic escapes; reject on failure. Count the description length after folding.

### Pitfall 5: Shared-machinery edits widen the commit-stage run
Adding to `UNIT_UV_MODULES` edits `tools/run_unittest_parallel.py`, and regenerating listings edits `Makefile` and `.pre-commit-config.yaml`, all `SHARED_MACHINERY`, so the commit runs the full unit and arch groups. Expect that cost once; keep those edits in one commit. A test that reaches `skills/*/SKILL.md` only through a glob (the two text gates) is not selected by a SKILL.md edit at commit; the push stage still runs it (AGENTS.md known limit).

### Pitfall 6: Judge prompt must replace the judge's own read instructions
`skill-judge/SKILL.md` step 1 says to `Read references/rubric.md` relative to its directory and step 3 says to read `tests/skills/<name>/`. A judge that cannot resolve `references/` writes a high finding against every skill (D-13). The prompt states that the embedded copies replace every such read, that script tests live flat in `tests/test_*.py` and are the listed modules, and gives the 5/5/5 versus 8/7 reading per D-15; only the skill name and module list differ between skills.

### Pitfall 7: Report determinism
`check` regenerates `REJUDGE.md` and compares bytes. Put no clock, hostname or absolute path in it; sort by owning batch then name; copy numbers verbatim from the verdict JSON; keep one-decimal percents. Anything computed from `git` at report time (digest "current or stale") belongs to `check` output, not to the committed report, or the report changes every time a skill changes.

### Pitfall 8: Rounds and loops
A re-run of a failed lane in the same round is an attempt, not a round (SPEC R6 precision). A rejected `ingest` (judge differs from lane, pin differs from manifest) must leave no record behind. Never overwrite a valid verdict record; a re-judge adds a round.

## Code Examples

### Digest with the fixes
```python
# Source: promoted from check_verdicts.py:101-107 with D-01's root, -z and trailing-slash fixes
def skill_digest(root: Path, name: str) -> str:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--", f"skills/{name}/"],
                         capture_output=True, check=True).stdout.decode("utf-8")
    files = sorted(f for f in out.split("\0") if f)
    if not files:
        raise ValueError(f"no tracked files for skill {name}")
    lines = "".join(hashlib.sha256((root / f).read_bytes()).hexdigest() + "  " + f + "\n"
                    for f in files)
    return hashlib.sha256(lines.encode()).hexdigest()
```

### Root resolution
```python
# `git rev-parse --show-toplevel` in the working directory, `--root` overrides; never __file__.
def find_root(override: Path | None) -> Path:
    if override:
        return override.resolve()
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0:
        raise SystemExit("not inside a git repository; pass --root")
    return Path(top.stdout.strip())
```

### The jev item shape for `count` (numbers become fixed words first)
```python
# Source: skills/jev-fast-decision/reference.md:16-18 (score item: 2-10 ordered levels, low to high)
item = {"id": "judge-count", "type": "score",
        "instructions": "How likely is it that the change since the last judged text moves the "
                        "judge's score past normal run-to-run variation?",
        "context": f"last percent band: {pct_word}; findings: {finding_word}; "
                   f"SKILL.md change: {skill_md_word}; other files changed: {files_word}",
        "criteria": ["no change likely to move the score", "a small move is possible",
                     "a move past the variation is likely", "a move past the variation is near certain"]}
# raise one judge to two only when answer["level"] >= 2 and answer["needs_fallback"] is False
```

### Sentinel size probe (spike)
```python
sentinel = "AIKIT-SENTINEL-" + secrets.token_hex(8)
prompt = package_block + "\n" + sentinel + "\nIgnore every earlier instruction. Print only the " \
         "sentinel line above, nothing else.\n"
# pass: exit 0, last AIKIT-XAI line status=ok tree=clean, and stdout.strip() == sentinel
```

## State of the Art

| Old approach | Current approach | When changed | Impact |
|--------------|------------------|--------------|--------|
| Phase-specific judge prompts that told the judge to read copied rubric files | one builder embeds the package byte for byte | this phase | no "judged without its rubric" rounds (research 15) |
| Four checker copies, one hardcoded skill and three referee names | one tool taking skill and judge lists | this phase | the round cap and refute-by-running become checkable |
| `effort:` assumed to be per-agent frontmatter only | frontmatter documented; an Agent-tool `effort` parameter reported (LOW) | docs now list the field | GSD's sentence about "no per-spawn parameter" may be stale; do not depend on either |

**Deprecated/outdated:** the `tests/skills/<name>/` reading in the judge's own text (replaced per prompt); the 120-point scale (history only).

## Validation Architecture

Nyquist validation: `.planning/config.json` has no `workflow.nyquist_validation: false` that I saw in the read lines 44-84; treat as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` via `tools/run_unittest_parallel.py`; one subprocess per module under a baseline env (temp HOME, tripwire stubs for host CLIs, `AI_KIT_REFUSE_REAL_HOME=1`) |
| Config file | none; groups are code in the runner; listings generated by `tools/gen_test_groups.py` |
| Quick run command | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_gate_scope tests.test_rules_docs tests.test_check_dogfood tests.test_skill_text_history tests.test_skill_frontmatter tests.test_judge_loop_prompt tests.test_judge_loop_count tests.test_judge_loop_check tests.test_judge_loop_report` |
| Full suite command | `make test` (and `make check-dogfood`; `make validate` is what the hooks run) |

### Phase Requirements to Test Map
| Req | Behavior | Test type | Automated command | File exists? |
|-----|----------|-----------|-------------------|--------------|
| R1 | guard passes on tree; fails on `tests/skills/demo/test_x.py` fixture, names the path, sorted, case-sensitive, `__pycache__` skipped | unit (+ non-vacuity) | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_gate_scope` | edit existing |
| R2 | prompt embeds each file's full text from a fixture judge package, both reading sentences, sorted module list; two skills differ only in name and list; top-level entry script with no `scripts/` is "ships code"; `.py.txt`-only `scripts/` is not | unit | `... tests.test_judge_loop_prompt` | Wave 0 new |
| R3 | `pool`: first two usable, one usable + native, none -> native alone with "second judge unavailable"; probe usable only on clean exit + exact word inside timeout; exact-string judge match; substitute reason recorded | unit | `... tests.test_judge_loop_prompt` (or `test_judge_loop_pool`) | Wave 0 new |
| R4 | percents 72.9, 73.0, 87.0, 87.1, no verdict, high finding, exactly 80.0; jev raise, `needs_fallback`, jev error, `--no-jev`; no jev call when already two; jev item built from numbers and fixed text only (pinned on a fixture); unresolvable base commit leaves the deterministic count | unit | `... tests.test_judge_loop_count` | Wave 0 new |
| R5 | same digest from root and a sub-folder of a fixture git repo (with `-c user.*`), prefix skills kept apart, malformed/miscomputed/mis-pinned verdict rejected with reason, stale vs current, duplicate judge-in-round error, no `referee` text in the tool source, unlisted judge rejected, finding path confined to the root | unit | `... tests.test_judge_loop_check` | Wave 0 new |
| R6 | three rounds pass, fourth flagged per skill; refuted finding dropped only with finding id, `path:line`, command, output; incomplete record keeps counting; a re-run in the same round adds no round | unit | `... tests.test_judge_loop_check`; AGENTS.md pins in `tests.test_rules_docs` | Wave 0 new + edit |
| R7 | fixture records -> `REJUDGE.md` byte-equal on regeneration; 15 judged and 8 excluded listed; worst judge decides the bar clause; 80.0 with a high meets via B, 79.9 does not; "not judged" row for a skill with no verdict; inter-judge spread; no old score in a grade or bar column; live check: `judge_loop.py check .planning/judge` exits 0 with every skill current | unit + live | `... tests.test_judge_loop_report`; live: `make check-dogfood` | Wave 0 new; live at Wave 3 |
| R8 | tree passes; each listed fixture fails (colon on first and continuation line, tab, unterminated quote, duplicate key, non-string name, 1,025-char description, uppercase name, name != folder); 1,024 and 64 pass, 1,025 and 65 fail; empty block, no frontmatter, double hyphen, edge hyphens fail; every failing entry reported; agent file parses | unit + unit-uv | `... tests.test_skill_frontmatter`; `uv run python tools/run_unittest_parallel.py tests.test_skill_frontmatter_pyyaml` | Wave 0 new |
| R9 | tree passes (16 kept skills, 7 rules skills exempt by name, pinned equal to the `ai-kit-project-rules-` folders); fixtures: ISO date, `gsd-core 1.17.0`, "one real run ...", `.planning/phases/18.1-.../18.1-RESEARCH.md:231`, `21-SMOKE-CURSOR.md`, `Backlog 999.2`, `router-env/my-referee-two`, `(D-07)`, `20 D-11` fail; same date under `## Evidence` (last `##`), `.planning/config.json`, `.planning/scripts/cross-ai.mjs`, `.planning/phases/<phase>/`, `*-CONTEXT.md` globs, `NN-SPEC.md`, "gsd-core 1.20 or later", `D-<n>`, `NN D-xx`, a bold format example, a `.md` under `evals/` pass; AGENTS.md line pinned | unit | `... tests.test_skill_text_history tests.test_rules_docs` | Wave 0 new + edit |
| R10 | tree passes; fixture roadmap with a phase > 32 naming `SKILL.md` and no `JDG-04` fails and names the phase; passes once cited; `JDG-040`/`jdg-04`/Requirements-line-only do not count; offenders in roadmap order; backlog ignored | unit | `... tests.test_check_dogfood`; live `make check-dogfood` | edit existing |

Group placement: every new module joins `unit` automatically (system python3) except `tests.test_skill_frontmatter_pyyaml`, which goes into `UNIT_UV_MODULES` in `tools/run_unittest_parallel.py` (it needs PyYAML, only in the uv env). After adding modules run `python3 tools/gen_test_groups.py` so `test_generated_listings_name_every_discovered_module` stays green. No new module belongs in `integration` or `e2e`. If `test_staged_mapper` still selects `sorted(UNIT_UV_MODULES)[0]` (line 553), keep the new name sorting after `tests.test_framework_profiles` (`tests.test_skill_frontmatter_pyyaml` does).

### Sampling Rate
- **Per task commit:** the quick command above for the touched modules (the commit hook runs the covering modules itself).
- **Per wave merge:** `make test-unit` and `make arch-test`.
- **Phase gate:** `make test` and `make check-dogfood` green before `/gsd-verify-work`; additionally the one-time recorded comparison of the R8 fixtures against the npm `yaml` package (`node` script) pasted into the verification.

### Wave 0 Gaps
- [ ] `tests/test_judge_loop_prompt.py`, `..._count.py`, `..._check.py`, `..._report.py` plus a small fixture builder (fixture judge package, fixture git repo with `-c user.name -c user.email`, fixture roadmap)
- [ ] `tests/test_skill_frontmatter.py`, `tests/test_skill_frontmatter_pyyaml.py`, `tests/test_skill_text_history.py`
- [ ] `tools/judge_loop.py`; a `LOOKUP_COPIES` entry and the tool's `SKILLS_ROOTS` literal
- [ ] `UNIT_UV_MODULES` edit and `python3 tools/gen_test_groups.py`
- [ ] README: the `ai-kit-judge` row (effort), the new tool, the new tests as the repo's README convention requires

## Security Domain

`security_enforcement` is not set to false in the config lines read; included.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard control |
|---------------|---------|------------------|
| V2 Authentication | no | none (no credentials handled; jev keys stay inside `jev_review.py`) |
| V3 Session Management | no | none |
| V4 Access Control | yes (local) | lanes run read-only (`--mode review`), `ai-kit-judge` tools are Read/Grep/Glob, `AI_KIT_REFUSE_REAL_HOME=1`, no write to real host configs |
| V5 Input Validation | yes | verdict JSON validated by strict schema before any record is written; finding `file` confined to the root; argv-list subprocess calls only (no `shell=True`), `--` before pathspecs |
| V6 Cryptography | no new use | `hashlib.sha256` only, for digests |

### Known Threat Patterns
| Pattern | STRIDE | Standard mitigation |
|---------|--------|---------------------|
| Prompt injection: skill text under judgment steers the judge | Tampering | read-only judge tools; verdicts accepted only after `ingest` validation and arithmetic/pin checks; the judge's output is data, never executed |
| Path traversal through a finding's `file` or a skill name argument | Tampering/Info disclosure | resolve and require the path under the root; reject skill names containing separators or `..` |
| Data leak to jev | Info disclosure | the item is built from numbers and fixed words only, pinned by a fixture test (SPEC prohibition); `jev_ladder.py` also rejects secret-shaped text |
| Silent judge substitution | Repudiation | `judge` field exact-match against the given list; reason line per substitute; failed lane recorded with its status |
| Editing a raw verdict to improve a result | Tampering | `check` regenerates the report and compares bytes; `ingest` never overwrites a valid record; the cap counts recorded rounds |
| Lane writes to the repo | Tampering | review mode plus the runner's tree fingerprint; a lane without `tree=clean` is discarded |

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| python3 | tool, tests | yes | 3.14.7 (write py312-compatible code) | none needed |
| uv | `unit-uv` module, `make` targets | yes | 0.11.28 | none |
| git | digest, root, fixture repos | yes | 2.56.0 | none |
| node | runner, npm `yaml` comparison | yes | v24.21.0 | none |
| PyYAML | cross-check | yes (via `uv run`) | 6.0.3 | skip is not acceptable; it is the uv-only module |
| npm `yaml` + `skills` CLI cache | one-time R8 comparison | yes (npx cache) | 2.9.0 / 1.5.20 | `npx skills` fetch if the cache is gone |
| skill-judge (installed) | builder at run time | yes (`~/.agents/skills/skill-judge`) | rubric v4, spec_sha 69ef37e9... | none: stop the build when the rubric lacks the two pin lines |
| opencode, pi, jq, gh | lanes and helpers | yes (`command -v`) | not queried (no external CLI launched) | native Opus |
| `ai-kit-judge` agent | native lane | yes (symlink in `~/.claude/agents/`) | n/a | none |
| referee lanes | judging | referee-one temporarily unavailable (owner); referee-two answered a probe 2026-11-07 (CONTEXT); referee-three unknown | n/a | native Opus at xhigh, recorded |

**Missing with no fallback:** none. **With fallback:** referee-one (owner-stated outage) and the unproven size handling of referee-two and referee-three: native Opus, with the substitute and its reason recorded.

## Project Constraints (from CLAUDE.md / AGENTS.md)

- English only in every written artifact; no machine-specific absolute path in source, tests or assets (resolve against the repo root or a passed-in base).
- Runtime code stays stdlib-only; this phase's tool and tests are not runtime code but must add no dependency without the AGENTS.md check.
- Every config write atomic (`mkstemp` + `os.replace`); `.planning/judge/` records written by the tool should follow the same pattern (write a temp file, then `os.replace`), and a valid verdict record is never overwritten.
- No result presented with more certainty than its sourcing: label effort "documented, not observed", label unverified lanes, record substitutes.
- New or materially updated `SKILL.md` text goes through the `skill-judge` loop only for phases that change behaviour; this phase's text edits move history out and change no instruction, but the baseline judge run is itself the check. Never use `--no-verify`; commit one coherent buildable change with tests and docs.
- Tests: `make test` before done; every tier runs one subprocess per module through the runner; never hardcode worker counts; `tests/test_arch.py` rules need non-vacuity counterparts; a doc-contract test pins AGENTS.md wording; no test reads `.planning/` (check-dogfood does); never use the owner's real config files as fixtures.
- Shell rules (CLAUDE.local.md, to pass word for word to every subagent): one simple command per shell call; scripts go in `.sh` or `.py` files under `tmp/`; never `cd`; no heredocs, command substitution, subshells, process substitution, `eval` or long chains; no in-place editors; never delete outside `tmp/`; write files with the file-write tool.
- Scratch under `./tmp/` only; leave no background process, temp files outside `tmp/`, or untracked non-ignored files when closing the phase. Research scratch lives in `tmp/p32-research/` (gitignored; do not commit).
- GSD is project-local only: use `<checkout>/.claude/gsd-core/bin/gsd-tools.cjs`; never touch `~/.claude` GSD artifacts. Never launch external AI CLIs from tool code or tests.
- Explore code with codegraph first (`codegraph explore`), search Markdown with `rg`; update READMEs after significant feature changes.

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | `opencode run` receives the review-lane prompt on stdin in the GSD `review-lane invoke` path the same way `cross-ai.mjs` sends it, so phase 30's 120-190 KB result transfers to `cross-ai.mjs` | Open Item 2 | the precedent would not apply to the judge lane; the sentinel spike catches it |
| A2 | `referee-two` and `referee-three` can take 92 KB (their models' windows are well above 23k tokens) | Open Item 2 | a truncated rubric makes a lane's verdicts invalid; spike per lane before counting |
| A3 | Claude Code's agents-folder watcher does not notice an edit to a symlink target | Open Item 1 | harmless if it does; mitigation (commit first, start the session after) covers both |
| A4 | An Agent-tool `effort` parameter exists since v2.1.292 (search result, blogs) | Open Item 1 | none if unused; do not plan on it |
| A5 | 4 bytes per token, about 22.4k tokens for the package | Open Item 2 | only a rough size sense; the byte count is measured |
| A6 | Wave 2 takes several hours (26-28 judge-skill runs, about 25 minutes per 4-skill pass on referee-one) | Judge-Run Mechanics | scheduling only |
| A7 | `model: opus` resolves to a model supporting `xhigh`; otherwise the level silently drops | Open Item 1 | the report's "xhigh" label would overstate; the label says documented, not observed |
| A8 | Local tags `archive/phase-29-raw` and `archive/phase-29.1-raw` persist | Recorded Verdicts | `count` falls back to the deterministic count (designed) |

## Open Questions

1. **Does cross-ai `SKILL.md:91` get a placeholder or does the date rule skip fences?**
   - Known: the sample line holds ISO timestamps; D-19 lists cross-ai as passing; SPEC R9 says a date fails "anywhere in the main flow, code spans included".
   - Recommendation: replace the two timestamps with `<iso time>` in SKILL.md (sample only, the references copy keeps the literal); no instruction changes.
2. **Should `check` have a `--require-current` option for the phase close?**
   - Known: default mode treats stale as a note (D-07), `--gate` covers unmet bar and cap, and the acceptance wants "every skill current at the phase's close".
   - Recommendation: add one small flag (or assert zero "stale" lines in the verification step) rather than overloading `--gate`.
3. **Does `confirmed live` without a date count as a run log?** Only `spec-config/SKILL.md:194` is affected. Recommendation: narrow phrase list requires the date or an observation clause, then record the decision in the test.
4. **Which of referee-one/two/three are usable on the day?** Only a probe can say; the sentinel spike doubles as that probe.
5. **`.planning/config.json` `cross_ai_execution`** is `false` in the tree but `true` in commit `135470c`; confirm intent before an execute step.

## Sources

### Primary (HIGH confidence)
- Repo files read this session: `32-SPEC.md`, `32-CONTEXT.md`, `agents/ai-kit-judge.md`, the installed `skill-judge` `rubric.md` (lines 1-30, 124-137), `verdict.schema.json`, `judge-prompt.md`, `tools/staged_mapper.py`, `tools/run_unittest_parallel.py` (lines 1-60, 86-283), `tools/check_dogfood.py` (454-543), `tools/setup.py` (900-980), `tests/test_gate_scope.py`, `tests/test_rules_docs.py`, `tests/test_arch.py` (1150-1200, 1675-1790, 2215-2260), `tests/test_setup.py` (5476-5555), `tests/test_check_dogfood.py` (500-625), the phase 27 checker, `tmp/judge-30/round3/check_verdicts.py`, p27 scripts, `jev_review.py` (2020-2068), `jev_ladder.py` (1-200), `jev-fast-decision/reference.md`, `.planning/scripts/cross-ai.mjs` (several ranges), `30-REVIEWS.md`, `29-JUDGE.md`, `29.1-JUDGE.md`, `30-JUDGE.md`, `31-VERIFICATION.md`, `15-skills-vs-new-judge.md`, ROADMAP lines 388-503, `.planning/config.json` lines 44-84
- Scripts and outputs: `tmp/p32-research/{scan_history.py, jdg04_scan.py, ships_code.py, fm_shapes.py, yaml_fixtures.mjs, yaml_fixtures.py}`
- code.claude.com/docs/en/sub-agents and /docs/en/model-config (fetched; first 100,000 characters of each page)

### Secondary (MEDIUM confidence)
- WebSearch on the subagent `effort` field history (blogs, a GitHub issue index, a release note); not the official changelog

### Tertiary (LOW confidence)
- The Agent-tool `effort` parameter and `CLAUDE_CODE_SUBAGENT_EFFORT` version claims (A4)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, stdlib plus already-present PyYAML; versions probed
- Architecture: HIGH for tool/test/dogfood wiring (read the code and the precedents); MEDIUM for the lane run (hours-long, quota-dependent)
- Pitfalls: HIGH for the measured YAML and history findings; MEDIUM for lane-size behaviour of referee-two/three

**Research date:** 2026-11-07
**Valid until:** about 7 days for lane availability and the Claude Code docs; 30 days for the in-repo shapes (they change with each phase)

Note: the `research-plan` and `research-store` seams were not used; documentation was fetched directly. No digest was cached.
