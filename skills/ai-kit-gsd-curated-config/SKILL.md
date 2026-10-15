---
name: ai-kit-gsd-curated-config
description: Curated GSD `.planning/config.json` setup for a target project — v2 flow (inventory → recommend → plan edits → apply → follow-ups) or the kept v1 one-question `model_profile` path. Writes only through gsd-tools' schema-validated `config-set`/`config-new-project`, cross-AI execution via a generated `.planning/scripts/cross-ai.mjs`, skill wiring, and grouped post-apply follow-ups. Use when a project needs GSD configured fast without the full `gsd-settings`/`gsd-config` interrogation — a faster alternative, not a replacement.
---

# ai-kit-gsd-curated-config

## Scope

This skill wraps `ai-kit-gsd-curated-config.py`. **Primary path:** the v2 pipeline
(`inventory` → `recommend` → `plan-set`/`plan-unset` → `apply` → follow-up approval).
**Secondary path:** the kept v1 curated flow (one `model_profile` question plus fixed
presets) — see [v1 path](#v1-path-kept-secondary).

Every write goes through the shared `ai_kit_spec.gsd_tools` wrappers (`config-set` /
`config-new-project`), never a hand-edited JSON file. The `ai-kit-spec-review` skill must
be installed beside this one; `node` and a resolvable gsd-core are required.

## Prerequisites and trust model

**Trusted checkouts only.** `inventory` runs the target project's own gsd-core under
`node` (project-local gsd-core wins over global). Point `--project-dir` only at trees you
would already run GSD in. gsd-core resolution matches GSD's launcher:
`<root>/gsd-core`, `<root>/.claude/gsd-core`, `<root>/.codex/gsd-core`, then global
installs.

Exit `2` (install problem, not a logic bug): sibling `ai-kit-spec-review` missing,
`node` missing, or no `gsd-tools.cjs` found. Surface stderr verbatim; do not retry.
Exit `1`: a gsd-tools read/write failed.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-gsd-curated-config}" \
         "$HOME/.claude/skills/ai-kit-gsd-curated-config" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-gsd-curated-config" \
         "$HOME/.agents/skills/ai-kit-gsd-curated-config" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-gsd-curated-config.py" ] && { printf '%s\n' "$d/ai-kit-gsd-curated-config.py"; break; }
done
```

If none exists, stop — the skill is not installed. Substitute the directory containing
this `SKILL.md` for the fifth candidate when invoked from a checkout.

## Run the v2 flow

Resolve `$ENTRYPOINT` once (see above). Every project-touching subcommand:
`python3 "$ENTRYPOINT" <subcommand> --project-dir <target> [...]`.

1. **Inventory.** Snapshot models, skills, plugins, and config shape (read-only):

```bash
python3 ai-kit-gsd-curated-config.py inventory --project-dir <target> --host claude
python3 ai-kit-gsd-curated-config.py inventory --project-dir <target> --refresh
```

2. **Recommend.** Build `plan.json` from inventory + rigor/profile answers:

```bash
python3 ai-kit-gsd-curated-config.py recommend --inventory <inv.json> --profile quality --rigor mvp --out <dir>/plan.json --cross-ai-review n --cross-ai-exec y
```

3. **Review** the JSON: `needs_choice` entries, notes, warnings, unverified flags. Resolve
   each choice with `plan-set` or `plan-unset` (never skip silently).

```bash
python3 ai-kit-gsd-curated-config.py plan-set model_profile quality --plan <plan.json> --inventory <inv.json>
python3 ai-kit-gsd-curated-config.py plan-set workflow.cross_ai_command "node .planning/scripts/cross-ai.mjs" --plan <plan.json> --force
python3 ai-kit-gsd-curated-config.py plan-unset agent_skills_security.trusted_global_roots --plan <plan.json>
```

4. **Dry-run apply** (refuses while `needs_choice` remains; inventory digest must match):

```bash
python3 ai-kit-gsd-curated-config.py apply --plan <plan.json> --inventory <inv.json> --project-dir <target> --dry-run
```

5. **Apply** (backup + marker `config.json.ai-kit-apply-marker`, runner snapshot
   `.ai-kit-apply-backup`):

```bash
python3 ai-kit-gsd-curated-config.py apply --plan <plan.json> --inventory <inv.json> --project-dir <target>
```

6. **Follow-up approval.** After exit 0, read the `followups` block in the apply report.
   Ask **one grouped yes/no** listing each required follow-up's argv, cwd, purpose,
   alternative, disclosures, and unverified notes. On yes, run the resolved entrypoint
   followed by the report's `approve_with` string **unchanged** — it starts at
   the `followups` subcommand and includes `--require` for the keys apply wrote:

```bash
python3 ai-kit-gsd-curated-config.py followups --plan <plan.json> --inventory <inv.json> --project-dir <target>
python3 ai-kit-gsd-curated-config.py followups --plan <plan.json> --inventory <inv.json> --project-dir <target> --approve --require installer
```

**Failure states to report as such:**

- **`restore_error` (exit 1):** rollback failed — marker, config backup, and runner
  snapshot stay. Do not delete the marker blindly. The next `apply` refuses and prints
  recovery steps recorded in the marker; follow them.
- **Exit 0 with cleanup warnings:** the apply **committed** — config and runner hold the
  applied state; **never** restore its backup. Delete only leftovers the warning names
  (marker, runner snapshot, stale backups). If a marker remains, the next apply's refusal
  must agree after its `apply --dry-run` check (recovery follows what that apply recorded).
- **Runner `unverified` status** (git tree could not be read): stop — claim nothing about
  success/fallback; report the status line only.
- **Effort sync** is not offered when the inventory points at a workstream config (gsd-core
  sync reads only the root config).

## Cross-AI execution

Apply sets `workflow.cross_ai_command` to `node .planning/scripts/cross-ai.mjs` and
renders the runner from the bundled template. **Targets run unattended with full permissions**
(no sandbox, no ask mode). After every external dispatch, print the
`AIKIT-XAI status=…` line from stderr **verbatim** (one line, stable vocabulary).

**Bare profile by default** (pi `--no-skills --no-extensions`, opencode with Claude-skill
loading off). The opencode bare profile is **partial**: `~/.agents/skills` and
`~/.config/opencode/skills` still load — document that honestly.

**Live timeout:** only `GSD_WORKSTREAM` is honored when the runner reads
`workflow.cross_ai_timeout` from config (baked outer timeout is the minimum with live).

**Opt-in skills and MCP servers:** set by hand-editing the generated script's CONFIG
`extraArgs` per target. The next apply then writes `cross-ai.mjs.new` instead of
overwriting the live runner.

**`.new` is not active:** the runner at `.planning/scripts/cross-ai.mjs` keeps its old
CONFIG; apply reports `script.active: false`. Merge `.new` by hand (keep customizations),
verify the **active** runner with:

```bash
node .planning/scripts/cross-ai.mjs --print-argv
```

(each target's argv with its model and the deadline line — no CLI dispatch), then delete
`.new`.

## Skills

- **Bare names only** in the plan; the skill translates to `global:…` or project-relative
  paths when writing `agent_skills.<agent>`.
- **Trusted-root approval** is one `needs_choice`: if the user **declined**, the skill stays
  wired and gsd-core skips paths outside trusted roots with a reported warning (use
  `plan-unset` on decline).
- Unknown installed skills: capped proposals from descriptions only — never auto-install.
- **Jev session gate:** `GSD_PATH_JEV=1` and `GSD_PATH_JEV_TIMEOUT_SECONDS` apply when
  System One reachability is detected (TCP/key presence only — not a health check).
- **Ponytail visibility (2026-10-15):** on this machine the six ponytail names are visible
  only through the Claude plugin cache, not other hosts' skill roots.
- **Limit:** skills kept only in `.claude/skills` inside a project are **not** scanned.
- **Plugin skills:** require install + layered `enabledPlugins` (user, project, local).
  Per-key layering across those files is **unverified** — inventory notes when it
  assumes last-wins per key.

## Limits

| Topic | Limit |
|---|---|
| cursor / pi | **not live-validated** on this maintainer's machine |
| opencode providers | Providers defined only in a project's `opencode.json` are not candidates |
| effort sync | Skipped for workstream configs; `--config-dir <project>/<host dir>` value **unverified** |
| local gsd root | `.opencode/gsd-core` install root **unverified** until Phase 20 |

## v1 path (kept, secondary)

One curated question (`model_profile`) plus detected/preset steps — unchanged behavior.
Use when v2 is unnecessary. Order: `ensure-project` → `apply-profile` →
`apply-critical-agents` → detect/apply execution → detect/apply review → detect frontend
→ `apply-workflow-defaults` (and optional `apply-claude-md-path`). See v1 subcommands
below; never mix v1 writes with an in-progress v2 plan on the same config without intent.

```bash
python3 ai-kit-gsd-curated-config.py ensure-project --project-dir <target>
python3 ai-kit-gsd-curated-config.py apply-profile --project-dir <target> --profile balanced
python3 ai-kit-gsd-curated-config.py apply-critical-agents --project-dir <target>
python3 ai-kit-gsd-curated-config.py detect-execution-candidate
python3 ai-kit-gsd-curated-config.py apply-execution --project-dir <target> --cli opencode --model x
python3 ai-kit-gsd-curated-config.py detect-review-candidate
python3 ai-kit-gsd-curated-config.py apply-review --project-dir <target> --cli claude --model x
python3 ai-kit-gsd-curated-config.py detect-claude-md-path --project-dir <target>
python3 ai-kit-gsd-curated-config.py detect-frontend --project-dir <target>
python3 ai-kit-gsd-curated-config.py apply-claude-md-path --project-dir <target> --path AGENTS.md
python3 ai-kit-gsd-curated-config.py apply-workflow-defaults --project-dir <target> --ui-phase false --ui-review false
```

## Subcommand reference

**v2**

| Subcommand | Required flags | Role |
|---|---|---|
| `inventory` | `--project-dir` | Read-only snapshot via project's gsd-core |
| `recommend` | `--inventory`, `--profile`, `--rigor`, `--out` | Write `plan.json` |
| `plan-set` | `key`, `value`, `--plan` | Resolve a plan entry |
| `plan-unset` | `key`, `--plan` | Decline / remove a plan entry |
| `apply` | `--plan`, `--inventory`, `--project-dir` | Write config + runner (`--dry-run` previews) |
| `followups` | `--plan`, `--inventory`, `--project-dir` | List or `--approve` post-apply commands |

**v1** — same as prior skill: `ensure-project`, `apply-profile`, `apply-critical-agents`,
`detect-*`, `apply-*`, `apply-workflow-defaults` (see v1 path).

## NEVER

- **Never replace `gsd-settings` / `gsd-config`.** Power-user and integration knobs stay there.
- **Never hand-write `.planning/config.json` or `plan.json`.** Use the CLI subcommands only.
- **Never run `inventory` on untrusted checkouts** (it executes project JavaScript).
- **Never delete an apply marker** without following the recovery text the next apply prints.
- **Never treat `cross-ai.mjs.new` as active** without merge + `--print-argv` on the live runner.
- **Never ask follow-up questions beyond what v1/v2 already expose** — route tuning to
  `gsd-settings --advanced`.

## Common mistakes

| Mistake | Fix |
|---|---|
| `apply` while `needs_choice` remains | Run `plan-set`/`plan-unset` until dry-run is clean |
| Stale inventory digest | Re-run `inventory` and `recommend`, or pass matching `--inventory` |
| Editing CONFIG then expecting immediate runner behavior | Merge `.new` or wait for pristine overwrite; check `script.active` |
| Running `approve_with` without the entrypoint prefix | Always `python3 "$ENTRYPOINT"` then the exact `approve_with` argv tail |
| Restoring backup after a committed apply with cleanup warnings | Delete named leftovers only; config/runner already match the plan |

## Reporting rule

Report inventory/recommend/apply JSON inline in conversation order — no separate report file.
For cross-AI dispatches, include the verbatim `AIKIT-XAI` line. Flag every **unverified**
inventory/recommend note instead of upgrading it to fact.
