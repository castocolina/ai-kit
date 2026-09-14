---
name: ai-kit-project-rules-docker
description: Use when a target repo's local-dev Docker Compose conventions need auditing -- whether the eight-member docker-* Makefile target family exists, whether docker/local/README.md documents the local-dev runbook, whether a docker-compose.yml service's healthcheck timeout/start_period/interval stay within 2s/10s/5s, whether depends_on entries use condition: service_healthy rather than bare ordering, and whether a local-dev service definition uses a bind mount plus a hot-reload-capable command override rather than the production image baked at build time -- or when asked "does my compose file wait for a dependency to become healthy", "is my local-dev container actually hot-reloading", or "why is my depends_on flagged". Routes apart from the ai-kit-project-rules-makefile sibling, which also has an opinion about docker-* targets: that sibling checks that a docker-up-shaped target builds its image before it runs; this skill checks that the eight-target local-dev family exists at all and that the compose file's own conventions hold. Detects and reports only; never edits the target repo.
---

# ai-kit-project-rules-docker

## Scope

This skill DETECTS AND REPORTS gaps in a repo's LOCAL-DEV Docker workflow conventions only. It
never edits the target repo's Makefile, compose files, or any other file; never runs, builds, or
inspects a container; never invokes a `docker` or `docker compose` command; and never resolves an
environment-variable interpolation inside a compose file. Applying a fix is a decision for
whoever invoked this skill.

One neighbouring boundary matters more than the others, because both skills have an opinion
about a `docker-*`-named Makefile target:

- The `ai-kit-project-rules-makefile` sibling skill checks that a `docker-up`-SHAPED target
  builds its image before it runs (the Docker-build-before-up convention) -- a question about
  ONE target's recipe order. This skill checks something different: whether the full eight-member
  `docker-*` local-dev target family exists at all, and whether the compose file(s) behind it
  follow this skill's healthcheck/`depends_on`/hot-reload conventions. A report from this skill
  about a missing `docker-clean` target is not the makefile sibling's business, and a report from
  that sibling about build ordering on `docker-up` is not this skill's business.
- Auditing an AGENTS.md/CLAUDE.md-style agent-instruction file, general Makefile target shape
  beyond the docker family, and pre-commit configuration all belong to the other three sibling
  skills, not this one.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path as a literal absolute
path:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-project-rules-docker}" \
         "$HOME/.claude/skills/ai-kit-project-rules-docker" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-project-rules-docker" \
         "$HOME/.agents/skills/ai-kit-project-rules-docker" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-project-rules-docker.py" ] && { printf '%s\n' "$d/ai-kit-project-rules-docker.py"; break; }
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

Before anything else: this skill evaluates a repo only when ROOT-level Docker evidence exists --
a root `docker-compose.yml`/`compose.yml` (or their `.yaml` spellings, or the local-dev
`docker-compose.override.yml`/`docker-compose.local.yml` variants), a root `Dockerfile` or
`Dockerfile.<suffix>`, a root `docker/` directory, or a Makefile target named `docker` or
prefixed `docker-`. A repo with no root-level evidence -- ai-kit's own repository is the live
example, whose only Docker asset is a nested, CI-only `tests/e2e/docker/Dockerfile` behind an
`e2e-docker` target -- gets an EMPTY report, and that is the correct answer, not a failure to
run. Docker assets that live only below the root are not evaluated at all: this gate never
descends into subdirectories.

## Run the check

```bash
python3 "$ENTRYPOINT" check <repo_root>
python3 "$ENTRYPOINT" remediate <repo_root>
```

`check` returns a single key: `{"docker": [...]}` -- every finding this skill emits, sorted by
criticality. `remediate` runs `check` internally and returns the shared builder's two-key
payload: `{"remediate": [...ordered, most-critical-first...], "blocked": [...]}`. This skill's
findings never populate `blocked`, because nothing it emits carries `needs_research` -- its
baseline knowledge is entirely hardcoded (see below). Every `remediate` entry carries
`auto_apply`, `True` UNLESS the underlying finding carries `advisory: True`, in which case it
arrives `False` -- an ADVISORY finding is a suggestion to confirm by hand, never something a
caller should apply automatically.

Trimmed worked example, contrasting an auto-applying entry against an advisory one:

```json
{
  "remediate": [
    {"kind": "docker", "id": "docker-clean", "issue": "docker_target_missing",
     "criticality": 3, "summary": "...", "auto_apply": true},
    {"kind": "docker", "id": "docker-depends-on", "issue": "docker_depends_on_unreadable",
     "criticality": 4, "summary": "...", "auto_apply": false}
  ],
  "blocked": []
}
```

This skill has exactly two subcommands, `check` and `remediate` -- unlike the Phase 10
(`ai-kit-project-rules-makefile`) and Phase 11 (`ai-kit-project-rules-precommit`) siblings, there
is no third subcommand behind either one. There is no research step and no cache: this skill's
baseline knowledge -- the eight target names, the three healthcheck bounds, the conforming
`depends_on` condition, and the per-stack hot-reload marker table -- is written directly into
its source, matching the Phase 12 (`ai-kit-project-rules-arch`) sibling rather than the
Phase 10/11 siblings, whose per-stack tooling genuinely goes stale and is therefore researched
and cached.

## What it checks

Five finding categories, re-derived from the committed checker modules, in the order this
skill evaluates them:

1. **`docker-target-family`** (`docker_target_missing`, criticality MEDIUM). One finding per
   missing member of the fixed eight-name `docker-*` local-dev Makefile target family:
   `docker-up`, `docker-health`, `docker-stop`, `docker-clean`, `docker-prune`,
   `docker-events-up`, `docker-events-monitor`, `docker-events-test`. Matched by exact name after
   normalization (casefold, `_` folded to `-`), never a shape rule.
2. **`docker-local-runbook`** (`docker_runbook_missing`, criticality MEDIUM). One finding when
   `docker/local/README.md` does not exist -- the runbook documenting how an agent interacts with
   the local-dev containers, which networks and secrets the stack requires, how to copy `.env`
   files into a new worktree, and whether a new worktree needs fresh containers or can reuse a
   sibling worktree's already-running ones.
3. **`docker-healthcheck-bounds`** (`docker_healthcheck_out_of_bounds`, criticality MEDIUM;
   `docker_healthcheck_unreadable`, criticality ADVISORY). A service's `healthcheck:` timing key
   -- `timeout`, `start_period`, `interval` -- declared with a value strictly greater than its
   bound (2s / 10s / 5s respectively) is flagged by name; a declared value this skill cannot parse
   as a duration is an advisory naming the raw text, since an unreadable timing is exactly where a
   real violation can hide.
4. **`docker-depends-on`** (`docker_depends_on_bare`, criticality HIGH;
   `docker_depends_on_weak_condition`, criticality HIGH; `docker_depends_on_completion_condition`,
   criticality ADVISORY; `docker_depends_on_unreadable`, criticality ADVISORY). A bare-ordering
   `depends_on` entry (a sequence form, or a mapping entry with `condition: service_started` or no
   `condition:` key at all -- Compose's own default IS `service_started`) is flagged; a mapping
   entry with `condition: service_completed_successfully` is an advisory confirming the legitimate
   one-shot-container form rather than a plain violation; a condition this skill cannot read is an
   advisory naming the raw text. Evaluated PER dependency entry, never "does the block mention the
   conforming condition anywhere."
5. **`docker-hot-reload`** (`docker_hot_reload_convention_missing`, criticality MEDIUM;
   `docker_hot_reload_tool_unrecognized`, criticality ADVISORY). A local-dev service definition
   (one declared in `docker-compose.override.yml`/`docker-compose.local.yml`, never a base-file
   service) missing a bind mount, a `command:`/`entrypoint:` override, or both, is flagged as
   carrying the production image/entrypoint baked at build time rather than a reloading local-dev
   workflow. A service that declares both halves but whose override this skill cannot confirm
   reloads on change is an advisory naming one of five reasons (a script-runner indirection, no
   detected stack, a detected stack with no baseline in this skill's table, the override simply not
   matching a known marker, or the volume entry being unreadable) -- never a confident "no hot
   reload" claim built on evidence this skill does not have.

`check_docker_rules` degrades rather than crashes: an absent Makefile yields all eight
target-family findings (the shared parser already returns an empty result for an absent file),
and an unreadable one yields the same answer.

## Hardcoded Baseline Knowledge

This skill's knowledge is entirely hardcoded -- no research is needed to apply it, and there is
no per-stack cache to keep current:

- **The eight-target family**, in the order listed above.
- **The three healthcheck bounds**: `timeout` 2s, `start_period` 10s, `interval` 5s.
- **The conforming `depends_on` condition**: `service_healthy`.
- **The per-stack hot-reload marker table**, keyed by exactly the stacks the shared stack
  detector can return (`python`, `node`, `go`, `rust`, `java`) -- for example Python's
  `--reload`/`runserver`/`watchmedo`, Node's `vite`/`nodemon`/`--watch`, Go's `air`/`reflex`,
  Rust's `cargo watch`/`bacon`, and Java's `spring-boot:run`/`quarkus:dev`. This table is
  transcribed as baseline knowledge that is expected to go STALE -- see Limits below for how that
  staleness surfaces honestly in a report rather than becoming a confident false accusation. No
  recommendation text in this skill's source ever names a marker as a literal outside this table;
  every list a report shows a reader is built at runtime by joining from the same table the check
  itself consulted, so the document and the report can never disagree about which markers this
  skill knows.

## Limits

Eight places this skill knows less than it might appear to, stated here rather than left to be
discovered, in one scannable section, per this family's own lesson that a document stating what
it cannot do is more useful than one implying it can do everything. Each is its own standalone
sentence a reader can act on.

1. **The applicability gate is root-scoped.** This skill evaluates a repo only when root-level
   Docker evidence exists, and reports nothing otherwise. A repo whose Docker assets live only
   below the root -- ai-kit's own CI-only `tests/e2e/docker/Dockerfile` is the live example -- is
   not evaluated at all.
2. **The compose reader is a text parser, not a YAML implementation.** Compose files are read
   with an indentation-aware stdlib scan, never a YAML library. A TAB-indented file (invalid YAML)
   may be mis-attributed to the wrong service rather than rejected outright.
3. **Healthcheck bounds cover DECLARED values only.** An absent `interval` inherits Compose's own
   30s default, which exceeds this skill's 5s bound, and is NOT flagged; a service with no
   `healthcheck:` block at all is NOT flagged either. This is the limit most likely to read as a
   bug to a user who knows Compose's own defaults, so it is stated rather than left to be
   discovered.
4. **Hot-reload stack attribution is REPO-WIDE, not PER-SERVICE.** The override command is
   resolved against the union of every stack detected anywhere in the repo, because a compose
   service definition carries no per-service language signal of its own. In a polyglot repo, a
   Node dev server can therefore satisfy a Python service's command line.
5. **The hot-reload marker baseline is hardcoded and will go STALE.** The per-stack table above is
   knowledge that ages, which is exactly why an override this skill does not recognize produces an
   ADVISORY finding with a named reason rather than a confident defect claim -- an unrecognized
   tool is not an accusation.
6. **No local-dev compose file means no hot-reload finding at all.** The hot-reload check's
   subject is the local-dev service definition; a repo that does local development straight from
   its base compose file, with no `docker-compose.override.yml`/`docker-compose.local.yml`
   present, is not evaluated for the hot-reload convention.
7. **Same-line flow-mapping compose bodies are unread.** `healthcheck: {interval: 30s}` and
   `depends_on: {db: {condition: service_healthy}}` are valid Compose forms the block-indentation
   parser does not read, so a service written this way is neither flagged nor confirmed
   conforming for that block. This is a stated reader gap, not a silent mis-parse: the parser
   never lets a flow-mapping value swallow the block boundary of the service defined after it.
8. **Long-form (mapping-style) volume entries are unread.** A local-dev service that declares its
   mounts as a `volumes:` sequence of mappings (`- type: bind` / `source:` / `target:`), rather
   than the short form `./src:/app/src` this skill reads, is reported as NOT CONFIRMABLE -- an
   advisory naming the reason `volumes_unreadable` -- rather than flagged as missing the
   convention or confirmed conforming. This skill reads only the short-form entry.

`SKILL-SHAPE-OK`-style keyword checks on this section are a DELETION DETECTOR and nothing more:
they confirm a limit's keyword survived, not that the sentence still states something a reader
would act on. A wording change that keeps the token but drops the content is the real failure to
guard against.

## What a user does with the output

Read the `remediate` list in criticality order. Apply the non-advisory entries -- their
`auto_apply` is `true`, but this skill never applies them itself; the caller decides. Confirm
every advisory entry by hand: each one exists because this skill could not read a value or could
not match a hardcoded baseline confidently enough to assert a defect, not because nothing is
there to check.

## Anti-patterns (NEVER)

- **NEVER hardcode a host-specific absolute path** when resolving this skill's own entrypoint --
  always walk the host-neutral candidate list above.
- **NEVER treat a `remediate` entry with `advisory: true` as safe to auto-apply.** It arrives with
  `auto_apply: false` and must stay a suggestion to confirm, never an automatic edit.
- **NEVER run a container, a `docker` command, or a `docker compose` command from this skill.**
  It reads compose and Makefile text only.
- **NEVER edit the target repo's Makefile, compose files, or any other file from this skill.**
  The family's report-only boundary holds even when a finding's `auto_apply` is `true` --
  "auto-apply" means "safe for the caller to apply automatically," not "this skill applies it."
- **NEVER treat an unrecognized hot-reload override as proof a service lacks hot reload.** The
  marker table is a hardcoded baseline that goes stale (Limits #5); an unrecognized command
  produces an advisory, not a defect claim.
- **NEVER read a clean report from this skill as proof the repo's full local-dev workflow is
  correct.** It proves only that this skill's five checked conventions hold under this skill's
  stated limits -- not that every convention a team might want holds.
- **NEVER expect this skill to refactor or rewrite any file it finds a gap in.** Unlike the
  AGENTS.md-domain sibling skill, which hands its own findings off to a dedicated remediation
  skill for that one file type, this skill has no such mechanism: its report-only boundary has no
  exception.

## Reporting rule

Findings and remediation results are reported INLINE in the conversation only. This skill never
writes a persisted report file into the target repo.
