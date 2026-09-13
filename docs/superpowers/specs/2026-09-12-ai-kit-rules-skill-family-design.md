# ai-kit Rules Skill Family — Design

## Context and motivation

`ai-kit-project-rules-agents` currently audits two unrelated concerns in
one skill: AGENTS.md/CLAUDE.md workflow-rule prose, and Makefile/
`.pre-commit-config.yaml` target shape. Growing it further (architecture
fitness, Docker Compose conventions, CI/CD parity) would make one skill
responsible for five unrelated domains. This design splits it into a family
of single-domain skills plus an orchestrator, sharing common infrastructure
through a `skills/_shared/` package.

Skill-judge review of the current skill scored it 98/120 (B). Two fixes
(consolidating anti-patterns, documenting the literal-substring-matching
engine quirk, adding decision criteria for branch points) brought it to an
estimated 109/120 (A) — see that skill's `SKILL.md` for the applied fixes.
Every new skill in this family starts from those lessons rather than
re-discovering them:

1. Anti-patterns live in one scannable `## Anti-patterns (NEVER)` section,
   each with the non-obvious *why*.
2. Any "pick option A or B" branch point gets explicit decision criteria —
   never a bare "choose one."
3. Empirically-discovered engine quirks get written down the moment they're
   found.
4. `description` frontmatter answers WHAT/WHEN/KEYWORDS explicitly.
5. Point at code as source of truth instead of duplicating rule text in
   prose — keeps `SKILL.md` lean.

## Scope boundary

Each checker skill **detects and reports findings only** — it never edits
the target repo's files. Applying a fix (editing a Makefile, inserting an
AGENTS.md rule, wiring a CI step) is a decision for whoever invoked the
checker, the same way this session manually applied the Makefile/
pre-commit edits after `ai-kit-project-rules-agents` reported them. The
one existing exception that carries forward unchanged: `ai-kit-project-
rules-agents`'s hand-off to `/agent-md-refactor` for AGENTS.md content,
since that's a pre-existing, already-designed mechanism specific to that
one file type.

## Components

### `skills/_shared/ai_kit_rules_common/` (new)

Domain-agnostic infrastructure every checker skill imports via a relative
`sys.path` insert from its own `__file__` — no skill imports another
skill's package directly, so each remains independently copyable to a
different host (only `_shared/` must travel with it).

- **Classification engine**: `evaluate_condition`, `_classify_flat`,
  `_classify_plain_groups`, `_classify_tool_scoped_groups`, generalized to
  take any rules tuple + text (today's `rule_checker.py` logic, with the
  17-rule-specific coupling removed).
- **`tool_presence.py`**: binary/marker-on-PATH detection primitives.
- **`stack_cache.py`**: generic per-`(skill_name, stack)` cache read/write/
  validate helpers. Each skill gets its own cache namespace at
  `~/.cache/ai-kit/<skill-name>/stack-refs/<stack>.json`, same validation
  contract as today (`ALL_TOOLING_KEYS` membership, non-empty strings,
  `(source: ...)` provenance required) but keyed generically instead of
  hardcoded to Makefile tooling categories.
- **`remediation.py`**: the single-domain ordering helper (criticality-sort
  + `auto_apply` split) each skill uses for its own `remediate` output.
  Cross-skill merging is the orchestrator's job, not this helper's.

### `ai-kit-project-rules-agents` (pruned)

- **Keeps**: `rules.py` (all 17 rules — `check_workflow_rules` already
  filters by non-empty `signals`, not by `category == "workflow"`, so R02's
  AGENTS.md-prose clause stays checked here regardless of its `"makefile"`
  category label), `rule_checker.py` (now importing the shared engine),
  `cli.py`'s `check`/`remediate`.
- **Drops**: `makefile_checker.py`, `stack_cache.py` (the Makefile-tooling-
  specific version), the `cache-path`/`cache-update` subcommands, Step D
  (research-dispatch) — all move to `ai-kit-project-rules-makefile`.
- `check` returns `{"workflow": [...]}` only.
- `SKILL.md` scope line drops all Makefile/`.pre-commit-config.yaml`
  language; Step A/B/C hand-off to `/agent-md-refactor` is unchanged.

### `ai-kit-project-rules-makefile` (new)

Inherits from the current `makefile_checker.py`: `parse_makefile_targets`/
`parse_makefile_recipe`/`parse_makefile_prerequisites`,
`REQUIRED_STATIC_TARGETS` shape check, the `chain_incomplete` check on
`validate`, the `test`/`test-unit` pairing check, and the tooling-
recommendation research-dispatch (Step D, moved here since it's Makefile-
tooling research, not AGENTS.md).

**New checks**:

- **`validate-<category>` family**: for each tooling category with a
  concrete target present (`security-scanner`, `duplicate-code-detector`,
  `dead-code-detector`, `formatter`, `code-smell-detector`), require a
  matching `validate-<short-name>` alias target (`validate-security`,
  `validate-duplicate`, `validate-dead`, ...), and require `validate` to
  chain all of them as prerequisites — not just the flat tool-hook list
  checked today.
- **Fail/help reachability**: the Makefile must define a target (commonly
  `help`) that lists reachable targets, reached either via
  `.DEFAULT_GOAL := help` or a catch-all `%:` rule, so an unknown-target
  invocation prints something actionable instead of a bare Make error.
- **Recipe line-length cap**: no recipe body may exceed 3 lines, except the
  help/fail-printing target itself (which legitimately needs to enumerate
  targets). A longer recipe is a finding recommending extraction to a
  `.sh` script the target then calls.
- **Docker build-before-up**: a `docker-up`-shaped target must have a build
  step (`docker-build`-shaped target, or an inline `build` invocation) as a
  Make prerequisite — never assume a stale cached image is acceptable.
- **Shellcheck threshold**: once a repo has ≥5 bash scripts, a `shellcheck`
  target is required, AND it must be wired into both `.pre-commit-config.
  yaml` and the CI config (cross-checked via `ai-kit-project-rules-cicd`'s
  output when the orchestrator runs both; standalone this skill can only
  confirm the Makefile+pre-commit halves).
- **Advisory ordering heuristic** (non-blocking): using this skill's
  hardcoded baseline knowledge of typical tool speed/failure-frequency
  (formatters/fast-narrow linters early, compilers/type-checkers/test
  suites/security scanners late — see Tooling Taxonomy below), suggest a
  reordering when something is obviously misplaced (e.g. a slow test suite
  declared before a fast linter in `validate`'s prerequisite list). This
  never fails the check — real failure frequency isn't statically knowable,
  so `check_validate_order`'s existing "cost-order unverifiable by regex"
  limitation stays true for blocking purposes; this is advisory-only and
  replaces the prior total no-op with a best-effort suggestion.

### `ai-kit-project-rules-precommit` (new)

Inherits `parse_precommit_hooks`, `check_precommit_prepush_split` (slow-
hook-without-own-stage detection). Owns the Makefile/pre-commit **parity**
check (every hook id ↔ a matching single-tool Makefile target, both
directions) since it needs both files and pre-commit's own
`default_install_hook_types` is the more natural home for "is this hook
reachable at all."

**Ruleset**: classifies any detected tool (regardless of language) into
the 6-category taxonomy below, then applies two baseline (no-research-
needed) heuristics plus stack-specific research for what *should* fill
each category:

- Flag "enable-everything" configs: ruff `select = ["ALL"]`, an unpinned
  PMD ruleset wildcard, ESLint configs enabling all plugins indiscriminately,
  golangci-lint's full available-linter list with no curation. Every
  researched ecosystem's own docs independently discourage this pattern in
  favor of a maintained preset plus explicit, reviewed extension.
- Flag complete absence of **Duplicate-code** or **Dead-code** category
  tooling — research confirms these are the two categories most commonly
  skipped entirely across every ecosystem surveyed.
- Two tools covering the same category is **not** auto-flagged as
  redundant when it's a fast/narrow tool paired with a slow/wide-but-robust
  one for genuinely different failure classes (see pairs table below) —
  that's intentional complementary layering.
- Ruff-specific: flag a config relying solely on `ANN`/`TC` rules for "type
  safety" (those check annotation presence/style, never type correctness —
  a real gap requiring mypy/pyright/ty). Flag `preview = true` with no
  pinned ruff version in CI (preview rules aren't covered by ruff's normal
  stability guarantee). Flag a child config that sets its own `lint.select`
  without noticing it silently discards the parent's `lint.ignore`.
- golangci-lint-specific: flag standalone `staticcheck` run alongside
  golangci-lint with staticcheck already enabled as the one confirmed fully-
  redundant pairing in the Go ecosystem (golangci-lint bundles it verbatim).

### `ai-kit-project-rules-arch` (new, form/convention scope)

Per the scoped-down decision: audits that an `arch-test`-shaped Makefile
target exists, is chained into `test`, and (where the backing test file is
discoverable) that it is AST-only — parses source, never imports/executes
the modules it's checking. Does not attempt real layering/dependency-
direction rule enforcement itself.

Hardcoded baseline knowledge (so remediation advice is concrete, not
generic, even though enforcement stays out of scope): the canonical tool
per stack, confirmed by research as the most-recommended pattern in each
ecosystem —

- **Python → import-linter** (static AST-only via Grimp, safe against
  untrusted target-repo code, config-DSL "contracts")
- **Node/TS → dependency-cruiser** (broadest rule surface: circular deps,
  path-based layering, orphan detection; static, no build/type-system
  dependency)
- **Java → ArchUnit** (runs as ordinary JUnit tests — the most consistently
  recommended pattern across every source surveyed, since a failing named
  test is a stronger CI signal than a side lint-pass failure)
- **Rust / Go**: no equally canonical dedicated tool surfaced in research;
  note this as a known gap rather than asserting a false canonical choice.

ai-kit's own `tests/test_arch.py` already follows the best-practice pattern
(architecture checks live as tests in the normal suite, not a side lint
pass) — confirmed by research, not something this skill needs to change in
ai-kit itself.

### `ai-kit-project-rules-docker` (new)

New rule domain, own rules module (not signal-prose matching — structural
YAML/Makefile parsing, same shape as `makefile_checker.py`'s pattern).

- **Target family** (parity-checked the same way as
  `REQUIRED_STATIC_TARGETS`): `docker-up`, `docker-health`, `docker-stop`,
  `docker-clean`, `docker-prune`, `docker-events-up`, `docker-events-
  monitor`, `docker-events-test`.
- **Healthcheck conventions** per `docker-compose.yml` service: `timeout ≤
  2s`, `start_period ≤ 10s`, `interval ≤ 5s`.
- **`depends_on` discipline**: entries use `condition: service_healthy`,
  never bare ordering-only dependencies.
- **Hot-reload for local dev**: local-dev service definitions use bind-
  mounts plus a dev command override rather than the production image/
  entrypoint baked at build time.
- **Local-dev convention**: entrypoint scripts and dev-only container
  assets live at `docker/local/container/`.
- **Runbook requirement**: `docker/local/README.md` must exist, documenting
  how an agent interacts with the containers, what networks and secrets
  are required, how to copy `.env` files when a new worktree is created,
  and whether that worktree needs fresh containers or can reuse ones
  already running from a sibling worktree.

### `ai-kit-project-rules-cicd` (new)

Checks that the CI config (`.github/workflows/*.yml`, `.gitlab-ci.yml`, or
equivalent) **reuses** the commands already defined in Makefile targets,
pre-commit hooks, `package.json` scripts, or Gradle tasks, rather than
duplicating tool invocations inline in the CI YAML. A CI step that runs
`ruff check .` directly when `make ruff` (or an equivalent single-tool
target) already exists and does the same thing is a finding: the CI step
should call `make ruff` instead, so the two never drift independently.
Reuses the shared classification/cache package like every other skill in
the family.

### `ai-kit-project-rules-all` (new)

Runs all 6 checkers' `check`/`remediate` against one target repo,
aggregates into one report. For AGENTS.md-domain findings only, keeps the
existing Step A/B/C hand-off to `/agent-md-refactor`. For makefile/
precommit/arch/docker/cicd findings, surfaces the aggregated, criticality-
ordered report inline — report-only, no auto-apply, consistent with the
scope boundary above.

## Dual-knowledge pattern (applies to every skill in the family)

Each skill's `SKILL.md` carries two distinct kinds of knowledge, kept
explicitly separate:

1. **Hardcoded baseline** — facts that don't go stale: the 6-category
   taxonomy, the "enable-everything is discouraged everywhere" heuristic,
   the "duplicate/dead-code categories are most often missing" heuristic,
   the canonical-tool-per-stack names for the arch checker, the fast-vs-
   slow ordering callouts below. These are written directly into the
   skill, no research needed to apply them.
2. **Research step** — an explicit instruction to WebFetch/WebSearch the
   *current* recommended concrete tool per category for the target repo's
   detected stack, because concrete tool names go stale fast: this research
   pass alone surfaced `flake8+plugins → ruff`, `ts-prune → knip`,
   `cargo-audit → cargo-deny` (partial), and `ANN rules ≠ type-checking` as
   exactly the kind of drift a hardcoded-only skill would miss. This step
   only fires when no per-stack cache entry exists, or the cached entry's
   timestamp is older than 180 days (matching the staleness convention
   `ai-kit-spec-review`'s framework-profile cache already uses), reusing
   the shared `stack_cache.py` pattern. Since these skills run "a couple of times per
   project, or once per milestone" (infrequent, per the explicit
   requirement), caching is what makes repeat runs cheap instead of
   re-researching every time — the research cost is paid once per stack,
   not once per invocation.

## Tooling taxonomy (cross-language, generalized)

| # | Category | Definition |
|---|---|---|
| 1 | Formatting | Deterministic, opinionated code-shape rewriting. No semantic judgment. |
| 2 | Type-checking | Static type/contract verification requiring a type system or annotations. |
| 3 | Linting/code-quality | Syntactic/semantic rule-based checks for bugs, anti-patterns, complexity. |
| 4 | Security (SAST) | Pattern/taint-based detection of exploitable vulnerability classes. |
| 5 | Duplicate-code | Clone/copy-paste detection via token or AST matching. |
| 6 | Dead-code | Reachability/usage analysis for unused symbols, exports, files, deps. |

Classify by what kind of defect class the tool targets and what input it
needs (AST of one file → linting; whole-project symbol graph → dead-code;
taint/dataflow across files → security; type system → type-checking; pure
text/AST shape → formatting; near-duplicate AST subtrees → duplicate-code).
This generalizes to languages not yet researched without new categories.

### Baseline stacks by language

| Language | Formatting | Type-check | Linting | Security | Duplicate-code | Dead-code |
|---|---|---|---|---|---|---|
| Python | `ruff format` | `mypy`/`pyright` (ruff `ANN` is NOT this) | `ruff check` (curated `extend-select`) | `bandit` (+ruff `S` for speed) | `jscpd` / pylint `R0801` | `vulture` |
| Node/TS | `prettier`/`biome format` | `tsc --noEmit` | `eslint`+`typescript-eslint` (or `biome`) | `eslint-plugin-security` (+`semgrep` in CI) | `jscpd` | `knip` (not `ts-prune` — unmaintained) |
| Java | `spotless`+`google-java-format` | N/A (`javac` inherent) | `checkstyle`+`PMD` (curated ruleset) | `SpotBugs`+`find-sec-bugs` | `PMD CPD` | PMD unused-code rules / SpotBugs UC_* |
| Rust | `rustfmt` | N/A (`rustc` inherent) | `clippy` (default groups; `pedantic` opt-in) | `cargo-deny` (supersedes `cargo-audit` on the advisory axis) | `jscpd` (jscpd-rs emerging, unproven) | `rustc`/clippy `dead_code` + `cargo-machete`(fast)/`cargo-udeps`(deep) for unused deps |
| Go | `goimports` | N/A (compiler inherent) | `golangci-lint` (errcheck/govet/ineffassign/staticcheck/unused defaults) | `gosec` (code patterns) + `govulncheck` (dependency CVEs — different scope, run both) | `dupl` (via golangci-lint) | `staticcheck unused` (+`x/tools/cmd/deadcode` for function-only, narrower) |

### Confirmed redundant-vs-complementary pairs (don't flag complementary pairs as duplication)

| Ecosystem | Pair | Relationship |
|---|---|---|
| Python | ruff `S` rules vs `bandit` | Overlapping — ruff S is a partial/stale port; bandit has 5 checks ruff lacks. Keep both: ruff S at edit-speed, bandit in CI for full coverage. |
| Python | ruff vs `vulture` | Complementary — ruff only catches locally-unused imports/vars; vulture does whole-project reachability. |
| Node/TS | `eslint-plugin-security` vs `semgrep` | Complementary — plugin is single-file/AST pattern match (fast, shallow); semgrep does cross-file taint (slower, deeper). Keep both. |
| Node/TS | `knip` vs `ts-prune` | Supersession, not complementary — `ts-prune` is unmaintained; knip is the strict superset. Don't run both. |
| Java | `checkstyle` vs `PMD` | Overlapping on style/naming, complementary elsewhere (PMD adds bug-pattern/design/security PMD-specific rules). Keep both. |
| Java | `PMD` vs `SpotBugs` | Complementary — PMD analyzes source pre-compile; SpotBugs analyzes compiled bytecode (different failure classes entirely). |
| Rust | `cargo-audit` vs `cargo-deny` | Redundant on the advisory axis once `cargo-deny` is adopted — cargo-deny's `check advisories` covers the same RustSec DB. Pick one (deny, if adopting its broader scope). |
| Rust | `cargo-machete` vs `cargo-udeps` | Complementary — machete is fast/narrow (text-scan, no compile, every-push gating); udeps is slow/wide (full nightly compile, periodic deep sweep). Keep both. |
| Go | standalone `staticcheck` vs `golangci-lint` (staticcheck enabled) | Fully redundant — golangci-lint bundles staticcheck verbatim. Don't run both. |
| Go | `gosec` vs `govulncheck` | Complementary — different scope entirely (code-pattern SAST vs. dependency-CVE reachability scanning). Keep both. |

### Fast-vs-slow ordering guidance (feeds the Makefile checker's advisory heuristic)

General pattern confirmed across every ecosystem researched: pure syntax/
AST-only tools (formatters, fast narrow linters) run first; anything
requiring a full compile pass, type-checking, or cross-file/taint analysis
runs last. Concretely: `rustfmt`/`gofmt`/`ruff format`/`prettier` first;
`cargo-machete`/`gosec`/ruff's default `check` next; full-type-analysis
passes (`cargo clippy`, `golangci-lint`'s "slow" tier, `mypy`, `tsc`) after
that; `cargo-udeps`/`govulncheck`/CI-grade SAST (`bandit`, `semgrep`) last,
since they're the slowest and often network- or compile-dependent.
golangci-lint's own `linters.default: fast` tier and documented Fast/Slow
linter classification is the most directly citable precedent for this
ordering philosophy, and is advisory guidance the Makefile checker's
baseline knowledge reuses directly — not a novel invention.

## Testing approach

- Each new skill gets the same unit-test shape as the existing `tests/
  test_ai_kit_agents_md_rules_checker.py`: synthetic target-repo fixtures
  (temp dirs with crafted Makefile/`.pre-commit-config.yaml`/
  `docker-compose.yml`/CI YAML content), asserting `check`/`remediate`
  output shape and specific finding detection/absence.
  `skills/_shared/ai_kit_rules_common/` gets its own test module for the
  classification engine and cache helpers, since multiple skills now depend
  on its correctness.
- `tests/test_arch.py`-style AST non-vacuity proof applies here too: for
  every new structural check (recipe-line-cap, healthcheck-timeout bounds,
  shellcheck-threshold), include a fixture that should trigger the finding
  and one that shouldn't, proving the check actually discriminates.
- Orchestrator gets an integration-style test that stubs all 6 checkers'
  `check` output and asserts the aggregation/ordering logic, without
  needing every individual checker's full logic re-exercised there.

## Open gap, explicitly flagged (not silently dropped)

No equally canonical dedicated architecture-fitness tool surfaced for Rust
or Go in research (unlike Python/import-linter, Node-TS/dependency-cruiser,
Java/ArchUnit). `ai-kit-project-rules-arch`'s baseline knowledge notes this
gap rather than asserting a false canonical recommendation for those two
languages; its scope (Makefile target shape + AST-only test-file check)
stays language-agnostic regardless, so the gap only affects the stack-
specific remediation-advice quality, not the core check.
