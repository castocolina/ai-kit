# ai-kit-spec Family Rename + Cross-AI Execution Wrapper Design Spec

- **Status**: design ready
- **Date**: 2026-08-28
- **Scope**: rename `skills/review-spec*` → `skills/ai-kit-spec-review*`
  (see §2); new `skills/ai-kit-spec-execute/` (router), new
  `skills/ai-kit-spec-execute-gsd/` (adapter), new
  `skills/ai-kit-spec-execute-superpowers/` (adapter); split the existing
  `review-spec.py` (currently ~1133 lines, single flat file) into a
  shared module package under `skills/ai-kit-spec-review/` reused by both
  the review and execute families (see §4); cache namespace migrates from
  `~/.cache/ai-kit/review-spec/` to `~/.cache/ai-kit/spec/` (see §11).
- **Relates to**: builds directly on
  `docs/superpowers/specs/2026-08-27-review-spec-cross-ai-design.md`
  (deterministic CLI/model detection, vendor inference, command
  Strategy/Factory, quota probing, priority ladder — all reused, not
  reinvented). This spec extends that foundation to a new purpose
  (execution, not review) and renames the family it lives under.

---

## 1. Intent

The review-spec family solved cross-AI reviewer dispatch: detect
installed CLIs, infer vendors, build commands per-CLI, probe quota, walk
a priority ladder. That same foundation is needed for a different job —
**executing** an already-written plan/phase, not reviewing a document.
Execution has different constraints (needs write access, needs enough
context for the actual files touched, benefits from exploration tooling)
and different integration points (GSD and superpowers each already own
an execution harness with their own conventions — we extend them, we
don't replace them).

**Goal**: a new `ai-kit-spec-execute` skill family that is *responsible
for choosing the best available model/CLI for a given execution task*
(task-type affinity, context-size fit, user's ranked preferences, live
quota) and *handing that choice to the right harness* — GSD's own
config + `gsd-execute-phase`, or superpowers' `subagent-driven-development`
(see §8's scope correction: `executing-plans` runs every task inline with no
subagent-dispatch point to inject into, so it is not a real target here) —
rather than reimplementing either framework's execution discipline.

## 2. Family rename

| Current | New |
|---|---|
| `review-spec` | `ai-kit-spec-review` |
| `review-spec-checklist` | `ai-kit-spec-review-checklist` |
| `review-spec-fixer` | `ai-kit-spec-review-fixer` |
| `review-spec-config` | `ai-kit-spec-config` (drops "review" — now configures both review and execute) |
| *(new)* | `ai-kit-spec-execute` (router) |
| *(new)* | `ai-kit-spec-execute-gsd` (GSD adapter) |
| *(new)* | `ai-kit-spec-execute-superpowers` (superpowers adapter) |

All internal cross-references (Skill-tool invocations, `SEEDS_DIR`/
`CLI_PROFILES_DIR` resolution, the `CACHE_DIR` framework-profile cache,
Makefile/pre-commit/README entries) move with the rename — same pattern
as the `reviewing-specs` → `review-spec-checklist` rename already done
in the prior spec.

## 3. Architecture

```
ai-kit-spec-execute (router)
  ├─ detects framework (GSD / superpowers / generic — same signal-matching
  │  approach as ai-kit-spec-review Step 0.5)
  ├─ resolves best model/CLI via the shared engine (§5)
  └─ dispatches to the matching adapter
        ├─ ai-kit-spec-execute-gsd          (§7)
        └─ ai-kit-spec-execute-superpowers  (§8)
```

Same shape as the review family: a thin orchestrator + specialized
skills, never one mega-skill. Adding a framework later (Spec Kit,
OpenSpec) means adding one adapter skill, not touching a large shared
file.

## 4. Shared module split

The existing `review-spec.py` (~1133 lines) is split by responsibility
into a package (exact file layout TBD at plan time, but the boundaries
are fixed here):

| Module | Responsibility | Status |
|---|---|---|
| `detection.py` | CLI/model discovery, tool-availability checks (`rg`/`sd`/`bat`/`eza`/`fd`/`codegraph`) | existing `build_runtimes_snapshot`, extended |
| `vendor.py` | deterministic vendor-from-model-name inference | existing `infer_vendor_from_model`, unchanged |
| `commands.py` | Strategy/Factory command building — **two catalogs**, `_REVIEW_COMMAND_BUILDERS` (read-only, existing, unchanged) and `_EXECUTE_COMMAND_BUILDERS` (write-capable, new — §6) | existing builders kept; new ones added |
| `config_io.py` | TOML/JSON local/global merge, `strategy` handling | existing `cfg_resolve`/`cfg_write_toml`, unchanged |
| `quota.py` | live probing, priority-ladder resolution, escalation | existing `resolve_ladder_pick`/`probe_reviewer_quota`, unchanged |
| `execute_selection.py` | task-type affinity, context-size filtering, GSD `model_profile`/`dynamic_routing` mapping | new (§5) |
| `dispatch.py` | generic process dispatcher: stdin prompt delivery, heartbeat with timestamp, resumable-state persistence | new (§6, §9) |

Both `ai-kit-spec-review` and `ai-kit-spec-execute*` skills import from
this one package — no duplicated detection/vendor/quota logic between
the two families.

## 5. Model selection (`execute_selection.py`)

Resolution order per execution task, entirely deterministic (no
per-execution LLM judgment):

1. **Task classification** — infer task type (frontend/backend/mixed)
   and file scope from the plan/phase text, by path/extension signals
   (deterministic, not inferred by a model).
2. **Context-size requirement** — estimate from files/lines the task
   touches.
3. **Candidate resolution** — intersect: task-type affinity (roster
   table, populated by `ai-kit-spec-config`'s WebSearch-informed
   research, same pattern as review's model curation — **never**
   hardcoded permanently) ∩ user's ranked top-N preferences ∩ live quota
   availability ∩ sufficient context for the estimated requirement.
4. **Escalation** — if the top-N ∩ affinity subset exhausts quota within
   the same execution wave, fall through to any other detected-available
   candidate (not limited to the user's top-N) — confirmed behavior,
   simple first-available-wins-fallback-on-failure semantics, matching
   the review family's existing ladder.

**Context-size data**: no CLI exposes cheap live introspection of the
*effective* context window for a specific model+effort+service-tier
combination — verified directly against `claude`, `codex`, and
`cursor-agent`: none has a scriptable command for it (`codex --help`
has no `models`/`info` subcommand at all; `cursor-agent models`'s raw
per-line output is only `id - display name`, no numeric field;
`claude --help`'s `--autocompact <auto|tokens>` range hints the tool
knows its own model's limit internally, but doesn't expose it as
queryable data). Each of these clearly surfaces the number somewhere in
its own interactive UI (Claude's status line, codex's banner in other
modes, cursor's model picker) — the data exists, but as a table each
vendor bundles and updates with their own tool releases, not as a public
API this design can query. Two sources, in order:
- **Structural, when a CLI's own model catalog reports it** (confirmed
  example: `opencode`'s config-defined custom-provider models carry
  `limit.context`/`limit.output`) — parsed directly.
- **Curated, researched at `ai-kit-spec-config` time** — WebSearch
  against the vendor's docs, capturing the *specific parameter
  combination* when the vendor's own docs differentiate it (e.g. a
  model's flagship tier at 1M context vs. the same model's `fast`
  service-tier capped lower) — never assumed constant across all
  parameter combinations for a model family.
- **Reactive learning, not proactive exhaustive probing**: a real
  context-overflow error during actual execution is a real, cheap-to-
  detect signal (same generic error-text-matching mechanism already
  used for quota exhaustion) — record it as a learned constraint for
  next time. Proactively probing every model×effort×service-tier
  combination with a context-sized prompt at config time is not done —
  it costs real tokens/money for combinations that may never be used.

## 6. Dispatch (`dispatch.py`) and execute-mode command builders

**Dispatch decision**: resolved candidate is a Claude tier → native
`Agent`-tool subagent dispatch (in-process, no external process). Resolved
candidate is an external CLI → the generic dispatcher: `subprocess.Popen`,
stdin redirected from the already-persisted prompt file (same pattern as
the review family's stdin-delivery design), stdout to a scratch file,
periodic timestamped heartbeat lines while polling for completion,
timeout enforcement.

**Execute-mode command builders — new, parallel catalog, `purpose:
execute`**: the review family's `_COMMAND_BUILDERS` are deliberately
hardcoded to read-only invocations (`cursor-agent`'s builder *rejects*
any mode but `plan`/`ask`). Execute needs the opposite guarantee —
write-capable, no artificial restriction. Each CLI gets its own
execute-mode builder, verified live before being trusted (§13):
codex (`--sandbox workspace-write -C <target-dir>` or
`danger-full-access`), cursor-agent (`--force`/`--yolo`, dropping
`--mode plan`/`ask`, respecting the one-time workspace-trust flow
confirmed live during design), opencode (`--auto`), grok and claude
(mechanism not yet confirmed — smoke test required, see §13).

## 7. GSD adapter (`ai-kit-spec-execute-gsd`)

GSD (Open GSD / `gsd-core`) already has a real model/runtime config
surface — confirmed live via its own docs (not assumed):
`.planning/config.json`'s `runtime`, `model_profile`, `model_overrides`,
`models` (per phase-type: planning/discuss/research/execution/
verification/completion), and `dynamic_routing` (tier escalation on
*verification failure*, not on quota exhaustion — a real gap this design
fills). Built-in tier maps are hardcoded to 3 runtimes with static model
IDs that will go stale — same staleness problem review's model curation
already solved.

Two integration points, used together:

- **Native Claude tiers**: write `model_overrides`/`model_profile` —
  this part of GSD's config genuinely works today, no limitation.
- **Cross-provider**: GSD's *native runtime enum* (cursor/gemini/claude/…)
  is a closed, unparameterized set — **confirmed disputed** in this
  design's own discussion (docs describe a separate, more general
  `workflow.cross_ai_execution`/`cross_ai_command` hook — an arbitrary
  shell command receiving the phase prompt via stdin, producing
  `SUMMARY.md`-compatible output — but this has **not** been verified
  against a real GSD install, and direct prior experience with a similar
  project suggests it may be more closed than documented). The adapter
  is designed to degrade gracefully either way:
  - If `cross_ai_command` proves to be a real general-purpose hook: point
    it at our own `dispatch.py` entrypoint, receiving the phase prompt
    on stdin exactly like every other CLI in this design already does,
    emitting `SUMMARY.md`-shaped output (exact shape TBD — open risk,
    §14).
  - If it proves closed/unusable: fall back to populating only the
    native runtime enum (best-effort, no fine-grained model/effort/
    context control), and **explicitly tell the user** cross-AI
    execution for GSD is limited in this project — never fail silently.

## 8. superpowers adapter (`ai-kit-spec-execute-superpowers`)

superpowers has **no** cross-CLI config surface at all — confirmed live
(`subagent-driven-development`'s own "Model Selection" section only
knows Claude tiers dispatched via the native `Agent` tool, chosen by task
complexity). There is nothing to *extend*; there is a real, good harness
to *preserve*.

**Scope correction (this revision, sourced from the implementation plan's own
verification against both skills' real SKILL.md text — cross-AI review flagged
the original text below as narrowed by the plan without the design being
updated to match; this is that update):** the adapter targets
`subagent-driven-development` only, and only its one documented
subagent-dispatch point ("1. Dispatch the implementer"). `superpowers:
executing-plans`, read directly, runs every task inline in the controller's
own session — "Follow each step exactly", no `Agent`-tool dispatch, no
subagent, no report file anywhere in its process — so it has no extension
point this adapter (or any adapter) could inject a resolved model/CLI into;
this design's earlier phrasing ("invokes `executing-plans` (or
`subagent-driven-development`)") was aspirational and unverified against that
skill's actual text, not a real integration path. Likewise, substitution
applies only at the implementer-dispatch point, not at every point
`subagent-driven-development` happens to dispatch a subagent: that skill's
own "3. Review the task" / "4. The fix loop" / final-review dispatches are
answering a different question (which judgment tier should read this task's
work, per that skill's own cost/complexity-tiered "Model Selection" section)
than this adapter's live-quota execute-candidate ladder (which write-capable
candidate can actually run the task) — folding review-model selection into
the execute ladder would silently mix two unrelated policies, so those
dispatches keep using `subagent-driven-development`'s own native
model-selection logic, unmodified.

The adapter invokes `subagent-driven-development` as the actual execution
methodology — same task-by-task discipline, TDD enforcement,
fresh-subagent-per-task, review-between-tasks, commit cadence, all unchanged.
The adapter is the one *invoking* that skill (as its orchestrator), and
passes the already-resolved model/CLI choice as an explicit input at its
implementer-dispatch point — same pattern `ai-kit-spec-review` already uses
to hand pre-resolved `ARCHETYPE`/`FRAMEWORK_PROFILE_PATH` into
`ai-kit-spec-review-checklist` rather than letting it re-detect. At that one
point, the adapter substitutes: native `Agent` tool if the resolved candidate
is a Claude tier dispatched natively (unchanged from today), or
`dispatch.py`'s external-CLI path otherwise — while every other structural
guarantee (scope, TDD, review cadence, task/re-review/final-review dispatch)
stays exactly as `subagent-driven-development` already defines it.

## 9. Codebase exploration tooling (applies to both review and execute)

Two existing, already-installed sources of tool-preference guidance are
*pointed to*, never duplicated inline:

- `/var/home/bazzite/.agents/AGENTS-TOOLING.md` (machine-level, path
  must be detected/configurable, not hardcoded — may not exist on other
  machines) — `rg`/`fd`/`bat`/`eza`/`delta` preference, and the CodeGraph
  protocol (`codegraph init` if uninitialized, `codegraph_explore` MCP
  tool preferred over broad reads, `codegraph status`/`sync`/`index` for
  maintenance).
- RTK (`~/.claude/RTK.md`, already in this session's own global
  instructions) — a Claude-Code-hook-based transparent command rewriter.
  Its benefit is automatic within native Claude dispatch (the hook
  applies); it does **not** reliably extend to an externally-dispatched
  CLI process (no such hook there) — never assume an external CLI will
  honor a prose instruction to prefix commands with `rtk`.

**CodeGraph — confirmed via the project's own docs, not assumed**:
`@colbymchenry/codegraph`, npm-global package (installed via `pnpm
install -g @colbymchenry/codegraph` — pnpm preferred over npm per this
project's security convention; `pnpx` preferred over `npx` for
one-off invocation). Registration is global and reused across projects
via `codegraph install --target=<client> --location=global --yes --init`
(confirmed real flags, `--location` accepts `global`/`local`, default:
interactive prompt) — per the project's own docs *"one global `codegraph
install` works in every project you open — no need to re-run the
installer per project."* That said, **global** does not mean
**install-once-ever, skip-checking-forever**: `codegraph` itself, or any
individual client CLI (`codex`/`cursor`/etc.), can be installed *after*
the initial `codegraph install` ran — that client's registration would
simply never have happened. So the check (cheap: read that client's own
MCP-config file, below) runs **every session, scoped to whichever client
is about to be dispatched** — not once ever. Only the `install` command
itself is conditional: it runs (targeting that one client) when the
check for it comes back missing; a client already confirmed registered
is never reinstalled. `codegraph init`/`sync` (building a given
project's actual index) remains per-project/per-session regardless of
install location — that part can't be made global, it reflects that
specific codebase's current state. **Officially supported clients**
(confirmed from the project
README): Claude Code, Cursor, Codex CLI, opencode, Hermes Agent, Gemini
CLI, Antigravity IDE, Kiro, GitHub Copilot. **`grok` is not on this
list** — confirmed unsupported, not a gap to research further.

No dedicated "verify MCP registration" command exists in codegraph
itself (`codegraph status` reports indexing state, not MCP-registration
state) — verification is done by reading each target CLI's own MCP
config location directly (a new small per-CLI lookup table: where each
CLI stores its MCP server registrations — same shape as
`_MODEL_VENDOR_PREFIXES`).

**Hard rule, and it applies identically to review and execute**: if a
CLI's codegraph MCP registration cannot be confirmed (grok always; any
other CLI where the config-file check fails), the `codegraph_explore`
guidance is **omitted entirely** from that dispatch's prompt — never
pass a subagent prose it would have to infer/guess about when the
answer should be certain.

**Write-vs-read-only ordering (review specifically)**: `codegraph
init`/`sync` **writes** `.codegraph/` into the target repo. Reviewers run
read-only by design (§ prior spec) and must never run this themselves.
The **orchestrator** (unsandboxed, normal write access) runs `codegraph
sync || codegraph init` — minimum 15s timeout regardless of the
typically-fast real runtime (<5s medium codebases, <2s small, confirmed
by direct experience; the margin is worth it against occasional slow
runs) — **before** dispatching the reviewer/fixer/executor subagent.
The dispatched subagent only ever calls the already-built index via the
read-only `codegraph_explore` MCP tool afterward — the read-only
guarantee is never touched.

## 10. Resilience

**Heartbeat**: `dispatch.py` prints a timestamped line at a fixed
interval while polling an in-flight external-CLI dispatch — a real,
lived pain point (GSD subagent/cross-execution going silent for long
stretches), not hypothetical. Same dispatcher serves review's future
JSONL-findings work (separate, already-deferred increment) and
execute's need here — one piece of infrastructure, two consumers.

**Auto-wake on quota exhaustion**: when every candidate (top-N ∩
affinity, then the escalation fallback) is quota-exhausted within a
wave, the orchestrator persists minimal resumable state (framework,
plan/phase reference, candidates already tried, iteration) to a status
file, then schedules `CronCreate` (confirmed available in this harness;
confirmed **session-scoped only** — jobs vanish if the session/terminal
exits, only fire while the session is idle, recurring jobs auto-expire
after 7 days) to re-check quota (`probe-quota`) roughly hourly, resuming
once quota is confirmed restored. This is **not** a true
shutdown-and-resume mechanism — it requires the session to stay alive
and idle. Applies identically to `ai-kit-spec-review`'s own loop and to
`ai-kit-spec-execute` — same shape of problem (a long loop that can hit
a quota wall), same mechanism.

**Scratch/tmp directory naming**: run-scoped scratch directories
(`mktemp -d`, confirmed collision-immune — atomic directory creation,
~62¹⁰ combinations, retried on the astronomically rare collision, never
silently reused) get a slug in their working-notes reference (e.g.
`$RUN_TMP_DIR` recorded alongside a human-readable slug: feature/plan
name + iteration), not left as an opaque random path — directly
motivated by this session's own `worktree-agent-<random>` naming being
hard to trace back to what it was for.

## 11. Cache namespace rename

`~/.cache/ai-kit/review-spec/{runtimes,quota}.json` →
`~/.cache/ai-kit/spec/{runtimes,quota}.json` — no longer review-specific,
shared by both families. `cache_runtimes_path`/`cache_quota_path` move
into `detection.py`/`quota.py` respectively (§4) with the new base path;
existing cached files at the old path are not migrated automatically —
first run under the new path just re-detects (cheap, already `--if-stale`
gated).

## 12. Error handling

| Condition | Behavior |
|---|---|
| Quota exhausted mid-wave (top-N ∩ affinity) | escalate to next detected-available candidate outside top-N |
| All candidates exhausted | persist resumable state, schedule `CronCreate` (~hourly), resume on confirmed quota restoration |
| `cross_ai_command` closed/unusable (GSD) | fall back to native enum only, explicitly report degraded capability to user |
| execute-mode builder not yet live-verified for a CLI | refuse with explicit error (same `ValueError` pattern as review's `cursor-agent` mode guard) — never attempt an unverified invocation |
| codegraph MCP registration unconfirmed for target CLI | omit `codegraph_explore` guidance from that dispatch's prompt entirely |
| dispatch process dies for a non-quota reason | surface the real error; never silently retry disguised as quota-wait (only the quota path triggers auto-wake) |

## 13. Testing strategy

- **Unit tests** (deterministic pieces): affinity table resolution,
  context-size filtering, ladder escalation across a wave, config merge
  — same style as the review family's 146 tests.
- **Smoke tests, required before trusting any new execute-mode builder**:
  live verification against the real installed CLI for each — same
  standard that caught 2 real bugs in the review family's grok builder;
  no execute-mode builder ships untested.
- **Dedicated smoke test for GSD's `cross_ai_command`** — resolves the
  disputed-doc risk (§7) empirically, against a real GSD install, before
  the adapter's design is finalized on that path.
- **End-to-end smoke test**: one toy plan/phase run through the full
  loop (selection → dispatch → heartbeat → completion) against at least
  one real external CLI, not just isolated command-building tests.
- **`skill-judge`** run against all 3 new skills
  (`ai-kit-spec-execute`, `-gsd`, `-superpowers`) before considering them
  done — same bar already applied to the review family.

## 14. Open risks (explicit, not silently assumed away)

1. GSD's `workflow.cross_ai_execution`/`cross_ai_command` real behavior —
   disputed, needs live verification (§7, §13).
2. `SUMMARY.md`-compatible output shape for GSD's cross-AI hook — not yet
   reverse-engineered against a real install.
3. Execute-mode command builders for grok and claude — mechanism not yet
   identified/confirmed (codex/cursor-agent/opencode have a documented
   starting point; grok/claude do not yet).
4. Per-CLI MCP-config-file locations (for codegraph registration
   verification) — table not yet built; needs one entry per supported
   client.
5. Context-size curated data — depends on `ai-kit-spec-config`'s
   WebSearch research quality at config time; no live-CLI shortcut
   exists (confirmed, §5).

## 15. Naming

`ai-kit-spec-execute` (not `-code`/`-run`) — used consistently throughout
this design's discussion with no objection raised; finalized here.
