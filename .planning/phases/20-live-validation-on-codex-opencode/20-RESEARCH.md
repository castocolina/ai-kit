# Phase 20: Live Validation on Codex + Opencode - Research

**Researched:** 2026-10-17
**Domain:** live host validation of `ai-kit-gsd-curated-config` on codex-cli 0.162.1 and opencode v2.0.31, reusing the Phase 19 harness (`tests/gsd_curated_eval.py`) parameterized by host
**Confidence:** MEDIUM-HIGH (harness and gsd-core claims read this session; live host behavior is unverified by design: no model calls were allowed in this research)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Carried forward (locked elsewhere, do not re-decide)**
- **19 D-03:** a real `apply` runs only on scratch projects (a copy of this repo's `.planning/config.json`, plus an empty project). On ai-kit itself, only `inventory` and `apply --dry-run`.
- **19 D-04/D-05:** the 5-combination `resolve-model` matrix for 35 agents, run with `GSD_RUNTIME=codex` and `GSD_RUNTIME=opencode` here, recorded as live evidence.
- **17 D-02:** codex's native sol/terra/luna slots are kept when valid; opencode's `anthropic/*` slots get overridden.
- **17 D-04:** the user's routers win the slot for their declared role.

**D-01:** Headless iteration first, then a final interactive run.
- Iterate and fix using headless runs launched from the Claude session (`codex exec ...`, `opencode run ...`) with a cleaned env: remove `CLAUDECODE` and other outer-host signals.
- Only the user's own interactive session in each host counts as the EVAL-04/EVAL-05 evidence.
- For that run, give the user a short script (steps and prompts to paste). Afterwards, analyze the artifacts it leaves: `plan.json`, the resulting `config.json`, the smoke log and the `resolve-model` output.
- When a headless dispatch is killed or hangs, follow the user's memory rule: probe with a short foreground run that polls output growth before retrying.
- Known transient blockers: opencode's xai/grok lane billing block (2026-09-14) and opencode's sandbox denying `external_directory` access to `~/.claude/gsd-core` (v1.1 Phase 07). If either recurs, record it as an environment finding, not a skill bug.

**D-02 (host precedence, amends 16 D-01):** The host order becomes pi > opencode > cursor > codex > claude, with claude last. Rationale: env signals are inherited, and Claude is the user's usual outer orchestrator (it dispatches cross-AI review/execution to codex and opencode). A codex launched from Claude carries `CLAUDECODE`, and under the previous order it would read as claude. The reverse nesting (claude launched from codex) is rare for this user and is accepted as a known limitation, documented in the detection docstring. Headless runs also clean the env (D-01), as belt and braces. Phase 16 has not been planned yet, so this is a free change. 16-CONTEXT D-01, REQUIREMENTS SPEC-01 and the ROADMAP Phase 16 success criteria are updated to match. Reversibility: costly.

**D-03 (opencode model application, amends 18 D-05):** On an opencode host, the models written by `apply` only take effect through a local (project) gsd install.
- Evidence: gsd-core `install-model-override-resolver.cjs` bakes models into agent frontmatter at install time. It merges `<project>/.planning/config.json` only when the install target is inside a project. A global install reads only `~/.gsd/defaults.json`.
- So the opencode follow-up in 18 D-05's grouped confirmation is a local gsd install into the target project (e.g. `.opencode/`).
- The report also explains, without running it, the global alternative (`~/.gsd/defaults.json` plus a global reinstall), which would change every opencode project.
- The user's global opencode setup is never modified.
- Research must confirm: the exact local-install flag/command for the installed gsd version; that opencode prefers project `.opencode/agents` over the global agents; whether the `.opencode/` output should be gitignored or committed in target projects.

**D-04 (fix policy):** Small, local fixes (a parser, a flag, a message, one module) are fixed within Phase 20, each with a regression test. Anything that changes a decision recorded in a CONTEXT.md, or touches more than one module, becomes a decimal phase (`/gsd-phase --insert 20` -> 20.x) with its own plan and verification.

**D-05 (codex env signal):** confirm `CODEX_THREAD_ID` and/or `CODEX_VERSION` in the user's interactive codex session; update the detection docstring label from "observed in session snapshots" to "live-verified"; drop whichever signal does not appear. Refined 2026-10-14: `CODEX_VERSION` has 0 hits in the codex 0.153.4 binary; its only hits under `~/.codex/sessions` are the user's own `env | grep` probe. `CODEX_THREAD_ID` is a shell-snapshot override in the binary and appears in 20 snapshots. Expected outcome: `CODEX_THREAD_ID` confirmed, `CODEX_VERSION` dropped from `_RUNTIME_ENV_SIGNALS` and from the 16.1 D-14 scrub list. `CODEX_THREAD_ID` stays scrubbed (gsd-core reads it as a workstream key). The interactive run prints all `CODEX_*` names, names only. If `CODEX_THREAD_ID` is also absent, codex env detection is empty and a replacement signal is chosen from that names list.

**D-06 (opencode lane from an opencode host):** determine whether `/gsd-review` self-skips the opencode lane on an opencode host, or whether it can be used intentionally (e.g. a different provider/model through the same CLI); reflect the answer in `recommend`'s lane eligibility and in SKILL.md. Until settled, the spec's default stands: not recommended.

**D-07 ("Planned == baked" is its own check):** The `GSD_RUNTIME=<host>` `resolve-model` matrix cannot prove R5/R7.
- The installer bakes through `readGsdRuntimeProfileResolver`, whose runtime is the project config's `runtime`, else `~/.gsd/defaults.json`'s, else null (bakes nothing). It never reads `GSD_RUNTIME` (gsd-core 1.16.0 `install-model-override-resolver.cjs:172-197`).
- Scratch experiment: with this machine's global `runtime: "codex"` and no project `runtime`, opencode agents bake bare `gpt-5.6-*` ids, which `opencode debug agent` parses as `providerID=gpt-5.6-terra, modelID=""`.
- The chain recorded per agent: plan -> project-local `resolve-model` -> baked `model:` line -> `opencode debug agent <name>` (model-free; non-empty `providerID`/`modelID`, id in `opencode models`). Codex: explicit `model_overrides` pins only, read from `.codex/agents/gsd-*.toml` with `tomllib`.
- Baked values are compared only after the post-apply installer run (18 D-37). R1's idempotency edge holds only for unchanged config.

**D-08 (`runtime` is a managed key on opencode and codex; amends 17 R5, adds 17 D-23):** `recommend` emits `runtime: <host>` (`source: preset`). On codex the tier layer is labelled "resolve-model only": `generateCodexAgentToml` embeds `model =` only for an explicit `model_overrides` entry (#3241). Laya amend_both 0.90.

**D-09 (scratch installs run under a throwaway HOME):** seeded with a copy of the real `~/.gsd/defaults.json`.
- A `--local` install still runs `writeNonClaudeDefaults` (rewrites `~/.gsd/defaults.json`) and `cleanupLegacyGsdCc` (scans `~/.config/opencode`, `~/.codex`) (`bin/install.js:6972-7014, 12234, 14360-14375`). On this machine the write is a no-op by luck.
- `GSD_TEST_MODE=1` is rejected: it also skips the opencode permission writer.
- 18 D-37's approval block must disclose these global writes (amended there).
- Laya isolated_home 0.44 (fb), TypeSafe 0.96.

**D-10 (the "global config unchanged" prohibition is a semantic allowlist guard, not a directory checksum):**
- Files: `~/.codex/{config.toml, agents, hooks.json}`, `~/.config/opencode/{opencode.jsonc, agents, commands, skills, plugins}`, `~/.gsd/defaults.json`.
- `config.toml` is compared with `tomllib` minus any `projects."<scratch path>"` table: the codex TUI persists project trust there (`tui-project-trust-write`).
- opencode's own `package.json`/`bun.lock` refresh is excluded. The 20-SPEC prohibition row is amended.

**D-11 (the host is never a review lane; settles D-06's policy half):**
- gsd-core has no code-level self-skip: `SELF_CLI` is deterministic only for antigravity, cursor and claude, and `auto` (LLM-judged) elsewhere (`workflows/review.md:126-149`). `resolveReviewerSelection` takes no host input.
- `recommend` never proposes the host slug, with a test. A copied `review.default_reviewers=["opencode"]` on an opencode host is flagged for replacement (17 D-08). SKILL.md documents the manual `review.reviewer_instances` route as user-owned.
- The live run still records the mechanics both ways (`--opencode` and `default_reviewers`), two trials each.
- Laya instance_after_proof 0.41 (fb), TypeSafe never_host_lane 0.98.

**D-12 (GSD-generated paths are gitignored by prefix; baked output is never committed):**
- opencode: `.opencode/{gsd-core/, agents/gsd-*, commands/gsd-*, skills/gsd-*, plugins/gsd-core.js, gsd-*.json}`; the `.codex/` equivalents.
- Codex agent TOMLs bake an absolute `gsd-core/` path; the opencode permission writer adds an absolute allow and an unpinned `mcp.gsd`.
- A blanket ignore is wrong: opencode drops its own `.gitignore` into `.opencode/`, so the dir is shared by design. curated-config only reports this; it never edits `.gitignore`.
- Answers D-03's open gitignore question. Laya prefix_ignore 0.50 (fb), TypeSafe 0.86.

### Claude's Discretion
- The headless command templates.
- The interactive-run script format.
- The names of the evidence files (e.g. `20-SMOKE-CODEX.md`, `20-SMOKE-OPENCODE.md`).
- How the env is cleaned for headless runs.

### Deferred Ideas (OUT OF SCOPE)
- Open for research (2026-10-14): whether `-c 'projects."<scratch>".trust_level="trusted"'` gives session-only codex trust, and whether project `.codex` agents load only after trust; whether `CODEX_THREAD_ID` is present in the TUI shell and `codex exec`; the opencode background `@opencode-ai/plugin` install inside scratch `.opencode/` dirs (a network side effect); an upstream gsd-core issue about `--local` writing `~/.gsd/defaults.json`.
- Process-tree host detection (walking parent PIDs for the nearest CLI) was considered and not chosen. Revisit only if env-signal ordering proves insufficient in real use.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-04 | Live smoke on the codex host, including confirmation of the codex session env signal | Harness reuse plan (smoke + oracle extension, spike passed 350/350 checks), codex env-name evidence (both `CODEX_THREAD_ID` and `CODEX_VERSION` present in a 0.162.1 `codex exec` session), D-09/D-10 isolation mechanics, what headless can and cannot prove |
| EVAL-05 | Live smoke on the opencode host, including whether the opencode review lane is usable from an opencode host | opencode v2.0.31 facts (service, `OPENCODE=1`, no `debug agent`), local install path, planned==baked chain, D-11 already enforced in code, gsd-core 1.17.0 opencode-2.x adaptation |
</phase_requirements>

## Summary

Phase 20 is mostly harness generalization, not new product code. The Phase 19 smoke (`tests/gsd_curated_eval.py`, `run_smoke`) already drives the real product (`cli.main` in-process) against scratch projects and a seeded cache. Three things in it are claude-specific and block a codex or opencode run: (1) `run_matrix` raises a refusal for any non-claude host because `promised()` returns tier aliases; (2) `_scratch_project` symlinks this checkout's `.claude/gsd-core` into every scratch project, which would shadow a host-local install (`local_gsd_core_roots` tries `.claude/gsd-core` before `.codex/gsd-core`); (3) the protected-set snapshot covers `~/.claude`, `~/.gsd`, `~/.cursor` but not the codex and opencode allowlist D-10 names. All three are small, in one module (`tests/gsd_curated_eval.py`), so they stay inside D-04's "fix within the phase" threshold.

The central de-risking result of this research: a ~15-line host-aware `promised()` (override, then phase shift, then tier -> `model_profile_overrides.<host>.<tier>` set or keep entry, then `RUNTIME_PROFILE_MAP[host][tier]`) passes all 10 rows x 35 agents (350 checks) on both `GSD_RUNTIME=codex` and `GSD_RUNTIME=opencode` against the installed gsd-core 1.17.0, using the existing bundle builder. Control 1 as designed in Phase 19 does not transfer (non-claude plans contain no `resolve_model_ids` entry to remove), but a replacement control (apply a plan copy without its `model_overrides.*` entries; those agents must then fail) was spiked and is discriminating on both hosts (codex 2 of 2, opencode 6 of 6).

Two expectations in the CONTEXT/SPEC are stale and must be re-decided from live evidence, not carried forward. (a) D-05 expects `CODEX_VERSION` to be dropped. In codex 0.162.1 the binary now contains the string, and a 2026-10-14 `codex exec` session (cli_version 0.162.1) dumped `CODEX_VERSION`, `CODEX_THREAD_ID`, `CODEX_SESSION_ID`, `CODEX_CI`, `CODEX_SANDBOX_NETWORK_DISABLED` and `CODEX_APPLY_PATCH_PRESERVE_LINE_ENDINGS` in its tool env. The likely outcome is "keep both, relabel live-verified" once the interactive session confirms. (b) D-07's `opencode debug agent <name>` does not exist in opencode v2.0.31; the subcommand is `opencode debug agents` (list), served by the shared background service on a fixed port. That service is the biggest isolation hazard for the opencode runs and must be bypassed with `--standalone` wherever the command accepts it.

**Primary recommendation:** Extend the existing Phase 19 harness in place (host-aware `promised`/controls, `--host` smoke with a real per-scratch-project local install under a throwaway HOME, a semantic allowlist snapshot for codex/opencode), run headless iterations through the existing cross-AI runner, and ship a short per-host interactive script whose run is a `human_verification` item; never claim headless runs satisfy EVAL-04/05.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Host detection from env (`detect_current_runtime`) | Python library (`ai_kit_spec/detection.py`) | Host process env | The table is the single source of truth (AGENTS.md); the host only supplies env |
| Smoke orchestration, oracle, snapshot guard | Dev harness (`tests/gsd_curated_eval.py`) | Real `gsd-tools.cjs` (node) | Harness calls the product in-process and real gsd-tools as subprocess; not shipped runtime code |
| Model baking into agent files | gsd-core installer (`bin/install.js`, external) | Project `.planning/config.json` | ai-kit only plans and reports; the installer bakes. ai-kit must not reimplement baking |
| Per-call model resolution | gsd-core `resolve-model` (external) | Plan entries (`model_profile_overrides`, `model_overrides`) | The oracle derives the promise from the plan plus live tables, never from the applied config |
| Host CLI global config protection | Harness snapshot (allowlist) | Throwaway HOME for installers | Prevention (HOME) plus detection (snapshot); either alone is insufficient |
| Headless dispatch to codex/opencode | Cross-AI runner (`cross-ai.mjs`) | `child_env` scrub | R8 requires the runner with the 16.1 scrub |
| Review-lane eligibility | `cross_ai.eligible_lanes` + `plan_io._host_reviewer_problem` | SKILL.md docs | Already enforced in code at two layers; Phase 20 adds a regression test and docs |

## Standard Stack

### Core
| Library / tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| `tests/gsd_curated_eval.py` (in repo) | HEAD | Smoke, matrix, snapshot, secret-scan, digest | Phase 19's verified harness; Phase 20 spec says "parameterized by host" |
| `@opengsd/gsd-core` | 1.17.0 | Installer and `gsd-tools` under test | `.claude/gsd-core/VERSION` = 1.17.0 [VERIFIED: file read this session]; R1 pins to the claude host version |
| `tomllib` (stdlib, py312) | stdlib | Parse `.codex/agents/*.toml`, semantic `config.toml` compare | Project is stdlib-only for runtime code; `requires-python >=3.12,<3.13` [VERIFIED: pyproject.toml:9] |
| `unittest` via `tools/run_unittest_parallel.py` | stdlib | Tests | AGENTS.md Testing section |
| `node` | via volta | Real `gsd-tools.cjs` | Already required by the e2e tier |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `codex` CLI | 0.162.1 [VERIFIED: `codex --version`] | Host under test | Headless: `exec --ephemeral --ignore-user-config` |
| `opencode` CLI | v2.0.31 [VERIFIED: `opencode --version`] | Host under test | Headless: `run --standalone --auto --format json` |
| `cross-ai.mjs` runner | template 3 | Headless dispatch with scrub, timeout, status line | R8; `--print-argv` verifies argv without a model call |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New per-host scripts | Parameterize the Phase 19 smoke | Locked by spec ("parameterized by host"); fewer files |
| `npx -y ... @opengsd/gsd-core@1.17.0` in smoke | Run `node <pnpm-store>/.../bin/install.js` from the already-fetched 1.17.0 package | npx needs network, and the user's `npx` is an alias for `pnpm dlx` (unverified). The pnpm store copy is a complete package with `node_modules` [VERIFIED: directory listing]. Planner decides; see Open Question 1 |
| `GSD_TEST_MODE=1` for the installer | Throwaway HOME | Rejected by D-09 (also skips the opencode permission writer) |

**Installation:** no new dependencies. Installer invocation shape for a scratch project (cwd MUST be the scratch project; local target is `process.cwd()/.opencode` or `.codex`, bin/install.js:8463, 9587):
```bash
# cwd = scratch project; HOME = throwaway dir seeded from ~/.gsd/defaults.json if it exists
HOME="$THROWAWAY" node "$INSTALLER_DIR/bin/install.js" --opencode --local --no-legacy-cleanup
```
`--no-legacy-cleanup` exists in 1.17.0 [VERIFIED: bin/install.js usage text and `parseNoLegacyCleanupArg`]. The locked Phase 18 R14 argv (`followups.installer_argv`) omits it on purpose (it discloses the home scan instead), so the throwaway HOME is the primary guard and the flag is belt and braces for the smoke only.

**Version verification:** `node -e` on the worktree: `cat .claude/gsd-core/VERSION` = `1.17.0`; pnpm store holds 1.12.0, 1.13.0, 1.14.0, 1.16.0, 1.17.0 [VERIFIED: directory listing].

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `@opengsd/gsd-core` | npm | package since 1.12.x; latest published 2026-10-14 | 6,897/wk | github.com/open-gsd/gsd-core | SUS (`too-new`) | Flagged. Already the project's installed gsd-core 1.17.0 and a long-standing dependency, so the SUS reason is the latest-publish date only. Planner: add a `checkpoint:human-verify` before any network fetch of it; prefer the already-fetched pnpm store copy (no new download) |

[VERIFIED: `gsd-tools query package-legitimacy check --ecosystem npm @opengsd/gsd-core` this session; `postinstall: null`]

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** `@opengsd/gsd-core` (reason `too-new`, see above). No other package is installed by this phase.

## Architecture Patterns

### System Architecture Diagram

```
 user's interactive host session (codex TUI | opencode TUI)  <-- the only EVAL-04/05 evidence
 headless iteration: claude session -> cross-ai.mjs (scrub) -> codex exec | opencode run
        |  (host shell tool, real HOME, real host auth)
        v
 python3 tests/gsd_curated_eval.py smoke   (host detected from the shell tool's env)
        |
        +--> snapshot BEFORE (strict claude/gsd set + codex/opencode allowlist, TOML semantic)
        |
        +--> per scratch project (system temp, NOT under the repo):
        |       git init -> installer(--<host> --local, cwd=project, HOME=throwaway)  [R1]
        |       inventory (scope local, version pinned)  -> recommend -> plan.json
        |       dry-run -> real apply -> second apply -> forced-failure restore
        |       re-run installer (post-apply bake)  -> planned==baked chain [D-07]
        |            plan -> project-local resolve-model -> baked agent file -> (opencode) debug agents
        |
        +--> matrix: 5 combos x {P1,P2} x 35 agents, GSD_RUNTIME=<host>, host-aware oracle + control
        |
        +--> snapshot AFTER -> diff == nothing (TOML minus projects."<scratch>")
        v
 evidence file (placeholders only) -> secret-scan -> committed in the phase dir
```

### Recommended Project Structure
```
tests/gsd_curated_eval.py            # extend in place: promised/compare host-aware, smoke --host install step,
                                     #   allowlist snapshot, planned==baked check (one module, D-04 in-phase)
tests/test_gsd_curated_eval.py       # replace test_matrix_refuses_non_claude_host; add host oracle,
                                     #   control, allowlist, baked-chain, scratch-location tests
tests/test_ai_kit_gsd_curated_config_matrix.py   # e2e (real node): per-host matrix incl. controls
skills/ai-kit-spec-review/ai_kit_spec/detection.py   # codex labels / table per live finding (one module)
.planning/phases/20-.../20-SMOKE-CODEX.md, 20-SMOKE-OPENCODE.md, 20-INTERACTIVE-*.md  # evidence + user scripts
```

### Pattern 1: Host-aware oracle (spiked, 350/350 on each host)
**What:** For a non-claude host the promise is `model_overrides.<agent>` if present, else the tier (phase shift `models.<phase>` wins over the profile tier) resolved through `model_profile_overrides.<host>.<tier>` (plan `set` or `keep`), else the live `RUNTIME_PROFILE_MAP[host][tier].model`. Tier is checked only for agents without a `model_overrides` entry (resolve-model reports `tier: unknown` for override agents on both hosts [VERIFIED: spike output]).
**When to use:** `run_matrix(host != "claude")`; replaces the `MESSAGE_NON_CLAUDE` refusal.
**Example:**
```python
# Source: validated spike (tmp probe, not committed); tables from gsd-core 1.17.0
# live_tables() must also export RUNTIME_PROFILE_MAP from bin/lib/model-catalog.cjs
def entries(plan):  # set AND keep: codex's native sol/terra/luna slots are `keep` entries
    return {e["key"]: e["value"] for e in plan["entries"]
            if e.get("op") in ("set", "keep") and isinstance(e.get("key"), str)}

def promised_host(agent, plan, tables, host):
    s = entries(plan)
    if f"model_overrides.{agent}" in s:
        return str(s[f"model_overrides.{agent}"]), None
    phase = tables["phase"].get(agent)
    shift = f"models.{phase}" if phase else None
    tier = s[shift] if shift in s else tables["profiles"][agent][plan["profile"]]
    ent = s.get(f"model_profile_overrides.{host}.{tier}") or tables["runtime_profiles"].get(host, {}).get(tier)
    return (ent.get("model") if isinstance(ent, dict) else ent) or "", tier
```
Empty result (no plan entry and no builtin for that host/tier) is the real "promised inheritance" case; derive it here instead of keeping the speculative `inheritance_promised` flag (resolves Phase 19 L4: the flag was kept for Phase 20; Phase 20's actual need is this derived rule, so delete the flag and its test or keep it only if a case exists).

### Pattern 2: Replacement Control 1 for non-claude hosts (spiked)
Apply a copy of the plan with every `model_overrides.*` entry removed; each agent that had one must now mismatch the promise. Codex: 2 of 2 failed; opencode: 6 of 6 failed [VERIFIED: spike]. Keep Control 2 (clean P1 must pass). Skip the "informational runtime row" for non-claude hosts (its purpose, the omit-poison runtime interaction, is claude-only; non-gating).

### Pattern 3: planned == baked chain (D-07) per host
- opencode: after the post-apply installer run, parse `<project>/.opencode/agents/gsd-*.md` frontmatter `model:`; compare to the oracle; agents with no promised model must have no `model:` line (J7 omit). Resolve with the project-local `gsd-tools` (`.opencode/gsd-core/bin/gsd-tools.cjs`), whose `.gsd-runtime` marker (written by the installer, bin/install.js:12117) makes `GSD_RUNTIME` unnecessary. Compare `model:` only: opencode agents may also get a `variant:` line, emitted only when an effort config exists (`runtime-artifact-layout.cjs`).
- codex: only explicit `model_overrides` pins are baked into `.codex/agents/gsd-*.toml` as `model = "..."`; read with `tomllib`; every other agent must have no `model` key (inherits the session model) [VERIFIED: bin/install.js:4163-4186 comment and code, gsd-core 1.17.0 store copy].
- Compare only after the post-apply installer run; a second install of unchanged config must change no agent file (R1 idempotency edge: hash the agents dir before and after).

### Anti-Patterns to Avoid
- **Scratch projects under the repo tree** (`./tmp/...`): the installer's `_findAncestorGsdConfigPath` walks up 8 levels to the first `.planning/config.json` [CITED: install-model-override-resolver.cjs doc comment, read this session]. An "empty" project (b) under the repo would inherit ai-kit's own config and bake wrong models. Keep `tempfile.mkdtemp()` scratch in the system temp dir.
- **Symlinking `.claude/gsd-core` into non-claude scratch projects:** `local_gsd_core_roots` order is `gsd-core`, `.claude/gsd-core`, `.codex/gsd-core` [VERIFIED: gsd_tools.py:92-93], so the symlink wins on codex. Only claude scratch projects keep the symlink.
- **Running `opencode run` without `--standalone`:** attaches to the user's long-lived managed service (see Pitfall 1).
- **Reading the host's credential or service files** to "copy auth": unnecessary and forbidden (see Security).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Host model baking | A model-writer for agent files | gsd-core installer `--<host> --local` | The installer owns the precedence chain; ai-kit only reports (18 D-05, D-03) |
| Tier -> model for a host | Hardcoded gpt-5.6-* / glm tables in the harness | Live `RUNTIME_PROFILE_MAP` from `model-catalog.cjs` + plan entries | Tables move between gsd-core releases; the harness already refuses unchecked lines (`GSD_CORE_PREFIXES`) |
| TOML parsing | Regex over `.codex/agents/*.toml` or `config.toml` | `tomllib` | stdlib, py312 |
| Dispatch/timeout/scrub for headless runs | New subprocess wrapper | `cross-ai.mjs` + `child_env` | R8; runner has group-kill, status line, `--print-argv`; the Phase 19 reaper is also reusable |
| Host detection | A second env table | `detection.RUNTIMES` | AGENTS.md: single source of truth |
| Secret scan of evidence | A new scanner | `gsd_curated_eval.py secret-scan` | Existing, canary-tested |

**Key insight:** every piece of Phase 20 either already exists in the harness or is a thin host parameter on it. The only genuinely new mechanisms are the allowlist snapshot (TOML semantic compare), the per-scratch local install under a throwaway HOME, and the baked-agent readers.

## Runtime State Inventory

> Not a rename/refactor phase. Omitted. (Isolation concerns are covered under Common Pitfalls and Security.)

## Common Pitfalls

### Pitfall 1: opencode v2 background service is machine-wide, on a fixed port
**What goes wrong:** `opencode run` (and `debug agents`, `models`) without `--standalone` talk to a managed service. In this session a scratch-HOME `opencode debug agents` failed with `Managed service port 49374 on 127.0.0.1 is already in use by another process` [VERIFIED: command output], because the user's service (`opencode serve --service`) was already running. Scratch HOME/XDG therefore does NOT isolate; a non-standalone run would attach to the user's service and "serve whichever config it booted with" (gsd-core's own comment, `opencode-version.cjs`).
**How to avoid:** use `opencode run --standalone` for all headless runs (flag exists [VERIFIED: `opencode run --help`]). `opencode debug agents` and `opencode models` document no `--standalone` in `--help` (`debug agents` rejected it: `Unrecognized flag`), so for the precedence/loader proof use a standalone `run`-based probe, or accept the shared service for read-only listing and record it (see Open Question 2). Other agents run opencode review lanes on this machine concurrently (a `review-lane invoke --slug opencode` process was visible), so never stop or restart the user's service.
**Warning signs:** `Server process exited with code 1`; port-in-use message; results that reflect the user's real config.

### Pitfall 2: stale expectation that `CODEX_VERSION` is absent
**What goes wrong:** D-05/SPEC-01 wording expects it dropped. Evidence now says both names are real in 0.162.1 (see Code Examples, "Codex env evidence"). Dropping it blindly would remove a working signal.
**How to avoid:** decide strictly from the interactive session's recorded NAMES; keep each name that appears. Update the unit test that pins the table (`tests/test_ai_kit_spec_runtimes_table.py` lists both names) in the same commit.

### Pitfall 3: `opencode debug agent` (singular) no longer exists
v2.0.31 has `opencode debug agents` (list all agents) [VERIFIED: `opencode debug --help`]. Output shape is unverified (not run against a real service here). The D-07 chain's last link must be rewritten as "listing contains `gsd-*` agents whose model matches", with the parse written after the first observation.

### Pitfall 4: global writes by `--local` installs
`writeNonClaudeDefaults` writes `~/.gsd/defaults.json` using `os.homedir()` (honors `$HOME`) [VERIFIED: bin/install.js:7087-7137]. `~/.gsd` does not exist on this machine today [VERIFIED: ls failed], so the "no-op by luck" in D-09 is now false: a real-HOME install would CREATE `~/.gsd/defaults.json` with `runtime` and `resolve_model_ids: "omit"`. Throwaway HOME is therefore mandatory; seed it from `~/.gsd/defaults.json` only if that file exists (tolerate absence). The strict snapshot already lists `~/.gsd` and `~/.gsd/defaults.json`.

### Pitfall 5: host env leakage from the outer Claude session
A 0.162.1 `codex exec` session started from Claude carried `CLAUDE_CODE_*` variables in its tool env alongside `CODEX_*` [VERIFIED: names-only scan of a session file]. D-02's order (codex before claude) handles detection; scrub with `child_env` for headless runs anyway (note: `child_env` removes the target host's own signals from what the child *inherits*, which is harmless because the host sets its own again).

### Pitfall 6: `_cmd_smoke` temp scratch vs host sandboxes
Codex's workspace-write sandbox allows cwd, `/tmp` and `$TMPDIR` [CITED: cross-ai.mjs header, `--codex-sandbox`]; headless runs use `--dangerously-bypass-approvals-and-sandbox` anyway. opencode's `external_directory` denial mediates tool-call paths, not the paths a spawned python process opens; the smoke command line contains only repo-relative paths. If the denial still fires, record it as an environment finding (D-01).

### Pitfall 7: SKILL.md and note strings are pinned by tests
Notes such as `followups._opencode_root_note` ("inferred (unverified until Phase 20)"), `_codex_installer_note`, `_config_dir_note`, `host.py` shortcut comment, the SKILL.md Limits row ("local gsd root ... unverified"), and `cross_ai.OPENCODE_EFFORT_EFFECT` (line 182) all encode "unverified until Phase 20". After live evidence, update each with its test in the same change; SKILL.md edits trigger the `skill-judge` loop (AGENTS.md rule) and `TestSkillDocCommands`.

### Pitfall 8: sequential smoke steps and the evidence digest
Evidence must carry only placeholders (`<scratch>`, `<home>`, `<worktree>`) via `_smoke_placeholders`, names only for env variables, and pass `secret-scan` before commit.

## Code Examples

### Codex env evidence (names only), the basis for D-05
```
# [VERIFIED: names-only scan of ~/.codex/sessions this session; values never printed]
session: originator=codex_exec, cli_version=0.162.1, source=exec, 2026-10-14
tool-env names present: CODEX_APPLY_PATCH_PRESERVE_LINE_ENDINGS, CODEX_CI,
  CODEX_SANDBOX_NETWORK_DISABLED, CODEX_SESSION_ID, CODEX_THREAD_ID, CODEX_VERSION
# [VERIFIED: byte scan of the 0.162.1 binary] "CODEX_THREAD_ID" and "CODEX_VERSION" are adjacent
# entries in one string list next to CODEX_PERMISSION_PROFILE (shell-snapshot protected-env list).
```
This is `codex exec`, not the TUI. The TUI is still unconfirmed (Open Question 4). `CODEX_SESSION_ID` is a possible third signal; do not add it without the interactive names list (D-05 allows choosing a replacement only if both are absent).

### opencode v2.0.31 host env (source-inspected)
```
# [VERIFIED: byte scan of ~/.opencode/bin/opencode] the bash tool does:
#   env.AGENT="1", env.OPENCODE="1", env.AI_AGENT ||= "opencode", env.OPENCODE_SESSION_ID=<id>
```
The `OPENCODE` signal in `RUNTIMES["opencode"]` is therefore still present in v2.0.31 per source; the existing label "live-verified (01.2)" was for 1.x. Re-confirm with a names-only dump in the opencode runs and keep the label wording honest (live-verified on 1.x; v2.0.31 source-inspected until the run records it).

### Throwaway HOME + allowlist snapshot (pattern)
```python
# Source: pattern for tests/gsd_curated_eval.py; stdlib only
import tomllib, json, hashlib
def toml_semantic_sha(path, scratch_prefix):
    try: data = tomllib.loads(path.read_text("utf-8"))
    except FileNotFoundError: return None
    projects = data.get("projects", {})
    data["projects"] = {k: v for k, v in projects.items() if not k.startswith(scratch_prefix)}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
```
Strict additions (hash/listing, names only): `~/.codex/{agents/ listing, hooks.json}`, `~/.config/opencode/{opencode.jsonc, agents/, commands/, skills/, plugins/ listings}`; semantic: `~/.codex/config.toml`. Exclude `package.json`, `bun.lock`, and never touch `~/.config/opencode/service.json` or any `auth.json`.

### Headless commands (templates, Claude's discretion)
```bash
# argv check with no model call (verified; matches v2.0.31 run flags --model/--auto/--format/--session)
echo | node .planning/scripts/cross-ai.mjs --print-argv --prefer opencode,codex \
  --model-opencode <provider/model> --model-codex <model>
# codex (0.162.1): less host-state written
codex exec --ephemeral --ignore-user-config --skip-git-repo-check -C <repo> -o <out> "<prompt>"
# opencode (v2.0.31): private server, never the user's service
opencode run --standalone --auto --format json --model <provider/model> "<prompt>"
```
`codex exec --ephemeral` ("Run without persisting session files") and `--ignore-user-config` ("Do not load $CODEX_HOME/config.toml; auth still uses CODEX_HOME") exist [VERIFIED: `codex exec --help`]. So the host runs with its real HOME and real auth (no copy needed), while every gsd install/apply inside the smoke runs under the scratch HOME that the smoke itself builds. The runner's opencode profile currently omits `--standalone` (cross-ai.mjs RUNTIMES.opencode `exec`/`review`); adding it is a one-line, one-module candidate fix (or pass via `CONFIG.extraArgs`), regression test in the runner self-test.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| opencode 1.x `run --variant <level>` | v2: effort rides on `-m provider/model#variant`; no `--variant`, no `--dir` | opencode 2.0.x | RUN-26 (gsd-core 1.16.0) is handled in 1.17.0: `adaptLaneInputForGeneration` drops `--variant`, appends `#<effort>` to the configured model, `adaptLanePlanForGeneration` adds `--standalone` and drops a trailing `-` [VERIFIED: `.claude/gsd-core/bin/lib/opencode-version.cjs`] |
| `opencode debug agent <name>` | `opencode debug agents` (list) | v2 | D-07's last link needs rewriting |
| codex `CODEX_VERSION` not in binary (0.153.4) | present in 0.162.1 binary and in a 0.162.1 session env | codex 0.15x -> 0.162 | D-05 expected outcome flips |
| codex sessions always persisted | `codex exec --ephemeral`, `--ignore-user-config` | 0.162.x | headless codex can avoid sessions and config writes |

**Deprecated/outdated:** the SPEC's "Host CLIs: codex 0.153.4, opencode 1.18.35" and CONTEXT's "gsd 1.13.0 global installs" (no global GSD exists now; `~/.gsd` is absent). AGENTS.md says amend ROADMAP/REQUIREMENTS when live facts contradict them: SPEC-01 wording on `CODEX_VERSION` and the host-CLI versions in the 20-SPEC need a dated amendment.

## Items Deferred Into Phase 20 (disposition)

| Item | Source | Disposition for the plan |
|------|--------|--------------------------|
| Codex stream-error parse assumption (`error` then `turn.completed`) | 18-VERIFICATION #11, cross-ai.mjs `shortcut:` | Record the real `codex exec --json` event type sequence from one headless run (observed shapes). The recovered-error path cannot be provoked deterministically: leave the `shortcut:` comment, state "not provoked" explicitly (human item or defer) |
| CR-03/CR-04 signal rework on real CLIs | 18-VERIFICATION #12, deferred to 20-22 | Executable headless for codex and opencode: run the runner under `gsd-tools run-with-timeout`, SIGTERM mid-run, expect one `AIKIT-XAI status=signal ... tree=<real>` line within about 2.9 s, process group dead, no temp dirs, second signal SIGKILLs at once. Needs a real (killed) model call; verify with a `ps` before/after pid check. cursor/pi stay in 21/22 |
| C-W12 failed vs empty model listing on a real host | 18-VERIFICATION #6 | Run an UNSEEDED inventory on each host (the Phase 19 smoke deliberately seeds the cache and asserts no probe, so host model enumeration is not exercised by it); add one step with a scratch `XDG_CACHE_HOME`. Provoke a real failure (e.g. unreachable service/bad `CODEX_HOME`) and record whether `runtime_enumeration` reads `failed` vs `empty`; if it cannot be provoked, say so |
| Phase 19 L4 `inheritance_promised` | 19-REVIEW-FIX | Replace by the derived rule in Pattern 1 (empty promise only when plan and builtin both lack the host/tier), or keep the flag if a concrete case appears |
| Native per-call model selection (ROADMAP SC3, 18.1 deferred) | 18.1-VERIFICATION | `RUNTIMES["codex"|"opencode"].native_selectors` is `()` so `host_can_select` is False for both [VERIFIED: detection.py:78-107, routing.py:44-56]. Codex 0.162.1 binary strings show `spawn_agent` validates a model ("Unknown model ... for spawn_agent. Available models") and a config `expose_spawn_agent_model_overrides` [source-inspected, not live]. Default outcome: keep the session-default-only label; a human-verification probe (ask codex to spawn a subagent with a named model, read the child model from the rollout) is optional. opencode: unverified |

## Don't-Do List for Scope (ponytail)

Skip: new scripts per host, a TUI-driving harness, re-running the 4 scenario `claude -p` evals on other hosts (Phase 19 EVAL-01 scope), cursor/pi anything, changing the user's global configs, and model-judged `/gsd-review` trials beyond what D-11 already locks (see Open Question 5).

## What Headless Runs Can and Cannot Prove

| Claim | Headless (`codex exec`, `opencode run`) | Interactive only |
|-------|------------------------------------------|------------------|
| Smoke steps, matrix, planned==baked, allowlist guard | Yes, same code path (the script runs in the host's shell tool) | EVAL-04/05 acceptance still requires the user's own session (SPEC constraint) |
| Env names set in the host's tool shell | exec/run path only | TUI path unconfirmed (could differ) |
| Project trust persistence (`projects."<path>".trust_level`) | No (`--ignore-user-config`/exec) | Yes (TUI writes it, confirmed in 0.162.1 binary strings) |
| `/gsd-review` self-skip behavior | Source-level only (`SELF_CLI=auto` for codex/opencode, review.md:126-149) | LLM-judged behavior needs real trials |
| Native per-call model selection | No | Needs a live subagent spawn |

Plan statement: the executor runs and records headless iterations; produces one short interactive script per host (steps and paste-able prompts, a names-only env dump command, the smoke command, a snapshot check, the planned==baked report); the interactive run is a `human_verification` item; the autonomous run never pauses for it.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The opencode TUI bash tool sets the same `OPENCODE=1` env as the `run` path | Code Examples | Detection might differ in TUI; the interactive names dump catches it |
| A2 | A `--local` install with a throwaway HOME touches nothing else outside the project and the throwaway HOME | Pitfall 4 | Unseen global write; the allowlist snapshot is the backstop |
| A3 | `opencode run --standalone` reads the real `~/.config/opencode` config read-only and writes only its own state | Headless commands | Could write under `~/.config/opencode` (package refresh); D-10 excludes `package.json`/`bun.lock` only |
| A4 | The codex TUI sets the same `CODEX_*` names as `codex exec` | Code Examples | D-05 outcome could change; interactive names list decides |
| A5 | The `.opencode/gsd-core` local root is where the opencode installer puts it and `gsd-tools.cjs` is at `.opencode/gsd-core/bin/gsd-tools.cjs` | Architecture | Install layout mismatch breaks inventory scope; verify on first install (host.py shortcut comment says "inferred") |
| A6 | opencode v2 loads project `.opencode/agents` over global `agents/` | State of the Art | Documented precedence (project `.opencode` dirs rank above global config) is from v1-era docs; v2 binary scans `{agent,agents}/**/*.md` [source-inspected]; live proof pending |

## Open Questions

1. **Installer source for the smoke (UNVERIFIED).**
   - Known: Phase 18 R14 argv is `npx -y --registry=... @opengsd/gsd-core@<v> --<host> --local`; npx is aliased to `pnpm dlx` in the user's shell; a complete 1.17.0 package exists in the local pnpm store.
   - Unclear: whether the executor may use network, and whether `pnpm dlx` honors the scoped registry flags.
   - Recommendation: add a smoke option naming an installer directory and default to R14's argv; the plan runs the offline store copy (discovered at run time via `pnpm store path`, never hardcoded) with a `checkpoint:human-verify` because the package is SUS-flagged `too-new`.
2. **opencode project-agent precedence and `debug agents` output shape (UNVERIFIED).** Not run (would attach to or conflict with the user's shared service). Recommendation: a first-observation spike in the executor under `--standalone`-only paths; if `debug agents` cannot be made standalone, treat its output as read-only listing against the shared service, record that, and prove precedence with a same-named agent supplied via `OPENCODE_CONFIG_DIR`-style scratch plus project `.opencode/agents` in a standalone run. Note `OPENCODE_CONFIG_DIR` loads AFTER `.opencode` dirs per the docs, so it can override project agents for users who set it [CITED: opencode.ai/docs/config].
3. **Does codex load project `.codex/agents` only after trust? Does `--ignore-user-config` drop the project layer? (UNVERIFIED).** Not needed for the oracle (tomllib reads files). Defer unless the interactive run shows agents not loading.
4. **TUI env names for codex and opencode (UNVERIFIED).** The interactive script prints names only: `env | cut -d= -f1 | grep -E '^(CODEX|OPENCODE|AI_AGENT|AGENT|CLAUDE)'`.
5. **`/gsd-review` mechanics trials (D-11, two per route per host) are LLM-judged and costly (UNVERIFIED).** Recommendation: put them in the interactive scripts as optional steps for the user; policy half is already enforced in code. The executor records "not re-run headless" with the source citation rather than faking trials.
6. **Whether an unseeded real-host inventory is stable enough to automate (UNVERIFIED).** `codex debug models`/`opencode models` calls were not run here (outside the allowed probe list).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| codex | EVAL-04 headless/interactive | yes | 0.162.1 | none (blocker for EVAL-04) |
| opencode | EVAL-05 | yes | v2.0.31 (user's managed service already running on port 49374) | `--standalone` |
| node | gsd-tools, installer | yes | via volta | none |
| python3 | harness | yes | 3.14.7 on PATH (project pins >=3.12,<3.13 for uv); `tomllib` present | `uv run` for the `unit-uv` group |
| pnpm | offline installer copy / R14 alias | yes | present | npx R14 argv |
| gsd-core installer 1.17.0 | R1 | yes (pnpm store, 5 versions) | 1.17.0 | R14 npx (network) |
| git | scratch projects | yes | - | none |
| network | R14 npx, opencode/codex model calls | unknown | - | pnpm store copy for the install; model calls need it |
| `~/.gsd/defaults.json` | D-09 seed | absent | - | seed an empty/absent file; assert that |

**Missing dependencies with no fallback:** none found. **With fallback:** network (installer via store copy).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib `unittest` via `tools/run_unittest_parallel.py` (groups `unit`, `e2e` real node, `arch`) |
| Config file | `tools/run_unittest_parallel.py`; `tests/test_gate_scope.py` enforces group membership |
| Quick run command | `python3 -m unittest tests.test_gsd_curated_eval tests.test_ai_kit_spec_runtimes_table tests.test_curated_config_followups tests.test_curated_config_recommend tests.test_gate_scope` |
| Full suite command | `make test && make validate` |

### Phase Requirements -> Test Map
| Req / SPEC item | Behavior | Test Type | Automated Command | File Exists? |
|-----------------|----------|-----------|-------------------|-------------|
| R1 | Smoke installs gsd-core locally before inventory, pinned to claude host version; failed install stops before inventory; second install changes no agent file | unit (injected installer/run_fn) + live | `python3 -m unittest tests.test_gsd_curated_eval -k TestSmoke` | Wave 0 (new cases) |
| R2/R5 smoke | host-parameterized smoke, ai-kit config byte-identical | unit + live | `python3 -m unittest tests.test_gsd_curated_eval -k TestSmoke`; live: `python3 tests/gsd_curated_eval.py smoke --evidence-out <file>` from the host | Wave 0 |
| R3 | detection table pinned per live finding; neither-variable-set yields not-codex | unit | `python3 -m unittest tests.test_ai_kit_spec_runtimes_table` | exists (update) |
| R4/R7 | host-aware oracle: empty model fails unless derived inheritance; override and tier checked separately; sorted reporting | unit | `python3 -m unittest tests.test_gsd_curated_eval -k Matrix -k Promised` | Wave 0 (replace `test_matrix_refuses_non_claude_host`, line 446) |
| R4/R7 e2e | 5x35 passes on both hosts with real node, Control 1 replacement discriminates, Control 2 passes | e2e (real node) | `python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix` | exists (extend) |
| R5 | planned == baked per agent (opencode frontmatter `model:`; codex TOML pins), project agents win | unit (fixtures) + live | `python3 -m unittest tests.test_gsd_curated_eval -k Baked` | Wave 0 |
| R6/D-11 | host slug never proposed; copied `default_reviewers=[host]` flagged | unit | `python3 -m unittest tests.test_curated_config_recommend tests.test_curated_config_plan_edit` | extend (enforcement exists: cross_ai.py:217, plan_io.py:542-550; add a host-parametrized regression test) |
| R8 | headless runs recorded with status line; no status line = failure; hung run probed before retry | live + unit for the recorder | runner `--self-test` (`node .planning/scripts/cross-ai.mjs --self-test`) and unit tests of the recorder | Wave 0 |
| D-10 | allowlist guard: codex/opencode files; TOML minus `projects."<scratch>"` ignored, other TOML change fails | unit | `python3 -m unittest tests.test_gsd_curated_eval -k Snapshot` | Wave 0 |
| Evidence safety | no secret, no env value, placeholders only | script | `python3 tests/gsd_curated_eval.py secret-scan <evidence files>` | exists |
| Gate | whole repo | full | `make test && make validate` | exists |

### Sampling Rate
- **Per task commit:** the quick run command for the touched module plus `tests.test_gate_scope`.
- **Per wave merge:** `python3 tools/run_unittest_parallel.py --group unit` and `--group e2e`.
- **Phase gate:** `make test`, `make validate`, snapshot `--check` clean, secret-scan clean, no orphan `codex`/`opencode` processes started by the run (`ps` before/after).

### Wave 0 Gaps
- [ ] host-aware `promised`/Control tests replacing the non-claude refusal test
- [ ] smoke install-step seam tests (installer argv, cwd, HOME, ordering, failure stops before inventory)
- [ ] allowlist snapshot tests incl. TOML semantic compare
- [ ] planned==baked readers with fixtures (frontmatter, TOML)
- [ ] `live_tables` exports `RUNTIME_PROFILE_MAP`
- [ ] host-parametrized "never the host lane" test in recommend

## Security Domain

### Applicable ASVS Categories (level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (ai-kit adds none) | Host auth is the host's own; never copied |
| V4 Access Control | yes | Allowlist guard; real applies only on scratch projects; repo-root refusal (`refuse_repo_apply`) |
| V5 Input Validation | yes | Only exact-semver version strings reach an installer argv (`followups._SEMVER`); scratch paths via `tempfile.mkdtemp` |
| V6 Cryptography | no | none |
| V8/V14 Data protection and config | yes | names-only env evidence; `secret-scan`; placeholders for every path |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Installer rewrites global state (`~/.gsd/defaults.json`, home scans) | Tampering | Throwaway HOME (+ `--no-legacy-cleanup`); strict snapshot of `~/.gsd` |
| Host persists project trust into `~/.codex/config.toml` | Tampering (benign) | Semantic compare minus `projects."<scratch>"` |
| Secret exposure through evidence or logs | Information disclosure | Names only; never read `auth.json`, `~/.config/opencode/service.json` (it holds a service password), or any credential file; do not list or hash them; `secret-scan` before commit |
| Full-permission headless dispatch (`--dangerously-bypass-approvals-and-sandbox`, `--auto`) | Elevation | Scratch cwd, scratch-only apply, `--ephemeral`; user memory records cross-AI runs unattended with no sandbox |
| Supply chain: SUS `too-new` installer package | Tampering | Use the already-fetched store copy; human-verify checkpoint |
| Orphaned host processes | DoS | Reaper and group-kill (reuse Phase 19 reaper and runner group-kill); pid check before and after |

## Sources

### Primary (HIGH confidence)
- Worktree files read this session: `tests/gsd_curated_eval.py` (smoke, matrix, snapshot), `skills/ai-kit-spec-review/ai_kit_spec/detection.py`, `routing.py`, `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/{host,followups,cross_ai,plan_io}.py`, `.claude/gsd-core/bin/lib/{model-resolver,model-catalog,opencode-version,install-model-override-resolver}.cjs`, `.claude/gsd-core/workflows/review.md`, the Phase 18/18.1/19 verification and review files.
- gsd-core 1.17.0 installer source in the local pnpm store: `bin/install.js` (`writeNonClaudeDefaults` 7087, local target `process.cwd()` 8463/9587, `generateCodexAgentToml` 4116-4186, `--no-legacy-cleanup`, `.gsd-runtime` marker 12117) and `gsd-core/bin/lib/runtime-artifact-layout.cjs`.
- Live probes: `codex --version/--help/exec --help/features list`, `opencode --version/--help/run --help/debug --help/debug paths/service --help`, one failed `opencode debug agents` (port conflict), `gsd-tools query package-legitimacy check`, and the spiked oracle/control runs against real node and gsd-core 1.17.0 in scratch projects.
- Byte scans of the codex 0.162.1 and opencode v2.0.31 binaries (string presence only; see Assumptions for what that does not prove).

### Secondary (MEDIUM confidence)
- [CITED: https://opencode.ai/docs/config/] config precedence: project `.opencode` directories rank above the global config; `OPENCODE_CONFIG_DIR` loads after them.

### Tertiary (LOW confidence)
- None used for recommendations.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, all in-repo or verified versions.
- Architecture: HIGH for the codex/opencode oracle and controls (executed spike); MEDIUM for the baked-agent readers and opencode loader proof (installer not run here, per rules).
- Pitfalls: MEDIUM-HIGH; the opencode service hazard is observed, the TUI-vs-exec env difference is not.

**Research date:** 2026-10-17
**Valid until:** about 7 days: codex, opencode and gsd-core all moved within the last two weeks.
