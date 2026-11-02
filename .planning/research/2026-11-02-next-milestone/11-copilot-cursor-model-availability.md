# Copilot and Cursor: which listed models are actually usable

Research date 2026-11-02. Read-only. This note builds on `7-model-catalog-and-discovery.md`
(copilot section) and does not repeat it. Scripts and raw outputs are in this folder
(`11-*.py`, `11-*.sh`, `11-out/`). No keys or auth file contents were printed.

## Short answer

- **Copilot: the owner is right, and the gap is bigger than expected.** This account is on
  **Copilot Free** (local cache: `access_type_sku = free_limited_copilot`). GitHub's docs say Free
  and Student get models "through auto model selection only". The CLI rejects every named model,
  even one the server marks as enabled for this account. Past sessions resolved Auto to exactly
  one model, `mai-code-1.1-flash`.
- **There is a per-account, machine-readable Copilot list** (the models API that editors use). It
  carries a per-model `policy.state` (enabled/disabled). But on Free, `enabled` does **not** mean the
  CLI accepts it. So that list is only "listed", never "usable".
- **Copilot gives a clean, free availability probe.** `copilot -p "reply ok" --model X` fails in
  about 4 seconds with exit 1 and `Error: Model "X" from --model flag is not available.` That
  happens before any request, so it costs nothing. ai-kit's error catalogue does not match this
  text today.
- **Cursor: not checked live.** `cursor-agent` on this machine is **not logged in**
  ("Authentication required", `about` shows `Subscription Tier: Unknown`). The docs say Free has no
  third-party models. They do **not** say "Auto only". The "Free plans can only use Auto" text in
  ai-kit's catalogue is labelled unverified.

## 1. Copilot

### Official online lists (docs.github.com)

- **Supported models:** https://docs.github.com/en/copilot/reference/ai-models/supported-models
  - Has a per-client table with a Copilot CLI column, plus an "Auto model selection" table. Auto in
    the CLI includes GPT-5.6 Luna/Sol/Terra, GPT-6 Astra/Luna/Sol, GPT-6.1 Sol, Claude Opus 5/5.5,
    Claude Sonnet 5/5.5, Gemini 3.8 Flash and MAI-Code-1.1-Flash.
  - The page has no per-plan columns. It is about 380 KB of HTML and not machine-readable.
- **Per plan:** https://docs.github.com/en/copilot/get-started/plans
  - **Free:** "An allowance of GitHub AI Credits"; models: "Auto model selection only".
  - **Student:** same as Free.
  - **Pro:** 1,000 base AI credits (1,500 with the flex allotment); "A selection of models".
  - **Pro+:** 3,900 base credits (7,000 with flex); "Access to premium models".
  - **Business:** 1,900 credits per user per month; premium models.
  - **Enterprise:** 3,900 credits per user per month; "Priority access to premium models".
  - Quote: "On Copilot Free and Copilot Student plans, access to models is available through auto
    model selection only."
  - A June 2026 report says manual model selection was removed from Free and Student on
    2026-06-24 (roboin.io; secondary source).
- **Premium-request multipliers are gone.** Since 2026-06-01, Copilot bills in **AI credits**
  (1 credit = USD 0.01) at per-token rates. See
  https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing.
  - Each model has input, cached-input and output rates, and some have a long-context tier.
    Examples: MAI-Code-1.1-Flash 0.20/0.02/1.20; Claude Opus 5.5 4/0.20/20; GPT-6 Luna
    0.10/0.01/0.50 USD per 1M tokens.
  - Multipliers survive only for legacy annual Pro/Pro+ plans on request-based billing, on a
    separate legacy page (not fetched).
  - The pricing page names no machine-readable source.
- **Consequence for the catalog:** a "multiplier" field would be wrong for this account. The local
  cache shows `token_based_billing: true`, and the models API returns `billing.multiplier = 1` for
  every model, which carries no information.

### Local files (names and keys only)

- `~/.copilot/config.json`: JSONC with only `firstLaunchAt`; no model list.
  `~/.copilot/settings.json` does not exist (only its lock file).
- `~/.cache/copilot/copilot-user-cache.json`: the cached `copilot_internal/user` response for each
  account.
  - Keys: `copilot_plan` (`individual`), `access_type_sku` (`free_limited_copilot`),
    `token_based_billing` (true), `can_upgrade_plan`, `endpoints.api`
    (`api.individual.githubcopilot.com`), and `quota_snapshots`.
  - `quota_snapshots` holds `chat` (entitlement 200), `completions` (2000) and
    `premium_interactions` (entitlement 0). Each one has `remaining`, `percent_remaining`,
    `unlimited`, `overage_permitted` and `quota_reset_at`.
  - **This cache tells you the plan, but it has no model list.**
- `~/.copilot/session-state/<id>/events.jsonl`: each session has a
  `session.auto_mode_resolved` event with `data.availableModels`. Both recorded sessions show
  `['mai-code-1.1-flash']`. **This is the only local trace of what the account can really use, and
  it only exists after a real (prompt-consuming) session.**
- `~/.copilot/logs/process-*.log`: on rejection the CLI logs
  `[model_bindings::api_resolver] Model 'X' from CLI argument is not available. Falling back to
  next option.` The logs also contain the GitHub login, so do not copy them anywhere.

### CLI surfaces

- `copilot --help`, `copilot help config` and `copilot help commands`: there is still no
  list-models command.
  - `/model` (interactive only) is the picker.
  - `help config` lists the `model` enum: 31 ids, all models the CLI knows about, not filtered by
    entitlement.
  - Auth comes from `COPILOT_GITHUB_TOKEN`, then `GH_TOKEN`, then `GITHUB_TOKEN`, then the stored
    login.
- `copilot --acp` (Agent Client Protocol server; script `11-acp-models.py` / `11-acp-drain.py`):
  - `initialize` plus `session/new` work with no prompt.
  - The response has `configOptions` for `mode` and `allow_all` only. There is **no `models`
    field and no model config option**, and none arrived within 25 seconds.
  - So ACP does not expose the picker list in 1.0.105.
- `gh copilot` only runs the same `copilot` binary.

### The machine-readable per-account list (models API)

- Script `11-copilot-models-api.py`. It sends `GET https://api.individual.githubcopilot.com/models`
  with the `gh auth token` (a `gho_` token kept in memory only). It returned HTTP 200.
  - With `Copilot-Integration-Id: copilot-developer-cli`: 42 models.
  - With `vscode-chat` plus `X-GitHub-Api-Version: 2025-05-01`: 48 models, plus a `billing`
    object (`is_premium`, `multiplier`, `restricted_to`).
  - Per-model fields: `id`, `name`, `vendor`, `version`, `capabilities.type` (chat/embeddings),
    `model_picker_category` (lightweight/versatile/powerful), `model_picker_enabled`,
    `policy.state`, `preview`, `supported_endpoints` and `warning_text`.
- **Result for this Free account:**
  - **`policy.state = enabled`:** gpt-5.6-luna, gpt-6-luna, mai-code-1.1-flash, claude-haiku-4.5,
    gpt-4.1 and gpt-4.1-2025-04-14. The vscode-chat view adds kimi-k3-base, kimi-k3-copilot and
    three mai-code-1-flash variants.
  - **`disabled`:** all the Opus, Sonnet and Fable models, gemini-4-argon, gemini-3.8-flash,
    gpt-6.1-sol, gpt-6-sol and similar.
  - `model_picker_enabled` is false for every model.
  - grok-4.5/4.6/4.7 appear in the CLI enum but not in this API response.
  - A hidden `gpt-5.6-luna-free-auto` entry exists. Its name suggests it is what Free Auto uses,
    but that is an inference.
- **Status: reverse-engineered and undocumented.** This is the endpoint that editors and opencode's
  `github-copilot` provider use. It is not in GitHub's public docs, and the header requirements
  were found by trial.

### Probes (two allowed, two used; script `11-copilot-probe.sh`, run in an empty temp dir)

| Probe | Output | Exit | Time |
|---|---|---|---|
| `copilot -p "reply ok" --model claude-opus-5.5` (API: disabled) | `Error: Model "claude-opus-5.5" from --model flag is not available.` | 1 | 4.1 s |
| `copilot -p "reply ok" --model gpt-6-luna` (API: **enabled**) | `Error: Model "gpt-6-luna" from --model flag is not available.` | 1 | 4.1 s |

- Neither probe reached a model, so no chat quota was used.
- **The second probe is the key finding: on Free, `policy.state = enabled` does not predict that
  the CLI will accept a model.** That matches the docs ("Auto only").
- Not run because of the probe limit: `--model mai-code-1.1-flash` and `--model auto`. The next
  check would confirm whether Free accepts any named id at all, or only `auto`.

## 2. Cursor

- **Official list:** https://cursor.com/docs/models (also `/llms.txt`).
  - **Cursor models** in the weekly pool: Grok 4.7/4.6/4.5 (Fast and 500k variants) and
    Composer 2.5.
  - **Third-party models:** Anthropic, OpenAI, Google, DeepSeek, GLM, Kimi and Muse, marked
    "Premium and above, at API list price from prepaid credit; not on Plus or Free".
  - Flags: many are "Hidden by default", and several say "Requires Max Mode on legacy
    request-based plans".
  - No models API is documented.
- **Per plan:** https://cursor.com/pricing.
  - **Free:** "Limited agent requests", "Limited Chat requests", no third-party models.
  - **Plus ($8):** "Only Grok models are available on this plan".
  - **Premium ($30):** latest Grok models plus third-party models at API list price.
  - **Super ($100)** and **Ultra ($200):** priority and earliest access.
  - **Legacy Pro, Pro+, Ultra and Start:** keep working as they are, with two monthly pools.
  - **Neither page says Free is "Auto only".** The owner's suspicion is plausible but not
    documented.
- **This machine:**
  - `cursor-agent` is version 2026.10.22-27dcf5f.
  - `cursor-agent models` and `--list-models` both fail with
    `Error: Authentication required. Run 'agent login' ...` and exit 1.
  - `cursor-agent about` shows `Model Auto`, `Subscription Tier Unknown` and
    `User Email Not logged in`.
  - **So the model count, the ids and the free-tier status could not be checked.**
    `~/.config/cursor/auth.json` exists but was not read.
  - Indirect hints:
    - `~/.cursor/cli-config.json` has `modelParameters` for 12 ids (gpt-5.2, glm-5.2,
      gpt-5.6-luna/sol/terra, composer-2.5, claude-sonnet-5-5, claude-opus-5-5, grok-4.7,
      gemini-3.1-pro, kimi-k3, default) and a 12-entry `modelSelectionHistory`. The current
      model is `default`, displayed as `auto`.
    - That suggests named models were picked at some point. It does not show they ran.
    - The old ai-kit catalog cache holds 143 `cursor-agent` entries (from note 7).
- **No probe was run.** With no login, a non-auto request can only return the auth error.
- **What a non-auto request returns on Free:** not in the docs. ai-kit's catalogue carries two
  unverified rows from earlier research: `Free plans can only use Auto` and
  `ActionRequiredError: Named models unavailable`, both classed `billing`.

## 3. How the other runtimes signal "listed but not usable" (from `.planning/scripts/cross-ai.mjs`)

| Runtime / route | Text matched | Class | Label |
|---|---|---|---|
| any (wildcard) | `model not found`, `unknown model`, `invalid model`, `cannot use this model` | bad_model | (generic) |
| opencode | `Model access is disabled` (provider.auth 403) | billing | unverified |
| opencode / pi via router (OmniRoute) | `model_not_in_catalog`; `no_executable_targets` / `Combo has no executable targets` (`code: model_not_found`) | bad_model | verified 2026-10-25 |
| pi via router | `Model X is unavailable` (503) | transient | verified 2026-10-24 |
| cursor | `Named models unavailable`, `Free plans can only use Auto` | billing | unverified |
| codex | `Model metadata for x not found` as an item error | not classed (counted as a crash) | fixture |
| copilot | none; the runner table says `errorsUnverified: true` | — | — |

- **Gap:** copilot's real text, `Model "X" from --model flag is not available.`, matches **none** of
  the patterns (checked with node against all six model regexes). Today it would fall through as an
  unclassified failure. Suggested new row: `from --model flag is not available` → class
  `bad_model` (or `billing` when the plan is Free), label verified 2026-11-02.
- Note that the router's "model X **is unavailable**" (transient) and copilot's "**is not
  available**" (permanent for this plan) need different classes.

## 4. Proposal: discovery per runtime (a proposal, not decided)

Every runtime entry should carry two separate fields: `listed` (where the id came from) and
`usable` (`verified` with a date, `rejected` with the error text, or `unverified`). Show
`unverified` visibly, never as usable.

### Copilot
- **List source:** first the models API (`policy.state`, category and vendor). It needs a token,
  which the CLI's own env order already gives (`COPILOT_GITHUB_TOKEN`, `GH_TOKEN`, then
  `gh auth token`). It is undocumented, so flag it. If that fails, fall back to the
  `copilot help config` enum (no entitlement).
- **Plan gate:** read `access_type_sku` and `copilot_plan` from
  `~/.cache/copilot/copilot-user-cache.json`. When it is a free or student SKU:
  - mark every named model "listed, not usable";
  - mark `auto` as the only usable entry;
  - record the last `session.auto_mode_resolved.availableModels` as "Auto resolves to".
- **Availability probe:** `copilot -p "reply ok" --model <id>` in an empty temp dir. A rejection
  fails before inference, costing nothing in about 4 seconds. An acceptance costs one real chat
  request, so stop the run at the first output and treat that as "usable".
  - Rate: at most one probe per id per cache period, run in sequence, only for ids a lane actually
    configures. Never sweep the full list.
- **Cache:** 1 day for the plan and the probe results. Re-check sooner when the cached
  `retrievedAt` changes or `quota_reset_date` passes.
- **Interactive `/model` via herdr** (herdr 0.9.3 is installed, `HERDR_ENV=1`):
  - Do it only if the probe approach turns out unreliable on paid plans.
  - It costs nothing per model. But it depends on a screen-scraped TUI, so it breaks on UI
    changes, and it needs a live pane.
  - Not tried here.

### Cursor
- **List source:** `cursor-agent models` (official CLI, per account) when logged in.
  - Online catalog: cursor.com/docs/models, through `/llms.txt`, for the plan rules ("not on Plus
    or Free", "Max Mode").
  - No models API is documented.
- **Plan gate:** `cursor-agent about` gives `Subscription Tier`. On Free:
  - mark third-party ids "listed, not usable" (documented);
  - mark Cursor-own models "listed, not verified";
  - mark `auto` usable.
  - When not logged in, report "not logged in" rather than an empty list.
- **Availability probe:** `cursor-agent -p "reply ok" --model <id>` once per configured id.
  - Classify the error text through the existing rows (`Free plans can only use Auto` and
    `Named models unavailable`). The first real capture turns those rows into verified ones.
  - Cost is unknown (it may use one limited request). Probe only configured ids.
- **Cache:** 1 day.

### opencode, pi, codex, claude
- **Lists:**
  - opencode: `opencode models`.
  - pi: RPC `get_available_models`.
  - codex: as today.
  - claude: aliases plus the catalog.
- These are not free-tier-gated in the same way. Paid keys and routers fail per request.
- **Usable** comes from the existing error classes: a `bad_model` result marks the
  (runtime, model) pair "rejected" until the next refresh. `billing` marks it "blocked by plan".
  A transient error marks nothing.
- No proactive probe is needed. Record the outcome of real runs, which `cross-ai.mjs` already
  classifies.

### Shared
- **Per-source cache times:** catalog sources 7 days, CLI listings 1 day, usability verdicts
  1 day or until the plan changes.
- **The marking should be a visible state**, not a hidden filter, for example
  `listed (help-enum) · not verified` versus `usable (probe 2026-11-02)`. This follows the rule
  against showing more certainty than the sourcing allows.

## Sources

- https://docs.github.com/en/copilot/reference/ai-models/supported-models
- https://docs.github.com/en/copilot/get-started/plans
- https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing
- https://github.blog/changelog/2026-04-17-github-copilot-cli-now-supports-copilot-auto-model-selection
- https://roboin.io/article/en/2026/06/25/github-copilot-free-and-student-plans-limited-to-auto-model-selection/ (secondary)
- https://cursor.com/docs/models
- https://cursor.com/pricing

Not checked: the legacy multiplier page for annual plans; Cursor live (not logged in); whether
Copilot Free accepts `--model mai-code-1.1-flash` or `--model auto` (the probe limit was reached);
paid-plan behaviour of the Copilot `policy.state` field.
