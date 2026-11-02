# Phase 20: Live Validation on Codex + Opencode - Pattern Map

**Mapped:** 2026-10-17
**Files analyzed:** 9 modified, 3 new evidence/script docs
**Analogs found:** 9 / 9 code files (all tracked; checked with `git ls-files`)

Approach: Phase 20 is harness generalization. Every code change extends an existing Phase 19
function in place; no new Python module is needed (D-04, "one module").

## File Classification

| Modified / New File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `tests/gsd_curated_eval.py` `promised`/`_set_entries`/`compare`/`live_tables` (host-aware) | utility (oracle) | transform | same functions, claude branch (lines 436-520) | exact |
| `tests/gsd_curated_eval.py` `run_matrix` + `_write_control_plan`/`_control_one` (non-claude control) | utility | batch | `_control_one` (727-748), `run_matrix` (808-841) | exact |
| `tests/gsd_curated_eval.py` snapshot allowlist (`_strict_files`, `_strict_listings`, `_host_managed_files`, TOML semantic sha) | utility (guard) | file-I/O | `_strict_files` (191-216), `_tree_sha` (251-271) | exact |
| `tests/gsd_curated_eval.py` `_scratch_project` + smoke install step + planned==baked reader | utility | file-I/O, batch | `_scratch_project` (3915-3928), `_smoke_ai_kit` (4056-4073), `run_smoke` (4223-4260) | exact |
| `tests/gsd_curated_eval.py` `_cmd_smoke` (installer dir option, throwaway HOME) | CLI entry | request-response | `_cmd_smoke` (4321-4357) | exact |
| `tests/test_gsd_curated_eval.py` (replace `test_matrix_refuses_non_claude_host`; add oracle, control, allowlist, baked tests) | test | unit | `TestOracle` (87), `TestSnapshot` (242), `TestMatrixEnv` (403) | exact |
| `tests/test_ai_kit_gsd_curated_config_matrix.py` (per-host matrix incl. controls) | test | e2e real node | `TestResolveModelMatrix` (class at line 33) | exact |
| `skills/ai-kit-spec-review/ai_kit_spec/detection.py` + `tests/test_ai_kit_spec_runtimes_table.py` (codex labels / table) | config (table) | transform | `_LABEL_CODEX_*` (51-60), `RUNTIMES["codex"]` (101-107), docstring (208-250) | exact |
| `skills/ai-kit-gsd-curated-config/.../cross_ai.py` `eligible_lanes` + `plan_io._host_reviewer_problem` (D-11 regression test only) | service | request-response | itself (enforcement exists) + `tests/test_curated_config_recommend.py` `make_inventory(host=...)` | exact |
| Stale notes: `followups.py:229`, `host.py:24`, `cross_ai.py:182`, `SKILL.md:247` | docs/strings | n/a | each pinned by a test (Pitfall 7) | exact |
| `20-SMOKE-CODEX.md`, `20-SMOKE-OPENCODE.md`, `20-INTERACTIVE-*.md` | evidence/doc | n/a | `render_smoke_evidence` output (placeholders via `_smoke_placeholders`) | role-match |

## Pattern Assignments

### Host-aware oracle (`tests/gsd_curated_eval.py`, transform)

**Analog:** `promised` / `_set_entries` / `compare`, lines 470-520. Keep the branch order (override, phase shift, tier) and add a tier -> host-model step.

Existing claude core to extend (lines 478-492):
```python
sets = _set_entries(plan)
override = f"model_overrides.{agent}"
if override in sets:
    return str(sets[override])
phase = (tables.get("phase") or {}).get(agent)
shift = f"models.{phase}" if phase else None
if shift and shift in sets:
    return str(sets[shift])
entry, profile = (tables.get("profiles") or {}).get(agent), plan.get("profile")
if not isinstance(entry, dict) or profile not in entry:
    raise _refusal(1, f"no live MODEL_PROFILES entry for {agent}/{profile}")
return str(entry[profile])
```
Changes: `_set_entries` must also accept `op == "keep"` (codex native slots are keep entries); resolve the tier through `model_profile_overrides.<host>.<tier>` then `tables["runtime_profiles"][host][tier]` (add `RUNTIME_PROFILE_MAP` to `_LIVE_TABLES_SCRIPT`, lines 436-441, and to the return dict of `live_tables`, line 467). Spiked body is in 20-RESEARCH.md "Pattern 1". `compare` (505-519): tier check applies only when the agent has no `model_overrides` entry (resolve-model reports `tier: unknown` otherwise).
Error style: `raise _refusal(1, "...")` (class at line 72). Keep it.

### Matrix + non-claude control (`run_matrix`, `_control_one`)

**Analog:** `_control_one` lines 727-748 and `_write_control_plan` 714-724.
```python
def _write_control_plan(bundle: dict, plan: dict) -> None:
    entries = plan.get("entries") or []
    kept = [entry for entry in entries if entry.get("key") != "resolve_model_ids"]
    if len(kept) == len(entries):
        raise _refusal(1, "control 1: no resolve_model_ids entry to remove")
    path = os.path.join(os.path.dirname(bundle["plan_path"]), "plan-control1.json")
    _write_json(_abs(path), {**plan, "entries": kept})
    bundle["plan_path"] = path
```
Host variant: drop entries whose key startswith `model_overrides.` (keep the same "no entry to remove" refusal), expected failures = agents that had an override (`_unoverridden` at line 705 is the inverse helper). Remove the guard at `run_matrix` lines 833-834 (`if host != "claude": raise _refusal(2, MESSAGE_NON_CLAUDE)`) and the `MESSAGE_NON_CLAUDE` constant (114-117). Skip `_informational_row` for non-claude (its poison is claude-only; `POISON_DEFAULTS` at 112 sets `runtime: codex`). `run_matrix` return shape (rows/controls/informational/gsd_core/agents/checks) must stay stable for `_render_matrix` and the e2e test's `checks` arithmetic.
Host plumbing already exists: `matrix_env(bundle, home, host)` (548-552) sets `GSD_RUNTIME`; `_seams(..., host)` (541).

### Allowlist snapshot (D-10, file-I/O)

**Analog:** `_strict_files` (191-216), `_strict_listings` (219-228), `_host_managed_files` (231-248), `_tree_sha` (251-271).
Label convention: `f"{HOME_LABEL}/<relative>"` keys, values from `_file_sha` / `_dir_names`; absence is `None`.
```python
f"{HOME_LABEL}/.gsd/defaults.json": home / ".gsd" / "defaults.json",
...
f"{HOME_LABEL}/.gsd": _dir_names(home / ".gsd"),
```
Add strict listings for `~/.codex/agents`, `~/.config/opencode/{agents,commands,skills,plugins}` and strict files `~/.codex/hooks.json`, `~/.config/opencode/opencode.jsonc`. Move `~/.codex/config.toml` out of `_host_managed_files` (currently a tripwire at lines 243-247) into a semantic entry: `tomllib.loads`, drop `projects` keys that start with the scratch prefix, sha256 of `json.dumps(sort_keys=True)` (pattern in 20-RESEARCH.md "Throwaway HOME + allowlist snapshot"). Never list or hash `auth.json`, `service.json`, or `CREDENTIALS_BASENAME` (line 98; `test_credentials_file_is_never_snapshot` pins this). Output stays labels-only (`_snapshot_report`, 301-309).

### Scratch project + smoke install step (`_scratch_project`, `run_smoke`)

**Analog:** lines 3915-3928:
```python
def _scratch_project(work: str, label: str, with_planning: bool) -> str:
    project = os.path.join(work, label)
    os.makedirs(project)
    subprocess.run(["git", "init", "-q", project], check=True)
    link = os.path.join(project, ".claude", "gsd-core")
    os.makedirs(os.path.dirname(link), exist_ok=True)
    os.symlink(os.path.join(REPO_ROOT, ".claude", "gsd-core"), link)
    ...
```
Changes: symlink only when host is claude (it wins `local_gsd_core_roots` order and would shadow a host install); for codex/opencode run the installer (`node <installer>/bin/install.js --<host> --local --no-legacy-cleanup`, cwd = project, `HOME` = throwaway dir) before inventory, as a new `_step(...)`-wrapped call. Scratch stays under `tempfile.mkdtemp(prefix="smoke-")` (as `_cmd_smoke` line ~4339 does), never under the repo (ancestor `.planning/config.json` walk).
Step recording pattern (3905-3912): `_step(name, fn)` returns `{"name","ok","detail"}`, never raises, so the snapshot always runs. New steps (install, planned==baked) must use it and be appended in `run_smoke` between `_smoke_project_a/b` as the existing ones are.
`_smoke_ai_kit` (4056-4073) is the template for a step: nested `run()` returning a detail string; guarded by dry run only (no `refuse_repo_apply`).
`SmokeCtx` (3653-3662) is a NamedTuple; add the installer dir and throwaway home as defaulted trailing fields so existing call sites keep working.

### Smoke CLI (`_cmd_smoke`, lines 4321-4357)

Already host-aware: `host_mod.detect_host(dict(os.environ), args.host)`, env carries `GSD_RUNTIME`, `XDG_CACHE_HOME` under `work`, `finally: shutil.rmtree(work)`. Add an `--installer-dir` argument via `_build_parser` (4360+, same `sub.add_parser` style); discover the pnpm store copy at run time, never hardcode a path (AGENTS.md rule; research Open Question 1).

### Planned == baked readers (D-07, file-I/O)

No close analog; closest is `validate_applied` / `ValidateCtx` (3665+) for "compare applied files to the plan". Use `tomllib` for `.codex/agents/gsd-*.toml` (only explicit `model_overrides` pins carry `model`) and a small frontmatter `model:` line parse for `.opencode/agents/gsd-*.md`. Compare `model:` only (ignore `variant:`). Run only after the post-apply installer re-run; idempotency check = `_tree_sha(agents_dir)` before/after (reuse, 251-271).

### Detection table (`detection.py`, config)

**Analog:** itself. Label constants + `Runtime` row:
```python
_LABEL_CODEX_THREAD = ("observed in real codex session shell snapshots ... not yet live-verified from a codex host (Phase 20, EVAL-04).")
_LABEL_CODEX_VERSION = ("source-inspected-only ... not a live subprocess.")
"codex": Runtime(("codex",),
    (("CODEX_THREAD_ID", _LABEL_CODEX_THREAD), ("CODEX_VERSION", _LABEL_CODEX_VERSION)),
    scrub_signals=("CODEX_SANDBOX",), list_argv=("debug", "models"), mcp_list=True),
```
Update labels and the `detect_current_runtime` docstring bullets (lines 235-248) to "live-verified (Phase 20)" only for names the interactive run records; the order is already `pi > opencode > cursor > codex > claude` (D-02 done). The research found both names present in a 0.162.1 `codex exec` session, so D-05's "drop CODEX_VERSION" is stale: decide from the interactive names list. Pinning tests in `tests/test_ai_kit_spec_runtimes_table.py`: names list (lines 30-33), `len(HOST_SIGNAL_ENV_VARS) == 11` (line 85), precedence pairs (88-94). Change them in the same commit. SKILL/AGENTS.md certainty rule: do not label live-verified without the recorded evidence.

### D-11 host-never-a-lane regression test

**Analog (enforcement):** `cross_ai.py` lane loop skips `slug in (host, "pi")` (line ~217); `plan_io._host_reviewer_problem` (lines 542-550):
```python
if isinstance(value, list) and plan_host in value:
    return f"review.default_reviewers: {plan_host!r} is the host CLI, not a review lane"
```
**Analog (test fixture):** `tests/test_curated_config_recommend.py` `make_inventory(host="codex", ...)` (line 257) and `tests/test_curated_config_plan_edit.py`. Add a loop over `("codex", "opencode")` asserting the host slug is absent from proposed lanes and the plan-edit problem fires. Enforcement already exists, so this is test-only plus SKILL.md doc.

### e2e matrix test

**Analog:** `tests/test_ai_kit_gsd_curated_config_matrix.py` `TestResolveModelMatrix` (setUpClass runs `ev.run_matrix(node_bin, _TOOLS, cls.home_dir)` once, asserts on the structured result; `_ROW_COUNT`, `_gsd16_or_skip` guard). Parameterize by host (run once per host, `host="codex"`/`"opencode"`); keep the `checks == rows*agents + 2*agents` assertion, `test_repo_config_untouched`, and the strict-snapshot-unchanged test. Note the claude class uses the real home; for non-claude hosts the matrix applies only to scratch projects.

### Headless dispatch (cross-AI runner)

**Analog:** `ai_kit_spec/runner_dispatch.child_env` (line 130): copies env, pops every `HOST_SIGNAL_ENV_VARS` name, applies `extra` last. Use it for D-01 clean-env headless runs; no new env-scrub helper. Runner argv check without a model call: `node .planning/scripts/cross-ai.mjs --print-argv ...`. Adding `--standalone` to the opencode profile is a candidate one-line fix in `.planning/scripts/cross-ai.mjs` with a runner `--self-test` regression (verify tracked status first: it is a generated copy of a template, so fix the template, not the generated file).

## Shared Patterns

### Refusal / exit style
**Source:** `tests/gsd_curated_eval.py` `_refusal(SystemExit)` (line 72), `raise _refusal(1, reason)`; tests assert `caught.exception.exit_code` and `.reason` (see `test_matrix_refuses_non_claude_host`, lines 446-460, to be replaced).

### Placeholders and secrets in evidence
**Source:** `label_path` (150), `_smoke_placeholders` (4263), `secret_scan` (2011). Evidence uses `<scratch>`, `<home>`, `<worktree>` only; env vars by name only; run `python3 tests/gsd_curated_eval.py secret-scan <files>` before commit.

### Real apply only on scratch
**Source:** `refuse_repo_apply` (558) called first by `_apply_bundle` (568). Every new apply path calls it.

### Test seams instead of mocks
**Source:** `_MatrixCtx` (522-538) injects `bundle_fn/apply_fn/run_fn/tables_fn`; `tests/test_gsd_curated_eval.py` `_ctx(bundle_fn=...)`. New host tests inject the same seams; a hermetic test never needs node.

### Test registration
`tests/test_gate_scope.py` enforces group membership; new `tests/test_*.py` join `unit` automatically; node-needing modules are in the `e2e` exception set. Prefer extending existing modules (no new test file).

## No Analog Found

| File / piece | Role | Data Flow | Reason |
|---|---|---|---|
| TOML semantic compare (`tomllib`, minus `projects."<scratch>"`) | utility | transform | No TOML reader in the harness; use research snippet (stdlib) |
| Baked-agent frontmatter / TOML readers | utility | file-I/O | Nothing parses installer output today |
| Interactive-run scripts (`20-INTERACTIVE-*.md`) | doc | n/a | No prior user-run script; follow D-01 (steps, paste prompts, names-only env dump, smoke command, snapshot check) |
| `opencode debug agents` parse (D-07 last link) | utility | transform | Subcommand is `debug agents` (list) in v2.0.31, output shape unobserved; write parse after first observation, via a standalone path |

## Metadata

**Analog search scope:** `tests/`, `skills/ai-kit-spec-review/ai_kit_spec/`, `skills/ai-kit-gsd-curated-config/`
**Files scanned:** about 12 (targeted ranges of a 4,000+ line harness via grep then offset reads)
**Pattern extraction date:** 2026-10-17
