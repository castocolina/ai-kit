# ai-kit Agent Instructions

`ai-kit` is uz's personal collection of Agent Skills (agentskills.io
standard) and a one-line installer, portable across Claude Code, opencode,
Codex CLI, Cursor, and other conformant hosts. This is a solo-dev project.

## Required Start

1. For milestone work, read `.planning/PROJECT.md`, `.planning/STATE.md`,
   `.planning/ROADMAP.md`, and the active phase's `NN-CONTEXT.md` before
   planning or implementation.
2. Use a GSD workflow before repository edits: `/gsd-discuss-phase` →
   `/gsd-plan-phase` → `/gsd-execute-phase` for milestone-scale work;
   `/gsd-quick` or `/gsd-debug` for small, well-scoped out-of-plan work.
3. Live-verify claims against the actually-installed tools/config on this
   machine before trusting a PRD's, REQUIREMENTS.md's, or a doc's wording at
   face value (`.planning/PROJECT.md`'s core value: never claim more
   certainty than verified).

## Non-Negotiable Rules

- **Design rule**: Simple is not the same as easy. Prefer the simple design over the
  complex one, but never recommend the easier option when it gives the user less value
  only to skip a few steps that are not hard, and never ship a half-done feature or
  mediocre value to keep a change small. Ponytail decides how the code is built (reuse
  existing components, helpers and well-known design patterns before writing from
  scratch, with no speculative abstraction), not how much of the feature ships. MVP mode
  only shifts the weight toward simplicity and never allows a half-done feature. When jev
  is present it classifies the options against these criteria; without jev the rule still
  applies, decided by the agent's own reasoning. Where ponytail's smallest-change wording
  meets this rule, ponytail yields.
- **English only, always**: write all documentation, planning artifacts,
  commit messages, code comments, and any other written project artifact in
  English, regardless of what language the conversation with uz happens to
  be in. Never mix languages within a single document or file (no
  "Spanglish"). Translate quoted non-English input faithfully into English
  rather than leaving it verbatim. Conversing with uz in another language is
  fine — everything written to a file must be English.
- Runtime code (`tools/claude-status-line.py`, `tools/cursor-status-line.py`,
  `tools/common_*`, `tools/claude_*`, `tools/cursor_*`, `tools/statusline-doctor.py`,
  and `tools/setup.py`'s non-wizard paths) stays **stdlib-only** — no third-party imports, ever. `uv`/`textual`-class dependencies are dev- or
  wizard-only, reached only through the guard + re-exec + fail-closed
  pattern (`ensure_rich_runtime()`/`_textual_importable()` in
  `tools/setup.py`) — never a silent runtime import.
- Every write to a runtime's config file (opencode.jsonc, Codex TOML, Claude
  JSON, ai-kit's own `settings.json` wiring) is atomic (`tempfile.mkstemp()`
  + `os.replace()`), reusing `_read_json_checked()`/`_atomic_write_json()`. JSONC surgical
  edits preserve every other byte untouched — comments, formatting,
  unrelated entries.
- No diagnostic, detection, or catalog result is presented with more
  certainty than its actual sourcing — reverse-engineered formats,
  informational-only settings, and inferred classifications are visibly
  flagged, never shown at the same confidence as officially documented
  behavior.
- Any new or materially updated `SKILL.md` passes the `skill-judge` review
  loop before being marked complete: no remaining critical or high-severity
  finding, or a grade of B or better on the skill's own percent bands (the
  `skill-judge` rubric defines the bands and the total, so this rule carries no
  absolute score), and no regression against the previous judged result of the
  same skill beyond the judge's run-to-run variation.
- Commit one coherent, buildable logical change (a logical commit) with its
  tests and documentation together. Let pre-commit hooks run; never use
  `--no-verify` to skip pre-commit checks or dodge a real failure. The one
  sanctioned exception: deliberately committing a failing test before
  turning it green (TDD red-green) is not "skipping the check" — the check
  still runs, the red state is intentional.
- Preserve unrelated dirty or untracked work. Never `git reset --hard`,
  `git clean -f`, `git checkout .`/`git restore .` without uz's explicit
  confirmation.
- Never hardcode an absolute path (a machine-specific filesystem path) in
  source, tests, or project assets — resolve a relative path against the
  repo root, or via a discovered/passed-in base path, instead.
- Fix a failing test or bug; no excuse-driven deflection ("flaky test",
  "unrelated tooling", "pre-existing issue") or silently redefining it as
  out of scope to dodge the work. When something genuinely is pre-existing
  or out of scope, say so explicitly to uz — don't quietly work around it.

## Architecture

- The `RUNTIMES` table in `skills/ai-kit-spec-review/ai_kit_spec/detection.py`
  is the single source of truth for runtime ids, binaries, host signals,
  listing, native selectors and the review-only flag. `KNOWN_CLIS` derives
  from it. `detect_installed_clis()` (binary-on-PATH) and
  `detect_current_runtime()` (which CLI hosts *this* process) stay different
  questions — never conflate them.
- A reviewer or executor entry is a (runtime, model) pair, the session default
  (neither a runtime nor a model), or a trust-gated custom `command` entry
  (a command and no runtime). Native versus subprocess is decided per call by
  `ai_kit_spec/routing.py` and never stored. Every subprocess runs through the
  runner template via `ai_kit_spec/runner_dispatch.py`; a custom entry runs
  through the custom launcher on the same core. Legacy reviewer fields still
  load in memory, with a note naming the entry and the re-save command.
- `model-catalog.json` reserves the top-level key `_meta` for cache metadata such as
  `schema_version`; every other top-level key is a `provider/model` entry. Code that iterates
  the catalog must skip `_meta` (the sibling skills that read this file already skip non-model
  values, pinned by regression tests); writers go through
  `model_catalog.split_catalog_meta`/`join_catalog_meta`, and `merge_catalog_entry` rejects
  `_meta` as a model id.
- Status-line role modules use banner-delimited blocks and role-prefixed top-level functions.
  `tests/test_arch.py` enforces those conventions, dependency direction (common modules do not
  import either host family; host families do not import one another), allowed host imports, and
  the networking boundary in `cursor_quota.py` via AST checks. Extend those rules, don't bypass
  them. The broader whole-tree layering suite remains backlog 999.3.
- Skills under `skills/` follow the Agent Skills open standard so they work
  unmodified across hosts — don't write one against Claude-Code-specific
  behavior unless there's genuinely no portable equivalent; flag the gap
  explicitly instead of silently degrading.
- Before reusing the `ensure_rich_runtime()` guard pattern for a new
  interactive feature, confirm its fail-closed path is exercised by more
  than a mock — a prior investigation found it lacks a genuinely-clean-
  container e2e test.

## Tools and Stack

- Dev/lint env is `uv`-managed, pinned via `uv.lock`
  (`pyproject.toml`'s `dev` group): `ruff~=0.14` (target `py312`,
  line-length 100, `select = [E, F, W, I, UP, B, SIM, RUF]` — the `RUF00x`
  ambiguous-unicode rules are ignored globally since the status line is
  intentionally unicode-rich UI), `pylint~=4.0` (`max-args=5`,
  `max-locals=15`, `max-branches=12`, `max-returns=6`, `max-statements=50`),
  `pyright~=1.1` (`basic` mode), `vulture~=2.14` (`min_confidence=80`),
  `pre-commit~=4.4`, `textual>=8.0,<9.0` (dev/wizard-only).
- `tools/install.sh` and `tests/test_install.sh` are checked with
  `shellcheck` — fix findings, don't suppress without a documented reason.
- Don't add a new dev dependency without checking whether an existing
  stdlib-only or already-approved approach covers the need (e.g. the
  hand-rolled-JSONC-scanner precedent over a JSONC-parser dependency).
- uz's local shell may add modern CLI tools (`rg`, `bat`, `sd`, `fd`, `eza`) and `graphify` (knowledge-graph indexing; `graph.json` under `graphify-out/`) over the defaults; use them when present.

## Testing

- `make test` is the aggregate over four pyramid tiers, each a runner group:
  `test-unit` runs `unit` under system python3 plus `unit-uv` under uv;
  `test-integration` runs `integration`, the Textual app and PTY suites;
  `e2e-test` runs `e2e`, the real git worktrees, memory checks and real
  `node` runs against the checkout-local gsd-core, plus
  `bash tests/test_install.sh`; `arch-test` runs `arch`. Run `make test`
  before considering work done — the Python suite alone doesn't cover
  installer behavior (fetch, symlink, wiring).
- Every tier runs one subprocess per module, in parallel, through
  `tools/run_unittest_parallel.py --group <name>`, never a sequential
  `python3 -m unittest` list. A new `tests/test_*.py` joins the `unit` group
  automatically. A module that needs uv, a PTY or Textual run, or must stay
  out of `make validate` goes into the matching commented exception set in
  the runner; a module that cannot run in parallel goes into an explicit,
  commented exception set, never a silent sequential path.
  `tests/test_gate_scope.py` enforces this.
- Parallelism is a share of the available CPUs (`os.process_cpu_count()`,
  then the affinity mask, then `os.cpu_count()`), capped at 40%.
  `AI_KIT_TEST_CPU_SHARE` may lower the share, never raise it. Never
  hardcode a worker or core count.
- `make lint` — the shellcheck and py-compile hooks (pre-commit, all files),
  aggregated like `validate`. `make validate` — the commit and push hooks, run
  across all files via the per-hook single-tool targets (`ruff`, `pylint`,
  `pyright`, `vulture`, `shellcheck`, `py-compile`, `unittest`,
  `unittest-wizard`, `check-dogfood`). Ruff, py-compile, pyright and vulture cover
  `tools/`, `skills/` and `tests/`; pylint covers `tools/` and `skills/`.
  `security-scanner` and `duplicate-code` are informational-only Makefile
  targets, not wired into `validate`.
- Commit stage: the `staged-tests` hook (pre-commit, verbose) runs
  `tools/run_unittest_parallel.py --staged`, which runs only the modules that
  cover the staged files. The name index (`tools/staged_mapper.py`) is rebuilt on
  every commit; `python3 tools/staged_mapper.py --stats` shows its selectivity.
  A staged data file outside the unit folders (`.md`, `.json`, `.jsonc`, `.yaml`,
  `.yml`, `.toml`, `.txt`) selects only the modules whose code names it: a comment
  or docstring that names it selects nothing. Code files match anywhere.
  Unit and arch modules run under python3; the modules that need uv (unit-uv,
  integration, and the covering e2e modules within budget) run under uv after
  them. A covering e2e module over the 60 s commit budget
  (`COMMIT_E2E_BUDGET_SECS`), or with no recorded time (`E2E_RECORDED_SECS`), is
  not run at commit: the hook prints `staged: deferred to push` with its run-now
  command, and the pre-push `deferred-e2e` hook runs it. The full unit and arch
  groups run instead when a `SHARED_MACHINERY` file is staged, a tests/ helper or
  fixture covers two or more modules, a staged file that the test sources name
  has no covering module, or the mapper fails. Refresh `E2E_RECORDED_SECS` from
  the `=== <module>: ok in <s>` lines of `make e2e-test` when an e2e module's time
  changes. Known limit: a test that reaches files only through a glob (for example
  `skills/*/SKILL.md`) is not selected for them at commit; the push stage still
  runs it. A tool that another tool loads by path is selected only when the
  loader's test names it.
- Push stage: the pre-push hooks are `unittest` (unit and arch, under python3),
  `unittest-wizard` (unit-uv and integration, under uv), `pyright`, `vulture`,
  `check-dogfood` (the live-project check) and `deferred-e2e`. `deferred-e2e` runs
  the covering e2e modules the commit stage deferred. It narrows to the pushed
  range only when the proof holds: the push is the checked-out branch, pushed from
  its own checkout, and no other unpushed local branch or worktree HEAD holds a
  commit outside it. Local tags are left out of that check, so unpushed archive or
  backup tags do not force the slow path; a tag pushed by name, or with `--tags`
  beside the branch and pointing outside it, is not seen, so push such a tag on its
  own. Every other push (several refs, a branch other than the checkout, an
  unpushed side branch, no range, a mapper error) runs every over-budget e2e module,
  the worst case below. Like every push hook, the checks test the checkout, so push
  a branch from its own checkout to test that branch's code.
- Push timing: the 60 s target covers the two test hooks only, their subtotal,
  measured back to back by `python3 tools/time_prepush.py` at the default 40 %
  share. Before this phase they took 183.9 s (2026-11-03: 24 CPUs, 9 workers,
  one-minute load 1.86 at start); after this phase and the runner self-test split
  they took 55.4 s (2026-11-04: 24 CPUs, 9 and 5 workers, share 0.40, one-minute
  load 4.48 at start; unit and arch 34.4 s, wizard 21.0 s); after the test-time
  cuts, 30.7 s (2026-11-04: 9 and 7 workers, load 1.90; unit and arch 21.6 s,
  wizard 9.0 s). The pyright (9.7 s), vulture (1.9 s), check-dogfood (0.5 s) and
  deferred-e2e (0.0 s, no push range; no e2e module is over the commit budget)
  times are recorded beside the subtotal, never inside the 60 s figure, with
  `push-worst` (all six pre-push hooks timed alone, deferred-e2e at its no-range
  worst case) as the worst-case whole push: 42.7 s.
- Runner self-test shards: `cross-ai.mjs --self-test-list` prints every self-test
  case as `name<TAB>kind`, `logic` or `runtime` (a case that waits on or measures
  a real clock is `runtime`). `tests/cross_ai_selftest.py` deals each kind,
  longest first by the generated `tests/fixtures/cross_ai_selftest_secs.json`,
  into the `tests/test_cross_ai_selftest_<kind>_<i>_e2e.py` shard modules, so each
  fits the commit budget and a template change runs its shards at commit. Refresh
  that file with `python3 tests/cross_ai_selftest.py --record-times` on a quiet
  machine after adding or slowing a case.
- Isolation: every module runs behind a tripwire. A stub for each host CLI sits
  first on its PATH, and a real host call fails the module with a `tripwire:`
  block; host behaviour comes from `tests/host_fakes.py`. The stubs make
  `shutil.which` find every host inside a module, so a test that needs a host
  absent sets its own PATH. Every module also runs under a baseline env: no host
  signals or inherited git state, no host config, status-line, credential or
  backend-URL overrides, a temporary HOME with `AI_KIT_REFUSE_REAL_HOME=1`, and
  the caller's tool caches forwarded. The tripwire sees PATH lookups only; a host
  CLI called through an absolute path is not seen at run time, and the arch rule
  in `tests/test_arch.py` catches a test that names a host CLI as the program it
  spawns. No test reads the repo's `.planning/`: archived data lives under
  `tests/fixtures/archived/`, pinned by an arch rule with no exceptions.
- `make check-dogfood`: the live-project check. It verifies that the project's own
  cross-AI runner copy is a pristine render of the shipped template, and that the
  curated-config write flows leave the live `.planning/` config and runner files
  untouched. It is the only reader of `.planning/`, part of `make validate`, and a
  pre-push hook.
- `make test-env-matrix`: the six-environment proof (SPEC R7). It runs `make test`
  in plain, host-session, no-host-cli, long-path (a checkout path of 200+
  characters), custom-tmpdir (a TMPDIR with a space inside a repo) and outside-git
  (started from outside any repository) environments, one after another, for about
  six `make test` durations (about 45 minutes here). Each environment is compared
  module by module with the plain run, which must itself be green with one report
  per module. It is not part of `make test`, `validate` or any hook; run it when
  test infrastructure changes. Because the runner baseline already strips host
  signals, stubs host CLIs and fixes the cwd, the host-session, no-host-cli and
  outside-git environments mainly check make, uv and `tests/test_install.sh`; the
  long-path and custom-tmpdir environments carry most of the module-level evidence.
  The long-path clone has no `.planning/`, so a test that still reads it shows as a
  difference there.
- `tests/*` gets a lighter ruff bar than runtime code (idiomatic test
  patterns are fine there even where they'd fail elsewhere).
- `tests/test_arch.py` is a structural-fitness test (parses source with
  `ast`, no import/execution). Its `TestArchNonVacuity` class proves each
  rule actually catches the violation it claims to — don't add a structural
  rule without a non-vacuity counterpart.
- Never use uz's real config files (`~/.claude/settings.json`,
  `~/.cursor/...`, `~/.config/opencode/...`) as a test fixture — use
  temporary directories and synthetic content.
- For UI/wizard changes, actually run `tools/wizard_app.py` under `uv run`
  before reporting done — type checking and unit tests verify code
  correctness, not feature correctness.
- Kill/stop any ephemeral process or window spawned for e2e verification (a
  dev server, a spawned terminal, a background listener) once verification
  is done — never leave it orphaned after the task ends.
- Don't run `make validate` before each commit or push: the hooks run the same checks. After a
  hook fails, fix the cause, re-run only the failed check's target (`make test-unit`,
  `make pyright`, ...) until it passes, then commit again so the hooks re-run everything.
- Closing a plan, phase or spike leaves nothing behind that the run started: no background
  process, container, browser or Playwright instance, held lock, temp files in `/tmp` (size or
  inode count), large scratch files outside `tmp/` or swap pressure, and no untracked,
  non-ignored ephemeral file in the working tree (move it under `tmp/`, remove, ignore or
  commit it). Leftovers that predate the run are reported, never removed. Phases 47 and 49
  turn both rules into a playbook and a hook advisory.
- **Deferred**: a whole-tree architecture-layer test suite across `tools/` and `skills/` remains
  backlog 999.3. Status-line modules now have focused dependency-direction, host-import and
  networking-boundary rules in `tests/test_arch.py`; these do not replace that broader suite.

## Code Exploration

- Explore code with codegraph first: the `codegraph_explore` MCP tool, or `codegraph explore` in a shell.
- Search Markdown with `rg`; codegraph indexes no Markdown.
- Use graphify and `/gsd-graphify` for documents and planning next to code.
- Index and sync automatically whenever the CLI is present: with no `.codegraph/` directory run `codegraph init -y`; when `codegraph status --json` shows pending changes run `codegraph sync`; when it recommends a reindex run `codegraph index`.
- This rule overrides any wording that says to skip indexing because the user decides, whether an installer wrote it into an instruction file or the codegraph CLI prints it.
- Build or refresh the graph with `graphify update .` (AST-only, honoring the root `.graphifyignore`) or `/gsd-graphify build`.
- One `graphify update .` build feeds both locations: `graphify-out/graph.json`, and in a GSD project with `graphify.enabled` true the copy in `.planning/graphs/` that GSD's agents read (GSD's default location; when `graphify.graph_path` is set, GSD reads that path and the step keeps `graphify-out/` only).
- `graphify update` takes no `--graph`; raw queries reach GSD's copy with `--graph .planning/graphs/graph.json`.
- In a project without GSD, query `graphify-out/graph.json`.
- On stacked branches with no local merges GSD's auto-update never fires, so both indexes go stale unless refreshed.
- The unit flow's boundary step refreshes both indexes and rewrites `.aikit/brief/SKILL.md` at a unit's start (in GSD, the `discuss:pre` start step, so before discussion and research), before its planning (in GSD, the orchestrator's numbered pre-plan step, plus the planner's own first step) and before its first execution wave.
- Before a superpowers plan exists, run `python3 <fold skill>/scripts/fold.py boundary --next --point plan` (`<fold skill>` is the `ai-kit-commit-fold` folder that the superpowers adapter's `references/start-step.md` finds; in ai-kit, `skills/ai-kit-commit-fold`) and hand `.aikit/brief/SKILL.md` to the plan writer.
- Build, refresh, freshness and query steps: [the graphify runbook](docs/run-book/graphify.md).

## Workflow

- When a live-verified fact contradicts `REQUIREMENTS.md`/`ROADMAP.md`
  wording, amend those files formally (not just the phase's own
  `CONTEXT.md`) — downstream researcher/planner agents trust them as the
  source of truth for phase boundaries.
- Genuinely unresolved factual questions get routed to the
  `gsd-phase-researcher` as explicit open questions, never answered by
  invented/guessed content.
- A proposal outside a phase's literal requirement scope gets a real
  feasibility check against the already-confirmed architecture before being
  deferred — don't reflexively push it to the backlog.
- An idea that's genuinely out of scope goes to the GSD backlog
  (`.planning/ROADMAP.md` §Backlog) with a real goal statement, not silently
  dropped.
- Review `git status`/`git diff` after a broad `git add` before committing;
  double-check file contents (not just filenames) for anything that might
  be a secret.
- Every implementation plan must be written so a cross-AI reviewer can
  review it (cross-AI review / plan-review convergence), a cheap cross-AI
  model can execute it (cheap model execution), and every generated command
  is path-agnostic and portable — never a machine-specific absolute path
  baked into a plan.
- Before closing out a plan or PR, fold its commits by the one folding policy,
  `skills/ai-kit-commit-fold/references/folding-policy.md` (one buildable commit
  per logical feature; this compaction covers the whole plan's history, and the
  per-commit rule in Non-Negotiable Rules above still applies to each folded
  commit). Fold before every push without asking for confirmation.
- Ship a finished unit in this order: gates green on the unit branch; an
  installer dry run and the new hooks against a scratch HOME; then the main
  checkout on the unit branch's tip for the install and a live re-check, all
  before verification is marked passed (so the orchestrator's
  `ai-kit-fold ready` runs after them); local `main` moves only when the
  stacked PRs merge, through the owner-started `fold.py merge-chain`.
- Update READMEs and other nested docs (submodule READMEs, diagrams,
  docstrings) after any significant feature change — stale docs are a
  defect, not a follow-up.
- On gray-area or genuinely new/unfamiliar technical topics, verify before
  trusting potentially-stale training data — treat it as stale knowledge
  until confirmed against current external resources (docs, changelogs).
  This is distinct from Required Start #3's live-verify rule: that one
  covers this machine's installed tools/config, this one covers
  external/web currency.
- For genuinely new or unfamiliar technical territory, follow theory →
  hypothesis → spike (`/gsd-spike`) before writing a plan — never plan
  directly on untested assumptions about how something behaves.
- Before closing out a plan, leave no unexplained dangling
  uncommitted/untracked files in the working tree — fold them into a
  commit, add them to `.gitignore`, or ask uz explicitly. This is narrower
  than "preserve unrelated dirty work" in Non-Negotiable Rules above: that
  rule protects work that predates your task from destruction; this one
  stops your own task from leaving its own mess behind.
- Ephemeral scratch files or throwaway scripts with no lasting project
  value go under `./tmp/` (already gitignored) — never scattered loose
  through the repo tree.
- Keep commit messages, plan docs, and summaries concise — no excess
  documentation, no narrative padding: state what was done and why, and
  skip narrating rejected alternatives unless the rejection itself carries a
  load-bearing lesson (e.g. "tried X, breaks because Y" is worth keeping;
  "considered X, went with Y" with no Y-specific reason is not).

## Commands

- `make setup-env` — provision the uv-managed dev/lint venv only (no hook install)
- `make dev` — `setup-env` plus install the pre-commit hooks
- `make setup-dev` — `setup-env`'s `uv sync`, each missing flow tool (codegraph, graphify, pre-commit, gh, gh-stack) and the pre-commit hooks (including `post-checkout`), each through a guarded step that reports a failure with its manual command and still exits 0
- `make test` — aggregate of `test-unit`, `test-integration`, `e2e-test`, `arch-test`
- `make test-unit` / `test-integration` / `e2e-test` / `arch-test` — individual pyramid tiers
- `make lint` — shellcheck + py-compile hooks (pre-commit, all files)
- `make validate` — the commit and push hooks, all files (via per-hook targets)
- `make check-dogfood` — the live-project check (dogfood runner copy, curated-config guards); also a pre-push hook
- `make test-env-matrix` — the six-environment proof (about six `make test` durations); not part of `make test`, `validate` or any hook
- `make format` — `ruff format .` (dev-only, mutates files, not wired into validate)
- `make security-scanner` / `make duplicate-code` — informational/non-gating checks, not wired into `validate`
- `make doctor` / `make check` — installer diagnostics
