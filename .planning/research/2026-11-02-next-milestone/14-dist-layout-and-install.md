# Dist layout and install through `npx skills` (research for the next milestone)

Date: 2026-11-02. Read-only research. Nothing was installed. The only commands run against
the `skills` CLI were `--help` and `add <local path> --list` (no writes to `~/.claude`,
`~/.agents`, `~/.cursor` or `~/.config`; `~/.agents/.skill-lock.json` still has its
2026-10-31 timestamp). The CLI source was read from the published npm tarball
(`skills@1.7.5`, released 2026-11-02), unpacked under `tmp/next-milestone-research/skills-pkg/`.

Confidence labels: **verified** = run or read on this machine; **read in code** = read in
the CLI bundle, not exercised; **unverified** = not checked, must be confirmed before planning.

Helper scripts in this folder: `grep_skills_cli.py` (context search in the CLI bundle),
`14_cross_skill_refs.py` (+ `.out`, which skills reach outside their own folder).
Raw outputs: `list-aikit.out`, `list-agent-toolkit.out`, `list-subfolder.out`, `npx-y.out`.

---

## 1. How agent-toolkit does it (`/var/home/bazzite/git/github/agent-toolkit`)

### Layout (verified)

- Source: `skills/<name>/` holds `SKILL.md`, `README.md`, `references/`, `scripts/` and
  **`evals/`** (45 of 47 skills have `evals/evals.json` + `trigger-queries.json`). Evals stay
  inside the source skill folder; they are dropped at build time, not moved.
- Tests live outside skills: `tests/skills/<name>/` (`test-*.sh`, `test_*.py`, `fixtures/`),
  plus `tests/scripts/` and `tests/audit/`. Runner: `scripts/audit/run-script-tests.sh`.
- Also `agents/*.md` and `commands/*.md` (Claude Code only).
- Dist: `dist/plugins/<plugin>/skills/<name>/` (or `/agents/<f>.md`, `/commands/<f>.md`):
  one self-contained folder per plugin. Committed to git (286 tracked files under `dist/`).

### Build (verified, `scripts/build_plugins.py`, 207 lines, stdlib only)

- Reads `.claude-plugin/marketplace.json`, and for each plugin copies the declared
  `skills`/`agents`/`commands` paths into `dist/plugins/<name>/`, then rewrites each plugin's
  `"source"` to `./dist/plugins/<name>` and saves the marketplace file.
- Exclusion list: `EXCLUDED_DIRS = ("evals", "tests", "__pycache__")` with the comment
  "Evals and tests are not shipped (roadmap Decision 16)." Uses
  `shutil.copytree(..., ignore=shutil.ignore_patterns(*EXCLUDED_DIRS))`.
- `rm -rf dist/plugins` first, so a removed skill disappears. `--dry-run` / `--verbose`.
- One unit test pins the exclusions: `tests/scripts/test_build_plugins.py`
  (`test_evals_tests_and_pycache_are_not_copied`).

### Keeping dist in sync (verified)

- CI `.github/workflows/main.yaml`, job "Validate dist/ is up to date" (pull requests only):
  runs the build, then `git diff --quiet dist/ .claude-plugin/marketplace.json`, fails with
  "dist/ is out of date. Run 'python3 scripts/build_plugins.py' and commit."
- `.github/workflows/auto-bump.yaml`: on push to main touching `skills/**`, `agents/**` or
  `commands/**`, bumps the version (`scripts/bump_version.py patch`), rebuilds dist and
  commits `chore: auto-bump version [skip ci]` with `marketplace.json` + `dist/plugins/`.
- So: generated, committed, and checked by CI diff (not by a local test or pre-commit hook).

### Plugin manifest (verified, `.claude-plugin/marketplace.json`)

Top level `name: agent-toolkit`, `owner`, `metadata.version` (1.0.15). One entry per skill,
agent and command, for example:

```json
{ "name": "codex", "source": "./dist/plugins/codex", "strict": false,
  "skills": ["./skills/codex"], "category": "ai-tools", "keywords": [...] }
```

No per-plugin `plugin.json` (`strict: false` lets the marketplace entry act as the manifest).
Agents/commands are published as `agent-<name>` / `command-<name>` plugins.

### README install section (verified, `README.md` lines 17-100, condensed)

- **Claude Code:** `claude plugin marketplace add castocolina/agent-toolkit`, then
  `claude plugin install humanizer@agent-toolkit` (same for `agent-…` and `command-…`);
  interactive alternative `/plugin`. Update: `claude plugin marketplace update agent-toolkit`
  or enable auto-update in `/plugin` → Marketplaces.
- **Switching from the upstream marketplace:** same name, so `claude plugin marketplace remove
  agent-toolkit` first, with a warning that removing uninstalls its plugins.
- **Codex, Cursor, GitHub Copilot CLI, opencode, pi (skills only):** a table of
  `npx -y skills add castocolina/agent-toolkit --skill <skill-name> -a <agent> -y` (project)
  and the same with `-g` (user scope); agents `codex`, `cursor`, `github-copilot`,
  `opencode`, `pi`. All at once: `--skill '*'`. "Agents and commands are Claude Code-only."
- **Manual install:** `cp -r skills/<skill-name> ~/.claude/skills/`, or a clone-to-temp +
  `cp -r "$T"/skills/. ~/<dir>/` one-liner with `<dir>` = `.agents/skills` for every other
  harness ("verified 2026-10-24").
- **claude.ai:** paste `SKILL.md` into project knowledge.

### A gap in agent-toolkit worth not copying (read in code)

`npx skills add castocolina/agent-toolkit` does **not** install from `dist/`. The CLI searches
the standard folders (`skills/` first) before the folders named in `marketplace.json`
(`prioritySearchDirs.push(...await getPluginSkillPaths(searchPath))` comes last), and "if two
skills have the same name, only the first one found is kept". So the `npx skills` route
installs the source folders, and the CLI's copy step only drops `.git`, `__pycache__`,
`__pypackages__` and `metadata.json`, which means **`evals/` is shipped to every non-Claude
host**. Only the Claude plugin route gets the trimmed dist copy. (`--list` on a local
checkout found 47 skills, one per name, which is consistent with this but does not show the
chosen path; the order is from reading the bundle.)

---

## 2. The `skills` CLI (`npx skills`)

Package: npm `skills` 1.7.5, repo `github.com/vercel-labs/skills`, bins `skills` and
`add-skill`, needs Node 22.20+ (this machine: node v24.21.0). Docs: package `README.md`,
`docs/commands.md`, `docs/agents.md`, `docs/creating-skills.md`, `docs/troubleshooting.md`.

### `npx` on this machine (verified)

`type npx` → aliased to `pnpm dlx` in the interactive shell, and `/home/bazzite/.local/bin/npx`
is a tools-installer shim: `exec /home/bazzite/.volta/bin/pnpm dlx "$@"`. So a subprocess from
`setup.py` also gets `pnpm dlx`. `npx -y skills --help` works through the shim (pnpm accepts
`-y`), but `npx --version` fails ("Unknown option: 'version'"). Pinning an exact version made
pnpm print "Added 1 entry to minimumReleaseAgeExclude in pnpm-workspace.yaml" (written inside
the dlx cache temp dir, `~/.cache/pnpm/dlx/...`): this machine's pnpm has a minimum-release-age
gate, so a brand-new pinned version may need that exclusion. npm itself is banned here
("use pnpm (local) or volta install <pkg> (global)").

### Commands (verified from `--help` and docs)

- `add <source>` (alias `a`): `-g/--global`, `-a/--agent <agents…>` (`'*'` = all),
  `-s/--skill <skills…>` (`'*'` = all), `-l/--list` (list only), `-y/--yes`, `--copy`,
  `--all` (= `--skill '*' --agent '*' -y`), `--full-depth`, `--json` (machine-readable, no
  ANSI; cannot be combined with `--list`).
- `list` / `ls`: `-g`, `-a <agents>`, `--json`.
- `remove` / `rm [skills]`: `-g`, `-a` (omit to clean all agent links), `-s`, `-y`, `--all`;
  also `remove owner/repo` removes everything from that lock source.
- `check` (exit 1 when an update exists), `update [skills…]` (`-g`, `-p`, `-y`).
- `use <source>@<skill>` (prompt without installing), `find`, `init`.
- Experimental: `experimental_sync` (alias `sync`; links skills shipped by **npm
  dependencies** from `node_modules` into `.agents/skills` + agent dirs, project scope, has
  `--dry-run`, `--copy`, `--include/--exclude`, `skills-lock.json`) and
  `experimental_install` (restore from `skills-lock.json`). `sync` is not a general
  "sync my repo to hosts" command; it is about npm packages in a project.

### Host selection (read in code, agent table in `dist/cli.mjs`)

| ai-kit host | `-a` id | global dir | "installed" check |
|---|---|---|---|
| Claude Code | `claude-code` | `$CLAUDE_CONFIG_DIR or ~/.claude` + `/skills` | that dir exists |
| opencode | `opencode` | `$XDG_CONFIG_HOME/opencode/skills` | `~/.config/opencode` exists |
| Codex | `codex` | `~/.agents/skills` | `$CODEX_HOME` or `/etc/codex` exists |
| Cursor | `cursor` | `~/.cursor/skills` | `~/.cursor` exists |
| pi | `pi` | `~/.agents/skills` | `~/.pi/agent` exists |
| Copilot CLI | `github-copilot` | `~/.copilot/skills` | `~/.copilot` exists |

(One table here because the column set is the point; 80 agents total.) Project scope uses
`.claude/skills/` for Claude and `.agents/skills/` for the rest.

Facts that matter for ai-kit:

- **Host auto-detection overrides the prompt.** Inside a coding agent the CLI says "Agent
  detected — installing non-interactively" and targets that host only (verified: it printed
  `claude-code_2-1-310_agent` when run from this session). Detection uses env vars via
  `@vercel/detect-agent`: `AI_AGENT`, `CLAUDECODE`, `CLAUDE_CODE`, `CODEX_THREAD_ID`,
  `CODEX_SANDBOX`, `OPENCODE_CLIENT`, `CURSOR_AGENT`, `CURSOR_TRACE_ID`, `GEMINI_CLI`,
  `COPILOT_MODEL`, and others. **setup must always pass `-a` explicitly** and should scrub
  these vars (ai-kit already has a host-signal scrub list).
- **Global symlink mode copies into `~/.agents/skills/<name>` first**, then symlinks each
  agent dir to that copy (`getCanonicalSkillsDir(global) = ~/.agents/skills`). So installing
  only for `claude-code` still puts every chosen skill in `~/.agents/skills`, which **pi and
  Codex read** (pi docs: "Pi also supports the Agent Skills locations `~/.agents/skills/`").
  That breaks ai-kit's rule that pi only gets three skills (`PI_SKILLS` in `tools/setup.py`)
  and the README promise "nothing is ever linked under `~/.agents/skills`".
- **`--copy` mode writes straight into each agent dir**, with no `~/.agents/skills` copy
  (read in code: `if (installMode === "copy") { cleanAndCreateDirectory(agentDir);
  copyDirectory(...) }`). But pi and Codex share `~/.agents/skills`, so choosing either one
  exposes the skill to both.
- `~/.agents/skills` already holds 12 third-party skills installed by tools-installer through
  this same CLI; the lock `~/.agents/.skill-lock.json` (or `$XDG_STATE_HOME/skills/`) lists
  sources `castocolina/agent-toolkit`, `herdrdev/herdr`, `typesafe-ai/skills`,
  `vercel-labs/skills`. Each record holds `source`, `sourceType`, `sourceUrl`, `skillPath`,
  dates and a hash, **not the agents it went to**. ai-kit must never `remove --all`.

### Sources it accepts (docs + verified where noted)

- GitHub shorthand `owner/repo`, full URL, **a tree URL to a subfolder**
  (`https://github.com/<o>/<r>/tree/main/skills/<name>`), GitLab URL, Azure `?path=`, any git
  URL, direct `SKILL.md`/archive URL, and **a local path** (verified: `add <ai-kit
  checkout> --list` and `add <ai-kit checkout>/skills --list` both found 22 skills).
- Discovery inside a source: root `SKILL.md`, `skills/` (up to 3 levels), `skills/.curated|
  .experimental|.system/`, ~55 host folders such as `.claude/skills/` and `.agents/skills/`,
  then folders named in `.claude-plugin/marketplace.json` or `plugin.json` (`skills` arrays
  and `<plugin>/skills`), then `paths` in a root `skills.sh.json`. A recursive search runs
  only when nothing is found. A `dist/` folder is not searched unless the source points into
  it (a local path or tree URL to `dist/...`), a manifest names it, or `skills.sh.json`
  lists it. (Note: `experimental_sync` alone also looks at `dist/skills/<name>/SKILL.md`
  inside npm packages.)
- Copy rules: everything in the skill folder except `.git`, `__pycache__`, `__pypackages__`
  and `metadata.json`; **symlinks that point outside the skill folder are skipped** with a
  warning. So in-repo symlinks such as `<skill>/_shared -> ../_shared` cannot work; shared
  code must be real files in each distributed skill.
- Frontmatter is parsed with a strict YAML parser. Skills with `metadata.internal: true` are
  hidden unless `INSTALL_INTERNAL_SKILLS=1`. Telemetry is on unless `DISABLE_TELEMETRY=1`
  or `DO_NOT_TRACK=1`.

### Defect found in ai-kit today (verified)

The CLI **skips three ai-kit skills** because their `description:` is an unquoted YAML
scalar containing `: `: `ai-kit-project-rules-agents`, `ai-kit-project-rules-cicd`,
`ai-kit-project-rules-docker` ("YAML parse error: Nested mappings are not allowed in compact
mappings at line 2, column 14"). Claude Code accepts them; the `skills` CLI does not. Any
`npx skills` route needs those descriptions quoted (or folded with `>-`), plus a test that
parses every `SKILL.md` frontmatter strictly. This is pre-existing, not caused by this work.

---

## 3. ai-kit today

### Fetch and install (verified, `tools/install.sh`, `tools/setup.py`, README "How the installer works")

- `tools/install.sh` (294 lines): LOCAL mode (run from a clone) or BOOTSTRAP mode (piped from
  curl): `git clone --single-branch --depth 1` into `~/.local/share/ai-kit` (or `AI_KIT_DIR`),
  or a tarball download when git is missing; then hands off to `tools/setup.py`.
- `tools/setup.py` (4,857 lines): `enumerate_entries()` lists `skills/`, `commands/`,
  `agents/`; `link_one()` symlinks each into `~/.claude/<category>/` (`CLAUDE_CONFIG_DIR`);
  `installed_links()` treats "symlinks into the install dir" as the saved selection (no
  state file). `sync_pi_links()` mirrors only `PI_SKILLS = {ai-kit-cross-ai,
  jev-fast-decision, ai-kit-session-wake}` into `${PI_CODING_AGENT_DIR:-~/.pi/agent}/skills`.
  opencode is covered because it reads `~/.claude/skills`; Codex and Cursor get no skill
  links; nothing goes to `~/.agents/skills`. Headless: `--headless --skills=…
  [--replace-existing]`; backups, dry-run and atomic JSON writes already exist.
- `.claude-plugin/plugin.json` exists (single plugin `ai-kit`, version 0.2.0, description
  still says "a one-line installer that symlinks them into Claude Code"); there is no
  `marketplace.json`.
- Backlog **999.14** (`.planning/ROADMAP.md` line 324, priority major, "the next feature to
  implement after v1.3"): replace symlinks with real copies through the `skills` CLI for pi,
  cursor, copilot, codex, opencode and claude. Open in the backlog: copy instead of link for a
  local path (answered above: `--copy`), drift detection, migrating existing symlinks
  without touching other skills, atomic writes/backups, dry-run first, scratch HOME in tests.

### Tests and evals today (verified)

- Tests already live outside skills: `tests/` (104 entries), run by
  `tools/run_unittest_parallel.py`.
- Evals live inside 7 skills (`skills/<name>/evals/`, 45 tracked files, about 230 KB):
  `ai-kit-gsd-curated-config`, `ai-kit-spec-goal-prompt`, `ai-kit-spec-review`,
  `ai-kit-spec-review-checklist`, `ai-kit-spec-review-fixer`, `jev-fast-decision`,
  `mermaid-audit`. Tests read them by path (`tests/test_ai_kit_spec_goal_prompt_evals.py`,
  `tests/gsd_curated_eval.py`, `tests/test_gsd_curated_eval.py`, `tests/test_mermaid_style.py`,
  `tests/test_jev_fast_decision.py`). No test files inside skill folders.
- Extra non-runtime files in skills: `ai-kit-spec-goal-prompt/README.md` (fine to ship),
  untracked `__pycache__/` (the CLI drops these anyway).

### What breaks if `npx skills` copies the skills (verified by `14_cross_skill_refs.py` + reading the resolvers)

**Hard break: `skills/_shared` is not a skill (no `SKILL.md`), so the CLI never installs it.**
Every `ai_kit_rules_common` user raises `ImportError` from its package `__init__.py`, which
looks only at `<skills root>/_shared` from its own real path and says a copy install "does
not carry the shared package":

1. `ai-kit-project-rules-agents` (5 importing files)
2. `ai-kit-project-rules-arch` (3)
3. `ai-kit-project-rules-cicd` (4)
4. `ai-kit-project-rules-docker` (6)
5. `ai-kit-project-rules-makefile` (3)
6. `ai-kit-project-rules-precommit` (9)
7. `ai-kit-project-rules-all`: runs the six above as subprocesses, found as siblings next to
   its own real path, then `$CLAUDE_PLUGIN_ROOT/skills`, `~/.claude/skills`,
   `$XDG_CONFIG_HOME/opencode/skills`, `~/.agents/skills`; it skips the agents sibling when
   `_shared` is missing beside it. So it fails with the six.

**Breaks unless `ai-kit-spec-review` is installed in the same skills folder for the same
host** (they import the `ai_kit_spec` package from the sibling folder, resolved from
`os.path.realpath(__file__)`):

8. `ai-kit-session-wake` (hard: exits 2, "the ai-kit-spec-review sibling skill is missing")
9. `ai-kit-spec-execute-gsd` (5 importing files)
10. `ai-kit-spec-execute-superpowers` (2)
11. `ai-kit-gsd-curated-config` (3; the import is optional and degrades: "the sibling skill
    is optional")
12. `ai-kit-spec-config`: its `SKILL.md` Step 0 runs `ai-kit-spec.py` and reads
    `references/cli-profiles/` from the sibling `ai-kit-spec-review` folder.

Because the CLI puts all selected skills for one host in one folder (and, in symlink mode,
the real path is `~/.agents/skills/<name>`), sibling lookup keeps working **when the whole
group is installed together for that host**. It breaks on partial installs, which the
README's `--skill <name>` table invites, and on pi today: pi gets `ai-kit-session-wake`
without `ai-kit-spec-review` unless the copy lands in `~/.agents/skills` next to it.

**Soft links only (documentation):** many `SKILL.md`/`references/` files link to sibling
skills by relative path (`../ai-kit-cross-ai/SKILL.md` from `ai-kit-spec-review`,
`ai-kit-spec-execute-gsd`, `ai-kit-spec-execute-superpowers`, `ai-kit-spec-config`,
`ai-kit-gsd-curated-config`; `../agent-md-refactor` from `ai-kit-project-rules-agents`, which is
a third-party skill). Those links are dead when the target is not installed, but nothing
crashes. The other hits (`tools/…`, `skills/…` in `usage-metrics`, `goal-prompt`,
`markdown-to-pdf`, `spec-execute`) are "ported from, not imported" comments: no runtime
dependency.

Standalone (no sibling or shared code needed): `ai-kit-cross-ai`, `ai-kit-gsd-spec-discuss`,
`ai-kit-opencode-providers`, `ai-kit-spec-execute`, `ai-kit-spec-goal-prompt`,
`ai-kit-spec-review` itself, `ai-kit-spec-review-checklist`, `ai-kit-spec-review-fixer`,
`ai-kit-usage-metrics`, `cst-refactor`, `jev-fast-decision`, `markdown-to-pdf`,
`mermaid-audit`.

---

## 4. Proposal outline (a proposal, not a decision)

### 4a. Dist layout

```
skills/<name>/              # source, unchanged: SKILL.md, code, references/, evals/
skills/_shared/             # source only, never a distributed skill
tests/                      # unchanged
dist/skills/<name>/         # generated + committed: one self-contained folder per skill
.claude-plugin/marketplace.json   # new; plugin "ai-kit" -> source ./dist (skills under ./dist/skills)
tools/build_dist.py         # stdlib-only build, modeled on agent-toolkit's build_plugins.py
```

Each `dist/skills/<name>/` holds `SKILL.md` and whatever it ships today **minus**
`evals/`, `tests/`, `__pycache__/`, plus the vendored shared code (4b). Evals stay where they
are in source, as agent-toolkit does, so the five tests that read `skills/<name>/evals/`
keep working with no path churn. Moving evals to `tests/evals/<name>/` is possible but costs
churn and buys nothing the exclusion does not already give.

Why `dist/skills/` and not agent-toolkit's `dist/plugins/<name>/skills/<name>/`: ai-kit is one
plugin whose skills call each other, so one plugin folder is the right Claude unit, and a
flat `dist/skills/` is also a valid `npx skills` container for local and tree-URL installs.
Per-skill plugins are worth it only if ai-kit wants à-la-carte Claude installs.

Avoid agent-toolkit's gap: the public `npx skills` command must point **into** dist, for
example `npx -y skills add https://github.com/castocolina/ai-kit/tree/main/dist/skills
--skill '*' -a opencode -g -y` (a tree URL to a container folder is **unverified**; the docs
show a tree URL to one skill; a local container path is verified). The other option is to
move source out of `skills/` so the shorthand `castocolina/ai-kit` finds dist first, which
is a large rename across tests, docs and `AGENTS.md`.

Keeping dist in sync: same pattern as agent-toolkit, but local, because ai-kit's CI is
GitLab-secondary and the real gate is pre-commit: a unit test (or pre-commit hook) runs
the build into a temp dir and diffs it against the committed `dist/`, failing with "run
`make dist`". Add a `make dist` target. The build should also parse every `SKILL.md`
frontmatter with strict YAML rules (a stdlib check for unquoted `: ` in plain scalars is
enough) so the three skipped skills cannot come back.

### 4b. Vendoring shared code at build time

- `_shared/ai_kit_rules_common` → copied into each of the six rules skills as
  `dist/skills/<rules-skill>/ai_kit_rules_common/`. The entry script's own folder is already
  `sys.path[0]`, so the vendored package imports with no path tricks. Each package
  `__init__.py` guard must change from "must find `<skills root>/_shared`" to "vendored copy
  beside me first, else checkout `_shared`" (source keeps working unvendored).
  `ai-kit-project-rules-all` needs the same "vendored or `_shared`" test in `dispatch.py`.
  Cost: 132 KB × 6.
- `ai_kit_spec` (388 KB, 28 modules, plus `references/` it reads at run time such as
  `tooling-guidance.md` and `cli-profiles/`): two options to weigh.
  - Vendor it into the four Python users (session-wake, spec-execute-gsd,
    spec-execute-superpowers, gsd-curated-config): fully self-contained, about 1.5 MB of
    duplicates, and the resource lookups that rely on "this module's own sibling" need
    checking per file.
  - Ship it once in `ai-kit-spec-review` and make setup install the dependency group
    together (selecting any dependent selects `ai-kit-spec-review`, per host); document the
    group in the README table instead of a bare `--skill <name>`. Smaller, but a hand-run
    `npx skills add … --skill ai-kit-session-wake` still breaks.
  - Recommendation: vendor `ai_kit_rules_common` (small, pure library); decide `ai_kit_spec`
    with a spike on the resource lookups first. `ai-kit-spec-config` stays a group member
    either way (it runs the sibling's CLI script).
- Vendored files must be real copies (the CLI skips symlinks that leave the skill folder).
  A build-time stamp (a hash file per vendored package) lets the sync test catch a stale copy.

### 4c. Setup calling `npx skills` headless (an early phase)

1. **Detect** hosts with the existing `RUNTIMES` table / `detect_installed_clis()` and map
   them to `-a` ids (`claude` → `claude-code`, `opencode`, `codex`, `cursor`, `pi`,
   `copilot` → `github-copilot`). Pre-check only the detected ones in the wizard; headless
   takes `--hosts=…`.
2. **Plan, then show** a dry run: per host, the skill list and the target folder from the
   table above, and call out the shared `~/.agents/skills` folder (pi and Codex see the same
   skills; there is no way to give pi only three skills while Codex gets all of them).
3. **Run**, one call per host (so a failure names its host):
   `npx -y skills@<pinned> add <checkout>/dist/skills --skill <names…> -a <host> -g --copy -y`
   with `DISABLE_TELEMETRY=1`, the host-signal env vars removed, a scratch `HOME` in tests,
   and `--json` to parse results; stream the CLI's own output to the user unchanged (the
   owner's wish: run it headless, only show its output). `--copy` keeps every host off the
   `~/.agents/skills` canonical copy unless the host is pi or Codex.
4. **Migrate**: remove only ai-kit's own symlinks (`installed_links()` already finds them),
   then install; never touch other skills or the third-party lock entries; back up a real
   folder before replacing it, as today.
5. **Uninstall/resync**: `npx skills remove <names…> -a <host> -g -y` with explicit names,
   never `--all` and never `remove <source>`, which could hit tools-installer's entries.

Open questions to route to the phase researcher (unverified):
- How the lock records a local-path source, and whether `check`/`update` work for it, or
  whether setup must re-run `add` itself to detect drift (a changed `SKILL.md`, a removed or
  renamed skill).
- Whether a GitHub tree URL to a container folder (`…/tree/main/dist/skills`) installs all
  skills inside it.
- Whether opencode also reads `~/.agents/skills` and `~/.claude/skills` today (that would
  double-list skills installed for both claude-code and opencode).
- Whether `--json` output on `add` is stable enough to parse, or setup should rely on exit
  codes plus a `list --json` check afterward.
- Whether Cursor and Copilot actually load `~/.cursor/skills` / `~/.copilot/skills` on this
  machine (CLI table says so; not live-checked).
- The pnpm minimum-release-age gate on a pinned new version when `npx` is the pnpm shim.

### README outline (proposal)

Follow agent-toolkit's order: (1) the one-line ai-kit installer, which now drives
`npx skills` for the hosts you pick; (2) Claude Code plugin: `claude plugin marketplace add
castocolina/ai-kit` + `claude plugin install ai-kit@ai-kit`; (3) other hosts with `npx
skills` (a host → command list in agent-toolkit's style, project and user scope, pointing at
`dist/skills`, with the dependency groups spelled out); (4) manual copy from `dist/skills`;
(5) status line, hooks and wizard sections unchanged. Also update `.claude-plugin/plugin.json`'s
description, which still says "symlinks".
