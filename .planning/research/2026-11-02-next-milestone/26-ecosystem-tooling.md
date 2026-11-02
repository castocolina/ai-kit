# Ecosystem tooling for the project rules skill

Researched 2026-11-02, about 25 minutes. Web sources are listed at the end. Where the only
source was a secondary blog or aggregator, the text says so. Nothing was installed.

## Bottom line

- Bake in the parts that hardly change: the category list, the stage each category runs at,
  the Makefile-as-single-source pattern, the official tool of each language (gofmt, rustfmt,
  clippy, `go vet`, `cargo test`, `go test`, javac/rustc as the type checker), architecture-test
  libraries that are over five years old (ArchUnit, import-linter, dependency-cruiser), and
  the Compose healthcheck and `depends_on` keys.
- Look up at invocation time, then cache: the "which fast linter" choices (Biome, Oxlint and
  ESLint; ty, pyright and mypy), anything owned by a vendor or recently forked (Trivy,
  Gitleaks/Betterleaks, tach), mutation tools, architecture tools younger than about two
  years (Konsist, cargo-pup, arch-go), and every pinned version or action SHA.
- 2026 showed why this split matters. Each of these happened this year and would make a
  baked default wrong:
  - TypeScript 7 shipped its Go-native compiler, without a stable programmatic API until 7.1.
  - Oxlint's type-aware rules went stable (tsgolint v7, July 2026).
  - ESLint 10 dropped the old eslintrc config, and ESLint 9 reached end of life on 2026-08-06.
  - OpenAI announced it is acquiring Astral (uv, ruff, ty).
  - Trivy's GitHub Actions were compromised in March 2026 (CVE-2026-33634; 76 of 77 tags
    repointed).
  - The creator of Gitleaks lost control of its repo and launched Betterleaks.
  - ty is still at 0.0.x (0.0.95 on 2026-10-29), even though a 1.0 was targeted for 2026.
  - detekt 2.0 is still in alpha.
- Two concrete gaps in ai-kit's own checkers came up along the way. Both are explained further
  down.
  - The docker checker does not know about `develop.watch` (Compose Watch).
  - `stack_detect` maps `build.gradle.kts` to `java`, so a Kotlin project gets Java tools.

## What already exists, and how to extend it rather than reinvent it

What is there today, in `skills/_shared/ai_kit_rules_common/`:

- `tool_catalog.py` has six categories in `TAXONOMY_CATEGORIES`: formatting, type-checking,
  linting, security, duplicate-code and dead-code.
  - `BASELINE_STACKS` holds a tuple of tool names for each of five stacks and each category.
  - `TOOL_CATEGORY_INDEX` is built from it, plus a short cited supplement.
  - `REDUNDANT_VS_COMPLEMENTARY_PAIRS` lists which tools overlap, replace or complement each
    other.
  - `OUT_OF_TAXONOMY_GROUPS` covers test runners and file-hygiene hooks.
  - `HOT_RELOAD_TOOLS` lists dev-server markers for each stack.
- `stack_cache.py` stores one JSON file per stack:
  - The path is `~/.cache/ai-kit/<namespace>/stack-refs/<stack>.json`.
  - The payload is `{cached_at, stack, tooling: {category: "text (source: ...)"}}`.
  - One global `STALE_AFTER_DAYS = 30` applies to every entry.
  - `validate_stack_payload(data, allowed_keys)` takes each skill's own key set and rejects
    any value that has no `(source: ...)` citation.
- The Makefile checker uses its own five-name `RESEARCH_CATEGORIES`, mapped to the six through
  `MAKEFILE_CATEGORY_ALIAS`.

Smallest extension that covers this research:

1. Add these categories to the vocabulary, as a second tuple next to the six. Keep it apart,
   because the six are "static analysis" by definition and the pre-commit classifier depends
   on that.
   - Static, so they could also join the six: dependency-audit, secrets-scan,
     architecture-test, dockerfile-lint, iac-lint and ci-workflow-lint.
   - Process, not static analysis: test-runner (already an out-of-taxonomy group), coverage
     and mutation-testing.
2. Give each category a stage hint as baked, uncached data: pre-commit, ci, pre-image or
   pre-deploy. The stage of a category barely moves, so it never needs research. The list is
   in the stage section below.
3. Add an expiry per category instead of the single 30-day value.
   - Today `read_stack_cache` checks staleness once for the whole file. The smallest change
     keeps that, and lets the consuming skill re-research a few listed fast-moving keys sooner
     (for example 14 days for security, dependency-audit and secrets-scan, which carry the
     supply-chain risk, and 90 days for formatting).
   - That needs one optional `stale_after_days` argument on `read_stack_cache`, or a
     category-to-days map checked by the consumer.
   - shortcut: one file-level timestamp means a key-level expiry re-researches the whole stack
     file, which is fine until the files get large.
4. Use a pseudo-stack id for tools that do not depend on the language: secrets scan,
   Dockerfile lint, IaC lint and CI workflow lint.
   - An id such as `cross-stack` already passes `_STACK_ID_RE`, so the cache format does not
     change.
5. Add markers to `stack_detect`:
   - `kotlin`: `build.gradle.kts` plus a `src/main/kotlin` directory or the
     `org.jetbrains.kotlin` plugin. Today `build.gradle.kts` means `java`, which is wrong for
     Kotlin-only projects. ktlint, detekt and Konsist do not apply to Java, and checkstyle and
     PMD do not cover Kotlin.
   - `dotnet`: `*.csproj` or `*.sln`. This needs a glob, and today's markers are exact
     filenames.
   - `php`: `composer.json`.
   - Keep `go.mod` and the rest as they are.

## Tools by ecosystem and category

Each tool has a tag:

- "bake" means a stable default the skill can name without a lookup.
- "research" means checking it at invocation time.
- "context" means it depends on the project (framework, monorepo, cloud).

Tags apply to the default choice, not to whether the tool exists.

### Python

- Formatter: `ruff format` (bake). Black is still valid where a project already uses it.
- Linter: `ruff check` (bake). pylint is slower and complementary; ai-kit uses it for the
  duplicate-code check `R0801` and for complexity budgets.
- Type checker: mypy or pyright (bake both as accepted). Pyrefly (Meta) and ty (Astral) are
  research items.
  - ty is still 0.0.x on 2026-10-29, so it is not a default yet. Re-check each invocation.
- Dead code: vulture (bake).
- Duplicate code: jscpd, or pylint `R0801` (bake, already in the catalog).
- Security / SAST: bandit, plus ruff's `S` rules for speed (bake). Semgrep is CI-only.
  - Semgrep's rules and licence terms have shifted (Opengrep fork, 2025), so mark it
    research.
- Dependency audit: pip-audit (PyPA, bake). osv-scanner v2 reads `uv.lock` (research, as the
  cross-language option).
- Test runner: pytest (bake). The standard-library `unittest` is valid, and ai-kit itself uses
  it.
- Coverage: coverage.py, or pytest-cov (bake).
- Mutation testing: mutmut (3.5.0 in February 2026, according to a secondary source) or
  cosmic-ray (research). Run them nightly or by hand, never on every commit.
- Architecture test: import-linter (bake). It is on 2.15 (2026-09-04) and has `layers`,
  `forbidden` and `independence` contracts.
  - tach is an option (research). The original `gauge-sh/tach` repo carries an "unmaintained"
    banner; the `tach-org/tach` fork is active (v0.35, May 2026, according to an aggregator).
  - A custom AST test, like ai-kit's own `tests/test_arch.py`, is the zero-dependency
    fallback.
- Ownership risk (research): ruff, uv and ty are now owned by OpenAI (deal announced
  2026-03-19). They are still open source and permissively licensed, so they stay the
  defaults. The skill should re-check their status each time it researches Python, not
  assume it.

### Node / TypeScript

- Formatter: prettier or `biome format` (bake both, already in the catalog). dprint is
  context.
- Linter: eslint with typescript-eslint (bake as the reference for type-aware rules).
  - ESLint 10 accepts only the flat config (`eslint.config.*`), and v9 reached end of life
    on 2026-08-06. The skill should flag any `.eslintrc*` file it finds. That is a stable fact
    worth baking.
  - Biome 2 (its own type inference, not complete) and Oxlint are research items.
    Oxlint's type-aware rules went stable in July 2026 through tsgolint v7: 59 of the 61
    typescript-eslint type-aware rules, per the vendor.
  - A common mature split runs Oxlint or Biome in pre-commit and ESLint for the type-aware
    rules in CI.
- Type checker: `tsc --noEmit` (bake).
  - TypeScript 7 is the Go-native compiler (released July 2026), and its programmatic API is
    not stable until 7.1. Tools built on the TS API may pin `@typescript/typescript6` (the
    `tsc6` binary) for a while (research).
- Dead code: knip (bake). ts-prune is unmaintained (already a supersession row in the
  catalog).
- Duplicate code: jscpd (bake).
- Security / SAST: eslint-plugin-security (bake) plus semgrep in CI (research).
- Dependency audit: `npm audit`, `pnpm audit` or `yarn npm audit`, whichever package manager
  the lockfile shows (bake the mapping). osv-scanner is research.
- Test runner: vitest or jest (bake both), or node's built-in `node --test`. Playwright for
  end-to-end tests is context.
- Coverage: the runner's built-in coverage (`vitest --coverage` with v8, or `jest --coverage`)
  (bake).
- Mutation testing: StrykerJS (bake as the only mature option; versions are research).
- Architecture test: dependency-cruiser (bake).
  - Alternatives: `eslint-plugin-boundaries`, `import/no-restricted-paths`, and Nx
    `enforce-module-boundaries` in Nx monorepos (context).

### Go

- Formatter: gofmt or goimports (bake). golangci-lint v2 also has `golangci-lint fmt`
  (gofumpt and gci are opt-in).
- Linter: golangci-lint v2 (bake).
  - The v2 config format differs from v1: `linters.default`, and `linters.settings` instead of
    `linters-settings`.
  - `golangci-lint migrate` converts a v1 config. The skill should flag a v1 config as stale,
    which is a baked fact.
  - `go vet` is built in.
- Type checker: the compiler (bake, an empty entry in the catalog).
- Dead code: staticcheck's `unused` check, through golangci-lint (bake).
  `golang.org/x/tools/cmd/deadcode` is a narrower, whole-program option.
- Duplicate code: dupl, through golangci-lint (bake).
- Security / SAST: gosec (bake).
- Dependency audit: govulncheck (bake). It is the official tool and checks whether the
  vulnerable code is actually reachable.
- Test runner: `go test ./...` with `-race` in CI (bake).
- Coverage: `go test -coverprofile`, with `-coverpkg` (bake).
- Mutation testing: research. There is no dominant tool (go-mutesting forks, gremlins).
- Architecture test:
  - The `internal/` directory rule is enforced by the compiler (bake).
  - depguard, inside golangci-lint, can deny imports for each file glob (bake). It runs in
    the linter you already have, so it needs no new tool.
  - go-arch-lint or arch-go for declared layers (research).

### Java (Maven / Gradle)

- Formatter: Spotless, which drives google-java-format or palantir-java-format (bake).
- Linter: Checkstyle plus PMD (bake). Error Prone with NullAway is a strong, context-dependent
  addition, because it is a compiler plugin.
- Type checker: javac (bake, empty entry).
- Dead code: PMD's unused-code rules, or SpotBugs `UC_*` (bake).
- Duplicate code: PMD CPD (bake).
- Security / SAST: SpotBugs plus find-sec-bugs (bake). Semgrep or CodeQL in CI (research).
- Dependency audit: OWASP dependency-check (Maven and Gradle plugins). It is slow and needs
  an NVD API key, so it is CI-only (research). osv-scanner v2 does guided remediation for
  Maven (research).
- Test runner: JUnit 5 through Surefire/Failsafe or Gradle `test` (bake).
- Coverage: JaCoCo (bake).
- Mutation testing: PIT, also called pitest (bake as the only mature option). It is slow, so
  run it nightly or on changed classes only.
- Architecture test: ArchUnit (bake).
  - Spring Modulith's `ApplicationModules.verify()` is context (Spring projects).
  - Gradle or Maven multi-module builds, and JPMS `module-info.java`, enforce direction at
    compile time (bake as the strongest option where the project already has modules).

### Kotlin (Gradle)

This needs its own stack id. See "Smallest extension" above.

- Formatter: ktlint, or ktfmt through Spotless (bake).
- Linter: detekt (bake as the tool). Which version is research: detekt 2.0 is still in alpha
  (2.0.0-alpha.5, 2026-06-17), so 1.23.x is the stable line.
- Type checker: kotlinc (bake, empty entry).
- Dead code: detekt's unused rules (bake). There is no strong dedicated tool.
- Duplicate code: PMD CPD supports Kotlin (bake).
- Security / SAST: semgrep or CodeQL (research). find-sec-bugs works on the bytecode.
- Dependency audit: the same as Java.
- Test runner: JUnit 5 or Kotest (bake).
- Coverage: Kover or JaCoCo (bake).
- Mutation testing: PIT with the Kotlin plugin (research).
- Architecture test: Konsist (research, version numbers vary by source; 0.17 is the latest
  seen). ArchUnit works on the bytecode but needs custom predicates for Kotlin constructs.

### Rust

- Formatter: rustfmt (bake).
- Linter: clippy, with `-D warnings` in CI (bake).
- Type checker: rustc (bake, empty entry).
- Dead code: rustc and clippy `dead_code`, plus cargo-machete (fast) and cargo-udeps (deep,
  needs nightly) (bake, already in the catalog).
- Duplicate code: jscpd (bake, weak for Rust).
- Security / SAST: cargo-deny (bake). There is no mainstream Rust SAST tool; clippy plus
  `#![forbid(unsafe_code)]` is the usual practice.
- Dependency audit: `cargo deny check advisories`, or cargo-audit (bake, a redundant pair in
  the catalog).
- Test runner: `cargo test`, or cargo-nextest for speed (bake both).
- Coverage: cargo-llvm-cov (bake). cargo-tarpaulin is valid but Linux-centred.
- Mutation testing: cargo-mutants (bake as the only mature option; versions are research).
- Architecture test:
  - Splitting into workspace crates is enforced by the compiler (bake as the main answer):
    a crate can use only what its `Cargo.toml` declares.
  - cargo-deny `[bans]` with `wrappers` can say "only crate X may depend on crate Y"
    (bake, from official docs).
  - Rules inside one crate: cargo-pup from Datadog (0.1.x, young, research).
  - cargo-modules only draws the graph and enforces nothing.

### .NET and PHP (one line each)

- .NET: `dotnet format`, Roslyn analyzers with `TreatWarningsAsErrors`, nullable reference
  types, `dotnet list package --vulnerable`, xUnit or NUnit with coverlet, Stryker.NET,
  NetArchTest or ArchUnitNET. All research; this was not verified in this pass.
- PHP: PHP-CS-Fixer or Laravel Pint, PHPStan or Psalm, `composer audit`, PHPUnit or Pest,
  Infection (mutation), and Deptrac, PHPArkitect or Pest `arch()` for layers. All research;
  this was not verified in this pass.

### Cross-stack (pseudo-stack `cross-stack`)

- Secrets scan: gitleaks, or Betterleaks (research).
  - Betterleaks is from the original Gitleaks author, who lost admin control of the Gitleaks
    repo. It claims to be a drop-in replacement (v1.3.1 in May 2026).
  - trufflehog is the verify-against-live-API option for CI.
  - The `detect-private-key` hook is the zero-cost minimum (already a hygiene marker).
- Dockerfile lint: hadolint (bake; still released, v2.15.1 in August 2026) plus
  `docker build --check` (bake; built into BuildKit, needs Buildx 0.15 or later and Dockerfile
  syntax 1.8 or later).
  - `docker build --check` only warns unless `# check=error=true` is set.
  - The two overlap partly, so keep both: hadolint in pre-commit, `--check` before the image
    build.
- IaC lint: research, because it depends on the cloud and the tool.
  - Terraform: `terraform fmt`, `terraform validate` and tflint. tfsec has been folded into
    Trivy.
  - Policy: checkov or Trivy config.
  - Kubernetes: kubeconform, kube-linter.
  - Compose: `docker compose config -q`.
- Image or container vulnerability scan: Trivy, Grype or osv-scanner (research).
  - The Trivy action compromise means "pin by SHA" is mandatory, not a style choice.
- CI workflow lint (bake as a category, tools are research):
  - actionlint for GitHub Actions syntax.
  - zizmor for Actions security.
  - pinact, or GitHub's own "require SHA pinning" policy (August 2025; checked at run time,
    not at PR time).
  - GitLab has `glab ci lint`, or the CI Lint API.

## Which stage each category belongs to

Bake this list. It is the part that does not go stale.

- Pre-commit: fast, runs on staged files, aim for under 5 seconds total.
  - Formatter, linter on staged files, secrets scan on the staged diff, file hygiene,
    hadolint, and `tflint` or `terraform fmt -check` on changed files.
  - Run type checking here only if it is incremental and fast: pyright or mypy daemon on a
    small repo, `tsc` with TS 7.
  - Tools that need a whole-project view are wrong here, because they produce false results on
    a partial file set: vulture, knip, dependency-cruiser on a full graph, govulncheck, and
    import-linter on a large repo.
  - Pre-push is the place for "fast but whole-project". The Makefile checker already checks
    the pre-commit/pre-push split.
- CI: full run, every change.
  - Everything above on all files, plus the type checker, dead code, duplicate code, SAST,
    dependency audit, the unit and integration tests with coverage, the architecture test and
    CI workflow lint.
  - Mature projects run `pre-commit run --all-files` (or prek, or `make validate`) here, so
    the hooks are defined once.
- Before an image build: Dockerfile lint (hadolint, plus `docker build --check` with
  `check=error=true`), the full test suite on the commit being built, and the lockfile/licence
  checks that decide what goes into the image (`cargo deny check bans licenses`).
- Before a deploy:
  - An image vulnerability scan of the built digest (not of the source).
  - IaC policy checks (checkov, Trivy config, kube-linter) on the manifests that will be
    applied.
  - End-to-end or smoke tests against a staging environment.
  - Signature or provenance checks where the project uses them (cosign, SLSA; context).
- Nightly or by hand:
  - Mutation testing.
  - Deep dead-dependency sweeps (cargo-udeps).
  - OWASP dependency-check, which is too slow for every push.
  - A full semgrep or CodeQL scan if the per-change one is diff-only.

How mature projects avoid defining things twice:

- Pattern A, the hook config as the source:
  - `.pre-commit-config.yaml` pins the tool versions.
  - CI runs `pre-commit run --all-files` (or `prek run --all-files`).
  - A `make validate` target wraps that same command.
  - This works best when the tools are fetched hook repos.
- Pattern B, Makefile targets as the source:
  - Each tool gets a `make <tool>` target.
  - Hooks are `language: system` entries that call those targets (or call the tool with the
    same arguments).
  - CI calls `make validate` and `make test`.
  - This works best when a lockfile (uv.lock, package-lock, go.mod tool directives, Gradle)
    already pins the tools.
  - ai-kit uses this pattern; the cicd checker flags CI steps that bypass it.
- prek, the Rust rewrite of pre-commit (0.4.11, July 2026, "Production/Stable" classifier,
  adopted by Airflow, ty and others according to its own docs), reads the same config. The
  skill should accept either binary and never require one (research).

## Architecture tests: how each ecosystem says "who may depend on whom"

Every rule below says the same thing: the domain layer must not depend on infrastructure, and
higher layers may use lower ones. Each example is minimal and comes from official docs or the
tool's README, unless it says otherwise.

### Python, import-linter (`pyproject.toml`)

```toml
[tool.importlinter]
root_package = "myapp"

[[tool.importlinter.contracts]]
name = "Layers"
type = "layers"            # higher entries may import lower, never the reverse
layers = ["myapp.api", "myapp.service", "myapp.domain"]
```

Run it with `lint-imports`. Use `type = "forbidden"` for one-off bans such as "domain must
not import sqlalchemy".

### Node / TypeScript, dependency-cruiser (`.dependency-cruiser.cjs`)

```js
module.exports = {
  forbidden: [
    { name: "domain-not-to-infra", severity: "error",
      from: { path: "^src/domain" }, to: { path: "^src/infra" } },
  ],
};
```

Run it with `depcruise src`.

### Go, depguard inside golangci-lint v2 (`.golangci.yml`)

```yaml
version: "2"
linters:
  enable: [depguard]
  settings:
    depguard:
      rules:
        domain:
          files: ["**/internal/domain/**"]
          deny:
            - pkg: "example.com/app/internal/infra"
              desc: "domain must not depend on infra"
```

Alternatively, arch-go's `arch-go.yml` uses `dependenciesRules: [{package: "**.domain.**",
shouldNotDependsOn: {internal: ["**.infra.**"]}}]`. The exact key shape changed between arch-go
versions, so treat it as research. The project also moved from `fdaines/arch-go` to
`arch-go/arch-go`.

### Java, ArchUnit (JUnit 5)

```java
@AnalyzeClasses(packages = "com.example")
class ArchTest {
  @ArchTest
  static final ArchRule layers = layeredArchitecture().consideringAllDependencies()
      .layer("Web").definedBy("..web..")
      .layer("Service").definedBy("..service..")
      .layer("Persistence").definedBy("..persistence..")
      .whereLayer("Web").mayNotBeAccessedByAnyLayer()
      .whereLayer("Service").mayOnlyBeAccessedByLayers("Web")
      .whereLayer("Persistence").mayOnlyBeAccessedByLayers("Service");
}
```

### Kotlin, Konsist

The API was checked against secondary sources only; 0.17 changed how layers are declared.

```kotlin
@Test fun layers() = Konsist.scopeFromProduction().assertArchitecture {
  val domain = Layer("Domain", "com.example.domain..")
  val data = Layer("Data", "com.example.data..")
  domain.dependsOnNothing()
  data.dependsOn(domain)
}
```

### Rust, crate split plus cargo-deny (`deny.toml`)

```toml
# app-infra may only be used directly by the binary crate
[bans]
deny = [{ crate = "app-infra", wrappers = ["app-bin"] }]
```

Not verified: whether `bans` applies to workspace path crates the same way it does to
registry crates. Test it on a sample workspace before baking it. The crate split itself is
enforced by the compiler with no tool at all.

### .NET and PHP (not verified)

- .NET, NetArchTest:
  `Types.InAssembly(a).That().ResideInNamespace("App.Domain").ShouldNot().HaveDependencyOn("App.Infra")`.
- PHP: a Deptrac `deptrac.yaml` with `layers` and a `ruleset`, or Pest:
  `arch()->expect('App\Domain')->not->toUse('App\Infra')`.

### The baked fallback

The fallback that never goes stale is ai-kit's own approach: a structural test written with
`ast`, or an equivalent parser, that never imports the module it checks. The arch checker
already checks for exactly that shape.

## CI and local-dev patterns that cut across ecosystems

### GitHub Actions (stable, bake the shape)

- One `checks` job runs `make validate` and `make test`. An `image` job has
  `needs: [checks]`. A `deploy` job has `needs: [image]`, runs
  `if: github.ref == 'refs/heads/main'`, and uses `environment: production`, so the
  environment's required reviewers and protection rules gate it.
- `concurrency: {group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true}`
  cancels stale runs.
- Reuse, across repos: a reusable workflow (`on: workflow_call`) or a composite action. Inside
  a repo, the Makefile is the reuse layer, so the YAML stays thin.
- Caching:
  - The language setup actions have built-in caches: `setup-python` with `cache: pip`,
    `astral-sh/setup-uv` with `enable-cache`, `setup-node` with `cache: pnpm`, `setup-go`
    (caches by default), `gradle/actions/setup-gradle`, and `Swatinem/rust-cache`.
  - Cache the pre-commit or prek cache directory, keyed on the hash of
    `.pre-commit-config.yaml`.
  - Docker layers: `docker/build-push-action` with `cache-from/cache-to: type=gha`.
- Security, baked as a fact after the Trivy incident:
  - Pin every third-party action by full commit SHA, with a version comment.
  - Set minimal `permissions:` per job.
  - Lint the workflows with actionlint and zizmor.

### GitLab CI (stable, bake the shape)

- Use `stages:`, plus `needs:` for a dependency graph that skips stage barriers.
- Use `rules: - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH` for main-only jobs, and set
  `interruptible: true` on check jobs.
- Deploy:
  - Use `environment: {name: production}` on a protected environment.
  - Add `when: manual` where a person approves the release.
  - `needs:` on the image job and the scan job.
- Reuse:
  - `extends:` and `!reference` inside a repo.
  - Across repos, CI/CD components through `include: - component:
    $CI_SERVER_FQDN/group/proj/name@1.2.3` with typed `spec:inputs`.
  - Official guidance: pin to a SHA or a semantic version. Never `~latest` or a branch.
  - A component must be self-contained (no `spec:include`), and job names can collide when
    its config merges into the pipeline.
- Caching: `cache: {key: {files: [uv.lock]}, paths: [.venv/]}` (or a lockfile per language).
  Use `artifacts:` to pass build outputs between jobs.
- Image build: buildx with a registry cache (`--cache-to type=registry`).
  - Kaniko was archived upstream by Google in 2025 (from memory, verify). Chainguard maintains
    a fork. Research which builder to use.

### Docker local dev (stable, bake)

- Healthcheck:
  - Compose keys: `test`, `interval`, `timeout`, `retries`, `start_period`, and
    `start_interval`. The duration keys are documented for Compose 2.20.2 or later.
    `start_interval` also needs Docker Engine 25 or later (from memory, verify).
  - The docker checker's limits (timeout 2s or less, start_period 10s or less, interval 5s or
    less) fit, and `start_interval: 1s` makes startup checks fast without spamming checks
    later.
- `depends_on: {db: {condition: service_healthy}}` is already checked. Also accepted:
  `service_completed_successfully` (for migration and seed jobs), `restart: true` (Compose
  2.17 or later) and `required: false` (Compose 2.20 or later).
- Hot reload has two accepted shapes:
  1. A bind mount plus a reload command (`uvicorn --reload`, `vite`, `air`, `cargo watch`).
     This is what the docker checker accepts today.
  2. Compose Watch: `develop.watch` with `action: sync | rebuild | sync+restart`, run with
     `docker compose up --watch` or `docker compose watch`. It works only on services that
     have `build:`, and the image needs `stat`, `mkdir` and `rmdir`. Newer Compose versions
     also have `sync+exec`, which was not on the fetched page (verify).
- Gap: `skills/ai-kit-project-rules-docker` has no reference to `develop` or `watch`. A
  service that uses Compose Watch instead of a bind mount would likely be reported as
  "no hot reload" by mistake. This is the most concrete follow-up from this research. Accept
  a `develop.watch` block with a `sync*` or `rebuild` action as a valid hot-reload shape.

## What to bake, and what to research at invocation time

### Bake

These change on the scale of years, or are official language tools:

- The category vocabulary, the stage for each category, and the redundant and complementary
  pairs.
- The official tools: gofmt, `go vet`, govulncheck, `go test -race`, rustfmt, clippy,
  `cargo test`, cargo-deny, cargo-llvm-cov, `tsc`, pip-audit, coverage.py, JaCoCo, the JUnit
  runners.
- Long-standing third-party tools: ruff, mypy, pyright, pytest, vulture, bandit,
  import-linter, prettier, eslint (flat config), typescript-eslint, knip, jscpd,
  dependency-cruiser, StrykerJS, golangci-lint v2, Spotless, Checkstyle, PMD, SpotBugs,
  find-sec-bugs, PIT, ArchUnit, ktlint, cargo-mutants, hadolint, `docker build --check`,
  actionlint.
- Structural facts:
  - ESLint 10 is flat-config only.
  - golangci-lint v1 configs need `migrate`.
  - Go `internal/` and Rust crate splits are compiler-enforced layers.
  - Pin CI actions or components by SHA.
  - The Compose healthcheck and `depends_on` keys.
  - Compose Watch only works with `build:`.

### Research at invocation time, cached per stack, with these suggested expiries

- 14 days, for supply-chain-sensitive items:
  - The image, IaC and secrets scanners (Trivy, Grype, Betterleaks or gitleaks, trufflehog,
    checkov).
  - Semgrep or Opengrep.
  - The SHA or version for any action or hook the skill would write.
  - Recent history shows these change ownership or get compromised within weeks.
- 30 days, the current default:
  - The fast linter choice (Oxlint, Biome or ESLint; whether ty is ready).
  - The TypeScript 7 API status.
  - detekt 2.0 status, Konsist, arch-go or go-arch-lint, tach, cargo-pup.
  - Go mutation tools.
  - osv-scanner coverage.
  - Every .NET and PHP entry.
- 90 days: formatter versions and test-runner versions. The choice is stable; only the pin
  moves.

Never research these; read them from the target repo: which package manager (from the
lockfile), which framework (from the dependencies), whether the repo is a monorepo, and which
cloud or IaC tool. These are "context" facts. The cache rule that every value carries a
`(source: ...)` citation already fits research results. Context facts should carry
`(source: <repo file>)` instead.

## Open questions for the next phase's researcher

- Confirm whether cargo-deny `bans` with `wrappers` applies to workspace path crates.
- Confirm arch-go's current `dependenciesRules` key shape.
- Confirm when Compose added `sync+exec`, and the minimum Docker Engine version for
  `start_interval`.
- Confirm Kaniko's archive status and the maintained fork.
- Check whether `stack_detect` should glob for `*.csproj` (today it only checks exact marker
  filenames).

## Sources

- ty: [releases](https://github.com/astral-sh/ty/releases), [beta, InfoWorld](https://www.infoworld.com/article/4108979/python-type-checker-ty-now-in-beta.html), [pydevtools handbook](https://pydevtools.com/handbook/topics/ty/)
- Astral acquisition: [Simon Willison](https://simonwillison.net/2026/Mar/19/openai-acquiring-astral/), [SiliconANGLE](https://siliconangle.com/2026/03/19/openai-acquires-open-source-python-tooling-startup-astral/)
- [import-linter on PyPI](https://pypi.org/project/import-linter/); tach: [tach-org/tach](https://github.com/tach-org/tach) (maintenance status from an aggregator)
- Python mutation: [pytest-gremlins comparison](https://pytest-gremlins.readthedocs.io/en/latest/guide/comparison/) (a vendor page; treat with caution)
- Oxlint type-aware stable: [Oxc blog 2026-07-22](https://oxc.rs/blog/2026-07-22-type-aware-linting-stable), [InfoQ](https://infoq.com/news/2026/09/tsgolint-oxlint-typescript)
- Biome, Oxlint and ESLint comparison: [pkgpulse](https://www.pkgpulse.com/guides/biome-vs-eslint-vs-oxlint-2026) (secondary)
- TypeScript 7: [InfoWorld](https://www.infoworld.com/article/4196378/go-based-typescript-7-0-arrives.html), [InfoQ](https://infoq.com/news/2026/08/typescript-7-released/)
- ESLint 10: [InfoQ](https://infoq.com/news/2026/04/eslint-10-release), [ESLint blog](https://eslint.org/blog/2025/11/eslint-v10.0.0-alpha.0-released/)
- golangci-lint v2: [v2 announcement mirror](https://scriptagc.wasmer.app/https_ldez_github_io/blog/2025/03/23/golangci-lint-v2), [linter settings](https://golangci-lint.run/docs/linters/configuration/)
- arch-go: [pkg.go.dev](https://pkg.go.dev/github.com/arch-go/arch-go)
- detekt 2.0: [changelog](https://detekt.dev/changelog-2.0.0/); [Konsist](https://github.com/LemonAppDev/konsist)
- cargo-deny bans: [docs](https://embarkstudios.github.io/cargo-deny/checks/bans/cfg.html); cargo-pup: [docs.rs](https://docs.rs/crate/cargo_pup_lint_impl/latest/source/README.md)
- [osv-scanner v2](https://blog.google/security/announcing-osv-scanner-v2-vulnerability/)
- Trivy compromise: [Phoenix Security](https://phoenix.security/trivy-supply-chain-attack-team-pcp/), [NHS cyber alert](https://nhsd-proxy.openprescribing.net/cyber-alerts/2026/cc-4758)
- Betterleaks: [BleepingComputer](https://bleepingcomputer.com/news/security/betterleaks-a-new-open-source-secrets-scanner-to-replace-gitleaks), [The New Stack](https://thenewstack.io/betterleaks-open-source-secret-scanner/)
- prek: [docs](https://prek.j178.dev/), [PyPI mirror](https://simple-repository.app.cern.ch/project/prek)
- hadolint activity: [hadolint-action bump PR](https://github.com/TomerFi/switcher_webapi/pull/1072) (secondary signal)
- [Docker build checks](https://docs.docker.com/build/checks/)
- [Compose file watch](https://docs.docker.com/compose/how-tos/file-watch/), [Compose healthcheck and depends_on](https://docs.docker.com/reference/compose-file/services/#healthcheck)
- [GitLab CI/CD components](https://docs.gitlab.com/ci/components/)
- [GitHub Actions SHA-pinning policy](https://github.blog/changelog/2025-08-15-github-actions-policy-now-supports-blocking-and-sha-pinning-actions/)
