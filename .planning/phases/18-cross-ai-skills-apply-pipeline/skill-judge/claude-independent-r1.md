# Independent skill-judge: ai-kit-gsd-curated-config SKILL.md

- Current: working-tree `skills/ai-kit-gsd-curated-config/SKILL.md`, blob bb81efde (230 lines, no references/ dir)
- Baseline: `d164697:skills/ai-kit-gsd-curated-config/SKILL.md` (194 lines, v1 only)
- Scored blind: 18-SKILL-JUDGE.md was read only after both scores were final.

## Command/flag verification (offline, scratch HOME, `--help` only)

All 17 subcommands named in SKILL.md exist in the argparse (`inventory recommend plan-set plan-unset apply followups` +
the 11 v1 ones). Every flag used in the examples exists: `inventory --host {claude,codex,opencode,cursor,pi} --refresh`;
`recommend --inventory --profile --rigor {mvp,standard,rigorous} --cross-ai-review {y,n} --cross-ai-exec {y,n} --out`;
`plan-set key value --plan [--inventory] [--force]`; `plan-unset key --plan [--inventory]`;
`apply --plan --inventory --project-dir [--dry-run]`; `followups --plan --inventory --project-dir [--approve] [--require]`.
v1 flags all match. The runner flag `--print-argv` and the `AIKIT-XAI status=...` line exist in
`skills/ai-kit-spec-review/references/cross-ai.mjs` (the template; `status=unverified` with `tree=unknown` also exists). Marker and
snapshot suffixes (`.ai-kit-apply-marker`, `.ai-kit-apply-backup`), `approve_with`, `restore_error`, `script.active`,
`GSD_PATH_JEV*` and `GSD_WORKSTREAM` all exist in code. No command in the skill is missing from the CLI.

Problems found during verification, not visible from `--help` alone:
1. `inventory` writes JSON to **stdout** only (it has no `--out`). The skill never says to redirect it to the file that later
   `--inventory <inv.json>` flags read. `plan-set`/`plan-unset` default `--inventory` to `inventory.json` next to `plan.json`
   (`plan_io.sibling_inventory_path`). The skill does not say that either.
2. `recommend --out` is refused inside the project's `.planning/` and over any input/config file (`plan_io.out_path_problem`).
   `.planning/plan.json` is the obvious place an agent would try, and the skill does not warn against it.
3. `plan-set workflow.cross_ai_command "node .planning/scripts/cross-ai.mjs" --force` uses `--force` for nothing: that value is
   the canonical one and passes without it (`plan_edit._check_cross_ai_command`). `--force` exists to bypass candidate checks and
   the full-permissions-command guard. The skill never explains this, and its only example teaches agents to add the flag by habit.
4. v2 exits `2` on refusals the agent can fix (bad `--out`, inventory-digest mismatch, `needs_choice` left open on apply,
   malformed inventory). The skill says exit 2 means an install problem and "do not retry". That is true for v1 only.
5. v1 `apply-execution` writes a direct `opencode run ...`/`cursor-agent ...` value into `workflow.cross_ai_command`
   (`cli._cmd_apply_execution`). Run after a v2 apply, it silently replaces the v2 `node .planning/scripts/cross-ai.mjs` runner wiring.
   The skill only says "never mix v1 writes with an in-progress v2 plan ... without intent".
6. `inventory` already reports `ponytail_visibility` live (`inventory.py:373`). The SKILL.md bullet "on this machine the six
   ponytail names are visible only through the Claude plugin cache" is a dated fact about the maintainer's machine, written as if it were general.

## Scores

### Baseline (d164697) — 104/120 (B)

| Dim | Score | Justification |
|---|---|---|
| D1 Knowledge delta | 16/20 | Strong expert gotchas: `config-set` silently creates a sparse one-key config without `ensure-project`; pass detect output through unchanged; `apply-execution` no-candidate asymmetry; bare binary on PATH vs a venv path; absolute `--dir` breaks after a re-clone; `gsd-executor` excluded from the heavy-tier sweep. Some repeated prose (the ensure-project footgun is explained twice). |
| D2 Mindset + procedures | 13/15 | Has an explicit "before any apply-*, ask yourself" check plus a correctly ordered detect, then ask, then apply procedure. |
| D3 Anti-patterns | 13/15 | NEVER list with non-obvious reasons; a common-mistakes table with a Why column. |
| D4 Spec/description | 13/15 | Valid frontmatter. WHAT is very specific, WHEN is present. The description is long (~800 chars) and full of implementation detail (`AGENT_DEFAULT_TIERS`), and it has few phrases a user would actually type. |
| D5 Progressive disclosure | 12/15 | Self-contained, under 200 lines. Points to source files for the literal lists. Some redundancy. |
| D6 Freedom calibration | 14/15 | Low freedom where config writes are fragile; exact order; the one question is fixed. |
| D7 Pattern | 9/10 | Clean Process pattern with a Tool-style reference table. |
| D8 Usability | 14/15 | Required-flags table, exit codes, null/no-candidate edge cases. |

### Current (bb81efde) — 88/120 (C)

| Dim | Score | Justification |
|---|---|---|
| D1 Knowledge delta | 15/20 | Much new expert content: trusted-checkout model, marker/`restore_error` semantics, "exit 0 with cleanup warnings = committed, never restore", `.new` runner not active, partial opencode bare profile, unverified plugin layering. Lost every v1 gotcha. Several lines are too compressed to act on ("System One reachability", "only `GSD_WORKSTREAM` is honored ...", "the next apply's refusal must agree after its `apply --dry-run` check"). Includes the machine-specific ponytail note. |
| D2 Mindset + procedures | 10/15 | The 6-step v2 procedure is domain-specific and correctly ordered. It never says which questions to ask the user to fill `--profile`/`--rigor`/`--cross-ai-review`/`--cross-ai-exec`, and gives no rule for choosing them. The baseline's "before apply, ask yourself" check is gone. |
| D3 Anti-patterns | 11/15 | Specific NEVER list and a mistakes table, but most reasons are terse and the Why column was dropped. Two traps are missing: `--force` used by habit, and v1 `apply-execution` overwriting the v2 runner command. |
| D4 Spec/description | 12/15 | Valid. WHAT and WHEN are both present and shorter than the baseline. It lacks trigger phrasing for the new v2 capabilities (wiring skills to GSD agents, setting up a cross-AI runner, "configure .planning/config.json"). The WHEN clause is unchanged from v1. |
| D5 Progressive disclosure | 11/15 | Sectioned and 230 lines, fine without references/. v1 is now a bare command dump. The phrase "v1 — same as prior skill" points to text that no longer exists in the installed file. |
| D6 Freedom calibration | 11/15 | Low freedom where it matters (`approve_with` unchanged, grouped yes/no, never hand-write). But the examples use literal values that agents will copy: `--profile quality --rigor mvp --cross-ai-review n --cross-ai-exec y`, `--force`, `--model x`, `--require installer`. Nothing marks them as placeholders, and they directly drive config writes. |
| D7 Pattern | 8/10 | Process pattern. Putting v1 and v2 side by side blurs it a little. |
| D8 Usability | 10/15 | Good failure-state coverage. Gaps: inventory output is never captured to a file; `--out` refusal under `.planning/` is not mentioned; exit-2 semantics are wrong for v2; code blocks use the bare `ai-kit-gsd-curated-config.py` instead of `"$ENTRYPOINT"`; the v1 edge cases (null `claude_md_path`, detect takes no `--project-dir`, apply-execution optional flags) are gone. |

## Findings (current file)

### Critical
None.

### Important
- **I1: The skill never says which questions to ask before `recommend`, or how to choose the values.** Fix: in step 2, add
  "Ask the user, in one message: `model_profile` (quality/balanced/budget/adaptive; adaptive recommended), rigor
  (mvp/standard/rigorous), cross-AI plan review (y/n), cross-AI execution (y/n). Omit `--cross-ai-*` to take the inventory-derived
  default. Ask nothing else." Then replace the example literals with `<profile> <rigor> <y|n>` placeholders.
- **I2: Exit-code semantics are wrong for v2.** Fix: "v1: exit 2 = install problem (surface verbatim, do not retry). v2: exit 2 is also
  a refusal you can fix (bad `--out`, inventory digest mismatch, open `needs_choice`, malformed inventory). Read the stderr line and fix
  the input, re-running `inventory`/`recommend` where it says so. Exit 1 = a gsd-tools read/write or restore failure."
- **I3: Inventory and plan file locations are undefined.** Fix: in step 1, `python3 "$ENTRYPOINT" inventory --project-dir <target> > "$WORK/inventory.json"`,
  where `$WORK` is a scratch dir outside `<target>/.planning/`. In step 2, add "`--out` must be an existing directory outside the project's
  `.planning/`; keeping `inventory.json` beside `plan.json` lets `plan-set`/`plan-unset` omit `--inventory`."
- **I4: The `--force` example teaches agents to add the flag by habit.** Fix: delete `--force` from the `workflow.cross_ai_command` example (or the whole line;
  apply already sets that value). Add a NEVER: "Never pass `--force` to `plan-set` unless the user explicitly chose a value outside the
  listed candidates. It bypasses the candidate check and the full-permissions command guard."
- **I5: v1 `apply-execution` silently replaces v2 runner wiring.** Fix: replace "never mix v1 writes ... without intent" with "Never run v1
  `apply-execution`/`apply-review` on a project configured by v2 `apply`. `apply-execution` overwrites `workflow.cross_ai_command` with a
  direct CLI command, so `.planning/scripts/cross-ai.mjs` stops being used."
- **I6: A machine-specific fact is written as general guidance (ponytail bullet).** Fix: replace it with "Inventory reports
  `ponytail_visibility` per host. Report what it says; do not assume plugin-cache-only visibility."
- **I7: The v1 path regressed compared with the baseline.** "Same as prior skill" points to nothing, and the baseline's v1 safeguards were dropped. Fix: restore
  three one-line rules under the v1 path: run `ensure-project` first (otherwise `config-set` silently writes a sparse config); pass the `detect-*` `{cli, model}`
  output through unchanged (`apply-execution` flags are optional, `apply-review` flags are required); skip `apply-claude-md-path` when the detected path
  is `null`. Replace `--model x` with `--model <detected model>`.

### Minor
- M1: The code blocks use `python3 ai-kit-gsd-curated-config.py`, while the prose says `python3 "$ENTRYPOINT"`. Use `"$ENTRYPOINT"` in the blocks too.
- M2: Rewrite the "Live timeout" bullet: "The runner's live outer timeout comes from `workflow.cross_ai_timeout` in `.planning/config.json`, or
  `.planning/workstreams/$GSD_WORKSTREAM/config.json` when `GSD_WORKSTREAM` is set. The baked timeout caps it from below."
- M3: Simplify the cleanup-warnings sentence ("the next apply's refusal must agree after its `apply --dry-run` check") to "If a marker remains,
  run `apply --dry-run`; it prints the recorded recovery steps; follow them."
- M4: Define "System One" in a few words (the jev backend the inventory TCP-probes), or drop the term.
- M5: Document the `script:cross-ai.model.<runner>` / `script:cross-ai.prefer` plan-set keys. They are the only way to pick runner models, and
  agents meet them in `needs_choice` without context.
- M6: Description: add v2 trigger phrases ("configure .planning/config.json", "wire skills to GSD agents", "set up a cross-AI execution runner").
- M7: Restore a short Why column in the Common mistakes table. The baseline's reasons were its strongest anti-pattern content.

## Verdict: FAIL

- Current 88/120 (C), baseline 104/120 (B). That is a 16-point regression, below the 96 bar, with 7 Important findings open.
- The CLI surface is accurate. The failures are in guidance: missing question protocol, wrong exit semantics, undefined file locations,
  examples agents will copy, and the v1 regression.
- Fixing I1-I7 should bring it back to at least about 100 without restructuring.

## Comparison with the executor self-check (18-SKILL-JUDGE.md)

- The self-check judged the same blob (bb81efde). It scored baseline 100 and current 103 (PASS, one Minor finding, now fixed).
- This review: baseline 104, current 88 (FAIL).
- The baselines roughly agree (100 vs 104). The current scores diverge by 15. The biggest gaps are D2 (13 vs 10), D6 (13 vs 11) and D8 (13 vs 10).
- The self-check gave credit for the new v2 content. It did not test the instructions against the CLI's actual behavior:
  - inventory is stdout-only;
  - `--out` is refused under `.planning/`;
  - `--force` is unnecessary in its example;
  - v2 exit 2 can be fixed and retried;
  - v1 `apply-execution` clobbers the runner.
- It also did not register that the v1 safeguards were dropped. That loss is why this review finds a regression where the self-check found +3.
- Its only finding (internal decision IDs) was cosmetic.
