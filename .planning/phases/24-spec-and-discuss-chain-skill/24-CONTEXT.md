# Phase 24: Spec-and-discuss chain skill - Context

**Gathered:** 2026-10-14 (assumptions mode, `--analyze --all --batch`, jev screening, best over easy)
**Status:** Plan 01 executed

<domain>
## Phase Boundary

ai-kit ships `skills/ai-kit-gsd-spec-discuss/`: a portable skill that takes a phase range
through spec then assumptions-mode discuss, routing gray areas through an optional decision
ladder (Laya → TypeSafe → own reasoning) with logging, a ledger and a quality rule. The WHAT is
locked in `24-SPEC.md` (R1–R13, amended 2026-10-14). This file locks the HOW.
</domain>

<decisions>
## Implementation Decisions

### Driving the two GSD steps
- **D-01: The discuss step never passes `--assumptions`; the skill encodes the flags' intent.**
  The shim routes the literal flag to `list-phase-assumptions.md` (writes no files), and
  `--analyze/--all/--batch` are read only by `discuss-phase.md`, not by
  `discuss-phase-assumptions.md`. So: "all" = every analyzer area in one pass; "analyze" = each
  Likely/Unclear item carries 2-3 alternatives with best and easy marked; "batch" = all of a
  phase's questions go through one ladder run. ROADMAP goal and SC1 amended.
- **D-02: Both steps run by reading the installed workflow file** (`<gsd-core root>/workflows/
  spec-phase.md`, `discuss-phase-assumptions.md`), the root derived from the resolved
  `gsd-tools` path with the standard `gsd_run` resolver. No `Skill()` delegation (unreliable on
  Cursor, `agent-skills-bootstrap.md` #1600/#1601) and no `workflow.discuss_mode` flip (also read
  by `plan-phase.md:236` and `progress.md:27`). Laya config_flip 0.60 (fb), TypeSafe
  workflow_file 0.88.
- **D-03: Spec runs with `--auto`; discuss runs without it** and the skill pre-answers the four
  prompts by rule: `check_existing` → "Update it"; `has_plans` → "Continue and replan after";
  todos → fold those scoring ≥ 0.4; `present_assumptions` → "Yes, proceed" only after the ladder
  resolved every Unclear item. `auto_advance` (which chains into plan-phase) never runs. Laya
  auto_accept 0.63 (fb), TypeSafe emulate 0.89.
- **D-04: The brief names the phase SPEC as the locked WHAT and passes existing same-phase
  CONTEXT decisions as locked; CONTEXT is updated in place, additively.** The assumptions
  workflow loads no SPEC and writes CONTEXT wholesale. Conventions (this milestone): the header
  `**Gathered:** <date> (interactive); updated <date> (assumptions mode, after NN-SPEC.md)`,
  new decisions under `### Added <date> (...)` continuing the numbering, `**Refined <date>:**` /
  `*(amended <date>, ...)*`, `~~...~~ *(superseded ...)*`, and an appended
  `# Update <date> (assumptions mode)` section in the DISCUSSION-LOG with an `**Input:**` line.
  Laya merge_in_place 0.53 (fb), TypeSafe 0.96.
- **D-05: Subagents are host-conditional.** Gate on `init phase-op`'s `agents_installed`,
  `missing_agents`, `agent_runtime`; spawn `gsd-assumptions-analyzer` through the host's
  subagent mechanism (Claude Code's Agent tool is one example); otherwise run the brief inline
  and say so. Omit `model` when it is `inherit` or empty (#2517). R12's background pacing
  applies only where the host has background subagents with a completion notification; the gap
  is flagged for other hosts. Laya always_inline 0.43 (fb), TypeSafe conditional 0.99.

### `scripts/decide.py`
- **D-06: Each child env is built from scratch per backend; only parsed, typed fields are
  re-emitted.** Laya: `JEV_API_URL`, `JEV_MODEL=jev-1`, `JEV_RESPONSE_MODEL=laya-rl-agent`, no
  key. TypeSafe: `https://api.typesafe.ai/v1/systemone`, `jev-latest`/`jev-1.13.0`,
  `JEV_API_KEY`. Both: `GSD_PATH_JEV=1`, explicit `GSD_PATH_JEV_TIMEOUT_SECONDS` and
  `JEV_MIN_CONFIDENCE`. Inherited `JEV_*` and `OPENCODE_API_KEY` are dropped first (the client
  falls back to them). Failures use a closed set of reason codes; raw client output is never
  copied (the prototype leaked its last 300 characters into `reason`).
  - *Amended 2026-10-18 (21.1 D-09):* the backend URLs, model ids and key now come from the client's backend table; `decide.py` scrubs only the control variables (`JEV_BACKEND`, `JEV_ALLOW_REMOTE`, `JEV_MIN_CONFIDENCE`, `GSD_PATH_JEV*`) and lets the client resolve keys and URLs, each key going only to its own backend.
- **D-07: CLI contract.** `decide.py ladder` reads `{"items":[...]}` on stdin;
  `ladder --second-opinion` sends the given items to TypeSafe only; `decide.py detect` reports
  state without values; `decide.py consent grant|revoke|show <backend>`. `--client PATH` /
  `AI_KIT_JEV_CLIENT` override the client. Per item: `{laya, typesafe, decided_by}`, each
  backend `{choice, top, fallback}` or `{error: code}` or null; `top` is the winning
  probability (`max(p, 1-p)` for a `noul`). Exit 0 for every advisory outcome, 2 only for
  unusable CLI or stdin JSON. `reviewed_head` is the real `git rev-parse HEAD`, else 40 zeros.
  Item types: `choice` and `noul`. **A malformed item is rejected alone**
  (`{"error":"invalid_input","reason":"empty_context"}`) and the rest proceed (the client's
  all-or-nothing validation failed a whole 18.1 batch). Laya per_item 0.71.
- **D-08: Laya's URL comes from `AI_KIT_LAYA_URL`, falling back to `JEV_API_URL` only when its
  host is loopback.** Detection is `socket.create_connection` with a 2 s timeout, reported
  "reachable, not verified as System One". A non-loopback Laya URL is a remote backend needing
  its own consent. **Own reasoning** (Laya client_var_loopback 0.72; TypeSafe second opinion
  dedicated_only 0.61 fb): `JEV_API_URL` is also the client's per-call target, so one variable
  would mean two things; the fallback keeps 18 D-36's existing setups working. Ledger.
  - *Amended 2026-10-18 (21.1 D-08):* a non-loopback Laya URL is refused (`non_loopback_url`, System One plan Global Constraints); `consent grant laya` is dropped.
- **D-09: TypeSafe key lookup, by name only:** `JEV_API_KEY`, then a key file named by
  `JEV_API_KEY_FILE`, then a `JEV_API_KEY=` line in `${XDG_CONFIG_HOME:-~/.config}/ai-kit/
  secrets.env`. `detect` prints only the source label (`env`, `key_file`, `secrets_env`). The
  value is read at call time and passed through the child env only. The secrets parser is a
  standalone ~10-line copy of `local_secrets.load_secret` (precedent `tools/setup.py:1432-1433`),
  not an import. Laya 0.38 (fb), TypeSafe env_file_secrets 0.99.
  - *Amended 2026-10-18 (21.1 D-07):* the lookup moves into the client's TypeSafe adapter, order `TYPESAFE_API_KEY`, `JEV_API_KEY`, `JEV_API_KEY_FILE`, then `secrets.env`; `detect` prints the client probe's source labels.
- **D-10: Consent is a per-user, per-backend record** in `${XDG_CONFIG_HOME:-~/.config}/ai-kit/
  jev-consent.json`, written atomically (mkstemp + `os.replace`), keyed by backend id and
  endpoint host, dated. `consent grant` runs only after the user answers the one range/consent
  question (naming the host, "summaries only", and how to revoke). Every run announces "using
  TypeSafe (consent recorded <date>; revoke with ...)". With no record, a remote call returns
  `no_consent` and makes no call. **Confirmed by uz 2026-10-14** ("once per user"), after
  own reasoning (Laya session_only 0.65 fb, TypeSafe user_level_persistent 0.60 fb): SPEC R2/R6
  want consent recorded once; the jev skill's per-session rule is overridden for this skill.
  - *Amended 2026-10-18 (21.1 D-06):* the same record (path, keys, host binding, announce, revoke) is now owned by the `jev-fast-decision` client skill, so every caller shares it; `decide.py consent` delegates to the client.
- **D-11: The payload guard is a schema:** item keys limited to `id`, `type`, `instructions`,
  `context`, `criteria`; non-empty `instructions`/`context`; `choice` needs ≥ 2 criteria; fields
  capped at ~1500 characters (real max 649); code fences rejected; a small secret-pattern scan
  (`-----BEGIN`, `sk-`-style tokens, long base64 runs). A tripped item falls to own reasoning
  before any call. Labelled defense in depth, not a guarantee. Laya prose_only 0.50 (fb),
  TypeSafe schema_caps_scan 0.83.
- **D-12: The jev client is found by:** `--client`/`AI_KIT_JEV_CLIENT`; the sibling of its own
  skill dir from `os.path.abspath(__file__)` (never `realpath`: the skill is symlinked into the
  host dir); then the static roots `$CLAUDE_CONFIG_DIR|~/.claude/skills`, `~/.agents/skills`,
  `${XDG_CONFIG_HOME:-~/.config}/opencode/skills`, `$CURSOR_CONFIG_DIR|~/.cursor/skills`,
  `$PI_CODING_AGENT_DIR|~/.pi/agent/skills`, each with `jev-fast-decision/scripts/
  jev_review.py`. `detect` lists the roots tried. Laya env_only 0.46 (fb), TypeSafe
  static_roots 1.00.
- **D-13: Tests in `tests/test_ai_kit_gsd_spec_discuss.py` on two layers:** injected seams
  (env, run, connect, which) bundled in one NamedTuple (pylint `max-args=5`), plus subprocess
  tests of the CLI against a fake client in a tmpdir and a real loopback listener. Fixtures:
  synthetic `HOME`/`XDG_CONFIG_HOME`, a detection-combination table, a leaky fake client that
  echoes its env (no key sentinel reaches stdout/stderr), a zero-calls assertion without
  consent, and a real-client smoke skipped when jev is absent. Laya both_layers 0.93.

### SKILL.md, brief and rules
- **D-14: Layout:** `SKILL.md` (≤ ~300 lines: flow, a NEVER list with reasons, MANDATORY
  read-before-step triggers); `references/analyzer-brief.md`, `references/log-formats.md`,
  `references/decision-table.md`, `references/worked-examples.md`; `scripts/decide.py`,
  `scripts/phase_range.py`, `scripts/edge_floor.py`. Trigger words lead the description (the
  wizard truncates at 200 characters). Worked examples: 17 K01/K08 (override confirmed by a
  second opinion), 18.1 T2 (0.75 vs 0.74), 18 B07. Laya single_file 0.45 (fb), TypeSafe
  split_by_topic 0.94.
- **D-15: The analyzer returns pre-formed "Jev question" lines and never calls jev;** the
  orchestrator runs them through `decide.py`. The brief extends the workflow's spawn prompt with
  the SPEC path, locked CONTEXT decisions, the quality rule, the CodeGraph block, "Alternatives
  (best vs easy marked)" and "Jev question" output fields, and the background coupling note.
  **Laya overridden** (analyzer_calls 0.93): remote calls would bypass consent, the one-item
  Laya rule and the log. TypeSafe second opinion return_questions 0.92.
- **D-16: MVP mode is read through `gsd-tools query phase.mvp-mode <N>`,** with
  `config-get workflow.mvp_mode --default false --raw` as the fallback (SPEC R9 amended). Live
  for Phase 24: `{"active":false,"source":"none",...}`. **Own reasoning** (Laya engine_resolver
  0.63 fb, TypeSafe 0.56 fb): the engine's resolver is what the planner itself uses. Ledger.
- **D-17: The CodeGraph paragraph is a marked block in the brief template,** included only when
  `command -v codegraph` succeeds: `codegraph sync <path>` (or `codegraph init <path>` when
  `.codegraph/` is missing), then `codegraph explore` / `codegraph_explore`; in a worktree,
  index the worktree first or treat results as hints. Laya 0.59 (fb), TypeSafe marked_block
  0.98.

### Range, commits, ledger, edges, gates
- **D-18: `scripts/phase_range.py`** is a pure function plus CLI over `roadmap analyze`
  (order, `has_context`, `disk_status`, `roadmap_complete`) and `phases list --phase N` (file
  names). "SPEC newer than CONTEXT" compares `git log -1 --format=%ct` per file, with an mtime
  fallback for untracked files (mtime flags Phase 18, written 12 s apart in one commit). It
  excludes executed/complete phases, sorts decimals numerically, and gives each proposed phase a
  reason (`no CONTEXT` / `SPEC newer`). Laya 0.55 (fb), TypeSafe git_commit_time 0.82.
- **D-19: Commit order per phase:** the spec workflow's own SPEC commit; one
  `gsd_run query commit` with CONTEXT, DISCUSSION-LOG and every cross-phase amended file; then
  `state.record-session` and a separate `docs(state)` commit (batched across phases is fine).
- **D-20: The ledger is appended to a run file under `tempfile.gettempdir()`** and each ledgered
  row is marked in the committed DISCUSSION-LOG ("own reasoning ... ledger"); printed at the end
  or with a critical stop. "Blocking" means another decision in this run depends on it; an item
  that blocks only later planning is ledgered with a `Blocks:` field. A low-confidence item
  against a user-locked decision is decided provisionally and flagged "needs confirmation",
  never a silent override. User-owned preconditions go on the ledger. Laya committed_file 0.57
  (fb), TypeSafe tempfile_plus_log_marks 0.79.
- **D-21: The cross-phase amendment step:** live-verify, grep other phases' SPEC/CONTEXT and
  REQUIREMENTS/ROADMAP for the statement, amend with the D-04 markup in the same commit, hand
  couplings to the coupled phase's discuss. References: `resolve_model_ids: omit` (19 → 17
  R5/R13, 18 R13, `a5b3fab`) and the pi registry (22 → 17).
- **D-22: `scripts/edge_floor.py` with `floor` and `check`.** `floor` extracts requirements by
  one documented rule (title plus Current/Target/Acceptance sub-bullets, no truncation), resolves
  `edge-probe.cjs` with `spec-phase.md:231-238`'s candidate chain plus the host list, and fails
  closed when node or the engine is missing. `check` diffs the SPEC's `## Edge Coverage` table
  against the floor: a missing floor row fails; an extra row needs an `(added)` suffix in the
  Resolution cell (a new convention; no new column); `unclassified` stays `⚠ UNRESOLVED`. Live
  on `24-SPEC.md`: 40 applicable edges, 1 unclassified, equal to the table. Laya inline_node
  0.44 (fb), TypeSafe wrapper_check 0.93.
- **D-23: Gate coverage depends on 16.1's widening (D-01, D-06).** Phase 24 is sequenced after
  16.1's gate commit, or the plan verifies selection itself; 16.1's `tests/test_gate_scope.py`
  proves it. ROADMAP "Depends on" amended. Laya assume_landed 0.65 (fb), TypeSafe
  sequence_after 0.82.
- **D-24: Registration is the README row only;** `enumerate_entries`/`validate_entry` auto-discover
  any `skills/<name>/SKILL.md` (`tools/setup.py:582-610`). ROADMAP SC2 and SC5 amended.

### Claude's Discretion
- Reason-code names; `phase_range.py`/`edge_floor.py` output shapes; the consent file's field
  names; the cap values within the stated ranges.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/24-spec-and-discuss-chain-skill/24-SPEC.md` (R9 amended)
- `~/.claude/gsd-core/workflows/spec-phase.md` (`:82-85,133,188,194-381,514-520`), `discuss-phase-assumptions.md` (`:101-195,239-322,356-395,425-509,566-655`), `discuss-phase.md:26-32,148-197`
- `~/.claude/skills/gsd-discuss-phase/SKILL.md:53-63`; `~/.claude/gsd-core/references/gsd-run-resolver.md`, `agent-skills-bootstrap.md`, `planning-config.md:302`
- `~/.claude/skills/jev-fast-decision/SKILL.md:44-81`, `scripts/jev_review.py:127-296`, `reference.md:40-44`
- `skills/ai-kit-spec-review/ai_kit_spec/local_secrets.py:7-24`; `skills/ai-kit-gsd-curated-config/SKILL.md:21-38`; `tools/setup.py:51-62,582-610,1429-1454`
- `.planning/phases/18-cross-ai-skills-apply-pipeline/18-CONTEXT.md` D-31, D-36; `.planning/phases/16.1-hardening/16.1-CONTEXT.md` D-01, D-04, D-06, D-09, D-16
- `~/.claude/skills/skill-judge/SKILL.md:293-325`; `.planning/phases/16-ai-kit-spec-extensions/16-SKILL-JUDGE.md`
</canonical_refs>

<code_context>
## Existing Code Insights

- The scratchpad prototypes (`jev_ladder.py`, `edgefloor.py`, `edgetable.py`, `deferred-ledger.md`, `skill-notes.md`) are reference only; their hardcoded paths and env copying are not carried over (D-06, D-09).
- `tests/test_ai_kit_gsd_curated_config.py:30-43` (`make_fake_run`) and `tests/test_markdown_to_pdf.py:6-8` (`sys.path` insert) are the test precedents.
</code_context>

<specifics>
## Specific Ideas

- Open for research: whether TypeSafe accepts `jev-1.13.0` as a request model (the client checks the response string exactly, so an alias bump would fail every call); TypeSafe's data-retention terms for the consent wording; cross-skill invocation and background subagents on codex/opencode/cursor/pi; current agentskills.io frontmatter limits; `gsd-tools query commit` with files spanning several phases under `branching_strategy: phase`.
</specifics>

<deferred>
## Deferred Ideas

- **Jev 1.14 capabilities (owner note 2026-10-15, not researched):** image questions
  (`TypeSafe-Danger-Zone-Images: true` + `assets`), the `box` type, long context, and
  `jev-preview`/`jev-latest` moving to 1.14. `decide.py` stays text-only and keeps D-07's item
  schema and D-11's payload guard. Extending it is future work. Its first step is to decide the
  response-model check (`jev-latest` → 1.14) and per-question thresholds, since `confidence` is
  a peakedness summary, not calibration. Required reading: [Jev 1.14 release notes](https://typesafe.ai/blog/jev-1-14), [Primitives](https://docs.typesafe.ai/primitives), [Images](https://docs.typesafe.ai/images), [Confidence](https://docs.typesafe.ai/confidence).
</deferred>

---

*Phase: 24-spec-and-discuss-chain-skill*
*Context gathered: 2026-10-14*
