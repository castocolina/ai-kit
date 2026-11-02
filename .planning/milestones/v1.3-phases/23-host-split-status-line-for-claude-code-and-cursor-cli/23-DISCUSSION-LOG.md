# Phase 23: Host-split status line - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-10-14
**Phase:** 23-host-split-status-line-for-claude-code-and-cursor-cli
**Mode:** assumptions (`--analyze --all --batch`), jev screening, best over easy, CodeGraph
**Areas analyzed:** Part A audit/layout/oracle; gauge, quota normalization (R3-2), Cursor segments (R3-6); fetch, transport and credentials (R3-4), spike, cache; config files, env prefixes, providers (R3-3), TOML writes (R3-5), Cursor config dir; Part C setup and wizard (R3-1)

## Assumptions Presented

The analyzer was `gsd-assumptions-analyzer` (sonnet), with 93 tool calls. It ran scratch AST and
call-graph scripts, a urllib redirect experiment and a concurrent `os.link` experiment, and read
the installed Cursor 2026.10.01 bundle statically. No live Cursor, token or network calls.

| Assumption | Confidence | Evidence |
|---|---|---|
| 182-row audit with taint cross-check | Likely | scratch `ast_inv.py`, `graph.py`; `test_arch.py:133` |
| Role-split layout plus types leaf | Unclear | one upward edge `:565→:1983`; design §4.2 cycle; owner decision |
| Neutral `Context` + typed host | Likely | bundle payload builder; golden `fresh-clear-120x45` |
| Oracle before a pure move | Likely | 562 `sl.` refs; golden covers default-on only |
| Arch rules and anchored reference check | Confident | `test_arch.py:46,197,377-381`; `rg -c` history hits |
| Gauge split, behavior kept | Confident | `:1493-1533,1677-1715` |
| Per-segment windows | Likely | `IncludedUsagePeriod` enum in descriptors |
| First-party normalization | Likely | bundle `usage-data.ts`; POC fixtures are made up |
| Four segments, no toggles | Likely | `:72-123`; design §5.2 |
| POC reference only | Confident | POC FINDINGS; research 13 |
| Cache-only render + refresher | Likely | bundle `use-status-line.ts` debounce/abort/close |
| Refuse every redirect | Likely | `redir_exp.py` |
| Scratch `CURSOR_CONFIG_DIR` for the spike | Likely | bundle `paths.js`; config mtime today |
| Cache states, git timeouts, bad TOML | Confident | `:503,:760,:831,:2522-2546` |
| Separate provider namespace | Likely | `:615,:668-677,:2056-2078` |
| Link-based create-if-absent | Confident | `link_exp.py` (16 processes, 1 winner) |
| Separate Cursor config-dir resolver | Likely | bundle `paths.js` vs `190.index.js` hooks |
| Host-keyed wizard | Likely | `wizard_app.py:101-126,208,236`; `setup.py:2413-2560` |
| Per-host wiring, Cursor shape | Confident | bundle statusLine schema; `setup.py:1627,3122` |
| Preview over a synthetic cache | Unclear | `setup.py:232-283,2293` |

## jev screening

One Laya call per item; `needs_fallback` items batched to TypeSafe direct. Summaries only.

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| B01 audit rows | defs_only 0.81 | with_assignments 0.75 (second opinion) | **Laya overridden**: D-01 |
| B02 module layout | role_split 0.47 (fb) | hybrid 0.62 (fb) | **Own reasoning:** role split per the owner design (D-02, ledger) |
| B03 context segment | cursor_folded 0.53 (fb) | shared_nullable 0.99 | D-06 |
| B04 oracle | oracle_then_move 0.68 (fb) | oracle_then_move 0.99 | D-05 |
| B05 gauge window | billing_cycle_all 0.63 (fb) | per_segment_window 0.91 | D-09 |
| B06 missing percent | show_zero 0.48 (fb) | derive_else_hide 0.49 (fb) | **Own reasoning:** derive else hide (D-11, ledger) |
| B07 segments | four_api_off 0.45 (fb) | four_api_off 0.95 | D-08 |
| B08 fetch | raise_knobs 0.48 (fb) | cache_plus_refresher 0.94 | D-13 |
| B09 redirects | refuse_all 0.50 (fb) | refuse_all 0.72 | D-15 |
| B10 spike capture | edit_real_file 0.72 | scratch_config_dir 0.98 (second opinion) | **Laya overridden**: D-14 |
| B11 providers | separate_namespace 0.34 (fb) | separate_namespace 0.88 | D-18 |
| B12 cursor dir | fix_both 0.97 | separate_resolver 0.99 (second opinion) | **Laya overridden**: D-21, backlog 999.2 |
| B13 wizard | headless_only 0.51 (fb) | host_keyed_one_app 0.95 | D-22 |
| B14 preview | static_samples 0.35 (fb) | static_samples 0.66 (fb) | **Own reasoning:** synthetic cache (D-24, ledger) |

## Live facts that changed the plan

- Stock urllib forwards `Authorization` on cross-origin 301/302 and turns a POST into a
  bodiless GET: the SPEC R8 edge row "same-origin redirect is followed" is superseded.
- The Cursor CLI rewrites `cli-config.json` during use: SPEC R5's byte-identical restore is
  superseded by a scratch `CURSOR_CONFIG_DIR`.
- The unanchored R3 `rg` pattern matches `claude-status-line.py` and ~140 history files.
- `render_width_chars` is `columns - 4` (design §5.1 amended); the ROADMAP gauge supersedes
  design §5.2's on-demand ramp.
- Hooks are always read from `~/.cursor/hooks.json`, unlike `cli-config.json`: backlog 999.2.

## Corrections Made

No user corrections. Amendments: 23-SPEC R1, R3, R4, R5, the R5 and R8 edge rows and a
constraint; ROADMAP Phase 23 goal (module names are shorthand) and backlog 999.2; design §5.1,
§5.2.
