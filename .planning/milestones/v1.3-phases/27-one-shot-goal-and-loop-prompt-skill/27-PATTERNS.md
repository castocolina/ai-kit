# Phase 27: One-shot goal and loop prompt skill - Pattern Map

**Mapped:** 2026-10-31
**Files analyzed:** 25 (new and modified)
**Analogs found:** 23 / 25
All analog paths are git-tracked. Line numbers are from this worktree at mapping time.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `skills/ai-kit-spec-goal-prompt/SKILL.md` | skill doc | n/a | `skills/ai-kit-gsd-spec-discuss/SKILL.md` (frontmatter, NEVER list, resolver block) | exact |
| `.../references/*.md` (4) | reference docs | n/a | `skills/ai-kit-gsd-spec-discuss/references/` | exact |
| `.../scripts/goal_prompt.py` | CLI (argparse subcommands, JSON out, exit 0 / 2) | request-response | `skills/ai-kit-gsd-spec-discuss/scripts/decide.py:623-645` (`main(argv, seams)`) | exact |
| `.../scripts/gp_common.py` | utility | transform | `phase_range.py:28-37` (`phase_key`), `skills/_shared/ai_kit_rules_common/makefile_parse.py:16` (`_TARGET_HEADER_RE`), `ai_kit_project_rules_cicd/package_scripts.py` | copy + parity |
| `.../scripts/gp_scope.py` | service (reads repo + injected JSON) | transform | `phase_range.py:125-145` (`propose` over `roadmap analyze` JSON) | role |
| `.../scripts/gp_host.py` | service (runs sibling CLIs) | request-response | `decide.py` `Seams` / `real_seams()` (injected `run_fn`) and `ai_kit_spec/gsd_tools.py:117-133` | role |
| `.../scripts/gp_e2e.py` | utility | transform | `package_scripts.py` + `makefile_parse.py` readers | partial |
| `.../scripts/gp_matrix.py` | config table + pure selector | transform | `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py:49` (`RULES` tuple of dicts) | exact |
| `.../scripts/gp_render.py`, `gp_sections.py` | renderer | transform | `string.Template` (stdlib); budgets pinned like `tests/test_quota_policy_text.py` | partial |
| `.../assets/prompt-template.md` | template asset | n/a | `.planning/goals/2026-10-14-v1.3-phases-16-27.md` (third version; the reference shape) | exact |
| `tests/goal_prompt_fixtures.py` | test support | n/a | `tests/session_wake_fakes.py` | role |
| `tests/test_ai_kit_spec_goal_prompt_*.py` | tests | n/a | `tests/test_ai_kit_gsd_spec_discuss.py:1-40` (`SCRIPTS`, `sys.path.insert`) | exact |
| `tests/test_ai_kit_spec_goal_prompt_e2e.py` | e2e test | subprocess | `tests/test_ai_kit_gsd_spec_discuss_e2e.py`; fake node pattern in `tests/test_ai_kit_project_rules_all_e2e.py` | role |
| `tests/fixtures/goal_prompt/golden/*.md` | golden | n/a | `tests/test_curated_config_golden.py:42-66,220` (`UPDATE_GOLDEN=1` regen, `check_golden`) | exact |
| `tools/run_unittest_parallel.py` (mod, `E2E_MODULES`) | config | n/a | the commented entries at lines 24-43 | exact |
| `Makefile`, `.pre-commit-config.yaml` (generated listings) | generated | n/a | run `python3 tools/gen_test_groups.py`; never hand-edit | exact |
| `pyproject.toml` (pyright `extraPaths`) | config | n/a | `"skills/ai-kit-gsd-spec-discuss/scripts"` at the end of the list | exact |
| `README.md` (one skill row) | docs | n/a | the `ai-kit-gsd-spec-discuss` row (README.md:48) | exact |
| `.planning/phases/27-.../27-SKILL-JUDGE.md` + `skill-judge/` | evidence | n/a | `.planning/phases/26-.../26-SKILL-JUDGE.md` and its `check_verdicts.py` (simplified: one skill, 3 rounds) | role |
| `.planning/phases/27-.../27-OWNER-CAPTURES.md` | evidence | n/a | `26-OWNER-CAPTURES.md` | exact |

No analog (new shape): the dated `goals/` placement helper and the prompt-budget ratio test; both are small pure functions.

## Shared Patterns

### CLI shape (goal_prompt.py)
**Analog:** `decide.py:623-645`. A `main(argv=None, seams=None) -> int`; non-interactive; JSON on stdout; `{"error": ...}` JSON on stderr and exit 2 for bad input; seams (the subprocess runner, the clock, the environment) injected through a `NamedTuple` so pylint `max-args=5` holds.

### Sibling skills only through their CLIs (D-03)
Never `import ai_kit_*` from another skill and never `skills/_shared`. Call with a list argv through an injected `run_fn(argv, timeout) -> (rc, stdout)`:
- `python3 <skills dir>/ai-kit-session-wake/ai-kit-session-wake.py matrix --json`
- `python3 <skills dir>/ai-kit-spec-review/ai-kit-spec.py detect-current-runtime` and `detect-runtimes`
- `python3 <skills dir>/ai-kit-gsd-spec-discuss/scripts/decide.py detect`
- the project-local `node .claude/gsd-core/bin/gsd-tools.cjs query ...` command resolved by the agent (passed in, see Contracts)
- `node .planning/scripts/cross-ai.mjs --print-argv` (exit code and CLI names only)
Default `<skills dir>` = the parent of this skill's directory (works for repo checkouts and copy installs); `--wake-cli`, `--spec-cli`, `--decide-cli` override it. A missing CLI is a labelled "unverified" result, never an exception.

### Copy plus parity (D-03)
Each copied helper has one test that loads the ORIGINAL by file path (`importlib.util.spec_from_file_location`) and compares outputs over a table of inputs, so a drift in the original fails a test.

### Strict template (D-14)
```python
class PromptTemplate(string.Template):
    delimiter = "§§"      # rare double-section-sign; $?, ${PIPESTATUS[0]} and JSON braces stay literal
    idpattern = r"[A-Z][A-Z0-9_]*"
text = PromptTemplate(source).substitute(values)   # a missing key raises KeyError: generation fails
```
A test asserts `"§§"` appears in no rendered output.

### Seams as a NamedTuple (pylint max-args=5)
```python
class Seams(NamedTuple):
    run: Callable[[list[str], int], tuple[int, str]]
    which: Callable[[str], str | None]
    environ: Mapping[str, str]
```

### Golden files
`UPDATE_GOLDEN=1 python3 -m unittest tests.test_ai_kit_spec_goal_prompt_golden` regenerates; without it a diff fails with the regen command in the message (precedent: `tests/test_curated_config_golden.py:220-223`).

### Rule parity (D-22)
`skills/_shared/ai_kit_rules_common/classification.py:309` `check_rules(...)` is what the agents checker calls; the rule dicts are `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py` R18 (flat `signals` `("session wake", "self-resume", "resume by session id")`) and R19 (grouped `signals`: `("cross-ai.mjs",)`, `("never switches", "never switch")`, `("aikit-xai",)`, `("ai-kit-cross-ai",)`). The parity TEST (not the runtime) may import those modules by file path; the shipped scripts never do. The generated QUOTA text must contain at least one R18 signal phrase and one phrase from every R19 group, in two separate labelled directives.

## Contracts (every plan implements these exactly; names are the greppable acceptance targets)

### `goal_prompt.py detect` -> stdout JSON (`schema_version` 1)
```
goal_prompt.py detect [--repo DIR] [--target-host HOST] [--tools A,B,..] [--roadmap FILE]
                      [--identity FILE] [--phase-op DIR] [--work-set KIND:VALUE] [--gsd-cmd "node <path>"]
                      [--wake-cli P] [--spec-cli P] [--decide-cli P]
{
  "schema_version": 1,
  "host":   {"current": "claude", "target": "claude", "current_version": "2.1.314"},
  "primitives": [ {"host","primitive","kind","surface","availability","usage_source",
                   "survives_stall","survives_process_death","survives_reboot","rank","note"} ],
  "unrecognized_tools": [],
  "matrix_source": "session-wake" | "missing",
  "scope":  {"kind": "opengsd|gsd-unproven|superpowers|both|none", "identity": "opengsd|unverified",
             "ask": null | "which work set", "phases": [Phase], "plans": [Plan], "order": [..]},
  "e2e":    {"commands": [{"command","source","kind","confidence"}], "none": false},
  "readiness": {"runner_ok": true, "cli_listed": true, "reviewers_ok": true, "label": "..."},
  "jev":    {"usable": false, "reason": "..."},
  "derived": {"must_outlive": true, "provable": true},
  "strategies": [ {"id","rank","recommended","reason","primitive"} ]
}
```
`--roadmap` is a file holding `gsd-tools query roadmap.analyze` output and `--phase-op` a directory of `<N>.json` files holding `query init.phase-op <N>` output (the agent captures them, as with `phase_range.py --roadmap`). No absolute path ever appears in the output (`phase_dir` and `state_path` are relativized or dropped). `availability` is one of `available | not seen | unverified | absent`; `usage_source` one of `official docs | live | third-party | binary strings | unverified`.

### `goal_prompt.py render` -> writes the file, stdout JSON
```
goal_prompt.py render --repo DIR --detect FILE --answers FILE [--out-dir DIR]
answers.json: {"work_set": {"kind": "phases", "numbers": ["16","17"]}
                          | {"kind": "plans", "files": ["docs/superpowers/plans/a.md"]},
               "target_host": "claude", "native_execution": false, "mockups": [],
               "strategy": null | "goal" | "loop" | "autonomous",   // the user's explicit request only
               "objective": "one plain sentence", "output_dir": null | "tmp/goals"}
stdout: {"path": ".planning/goals/2026-10-31-phases-16-27.md", "strategies": [{"id","recommended"}],
         "conditions": [{"strategy","chars"}], "sections": ["OBJECTIVE", ...], "paste_chars": 1480, "rails_lines": 52}
```
Exit 0 ok; 2 bad input or a guard failure (message names the field, never echoes a secret).

### Additions fixed during planning (2026-10-31)
- `detect` also prints `"dropped": [{"id","reason"}]` (a user-requested strategy the host cannot run) and `"needs": [...]` (captures still missing); `render` stdout also prints `"warnings": [...]` (cross-AI readiness problems; never written into the file).
- Rails placement: inline in the block iff the ranked strategy list is exactly `autonomous`; otherwise one shared `## Rails` section follows the `COPY TO HERE` marker and each block names the file by its own repo-relative path.
- Template delimiter is `\u00a7\u00a7`; if `string.Template` rejects a two-character delimiter on this Python the single `\u00a7` is used (noted in the 27-06 SUMMARY).

- `detect` also prints `"candidate_skills": [str]` (sibling skill names among `ai-kit-cross-ai`, `ai-kit-session-wake`, `ai-kit-gsd-spec-discuss`, `ai-kit-spec-execute-superpowers` that exist next to this skill, sorted; `[]` when none), `"wake": {"primitive": str|null, "label": ""|"unverified"}` (`gp_matrix.wake_primitive`: the loop-capable row with the highest survival rank) and `"runner": {"command": str, "label": str}` (the `workflow.cross_ai_command` text and the readiness label). `render` reads these three.
- `free:<text>` and `plans:<files>` work sets need no GSD capture; only a `phases:` work set on a project with `.planning/` does.
- The block fence is a line of exactly four backticks; no other line may contain that token (`check_text` enforces it) so a block can be extracted by its fences.
- An `autonomous` block always carries the rails inline; every other block names the shared `## Rails` section, emitted only when a non-autonomous block exists.

### File format
Wrapper (at most three sentences), then `▼▼▼ COPY FROM HERE ▼▼▼`, one fenced block per ranked strategy (recommended first and marked), `▲▲▲ COPY TO HERE ▲▲▲`. OpenGSD: one block; line 1 `/gsd-autonomous --from N --to M --converge` (or `--only N`); the labeled sections OBJECTIVE, ROLE, RULES FOR EVERY PLAN, ORDER, QUOTA, DECISIONS, SAFETY, DONE WHEN, CLEANUP, STOP IF, REPORT. Non-OpenGSD blocks use the same sections minus the autonomous first line; a `/goal` block is `/goal <condition>` where the condition (at most 4,000 code points) names the rails file (`§Rails` section of the same file, by repo-relative path) and the evidence to print.

### Budgets and guard strings (tests pin these; numbers are Claude's-discretion defaults, edit only with the test)
- OpenGSD inline block: at most 60 rule lines (non-blank lines after line 1, excluding the eleven section headings), each at most 200 characters; a `/goal` condition at most 1,800 characters in practice, hard cap 4,000 code points (4,000 passes, 4,001 fails generation).
- wrapper: at most three sentences and at most 15 percent of the file's characters.
- forbidden anywhere in a generated file: `--no-verify`, `skip` followed by `test tier`, the home directory string, the sentinel secret, any `sk-`/`ghp_` key shape, a leading-slash absolute path in any path field, a jev mention without the word "advisory" in the same line, jev inside DONE WHEN or STOP IF.
- OpenGSD block: no `--` followed by a letter after line 1.
- required in DONE WHEN: every detected e2e command by name, "exit code", "count", "process group", "ps"; never a unit-test-only done.

## Reuse inventory (what is NOT rebuilt)
- Survival ranking: the `rank` field of `matrix --json` (sorted descending = most survivable). Phase 27 never recomputes survival.
- OpenGSD identity: `gsd-tools query runtime-identity` -> `packageName == "@opengsd/gsd-core"` exactly (26 D-18/D-19).
- jev usability: `decide.py detect` `backends.*.usable`. No `ladder` call is ever made by this phase's tests or code paths except in the rendered prompt text.
- Quota directive wording: `skills/ai-kit-cross-ai/references/subprocess-quota-policy.md` (mechanism B) and `skills/ai-kit-session-wake/SKILL.md` (mechanism A); the template references them by skill name and never restates the ladder.
