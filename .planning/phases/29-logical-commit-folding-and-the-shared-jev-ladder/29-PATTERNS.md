# Phase 29: Logical-commit folding and the shared jev ladder - Pattern Map

**Mapped:** 2026-11-04
**Files analyzed:** 22 (new or modified)
**Analogs found:** 17 / 22

Binding inputs: `29-CONTEXT.md` (D-01..D-16), `29-RESEARCH.md`, `tmp/plan-29/rulings.md` (rulings 1-5 override the research where they differ).
Ruling 2 changes the R9 scope: the cross-skill structural rule covers every cross-skill path, with a frozen allowlist for the existing non-jev references.

Tracking note: every analog path below was seen in a tracked-file listing or a `git ls-files` check this session, except the three marked "(verify tracked)".

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `skills/ai-kit-commit-fold/scripts/fold.py` (new) | script / CLI | batch, file-I/O (git) | `skills/ai-kit-gsd-spec-discuss/scripts/phase_range.py`, `skills/jev-fast-decision/scripts/jev_review.py` (argparse + subprocess) | role-match |
| `skills/ai-kit-commit-fold/SKILL.md` (new) | skill doc | - | `skills/ai-kit-spec-goal-prompt/SKILL.md` (sections, NEVER, evals) | role-match |
| `skills/ai-kit-commit-fold/references/folding-policy.md` (new) | reference doc | - | `skills/jev-fast-decision/reference.md` | role-match |
| `skills/ai-kit-commit-fold/gsd-capability/capability.json` (new) | config (manifest) | - | none in repo (RESEARCH spike manifest) | no-analog |
| `skills/ai-kit-commit-fold/gsd-capability/fold-cmd.cjs` (new) | utility (node, ~20 lines) | request-response (argv) | none in repo (RESEARCH spike module) | no-analog |
| `skills/ai-kit-commit-fold/evals/evals.json`, `trigger-queries.json`, `files/` (new) | eval data | - | `skills/ai-kit-spec-goal-prompt/evals/` | exact |
| `tests/test_ai_kit_commit_fold.py` (new) | test (unit, temp git repos) | batch | `tests/test_ai_kit_project_rules_agents.py` (`_git` helper, ~1012-1020); `tests/test_ai_kit_gsd_spec_discuss.py` (~871) | role-match |
| `tests/test_ai_kit_commit_fold_policy.py` (new) | test (doc-contract) | - | `tests/test_ai_kit_spec_goal_prompt_evals.py` (reads SKILL/refs by path) | role-match |
| `tests/test_ai_kit_commit_fold_evals.py` (new) | test (structure) | - | `tests/test_ai_kit_spec_goal_prompt_evals.py` | exact |
| `tests/test_ai_kit_commit_fold_e2e.py` (new) | test (e2e, node + gsd-tools) | request-response | `tests/test_ai_kit_spec_e2e.py`, `tests/test_ai_kit_project_rules_all_e2e.py` (~154, `git init`) | role-match |
| `tests/test_ai_kit_caller_text.py` (new, R10) | test (text, black box) | - | `tests/test_ai_kit_spec_goal_prompt_golden.py` (text builders) + `tests/test_arch.py` non-vacuity style | role-match |
| `skills/jev-fast-decision/scripts/jev_ladder.py` (new module, moved code) | service / client | request-response (child process) | `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` (source of the move) | exact (move) |
| `skills/jev-fast-decision/scripts/jev_review.py` (modified: `ladder`, `detect`) | controller (CLI) | request-response | itself, `build_parser` / `main` (~2010-2030) | exact |
| `skills/jev-fast-decision/SKILL.md` (modified, judge bar) | skill doc | - | itself; `skills/ai-kit-spec-goal-prompt/SKILL.md` for NEVER/evals shape | exact |
| `skills/jev-fast-decision/reference.md` (modified: lookup order, consent flow D-15) | reference doc | - | itself | exact |
| `skills/jev-fast-decision/evals/evals.json`, `trigger-queries.json` (new) | eval data | - | `skills/ai-kit-spec-goal-prompt/evals/` | exact |
| `tests/test_jev_fast_decision.py` (modified, receives moved tests) | test | request-response | `tests/test_ai_kit_gsd_spec_discuss.py` `_TmpHome` (155-166), `TestLadderCli` | exact (move) |
| `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` (DELETED) | - | - | - | - |
| `skills/ai-kit-gsd-spec-discuss/SKILL.md`, `references/decision-table.md`, `analyzer-brief.md`, `log-formats.md`, `worked-examples.md` (modified) | skill doc | - | itself | exact |
| `tests/test_ai_kit_gsd_spec_discuss.py` (modified: remove ladder tests, update text asserts) | test | - | itself | exact |
| `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py` (modified: `DECIDE_CLI` -> jev, `jev_status`) | utility (host seams) | request-response | itself (`sibling_cli`, 466-490) | exact |
| `skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py`, `goal_prompt.py`, `SKILL.md`, `README.md` (modified) | script / doc | - | itself | exact |
| `tests/fixtures/goal_prompt/golden/opengsd-goal-pointer.md`, `opengsd-recommended.md` (regenerated) | golden | - | `tests/test_ai_kit_spec_goal_prompt_golden.py` | exact |
| `tools/hooks/precompact_core.py` (modified: `find_client`) | utility (hook) | request-response | itself (`find_client`, 77-84) | exact |
| `tools/hooks/claude_decision_probe.py` (modified: line ~59) | hook | request-response | itself | exact |
| `skills/ai-kit-spec-execute-superpowers/SKILL.md` (modified: Step 5 fold, Step 1 check) | skill doc (judge bar) | - | itself (Step 4 at 278, Close at 285) | exact |
| `tests/test_arch.py` (modified: `check_no_cross_skill_jev_path`, `check_no_reset_hard`, lookup drift, allowlist, non-vacuity) | test (AST) | - | `check_no_planning_reader` (948) + `test_planning_reader_flags_each_join_form` (2175) | exact |
| `tools/run_unittest_parallel.py` (modified: `E2E_MODULES`, `E2E_RECORDED_SECS` for the e2e module) | config (runner) | - | itself (lines 104, 144) | exact |
| `tools/setup.py` (modified only if fold skill mirrors to pi: `PI_SKILLS` line 48) | config | - | itself | exact |
| `README.md` (skill table rows 49, 52, new fold row; pi mirror text ~536) | doc | - | itself | exact |
| `AGENTS.md` (Workflow folding sentence, ~line 293) | doc | - | itself | exact |
| `.gitignore` / `pyproject.toml` (tool roots lines 111, 137) | config | - | itself | exact |

## Pattern Assignments

### `skills/ai-kit-commit-fold/scripts/fold.py` (script, batch / git plumbing)

**Analog:** `skills/ai-kit-gsd-spec-discuss/scripts/phase_range.py` (stdlib argparse CLI) and `skills/jev-fast-decision/scripts/jev_review.py` (argparse + subprocess + `main(argv)`).
**No git-plumbing analog exists in tracked code.** The engine follows RESEARCH "Fold engine mechanics" (prototype `tmp/plan-29/fold_proto.py`, gitignored, do not cite it as a deliverable path). Build it from that sequence.

**Argparse + main shape** (`jev_review.py` 2010-2030):
```python
def build_parser():
    parser = argparse.ArgumentParser(
        prog="jev_review.py", description=(__doc__ or "").split("\n", 1)[0])
    parser.add_argument("--probe", action="store_true", ...)
    sub = parser.add_subparsers(dest="command")
    consent = sub.add_parser("consent", help="manage the per-user remote-consent record")
    consent.add_argument("action", choices=("grant", "revoke", "show"))
    return parser

def main(argv=None):
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
```
Apply: subcommands `fold <checkpoint.json>`, `status <phase>` (ruling 3, read-only, never a gate), `adapt-gsd`, `adapt-superpowers`. Keep the subparsers non-required, as jev does.

**Git plumbing rules to copy (from RESEARCH, executed in the prototype):**
- Guards before any write: `git status --porcelain` empty; `rev-parse <ref>` equals the tested tip; `merge-base --is-ancestor <c> <main>`: exit 0 refuses, exit 1 is normal (not an error), other exit is an error.
- Temp index: `GIT_INDEX_FILE=<tmp> git read-tree <base>`, `update-index --add --cacheinfo`, `write-tree`, `commit-tree -F -` with **UTF-8 bytes** on stdin (str input raises TypeError). Delete the temp index in `finally`.
- Proof: `rev-parse <folded>^{tree}` == `rev-parse <tip>^{tree}`, else refuse with no tag and no ref move.
- Tag then move: `git tag ai-kit-fold/<unit>/<old-short-sha> <tip>`, then `git update-ref <ref> <new> <tip>`; delete the tag if `update-ref` fails.
- Never `reset --hard` (SPEC R4, enforced by the arch rule in this phase).
- Run git with an argv list, never `shell=True`. NUL-split `git diff --name-status -z --no-renames`.

### `skills/ai-kit-commit-fold/SKILL.md` and `references/folding-policy.md` (docs)

**Analog:** `skills/ai-kit-spec-goal-prompt/SKILL.md` (sections: `## 0. Set up once per run`, `## NEVER` at line 144, `## Evidence and limits`, `## When something is missing`) and `skills/jev-fast-decision/reference.md` for the progressive-disclosure split.

Keep SKILL.md short and point to `references/folding-policy.md` for the one policy text (D-11). Put the two-step capability install (ruling 1) in SKILL.md: `capability install <bundle> --scope project`, then the same with `--yes` after the owner agrees. Put the `status` backstop instruction (ruling 3) in SKILL.md.

### `skills/ai-kit-commit-fold/gsd-capability/*` (manifest and command module, no repo analog)

RESEARCH "Spike" section holds the working shapes. Copy them, do not improvise:
- `capability.json`: required keys `id` (kebab, equal to folder name), `role:"feature"`, `version`, `title`, `description`, `tier`, `requires`, `skills`, `agents`, `config`, `steps`, `contributions`, `gates`; `engines.gsd`, `runtimeCompat`, and `commands` with `"module":"fold-cmd.cjs"` at the bundle root (no path in the module name).
- Step: `"point":"execute:wave:post"`, `"ref":{"command":"fold-cmd run"}`, `"onError":"skip"`.
- `fold-cmd.cjs`: exports `route({args, cwd})` synchronously. Runs the fold script with `execFileSync("python3", [script, ...fixedArgs], {cwd})`, where the script path comes from the D-13 lookup (a JS copy of it). Keep it under ~20 lines.

### `skills/jev-fast-decision/scripts/jev_ladder.py` (service, moved from decide.py)

**Analog (source of the move):** `skills/ai-kit-gsd-spec-discuss/scripts/decide.py`. Move as-is (D-12, CONTEXT reusable assets):

**Lookup (copy the order, decide.py 89-108):**
```python
def client_candidates(env: Mapping[str, str], override: str | None) -> list[str]:
    home = env.get("HOME", "~")
    xdg = env.get("XDG_CONFIG_HOME", "").strip() or os.path.join(home, ".config")
    own_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    roots = [
        own_root,
        os.path.join(env.get("CLAUDE_CONFIG_DIR", "").strip() or os.path.join(home, ".claude"), "skills"),
        os.path.join(home, ".agents", "skills"),
        os.path.join(xdg, "opencode", "skills"),
        os.path.join(env.get("CURSOR_CONFIG_DIR", "").strip() or os.path.join(home, ".cursor"), "skills"),
        os.path.join(env.get("PI_CODING_AGENT_DIR", "").strip() or os.path.join(home, ".pi", "agent"), "skills"),
    ]
    explicit = override or env.get("AI_KIT_JEV_CLIENT", "").strip()
    found = [os.path.expanduser(explicit)] if explicit else []
    return found + [os.path.expanduser(os.path.join(root, CLIENT_REL)) for root in roots]
```
Note: `own_root` uses `abspath`, never `realpath` (the skill is symlinked). Keep that comment.

**Other pieces that move unchanged:** `find_client` (111-117), `client_ok`, `item_error` (208), `partition` (238), `child_env` (400), `call_client` (428), `typed_answer` (461), `fill_columns` (503), `run_ladder` (535), `detect` (576), `consent` (593). Constants: `CALL_TIMEOUT_SECONDS = 30`, `MAX_FIELD_CHARS = 1500`, `_SECRET_RE`, closed vocabularies. The client still runs as a child process with the scrubbed env (RESEARCH design note). Keep `CLIENT_PROTOCOL = 2` in jev_review.py, because the moved check reads it.

### `skills/jev-fast-decision/scripts/jev_review.py` (controller CLI, add `ladder` and `detect`)

**Analog:** itself, `build_parser` at 2010-2022. Add `ladder [--second-opinion]` and `detect` as sibling subparsers. Keep the subparsers non-required so the bare stdin call still works. Existing `--probe`, `--skip-local` and `consent` stay.

### `skills/jev-fast-decision/SKILL.md` and `reference.md` (judge-bar docs)

**Analog:** itself. Current "Pick the backend" section (lines 10-12) says to run `--probe` and read `backends/<selected>.md`, but **does not document the lookup order** (D-13 needs it). Add a lookup-order list, the `ladder`/`detect` commands, the D-15 consent flow ("an agent that follows this SKILL meets the consent ask here"), and the "older skill without the entry point" update message. Put the lookup table and consent steps in `reference.md`, not SKILL.md. Current SKILL.md is 62 lines; keep it near that.

### `tests/test_jev_fast_decision.py` (test, moved ladder tests)

**Analog:** `tests/test_ai_kit_gsd_spec_discuss.py` `_TmpHome` (155-166) and the moved classes `TestItemError`, `TestPartitionIds`, `TestTypedAnswer`, `TestFindClient`, `TestLadderCli` (~350-770):
```python
class _TmpHome(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        home = self.tmp / "home"
        home.mkdir()
        self.env = {"HOME": str(home),
                    "XDG_CONFIG_HOME": str(home / ".config"),
                    "XDG_STATE_HOME": str(home / ".local" / "state"),
                    "XDG_DATA_HOME": str(home / ".local" / "share"),
                    "PATH": os.environ.get("PATH", ""),
                    "JEV_LAYA_URL": closed_port_url()}
```
Re-point `SCRIPTS / "decide.py"` to the jev entry. Keep the `closed_port_url()` isolation. Stay in spec-discuss: `TestPhaseRange`, `TestEdgeFloor`, `TestSkillContract` (update the text asserts on lines ~1077, 1102, 1126, 1132, 1217, 1243, 1252 that pin backend/consent text D-14/D-15 removes; read each first).

### `skills/ai-kit-gsd-spec-discuss/` (decide.py deletion and SKILL.md / references)

**Delete** `scripts/decide.py`. Replace the SKILL.md references (lines 28-29, 46, 68-69, 183-184, 197, 267, 275) and `references/decision-table.md` (18, 29) with one black-box instruction: ask `jev-fast-decision` and follow its SKILL.md. Also reduce `analyzer-brief.md`, `log-formats.md`, `worked-examples.md` (backend and Laya mentions) to the same. Keep `phase_range.py` and `edge_floor.py`. The directory stays, so `pyproject.toml` tool roots (lines 111, 137) still resolve.

### `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py` (host seams, jev status)

**Analog:** itself. Change `DECIDE_CLI` (line 30) to the jev entry; `jev_status` (466-490) uses `sibling_cli(DECIDE_CLI, decide_cli)` and runs `... detect`. Replace it with the lookup copy (D-13) and the update-message path. Keep the WAKE_CLI/SPEC_CLI lines (28-29) as they are, and put them in the allowlist (ruling 2).

**Goldens:** regenerate with the test's own command, `UPDATE_GOLDEN=1 python3 -m unittest tests.test_ai_kit_spec_goal_prompt_golden` (`tests/test_ai_kit_spec_goal_prompt_golden.py` lines 7, 435-459). Affected: `opengsd-goal-pointer.md` (56, 137) and `opengsd-recommended.md` (50), which contain the `decide.py` text. Review the diff by hand before committing.

### `tools/hooks/precompact_core.py` and `tools/hooks/claude_decision_probe.py` (hook lookup)

**Analog:** itself. `find_client` (77-84) today checks `CLIENT_ENV` and then a checkout-relative `skills/jev-fast-decision/scripts/jev_review.py`. Replace the checkout path with the D-13 installed-skill lookup (the hook may be installed where `skills/` is not beside it). Keep the `CLIENT_ENV` override. `claude_decision_probe.py:59` calls `core.find_client` and needs no change beyond that. Tests: `tests/fixtures/precompact/stub_client.py`, `test_precompact_core.py`, `test_claude_precompact.py`, `test_decision_probe.py`.

### `skills/ai-kit-spec-execute-superpowers/SKILL.md` (adapter, judge bar)

**Analog:** itself. Existing headings: `## NEVER` (18), `## Step 0` (50), `## Step 1` (100), `## Task paths` (107), `## Arm the session wake` (130), `## Step 2` (137), `## Step 3` (209), `## Step 4` (278), `## Close the session wake` (285).

Place the fold as a new **Step 5** between Step 4 (final review passes) and `## Close the session wake` (285). Add to Step 1 the pre-execution check: if the plan lacks a final "Fold commits" task, append it to the in-memory task list (do not rewrite the plan file). The step text is "run `python3 <fold.py found by lookup> ... adapt-superpowers`". Keep additions to a few lines and push detail into `references/` (progressive disclosure, D5 regression risk). No merge, push or PR through the finishing step (D-03 refinement, 29.1).

**Judge baseline first:** D-16 requires a fresh new-rubric baseline of this SKILL.md before editing (RESEARCH, JDG-04 section).

### `tests/test_arch.py` (AST structural rules)

**Analog:** `check_no_planning_reader(tree)` (948) and its non-vacuity test `test_planning_reader_flags_each_join_form` (2175). Pattern:
```python
def test_planning_reader_flags_each_join_form(self):
    setup = ("import os\nfrom pathlib import Path\n"
             "REPO_ROOT = Path(__file__).resolve().parent.parent\n")
    offenders = ('open(REPO_ROOT / ".planning" / "STATE.md")\n', ...)
    for body in offenders:
        with self.subTest(body=body):
            self.assertNotEqual([], check_no_planning_reader(ast.parse(setup + body)))
```
Non-vacuity class: `TestArchNonVacuity` (1818). Add, each with a non-vacuity case per form:
- `check_no_cross_skill_jev_path(relpath, tree)`: `import`/`from` of another skill; `sys.path` insert to a sibling skill; a string constant naming `jev-fast-decision/scripts` or `jev_review.py` outside jev's folder and the lookup helper; any `decide.py` name.
- Frozen allowlist (ruling 2): gp_host.py `WAKE_CLI`/`SPEC_CLI` (28-29), `ai-kit-session-wake.py:19` `sys.path` insert, `gp_common.py:6` docstring. Each entry gets a one-line reason. Non-vacuity case: "a new allowlist entry fails". Mirror the `test_planning_reader_exception_list_rejects_an_entry` pattern (2262). Add a backlog entry in `.planning/ROADMAP.md` §Backlog for each removal.
- `check_no_reset_hard(...)` over the fold script, SKILL.md and policy text (SPEC R4).
- Lookup drift test: parse every copy's ordered roots with `ast` (Python copies) and by regex (the JS copy), compare to the order documented in jev `reference.md`/SKILL.md.

Structural rules take `(relpath, tree)` and live at module level. Add to the live `TestArchitecture` class and add a non-vacuity case per form. Do not add a new arch module (`tests.test_arch` is the only `arch` module).

### Fold tests: `tests/test_ai_kit_commit_fold.py` (unit, temp git repos)

**Analog:** `tests/test_ai_kit_project_rules_agents.py` `_git` helper (1012-1020):
```python
["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args]
```
and `tests/test_ai_kit_gsd_spec_discuss.py:871` (`git("init")` in a temp dir). Build fixtures once per class (`setUpClass`). Set `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`, explicit `GIT_AUTHOR_*`/`GIT_COMMITTER_*`, and `AI_KIT_REFUSE_REAL_HOME=1`. No sleeps; each test under 0.3 s. Non-git-only logic goes in plain unit tests (report <= 5 lines, no colour codes, jev absent / fake client same result).

### `tests/test_ai_kit_commit_fold_policy.py` and `_evals.py` (doc-contract, structure)

**Analog:** `tests/test_ai_kit_spec_goal_prompt_evals.py` (lines 1-30 constants: `REPO`, `SKILL`, `EVALS`; line 63 required-file list; line 142 `EVALS_FILE = EVALS / "evals.json"`). Read the policy under `skills/`, never `.planning/` (`test_no_test_reads_planning`; `PLANNING_READER_EXCEPTIONS` stays empty).

### `tests/test_ai_kit_commit_fold_e2e.py` (e2e, node)

**Analog:** `tests/test_ai_kit_spec_e2e.py` and `tests/test_ai_kit_project_rules_all_e2e.py` (~154, `subprocess.run(["git", "init", "-q", repo], check=True, capture_output=True)`). The fixture copies **both** `.claude/gsd-core` and `.claude/scripts/` (spike finding: without `scripts/` every command crashes). Install with `capability install <bundle> --scope project` and `--yes`. Register the module in `tools/run_unittest_parallel.py` `E2E_MODULES` (line 104) **and** `E2E_RECORDED_SECS` (line 144); `tests/test_gate_scope.py` enforces the match. Unit modules join group `unit` automatically.

### `tests/test_ai_kit_caller_text.py` (R10 text, black box)

**Analog:** the text builders in `tests/test_ai_kit_spec_goal_prompt_golden.py` and `skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py` (call builders, no host CLI). Reads only the five callers' SKILL.md, `references/*.md` and generated prompt text. Case-insensitive regex for `laya|typesafe|opencode zen|zen\b|consent|probe status`. Exempt only `skills/jev-fast-decision/`. Non-vacuity: a synthetic text containing each name fails. Do not scan the whole tree.

### Evals layout (new-shape, all new/changed SKILL.md)

**Analog:** `skills/ai-kit-spec-goal-prompt/evals/`: `evals.json` (10 cases), `trigger-queries.json` (20), `files/`. Apply to `ai-kit-commit-fold` (new), and to `jev-fast-decision` (new; its existing `evals/cases.jsonl` is backend calibration, not skill evals, keep it).

### Registration points

- `tools/setup.py:48` `PI_SKILLS = frozenset({"ai-kit-cross-ai", "jev-fast-decision", "ai-kit-session-wake"})`. Decide whether the fold skill mirrors to pi (pi is a primary host). If yes, add it and update `README.md` ~536. The installer scans `skills/` generically (RESEARCH A5, confirm with `bash tests/test_install.sh`).
- `README.md` skill table: rows 49 (spec-discuss, remove the `decide.py` mention) and 52 (jev, add `ladder`/`detect`); add a fold row.
- `AGENTS.md` Workflow folding sentence (~line 293): point to `skills/ai-kit-commit-fold/references/folding-policy.md`.
- `pyproject.toml` lines 111, 137: add the fold `scripts` dir and the jev scripts dir if not covered.

## Shared Patterns

### Installed-skill lookup (D-13), applies to every code caller
**Source:** `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` 89-108 (`client_candidates`).
**Apply to:** fold `fold.py`, `gp_host.py`, `precompact_core.py`, `claude_decision_probe.py`, and the `fold-cmd.cjs` JS copy. One drift test (arch rule above) compares every copy.

### Stdlib argparse CLI with non-required subcommands
**Source:** `skills/jev-fast-decision/scripts/jev_review.py` 2010-2030.
**Apply to:** `fold.py`, `jev_review.py` (`ladder`, `detect`).

### Temp git fixture helper
**Source:** `tests/test_ai_kit_project_rules_agents.py` 1012-1020; `tests/test_ai_kit_gsd_spec_discuss.py` 155-166 (`_TmpHome`).
**Apply to:** all fold tests and the e2e module. Pin `GIT_CONFIG_GLOBAL`/`GIT_CONFIG_SYSTEM` to `/dev/null`.

### Scrubbed child env and fail-closed ladder
**Source:** `decide.py` `child_env` (400-416), `call_client` (428). Moves unchanged.
**Apply to:** `jev_ladder.py` only. Callers never spawn jev themselves; they call the `jev_review.py` entry point.

### Advisory answers never gate
**Source:** `jev-fast-decision/SKILL.md` NEVER list (45-49).
**Apply to:** fold grouping (D-07), the `status` backstop (ruling 3), and every SKILL.md text in this phase.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `skills/ai-kit-commit-fold/gsd-capability/capability.json` | config | - | No capability bundle exists in the repo; use the RESEARCH spike manifest |
| `skills/ai-kit-commit-fold/gsd-capability/fold-cmd.cjs` | utility | request-response | No node command module in the repo; use the RESEARCH spike module (~20 lines) |
| Git plumbing fold engine (inside `fold.py`) | service | batch | No tracked code uses `GIT_INDEX_FILE` / `commit-tree` / `update-ref` CAS; build from RESEARCH "Fold engine mechanics" |
| GSD adapter parser (PLAN.md `<files>` tag) | utility | transform | Format not verified; pin against a real PLAN.md first (RESEARCH A4, Wave 0) |
| superpowers adapter parser (`### Task N`, `Files:`) | utility | transform | Format not verified; pin against `docs/superpowers/plans/*.md` first (RESEARCH A4) |

## Metadata

**Analog search scope:** `skills/` (jev, gsd-spec-discuss, goal-prompt, superpowers, evals dirs), `tests/` (arch, jev, spec-discuss, goal-prompt, project-rules, e2e), `tools/` (run_unittest_parallel, staged_mapper, setup, hooks).
**Files scanned:** about 40 (targeted greps and ranges; no whole large-file loads).
**Not checked this session (time-box):** `tests/test_gate_scope.py` internals beyond existence, `tools/staged_mapper.py` mapping rules beyond its index design (reach text per module, names covered by name match), the exact `tools/install.sh` skill scan, and the R9 allowlist's full scan results (the scan must be run when the test is written).
**Pattern extraction date:** 2026-11-04

## PATTERN MAPPING COMPLETE

**Phase:** 29 - Logical-commit folding and the shared jev ladder
**Files classified:** 22
**Analogs found:** 17 / 22

### Coverage
- Files with exact analog: 13
- Files with role-match analog: 4
- Files with no analog: 5 (capability bundle x2, fold git plumbing, two adapter parsers)

### Key Patterns Identified
- The ladder is a move: `decide.py` functions copy unchanged into `jev_ladder.py`; `jev_review.py` gains `ladder`/`detect` as non-required subparsers.
- Every code caller carries the same D-13 lookup copy, pinned by one ordered-roots drift test.
- Structural rules follow `check_no_planning_reader` plus a per-form non-vacuity test in `TestArchNonVacuity`; the R9 allowlist is frozen (ruling 2).
- Fixture repos use a `_git` helper with pinned identity and `GIT_CONFIG_*` set to `/dev/null`; no host CLI, no `.planning/` reads.
- Goal-prompt goldens regenerate with `UPDATE_GOLDEN=1`; review the diff by hand.

### File Created
`/var/home/bazzite/git/personal/ai-kit/.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can reference analog patterns in the plan files.
