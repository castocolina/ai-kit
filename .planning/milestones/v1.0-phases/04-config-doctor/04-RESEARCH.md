# Phase 4: Config Doctor - Research

**Researched:** 2026-09-09
**Domain:** Cross-runtime CLI configuration diagnostics (Claude Code, opencode, Codex, Cursor) — read-only checks catalog, interactive TUI review screen, per-item confirmed apply
**Confidence:** MEDIUM-HIGH (most core claims freshly verified against official docs and live machine state this session; several rows are explicitly flagged LOW/ASSUMED where no authoritative source exists — see Assumptions Log)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** The catalog is **data-driven**, not 12+ hardcoded functions: each
  row is a record (`runtime`, `check`, `current-value-reader`, `recommended`,
  `confidence`, `apply-fn` or `None` for informational-only rows) consumed by
  one generic check/apply engine. Adding or removing a row is a data change,
  not an engine rewrite.
- **D-02:** The schema needs a **`scope` field** (`runtime` vs. `model`) —
  some checks (e.g. Codex `model_reasoning_effort`) should vary by which
  *model/vendor* is active within a runtime, not be a single fixed
  runtime-wide recommendation. The exact mechanism for a `model`-scoped row
  to resolve "which model is active" is left to the researcher/planner — not
  designed in this discussion.
- **D-03 (major — expands REQ-config-doctor-diagnostic-checks):** A
  runtime's section is shown/skipped based on **config-file presence**
  (`~/.claude/settings.json`, `~/.config/opencode/opencode.jsonc`,
  `~/.codex/config.toml`, `~/.cursor/cli-config.json`), not
  `detect_installed_clis()`. **Cursor is added as a 4th runtime** to this
  phase's scope. Treat this as locked for this milestone unless the user
  explicitly reopens it.
- **D-03b:** Phase 1.2's `native_runtime` now allows `"cursor"`; Phase 3's
  Cursor `sessionStart` hook wiring is already complete. Not re-derived here.
- **D-04:** Row 9 (Codex `features.hooks`) is **informational only, no apply
  action** — same treatment as row 5 (opencode retention).
- **D-05:** The review screen is an **interactive TUI built with `textual`**
  (not a plain CLI report).
- **D-06:** The TUI reuses `tools/setup.py`'s existing `ensure_rich_runtime()`
  guard function as-is and the same visual style as `wizard_app.py`'s
  `WizardApp`, but lives in its **own separate module** (e.g.
  `tools/config_doctor_app.py`) — not embedded as another screen inside the
  existing `WizardApp` instance.
- **D-07 (naming):** The new flow is reached via a **new `--config-doctor`
  flag on `tools/setup.py`** (TUI by default), NOT by repurposing the
  existing `doctor` subcommand. `doctor` stays exactly as it is.

### Claude's Discretion

None — every gray area in this phase had an explicit user decision. Several
factual questions (the Open Research Questions this document resolves) were
explicitly **not** answered by invention, per the project's confidence-labeling
constraint.

### Deferred Ideas (OUT OF SCOPE)

- **Shared core between Config Doctor's TUI and a future CLI variant**
  (`.planning/ROADMAP.md` §Backlog Phase 999.1). Not built now — this phase
  still ships TUI-only per D-05/D-07 — but the D-01 engine should be written
  without coupling check/apply logic directly to `textual` widgets, so a CLI
  front-end can be added later without a rewrite.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-config-doctor-diagnostic-checks | A read-only Checks Catalog spans Claude Code, opencode, Codex, and Cursor settings (retention, cache TTL, sandboxing, telemetry, permissions, share mode, reasoning effort, history persistence) plus a folded-in cross-runtime `rtk`-Cursor-integration check; informational-only rows never offered as apply; lower-confidence rows visibly labeled; a runtime with no config file present has its whole section skipped. | See `## Checks Catalog` below — 20 rows across 4 runtimes + cross-runtime, each with `scope`, confidence, apply-eligibility, and citation. Row 6/7b/16 resolve the third-party-model-settings open question (D-02). Rows 13-19 are the new Cursor research this REQ explicitly calls out as not-yet-done. |
| REQ-config-doctor-review-screen | A dedicated interactive review screen shows every check's current value, recommended value, and citation across all installed runtimes in one command; an undeterminable value shows as "unknown," never silently pass/fail. | See `## Architecture Patterns` (TUI structure, reuse of `wizard_app.py`'s style) and Common Pitfall 3 (promptCacheTtl's real default is billing-tier-dependent — the reader must degrade to "unknown" rather than assert a flat default). |
| REQ-config-doctor-apply-flow | A per-item, explicitly confirmed apply step (reusing the opencode-provider-management atomic-write + surgical-edit pattern) names the exact change before writing; security-relevant applies show the literal resulting config; no bulk "apply all." | See `## Don't Hand-Roll` and Common Pitfall 1: "reuse the pattern" means **adapt/port**, not **cross-import** `skills/ai-kit-opencode-providers` from `tools/` — this is an already-established, explicitly-commented rule in this codebase (`tools/setup.py:1386-1388`). |

</phase_requirements>

## Summary

Config Doctor's Checks Catalog was originally scoped (in the source PRD) to
12 rows across Claude Code, opencode, and Codex. This research (a) re-verifies
those 12 rows against current official documentation and this machine's live
config state, finding one real inaccuracy worth correcting (Claude Code's
prompt-cache TTL default is billing-tier-dependent, not flatly "5 minutes")
and one now-outdated citation (the `cleanupPeriodDays: 0` bug, GitHub #23710,
was fixed in Claude Code v2.1.89 — the value is now rejected outright rather
than silently disabling persistence); (b) adds Cursor as a fourth runtime
with 7 new researched rows (permissions, approval mode, two distinct sandbox
mechanisms, an undocumented but live-observed per-model reasoning parameter,
and two genuinely unresolved rows — local retention and CLI telemetry — that
this session could not source either way); (c) adds several new
high-confidence rows surfaced by re-reading the full official config
references (opencode's complete permission action set, opencode's per-model
`reasoningEffort`/`thinking.budgetTokens` options, Codex's granular
`approval_policy` object form and its unrelated `[memories]` duration
settings); and (d) surfaces one hard architectural constraint the planner
must respect: this codebase already has an explicit, commented rule that
`tools/` code must **adapt**, not **import**, patterns from `skills/`
packages — REQUIREMENTS.md's "reuses the atomic-write + surgical-edit
pattern" wording must be read that way, not as a literal cross-package
import.

**Primary recommendation:** Build the Checks Catalog as a declarative table
of 20 rows (see below) inside a new `tools/config_doctor_checks.py`-style
module kept free of `textual` imports (for the deferred CLI-front-end split),
with per-format readers/appliers **ported from**, not imported from,
`skills/ai-kit-opencode-providers`'s tested JSONC/atomic-write modules and
`tools/setup.py`'s existing TOML/JSON helpers; ship the TUI as
`tools/config_doctor_app.py` per D-06/D-07; treat Cursor rows 15(a)/16/17/18
as either informational-only or gated behind an explicit
`checkpoint:human-verify` task, since they rest on undocumented schema or
genuinely unresolved absence-of-evidence, not confirmed fact.

## Architectural Responsibility Map

This is a local CLI tool, not a web app — the standard browser/SSR/API/CDN
tiers do not apply directly. Tiers below are adapted to this project's own
layering (already established by `tools/setup.py` and
`skills/ai-kit-opencode-providers`).

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Checks Catalog (declarative rows, value readers) | Core engine (`tools/config_doctor_checks.py` or package) | — | D-01: must stay decoupled from the TUI so a future CLI front-end can reuse it (Backlog 999.1) |
| Review screen rendering | TUI view layer (`tools/config_doctor_app.py`) | Core engine (read-only) | D-06: mirrors `wizard_app.py`'s pure-view-layer pattern — imports nothing from `setup.py`, receives an injected context |
| Per-item apply/confirm flow | TUI view layer (confirm dialog) | Core engine (apply-writer) | REQ-config-doctor-apply-flow: the TUI drives *when* to write; the engine's format-specific writer decides *how* |
| JSON atomic write (Claude Code, Cursor) | Core engine, adapted from `tools/setup.py::_atomic_write_json`/`_read_json`/`_write_json` | — | Already proven in this codebase (Phase 3's hook wiring) |
| JSONC surgical edit (opencode) | Core engine, **ported from** (not imported from) `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/jsonc_edit.py` | — | `tools/setup.py:1386-1388`'s own comment: a `tools/` → `skills/` import is a documented layering violation |
| TOML region-replace (Codex) | Core engine, adapted from `tools/setup.py::write_toml_preserving` | — | No stdlib TOML writer exists (`tomllib` is read-only) — text-region replace is the only established, byte-preserving approach in this codebase |
| Entrypoint wiring (`--config-doctor` flag) | `tools/setup.py::main()` | — | D-07: alongside the existing `choices=[...]` list, not inside it |

## Checks Catalog

Every row is a candidate for the D-01 declarative registry:
`{id, runtime, scope, check, current_value_reader, recommended, confidence,
apply_eligible, why, source}`. `scope` is `runtime` unless marked `model`
(D-02). Rows marked **Apply: no** are informational-only per D-04's
precedent (row 9) and REQ-config-doctor-diagnostic-checks' explicit
carve-out for lower-confidence/no-real-setting rows.

### Claude Code (`~/.claude/settings.json`)

| # | Scope | Check | Current default | Recommended | Confidence | Apply | Why / Source |
|---|-------|-------|------------------|-------------|------------|-------|--------------|
| 1 | runtime | Local transcript retention — `cleanupPeriodDays` | `30` days | Raise (e.g. `3650`) for long retention; **never `0`** | HIGH | yes | Local caching stores transcripts under `~/.claude/projects/` for 30 days by default; adjust with `cleanupPeriodDays`. [VERIFIED: code.claude.com/docs/en/data-usage, fetched this session] — GitHub #23710 ("`cleanupPeriodDays: 0` silently disables all transcript persistence") was **fixed in v2.1.89**: `0` is now rejected as invalid (shown as an error in `/status`) instead of silently misbehaving. [CITED: github.com/anthropics/claude-code/issues/23710] The apply-flow must still refuse `0` categorically — don't rely on version-detection to decide whether it's "safe." |
| 2 | runtime | Prompt-cache TTL (main conversation) — `promptCacheTtl` setting / `CLAUDE_CODE_PROMPT_CACHE_TTL` env | **Billing-tier-dependent, not flatly "5 min"**: 1 hour on a Claude subscription within plan usage; 5 minutes for API key / usage-credits / cloud-provider auth | `promptCacheTtl: "1h"` (only a real change for the 5-min-default cases) | HIGH | yes, but reader must report "depends on billing mode" not a flat current value | Corrects the source PRD's "5 min" framing. Requires Claude Code **v2.1.242+** for the setting/env var to exist at all. [VERIFIED: code.claude.com/docs/en/prompt-caching, fetched this session] |
| 2b | runtime | Prompt-cache TTL (subagents/workflows/compaction) — `subagentPromptCacheTtl` / `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL` | 5 minutes, **always** (even on subscription) | `subagentPromptCacheTtl: "1h"` if idle-then-resume subagent/workflow usage is common | HIGH | yes | New row, not in the source PRD. Same doc as row 2. [VERIFIED: code.claude.com/docs/en/prompt-caching] |
| 3 | runtime | Sandboxed Bash tool — `sandbox.enabled` | `false` | `true` (global, in `~/.claude/settings.json`) | HIGH | yes, security-relevant | OS-level (Seatbelt on macOS, bubblewrap+socat on Linux/WSL2) filesystem/network isolation. [VERIFIED: code.claude.com/docs/en/sandboxing, fetched this session] |
| 3b | runtime | Sandbox hard-fail — `sandbox.failIfUnavailable` | `false` (silently falls back to unsandboxed if deps missing) | `true` only if the user wants sandboxing to be a hard security gate rather than best-effort | HIGH | yes, security-relevant, user's own risk call | New row. Same doc as row 3. Not a universal recommendation — analogous framing to opencode row 6. |
| 4 | runtime | OpenTelemetry export — `CLAUDE_CODE_ENABLE_TELEMETRY` + exporter env vars | off | on, with exporter env vars, for org/self usage-cost visibility | HIGH | yes | **Distinct from** Anthropic's own default-on operational metrics/error-reporting stream (opt-out via `DISABLE_TELEMETRY=1`/`DISABLE_ERROR_REPORTING=1` — do not conflate the two in the UI). Resolves open question 3: this is **not** gated by individual-vs-corporate account tier; it's gated by which API provider you connect through — metrics/error-reporting default OFF on Vertex/Bedrock/Foundry/AWS unless the matching `CLAUDE_CODE_USE_*` flag is set, default ON for direct Claude API. [VERIFIED: code.claude.com/docs/en/data-usage, "Default behaviors by API provider" table, fetched this session] |

### opencode (`~/.config/opencode/opencode.jsonc`)

| # | Scope | Check | Current default | Recommended | Confidence | Apply | Why / Source |
|---|-------|-------|------------------|-------------|------------|-------|--------------|
| 5 | — | Session retention | not configurable | N/A — informational only | HIGH | **no** | Resolves open question 2 with **two independent, current-session sources**, upgrading confidence beyond the PRD's single citation: (a) GitHub issue #22110 ("Session storage grows unboundedly...") was **closed as "not planned"** [CITED: github.com/anomalyco/opencode/issues/22110, fetched this session — confirmed "Closed" status, not merely "open feature request" as the PRD framed it]; (b) the full official config reference documents every top-level and nested key and contains **no** retention/cache-TTL/cleanup-period key anywhere [CITED: opencode.ai/docs/config/, fetched this session]. Still phrase as "not currently configurable," never "will never be configurable" — "not planned" is a disposition, not a permanent guarantee. |
| 6 | runtime | `permission` block — full action set | Most default `"allow"`; `doom_loop`/`external_directory` default `"ask"`; `read` allows by default but denies `.env` | Lock down per the user's own risk tolerance (`"ask"`/`"deny"` per action) | HIGH | yes, security-relevant | Expands the PRD's 4-action list (`bash`/`edit`/`webfetch`/`read`) to the **full documented set**: `read`, `edit`, `glob`, `grep`, `bash`, `task`, `skill`, `lsp`, `question`, `webfetch`, `websearch`, `external_directory`, `doom_loop`. [CITED: opencode.ai/docs/permissions/, fetched this session] |
| 7 | runtime | `share` mode | `"manual"` | `"disabled"` for privacy-conscious users | MEDIUM | yes | Carried forward from the source PRD (`opencode.ai/docs/share/`) — not re-fetched this session. [CITED: PRD] |
| 7b | model | Per-model reasoning/verbosity options — `provider.<name>.models.<model>.options.{reasoningEffort, textVerbosity, reasoningSummary}` (OpenAI-family) / `.options.thinking.{type, budgetTokens}` (Anthropic-family) | unset | Set per the active model's capability (e.g. `reasoningEffort: "high"` for complex agentic work) | HIGH for the officially-documented `openai`/`anthropic` provider ids; **LOW/ASSUMED** for this specific machine's setup | yes for documented provider ids; **no** (informational) for custom-router setups until verified | Resolves D-02 and open question 6 for opencode. Verbatim documented example: `provider.openai.models["gpt-5"].options.reasoningEffort` / `provider.anthropic.models["claude-sonnet-4-5-20250929"].options.thinking.budgetTokens`. [CITED: opencode.ai/docs/models/, fetched this session, JSONC example captured verbatim] **This machine's own `opencode.jsonc` routes everything through a custom OpenAI-compatible provider `router-env`** (not the literal `"openai"`/`"anthropic"` provider ids) [VERIFIED: this session's own read of the live file] — whether `options.reasoningEffort` passes through such a custom router was **not tested this session**; see Assumptions Log A2. |

### Codex (`~/.codex/config.toml`)

| # | Scope | Check | Current default | Recommended | Confidence | Apply | Why / Source |
|---|-------|-------|------------------|-------------|------------|-------|--------------|
| 8 | runtime | `sandbox_mode` | Enum is `"read-only" \| "workspace-write" \| "danger-full-access"`; **no default value was stated in the fetched official doc**, and this machine's `config.toml` has **no `sandbox_mode` key at all** (live-verified — absence, not a documented default) | `workspace-write` + `approval_policy = "on-request"` (or the newer granular form, see below) | MEDIUM — enum confirmed, default unconfirmed (see Assumptions Log A5) | yes, security-relevant | [VERIFIED: learn.chatgpt.com/docs/config-file/config-reference, fetched this session] `approval_policy` also supports a newer granular object form: `{ granular = { sandbox_approval, rules, mcp_elicitations, request_permissions, skill_approval } }`, distinct from the PRD's simple string enum (`"on-request" \| "never"`) — worth surfacing as a richer apply option. |
| 9 | runtime | `features.hooks` | `false` by default; **this machine has it `= true`** (live-verified) | Informational only — same treatment as row 5, per D-04 | HIGH | **no** (D-04) | `features.codex_hooks` is a documented deprecated alias for the same key — the value-reader must check both. [VERIFIED: learn.chatgpt.com/docs/config-file/config-reference, fetched this session] |
| 10 | **model** | `model_reasoning_effort` | Enum `"minimal" \| "low" \| "medium" \| "high" \| "xhigh"` (Responses API only, `xhigh` model-dependent); **no default stated in the official doc** (PRD's "community-documented as medium" claim stays exactly as low-confidence as the PRD already flagged it — reconfirmed, not upgraded, this session) | `high`/`xhigh` for complex/multi-file work, **varying by the active model** | LOW on the "medium" default claim (community-sourced only); HIGH on the enum values themselves | yes, labeled low-confidence in the UI | Reframed to `scope: model` per D-02 (the PRD had this as a flat runtime recommendation). This machine's `config.toml` has `model = "gpt-5.6-luna"`, `model_reasoning_effort = "low"` (live-verified) — the mechanism for "recommend `high` only for capable models" is left to the planner per D-02's own scoping. [VERIFIED enum: learn.chatgpt.com/docs/config-file/config-reference, fetched this session] |
| 10b | runtime | `history.max_bytes` | unset (no cap) | Set a cap if disk usage is a concern | HIGH | yes | **Not a duration control** — caps `history.jsonl` by byte size, dropping oldest entries, when set. Partially answers open question 4: Codex has a size-based cap but not a duration-based one for actual session history. [VERIFIED: learn.chatgpt.com/docs/config-file/config-reference, fetched this session] |
| 10c | runtime | `[memories]` subsystem duration settings — `max_unused_days` (default `30`, clamp `0`-`365`), `max_rollout_age_days` (default `30`, clamp `0`-`90`), `min_rollout_idle_hours` (default `6`, clamp `1`-`48`) | as stated | Informational only unless `[memories]` is confirmed active | HIGH on the values; MEDIUM on whether they're relevant to this project's retention goal | **no** | **These are NOT session-history retention** despite the duration-adjacent naming — they govern a separate memory-consolidation feature (which threads get mined into durable "memories"), not the raw `history.jsonl` transcript. [VERIFIED: learn.chatgpt.com/docs/config-file/config-reference, `[memories]` section, fetched this session] GitHub issue #6015 (open, unaddressed as of this session) confirms Codex has no actual history-cleanup window: "Codex retains every conversation indefinitely." [CITED: github.com/openai/codex/issues/6015, fetched this session] |
| 11 | runtime | `history.persistence` | `"save-all"` | `"none"` only if the user wants it (privacy trade-off) | HIGH | yes, opt-in only, never defaulted to "recommended: apply" | Enum confirmed: `"save-all" \| "none"`. [VERIFIED: learn.chatgpt.com/docs/config-file/config-reference, fetched this session] |

### Cursor (`~/.cursor/cli-config.json`) — NEW, D-03

| # | Scope | Check | Current default | Recommended | Confidence | Apply | Why / Source |
|---|-------|-------|------------------|-------------|------------|-------|--------------|
| 13 | runtime | `permissions.allow`/`permissions.deny` | Entries are typed exact-match strings: `Shell(cmd)`, `Read(glob)`, `Write(glob)`, `WebFetch(domain)`, `Mcp(server:tool)`; **this machine's live config has `allow: ["Shell(ls)"], deny: []`** — very open by default | Lock down per risk tolerance, same framing as opencode row 6 | HIGH | yes, security-relevant | Deny rules take precedence over allow rules. [CITED: cursor.com/docs/cli/reference/permissions, fetched this session] Live value: [VERIFIED: `~/.cursor/cli-config.json`, read this session — `"permissions": {"allow": ["Shell(ls)"], "deny": []}`] |
| 14 | runtime | `approvalMode` | Enum `"allowlist" \| "auto-review" \| "unrestricted"`; **this machine already has `"allowlist"`** (the tightest documented mode) | Keep/set `"allowlist"` if not already | HIGH | yes (mostly a confirmation on this machine) | [CITED: cursor.com/docs/cli/reference/configuration, fetched this session] Live value: [VERIFIED: `~/.cursor/cli-config.json` — `"approvalMode": "allowlist"`] |
| 15a | runtime | `cli-config.json`'s own `sandbox.mode`/`sandbox.networkAccess` keys (CLI-level toggle) | Documented as existing optional keys but **no default or full enum value set was stated** in the fetched doc; this machine has `sandbox.mode: "disabled"`, `sandbox.networkAccess: "user_config_with_defaults"` | Informational only pending clearer official docs on exact values | MEDIUM (keys confirmed to exist; exact semantics unconfirmed) | **no**, until the value set is better documented | [CITED: cursor.com/docs/cli/reference/configuration, fetched this session] Live value: [VERIFIED: `~/.cursor/cli-config.json` — `"sandbox": {"mode": "disabled", "networkAccess": "user_config_with_defaults"}`] **Do not conflate with row 15b** — these are two separate mechanisms. |
| 15b | runtime | `sandbox.json` — a **separate file** (`~/.cursor/sandbox.json` global, or `<workspace>/.cursor/sandbox.json` project, higher priority) | `type` defaults to `"workspace_readwrite"` if the file is absent (per doc); other values `"workspace_readonly"` / `"insecure_none"`; `networkPolicy.default` defaults `"deny"` | `type: "workspace_readonly"` or a scoped `networkPolicy` for stronger isolation, analogous to Claude Code row 3 | HIGH (fully documented schema) | yes, security-relevant | Protected always-write-blocked paths: `.cursor/*.json`, `.git/hooks/**`, `.vscode/**` (with `rules/`, `commands/`, `worktasks/`, `skills/`, `agents/` subdirectories inside `.cursor` remaining writable). [CITED: cursor.com/docs/reference/sandbox, fetched this session] **Neither `sandbox.json` nor any file exists in `~/.cursor/sandbox-policies/` on this machine** — that directory is present but **empty** [VERIFIED: `ls -la ~/.cursor/sandbox-policies` this session, empty]. CONTEXT.md's open question 1 named `~/.cursor/sandbox-policies/` explicitly; the correct, currently-documented location is `sandbox.json` (singular file), **not** a `sandbox-policies/` directory — no official doc names that directory. Flag this discrepancy explicitly; it is unresolved (see Open Questions). |
| 16 | **model** | `modelParameters.<modelId>` array of `{id, value}` objects (e.g. `{"id": "reasoning", "value": "medium"}`) | Not documented on the official Configuration reference page fetched this session (that page lists `model`, `maxMode`, `hasChangedDefaultModel` but not `modelParameters`) | Informational only — schema is undocumented despite being directly observable | **LOW** (undocumented schema, despite being read from a real file) | **no** — or gated behind `checkpoint:human-verify` if the planner insists on an apply path | Resolves D-02 and part of open question 6 for Cursor. [VERIFIED: `~/.cursor/cli-config.json`, read this session, verbatim — `"modelParameters": {"gpt-5.2": [{"id": "reasoning", "value": "medium"}, {"id": "fast", "value": "false"}], "glm-5.2": [{"id": "reasoning", "value": "high"}], "gpt-5.6-luna": [{"id": "context", "value": "272k"}, {"id": "reasoning", "value": "low"}, {"id": "fast", "value": "false"}], "composer-2.5": [{"id": "fast", "value": "false"}]}`] Observed `id` values: `reasoning`, `fast`, `context` — no doc confirms this is the complete accepted set. |
| 17 | — | Local CLI chat/session retention | **Unresolved** — no key found in `cli-config.json`'s documented schema, no CLI docs page names a local retention/TTL/cleanup setting | N/A | **N/A — genuinely open, not "confirmed absent"** | **no** | CLI chats live under `~/.cursor/chats` [CITED: forum.cursor.com thread, fetched this session] (directory confirmed present on this machine: [VERIFIED: `ls -la ~/.cursor` this session shows `chats/`]). The only retention information found concerns **cloud-side** conversation storage ("kept indefinitely by default... Enterprise teams can cap retention") [CITED: cursor.com/docs/enterprise/privacy-and-data-governance-adjacent search result, fetched this session] and a 90-day environment-snapshot cloud window — neither is the local on-disk chat history this row would need. Per the absent-evidence provenance rule, this is **not** equivalent to opencode row 5 (which has a closed-not-planned issue as positive evidence) — this is a true gap requiring direct experimentation or a Cursor support inquiry before it becomes a real catalog row. See Open Questions and Assumptions Log A3. |
| 18 | — | CLI-specific telemetry toggle | **Unresolved** — no CLI docs page found documenting a telemetry flag/env var for `cursor-agent`; only the unrelated **editor's** `telemetry.enableTelemetry`/`telemetry.telemetryLevel` VS-Code-style settings were found, a different product surface | N/A | **N/A — genuinely open** | **no** | Same evidentiary situation as row 17. Do not present "no CLI telemetry setting" with the same confidence as opencode row 5. See Assumptions Log A4. |
| 19 | runtime | `attribution.attributeCommitsToAgent` / `attribution.attributePRsToAgent` | both `true` | Leave as-is or disable per privacy preference | HIGH | yes, low-stakes | Adds a "Made with Cursor" trailer/footer to commits/PRs. [CITED: cursor.com/docs/cli/reference/configuration, fetched this session] |

### Cross-runtime

| # | Scope | Check | Current default | Recommended | Confidence | Apply | Why / Source |
|---|-------|-------|------------------|-------------|------------|-------|--------------|
| 12 | — | `rtk` Cursor integration installed | Point-in-time — re-probe with `rtk init --show` at build/verify time, not fixed by this research session | `rtk init -g --agent cursor` if reported absent | HIGH (mechanism), inherently time-varying (result) | yes | Folded in from the Tool-Substitution Awareness Hook PRD's Non-Goals note, per `tools/hooks/README.md`'s own closing line: "Phase 4's config doctor folds this non-goals note in as its cross-runtime `rtk`-integration check." [VERIFIED: `tools/hooks/README.md`, read this session] |
| 20 | — | `rtk`'s own `[tee].max_files` | **This machine's live value:** `max_files = 20`, `max_file_size = 1048576` (1 MiB) [VERIFIED: `~/.config/rtk/config.toml`, read this session, verbatim] | ~`100` (user's own stated intent, CONTEXT.md open question 7) | Disk-math is HIGH (mechanical arithmetic on verified values: `20` files → ≤20 MiB cap; `100` files → ≤100 MiB cap); the "100 is sensible" claim itself is **LOW/ASSUMED** | **Scope question for the planner — see below** | No official rtk documentation was found: `rtk --help`, `rtk config --help`, and `rtk tee --help` (which resolved to GNU coreutils' unrelated `tee(1)`, not an rtk subcommand) do not document the `[tee]` block's tuning guidance, and no public rtk docs site was found via search. **`~/.config/rtk/config.toml` is not one of the four AI-CLI runtimes' own config files** — REQUIREMENTS.md's REQ-config-doctor-diagnostic-checks wording covers "Claude Code, opencode, Codex, and Cursor settings" plus a singular folded-in rtk-**Cursor-integration** check (row 12) — a new rtk-config-**editing** row is a further scope expansion the planner/user should explicitly confirm, since it requires a THIRD TOML-target beyond Codex, for a setting with zero upstream guidance on what value is "sensible." See Assumptions Log A1. |

## Standard Stack

No new external package is proposed by this phase. The TUI reuses the
project's existing dev/wizard-only `textual>=8.0,<9.0` dependency (already
declared in `pyproject.toml`'s `dev` group per `AGENTS.md`'s Tools and Stack
section — not re-verified this session, since it's an already-shipped,
already-pinned dependency, not a new one this phase introduces). TOML
reading uses the stdlib `tomllib` (Python 3.11+), already used in
`tools/setup.py:36`. There is **no stdlib TOML writer** — Codex's
`config.toml` (and, if row 20 is scoped in, rtk's `config.toml`) must be
edited via text-region replacement (see `write_toml_preserving`,
`tools/setup.py:451-508`), not a round-trip parse-mutate-serialize cycle.

### Installation

No new packages to install for this phase.

## Package Legitimacy Audit

**Not applicable.** This phase installs no new external packages —
`textual` is an already-audited, already-pinned dev/wizard dependency from
prior phases (Phase 2's wizard, `tools/wizard_app.py`). No new npm/PyPI/
crates package is introduced. If a future iteration proposes a third-party
TOML-writer library (e.g. to avoid the text-region-replace approach), that
would need its own legitimacy check at that time — flagged here as a
forward-looking note, not a current finding.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────┐
                    │  tools/setup.py --config-doctor │
                    │  (D-07: new flag, not a subcommand) │
                    └───────────────┬─────────────┘
                                    │ ensure_rich_runtime(env)  (D-06, reused as-is)
                                    ▼
                    ┌─────────────────────────────┐
                    │  tools/config_doctor_app.py  │  ◄── TUI view layer (D-06)
                    │  (textual App, mirrors        │      pure view: imports nothing
                    │   wizard_app.py's style)       │      from setup.py; receives an
                    └───────────────┬─────────────┘      injected context, same as
                                    │                     WizardContext today
           ┌────────────────────────┼────────────────────────┐
           │ read (all rows)        │ per-item confirm        │
           ▼                        ▼                         ▼
┌─────────────────────────┐  ┌───────────────────────┐  ┌────────────────────┐
│ Checks Catalog (D-01)   │  │ Confirm dialog: show   │  │ Format-specific     │
│ declarative row records │  │ literal resulting      │  │ apply-writer        │
│ {runtime, scope, check, │  │ config before writing  │  │ (per REQ-apply-flow)│
│  reader, recommended,   │  └───────────┬────────────┘  └──────────┬──────────┘
│  confidence, apply_fn}  │              │ confirmed                │
└────────────┬─────────────┘              ▼                         ▼
             │              ┌──────────────────────────────────────────────┐
             │ config-file  │  JSON atomic write   │ JSONC surgical edit  │ TOML region  │
             │ presence     │  (Claude Code,        │ (opencode — PORTED  │ replace      │
             │ (D-03)       │   Cursor)             │  from, not imported │ (Codex, and  │
             ▼              │  adapted from          │  from, skills/      │ optionally    │
┌─────────────────────┐     │  setup.py::            │  ai-kit-opencode-   │ rtk if row 20 │
│ ~/.claude/settings.json│  │  _atomic_write_json    │  providers)         │ is in-scope)  │
│ ~/.config/opencode/    │  └──────────────────────────────────────────────┘
│   opencode.jsonc       │
│ ~/.codex/config.toml   │
│ ~/.cursor/cli-config.json│
└─────────────────────┘
```

A section is skipped entirely (not shown failing) when its config file is
absent — the presence check itself is the first read, before any row inside
that runtime's section is evaluated.

### Recommended Project Structure

```
tools/
├── config_doctor_app.py       # TUI view layer (D-06) — textual App, no setup.py imports
├── config_doctor_checks.py    # D-01 declarative catalog + generic engine — NO textual import
│                               # (kept import-clean for the deferred CLI front-end, Backlog 999.1)
├── config_doctor_readers.py   # per-format value readers (JSON/JSONC/TOML), read-only
├── config_doctor_appliers.py  # per-format atomic writers — PORTED, not imported, from
│                               # skills/ai-kit-opencode-providers' jsonc_edit.py/atomic_write.py
│                               # and adapted from setup.py's write_toml_preserving /
│                               # _atomic_write_json
└── setup.py                   # wires --config-doctor (D-07), calls ensure_rich_runtime()
                                # then imports config_doctor_app the same way it already
                                # imports wizard_app (sys.path.insert pattern, setup.py:~2477-2483)
```

Module boundaries are a planning decision, not locked by this research — the
one hard constraint is: the D-01 engine module(s) must not import `textual`,
and no `tools/` module may import a `skills/ai-kit-opencode-providers`
package (see Common Pitfall 1).

### Pattern 1: Declarative check registry (D-01)

**What:** Each Checks Catalog row is a data record, not a hardcoded function.
**When to use:** Always, for every row in this catalog — this is a locked
decision.
**Example (illustrative shape, not sourced from any file — this project has
no prior declarative-registry precedent to cite verbatim):**
```python
CheckRow(
    id="claude-retention",
    runtime="claude",
    scope="runtime",
    check="cleanupPeriodDays",
    read=lambda cfg: cfg.get("cleanupPeriodDays", 30),
    recommended=3650,
    confidence="HIGH",
    apply=write_cleanup_period_days,   # or None for informational-only rows
    why="Local transcript retention; never recommend 0 (see Common Pitfall 2)",
    source="https://code.claude.com/docs/en/data-usage",
)
```

### Pattern 2: Config-file-presence detection (D-03)

**What:** A runtime's section is shown only if its config file exists on
disk — never based on `detect_installed_clis()` (binary-on-PATH).
**When to use:** Once per runtime, before evaluating any of its rows.
**Example:**
```python
# Source: pattern established by D-03's own live verification during
# Phase 4's discussion (04-CONTEXT.md) — not yet code in this repo.
RUNTIME_CONFIG_PATHS = {
    "claude": "~/.claude/settings.json",
    "opencode": "~/.config/opencode/opencode.jsonc",   # honors OPENCODE_CONFIG_DIR/XDG_CONFIG_HOME
    "codex": "~/.codex/config.toml",                    # honors $CODEX_HOME
    "cursor": "~/.cursor/cli-config.json",               # honors CURSOR_CONFIG_DIR/XDG_CONFIG_HOME
}
```
opencode's own override precedence (`OPENCODE_CONFIG_DIR` →
`XDG_CONFIG_HOME` → `$HOME/.config/opencode`) is already implemented in this
codebase: `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/config_paths.py:8-17`
(`default_config_path`). Cursor's equivalent override
(`CURSOR_CONFIG_DIR` / `XDG_CONFIG_HOME`) is documented but not yet
implemented anywhere in this repo. [CITED: cursor.com/docs/cli/reference/configuration, fetched this session]

### Anti-Patterns to Avoid

- **Importing `skills/ai-kit-opencode-providers` from `tools/`:** already an
  explicitly documented anti-pattern in this codebase — see Common Pitfall 1.
- **Round-tripping TOML through a third-party serializer:** violates the
  stdlib-only runtime constraint and risks losing comments/formatting the
  same way an unguarded JSON dump would (already solved for JSONC by
  `jsonc_edit.py`; must not be re-broken for TOML).
- **Recommending `cleanupPeriodDays: 0`:** never, regardless of version (see
  Common Pitfall 2).
- **Treating opencode's closed-not-planned issue as "will never happen":**
  present it as "not currently planned," a disposition that can change, not
  a permanent architectural fact.
- **Conflating two distinct mechanisms as one row:** Claude Code's two
  telemetry systems (Common Pitfall 4), Cursor's two sandbox mechanisms
  (Common Pitfall 5).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| TOML parsing | A new TOML reader | stdlib `tomllib` | Already used in `tools/setup.py:36`; read-only, which is all a Checks Catalog *reader* needs |
| TOML byte-preserving edit | A round-trip parse→mutate→serialize cycle | `write_toml_preserving`'s text-region-replace approach (`tools/setup.py:451-508`) | No stdlib TOML writer exists; a naive dump would also risk dropping comments the way JSONC's naive approach would have, before Phase 2 solved it properly |
| JSONC comment-safe editing | A second regex-based JSONC scanner | Port the four-state classifier from `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/jsonc_edit.py` (string/escape/line-comment/block-comment states, `_classify()` at lines 30-88) | Already tested against real-world edge cases (literal `{`/`}` inside string values, trailing commas) in Phase 2 |
| Atomic file replace with mode/ownership preservation | A bare `open(path, "w")` | Port `write_preserving_mode` (`skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py:11-62`) or reuse `tools/setup.py`'s own `_atomic_write_json`/`_read_json`/`_write_json` (`tools/setup.py:1329-1346`, `1383-1420`ish) for the JSON targets | Handles fsync-before-replace durability (WR-01) and non-root chown-permission-denied swallowing (WR-02) — both already debugged once |
| textual-runtime availability guard | A second uv-re-exec guard | `ensure_rich_runtime()` as-is (`tools/setup.py:2685-2714`) | D-06: locked decision, entrypoint-agnostic already |

**Key insight:** Every hard problem this phase touches (atomic writes,
comment-safe JSONC edits, rich-runtime bootstrapping) has already been
solved once in this exact codebase. The only genuinely new work is the
declarative registry itself (D-01) and the Cursor/Codex/TOML-specific
readers this research newly catalogs.

## Common Pitfalls

### Pitfall 1: Reading "reuse the pattern" as "import the package"

**What goes wrong:** REQUIREMENTS.md's REQ-config-doctor-apply-flow says
"reusing the opencode-provider-management atomic-write + surgical-edit
pattern." A literal reading could lead to `tools/config_doctor_appliers.py`
doing `from ai_kit_opencode_providers.jsonc_edit import remove_provider` or
similar.
**Why it happens:** The wording genuinely sounds like a code-reuse
instruction, and Phase 2's module is well-tested and directly applicable.
**How to avoid:** This codebase already has an explicit, commented rule
against exactly this: `tools/setup.py:1386-1388`'s own docstring for
`_atomic_write_json` says verbatim: *"Adapted from
skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py
rather than imported (a tools/ module importing a skills/ package would be
a layering violation)."* [VERIFIED: `tools/setup.py:1383-1394`, read this
session] Port/adapt the logic, don't cross-import it.
**Warning signs:** Any `import` statement in a `tools/` module whose target
path starts with `ai_kit_opencode_providers` or any other `skills/*`
package name.

### Pitfall 2: Recommending `cleanupPeriodDays: 0`

**What goes wrong:** A user or an overly-generous apply-flow UI sets
`cleanupPeriodDays` to `0` intending "keep forever."
**Why it happens:** `0` reads naturally as "no limit" in many config
schemas; the actual semantics were a real, cited bug (GitHub #23710).
**How to avoid:** The bug is now fixed (v2.1.89+ rejects `0` as invalid
rather than silently disabling persistence), but the apply-flow should
still categorically refuse to write `0` for this key — don't rely on
runtime-version detection to decide whether `0` is "safe" this week.
**Warning signs:** Any free-text or numeric-input widget for this row that
doesn't have an explicit `0` guard.

### Pitfall 3: Reporting a flat "current" value for `promptCacheTtl`

**What goes wrong:** The check-reader reports `promptCacheTtl`'s "current"
value as a flat "5 minutes" (as the source PRD framed it).
**Why it happens:** The setting itself, when explicitly configured, is a
single flat value — but the *default* (when unset) genuinely varies by
billing/auth mode (1h on subscription within-plan usage, 5m otherwise) in a
way the local config file alone cannot reveal.
**How to avoid:** When the setting key is absent from `settings.json`, the
reader must report "unknown — depends on billing mode" rather than a flat
default, per REQ-config-doctor-review-screen's own "unknown, never silently
pass/fail" contract.
**Warning signs:** A reader function that returns a hardcoded default string
for this specific key without first checking whether the key is present.

### Pitfall 4: Conflating Claude Code's two telemetry systems

**What goes wrong:** A single "Telemetry: off" row implies Claude Code sends
nothing to Anthropic by default.
**Why it happens:** "Telemetry" is used informally for two separate, real
mechanisms: (a) Anthropic's own default-on operational metrics/error
reports (`DISABLE_TELEMETRY`/`DISABLE_ERROR_REPORTING` to opt out), and (b)
opt-in OpenTelemetry export to a user's own collector
(`CLAUDE_CODE_ENABLE_TELEMETRY`, row 4 in this catalog).
**How to avoid:** Keep these as conceptually distinct in the UI's "Why"
text even if they end up as one row's citation block — a user reading "off
by default" for (b) could wrongly infer (a) is also off.
**Warning signs:** UI copy that says "telemetry" without specifying which
of the two systems.

### Pitfall 5: Conflating Cursor's two sandbox mechanisms

**What goes wrong:** Treating `cli-config.json`'s `sandbox.mode` key and
the separate `~/.cursor/sandbox.json` file as the same setting.
**Why it happens:** Both use the word "sandbox," both appeared in this
research, and this machine's `cli-config.json` genuinely does have a
`sandbox` object with `mode`/`networkAccess` keys.
**How to avoid:** Row 15a (the `cli-config.json` keys, MEDIUM confidence,
under-documented) and row 15b (the separate `sandbox.json` file, HIGH
confidence, fully documented schema) must stay two distinct catalog rows.
**Warning signs:** A single reader function trying to resolve both from one
file.

### Pitfall 6: Presenting Codex's `[memories]` settings as session-history retention

**What goes wrong:** `memories.max_rollout_age_days` (a real, documented,
duration-based setting) gets marketed to the user as "Codex's version of
Claude's `cleanupPeriodDays`."
**Why it happens:** It's the only duration-shaped setting Codex has, and
the name ("rollout age") is adjacent to "session history."
**How to avoid:** It governs which threads get mined into the separate
memory-consolidation feature, not whether `history.jsonl` itself is
retained or deleted — GitHub issue #6015 (open, unaddressed) confirms Codex
retains every conversation transcript indefinitely regardless of these
settings. [CITED: github.com/openai/codex/issues/6015, fetched this
session]
**Warning signs:** UI copy using the word "retention" for row 10c without
the "not the same as history.jsonl" caveat.

### Pitfall 7: Treating Cursor's `modelParameters` as a safe apply target

**What goes wrong:** Row 16's per-model `reasoning`/`fast`/`context`
parameters get an apply action because they were directly observed in a
real config file, which feels like solid ground.
**Why it happens:** [VERIFIED: read from a real file] and [documented by
Cursor] are not the same confidence tier — this key is entirely absent from
the official Configuration reference page fetched this session.
**How to avoid:** Treat row 16 as informational-only, or gate any apply
path behind `checkpoint:human-verify`, since the accepted `id`/`value`
combinations beyond the three observed (`reasoning`, `fast`, `context`) are
unknown, and a bad write here risks silent misconfiguration with no
official schema to validate against.
**Warning signs:** An apply-writer for this row that doesn't have an
explicit lower-confidence code path than every other apply-eligible row.

## Code Examples

### Atomic JSON write (adapt this pattern for Claude Code / Cursor targets)

```python
# Source: skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py:11-44
# (port/adapt, do not import — see Common Pitfall 1)
def write_preserving_mode(path: str, text: str) -> None:
    """Atomically write `text` to `path`, preserving mode and symlink target."""
    target = os.path.realpath(path)
    st = os.stat(target)
    mode = stat.S_IMODE(st.st_mode)
    dirname = os.path.dirname(target) or "."
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        with contextlib.suppress(OSError, AttributeError):
            os.chown(tmp, st.st_uid, st.st_gid)
        os.replace(tmp, target)
        dir_fd = os.open(dirname, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
```

### TOML region-preserving write (the only established pattern for Codex — no stdlib TOML writer exists)

```python
# Source: tools/setup.py:451-458 (signature + core write/verify shape; abridged)
def write_toml_preserving(path, text, statusline_doctor):
    """Atomically write `text` to `path`, then self-validate via the doctor.

    Writes to a sibling temp file and os.replace()s it into place (atomic).
    ...Returns True on success."""
    prev = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            prev = f.read()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        return False
    # ... (self-validation + revert-on-failure follows; adapt the
    # self-validation call for whichever per-runtime checker exists, if any —
    # Config Doctor has no equivalent of statusline-doctor.py per runtime,
    # so this step may be a plain "does it still parse as valid TOML/JSONC"
    # check via tomllib.loads / the JSONC scanner, not a subprocess call)
```

### Rich-runtime guard (reuse as-is, D-06)

```python
# Source: tools/setup.py:2685-2714 (signature only; call unmodified)
def ensure_rich_runtime(env):
    """Guarantee textual is importable, or fail closed. Re-exec under uv at most
    once (env marker guards the loop)."""
    if _textual_importable():
        return
    # ... re-exec-under-uv / install-uv / fail-closed logic, unchanged
```

### opencode per-model options (documented, citable example — use for row 7b's reader/writer target shape)

```jsonc
// Source: opencode.ai/docs/models/ (fetched this session, verbatim documented example)
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "openai": {
      "models": {
        "gpt-5": {
          "options": {
            "reasoningEffort": "high",
            "textVerbosity": "low",
            "reasoningSummary": "auto",
            "include": ["reasoning.encrypted_content"]
          }
        }
      }
    },
    "anthropic": {
      "models": {
        "claude-sonnet-4-5-20250929": {
          "options": {
            "thinking": { "type": "enabled", "budgetTokens": 16000 }
          }
        }
      }
    }
  }
}
```

### Config-path resolution honoring env-var overrides (established pattern to port for Cursor)

```python
# Source: skills/ai-kit-opencode-providers/ai_kit_opencode_providers/config_paths.py:8-17
def default_config_path(env: dict) -> str:
    """`${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}/opencode.jsonc`."""
    config_dir = env.get("OPENCODE_CONFIG_DIR")
    if config_dir:
        base = config_dir
    elif env.get("XDG_CONFIG_HOME"):
        base = os.path.join(env["XDG_CONFIG_HOME"], "opencode")
    else:
        base = os.path.join(env.get("HOME", ""), ".config", "opencode")
    return os.path.join(base, "opencode.jsonc")
```
Cursor's documented equivalent override is `CURSOR_CONFIG_DIR` (falling
back to `$XDG_CONFIG_HOME/cursor/cli-config.json` on Linux/BSD, then
`~/.cursor/cli-config.json`) — not yet implemented anywhere in this repo.
[CITED: cursor.com/docs/cli/reference/configuration, fetched this session]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-------------------|---------------|--------|
| `cleanupPeriodDays: 0` silently disables all transcript persistence | `0` is rejected as invalid, shown as an error in `/status` | Claude Code v2.1.89 | The PRD's original citation (GitHub #23710) described the *old* broken behavior; the underlying risk (never recommend `0`) is unchanged, but the failure mode the apply-flow must guard against has shifted from "silent data loss" to "rejected write" |
| `promptCacheTtl`/`subagentPromptCacheTtl` settings and their env vars did not exist | Both settings + env vars available | Requires Claude Code v2.1.242+ | A check-reader running against an older Claude Code install should report "setting unavailable on this version" rather than "unset, recommend 1h" |
| opencode issue #22110 was an open feature request (as the source PRD, written 2026-09-07, characterized it) | Closed as "not planned" | Closed sometime before this session (2026-09-09) | Slightly stronger evidentiary basis for row 5's "not currently configurable" framing than the PRD had |
| PreModelSwitch confirmation didn't check cache TTL, so Claude Code asked to confirm a model switch even after the cache had already expired | Checks the TTL first | Claude Code v2.1.238 | Tangential to this phase; noted for completeness, not a catalog row |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `rtk`'s `[tee].max_files` recommended value of ~`100` is sensible | Cross-runtime row 20 | Low security risk (local disk usage only), but the "recommended" value has zero sourced backing — presenting it with the same UI treatment as e.g. row 3 (which has official docs) would misrepresent its confidence tier |
| A2 | opencode's `options.reasoningEffort`/`textVerbosity` pass through when routed via this machine's custom `router-env` OpenAI-compatible provider (rather than the literal `"openai"` provider id) | opencode row 7b | A model-scoped recommendation could be silently ignored by the custom router with no error surfaced, giving the user false confidence that a setting took effect |
| A3 | Cursor's local CLI chat retention has no configurable control at all | Cursor row 17 | Could either wrongly claim "not configurable" (overclaiming certainty vs. opencode row 5's stronger evidence) or miss a real, undiscovered setting |
| A4 | Cursor's CLI has no telemetry-specific toggle distinct from the editor's `telemetry.*` settings | Cursor row 18 | Same as A3, elevated because it's a privacy-adjacent claim — PROJECT.md's confidence-labeling constraint treats these with extra care |
| A5 | Codex's `sandbox_mode` truly has no sandboxing as its behavior when the key is entirely absent from `config.toml` | Codex row 8 | The check-reader may report "unset = no sandboxing" as a known state without a citation confirming that's really what absence means (vs. some other implicit fallback) |

**If this table is empty:** N/A — see above.

## Open Questions

1. **Cursor's `sandbox-policies/` directory (empty, present on this machine) vs. the documented `sandbox.json` file** — no official doc names a `sandbox-policies/` directory anywhere. Is this a legacy/deprecated mechanism, a future-reserved location, or something Cursor's own installer created without ever populating? Recommendation: treat `sandbox.json` (row 15b) as the only citable apply target; do not build any reader/writer against the `sandbox-policies/` directory without further confirmation.
2. **Cursor local CLI chat retention (row 17)** — genuinely unresolved; requires either direct experimentation against a real `cursor-agent` install over time, or a Cursor support/community inquiry. Recommendation: ship without this row, or ship it explicitly labeled "unknown, needs confirmation" rather than skip it silently.
3. **Cursor CLI telemetry toggle (row 18)** — same situation as #2. Recommendation: same treatment.
4. **`rtk`'s `[tee].max_files` — is this in scope for this phase at all?** (row 20) REQUIREMENTS.md's wording covers the 4 AI-CLI runtimes plus a singular rtk-**Cursor-integration** check; a general rtk-config-editing row is an extra scope question. Recommendation: raise explicitly with the user before the planner locks this row into the build; it introduces a third TOML target with zero upstream documentation to build a reader/writer against.
5. **Whether opencode's per-model options apply through a custom OpenAI-compatible router (this machine's actual setup)** — see A2. Recommendation: either test directly against the live `router-env` provider before shipping row 7b as apply-eligible for non-standard provider ids, or scope row 7b's apply action to only the literal `"openai"`/`"anthropic"` provider ids and leave custom-provider setups informational-only.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Python `tomllib` (stdlib) | Codex TOML reading | ✓ | Python 3.11+ (already required project-wide per `AGENTS.md`) | — |
| `textual` | TUI (D-05/D-06) | ✓ | `>=8.0,<9.0` (already pinned, dev/wizard-only, per `pyproject.toml`'s `dev` group) | Fails closed via `ensure_rich_runtime()` if unimportable — no CLI-only fallback ships in this phase (that's the deferred Backlog 999.1 work) |
| `~/.claude/settings.json` | Claude Code section | ✓ (this dev machine) | — | Section skipped if absent, per D-03 — not a blocker |
| `~/.config/opencode/opencode.jsonc` | opencode section | ✓ (this dev machine) | — | Same |
| `~/.codex/config.toml` | Codex section | ✓ (this dev machine) | — | Same |
| `~/.cursor/cli-config.json` | Cursor section | ✓ (this dev machine) | — | Same |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:** `textual` absence is already handled
by the existing `ensure_rich_runtime()` fail-closed/re-exec-under-uv path
(D-06, reused as-is) — no new fallback logic needed for this phase.

Per `AGENTS.md`'s Testing section, **tests must never use these real
machine config files as fixtures** — the above table documents live
machine state observed for research/citation purposes only, not a build
dependency or a test fixture source.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `unittest` (stdlib), matching every existing test module in this repo |
| Config file | none — plain `python3 -m unittest` invocation |
| Quick run command | `python3 -m unittest tests.test_config_doctor` (proposed new module — see Wave 0 Gaps) |
| Full suite command | `make test` — [VERIFIED: `Makefile:33-34`, read this session — `test:` target runs `python3 -m unittest tests.test_setup tests.test_status_line tests.test_external_segments tests.test_statusline_doctor tests.test_arch tests.test_markdown_to_pdf tests.test_worktree_e2e tests.test_wizard_pty tests.test_system_memory_e2e tests.test_ai_kit_spec tests.test_ai_kit_spec_gsd tests.test_ai_kit_opencode_providers tests.test_tool_substitution_hook`] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| REQ-config-doctor-diagnostic-checks | Each value-reader handles present/absent/malformed config file | unit | `python3 -m unittest tests.test_config_doctor -k readers -v` | ❌ Wave 0 |
| REQ-config-doctor-diagnostic-checks | A runtime with no config file present skips its whole section | unit | `python3 -m unittest tests.test_config_doctor -k presence -v` | ❌ Wave 0 |
| REQ-config-doctor-review-screen | TUI renders current/recommended/citation per row, "unknown" for undeterminable values | TUI smoke test, PTY-driven (mirror `tests/test_wizard_pty.py`'s approach) | `python3 -m unittest tests.test_config_doctor_pty -v` | ❌ Wave 0 |
| REQ-config-doctor-apply-flow | Atomic write + byte-preservation for JSON/JSONC/TOML targets | unit | `python3 -m unittest tests.test_config_doctor -k apply -v` | ❌ Wave 0 |
| REQ-config-doctor-apply-flow | No bulk "apply all" exists anywhere in the flow | unit/structural | `python3 -m unittest tests.test_config_doctor -k no_bulk -v` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** the relevant `-k <filter>` slice above
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_config_doctor.py` — covers all REQ-config-doctor-diagnostic-checks and REQ-config-doctor-apply-flow unit-level behavior, using synthetic fixtures only (never this machine's real config files, per `AGENTS.md`'s Testing section)
- [ ] `tests/test_config_doctor_pty.py` (or folded into the above) — TUI smoke test mirroring `tests/test_wizard_pty.py`'s PTY-driven pattern
- [ ] `Makefile:34`'s `test:` target — add the new module(s) to the existing `python3 -m unittest tests....` line, same as `test_ai_kit_opencode_providers` and `test_tool_substitution_hook` were added for their phases
- Framework install: none — `unittest` is stdlib, already the project convention

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|--------------------|
| V2 Authentication | no | This tool has no auth surface of its own |
| V3 Session Management | no | N/A |
| V4 Access Control | **yes** | The sandbox/permission rows themselves (Claude row 3/3b, opencode row 6, Codex row 8, Cursor rows 13/15a/15b) ARE access-control configuration — the standard control is the existing atomic-write + explicit-per-item-confirm pattern (never silent, literal resulting config shown before write), not a new mechanism |
| V5 Input Validation | **yes** | Parsing 3 real-world config formats (JSON, JSONC, TOML) from potentially malformed/adversarial-looking files — standard control: stdlib `json`/`tomllib` plus the hand-rolled JSONC scanner, degrade to "unknown" on any parse failure per `_read_json`'s own established `{}`-on-any-error pattern (`tools/setup.py:1329-1338`), never crash or guess |
| V6 Cryptography | no | No crypto surface in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Partial/corrupted write leaving a config file unparseable | Tampering (of the config's own integrity, not by an external attacker) | Atomic temp-file + `os.replace()` + `fsync`, already established (`write_preserving_mode`, `write_toml_preserving`, `_atomic_write_json`) |
| TOCTOU: config file changes between the Checks Catalog's read and the apply-writer's write (e.g. the user hand-edits the file in another terminal mid-session) | Tampering | Not solved by any existing pattern in this codebase — flagged as a **design question for the planner**: either re-read-and-re-diff immediately before writing, or accept the narrower atomicity guarantee (correct w.r.t. the value the writer itself computed, not necessarily w.r.t. a concurrent edit) and document that limitation in the apply confirm-dialog's copy |
| Malformed/oversized config file causing a crash or a hang during parsing | Denial of Service (self-inflicted, not adversarial, but still a real failure mode for a tool run against arbitrary user-edited files) | Same graceful-degrade-to-"unknown" pattern as V5 above |

## Sources

### Primary (HIGH confidence — official docs, fetched this session)

- code.claude.com/docs/en/data-usage — retention, telemetry account-conditionality, `cleanupPeriodDays` bug fix status
- code.claude.com/docs/en/prompt-caching — `promptCacheTtl`/`subagentPromptCacheTtl`, billing-tier-dependent defaults
- code.claude.com/docs/en/sandboxing — `sandbox.enabled`, `sandbox.failIfUnavailable`
- learn.chatgpt.com/docs/config-file/config-reference — Codex `sandbox_mode`, `approval_policy`, `model_reasoning_effort`, `history.persistence`, `history.max_bytes`, `features.hooks`, `[memories]` settings
- opencode.ai/docs/config/ — full opencode config key reference, confirmed no retention key exists
- opencode.ai/docs/permissions/ — full opencode permission action set and defaults
- opencode.ai/docs/models/ — per-model `options.reasoningEffort`/`thinking.budgetTokens` documented example
- cursor.com/docs/cli/reference/configuration — Cursor `cli-config.json` documented keys, env var overrides
- cursor.com/docs/cli/reference/permissions — Cursor permission types and precedence
- cursor.com/docs/reference/sandbox — `sandbox.json` schema (separate from `cli-config.json`'s own `sandbox` keys)
- github.com/anthropics/claude-code/issues/23710 — `cleanupPeriodDays: 0` bug, confirmed fixed in v2.1.89
- github.com/anomalyco/opencode/issues/22110 — confirmed closed as "not planned"
- github.com/openai/codex/issues/6015 — confirmed open, "Codex retains every conversation indefinitely"
- This machine's own live config files, read this session for citation/documentation purposes only, never written to: `~/.claude/settings.json`, `~/.config/opencode/opencode.jsonc`, `~/.codex/config.toml`, `~/.cursor/cli-config.json`, `~/.cursor/hooks.json`, `~/.config/rtk/config.toml`
- This repo's own code, read this session: `tools/setup.py` (lines 451-508, 1329-1394, 2620-2725), `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/{atomic_write.py,jsonc_edit.py,config_paths.py}`, `tools/hooks/{README.md,detect.py,cursor_session_start.py}`, `tools/wizard_app.py`, `Makefile`

### Secondary (MEDIUM confidence)

- opencode.ai/docs/share/ — `share` mode row, carried forward from the source PRD, not re-fetched this session
- Cursor's `cli-config.json` `sandbox.mode`/`networkAccess` exact semantics (row 15a) — key existence confirmed, full value/default semantics not fully documented

### Tertiary (LOW confidence — flagged, not presented as fact)

- Cursor local CLI chat retention (row 17) and CLI telemetry toggle (row 18) — genuinely unresolved, not confirmed absent nor confirmed present
- `rtk`'s `[tee].max_files` recommended value (row 20) — no source at all beyond the user's own stated preference

## Metadata

**Confidence breakdown:**
- Standard stack: N/A (no new packages) — see Package Legitimacy Audit
- Checks Catalog core rows (1-4, 5, 6, 7, 8, 9, 10b, 10c, 11): HIGH — freshly verified against official docs this session
- Checks Catalog model-scoped rows (7b, 10, 16): MEDIUM/LOW — mechanism confirmed, but exact applicability to this project's own setup (custom opencode router, undocumented Cursor schema) unverified
- Cursor rows overall (13-19): MEDIUM overall — most rows HIGH (permissions, approvalMode, sandbox.json, attribution), two rows (17, 18) genuinely LOW/unresolved
- Architecture (layering, atomic-write reuse): HIGH — directly sourced from this repo's own existing, commented code
- Pitfalls: HIGH — each pitfall traces to a specific citation or a specific piece of this repo's own code

**Research date:** 2026-09-09
**Valid until:** ~30 days for the stable, well-documented rows (official doc references, this repo's own code); ~7 days for the genuinely open Cursor rows (17, 18) and the rtk row (20), since those depend on either direct experimentation not yet performed or an upstream disposition that could resolve at any time
