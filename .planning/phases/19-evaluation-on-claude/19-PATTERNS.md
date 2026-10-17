# Phase 19: Evaluation on Claude - Pattern Map

**Mapped:** 2026-10-17
**Files analyzed:** 14
**Analogs found:** 13 / 14

All analog paths are git-tracked (checked with `git ls-files`), except
`tmp/judge/check_digests.py`, which is untracked scratch (see No Analog Found).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tests/gsd_curated_eval.py` | utility (dev-only CLI helper) | request-response / batch | `tests/test_curated_config_apply_e2e.py` (`_golden_bundle`, `_real_run`, `_seed_home`) + `tests/test_curated_config_apply.py` (`_scratch_env`, `scratch_inventory`, `_decide_all_choices`) | role-match |
| `tests/test_gsd_curated_eval.py` | test (hermetic unit) | transform | `tests/test_curated_config_apply.py` | role-match |
| `tests/test_ai_kit_gsd_curated_config_matrix.py` | test (real-node e2e) | batch | `tests/test_curated_config_apply_e2e.py` | exact |
| `tools/run_unittest_parallel.py` (`E2E_MODULES`) | config | n/a | same file, lines 53-61 | exact |
| generated listings (`Makefile`, `.pre-commit-config.yaml`) | config | transform | `tools/gen_test_groups.py` (run, do not hand-edit) | exact |
| `skills/ai-kit-gsd-curated-config/evals/01..04-*.md` | eval doc | n/a | `skills/ai-kit-spec-review/evals/01-*.md` | exact |
| `skills/ai-kit-gsd-curated-config/SKILL.md` + `references/` | skill doc | n/a | itself (v2 rewrite) + `TestSkillDocCommands` | exact |
| `tests/test_curated_config_apply.py` (SKILL.md pins, if SKILL.md edits need pins) | test | transform | `TestSkillDocCommands`, line 2320 | exact |
| `19-PRESSURE-TESTS.md` | evidence | n/a | `.planning/phases/18.1-one-runtime-model/18.1-SKILL-JUDGE.md` (table style) | partial |
| `19-SMOKE.md` | evidence | n/a | same, plus RESEARCH "Helper contract" `smoke` | partial |
| `19-SKILL-JUDGE.md` | evidence | n/a | `.planning/phases/18.1-one-runtime-model/18.1-SKILL-JUDGE.md` | exact |
| `pressure/`, `skill-judge/` transcripts | evidence | file-I/O | `.planning/phases/18.1-one-runtime-model/skill-judge/*.md` | exact |
| digest-check script (`tmp/judge/check_digests.py` pattern) | utility | transform | spec in `18.1-21-PLAN.md:138-146` | spec-only |
| `tests/test_gate_scope.py` | test (no edit; fails while listing is stale) | n/a | n/a | n/a |

## Pattern Assignments

### `tests/gsd_curated_eval.py` (utility, request-response / batch)

**Analog:** `tests/test_curated_config_apply_e2e.py` and `tests/test_curated_config_apply.py`.
Rule from RESEARCH "Don't Hand-Roll": import these helpers, do not rebuild them.

**Imports pattern** (`test_curated_config_apply_e2e.py:26-50`):
```python
from ai_kit_gsd_curated_config import apply as apply_mod
from ai_kit_spec import gsd_tools
from tests.test_curated_config_apply import (...)
from tests.test_curated_config_e2e import REPO_ROOT, _real_node_executable, _RealGsdTestCase
from tests.test_curated_config_golden import load_fixture
from tests.test_curated_config_inventory import seed_cache
from tests.test_curated_config_recommend import run_recommend
from tests.test_curated_config_skills import add_plugin, add_skill
```
Caveat: importing `_`-private test helpers from a non-test module is allowed here (tests/ has the lighter ruff bar), but `tests.*` imports require running as `python3 -m tests.gsd_curated_eval` or with the repo root on `sys.path`. RESEARCH's contract says `python3 tests/gsd_curated_eval.py`; insert `REPO_ROOT` into `sys.path` (derive it from `__file__`, never a literal).

**Scratch env** (`test_curated_config_apply.py:462-468`): explicit env, empty `PATH`:
```python
def _scratch_env(home, gsd_home, xdg):
    return {"HOME": home, "GSD_HOME": gsd_home, "XDG_CACHE_HOME": xdg, "PATH": ""}
```

**Explicit-env subprocess wrapper** (`test_curated_config_apply_e2e.py:88-93`):
```python
def _real_run(child_env):
    def run(cmd, **kw):
        call_env = kw.pop("env", None) or {}
        return subprocess.run(cmd, env={**child_env, **call_env}, **kw)
    return run
```

**Bundle builder** (`test_curated_config_apply_e2e.py:152-197`): `_golden_bundle(scratch, with_planning=..., host_name="claude")` builds `project`, `home`, `gsd_home`, `xdg`, seeds the catalog with `seed_cache(xdg, load_fixture("runtimes.json"), load_fixture("model-catalog.json"))`, sets `resolve_env = {**env, "RUNTIME_DIR": str(REPO_ROOT)}`, runs `scratch_inventory`, then `run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")` and `_decide_all_choices`. Returns a dict with `project, resolve_env, child_env, config_path, inv_path, plan_path`. The matrix helper parameterizes profile and rigor (the analog hardcodes adaptive/standard); P2 fixture is `with_planning=True`.

**Cache seeding** (`test_curated_config_inventory.py:64-72`): `seed_cache(xdg_cache_home, runtimes, catalog)` writes `<xdg>/ai-kit/spec/{runtimes,model-catalog}.json`. Scenario fixtures C/D confirm routers by adding `heuristic_confirmed: ["is_router"]` on the catalog entries (R-4).

**Node/version guard** (`test_curated_config_apply_e2e.py:141-149`):
```python
tools = REPO_ROOT / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs"
version = gsd_tools.gsd_core_version(str(tools))
if not version or not version.startswith("1.16."): ...
```
In the helper, replace `skipTest` with a non-zero exit and a printed message (a CLI has no TestCase).

**Hash helper** (`test_curated_config_apply_e2e.py:56-60`): `_sha256(path)` for the protected-set snapshot (RESEARCH Pattern 3: `{path: sha256}` plus sorted dir name lists, exit 1 on drift).

**Oracle** (RESEARCH Pattern 2, 19-RESEARCH.md:268-276): compute `promised` from the plan, never from the applied config. Keep `inheritance_promised=False` as a parameter.

**CLI shape:** `argparse` subcommands `snapshot | fixture | smoke | matrix | grade` per RESEARCH "Helper contract" (19-RESEARCH.md:285-286). Output must contain no absolute paths (placeholders). Refuse `apply` when `--project-dir` resolves to `REPO_ROOT` (D-03).

---

### `tests/test_gsd_curated_eval.py` (test, transform)

**Analog:** `tests/test_curated_config_apply.py` (pure-function unittest style, `unittest.TestCase`, `tempfile` scratch). One test per subcommand's pure parts (promised-tier function, snapshot diff, digest, grade parser). No real node; joins the `unit` group automatically via discovery.

---

### `tests/test_ai_kit_gsd_curated_config_matrix.py` (test, batch, real node)

**Analog:** `tests/test_curated_config_apply_e2e.py`.

**Class base** (line 221): `class TestRealApply(_RealGsdTestCase):` from `tests.test_curated_config_e2e`. Use `_gsd16_or_skip(self)` first in each test. Loop (profile, rigor) x (P1, P2) x {fix, control} in `subTest`. Assert key parity between `MODEL_PROFILES` and the phase map (D-10) before comparing. Do not assert `dynamic_routing` for Standard/MVP (R-14).

---

### `tools/run_unittest_parallel.py` (config)

**Analog/edit site** (`tools/run_unittest_parallel.py:53-61`): add `"tests.test_ai_kit_gsd_curated_config_matrix",` to the `E2E_MODULES` frozenset, after `"tests.test_curated_config_apply_e2e"`. Then run `python3 tools/gen_test_groups.py` (docstring: "the listings are a projection of that discovery"); it rewrites the blocks between `# BEGIN GENERATED test groups` / `# END GENERATED test groups` in `Makefile` and `.pre-commit-config.yaml`. `tests/test_gate_scope.py` fails while stale.

---

### `skills/ai-kit-gsd-curated-config/evals/01..04-*.md` (eval doc)

**Analog:** `skills/ai-kit-spec-review/evals/01-superpowers-plan-routes-writing-plans.md`. Fixed section layout:
```markdown
# Eval 01 — <title>
## Scenario
## Prompt          (fenced block with the user message)
## Expected behavior   (numbered steps)
## Pass criteria       (bullets, each checkable from a transcript)
```
Naming: `NN-kebab-case.md`. Pass criteria must be gradable by `gsd_curated_eval.py grade` (stable phrases from SKILL.md and plan fields, not model prose).

---

### `skills/ai-kit-gsd-curated-config/SKILL.md` and `references/` (skill doc)

**Analog:** the current file (v2 primary, judged 106-112/120). Pinned by tests in `tests/test_curated_config_apply.py:2320-2345`:
```python
class TestSkillDocCommands(unittest.TestCase):
    def test_examples_use_entrypoint_and_no_habitual_force(self):
        for line in _bash_fenced_lines(_skill_md_text()):
            self.assertIn(_ENTRYPOINT, line, line)
            self.assertNotIn("--force", line, line)
```
Every new `bash` fence in SKILL.md must run `"$ENTRYPOINT"`, parse with `cli._build_parser()`, avoid `--force`, and avoid "on this machine" phrases. Keep the step order (R-2): inventory, four questions, recommend, review pass, needs_choice via plan-set, apply --dry-run, apply, grouped follow-up approval. Any SKILL.md or reference edit invalidates all digest-bound rows (R-13); the project rule also requires the skill-judge loop (>= 96/120, no regression).

---

### `19-SKILL-JUDGE.md` (evidence) and judge transcripts

**Analog:** `.planning/phases/18.1-one-runtime-model/18.1-SKILL-JUDGE.md`.

Header carries the pass rule; per skill a `## <skill>` section with this table:
```markdown
| Judge | Digest judged | Score | Baseline | Critical/Important left | Verdict | Report |
|---|---|---|---|---|---|---|
| pi gpt-6.1-sol xhigh | f87405ed2efe9722 | 101/120 | 99/120 | 0/6 | superseded (b42a259271e049cc) | r1 |
```
Verdict cells: `PASS`, `superseded (<new digest>)`, `context`, `unavailable, capacity`. Reports live under `skill-judge/` named `<skill>-pi-<model>-xhigh[-postreview].md`. Judge procedure and prompt: `18.1-21-PLAN.md:138-160`. Pass rule: (`CRITICAL 0` and `IMPORTANT 0`) or `CURRENT >= 96`, and `CURRENT >= BASELINE`. Phase 19 adds a GREEN/pressure-test digest column the same way (R-13).

---

### Digest check script

**Spec** (`18.1-21-PLAN.md:138-146`; DIGEST_CMD):
```python
d = pathlib.Path("skills", skill)
fs = [d/"SKILL.md"] + sorted(p for p in (d/"references").rglob("*") if p.is_file())
h = hashlib.sha256()
for p in fs:
    h.update(p.relative_to(d).as_posix().encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
print(h.hexdigest()[:16])
```
Checker: find `## <skill>` section, skip rows whose Verdict starts with `superseded` or `context`, compare Digest cell, print `digests ok` / exit 1 on mismatch, require at least one live row. Run a negative self-check with digest `0000000000000000` (must exit 1). Keep it under `tmp/judge/` (gitignored scratch) unless the plan decides to track it; if tracked, put it in `tools/` or `tests/` and cover it with a hermetic test.

## Shared Patterns

### Hermetic, explicit env, no real config
**Source:** `tests/test_curated_config_apply.py:462-468`, `tests/test_curated_config_apply_e2e.py:88-93`
**Apply to:** helper, matrix test, smoke. No real `~/.claude`, `~/.cursor`, `~/.config/opencode`, `~/.codex`, `~/.pi`, `~/.gsd` writes; reads only where RESEARCH allows.

### Real-node guard
**Source:** `tests/test_curated_config_apply_e2e.py:141-149`
**Apply to:** matrix test, helper `matrix`/`smoke`.

### Stdlib-only dev helper, atomic writes
**Source:** `AGENTS.md` Non-Negotiable Rules; `tools/gen_test_groups.py` (stdlib-only, `REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent`)
**Apply to:** helper and any script. Derive paths from `__file__`, never literals.

### Config writes only via the product
**Source:** RESEARCH "Don't Hand-Roll" (`apply`, `config-set`, `config_backup`)
**Apply to:** fixtures and smoke; the harness never writes config JSON directly.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `tmp/judge/check_digests.py` | utility | transform | Only exists as a plan spec in 18.1-21-PLAN.md; the original was untracked scratch. |
| `grade` subcommand (transcript grading) | utility | transform | No existing transcript grader; build from the eval docs' Pass criteria. |
| `19-PRESSURE-TESTS.md` / `19-SMOKE.md` | evidence | n/a | No prior RED/GREEN pressure-test evidence file; reuse the 18.1 table style and carry the SKILL.md digest per row. |

## Metadata

**Analog search scope:** `tests/`, `tools/`, `skills/ai-kit-spec-review/evals`, `skills/ai-kit-gsd-curated-config`, `.planning/phases/18.1-one-runtime-model`
**Files scanned:** about 12 read or grepped
**Pattern extraction date:** 2026-10-17
**Assumption:** `tests/wizard_fixtures.py` is Textual-wizard specific (`make_ctx`) and is not a useful analog; the curated-config e2e helpers replace it.
