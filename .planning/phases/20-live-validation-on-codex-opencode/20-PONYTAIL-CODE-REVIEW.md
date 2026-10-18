# Ponytail review: Phase 20 code (`git diff 43989c2..HEAD`, 21 files, +1411/-280)

1. What it does: the eval harness `tests/gsd_curated_eval.py` (+~720) gains a host-aware matrix oracle (`_host_model`, `RUNTIME_PROFILE_MAP` from `model-catalog.cjs`), a semantic allowlist snapshot for `~/.codex` and `~/.config/opencode` (D-10), and a non-Claude smoke. That smoke does a pinned local gsd-core install under a throwaway HOME (D-09), a planned == baked == resolve-model chain (D-07), a generated-paths list (D-12) and artifact export. The product changes are small: runner template 4 (`opencode run --standalone`), D-02/D-05 detection labels, a gitignore-by-prefix follow-up note (D-12), D-11 docs and tests, and the codex/opencode matrix classes.
2. Three correctness bugs, all in what the evidence or the product says, not in what it does. The smoke evidence renderer prints fixed text instead of results: "all equal" when the planned == baked step failed, and a "local install" section on claude where nothing was installed. The product's codex follow-up note says opencode writes `.codex/.gitignore`. The smoke's generated-paths list repeats every path twice. I checked all three live.
3. Most of the growth is one copy-paste: the ~50-line planned == baked == resolve-model block appears in both `_smoke_project_a` and `_smoke_project_b`, and already differs between the two copies. It also re-implements `_set_entries`, `_resolve_all` and `_mismatches`, which the matrix already has.
4. The e2e matrix module runs the Claude matrix twice: unittest also collects the `unittest.TestCase`-based mixin as a test class.
5. Nothing below conflicts with a locked decision in 20-CONTEXT.md (checked against D-02, D-05, D-07, D-09, D-10, D-11 and D-12; the notes say where a fix touches one). Rough lean estimate: -110 to -130 lines, mostly in `tests/gsd_curated_eval.py`. Behavior stays the same apart from the bug fixes.

## HIGH

### H1. The smoke evidence sections print fixed text, not results
- **Where:** `tests/gsd_curated_eval.py:4719-4740` (`render_smoke_evidence`, "## Local install" and "## Planned vs baked"), `:4826-4840` (`_cmd_smoke`'s `result.update`), `:4434-4455` (A's `post.update`), `:4591` (B's `report["idempotent"] = True`), `:4658` (the `idempotent` aggregate).
- **Finding:** These sections show text that does not depend on what happened:
  - Every mismatch is raised as `SystemExit` before `baked_summary` is set. So when planned == baked fails, `baked` is `{}` and the renderer prints `- agents: 0` / `- all equal`. I checked live: a result whose post step has `ok: False, detail: "planned != baked"` renders "all equal".
  - The `mismatches` field is always `[]`, so the `- mismatches:` branch can never run.
  - `_cmd_smoke` hard-codes `local_install = {"scope": "local", "root": "<scratch-a>/.<host>/gsd-core", "version": pinned}` and both `install_roots`, whether the install step passed, failed, or (on claude) never ran. On claude the evidence also claims an installer and an installer env "under <install-home>".
  - B sets `idempotent = True` without checking anything. On claude, A's post step leaves it `False`, so a claude smoke reports "idempotent re-install: no".
  - The update re-copies `baked`, `generated_paths`, `artifacts` and `idempotent` from `result` into `result`, which changes nothing.

  This breaks the project's core rule: never claim more certainty than was verified. The overall exit code and the step list are still right.
- **Fix:**
  - Only set `baked_summary` from a check that ran. Render "Planned vs baked" only when it is present, and print `not run / failed (see step N)` otherwise. Delete the always-empty `mismatches` field and its render branch.
  - Build `local_install` from the install step's own result (`ok`, detail). On claude, print `not applicable` and skip the `~/.gsd/defaults.json` seed copy.
  - Delete B's hard-coded `idempotent` and the no-op re-copies in `_cmd_smoke`. Aggregate `idempotent` only over steps that set it.
  - Add one hermetic test: render a result whose post step failed and assert "all equal" is absent.

  About -15 lines.

### H2. The codex follow-up note tells users opencode writes `.codex/.gitignore`
- **Where:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py:235-245` (`_gitignore_prefix_note`).
- **Finding:** On a codex host the shipped product prints "... (.codex = .codex); never ignore the whole directory (opencode writes its own .codex/.gitignore there)" (checked live). D-12 says only opencode drops its own `.gitignore` into `.opencode/`. The `({host_dir} = {host_dir})` part says the same thing on both sides on every host. The `host_dir is None` guard can never fire, because both hosts are in `HOST_DIRS`. `test_gitignore_prefix_note_is_only_for_non_claude_hosts` checks only substrings, so it misses this.
- **Fix:** Drop the `= ` part and the dead guard. Add the "opencode writes its own .gitignore" clause only when `host_name == "opencode"`. Add `assertNotIn("opencode writes", codex_note)` to the existing test. This adds 0 lines net.

## MEDIUM

### M1. The planned == baked == resolve-model chain is written twice, and re-implements the matrix helpers
- **Where:** `tests/gsd_curated_eval.py:4371-4434` (A's `baked_check`) and `:4542-4591` (B's `run`, the `if ctx.host != "claude":` block).
- **Finding:** The two blocks are near-copies of the same chain: `live_tables`, an `entries` dict, `promised_map`, `_baked_models`, `_baked_mismatches`, building a `_MatrixCtx`, a per-agent `_resolve_model` + tier + `compare` loop, and `_write_artifacts`. They already differ:
  - A's error names only the reason (`"resolve-model mismatches: model"`, no agent); B's names the agent.
  - A checks a repeat install; B claims it (H1).
  - A writes `state["baked"]`, `state["resolved"]`, `state["plan"]` (three times) and `state["idempotent"]` (twice), and nothing reads them.

  Inside each copy:
  - the `entries` dict is `_set_entries(plan)` (`:563`, now set+keep) written out again;
  - the per-agent loop is `_resolve_all` (`:714`) followed by `_mismatches(..., host)` (`:718`), which also return every mismatching agent instead of stopping at the first;
  - the `_install_local(...) != install_detail` half of the "third install" check compares two copies of a constant string.
- **Fix:** One `_baked_chain(ctx, project, plan, env, label) -> dict` that does the following, called from A (after its repeat-install tree-sha check) and from B. Keep D-07's three headless links exactly as they are.
  - Promise: `promised_map` comes from `_set_entries`.
  - Baked: `_baked_models` + `_baked_mismatches`.
  - Resolved: `got = _resolve_all(matrix_ctx, agents, project, env)`, then `_mismatches(agents, plan, tables, got, ctx.host)`.
  - It raises with every mismatch row and returns `{baked_summary, generated_paths, artifacts}`.

  Delete the dead `state` writes and the string comparison. About -60 lines.

### M2. The generated-paths list repeats every path, and lists opencode's own `.gitignore` as a path to ignore
- **Where:** `tests/gsd_curated_eval.py:4653` (`run_smoke`), `:4278-4288` (`_generated_paths`), `:4744-4748` (the D-12 decision line).
- **Finding:** A and B scratch projects give the same project-relative labels (`.codex/agents/gsd-x.toml`), and `run_smoke` concatenates both lists. I checked live: a stubbed A and B, each with one path, produce that path twice. `_generated_paths` also adds `.<host>/.gitignore` when it exists (checked live: `['.opencode/.gitignore', '.opencode/agents/gsd-x.md']`). The renderer follows the list with "ignore these prefixes in the target project". D-12 says that file is opencode's own and the directory is shared, so the evidence gives the exact advice D-12 rules out.
- **Fix:** `sorted(set(...))` in `run_smoke` (or take the list from A only). Drop `".gitignore"` from the `_generated_paths` prefix tuple. 1 line changed, 1 deleted. Note: the committed `20-SMOKE-*.md` lists have no duplicates, and in the codex list `gsd-file-manifest.json` comes after `gsd-verifier.toml`. That is not what the current code prints, so regenerate them after this fix.

### M3. Planned == baked counts codex agents with no TOML file as "equal"
- **Where:** `tests/gsd_curated_eval.py:4268-4275` (`_baked_mismatches`), and the test that locks this in at `tests/test_gsd_curated_eval.py:2949`.
- **Finding:** `baked.get(agent) != expected` is `None != None` when the agent file is missing and nothing was promised. So on codex, every agent without a `model_overrides` pin passes even when it has no `.codex/agents/<agent>.toml`. The committed codex evidence lists no TOML for 6 of the 35 agents (`gsd-code-fixer`, `gsd-doc-writer`, `gsd-eval-auditor`, `gsd-intel-updater`, `gsd-research-synthesizer`, `gsd-roadmapper`), yet says "agents: 35, all equal". The `"missing file"` label can only show up for a pinned agent. This may be the installer's real behavior, but the evidence presents it at the same confidence as a compared file.
- **Fix:** Count absent files separately: `absent = sorted(set(promised_map) - set(baked))`. Fail when an absent agent has a non-None promise. Report `compared N, no baked file M (<names>)` in `baked_summary`. That is 3 lines, and it fits D-07's chain wording ("Codex: explicit `model_overrides` pins only").

### M4. The e2e matrix module runs the Claude matrix twice
- **Where:** `tests/test_ai_kit_gsd_curated_config_matrix.py:19` (`class _ResolveModelMatrixMixin(unittest.TestCase)`), `:97-106`.
- **Finding:** `unittest.TestLoader` collects every `TestCase` subclass, whatever its name. I checked live: `loadTestsFromModule` yields `_ResolveModelMatrixMixin` next to the three real classes. So its `setUpClass` runs a full Claude matrix again (420 resolve-model checks, plus applies) in the slowest e2e module, without `_RealGsdTestCase`. The 2619290 "type-checkable" fix caused this.
- **Fix:** Make the base the test: `class TestResolveModelMatrix(_RealGsdTestCase): HOST = "claude"` with the tests in it. Then `class TestResolveModelMatrixCodex(TestResolveModelMatrix): HOST = "codex"`, and the same for opencode. Pyright is still happy, the extra run is gone, and it saves 3 lines.

### M5. Tier selection is written three ways, and `_host_model` re-builds `_set_entries`
- **Where:** `tests/gsd_curated_eval.py:519-545` (`_host_model`'s `entries`), `:718-736` (`_mismatches` tier block), `:4407-4415` and `:4572-4577` (the smoke loops).
- **Finding:**
  - `_host_model` builds a set/keep dict identical to `_set_entries(plan)`.
  - In `_mismatches`, `elif host != "claude": tier = None` can never change anything, because line 1 already gives `None` for non-Claude.
  - `_tier_for` runs twice per agent (once inside `promised`, once for the tier).
  - The smoke loops use a third spelling (`None if override else _tier_for`).
- **Fix:** `entries = _set_entries(plan)` in `_host_model` (-7 lines). Then have one `_promise(agent, plan, tables, host) -> (model, tier | None)` that `promised` and `_mismatches` both use. The tier is `None` for an override, unless it is a Claude tier alias, where the tier is the override itself. This also deletes the smoke copies once M1 lands. About -12 lines.

## LOW

- **L1.** `skills/ai-kit-spec-review/ai_kit_spec/detection.py:52-61`: `_LABEL_CODEX_THREAD` and `_LABEL_CODEX_VERSION` are now the same string. Use one `_LABEL_CODEX` for both signals (`:104`). This changes no behavior, and D-05 keeps both signals.
- **L2.** `tests/test_ai_kit_spec_runtimes_table.py:92`: the `any(...)` after `all(...)` adds nothing. The set-equality assert above it already rules out an empty mapping. Delete the line.
- **L3.** `tests/gsd_curated_eval.py:4051`: `ctx.installer_dir or _cached_installer(version)` can never use its fallback in practice, because `_cmd_smoke` already ran `_cached_installer` and passed the result in. `_install_local` also re-reads and re-checks `package.json`, which `_cached_installer` already did for the cached case. Keep the version check (the trust boundary for `--installer-dir`) and drop the fallback: `installer = ctx.installer_dir`. Update the "no cached" message to fire when it is None.
- **L4.** `tests/gsd_curated_eval.py:4101`, `:4182`: the `_project_env(ctx) if project != str(ctx.repo_root) else ctx.env` condition is written twice, and other call sites skip it. Fold it into `_project_env(ctx, project=None)`.
- **L5.** `tests/gsd_curated_eval.py:282-286`: `_under` already returns True for `path == root` (`commonpath((x, x)) == x`; checked), so `normalized == root or` at `:274` can go.
- **L6.** `tests/gsd_curated_eval.py:4241-4265`: `_baked_models`' opencode branch is a nested `next(...)` inside a conditional expression. `m = re.search(r"(?m)^model:\s*['\"]?([^'\"\n]+)", chunks[1])` reads at a glance and also stops stripping backslashes. About -8 lines.
- **L7.** `tests/test_ai_kit_gsd_curated_config_matrix.py:66`: `test_control_two_clean_defaults_pass` no longer says which agents failed. Put back the `f"control 2 mismatches: {control['mismatches']}"` message: one argument, and it saves a re-run when this real-node test fails.
- **L8.** `tests/gsd_curated_eval.py:349`: `getattr(args, "scratch_root", None)` exists only because a test builds a `Namespace` without the field, since the parser always sets `default=[]`. Use `args.scratch_root` and add `scratch_root=[]` to that one test `Namespace`.

## Not checked

I did not run `make test`, the real-node matrix, or either smoke. The hard rules forbade host CLI probes, and the smoke reads the real home, which I was not allowed to touch. So I could not tell why the committed `20-SMOKE-*.md` generated-paths lists differ from what the current code prints (M2), and I could not confirm whether the 6 TOML-less codex agents (M3) are the installer's intended behavior. I read but did not re-verify the cross-ai.mjs `--standalone` argv against opencode 2.x, the `_control_one` non-Claude discrimination on real data, or the new `test_curated_config_recommend` D-11 test beyond its assertions.
