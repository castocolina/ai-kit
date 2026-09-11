---
name: ai-kit-gsd-curated-config
description: Curated, one-question GSD config setup for a target project's `.planning/config.json` — asks only `model_profile` (quality/balanced/budget/adaptive), then writes preference-driven defaults through gsd-tools' own schema-validated `config-set`/`config-new-project`: critical-agent opus/high overrides derived live from the installed gsd-core's own `AGENT_DEFAULT_TIERS` (never a hardcoded agent list), cross-AI execution/plan-review CLI+model selection from live-detected opencode/cursor-agent candidates, `claude_md_path`/frontend-based `ui_phase`/`ui_review` detection, and a fixed workflow-flag bundle. Use when a project needs GSD configured fast without the full `gsd-settings`/`gsd-config` interrogation (power-user knobs, API keys/integrations) — this is a faster alternative entry point, not a replacement or wrapper for either.
---

# ai-kit-gsd-curated-config

## Scope

This skill wraps the already-built `ai-kit-gsd-curated-config.py` CLI. It writes
`.planning/config.json` for a target GSD project through ONE curated question
(`model_profile`) plus a fixed set of preference-driven defaults this
project's own maintainer already locked in (07-CONTEXT.md D-01 through D-10):
effort/model overrides for GSD's own critical agents, cross-AI
execution/plan-review CLI+model selection, `claude_md_path`/frontend
detection, and a 27-key workflow-flag bundle. It never invents new GSD
behavior — every write goes through gsd-tools' own `config-set`/
`config-new-project`, so the real schema manifest validates every key this
skill touches, exactly as if `gsd-settings`/`gsd-config` had written it.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path
as a literal absolute path:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-gsd-curated-config}" \
         "$HOME/.claude/skills/ai-kit-gsd-curated-config" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-gsd-curated-config" \
         "$HOME/.agents/skills/ai-kit-gsd-curated-config" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-gsd-curated-config.py" ] && { printf '%s\n' "$d/ai-kit-gsd-curated-config.py"; break; }
done
```

If no candidate exists, stop and report that the skill is not installed. The
fifth candidate covers a from-checkout invocation — substitute the directory
actually containing this `SKILL.md`.

## Run the curated flow

Every subcommand below is invoked as `python3 "$ENTRYPOINT" <subcommand>
--project-dir <target_dir> [...]`. Before running any `apply-*` subcommand,
ask yourself: has `ensure-project` already run for THIS `--project-dir` in
this session, and — for the two detect/apply pairs (Steps 4-6) — did the
matching `detect-*` call already run and get shown to the user this same
invocation? Skipping `ensure-project` is a silent footgun, not a hard
failure: `gsd-tools`' own `config-set` happily creates `.planning/config.json`
from an empty `{}` if nothing exists yet, so the call "succeeds" — but the
result is a one-key file missing every other schema default
`config-new-project`'s `buildNewProjectConfig` would have populated (the same
full default set `gsd-settings` itself produces), not a genuinely merged
project config. Likewise, guessing `--cli`/`--model` for
`apply-execution`/`apply-review` instead of passing the actual `detect-*`
output through unchanged writes a command that may not correspond to
anything installed on this machine. Follow the exact order below — later
steps assume `.planning/config.json` already exists with its full default
shape (Step 1), and Steps 4-6 are always detect-then-ask-then-apply, never
apply without first showing the detected candidate.

1. **Ensure the config exists.** `ensure-project` — idempotent: succeeds
   whether it creates a fresh `.planning/config.json` or finds one already
   there (D-09 merge mode; every later step only touches its own specific
   keys, never regenerates the whole file).
2. **Ask the ONE curated question.** Which `model_profile`: `quality` /
   `balanced` / `budget` / `adaptive`? Then `apply-profile --profile
   <answer>`.
3. **Apply critical-agent overrides — no question asked.**
   `apply-critical-agents` derives its writes live from the installed
   gsd-core's own `AGENT_DEFAULT_TIERS` export (never a baked-in agent
   list): `gsd-code-reviewer` gets opus/high unconditionally (the user's
   explicit top-up), `gsd-executor` and the `models.research`/
   `models.execution` phase-type floor get haiku unconditionally, and every
   OTHER agent the live catalog classifies `heavy` tier also gets opus/high
   — `gsd-executor` is excluded from that sweep even if a future gsd-core
   reclassifies it heavy, so its haiku floor can never be contradicted by a
   conflicting high-effort override. Degrades gracefully (writes only the
   five unconditional pairs, reports `degraded_reason`) when the live
   catalog can't be queried — never a hard failure.
4. **Detect and apply execution delegation.** `detect-execution-candidate`
   prints the best opencode/cursor-agent match against the execution
   preference ladder (`coding`/`executor` name match, then
   composer>=2.5, grok>=4.6, deepseek-flash, luna — see
   `ai_kit_gsd_curated_config/preference_match.py` for the exact rule order). Show
   the detected `{cli, model, rule}` to the user, then `apply-execution
   --cli <cli> --model <model>` (omit both flags when nothing matched —
   `workflow.cross_ai_execution` still gets written `true`, just with no
   `cross_ai_command`).
5. **Detect and apply plan-review delegation.** `detect-review-candidate`
   always resolves to something — when no opencode/cursor-agent model
   matches the plan-review ladder (`plan-review` name match, `gpt-<ver>-sol`
   pattern, glm-5.2/5.3), it returns the native last resort (`claude`/
   `opus`). Show it, then `apply-review --cli <cli> --model <model>` (always
   both flags — `apply-review` has no no-candidate branch).
6. **Detect and apply `claude_md_path` + frontend-driven UI flags.**
   `detect-claude-md-path` checks `AGENTS.md` / `CLAUDE.local.md` /
   `AGENTS.local.md` / `CLAUDE.md` in that priority order and returns the
   first hit (or `null` if none exist — in which case skip
   `apply-claude-md-path` entirely; it does not accept an empty path).
   `detect-frontend` scans `package.json` dependencies and `README.md` text
   for a frontend-framework signal. Then `apply-workflow-defaults --ui-phase
   <true|false> --ui-review <true|false>` using that frontend boolean for
   BOTH flags — this same call also writes the fixed 27-key
   `workflow.*` defaults bundle (research/plan_check/verifier/nyquist_validation/
   code_review/security_enforcement and 21 more; see
   `ai_kit_gsd_curated_config/workflow_defaults.py` for the literal list).

## Subcommand reference

| Subcommand | Required flags | What it writes |
|---|---|---|
| `ensure-project` | `--project-dir` | Creates `.planning/config.json` if absent; no-op if present |
| `apply-profile` | `--project-dir`, `--profile {quality,balanced,budget,adaptive}` | `model_profile` |
| `apply-critical-agents` | `--project-dir` | `model_overrides.*`/`effort.agent_overrides.*` for `gsd-code-reviewer` + live heavy-tier sweep; `models.research`/`models.execution` |
| `detect-execution-candidate` | — | Prints `{cli, model, rule}` or all-`null`; writes nothing |
| `detect-review-candidate` | — | Prints `{cli, model, rule}` (never null — native last resort); writes nothing |
| `apply-execution` | `--project-dir`; `--cli`/`--model` optional | `workflow.cross_ai_execution` (always); `workflow.cross_ai_command` (bare command name, only when `--cli`/`--model` given) |
| `apply-review` | `--project-dir`, `--cli`, `--model` | `workflow.plan_review_convergence`, `review.effort.opencode`, `review.default_reviewers` (dedupe-merged), `review.models.<slug>` |
| `detect-claude-md-path` | `--project-dir` | Prints `{path}` (nullable); writes nothing |
| `detect-frontend` | `--project-dir` | Prints `{frontend_present}`; writes nothing |
| `apply-claude-md-path` | `--project-dir`, `--path` | `claude_md_path` (no-op with `reason: empty_path` when `--path` is empty) |
| `apply-workflow-defaults` | `--project-dir`, `--ui-phase {true,false}`, `--ui-review {true,false}` | The fixed 27-key `workflow.*` bundle, plus `workflow.ui_phase`/`workflow.ui_review` |

Every subcommand exits `2` when `node` or an installed gsd-core's
`gsd-tools.cjs` can't be resolved on this machine — surface that message
verbatim rather than retrying silently; it means gsd-core itself isn't
installed where this skill can find it, not a bug in this skill.

## NEVER

- **Never replace or wrap `gsd-settings`/`gsd-config`.** Those remain the
  entry points for power-user knobs (`--advanced`) and third-party API
  keys/integrations (`--integrations`) this curated skill intentionally
  skips (07-CONTEXT.md D-10). This skill is a faster ALTERNATIVE, invoked
  instead of them, never routed through them and never routing to them.
- **Never hand-write `.planning/config.json`.** Every write in this skill's
  own CLI goes through `gsd-tools config-set`/`config-new-project`
  (`ai_kit_gsd_curated_config/gsd_write.py` is the only module in the package
  permitted to shell out for a write) — this is what keeps every key this
  skill touches schema-validated the same way `gsd-settings` output is,
  never a parallel, unvalidated write path.
- **Never bake a resolved absolute path into `workflow.cross_ai_command`.**
  `apply-execution` always writes the bare command name (`opencode`,
  `cursor`), resolved via `PATH` at dispatch time — a venv/nvm/brew-resolved
  absolute path here is a known landmine (D-05) that breaks the moment the
  project moves machines or the venv is rebuilt.
- **Never ask more than the one curated question (`model_profile`).**
  Everything else in the Run the curated flow section above is a detected
  default or a fixed preset, by design — if a user wants deeper control
  over any of it, that is exactly what `gsd-settings --advanced` is for,
  not a reason to add more questions here.
- **Never treat this repo's own `.planning/config.json` as the write
  target implicitly.** Every subcommand takes an explicit `--project-dir`
  for the TARGET project being configured — never assume the current
  working directory when it wasn't given explicitly.

## Common mistakes

| Mistake | Why it's wrong | Fix |
|---|---|---|
| Calling `apply-profile`/`apply-critical-agents`/etc. against a project that never had `ensure-project` run | `config-set` doesn't fail here — it silently creates a sparse `.planning/config.json` containing only the one key you set, missing every other schema default `config-new-project` would have populated. No error to notice; the gap only surfaces later as a project with an incomplete config | Always run `ensure-project` first, once per `--project-dir`, even if you believe a config already exists (it's idempotent — a no-op when one is already there) |
| Writing `--cli opencode --model <guessed-id>` to `apply-execution`/`apply-review` without first running the matching `detect-*` call | Skips the live preference-ladder match entirely — you may write a model id that isn't even installed on this machine, or miss a better-ranked candidate the ladder would have found | Always run `detect-execution-candidate`/`detect-review-candidate` first and pass its exact `{cli, model}` output through unchanged |
| Asking the user follow-up questions beyond `model_profile` (e.g. "which effort level for gsd-code-reviewer?") | Defeats the entire point of this skill — those overrides are locked presets (D-03), and a user who wants to tune them individually should be routed to `gsd-settings --advanced`, not asked here | Ask only `model_profile`; treat every other value in this flow as detected or preset |
| Treating `apply-execution`'s `--cli`/`--model` as required like `apply-review`'s | `apply-execution` has a real no-candidate path (`workflow.cross_ai_execution: true` written with no `cross_ai_command`) that `apply-review` does not — copying one subcommand's flag pattern onto the other produces a spurious required-argument error | Check the Subcommand reference table's "Required flags" column per subcommand, not by analogy |

## Reporting rule

Report the curated question's answer and every applied default/detection
result inline in the conversation, in the order Run the curated flow lists
them — never a separate persisted report file; the resulting
`.planning/config.json` diff is already the record of what changed.
