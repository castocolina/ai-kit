# review-spec Cross-AI Reviewer Design Spec

- **Status**: design ready
- **Date**: 2026-08-27
- **Scope**: `skills/review-spec/`, `skills/reviewing-specs/` (renamed),
  `skills/applying-review-feedback/` (renamed), new `skills/review-spec-config/`,
  new `skills/review-spec/review-spec.py` (one stdlib-only module, file
  layout/testing style matching this repo's established
  `tools/status-line.py`/`tools/setup.py` single-flat-file convention —
  but placed **inside `review-spec`'s own skill directory**, not a
  top-level `tools/`, because that's the only placement reachable from an
  installed skill: `tools/setup.py` symlinks only `agents`/`commands`/
  `skills` into `~/.claude`, never a top-level `tools/`), new
  `skills/review-spec/references/cli-profiles/` (same reasoning — inside
  the skill directory, not a new top-level `references/`). Both resolve
  via the exact same three-candidate pattern (`CLAUDE_PLUGIN_ROOT`/
  `~/.claude/skills`/sibling-of-this-file) `review-spec/SKILL.md` already
  uses for its own `SEEDS_DIR` (§8), so `review-spec-config` — a sibling
  skill — reaches them the same way.
- **Relates to**: builds on the existing `review-spec` orchestrator
  (Step 0–0.6, the review↔fix loop) without changing its framework-detection
  or fixer-routing behavior — this spec only changes **who performs the
  review** and **how that choice is configured/cached**.

---

## 1. Intent

`review-spec`'s reviewer is hardcoded today: always a Claude `sonnet`
subagent running the `reviewing-specs` skill. Two problems:

1. **No tier awareness within Claude itself.** It should prefer the
   strongest available Claude tier (flagship, e.g. Opus) and fall back to a
   cheaper tier only under budget/quota pressure — never a fixed model name.
2. **No cross-vendor option.** A spec/plan authored by one vendor's model
   benefits from an independent, differently-biased reviewer — ideally a
   *different* vendor's flagship, when one is actually reachable and has
   quota to finish the job.

**Goal**: make the reviewer selection **config-driven and quota-aware**.
`policy.mode` (§3) is the two-value knob that actually ships:
`"single"` (one reviewer, preferring a vendor different from the
document's own author, tier-aware, quota-aware) and `"double"` (a
guaranteed native baseline reviewer *plus* one cross-vendor alternate,
findings unioned and tagged by source). A third case —
**today's exact behavior, unchanged: single reviewer, always same vendor,
no ladder walk at all** — is reached via `--no-cross-ai`, not a third
`policy.mode` value (§3); it is the "minimize effort" escape hatch from
the original ask, not a tier a config author picks. Selection must degrade
gracefully — never block a review because cross-AI isn't configured or a
candidate is out of quota — and must never guess specific model IDs, since
availability shifts by subscription and by day.

**Out of scope**: the *fixer* stays Claude-only always (this spec only
changes who reviews, not who edits files in place — an external CLI editing
the working tree as a separate process is a different, riskier problem not
asked for here). Live-verifying every CLI's exact quota-probe/fast-tier
syntax is also out of scope for this doc — `codex` is empirically confirmed
(§5), `claude`/`opencode`/`grok` have confirmed non-interactive/model flags
but unconfirmed quota-introspection syntax, and `cursor-agent` is
web-research-only (not installed on the reference machine). Those specifics
are implementation-phase (plan-writing) research, tracked as an explicit
task per profile, not fabricated here.

---

## 2. Skill renaming

Confusable names (`review-spec` vs `reviewing-specs`) get a shared,
hierarchical prefix. `review-spec` itself is **unchanged** — it's the
public entrypoint (`/review-spec`) and nothing should break users' muscle
memory:

| Today | Renamed to |
|---|---|
| `skills/review-spec/` | *(unchanged)* |
| `skills/reviewing-specs/` | `skills/review-spec-checklist/` |
| `skills/applying-review-feedback/` | `skills/review-spec-fixer/` |
| *(new)* | `skills/review-spec-config/` |

Mechanically: `git mv` each directory, update each moved skill's own
frontmatter `name:` field, update every cross-reference inside
`review-spec/SKILL.md` (reviewer/fixer prompt templates currently say
`Invoke the Skill tool with skill name "reviewing-specs"` /
`"applying-review-feedback"`, and `SEEDS_DIR` fallback paths reference
`reviewing-specs/references/frameworks/`), and re-grep the repo for any
other reference to the old names (docs, other skills, READMEs). This is a
plan-phase task list, not enumerated exhaustively here.

---

## 3. Config: `review-spec.toml`

**Format**: TOML, matching the repo's existing convention
(`tools/status-line.py`'s `statusline.toml` — `tomllib` is stdlib, already
used; this repo has zero external dependencies and stays that way. YAML was
considered and rejected — it would add `PyYAML` as a new dependency for a
project that has none today.)

**Locations, resolved in this order:**

1. `./.aikit/review-spec.toml` (project-local, if present)
2. `${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/review-spec.toml` (global,
   matching `statusline.toml`'s own resolution — including the
   `CC_AI_KIT_CONFIG_FILE`-style override precedent, applied analogously if
   ever needed)

**Local/global relationship** — declared *by the local file itself* via a
top-level `strategy` key, not hardcoded by the skill:

```toml
# ./.aikit/review-spec.toml
strategy = "global-merge"   # "local-only" | "global-merge" (default if omitted: "global-merge")
```

- `local-only`: the global file is ignored entirely; the local file must be
  self-sufficient (a missing `[policy]` falls back to built-in defaults —
  §6 — not to the global file).
- `global-merge` (default): `[policy]` shallow-merges (local keys override
  global keys per-field; unspecified fields inherit from global).
  `[[reviewers]]` merges by `key` (a local entry with the same `key`
  overrides/extends that entry's fields — e.g. only `effort` — inheriting
  every other field from the global entry of the same `key`; a local `key`
  not present globally is simply added; a global `key` not mentioned
  locally is inherited unchanged).

**Schema:**

```toml
[policy]
mode = "double"                                    # "single" | "double"
ladder = ["codex-gpt", "grok-flagship", "claude-opus"]  # ordered candidates

[[reviewers]]
key = "claude-opus"
model = "opus"                                     # runtime-native dispatch (no `cli`) — one of the Agent tool's 4 model aliases, never a full model id
vendor = "anthropic"

[[reviewers]]
key = "codex-gpt"
cli = "codex"
model = "gpt-5.2"
vendor = "openai"
command = "codex exec --sandbox read-only --skip-git-repo-check -m {model} -c model_reasoning_effort='\"{effort}\"' {prompt}"
effort = "high"

[[reviewers]]
key = "grok-flagship"
cli = "grok"
model = "grok-4.6"
vendor = "xai"
command = "grok -m {model} --output-format json -p {prompt}"

[[reviewers]]
key = "opencode-kimi"
cli = "opencode"
model = "opencode-go/kimi-k3"
vendor = "moonshot"                                # explicit — opencode itself isn't a vendor
command = "opencode run -m {model} {prompt}"
```

**Field semantics:**

- `key` (required, unique): stable identifier referenced by `policy.ladder`
  and by finding-provenance tags (§8).
- `model` (required): the model identifier the dispatch mechanism will use.
  **Never assumed/hardcoded by review-spec** — always either detected via
  the CLI's own model-listing command (`opencode models`, etc. — §5) and
  confirmed by the user in `review-spec-config`, or typed by the user
  directly. **Exception for native (`cli`-less) entries**: Claude Code's
  `Agent` tool only accepts one of four model aliases —
  `sonnet`/`opus`/`haiku`/`fable` — never a full model id like `"opus-5"`;
  `review-spec-config` writes exactly one of those four for any native
  entry, and a hand-written config with anything else there is a config
  error (§8 surfaces it at dispatch rather than passing it through).
- `vendor` (required): the model's actual maker (`anthropic`, `openai`,
  `xai`, `moonshot`, `alibaba`, `google`, …) — **independent of `cli`**,
  since a single CLI can host multiple vendors (confirmed: `opencode`
  routes to Anthropic/OpenAI/xAI/Moonshot/Alibaba models alike under its
  own namespace). This is the field the `policy.ladder` same-vendor skip
  (§3, mode semantics) actually reads; it is never inferred from `cli`.
  `review-spec-config` fills it in when writing entries from detected
  model lists (it knows, e.g., that `opencode-go/kimi-k3` is Moonshot);
  hand-written entries must set it explicitly.
- `cli` (optional): the name of an **external runtime's** CLI profile
  (§5) to shell out to as a separate process. **Absent `cli` means dispatch
  natively through the CURRENT session's own subagent mechanism** — this is
  a statement about *dispatch mechanism* (no new process), not about
  vendor: the current runtime can itself be multi-provider (confirmed live
  — `opencode models` lists `opencode-go/kimi-k3`, `opencode-go/grok-4.6`,
  `opencode-go/qwen3.8-max` etc. under its own routing, and a Claude Code
  session pointed at an Anthropic-compatible third-party endpoint could
  equally expose non-Anthropic models under `model`). Whether a given
  `model` string is actually valid is resolved by the current runtime, not
  by review-spec.
- `command` (required iff `cli` present): a shell template with
  placeholders. Only `{model}` and `{prompt}` are universal/guaranteed —
  every other field on the reviewer entry (`effort`, or any CLI-specific
  knob) is interpolated **only if referenced in `command`**, and CLIs are
  free to need more than one such knob (confirmed: `codex` separates
  reasoning effort (`model_reasoning_effort`) from service speed tier
  (`service_tier`) as two independent `-c key='"value"'` flags — no single
  universal `{effort}` covers both, so a reviewer entry targeting codex's
  fast tier would add its own extra field, e.g. `service_tier = "fast"`,
  and reference `{service_tier}` in `command`). **Write `{prompt}` bare,
  never wrapped in the template's own quotes** (no `"{prompt}"`/
  `'{prompt}'`) — the dispatch mechanism (§8) always shell-escapes the
  prompt text itself (`shlex.quote`) before substitution, since it's free
  text built from document paths/content that must survive as exactly one
  shell argument; `{model}` and every extra field stay unescaped, since a
  CLI's own quoting idiom around them (`codex`'s `-c key='"{effort}"'`
  above is the example) is the template author's responsibility and
  auto-quoting would break it.
- `effort` / any other extra key (optional): CLI-specific tuning, free-form,
  only meaningful if `command` references it as a placeholder.

`policy.mode`:

- `"single"`: exactly one reviewer runs. Walk `policy.ladder` in order,
  skip any candidate whose vendor matches the source model's vendor (§4)
  *unless* skipping it would exhaust the ladder, skip any candidate without
  quota (per `quota.json`, §7), and use the first that survives both
  filters. If the ladder is exhausted, fall back to the current session's
  own native reviewer (never zero reviewers).
- `"double"`: a **native** reviewer runs unconditionally as the guaranteed
  baseline — walk `policy.ladder` restricted to its `cli`-less entries only
  (tier-aware: the best-quota-having native entry wins, e.g. `claude-opus`
  before `claude-sonnet` when both are configured and Opus has quota),
  falling back to the current session's own default model (no config, or
  no native entry has quota — never zero reviewers) — **plus** the best
  entry anywhere in the full `policy.ladder` whose vendor differs from the
  baseline's, quota-aware, dropped (not substituted) if none survives. The
  baseline is always native/current-runtime; only the second slot may be
  external.

`--no-cross-ai` (on `/review-spec`) forces single-mode, current-session-only,
and **skips the ladder walk and quota probe entirely** (the "minimize
effort" case from the original ask — zero detection overhead when the user
already knows there's no cross-AI quota available). `--cross-ai` (default)
uses whatever `policy.mode` says.

---

## 4. Source-vendor detection

Default: the document's authoring vendor is assumed to be **the current
session's own vendor** (the common case — `brainstorming`/`writing-plans`
ran earlier in the same session that now invokes `/review-spec`). The
orchestrator has no runtime introspection API for its own model's real
vendor, so this default is instantiated as the literal `anthropic` (a
native Claude Code session is overwhelmingly the common case) rather than
detected dynamically. Override
via `--source-vendor=<vendor>` for the case where the spec was authored
elsewhere (a different session, a teammate, another tool) and the current
session isn't the author. The flag takes a vendor directly (e.g. `openai`,
`anthropic`) rather than a model id — deriving a vendor from an arbitrary
model id string has no sanctioned mapping and would mean guessing, which
this spec's own §1 rules out.

Rejected: scanning the document's frontmatter or git commit trailers for
authorship — this repo's commits don't carry such trailers today (verified:
`git log` shows none), so that path would almost always fall through to the
same session-based default anyway, adding complexity without a real payoff
right now.

---

## 5. CLI profiles (`skills/review-spec/references/cli-profiles/`)

One file per runtime, holding: how to detect the binary + version, how to
list its available models, its non-interactive invocation flags, and
(where known) how to probe quota/context cheaply. **v1 covers what's
actually installed and verifiable on the reference machine**; others are
documented stubs (same shape, unverified) to fill in later without any
architecture change.

| CLI | Status | Confirmed (this session) |
|---|---|---|
| `claude` | full profile | `-p/--print` (non-interactive), `--model <model>`, `--output-format` |
| `codex` | full profile | `codex exec -m <model> -c model_reasoning_effort='"<level>"' -c service_tier='"<tier>"' "<prompt>"`; a low-effort/fast-tier call against exhausted quota returns a detectable usage-limit error — **this is the quota-probe mechanism**, confirmed live by the user against their own account |
| `opencode` | full profile | `-m/--model <provider/model>`, `opencode models` (lists everything routed, including third-party models under `opencode-go/*`, `ollama-cloud/*` — confirmed live: `kimi-k3`, `qwen3.8-max`, `grok-4.6`, `gpt-5.6-luna` all reachable natively) |
| `grok` | full profile | `-m/--model`, `--output-format`, `--json-schema` for structured output |
| `cursor-agent` | stub (web research only, not installed here) | `-p/--print`, `--output-format json\|text`, `--model <name>`, `cursor-agent status` (auth/version; quota shape unconfirmed) |
| `gemini` | stub (carried over from the existing `gemini` skill's documented flags) | — |

Exact quota/context-window probe syntax for `claude`, `opencode`, `grok`,
and `cursor-agent` is an explicit **research task per profile** during the
implementation plan — do not fabricate flags beyond what's listed above.

---

## 6. Cache: detection + quota (`~/.cache/ai-kit/review-spec/`)

JSON, matching the repo's existing cache convention (`cfg_cache_base` →
`${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit`; the *existing* `review-spec`
skill's framework-profile cache under `~/.claude/cache/framework-profiles/`
already breaks this convention — a pre-existing inconsistency, noted but
not in scope to fix here).

Two files, deliberately separate because their staleness windows differ by
orders of magnitude:

- **`runtimes.json`** — which CLIs are installed, their versions, and their
  listed models. Near-static (changes only on install/uninstall). TTL ~30
  days, or refreshed on demand via `review-spec-config`.
- **`quota.json`** — per reviewer `key`: a boolean `available` from the
  last probe (a trivial prompt run through the reviewer's own `command`,
  classified by exit code / a usage-limit-shaped error signal — no
  CLI-specific quota subcommand required), plus `checked_at`. TTL ~1 hour,
  refreshed automatically (no user interaction) whenever stale at dispatch
  time, and never re-probed more than once per TTL window regardless of
  how many `/review-spec` invocations happen inside it. **Does not**
  capture remaining context-window headroom — no CLI profile (§5) has a
  confirmed mechanism for that today; §10's context-window edge case is
  aspirational until one is found, not implemented by v1.

**Missing `runtimes.json` at `/review-spec` invocation time**: this is the
first invocation ever (before `review-spec-config` has run, or before any
prior `/review-spec` run reached this step). Detect live via the same
`detect-runtimes --save <path>` call `review-spec-config` itself uses (§7)
— this both produces the snapshot for informational use *and* persists it
in the same step, so the hint below fires once, not on every invocation.
Print one line ("No cross-AI config saved yet — run `review-spec-config`
so this doesn't repeat every invocation") and proceed with reviewer
resolution as normal — resolving against whatever `review-spec.toml` state
actually exists (typically none yet, which degrades gracefully to the
current-session-only fallback, §3). No separate "declined" stub is needed:
once `runtimes.json` exists — whether written here or by an explicit
`review-spec-config` run — Step 0.7 stops live-detecting and hinting
regardless of whether the user ever configured any `[[reviewers]]`
entries; an explicit `review-spec-config` run is what reopens that
decision (it always re-detects and re-saves).

---

## 7. `review-spec-config` skill (new)

Interactive setup, modeled on `gsd-config`/`gsd-settings`: runs
`review-spec.py detect-runtimes` (resolved to an absolute path per §8's
resolution mechanism — this module lives inside the `review-spec` skill's
own directory, a sibling of this skill, not inside this skill's own
installed directory), shows what it found (installed CLIs, their listed
models), and asks the user (via `AskUserQuestion`) to name/rank
`[[reviewers]]` entries and set `[policy]` — writing the result to
`review-spec.toml` (global by default; `--local` writes
`./.aikit/review-spec.toml` instead). Also exposes a `--check-only` mode
(no writes) that reports current cross-AI availability — this is the
"standalone availability check" the original ask wanted as a separate
script, implemented here as a flag rather than a fifth skill to avoid
skill sprawl (`review-spec.py detect-runtimes` remains independently
callable too, for anyone who wants the raw command instead of the
interactive wrapper).

---

## 8. Orchestrator integration (`review-spec/SKILL.md`)

- **Step 0.7 (new)**, runs once per invocation, after Step 0.6:
  0. Resolve `TOOLS_PY` and `CLI_PROFILES_DIR`. `review-spec.py` and its
     `references/cli-profiles/` live inside this skill's **own**
     directory (§3), so they resolve with the exact same three-candidate
     pattern already used for `SEEDS_DIR` just above in this same skill
     (`${CLAUDE_PLUGIN_ROOT}/skills/review-spec/…`, then
     `~/.claude/skills/review-spec/…`, then the directory containing this
     `SKILL.md` itself) — no separate "resolve a skill directory, then
     derive a repo root" step, and no dependency on any `SKILL_DIR`
     variable (this skill never defines one; `SEEDS_DIR` itself is
     resolved from three full candidate paths directly, not derived from
     an intermediate name). Record both as literal absolute paths, exactly
     like `RUN_TMP_DIR` below — they are not shell variables that survive
     across separate `Bash` tool calls. Missing `TOOLS_PY`
     at this resolved path degrades exactly like `--no-cross-ai`.
  1. Run `mktemp -d`, capture its stdout, and record that absolute path as
     `RUN_TMP_DIR` **in the skill's own working notes/context** — not as a
     shell environment variable. Each `Bash` tool call in this harness runs
     in its own fresh shell, so a variable assigned in one call does not
     exist in the next; `RUN_TMP_DIR` must be substituted as a literal
     absolute path into every later command and prose reference for the
     rest of this run, exactly the way `CODEBASE_ROOT`/`SEEDS_DIR`/
     `CACHE_DIR` are already resolved once and substituted literally
     elsewhere in this skill. See §9.
  2. Resolve source vendor (§4).
  3. Load config (§3) and cache (§6); refresh `quota.json` entries that are
     stale for any ladder candidate actually needed this run.
  4. Resolve the effective reviewer list (1 or 2 entries) per `policy.mode`
     (§3) and `--cross-ai`/`--no-cross-ai`.
- **Step 1**, per resolved reviewer: `cli` absent → dispatch as today (the
  `Agent` tool, now running `review-spec-checklist` instead of
  `reviewing-specs`); `cli` present → `Bash`, running the reviewer's
  `command` (placeholders filled), with the prompt telling that CLI to
  **read `review-spec-checklist`'s `SKILL.md` from disk and follow it**
  (external CLIs can't call our `Skill` tool, but they can read a file path
  — this preserves single-sourcing the checklist instead of duplicating its
  content into every CLI's prompt). Output captured to
  `$RUN_TMP_DIR/iter<N>-<key>.md`.
- **Step 1.5 (new, only when 2 reviewers ran)**: merge the two reports —
  union of findings, deduplicated by (severity, exact `Location` string)
  ACROSS the two reports only — the reviewer output template's `###
  <SEVERITY>` heading plus its bullet's `Location:` field are the only
  structured fields the template actually guarantees; `file`/`line`/
  `category` aren't reliably parseable from free-text findings, so dedup
  keys off what's really there. Two DIFFERENT findings from the SAME
  report that happen to share a (severity, location) — e.g. two distinct
  HIGH issues both in "§3" — are never collapsed into each other; only
  the first such finding per report claims that dedup key, so this rule
  only ever merges a genuine cross-reviewer duplicate, never two of one
  reviewer's own distinct findings. Each finding is tagged with which
  reviewer `key`(s) surfaced it. No severity arbitration by the
  orchestrator (option **(c)** from the design discussion). Merged report
  becomes the input to Step 2/3, unchanged otherwise.
- **Fixer (Step 3a/3b)**: unchanged, always Claude-native, always
  `review-spec-fixer` (renamed).
- **Cleanup**: `rm -rf "$RUN_TMP_DIR"` once, replacing today's ad hoc
  `/tmp/review-spec-*` file-by-file cleanup.

---

## 9. Temp-file collision fix

**Pre-existing bug, fixed as part of this work** (not newly introduced by
cross-AI, but directly aggravated by it — double-review produces more files
per iteration): today's `Step 3` literally uses
`/tmp/review-spec-report-iter<N>.md` — no project, worktree, or process
identifier. Two concurrent `/review-spec` runs (two different projects, or
two worktrees of the same repo) on the same machine collide on that exact
path. Fixed by resolving one `RUN_TMP_DIR` via `mktemp -d` at the very start
of the loop (§8, Step 0.7) — captured as a literal absolute path substituted
into every later reference, not a shell variable (Bash tool calls run in
independent fresh shells with no shared state) — and writing every artifact
for that run — every reviewer's raw report, the Step 1.5 merge, the fixer's
report — under that one guaranteed-unique directory.

---

## 10. Edge cases

- **No CLIs installed besides the current runtime**: `policy.ladder`
  resolves to nothing usable; `single` mode falls back to the current
  session's own reviewer, `double` mode effectively behaves like `single`
  (only the guaranteed baseline runs) — no error, no blocked review.
- **A ladder candidate has quota but its context window can't fit the
  document(s)**: **not implemented by v1** — `quota.json` only tracks a
  boolean `available` (§6), not context-window headroom, since no CLI
  profile (§5) has a confirmed introspection mechanism for it yet. Once one
  is found for a given CLI, it would be treated identically to "no quota"
  for filtering purposes (skip and try the next candidate); until then this
  case simply isn't detected — an oversized document sent to a
  small-context reviewer fails the same way it would today.
- **`--source-vendor` given but doesn't match any configured reviewer's
  vendor**: treat as unknown vendor — `single`/`double` ladder walks still
  work (nothing to "skip as same-vendor"), just without that one
  optimization.
- **Both local and global config missing entirely, and `runtimes.json`
  doesn't exist yet**: live one-shot detection + persist (§6), never
  blocks the review — resolution still proceeds and degrades to the
  current-session-only fallback since there's no `[[reviewers]]` config.
- **`strategy = "local-only"` but the local file omits `[policy]`
  entirely**: falls back to review-spec's built-in default policy
  (`mode = "single"`, empty ladder → always current-session), never to the
  global file (that would silently contradict `local-only`).
- **An external reviewer's `Bash` dispatch errors, times out, or produces
  a non-conforming report** (no parseable `### Status:` line): in
  `single` mode this is indistinguishable from any other missing-Status
  failure — the existing orchestrator rule already applies ("No Status
  line → Surface failure", unchanged by this spec). In `double` mode, the
  merge step (§8) checks every report for a `### Status:` line *before*
  merging and, if any is missing, emits no `### Status:` line of its own
  rather than fabricating an `Approved`/`Issues Found` verdict from an
  incomplete pair — the same existing "No Status line" rule then catches
  it at the orchestrator level. A failed external reviewer never silently
  degrades to "the surviving reviewer's verdict alone"; it surfaces as a
  failure of the whole iteration, same as a single-reviewer failure would
  today.

---

## 11. Testing

Given this touches orchestration prose (SKILL.md files) and shell/Python
detection scripts rather than a single testable module, testing splits by
artifact:

- **`review-spec.py`'s runtime/CLI detection**: unit-testable — mock
  `PATH`/binary presence (`which_fn`) and process execution (`run_fn`),
  assert correct `runtimes.json` shape; assert `opencode models` output
  parses into the expected provider/model list shape (a fixture built
  from the model ids confirmed live in §5's table —
  `opencode-go/kimi-k3`, `opencode-go/qwen3.8-max`, etc.).
- **Config loading (TOML parse + local/global merge + `strategy`
  resolution)**: unit-testable in isolation — `local-only` ignores global
  entirely; `global-merge` merges `[[reviewers]]` by `key` and shallow-merges
  `[policy]`; missing `strategy` defaults to `global-merge`.
- **Policy resolution (`single`/`double` ladder walk, vendor-skip,
  quota-skip, fallback-to-current-session)**: unit-testable as pure
  functions over a fixture `policy` + fixture `quota.json`.
- **Quota probing (`render_reviewer_command`, `probe_reviewer_quota`,
  `refresh_quota_cache`)**: unit-testable — a fake `run_fn` simulates
  success/nonzero-exit/usage-limit-text/timeout outcomes; the command
  renderer is tested separately for correct `{model}`/`{prompt}`/extra
  substitution and for `{prompt}` shell-escaping.
- **Findings merge (`parse_findings`, `report_has_status`,
  `merge_findings`, `render_merged_report`)**: unit-testable over fixture
  report strings — severity/location extraction, the
  `Cross-Document Consistency` section, cross-report dedup vs.
  same-report distinctness, and the fail-closed path for a report with no
  `### Status:` line.
- **`review-spec/SKILL.md` orchestration changes**: no automated test
  (prose, not code) — validated the same way the existing skill is
  validated: a manual dry run reviewing a real spec/plan with `--cross-ai`
  and `--no-cross-ai`, and with `policy.mode` set to each of `single`/
  `double`, confirming `RUN_TMP_DIR` is created/cleaned and the merge step
  (§8) only runs when 2 reviewers actually ran.
