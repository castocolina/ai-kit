---
name: ai-kit-project-rules-cicd
description: Use when a target repo's CI config (`.github/workflows/*.yml` or `.gitlab-ci.yml`) needs checking for direct tool invocations that duplicate a command already defined in a Makefile target, a pre-commit hook, a `package.json` script, or a Gradle build task -- or when asked "does my CI call ruff directly instead of make ruff", "is my pipeline duplicating a pre-commit hook", or "why is this CI step flagged for reuse". Routes apart from `ai-kit-project-rules-makefile`, which judges a Makefile's own target shape, and `ai-kit-project-rules-precommit`, which judges Makefile-versus-pre-commit-hook parity: this skill reads both files too, but only as a command-vocabulary of what already exists, and never reports on either file's own quality. Detects and reports only; never edits the target repo.
---

# ai-kit-project-rules-cicd

## Scope

This skill DETECTS AND REPORTS a repo's CI config duplicating a command that a Makefile target,
a pre-commit hook, a `package.json` script, or a Gradle build task already defines. It never
edits the target repo's CI file, Makefile, `.pre-commit-config.yaml`, `package.json`, or Gradle
build script; never runs a CI job; never executes, shell-expands, or interpolates any command it
reads; and never fetches a referenced GitHub Action or a GitLab `include:`d file. Applying a fix
is a decision for whoever invoked this skill.

Two neighbouring skills also have an opinion about the two files this skill reads most --
`Makefile` and `.pre-commit-config.yaml` -- and a reader who cannot tell the three apart will
invoke the wrong one for a CI-reuse question:

- `ai-kit-project-rules-makefile` judges a Makefile's OWN target shape: the
  `validate-<category>` alias chain, recipe length, the Docker build-before-up convention. It
  never looks at a CI file.
- `ai-kit-project-rules-precommit` judges Makefile-VERSUS-pre-commit-hook PARITY: whether every
  hook id has a matching Makefile target and vice versa. It never looks at a CI file either.
- This skill reads the SAME two files, but only as a command-vocabulary of what already exists
  in the repo -- a Makefile target's recipe or a hook's `entry:` is read purely to learn what
  command it runs, never to judge whether the target or the hook itself is well-formed. A
  Makefile-shape question or a Makefile/hook-parity question is not this skill's business; a
  "does my CI duplicate a command I already have" question is.

Auditing an AGENTS.md/CLAUDE.md-style agent-instruction file, architecture-fitness conventions,
and local-dev Docker Compose conventions belong to the other three sibling skills, not this one.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path as a literal absolute
path:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-project-rules-cicd}" \
         "$HOME/.claude/skills/ai-kit-project-rules-cicd" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-project-rules-cicd" \
         "$HOME/.agents/skills/ai-kit-project-rules-cicd" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-project-rules-cicd.py" ] && { printf '%s\n' "$d/ai-kit-project-rules-cicd.py"; break; }
done
```

If no candidate exists, stop and report that the skill is not installed. The fifth candidate
covers a from-checkout invocation -- substitute the directory actually containing this
`SKILL.md`.

Only the `$HOME/.claude/skills/...` symlink install (`tools/setup.py`) and a direct git checkout
can actually import this skill: those layouts keep `skills/_shared/` beside the skill package.
The other three candidates (`$CLAUDE_PLUGIN_ROOT`, opencode's skills dir, `~/.agents/skills`)
raise `ImportError` at import time by design -- they are copy-installs that do not carry
`skills/_shared/`. A successful path lookup is not proof the import will succeed; prefer the
symlink or a checkout.

## The applicability gate comes first

Before anything else: this skill evaluates a repo only when root-level CI evidence exists -- a
root `.gitlab-ci.yml`/`.gitlab-ci.yaml`, OR a root `.github/workflows/` directory containing at
least one entry whose name ends in `.yml`/`.yaml`. Both clauses are root-scoped:
`os.path.isfile`/`os.path.isdir` against explicitly-joined paths, plus one non-recursive
`os.listdir` of the workflows directory -- no walk, no descending glob. A repo with no root CI
config gets `{"cicd": []}`, and that is the correct answer, not a failure to run.

## Run the check

```bash
python3 "$ENTRYPOINT" check <repo_root>
python3 "$ENTRYPOINT" remediate <repo_root>
```

`check` returns a single key: `{"cicd": [...]}` -- every finding this skill emits, sorted by
criticality. A real run against a fixture repo (a Makefile `ruff` target beside a `.gitlab-ci.yml`
job running `ruff check .` directly):

```json
{
  "cicd": [
    {
      "category": "cicd-command-reuse",
      "issue": "ci_duplicates_existing_command",
      "criticality": 3,
      "summary": "CI job 'lint' in .gitlab-ci.yml runs 'ruff check .' directly, duplicating the existing 'make ruff' command -- call 'make ruff' instead of running 'ruff check .' directly.",
      "recommendation": "CI job 'lint' in .gitlab-ci.yml runs 'ruff check .' directly, duplicating the existing 'make ruff' command -- call 'make ruff' instead of running 'ruff check .' directly.",
      "needs_research": false,
      "ci_file": ".gitlab-ci.yml",
      "job": "lint",
      "command": "ruff check .",
      "tool": "ruff check",
      "reuse_surface": "makefile",
      "reuse_command": "make ruff"
    }
  ]
}
```

`remediate` runs `check` internally and returns the shared builder's two-key payload:
`{"remediate": [...ordered, most-critical-first...], "blocked": [...]}`. This skill's findings
never populate `blocked`, because nothing it emits carries `needs_research` -- its baseline
knowledge is entirely hardcoded (see below). Every `remediate` entry carries `auto_apply`,
always `True` for this skill's one finding category -- confirmed against a real run over the
same fixture:

```json
{
  "remediate": [
    {"kind": "cicd", "id": "cicd-command-reuse", "issue": "ci_duplicates_existing_command",
     "criticality": 3, "summary": "...", "auto_apply": true}
  ],
  "blocked": []
}
```

`python3 "$ENTRYPOINT" bogus <repo_root>` exits `2` and prints `unknown subcommand: bogus` --
confirmed against a real run.

A fixture whose CI already calls the reuse command directly (the same `.gitlab-ci.yml` job now
running `make ruff` instead of `ruff check .`) produces `{"cicd": []}` -- confirmed against a
real run.

This skill has exactly two subcommands, `check` and `remediate` -- unlike the Phase 10
(`ai-kit-project-rules-makefile`) and Phase 11 (`ai-kit-project-rules-precommit`) siblings, there
is no third, research-triggering command behind either one. There is no research step and no
per-stack cache: this skill's baseline knowledge -- the tool catalog's role in the identity gate,
the package-manager lockfile precedence, and the Gradle plugin table -- is written directly into
its source and does not need refreshing the way the Phase 10/11 siblings' per-stack tooling does.

## What it checks

One finding category, `cicd-command-reuse` (issue `ci_duplicates_existing_command`, criticality
MEDIUM), across four reuse surfaces, each with its own recommendation form:

1. **Makefile target** -- `make <target-name>`. A CI command whose key matches a Makefile
   target's identity (the target's own recipe, reduced to a command key) is flagged, recommending
   that target.
2. **Pre-commit hook** -- `pre-commit run <hook-id> --all-files`. A CI command matching a hook's
   `entry:` (or, for an upstream hook with no `entry:`, the hook id itself when catalog-known) is
   flagged, recommending that hook by its real id.
3. **`package.json` script** -- `<runner> run <script-name>`, where `<runner>` is resolved from
   the repo's lockfile (`pnpm`/`yarn`/`bun`/`npm`, in that precedence). A CI command matching a
   root `scripts` entry's command is flagged, recommending that script.
4. **Gradle build task** -- `./gradlew <task-name>` when a root `gradlew` wrapper exists,
   `gradle <task-name>` otherwise. A CI command matching a declared task name, or a task the
   pinned plugin table contributes given real plugin-id evidence in the build script, is flagged.

When the same command key exists across more than one surface, exactly one finding is produced,
naming the FIRST surface in the fixed order `makefile`, `precommit`, `package-json`, `gradle` --
never all of them, and never the losing alternative.

`check_cicd_rules` degrades rather than crashes: an absent Makefile, `.pre-commit-config.yaml`,
`package.json`, or Gradle build script simply contributes no reuse sources from that surface, and
an unreadable one degrades the same way.

## Hardcoded Baseline Knowledge

This skill's knowledge is entirely hardcoded -- no research is needed to apply it, and there is
no per-stack cache to keep current:

- **The tool catalog's role in the identity gate.** An identity is usable only when the shared
  `ai_kit_rules_common.tool_catalog` resolves it to a category, it is an out-of-taxonomy marker
  (a test runner or a pre-commit-hygiene tool the catalog deliberately excludes), or it was
  derived from a real command body and normalizes to the same name as its own source (closed to a
  bare name declaration with no command body behind it).
- **The package-manager lockfile precedence (D-C18b)**: the FIRST of these lockfiles present at
  the repo root decides the recommended runner -- `pnpm-lock.yaml` -> `pnpm`; `yarn.lock` ->
  `yarn`; `bun.lockb` or `bun.lock` -> `bun`; otherwise `npm`.
- **The pinned Gradle plugin table**, row by row -- a task name is admitted through this route
  only when its plugin-id fragment is real text evidence in the build script:

  | Task name | Plugin-id fragment | Tool identity |
  |---|---|---|
  | `spotlessCheck` | `com.diffplug.spotless` | `spotless` |
  | `spotlessApply` | `com.diffplug.spotless` | `spotless` |
  | `checkstyleMain` | `checkstyle` | `checkstyle` |
  | `pmdMain` | `pmd` | `PMD` |
  | `spotbugsMain` | `spotbugs` | `SpotBugs` |
  | `detekt` | `io.gitlab.arturbosch.detekt` | `detekt` |
  | `ktlintCheck` | `org.jlleitschuh.gradle.ktlint` | `ktlint` |
  | `dependencyCheckAnalyze` | `org.owasp.dependencycheck` | `dependency-check` |

  This table is transcribed baseline knowledge and is expected to go stale as new plugins and
  taxonomies appear -- a build script applying a plugin outside this table contributes nothing
  through this route (see Limits below).

## Limits

Eleven places this skill knows less than it might appear to, stated here rather than left to be
discovered, in one scannable section, per this family's own lesson that a document stating what
it cannot do is more useful than one implying it can do everything. Each is its own standalone
sentence a reader can act on.

1. **The applicability gate is root-scoped, and CI platforms outside GitLab CI and GitHub Actions
   are ignored entirely.** A repo using CircleCI, Jenkins, Azure Pipelines, Travis, or any other
   CI platform gets an empty report, not a warning that it was skipped.
2. **The CI readers are text readers, not a YAML implementation.** Both the GitLab CI and GitHub
   Actions readers are stdlib-only, indentation-aware text scans, never a YAML library. A
   tab-indented file (YAML forbids tabs) may have a block mis-attributed rather than raise, and
   anchors, aliases, merge keys, and GitLab's `!reference` are never resolved -- a command site
   using one may be read incompletely.
3. **A `uses:` step's action, and a `jobs.<id>.uses` reusable workflow, are never fetched.** A
   tool invoked inside a third-party or composite GitHub Action, or inside a called reusable
   workflow, is invisible to this reader -- only a step's own `run:` text is ever read.
4. **GitLab `include:` is never followed, in ANY form -- `local:` included.** `include:`'s
   children (`local:`, `template:`, `project:`, `remote:`, `component:`) are all skipped
   uniformly as a reserved non-job key; none is ever resolved or opened. A pipeline composed from
   included files can run a tool this reader never sees, so a zero-finding result on such a repo
   is not evidence its CI is clean -- and this is the limit the first repo a user points this
   skill at is most likely to hit, since ai-kit's own `.gitlab-ci.yml` is itself include-composed.
5. **Unresolved expressions and unevaluated execution context.** `${{ }}` expressions are never
   resolved, so a step whose command is entirely an expression has no classifiable tool token;
   matrix expansion, `if:` conditions, and `working-directory:` are not evaluated, so a command
   that would never actually run on this platform is still read; `defaults.run` is not evaluated
   either, at workflow or job level, so a `shell:`/`working-directory:` default that changes how
   every `run:` in the file actually executes contributes nothing to the command text this reader
   sees.
6. **The scope is reuse-source-driven: a duplicate with no existing equivalent is never
   flagged.** A CI step running a tool directly that the repo has no Makefile target, hook,
   script, or task for produces no finding -- this skill never recommends creating a new reuse
   source, only reusing one that already exists.
7. **The single-tool shape requirement excludes several real target/script/task shapes.** An
   identity is extracted only from a Makefile target with at most two real recipe lines (and, for
   two lines, only when both compute the same command key), a pre-commit hook entry or
   `package.json` script with no top-level `&&`/`||`/`;`, and a Gradle task whose bare name is the
   identity. Aggregate Makefile targets, a two-line target whose lines compute different keys,
   aggregate hook entries and scripts, multi-segment hook entries, and Gradle's own lifecycle
   task names (`check`, `build`, `test`, `assemble`) never become reuse sources, even when one of the tools
   they run would otherwise match a CI line.
8. **The unrecognized-tool case is silent: when neither the catalog nor a qualified-name match
   can answer an identity, it is silently unusable.** An identity the shared tool catalog does not resolve, that
   is not an out-of-taxonomy marker, and that was not derived from a command body naming itself,
   admits no reuse source -- with no error or warning saying so. A `clean: rm -rf dist` target,
   for example, is never a reuse source for anything.
9. **`package.json` is read root-and-`scripts`-only, with workspace members unread.** Only the
   repository root's `package.json` is read, and only its `scripts` object; a workspace member's
   own `package.json`, and every other top-level field (`bin`, `config`, and so on), are never
   read as a command to reuse.
10. **Gradle is read root-and-text-only, with a plugin-table blind spot.** Only root
    `build.gradle`/`build.gradle.kts` are read (a subproject's build script and
    `settings.gradle`'s project list are not); this skill never invokes the build tool to
    enumerate its own real task set, so a task contributed by a plugin outside the pinned table
    above is invisible; the plugin-id evidence check is a plain containment test against the
    build-script TEXT, so a comment merely mentioning a plugin id counts as evidence too (an
    accepted over-admission -- nobody comments out a plugin they never applied); and a declared
    task's identity is its NAME with no command body behind it, so a task named for its purpose
    rather than its tool (`tasks.register("jscpdReport")` beside a `jscpd` invocation elsewhere in
    CI) is not a reuse source for that tool -- this family's match rule never does suffix
    stripping to recover one.
11. **The command-segmentation scope leaves pipelines' downstream stages, subshells, and
    heredocs unanalyzed.** Only a command line's own top-level segments (split on `&&`/`||`/`;`,
    truncated at an unquoted pipe) are classified; a line containing a heredoc (`<<`) is skipped
    rather than mis-parsed, and nothing inside a subshell or piped into a later stage is read as
    its own command.

`SKILL-SHAPE-OK`-style keyword checks on this section are a DELETION DETECTOR and nothing more:
they confirm a limit's keyword survived, not that the sentence still states something a reader
would act on. A wording change that keeps the token but drops the content is the real failure to
guard against.

## What a user does with the output

Read the `remediate` list in criticality order. Each entry's `summary` names both sides of the
duplication -- the command CI runs directly and the reuse command that already exists -- so
applying the fix means replacing the CI line with the named `reuse_command`, verbatim. Nothing
here is auto-applied by this skill itself; `auto_apply: true` on an entry means it is safe for
the CALLER to apply automatically, never that this skill has already done so.

## Anti-patterns (NEVER)

- **NEVER hardcode a host-specific absolute path** when resolving this skill's own entrypoint --
  always walk the host-neutral candidate list above.
- **NEVER run, execute, or shell-expand any command this skill reads out of a CI file.** It reads
  command text only, never invokes it.
- **NEVER fetch, download, or analyze a `uses:` step's referenced action, or a `jobs.<id>.uses`
  reusable workflow**, to see what tool it runs internally.
- **NEVER follow a GitLab `include:`, in any of its forms** -- `local:` included -- to see what it
  contributes to the pipeline.
- **NEVER ask a build tool to enumerate its own tasks.** Gradle task identity comes from a
  text/regex read of the build script and the pinned plugin table, never from invoking the build
  tool itself.
- **NEVER edit the target repo's CI file, Makefile, `.pre-commit-config.yaml`, `package.json`, or
  Gradle build script.** The family's report-only boundary holds even when a finding's
  `auto_apply` is `true` -- "auto-apply" means "safe for the caller to apply automatically," not
  "this skill applies it."
- **NEVER report a duplicate the repo has no existing reuse source for.** This skill flags reuse
  gaps, never missing-tooling gaps.
- **NEVER present this skill's silence as proof that a repo's CI is clean.** An include-composed
  pipeline -- ai-kit's own `.gitlab-ci.yml` is one -- is the concrete way that mistake gets made:
  this reader never opens the included file, so a zero-finding run against it says nothing about
  the tools that file's own jobs actually run.

## Reporting rule

Findings and remediation results are reported INLINE in the conversation only. This skill never
writes a persisted report file into the target repo.
