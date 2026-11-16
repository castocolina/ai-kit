# Phase 39: Lane capability blocks and lens skills - Context

**Gathered:** 2026-11-16 (interactive path, no owner question needed, jev screening, after 39-SPEC.md)
**Status:** Ready for planning (after Phase 37 lands: this phase extends its planner with a capabilities result and one setting, reads
Phase 35's window per (runtime, model), and reuses Phase 36's read-only commands and Phase 38's run lock)

<domain>
## Phase Boundary

Every lane is told, in its prompt, only what its own final argument list lets it do: the runner prints each lane's capabilities
from the argv it will start with, one composer turns them into a capability block, and the tools named in it are the ones found on
the child's PATH. Lens skills come from one role-keyed table of the skills and MCP servers present on each host, rescanned every
run, and reach a lane by path where a host verifiably loads it and inlined where not. A prompt larger than a lane's known window,
or a prompt value with a control character or a path outside the repository and skill roots, is refused for that lane before it is
spawned and never trimmed.
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**12 requirements are locked.** See `39-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `39-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope:** the shared role table and scan (R1); the optional sorter (R2); the runner's capabilities line (R3); the block and its
entry points (R4); lens delivery (R5); the skill-path setting (R6); the pre-spawn window check (R7); the embedded-value validator
(R8); the after-approval pass (R9); the GSD config skill's read of the table (R10); one builder for review and execute with the
spec-config summary (R11); skill text, docs and the judge bar (R12).

**Out of scope:** lane switching, ping reasons and the review loop beyond one pass step (Phase 40); the host's own
`context_length_exceeded` answer (38.1); setting reasons and host forms (37, 38.1); the catalog and window source (35); lens wiring
into GSD agents and the hook route's block file or window flag (44); the vertical-slices runbook (45); the adapter's lens use at
`receiving-code-review` (42).
</spec_lock>

<decisions>
## Implementation Decisions

### Layout and where the facts come from (SPEC R3, R4, R11)

- **D-01: One small new module per concern, each with its own tests; `cli.py` only wires subcommands.** Modules (names are the plan's
  to fix): the capability block composer, the prompt guard (size check, embedded-value validator, the closed refusal list), the skill
  table (seed file loader, scan, persisted sorts), the role classifier (jev step). New subcommands: `capability-block`,
  `skill-table`, `classify-skills`, `confirm-skill-role`, all read-only except the last. Evidence: `cli.py` (about 1,000 lines),
  `detection.py` (1,348) and `runner_dispatch.py` (663) are near the pylint caps, and Phases 35 and 36 set the same pattern; the
  composer must be unit-testable with fake runner output. choice 0.87 (typesafe; laya low 0.48 none_of_these).
- **D-02: The runner computes a lane's capabilities from the same planner that builds its argv.** Phase 37's pure planner (D-11)
  gains one result, `capabilities`: `write` (`none`, `workspace`, `full`, `unknown`), `shell` and `mcp` (`yes`, `no`,
  `unknown`; `mcp` also `host_config` when the host reads its own config), `skills` (`none`, `path`, `discovery`, `unknown`), each
  with a label (`from argv` plus the flag, or the source label of the row's form with host version and date). One pure function
  over (row, role, final argv) decides, so a flag a user adds through `extraArgs` is seen: a tool list (pi `--tools`, copilot
  `--available-tools` and `--excluded-tools`, claude `--tools`) decides `shell`; a mode flag the host's own help calls read-only
  (cursor `--mode ask`, codex `--sandbox read-only`) decides `write` and leaves `shell` `unknown` where the help does not say.
  `--print-argv` prints one extra `capabilities` JSON line and `--describe` lists each row's capability form with its source
  label (extends 37 D-10). Why the runner: a GSD hook route has no Python layer, the flag meanings are fixed host knowledge that
  37's HOST SETTINGS FORMS keeps in one place, and a Python parser would hold a second copy that drifts. An unknown runtime and an
  `--argv-file` lane report every field `unknown`. Live now (the pre-37 template): pi review shows no shell, no skills and no MCP in
  its argv; copilot review no shell, no write, no MCP; claude, cursor, opencode and codex review show a read-only mode but no
  tool list, so their `shell` stays `unknown` until a probe says otherwise. laya none_of_these 0.85 (contradicts the evidence);
  second opinion typesafe runner_row low 0.70. **jev overridden**; **own reasoning.** Ledger. **Needs owner awareness** (a
  cross-phase addition to 37's planner, recorded in 37 CONTEXT's handoff).
- **D-03: Python reads the line by running `--print-argv` for the lane at dispatch.** Live: 0.032 s per call, read-only, no
  migration (the existing WR-53 guarantee). The composer calls it once per (runtime, model, role, extras) in a run and keeps the
  result in memory for that run only. A missing `node`, a runner without the line (an old rendered copy) or an unparseable line
  gives the all-`unknown` capabilities with a visible reason, never a refusal and never a guess. A native lane (the host runs it,
  no argv) gets no tool claims.
- **D-04: The block has fixed sections in a fixed order.** `LANE` (runtime, model, role), `ACCESS` (write, shell, MCP in the
  runner's words), `TOOLS` (see D-05), `CODE INDEX` (D-06), `SKILLS` (delivered lenses by path or inline, skipped lenses with their
  note), `SETTINGS` (the settings actually applied from `--print-argv`: model, effort, context form; ignored ones are not
  listed as applied). An `unknown` fact prints as `unknown: make no assumption`, never as a negative claim. The names
  `SHARED_TOOLING_PATH`, `AGENTS_TOOLING_PATH` and `TOOL_AVAILABILITY` stay in the block, filtered the same way, because
  `ai-kit-spec-review-checklist` keys its tool-preference rule off those literal names (the existing code comments say so). The
  execute lane's soft-confinement sentence is chosen from `write` (`full` or `unknown` gets it, `workspace` or `none` does not),
  replacing the `OS_SANDBOXED_EXEC` membership test; the set stays until then as a seed. Own reasoning (the SPEC fixes the content;
  the order is a stability choice pinned by a fixture).
- **D-05: Tools are resolved against the child's PATH at dispatch time.** Each tool is resolved with `shutil.which` over the PATH of
  the exact environment the child receives (`runner_dispatch.child_env` for a Python dispatch; for a GSD hook the runner's
  `childEnv`, whose scrub list does not touch PATH). The tool line appears only when `shell` is `yes` or `unknown` and then reads
  "if you have a shell"; a `no` prints no tool line. The parent's cached `TOOL_AVAILABILITY_JSON` step in the review skill and
  `cross-ai-dispatch.md` goes: `dispatch-reviewer` and `dispatch-execute` resolve it themselves, and `--tool-availability-json`
  stays accepted for old callers, ignored with a note naming the flag. `detect-tools` stays for spec-config's setup-time report.
  laya child_env_at_dispatch low 0.56; typesafe parent_path_cached low 0.71 (a split of two low answers). **Own reasoning:**
  the requirement says the child's PATH and the two environments can differ (per-runtime extras, a runner-side scrub). Ledger.
- **D-06: codebase-memory-mcp is named only when its binary is on the child's PATH.** Then: the MCP tool list when a host config
  registers the server (read by the existing registration reader, evidence phrase kept: "read from its config" or "inferred from
  its extension file" for pi) and the lane's `mcp` is not `no`; else the CLI form when `shell` is not `no`; else no line. Never
  both for one lane. The registration read stays per host and keeps returning `unknown` for a host with no reader; the line says
  "not tested in this session" as today. The same rule applies to any server in the table with the role `code_index`.

### The shared table (SPEC R1, R2, R10)

- **D-07: The roles are a closed list; the seed file holds examples, each with a source label.** `review_lens`, `edit_lens`,
  `ui_lens`, `code_index`, `decision_helper`, `host_control`, `skill_judge`, `unsorted`. A role is added only by an amendment with
  the locking test updated (the list in code, the seed file and the SKILL.md table are compared by one test, as 38.1 D-02 does for
  classes). Seed file: `skills/ai-kit-spec-review/references/skill-roles.json`; each row `{name, kind: skill|mcp, role, source}`
  with `source` "judged 2026-11-16 from the skill's own description" (unverified: a role is a judgment, not a host fact). Initial
  rows: `review_lens` for `ponytail-review`, `ponytail-audit`, `ponytail-debt`, `reducing-entropy`, `naming-analyzer`; `edit_lens`
  for `ponytail` and `simplify`; `ui_lens` for `impeccable`; `code_index` for `codebase-memory`, `graphify` and the server
  `codebase-memory-mcp`; `decision_helper` for `jev-fast-decision`; `host_control` for `herdr`; `skill_judge` for `skill-judge`.
  Everything else is `unsorted` until the owner or the sorter says otherwise. A row never decides presence (R1). typesafe
  closed_list_with_lock 0.91 (laya none_of_these low 0.63).
- **D-08: The scan reads the host roots and each host's own MCP config on every call.** Hosts: claude, codex, opencode, cursor,
  copilot, pi and the shared agents root, each root honoring the host's own config-dir variable (the existing scripts honor
  `CLAUDE_CONFIG_DIR`, `XDG_CONFIG_HOME`, `CURSOR_CONFIG_DIR` and `PI_CODING_AGENT_DIR`; the registration reader in
  `detection.py` adds `CODEX_HOME` and `COPILOT_HOME`). That the codex and copilot hosts load skills from `~/.codex/skills` and
  `~/.copilot/skills` is unverified (the directories exist here with 2 and 1 entries); the scan lists what is on disk and a
  lens still reaches those lanes by inlining. Claude's
  enabled plugin skills are read as `skill_scan.plugin_skills` does today. MCP names come from the registration reader's file
  list and parser generalized to return names only (keys of the servers table, never a value; a malformed file is `unknown`).
  The scan rows are generic (`name`, `path`, `root_kind`, `role`, `role_source`); the GSD-specific fields (`addressable`,
  `escapes_root` against GSD's own rule, `ai_kit_skills_dir`) stay in the GSD config skill, which keeps asking GSD for its roots
  (`getGlobalSkillsBase`) for its own purpose. Honest note: the shared module becomes the sixth copy of the host-root list; the
  five others (`fold_group.py`, `jev_ladder.py`, `gp_host.py`, `tools/judge_loop.py`, `tools/hooks/precompact_core.py`) are
  skill-local or tools-local by design and
  are listed here for the owner, not migrated (the self-contained-skill rule and the frozen cross-skill allowlist forbid an
  import). The scan is cheap (a directory listing per root; 43 entries under claude here), so nothing is cached across runs.
  typesafe review_package_module 0.80 on the second opinion; laya none_of_these 0.85 **jev overridden** (it contradicts the loader
  precedent and the frozen allowlist).
- **D-09: A confirmed sort is a config entry; the sorter is a proposal command and a confirm command.** `[skills.roles]` maps a
  skill name to a role, labeled `user-stated`, in the layered config (project over user), written only by `confirm-skill-role`
  through the existing atomic splicing writer. `classify-skills` is read-only: for each `unsorted` skill it asks jev when present
  (through jev's own ladder, probed at runtime, one item per skill, name plus the first 300 characters of description, choice among
  the closed roles plus `none of these`) and prints role, confidence and "advisory"; a low, forced or missing answer, or no jev,
  prints no proposal and the skill stays `unsorted`. The skills (spec-config, and curated-config through the loader) show each
  proposal to the owner and call `confirm-skill-role` per accepted sort. It runs at configuration time only, never in a review or
  an execute run. MCP server names are not sent to jev (no description); only a seed row or the owner sorts them. typesafe
  config_roles_table 0.97 and read_only_proposal_command 0.84 (laya low both); the sorter shape: laya none_of_these 0.93 contradicts
  the evidence, second opinion typesafe helper_with_fallback low 0.79: **jev overridden**, **own reasoning.** Ledger.

### Lenses and the skill-path setting (SPEC R5, R6, R9)

- **D-10: The lens set, the delivery and the closed notes.** The set is the present skills with role `review_lens`, plus `ui_lens`
  only when the files named in the prompt hold a UI file by the extension list the superpowers adapter already keeps (the plan
  reuses it or moves it to one shared home; no third list). Delivery per lane: by path only when the lane's applied settings carry
  a `--skill-path` form labeled verified or probed (D-11), otherwise inlined from the skill's SKILL.md body between delimiters with
  its path and sha256, byte-equal to the file. Lenses are added one by one in table order while the total prompt stays within the
  lane's known window (D-12); one that would not fit is skipped whole with the note `over_window`; the base prompt is never cut. The
  closed lens-note list is `built_in_no_file`, `over_window`, `path_rejected`, `not_present`, `host_cannot_load`, locked by a test
  and disjoint from the refusal reasons, the setting reasons (37) and the error classes (38.1). A built-in lens with no file on
  disk (`simplify`: no `simplify*` under `~/.claude` or `~/.agents`) is delivered only to a native lane of its own host by name,
  labeled unverified; every other lane gets `built_in_no_file`. typesafe inline_unless_verified 0.95, native_only_named 0.86 on the
  second opinion; skip_whole_lens_named low 0.70 (typesafe; laya low 0.37): **own reasoning** for the whole-lens skip, since cutting
  a lens would be trimming and a refused lane would punish an optional extra. Ledger. Roadmap criterion 3 and REV-03 are amended
  for the live facts (see D-19).
- **D-11: A repeatable runner setting `--skill-path <dir>` with a form per host, labeled.** It joins 37's settings report: `applied`
  where the row has a verified form (pi `--skill <path>`: pi 1.5.2's docs say explicit `--skill` paths still load under
  `--no-skills`), `ignored` with `unverified_form` for claude, copilot and cursor-agent (an `--add-dir <path>` flag exists in each
  help; its effect on a read-only lane is unverified, so it is reported and not fed, as 37 D-15 does for unverified forms), and
  `ignored` with `no_form` for codex, opencode and every other runtime. The path must lie inside the working tree or a skill root;
  the runner holds a plain-Node copy of the control-character and root rules, and one shared fixture pins it equal to the Python
  validator (D-13). The capabilities line reports `skills=path` only when a form was applied. opencode's `run --file` attaches a
  file's text to the message, which is inlining by another route and not adopted. typesafe runner_setting_with_forms 0.86 (laya low
  0.64). Needs owner awareness (a new setting on the runner surface 37 defined).

### The window check and the validator (SPEC R7, R8)

- **D-12: The check runs in the Python dispatch, last before the spawn.** Estimate = `ceil(UTF-8 bytes / BYTES_PER_TOKEN)`
  over everything sent (block, lens text, prompt; not the runner's preamble nor the host's system prompt, a stated limit), the
  constant seeded at 4 and labeled `estimated` and `judged` (a divisor of 4 counts prose about right and under-counts code and
  dense scripts, so a wrong refusal is rarer than a wrong pass; a wrong pass ends in the host's `bad_request` class from 38.1).
  The window is read through the catalog's accessor for (runtime, model) (35 D-09: the user's `[[models.context]]` override, then
  the host's figure, then models.dev's; an exact integer with its label and source), or `unknown`; `unknown` is never capped. When
  the lane's final argv applies a context form with an unverified effect (cursor bracket, codex key, copilot tier: 37 D-15, D-22),
  the window is `unknown` for that lane with the note `context_form_applied`, unless the user stated one (a copilot `long_context`
  tier is a tier, not a number). Refuse when estimate > window (equal passes). The refusal is a result record `{status: refused,
  reason, detail}` with estimate, window, the window's label and source and the constant, no child spawned, and a distinct non-zero
  exit that is not one of the runner's exits (0, 1, 2, 69, 75, 124, 127, 128 are taken; candidate 65, the plan confirms against
  `STATUS_TABLE`); under `--stdout-only` nothing is written to stdout, so the review skill's existing "no Status line" rule
  reads it as a failed lane. The closed refusal list is `prompt_over_window`, `value_control_char`, `path_outside_roots`,
  `path_unresolvable`, locked by a test, and Phase 40's ping reasons reuse it. A refusal never alters the prompt, changes the model
  or runtime, or cancels a sibling lane (the review is reported partial: 40). typesafe low_ratio_estimate 0.89 on the second
  opinion (laya none_of_these 0.75 **jev overridden**), unknown_unless_user_stated 0.86, two_closed_lists 0.94,
  refused_result_no_spawn 0.84 (its reordered second opinion came back low, none_of_these 0.48, so the first answer stands). Open
  question for the researcher: calibrate the constant against recorded host usage (copilot's `--usage-output-file` writes token
  counts; other hosts' usage output is unrecorded).
- **D-13: One validator for every embedded value, rejecting and never rewriting.** Control characters: Unicode categories `Cc`,
  `Zl`, `Zp` and the bidirectional and zero-width format characters U+200B to U+200F, U+202A to U+202E, U+2060 to U+2064, U+2066 to
  U+2069 and U+FEFF. A path is resolved (symlinks first) and must lie, compared by path components, inside the repository root of
  the dispatch's working directory (the git top level, else the real path of the directory, as 38 D-06 resolves it) or inside a skill
  root the scan found; a sibling checkout, a sibling-prefix name and a link out of a root are outside. The result names the value's
  position and reason and prints it with control characters escaped; all bad values of one dispatch are reported together. The
  check runs immediately before the spawn; check-then-use is a stated limit (a path can change after it).

### After-approval pass, curated-config, summary, jev and herdr (SPEC R9, R10, R11)

- **D-14: The editing pass is opt-in and shows its diff.** `[review] edit_lens_pass` (default false, a boolean in the layered
  config) enables it; an unattended run never enables it. After the final approval record it runs the present `edit_lens` skills on a
  lane whose capabilities show `write` of `workspace` or `full`, with the approved files only (validated by D-13) and the block's lens
  delivery; pre-pass content is kept as bytes, the loop prints the diff summary, and the owner accepts or rejects; a rejection
  restores byte-equal files. A lane with `write` of `none` or `unknown` is never used; the pass is an execute-role lane, so the
  Phase 38 run lock applies. typesafe opt_in_with_diff 0.83 (laya low 0.28). **Needs owner confirmation:** REV-03 and roadmap
  criterion 3 say file-editing lenses "run as a pass after approval"; a default-off key softens that, because an editing pass over a
  document the reviewers just approved makes the approval stale and an unattended run cannot accept a diff. Provisional until the
  owner answers. Ledger. Phase 40 owns the loop and places the step; this phase writes the step's contract.
- **D-15: curated-config derives its lens visibility from the table.** `inventory` gains `skill_roles` (through
  `load_ai_kit_spec_module`); `ponytail_visibility` is derived from it with the same output shape and the same five hosts it covers
  today, the hardcoded `PONYTAIL_SKILLS` tuple is removed, and a fixture test pins byte-equal output with the old function;
  copilot appears in `skill_roles` while `ponytail_visibility` keeps its hosts until 44 decides. A missing review package leaves
  `skill_roles` absent with the existing note. laya none_of_these 0.70 (contradicts the evidence: the plan files validate the old
  shape); second opinion typesafe derive_same_shape low 0.73. **jev overridden**, **own reasoning.** Ledger. Lens wiring is 44's.
- **D-16: One builder, a summary line, jev and herdr conditional.** `dispatch-reviewer`, `dispatch-execute` and `capability-block`
  call the same composer with the same arguments for a lane, pinned by a byte-equality test. Phase 36's read-only `check-reviewer`
  and `config-status` outputs print one capability summary line per lane from it (no spawn). jev is used only by the sorter (D-09),
  probed at runtime, advisory, owner-confirmed, with the no-jev path (nothing proposed) tested. herdr is not used: the summary is
  plain text the calling skill prints, and the one place a pane might help (the spike below) runs headless first. typesafe
  not_used 0.87 (laya low 0.63).

### Skills, docs, spike (SPEC R12)

- **D-17: Skills and docs.** `ai-kit-spec-review/SKILL.md` (capability block, lens delivery, the refusal result, the optional pass;
  history in a trailing section) and `ai-kit-spec-config/SKILL.md` (the sorting step with both paths) change and meet the judge bar;
  the superpowers adapter's and curated-config's SKILL.md join the loop only if their text changes. `tooling-guidance.md`,
  `reviewer-prompts.md`, `cross-ai-dispatch.md` (the `detect-tools` step becomes the child-PATH rule), the READMEs and the config
  documentation for `[skills.roles]`, `[review] edit_lens_pass` and `[[models.context]]` follow. Doc-contract tests pin the three
  closed lists (roles, refusal reasons, lens notes), the block's section names and the keys. The hardcoding guard passes on every
  changed file. Own reasoning.
- **D-18: A spike at execute start, headless first.** One cheap call per primary host (claude, opencode, pi) in a scratch
  repository records: whether a review lane reads a lens file outside the repository with and without the form (pi `--skill`,
  `--add-dir` for claude), whether claude's plan mode and opencode's plan agent can run a shell command, and whether codex's
  read-only sandbox and cursor's ask mode can; findings go to `tmp/` and into the rows' source labels (a verified form flips from
  `unverified_form`). herdr may drive a host for it where `HERDR_ENV=1` and the CLI exist; the fake-argv tests do not depend on it.
  A host the spike does not cover stays unverified and inlines.
- **D-19: Cross-phase amendments made in this commit.** Roadmap Phase 39 criterion 3 and code anchors; REQUIREMENTS REV-03, REV-04
  and REV-05; Phase 37's CONTEXT handoff to Phase 39 (the capabilities result and `--skill-path` are added by this phase's plan;
  37's planner stays open to a row field per setting). Each is dated and cites the decision ids above. The live facts behind them:
  pi's documented `--skill`, the missing file for a built-in lens, the per-host argv, and the parent-versus-child PATH.
- **D-20: Todo folding.** The pending todos hold no item for this phase (a search for lens, capability block, tooling guidance, skill
  table, prompt size and context window matched only a compact-metrics note and a lens-brief eval note of Phase 30, neither in
  scope). Nothing folds here.

### Handoffs to later phases

- **Phase 35**: exposes the window accessor for (runtime, model) with label and source (its D-09); if the executed shape differs,
  this phase's plan adapts and records it.
- **Phase 36**: its read-only `check-reviewer` and `config-status` outputs print the summary line (D-16); nothing else changes.
- **Phase 37**: the planner gains `capabilities` and `--skill-path` through a row field and a function (amendment recorded in 37
  CONTEXT); a context form applied there makes the window `unknown` for the size check; the recorded-help fixtures cover the new
  flags.
- **Phase 38**: the editing pass runs under its run lock; nothing else.
- **Phase 38.1**: `context_length_exceeded` stays the host's answer after a call; this phase's refusal reasons are separate from
  its classes and the lock test asserts disjointness.
- **Phase 40**: reuses the refusal reasons in its closed ping-reason list, decides whether a refused lane is switched or only
  reported partial, and places the after-approval pass step in the loop.
- **Phase 41**: the superpowers adapter's dispatch uses the same builder through `dispatch-execute` (no separate tool-map step); its
  SKILL.md text about the parent-PATH map is rewritten there if this phase did not.
- **Phase 42**: EXE-02's lens use at `receiving-code-review` reads the table and the delivery rules.
- **Phase 44**: wires lenses into GSD agents from the table, and for a rendered GSD hook generates the `--prepend-file` block with
  `capability-block` and carries a window to the runner (the runner never reads the catalog).
- **Phase 45**: the vertical-slices runbook reads the table.

### Open questions for the phase researcher

- The bytes-per-token constant against recorded host usage (D-12).
- Whether claude's plan mode, opencode's plan agent, codex's read-only sandbox and cursor's ask mode can run a shell, and whether any
  lane reads a path outside its tree under its review argv (the spike, D-18).
- The exact `skill_roles` inventory field shape and the single home of the UI extension list (D-10, D-15).
- Whether the runner's per-runtime `env` additions can ever change PATH (none do today) and how the Python child-PATH rule follows
  (D-05).

</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/39-lane-capability-blocks-and-lens-skills/39-SPEC.md` (requirements, live facts, findings)
- `.planning/phases/37-shared-runner-options-and-session-ids/37-CONTEXT.md` (D-11 planner, D-14 reasons, D-15 and D-22 forms),
  `35-model-discovery-and-catalog/35-CONTEXT.md` (D-09 window), `38.1-runner-error-classification-and-retry-policy-inserted/38.1-CONTEXT.md`
  (D-02 class lock, `bad_request`), `38-runner-hardening-and-run-safety/38-CONTEXT.md` (D-06 root rule, run lock)
- `skills/ai-kit-spec-review/ai_kit_spec/` (`reviewer_dispatch.py`, `tooling_guidance.py`, `execute_dispatch.py`,
  `runner_dispatch.py`, `detection.py`, `cli.py`, `config_io.py`, `toml_splice.py`), `skills/ai-kit-spec-review/references/`
  (`cross-ai.mjs`, `tooling-guidance.md`, `reviewer-prompts.md`, `cross-ai-dispatch.md`)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/` (`skill_scan.py`, `inventory.py`, `gsd_catalog.py`, `host.py`)
- `skills/ai-kit-spec-review/SKILL.md`, `skills/ai-kit-spec-config/SKILL.md`, `skills/ai-kit-spec-execute-superpowers/`
  (`dispatch_injection.py`, `task_classification.py`)
- pi docs `docs/cli.md` (the `--skill` and `--no-skills` lines), the hosts' own `--help` (recorded in Phase 37's fixtures)
</canonical_refs>
