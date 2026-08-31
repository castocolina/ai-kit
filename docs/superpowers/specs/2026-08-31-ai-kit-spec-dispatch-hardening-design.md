# ai-kit-spec Dispatch Hardening Design

**Status:** design ready

## 1. Goal

Fix four concrete gaps found while live-running `/ai-kit-spec-review` against a real plan
document (`docs/superpowers/plans/2026-08-29-ai-kit-spec-execute-superpowers.md`, "Plan 3") this
session:

1. External reviewer CLIs get zero explicit tool-preference guidance from this project — a
   dispatched CLI either happens to load its own machine-level hook (codex) or gets nothing at
   all (grok has no `AGENTS.md`/`GROK.md` ingestion whatsoever).
2. Reviewer/model selection has no awareness that the *same* model can be reachable through
   multiple CLI wrappers with very different tool-access profiles (codegraph/MCP support).
3. Cross-AI reviewer dispatch used a single flat 300s timeout, unusable for `effort=high`
   models on a codebase-grounded review — required four manual escalations (300/600/900/1500s)
   before producing any usable signal.
4. The orchestrator only ever inspects a dispatched CLI's output after the subprocess dies —
   there is no interim visibility into whether it's making progress or stalled.

## 2. Motivation — live evidence from this session

- Dispatching `grok-4.6` via the standalone `grok` CLI (not `cursor-agent`/`opencode`) left it
  working blind for ~55 minutes across 4 escalating timeouts without producing a single finding.
  `grok` has no `AGENTS.md`/`GROK.md` ingestion (confirmed: `~/.grok/` contains no such file) and
  `detection.py`'s `_SUPPORTED_CODEGRAPH_CLIENTS = {"claude", "codex", "cursor-agent",
  "opencode"}` deliberately excludes it — it never gets `codegraph_explore` guidance.
- `codex/gpt-5.6-sol` (effort=high), which DOES have codegraph access, made real, visibly
  growing progress on every retry (read the grounding doc, then ran genuine
  `codegraph_explore` queries against the merged Plan 2 codebase) but never reached 5, 10, or 15
  minutes.
- `~/.agents/AGENTS-TOOLING.md` (the one file that DOES get read, by codex, via its own
  unrelated hook) does not even mention `sd` as the modern replacement for `sed` — confirmed by
  grep. This project has no canonical, versioned, portable tooling-preference resource of its
  own; it depends entirely on a machine-level file outside the repo.
- The orchestrator's Step 1 dispatch is hand-rolled `nohup ... > file 2>&1 &` bash, built fresh
  each run — a `sed`-based attempt to fix a multi-line command this session corrupted grok's
  entire invocation silently (0 bytes output, no error surfaced) until manually diagnosed.

## 3. Architecture overview

Four independent components, three of which are net-new, one of which extends an existing
module:

```
dispatch.py
  dispatch_with_heartbeat()      <- unchanged, execute path keeps using it (Non-Goals, §11)
  dispatch_with_polling()        <- NEW: tiered timeout escalation + progressive file polling

cli.py (Foundation)
  dispatch-reviewer               <- NEW subcommand, wraps dispatch_with_polling for review

tooling_guidance.py
  build_tooling_guidance()        <- EXTENDED: always includes the new shared reference file

references/tooling-guidance.md    <- NEW: canonical, repo-owned tool-preference prose

ai-kit-spec-review-checklist/SKILL.md   <- EXTENDED: legacy-tool-usage rule (MEDIUM)
ai-kit-spec-config/SKILL.md             <- EXTENDED: codegraph-aware CLI-preference note
ai-kit-spec-review/SKILL.md             <- EXTENDED: Step 0.7 detect-tools, Step 1 rewritten
                                            to call dispatch-reviewer instead of hand-rolled bash
config_io.py / render-toml               <- EXTENDED: policy.timeout_tiers schema field
```

## 4. `dispatch_with_polling` (new, `dispatch.py`)

```python
def dispatch_with_polling(command: str, prompt: str, timeout_tiers: list[int],
                           poll_interval: int = 150, popen_fn=subprocess.Popen,
                           time_fn=time.time, sleep_fn=time.sleep,
                           kill_fn=_default_kill_process_group, print_fn=_default_print_fn,
                           tmp_dir_fn=tempfile.mkdtemp) -> dict:
```

Differs from `dispatch_with_heartbeat` in exactly one structural way: **stdout/stderr are
redirected to real files, never `PIPE`.** This has two consequences:

- **No deadlock risk delivering `prompt` via a direct `stdin.write()`.** `dispatch_with_
  heartbeat`'s own docstring documents why a direct write is unsafe there — stdout backpressure
  through our own pipe can fill and block concurrently with stdin filling. With stdout/stderr
  going straight to files (OS-buffered, never routed through our process), that specific
  condition cannot occur; `communicate()`'s concurrent-draining machinery is no longer needed
  for this function.
- **Real progress is inspectable while the subprocess is alive.** A poll loop calls
  `os.stat(stdout_path).st_size` every `poll_interval` seconds and prints a one-line delta via
  `print_fn` (stderr, same convention as the existing heartbeat) — e.g. `[12:03:41] codex-sol:
  +4231 bytes since last check (total 9872)`. **Informational only — never aborts an attempt
  early**, even at zero growth (design decision: a false "stalled" verdict on a genuinely
  slow-but-working model is worse than the wasted wait; a human watching the interim lines can
  always choose to interrupt).

For each `timeout_tiers` entry, in order:

1. Start a fresh `Popen` (a killed CLI process cannot resume its own reasoning state — each
   tier restart genuinely starts over; this is an accepted, documented cost, not an oversight).
2. Write `prompt` to stdin directly, close stdin.
3. Poll until the process exits or this tier's timeout elapses.
4. On tier timeout: `kill_fn`, drain the files' current contents, print an escalation line
   (`"tier N (Xs) timed out — escalating to tier N+1 (Ys)"`), continue to the next tier if one
   remains.
5. On the last tier's timeout, or on a clean exit at any tier: return
   `{"returncode", "stdout", "stderr", "timed_out", "tiers_tried", "final_timeout"}` — a superset
   of `dispatch_with_heartbeat`'s return shape (two new informational keys).

## 5. `dispatch-reviewer` CLI subcommand (new, Foundation `cli.py`)

Mirrors `dispatch-execute`'s existing shape and contract (`--stdout-only`, real returncode) but
for the review path:

```
dispatch-reviewer --command <rendered reviewer command> --prompt-file <path|-> \
  --timeout-tiers 600,1200,1800 --cli <id|none> \
  --tool-availability-json <json> --agents-tooling-path <path|omit> \
  --codegraph-registered --stdout-only
```

Composes the full prompt as `build_tooling_guidance(...) + "\n\n" + <prompt file content>` (see
§6), then calls `dispatch_with_polling`. `--stdout-only` writes only `result["stdout"]` and
exits with `result["returncode"]` (or `1` if `None`), identical contract to `dispatch-execute`,
so `ai-kit-spec-review/SKILL.md`'s Step 1 replaces its entire hand-rolled `nohup`/`timeout`/
redirect block with one call to this subcommand — removing the class of bug that produced
today's `sed`-corrupted grok dispatch (one tested Python code path builds and runs the command,
never ad hoc shell assembled fresh per run).

## 6. Shared tooling-guidance reference (new)

`skills/ai-kit-spec-review/references/tooling-guidance.md` — canonical, versioned prose:
`rg` over `grep`, `fd` over `find`, `bat` for viewing, `eza` over `ls`, **`sd` over `sed`**
(the gap `~/.agents/AGENTS-TOOLING.md` has today), `delta`/`difftastic` over `diff`, and
`codegraph_explore` (MCP) preference language for architecture/cross-reference questions —
mirroring `tooling_guidance.py`'s existing confirmed-only discipline.

`build_tooling_guidance(cli, tool_availability, agents_tooling_path, codegraph_registered,
shared_reference_path)` gains one new parameter: `shared_reference_path` — always resolved by
the caller (this repo-owned file always exists in this install, unlike the best-effort
machine-level `agents_tooling_path`) and always emitted as its own `"Read {shared_reference_
path} for this repo's confirmed tool preferences."` line, independent of whether
`agents_tooling_path` resolved to anything. This is an explicit in-prompt instruction, not a
reliance on the target CLI's own hook-loading — the same proven mechanism `FRAMEWORK_PROFILE_
PATH`/`CHECKLIST_SKILL_MD` already use, so it works identically whether the dispatched CLI is
codex (which happens to also have its own unrelated hook), grok (which has none), or any future
CLI this project adds.

`ai-kit-spec-execute`'s own `prepare-tooling` call site also switches to passing this same
`shared_reference_path`, so execute-mode dispatches get the same canonical prose — the two
families no longer diverge on this point (Global Constraint, §9).

## 7. `ai-kit-spec-review-checklist` — legacy-tool-usage rule (new)

New rule, **MEDIUM** severity always (not conditioned to a softer default): fires when the
reviewed document references a legacy tool (`grep`, `find`, `cat` for search/listing, `sed`) via
a literal command invocation, **and** `tool_availability` (passed in by the orchestrator,
resolved via `detect-tools`) confirms the modern equivalent (`rg`/`fd`/`bat`/`sd`) is installed
on the target machine. Finding names the specific line and the exact modern replacement.

Separately (not a finding about the document): a new short instruction tells the reviewer to
prefer `rg`/`fd`/`bat`/`sd`/`eza` during its **own** grounding work, pointing at the same
`tooling-guidance.md` reference (§6) — consistent with how `FRAMEWORK_PROFILE_PATH` is already
handled (a `Read`-and-apply reference, not inlined prose).

## 8. `ai-kit-spec-config` — codegraph-aware CLI preference (new, Step 2.2-2.4)

Best-effort, informational only (never a hard block, consistent with this skill's existing
"never silently pre-filter — user decides" principle). When building the model-family list for
a CLI outside `_SUPPORTED_CODEGRAPH_CLIENTS` (today: `grok`), cross-reference `runtimes.json`'s
per-CLI `models` lists for a same-vendor, same-base-model entry under a codegraph-capable CLI
(`cursor-agent`/`opencode`) — a substring/heuristic match on the base model name, since id
conventions differ per CLI (`grok-4.6` vs. `cursor-grok-4.6-high`). When found, print one line
before the user picks: `"<model> is also reachable via <codegraph-capable CLI>, which supports
codegraph_explore (grok CLI does not) — prefer that pairing for grounding-heavy review/execute
work."` The user still makes the final call; this is a note, not a filtered-out option.

## 9. `review-spec.toml` schema — `policy.timeout_tiers`

```toml
[policy]
mode = "double"
ladder = ["codex-sol", "grok-flagship"]
timeout_tiers = [600, 1200, 1800]   # NEW, optional, defaults to this 10/20/30-minute ladder
```

An individual `[[reviewers]]` entry may set its own `extra.timeout_tiers` to override the
policy default (e.g. a CLI/effort combination known to need longer). `poll_interval` is
**deliberately not** a config knob — fixed at a sane constant inside `dispatch_with_polling`
(YAGNI until a real need for per-project tuning appears).

`ai-kit-spec-config` Step 2.8 gains one optional ask: whether to customize `timeout_tiers` from
the default, presented only when at least one external-CLI reviewer is being registered (native
dispatch has no subprocess to time out).

## 10. `ai-kit-spec-review/SKILL.md` changes

- **Step 0.7 point 0**: alongside the existing `RUNTIMES_JSON`/`QUOTA_JSON` resolution, add a
  `detect-tools` call (mirroring `ai-kit-spec-config`'s own Step 1), cached the same way, so
  `tool_availability` is available to pass into `dispatch-reviewer` and into the reviewer
  prompt template.
- **Step 1 (external CLI dispatch)**: the entire hand-rolled
  `<printed command> < prompt > report` block is replaced with one `dispatch-reviewer` call,
  passing `--timeout-tiers` (resolved from `policy.timeout_tiers` or the entry's own
  `extra.timeout_tiers` override), `--tool-availability-json`, `--agents-tooling-path` (best
  effort, may be absent), and `--codegraph-registered` (from `check_codegraph_mcp_healthy`,
  already exists).
- **Native reviewer prompt template**: gains the same tooling-guidance line pointing at
  `tooling-guidance.md`, for consistency — a native (in-session Claude) reviewer already has
  real tool access, but explicitly telling it the repo's preferences (same as any other
  subagent gets) keeps behavior symmetric rather than accidentally better for one path.

## 11. Non-Goals

- Migrating `execute_dispatch.dispatch_execute`'s existing single-`timeout` call site (Plan 2,
  already shipped and merged) to `dispatch_with_polling`. The new function is designed as a
  drop-in future replacement, but touching already-merged, already-live-tested execute-path code
  is out of scope for this plan.
- Making `poll_interval` user-configurable.
- Auto-aborting a stalled dispatch early — informational polling only (§4, §2 decisions).
- Hard-blocking a CLI/model registration in `ai-kit-spec-config` based on codegraph support —
  informational note only (§8).

## 12. Error handling

| Condition | Behavior |
|---|---|
| All `timeout_tiers` exhausted without a clean exit | Return `timed_out: True` with whatever partial stdout/stderr the LAST tier's attempt produced (not concatenated across tiers) — same "never force-discarded to empty" principle `dispatch_with_heartbeat` already follows. |
| `shared_reference_path` file missing (corrupted install) | `build_tooling_guidance` omits that line entirely rather than erroring — same never-guess-if-uncertain principle already governing `agents_tooling_path`. |
| `tool_availability` missing a key the legacy-tool rule needs | Treat as "modern equivalent not confirmed available" — never flag on an unconfirmed presence (same principle as `tooling_guidance.py`'s codegraph check). |
| No same-vendor/base-model match found across CLI catalogs (§8) | No note printed — silence is the correct default, not a placeholder message. |

## 13. Testing strategy

- **Unit tests** (deterministic): `dispatch_with_polling`'s tier-escalation logic (injected
  `popen_fn`/`time_fn`/`sleep_fn` fakes, no real subprocess), `build_tooling_guidance`'s new
  parameter, the legacy-tool-usage rule's condition logic, the CLI-preference substring matcher.
- **Live smoke test, required before trusting this**: a real dispatch that genuinely needs tier
  escalation (or a fake command with an artificial delay) to confirm a real process survives a
  kill-and-restart cycle correctly and the final result reflects the successful tier, not a
  stale one.
- **`skill-judge` run against every SKILL.md this plan modifies** — `ai-kit-spec-review`,
  `ai-kit-spec-review-checklist`, `ai-kit-spec-config` — same bar already applied to the
  `ai-kit-spec-execute-*` family before considering Plans 1-3 done (established precedent, not
  a new requirement invented here). Run it after edits land, as a gate before the plan is
  considered complete.

## 14. Open risks

1. The CLI-preference substring matcher (§8) is inherently heuristic — model-id naming drifts
   fast across vendors/CLIs; a missed match degrades silently to "no note," never a false claim.
2. Redirecting stdout/stderr to real files (vs. pipes) means this function now touches the
   filesystem for every dispatch attempt — needs cleanup (temp dir per attempt, removed after
   the final result is read) to avoid accumulating stale files across many review iterations.
3. `dispatch_with_polling`'s tier-restart cost (full re-dispatch, losing prior reasoning state)
   is real and not hidden — the actual time cost of hitting the last tier is the SUM of every
   earlier tier's timeout, not just the last one. Documented in §4; worth revisiting if this
   proves too expensive in practice (e.g. starting straight at the tier matching a known
   `effort=high` reviewer, rather than always escalating from tier 1).

## 15. File structure summary

```
skills/ai-kit-spec-review/
  ai_kit_spec/dispatch.py                    (extend: dispatch_with_polling)
  ai_kit_spec/cli.py                         (extend: dispatch-reviewer subcommand)
  ai_kit_spec/tooling_guidance.py            (extend: shared_reference_path param)
  ai_kit_spec/config_io.py                   (extend: policy.timeout_tiers schema)
  references/tooling-guidance.md             (NEW)
  SKILL.md                                   (extend: Step 0.7, Step 1, native prompt template)

skills/ai-kit-spec-review-checklist/
  SKILL.md                                   (extend: legacy-tool-usage rule)

skills/ai-kit-spec-config/
  SKILL.md                                   (extend: Step 2.2-2.4 CLI preference, Step 2.8 timeout_tiers ask)
```
