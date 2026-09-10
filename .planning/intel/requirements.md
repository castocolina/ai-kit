# Requirements (from PRDs)

All 5 classified PRDs are represented below (`ai-kit-config-doctor`,
`ai-kit-multi-cli-runtime-support`, `ai-kit-opencode-provider-management`,
`ai-kit-tool-substitution-awareness-hook`, `ai-kit-usage-metrics-dashboard`).

(Note: this is a second re-run. The originally-reported 3-node cycle
(config-doctor → tool-substitution-awareness-hook → usage-metrics-dashboard
→ config-doctor) was broken in the prior run by removing
usage-metrics-dashboard's back-reference to config-doctor. A residual
2-node cycle then remained between tool-substitution-awareness-hook and
usage-metrics-dashboard. The user has since edited
`docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md` to also remove both
of its back-references to `ai-kit-tool-substitution-awareness-hook` (the
rtk-mechanism NOT-IN note and the command-family-mirroring note), replacing
them with generic "a separate, unnamed tool-substitution effort" phrasing
that no longer names the sibling PRD. Cycle detection was re-run fresh
against the current source files — not cached classification state — and
found no cycles: the cross-reference graph is now a DAG (`config-doctor` and
`tool-substitution-awareness-hook`/`opencode-provider-management` point
forward toward `multi-cli-runtime-support` and `usage-metrics-dashboard`,
both of which are sinks with no outgoing named PRD references). All 5 PRDs
are synthesized below. See `.planning/INGEST-CONFLICTS.md` for the full
cycle-detection trail.)

---

## REQ-config-doctor-diagnostic-checks
- source: docs/prds/ai-kit-config-doctor-v1.0-prd.md
- description: A read-only diagnostic pass across Claude Code, opencode, and Codex configuration implementing the 12-row Checks Catalog: Claude Code transcript retention, prompt-cache TTL, sandboxed Bash tool, OpenTelemetry; opencode session retention (informational-only, no real setting exists), `permission` block, `share` mode; Codex `sandbox_mode`, `features.hooks` (informational), `model_reasoning_effort` (community-sourced, lower-confidence-flagged), `history.persistence`; and a cross-runtime check for whether `rtk`'s Cursor integration is installed (folded in from the sibling `ai-kit-tool-substitution-awareness-hook` PRD's Non-Goals).
- acceptance:
  - Every row in the Checks Catalog is implemented as a read-only check showing current vs. recommended value.
  - Row #5 (opencode retention) is shown as informational-only, never offered as an apply action, since no real setting exists to change.
  - Row #10 (Codex reasoning effort) is visibly labeled with its lower-confidence sourcing in the UI.
  - A runtime not installed on this machine has its whole section skipped, not shown as failing checks.
  - No check's "current default" claim is presented with the same certainty as an officially-documented row unless it is one (confidence labeling constraint).
- scope: Claude Code, opencode, Codex, configuration audit, checks catalog

## REQ-config-doctor-review-screen
- source: docs/prds/ai-kit-config-doctor-v1.0-prd.md
- description: A dedicated interactive review screen presenting every check's current value, recommended value, and citation per runtime — explicitly not folded into `tools/statusline-doctor.py` (a different domain: that script's scope is the statusline renderer's own config validity, not runtime behavioral settings).
- acceptance:
  - Not folded into `tools/statusline-doctor.py` (dedicated screen, per PRD clarification).
  - A setting whose current value can't be determined is shown as "unknown," never silently treated as pass or fail.
  - One command surfaces every check across all installed runtimes in one screen.
- scope: review UI, diagnostic output, opencode/claude/codex

## REQ-config-doctor-apply-flow
- source: docs/prds/ai-kit-config-doctor-v1.0-prd.md
- description: A per-item, explicitly confirmed apply step for whichever checks the user chooses to change, reusing the atomic-write + minimal-surgical-edit pattern established in the sibling `ai-kit-opencode-provider-management` PRD — never a bulk "apply all" default.
- acceptance:
  - No check ever writes to config without an explicit, per-item user confirmation naming the exact change about to be made.
  - Applying a JSONC-format change (opencode) preserves every other byte of the file (reuses the sibling PRD's tested surgical-edit approach).
  - Security-relevant applies (`sandbox.enabled`, `permission` lockdowns, `sandbox_mode`) show their literal resulting config before writing, never inferred/summarized only.
- scope: apply flow, atomic write, confirmation, opencode JSONC / Codex TOML / Claude JSON

## REQ-multi-cli-install-single-branch
- source: docs/prds/ai-kit-multi-cli-runtime-support-v1.0-prd.md
- description: Harden `tools/install.sh`'s primary git-based fetch to clone only the target branch by adding `--single-branch` to the primary `git clone` call, without altering the tarball-fallback path or the already-cloned `git pull --ff-only` convergent-update path.
- acceptance:
  - `tools/install.sh`'s primary `git clone` call includes `--single-branch` alongside the existing `--branch "$REPO_BRANCH" --depth 1` flags.
  - The tarball-fallback path and the already-cloned `git pull --ff-only` path are verified unchanged (no diff to those lines).
  - The existing `--branch`/`--branch=` CLI override flags still work end-to-end with `--single-branch` added.
  - A new/updated `tests/test_install.sh` case asserts the `--single-branch` flag is present on the primary clone invocation.
- scope: install.sh, git clone, bootstrap fetch

## REQ-multi-cli-runtime-detection
- source: docs/prds/ai-kit-multi-cli-runtime-support-v1.0-prd.md
- description: Add runtime self-detection (which CLI/host process ai-kit is currently executing under: Claude Code, opencode, or codex) surfaced as a new optional `native_runtime` field on model-catalog entries that already have `cli: None`.
- acceptance:
  - A runtime-detection function `detect_current_runtime() -> str` returns one of `"claude"` / `"opencode"` / `"codex"` / `"unknown"`, confirmed empirically for at least Claude Code and opencode (codex confirmed if the research finds a viable signal; otherwise permanently `"unknown"`, documented as such).
  - `native_runtime` is a recognized, optional, literal-validated field in `model_catalog.py`'s schema (`_FIELD_TYPES` entry + a `_VALID_NATIVE_RUNTIME` set + a post-type-loop validation check, mirroring `name_declared_purpose`'s existing pattern including its check-ordering fix: literal-value check runs after the generic `_FIELD_TYPES` type-check loop).
  - A catalog entry with `cli: None` gets `native_runtime` set to the detected value; a catalog entry with a real `cli` value never gets `native_runtime` set.
  - When detection is inconclusive, the entry gets `native_runtime: "unknown"` and `execute_dispatch.py`'s existing `cli is None` in-process execution path is empirically confirmed unchanged (no new behavior gated on this value).
  - `ai-kit-spec-config/SKILL.md` is updated to document `native_runtime` labeling in the wizard's ranked candidate output, and passes a `skill-judge` review loop (no remaining Critical/Important finding, or score ≥ 96/120, no regression vs. pre-change baseline) before the task is marked complete.
- scope: runtime detection, model catalog, native_runtime field, execute_dispatch.py

## REQ-multi-cli-opencode-ui-research
- source: docs/prds/ai-kit-multi-cli-runtime-support-v1.0-prd.md
- description: Research-only task (no code changes) producing a written markdown report enumerating opencode's documented plugin hooks and assessing viability for status/sidebar-style output, to inform a future PRD.
- acceptance:
  - A written markdown research report exists (committed under `docs/`), enumerating every hook opencode documents, assessing each for sidebar/status-bar viability, cross-referencing the open feature request `anomalyco/opencode#5971` for maintainer signal, and giving an explicit recommendation (proceed with a specific hook-based prototype / wait for opencode to ship a real sidebar API / re-investigate later, no fixed trigger condition required).
- scope: opencode plugin hooks, research report, statusline UX

## REQ-opencode-provider-list-remove
- source: docs/prds/ai-kit-opencode-provider-management-v1.0-prd.md
- description: A new ai-kit skill (`ai-kit-opencode-providers`) to list config-based custom providers in `~/.config/opencode/opencode.jsonc`'s `"provider"` block and remove one by id via a string-literal-aware surgical brace-counting edit that preserves every other byte of the file, writing atomically (temp file + rename).
- acceptance:
  - `list` shows every entry under `opencode.jsonc`'s `"provider"` block (id, `npm`, `baseURL`), never the `apiKey` value.
  - `remove <id>` deletes exactly that provider's block; every other byte of the file (comments, unrelated providers, formatting) is verified byte-identical before/after via a diff in the test suite.
  - `remove <id>` on a non-existent id produces a clear no-op message, not a crash or silent success.
  - A provider whose `baseURL`/`apiKey` value contains a literal `{` or `}` character is removed correctly (pinned by a dedicated test fixture), proving the brace counter is string-literal-aware, not a naive byte count.
  - The write is atomic (temp file + rename) — a simulated failure mid-write never leaves a corrupted `opencode.jsonc`.
- scope: opencode.jsonc, provider block, JSONC editing, atomic file operations

## REQ-opencode-provider-cross-reference-check
- source: docs/prds/ai-kit-opencode-provider-management-v1.0-prd.md
- description: Before removing a provider, check whether the target provider id is referenced anywhere in ai-kit's own configuration (`.aikit/review-spec.toml`'s `cli`/`model` fields, and the cached model catalog) and warn if so — informational only, never blocking.
- acceptance:
  - Before removing, the tool checks `.aikit/review-spec.toml` and the cached model catalog (if present) for a reference to the target id and prints a warning naming every referencing location found; removal still proceeds (non-blocking) per the PRD's clarification.
  - `skills/ai-kit-opencode-providers/SKILL.md` is created, documenting both subcommands (`list`, `remove <id>`) with example output, and passes the `skill-judge` review loop (same bar as the sibling `ai-kit-multi-cli-runtime-support` PRD's Constraints section) before the work is marked complete.
- scope: cross-reference check, .aikit/review-spec.toml, model catalog, skill wiring

## REQ-tool-substitution-detection-composition
- source: docs/prds/ai-kit-tool-substitution-awareness-hook-v1.0-prd.md
- description: Pure, independently-testable live-detection and message-composition logic that checks which curated tool substitutions (rtk-driven: `cat`→`bat`, `grep`→`rg`, `find`→`fd`, `sed`→`sd`, `ls`→`eza`) are actually active on the current machine — cross-checking installed-binary state (`shutil.which`-style checks) against `tools-installer`'s `registry.toml` (`audience: ai|both`) and the active `rtk` version/config (`rtk init --show`) — narrowing the composed message to only genuinely active substitutions, never reciting catalog intent as if verified.
- acceptance:
  - The live-detection function reports `rtk` presence/version and, for each curated tool substitution, whether it's actually installed on this machine (not just registry-listed).
  - When `rtk` is not installed, the composed message either omits substitution content entirely or explicitly states none are active — never claims a substitution that isn't real.
  - A `registry.toml`-listed tool marked `audience: ai` that is NOT installed on this machine is excluded from the composed message.
  - Detection and composition are pure, independently unit-tested functions (rtk present/absent, various registry-tool present/absent combinations).
  - The curated substitution set (`cat`↔`bat`, `grep`↔`rg`, `sed`↔`sd`, `ls`↔`eza`, `find`↔`fd`) is the single source of truth for "family" membership — the sibling `ai-kit-usage-metrics-dashboard` PRD's command-family tagging reads/mirrors this same list rather than maintaining an independent, possibly-drifting copy.
- scope: live-detection, message composition, registry.toml, rtk, curated tool-substitution set

## REQ-tool-substitution-hook-wiring
- source: docs/prds/ai-kit-tool-substitution-awareness-hook-v1.0-prd.md
- description: A new Claude-Code-side `SessionStart` hook that wires the live-detection + message-composition logic into a real, registered hook firing on both `"startup"` and `"compact"` trigger sources, injecting the composed explanation via `hookSpecificOutput.additionalContext` — with opencode's lack of an equivalent injection explicitly documented as an accepted current-generation gap rather than silently absent.
- acceptance:
  - The `SessionStart` hook fires on both `"startup"` and `"compact"` trigger sources and injects the composed explanation via `hookSpecificOutput.additionalContext`.
  - The hook runs fast enough to not perceptibly delay session start or post-compaction resume (no network calls, no slow subprocess spawns beyond simple existence checks).
  - The hook degrades gracefully (shorter/empty message) when `rtk` or `tools-installer` is absent — never errors out or blocks session start.
  - opencode's lack of an equivalent hook is documented (in the hook's own code comments or the skill/doc wrapping it), not silently absent with no explanation trail.
  - If this work is wrapped in a `SKILL.md`, it passes the `skill-judge` review loop before being marked complete (same bar as `ai-kit-multi-cli-runtime-support`'s Constraints section).
- scope: SessionStart hook, Claude Code, hookSpecificOutput.additionalContext, opencode gap documentation

## REQ-usage-metrics-raw-capture
- source: docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md
- description: Per-runtime raw-capture parsers (Claude Code, opencode in Phase 1; Codex and Cursor in Phase 5) that parse each runtime's own local session-log files verbatim and losslessly into an append-only raw store, isolated per runtime so a format change or bug in one never breaks the others.
- acceptance:
  - Raw parsers exist for at least Claude Code (`~/.claude/projects/*.jsonl`) and opencode (`~/.local/share/opencode/storage/` + `opencode.db`) in Phase 1; Codex (`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`) and Cursor follow in later phases.
  - A raw parser failure for one runtime never crashes the pipeline for the others (empirically tested: simulate a malformed/missing log file for one runtime, confirm the rest still produce output).
  - A raw log file format change across a runtime's own version upgrade (e.g. opencode's SQLite `opencode.db`, added only in v1.2+) is version-detected or gracefully degraded, never crashes the whole pipeline.
  - Cursor's parser is flagged low-confidence (community reverse-engineered format only, no official docs) and built defensively, expecting breakage on Cursor updates.
  - Raw and refined data never leave the local machine.
- scope: raw capture, Claude Code, opencode, Codex, Cursor, session logs, event-sourcing raw store

## REQ-usage-metrics-refinement-pipeline
- source: docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md
- description: A refinement pipeline (mechanical compound-command decomposer + cwd-resolution state machine) that turns raw records into a single, cross-runtime-normalized refined schema covering the 5 MVP axes (date, model, commands with family tagging, tokens, price), distinguishing recognized-but-undecomposed `control_flow_script` segments from genuinely `unclassified` ones.
- acceptance:
  - The cwd-resolution state machine correctly resolves a relative-path command's effective absolute path using prior `cd` state from earlier in the same session (chronological replay across separate tool-calls, not just within one compound command) — pinned by a test reproducing a `cd` in one call and a `grep` with a relative path in a later, separate call.
  - The mechanical decomposer splits `&&`/`;`/`|`-joined compound commands into ordered logical steps.
  - A compound command mixing plain segments and a control-flow segment is decomposed for its plain parts and stored as one opaque `command_shape: control_flow_script` entry for its script-block part — never silently mis-decomposed into fabricated sub-commands.
  - A segment matching neither a compound operator nor a recognized control-flow keyword is tagged `command_shape: unclassified`, distinct from `control_flow_script` — the two never collapse into one bucket.
  - The refined schema records both a command's literal text and its "family" (e.g. `rg` invocations tagged with family `grep`) — family membership follows the same curated set the sibling `ai-kit-tool-substitution-awareness-hook` PRD establishes (`grep`↔`rg`, `cat`↔`bat`, `sed`↔`sd`, `ls`↔`eza`, `find`↔`fd`) as its single source of truth, read/mirrored here rather than independently duplicated.
  - The refined layer, not the raw layer, is where cross-runtime normalization happens; the raw/refined architectural separation is a hard constraint regardless of MVP performance.
- scope: mechanical decomposer, cwd-resolution state machine, refined schema, MVP axes (date, model, commands/family, tokens, price)

## REQ-usage-metrics-dashboard-ui
- source: docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md
- description: A locally-rendered, filterable/sortable interactive dashboard (Artifact HTML) that reads a local export of the refined store across the 5 MVP axes — explicitly never wired to any hosted-database capability, since session data must never leave the local machine (privacy-rejected alternative: storing refined data in the dashboard Artifact's own hosted database).
- acceptance:
  - The dashboard Artifact never has a hosted-database capability pointed at session content — confirmed by inspecting its published capability declaration.
  - The dashboard answers a filtered query like "how many grep-family invocations happened this month, grouped by unique session" directly from already-refined local data, no live re-parsing needed per query.
  - The dashboard loads a user-provided local export (exact load mechanism — pasted/uploaded JSON blob, local file drag-in, or an assets-capability upload — is an implementation detail resolved when this phase is built).
  - The refined schema's exact field list and the `contains_control_flow` limitation are documented wherever this pipeline's `SKILL.md` (or equivalent) lives.
  - If this work is wrapped in a `SKILL.md` (likely, for the capture/refine pipeline's invocation), it passes the `skill-judge` review loop before being marked complete.
- scope: dashboard Artifact, local export, privacy, MVP axes filtering/sorting

## REQ-usage-metrics-classification-refinement-loop
- source: docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md
- description: A periodic, offline pattern-mining analysis pass — triggered only after Phase 1-3 have ingested real historical session logs (not synthetic fixtures), never designed speculatively ahead of real data — that mines accumulated `control_flow_script`/`unclassified` refined entries for recurring shapes and feeds confirmed patterns back into the mechanical decomposer's rule set or attaches a confidence-flagged `inferred_family` annotation, both additive/reversible and re-applicable to historical entries.
- acceptance:
  - The classification refinement pass exists as a runnable, documented step (even if not yet triggered on real data at ship time) and, when run against a fixture with a recurring `for`-loop shape, demonstrably reclassifies matching entries from `unclassified`/`control_flow_script` toward a recognized pattern or `inferred_family` annotation — pinned by a test.
  - The pass never re-derives what actually ran (no shell-execution or tracing) — it only mines recurring textual/structural shapes, purely pattern-mining/inference.
  - A confidence-flagged `inferred_family` annotation is surfaced in the dashboard as an inference, never presented with the same certainty as a hard-decomposed command.
  - Because raw is retained losslessly, re-running this pass with improved pattern rules can reclassify historical entries too, not just future ones.
- scope: classification refinement loop, pattern mining, control_flow_script, unclassified, inferred_family
