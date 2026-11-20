# Phase 39: Lane capability blocks and lens skills - Discussion Log (standard discuss mode (`--analyze --all --batch`))

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-16
**Phase:** 39-lane-capability-blocks-and-lens-skills
**Mode:** interactive path: standard discuss mode (`--analyze --all --batch`) with the owner answering only the unclear gray areas
(none needed; one item is provisional and flagged), jev screening for every other gray area, best design over smallest diff
(mvp-mode inactive), code index
**Areas analyzed:** layout; where capability facts are computed; reading them; block content; child PATH; code-index line; role list;
scan and sources; sorter and persistence; lens delivery and notes; skill-path setting; window check; embedded-value validator;
after-approval pass; curated-config read; summary line; jev and herdr; spike; cross-phase amendments

## Assumptions Presented

No analyzer subagent ran: the phase subagent verified the facts itself (the runner's `--print-argv` for every runtime and role, the
hosts' `--help`, pi's own docs, the host skill directories and MCP configs by name, the code paths of the guidance builder and the
dispatch commands) and ran the analysis inline; this host nests subagents, but the facts needed live commands in this shell. Not run
live: any model call, a probe of path reading or shell use under a read-only lane (the spike of D-18), a client-side window figure
from the catalog (Phase 35 has not executed).

| Assumption | Confidence | Evidence |
|---|---|---|
| The guidance builder tells each lane what it can do | Wrong | It takes no argv and no role: a pi or copilot review lane (no shell tool) is told to prefer `rg` and the CLI form (code reading, live argv) |
| Tool availability is a property of the child | Half wrong | The map comes from the parent's PATH, computed once; the child's PATH is the parent's today but is built separately |
| Lens skills can always be inlined where a lane cannot load them | Wrong | `simplify` has no file anywhere on this machine; pi can load by path (docs); three hosts have an unverified `--add-dir` |
| A shared skill table needs a new cross-skill import | No | `gsd_catalog.load_ai_kit_spec_module` already loads modules of the review package |
| The runner prints what a lane can do | No | `--print-argv` prints runtime, binary and argv only |
| A window check exists in the pre-spawn path | No | Only the runner's argv length limit exists; the host's `context_length_exceeded` is 38.1's post-call class |
| copilot is covered by the GSD config skill's host list | No | `host.HOSTS` has five hosts and no copilot |

## jev screening

One jev request for the SPEC step's open items (10 items) and one for this step's (9 items); the five confident answers that
contradicted the evidence got one second-opinion request each (reordered options, remote rung). Each item got one advisory answer;
low items are decided by own reasoning. Summaries only, no code or config values.

| Item | jev | Outcome |
|---|---|---|
| module layout | typesafe module_per_concern 0.87 (laya none_of_these low 0.48) | D-01 |
| where capability facts are computed | laya none_of_these 0.85; second opinion typesafe runner_row low 0.70 | **jev overridden**; **Own reasoning:** the runner row (D-02, ledger) |
| default lens delivery | typesafe inline_unless_verified 0.95 (laya low 0.38) | D-10 |
| token estimate | laya none_of_these 0.75; second opinion typesafe low_ratio_estimate 0.89 | **jev overridden**: D-12 |
| window with an unverified context form | typesafe unknown_unless_user_stated 0.86 (laya low 0.64) | D-12 |
| table home | laya none_of_these 0.85; second opinion typesafe review_package_module 0.80 | **jev overridden**: D-08 |
| where a confirmed sort is kept | typesafe config_roles_table 0.97 (laya low 0.57) | D-09 |
| how an unknown skill is sorted | laya none_of_these 0.93; second opinion typesafe helper_with_fallback low 0.79 | **jev overridden**; **Own reasoning:** helper when present, owner confirms (D-09, ledger) |
| a built-in lens with no file | laya none_of_these low 0.39; second opinion typesafe native_only_named 0.86 | D-10 |
| the editing pass after approval | typesafe opt_in_with_diff 0.83 (laya low 0.28) | D-14, **needs owner confirmation** (ledger) |
| herdr use | typesafe not_used 0.87 (laya low 0.63) | D-16 |
| child PATH | laya child_env_at_dispatch low 0.56; typesafe parent_path_cached low 0.71 | **Own reasoning:** the child's PATH at dispatch time (D-05, ledger) |
| classifier home | typesafe read_only_proposal_command 0.84 (laya low 0.43) | D-09 |
| closed reason lists | typesafe two_closed_lists 0.94 (laya low 0.39) | D-10, D-12 |
| refusal surface | typesafe refused_result_no_spawn 0.84; reordered second opinion low none_of_these 0.48 | D-12 (the first confident answer stands) |
| lens budget | laya none_of_these low 0.37; typesafe skip_whole_lens_named low 0.70 | **Own reasoning:** skip the lens whole, name it (D-10, ledger) |
| skill-path setting | typesafe runner_setting_with_forms 0.86 (laya low 0.64) | D-11 |
| role list | typesafe closed_list_with_lock 0.91 (laya low 0.63) | D-07 |
| curated-config read | laya none_of_these 0.70; second opinion typesafe derive_same_shape low 0.73 | **jev overridden**; **Own reasoning:** derive with the same shape (D-15, ledger) |

## Live facts that changed the plan

- The runner's final argv differs by host in ways the guidance never sees (pi and copilot review have no shell tool and no MCP):
  the facts must come from the argv, so the runner computes them (D-02, D-04).
- pi documents that `--skill` paths still load under `--no-skills`; claude, copilot and cursor have an `--add-dir` flag of unverified
  effect: path delivery is verified for one host only, so inlining is the default and a spike verifies the rest (D-10, D-11, D-18).
- `simplify` has no file on disk: it cannot be inlined, so only a native lane of its host runs it (D-10).
- The shared table can live in the review package because the GSD config skill already loads that package's modules (D-08).
- The roadmap and REV-03 said a lens is inlined where a path fails (Claude built-ins, pi through an allow-listed `--skill`): amended
  with the facts above (D-19).

## Corrections Made

- The first draft of the SPEC counted four other copies of the host skill-root list; the repository holds five (three skill scripts
  and two tools files). The SPEC and CONTEXT say five.
- The first draft attributed `CODEX_HOME` and `COPILOT_HOME` to the existing skill-root scripts (only `detection.py` reads them) and
  did not say that codex and copilot loading skills from their directories is unverified (only the directories' existence is);
  CONTEXT D-08 now says both.

## External Research

None (no web search): the facts are this machine's hosts, their own help and docs, the code and the config files. No Artificial
Analysis or web source is read in this phase.
