# ai-kit-spec-execute-gsd Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the GSD (Get Sh*t Done) adapter for `ai-kit-spec-execute`: a skill that resolves the best available model/CLI for a GSD phase's execution task, then dispatches it either through GSD's own native tiering (`model_overrides`/`models`/`model_profile`) or, if genuinely a real hook, GSD's `workflow.cross_ai_execution`/`cross_ai_command` — falling back to explicit user notification (never silent failure) when neither native tiering nor a real cross-provider hook can carry the chosen model.

**Architecture:** Task 1 is a live spike against a real GSD install that settles the one fact this entire adapter's shape depends on: is `cross_ai_command` a general arbitrary-shell-command hook, or a closed enum restricted to specific known providers? Every later task is written as two branches gated on that spike's finding — this plan cannot be collapsed to a single path before Task 1 runs, because the correct adapter architecture literally differs depending on the answer.

**Tech Stack:** Python 3 stdlib only, `unittest`, GSD's own `.planning/config.json` JSON config
surface (confirmed JSON, not TOML, by design brainstorming and GSD's own docs — Task 1 Step 2
re-confirms this live; if that re-confirmation ever finds otherwise, treat it as a stop-the-plan
discrepancy to resolve before Task 2, not a silent branch this plan already anticipates).

**Spec:** `docs/superpowers/specs/2026-08-28-ai-kit-spec-execute-design.md` (§7, GSD adapter)

## Global Constraints

- Depends on Plan 1 (Foundation) being complete and merged: `ai_kit_spec.execute_selection`, `ai_kit_spec.commands.build_execute_command`, `ai_kit_spec.dispatch.dispatch_with_heartbeat`, `ai_kit_spec.config_io.cfg_resolve`, `ai_kit_spec.detection.*`, `ai_kit_spec.tooling_guidance.build_tooling_guidance`, `ai_kit_spec.quota._UNAVAILABLE_SIGNALS` all exist and are tested (`skills/ai-kit-spec-review/ai_kit_spec/{execute_selection,commands,dispatch,detection,tooling_guidance,config_io,quota}.py`) before this plan's Task 2 onward.
- **Real, live-verified constraint on Foundation's `build_execute_command`** (confirmed by reading the actual shipped `skills/ai-kit-spec-review/ai_kit_spec/commands.py`, not assumed from the design spec): `_EXECUTE_COMMAND_BUILDERS` has exactly ONE working execute-mode (write-capable) builder today — `codex`. `cursor-agent` and `opencode` were live-tested and failed real write confinement (demoted, per that file's own comment); `grok` and `claude` were never implemented; `gemini` is not registered at all. Every one of those raises `ValueError`. Any cross-AI execute path this plan designs must degrade gracefully within that real constraint (Task 3), never assume a broader builder set exists.
- Never silently fail to honor the user's chosen model — if GSD's config surface can't carry it (native tier map too coarse, `cross_ai_command` unusable), the adapter must explicitly tell the user which vendor's default it fell back to and why (design spec §7, §12).
- `cross_ai_command`'s real behavior is disputed (WebFetch-sourced docs said "general hook"; user's own direct prior experience says "closed enum") — this plan trusts neither claim until Task 1 confirms one against a real install.
- GSD's built-in tier maps are hardcoded to claude/codex/gemini only, with static (staling) model IDs (confirmed during design brainstorming) — do not assume any other vendor is reachable through native tiering. This set (`NATIVE_TIER_VENDORS`, Task 2) is a distinct concept from design spec §7's "native runtime enum" (`cursor/gemini/claude/…`, open-ended, gated by Task 1 as Branch B's `_CLOSED_ENUM_PROVIDERS`, Task 3) — the two sets are NOT guaranteed to match and this plan never conflates them.
- **Writing `model_overrides` alone does not establish which vendor runtime GSD invokes (iteration-4 review finding 5)** — design spec §7 confirms GSD's own config surface separately carries a `runtime` key (".planning/config.json's `runtime`, `model_profile`, `model_overrides`, `models`") alongside the model-tier maps; `model_overrides`/`model_profile`/`models` only select WHICH MODEL within whatever runtime `runtime` currently names, not which vendor CLI executes it. Every task in this plan that writes a native-tier model override MUST also confirm/write the matching `runtime` value (`gsd_config.write_active_runtime`, Task 2) so GSD's active runtime actually matches the vendor of the model just written — writing `model_overrides["backend"] = "gpt-5.6-sol"` while `runtime` still names `"claude"` would silently have GSD attempt to run an OpenAI model id through its Claude runtime. Task 1 Step 2 confirms this key's exact name/shape/reload-semantics live; Task 2's shipped code is a defensive scaffold pending that confirmation, same as `model_overrides` itself.
- **A candidate whose config entry has no `cli` (`cli is None`) is a NATIVE (current-runtime) reviewer/dispatch entry** — this repo's own `.aikit/review-spec.toml` ships exactly such an entry (`[[reviewers]] key = "opus-native"`, `model = "opus"`, no `cli`), matching `ai_kit_spec.commands.ResolvedReviewer`'s and `quota._to_resolved`'s own documented shape for native dispatch ("cli/command are None for native (current-runtime) dispatch"). Every task in this plan that branches on `candidate["cli"] in NATIVE_TIER_VENDORS` MUST also treat `candidate["cli"] is None` the same way (native tiering is always reachable for it — it runs as the current Claude session itself, exactly what `model_overrides` is for) — a `None`-`cli` candidate must never fall through to `fallback_notice`.
- **`execute_selection.resolve_execute_candidates` never itself probes quota** — its own docstring states plainly it "only narrows and ranks... the caller must feed its output through `candidates_to_ladder` into `quota.resolve_ladder_pick`" for a live-availability pick. Every task that selects a dispatch candidate MUST go through that two-step call, and MUST be able to escalate past a candidate that has quota but turns out unusable (no native/cross-AI dispatch path) to the *next* quota-available candidate — never just `ranked[0]`.
- **The CLI entrypoint MUST load live quota before resolving a dispatch decision, and a RUNTIME (not just probe-time) quota failure MUST escalate within the same wave (iteration-4 review finding 2)** — `ai_kit_spec_gsd/cli.py`'s `resolve-dispatch` subcommand (Task 4) MUST call `ai_kit_spec.quota.refresh_quota_cache`/read `ai_kit_spec.quota.cache_quota_path` (the exact mechanism `ai_kit_spec/cli.py`'s own `probe-quota` subcommand already uses) and pass the resulting dict as `resolve_gsd_dispatch`'s `quota=` argument — an omitted `quota` makes `{}` look like "every candidate has quota," defeating live-availability entirely. Separately, when the CANDIDATE `resolve-dispatch` selected is actually dispatched (Task 5 Step 3/4) and that real dispatch fails with a quota signal (`classify_dispatch_failure` returns `"quota"`), Task 5's SKILL.md MUST re-invoke `resolve-dispatch` with that candidate's key added to a growing `--exclude-key` list (Task 4's CLI gains this flag) BEFORE writing resumable state or scheduling any auto-wake — auto-wake is scheduled ONLY once `resolve-dispatch` itself returns `fallback_notice` (every quota-available candidate in the ladder has now been tried and excluded), never after the first runtime failure. The resumable state written at that point (Task 5 Step 4) MUST include the full `candidates_tried` list accumulated across that loop, not just the last one attempted.
- **`execute_selection.filter_by_affinity`'s `task_type` parameter is a frontend/backend/mixed "task_affinity" axis (design spec §5.1) — a different concept than GSD's own phase-type category** (planning/discuss/research/execution/verification/completion, design spec §7, the key `resolve_native_tier` looks up by). Never pass GSD's `phase_type` as `execute_selection`'s `task_type` argument. Since no task in this plan populates curated `task_affinity` data yet (design spec §14, open risk #5 — Foundation ships every candidate untagged), the correct value to pass is literally `None` (an explicit "no known task-affinity axis at this layer," not a stand-in for phase_type) — `filter_by_affinity` already treats `task_type=None`-compared-candidates as a no-op pass-through by design, so this is honest, not a workaround.
- **Out of scope, stated explicitly**: design spec §7's `dynamic_routing` key (GSD's own tier-escalation-on-verification-failure behavior) is read/written by no task in this plan — every write this adapter makes to `.planning/config.json` touches `model_overrides`/`runtime`/the two cross-AI keys from Task 2/3/5, and preserves `dynamic_routing` and every other existing key unchanged. Quota-exhaustion escalation (Task 5 Step 4's `CronCreate` auto-wake) is a *different* problem this plan does solve; verification-failure escalation remains entirely GSD's own existing behavior. This is a deliberate scope boundary — reimplementing GSD's own escalation logic risks fighting it instead of coexisting with it.
- **Second explicit scope boundary (iteration-4 review finding 3) — curated task-affinity/context-size data does not exist anywhere in Foundation yet** (design spec §14, open risk #5: no `[[reviewers]]` entry in any shipped `review-spec.toml` carries a `task_affinity`/`context_limit` field). This plan does NOT implement per-candidate task-fit/context-fit *filtering* — but `assemble_candidates` (Task 4) genuinely READS `task_affinity`/`context_limit` off each config entry when present (iteration-5 review finding 12 — never hardcoded), defaulting to `None` for BOTH fields only when the entry genuinely doesn't carry them, which is every entry that exists today. **CORRECTED (iteration-6 review, CRITICAL finding, two independent reviewers): the default MUST be `None`, never `0` — the real shipped `execute_selection.filter_by_context` treats `context_limit is None` as "unknown, pass through" but treats `context_limit == 0` as "confirmed insufficient for any positive required_context," which would silently drop every uncurated candidate on every real run** (an earlier revision of this plan wrongly defaulted `context_limit` to `0`, which independently broke production dispatch — fixed here). `execute_selection.filter_by_context` treats that honest `None` default as a documented no-op pass-through. Selection among today's untagged candidates in this plan therefore reduces to live-quota-checked ladder order — this is accurate and is what "live-quota-checked, tier-aware" means in this plan's Goal/Architecture; it does NOT mean "task-fit-aware" or "context-fit-aware" selection, and no prose in this plan claims otherwise after this revision. What this plan DOES do for `context_limit`, so that axis is not permanently inert once curated data exists: `resolve_gsd_dispatch` (Task 4) computes a real, non-hardcoded `required_context` estimate from the actual phase prompt text (`adapter.estimate_required_context`, Task 4) — today every candidate's `context_limit` is `None` (no config entry curates it yet) so this estimate has no filtering effect yet (per `filter_by_context`'s own missing-data-passes-through rule), but the moment `ai-kit-spec-config` (or a future increment) starts writing a real `context_limit` into a `review-spec.toml` `[[reviewers]]` entry, `assemble_candidates` picks it up automatically and this plan's dispatch path starts honoring it — with ZERO code change required here. **`task_affinity` does NOT share this "zero code change" guarantee (iteration-6 review, HIGH finding — corrected here): `resolve_gsd_dispatch` always passes `task_type=None` to `filter_by_affinity`, and the real shipped `filter_by_affinity` keeps a candidate only when `c.get("task_affinity") is None or c.get("task_affinity") == task_type` — so the MOMENT a config entry is curated with a real `task_affinity` value (e.g. `"backend"`), it compares unequal to the hardcoded `task_type=None` and that candidate is FILTERED OUT, the opposite of "activates automatically." Honoring curated `task_affinity` requires a FUTURE change to this plan's dispatch path (classifying the GSD phase into a real `task_type` and passing it through) — this plan explicitly declines to build that classifier now (YAGNI, zero curated data exists to test against), so `task_affinity` curation must not be relied upon until that future work lands.** `task_type` remains explicitly `None` (never a computed frontend/backend/mixed guess) — inventing a classifier for an axis with zero curated candidate data to filter against would be speculative, untestable machinery this plan explicitly declines to build (YAGNI); this is a stated decision, not a silent default.
- **Adapter-vs-user config-write provenance (iteration-4 review finding 6)**: every `model_overrides`/`runtime` write this adapter makes via `gsd_config.write_native_tier_override`/`write_active_runtime` (Task 2) is also recorded in a sidecar ownership-marker key (`gsd_config["_ai_kit_spec_execute_gsd"]["overrides"][phase_type]`, Task 2) in the SAME write. `resolve_gsd_dispatch` (Task 4) reads this marker before treating an existing `model_overrides[phase_type]` entry as an unmodifiable prior user choice — an entry that exactly matches this run's own marker is the adapter's OWN prior write, still eligible for re-resolution (a stale, no-longer-quota-available previous pick must not permanently pin a project once written); an entry present with no matching marker (or a mismatched one) is a genuine external user choice and is honored unconditionally, exactly as before. Backups (`gsd_config.py`'s `_backup_once`) use a per-run backup path (a monotonic run id, not a single fixed suffix reused by every future run) so a second run's write can never silently overwrite the ONE backup taken before the first-ever write to a project's config.
- **Malformed vs. missing config are distinct, machine-readable outcomes (iteration-4 review finding 7)**: `gsd_config.read_gsd_config` (Task 2) already distinguishes them via `warn_fn` (silent `{}` for missing, a warned `{}` for malformed/unreadable) — `ai_kit_spec_gsd/cli.py` (Task 4) MUST route `warn_fn` to **stderr**, never stdout (every `cli.py` subcommand's stdout is a parseable JSON result; a warning line mixed into it would corrupt every caller's `json.loads`), and MUST abort any config-mutating subcommand (never call `write_native_tier_override`/`write_active_runtime`/`write_workflow_key`) when the read was malformed/unreadable rather than genuinely missing — overwriting a real, broken-but-recoverable user config with a near-empty generated one is exactly the "silently discard the user's data" failure design spec §12 forbids. The distinction is carried as an explicit `read_gsd_config` return-shape change, not inferred by the caller re-parsing warnings — see Task 2 Step 0's revision to `read_gsd_config`'s signature/return shape.

---

## File Structure

```
skills/ai-kit-spec-execute/                    (new skill directory)
  SKILL.md                                      (router: classifies GSD vs superpowers vs other, delegates)
  detect_framework.py
skills/ai-kit-spec-execute-gsd/                 (new skill directory, this plan's primary deliverable)
  SKILL.md                                      (GSD-specific dispatch flow)
  ai-kit-spec-gsd.py                            (import-bootstrap SHIM -- the ONLY thing SKILL.md
                                                  ever invokes by absolute path; mirrors
                                                  skills/ai-kit-spec-review/ai-kit-spec.py's own
                                                  "python puts the running script's own directory
                                                  on sys.path[0]" trick, PLUS explicitly inserts the
                                                  sibling skills/ai-kit-spec-review/ directory onto
                                                  sys.path so ai_kit_spec_gsd's own `from
                                                  ai_kit_spec...` imports resolve too -- see Task 2
                                                  Steps 7-9. Dispatches `<shim> resolve-dispatch ...`
                                                  etc. to ai_kit_spec_gsd.cli.main, and
                                                  `<shim> cross-ai-wrapper ...` to
                                                  ai_kit_spec_gsd.cross_ai_wrapper.main -- the SAME
                                                  shim is what Branch A's cross_ai_command string
                                                  (Task 3) invokes, since GSD shells that command out
                                                  from an arbitrary, unknown cwd.)
  ai_kit_spec_gsd/
    __init__.py
    gsd_config.py                               (read/write .planning/config.json: native-tier
                                                  mapping, active-runtime key, workflow-key writes,
                                                  adapter-ownership marker, per-run backups)
    gsd_cross_ai.py                             (cross_ai_command usage -- shape depends on Task 1's finding)
    cross_ai_wrapper.py                         (Branch A only: the program GSD's cross_ai_command hook actually shells out to, invoked via the shim above)
    adapter.py                                  (candidate assembly + live-quota-checked dispatch resolution + phase context-size estimate)
    cli.py                                      (resolve-dispatch + config-path + write-workflow-key + write-active-runtime + prepare-tooling + write-resumable-state subcommands -- concrete invocation paths for SKILL.md, invoked via the shim)
tests/test_ai_kit_spec_gsd.py                   (new test file)
```

`ai-kit-spec-execute` (the router skill) is a thin dispatcher: detect which framework generated
the plan/phase (GSD's `.planning/` markers vs. superpowers' plan-file conventions), then delegate
to `ai-kit-spec-execute-gsd` or `ai-kit-spec-execute-superpowers` (Plan 3). This plan only builds
the GSD-specific half plus a minimal router stub (Task 6) — Plan 3 fills in the superpowers half
of the same router file.

---

### Task 1: SPIKE — confirm `cross_ai_command`'s real behavior against a live GSD install

**Files:** no source files created/modified. Modify: this plan file itself, `docs/superpowers/plans/2026-08-29-ai-kit-spec-execute-gsd.md` (iteration-5 review finding 18 — Step 5 below inserts the dated finding subsection directly into this file; that edit is the entirety of this task's deliverable, no other file changes).

**Interfaces:** none — spike output is a plain-English finding, not code.

- [ ] **Step 1: Obtain a real GSD install to test against**

If a GSD-managed project already exists locally (check for `.planning/PROJECT.md` under any
known repo, or the ai-kit repo's own git history for a GSD reference), use it. Otherwise, install
GSD fresh in a scratch directory per its own README (`gsd-build/get-shit-done` or its current
relocated home — confirmed during design brainstorming that the canonical repo moved from
`gsd-build` to "Open GSD"/"GSD Core"; resolve the current canonical location first, do not
assume the old org name still resolves) and run its own init flow to produce a real
`.planning/config.json`.

- [ ] **Step 2: Read the real `.planning/config.json` schema and any `workflow.cross_ai_*` keys**

```bash
cat .planning/config.json 2>&1 | head -100
```

Look specifically for `workflow.cross_ai_execution`, `workflow.cross_ai_command`,
`workflow.cross_ai_timeout` keys, GSD's native-runtime-enum key (the one Task 3 Branch B writes
into), and `model_overrides`/`models`/`model_profile` — record their actual current key names
and, if more than one of `model_overrides`/`models`/`model_profile` is present simultaneously in
a real config, which one GSD itself prefers (Task 2's `resolve_native_tier` priority order is
provisional pending this). The design spec's names are provisional, sourced from a WebFetch
summary that may be stale or wrong.

Also record, definitively, each of these — Task 2's shipped code is a defensive scaffold (see
Task 2 Step 0) but is NOT guaranteed correct on any of these axes until this step confirms them:
- Is `models[...]` a per-**phase-type** tier alias (`models["execution"] = "tier-2"`), or
  something else (e.g. per-agent)?
- Is `model_overrides[...]` keyed by **phase type** (`model_overrides["execution"] = "<model>"`,
  what Task 2 assumes) or by **agent name** (`model_overrides["<agent-id>"] = "<model>"`)? If
  agent-keyed, record how an agent maps to a phase type, since `resolve_native_tier`/
  `write_native_tier_override`'s `phase_type` parameter would need to become an agent id instead.
- Is `model_profile` a **scalar** string (applies uniformly, not keyed by phase type at all) or a
  dict? Task 2's `resolve_native_tier` must not crash by blindly calling `.get()` on whichever
  shape this turns out to be — confirm the real shape so Task 2's type-dispatch logic is exercised
  against fact, not guesswork.
- What are GSD's "active-runtime" semantics — does writing a new `model_overrides` entry take
  effect on GSD's very next command, or does GSD require an explicit reinstall/reload/restart of
  its own process before a config write is honored? If a reload is required, record the exact
  command/mechanism; Task 5 Step 2 must be updated to run it after any config write.
- Does an active GSD **workstream** use a workstream-scoped config path (distinct from the
  project-root `.planning/config.json` Task 2/5 currently hardcode), and if so, what is that path
  convention and how does an executing agent learn the current workstream id?
- **What is the exact key name and shape of GSD's `runtime` key** (design spec §7: ".planning/
  config.json's `runtime`, `model_profile`, `model_overrides`, `models`") — the key that selects
  WHICH VENDOR CLI/runtime executes a phase, separate from `model_overrides`/`model_profile`
  selecting which model WITHIN that runtime? Record: its exact key name (confirm `"runtime"` is
  correct, not a different name), whether it is a bare vendor-id string (e.g. `"claude"`) or a
  structured value, whether it is phase-type-scoped or project-global, and its own reload
  semantics. Task 2's `write_active_runtime`/`resolve_active_runtime` (Step 0 below) are a
  defensive scaffold pending this confirmation — writing a model override for vendor X while
  `runtime` still names vendor Y is a real, silent misconfiguration this plan must not ship
  (iteration-4 review finding 5).

If any of these diverge from Task 2's shipped defaults, that divergence is itself the deliverable
of this step — do not silently proceed past a mismatch; it gates a mandatory Task 2 revision
(Task 2 Step 0, added below).

- [ ] **Step 3: Read GSD's own source/docs for how it consumes `cross_ai_command`**

```bash
grep -rn "cross_ai" <path-to-cloned-gsd-source> 2>&1 | head -50
```

Locate the actual code path that reads this config value. Answer definitively:
- Is the value a shell command string GSD executes verbatim (general hook), or
- Is it a closed enum/set of recognized provider identifiers GSD switches on internally (closed enum, matching the user's direct prior experience)? If closed enum: record the exact fixed value set.
- What does GSD do with the *output* of whatever this produces — does it expect a specific file (e.g. `SUMMARY.md`) to exist afterward, parse stdout directly, or something else?
- Which config key name holds the native-runtime-enum case specifically (distinct from `cross_ai_command`, per design spec §7) — record its exact name for Task 5 Step 2.

- [ ] **Step 4: Attempt a live round-trip if the finding suggests a general hook**

Only if Step 3 concludes "general shell-command hook": configure `cross_ai_command` to invoke
a trivial script and run whatever GSD command actually consumes this against a throwaway phase:

```bash
cat > /tmp/trivial-hook.sh <<'EOF'
#!/bin/sh
cat > /dev/null   # drain stdin (the phase prompt), same contract dispatch.py's real hook will use
echo "SUMMARY.md-shaped output goes here" > /tmp/SUMMARY.md
EOF
chmod +x /tmp/trivial-hook.sh
# set workflow.cross_ai_command (or the confirmed equivalent key) to /tmp/trivial-hook.sh in the
# scratch GSD install's .planning/config.json, then:
gsd-execute-phase <throwaway-phase-id>   # or GSD's actual confirmed equivalent command
cat /tmp/SUMMARY.md 2>&1
```

Confirm GSD actually shells out to it and reads the output the way Step 3 predicted. If Step 3
concludes "closed enum", skip this — there is nothing to round-trip, document the enum's fixed
value set instead.

- [ ] **Step 4.5: Record GSD's own phase-execution invocation contract — REQUIRED regardless of which branch Step 3 confirms (iteration-4 review finding 10)**

Every branch this plan later forks on (Task 3's Branch A/B, Task 5's dispatch modes) still needs
ONE common fact this step alone establishes: the exact command GSD itself runs to execute a
phase (Task 5 Step 3 calls this "GSD's own execution entry point", used identically for
`native_tier`, `cross_ai_hook`, and `native_enum` dispatch modes alike). Record, definitively,
for BOTH Branch A and Branch B (this does not depend on Step 3's finding — do not skip this for
whichever branch does not win):
- The exact executable/invocation (e.g. `gsd-execute-phase <phase-id>`, or GSD's real confirmed
  equivalent) — literal command name and argument shape, not a placeholder.
- The required working directory (project root, or something else) it must be run from.
- Its stdin behavior: does it read the phase prompt from stdin at all (Task 5 Step 3 pipes the
  phase's prompt/context file content into it via `dispatch_with_heartbeat`), or does it resolve
  the phase content itself from `.planning/` given only a phase id?
- Its output contract: does it print a machine-parseable result on stdout, write a result file
  (and if so, the exact path/name — confirmed, not guessed, unlike Step 4's earlier
  `/tmp/SUMMARY.md` example, which was a throwaway hook test, not GSD's real phase-completion
  file), or something else? What exit code means success vs. failure?

**Execution-boundary direction, stated explicitly to prevent a real prior confusion (iteration-5
review finding 11):** this command (GSD's own phase-execution entry point) is what Task 5 Step 3
runs directly, in EVERY dispatch mode — `native_tier`, `cross_ai_hook`, AND `native_enum` alike.
It is GSD's OUTER caller. If Branch A wins, GSD's OWN phase-execution flow separately invokes
`cross_ai_command` (Task 3's wrapper, `cross_ai_wrapper.py`) as ITS OWN cross-AI hook — the
wrapper is the INNER command GSD's hook calls, never the reverse. The wrapper's own job (Task 3
Branch A) is to dispatch the SELECTED EXTERNAL CLI via `ai_kit_spec.commands.build_execute_command`
— it does NOT shell back out to this command (GSD's phase-execution entry point) at all; that
would be circular. In short: Task 5 Step 3 → GSD's phase-execution entry point (this step's own
finding) → (Branch A only, and only when GSD itself decides to invoke its configured
`cross_ai_command` hook) → `cross_ai_wrapper.py` → the selected external CLI. If Branch B wins,
this command (GSD's phase-execution entry point) is still the only invocation Task 5 Step 3 ever
runs directly (Branch B has no wrapper of its own, since GSD's own native-runtime-enum switch
handles cross-provider dispatch internally) — record it here regardless, this step is not
conditional on Step 3's branch outcome.

- [ ] **Step 5: Record the finding**

Add a dated note directly to this plan file (edit this file, insert a subsection here) with:
one paragraph stating definitively which of the two it is, the exact config key names
confirmed live (including the separate native-runtime-enum key from Step 3, AND the `runtime`
key's exact name/shape from Step 2's new checklist item), the confirmed
`model_overrides`/`models`/`model_profile` precedence AND their confirmed shapes (phase-type-keyed
vs. agent-keyed vs. scalar, per Step 2's checklist), the active-runtime/reload semantics, the
workstream-scoped config path convention (or confirmation that none exists), Step 4.5's recorded
phase-execution invocation contract (command, cwd, stdin behavior, output contract) for BOTH
branches, and (if a hook) the exact invocation contract (env vars/args passed, expected output
shape) or (if an enum) the exact fixed value set GSD recognizes. This finding gates which of
Task 3's two branches every subsequent task follows, and gates Task 2 Step 0's mandatory revision
checkpoint — do not proceed to Task 2 Step 1 until this is written down.

---

### Task 2: `gsd_config.py` — read/write GSD's native tier map

**Depends on Task 1's Step 5 finding** for `model_overrides`/`models`/`model_profile`'s exact
key names, shapes (phase-type-keyed vs. agent-keyed vs. scalar), and precedence — do not begin
implementation until Task 1 is recorded; the priority order and shapes below are provisional and
must be re-verified against Task 1's live finding first.

- [ ] **Step 0: Mandatory revision checkpoint against Task 1's finding**

Before writing Step 1's tests, re-read Task 1's Step 5 finding (this plan file). If it confirms
any of the following, revise this task's interfaces/tests/implementation below to match BEFORE
proceeding — the code that follows is a defensively-typed starting scaffold, not a
guaranteed-correct final shape:
- `model_overrides` is keyed by **agent id**, not phase type: rename `phase_type` parameters in
  this task to `agent_id` (or add a phase-type→agent-id mapping step first) throughout
  `resolve_native_tier`/`write_native_tier_override`, and update Task 4/5 callers accordingly.
- `model_profile` is confirmed a **scalar** (not phase-type-keyed): `resolve_native_tier`'s
  type-dispatch below already handles this without crashing — verify the live shape matches, and
  if `models` also turns out scalar, extend the same type-dispatch branch to it.
- A config write requires a GSD reload/reinstall to take effect: add that step explicitly to
  Task 5 Step 2, naming the exact command Task 1 recorded.
- A workstream-scoped config path is confirmed: `resolve_gsd_config_path` below already accepts
  a `workstream_id` override — wire the real detection Task 1 found into its default resolution,
  and update Task 5 Step 1 to call it with the current workstream id instead of assuming project
  root.
- `runtime`'s real key name differs from `"runtime"`, or its shape is not a bare vendor-id string:
  rename/reshape `write_active_runtime`/`resolve_active_runtime` (below) to match before Task 4/5
  ever call them — a native-tier write that sets the wrong key name silently fails to switch
  GSD's active runtime at all (iteration-4 review finding 5).

If Task 1 confirms this plan's provisional defaults exactly, this step is a no-op — record that
confirmation in a one-line comment at the top of `gsd_config.py` and proceed.

**Files:**
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/__init__.py` (empty file — makes the
  package importable)
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_config.py`
- Create: `skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py` (the import-bootstrap shim, Steps
  7-9 below — iteration-4 review finding 13)
- Modify: `Makefile`, `.pre-commit-config.yaml` (Step 5 below — register the new test module and
  expand the ruff/py-compile hooks' `files:` scope to this plan's new source directories)
- Test: `tests/test_ai_kit_spec_gsd.py`

**Interfaces:**
- Consumes: `ai_kit_spec.cache.cache_write_json` (Plan 1, for atomic JSON writes).
- Produces:
  - `read_gsd_config(path: str, read_fn=open, warn_fn=print) -> tuple[dict, str]` — parses `.planning/config.json`. Returns `({}, "missing")` if the file doesn't exist (a project not yet GSD-configured is a valid, non-error state — no warning). Returns `({}, "malformed")` on malformed JSON or an unreadable file, and calls `warn_fn` with an explicit message first — "not configured" and "broken config being silently swallowed" must never look identical to a caller, per the "never silently fail" global constraint AND per iteration-4 review finding 7 (a `dict`-only return forced every caller to re-infer the distinction from warning side effects, or not at all). Returns `(config, "ok")` on a successful parse. **Every caller in this plan (Task 4's `resolve_gsd_dispatch`, Task 5's SKILL.md) MUST treat `"malformed"` as a hard abort for any config-MUTATING operation** (`write_native_tier_override`/`write_active_runtime`/`write_workflow_key` must not be called) — overwriting a real, broken-but-recoverable user config with a near-empty generated one silently destroys it, which design spec §12 forbids. `"missing"` is safe to proceed past (nothing to lose, the project just isn't GSD-configured yet).
  - `resolve_native_tier(gsd_config: dict, phase_type: str) -> str | None` — looks up `model_overrides` → `models` → `model_profile` (priority order provisional pending Task 1, see above) for the given phase type. Each key's value may be a `dict` (looked up by `phase_type`) OR a bare `str` (a scalar tier that applies uniformly, regardless of `phase_type` — this is `model_profile`'s documented possible shape, and calling `.get()` on it unconditionally would raise `AttributeError`; this function never does that). Returns the resolved model id string or `None` if nothing resolves.
  - `resolve_active_runtime(gsd_config: dict) -> str | None` — reads `gsd_config.get("runtime")` (exact key name/shape pending Task 1 Step 2's live confirmation, see Task 1's new checklist item and this task's Step 0). Returns the currently-active vendor runtime id, or `None` if unset.
  - `write_active_runtime(path: str, gsd_config: dict, runtime: str, write_fn=cache_write_json, backup_copy_fn=shutil.copy2, isfile_fn=os.path.isfile, run_id: str | None = None) -> dict` — persists `runtime` into `gsd_config["runtime"]` (every other existing key preserved unchanged) AND, in the SAME write, records its OWN adapter-ownership marker into `gsd_config["_ai_kit_spec_execute_gsd"]["runtime"] = runtime` (iteration-5 review finding 5 — mirrors `write_native_tier_override`'s own `["overrides"][phase_type]` sidecar contract, under its own `"runtime"` sub-key rather than reusing `"overrides"`), with the SAME per-run backup guarantee as `write_native_tier_override`/`write_workflow_key` below. This is the function that makes a native-tier model-override write actually take effect against the RIGHT vendor CLI (iteration-4 review finding 5) — `resolve_gsd_dispatch` (Task 4) calls this alongside `write_native_tier_override` whenever the candidate's vendor differs from `resolve_active_runtime(gsd_config)`'s current value, never model-override-only, and (per this task's Step 0 writing-ordering contract) THREADS this call's own returned dict into the following `write_native_tier_override` call's `gsd_config` argument — never the pre-runtime-write snapshot (iteration-5 review finding 3).
  - `generate_run_id(time_fn=time.time) -> str` — PUBLIC (iteration-5 review finding 5). A caller performing more than one write per logical run (`resolve_gsd_dispatch`'s own two write calls, Task 4; `cli.py`'s `resolve-dispatch`/`write-workflow-key` subcommands, Task 4) MUST call this exactly ONCE at the start of that run and thread the SAME string through every write call's own `run_id=` argument — leaving `run_id=None` on two separate write calls does NOT give them the same id (each call's own default is evaluated independently and returns a different timestamp), silently defeating the "one run_id, one backup per run" guarantee. `_backup_once`'s internal default-generation behavior (below) is unchanged; this just gives external callers (`cli.py`) the same generator to call up front, once, instead of duplicating the timestamp formula.
  - `write_native_tier_override(path: str, gsd_config: dict, phase_type: str, model: str, write_fn=cache_write_json, backup_copy_fn=shutil.copy2, isfile_fn=os.path.isfile, run_id: str | None = None) -> dict` — persists `model` into `gsd_config["model_overrides"][phase_type]` AND, in the SAME write, records adapter ownership of that write into `gsd_config["_ai_kit_spec_execute_gsd"]["overrides"][phase_type] = model` (iteration-4 review finding 6 — an ownership marker distinguishing an adapter-made override from a genuine prior user choice, read back by `override_is_adapter_owned` below). Writes the merged dict to `path` (every other existing key preserved unchanged). Before the first write of a run (`run_id` — see `_backup_once` below), if `path` already exists on disk and no backup yet exists at this run's OWN backup path, copies the REAL ON-DISK BYTES of `path` to the backup path via `backup_copy_fn(path, backup_path)` — never a re-serialization of the in-memory `gsd_config` dict (which may already be `{}` on a malformed-JSON read; backing up `{}` while the real file has content would make the documented manual restore destroy the user's config instead of restoring it). Returns the updated dict.
  - `override_is_adapter_owned(gsd_config: dict, phase_type: str) -> bool` — `True` only when `gsd_config["model_overrides"][phase_type]` is present AND exactly equals `gsd_config["_ai_kit_spec_execute_gsd"]["overrides"][phase_type]` (both keys present and matching — a prior run of THIS adapter wrote the currently-active override, so it is safe to re-resolve/replace on this run rather than treated as an immovable user choice). `False` when the marker is absent, mismatched, or the override itself is absent (the honest "not confirmed adapter-owned" default — treat as a genuine user choice, never override it).
  - `resolve_gsd_config_path(cwd: str, workstream_id: str | None = None, isfile_fn=os.path.isfile) -> str` — returns the one authoritative config path to read/write/back up consistently. Default (Task 1 has not yet confirmed a workstream-scoped convention): `os.path.join(cwd, ".planning", "config.json")`. Accepts an explicit `workstream_id` override so Task 5's caller can pass one once Task 1's Step 2 finding (or Step 0 above) confirms the real convention; until then this is honest about being project-root-only, not silently wrong about workstreams it was never told about.
  - `write_workflow_key(path: str, gsd_config: dict, key: str, value, write_fn=cache_write_json, backup_copy_fn=shutil.copy2, isfile_fn=os.path.isfile, run_id: str | None = None) -> dict` — persists `value` into `gsd_config["workflow"][key]` (every other `workflow` key and every other top-level key preserved unchanged) AND, in the SAME write, records adapter ownership into `gsd_config["_ai_kit_spec_execute_gsd"]["workflow"][key] = value` (iteration-5 review finding 6 — mirrors `write_native_tier_override`'s own `["overrides"][phase_type]` sidecar contract, under its own `"workflow"` sub-key, read back by `workflow_key_is_adapter_owned`/cleared by `clear_workflow_key_if_adapter_owned` below), with the SAME per-run-backup guarantee as `write_native_tier_override` (a run that calls both this and `write_native_tier_override`/`write_active_runtime` still only backs up once total, on whichever call goes first — all three share `_backup_once`'s `run_id`-scoped check). This is the function Task 5 Step 2 uses for `workflow.cross_ai_command`/`workflow.cross_ai_execution`/the native-runtime-enum key — no cross-AI config write in this plan happens through hand-rolled prose, all go through this tested function. **Returns the updated dict, which the caller MUST thread into the next `write_workflow_key`/`write_native_tier_override`/`write_active_runtime` call's own `gsd_config` argument** (iteration-4 review finding 11) — two writes against the same stale `gsd_config` snapshot would have the second silently discard the first's key.
  - `workflow_key_is_adapter_owned(gsd_config: dict, key: str) -> bool` — `True` only when `gsd_config["workflow"][key]` is present AND exactly equals `gsd_config["_ai_kit_spec_execute_gsd"]["workflow"][key]` (mirrors `override_is_adapter_owned` above, for workflow keys instead of `model_overrides`).
  - `clear_workflow_key_if_adapter_owned(path: str, gsd_config: dict, key: str, write_fn=cache_write_json, backup_copy_fn=shutil.copy2, isfile_fn=os.path.isfile, run_id: str | None = None) -> dict` — iteration-5 review finding 6's mode-transition fix: when `workflow_key_is_adapter_owned(gsd_config, key)` is `True` (a PRIOR run of THIS adapter set this workflow key, e.g. `cross_ai_command`/`cross_ai_execution`, while dispatching through `cross_ai_hook`/`native_enum` mode), deletes both `gsd_config["workflow"][key]` and its own ownership-marker entry and writes the result — a stale adapter-owned cross-AI hook must not stay active once a LATER run picks a different dispatch mode (`native_tier`/`fallback_notice`), or GSD would keep routing through a hook this plan no longer intends active. When the key is absent, or present but NOT adapter-owned (a genuine value the user set by hand), this is a no-op that returns `gsd_config` unchanged and never writes — a user's own choice is never touched.
  - `_backup_once(path, backup_copy_fn, isfile_fn, run_id) -> None` (internal, shared by all three write functions) — backup path is `f"{path}.ai-kit-spec-execute-gsd.{run_id}.bak"`, one distinct file PER RUN (`run_id` defaults to a timestamp captured once by the caller — Task 4's `resolve_gsd_dispatch`/Task 5's SKILL.md compute ONE `run_id` at the start of a run and pass it through every write call in that run) rather than one fixed suffix shared across every future run of this adapter against the same project — the fixed-suffix design let a second run's write silently overwrite the ONE backup taken before the very first write ever made (iteration-4 review finding 6). Skips the copy (as before) once a backup already exists at that run's specific path.
  - `NATIVE_TIER_VENDORS = {"claude", "codex", "gemini"}` — sourced from this plan's own Global Constraints (confirmed during design brainstorming that GSD's built-in tier maps only cover these three), **not** design spec §7's "native runtime enum" (a separate, open-ended, possibly-different set — see `gsd_cross_ai.py` Branch B). Any resolved model outside this vendor set (and NOT `None`, which is the separate native-current-runtime case — see Global Constraints) could not have come from native tiering — a defensive assertion point for Task 4.

- [ ] **Step 1: Write the failing tests**

```python
import os
import sys
import unittest
from unittest import mock

# iteration-4 review finding 15: no top-level `import shutil` here -- no test in this file
# references the real shutil module directly (every write function's own backup_copy_fn is
# always a fake/lambda in tests), and the repo's own ruff/py-compile gate (Task 2 Step 5) would
# flag an unused import.
#
# Bootstraps ALL package roots this plan's tests need -- ai_kit_spec_gsd (this plan) and
# ai_kit_spec (Plan 1, Foundation) both live outside this file's own directory, on no search
# path by default, same reason tests/test_ai_kit_spec.py already does this for ai_kit_spec.
# skills/ai-kit-spec-execute is ALSO added here (not just skills/ai-kit-spec-execute-gsd) because
# Task 6's detect_framework module lives there and this is the ONE bootstrap block for the whole
# file -- it goes ONCE at the top; every later Task in this plan appends test classes below it,
# never repeats it, and each later Task's own snippet below still includes its own `from ... import
# ...` line for the specific module it exercises (shown in that Task's Step 1).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute-gsd"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute"))

# ai_kit_spec_gsd submodules are imported INCREMENTALLY -- one `from ai_kit_spec_gsd import X`
# line, added by the SPECIFIC task that first exercises X, placed immediately above that task's
# own test class(es) below (iteration-5 review finding 1, independently found by two reviewers:
# this task, Task 2, creates ONLY gsd_config.py -- adapter.py/cli.py don't exist until Task 4,
# gsd_cross_ai.py not until Task 3, and cross_ai_wrapper.py not until Task 3 BRANCH A ONLY (Branch
# B never creates it at all). A single top-level `from ai_kit_spec_gsd import adapter, cli,
# gsd_config, gsd_cross_ai, cross_ai_wrapper` here would raise ModuleNotFoundError at IMPORT time
# -- before any test in ANY task can even collect -- for every task run before the LAST one that
# creates one of these modules, permanently breaking every earlier task's own "Expected: PASS"
# step, and permanently breaking Branch B (which never creates cross_ai_wrapper.py at all). Every
# later Task's own Step 1/1A/1B/6 snippet below carries an explicit note showing exactly which
# import line it adds and why that module already exists at that point -- follow those notes
# literally; never restore a single combined import line here.
#
# This task's own tests need only gsd_config, created by THIS task -- import it here, nothing
# else:
from ai_kit_spec_gsd import gsd_config


class TestReadGsdConfig(unittest.TestCase):
    def test_returns_empty_dict_and_missing_status_when_file_missing(self):
        def raise_not_found(*a, **k):
            raise FileNotFoundError()
        warnings = []
        config, status = gsd_config.read_gsd_config("/nonexistent", read_fn=raise_not_found,
                                                      warn_fn=warnings.append)
        self.assertEqual(config, {})
        self.assertEqual(status, "missing")
        self.assertEqual(warnings, [])  # missing file is a valid state -- no warning

    def test_parses_real_config_shape_with_ok_status(self):
        import io
        fake = io.StringIO('{"model_overrides": {"backend": "claude-opus-5"}}')
        config, status = gsd_config.read_gsd_config("/x", read_fn=lambda *a, **k: fake)
        self.assertEqual(config["model_overrides"]["backend"], "claude-opus-5")
        self.assertEqual(status, "ok")

    def test_malformed_json_warns_and_returns_empty_dict_with_malformed_status(self):
        # "missing" and "malformed" MUST be distinguishable by status alone -- a caller must
        # never have to re-parse warn_fn output to tell them apart (iteration-4 review finding 7).
        import io
        fake = io.StringIO("not valid json {{{")
        warnings = []
        config, status = gsd_config.read_gsd_config("/x", read_fn=lambda *a, **k: fake,
                                                      warn_fn=warnings.append)
        self.assertEqual(config, {})
        self.assertEqual(status, "malformed")
        self.assertEqual(len(warnings), 1)
        self.assertIn("/x", warnings[0])


class TestResolveNativeTier(unittest.TestCase):
    def test_model_overrides_takes_priority(self):
        config = {"model_overrides": {"backend": "claude-opus-5"},
                   "models": {"backend": "gemini-3.7-pro"},
                   "model_profile": {"backend": "codex-tier-1"}}
        self.assertEqual(gsd_config.resolve_native_tier(config, "backend"), "claude-opus-5")

    def test_falls_back_to_models_then_model_profile(self):
        config = {"models": {"backend": "gemini-3.7-pro"},
                   "model_profile": {"backend": "codex-tier-1"}}
        self.assertEqual(gsd_config.resolve_native_tier(config, "backend"), "gemini-3.7-pro")
        config2 = {"model_profile": {"backend": "codex-tier-1"}}
        self.assertEqual(gsd_config.resolve_native_tier(config2, "backend"), "codex-tier-1")

    def test_returns_none_when_phase_type_unresolved(self):
        config = {"model_overrides": {"frontend": "claude-opus-5"}}
        self.assertIsNone(gsd_config.resolve_native_tier(config, "backend"))

    def test_scalar_model_profile_applies_uniformly_without_crashing(self):
        # model_profile may be a bare string (Task 1 Step 2 confirms live) -- must never crash
        # by calling .get() on a str, and must resolve regardless of phase_type.
        config = {"model_profile": "codex-tier-1"}
        self.assertEqual(gsd_config.resolve_native_tier(config, "backend"), "codex-tier-1")
        self.assertEqual(gsd_config.resolve_native_tier(config, "frontend"), "codex-tier-1")


class TestWriteNativeTierOverride(unittest.TestCase):
    def test_writes_model_override_records_ownership_marker_and_preserves_other_keys(self):
        # Ownership marker (iteration-4 review finding 6): a later run must be able to tell this
        # write apart from a genuine user edit -- see TestOverrideIsAdapterOwned below.
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        result = gsd_config.write_native_tier_override(
            "/repo/.planning/config.json", {"dynamic_routing": {"foo": "bar"}},
            "backend", "claude-opus-5",
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        self.assertEqual(result["model_overrides"]["backend"], "claude-opus-5")
        self.assertEqual(result["_ai_kit_spec_execute_gsd"]["overrides"]["backend"],
                          "claude-opus-5")
        self.assertEqual(result["dynamic_routing"], {"foo": "bar"})  # untouched
        self.assertEqual(writes["/repo/.planning/config.json"]["model_overrides"]["backend"],
                          "claude-opus-5")

    def test_backs_up_existing_config_once_before_first_write_of_this_run(self):
        # isfile_fn distinguishes the real source path (exists) from THIS RUN's backup path (does
        # not yet exist) -- a fixed `lambda p: True` for both would make the code believe a
        # backup already exists and skip writing one, which is exactly the bug this test catches.
        copies = []
        def fake_copy(src, dst):
            copies.append((src, dst))
        gsd_config.write_native_tier_override(
            "/repo/.planning/config.json", {"model_overrides": {}}, "backend", "claude-opus-5",
            write_fn=lambda *a: None, backup_copy_fn=fake_copy,
            isfile_fn=lambda p: p == "/repo/.planning/config.json", run_id="run-1")
        self.assertEqual(copies, [("/repo/.planning/config.json",
                                    "/repo/.planning/config.json.ai-kit-spec-execute-gsd.run-1.bak")])

    def test_does_not_back_up_again_within_the_same_run_once_a_backup_already_exists(self):
        copies = []
        def fake_copy(src, dst):
            copies.append((src, dst))
        # both the source AND this run's backup already exist -- a second write within the SAME
        # run must not clobber the backup taken before that run's own first write.
        gsd_config.write_native_tier_override(
            "/repo/.planning/config.json", {"model_overrides": {"backend": "claude-opus-5"}},
            "frontend", "gemini-3.7-pro",
            write_fn=lambda *a: None, backup_copy_fn=fake_copy, isfile_fn=lambda p: True,
            run_id="run-1")
        self.assertEqual(copies, [])

    def test_a_later_run_gets_its_own_distinct_backup_path(self):
        # This is the exact bug iteration-4 review finding 6 flagged: a single fixed suffix meant
        # every future run shared ONE backup slot, so run 2's write could silently overwrite the
        # only backup ever taken (from before run 1's first write) with run 1's OWN output.
        copies = []
        def fake_copy(src, dst):
            copies.append(dst)
        gsd_config.write_native_tier_override(
            "/repo/.planning/config.json", {"model_overrides": {}}, "backend", "claude-opus-5",
            write_fn=lambda *a: None, backup_copy_fn=fake_copy,
            isfile_fn=lambda p: p == "/repo/.planning/config.json", run_id="run-2")
        self.assertEqual(copies, ["/repo/.planning/config.json.ai-kit-spec-execute-gsd.run-2.bak"])


class TestOverrideIsAdapterOwned(unittest.TestCase):
    def test_true_when_marker_matches_current_override_exactly(self):
        config = {"model_overrides": {"backend": "claude-opus-5"},
                  "_ai_kit_spec_execute_gsd": {"overrides": {"backend": "claude-opus-5"}}}
        self.assertTrue(gsd_config.override_is_adapter_owned(config, "backend"))

    def test_false_when_no_marker_present_at_all(self):
        # A genuine, hand-written user override -- never touched, per Global Constraints.
        config = {"model_overrides": {"backend": "claude-opus-5"}}
        self.assertFalse(gsd_config.override_is_adapter_owned(config, "backend"))

    def test_false_when_marker_present_but_value_no_longer_matches(self):
        # The user edited model_overrides by hand AFTER the adapter's own prior write -- the
        # marker is now stale and must not be trusted.
        config = {"model_overrides": {"backend": "claude-hand-edited"},
                  "_ai_kit_spec_execute_gsd": {"overrides": {"backend": "claude-opus-5"}}}
        self.assertFalse(gsd_config.override_is_adapter_owned(config, "backend"))


class TestWriteActiveRuntime(unittest.TestCase):
    def test_writes_runtime_key_and_preserves_other_keys(self):
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        result = gsd_config.write_active_runtime(
            "/repo/.planning/config.json", {"dynamic_routing": {"foo": "bar"}}, "codex",
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        self.assertEqual(result["runtime"], "codex")
        self.assertEqual(result["dynamic_routing"], {"foo": "bar"})  # untouched
        self.assertEqual(writes["/repo/.planning/config.json"]["runtime"], "codex")
        # Ownership marker (iteration-5 review finding 5) -- mirrors write_native_tier_override's
        # own sidecar contract, under its own "runtime" sub-key.
        self.assertEqual(result["_ai_kit_spec_execute_gsd"]["runtime"], "codex")

    def test_resolve_active_runtime_reads_the_same_key(self):
        self.assertEqual(gsd_config.resolve_active_runtime({"runtime": "codex"}), "codex")
        self.assertIsNone(gsd_config.resolve_active_runtime({}))


class TestSharedRunIdOneBackupAcrossWriteFunctions(unittest.TestCase):
    def test_runtime_write_then_override_write_with_the_same_run_id_share_exactly_one_backup(self):
        # iteration-5 review finding 5: "one run_id, one backup per run" means a runtime write
        # and a model-override write in the SAME run (the SAME run_id, generated ONCE by the
        # caller via generate_run_id() and threaded through both calls) must produce exactly ONE
        # backup file total, not two -- _backup_once's own isfile_fn check is what makes the
        # SECOND call's backup attempt a no-op once the FIRST call's backup already exists at
        # that run's own path.
        copies = []
        def fake_copy(src, dst):
            copies.append(dst)
        def fake_isfile(p):
            if p == "/repo/.planning/config.json":
                return True
            return p in copies  # this run's backup path, once fake_copy has "created" it
        config_after_runtime_write = gsd_config.write_active_runtime(
            "/repo/.planning/config.json", {}, "codex", write_fn=lambda *a: None,
            backup_copy_fn=fake_copy, isfile_fn=fake_isfile, run_id="run-shared")
        gsd_config.write_native_tier_override(
            "/repo/.planning/config.json", config_after_runtime_write, "backend", "gpt-5.6-sol",
            write_fn=lambda *a: None, backup_copy_fn=fake_copy, isfile_fn=fake_isfile,
            run_id="run-shared")
        self.assertEqual(
            copies, ["/repo/.planning/config.json.ai-kit-spec-execute-gsd.run-shared.bak"])


class TestResolveGsdConfigPath(unittest.TestCase):
    def test_defaults_to_project_root_planning_config(self):
        self.assertEqual(gsd_config.resolve_gsd_config_path("/repo"),
                          "/repo/.planning/config.json")

    def test_explicit_workstream_id_overrides_default(self):
        # Exact workstream-scoped shape is Task 1/Step-0-pending -- this exercises the plumbing
        # of an explicit override without guessing GSD's real path convention.
        result = gsd_config.resolve_gsd_config_path("/repo", workstream_id="ws-42")
        self.assertNotEqual(result, "/repo/.planning/config.json")
        self.assertIn("ws-42", result)


class TestWriteWorkflowKey(unittest.TestCase):
    def test_writes_key_under_workflow_and_preserves_other_keys(self):
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        result = gsd_config.write_workflow_key(
            "/repo/.planning/config.json",
            {"dynamic_routing": {"foo": "bar"}, "workflow": {"other_key": "keep-me"}},
            "cross_ai_command", "codex exec ...",
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        self.assertEqual(result["workflow"]["cross_ai_command"], "codex exec ...")
        self.assertEqual(result["workflow"]["other_key"], "keep-me")  # untouched
        self.assertEqual(result["dynamic_routing"], {"foo": "bar"})  # untouched
        self.assertEqual(writes["/repo/.planning/config.json"]["workflow"]["cross_ai_command"],
                          "codex exec ...")

    def test_a_second_write_against_the_first_writes_own_returned_dict_keeps_both_keys(self):
        # iteration-4 review finding 11: two workflow-key writes against the SAME stale
        # gsd_config snapshot can have the second discard the first's key. The caller (Task 5's
        # SKILL.md) MUST thread the first call's return value into the second call's own
        # gsd_config argument -- this test proves both keys survive when that's done correctly.
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        first_result = gsd_config.write_workflow_key(
            "/repo/.planning/config.json", {}, "cross_ai_command", "codex exec ...",
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        second_result = gsd_config.write_workflow_key(
            "/repo/.planning/config.json", first_result, "cross_ai_execution", True,
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        self.assertEqual(second_result["workflow"]["cross_ai_command"], "codex exec ...")
        self.assertEqual(second_result["workflow"]["cross_ai_execution"], True)
        self.assertEqual(writes["/repo/.planning/config.json"]["workflow"]["cross_ai_command"],
                          "codex exec ...")
        self.assertEqual(writes["/repo/.planning/config.json"]["workflow"]["cross_ai_execution"],
                          True)


class TestWorkflowKeyOwnershipAndClearing(unittest.TestCase):
    def test_workflow_key_is_adapter_owned_true_when_marker_matches(self):
        config = {"workflow": {"cross_ai_command": "codex exec ..."},
                  "_ai_kit_spec_execute_gsd": {"workflow": {"cross_ai_command": "codex exec ..."}}}
        self.assertTrue(gsd_config.workflow_key_is_adapter_owned(config, "cross_ai_command"))

    def test_workflow_key_is_adapter_owned_false_when_no_marker(self):
        # A genuine, hand-written user value -- never touched.
        config = {"workflow": {"cross_ai_command": "user-set-command"}}
        self.assertFalse(gsd_config.workflow_key_is_adapter_owned(config, "cross_ai_command"))

    def test_clear_workflow_key_if_adapter_owned_removes_an_adapter_owned_key(self):
        # iteration-5 review finding 6: a LATER run that resolves a DIFFERENT dispatch mode must
        # be able to disable a PRIOR run's own cross_ai_command/cross_ai_execution write.
        config = {"workflow": {"cross_ai_command": "codex exec ...", "other_key": "keep-me"},
                  "_ai_kit_spec_execute_gsd": {"workflow": {"cross_ai_command": "codex exec ..."}}}
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        result = gsd_config.clear_workflow_key_if_adapter_owned(
            "/repo/.planning/config.json", config, "cross_ai_command", write_fn=fake_write,
            backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False, run_id="run-1")
        self.assertNotIn("cross_ai_command", result["workflow"])
        self.assertEqual(result["workflow"]["other_key"], "keep-me")  # untouched
        self.assertNotIn("cross_ai_command", result["_ai_kit_spec_execute_gsd"]["workflow"])
        self.assertEqual(writes["/repo/.planning/config.json"], result)

    def test_clear_workflow_key_if_adapter_owned_never_touches_a_genuine_user_value(self):
        config = {"workflow": {"cross_ai_command": "user-set-command"}}
        write_calls = []
        result = gsd_config.clear_workflow_key_if_adapter_owned(
            "/repo/.planning/config.json", config, "cross_ai_command",
            write_fn=lambda *a: write_calls.append(a), backup_copy_fn=lambda *a: None,
            isfile_fn=lambda p: False, run_id="run-1")
        self.assertEqual(result, config)  # unchanged
        self.assertEqual(write_calls, [])  # never wrote over a genuine user value

    def test_clear_workflow_key_if_adapter_owned_is_a_noop_when_key_absent(self):
        config = {"workflow": {}}
        write_calls = []
        result = gsd_config.clear_workflow_key_if_adapter_owned(
            "/repo/.planning/config.json", config, "cross_ai_command",
            write_fn=lambda *a: write_calls.append(a), backup_copy_fn=lambda *a: None,
            isfile_fn=lambda p: False, run_id="run-1")
        self.assertEqual(result, config)
        self.assertEqual(write_calls, [])
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestReadGsdConfig \
  tests.test_ai_kit_spec_gsd.TestResolveNativeTier \
  tests.test_ai_kit_spec_gsd.TestWriteNativeTierOverride \
  tests.test_ai_kit_spec_gsd.TestOverrideIsAdapterOwned \
  tests.test_ai_kit_spec_gsd.TestWriteActiveRuntime \
  tests.test_ai_kit_spec_gsd.TestSharedRunIdOneBackupAcrossWriteFunctions \
  tests.test_ai_kit_spec_gsd.TestResolveGsdConfigPath \
  tests.test_ai_kit_spec_gsd.TestWriteWorkflowKey \
  tests.test_ai_kit_spec_gsd.TestWorkflowKeyOwnershipAndClearing -v 2>&1 | tail -30
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""GSD's .planning/config.json read/write -- key names/precedence confirmed live by Task 1's
spike (see this plan's Task 1, Step 5 finding)."""
import json
import os
import shutil
import time

from ai_kit_spec.cache import cache_write_json


NATIVE_TIER_VENDORS = {"claude", "codex", "gemini"}
_BACKUP_INFIX = ".ai-kit-spec-execute-gsd."  # per-run suffix: f"{path}{_BACKUP_INFIX}{run_id}.bak"
_OWNERSHIP_KEY = "_ai_kit_spec_execute_gsd"


def read_gsd_config(path: str, read_fn=open, warn_fn=print) -> tuple:
    """Returns (config, status) -- status is one of "missing"/"malformed"/"ok". "missing" and
    "malformed" are DELIBERATELY distinguishable (iteration-4 review finding 7): a missing file
    is a valid, unconfigured-project state (no warning, safe to proceed); a malformed/unreadable
    file is a real problem (warned, and callers MUST treat it as a hard abort for any
    config-mutating write -- see this task's Interfaces block)."""
    try:
        with read_fn(path, encoding="utf-8") as f:
            return json.load(f), "ok"
    except FileNotFoundError:
        return {}, "missing"  # not yet GSD-configured -- valid, non-error state, no warning
    except (json.JSONDecodeError, OSError) as exc:
        warn_fn(f"ai-kit-spec-execute-gsd: could not read {path} ({exc}) -- "
                 f"config is MALFORMED, not merely unconfigured -- refusing to write over it")
        return {}, "malformed"


def resolve_native_tier(gsd_config: dict, phase_type: str):
    for key in ("model_overrides", "models", "model_profile"):
        value = gsd_config.get(key)
        if value is None:
            continue
        if isinstance(value, dict):
            resolved = value.get(phase_type)
            if resolved is not None:
                return resolved
        elif isinstance(value, str):
            return value  # scalar tier (e.g. model_profile) applies uniformly, not phase-keyed
    return None


def resolve_active_runtime(gsd_config: dict):
    """Reads GSD's own active-runtime key (design spec §7; exact name/shape confirmed by Task 1
    Step 2 -- see this task's Step 0). Separate from resolve_native_tier: that resolves WHICH
    MODEL to use, this resolves WHICH VENDOR RUNTIME executes it (iteration-4 review finding 5)."""
    return gsd_config.get("runtime")


def resolve_gsd_config_path(cwd: str, workstream_id: str | None = None,
                             isfile_fn=os.path.isfile) -> str:
    """Default: project-root .planning/config.json. Task 1 Step 2/Task 2 Step 0 confirm whether
    an active workstream needs a scoped path instead -- until confirmed, an explicit
    workstream_id still produces a distinct, documented path rather than silently ignoring it."""
    if workstream_id is None:
        return os.path.join(cwd, ".planning", "config.json")
    return os.path.join(cwd, ".planning", "workstreams", workstream_id, "config.json")


def generate_run_id(time_fn=time.time) -> str:
    """PUBLIC (iteration-5 review finding 5) -- a caller that writes more than once per logical
    run (cli.py's resolve-dispatch/write-workflow-key subcommands) MUST call this ONCE at the
    start of that run and thread the SAME string through every write call's own run_id argument.
    Leaving run_id=None on two separate write calls does NOT give them the same id -- each call's
    own default (this function) is evaluated independently and returns a DIFFERENT timestamp,
    which is exactly the "one run_id, one backup per run" guarantee this plan requires and a
    caller that never threads an explicit run_id silently violates."""
    return str(int(time_fn() * 1000))


def _backup_once(path: str, backup_copy_fn, isfile_fn, run_id: str) -> None:
    if not isfile_fn(path):
        return
    backup_path = f"{path}{_BACKUP_INFIX}{run_id}.bak"
    if not isfile_fn(backup_path):
        backup_copy_fn(path, backup_path)  # real on-disk bytes, never the in-memory dict


def write_native_tier_override(path: str, gsd_config: dict, phase_type: str, model: str,
                                write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                                isfile_fn=os.path.isfile, run_id: str | None = None) -> dict:
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    updated["model_overrides"] = dict(updated.get("model_overrides", {}))
    updated["model_overrides"][phase_type] = model
    # Ownership marker (iteration-4 review finding 6): records that THIS ADAPTER made this
    # write, so a later run can tell it apart from a genuine user edit via
    # override_is_adapter_owned -- see this task's Interfaces block.
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    updated[_OWNERSHIP_KEY]["overrides"] = dict(updated[_OWNERSHIP_KEY].get("overrides", {}))
    updated[_OWNERSHIP_KEY]["overrides"][phase_type] = model
    write_fn(path, updated)
    return updated


def override_is_adapter_owned(gsd_config: dict, phase_type: str) -> bool:
    current = gsd_config.get("model_overrides", {}).get(phase_type)
    marker = gsd_config.get(_OWNERSHIP_KEY, {}).get("overrides", {}).get(phase_type)
    return current is not None and current == marker


def write_active_runtime(path: str, gsd_config: dict, runtime: str,
                          write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                          isfile_fn=os.path.isfile, run_id: str | None = None) -> dict:
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    updated["runtime"] = runtime
    # Ownership marker (iteration-5 review finding 5) -- mirrors write_native_tier_override's own
    # sidecar contract above: records that THIS ADAPTER made this runtime write, under its own
    # "runtime" sub-key (distinct from "overrides", which tracks model_overrides writes) so a
    # later run's tooling can distinguish an adapter-made runtime switch from a genuine
    # hand-edited one, the same way override_is_adapter_owned already does for model_overrides.
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    updated[_OWNERSHIP_KEY]["runtime"] = runtime
    write_fn(path, updated)
    return updated


def write_workflow_key(path: str, gsd_config: dict, key: str, value,
                        write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                        isfile_fn=os.path.isfile, run_id: str | None = None) -> dict:
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    updated["workflow"] = dict(updated.get("workflow", {}))
    updated["workflow"][key] = value
    # Ownership marker (iteration-5 review finding 6) -- mirrors write_native_tier_override's own
    # sidecar contract, under its own "workflow" sub-key, read back by
    # workflow_key_is_adapter_owned / cleared by clear_workflow_key_if_adapter_owned below.
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    updated[_OWNERSHIP_KEY]["workflow"] = dict(updated[_OWNERSHIP_KEY].get("workflow", {}))
    updated[_OWNERSHIP_KEY]["workflow"][key] = value
    write_fn(path, updated)
    return updated


def workflow_key_is_adapter_owned(gsd_config: dict, key: str) -> bool:
    current = gsd_config.get("workflow", {}).get(key)
    marker = gsd_config.get(_OWNERSHIP_KEY, {}).get("workflow", {}).get(key)
    return current is not None and current == marker


def clear_workflow_key_if_adapter_owned(path: str, gsd_config: dict, key: str,
                                         write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                                         isfile_fn=os.path.isfile,
                                         run_id: str | None = None) -> dict:
    """Mode-transition fix (iteration-5 review finding 6): a LATER run that selects a DIFFERENT
    dispatch mode must not leave a PRIOR run's own cross_ai_command/cross_ai_execution/
    native-runtime-enum write active -- GSD would keep routing through a stale hook this plan no
    longer intends. Only ever clears a key THIS ADAPTER itself set (workflow_key_is_adapter_owned)
    -- a genuine user-set value is never touched, and a key that's already absent is a no-op
    (no write at all, in either case)."""
    if not workflow_key_is_adapter_owned(gsd_config, key):
        return gsd_config
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    updated["workflow"] = dict(updated.get("workflow", {}))
    del updated["workflow"][key]
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    updated[_OWNERSHIP_KEY]["workflow"] = dict(updated[_OWNERSHIP_KEY].get("workflow", {}))
    del updated[_OWNERSHIP_KEY]["workflow"][key]
    write_fn(path, updated)
    return updated
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestReadGsdConfig \
  tests.test_ai_kit_spec_gsd.TestResolveNativeTier \
  tests.test_ai_kit_spec_gsd.TestWriteNativeTierOverride \
  tests.test_ai_kit_spec_gsd.TestOverrideIsAdapterOwned \
  tests.test_ai_kit_spec_gsd.TestWriteActiveRuntime \
  tests.test_ai_kit_spec_gsd.TestSharedRunIdOneBackupAcrossWriteFunctions \
  tests.test_ai_kit_spec_gsd.TestResolveGsdConfigPath \
  tests.test_ai_kit_spec_gsd.TestWriteWorkflowKey \
  tests.test_ai_kit_spec_gsd.TestWorkflowKeyOwnershipAndClearing -v 2>&1 | tail -20
```

Expected: PASS.

- [ ] **Step 5: Register the new test module AND the new source directories with the repo's real quality gate (iteration-4 review finding 16)**

Edit `Makefile`'s `test:` target (currently ends `... tests.test_wizard_pty tests.test_system_memory_e2e tests.test_ai_kit_spec`) to append `tests.test_ai_kit_spec_gsd`.

Edit `.pre-commit-config.yaml`'s `unittest (core)` hook entry (currently ends `... tests.test_arch tests.test_ai_kit_spec`) to likewise append `tests.test_ai_kit_spec_gsd`.

The repository's REAL full quality gate is `make validate` (→ `uv run pre-commit run --all-files`,
confirmed by reading `Makefile`'s own `validate:` target), not a bare `python3 -m unittest` — and
its `ruff`/`py-compile` hooks are currently scoped by `files:` regex to `tools/`, `tests/`, and
`skills/ai-kit-spec-review/ai-kit-spec.py` only, which does NOT cover this plan's new source
directories. Edit `.pre-commit-config.yaml`'s `ruff` hook's `files:` regex from:
`^((tools|tests)/.*|skills/ai-kit-spec-review/ai-kit-spec-review)\.py$` to additionally match
`skills/ai-kit-spec-execute-gsd/.*\.py` and `skills/ai-kit-spec-execute/.*\.py` (e.g.
`^((tools|tests)/.*|skills/ai-kit-spec-review/ai-kit-spec-review|skills/ai-kit-spec-execute-gsd/.*|skills/ai-kit-spec-execute/.*)\.py$`).
Edit the `py-compile` hook's `files:` regex the same way, additionally including this plan's own
shim (`skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py`) and every `ai_kit_spec_gsd/*.py`/
`detect_framework.py` module. Task 6 Step 8 (the plan's final commit) runs `make validate` against
this expanded scope — see that task's revision.

- [ ] **Step 6: Commit `gsd_config.py`**

```bash
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add gsd_config.py (native tier + active-runtime + workflow-key read/write, ownership marker, per-run backups), register test module"
```

- [ ] **Step 7: Create the import-bootstrap shim `ai-kit-spec-gsd.py` (iteration-4 review finding 1)**

`skills/ai-kit-spec-review/ai-kit-spec.py` (the Foundation shim this mirrors) is a 7-line script:
running `python3 <that path> <subcommand>` relies on a plain fact about how Python starts a
script — it puts the SCRIPT'S OWN DIRECTORY on `sys.path[0]` automatically, before any of its own
`import` lines run, regardless of the caller's cwd. That is what makes `from ai_kit_spec.cli
import main` resolve inside that shim: `ai_kit_spec/` is a sibling directory of the shim itself.
This plan's `ai_kit_spec_gsd` package needs the EXACT SAME trick, PLUS one more line: unlike
`ai_kit_spec`, `ai_kit_spec_gsd`'s own modules (`adapter.py`, `gsd_cross_ai.py`, `cli.py`,
`cross_ai_wrapper.py`) do `from ai_kit_spec... import ...` (Foundation, a SIBLING skill directory,
not a sibling of `ai_kit_spec_gsd` itself) — so the shim must ALSO insert
`skills/ai-kit-spec-review/` onto `sys.path` before importing anything from `ai_kit_spec_gsd`.

Create `skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py`:

```python
#!/usr/bin/env python3
"""Entrypoint shim for ai-kit-spec-execute-gsd -- mirrors skills/ai-kit-spec-review/ai-kit-spec.py's
own trick (Python puts a directly-run script's OWN directory on sys.path[0] automatically, making
ai_kit_spec_gsd importable regardless of the caller's cwd), PLUS explicitly inserts the SIBLING
skills/ai-kit-spec-review/ directory onto sys.path so ai_kit_spec_gsd's own `from ai_kit_spec...`
imports resolve too (ai_kit_spec_gsd depends on Foundation's ai_kit_spec package, which is not
inside this script's own directory). This is the ONLY thing SKILL.md ever invokes by absolute
path (Task 5) -- and the SAME file GSD itself shells out to for Branch A's cross_ai_command hook
(Task 3), since GSD runs that command from an arbitrary, unknown cwd with no guarantee
ai_kit_spec_gsd is importable any other way.

Usage: python3 <this file> resolve-dispatch ...      -> ai_kit_spec_gsd.cli.main
       python3 <this file> config-path ...            -> ai_kit_spec_gsd.cli.main
       python3 <this file> cross-ai-wrapper --cli ...  -> ai_kit_spec_gsd.cross_ai_wrapper.main
       (every other ai_kit_spec_gsd.cli subcommand, same dispatch)"""
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, "..", "ai-kit-spec-review"))

if len(sys.argv) > 1 and sys.argv[1] == "cross-ai-wrapper":
    from ai_kit_spec_gsd.cross_ai_wrapper import main
    sys.exit(main(sys.argv[2:]))
else:
    from ai_kit_spec_gsd.cli import main
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 8: Prove the shim's `sys.path` wiring resolves BOTH packages from OUTSIDE the repository — WITHOUT invoking `cli.py` (it doesn't exist until Task 4)**

**iteration-6 review, CRITICAL finding, two independent reviewers**: an earlier revision of this
step ran `python3 <shim> resolve-dispatch ...`, but the shim's `else` branch always does
`from ai_kit_spec_gsd.cli import main` — and `ai_kit_spec_gsd/cli.py` is not created until Task 4
Step 8, two tasks after this one. Running that command here would raise
`ModuleNotFoundError: No module named 'ai_kit_spec_gsd.cli'` even with perfectly correct
`sys.path` wiring, which is exactly the failure this step's own old text told the implementer to
interpret as "the shim's wiring is wrong" — sending them to debug code that was never broken.

This step proves ONLY what Task 2 can actually prove at this point in the sequence: that the
shim's `sys.path` insertion makes BOTH `ai_kit_spec_gsd` (this plan's own package, which exists —
`gsd_config.py` was created in Step 1) and `ai_kit_spec` (Foundation's package, a sibling of the
shim inserted onto `sys.path` in the shim itself) importable from a directory provably outside
this repo's own tree — without touching `cli.py`. The end-to-end `resolve-dispatch` proof (a real
subcommand invocation from outside the repo) happens later, in Task 4 Step 9, once `cli.py`
actually exists.

```bash
SCRATCH_DIR="$(mktemp -d)"
cd "$SCRATCH_DIR" && python3 -c "
import sys
sys.path.insert(0, '/absolute/path/to/skills/ai-kit-spec-execute-gsd')
sys.path.insert(0, '/absolute/path/to/skills/ai-kit-spec-review')
import ai_kit_spec_gsd
import ai_kit_spec
print('both packages imported OK from', __import__('os').getcwd())
"
```

Expected: `both packages imported OK from <SCRATCH_DIR>` — no `ModuleNotFoundError`. This proves
the two `sys.path` insertion lines the shim performs are individually correct; it does not invoke
the shim script itself (that requires a real subcommand, which requires `cli.py`).

- [ ] **Step 9: Commit the shim**

```bash
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add ai-kit-spec-gsd.py import-bootstrap shim, verified importable from outside the repo"
```

---

### Task 3: `gsd_cross_ai.py` (+ Branch A's `cross_ai_wrapper.py`) — branch A (general hook) OR branch B (closed enum), per Task 1's finding

**Files:**
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_cross_ai.py`
- Create (Branch A only): `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cross_ai_wrapper.py`
- Test: `tests/test_ai_kit_spec_gsd.py`

**Interfaces:**
- Consumes: `ai_kit_spec.commands.build_execute_command` (Plan 1), `ai_kit_spec.dispatch.dispatch_with_heartbeat` (Plan 1, Branch A's wrapper only), `ai_kit_spec_gsd.gsd_config.NATIVE_TIER_VENDORS` (Task 2).
- Produces: `build_cross_ai_dispatch(resolved_candidate: dict, target_dir: str, ...) -> dict | None` — BRANCH-SPECIFIC signature (iteration-5 review finding 14 — a single shared signature previously claimed the same `execute_command_fn` parameter for both branches, but Branch B's real implementation never takes one; each branch's own Step 1A/1B and Step 3A/3B below states its own exact signature, which is authoritative over this line): returns a dispatch plan `{"mode": "cross_ai_hook", "cross_ai_command": str, "cli": str, "key": str, "model": str}` (Branch A) or `{"mode": "native_enum", "provider": str, "message": str, "cli": str, "key": str, "model": str}` (Branch B) or `None` when cross-provider dispatch isn't usable for this candidate at all (caller falls back to Task 4's native-tier/fallback path). `target_dir` is the real, already-resolved project/worktree directory the execute command must confine writes to — no caller of this function ever leaves a literal `{target_dir}` placeholder unfilled. (`gsd_config` was dropped from this signature — Branch A/B's logic never actually reads it; see MEDIUM-severity note removed by this revision.) **`cli`/`key`/`model` are always the SELECTED CANDIDATE's own values** (`resolved_candidate["cli"]`/`["key"]`/`["model"]`, copied through verbatim, never re-derived) — iteration-4 review finding 4: every dispatch-result shape this task and Task 4 produce must carry enough provenance for Task 5's tool-detection step to know which CLI it's preparing guidance for, since none of these dicts otherwise expose it.

This task's implementation body is written AFTER Task 1 completes, using whichever branch below
matches Task 1's recorded finding. Both branches are specified now so the plan is complete
regardless of outcome — the implementer picks the one matching Task 1's Step 5 finding and
deletes the other branch's tests/code from this task, never implements both.

**Branch A — if Task 1 confirms `cross_ai_command` is a general shell-command hook:**

GSD itself will execute whatever string `cross_ai_command` holds and read that command's raw
stdout as the candidate's summary (per Task 1 Step 3's confirmed output contract — update this
paragraph if the real contract differs). See finding 4's revised Step 1.5 (Task 7) for how this
branch's real (non-native) dispatch path is eventually proven against a real external CLI, not
just this task's own injected-fake-builder plumbing tests. That means the string this branch produces cannot be
the bare CLI invocation (e.g. `codex exec ...`) — it must be a self-contained wrapper program
that: (1) receives GSD's own phase prompt on **its** stdin exactly as GSD delivers it, (2) drives
the real dispatch through `ai_kit_spec.dispatch.dispatch_with_heartbeat` so timeout/process-group
kill/deadlock-safety are inherited for free, (3) sends heartbeat lines to **stderr**, never stdout
(GSD only reads stdout as the summary — a heartbeat line leaking into stdout would corrupt it),
(4) writes ONLY the dispatched CLI's own stdout to the wrapper's real stdout on success, and (5)
exits with a classifiable status: `0` on success, the dispatched command's own nonzero exit code
on a real failure, so GSD (and Task 5 Step 4's classifier) can tell success from failure without
parsing prose. `cross_ai_wrapper.py` (below) is that program; `build_cross_ai_dispatch` returns
the exact command line that invokes it with `cli`/`model`/`target_dir` already baked in as
argv — never as an unfilled template GSD would have to substitute into (GSD does not do template
substitution on this string at all).

- [ ] **Step 1A: Write the failing tests**

Add this import line to the shared test file, directly above the test class below (iteration-5
review finding 1 -- `gsd_cross_ai.py` doesn't exist yet at this point; Step 2A's "Expected: FAIL
-- module not found" IS this import line failing. Task 2's own `from ai_kit_spec_gsd import
gsd_config` line, already in the file, is untouched):

```python
from ai_kit_spec_gsd import gsd_cross_ai


class TestBuildCrossAiDispatchGeneralHook(unittest.TestCase):
    def test_vendor_already_in_native_tier_set_returns_none(self):
        # already reachable via native tiering -- cross_ai hook is unnecessary overhead
        candidate = {"cli": "claude", "model": "claude-opus-5", "key": "claude/claude-opus-5"}
        self.assertIsNone(gsd_cross_ai.build_cross_ai_dispatch(candidate, "/repo"))

    def test_no_live_verified_builder_returns_none_not_raise(self):
        # REAL current behavior: grok has no execute-mode builder yet -- Foundation's real
        # ai_kit_spec.commands.build_execute_command raises ValueError for it. This must
        # degrade to None (caller falls back to Task 4's fallback_notice), never raise or crash.
        candidate = {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast"}
        self.assertIsNone(gsd_cross_ai.build_cross_ai_dispatch(candidate, "/repo"))

    def test_builds_wrapper_invocation_with_real_target_dir_when_a_builder_exists(self):
        # Injected fake builder -- exercises this module's plumbing without depending on which
        # CLIs Foundation has actually implemented today (currently only "codex", which is
        # excluded by the native-tier check above and so can never reach this path for a real
        # candidate until Foundation demotes it out of NATIVE_TIER_VENDORS or ships another
        # execute builder). This is what makes the branch forward-compatible: as Foundation adds
        # real builders, this function picks them up automatically with no adapter change.
        seen_calls = []
        def fake_execute_command(cli, target_dir):
            seen_calls.append((cli, target_dir))
            return "future-cli exec --write -C {target_dir} -m {model}"
        candidate = {"cli": "future-cli", "model": "gpt-5.6-terra",
                     "key": "future-cli/gpt-5.6-terra"}
        result = gsd_cross_ai.build_cross_ai_dispatch(candidate, "/repo/worktree",
                                                        execute_command_fn=fake_execute_command)
        self.assertEqual(result["mode"], "cross_ai_hook")
        # the REAL target_dir, not a literal "{target_dir}" placeholder GSD would have to fill:
        self.assertIn("/repo/worktree", result["cross_ai_command"])
        self.assertNotIn("{target_dir}", result["cross_ai_command"])
        # Invokes the ai-kit-spec-gsd.py SHIM's "cross-ai-wrapper" subcommand (iteration-4 review
        # finding 1) -- NOT `python3 -m ai_kit_spec_gsd.cross_ai_wrapper`, which only resolves
        # when ai_kit_spec_gsd already happens to be on sys.path (never guaranteed: GSD shells
        # this command out from an arbitrary, unknown cwd, same reason the shim exists at all).
        self.assertIn("ai-kit-spec-gsd.py", result["cross_ai_command"])
        self.assertIn("cross-ai-wrapper", result["cross_ai_command"])
        self.assertNotIn("-m ai_kit_spec_gsd.cross_ai_wrapper", result["cross_ai_command"])
        self.assertIn("future-cli", result["cross_ai_command"])
        self.assertIn("gpt-5.6-terra", result["cross_ai_command"])
        # Provenance fields (iteration-4 review finding 4) -- Task 4/Task 5 need these to know
        # which CLI/candidate this dispatch decision actually selected.
        self.assertEqual(result["cli"], "future-cli")
        self.assertEqual(result["key"], "future-cli/gpt-5.6-terra")
        self.assertEqual(result["model"], "gpt-5.6-terra")
```

- [ ] **Step 2A: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestBuildCrossAiDispatchGeneralHook -v 2>&1 | tail -20
```

Expected: FAIL — module not found.

- [ ] **Step 3A: Implement** `gsd_cross_ai.py` (exact wrapper invocation args match `cross_ai_wrapper.py`'s
  own argparse definition below — write both together)

```python
"""Cross-provider dispatch via GSD's cross_ai_command hook -- confirmed a general shell-command
hook by Task 1's live spike (see this plan's Task 1, Step 5 finding).

REAL CONSTRAINT (confirmed against the actual shipped Foundation code, not the design spec's
original assumption): ai_kit_spec.commands.build_execute_command has exactly ONE working
execute-mode builder today -- codex. cursor-agent and opencode were live-tested and failed real
write confinement (demoted, see commands.py's _EXECUTE_COMMAND_BUILDERS comment); grok and
claude were never implemented. Every one of those four raises ValueError. Since codex is also in
NATIVE_TIER_VENDORS (already reachable without this hook at all), this branch has NO candidate
today for which it produces a live dispatch -- it always returns None until Foundation ships
more execute-mode builders. This is correct, honest behavior (never attempt an unverified
invocation, design spec §12), not a bug: the plumbing is exercised in tests by injecting a fake
`execute_command_fn`, verified independent of how many real builders exist yet.

The wrapper is invoked through the ai-kit-spec-gsd.py import-bootstrap SHIM (Task 2 Steps 7-9),
never via `python3 -m ai_kit_spec_gsd.cross_ai_wrapper` -- GSD shells `cross_ai_command` out from
an arbitrary, unknown cwd with no guarantee `ai_kit_spec_gsd` is importable any other way
(iteration-4 review finding 1), the exact problem the shim exists to solve."""
import os
import shlex

from ai_kit_spec.commands import build_execute_command
from ai_kit_spec_gsd.gsd_config import NATIVE_TIER_VENDORS

# skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_cross_ai.py -> skills/ai-kit-spec-execute-gsd/
# -> skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py (the shim, a sibling of ai_kit_spec_gsd/).
_SHIM_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai-kit-spec-gsd.py")


def build_cross_ai_dispatch(resolved_candidate: dict, target_dir: str,
                             execute_command_fn=build_execute_command):
    if resolved_candidate["cli"] in NATIVE_TIER_VENDORS:
        return None
    try:
        execute_command_fn(resolved_candidate["cli"], target_dir=target_dir)
    except ValueError:
        return None  # no live-verified execute-mode builder for this CLI yet -- decline, don't guess
    # The wrapper (cross_ai_wrapper.py, invoked via the shim's "cross-ai-wrapper" subcommand)
    # re-derives the real command itself from cli/model/target_dir at run time -- this module
    # only proves a builder exists for this cli right now (fail fast, before ever writing an
    # unusable command into GSD's config) and hands the wrapper everything it needs as plain
    # argv, never as a template GSD must fill in.
    wrapper_cmd = (
        f"python3 {shlex.quote(_SHIM_PATH)} cross-ai-wrapper "
        f"--cli {shlex.quote(resolved_candidate['cli'])} "
        f"--model {shlex.quote(resolved_candidate['model'])} "
        f"--target-dir {shlex.quote(target_dir)}"
    )
    return {"mode": "cross_ai_hook", "cross_ai_command": wrapper_cmd,
            "cli": resolved_candidate["cli"], "key": resolved_candidate["key"],
            "model": resolved_candidate["model"]}
```

- [ ] **Step 4A: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestBuildCrossAiDispatchGeneralHook -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5A: Write the failing tests for `cross_ai_wrapper.py`**

This is the actual program `cross_ai_command` above invokes — it is what GSD shells out to, reads
GSD's phase prompt from **its own** stdin, and is the ONLY thing standing between
`dispatch_with_heartbeat` and GSD's stdout-is-the-summary contract.

Add this import line to the shared test file, directly above the test class below (iteration-5
review finding 1 -- `cross_ai_wrapper.py` doesn't exist until Step 7A, later in THIS SAME task,
implements it; Step 6A's "Expected: FAIL -- module not found" IS this import line failing. This
import is BRANCH A ONLY -- Branch B's own Step 1B below never adds it, since Branch B never
creates `cross_ai_wrapper.py` at all):

```python
from ai_kit_spec_gsd import cross_ai_wrapper


class TestCrossAiWrapperMain(unittest.TestCase):
    def test_success_writes_only_child_stdout_to_real_stdout_and_exits_zero(self):
        import io
        heartbeat_lines = []
        def fake_dispatch(command, prompt, heartbeat_interval, timeout, print_fn=print):
            print_fn("[12:00:00] still running, 5s elapsed")  # must NOT reach real stdout
            return {"returncode": 0, "stdout": "PHASE SUMMARY: done.", "stderr": "",
                     "timed_out": False}
        stdout_buf, stderr_buf = io.StringIO(), io.StringIO()
        exit_code = cross_ai_wrapper.main(
            ["--cli", "future-cli", "--model", "gpt-5.6-terra", "--target-dir", "/repo/worktree"],
            stdin_read_fn=lambda: "the phase prompt text",
            dispatch_fn=fake_dispatch, execute_command_fn=lambda cli, target_dir: "future-cli run",
            stdout=stdout_buf, stderr=stderr_buf)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_buf.getvalue(), "PHASE SUMMARY: done.")
        self.assertNotIn("still running", stdout_buf.getvalue())  # heartbeat never leaks to stdout
        self.assertIn("still running", stderr_buf.getvalue())     # heartbeat goes to stderr instead

    def test_failure_propagates_child_returncode_and_diagnostic_to_stderr(self):
        import io
        def fake_dispatch(command, prompt, heartbeat_interval, timeout, print_fn=print):
            return {"returncode": 17, "stdout": "", "stderr": "usage limit exceeded",
                     "timed_out": False}
        stdout_buf, stderr_buf = io.StringIO(), io.StringIO()
        exit_code = cross_ai_wrapper.main(
            ["--cli", "future-cli", "--model", "gpt-5.6-terra", "--target-dir", "/repo/worktree"],
            stdin_read_fn=lambda: "the phase prompt text",
            dispatch_fn=fake_dispatch, execute_command_fn=lambda cli, target_dir: "future-cli run",
            stdout=stdout_buf, stderr=stderr_buf)
        self.assertEqual(exit_code, 17)
        self.assertEqual(stdout_buf.getvalue(), "")  # never claim success on stdout for a failure
        self.assertIn("usage limit exceeded", stderr_buf.getvalue())
```

- [ ] **Step 6A: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestCrossAiWrapperMain -v 2>&1 | tail -20
```

Expected: FAIL — module not found.

- [ ] **Step 7A: Implement `cross_ai_wrapper.py`**

```python
"""The actual program GSD's cross_ai_command hook shells out to (see gsd_cross_ai.py's
build_cross_ai_dispatch). Reads GSD's own phase prompt from stdin, dispatches through
ai_kit_spec.dispatch.dispatch_with_heartbeat (heartbeat routed to stderr, never stdout -- GSD
reads this program's stdout as the whole phase summary, per Task 1 Step 3's confirmed contract),
and exits with a status GSD/Task 5 Step 4 can classify: 0 on success, the dispatched command's
own nonzero return code on failure -- never swallowed into a generic 1."""
import argparse
import sys

from ai_kit_spec.commands import build_execute_command
from ai_kit_spec.dispatch import dispatch_with_heartbeat

HEARTBEAT_INTERVAL_SECONDS = 30
DISPATCH_TIMEOUT_SECONDS = 1800  # 30 min -- matches this plan's Task 5 Step 3 default


def main(argv: list, stdin_read_fn=sys.stdin.read, dispatch_fn=dispatch_with_heartbeat,
         execute_command_fn=build_execute_command, stdout=sys.stdout, stderr=sys.stderr) -> int:
    parser = argparse.ArgumentParser(prog="cross_ai_wrapper")
    parser.add_argument("--cli", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--target-dir", required=True)
    args = parser.parse_args(argv)

    prompt = stdin_read_fn()
    command_template = execute_command_fn(args.cli, target_dir=args.target_dir)
    command = command_template.format(model=args.model)

    def _heartbeat_to_stderr(msg):
        print(msg, file=stderr)

    result = dispatch_fn(command, prompt, HEARTBEAT_INTERVAL_SECONDS, DISPATCH_TIMEOUT_SECONDS,
                          print_fn=_heartbeat_to_stderr)
    if result["timed_out"] or result["returncode"] != 0:
        print(result["stderr"] or result["stdout"] or "cross-AI dispatch failed with no output",
              file=stderr)
        return result["returncode"] if result["returncode"] else 1
    stdout.write(result["stdout"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 8A: Run tests to verify pass, commit**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestBuildCrossAiDispatchGeneralHook \
  tests.test_ai_kit_spec_gsd.TestCrossAiWrapperMain -v 2>&1 | tail -10
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add gsd_cross_ai.py + cross_ai_wrapper.py (general-hook cross-provider dispatch with real target_dir, heartbeat-safe stdout)"
```

**Branch B — if Task 1 confirms `cross_ai_command` is a closed enum:**

`_CLOSED_ENUM_PROVIDERS` in this branch's implementation MUST be populated directly from Task 1
Step 5's recorded finding — it ships EMPTY only if Task 1 actually confirmed the enum has zero
members reachable from this adapter's own candidate set (an unlikely but possible outcome worth
recording explicitly if it happens). An empty set here with no accompanying note in Task 1's
finding explaining why is a plan defect, not a conservative default — do not implement this
branch by copying the empty-set scaffold below without first checking Task 1's recorded value
set and inserting every member it confirmed.

- [ ] **Step 1B: Write the failing tests**

```python
# LITERAL, hand-transcribed copy of Task 1 Step 5's recorded closed-enum member set -- e.g.
# EXPECTED_CLOSED_ENUM_PROVIDERS = {"cursor", "gemini", "claude"}. Transcribe this from the
# actual recorded finding when implementing this branch; do NOT leave it equal to
# gsd_cross_ai._CLOSED_ENUM_PROVIDERS by construction (iteration-4 review finding 15: a test that
# only iterates the implementation's OWN set passes vacuously if that set ships empty by
# accident -- this constant is this test file's independent source of truth, transcribed by a
# human reading Task 1's finding, not derived from the code under test).
EXPECTED_CLOSED_ENUM_PROVIDERS = {"REPLACE", "WITH", "TASK-1S-RECORDED-SET"}

# Import added here, directly above the test class below (iteration-5 review finding 1 --
# gsd_cross_ai.py doesn't exist yet at this point; Step 2B's "Expected: FAIL -- module not found"
# IS this import line failing). Branch B never adds a `cross_ai_wrapper` import -- this branch
# never creates that module at all (only Branch A's Step 5A does, conditionally).
from ai_kit_spec_gsd import gsd_cross_ai


class TestBuildCrossAiDispatchClosedEnum(unittest.TestCase):
    def test_closed_enum_providers_constant_matches_task_1s_recorded_finding_exactly(self):
        self.assertEqual(gsd_cross_ai._CLOSED_ENUM_PROVIDERS, EXPECTED_CLOSED_ENUM_PROVIDERS)

    def test_recognizes_every_task_1_confirmed_provider(self):
        # Iterates the LITERAL constant above, never gsd_cross_ai._CLOSED_ENUM_PROVIDERS itself --
        # an empty implementation set must fail the previous test, not pass this one vacuously.
        for provider in EXPECTED_CLOSED_ENUM_PROVIDERS:
            candidate = {"cli": provider, "model": "m-1", "key": f"{provider}/m-1"}
            result = gsd_cross_ai.build_cross_ai_dispatch(candidate, "/repo")
            self.assertEqual(result["mode"], "native_enum")
            self.assertEqual(result["provider"], provider)
            # native_enum is a coarse, precision-losing substitution -- callers (Task 4/5) must
            # be able to surface WHY, not just that it happened:
            self.assertIn("message", result)
            self.assertTrue(result["message"])
            # Provenance fields (iteration-4 review finding 4):
            self.assertEqual(result["cli"], provider)
            self.assertEqual(result["key"], f"{provider}/m-1")
            self.assertEqual(result["model"], "m-1")

    def test_returns_none_for_a_provider_outside_the_confirmed_set(self):
        candidate = {"cli": "definitely-not-a-real-provider", "model": "m-1",
                     "key": "definitely-not-a-real-provider/m-1"}
        self.assertIsNone(gsd_cross_ai.build_cross_ai_dispatch(candidate, "/repo"))
```

- [ ] **Step 2B: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestBuildCrossAiDispatchClosedEnum -v 2>&1 | tail -20
```

Expected: FAIL — module not found.

- [ ] **Step 3B: Implement**

```python
"""Cross-provider dispatch via GSD's closed cross_ai_command enum -- confirmed a fixed provider
set, not a general hook, by Task 1's live spike (see this plan's Task 1, Step 5 finding).

_CLOSED_ENUM_PROVIDERS below MUST be populated from Task 1 Step 5's recorded finding before this
branch ships -- replace the placeholder set() with the exact confirmed member set (implementer:
do this before writing Step 1B's test, then make the test assert against the real set). Shipping
this empty with no corresponding "Task 1 confirmed zero usable members" note in the Step 5
finding is a plan defect, not the conservative "refuse rather than guess" default it looks like."""

_CLOSED_ENUM_PROVIDERS = set()  # REPLACE with Task 1 Step 5's exact confirmed member set


def build_cross_ai_dispatch(resolved_candidate: dict, target_dir: str):
    if resolved_candidate["cli"] not in _CLOSED_ENUM_PROVIDERS:
        return None
    provider = resolved_candidate["cli"]
    return {
        "mode": "native_enum",
        "provider": provider,
        "cli": resolved_candidate["cli"],
        "key": resolved_candidate["key"],
        "model": resolved_candidate["model"],
        "message": (
            f"Dispatching via GSD's native-runtime-enum for {provider!r} -- this is a coarse, "
            f"precision-losing substitution: GSD recognizes {provider!r} as a runtime identity, "
            f"not the specific model id {resolved_candidate['model']!r} ai-kit-spec-execute "
            f"selected. The actual model GSD runs is whatever {provider!r}'s own current default "
            f"is, not necessarily the one chosen here."
        ),
    }
```

- [ ] **Step 4B: Run tests to verify pass, commit**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestBuildCrossAiDispatchClosedEnum -v 2>&1 | tail -10
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add gsd_cross_ai.py (closed-enum cross-provider dispatch, precision-loss notice)"
```

---

### Task 4: Adapter — assemble candidates, resolve native/cross-AI dispatch with live quota, explicit fallback

**Files:**
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/adapter.py`
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py` (Step 6–9 below)
- Test: `tests/test_ai_kit_spec_gsd.py`

**Interfaces:**
- Consumes (split per module — iteration-6 review, MEDIUM finding, corrected here to name only what each module actually imports): `adapter.py` imports `ai_kit_spec.quota.resolve_ladder_pick` (Plan 1), `gsd_config.{resolve_active_runtime, write_native_tier_override, write_active_runtime, override_is_adapter_owned, read_gsd_config, NATIVE_TIER_VENDORS}` (Task 2), `gsd_cross_ai.build_cross_ai_dispatch` (Task 3). `cli.py` additionally imports `ai_kit_spec.quota.{refresh_quota_cache, QUOTA_TTL_SECONDS}`, `ai_kit_spec.config_io.cfg_resolve`, `ai_kit_spec.execute_selection.{resolve_execute_candidates, candidates_to_ladder}`, `ai_kit_spec.cache.{cache_read_json, cache_write_json}` (Plan 1). Neither module imports `gsd_config.resolve_native_tier` directly (iteration-5 review finding 10 removed the short-circuit that used to call it — `resolve_native_tier` remains a real, tested `gsd_config.py` export used only by `gsd_config`'s own internal callers) nor `ai_kit_spec.quota.cache_quota_path` (dead import removed — the quota cache path is resolved once by `cli.py`'s own `--quota-path` CLI flag, supplied by the caller, never re-derived internally). `adapter.py` does NOT import `ai_kit_spec.quota._UNAVAILABLE_SIGNALS` (a private, underscore-prefixed name) — it keeps its own local copy of the quota-class phrases instead (iteration-5 review finding 16, see `classify_dispatch_failure`'s own implementation below).
- Produces:
  - `estimate_required_context(phase_prompt: str) -> int` — a real, non-hardcoded estimate of the phase's own context footprint (`len(phase_prompt) // 4`, a standard rough chars-per-token heuristic), NOT curated per-candidate data (see Global Constraints' second scope-boundary bullet, iteration-4 review finding 3). Every candidate's `context_limit` is `None` today (no curation exists yet), so this estimate has no filtering effect through `execute_selection.filter_by_context` YET — it exists so the moment curated `context_limit` data ships, this plan's dispatch path honors it immediately, with zero code change here. `resolve_gsd_dispatch` (below) calls this on the real phase prompt instead of hardcoding `0`.
  - `assemble_candidates(cwd: str, env: dict, cfg_resolve_fn=cfg_resolve) -> tuple[list, list]` — returns `(candidates, top_n_keys)`. Reshapes `cfg_resolve_fn(cwd, env)["reviewers"]` entries (the same `key`/`model`/`vendor`/`cli`/`command` config surface the review family already reads — this plan does not invent a second config file) into `execute_selection`'s expected candidate shape, preserving `vendor` (needed by `quota.resolve_ladder_pick`'s own `entry.get("vendor")` check, below — omitting it would silently defeat that check's cross-vendor logic) AND **preserving `command` verbatim** (iteration-5 review finding 2, independently found by two reviewers — `ai_kit_spec.quota.refresh_quota_cache` → `probe_reviewer_quota` → `ai_kit_spec.commands.render_reviewer_command` raises `ValueError("has cli=… set but no command template")` for any `cli`-set entry with no `command`, which `probe_reviewer_quota` converts to `{"available": False, ...}` — dropping `command` here would make every `cli`-set candidate probe unavailable on every real run, regardless of its actual quota). `task_affinity`/`context_limit` are read from the config entry when present (`r.get("task_affinity")`/`r.get("context_limit")` — **BOTH default to `None`, never `0`, when the field is genuinely absent** — iteration-6 review, CRITICAL finding, two independent reviewers: the real shipped `execute_selection.filter_by_context` treats `context_limit is None` as "unknown, pass through" but `context_limit == 0` as "confirmed insufficient," so a `0` default would make `filter_by_context` reject every candidate on any real (non-empty) phase prompt, since `estimate_required_context` is always positive for real text — this previously made every production dispatch fall through to `fallback_notice`, wrongly reported as "no configured candidate at all"). `execute_selection.filter_by_affinity`/`filter_by_context` both treat that honest `None` default as a documented no-op pass-through, so every entry that exists today (none curates `task_affinity`/`context_limit` yet) resolves through unaffected — but see Global Constraints' second scope-boundary bullet for why `task_affinity` curation, unlike `context_limit`, does NOT "activate with zero code change" (a hardcoded `task_type=None` filters OUT any candidate a future curation step tags). `top_n_keys` is `cfg_resolve_fn(cwd, env)["policy"]["ladder"]`.
  - `classify_dispatch_failure(stdout: str, stderr: str) -> str` — returns `"auth"` when the combined, lowercased output contains an entitlement/authentication phrase (`"actionrequirederror"`, `"not authenticated"`, `"not logged in"` — the SAME phrases inside `ai_kit_spec.quota._UNAVAILABLE_SIGNALS`, but classified separately here), `"quota"` when it contains a transient-limit phrase (`"usage limit"`, `"quota"`, `"rate limit"`, `"rate_limit"`) and no auth phrase, `"other"` otherwise. `_UNAVAILABLE_SIGNALS` itself is a single flat tuple mixing both classes (belt-and-suspenders for a quota probe that already has a nonzero exit code to key off) — Task 5 Step 4's classifier MUST call this function rather than testing membership in `_UNAVAILABLE_SIGNALS` directly, because an unqualified membership test would misclassify a persistent auth/entitlement failure as transient quota exhaustion and schedule a futile hourly auto-wake for it.
  - `resolve_gsd_dispatch(candidates: list, top_n_keys: list, phase_type: str, gsd_config: dict, gsd_config_path: str, target_dir: str, required_context: int = 0, quota: dict | None = None, exclude_keys: list | None = None, run_id: str | None = None, write_fn=write_native_tier_override, write_runtime_fn=write_active_runtime, resolve_ladder_pick_fn=resolve_ladder_pick) -> dict` — returns exactly one of:
    - `{"mode": "native_tier", "model": str, "written": bool, "cli": str | None, "key": str | None, "provenance": str}` — `written=False`/`provenance="existing_gsd_config"`/`key=None` when GSD's own config already has a genuine PER-PHASE `model_overrides[phase_type]` entry (iteration-5 review finding 10 — the short-circuit checks `model_overrides[phase_type]` specifically, NOT `resolve_native_tier`'s broader `model_overrides`→`models`→`model_profile` precedence, since `models`/`model_profile` are coarse project-WIDE defaults with no per-phase granularity — a project that only ever set one of those, with no per-phase `model_overrides` entry, must NOT permanently short-circuit selection for every phase type) AND that override is NOT adapter-owned (`gsd_config.override_is_adapter_owned` returns `False` — a genuine prior user choice, never overridden or re-derived). In this case `cli` is the ACTUAL configured runtime identity — `gsd_config.resolve_active_runtime(gsd_config) or "claude"` (never a fabricated/hardcoded `None` — iteration-5 review finding 10's second half: an unset `runtime` key still means "the current session", i.e. `"claude"`, design spec §6) — so Task 5 Step 3 prepares tooling guidance for the REAL runtime this phase will actually execute through, never assuming Claude by omission. When the existing override IS adapter-owned (a prior run of THIS adapter wrote it — iteration-4 review finding 6), resolution proceeds exactly as if nothing were configured, so a stale prior pick can be re-resolved against current quota rather than permanently pinning the project. `written=True`/`provenance="resolved_candidate"`/`cli`/`key` set to the winning candidate's own values when a live-quota-checked candidate is natively reachable (`cli` in `NATIVE_TIER_VENDORS`, OR `cli is None` — the current-runtime/native-dispatch case, see Global Constraints) and this call just persisted its model into `model_overrides` via `write_fn` — AND, whenever the winning candidate's `cli` differs from `gsd_config.resolve_active_runtime(gsd_config)`'s current value (or `cli is None`, treated as `"claude"` — the current session's own identity), also calls `write_runtime_fn` to switch GSD's active runtime to match (iteration-4 review finding 5 — a model override alone does not establish which vendor runtime executes it).
    - `{"mode": "cross_ai_hook" | "native_enum", "cli": str, "key": str, ...}` from Task 3 (already carries `cli`/`key`/`model`, see Task 3's revised Interfaces), when a live-quota-checked candidate isn't natively reachable but cross-AI dispatch can carry it.
    - `{"mode": "fallback_notice", "message": str}` when no live-quota-checked candidate (native, native-current-runtime, or cross-AI) can be carried at all — never fabricates a vendor it did not actually enforce; `message` explicitly states the original top choice, why every quota-available candidate was tried and failed, and that no configuration change was made (GSD's own currently-active default, whatever it is, will run unmodified). Also returned, with a distinct message, when `read_gsd_config`'s caller (Task 4's `cli.py`, below) found `status == "malformed"` — this function itself never reads config off disk, but its caller MUST short-circuit to an equivalent fallback rather than call this function with a config it knows is broken (iteration-4 review finding 7).
  - `resolve_gsd_dispatch` **live-quota-checks and escalates past more than just `ranked[0]`**: it walks `resolve_execute_candidates`'s ranked output (now passing `estimate_required_context`'s real value as `required_context`, never a hardcoded `0`) through `candidates_to_ladder` + `resolve_ladder_pick_fn` (never taking `ranked[0]` unconditionally, per `execute_selection.resolve_execute_candidates`'s own docstring: "this function only narrows and ranks, it never itself probes quota" — the caller MUST feed its output through `candidates_to_ladder()` into `quota.resolve_ladder_pick()`), and on finding a quota-available candidate that turns out to have no usable native/cross-AI dispatch path, removes it from the ladder and retries the NEXT quota-available candidate, so a later native-reachable candidate is never blocked by an earlier unusable external one. **`exclude_keys`** (iteration-4 review finding 2) is folded into the effective `quota` dict BEFORE the ladder walk (each key in it is forced to `{"available": False, "detail": "excluded: prior runtime dispatch attempt in this same wave failed with a quota signal"}`, overriding whatever the real probe-based `quota` dict said) — this is how Task 5's SKILL.md escalates past a candidate whose PROBE said available but whose REAL dispatch attempt then hit a live quota wall, without a second, separate resolution function.

- [ ] **Step 1: Write the failing tests**

Add this import line to the shared test file, directly above the test classes below (iteration-5
review finding 1 -- `adapter.py` doesn't exist until Step 3, later in THIS SAME task, implements
it; Step 2's "Expected: FAIL -- module not found" IS this import line failing. By this point in
the sequence, `gsd_config` (Task 2) and `gsd_cross_ai` (Task 3) already exist and are already
imported earlier in the file -- this adds only the one new name this task needs):

```python
from ai_kit_spec_gsd import adapter


class TestAssembleCandidates(unittest.TestCase):
    def test_reshapes_cfg_reviewers_into_candidate_shape_with_open_risk_fields_none(self):
        def fake_cfg_resolve(cwd, env):
            return {"policy": {"ladder": ["codex/gpt-5.6-sol", "claude/opus-5"]},
                    "reviewers": [{"key": "codex/gpt-5.6-sol", "model": "gpt-5.6-sol",
                                    "vendor": "openai", "cli": "codex"}]}
        candidates, top_n_keys = adapter.assemble_candidates(
            "/repo", {}, cfg_resolve_fn=fake_cfg_resolve)
        self.assertEqual(candidates, [{"key": "codex/gpt-5.6-sol", "model": "gpt-5.6-sol",
                                        "cli": "codex", "vendor": "openai", "command": None,
                                        "task_affinity": None, "context_limit": None}])
        self.assertEqual(top_n_keys, ["codex/gpt-5.6-sol", "claude/opus-5"])

    def test_preserves_command_and_curated_task_affinity_context_limit_when_present(self):
        # iteration-5 review finding 2: `command` MUST survive into the candidate shape, or
        # every cli-set candidate probes unavailable purely from a missing template, regardless
        # of real quota. iteration-5 review finding 12: task_affinity/context_limit must be read
        # from the config entry, not hardcoded, so a future curated entry activates with zero
        # code change here.
        def fake_cfg_resolve(cwd, env):
            return {"policy": {"ladder": ["codex/gpt-5.6-sol"]},
                    "reviewers": [{"key": "codex/gpt-5.6-sol", "model": "gpt-5.6-sol",
                                    "vendor": "openai", "cli": "codex",
                                    "command": "codex exec -m {model} -- {prompt}",
                                    "task_affinity": "backend", "context_limit": 128000}]}
        candidates, _ = adapter.assemble_candidates("/repo", {}, cfg_resolve_fn=fake_cfg_resolve)
        self.assertEqual(candidates[0]["command"], "codex exec -m {model} -- {prompt}")
        self.assertEqual(candidates[0]["task_affinity"], "backend")
        self.assertEqual(candidates[0]["context_limit"], 128000)


class TestEstimateRequiredContext(unittest.TestCase):
    def test_estimates_a_real_nonzero_value_from_the_actual_phase_prompt(self):
        # Not hardcoded 0 (iteration-4 review finding 3) -- a real, if approximate, measurement
        # of the phase's own size, so a future curated context_limit has something honest to
        # filter against instead of a permanently-inert placeholder.
        prompt = "x" * 4000
        self.assertEqual(adapter.estimate_required_context(prompt), 1000)

    def test_empty_prompt_estimates_zero(self):
        self.assertEqual(adapter.estimate_required_context(""), 0)


class TestClassifyDispatchFailure(unittest.TestCase):
    def test_auth_signal_classified_auth_even_with_quota_word_also_present(self):
        # "quota" appears in an ActionRequiredError message in the wild -- auth must win, since
        # it is the persistent, never-retry-worthy failure class.
        self.assertEqual(
            adapter.classify_dispatch_failure(
                "", "ActionRequiredError: Named models unavailable, upgrade your quota plan."),
            "auth")

    def test_pure_quota_signal_classified_quota(self):
        self.assertEqual(adapter.classify_dispatch_failure("", "usage limit exceeded"), "quota")

    def test_unrelated_failure_classified_other(self):
        self.assertEqual(adapter.classify_dispatch_failure("", "connection refused"), "other")


class TestResolveGsdDispatch(unittest.TestCase):
    def test_native_tier_wins_unwritten_when_gsd_already_configures_this_phase_type(self):
        # No _ai_kit_spec_execute_gsd ownership marker present -- a genuine prior user choice,
        # never overridden. No "runtime" key set -- resolve_active_runtime returns None, so the
        # honest default reported here is "claude" (iteration-5 review finding 10: never a
        # fabricated/hardcoded cli=None -- an unset runtime key still means "the current
        # session").
        gsd_config = {"model_overrides": {"backend": "claude-opus-5"}}
        result = adapter.resolve_gsd_dispatch([], [], "backend", gsd_config,
                                               "/repo/.planning/config.json", "/repo")
        self.assertEqual(result, {"mode": "native_tier", "model": "claude-opus-5",
                                    "written": False, "cli": "claude", "key": None,
                                    "provenance": "existing_gsd_config"})

    def test_native_tier_existing_config_reports_the_real_configured_runtime_identity(self):
        # iteration-5 review finding 10 (second half): when the existing-config short-circuit
        # fires against a project that ALREADY has a non-claude runtime active, the result must
        # name that REAL runtime, not silently default to "claude" -- SKILL.md prepares
        # tooling guidance for whatever this field says, and a wrong answer here would prepare
        # Claude-flavored guidance for a phase that actually runs through codex.
        gsd_config = {"model_overrides": {"backend": "gpt-5.6-sol"}, "runtime": "codex"}
        result = adapter.resolve_gsd_dispatch([], [], "backend", gsd_config,
                                               "/repo/.planning/config.json", "/repo")
        self.assertEqual(result["cli"], "codex")

    def test_project_wide_model_profile_alone_does_not_permanently_short_circuit_selection(self):
        # iteration-5 review finding 10: model_profile/models are coarse PROJECT-WIDE defaults
        # with no per-phase granularity -- unlike a genuine per-phase model_overrides[phase_type]
        # entry, they must NOT make the existing-config short-circuit fire, or a project that only
        # ever set a project-wide default would make this adapter permanently inert for EVERY
        # phase type, forever.
        gsd_config = {"model_profile": "codex-tier-1"}
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None}]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], "backend", gsd_config,
            "/repo/.planning/config.json", "/repo", write_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {})
        # Selection logic actually ran (not short-circuited) -- the candidate ladder resolved a
        # real pick instead of returning the inert existing_gsd_config provenance.
        self.assertEqual(result["provenance"], "resolved_candidate")

    def test_adapter_owned_existing_override_is_re_resolved_not_treated_as_fixed(self):
        # iteration-4 review finding 6: an override THIS ADAPTER wrote on a prior run must be
        # re-resolvable against current quota, not permanently pinned as if a user set it.
        gsd_config = {
            "model_overrides": {"backend": "stale-model"},
            "_ai_kit_spec_execute_gsd": {"overrides": {"backend": "stale-model"}},
        }
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None}]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], "backend", gsd_config,
            "/repo/.planning/config.json", "/repo",
            write_fn=lambda *a, **k: {}, write_runtime_fn=lambda *a, **k: {})
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")
        self.assertTrue(result["written"])

    def test_writes_native_tier_and_active_runtime_when_top_candidate_is_native_vendor(self):
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None}]
        written, runtime_written = {}, {}
        def fake_write(path, gsd_config, phase_type, model, **kw):
            written["args"] = (path, gsd_config, phase_type, model)
            return {**gsd_config, "model_overrides": {phase_type: model}}
        def fake_write_runtime(path, gsd_config, runtime, **kw):
            runtime_written["args"] = (path, gsd_config, runtime)
            return {**gsd_config, "runtime": runtime}
        result = adapter.resolve_gsd_dispatch(candidates, ["codex/gpt-5.6-sol"], "backend", {},
                                               "/repo/.planning/config.json", "/repo",
                                               write_fn=fake_write,
                                               write_runtime_fn=fake_write_runtime)
        self.assertEqual(result, {"mode": "native_tier", "model": "gpt-5.6-sol",
                                    "written": True, "cli": "codex", "key": "codex/gpt-5.6-sol",
                                    "provenance": "resolved_candidate"})
        # Write-ordering contract (iteration-5 review finding 3): the runtime write happens
        # FIRST, and its OWN returned dict is threaded into the model-override write's
        # gsd_config argument -- never the stale pre-runtime-write snapshot. Two writes against
        # the same stale dict would have the second silently discard the first's key (the same
        # principle write_workflow_key's own threading contract already states, Task 2's
        # Interfaces block). fake_write_runtime's own return value is {**gsd_config, "runtime":
        # runtime} = {"runtime": "codex"} here (gsd_config was {} going in), so that -- not the
        # original {} -- is what write_fn must receive.
        self.assertEqual(runtime_written["args"],
                          ("/repo/.planning/config.json", {}, "codex"))
        self.assertEqual(written["args"],
                          ("/repo/.planning/config.json", {"runtime": "codex"}, "backend",
                           "gpt-5.6-sol"))

    def test_does_not_rewrite_active_runtime_when_it_already_matches_the_candidate(self):
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None}]
        runtime_written = {"called": False}
        def fake_write_runtime(*a, **kw):
            runtime_written["called"] = True
            return {}
        adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], "backend", {"runtime": "codex"},
            "/repo/.planning/config.json", "/repo", write_fn=lambda *a, **k: {},
            write_runtime_fn=fake_write_runtime)
        self.assertFalse(runtime_written["called"])

    def test_native_no_cli_candidate_resolves_to_native_tier_with_claude_as_active_runtime(self):
        # cli=None is the "opus-native"-shaped entry this repo's own review-spec.toml ships --
        # native/current-runtime dispatch, reachable exactly like a NATIVE_TIER_VENDORS entry.
        # Its vendor identity for runtime-switching purposes is "claude" -- the current session's
        # own identity (design spec §6: a Claude-tier candidate dispatches in-process).
        candidates = [{"cli": None, "model": "opus", "key": "opus-native", "vendor": "",
                       "task_affinity": None, "context_limit": None}]
        written, runtime_written = {}, {}
        def fake_write(path, gsd_config, phase_type, model, **kw):
            written["args"] = (path, gsd_config, phase_type, model)
            return {**gsd_config, "model_overrides": {phase_type: model}}
        def fake_write_runtime(path, gsd_config, runtime, **kw):
            runtime_written["args"] = (path, gsd_config, runtime)
            return {**gsd_config, "runtime": runtime}
        result = adapter.resolve_gsd_dispatch(candidates, ["opus-native"], "backend", {},
                                               "/repo/.planning/config.json", "/repo",
                                               write_fn=fake_write,
                                               write_runtime_fn=fake_write_runtime)
        self.assertEqual(result, {"mode": "native_tier", "model": "opus", "written": True,
                                    "cli": None, "key": "opus-native",
                                    "provenance": "resolved_candidate"})
        self.assertEqual(runtime_written["args"][2], "claude")

    @mock.patch("ai_kit_spec_gsd.adapter.build_cross_ai_dispatch")
    def test_falls_through_to_cross_ai_when_top_candidate_not_native(self, mock_build):
        mock_build.return_value = {
            "mode": "cross_ai_hook", "cross_ai_command": "python3 .../ai-kit-spec-gsd.py ...",
            "cli": "grok", "key": "grok/grok-4-fast", "model": "grok-4-fast"}
        candidates = [{"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast",
                       "vendor": "xai", "task_affinity": None, "context_limit": None}]
        result = adapter.resolve_gsd_dispatch(candidates, ["grok/grok-4-fast"], "backend", {},
                                               "/repo/.planning/config.json", "/repo")
        self.assertEqual(result["mode"], "cross_ai_hook")
        self.assertEqual(result["cli"], "grok")

    @mock.patch("ai_kit_spec_gsd.adapter.build_cross_ai_dispatch")
    def test_escalates_past_an_unusable_external_candidate_to_a_later_native_one(self, mock_build):
        # ranked[0] (grok) has no usable dispatch path at all -- build_cross_ai_dispatch returns
        # None for it -- so resolution must NOT stop there; it must escalate to ranked[1] (codex,
        # a NATIVE_TIER_VENDORS member) instead of producing fallback_notice prematurely. This is
        # the exact "only checks ranked[0]" defect this test guards against.
        mock_build.return_value = None
        candidates = [
            {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast", "vendor": "xai",
             "task_affinity": None, "context_limit": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None},
        ]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast", "codex/gpt-5.6-sol"], "backend", {},
            "/repo/.planning/config.json", "/repo", write_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {})
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_skips_a_candidate_with_no_quota_and_uses_the_next_one(self):
        candidates = [
            {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast", "vendor": "xai",
             "task_affinity": None, "context_limit": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None},
        ]
        quota = {"grok/grok-4-fast": {"available": False}}
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast", "codex/gpt-5.6-sol"], "backend", {},
            "/repo/.planning/config.json", "/repo", quota=quota, write_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {})
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_exclude_keys_forces_a_runtime_quota_failed_candidate_to_the_next_one(self):
        # iteration-4 review finding 2: a candidate whose PROBE said available but whose REAL
        # dispatch attempt then hit a live quota wall must be excludable within the same wave,
        # without a second resolution function -- exclude_keys is how Task 5's SKILL.md does
        # this on retry after a runtime (not probe-time) quota failure.
        candidates = [
            {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast", "vendor": "xai",
             "task_affinity": None, "context_limit": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None},
        ]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast", "codex/gpt-5.6-sol"], "backend", {},
            "/repo/.planning/config.json", "/repo", exclude_keys=["grok/grok-4-fast"],
            write_fn=lambda *a, **k: {}, write_runtime_fn=lambda *a, **k: {})
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_falls_back_with_explicit_reason_and_no_fabricated_vendor_when_nothing_can_carry_it(self):
        # real (unmocked) gsd_cross_ai.build_cross_ai_dispatch: grok is not in
        # NATIVE_TIER_VENDORS and has no live-verified execute builder -- returns None for real.
        candidates = [{"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast",
                       "vendor": "xai", "task_affinity": None, "context_limit": None}]
        result = adapter.resolve_gsd_dispatch(candidates, ["grok/grok-4-fast"], "backend", {},
                                               "/repo/.planning/config.json", "/repo")
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertNotIn("vendor", result)  # never a fabricated, unenforced vendor claim
        self.assertIn("grok/grok-4-fast", result["message"])
        self.assertIn("backend", result["message"])
        self.assertIn("no configuration change", result["message"].lower())

    def test_every_candidate_lacks_quota_at_initial_probe_time_falls_back(self):
        # iteration-5 review finding 2: this is the "still no quota anywhere in the ladder"
        # exhaustion case Task 5 Step 4's escalation loop must be able to tell apart from a
        # single candidate's RUNTIME dispatch failure (see
        # test_exclude_keys_forces_a_runtime_quota_failed_candidate_to_the_next_one above, which
        # covers the latter) -- here EVERY candidate is already unavailable at probe time, before
        # any dispatch is even attempted.
        candidates = [
            {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast", "vendor": "xai",
             "task_affinity": None, "context_limit": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None},
        ]
        quota = {"grok/grok-4-fast": {"available": False},
                 "codex/gpt-5.6-sol": {"available": False}}
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast", "codex/gpt-5.6-sol"], "backend", {},
            "/repo/.planning/config.json", "/repo", quota=quota)
        self.assertEqual(result["mode"], "fallback_notice")

    def test_real_nonempty_phase_prompt_with_uncurated_candidates_still_resolves(self):
        # iteration-6 review, CRITICAL finding (two independent reviewers): a prior revision
        # defaulted context_limit to 0 instead of None, which made execute_selection's real
        # filter_by_context reject every candidate whenever required_context was positive --
        # true for ANY real, non-empty phase prompt. This test uses a real prompt string (so
        # estimate_required_context returns something > 0, exactly like production) against
        # today's uncurated candidates (context_limit=None, the honest "no data yet" default)
        # and asserts a candidate is still resolved -- proving the None default's pass-through
        # behavior actually holds end-to-end, not just in isolated unit tests of filter_by_context.
        real_phase_prompt = "Implement the login form validation for the signup flow." * 20
        required_context = adapter.estimate_required_context(real_phase_prompt)
        self.assertGreater(required_context, 0)  # sanity: a real prompt always yields > 0
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None}]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], "backend", {}, "/repo/.planning/config.json",
            "/repo", quota={}, required_context=required_context)
        self.assertNotEqual(result["mode"], "fallback_notice")
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestAssembleCandidates \
  tests.test_ai_kit_spec_gsd.TestEstimateRequiredContext \
  tests.test_ai_kit_spec_gsd.TestClassifyDispatchFailure \
  tests.test_ai_kit_spec_gsd.TestResolveGsdDispatch -v 2>&1 | tail -50
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Top-level GSD adapter: assembles candidates from ai-kit-spec's own shared config surface,
then never silently drops the user's chosen model (design spec §7, §12): a live-quota-checked
native tiering pick wins if GSD already configures it (and is a genuine user choice, not this
adapter's own prior write -- see override_is_adapter_owned) or a ranked candidate is natively
reachable (including the native/current-runtime `cli=None` case, whose active-runtime identity is
"claude"), else cross-AI if reachable, escalating past any earlier quota-available-but-unusable OR
exclude_keys-forced candidate to the next one, else an honest fallback notice that makes no
unenforced vendor claim. Every native-tier write also confirms/switches GSD's own `runtime` key
so the model override actually takes effect against the right vendor (iteration-4 review finding
5) -- a model id alone does not select which CLI executes it."""
from ai_kit_spec.config_io import cfg_resolve
from ai_kit_spec.execute_selection import candidates_to_ladder, resolve_execute_candidates
from ai_kit_spec.quota import resolve_ladder_pick
from ai_kit_spec_gsd.gsd_config import (
    resolve_active_runtime, write_native_tier_override,
    write_active_runtime, override_is_adapter_owned, NATIVE_TIER_VENDORS,
)
from ai_kit_spec_gsd.gsd_cross_ai import build_cross_ai_dispatch

# _QUOTA_SIGNALS below is a LOCAL copy of the transient-limit phrases from
# ai_kit_spec.quota._UNAVAILABLE_SIGNALS's own quota-class members -- never imported directly
# (iteration-5 review finding 16: importing a private, underscore-prefixed name across a module
# boundary is a lint-flaggable, silently-driftable dependency on another package's internal
# constant). The canonical source of truth for these phrases is ai_kit_spec/quota.py's own
# _UNAVAILABLE_SIGNALS docstring/comment -- if that module ever adds/removes a quota-class phrase,
# update this tuple to match by hand; this module's own test suite
# (TestClassifyDispatchFailure) is what would catch a drift.
_AUTH_SIGNALS = ("actionrequirederror", "not authenticated", "not logged in")
_QUOTA_SIGNALS = ("usage limit", "quota", "rate limit", "rate_limit")


def classify_dispatch_failure(stdout: str, stderr: str) -> str:
    """auth/entitlement failures are persistent -- never schedule a quota-style auto-wake retry
    for them (design spec §12). Checked BEFORE quota signals since a real ActionRequiredError
    message can also happen to contain the word "quota" without being transient exhaustion."""
    combined = (stdout + stderr).lower()
    if any(s in combined for s in _AUTH_SIGNALS):
        return "auth"
    if any(s in combined for s in _QUOTA_SIGNALS):
        return "quota"
    return "other"


def estimate_required_context(phase_prompt: str) -> int:
    """A real, non-hardcoded estimate of the phase's own context footprint -- standard
    chars-per-token-4 heuristic. Every candidate's context_limit is None today (no curation
    exists yet -- design spec §14 open risk #5), so this has no filtering effect through
    execute_selection.filter_by_context YET; it exists so a future curated context_limit is
    honored immediately, with no change to this function or its caller (iteration-4 review
    finding 3, second scope-boundary bullet in Global Constraints)."""
    return len(phase_prompt) // 4


def assemble_candidates(cwd: str, env: dict, cfg_resolve_fn=cfg_resolve) -> tuple:
    resolved = cfg_resolve_fn(cwd, env)
    candidates = [
        {"key": r["key"], "model": r.get("model", ""), "cli": r.get("cli"),
         "vendor": r.get("vendor", ""), "command": r.get("command"),
         # command MUST survive verbatim (iteration-5 review finding 2) -- quota.
         # refresh_quota_cache -> probe_reviewer_quota -> commands.render_reviewer_command raises
         # ValueError for any cli-set entry with no command template, which probe_reviewer_quota
         # converts to available: False -- dropping command here would make every cli-set
         # candidate probe unavailable on every real run regardless of actual quota.
         "task_affinity": r.get("task_affinity"), "context_limit": r.get("context_limit")}
        for r in resolved.get("reviewers", []) if "key" in r
    ]
    top_n_keys = resolved.get("policy", {}).get("ladder", [])
    return candidates, top_n_keys


def _is_native(cli) -> bool:
    # cli is None -> native/current-runtime dispatch (this repo's own "opus-native"-shaped
    # entries); cli in NATIVE_TIER_VENDORS -> reachable through GSD's own hardcoded tier maps.
    # Both are "native_tier" from this adapter's point of view -- see Global Constraints.
    return cli is None or cli in NATIVE_TIER_VENDORS


def _runtime_identity(cli) -> str:
    # The vendor identity to write into GSD's own `runtime` key. cli=None (native/current-runtime
    # dispatch) is literally this session's own identity -- "claude" (design spec §6: a
    # Claude-tier candidate dispatches in-process, i.e. IS the current runtime).
    return cli if cli is not None else "claude"


def _fallback_notice(phase_type: str, top_choice_key, reason: str) -> dict:
    # iteration-6 review, CRITICAL finding, two independent reviewers: EVERY mode this function
    # (and the whole resolve_gsd_dispatch/cli.py result surface) can return MUST carry the SAME
    # base keys (mode, key, cli, provenance) -- Task 5's SKILL.md accesses result["key"] etc.
    # unconditionally in several places, and a mode that silently omits one is a KeyError waiting
    # to happen on exactly the fallback path Task 5's escalation loop terminates on. key is the
    # top choice that COULDN'T be dispatched (or None if there was no candidate at all); cli/
    # provenance are always None/"fallback" here since nothing was ever selected or written.
    top_choice = top_choice_key or "no candidate resolved"
    return {
        "mode": "fallback_notice",
        "key": top_choice_key,
        "cli": None,
        "provenance": "fallback",
        "message": (
            f"ai-kit-spec-execute chose {top_choice} for this task, but {reason}. No "
            f"configuration change was made to GSD's config for phase type {phase_type!r} -- "
            f"GSD's own currently-active default (unmodified by ai-kit-spec-execute) will run "
            f"instead. Update .planning/config.json's model_overrides directly to carry your "
            f"preferred model natively if this matters."
        ),
    }


def resolve_gsd_dispatch(candidates: list, top_n_keys: list, phase_type: str, gsd_config: dict,
                          gsd_config_path: str, target_dir: str, required_context: int = 0,
                          quota: dict | None = None, exclude_keys: list | None = None,
                          run_id: str | None = None, write_fn=write_native_tier_override,
                          write_runtime_fn=write_active_runtime,
                          resolve_ladder_pick_fn=resolve_ladder_pick) -> dict:
    # Short-circuit ONLY on a genuine per-phase model_overrides[phase_type] entry (iteration-5
    # review finding 10) -- never on resolve_native_tier's broader models/model_profile
    # precedence, which includes coarse, project-WIDE defaults with no per-phase granularity
    # (model_profile can even be a bare scalar applying to every phase type at once). Falling
    # through to resolve_native_tier here would make this short-circuit fire on EVERY phase type
    # for a project that only ever set a project-wide default, permanently making this adapter's
    # own selection logic inert -- override_is_adapter_owned only ever inspects model_overrides
    # too, so this keeps both checks aligned on the same key.
    existing_override = gsd_config.get("model_overrides", {}).get(phase_type)
    if existing_override is not None and not override_is_adapter_owned(gsd_config, phase_type):
        # Report the ACTUAL configured runtime identity here (iteration-5 review finding 10),
        # never a fabricated/hardcoded None -- an unset runtime key still means "the current
        # session", i.e. "claude" (design spec §6), so that is the honest default, not a
        # placeholder for "unknown".
        cli_identity = resolve_active_runtime(gsd_config) or "claude"
        return {"mode": "native_tier", "model": existing_override, "written": False,
                "cli": cli_identity, "key": None, "provenance": "existing_gsd_config"}

    quota = dict(quota or {})
    for excluded_key in (exclude_keys or []):
        quota[excluded_key] = {
            "available": False,
            "detail": "excluded: prior runtime dispatch attempt in this same wave failed with "
                       "a quota signal",
        }
    # task_type is execute_selection's own frontend/backend/mixed "task_affinity" axis (design
    # spec §5.1) -- a DIFFERENT concept than GSD's phase_type, and no curated task_affinity data
    # exists anywhere in Foundation yet (assemble_candidates tags every candidate None). Passing
    # phase_type here would silently conflate the two; None is the honest, stated scope decision
    # (see Global Constraints). required_context IS a real measurement (estimate_required_context),
    # never a hardcoded 0.
    ranked = resolve_execute_candidates(candidates, None, required_context, {}, top_n_keys)
    if not ranked:
        return _fallback_notice(
            phase_type, None,
            "ai-kit-spec-execute has no configured candidate at all (review-spec.toml has no "
            "[[reviewers]] entries) -- nothing to select from")

    by_key = {c["key"]: c for c in ranked}
    remaining_ladder = candidates_to_ladder(ranked)
    top_key = ranked[0]["key"]

    while remaining_ladder:
        pick = resolve_ladder_pick_fn(ranked, remaining_ladder, skip_vendor="", quota=quota)
        if pick is None:
            break  # nothing left in the ladder has quota
        candidate = by_key[pick.key]
        if _is_native(candidate["cli"]):
            runtime_identity = _runtime_identity(candidate["cli"])
            if resolve_active_runtime(gsd_config) != runtime_identity:
                gsd_config = write_runtime_fn(gsd_config_path, gsd_config, runtime_identity,
                                               run_id=run_id)
            write_fn(gsd_config_path, gsd_config, phase_type, candidate["model"], run_id=run_id)
            return {"mode": "native_tier", "model": candidate["model"], "written": True,
                    "cli": candidate["cli"], "key": candidate["key"],
                    "provenance": "resolved_candidate"}
        cross_ai = build_cross_ai_dispatch(candidate, target_dir)
        if cross_ai is not None:
            return cross_ai
        remaining_ladder = [k for k in remaining_ladder if k != pick.key]

    return _fallback_notice(
        phase_type, top_key,
        f"no quota-available candidate in the ladder has a usable native or cross-AI dispatch "
        f"path for phase type {phase_type!r}")
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestAssembleCandidates \
  tests.test_ai_kit_spec_gsd.TestEstimateRequiredContext \
  tests.test_ai_kit_spec_gsd.TestClassifyDispatchFailure \
  tests.test_ai_kit_spec_gsd.TestResolveGsdDispatch -v 2>&1 | tail -30
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add adapter.py (candidate assembly + live-quota-checked dispatch resolution with write-back, honest fallback)"
```

- [ ] **Step 6: Write the failing tests for a runnable CLI covering every operation Task 5's SKILL.md needs (iteration-4 review finding 8)**

A zero-context executing agent (Task 5's SKILL.md) needs concrete, invokable commands for every
operation it performs — not just dispatch resolution, but config-path resolution, quota loading,
tooling-guidance preparation, and resumable-state creation too — mirroring `ai_kit_spec/cli.py`'s
own subcommand pattern (Plan 1), never a bare "call this Python function" instruction with no
interpreter entrypoint shown.

Add this import line to the shared test file, directly above the test classes below (iteration-5
review finding 1 -- `cli.py` doesn't exist until Step 8, later in THIS SAME task, implements it;
Step 7's "Expected: FAIL -- module not found" IS this import line failing):

```python
from ai_kit_spec_gsd import cli


class TestCliResolveDispatch(unittest.TestCase):
    def test_resolve_dispatch_subcommand_prints_json_dispatch_decision(self):
        import io
        import json
        def fake_assemble(cwd, env):
            return ([{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None}],
                    ["codex/gpt-5.6-sol"])
        def fake_read_config(path, warn_fn=None):
            return {}, "missing"
        def fake_refresh_quota(config, ladder, existing, ttl, run_fn=None):
            return {}
        stdout = io.StringIO()
        exit_code = cli.main(
            ["resolve-dispatch", "--cwd", "/repo", "--phase-type", "backend",
             "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
             "--quota-path", "/cache/quota.json"],
            assemble_candidates_fn=fake_assemble, read_gsd_config_fn=fake_read_config,
            refresh_quota_cache_fn=fake_refresh_quota, cache_read_json_fn=lambda p: {},
            cache_write_json_fn=lambda p, d: None, write_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {}, stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_resolve_dispatch_folds_exclude_key_flags_through_to_the_adapter(self):
        import io
        import json
        def fake_assemble(cwd, env):
            return ([{"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast",
                       "vendor": "xai", "task_affinity": None, "context_limit": None},
                      {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None}],
                    ["grok/grok-4-fast", "codex/gpt-5.6-sol"])
        stdout = io.StringIO()
        exit_code = cli.main(
            ["resolve-dispatch", "--cwd", "/repo", "--phase-type", "backend",
             "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
             "--quota-path", "/cache/quota.json",
             "--exclude-key", "grok/grok-4-fast"],
            assemble_candidates_fn=fake_assemble,
            read_gsd_config_fn=lambda p, warn_fn=None: ({}, "missing"),
            refresh_quota_cache_fn=lambda *a, **k: {}, cache_read_json_fn=lambda p: {},
            cache_write_json_fn=lambda p, d: None, write_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {}, stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")  # grok excluded, codex wins

    def test_resolve_dispatch_aborts_and_reports_malformed_config_without_mutating(self):
        # iteration-4 review finding 7: a malformed config must abort the whole subcommand
        # rather than silently proceed as if it were merely unconfigured.
        import io
        import json
        write_calls = []
        stdout = io.StringIO()
        exit_code = cli.main(
            ["resolve-dispatch", "--cwd", "/repo", "--phase-type", "backend",
             "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
             "--quota-path", "/cache/quota.json"],
            assemble_candidates_fn=lambda cwd, env: ([], []),
            read_gsd_config_fn=lambda p, warn_fn=None: ({}, "malformed"),
            refresh_quota_cache_fn=lambda *a, **k: {}, cache_read_json_fn=lambda p: {},
            cache_write_json_fn=lambda p, d: None,
            write_fn=lambda *a, **k: write_calls.append(a),
            write_runtime_fn=lambda *a, **k: write_calls.append(a), stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertIn("malformed", result["message"].lower())
        self.assertEqual(write_calls, [])  # never attempted a write over a broken config

    def test_resolve_dispatch_preserves_command_field_for_quota_probing(self):
        # iteration-5 review finding 2, independently found by two reviewers:
        # quota.refresh_quota_cache -> probe_reviewer_quota -> commands.render_reviewer_command
        # raises ValueError for any cli-set entry with no `command` template, which
        # probe_reviewer_quota converts to available: False -- so the synthetic reviewers list
        # this subcommand builds for refresh_quota_cache_fn MUST carry each candidate's own real
        # `command` field through, never drop it.
        import io
        def fake_assemble(cwd, env):
            return ([{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "command": "codex exec -m {model} -- {prompt}",
                       "task_affinity": None, "context_limit": None}],
                    ["codex/gpt-5.6-sol"])
        captured = {}
        def fake_refresh_quota(config, ladder, existing, ttl, run_fn=None):
            captured["reviewers"] = config["reviewers"]
            return {}
        stdout = io.StringIO()
        cli.main(
            ["resolve-dispatch", "--cwd", "/repo", "--phase-type", "backend",
             "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
             "--quota-path", "/cache/quota.json"],
            assemble_candidates_fn=fake_assemble,
            read_gsd_config_fn=lambda p, warn_fn=None: ({}, "missing"),
            refresh_quota_cache_fn=fake_refresh_quota, cache_read_json_fn=lambda p: {},
            cache_write_json_fn=lambda p, d: None, write_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {}, stdout=stdout)
        self.assertEqual(captured["reviewers"][0]["command"],
                          "codex exec -m {model} -- {prompt}")

    def test_resolve_dispatch_generates_one_run_id_and_threads_it_through_every_write(self):
        # iteration-5 review finding 5: no CLI subcommand exposed a --run-id, and
        # resolve_gsd_dispatch's two write calls (write_fn/write_runtime_fn) would otherwise each
        # independently default their own run_id -- two DIFFERENT timestamps within one logical
        # invocation, defeating "one run_id, one backup per run." This subcommand must generate
        # exactly ONE run_id (or use an explicit --run-id if given) and pass the SAME string to
        # BOTH write calls, and also return it in the JSON result so a caller (Task 5's SKILL.md)
        # can thread the same id into later write-workflow-key calls in the same wave.
        import io
        import json
        def fake_assemble(cwd, env):
            return ([{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "command": "codex exec -m {model} -- {prompt}",
                       "task_affinity": None, "context_limit": None}],
                    ["codex/gpt-5.6-sol"])
        run_ids_seen = []
        def fake_write(path, gsd_config, phase_type, model, run_id=None, **kw):
            run_ids_seen.append(run_id)
            return {**gsd_config, "model_overrides": {phase_type: model}}
        def fake_write_runtime(path, gsd_config, runtime, run_id=None, **kw):
            run_ids_seen.append(run_id)
            return {**gsd_config, "runtime": runtime}
        stdout = io.StringIO()
        cli.main(
            ["resolve-dispatch", "--cwd", "/repo", "--phase-type", "backend",
             "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
             "--quota-path", "/cache/quota.json", "--run-id", "explicit-run-42"],
            assemble_candidates_fn=fake_assemble,
            read_gsd_config_fn=lambda p, warn_fn=None: ({}, "missing"),
            refresh_quota_cache_fn=lambda *a, **k: {}, cache_read_json_fn=lambda p: {},
            cache_write_json_fn=lambda p, d: None, write_fn=fake_write,
            write_runtime_fn=fake_write_runtime, stdout=stdout)
        self.assertTrue(run_ids_seen)  # at least one write call happened
        self.assertEqual(set(run_ids_seen), {"explicit-run-42"})  # every write shares ONE id
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["run_id"], "explicit-run-42")

    def test_resolve_dispatch_falls_back_to_zero_context_when_phase_prompt_file_is_unreadable(self):
        # iteration-4 review finding 17: a missing/unreadable --phase-prompt-file must never
        # crash this subcommand's entire parseable-JSON-on-stdout contract with an uncaught
        # traceback -- fall back to required_context=0 (the same value used when the flag is
        # omitted entirely) and warn on stderr only, never stdout.
        import io
        import json  # iteration-6 review, HIGH finding: this test uses json.loads below but
                     # never imported it locally (no module-level json import exists in this
                     # file's bootstrap) -- NameError without this line, unattainable "Expected:
                     # PASS".
        def fake_assemble(cwd, env):
            return ([{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "command": "codex exec -m {model} -- {prompt}",
                       "task_affinity": None, "context_limit": None}],
                    ["codex/gpt-5.6-sol"])
        stdout, stderr = io.StringIO(), io.StringIO()
        import contextlib
        with contextlib.redirect_stderr(stderr):
            exit_code = cli.main(
                ["resolve-dispatch", "--cwd", "/repo", "--phase-type", "backend",
                 "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
                 "--quota-path", "/cache/quota.json",
                 "--phase-prompt-file", "/nonexistent/phase-prompt.md"],
                assemble_candidates_fn=fake_assemble,
                read_gsd_config_fn=lambda p, warn_fn=None: ({}, "missing"),
                refresh_quota_cache_fn=lambda *a, **k: {}, cache_read_json_fn=lambda p: {},
                cache_write_json_fn=lambda p, d: None, write_fn=lambda *a, **k: {},
                write_runtime_fn=lambda *a, **k: {}, stdout=stdout)
        self.assertEqual(exit_code, 0)  # no uncaught traceback
        json.loads(stdout.getvalue())  # stdout is still valid, parseable JSON
        self.assertIn("phase-prompt.md", stderr.getvalue())  # warning went to stderr, not stdout


class TestCliConfigPath(unittest.TestCase):
    def test_config_path_subcommand_prints_the_resolved_path(self):
        import io
        stdout = io.StringIO()
        exit_code = cli.main(["config-path", "--cwd", "/repo"], stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().strip(), "/repo/.planning/config.json")


class TestCliWriteWorkflowKey(unittest.TestCase):
    def test_write_workflow_key_subcommand_writes_a_string_value(self):
        import io
        import json
        writes = {}
        def fake_write(path, gsd_config, key, value, **kw):
            writes["args"] = (path, gsd_config, key, value)
            return {**gsd_config, "workflow": {key: value}}
        stdout = io.StringIO()
        exit_code = cli.main(
            ["write-workflow-key", "--config-path", "/repo/.planning/config.json",
             "--config-json", "{}", "--key", "cross_ai_command", "--run-id", "run-1",
             "--value-json", json.dumps("codex exec ...")],
            write_workflow_key_fn=fake_write, stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["workflow"]["cross_ai_command"], "codex exec ...")
        self.assertEqual(writes["args"][2:], ("cross_ai_command", "codex exec ..."))

    def test_write_workflow_key_subcommand_writes_a_real_json_boolean_not_a_string(self):
        # iteration-5 review finding 6: argparse's plain --value always yields a Python str, so
        # `--value true` would previously write the STRING "true" into .planning/config.json's
        # workflow.cross_ai_execution, not the JSON boolean `true`. --value-json runs the raw
        # argument through json.loads, so this is a real, typed value end-to-end through the CLI
        # path (not just through write_workflow_key called directly, which was already covered).
        import io
        import json
        writes = {}
        def fake_write(path, gsd_config, key, value, **kw):
            writes["args"] = (path, gsd_config, key, value)
            return {**gsd_config, "workflow": {key: value}}
        stdout = io.StringIO()
        cli.main(
            ["write-workflow-key", "--config-path", "/repo/.planning/config.json",
             "--config-json", "{}", "--key", "cross_ai_execution", "--run-id", "run-1",
             "--value-json", "true"],
            write_workflow_key_fn=fake_write, stdout=stdout)
        value_written = writes["args"][3]
        self.assertIs(value_written, True)  # a real bool, never the string "true"
        result = json.loads(stdout.getvalue())
        self.assertIs(result["workflow"]["cross_ai_execution"], True)


class TestCliClearWorkflowKey(unittest.TestCase):
    def test_clear_workflow_key_subcommand_clears_an_adapter_owned_key(self):
        # iteration-5 review finding 6's mode-transition behavior: a later run that resolves a
        # DIFFERENT dispatch mode must be able to disable a prior run's own adapter-owned
        # cross_ai_command/cross_ai_execution write via a real, runnable subcommand.
        import io
        import json
        config_json = json.dumps({
            "workflow": {"cross_ai_command": "codex exec ..."},
            "_ai_kit_spec_execute_gsd": {"workflow": {"cross_ai_command": "codex exec ..."}},
        })
        writes = {}
        def fake_clear(path, gsd_config, key, **kw):
            writes["args"] = (path, gsd_config, key)
            updated = {**gsd_config, "workflow": {}}
            return updated
        stdout = io.StringIO()
        exit_code = cli.main(
            ["clear-workflow-key", "--config-path", "/repo/.planning/config.json",
             "--config-json", config_json, "--key", "cross_ai_command", "--run-id", "run-1"],
            clear_workflow_key_if_adapter_owned_fn=fake_clear, stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertNotIn("cross_ai_command", result["workflow"])


class _FakeCompletedProcess:
    def __init__(self, returncode):
        self.returncode = returncode
        self.stdout = ""
        self.stderr = ""


class TestCliPrepareTooling(unittest.TestCase):
    def test_prepare_tooling_subcommand_builds_the_index_for_real_and_prints_guidance_text(self):
        # iteration-4 review finding 8: run_fn must actually run (default subprocess.run, never
        # a None default that silently skips index-building in every real invocation) and its
        # real result must be inspected before the guidance text claims CodeGraph readiness.
        import io
        run_calls = []
        def fake_run(cmd, **kw):
            run_calls.append((cmd, kw))
            return _FakeCompletedProcess(returncode=0)
        stdout = io.StringIO()
        exit_code = cli.main(
            ["prepare-tooling", "--cli", "codex", "--target-dir", "/repo"],
            detect_tool_availability_fn=lambda **k: {"codegraph": True, "rg": True},
            resolve_agents_tooling_path_fn=lambda **k: "/home/u/.agents/AGENTS-TOOLING.md",
            ensure_codegraph_registered_fn=lambda cli, **k: True,
            build_codegraph_index_command_fn=lambda target_dir: "cd /repo && codegraph sync",
            run_fn=fake_run, stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(run_calls), 1)  # the index command was actually run, not skipped
        self.assertEqual(run_calls[0][1]["timeout"], 15)  # CODEGRAPH_INDEX_TIMEOUT_SECONDS
        self.assertIn("AGENTS-TOOLING.md", stdout.getvalue())
        self.assertIn("codegraph_explore", stdout.getvalue())

    def test_prepare_tooling_falls_back_to_unregistered_guidance_when_the_index_build_fails(self):
        # iteration-4 review finding 8: never claim CodeGraph readiness in the guidance text the
        # index command itself just failed to establish.
        import io
        def failing_run(cmd, **kw):
            return _FakeCompletedProcess(returncode=1)
        stdout = io.StringIO()
        cli.main(
            ["prepare-tooling", "--cli", "codex", "--target-dir", "/repo"],
            detect_tool_availability_fn=lambda **k: {"codegraph": True, "rg": True},
            resolve_agents_tooling_path_fn=lambda **k: "/home/u/.agents/AGENTS-TOOLING.md",
            ensure_codegraph_registered_fn=lambda cli, **k: True,
            build_codegraph_index_command_fn=lambda target_dir: "cd /repo && codegraph sync",
            run_fn=failing_run, stdout=stdout)
        self.assertNotIn("codegraph_explore", stdout.getvalue())


class TestCliWriteResumableState(unittest.TestCase):
    def test_write_resumable_state_subcommand_writes_the_given_state_json(self):
        import io
        writes = {}
        def fake_write(path, state):
            writes[path] = state
        stdout = io.StringIO()
        exit_code = cli.main(
            ["write-resumable-state", "--path", "/cache/gsd-resume-abc123-phase1.json",
             "--state-json",
             '{"framework": "gsd", "phase_id": "phase1", "candidates_tried": ["grok/grok-4-fast"]}'],
            write_resumable_state_fn=fake_write, stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(writes["/cache/gsd-resume-abc123-phase1.json"]["phase_id"], "phase1")


class TestCliDispatchPhase(unittest.TestCase):
    def test_dispatch_phase_subcommand_prints_json_result_and_routes_heartbeat_to_stderr(self):
        # iteration-5 review finding 7: SKILL.md Step 3 must never be told to call
        # ai_kit_spec.dispatch.dispatch_with_heartbeat directly -- this subcommand is its own
        # concrete, runnable entrypoint, exactly like every other operation in this plan.
        import io
        import json
        import os
        import tempfile
        def fake_dispatch(command, prompt, heartbeat_interval, timeout, print_fn=print):
            print_fn("[12:00:00] still running, 5s elapsed")
            return {"returncode": 0, "stdout": "PHASE SUMMARY: done.", "stderr": "",
                    "timed_out": False}
        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.md")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("the phase prompt text")
            stdout, stderr = io.StringIO(), io.StringIO()
            exit_code = cli.main(
                ["dispatch-phase", "--dispatch-command", "gsd-execute-phase phase1",
                 "--prompt-file", prompt_path],
                dispatch_with_heartbeat_fn=fake_dispatch, stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["stdout"], "PHASE SUMMARY: done.")


class TestCliClassifyFailure(unittest.TestCase):
    def test_classify_failure_subcommand_prints_the_classification(self):
        import io
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            stdout_path, stderr_path = os.path.join(d, "out.txt"), os.path.join(d, "err.txt")
            with open(stdout_path, "w", encoding="utf-8") as f:
                f.write("")
            with open(stderr_path, "w", encoding="utf-8") as f:
                f.write("usage limit exceeded")
            stdout = io.StringIO()
            exit_code = cli.main(
                ["classify-failure", "--stdout-file", stdout_path, "--stderr-file", stderr_path],
                classify_dispatch_failure_fn=lambda out, err: "quota", stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "quota")
```

- [ ] **Step 7: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestCliResolveDispatch \
  tests.test_ai_kit_spec_gsd.TestCliConfigPath \
  tests.test_ai_kit_spec_gsd.TestCliWriteWorkflowKey \
  tests.test_ai_kit_spec_gsd.TestCliClearWorkflowKey \
  tests.test_ai_kit_spec_gsd.TestCliPrepareTooling \
  tests.test_ai_kit_spec_gsd.TestCliWriteResumableState \
  tests.test_ai_kit_spec_gsd.TestCliDispatchPhase \
  tests.test_ai_kit_spec_gsd.TestCliClassifyFailure -v 2>&1 | tail -30
```

Expected: FAIL — module not found.

- [ ] **Step 8: Implement `ai_kit_spec_gsd/cli.py`**

```python
"""CLI entrypoint for ai-kit-spec-execute-gsd -- invoked via the ai-kit-spec-gsd.py shim (Task 2
Steps 7-9), NEVER `python3 -m ai_kit_spec_gsd.cli` directly (that only resolves when
ai_kit_spec_gsd already happens to be importable, which a caller running from an arbitrary GSD
project cwd cannot assume -- iteration-4 review finding 1). Mirrors ai_kit_spec/cli.py's own
subcommand pattern (Plan 1) so Task 5's SKILL.md gives an executing agent one concrete, runnable
command for EVERY operation it performs -- resolve-dispatch, config-path, write-workflow-key,
clear-workflow-key, prepare-tooling, write-resumable-state, dispatch-phase, classify-failure
(iteration-4 review finding 8, iteration-5 review finding 7) -- never a bare "call this Python
function" instruction."""
import argparse
import json
import os
import subprocess
import sys

from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.detection import (
    CODEGRAPH_INDEX_TIMEOUT_SECONDS, build_codegraph_index_command, detect_tool_availability,
    ensure_codegraph_registered, resolve_agents_tooling_path,
)
from ai_kit_spec.quota import refresh_quota_cache, QUOTA_TTL_SECONDS
from ai_kit_spec.tooling_guidance import build_tooling_guidance
from ai_kit_spec_gsd.adapter import (
    assemble_candidates, classify_dispatch_failure, estimate_required_context,
    resolve_gsd_dispatch,
)
from ai_kit_spec_gsd.gsd_config import (
    clear_workflow_key_if_adapter_owned, generate_run_id, read_gsd_config,
    resolve_gsd_config_path, write_active_runtime, write_native_tier_override, write_workflow_key,
)
from ai_kit_spec.dispatch import dispatch_with_heartbeat
from ai_kit_spec.dispatch import write_resumable_state as _write_resumable_state_default


def main(argv: list, assemble_candidates_fn=assemble_candidates,
         read_gsd_config_fn=read_gsd_config, refresh_quota_cache_fn=refresh_quota_cache,
         cache_read_json_fn=cache_read_json, cache_write_json_fn=cache_write_json,
         write_fn=write_native_tier_override, write_runtime_fn=write_active_runtime,
         write_workflow_key_fn=write_workflow_key,
         clear_workflow_key_if_adapter_owned_fn=clear_workflow_key_if_adapter_owned,
         detect_tool_availability_fn=detect_tool_availability,
         resolve_agents_tooling_path_fn=resolve_agents_tooling_path,
         ensure_codegraph_registered_fn=ensure_codegraph_registered,
         build_codegraph_index_command_fn=build_codegraph_index_command,
         run_fn=subprocess.run, dispatch_with_heartbeat_fn=dispatch_with_heartbeat,
         classify_dispatch_failure_fn=classify_dispatch_failure,
         write_resumable_state_fn=_write_resumable_state_default, stdout=sys.stdout) -> int:
    parser = argparse.ArgumentParser(prog="ai-kit-spec-execute-gsd")
    sub = parser.add_subparsers(dest="command", required=True)

    p_resolve = sub.add_parser("resolve-dispatch")
    p_resolve.add_argument("--cwd", required=True)
    p_resolve.add_argument("--phase-type", required=True)
    p_resolve.add_argument("--config-path", required=True)
    p_resolve.add_argument("--target-dir", required=True)
    p_resolve.add_argument("--quota-path", required=True)
    p_resolve.add_argument("--phase-prompt-file", default=None,
                            help="used to compute a real required_context estimate; omit for 0")
    p_resolve.add_argument("--exclude-key", action="append", default=[],
                            help="repeatable -- a candidate key to force unavailable this call "
                                 "(runtime quota-exhaustion escalation, see adapter.py)")
    p_resolve.add_argument("--run-id", default=None,
                            help="omit to generate one (iteration-5 review finding 5) -- this "
                                 "call's resolved run_id is ALSO printed in the JSON result "
                                 "(result['run_id']) so the caller can thread the SAME id into "
                                 "any later write-workflow-key/clear-workflow-key calls in the "
                                 "same wave, guaranteeing one shared backup per run")

    p_config_path = sub.add_parser("config-path")
    p_config_path.add_argument("--cwd", required=True)
    p_config_path.add_argument("--workstream-id", default=None)

    p_write_workflow = sub.add_parser("write-workflow-key")
    p_write_workflow.add_argument("--config-path", required=True)
    p_write_workflow.add_argument("--config-json", required=True,
                                   help="the current gsd_config dict as a JSON string -- thread "
                                        "the PREVIOUS write's own stdout into this on a second "
                                        "call in the same run (never re-serialize a stale copy)")
    p_write_workflow.add_argument("--key", required=True)
    p_write_workflow.add_argument("--value-json", required=True,
                                   help="the value to write, as a JSON literal -- e.g. "
                                        "'\"codex exec ...\"' for a string, 'true' for a JSON "
                                        "boolean (iteration-5 review finding 6: a plain --value "
                                        "always yields a Python str from argparse, which would "
                                        "silently write the STRING \"true\" instead of the JSON "
                                        "boolean true; --value-json is run through json.loads, "
                                        "never left as an untyped string)")
    p_write_workflow.add_argument("--run-id", required=True,
                                   help="REQUIRED -- always the SAME run_id captured from this "
                                        "wave's resolve-dispatch call (result['run_id']), so a "
                                        "cross_ai_command write and a cross_ai_execution write in "
                                        "the same wave share exactly one backup")

    p_clear_workflow = sub.add_parser("clear-workflow-key")
    p_clear_workflow.add_argument("--config-path", required=True)
    p_clear_workflow.add_argument("--config-json", required=True)
    p_clear_workflow.add_argument("--key", required=True)
    p_clear_workflow.add_argument("--run-id", required=True)

    p_prepare = sub.add_parser("prepare-tooling")
    p_prepare.add_argument("--cli", default=None,
                            help="omit (or pass 'claude') for native/current-runtime dispatch")
    p_prepare.add_argument("--target-dir", required=True)

    p_resume = sub.add_parser("write-resumable-state")
    p_resume.add_argument("--path", required=True)
    p_resume.add_argument("--state-json", required=True)

    # iteration-4 review finding 7: dispatch and failure-classification are the ONE thing every
    # OTHER operation in this plan got a CLI subcommand specifically to avoid -- a zero-context
    # SKILL.md step must never be told to call a bare Python function directly.
    p_dispatch = sub.add_parser("dispatch-phase")
    p_dispatch.add_argument("--dispatch-command", required=True,
                             help="the shell command to run -- GSD's own execution entry point, "
                                  "or (for cross_ai_hook mode) the resolved cross-AI command")
    p_dispatch.add_argument("--prompt-file", required=True,
                             help="its content is piped to the dispatched command's stdin")
    p_dispatch.add_argument("--heartbeat-interval", type=int, default=30)
    p_dispatch.add_argument("--timeout", type=int, default=1800)

    p_classify = sub.add_parser("classify-failure")
    p_classify.add_argument("--stdout-file", required=True)
    p_classify.add_argument("--stderr-file", required=True)

    args = parser.parse_args(argv)

    if args.command == "resolve-dispatch":
        # warn_fn routed to STDERR explicitly (iteration-4 review finding 7) -- read_gsd_config's
        # own default (warn_fn=print) writes to stdout, which would corrupt this subcommand's
        # JSON result the moment a malformed config triggers a warning.
        gsd_config, status = read_gsd_config_fn(
            args.config_path, warn_fn=lambda msg: print(msg, file=sys.stderr))
        if status == "malformed":
            # iteration-6 review, CRITICAL finding: this early-return result must carry the SAME
            # base shape as every other resolve-dispatch output (mode/key/cli/provenance/run_id)
            # -- Task 5's SKILL.md reads all five unconditionally, and this was the one path that
            # used to omit them (including run_id, which every other path gets at line "result
            # ["run_id"] = run_id" below -- unreachable from this early return, so generated here
            # instead, even though nothing is actually written on this path).
            result = {"mode": "fallback_notice", "key": None, "cli": None,
                      "provenance": "fallback",
                      "message": f"{args.config_path} is malformed/unreadable -- refusing to "
                                 f"write over it. Fix or remove it by hand, then re-run.",
                      "run_id": args.run_id if args.run_id else generate_run_id()}
            stdout.write(json.dumps(result))
            return 0
        # ONE run_id for this entire invocation (iteration-5 review finding 5) -- threaded into
        # BOTH resolve_gsd_dispatch's write calls (write_fn/write_runtime_fn), never left None
        # (each write function's own None-default independently generates a DIFFERENT timestamp,
        # which would defeat "one run_id, one backup per run" the moment both writes fire in the
        # same call).
        run_id = args.run_id if args.run_id else generate_run_id()
        candidates, top_n_keys = assemble_candidates_fn(args.cwd, dict(os.environ))
        existing_quota = cache_read_json_fn(args.quota_path) or {}
        quota = refresh_quota_cache_fn(
            {"reviewers": [
                # command MUST be threaded through here (iteration-5 review finding 2) --
                # quota.refresh_quota_cache -> probe_reviewer_quota -> commands.
                # render_reviewer_command raises ValueError for any cli-set entry with no
                # command template, and probe_reviewer_quota converts that into available:
                # False. Dropping command from this synthetic reviewers list would make every
                # cli-set candidate probe unavailable on every real run, regardless of quota.
                {"key": c["key"], "model": c["model"], "vendor": c["vendor"], "cli": c["cli"],
                 "command": c.get("command")}
                for c in candidates
            ]},
            # iteration-6 review, HIGH finding: probe EVERY assembled candidate's key here, not
            # just top_n_keys (policy.ladder) -- resolve_execute_candidates' own ranked output can
            # include candidates OUTSIDE policy.ladder (e.g. escalation past the configured
            # ladder), and quota._has_quota treats a genuinely un-probed key as "available" by
            # design (never block on absent quota data) -- so a candidate this call never even
            # tried to probe could be selected as if its availability were live-verified. Probing
            # the full candidate set (cheap: refresh_quota_cache already skips any key whose
            # existing cache entry is still within QUOTA_TTL_SECONDS) closes that gap.
            [c["key"] for c in candidates], existing_quota, QUOTA_TTL_SECONDS)
        cache_write_json_fn(args.quota_path, quota)
        required_context = 0
        if args.phase_prompt_file:
            # A missing/unreadable phase-prompt file must never crash this subcommand's entire
            # parseable-JSON-on-stdout contract with an uncaught traceback (iteration-4 review
            # finding 17) -- fall back to required_context=0 (the same value already used when
            # --phase-prompt-file is omitted entirely) and warn on stderr, never stdout.
            try:
                with open(args.phase_prompt_file, encoding="utf-8") as f:
                    required_context = estimate_required_context(f.read())
            except OSError as exc:
                print(f"ai-kit-spec-execute-gsd: could not read --phase-prompt-file "
                      f"{args.phase_prompt_file!r} ({exc}) -- falling back to "
                      f"required_context=0", file=sys.stderr)
        result = resolve_gsd_dispatch(
            candidates, top_n_keys, args.phase_type, gsd_config, args.config_path,
            args.target_dir, required_context=required_context, quota=quota,
            exclude_keys=args.exclude_key, run_id=run_id, write_fn=write_fn,
            write_runtime_fn=write_runtime_fn)
        result["run_id"] = run_id
        stdout.write(json.dumps(result))
        return 0

    if args.command == "config-path":
        stdout.write(resolve_gsd_config_path(args.cwd, workstream_id=args.workstream_id) + "\n")
        return 0

    if args.command == "write-workflow-key":
        gsd_config = json.loads(args.config_json)
        value = json.loads(args.value_json)
        result = write_workflow_key_fn(args.config_path, gsd_config, args.key, value,
                                        run_id=args.run_id)
        stdout.write(json.dumps(result))
        return 0

    if args.command == "clear-workflow-key":
        gsd_config = json.loads(args.config_json)
        result = clear_workflow_key_if_adapter_owned_fn(args.config_path, gsd_config, args.key,
                                                          run_id=args.run_id)
        stdout.write(json.dumps(result))
        return 0

    if args.command == "prepare-tooling":
        tool_availability = detect_tool_availability_fn()
        agents_tooling_path = resolve_agents_tooling_path_fn()
        codegraph_registered = False
        codegraph_index_result = None
        if args.cli is not None:
            codegraph_registered = ensure_codegraph_registered_fn(args.cli)
            if codegraph_registered:
                index_cmd = build_codegraph_index_command_fn(args.target_dir)
                # run_fn DEFAULTS to subprocess.run (iteration-4 review finding 8) -- a None
                # default (this task's prior revision) silently skipped index-building in EVERY
                # real invocation, only ever running inside the unit test that injects a fake.
                # CODEGRAPH_INDEX_TIMEOUT_SECONDS is imported from ai_kit_spec.detection (the
                # canonical source), never restated as a separate "15" literal here.
                #
                # iteration-6 review, HIGH finding: a nonzero returncode is only ONE of the ways
                # this can fail -- subprocess.run(timeout=...) raises TimeoutExpired on a slow
                # index build, and a missing/unexecutable codegraph binary raises OSError, NEITHER
                # of which the old bare call caught, crashing this subcommand's entire
                # parseable-stdout contract instead of degrading to generic guidance the same way
                # a nonzero returncode already does.
                try:
                    codegraph_index_result = run_fn(
                        index_cmd, shell=True, capture_output=True, text=True, check=False,
                        timeout=CODEGRAPH_INDEX_TIMEOUT_SECONDS)
                    if codegraph_index_result.returncode != 0:
                        codegraph_registered = False
                except (subprocess.TimeoutExpired, OSError):
                    # The guidance text built below must not claim CodeGraph readiness the index
                    # build itself just failed to establish (iteration-4 review finding 8) --
                    # fall back to "not registered" for the guidance builder's own purposes,
                    # exactly like the nonzero-returncode case above, never an uncaught traceback.
                    codegraph_registered = False
        guidance = build_tooling_guidance(args.cli, tool_availability, agents_tooling_path,
                                           codegraph_registered)
        stdout.write(guidance)
        return 0

    if args.command == "write-resumable-state":
        state = json.loads(args.state_json)
        write_resumable_state_fn(args.path, state)
        stdout.write(json.dumps({"written": True, "path": args.path}))
        return 0

    if args.command == "dispatch-phase":
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
        def _heartbeat_to_stderr(msg):
            print(msg, file=sys.stderr)
        result = dispatch_with_heartbeat_fn(args.dispatch_command, prompt,
                                             args.heartbeat_interval, args.timeout,
                                             print_fn=_heartbeat_to_stderr)
        stdout.write(json.dumps(result))
        return 0

    if args.command == "classify-failure":
        with open(args.stdout_file, encoding="utf-8") as f:
            captured_stdout = f.read()
        with open(args.stderr_file, encoding="utf-8") as f:
            captured_stderr = f.read()
        stdout.write(classify_dispatch_failure_fn(captured_stdout, captured_stderr))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 9: Run tests to verify pass, commit**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestCliResolveDispatch \
  tests.test_ai_kit_spec_gsd.TestCliConfigPath \
  tests.test_ai_kit_spec_gsd.TestCliWriteWorkflowKey \
  tests.test_ai_kit_spec_gsd.TestCliClearWorkflowKey \
  tests.test_ai_kit_spec_gsd.TestCliPrepareTooling \
  tests.test_ai_kit_spec_gsd.TestCliWriteResumableState \
  tests.test_ai_kit_spec_gsd.TestCliDispatchPhase \
  tests.test_ai_kit_spec_gsd.TestCliClassifyFailure -v 2>&1 | tail -30
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add cli.py resolve-dispatch/config-path/write-workflow-key/prepare-tooling/write-resumable-state subcommands -- concrete invocation paths for SKILL.md, with live quota loading"
```

- [ ] **Step 10: Prove the shim's real `resolve-dispatch` subcommand runs end-to-end from OUTSIDE the repository**

Task 2 Step 8 proved the shim's `sys.path` wiring resolves both packages; it deliberately stopped
short of invoking a real subcommand because `cli.py` did not exist yet. Now that it does, close
the loop with the actual invocation Task 2 Step 8's old (buggy) version attempted:

```bash
SCRATCH_DIR="$(mktemp -d)"
mkdir -p "$SCRATCH_DIR/.planning"
QUOTA_PATH="$(mktemp)"
echo '{}' > "$QUOTA_PATH"
cd "$SCRATCH_DIR" && python3 /absolute/path/to/skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py \
  resolve-dispatch --cwd "$SCRATCH_DIR" --phase-type backend \
  --config-path "$SCRATCH_DIR/.planning/config.json" --target-dir "$SCRATCH_DIR" \
  --quota-path "$QUOTA_PATH" 2>&1
```

Expected: prints a JSON dispatch decision (most likely `{"mode": "fallback_notice", ...}` since
`$SCRATCH_DIR` has no `review-spec.toml` — the point of this step is confirming NO
`ModuleNotFoundError` of any kind is raised and the command exits 0 with valid JSON on stdout, not
which dispatch mode an empty scratch project resolves to).

```bash
git add -A
git commit -m "test(ai-kit-spec-execute-gsd): verify shim's resolve-dispatch subcommand runs end-to-end from outside the repo"
```

---

### Task 5: `SKILL.md` for `ai-kit-spec-execute-gsd`

**Files:**
- Create: `skills/ai-kit-spec-execute-gsd/SKILL.md`

**Interfaces:**
- Consumes: `ai_kit_spec_gsd/cli.py`'s `resolve-dispatch`/`config-path`/`write-workflow-key`/
  `prepare-tooling`/`write-resumable-state` subcommands (Task 4 — every one invoked through the
  `ai-kit-spec-gsd.py` shim, Task 2 Steps 7-9, NEVER `python3 -m ai_kit_spec_gsd.cli` directly),
  `ai_kit_spec.dispatch.dispatch_with_heartbeat` (Plan 1).

**This skill's own entry precondition**, stated explicitly since nothing upstream of it invents
these values: it is invoked already knowing `cwd` (the GSD project root), `phase_id` (the
specific phase being executed — passed down by whatever triggered execution: the
`ai-kit-spec-execute` router, or the user directly) and, from GSD's own phase docs, the phase's
prompt/context file path. This skill never guesses any of the three.

- [ ] **Step 1: Write the skill body**

Structure (Process pattern, per skill-judge's pattern table — this is a multi-step phased
workflow like `mcp-builder`, not a Mindset/Navigation skill):

```markdown
---
name: ai-kit-spec-execute-gsd
description: Dispatches a GSD (Get Sh*t Done) phase's execution to the best available model/CLI, honoring GSD's own native tiering when configured and falling back to cross-AI dispatch or an explicit substitution notice otherwise. Use when ai-kit-spec-execute detects a GSD-managed plan (.planning/ directory present) and needs to actually run gsd-execute-phase (or equivalent) with a resolved model.
---

# ai-kit-spec-execute-gsd

## Step 0: Resolve the shim path (mirrors ai-kit-spec-review/SKILL.md's own Step 0.7 point 0)

This skill is not guaranteed a `CLAUDE_PLUGIN_ROOT` — take the FIRST existing of, in order (same
three-candidate pattern `ai-kit-spec-review/SKILL.md`'s Step 0.7 point 0 already uses for its own
`ai-kit-spec.py`):

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-execute-gsd}" \
         "$HOME/.claude/skills/ai-kit-spec-execute-gsd" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -d "$d" ] && { GSD_SKILL_DIR="$d"; break; }
done
GSD_SHIM="$GSD_SKILL_DIR/ai-kit-spec-gsd.py"
```

Every later step's `python3 $GSD_SHIM <subcommand> ...` invocation in this skill uses this
resolved `$GSD_SHIM` path — never a bare `python3 -m ai_kit_spec_gsd.cli` (iteration-4 review
finding 1: that only resolves when `ai_kit_spec_gsd` already happens to be on `sys.path`, which
running from an arbitrary GSD project cwd never guarantees).

**Also resolve `ai-kit-spec-review`'s own shim here** (iteration-5 review finding 9 — a prior
revision of this step left a bracketed placeholder, `<ai-kit-spec-review shim, Step 0.7>`, in two
later load-bearing commands instead of an actually-resolved path). This is the SAME literal
three-candidate discovery loop `skills/ai-kit-spec-review/SKILL.md`'s own Step 0.7 point 0 uses
for its own `ai-kit-spec.py`, run here a second time (a separate skill directory, a separate
resolution) with the SAME real variable names that skill's own body already uses:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-review}" \
         "$HOME/.claude/skills/ai-kit-spec-review" \
         "$(dirname "$GSD_SKILL_DIR")/ai-kit-spec-review"; do
  [ -d "$d" ] && { REVIEW_SPEC_SKILL_DIR="$d"; break; }
done
TOOLS_PY="$REVIEW_SPEC_SKILL_DIR/ai-kit-spec.py"
```

Every later step's reference to "the `ai-kit-spec-review` shim" means `python3 "$TOOLS_PY"
cache-path --kind quota` — this exact, resolved command, never a bracketed placeholder.

## Step 1: Resolve the dispatch decision via the CLI entrypoint

Run (concrete, runnable command — never call the underlying Python functions directly from this
skill's own prose):

```bash
GSD_CONFIG_PATH="$(python3 "$GSD_SHIM" config-path --cwd <cwd>)"
RESULT_JSON="$(python3 "$GSD_SHIM" resolve-dispatch --cwd <cwd> --phase-type <phase_type> \
  --config-path "$GSD_CONFIG_PATH" --target-dir <cwd> \
  --quota-path "$(python3 "$TOOLS_PY" cache-path --kind quota)" \
  --phase-prompt-file <phase's own prompt/context file path>)"
RUN_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])' <<< "$RESULT_JSON")"
```

**Capture `$RUN_ID` here** (iteration-5 review finding 5) — `resolve-dispatch` generates exactly
one `run_id` for this whole invocation (threaded through every write it makes) and returns it as
`result["run_id"]`. Every `write-workflow-key`/`clear-workflow-key` call later in this SAME wave
(Step 2 below) MUST pass `--run-id "$RUN_ID"` — never omit it or let a later call generate its
own — so a runtime-quota-hook write and this wave's resolve-dispatch write, if both fire, share
exactly one backup file, not two.

Where:
- `<cwd>` is this skill's own entry-precondition project root (see above). `target_dir` is the
  SAME value — GSD's own project working tree is the write-confinement target for any
  execute-mode CLI dispatch (Task 3's `build_cross_ai_dispatch`).
- `$GSD_CONFIG_PATH` comes from the `config-path` subcommand (Task 4), never a hand-written
  `.planning/config.json` string — once Task 1/Task 2 Step 0 confirms GSD's workstream-scoped
  path convention, pass `--workstream-id <id>` to this same subcommand instead of changing this
  step's own logic.
- `<phase_type>` is read from the GSD phase's own docs (e.g. its `NN-CONTEXT.md`'s declared
  category — planning/discuss/research/execution/verification/completion per design spec §7);
  infer it there, never guess.
- `--quota-path` loads/refreshes LIVE quota before resolving (iteration-4 review finding 2) — the
  `resolve-dispatch` subcommand itself calls `refresh_quota_cache` and passes the result into
  `resolve_gsd_dispatch`'s `quota=` argument; this skill never has to do that separately.
- `--phase-prompt-file` lets `resolve-dispatch` compute a real `required_context` estimate
  (`adapter.estimate_required_context`, Task 4) instead of a hardcoded `0` — see Global
  Constraints' second scope-boundary bullet for what this does and does not filter on today.

`$RESULT_JSON` is one JSON object — the exact dict `adapter.resolve_gsd_dispatch` returns (Task
4), now including `cli`/`key`/`provenance` on every mode (iteration-4 review finding 4, and
iteration-6 review finding — every mode, including both `fallback_notice` reasons, always carries
all three, `None` where not applicable, so unconditional extraction below never `KeyError`s) plus
this wave's own `run_id` (iteration-5 review finding 5). If `mode == "fallback_notice"` and
`message` mentions "malformed" (iteration-4 review finding 7 — `resolve-dispatch` aborts rather
than mutating a broken config), print the message and STOP — do not proceed to Step 2/3 at all for
that case.

**Extract every field this skill's later steps reference into real shell variables here
(iteration-6 review, HIGH finding — corrected: no bracketed placeholder like
`<result.cross_ai_command>` may survive into the shipped SKILL.md; every reference below is one of
these real variables)**:
```bash
RESULT_MODE="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["mode"])' <<< "$RESULT_JSON")"
RESULT_KEY="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("key") or "")' <<< "$RESULT_JSON")"
RESULT_CLI="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("cli") or "")' <<< "$RESULT_JSON")"
RESULT_PROVENANCE="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("provenance") or "")' <<< "$RESULT_JSON")"
RESULT_MESSAGE="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("message") or "")' <<< "$RESULT_JSON")"
# mode-specific fields -- empty string when the current mode doesn't carry them, never an error:
RESULT_CROSS_AI_COMMAND="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("cross_ai_command") or "")' <<< "$RESULT_JSON")"
RESULT_PROVIDER="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("provider") or "")' <<< "$RESULT_JSON")"
```
Its `$RESULT_MODE` drives Step 2 below.

## Step 2: Act on the dispatch mode

- `native_tier`, `written=False`: GSD's own config already covered this phase type via a genuine
  PER-PHASE `model_overrides[phase_type]` entry (a genuine prior user choice — see Task 2's
  ownership-marker check, `override_is_adapter_owned`, which `resolve-dispatch` already applies
  before returning this; a project-wide `model_profile`/`models` default alone does NOT trigger
  this case — iteration-5 review finding 10) — nothing to write; proceed to Step 3.
  `result["provenance"]` is `"existing_gsd_config"` here, and `result["cli"]` now names the ACTUAL
  configured runtime (never a fabricated `None`) — Step 3 reads it directly, it is not the
  native-current-runtime case below (that case is instead keyed on `result["cli"] is None`, a
  resolved CANDIDATE whose own `cli` field is `None`).
- `native_tier` (either `written` value): the resolved dispatch mode is NOT a cross-AI mode — run
  the mode-transition cleanup below before proceeding to Step 3, in case a PRIOR run of this
  project left an adapter-owned cross-AI hook active that this run's own resolution superseded.
- `native_tier`, `written=True`: the CLI call already wrote the resolved model into
  `.planning/config.json`'s `model_overrides[phase_type]` AND, whenever needed, GSD's own
  `runtime` key (iteration-4 review finding 5 — a model override alone does not select which
  vendor CLI executes it), taking a per-run backup first (Task 2) — re-read the config before
  Step 3 so GSD's own execution entry point picks up the new override on its next read.
  `result["cli"]`/`result["key"]` name the winning candidate.
- `cross_ai_hook`: thread the config write through `write-workflow-key`, capturing each call's
  own JSON output and feeding it into the NEXT call's `--config-json` (iteration-4 review finding
  11 — two writes against the same stale snapshot can have the second discard the first's key).
  `--value-json` takes a JSON literal, not a bare string (iteration-5 review finding 6 — a plain
  `--value` would write the Python string `"true"` for a boolean flag instead of the real JSON
  `true`), and `--run-id "$RUN_ID"` is the SAME id Step 1 captured (iteration-5 review finding 5):
  ```bash
  UPDATED="$(python3 "$GSD_SHIM" write-workflow-key --config-path "$GSD_CONFIG_PATH" \
    --config-json "$(cat "$GSD_CONFIG_PATH" 2>/dev/null || echo '{}')" \
    --key cross_ai_command --run-id "$RUN_ID" \
    --value-json "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$RESULT_CROSS_AI_COMMAND")")"
  ```
  (exact key name confirmed by Task 1 Step 2 — update this line if Task 1 found a different
  name). If Task 1 Step 2 found `workflow.cross_ai_execution` is a SEPARATE required enable flag
  (not just the presence of `cross_ai_command`), ALSO run:
  ```bash
  UPDATED="$(python3 "$GSD_SHIM" write-workflow-key --config-path "$GSD_CONFIG_PATH" \
    --config-json "$UPDATED" --key cross_ai_execution --run-id "$RUN_ID" --value-json true)"
  ```
  — note `--config-json "$UPDATED"` is the FIRST call's own output, not a re-read of
  `$GSD_CONFIG_PATH` from disk (which may not reflect the first write yet if the write is
  buffered) and never the ORIGINAL pre-write config either. Until Task 1 confirms one way or the
  other, run both defensively: setting an already-true/unused flag is harmless, but leaving a
  required one unset would silently drop the whole cross-AI dispatch path. `result["cli"]`/
  `result["key"]` name the winning external candidate for Step 3's tooling detection.
- `native_enum`: print `result["message"]` (the precision-loss notice from Task 3 Branch B) to
  the user, then write `result["provider"]` via the SAME threaded `write-workflow-key` pattern
  above (`--value-json "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$RESULT_PROVIDER")"`,
  `--run-id "$RUN_ID"`), key name `<native-runtime-enum key name confirmed by Task 1 Step 3>` —
  design spec §7 confirms this is a *different* key than `cross_ai_command` above; never conflate
  the two. `result["cli"]`/`result["key"]` still name the winning candidate for Step 3.
- `fallback_notice`: **iteration-6 review, CRITICAL finding, two independent reviewers — this
  mode's TWO possible reasons need DIFFERENT handling; the previous revision treated both
  identically and silently skipped the resumable-state/auto-wake path for genuine quota
  exhaustion discovered at PROBE time (Step 1), not just for a runtime dispatch failure (Step
  4).** Check `result["message"]` for which reason `resolve_gsd_dispatch` gave:
  - Message contains `"no configured candidate at all"`: the config genuinely has zero
    `[[reviewers]]` entries — nothing was ever available to try, this is NOT a quota-exhaustion
    case. Print the message to the user, proceed to Step 3 (generic tool detection only, no
    resumable state, no wake — there is nothing to wait FOR).
  - Message contains `"no quota-available candidate in the ladder"`: this IS a genuine
    quota-exhaustion case — every configured candidate was already unavailable at PROBE time,
    before any real dispatch was even attempted. This is functionally identical to Step 4's
    "every candidate in the ladder has now been tried and excluded" terminal case, just reached
    one step earlier (at Step 1/2 instead of after a runtime failure) — treat it EXACTLY the
    same way: skip Step 3's dispatch entirely, write resumable state via `write-resumable-state`
    (Task 4) with `candidates_tried: []` (nothing was ever dispatched this wave — the exhaustion
    was discovered at the probe, not mid-escalation) and the SAME `--run-id "$RUN_ID"`, then
    schedule the SAME hourly `CronCreate` auto-wake job Step 4 describes below. Do NOT proceed to
    Step 3 or let GSD's default silently run in this case — design spec §10/§12 requires the
    all-candidates-exhausted case to always resolve to a wait-and-retry, never a silent
    fall-through to GSD's default, regardless of which step in this skill discovers the
    exhaustion.
  Either way: there is no candidate to resolve `cli` from in this mode. This mode is also NOT a
  cross-AI mode — run the mode-transition cleanup below before whichever of the two paths above
  applies.

**Mode-transition cleanup (iteration-5 review finding 6)** — run this whenever the resolved
`mode` is `native_tier` or `fallback_notice` (i.e. NOT `cross_ai_hook`/`native_enum`), BEFORE
proceeding to Step 3, so a stale adapter-owned cross-AI hook from a PRIOR run of this project
never stays silently active once a LATER run resolves a different dispatch mode. Never touches a
value the user set by hand — `clear-workflow-key` is a no-op unless the key is adapter-owned
(Task 2's `clear_workflow_key_if_adapter_owned`):
**iteration-6 review, MEDIUM finding — the third loop element below is a real key NAME, not a
runtime value; it MUST be replaced with Task 1 Step 3's literal confirmed native-runtime-enum key
before this SKILL.md file is written to disk (Task 5's own implementation step, not something the
executing agent fills in later) — never ship the bracketed placeholder itself inside this `for`
loop. If Task 1 Step 3 found no such key exists at all (Branch B was never reached, or the enum
key concept doesn't apply), drop that third loop element entirely rather than leaving a
placeholder that would be passed as a literal `--key` value to a real config-mutating
subcommand:**
```bash
CURRENT_CONFIG_JSON="$(cat "$GSD_CONFIG_PATH" 2>/dev/null || echo '{}')"
for KEY in cross_ai_command cross_ai_execution "<REPLACE WITH TASK 1 STEP 3's REAL CONFIRMED KEY NAME AT SKILL.md WRITE TIME -- e.g. native_runtime -- OR DELETE THIS THIRD ELEMENT IF NO SUCH KEY EXISTS>"; do
  CURRENT_CONFIG_JSON="$(python3 "$GSD_SHIM" clear-workflow-key --config-path "$GSD_CONFIG_PATH" \
    --config-json "$CURRENT_CONFIG_JSON" --key "$KEY" --run-id "$RUN_ID")"
done
```

## Step 3: Prepare confirmed-only tooling guidance, then dispatch GSD's own execution entry point

Resolve the CLI identity to prepare tooling guidance for (iteration-4 review finding 9 — the
native/current-runtime path must NOT skip tooling guidance just because there is no external
process to detect):
- `native_tier` with `provenance == "existing_gsd_config"`: `result["cli"]` is now ALWAYS the
  ACTUAL configured runtime identity (iteration-5 review finding 10 — `resolve_active_runtime`'s
  real value, or `"claude"` only when that key is genuinely unset — never a hardcoded/fabricated
  `None`). Use `--cli "$RESULT_CLI"` directly; never assume Claude by omission here — a project
  actively running through `codex`/`gemini` gets `codex`/`gemini`-flavored tooling guidance, not
  Claude's.
- `native_tier` (any provenance) with `result["cli"] is None`: this is the native/current-runtime
  CANDIDATE case (a resolved candidate whose own `cli` field is `None`, e.g. this repo's own
  "opus-native"-shaped entries) — dispatch runs as the CURRENT session itself (design spec §6),
  whose real CLI identity is `"claude"` (Claude Code, an officially supported CodeGraph client per
  design spec §9). Use `--cli claude` below, never skip tooling preparation for this case.
- Every other mode: use `result["cli"]` directly.
- `fallback_notice`: no candidate was resolved at all — omit `--cli` (the `prepare-tooling`
  subcommand still runs generic `rg`/`fd`/`bat`/`eza`/`AGENTS-TOOLING.md` detection with no
  CLI-specific CodeGraph guidance, since there is no CLI identity to check registration for).

```bash
GUIDANCE="$(python3 "$GSD_SHIM" prepare-tooling --cli "$RESULT_CLI" --target-dir <cwd>)"  # RESULT_CLI is "" (empty) for fallback_notice -- prepare-tooling treats an empty/absent --cli exactly like an omitted one (generic detection only)
```

This one subcommand call (Task 4) runs, in order: `detect_tool_availability()`,
`resolve_agents_tooling_path()`, `ensure_codegraph_registered(cli)` (skipped when `--cli` is
omitted), and — only if that confirms registration — `build_codegraph_index_command(target_dir)`
with a minimum `CODEGRAPH_INDEX_TIMEOUT_SECONDS` (15s) timeout, THEN
`build_tooling_guidance(...)`, printing the resulting guidance text to stdout. Design spec §9's
ordering guarantee (the orchestrator builds the index BEFORE dispatch, the dispatched subagent
only ever reads it via `codegraph_explore`) is preserved because this all happens before the
dispatch below.

**Append `$GUIDANCE` to the phase's own prompt/context FILE on disk IDEMPOTENTLY** (iteration-4
review finding 12 — every prior revision of this step appended unconditionally, corrupting the
phase file with duplicate guidance blocks on a retried/resumed run). Before appending, check for
a marker this skill itself owns:

```bash
MARKER="<!-- ai-kit-spec-execute-gsd:tooling-guidance -->"
if ! grep -qF "$MARKER" "<phase prompt/context file path>"; then
  printf '\n%s\n%s\n' "$MARKER" "$GUIDANCE" >> "<phase prompt/context file path>"
fi
```

Writing it into the file (not passing it as a separate dispatch parameter) is what guarantees it
reaches the phase content regardless of which dispatch mode Step 2 chose (`native_tier` runs
through GSD's own subagent mechanism, which reads this same file; `cross_ai_hook` delivers this
same file's content to `cross_ai_wrapper.py`'s stdin, per Task 1's confirmed prompt-delivery
contract). Never fabricate guidance for a tool/registration that wasn't confirmed present this
session — `prepare-tooling` already enforces that.

Dispatch GSD's own execution entry point (the command Task 1 Step 4.5 confirmed FOR BOTH
BRANCHES, e.g. `gsd-execute-phase <phase_id>`) via the `dispatch-phase` subcommand (Task 4,
iteration-5 review finding 7 — never call `ai_kit_spec.dispatch.dispatch_with_heartbeat` as a
bare Python function from this skill's own prose, exactly like every other operation in this
plan):

```bash
DISPATCH_RESULT_JSON="$(python3 "$GSD_SHIM" dispatch-phase \
  --dispatch-command "<GSD's own execution command for phase_id, e.g. gsd-execute-phase <phase_id>>" \
  --prompt-file "<phase prompt/context file path>" \
  --heartbeat-interval 30 --timeout 1800)"
```

`--prompt-file` is the phase's own prompt/context file (now including this step's
idempotently-appended guidance) — its content is piped to the dispatched command's stdin. Run
from the working directory Task 1 Step 4.5 recorded. This applies uniformly across ALL FOUR
dispatch modes — it is THIS skill's own subprocess boundary with GSD itself, distinct from (and
outside of) whatever `cross_ai_wrapper.py` does internally when GSD's own `cross_ai_hook` mode
later shells out to it. The `30`/`1800` defaults match `cross_ai_wrapper.py`'s own defaults (Task
3) — keep them in sync if either changes. `$DISPATCH_RESULT_JSON` is the exact
`{"returncode", "stdout", "stderr", "timed_out"}` dict `dispatch_with_heartbeat` itself returns —
parse it; Step 4 below refers to its fields as `result["..."]`.

## Step 4: Classify dispatch outcome; escalate a runtime quota failure within the same wave BEFORE writing resumable state or scheduling any wake

`$DISPATCH_RESULT_JSON` (Step 3) is `{"returncode", "stdout", "stderr", "timed_out"}`. Maintain a
running `candidates_tried` list for this wave, starting with `[result["key"]]` from Step 1/2's
resolved candidate (skip this whole step's escalation loop, proceeding straight to success/failure
handling, when `result["key"]` is `None` — the `existing_gsd_config`/`fallback_notice` cases have
no candidate to exclude and retry). Classify, in this order:

1. `timed_out` is True: a real failure, never a quota signal — surface it to the user directly
   and stop (design spec §12: never silently retry a non-quota failure disguised as quota-wait).
2. `returncode != 0`: write `result["stdout"]`/`result["stderr"]` to two temp files and call the
   `classify-failure` subcommand (Task 4, iteration-5 review finding 7 — never call
   `ai_kit_spec_gsd.adapter.classify_dispatch_failure` as a bare Python function from this skill's
   own prose). **Real, concrete extraction — no bracketed placeholder (iteration-6 review, HIGH
   finding)**:
   ```bash
   DISPATCH_STDOUT_FILE="$(mktemp)"
   DISPATCH_STDERR_FILE="$(mktemp)"
   python3 -c 'import json,sys; print(json.load(sys.stdin)["stdout"], end="")' \
     <<< "$DISPATCH_RESULT_JSON" > "$DISPATCH_STDOUT_FILE"
   python3 -c 'import json,sys; print(json.load(sys.stdin)["stderr"], end="")' \
     <<< "$DISPATCH_RESULT_JSON" > "$DISPATCH_STDERR_FILE"
   python3 "$GSD_SHIM" classify-failure --stdout-file "$DISPATCH_STDOUT_FILE" \
     --stderr-file "$DISPATCH_STDERR_FILE"
   ```
   This prints one of `auth`/`quota`/`other` on stdout (NEVER test membership in
   `ai_kit_spec.quota._UNAVAILABLE_SIGNALS` directly here; that tuple mixes transient-quota AND
   persistent-auth/entitlement phrases, and
   an unqualified membership test would misclassify a real auth failure as quota exhaustion and
   schedule a futile hourly retry for it):
   - `"auth"`: a persistent, never-retry-worthy failure — surface it to the user directly and
     stop. Never write resumable state or schedule a wake for this case.
   - `"quota"` (iteration-4 review finding 2 — escalate WITHIN the wave before ever writing
     resumable state): append the just-failed candidate's key to `candidates_tried`, then
     RE-RUN Step 1's `resolve-dispatch` call with `--exclude-key <that key>` appended (repeat
     `--exclude-key` for every key accumulated so far across this loop) AND **`--run-id "$RUN_ID"`
     — the SAME id Step 1 originally captured, never omitted** (iteration-6 review, HIGH finding —
     omitting it here makes `resolve-dispatch` generate a NEW run_id for this re-invocation,
     silently producing a second backup file within what is still logically one wave/run, exactly
     the "one run_id, one backup per run" violation the shared-`run_id` mechanism exists to
     prevent) and repeat Steps 2-4 for the newly-resolved candidate. Only once a re-run itself
     returns `mode == "fallback_notice"`
     (every quota-available candidate in the ladder has now been tried and excluded — Task 4's
     `resolve_gsd_dispatch` already walks the whole ladder per call, so THIS loop only needs to
     fire once per genuinely EXHAUSTED wave, not once per candidate) does this skill write
     resumable state and schedule a wake:
     write resumable state via the `write-resumable-state` subcommand (Task 4) to
     `--path "$(python3 "$TOOLS_PY" cache-path --kind quota | xargs dirname)/gsd-resume-${PROJECT_KEY}-${phase_id}.json"`
     where `PROJECT_KEY` is a filesystem-safe identifier derived from `cwd` (e.g.
     `python3 -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:12])" "$cwd"`)
     — deriving the resume-state directory from the quota cache path's own directory reuses
     `ai_kit_spec.cache.cache_base`'s already-correct `$HOME`/`XDG_CACHE_HOME` resolution with no
     hand-written `"~"` literal, and the `PROJECT_KEY` prefix keeps two different projects with
     the same `phase_id` from colliding on one state file. State content (the `--state-json`
     argument): `{"framework": "gsd", "project_path": cwd, "config_path": gsd_config_path,
     "phase_id": phase_id, "candidates_tried": [...the FULL accumulated list from this wave...],
     "iteration": ...}`. Then schedule a `CronCreate` job: hourly interval, prompt `"re-check
     quota via probe-quota and, once restored, resume ai-kit-spec-execute-gsd from <resume state
     path>"`. `CronCreate` jobs are session-scoped (confirmed, design spec §10) — they vanish if
     the session exits, only fire while the session is idle, and recurring jobs auto-expire after
     7 days; tell the user this explicitly, it is not a true shutdown-and-resume mechanism.
   - `"other"`: a real, non-quota, non-auth failure — surface it directly, never write resumable
     state or schedule a wake for this case.
3. `returncode == 0`: success.
```

- [ ] **Step 2: Run skill-judge against this skill**

Invoke `skill-judge` on `skills/ai-kit-spec-execute-gsd/SKILL.md`. Fix any finding before
proceeding — in particular check description quality (WHAT/WHEN/keywords) and that Step 2's
dispatch-mode branching reads as a decision tree, not vague prose.

- [ ] **Step 3: Register the new skill in the repo's README**

Add `ai-kit-spec-execute-gsd` to `README.md`'s skills table (alongside the existing
`ai-kit-spec-*` rows, `README.md` lines 28–35), one row, matching that table's existing
column format (name/type/description).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs(ai-kit-spec-execute-gsd): add SKILL.md, register in README"
```

---

### Task 6: Router stub — `ai-kit-spec-execute`'s framework detection

**Files:**
- Create: `skills/ai-kit-spec-execute/SKILL.md`
- Create: `skills/ai-kit-spec-execute/detect_framework.py`
- Test: `tests/test_ai_kit_spec_gsd.py` (or a new `tests/test_ai_kit_spec_execute.py` — either is fine, this task creates whichever doesn't already exist from Plan 3 running first; if Plan 3 already created `tests/test_ai_kit_spec_execute.py`, add to it instead of creating a duplicate. Whichever file this task ends up using, if it is a NEW file not already registered by Task 2 Step 5, apply that same Makefile/`.pre-commit-config.yaml` registration to it too.)

**Interfaces:**
- Produces: `detect_framework(cwd: str, isfile_fn=os.path.isfile, isdir_fn=os.path.isdir) -> str` — returns `"gsd"` when `.planning/PROJECT.md` exists, `"superpowers"` when a plan file matching superpowers' own naming convention is findable (Plan 3 defines the exact check), `"unknown"` otherwise.

- [ ] **Step 1: Write the failing tests**

If this task's test file is `tests/test_ai_kit_spec_gsd.py` (per the **Files** note above), add
this import alongside the file's existing imports (the bootstrap block itself, added in Task 2
Step 1, already puts `skills/ai-kit-spec-execute` on the search path — do not repeat the
`sys.path.insert` lines, only add this one import line):

```python
import detect_framework
```

If this task instead uses a NEW `tests/test_ai_kit_spec_execute.py` file (per the **Files** note
above), that file needs its OWN copy of the same three-line `sys.path.insert` bootstrap Task 2
Step 1 defined (all three lines — this file also exercises `ai_kit_spec_gsd` indirectly through
future GSD-integration tests Plan 3 may add) followed by `import detect_framework`.

```python
class TestDetectFramework(unittest.TestCase):
    def test_detects_gsd_via_planning_project_md(self):
        result = detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: p == "/repo/.planning/PROJECT.md",
            isdir_fn=lambda p: False)
        self.assertEqual(result, "gsd")

    def test_unknown_when_no_markers_present(self):
        result = detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: False, isdir_fn=lambda p: False)
        self.assertEqual(result, "unknown")
```

**Note on which test module Step 2/4/8's commands target (iteration-4 review finding 14): every
`python3 -m unittest` invocation below MUST target `tests.test_ai_kit_spec_execute` if THIS
task's own "Files" note above resulted in that new file being created, or
`tests.test_ai_kit_spec_gsd` if it added to the existing one instead — the commands shown use
`tests.test_ai_kit_spec_gsd` as the default (existing-file) case; substitute the other module
name throughout Steps 2/4/8 if this task created the new file.**

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestDetectFramework -v 2>&1 | tail -10
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Framework detection for ai-kit-spec-execute's router. GSD's marker is confirmed
(.planning/PROJECT.md, per skills/ai-kit-spec-review-checklist/references/frameworks/gsd.md).
superpowers' marker is defined by Plan 3 (ai-kit-spec-execute-superpowers) -- this stub only
wires the GSD branch; Plan 3 fills in the superpowers check in this same function.

Also runnable directly (iteration-4 review finding 8 -- a zero-context agent needs a concrete
command, not just a Python function to `import`): `python3 detect_framework.py <cwd>` prints the
result on stdout."""
import os
import sys


def detect_framework(cwd: str, isfile_fn=os.path.isfile, isdir_fn=os.path.isdir) -> str:
    if isfile_fn(os.path.join(cwd, ".planning", "PROJECT.md")):
        return "gsd"
    return "unknown"


if __name__ == "__main__":
    print(detect_framework(sys.argv[1]))
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestDetectFramework -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Write the router `SKILL.md` stub**

```markdown
---
name: ai-kit-spec-execute
description: Routes execution of an already-generated plan/phase to the framework-specific ai-kit-spec-execute adapter (GSD or superpowers), based on which framework produced the plan. Use when the user asks to execute/run/implement a plan or phase and the generating framework isn't already known.
---

# ai-kit-spec-execute

1. Run `detect_framework(cwd)` from `detect_framework.py`.
2. `"gsd"` → delegate to `ai-kit-spec-execute-gsd`.
3. `"superpowers"` → delegate to `ai-kit-spec-execute-superpowers` (see that skill's own SKILL.md).
4. `"unknown"` → ask the user which framework generated this plan; do not guess.
```

- [ ] **Step 6: Run skill-judge against this skill**

Invoke `skill-judge` on `skills/ai-kit-spec-execute/SKILL.md` (design spec §13 requires
skill-judge against all 3 new skills — `ai-kit-spec-execute`, `-gsd`, `-superpowers` — this
covers the router; `-gsd` was covered in Task 5; `-superpowers` is Plan 3's responsibility). Fix
any finding before proceeding.

- [ ] **Step 7: Register the new skill in the repo's README**

Add `ai-kit-spec-execute` to `README.md`'s skills table (`README.md` lines 28–35), alongside the
`ai-kit-spec-execute-gsd` row Task 5 Step 3 already added, matching the table's existing
name/type/description column format.

- [ ] **Step 8: Run the repository's REAL full quality gate and commit (iteration-4 review finding 16)**

Not just this plan's own new test module — `make validate` (→ `uv run pre-commit run --all-files`,
the repository's actual quality gate, confirmed by reading `Makefile`) runs ruff/pylint/pyright/
vulture/shellcheck/py-compile/unittest across every hook, now scoped to include this plan's new
source directories per Task 2 Step 5's `.pre-commit-config.yaml` edits:

```bash
make validate
git add -A
git commit -m "feat(ai-kit-spec-execute): add router skill and GSD framework detection, register in README"
```

If `make validate` surfaces findings in files this plan touched, fix them before this commit —
this is the real gate a CI run would apply, not a narrower stand-in.

---

### Task 7: End-to-end smoke test against a real GSD phase

**Files:** Modify: this plan file (`docs/superpowers/plans/2026-08-29-ai-kit-spec-execute-gsd.md`), Step 2 below records the outcome. Modify (CONDITIONAL — only if Step 1's real-config proof or Step 1.5's real dispatch check finds a live divergence from Task 1's recorded contract): `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_config.py`, `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_cross_ai.py`, `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/adapter.py` (iteration-5 review finding 18 — Step 1's own text already requires fixing `gsd_config.py`'s schema assumptions "before considering this plan complete" if the real install diverges, and Step 2's text already requires recording "any discrepancy found and fixed in `gsd_cross_ai.py`/`adapter.py`" — this Files block must not silently promise zero source-file changes when the task's own steps conditionally require them). If any conditional fix is made, add its own commit (with its own test update) before Step 3's final commit — never fold an undocumented source change into the "chore" commit message Step 3 already specifies.

- [ ] **Step 1: Run the full adapter against a real (or realistic scratch) GSD phase**

Using the same GSD install from Task 1's spike, run `ai-kit-spec-execute-gsd`'s full flow
(Task 5's SKILL.md steps) against one real, small phase. Confirm:
- The correct dispatch mode is chosen (native_tier if config already has an override, else
  native_tier-written if the top candidate is native-vendor and nothing was configured, else
  cross_ai/fallback per Task 4's logic).
- If `fallback_notice` fires, the message actually reaches the user/log before dispatch proceeds.
- If `native_tier` with `written=True` fires, confirm a per-run `.planning/config.json.ai-kit-spec-execute-gsd.<run-id>.bak` was created (Task 2's per-run backup naming, iteration-4 review finding 6) and the live config now carries the new override, plus the `_ai_kit_spec_execute_gsd` ownership marker (Task 2) and, when the candidate's vendor required it, the updated `runtime` key (Task 2/4, iteration-4 review finding 5), AND (the real-config
  proof Task 2 Step 0 flagged as still owed) confirm the SAME model id actually reaches GSD's own
  execution agent for this phase — run GSD's own execution entry point after the write and check
  its own logs/output/prompt-preamble for the written model id, not just that the JSON key was
  written. If it does NOT reach the agent, this proves Task 2's `resolve_native_tier`/
  `write_native_tier_override` schema assumptions (phase-type-keyed `model_overrides`,
  no-reload-required) are wrong for the real install — fix `gsd_config.py` per Task 2 Step 0's
  checklist before considering this plan complete, do not just note the discrepancy and move on.
- Heartbeat output appears for any external-CLI dispatch path taken (in `cross_ai_wrapper.py`'s
  stderr for the `cross_ai_hook` mode; from `dispatch_with_heartbeat` wrapping GSD's own
  execution command directly, per Task 5 Step 3, for every mode).

- [ ] **Step 1.5: External-CLI dispatch coverage — real `codex` execute-mode dispatch, not a mock (iteration-5 review finding 4, design spec §13)**

Design spec §13 requires end-to-end coverage of a REAL external-CLI dispatch, not a mocked command
builder — a synthetic candidate with a mocked `execute_command_fn` (this step's own prior
revision) does not satisfy that requirement. `codex` is this repo's ONLY real, live-verified
execute-mode builder today (Global Constraints — `cursor-agent`/`opencode`/`grok`/`claude` all
raise `ValueError` from `build_execute_command`), and `codex` is ALSO a member of
`NATIVE_TIER_VENDORS` — so a real, naturally-ranked candidate can never resolve to `cross_ai_hook`
through `adapter.resolve_gsd_dispatch`'s own selection logic (native tiering always claims a
`NATIVE_TIER_VENDORS` candidate first, by design — see `adapter._is_native`). That selection
behavior is correct and is NOT what this step tests — this step instead exercises the REAL
external-CLI dispatch MACHINERY directly and for real, using `codex` as the live CLI, never a
mock/fake `execute_command_fn`:

1. Call `ai_kit_spec.commands.build_execute_command("codex", target_dir=<a real scratch
   directory outside /tmp — see that builder's own docstring caveat about /tmp confinement>)`
   directly (its REAL default builder, no override) and confirm it returns the real
   `codex exec --sandbox workspace-write -C <dir> -m {model}` template.
2. Invoke `ai_kit_spec_gsd.cross_ai_wrapper.main(["--cli", "codex", "--model", "<a real
   available codex model id>", "--target-dir", "<the same scratch directory>"], stdin_read_fn=lambda:
   "Reply with exactly: hello world")` — a trivial, side-effect-free prompt, not a real GSD phase
   — with its DEFAULT `dispatch_fn`/`execute_command_fn` (no mocks): this is the exact command
   `cross_ai_hook` mode would run in production. Confirm: exit code `0`, real codex stdout
   captured on the wrapper's own real stdout, and any heartbeat lines land on stderr only, never
   stdout (Task 3 Branch A's own contract).
3. Record BOTH facts together in Step 2's outcome note, never conflated: (a) this proves the
   WRAPPER's real dispatch of a real external CLI works end-to-end, and (b) it does NOT prove
   `adapter.resolve_gsd_dispatch` itself ever selects `cross_ai_hook` for a real, naturally-ranked
   candidate today.

**Explicit, permanent scope statement (iteration-6 review, CRITICAL finding, two independent
reviewers — corrected here, not just re-asserted)**: design spec §13 requires a full
selection→dispatch→heartbeat→completion loop through a REAL external CLI. That full loop IS
completely satisfied today for the `native_tier` dispatch mode (Step 1 above already exercises
real selection through `resolve_gsd_dispatch` end-to-end for whatever candidate naturally wins,
and `codex` — this repo's only live-verified execute-mode builder — is also `NATIVE_TIER_VENDORS`-
eligible, so a real project resolves to `native_tier` for it today, genuinely end-to-end, no mock
anywhere). It is **structurally impossible**, not merely untested, to also exercise the FULL loop
through `cross_ai_hook`/`native_enum` with a real (non-mocked) external CLI using ONLY this
repo's current code: `adapter._is_native` checks CLI membership in `NATIVE_TIER_VENDORS`, `codex`
is a member, and `codex` is the ONLY execute-mode builder that isn't a `ValueError` stub — so
ANY real candidate resolvable through `resolve_gsd_dispatch`'s own selection that also has a real
dispatch mechanism will ALWAYS resolve to `native_tier`, never `cross_ai_hook`, by design (native
tiering intentionally wins over cross-AI dispatch whenever it's available — this is the correct,
intended precedence, not a bug this plan should route around). Proving the cross-AI FULL loop
with a real external CLI requires Foundation to ship a second execute-mode builder for a vendor
OUTSIDE `NATIVE_TIER_VENDORS` — that is explicitly Plan 1 (Foundation)'s scope, not this plan's.
Until then, this task's Step 1.5 above is the closest honest proof available: real selection
proof for `native_tier` (Step 1, this task) PLUS real dispatch-machinery proof for
`cross_ai_hook`'s wrapper in isolation (Step 1.5, items 1-2 above) — together these are the
maximum real-component coverage achievable today, and this plan does not claim more than that.
Record this exact reasoning in Step 2's outcome note, not just the two individual facts.

If `codex` genuinely cannot be invoked in this environment (e.g. no credentials available to this
task's runner), record that concretely as a blocking environment gap in Step 2's outcome note —
never silently substitute a mock and call this step satisfied.

Separately, Branch B's `native_enum` path (if Task 1 confirmed a closed enum) has no equivalent
"real CLI" concept to invoke directly — it is GSD's OWN internal runtime switch, not a command
this adapter dispatches itself. For that path, run `adapter.resolve_gsd_dispatch` directly against
a SYNTHETIC candidate list containing one candidate in Task 1's confirmed `_CLOSED_ENUM_PROVIDERS`
set, and confirm the `native_enum` result dict shape is well-formed and Task 5's
`write-workflow-key` threading (Step 2's dispatch-mode branch) round-trips it into a real scratch
`.planning/config.json` correctly — this remains unit/integration-level wiring proof, not proof
GSD itself executes via that provider end-to-end (recorded as such in Step 2 below).

- [ ] **Step 2: Record the outcome directly in this plan file**

Edit this plan file (append a dated `## Smoke Test Result` subsection here) recording: which
dispatch mode fired, whether it matched Task 1's recorded contract, any discrepancy found
and fixed in `gsd_cross_ai.py`/`adapter.py` as a result, AND Step 1.5's explicit scope note
(whether `cross_ai_hook`/`native_enum` end-to-end coverage remains a stated TODO pending a second
real execute-mode CLI, or whether Foundation shipped one in the meantime and this task's Step 1
was re-run against it — do not silently drop this note if that hasn't happened yet). Do not
consider this plan complete if the live run diverges from Task 1's recorded contract and that
divergence isn't both fixed and noted here.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore(ai-kit-spec-execute-gsd): smoke-test verified against a live GSD phase"
```
