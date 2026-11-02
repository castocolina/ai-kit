# 27 - AGENTS.md per host, the vertical-slice cycle, and quota-wake facts

Research date: 2026-11-02. Time-boxed (about 20 minutes). Sources are official docs unless marked.
"Verified here" means checked on this machine; "unverified" means not tested.

Installed host versions seen here: Claude Code 2.1.316, codex-cli 0.162.1, opencode 2.0.31,
pi 1.3.0 (`@earendil-works/pi-coding-agent`), GitHub Copilot CLI 1.0.105. Gemini CLI is not
installed.

## 1. Instruction files per host

### Claude Code (code.claude.com/docs/en/memory)

- Reads `./CLAUDE.md` or `./.claude/CLAUDE.md` (project), `./CLAUDE.local.md` (personal, "add to
  `.gitignore`"), `~/.claude/CLAUDE.md`, `.claude/rules/`, and the same files in every parent
  directory. Everything is concatenated, root first; inside one directory `CLAUDE.local.md` comes
  after `CLAUDE.md`.
- **AGENTS.md is read natively since Claude Code v2.1.277** (a Claude Code version, through the
  built-in plugin `cc-plugin-agents-md@builtin`; before v2.1.285 the id was `agents-md@builtin`).
  It is not tied to a model. Before v2.1.281 some sessions (Bedrock, telemetry off) still could
  not read it. The first session after upgrading from v2.1.276 or older may miss it.
- **Precedence (default setting `claude-md-or-agents-md`):** AGENTS.md is read only when there
  is no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` in the working directory or above.
  `~/.claude/CLAUDE.md`, the managed CLAUDE.md and `.claude/rules/` do not count and load
  alongside. Setting `claude-md-and-agents-md` (in `/config`, or `pluginConfigs` in
  `~/.claude/settings.json`; project settings files are ignored for it) loads both, CLAUDE.md
  first, and skips an AGENTS.md already loaded through an import or symlink.
- **Not read:** "`AGENTS.local.md`, `AGENTS.override.md`, or anything under a `.agents/`
  directory" (quoted). So the owner's premise that current Claude reads `AGENTS.local.md` is
  wrong; only `AGENTS.md` (and `.claude/AGENTS.md`) is read.
- **Trap:** "Because `CLAUDE.local.md` counts, adding one ... in a project that relies on
  `AGENTS.md` stops Claude from reading `AGENTS.md`" (quoted). A `CLAUDE.local.md` alone (or
  symlinked to `AGENTS.local.md`) silently drops AGENTS.md unless a `CLAUDE.md` also exists or
  the setting is `claude-md-and-agents-md`.
- **Imports:** `@path` in CLAUDE.md (and inside a natively read AGENTS.md). Relative paths resolve
  against the importing file; absolute paths allowed; max depth four hops; code spans and fences
  are skipped; imports outside the working directory need a one-time approval dialog (for a
  natively read AGENTS.md they load only if already approved, with no prompt).
- **Symlink `CLAUDE.md -> AGENTS.md`:** officially supported ("Either way Claude reads the
  content once"). Caveats from the doc: the Edit/Write tools refuse to write through the link and
  point at the target; on Windows use a `@AGENTS.md` import instead, because creating a symlink
  needs Administrator or Developer Mode, and Git checks a committed symlink out as a one-line text
  file unless `core.symlinks` is enabled. Symlinks to network paths (UNC, `/net`) are not followed.
- Worktrees: a gitignored `CLAUDE.local.md` exists only in the worktree that created it; the doc
  suggests importing a file from the home directory to share personal notes across worktrees.

### opencode (opencode.ai/docs/rules)

- Project: `AGENTS.md`, with `CLAUDE.md` as fallback "used if no `AGENTS.md` exists"; found by
  walking up from the current directory. Global: `~/.config/opencode/AGENTS.md`, fallback
  `~/.claude/CLAUDE.md`. "The first matching file wins in each category."
- Kill switches: `OPENCODE_DISABLE_CLAUDE_CODE`, `..._PROMPT`, `..._SKILLS`.
- No `@` import parsing ("opencode doesn't automatically parse file references"). Extra files go
  through the `instructions` config field (paths, globs, URLs), which is the only way to load an
  `AGENTS.local.md`. Unverified: whether a relative `instructions` entry in the global config
  resolves against the project.
- No `.local` file is documented. A `CLAUDE.md` symlink is harmless (AGENTS.md wins).

### Codex CLI (learn.chatgpt.com/docs/agent-configuration/agents-md, redirected from developers.openai.com)

- Global `~/.codex` (or `CODEX_HOME`): `AGENTS.override.md`, else `AGENTS.md`.
- Per directory from the Git root down to cwd: `AGENTS.override.md`, then `AGENTS.md`, then
  `project_doc_fallback_filenames`; "at most one file per directory". CLAUDE.md is ignored unless
  added to the fallback list (inference from the doc's rule).
- `project_doc_max_bytes` default 32 KiB for the combined chain (this repo's AGENTS.md is about
  15 KB). No imports, no `.local` file. `AGENTS.override.md` *replaces* AGENTS.md in that
  directory, so it is not an additive personal layer. Symlink handling: undocumented, unverified.

### Cursor (cursor.com/docs/context/rules and /docs/cli/using)

- Editor and CLI read `AGENTS.md` at the root and in subdirectories (nested, more specific wins).
- The CLI page says it "also reads `AGENTS.md` and `CLAUDE.md` at the project root (if present)
  and applies them as rules alongside `.cursor/rules`". With a `CLAUDE.md -> AGENTS.md` link the
  CLI may load the same text twice (unverified). No `.local` file documented. Secondary sources
  disagree about CLAUDE.md in the editor.

### pi (installed docs `docs/configuration.md` and the loader in `dist/core/resource-loader.js`)

- Verified here in source: per directory the first existing file of `AGENTS.override.md`,
  `AGENTS.md`, `AGENTS.MD`, `CLAUDE.md`, `CLAUDE.MD` wins; loaded from the agent dir
  (`~/.pi/agent`), cwd and every parent. `statSync` follows symlinks, so a symlinked file loads.
- No `.local` files, no documented `@` imports. `--no-context-files` disables discovery. Context
  files load regardless of project trust.

### GitHub Copilot CLI (docs.github.com, add custom instructions)

- Reads `~/.copilot/copilot-instructions.md`, `~/.copilot/instructions/**/*.instructions.md`,
  `.github/copilot-instructions.md`, `.github/instructions/**/*.instructions.md`, `AGENTS.md`,
  `CLAUDE.md`, `.claude/CLAUDE.md`, `GEMINI.md`, plus `COPILOT_CUSTOM_INSTRUCTIONS_DIRS`; root,
  cwd, intermediate and nested directories.
- All files are combined; "does not define a general precedence order"; identical duplicate
  copies are removed (so a symlinked CLAUDE.md is probably deduplicated; unverified).
- `@` references must stay inside the repo; absolute and `~/` paths are not loaded. No `.local`
  file documented. Changes need a new or resumed session.

### Gemini CLI (geminicli.com/docs/cli/gemini-md)

- Default `GEMINI.md`; `context.fileName` in `settings.json` can list `AGENTS.md` (doc example).
  Global, then workspace and parents, then just-in-time per touched directory; concatenated.
  `@file.md` imports, relative or absolute.
- Status: Google announced on 2026-05-19 a move to Antigravity CLI (`agy`), with a shutdown date
  of 2026-06-18 reported for at least some tiers (seen only in excerpts and secondary press;
  the scope per tier is uncertain). open-gsd already treats `gemini` as a retired runtime and maps
  `antigravity` to `GEMINI.md`. Low priority for ai-kit.

### Summary: who reads what

- `AGENTS.md`: every host above (Gemini only when configured).
- `CLAUDE.md`: Claude Code; opencode and pi as a fallback; Copilot CLI and Cursor CLI in addition.
- `CLAUDE.local.md`: Claude Code only.
- `AGENTS.local.md`: **no host reads it natively.** opencode can load it through `instructions`.
- Windows: any committed symlink becomes a one-line text file unless `core.symlinks=true` and the
  user can create symlinks. Hosts that read `CLAUDE.md` would then read the target path as text.
  The portable choice for a committed Claude file is a `CLAUDE.md` holding `@AGENTS.md`.

### Recommended layout (fits the owner's "AGENTS.md is mandatory" wish)

- Commit `AGENTS.md`. Commit `CLAUDE.md` either as a symlink to it (Linux/macOS only teams) or as
  a one-line `@AGENTS.md` file (portable). Either way Claude reads it once.
- Personal layer: gitignore both `AGENTS.local.md` and `CLAUDE.local.md`; keep the text in
  `AGENTS.local.md` and make `CLAUDE.local.md` a symlink to it (or `@AGENTS.local.md`). This is
  safe only because a `CLAUDE.md` exists; without one, `CLAUDE.local.md` suppresses AGENTS.md.
  Other hosts ignore `AGENTS.local.md` unless wired (opencode `instructions`).
- `.local` files exist per worktree only. A wizard that creates worktrees must copy or link them.

### open-gsd `claude_md_path` (local install `.claude/gsd-core`)

- Default `./.claude/CLAUDE.md` (`config-defaults.manifest.json`, `templates/config.json`). This
  repo sets `"claude_md_path": "./AGENTS.md"` with `"runtime": "claude"`.
- Free string, no validation of name: `AGENTS.local.md` is accepted. Used by `generate-claude-md`
  and `profile-user` (`bin/lib/profile-output.cjs`). Honored only for the claude runtime; any
  other runtime (or `GSD_RUNTIME`) overrides it with `getProjectInstructionFile` (`AGENTS.md` for
  codex/opencode/unknown, `.github/copilot-instructions.md` for copilot, `GEMINI.md` for
  antigravity).
- **Symlinks: not safe as the target.** Writes go through `platformWriteSync`, which writes a
  sibling temp file and renames it over the path. Verified here with a node test: renaming over
  `CLAUDE.md -> AGENTS.md` replaced the link with a regular file and left AGENTS.md unchanged.
  So `claude_md_path` must name the real file (`AGENTS.md` or `AGENTS.local.md`), never the link.
- **Second trap:** the GSD default `.claude/CLAUDE.md`, once created, counts as a CLAUDE.md for
  Claude Code and stops native AGENTS.md reading. curated-config should set `claude_md_path`
  explicitly, as the inputs file already says.
- Choosing `AGENTS.local.md` puts GSD-managed sections in a gitignored, per-worktree file that
  Claude sees only through the `CLAUDE.local.md` link and that no other host reads. Choosing
  `AGENTS.md` keeps them shared. Owner decision.

## 2. Naming the development pattern

Short definitions:

- **Walking skeleton** (Alistair Cockburn, *Crystal Clear*, 2004): "a tiny implementation of the
  system that performs a small end-to-end function", linking the main architectural parts; it
  grows, it is not thrown away. Freeman and Pryce (*Growing Object-Oriented Software, Guided by
  Tests*, 2009) add: the thinnest slice of real functionality you can build, deploy and test end
  to end automatically. It is about the first slice of a project.
- **Tracer bullets** (Hunt and Thomas, *The Pragmatic Programmer*, 1999): write thin but real,
  production-shaped code through all layers early, get feedback, then fill in. Unlike a
  prototype, it is kept.
- **Steel thread** (practitioner term, Rubick and others; two 2011-2012 academic papers): the
  first thin end-to-end path through the most important use case. Close to walking skeleton.
- **Vertical slice architecture** (Jimmy Bogard, 2018): a code-organization style, each request
  or feature is its own slice through all layers, coupling kept inside the slice. It is about
  structure, not about the order of work (source recalled, not fetched this session).
- **Outside-in development** (GOOS, BDD's "London school"): start from the user-facing edge with
  a failing acceptance test, mock the collaborators, then replace the mocks layer by layer inward.
- **Mock-first / contract-first** (API-first, OpenAPI; consumer-driven contracts such as Pact):
  agree on the interface and fake its data first so front and back can proceed independently.
- **"Make it work, make it right, make it fast"** (Kent Beck, c2 wiki): an order of priorities for
  one piece of code, not an architecture.
- Related: **elephant carpaccio** (Cockburn), an exercise in cutting very thin slices.

**Best fit:** the owner's cycle is *tracer-bullet vertical slices built outside-in*: each feature
is a vertical slice (tracer bullet / steel thread), the first one is the walking skeleton, and
inside each slice the order mocks -> front -> backend -> database -> real data is outside-in,
mock-first development. The tail (security -> infra -> observability -> accessibility) is a
per-slice "definition of done" (hardening gates); no classic name covers that tail. A short label:
**"outside-in vertical slices"**, with "walking skeleton" for slice one.

Caveat worth stating in the playbook: placing security and accessibility last within a slice
conflicts with the common "shift left" advice. The draft below keeps the owner's order but asks
for a security and accessibility note at the mock stage, checked at their own stage
(recommendation, not owner-decided).

**What open-gsd already encodes** (`references/planner-mvp-mode.md`, `mvp-concepts.md`,
`skeleton-template.md`, `workflows/plan-phase.md`, `workflows/new-project.md`):

- Tracer-first planning is the **default** (`TRACER_MODE=true`, `--no-tracer` opts out): every
  phase leads with one `type="tracer"` end-to-end task. Order: tracer slice (UI -> API -> DB) ->
  real data layer -> validation and error states -> production polish (loading, edge cases,
  accessibility checks). Horizontal "all schemas" / "all endpoints" tasks are forbidden.
- MVP mode (`--mvp`, ROADMAP `**Mode:** mvp`, or `workflow.mvp_mode`) adds the user-story goal
  (`As a / I want to / so that`), SPIDR splitting and user-flow-first UAT. The new-project prompt
  offers "Vertical MVP vs Horizontal Layers".
- Walking skeleton (Phase 1 + new project + `--mvp`): scaffold, one real DB read/write, one UI
  interaction wired to the API, deployment or a documented full-stack run, plus `SKELETON.md`.
- Security already runs as its own gate (`workflow.security_enforcement: true`, ASVS level 1,
  block on high in this repo's config; `/gsd-secure-phase`).
- Gaps against the owner's cycle: GSD's tracer is "production-quality, not a prototype" with
  stubs allowed only where fillable later, so an explicit **mocks stage** is not encoded; there
  is no **infra** stage beyond the skeleton's deploy; no **observability** stage; accessibility is
  only a "polish" item and the UI review.

## 3. Drafts (DRAFT, not owner-approved)

### Top rule for AGENTS.md (DRAFT, 5 lines)

```markdown
- **Build in vertical slices, outside-in.** Each feature is one thin slice through every layer,
  never a whole layer at a time. A slice moves through: mocks, basic UI, backend, database, real
  data, security, infra, observability, accessibility. It is done only when a real user can do the
  new thing on real data, secured, deployed, observable and accessible; then the next slice starts.
  Stage lenses and exit checks: `docs/playbooks/vertical-slices.md`.
```

### Never / avoid (DRAFT, top 3)

1. Never build a whole layer (all schemas, all endpoints, all screens) before one slice works end
   to end.
2. Never let mock data, stub auth or fake endpoints survive past the slice's real-data stage;
   mark every mock where it is created and remove it inside the same slice.
3. Avoid parking security, observability or accessibility in a later "hardening phase"; they are
   part of the slice's done check, and their risks are noted at the mock stage.

### Playbook outline (DRAFT) - `docs/playbooks/vertical-slices.md`

For every stage: goal, exit check, lens skill, GSD hook. Installed status checked with
`ls ~/.claude/skills ~/.agents/skills`, `~/.claude/plugins/marketplaces`, and `enabledPlugins` in
`~/.claude/settings.json`.

0. **Walking skeleton (first slice only)**. Exit: deployed or documented full-stack run,
   `SKELETON.md`. GSD: `/gsd-new-project --mvp`, plan-phase walking-skeleton gate.
1. **Mocks and contract**. Interface, fixtures, user story, security and accessibility notes.
   Lens: ponytail for architecture (installed: plugin `ponytail@ponytail` enabled, and
   `~/.agents/skills/ponytail*`); `superpowers:brainstorming` (enabled); `/gsd-sketch`,
   `/gsd-spike`.
2. **Basic UI**. Lens: impeccable (available this session; project-local
   `.agents/skills/impeccable` v4.8.0, currently untracked in this repo with `skills-lock.json`),
   frontend-design (plugin `frontend-design@claude-plugins-official` enabled); `/gsd-ui-phase`.
3. **Backend**. Lens: ponytail; `superpowers:test-driven-development` (enabled); GSD `--tdd`.
4. **Database**. Migrations and one real read and write. No dedicated database skill installed.
5. **Real data**. Mocks removed, end-to-end test on real data. Lens: playwright plugin (enabled)
   for browser flows; `/gsd-verify-work`.
6. **Security**. Lens: `security-review` (Claude Code built-in skill, available); `/gsd-secure-phase`;
   `claude-security` plugin is in the official marketplace and plugin cache but **not enabled**.
7. **Infra**. **No infra skill installed** (no Terraform, Kubernetes or cloud skill found). Nearest:
   `ai-kit-project-rules-docker`, `-cicd`, `-makefile` (audit-only lenses). Gap.
8. **Observability**. Logs, metrics, health checks for the slice. **No skill installed.** Gap.
9. **Accessibility**. Lens: impeccable (covers accessibility); `/gsd-ui-review` (6-pillar audit);
   playwright for keyboard and screen checks.
- **Review across stages**: `ponytail:ponytail-review`, `ponytail:ponytail-audit`, built-in
  `code-review`, `/gsd-code-review`.
- Appendix: how the stages map onto GSD's tracer order and which stages GSD does not cover
  (mocks, infra, observability).

## 4. Quota-wake facts for a playbook

### Already decided or shipped

- **ai-kit-session-wake** (`skills/ai-kit-session-wake/SKILL.md` and references): one wake per
  session, a systemd user timer that resumes the recorded session id with the host's own resume
  command. It fires **hourly** and gives up after **24 counted fires** (locked hard stop, about a
  day). With a host-reported reset time (`--reset-text` or `--reset-at`, recorded as *inferred*)
  the first wake lands **60 s after the reset**, and fires before it are not counted.
- A fire resumes only when the host process is gone. A live host stalled at its limit is logged
  ("host alive; log only") and still spends a fire; only the **in-session companion** (one one-shot
  job, e.g. CronCreate, after the reset, with a duplicate check) can resume it, and only for a
  reset-timed wake. **"Never create a repeated or fixed-interval job."**
- Opt-in, experimental StopFailure hook (`rate_limit`) refreshes an already-armed wake with the
  reset text; it never arms one; payload unverified. Reboot survival, the first real fire, and
  auth after reboot are unverified.
- Owner memory (2026-10-23): on a usage-limit cut in an autonomous run, finish the piece in hand,
  log, schedule a wake at reset plus a few minutes with the resume prompt, then report; delete the
  wake when the run finishes.
- Owner memory (2026-10-14, Phase 25): classify a quota stop by message *and route*. Router
  combos (`router-env/*`) recover after minutes to a couple of hours; direct providers (OpenCode
  Zen, Cursor API) usually do not recover by waiting.
- Owner memory (2026-10-13): both status lines color each quota window as a pace gauge, spend %
  versus elapsed %, bands 5 / 10 / 15 points. The Claude line reads the `rate_limits` buckets
  (`five_hour`, `seven_day`, with `resets_at`) in `tools/claude_segments.py`. Cursor quota has
  three segments (API, included, extra).
- Retry-ladder memory: transient errors retry the same session 3 times, then a new session 3
  times; quota or auth errors stop and report; never switch harness, provider or model.

### Missing for the owner's new wish (inputs file, "quota-wake cases")

1. **Periodic checks for an early reset.** The timer is hourly but acts only when the host is
   dead; for a live host the skill forbids repeated in-session jobs. Hoping for an early reset
   needs either relaxing that rule (owner decision) or a cheap probe that tells "still limited"
   from "reset early" without burning a fire. No such probe exists today.
2. **Keeping the 5-hour windows even (pacing).** The gauge is display-only. Nothing lets the agent
   read spend versus elapsed and slow down, pause or pick cheaper work when ahead of pace. A
   data path is needed: the status line receives `rate_limits` on stdin, but whether any hook or
   the agent can read it is unverified (a status-line-written cache file is one option).
3. **Anticipating the limit before the window ends.** Arming only happens after a failure
   (StopFailure) or by an executor. A threshold rule (for example spend above some % with time
   left) that arms a reset-timed wake *before* the cut, and finishes or checkpoints the current
   piece, does not exist.
4. **"Check the schedule".** Window start and reset times are known only through `resets_at` in
   the status-line feed. How Claude's 5-hour window starts (first message after the previous
   window?) is unverified here and should be checked against current Anthropic docs.
5. **Conflicts to settle:** the resilience-policy wish (periodic retries for quota errors that may
   reset early) versus the skill's "no fixed-interval job" rule and the 24-fire cap; the retry
   ladder's "quota stops and reports" versus "wake and continue"; router-route quota (wait) versus
   direct-provider quota (stop) inside one rule.
6. **Host coverage:** wakes exist for claude, pi, opencode and codex (codex parts unverified);
   Cursor has no surviving primitive.

## Sources

- Claude Code memory: https://code.claude.com/docs/en/memory
- opencode rules: https://opencode.ai/docs/rules/
- Codex AGENTS.md: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Cursor rules: https://cursor.com/docs/context/rules ; Cursor CLI: https://cursor.com/docs/cli/using
- Copilot CLI instructions: https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions
- Gemini CLI context: https://geminicli.com/docs/cli/gemini-md/ ; transition post (excerpt only):
  https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/
- pi: installed package docs `docs/configuration.md`, `docs/cli.md`, `dist/core/resource-loader.js`
- Walking skeleton: Cockburn, *Crystal Clear* (2004); https://accu.org/content/conf2012/Walking_skeleton.pdf ;
  https://oreilly.com/library/view/97-things-every/9780596800611/ch60.html
- Steel threads: https://www.rubick.com/steel-threads/
- Tracer bullets: Hunt and Thomas, *The Pragmatic Programmer* (1999). Vertical slice architecture:
  https://www.jimmybogard.com/vertical-slice-architecture/ (not fetched). Beck: c2 wiki
  "MakeItWorkMakeItRightMakeItFast" (not fetched).
- Local: `.claude/gsd-core/references/{planner-mvp-mode,mvp-concepts,skeleton-template}.md`,
  `workflows/plan-phase.md`, `bin/lib/profile-output.cjs`, `bin/lib/shell-command-projection.cjs`,
  `bin/lib/runtime-name-policy.cjs`, `skills/ai-kit-session-wake/`, the three memory files named
  in the task, `.planning/milestones/NEXT-MILESTONE-INPUTS.md` lines 443-457.
