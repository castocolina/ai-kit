# GSD config post-write sync: what GSD does, what ai-kit skips

Scope: gsd-core 1.16.0 (`~/.claude/gsd-core`, identical code in `ai-kit/.claude/gsd-core`) vs ai-kit
review tree `review-v13` (tip `0acbd06`). Read-only investigation; nothing was run that writes.
Paths below: `G=~/.claude/gsd-core`, `R=<scratchpad>/review-v13`.

## Verdict

The suspicion is half right. Some values in `.planning/config.json` are **baked into agent files
at install time**, so they need a sync step. But **GSD never runs that step on its own** after a
config write. Not in `config-set`, not in the `/gsd-settings` or `/gsd-config` workflows, and not
in any hook. The sync is a manual verb (`effort sync --apply`) or a reinstall. GSD's only
automatic behavior is a warning. So ai-kit is not bypassing a GSD hook. It inherits the same gap
and does not close it.

## 1. What GSD does after a config write

### 1a. `config-set` and the settings workflows have no side effects
- `G/bin/lib/config.cjs:670-684`: `setConfigValue` takes the lock, writes JSON, and returns.
  There is no regenerate, install, or sync call. `setConfigValues` (`:718-735`) behaves the same.
- `config.cjs:1282-1305`: `config-set-model-profile` writes `model_profile`. Its message says
  "Next spawned agents will use the new profile" (`:1320`), which means spawn-time resolution.
- `G/workflows/settings.md:546`: every non-capability key goes through `config-set`.
  `:521-527`: capability-gate keys go through `capability set <owner> --gate`. For gates that
  ends in the same `setConfigValues` (`G/bin/lib/capability-writer.cjs:249-251`). Only the
  `enabled` and `--runtime` materialize axes touch skill files (`:252-296`), and settings never
  uses them for gates. `:570-576` writes `~/.gsd/defaults.json` directly.
- `G/workflows/settings-advanced.md:450-451,494-499,522-526`: `runtime` and
  `model_profile_overrides.*` are written with `config-set` and nothing follows. The confirmation
  table even lists `effort.*` (`:798-802`). No workflow in `G/workflows` calls `effort sync`
  (searched for it: zero hits).

### 1b. Hooks only advise, they do not sync
- `~/.claude/hooks/gsd-config-reload.js`: a `FileChanged` hook (matcher `config.json`). It fires
  on any write to `<cwd>/.planning/config.json`, whatever made the write, and only injects a text
  summary as `additionalContext` (`:83-140`). It writes nothing. It also reports `config.models`,
  not `model_overrides` or `effort`.
- `gsd-session-state.sh:7-15`: a `SessionStart` reminder showing the STATE.md head. It is opt-in
  (`hooks.community: true`) and unrelated to config sync.

### 1c. The real sync channels (manual) and the warn-only guard

| Value | Claude | opencode | codex | kilo | cursor / pi |
|---|---|---|---|---|---|
| model (`model_profile`, `model_overrides`, `model_profile_overrides`, `models.*`, `model_policy`, `runtime`) | **spawn-time**: `init` resolves per agent (`G/bin/lib/init.cjs:892,1071,1487`). No sync needed (`G/references/model-profiles.md:229-232`) | **baked** into agent frontmatter at install (`G/bin/lib/runtime-artifact-layout.cjs:520-546` and `install-model-override-resolver.cjs:172-271`) | **baked** into `~/.codex/agents/*.toml`, explicit pins only (`stale-bake-guard.cjs:6-13`; `gsd-tools.cjs:2636-2676`) | **baked** (same as opencode) | not baked (`bakesStaticAgentModel` false). Session/spawn model, no sync |
| effort (`effort.default`, `effort.routing_tier_defaults.*`, `effort.agent_overrides.*`) | **baked** as `effort:` frontmatter in `agents/gsd-*.md`. The Claude descriptor has `agentFrontmatterExtensions:["effort"]`. "An effort config change has no effect until `gsd_run effort sync --apply`" (`model-profiles.md:233-241`) | baked as `variant:` (`runtime-artifact-layout.cjs:536-543`). `effort sync` has an opencode branch (`commands.cjs:780-783`) | `effort sync` codex branch strips stale model and effort lines (`commands.cjs:770-775`) | ignored | none |

The runtimes that bake models come from the runtime descriptors: **codex, kilo, opencode**
(`stale-bake-guard.cjs:30-40`, checked live against the registry).

Sync verbs:
1. `gsd-tools effort sync --apply [--runtime R] [--config-dir D]`
   (`G/bin/gsd-tools.cjs:4344-4370`; `commands.cjs:764-830`). **It is a dry run unless you pass
   `--apply`** (`:4349`). It merges `~/.gsd/defaults.json` with the project config, the way
   install does (`commands.cjs:753-763`).
   - **Target directory trap:** without `--config-dir`, it writes to the `agents/` folder of
     **the gsd-core copy you invoke**. A local Claude install writes to `<project>/.claude/agents`.
     Anything else writes to the global `~/.claude/agents` (`commands.cjs:87-109`).
2. Re-bake models on codex, opencode, or kilo: `gsd install --<runtime>`, `gsd update`, or
   `/gsd-update --reapply`. This is the wording of `stale-bake-guard.cjs:64-75`; the `gsd` binary
   is at `~/.local/share/pnpm/bin/gsd`. Per Phase 20 D-03, opencode needs a **local** install so
   that the project config gets merged.
3. Warn only: `warnIfStaleBake` runs on every `gsd-tools init *` (`gsd-tools.cjs:4715-4718`).
   It compares the newest config mtime (project walk plus `~/.gsd/defaults.json`) with the oldest
   `gsd-*` agent mtime, and only for the three baking runtimes (`stale-bake-guard.cjs:185-219`).
   **There is no guard for Claude effort.** A stale `effort:` value stays silent.

## 2. What ai-kit skips, per writer

### v1 CLI (`R/skills/ai-kit-gsd-curated-config`)
- Writes go through `config-new-project` and `config-set` only (`gsd_write.py:18-65`). That part
  is correct: it skips no hook, because there is none to skip.
- **Gap 1, the main one:** `apply-critical-agents` writes `effort.agent_overrides.<agent>=high`.
  This covers `gsd-code-reviewer` (`critical_agents.py:64`) and every heavy-tier agent
  (`:77`). Nothing in `cli.py` or `SKILL.md` runs or even mentions
  `effort sync --apply`. On Claude these overrides stay inert until the next GSD
  install or update re-bakes the files.
  - It is hidden today only by coincidence: the 1.16 defaults already give `gsd-code-reviewer`
    `effort: high` (both copies), and the heavy agents get `xhigh`.
  - So syncing would *lower* heavy agents from xhigh to high. That needs a deliberate decision,
    not just running the verb.
- **Gap 2:** `model_overrides.*`, `models.*`, `review.*` are fine on Claude because they resolve
  at spawn time. On an opencode, codex, or kilo host they are inert until a reinstall. v1 neither
  says so nor runs one.
- **Gap 3, wrong copy:** `gsd_catalog.py:16-33` resolves `~/.claude/gsd-core` first and never
  looks at `<project>/.claude/gsd-core`. GSD's own shim checks the project-local copy first
  (`G/workflows/settings.md:15`, `_gsd_at "${root}/.claude/gsd-core/..."`; `gsd-config`
  SKILL.md, execution_context). If v1 ever adds `effort sync`, the global copy would write the
  global agents, but a project with a local install loads its own `.claude/agents`.

### execute-gsd `gsd_config.py` (`R/skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_config.py`)
- It writes `.planning/config.json` directly with `cache_write_json`:
  - `runtime` (`:65-75`),
  - `model_profile_overrides.<runtime>.<tier>` (`:84-100`),
  - `model_profile` (`:115-125`),
  - `workflow.*` (`:155-195`).
- Effects of the direct write:
  - It skips `config-set` validation and `withPlanningLock`.
  - It still triggers the `FileChanged` reload hook.
  - It skips no sync step for `model_profile` or `workflow.*`, because Claude resolves those at
    spawn time.
- **Gap:** `adapter.py:150-157` writes `runtime=<vendor>` plus a tier override when the pick is
  not Claude. When that vendor is opencode, codex, or kilo, the model is baked, so the write is
  inert until a reinstall. The next `init` prints a stale-bake warning and the run carries on
  with the old model.
- Writing `runtime` also changes `resolveActiveRuntime` for the Claude session: it affects
  dispatch isolation (`gsd-tools.cjs:2580-2600`) and the stale-bake guard.
- **Stale claim:** `gsd_config.py:30-41` and `adapter.py:116-121` say
  `model_profile_overrides.claude.*` is dead. As of 1.16 it is honored on Claude (#4192,
  `G/bin/lib/model-resolver.cjs:138-162`; `model-profiles.md:225-226`).

### v2 design + Phases 17/18
- The design already plans for the sync. Spec `:89-91` and `:240` say follow-ups are printed and
  run only after approval. Phase 18 D-05 (`18-CONTEXT.md:78-85`) bundles `gsd install <host>` and
  `effort sync --apply` into one confirmation. Writes still go through `config-set` (D-07,
  `:88-94`). Phase 17 is read-only (inventory and recommend), so **no fix lands in 17**.
- Gaps in the v2 plan:
  1. D-05 names only opencode as a baking host. **codex and kilo bake too.**
  2. The install trigger is underspecified. It must fire when any model-family key changes on a
     baking host: `model_overrides`, `model_profile_overrides`, `models.*`, `model_policy`,
     `model_profile`, `runtime`. Not only "models".
  3. `effort sync` needs explicit `--apply` and the **right target**: the host's local
     gsd-tools, or `--config-dir <project>/.claude` (Claude) or the opencode config dir.
     Otherwise project-scoped effort gets baked into the global agents, or never reaches the
     agents the session loads.
  4. Verification gap (spec `:250-252`; Phase 19): `resolve-model` shows what *would* resolve,
     not what a baked agent file holds. On baking hosts, also assert that the agent
     frontmatter/TOML (or `variant:`) matches, or that there is no stale-bake warning. On Claude,
     assert the `effort:` lines.
  5. The command spelling should come from the guard's own text (`gsd install --<runtime>`) or
     `/gsd-update --reapply`, not `gsd install <host>`.

## 3. Environment drift: which copy wins

- Global and local ai-kit and tools-installer are all **1.16.0**, with identical `bin/` (only the
  vendor README differs). The `gsd-config-reload.js` copies are byte-identical.
  - Global manifest: scope global, 2026-10-13T16:10Z, agents mtime 12:40.
  - ai-kit manifest: scope local, 2026-10-09.
- Hooks: `~/.claude/settings.json` and both projects' `settings.local.json` each register **18**
  GSD hook commands. The command strings differ (`$HOME/...` vs `$CLAUDE_PROJECT_DIR/...`), so
  inside ai-kit **both sets run**. For config-reload that means a duplicate advisory message,
  which is harmless. No hook does sync, so the hooks do not decide "who wins" for sync.
- What does decide it:
  - **Workflows and gsd-tools:** the project-local copy wins (settings.md:15 shim order, and the
    gsd-config skill's local-first workflow lookup).
  - **Agent files:** project `.claude/agents/gsd-*.md` take precedence over `~/.claude/agents`
    for the same names (Claude Code subagent precedence). So in ai-kit and tools-installer, the
    local agents' `effort:` is what runs.
  - **`effort sync`:** run from the local copy, it writes the local agents
    (`commands.cjs:96-102`, manifest says runtime claude, scope local). Run from the global copy,
    it writes `~/.claude/agents`, which these projects ignore.
  - **ai-kit v1:** always picks the global copy (`gsd_catalog.py:16-17`). That is the mismatch.
- Also seen: `~/.gsd/defaults.json` holds `runtime: "codex"` and `resolve_model_ids: "omit"`.
  - It has no effect at spawn time under a project config: Branch A never opens it
    (`G/bin/lib/config-loader.cjs:342-356`).
  - But the **install-time** resolvers merge it (`install-model-override-resolver.cjs:172-191`).
    A project with no `runtime` key gets `runtime=codex` at bake time.
  - Worth flagging in v2 `inventory` conflicts, next to `model_policy`.

## 4. Minimal fix

1. **Phase 18 `apply`, where the code lands:** after a successful `config-set` batch, compute the
   follow-ups from the changed keys:
   - effort keys changed:
     `node <host-gsd-tools> effort sync --apply --runtime <host> --config-dir <scope-config-dir>`.
     Read the JSON `changes`.
   - model-family key changed **and** host in {opencode, codex, kilo}: local reinstall for that
     host (the Phase 20 D-03 command).
   - Gate both behind the D-05 grouped confirmation (already decided).
   - Amend 18 D-05 to cover codex and kilo, the full key list, `--apply`, and the target dir.
   - Add `host.py` resolution with **project-local gsd-core first**, mirroring the GSD shim.
2. **v1, kept per Phase 18 D-08:** this is the smallest change.
   - `apply-critical-agents` prints the exact `effort sync --apply` command, plus the reinstall
     hint on baking hosts, in its JSON output.
   - Or it runs a dry-run `effort sync` and reports the pending changes.
   - Also make `gsd_catalog.resolve_gsd_tools_path` try `<project-dir>/.claude/gsd-core` first.
   - Decide the xhigh-to-high downgrade before turning on `--apply`.
   - Run `/skill-judge` on any SKILL.md change, per the project rule.
3. **execute-gsd:**
   - Route `runtime` and tier writes through `config-set`, or at least run the stale-bake check.
     It is cheap: `gsd-tools init` already prints the warning to stderr.
   - Refuse or warn when the picked runtime bakes models and no local reinstall has been
     approved.
   - Fix the stale #4192 comment.
   - This is outside v1.3 phases 17/18. Track it as a separate todo, or fold it into Phase 20's
     "small local fixes" if found live.
4. **Verification, Phase 19/20:** extend the `resolve-model` proof with a check of the baked
   files (`effort:` on Claude; `model:`/`variant:` on opencode; TOML on codex).
