# Phase 32: Re-judge baseline - Pattern Map

**Mapped:** 2026-11-07
**Files analyzed:** 22 new or modified (plus the records folder and the SKILL.md text fixes)
**Analogs found:** 21 / 22 (all analog paths verified tracked with `git ls-files`)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tools/judge_loop.py` | utility/CLI tool | batch + file-I/O + request-response (jev child) | `.planning/milestones/v1.3-phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/check_verdicts.py` (validator) + `tools/check_dogfood.py` (root, `(problems, notes)`, `main`) | role-match (composite) |
| `tests/test_judge_loop_prompt.py` | test | file-I/O (fixture git repo) | `tests/test_staged_mapper.py` `StagedPathsTest.git` (temp git repo) | role-match |
| `tests/test_judge_loop_count.py` | test | transform | `tests/test_check_dogfood.py` `TestEdgeFloors` (injected `run`/`which`) | role-match |
| `tests/test_judge_loop_check.py` | test | transform | `check_verdicts.py` `self_test()` (good verdict then mutated copies) | role-match |
| `tests/test_judge_loop_report.py` | test | file-I/O | `tests/test_check_dogfood.py` `TestEdgeFloors._root` | role-match |
| `tests/test_skill_frontmatter.py` | test (gate) | transform | `tests/test_setup.py` `TestReadFrontmatter` guards (lines 5524-5553, being replaced) | exact (replaces) |
| `tests/test_skill_frontmatter_pyyaml.py` | test (unit-uv) | transform | `tests/test_framework_profiles.py` | exact |
| `tests/test_skill_text_history.py` | test (gate) | transform | `tests/test_rules_docs.py` clause-pin helpers | partial |
| `tests/test_gate_scope.py` (edit) | test | transform | its own `TestGateScope` / `TestGateScopeNonVacuity` | exact |
| `tests/test_setup.py` (edit) | test | delete two tests | self | exact |
| `tests/test_rules_docs.py` (edit) | test | transform | `_DESIGN_MARKER` / `_DESIGN_CLAUSES` / `_design_bullet` | exact |
| `tests/test_arch.py` (edit) | test | transform | `LOOKUP_COPIES` tuple | exact |
| `tools/check_dogfood.py` (edit) | tool | file-I/O | `check_edge_floors` | exact |
| `tests/test_check_dogfood.py` (edit) | test | file-I/O | `TestEdgeFloors._root` | exact |
| `tools/run_unittest_parallel.py` (edit) | config | n/a | `UNIT_UV_MODULES` (line 94) | exact |
| `Makefile`, `.pre-commit-config.yaml` (generated) | config | batch | `python3 tools/gen_test_groups.py` | exact |
| `agents/ai-kit-judge.md` (edit) | config | n/a | self (add `effort: xhigh` plain line) | exact |
| `AGENTS.md`, `README.md` (edit) | doc | n/a | self | exact |
| SKILL.md and reference text fixes | doc | n/a | D-19 plus the research hits table | exact |
| `.planning/judge/*` | records | file-I/O | none | no analog |

## Pattern Assignments

### `tools/judge_loop.py` (utility, batch + file-I/O)

**Analog A:** `.planning/milestones/v1.3-phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/check_verdicts.py`

Promote `parse_status_line`, `grade_of`, `validate_verdict`, the digest idea (lines 30-79, 101-107). Drop `SKILL`, `JUDGES`, `lane_ok`, the seven-round label.

**Status line and grade** (lines 27-38):
```python
_STATUS_PREFIX = "AIKIT-XAI "

def parse_status_line(line):
    if not line.startswith(_STATUS_PREFIX):
        return None
    return dict(token.split("=", 1) for token in line.split() if "=" in token)

def grade_of(pct):
    return "A" if pct >= 90 else "B" if pct >= 80 else "C" if pct >= 70 else "D" if pct >= 60 else "F"
```

**Validator core** (lines 43-69): exact key set `KEYS`, `scores`/`max` exactly `D1..D8` ints, `(rubric_version, spec_sha) != rubric`, sum checks, `percent == round(total / max_total * 100, 1)`, `grade == grade_of(pct)`; finding shape check at lines 72-78. Copy as is; make `rubric` a parameter read from the pin reader, not a header line.

**Digest, with the three fixes** (original lines 101-107 use `git ls-files -- skills/<SKILL>` + `.split()` + cwd-relative open):
```python
files = sorted(subprocess.check_output(["git", "ls-files", "--", "skills/" + SKILL], text=True).split())
return hashlib.sha256("".join(hashlib.sha256(open(f, "rb").read()).hexdigest() + "  " + f + "\n" for f in files).encode()).hexdigest()
```
Change to: `git -C <root> ls-files -z -- skills/<name>/` (trailing slash, `-z` split on `\0`), read `root / f`, keep POSIX root-relative paths in the digest line. Also add from `tmp/judge-30/round3/check_verdicts.py` (gitignored scratch, copy the idea only): unique finding ids, finding `file` exists with `line <= line count`, a finding for each below-max dimension. Resolve the finding path and require it under `root` (the original does `ROOT / f["file"]` unguarded).

**Analog B:** `tools/check_dogfood.py` for root, `(problems, notes)` and exit codes.

**Pure check returning `(problems, notes)`** (lines 478-508): injected `run`/`which`, tuple return, missing prerequisites become notes, not problems. Copy the shape for `check(root, judge_dir)`.

**main composition** (lines 511-539):
```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=...)
    args = parser.parse_args(argv)
    ...
    for line in [*notes, *problems]:
        print(f"{PREFIX} {line}")
    if problems:
        return 1
    print(f"{PREFIX} ok")
    return 0
```
Difference: D-01 forbids `__file__` for the root (`REPO_ROOT = Path(__file__)...`, line 30). Use `git rev-parse --show-toplevel` in the cwd with `--root` override; one subcommand parser (`add_subparsers`). Exit 0/1/2, usage = 2 (argparse default).

**Analog C:** `tools/staged_mapper.py` for D-14: `build_index(root: Path) -> Index` (line 86) and `covering_modules(index, path) -> frozenset[str]` (line 218); it raises `MapperError` (line 42). Return `sorted(...)` or "no script test found". Import by path or `from tools import staged_mapper` as `check_dogfood.py` imports sibling tools.

**Analog D:** installed-skill lookup copy, `tools/hooks/precompact_core.py` lines 77-94 (same literal as `skills/jev-fast-decision/scripts/jev_ladder.py`):
```python
JEV_ENTRY_REL = os.path.join("jev-fast-decision", "scripts", "jev_review.py")
SKILLS_ROOTS = (("CLAUDE_CONFIG_DIR", ".claude", "skills"), (None, ".agents", "skills"),
                ("XDG_CONFIG_HOME", ".config", "opencode/skills"),
                ("CURSOR_CONFIG_DIR", ".cursor", "skills"),
                ("PI_CODING_AGENT_DIR", ".pi/agent", "skills"))

def skills_roots(env, own_root):
    roots = [own_root] if own_root else []
    home = env.get("HOME", "")
    for var, fallback, suffix in SKILLS_ROOTS:
        value = env.get(var, "").strip() if var else ""
        base = value or (os.path.join(home, fallback) if home else "")
        ...
```
`tests/test_arch.py` `python_roots` reads the module-level `SKILLS_ROOTS` with `ast.literal_eval`, so keep the exact literal-tuple form and the names `SKILLS_ROOTS` and `JEV_ENTRY_REL`. Use the same roots for `skill-judge` (`--judge-dir` override for tests) and for `jev_review.py`.

**Analog E (jev call):** `skills/jev-fast-decision/scripts/jev_review.py ladder [--second-opinion] [--client PATH]`, stdin `{"items":[{id,type:"score",instructions,context,criteria:[2-10 level texts]}]}`, stdout JSON with `status` ok|unavailable and per-answer `level`, `needs_fallback`. Needs `GSD_PATH_JEV=1` and `GSD_PATH_JEV_TIMEOUT_SECONDS` env. Run as a child process with injected runner (like `check_edge_floors`'s `run`), map any error, `needs_fallback` or `--no-jev` to the deterministic count and record why. Treat an unresolvable base commit as "jev input absent" (research: `16153d6`, `d2855bc` are not ancestors of HEAD).

**Count rule (research Pattern 5):** compare percents as integer tenths, `abs(round(p * 10) - 800) <= 70`.

**Gate bar (check_verdicts.py line 200):** `(crit == 0 and high == 0) or pct >= 80`, worst judge decides; name the clause.

---

### Tests for `judge_loop` (four modules)

**Temp git repo helper** (`tests/test_staged_mapper.py` lines 283-291), copy for the prompt and digest tests (sub-folder digest case `ai-kit-spec-review` vs `-fixer`):
```python
quiet = ["-c", "user.name=t", "-c", "user.email=t@t.invalid", "-c", "commit.gpgsign=false",
         "-c", f"core.hooksPath={os.devnull}"]
env = {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
       "GIT_CEILING_DIRECTORIES": str(self.tmp)}
subprocess.run(["git", *quiet, *args], cwd=self.root, env=env, check=True, capture_output=True)
```
Skip with `@unittest.skipUnless(shutil.which("git"), ...)`.

**Fixture root writer** (`tests/test_check_dogfood.py` lines 518-531): `tempfile.TemporaryDirectory()` + `addCleanup`, write `{rel: text}` into `root`. Fake the lane output; never spawn a host CLI (tripwire rule); pass `--judge-dir` fixtures, `--no-jev` or an injected runner. Verdict mutation tests follow `self_test()` (check_verdicts.py lines 82-92): one good verdict, then `dict(good, percent=70.0)`, `dict(good, grade="B")`, a short `scores`. Tests never read `.planning/`.

---

### `tests/test_skill_frontmatter_pyyaml.py` (test, unit-uv)

**Analog:** `tests/test_framework_profiles.py` lines 1-31: `import yaml` at top, `re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)` then `yaml.safe_load`. Add a `SafeLoader` subclass whose mapping constructor raises on a duplicate key (PyYAML accepts duplicates, npm `yaml` rejects). Add the module to `UNIT_UV_MODULES` in `tools/run_unittest_parallel.py` (line 94, currently `frozenset({"tests.test_framework_profiles"})`) and run `python3 tools/gen_test_groups.py`.

### `tests/test_skill_frontmatter.py` (test, unit)

Replaces `tests/test_setup.py::TestReadFrontmatter.test_real_entries_have_a_name_and_a_description` (5524-5536) and `test_real_inline_descriptions_are_strict_yaml` (5538-5553); keep the other `TestReadFrontmatter` tests. Do not reuse `setup._read_frontmatter` (lossy). For double-quoted scalars use `json.loads` as `setup._front_scalar` does (line 900). Entries: use `setup.enumerate_entries` (23 skills plus the agent). Count description length after folding. Stdlib only.

### `tests/test_skill_text_history.py` (test, unit)

No close analog for the scanner. Take structure from `tests/test_rules_docs.py` (`_flat`, constants of phrases/clauses at module top, `subTest` per file) and add a non-vacuity test per rule, as that file does. Detector must be fence-aware (a `## Review:` inside a fenced block is not a section, and the cross-ai date at `SKILL.md:91` sits in a fence; research says change the sample to `<iso time>` rather than skipping fences). Exempt set of seven `ai-kit-project-rules-*` pinned equal to the folders with that prefix.

---

### `tests/test_rules_docs.py` (edit: AGENTS.md pins for D-20)

**Analog:** lines 103-180 of the same file.
```python
_DESIGN_MARKER = "- **Design rule**:"
_DESIGN_CLAUSES = ("Simple is not the same as easy.", ...)

def _design_bullet(text):
    padded = "\n" + text
    start = padded.find("\n" + _DESIGN_MARKER)
    ...
    ends = [e for e in (padded.find("\n- ", start + 1), padded.find("\n## ", start + 1)) if e >= 0]
    return _flat(padded[start : min(ends) if ends else len(padded)])
```
New marker is the skill-judge bullet, "- Any new or materially updated `SKILL.md` passes the `skill-judge` review" (AGENTS.md line ~55); add `_JUDGE_CLAUSES` for the round cap, refute-by-running and behaviour-not-history, plus a non-vacuity test copying `test_removing_one_design_clause_reports_exactly_that_clause`. The AGENTS.md text must stay one bullet: a nested `- ` line ends it early.

### `tests/test_gate_scope.py` (edit: R1 stray-module guard)

Add a pure function (one walk of `tests/`, skip `__pycache__`, sorted nested `test_*.py`), a tree test in `TestGateScope` (line 452), and a fixture-tree non-vacuity case in `TestGateScopeNonVacuity` (line 633), same style as `test_path_under_roots_rejects_a_sibling_prefix` (653-655): call the function with a synthetic input and `assertEqual`/`assertTrue`.

### `tests/test_arch.py` (edit: lookup copy)

Add `"tools/judge_loop.py"` to `LOOKUP_COPIES` (lines 1687-1694). `test_every_lookup_copy_is_compared` scans only `skills/` and `tools/hooks/`, so the entry is manual.

### `tools/check_dogfood.py` (edit: `check_jdg04_citations`, judge records)

**Analog:** `check_edge_floors` (478-508) and `main()` lines 529-530:
```python
edge_problems, edge_notes = check_edge_floors(root)
problems, notes = problems + edge_problems, notes + edge_notes
```
Add the same two-line pair for each new check before the no-write guard. A missing `.planning/judge/` or ROADMAP is a note (the long-path clone has no `.planning/`). Keep pylint limits (`max-statements=50`, `max-branches=12`) in mind: `main()` is already long, so new composition lines should be minimal. Tests in `tests/test_check_dogfood.py` copy `TestEdgeFloors._root` (518-531) with a minimal ROADMAP: phase above 32 naming `SKILL.md` without `JDG-04` (flagged), with it (passes), `32.1` by tuple, `JDG-040`, `jdg-04`, JDG-04 only in a Requirements line, a Backlog entry.

### `agents/ai-kit-judge.md`

Add one plain line `effort: xhigh` after `model: opus` in the frontmatter (lines 1-6). Update the `README.md` judge row (~line 51) in the same commit.

## Shared Patterns

### Only `check_dogfood.py` reads `.planning/`
**Source:** `tests/test_arch.py` `check_no_planning_reader` (line ~1154). Every new test uses fixture roots; `tools/judge_loop.py` takes the folder as an argument with no `.planning` default.

### Stdlib-only runtime, atomic writes
**Source:** AGENTS.md Non-Negotiable Rules. `tools/judge_loop.py` imports only the stdlib (plus sibling tools). Record writes: `tempfile.mkstemp()` + `os.replace()`; never overwrite a valid verdict record.

### Return `(problems, notes)`, print with a prefix, exit 0/1/2
**Source:** `tools/check_dogfood.py` lines 511-539.

### Non-vacuity beside every gate rule
**Source:** `tests/test_gate_scope.py::TestGateScopeNonVacuity`, `tests/test_rules_docs.py` (clause removal reports exactly that clause).

### Generated listings
After adding test modules or editing `UNIT_UV_MODULES`, run `python3 tools/gen_test_groups.py`; `test_generated_listings_name_every_discovered_module` fails on a stale listing. These edits touch `SHARED_MACHINERY`, so the commit runs the full unit and arch groups once.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.planning/judge/REJUDGE.md`, `inputs.json`, `verdicts/...`, `refutations/<loop>.json` | records | file-I/O | New record layout; follow D-02, D-04, D-06 and the Report determinism pitfall (no clock, host or absolute path; sort by owning batch then name). The p27 `build_report.py` in `.planning/research/2026-11-02-next-milestone/p27-judge-scripts/` is a scan reference only (untracked-status unchecked; do not cite as a code source). |

## Metadata

**Analog search scope:** `tools/`, `tests/`, `skills/jev-fast-decision/scripts/`, `agents/`, the phase 27 judge folder
**Tracked check:** `tools/check_dogfood.py`, `tools/staged_mapper.py`, `tests/test_check_dogfood.py`, `tests/test_framework_profiles.py`, `tests/test_gate_scope.py`, `tests/test_rules_docs.py`, `skills/jev-fast-decision/scripts/jev_ladder.py` and `jev_review.py`, `agents/ai-kit-judge.md` and the phase 27 `check_verdicts.py` all returned from `git ls-files`. `tmp/judge-30/round3/check_verdicts.py` is gitignored scratch (idea only). `tools/hooks/precompact_core.py` was read but not `ls-files`-checked; `tests/test_arch.py` names it in `LOOKUP_COPIES`.
**Pattern extraction date:** 2026-11-07
