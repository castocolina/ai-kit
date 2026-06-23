# Status-Line Config Binding Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the `cfg_` env layer of `tools/status-line.py` into an access / convert / bind layering — one type-directed converter shared by env, TOML, and the doctor; a mechanical env-name projection; a generic structure-walk bind that kills the two-pass invocation; a silent render path with doctor-owned validation.

**Architecture:** Three thin layers (Spring `PropertySource` → `ConversionService` → `Binder`, stdlib-only): `cfg_source_get` (access), `cfg_coerce` (convert → value-or-problem), `cfg_bind` (walk the typed `Config`, access→coerce→apply per-field precedence `default < TOML < env`). One converter, two consumption modes: render discards problems (lenient, silent), the doctor collects and emits them. Behavior change (silent render) is isolated to Phase 3.

**Tech Stack:** Python 3.11+ stdlib only (`tomllib`, `ast` for the arch test). Tests via `python3 -m unittest`. Gate via `make validate` (ruff/pylint/pyright-strict/vulture/shellcheck/py-compile) + `make test`.

---

## SCOPE AMENDMENTS (2026-06-23, post-approval — supersede the body where they conflict)

1. **Canonical names only — NO back-compat (new Task 2.0, runs first in Phase 2).** Single user;
   breaking old config/env names is authorized. DELETE: `cfg_env_normalize` + its `_ALIASES`,
   `_LEGACY_SEGMENT_KEYS` + `cfg_forward_legacy_segment`, `_GIT_LEGACY_IGNORED` + the
   `cfg_git_key_problem` "legacy" branch + the `cfg_load_config` git "legacy" continue, and the
   `CC_AI_KIT_CONFIG` fallback in `cfg_config_path` (canonical `CC_AI_KIT_CONFIG_FILE` only). Repoint
   the doctor (drops its `cfg_env_normalize` call + `_LEGACY_SEGMENT_KEYS` import/union). Delete the
   deprecation/forwarding tests; strip the "Deprecated names" sections from README + sample. Golden
   byte-identical (default config has no deprecated keys); old names become unknown keys.
2. **Bind is two functions, NO forwarding.** The single `cfg_bind` in the body is superseded by
   `cfg_bind_scalars` (git/external, BEFORE discovery) + `cfg_bind_segments` (segments, AFTER
   discovery) — env-bound `ext_dir` must precede discovery, provider ids must precede segment bind,
   so one call can't straddle discovery. `cfg_bind_segments` binds known canonical segment keys only
   (no legacy forwarding). This eliminates the throwaway double env-walk (the real "two-pass" cost).
3. **Parity matrix drops the deprecation classes** (`deprecated-alias`, `deprecated-segment-key`) —
   they no longer exist. Remaining classes: invalid-value (env bad-int, TOML wrong-type),
   unknown-key, malformed-file, out-of-range. env-bad-bool stays silent.
4. **FR-9 (Phase 4): move the whole SHELL block to the END** of the module (just before
   `if __name__ == "__main__"`), functional-core-first / impure-shell-last. Renumber banners; update
   the FR-8 block-order arch test to `DEFAULTS → cfg_ → probe_ → fmt_ → util_ → core_ → seg_ → SHELL`.
   Golden byte-identical (call-time name resolution).

## Hard Constraints (EVERY task)

- **Golden byte-identical**: `tests/fixtures/golden/expected.txt` (stdout) unchanged after every task. NEVER run `UPDATE_GOLDEN=1`. The fixture must not appear in any commit diff.
- **Gate green**: `make validate && make test` pass before every commit.
- **FR-R.2**: the probe-timing test (`tests/test_status_line.py` `TestSlowestTiming` / `TestGitProbeMemoized`) stays green.
- **Runtime stdlib-only**: `tools/status-line.py` and `tools/statusline-doctor.py` import only the stdlib.
- **One-way import**: the doctor imports the render core; the core never imports the doctor.
- **Branch**: all work on `refactor/status-line-config-binding` off `main`. `rebase -i` is BLOCKED — Phase 5 uses path-disjoint `git cherry-pick -n` replay.
- **Output language**: English (code, comments, commits, reports).

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `tools/status-line.py` | Render core. Holds the new `cfg_` access/convert/bind layer; render binds silently. | Modify (net shrink) |
| `tools/statusline-doctor.py` | Sole config-validation surface; consumes the bind problem list and emits it. | Modify (absorbs validation) |
| `tests/test_status_line.py` | Core render + cfg_ unit tests. `cfg_env_bool` tests migrate to `cfg_coerce`; render-path stderr-warning assertions removed (Phase 3). | Modify |
| `tests/test_external_segments.py` | External-segment tests; any render-path stderr-warning assertions relocate to the doctor tests. | Modify |
| `tests/test_statusline_doctor.py` | Doctor tests; gains the captured-stderr parity fixture + relocated warning assertions. | Modify |
| `tests/test_arch.py` | FR-8 arch fitness. Rule 1 (`check_config_env_in_cfg`) reduced to the minimal guard. | Modify |
| `README.md`, `tools/statusline.toml.sample` | Document that the doctor is the validation surface; render is silent. | Modify (Phase 3) |

---

## Locked API & Parity Matrix (reference for the executing engineer)

### Target `cfg_` function set

```python
def cfg_warn(msg: str) -> None:
    """The single render-format warning emitter: dim, stderr, 'status-line:' prefix.
    Phase 1 callers print through this; Phase 3 the doctor prints bind problems
    through this, so the relocated text is byte-identical."""

def cfg_coerce(raw: Any, kind: str, source: str, label: str) -> tuple[Any, str | None]:
    """THE converter. kind in {'bool','int'}; source in {'env','toml'}.
    Returns (value, problem). Conventions:
      (value, None)  -> a coerced value to apply.
      (None, None)   -> no override / skip (no real config value is None).
      (None, problem)-> present but not coercible; `problem` is the core warning text.
    source='env'  (raw is str): bool -> _ENV_TRUE/_ENV_FALSE recognized; UNRECOGNIZED
                  string -> (None, None) (tri-state: preserves today's SILENT env-bad-bool).
                  int -> int(raw) or (None, problem).
    source='toml' (raw already typed): bool -> isinstance(raw,bool) or (None, problem);
                  int -> isinstance(raw,int) and not bool, or (None, problem).
    `label` is the message subject (e.g. 'CC_AI_KIT_GIT_CACHE_TTL', "segment 'alt_cost'",
    '[git] cache_ttl'); problem text is f"{label} must be {desc}, got {raw!r} — ignored"
    with desc 'true/false' (bool) or 'an integer' (int)."""

def cfg_source_get(source: str, raw_toml: dict, env: Env, path: tuple[str, ...]) -> Any | None:
    """Access layer. Returns the raw value for `path` from `source`, or None if absent.
    source='env': env name = 'CC_AI_KIT_' + '_'.join(path).upper(); the ('segments', KEY)
    path projects to 'CC_AI_KIT_SEGMENT_<KEY>'. source='toml': nested dict lookup."""

def cfg_bind(raw_toml: dict, env: Env, git: dict, ext_dir: str, ext_ttl: int,
             segments: dict[str, bool]) -> tuple[dict, str, int, dict[str, bool], list[str]]:
    """Bind layer. Per field: default < TOML < env. Present-but-invalid falls back AND
    records a problem; absent falls through. Binds `segments` as the ONE map-rule (legacy
    keys forwarded via cfg_forward_legacy_segment). Returns
    (git, ext_dir, ext_ttl, segments, problems)."""

def cfg_load_config_verbose(env: Env) -> tuple["Config", list[str]]:
    """Resolve the full Config AND return the ordered problem list (for the doctor).
    Binds via cfg_bind; the two-pass env reader is gone (scalars bound, providers
    discovered, segment map bound once)."""

def cfg_load_config(env: Env) -> "Config":
    """Lenient render entrypoint: cfg_load_config_verbose(env)[0]. Emits NOTHING."""
```

`util_to_int(s: str | None) -> int | None` — the former `cfg_to_int`, moved to the `util_` block (pure probe-support parser; not config).

**Deleted**: `cfg_env_bool`, `cfg_env_int`, and the per-token router body of `cfg_env_apply_overrides` (absorbed into `cfg_bind`).

### Bind-walk scope (boundary)

Binds ONLY the `line_conf` groups: `segments`, `git`, `external`. `palette`/`ramps` keep their existing resolvers and merge/replace policy. Does NOT touch SHELL geometry reads, JSON-derived effort, or the `CC_AI_KIT_CONFIG_FILE` bootstrap (stays in `cfg_config_path` — the one explicit pre-bind env read).

### Parity matrix (Phase 3) — doctor emits byte-identical to what render emitted before; render emits NONE after

| Problem class | Source today | Behavior after |
|---|---|---|
| deprecated-alias (env) | `cfg_env_normalize` dim warn | forwarded silently at runtime; doctor reports the deprecation (same text) |
| deprecated-segment-key | `cfg_forward_legacy_segment` dim warn | forwarded silently; doctor reports (same text) |
| invalid-value: env bad-int | `cfg_env_int` dim warn | doctor reports (same text) |
| invalid-value: TOML wrong-type (bool/int) | `cfg_resolve_segments` / git loop dim warn | doctor reports (same text) |
| invalid-value: **env bad-bool** | **SILENT today** | **stays silent** (tri-state no-override; NOT newly surfaced) |
| unknown-key (segment/[git]/palette/ramp) | dim warn | doctor reports (same text) |
| malformed-file | `cfg_load_toml` dim warn | doctor reports (same text) |
| out-of-range (external clamp) | `cfg_place_external` dim warn | doctor reports (same text) |

Oracle: a captured-stderr fixture asserted in `tests/test_statusline_doctor.py`. Render-path stderr assertions are deleted (render is silent).

---

## Phase 0: Branch Setup

### Task 0.1: Branch + green baseline

**Files:** none (git only)

- [ ] **Step 1: Create the branch off main**

```bash
git checkout main
git checkout -b refactor/status-line-config-binding
```

- [ ] **Step 2: Confirm a green baseline**

Run: `make validate && make test`
Expected: all hooks `Passed`; `Ran 540 tests ... OK`; `14 passed, 0 failed`.

- [ ] **Step 3: Record the baseline golden hash (sanity anchor for later)**

Run: `git rev-parse HEAD && sha256sum tests/fixtures/golden/expected.txt`
Expected: prints the HEAD sha and the golden checksum (note them; the checksum must never change).

---

## Phase 1: Conversion layer

### Task 1.1: `cfg_warn` — the single warning emitter

**Files:**
- Modify: `tools/status-line.py` (cfg_ block, near the top after `cfg_git_key_problem`)
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_status_line.py` (in the cfg_ test area near the existing `cfg_env_bool` tests, ~line 1360):

```python
def test_cfg_warn_format(self):
    """cfg_warn wraps a core message in the fixed dim render-format on stderr."""
    import io
    from contextlib import redirect_stderr
    buf = io.StringIO()
    with redirect_stderr(buf):
        sl.cfg_warn("segment 'x' must be true/false, got 'maybe' — ignored")
    self.assertEqual(
        buf.getvalue(),
        f"{sl._DIM}status-line: segment 'x' must be true/false, got 'maybe' — ignored{sl.RESET}\n",
    )
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_status_line -v -k test_cfg_warn_format`
Expected: FAIL — `AttributeError: module 'status_line' has no attribute 'cfg_warn'`.

- [ ] **Step 3: Add `cfg_warn`**

Insert in the cfg_ block of `tools/status-line.py` (after `cfg_git_key_problem`, before `cfg_default_config`):

```python
def cfg_warn(msg: str) -> None:
    """The single render-format config-warning emitter: dim grey, 'status-line:'
    prefix, stderr. Phase-3 the doctor prints bind problems through this same
    wrapper, so relocated warning text is byte-identical to what render emitted."""
    print(f"{_DIM}status-line: {msg}{RESET}", file=sys.stderr)
```

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 -m unittest tests.test_status_line -v -k test_cfg_warn_format`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(status-line): add cfg_warn single warning emitter (FR-4 prep)"
```

### Task 1.2: `cfg_coerce` — the converter

**Files:**
- Modify: `tools/status-line.py` (cfg_ block, after `cfg_warn`)
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_status_line.py`:

```python
def test_cfg_coerce_env_bool(self):
    self.assertEqual(sl.cfg_coerce("yes", "bool", "env", "X"), (True, None))
    self.assertEqual(sl.cfg_coerce("OFF", "bool", "env", "X"), (False, None))
    # unrecognized env bool is tri-state no-override (silent), NOT a problem:
    self.assertEqual(sl.cfg_coerce("maybe", "bool", "env", "X"), (None, None))
    self.assertEqual(sl.cfg_coerce("", "bool", "env", "X"), (None, None))

def test_cfg_coerce_env_int(self):
    self.assertEqual(sl.cfg_coerce("10", "int", "env", "CC_AI_KIT_GIT_CACHE_TTL"), (10, None))
    v, prob = sl.cfg_coerce("x", "int", "env", "CC_AI_KIT_GIT_CACHE_TTL")
    self.assertIsNone(v)
    self.assertEqual(prob, "CC_AI_KIT_GIT_CACHE_TTL must be an integer, got 'x' — ignored")

def test_cfg_coerce_toml_bool(self):
    self.assertEqual(sl.cfg_coerce(True, "bool", "toml", "segment 'alt_cost'"), (True, None))
    # a TOML STRING for a bool key is rejected (strict) — NOT parsed like env:
    v, prob = sl.cfg_coerce("true", "bool", "toml", "segment 'alt_cost'")
    self.assertIsNone(v)
    self.assertEqual(prob, "segment 'alt_cost' must be true/false, got 'true' — ignored")

def test_cfg_coerce_toml_int(self):
    self.assertEqual(sl.cfg_coerce(5, "int", "toml", "[git] cache_ttl"), (5, None))
    # bool is not an int here:
    v, prob = sl.cfg_coerce(True, "int", "toml", "[git] cache_ttl")
    self.assertIsNone(v)
    self.assertEqual(prob, "[git] cache_ttl must be an integer, got True — ignored")
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_status_line -v -k cfg_coerce`
Expected: FAIL — `AttributeError: ... 'cfg_coerce'`.

- [ ] **Step 3: Implement `cfg_coerce`**

Insert after `cfg_warn`:

```python
# kind -> (human description for messages, env-string parser).
# Open dispatch: add a kind by adding one row (no caller edits). bool/int only
# (FR scope; no float/list config field exists — YAGNI).
def _coerce_env_bool(raw: str) -> tuple[Any, bool]:
    """(value, recognized). Unrecognized -> (None, False) = tri-state no-override."""
    v = raw.strip().lower()
    if v in _ENV_TRUE:
        return True, True
    if v in _ENV_FALSE:
        return False, True
    return None, False


def cfg_coerce(raw: Any, kind: str, source: str, label: str) -> tuple[Any, str | None]:
    """Coerce a raw config value to `kind`; see the Locked API for the full contract."""
    desc = "true/false" if kind == "bool" else "an integer"
    bad = f"{label} must be {desc}, got {raw!r} — ignored"
    if source == "env":
        if kind == "bool":
            value, recognized = _coerce_env_bool(cast(str, raw))
            return (value, None) if recognized else (None, None)  # unrecognized = silent skip
        try:
            return int(cast(str, raw)), None
        except (TypeError, ValueError):
            return None, bad
    # source == "toml": strict, already-typed
    if kind == "bool":
        return (raw, None) if isinstance(raw, bool) else (None, bad)
    return (raw, None) if isinstance(raw, int) and not isinstance(raw, bool) else (None, bad)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest tests.test_status_line -v -k cfg_coerce`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(status-line): cfg_coerce type-directed converter (FR-1)"
```

### Task 1.3: Reclassify `cfg_to_int` → `util_to_int`

**Files:**
- Modify: `tools/status-line.py` (move def from cfg_ block ~693 to util_ block; repoint 4 probe call sites at ~746, ~747, ~914, ~919)
- Test: `tests/test_status_line.py` (rename any direct test reference)

- [ ] **Step 1: Confirm current call sites**

Run: `grep -n "cfg_to_int" tools/status-line.py`
Expected: the def (~693) plus calls at ~746, ~747, ~914, ~919, and possibly a test reference.

- [ ] **Step 2: Delete `cfg_to_int` from the cfg_ block**

Remove from `tools/status-line.py` (cfg_ block):

```python
def cfg_to_int(s: str | None) -> int | None:
    """Parse a stripped string to int, or None on empty/non-numeric input."""
    try:
        return int(s) if s else None
    except ValueError:
        return None
```

- [ ] **Step 3: Add `util_to_int` to the util_ block**

Insert in the `util_` block of `tools/status-line.py` (next to the other small pure parsers, e.g. near `util_trunc_cols`):

```python
def util_to_int(s: str | None) -> int | None:
    """Parse a stripped string to int, or None on empty/non-numeric input. Pure
    probe-support parser (tput/ps output) — not config; see cfg_coerce for config."""
    try:
        return int(s) if s else None
    except ValueError:
        return None
```

- [ ] **Step 4: Repoint the 4 probe call sites**

In `tools/status-line.py`, replace `cfg_to_int(` with `util_to_int(` at the four probe sites:

```python
                    cols = cols or util_to_int(_run("tput", "cols").strip())
                    lines = lines or util_to_int(_run("tput", "lines").strip())
```
```python
    return util_to_int(probe_ps_field(pid, "ppid"))
```
```python
    return util_to_int(probe_ps_field(pid, "rss"))
```

- [ ] **Step 5: Update any direct test reference**

Run: `grep -rn "cfg_to_int" tools/ tests/`
Expected: NO matches. If `tests/` references it, rename to `util_to_int`.

- [ ] **Step 6: Verify gate + golden**

Run: `make validate && make test`
Expected: green; `git diff main -- tests/fixtures/golden/expected.txt` empty.

- [ ] **Step 7: Commit**

```bash
git add tools/status-line.py tests/
git commit -m "refactor(status-line): reclassify cfg_to_int -> util_to_int (pure probe parser)"
```

### Task 1.4: Route the env helpers through `cfg_coerce`; delete `cfg_env_bool`/`cfg_env_int`

**Files:**
- Modify: `tools/status-line.py` (`cfg_env_apply_overrides` body ~445-466; delete `cfg_env_bool` ~362-373 and `cfg_env_int` ~402-410)
- Test: `tests/test_status_line.py` (migrate the `cfg_env_bool` tests ~1362-1373)

- [ ] **Step 1: Migrate the `cfg_env_bool` unit tests to `cfg_coerce`**

In `tests/test_status_line.py`, replace the block (~1362-1373) that calls `sl.cfg_env_bool(...)` with:

```python
def test_env_bool_via_coerce(self):
    for v in ("1", "true", "t", "y", "yes", "on", "TRUE", "On"):
        self.assertEqual(sl.cfg_coerce(v, "bool", "env", "X"), (True, None), v)
    for v in ("0", "false", "f", "n", "no", "off", "OFF"):
        self.assertEqual(sl.cfg_coerce(v, "bool", "env", "X"), (False, None), v)
    self.assertEqual(sl.cfg_coerce("maybe", "bool", "env", "X"), (None, None))
    self.assertEqual(sl.cfg_coerce("", "bool", "env", "X"), (None, None))
```

- [ ] **Step 2: Run to verify the migrated test passes and the old name is gone**

Run: `python3 -m unittest tests.test_status_line -v -k test_env_bool_via_coerce`
Expected: PASS.
Run: `grep -rn "cfg_env_bool" tests/`
Expected: NO matches.

- [ ] **Step 3: Rewire `cfg_env_apply_overrides` to use `cfg_coerce` + `cfg_warn`**

In `tools/status-line.py`, replace the SEGMENT/GIT/EXTERNAL branch bodies (~445-466) so they call `cfg_coerce` and warn via `cfg_warn`. The behavior (including the exact warning text) must be IDENTICAL — `cfg_coerce`'s `(None, None)` for an unrecognized bool reproduces today's silent skip, and its problem string equals today's `cfg_env_int` message:

```python
        if token == "SEGMENT":
            if not seg:
                continue
            seg_key = cfg_forward_legacy_segment(suffix.lower())
            if seg_key in seg:
                ov, _prob = cfg_coerce(val, "bool", "env", key)  # unrecognized -> ov None (silent)
                if ov is not None:
                    seg[seg_key] = ov
        elif token == "GIT":
            if suffix == "CACHE_TTL":
                v, prob = cfg_coerce(val, "int", "env", key)
                if prob:
                    cfg_warn(prob)
                elif v is not None:
                    g["cache_ttl"] = v
        elif token == "EXTERNAL":
            if suffix == "DIR":
                if val:
                    d = os.path.expanduser(val)
            elif suffix == "CACHE_TTL":
                v, prob = cfg_coerce(val, "int", "env", key)
                if prob:
                    cfg_warn(prob)
                elif v is not None:
                    t = v
```

- [ ] **Step 4: Delete `cfg_env_bool` and `cfg_env_int`**

Remove both functions from `tools/status-line.py`:

```python
def cfg_env_bool(env: Env, name: str) -> bool | None:
    ...
def cfg_env_int(key: str, val: str, fallback: int) -> int:
    ...
```

Then confirm no remaining references:

Run: `grep -rn "cfg_env_bool\|cfg_env_int" tools/ tests/`
Expected: NO matches.

- [ ] **Step 5: Verify gate + golden + FR-R.2**

Run: `make validate && make test`
Expected: green; `git diff main -- tests/fixtures/golden/expected.txt` empty.

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(status-line): route env parsing through cfg_coerce; drop cfg_env_bool/int (FR-1)"
```

---

## Phase 2: Access + Bind layer

### Task 2.1: `cfg_source_get` — access layer

**Files:**
- Modify: `tools/status-line.py` (cfg_ block, after `cfg_coerce`)
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_cfg_source_get_env_projection(self):
    env = {"CC_AI_KIT_GIT_CACHE_TTL": "9", "CC_AI_KIT_SEGMENT_ALT_COST": "1"}
    self.assertEqual(sl.cfg_source_get("env", {}, env, ("git", "cache_ttl")), "9")
    self.assertEqual(sl.cfg_source_get("env", {}, env, ("segments", "alt_cost")), "1")
    self.assertIsNone(sl.cfg_source_get("env", {}, env, ("git", "missing")))

def test_cfg_source_get_toml_nested(self):
    raw = {"git": {"cache_ttl": 7}, "segments": {"alt_cost": True}}
    self.assertEqual(sl.cfg_source_get("toml", raw, {}, ("git", "cache_ttl")), 7)
    self.assertIs(sl.cfg_source_get("toml", raw, {}, ("segments", "alt_cost")), True)
    self.assertIsNone(sl.cfg_source_get("toml", raw, {}, ("git", "missing")))
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_status_line -v -k cfg_source_get`
Expected: FAIL — `AttributeError: ... 'cfg_source_get'`.

- [ ] **Step 3: Implement `cfg_source_get`**

```python
def cfg_source_get(source: str, raw_toml: dict[str, Any], env: Env,
                   path: tuple[str, ...]) -> Any | None:
    """Raw value for `path` from `source`, or None if absent. Env name is the
    mechanical projection CC_AI_KIT_<PATH> (the ('segments', KEY) path projects to
    CC_AI_KIT_SEGMENT_<KEY>); TOML is a nested-dict lookup."""
    if source == "env":
        head = "SEGMENT" if path[0] == "segments" else path[0].upper()
        name = "CC_AI_KIT_" + "_".join([head, *(p.upper() for p in path[1:])])
        return env.get(name)
    node: Any = raw_toml
    for part in path:
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest tests.test_status_line -v -k cfg_source_get`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(status-line): cfg_source_get access layer with env-name projection (FR-2)"
```

### Task 2.2: `cfg_bind` — bind layer; rewire `cfg_load_config`; kill the two-pass

**Files:**
- Modify: `tools/status-line.py` (add `cfg_bind`; rewrite `cfg_load_config` ~591-672; delete `cfg_env_apply_overrides` ~413-468)
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test (bind precedence + problems)**

```python
def test_cfg_bind_precedence_and_problems(self):
    # default git cache_ttl 5; TOML sets 8; env overrides to 12 (env wins).
    raw = {"git": {"cache_ttl": 8}, "segments": {"alt_cost": True}}
    env = {"CC_AI_KIT_GIT_CACHE_TTL": "12"}
    git, ext_dir, ext_ttl, segs, probs = sl.cfg_bind(
        raw, env, dict(sl._GIT_DEFAULTS), "/d", 10,
        {"alt_cost": False, "path": True})
    self.assertEqual(git["cache_ttl"], 12)        # env > TOML > default
    self.assertIs(segs["alt_cost"], True)         # TOML applied
    self.assertEqual(probs, [])
    # invalid env int -> falls back to TOML/default AND records a problem
    _, _, _, _, probs2 = sl.cfg_bind(
        raw, {"CC_AI_KIT_GIT_CACHE_TTL": "x"}, dict(sl._GIT_DEFAULTS), "/d", 10, {})
    self.assertIn("CC_AI_KIT_GIT_CACHE_TTL must be an integer, got 'x' — ignored", probs2)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_status_line -v -k test_cfg_bind_precedence_and_problems`
Expected: FAIL — `AttributeError: ... 'cfg_bind'`.

- [ ] **Step 3: Implement `cfg_bind`**

Insert in the cfg_ block (after `cfg_source_get`). It binds the scalar groups (git, external) and the segment map with `default < TOML < env`, collecting problems instead of printing:

```python
def cfg_bind(  # pylint: disable=too-many-locals,too-many-branches
    raw_toml: dict[str, Any], env: Env, git: dict[str, Any], ext_dir: str,
    ext_ttl: int, segments: dict[str, bool],
) -> tuple[dict[str, Any], str, int, dict[str, bool], list[str]]:
    """Bind line_conf scalar groups + the segment map: default < TOML < env, per
    field. Present-but-invalid falls back AND records a problem; absent falls
    through. Returns (git, ext_dir, ext_ttl, segments, problems). Does NOT print —
    the caller (render = discard / doctor = report) decides."""
    g, d, t, seg = dict(git), ext_dir, ext_ttl, dict(segments)
    problems: list[str] = []

    def bind_scalar(path: tuple[str, ...], kind: str, cur: Any) -> Any:
        out = cur
        for source, label in (("toml", _toml_label(path)), ("env", _env_label(path))):
            raw = cfg_source_get(source, raw_toml, env, path)
            if raw is None:
                continue
            value, prob = cfg_coerce(raw, kind, source, label)
            if prob:
                problems.append(prob)
            elif value is not None:
                out = value
        return out

    g["cache_ttl"] = bind_scalar(("git", "cache_ttl"), "int", g["cache_ttl"])
    t = bind_scalar(("external", "cache_ttl"), "int", t)
    raw_dir = cfg_source_get("env", raw_toml, env, ("external", "dir"))
    if raw_dir:
        d = os.path.expanduser(cast(str, raw_dir))

    # segments: the ONE map-rule. default < TOML < env, each key forwarded for legacy.
    for source in ("toml", "env"):
        block = raw_toml.get("segments") if source == "toml" else None
        keys = (cast(dict[str, Any], block or {}).keys() if source == "toml"
                else _env_segment_keys(env))
        for raw_key in keys:
            key = cfg_forward_legacy_segment(raw_key.lower() if source == "env" else raw_key)
            if key not in seg:
                continue
            raw = (cast(dict[str, Any], block)[raw_key] if source == "toml"
                   else cfg_source_get("env", raw_toml, env, ("segments", raw_key.lower())))
            value, prob = cfg_coerce(raw, "bool", source, f"segment {key!r}")
            if prob:
                problems.append(prob)
            elif value is not None:
                seg[key] = value
    return g, d, t, seg, problems
```

Add the three small helpers alongside it:

```python
def _toml_label(path: tuple[str, ...]) -> str:
    """Message subject for a TOML field, matching today's text, e.g. '[git] cache_ttl'."""
    return f"[{path[0]}] {'.'.join(path[1:])}"


def _env_label(path: tuple[str, ...]) -> str:
    """Message subject for an env field = the projected env var name."""
    head = "SEGMENT" if path[0] == "segments" else path[0].upper()
    return "CC_AI_KIT_" + "_".join([head, *(p.upper() for p in path[1:])])


def _env_segment_keys(env: Env) -> list[str]:
    """Lower-cased segment keys present as CC_AI_KIT_SEGMENT_* in env."""
    pre = "CC_AI_KIT_SEGMENT_"
    return [k[len(pre):].lower() for k in env if k.startswith(pre)]
```

> NOTE for the implementer: today the unknown-segment / non-bool warnings for the **TOML** `[segments]` block come from `cfg_resolve_segments`, which ALSO warns on unknown keys. `cfg_bind` above only forwards+binds known keys (it skips unknown silently). To keep Phase 2 behavior-identical, **leave `cfg_resolve_segments` as the TOML segment resolver** (it still runs and still warns) and have `cfg_bind` apply only the ENV segment overrides in Phase 2 — i.e. in Step 4 wire `cfg_load_config` to call `cfg_resolve_segments` (TOML, warns) THEN `cfg_bind` for env. The unknown-key/non-bool warnings move to the problem channel in **Phase 3**, not here. Adjust the `for source in (...)` loop to `("env",)` for Phase 2; expand to include the TOML pass in Phase 3 when `cfg_resolve_segments`'s warnings migrate. (This keeps each phase byte-identical.)

- [ ] **Step 4: Rewrite `cfg_load_config` to use `cfg_bind`; remove the two-pass**

Replace the env-application section of `cfg_load_config` (~632-649) so the single bind replaces both `cfg_env_apply_overrides` calls. The git TOML loop (warns) and `cfg_resolve_segments` (TOML, warns) stay for Phase 2; `cfg_bind` applies env + records problems, which Phase 2 prints via `cfg_warn` for parity:

```python
    # FR-2/FR-3: bind line_conf scalars + env segment overrides via the single
    # structure walk (replaces the old two-pass cfg_env_apply_overrides).
    seg_defaults = dict(base.segments)
    specs0 = core_discover_external(ext_dir, ext_ttl, os.path.join(cache_base, "segments"))
    for s in specs0:
        seg_defaults.setdefault(s.id, True)
    segments = cfg_resolve_segments(seg_defaults, raw.get("segments"))   # TOML pass (warns)
    git, ext_dir, ext_ttl, segments, problems = cfg_bind(
        raw, env, git, ext_dir, ext_ttl, segments)                       # env pass + problems
    for p in problems:                                                   # Phase-2 parity: print
        cfg_warn(p)
    specs = core_discover_external(ext_dir, ext_ttl, os.path.join(cache_base, "segments"))
```

> The provider discovery now runs with the FINAL `ext_dir`/`ext_ttl` (env-bound) before segments are finalized — `specs0` seeds the segment defaults, `specs` is the post-env discovery used for placement. Confirm `cfg_place_external(layout, specs)` still receives `specs`.

- [ ] **Step 5: Delete `cfg_env_apply_overrides`**

Remove the whole function (~413-468) and confirm:

Run: `grep -rn "cfg_env_apply_overrides" tools/ tests/`
Expected: matches ONLY in `tools/statusline-doctor.py:167` (handled in Task 2.3) — none in `status-line.py`. If the doctor still references it, Task 2.3 fixes it; until then the doctor import may break, so do Task 2.3 in the SAME commit.

- [ ] **Step 6: (defer commit until Task 2.3 — the doctor must be repointed in the same unit)**

### Task 2.3: Repoint the doctor off `cfg_env_apply_overrides`

**Files:**
- Modify: `tools/statusline-doctor.py` (`validate_config_file` ~166-167)
- Test: `tests/test_statusline_doctor.py`

- [ ] **Step 1: Replace the doctor's external-resolution lines**

In `tools/statusline-doctor.py` `validate_config_file`, replace (~166-167):

```python
    ext_dir, ext_ttl = sl.cfg_resolve_external(raw, env)
    _, ext_dir, ext_ttl, _ = sl.cfg_env_apply_overrides(env, {}, ext_dir, ext_ttl, {})
```

with the new bind (env overrides for external only; segments/git problems handled by the file checks already present):

```python
    ext_dir, ext_ttl = sl.cfg_resolve_external(raw, env)
    _, ext_dir, ext_ttl, _, _ = sl.cfg_bind(raw, env, dict(sl._GIT_DEFAULTS), ext_dir, ext_ttl, {})
```

- [ ] **Step 2: Verify gate + golden + FR-R.2 + doctor tests**

Run: `make validate && make test`
Expected: green; `git diff main -- tests/fixtures/golden/expected.txt` empty.

- [ ] **Step 3: Commit Tasks 2.2 + 2.3 together (atomic)**

```bash
git add tools/status-line.py tools/statusline-doctor.py tests/
git commit -m "refactor(status-line): cfg_bind structure-walk; drop two-pass env reader (FR-2/FR-3)"
```

---

## Phase 3: Silent render / doctor-owned validation (ATOMIC behavior change)

### Task 3.1: `cfg_load_config_verbose` + silent render

**Files:**
- Modify: `tools/status-line.py` (split `cfg_load_config`; migrate `cfg_resolve_segments`/git/palette/ramp/clamp warnings to the problem channel)
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Write the failing test (0-byte stderr on broken config — the silent-render proof)**

```python
def test_render_silent_on_broken_config(self):
    """FR-4 proof: the render path writes ZERO bytes to stderr on broken config."""
    import io
    from contextlib import redirect_stderr
    env = {
        "CC_AI_KIT_GIT_CACHE_TTL": "not-an-int",   # invalid env int
        "CC_AI_KIT_SEGMENT_NOPE": "1",             # unknown segment
    }
    buf = io.StringIO()
    with redirect_stderr(buf):
        cfg = sl.cfg_load_config(env)
    self.assertEqual(buf.getvalue(), "")           # silent
    self.assertEqual(cfg.git["cache_ttl"], sl._GIT_CACHE_TTL)  # fell back to default

def test_verbose_reports_problems(self):
    env = {"CC_AI_KIT_GIT_CACHE_TTL": "not-an-int"}
    _, problems = sl.cfg_load_config_verbose(env)
    self.assertIn("CC_AI_KIT_GIT_CACHE_TTL must be an integer, got 'not-an-int' — ignored",
                  problems)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_status_line -v -k "test_render_silent_on_broken_config or test_verbose_reports_problems"`
Expected: FAIL (`cfg_load_config_verbose` missing; and today render prints the bad-int warning so stderr is non-empty).

- [ ] **Step 3: Convert `cfg_load_config` into verbose + lenient pair**

Rename the body of `cfg_load_config` to `cfg_load_config_verbose(env) -> tuple[Config, list[str]]`. Inside it, the warning sites that currently call `cfg_warn`/`print(...)` must instead **append to `problems`** (no printing). Specifically migrate the inline warnings in: the git TOML loop (unknown/bad_ttl), `cfg_resolve_segments` (unknown segment / non-bool — fold its TOML pass into `cfg_bind`'s segment loop now, per the Task 2.2 note, so it returns problems), the palette unknown-key loop, the ramp loops, and `cfg_place_external` (clamp). Each becomes `problems.append("<same core text>")`. Return `(Config(...), problems)`.

Then add the lenient entrypoint:

```python
def cfg_load_config(env: Env) -> "Config":
    """Lenient render entrypoint: resolve config, DISCARD problems, emit nothing."""
    cfg, _problems = cfg_load_config_verbose(env)
    return cfg
```

> Migrate `cfg_resolve_segments`'s warnings: change `cfg_bind`'s segment loop to `for source in ("toml", "env")` (TOML pass now included) and append unknown-key / non-bool problems there; reduce `cfg_resolve_segments` to a pure default<TOML merge that records problems, OR inline it into `cfg_bind`. Keep the EXACT message text: `f"unknown segment '{k}' in config"`, `f"segment '{k}' must be true/false, got {v!r} — ignored"`. Confirm against the captured-stderr fixture (Task 3.2).

- [ ] **Step 4: Run to verify pass + golden + FR-R.2**

Run: `python3 -m unittest tests.test_status_line -v -k "test_render_silent_on_broken_config or test_verbose_reports_problems"`
Expected: PASS.
Run: `make validate && make test` and `git diff main -- tests/fixtures/golden/expected.txt`
Expected: green; golden diff empty.

- [ ] **Step 5: (defer commit until Task 3.2 — doctor must emit the relocated warnings in the same unit)**

### Task 3.2: Doctor emits the bind problems (parity fixture); relocate render-path assertions

**Files:**
- Modify: `tools/statusline-doctor.py` (`cmd_check`/`cmd_doctor` consume `cfg_load_config_verbose`)
- Modify: `tests/test_status_line.py`, `tests/test_external_segments.py` (delete render-path stderr-warning assertions)
- Test: `tests/test_statusline_doctor.py` (captured-stderr parity fixture)

- [ ] **Step 1: Find the render-path stderr-warning assertions to relocate**

Run: `grep -rn "status-line:\|assertIn.*stderr\|redirect_stderr\|deprecated\|unknown segment\|must be true/false\|must be an integer" tests/test_status_line.py tests/test_external_segments.py`
Expected: a list of tests asserting render-side warnings. These move to the doctor.

- [ ] **Step 2: Write the doctor parity test (the oracle)**

Add to `tests/test_statusline_doctor.py`:

```python
def test_doctor_reports_bind_problems_byte_identical(self):
    """Parity: the doctor emits each relocated warning in the exact render dim format."""
    import io
    from contextlib import redirect_stderr
    env = {"CC_AI_KIT_GIT_CACHE_TTL": "not-an-int"}
    buf = io.StringIO()
    with redirect_stderr(buf):
        rc = doctor.cmd_check("", env)   # cmd_check now reports bind problems
    self.assertEqual(rc, 1)
    self.assertIn(
        f"{doctor.sl._DIM}status-line: CC_AI_KIT_GIT_CACHE_TTL must be an integer, "
        f"got 'not-an-int' — ignored{doctor.sl.RESET}",
        buf.getvalue(),
    )
```

(Use the test module's existing import handle for the doctor — match the file's current pattern for loading `statusline-doctor.py`.)

- [ ] **Step 3: Rewire `cmd_check`/`cmd_doctor` to the verbose problem list**

In `tools/statusline-doctor.py`, replace the `validate_config_file`-based error gathering with the single bind problem list, emitted through the render-format wrapper for byte-identical parity:

```python
def cmd_check(path: str, env: Env) -> int:
    """Validate config (file + env) via the render core's bind problem list; print
    each in the render dim format. Return process exit code (0/1)."""
    _cfg, problems = sl.cfg_load_config_verbose(env)
    for p in problems:
        sl.cfg_warn(p)
    if problems:
        return 1
    print(f"{sl.cfg_config_path(env)}: OK")
    return 0
```

Update `cmd_doctor` similarly: gather `problems` from `cfg_load_config_verbose`, emit via `sl.cfg_warn`, keep the dry-render failure loop. Remove `validate_config_file` (and its now-unused helpers/`_NO_CHECK`-adjacent imports) if nothing else references it — confirm with `grep -n validate_config_file tools/ tests/`.

- [ ] **Step 4: Delete the relocated render-path assertions**

Remove from `tests/test_status_line.py` and `tests/test_external_segments.py` the assertions identified in Step 1 that checked render-side stderr warnings (render is now silent). Keep tests that assert the RESULTING Config (those stay).

- [ ] **Step 5: Update docs**

In `README.md` and `tools/statusline.toml.sample`: state that the render module emits no config warnings and that `python3 tools/statusline-doctor.py --check` / `--doctor` is the validation surface (it validates both the file and the env). Update any wording implying the status line warns inline.

- [ ] **Step 6: Verify gate + golden + FR-R.2**

Run: `make validate && make test` and `git diff main -- tests/fixtures/golden/expected.txt`
Expected: green; golden diff empty.

- [ ] **Step 7: Commit Tasks 3.1 + 3.2 together (atomic behavior change)**

```bash
git add tools/status-line.py tools/statusline-doctor.py tests/ README.md tools/statusline.toml.sample
git commit -m "refactor(status-line): silent render; doctor owns validation, byte-identical (FR-4)"
```

---

## Phase 4: FR-8 rule reduction + extraction-seam comments

### Task 4.1: Add the single-reader proof test, then reduce the arch rule

**Files:**
- Modify: `tests/test_arch.py` (`check_config_env_in_cfg` / its docstring / allowlist)
- Modify: `tools/status-line.py` (a throwaway-field proof is a test, not core — see below)
- Test: `tests/test_status_line.py` (zero-edit-new-field proof)

- [ ] **Step 1: Write the zero-edit-new-field proof test (single-reader auto-extends)**

Add to `tests/test_status_line.py`. This proves a NEW typed scalar binds from env+TOML through `cfg_source_get`/`cfg_coerce`/`cfg_bind` with no reader edits — by binding an ad-hoc path directly through the generic layer:

```python
def test_single_reader_auto_extends(self):
    """FR-6 proof: a new typed field binds via the generic layer with no reader edits."""
    raw = {"newgroup": {"flag": True}}
    env = {"CC_AI_KIT_NEWGROUP_FLAG": "off"}
    # access projects the name; coerce types it; precedence env > TOML — all generic:
    self.assertEqual(sl.cfg_source_get("toml", raw, env, ("newgroup", "flag")), True)
    self.assertEqual(sl.cfg_source_get("env", raw, env, ("newgroup", "flag")), "off")
    self.assertEqual(sl.cfg_coerce("off", "bool", "env", "X"), (False, None))
```

- [ ] **Step 2: Run to verify it passes (the layer already supports it)**

Run: `python3 -m unittest tests.test_status_line -v -k test_single_reader_auto_extends`
Expected: PASS.

- [ ] **Step 3: Reduce the FR-8 single-reader rule**

In `tests/test_arch.py`, the `check_config_env_in_cfg` rule (rule 1) asserts every `CC_AI_KIT_*` literal read lives in a `cfg_` function. After the refactor the only literal `CC_AI_KIT_*` reads are the bootstrap names in `cfg_config_path` (the env-name projection builds names dynamically, not as literals). Reduce the rule to its minimal still-meaningful guard: assert the ONLY literal `CC_AI_KIT_*` env reads are the two bootstrap names (`CC_AI_KIT_CONFIG_FILE`, `CC_AI_KIT_CONFIG`) and that they live in `cfg_config_path`. Update the docstring to state single-reader is now structural (the generic walk), so the rule only guards the bootstrap exception. Keep the existing non-vacuity counterpart test meaningful (a literal read outside `cfg_` still fails).

Confirm the exact reduced assertion against the live tree:

Run: `python3 -m unittest tests.test_arch -v`
Expected: all arch tests PASS.

- [ ] **Step 4: Verify gate + golden**

Run: `make validate && make test` and `git diff main -- tests/fixtures/golden/expected.txt`
Expected: green; golden diff empty.

- [ ] **Step 5: Commit**

```bash
git add tests/test_arch.py tests/test_status_line.py
git commit -m "test(status-line): single-reader proof; reduce FR-8 env-reader rule to bootstrap guard (FR-6)"
```

### Task 4.2: Extraction-seam block comments

**Files:**
- Modify: `tools/status-line.py` (banner headers of the `probe_`, `fmt_`, `util_` blocks)

- [ ] **Step 1: Add the rule comments (zero runtime code)**

Under each of the `probe_`, `fmt_`, and `util_` banner headers in `tools/status-line.py`, add a short comment recording the rule (NOT a per-function census). Example for `util_`:

```python
# ═══ 6. util_ — pure non-format helpers (color / width / truncate / fit / parse)
# Shared by default; classify by NATURE, not caller. A helper keeps its prefix even
# if only one tier calls it today (reuse rots a caller-based name). Extraction seam:
# the git/todo/proc-only helpers travel with those probes if ever externalized; the
# cross-tier ones (util_first_fitting, util_icon, util_pick_color) are the irreducible
# shared core. The exact caller census is regenerable on demand via AST — not kept here.
```

For the `probe_` banner, add a one-line note distinguishing the raw gatherers from the memoized `*(ctx)` accessors:

```python
# ═══ 4. probe_ — side-effecting data gatherers (git / proc / fs / subprocess) ═
# Two sub-tiers: raw gatherers on primitives (probe_git_snapshot(work_dir), ...) and
# the memoized segment-facing accessors signed (ctx) (probe_git_for, probe_rss, ...).
# Classified by NATURE (side-effecting), not by which segment consumes them.
```

For the `fmt_` banner, a one-line note that formatters are value→display-string, consumer-independent.

- [ ] **Step 2: Verify gate + golden (comments only — must be a no-op for behavior)**

Run: `make validate && make test` and `git diff main -- tests/fixtures/golden/expected.txt`
Expected: green; golden diff empty.

- [ ] **Step 3: Commit**

```bash
git add tools/status-line.py
git commit -m "docs(status-line): extraction-seam rule comments on probe_/util_/fmt_ banners (FR-7)"
```

---

## Phase 5: Compaction + final review + merge

### Task 5.1: Compact WIP commits into per-logical-unit commits

**Files:** none (git only). `rebase -i` is BLOCKED — use path-disjoint `git cherry-pick -n` replay.

- [ ] **Step 1: Tag a safety anchor + record the tree**

```bash
git tag -f precompact-config-binding HEAD
git rev-parse HEAD
git log --oneline --no-decorate main..HEAD
```

- [ ] **Step 2: Replay onto a temp branch, grouped by logical unit**

Group the WIP commits into per-FR units (Phase 1 = FR-1 converter; Phase 2 = FR-2/FR-3 bind; Phase 3 = FR-4 silent render; Phase 4 = FR-6 rule + FR-7 comments). On a temp branch off `main`, `git cherry-pick -n` each unit's commits in original order and commit once per unit with a self-contained message:

```bash
git checkout -b compact-cb main
git cherry-pick -n <phase-1 commit shas in order>
git commit -m "refactor(status-line): cfg_coerce converter + cfg_warn; reclassify util_to_int (FR-1)"
git cherry-pick -n <phase-2 commit shas in order>
git commit -m "refactor(status-line): access/bind layer, single structure-walk, no two-pass (FR-2/FR-3)"
git cherry-pick -n <phase-3 commit shas in order>
git commit -m "refactor(status-line): silent render; doctor-owned validation, byte-identical (FR-4)"
git cherry-pick -n <phase-4 commit shas in order>
git commit -m "test(status-line): reduce FR-8 env-reader rule; extraction-seam comments (FR-6/FR-7)"
```

- [ ] **Step 3: Verify the compacted tree is identical to the pre-compaction tip**

```bash
git diff precompact-config-binding --stat
```
Expected: EMPTY (byte-identical tree).

- [ ] **Step 4: Gate on the compacted branch; point the refactor branch at it**

```bash
make validate && make test
git checkout refactor/status-line-config-binding
git reset --hard compact-cb
git branch -D compact-cb
```
Expected: gate green; `git diff main -- tests/fixtures/golden/expected.txt` empty.

### Task 5.2: Final whole-implementation review + merge to local main

**Files:** none (review + git)

- [ ] **Step 1: Final review against FR-1..FR-7 + Success Metrics**

Dispatch a final reviewer (or self-review) verifying: one converter shared by env/TOML/doctor; env-name mapping in one place; two-pass gone; render emits 0 stderr on broken config; doctor reports every problem class byte-identical; back-compat aliases/legacy keys still work; FR-8 rule reduced; seam comments present; `cfg_` count down; `status-line.py` line count strictly decreased; system total no net increase; golden byte-identical; stdlib-only; one-way import.

- [ ] **Step 2: Confirm golden byte-identical vs main + line metrics**

```bash
git diff main..HEAD -- tests/fixtures/golden/expected.txt   # must be empty
git diff main..HEAD --stat -- tools/status-line.py tools/statusline-doctor.py
```
Expected: golden diff empty; `status-line.py` net negative.

- [ ] **Step 3: Merge --no-ff into LOCAL main (do NOT push)**

```bash
git checkout main
git merge --no-ff refactor/status-line-config-binding -m "merge: status-line config binding layer (FR-1..FR-7)"
make validate && make test
git log --oneline origin/main..main | wc -l   # confirm local-only (NOT pushed)
```
Expected: gate green; main ahead of origin (not pushed).

- [ ] **Step 4: Update memory**

Update `MEMORY.md` + `status-line-config-binding` memory note: DONE, merged `--no-ff` to LOCAL main (record the merge sha), not pushed; 4 logical-unit commits; converter/access/bind landed; silent render; doctor sole validator; FR-8 rule reduced; util_to_int reclassified.

---

## Self-Review (completed by the plan author)

**1. Spec coverage** — FR-1 (Tasks 1.2, 1.4), FR-2 (Task 2.1, 2.2), FR-3 (Task 2.2, 2.3), FR-4/FR-4a (Tasks 3.1, 3.2), FR-5 back-compat (preserved in `cfg_bind` segment forwarding + `cfg_env_normalize`, asserted via existing tests + parity fixture), FR-6 (Task 4.1), FR-7 (Task 4.2). Success metrics: cfg_ count ↓ (1.4, 2.2), util_to_int reclassified (1.3), single-reader proof (4.1 Step 1), 0-byte-stderr proof (3.1 Step 1), line metrics (5.2 Step 2). All mapped.

**2. Placeholder scan** — every code step carries real code or an exact before→after; commands have expected output. The two design NOTEs (Task 2.2 segment-warning deferral; Task 3.1 segment-warning migration) are explicit sequencing instructions, not placeholders.

**3. Type/signature consistency** — `cfg_coerce(raw, kind, source, label) -> (value, problem)`, `cfg_source_get(source, raw_toml, env, path)`, `cfg_bind(...) -> (git, ext_dir, ext_ttl, segments, problems)`, `cfg_load_config_verbose(env) -> (Config, list[str])`, `cfg_load_config(env) -> Config`, `util_to_int(s) -> int|None`, `cfg_warn(msg) -> None` — used consistently across Tasks 1–5.
