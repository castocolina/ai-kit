# Headless (No-TTY) Install Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tools/setup.py install`/`reconfigure` gain a new `--headless` flag that lets CI/container/agent-driven environments link skills and wire the status-line/hooks without a TTY. (The status-line/hook wiring and the CI framing are a deliberate, explicitly declared departure from the cited spec's skills-only headless scope, at the user's direct request — see **Spec** delta 3 below before reading further.) Without `--headless`, `main()`'s command *routing* is byte-identical to today — `require_tty()` still fails closed exactly as now, and every existing dispatch line is untouched. The one deliberate exception is the internals of two status-line functions: Task 1 hardens `wire_statusline` against malformed `settings.json`/write failures AND applies a three-line defensive fix to `detect_statusline`. Both are shared by the interactive and headless paths, so this is an intentional bug fix that also changes five narrow interactive-path outcomes (a corrupt `settings.json` is now refused instead of silently clobbered; a write failure now returns `False` cleanly instead of raising or corrupting the file; a foreign *string*-form `statusLine` is now guarded instead of overwritten without consent; `wire_statusline` now refuses every unsupported `statusLine` shape — a list/number/bool, or a dict whose `"command"` is not a string — where today it raises `TypeError` for the dict-with-non-string-`"command"` case and silently overwrites the others; and `detect_statusline`, which TODAY raises an uncaught `TypeError: argument of type 'int' is not iterable` at `tools/setup.py:1635` for `{"statusLine": {"command": 1}}` — crashing the interactive wizard at its two call sites `tools/setup.py:2248` and `:2288` — now classifies that shape as `"unset"`, exactly as it already does for list/number/bool values) — see the `detect_statusline` bullet in Global Constraints for the verified per-shape behavior and the precise scope of both changes. With `--headless` and no other flags, the command is a pure no-op (nothing linked or wired, and nothing fetched — see the sync note below). `--skills all|name1,name2,...` links the requested skills additively (never unlinks anything already present). `--with-statusline` and `--with-hooks` independently opt into wiring those. `--examples=all|none|<ids>` (the existing top-level flag) composes with `--headless` unchanged, using the same non-interactive primitives `cmd_install` already uses for its own `--examples` override.

**Architecture:** A new flag block in `main()` intercepts `--headless` BEFORE `ensure_rich_runtime`/`open_tty`/`require_tty` are ever called — the headless path needs neither Textual nor `uv` re-exec, so it skips that whole dependency chain entirely (a real robustness win for minimal containers). It dispatches to a new `cmd_install_headless(env, dry, skills_flag, with_statusline, with_hooks, examples_flag=None)` — a thin orchestrator whose per-category work lives in four small private helpers (`_headless_paths_and_entries`, `_headless_link_skills`, `_headless_wire_hooks`, `_headless_install_examples`, plus a pure `_headless_summary` message builder) so every function stays inside this repo's configured Pylint design limits; see the Pylint bullet in Global Constraints for the exact numbers. It calls `resolve_paths`/`enumerate_entries` (both unchanged) inside an explicit error boundary — an `OSError` from `enumerate_entries` (its `os.path.isdir`/`os.listdir` at `tools/setup.py:605-606`, the only filesystem I/O of the two) becomes a reported, clean exit `1` instead of an uncaught traceback; `resolve_paths` (`tools/setup.py:49-77`) is pure string/`env` manipulation with no filesystem access and cannot raise `OSError`, so it sits inside the same `try` purely defensively — and a new small helper, `apply_additive_skills(names, entries, claude_dir, dry, counts)`, which loops `link_one()` over the resolved name set — deliberately NOT `apply_selection()`, because that function's deselect branch would unlink anything not explicitly requested, which contradicts "nothing touched unless asked." `link_one` can itself raise `OSError` (e.g. a permission failure creating the parent directory or the symlink), and for a link path occupied by a real file or a foreign symlink it instead bumps `counts["skip_real"]`/`counts["skip_foreign"]` and returns normally; `_headless_link_skills` wraps the `apply_additive_skills` call to catch the former and compares those two counters around it to catch the latter, so a requested skill that is not linked afterwards is always reported and mapped to exit `1` — never a traceback and never a silent success. Status-line wiring calls the hardened `wire_statusline(..., tty=None, dry, assume_overwrite=False)` (Task 1 below rewrites its internals to use `_read_json_checked`/`_atomic_write_json`, the same malformed-aware/atomic primitives `wire_hook_claude`/`wire_hook_cursor` already use, AND to recognize a bare-string `statusLine` value as a foreign command — mirroring `detect_statusline`'s existing two-shape handling — not just the dict form, AND to refuse outright any value that is neither of those two supported shapes instead of raising `TypeError` or overwriting it; its public signature and documented confirm/refuse behavior for the supported shapes are otherwise unchanged). Task 1 also routes `detect_statusline`'s own shape classification through the same new `_statusline_command` helper — a three-line change that turns today's uncaught `TypeError` on `{"statusLine": {"command": 1}}` into the `"unset"` result it already returns for every other unsupported shape, without adding any new `"state"` value the wizard UI would have to render. Hook wiring calls `wire_hook_claude`/`wire_hook_cursor` directly, completely unmodified — both already have documented, tested headless behavior (the hook wirers never touch `tty` at all, and already write through `_atomic_write_json` with malformed-config refusal). `--examples` composes by reusing `discover_example_segments`/`select_examples`/`install_example_segments` exactly as `cmd_install` already does for its own `--examples` override — `select_examples` never touches `tty` on the flag-given branch, so no headless-specific example-selection logic is needed.

**Tech Stack:** Python 3.12, stdlib only (`argparse`, `os`, `re` — all three already imported in `tools/setup.py`), `unittest` (`uv run python3 -m unittest tests.test_setup -v`).

**Spec:** `docs/superpowers/specs/2026-06-19-e5-installer-wizard-design.md` — its "`/dev/tty` unavailable (genuinely headless — agent automation)" row (spec line 303) and "The headless branch exists only so an agent can install skills unattended" (line 306) are the requirement this plan realizes. **Three deliberate deltas** from that spec text, all three stated in Out of scope / Global Constraints below:

1. **Entry point.** The headless path is entered by an **explicit `--headless` flag** rather than by TTY absence (the implicit branch was never built; `require_tty` fails closed instead, and this plan does not change that).
2. **Additive-only.** It does NOT "auto-remove dead symlinks with a printed warning" (`prune_stale`) or link first-time defaults, because nothing may be touched unless explicitly asked for.
3. **This plan intentionally supersedes the spec's skills-only headless scope.** The spec is explicit and repeated that headless means skills and *only* skills: "Only **skills** are ever installed headless … that path never needs the status line" (spec line 21); "**Headless re-run** (no TTY): the status line is not touched at all (skills-only path)" (line 183); the §7 condition table's headless row says "**skip the status-line wizard entirely** (headless contexts never render a status line)" (line 303); and "CI/cron is explicitly a **non-goal** — every status-line user is a developer, not a machine" (line 305). This plan's `--with-statusline`, `--with-hooks`, and its CI/container framing **contradict all four of those statements, deliberately and with the user's explicit direction** — the user asked for headless status-line and hook wiring, opt-in via flags, which is the reason this plan exists at all. The spec's narrower scope is therefore superseded **for this feature**, and the spec should be read as historical on those four lines. **Rationale, and why the spec's spirit survives:** the wiring is *opt-in only*. Default and bare `--headless` wire nothing, touch no `settings.json`, and render no status line — byte-for-byte the spec's "the status line is not touched at all" outcome. A machine only gets a status line or a hook when an operator explicitly types `--with-statusline`/`--with-hooks`, which is a human decision expressed in a flag, not an automated default. That keeps the spec's actual invariant — "don't touch anything unasked" — fully intact while removing its blanket prohibition. No other part of the spec is affected: the interactive wizard, its fail-closed TTY gate, and the status-line design itself are all untouched by this plan.

**Out of scope (explicit):** `prune_stale`/`predecessor_candidates`/`apply_predecessor_links` are NOT called from the headless path in this plan. `prune_stale` already has a fully-built, tested headless behavior (auto-removes dead links + prints a warning, per its own docstring's "§4" reference) — but that contradicts this plan's "nothing touched unless asked" requirement, so it stays unreached from `--headless` here. Task 3 leaves a two-line comment IN `cmd_install_headless`'s BODY, at the exact point a prune call would sit (between the path/entry resolution and the skill linking) — not only in the function's docstring — noting this was a deliberate omission, so a future `--prune-stale` flag has an obvious place to plug in. A Makefile convenience target (e.g. `make install-headless`) is also explicitly out of scope for this plan — see Global Constraints' file-scope bullet.

## Global Constraints

- `--headless` is the ONLY new gate on the existing fail-closed path. `main()`'s existing `require_tty(open_tty())` call for `install`/`reconfigure` must remain completely unchanged for the case where `--headless` is absent — this plan adds a new branch taken BEFORE that call, never modifies it.
- `cmd_install_headless` must never call `ensure_rich_runtime`, `open_tty`, `require_tty`, or import/touch Textual in any way — that is the whole point of the no-TTY path.
- **The "byte-identical without `--headless`" promise in the Goal is scoped to command routing, not to `wire_statusline`'s internals.** Task 1 changes `wire_statusline`'s handling of a malformed/non-object `settings.json`, of an unsupported `statusLine` shape (see the statusLine-shape bullet below), and of a write failure: previously `_read_json` silently collapsed unparseable JSON to `{}` (so a corrupt `settings.json` got overwritten instead of refused) and the non-atomic `_write_json` could raise past the caller or leave a partially-written file on failure. Afterward, both are refused/handled cleanly and return `False`. This is an intentional, in-scope hardening fix — call it out as such in Task 1's commit message rather than claiming zero behavior change for the interactive `install`/`reconfigure` flow, since `wire_statusline` is called from both `cmd_install` and (new, this plan) `cmd_install_headless`. What DOES remain byte-identical without `--headless` is `main()`'s dispatch: the `require_tty(open_tty())` gate, `ensure_rich_runtime`, and every other line of `cmd_install`/the wizard are untouched.
- **Sync note (no sync actually happens inside `setup.py`):** `tools/setup.py` never fetches the repo itself, headless or not — there is no "checkout refresh" inside this file to reuse. Refreshing the repo is entirely `tools/install.sh`'s job, and only in one of its two modes: piped/bootstrap mode (`curl ... | bash`) runs `git clone`/tarball fetch before handing off to `setup.py`; local-checkout mode (running `install.sh` or `make install` from an existing clone) explicitly SKIPS the fetch (`tools/install.sh`'s `detect mode` comment + `fetch_repo`/`info "local checkout — skipping fetch"` logic). Invoking `python3 tools/setup.py install --headless ...` directly — the expected CI/container entry point for this flag — never syncs anything; it operates on whatever is already on disk at `AI_KIT_DIR`. Document this precisely in Task 3's README subsection; do not claim `--headless` "still runs the sync."
- Bare `--headless` (no `--skills`, no `--with-statusline`, no `--with-hooks`, no `--examples`) links nothing and wires nothing — a pure no-op over whatever is already on disk (see sync note above — it does not fetch anything either). Print a one-line summary saying so (e.g. `headless: nothing requested — pass --skills/--with-statusline/--with-hooks/--examples to link or wire something`).
- `--skills` accepts `all` or a comma/space-separated list of skill names. It **actually mirrors** `resolve_example_selection`'s parsing (`tools/setup.py:808-821`), tokenizer and case-folding included — do not merely gesture at it: `resolve_example_selection` does `norm = flag.strip().lower()` before comparing against `"all"`/`"none"` (its docstring at `:812` states "`all`/`none` are case-insensitive") and splits the id list with `re.split(r"[,\s]+", flag.strip())`. `resolve_skills_flag` (Task 2) therefore lowercases/strips before the `all` comparison and splits on `re.split(r"[,\s]+", ...)` too, so `--skills ALL` and `--skills "alpha beta"` behave exactly as an `--examples` user would expect instead of degrading into unknown-name warnings. The ONE deliberate divergence is that `--skills` has **no `none` value** — bare `--headless` already means "nothing", so a `none` spelling would be a second way to say the same thing. (`re` is already imported in `tools/setup.py` — `resolve_example_selection` uses `re.split` at `:820` — so no new import is needed.) Scope is the `skills` category only (this repo currently has no `agents`/`commands` directories — do not invent handling for categories that don't exist in the repo).
- `--skills <list>` is validated against `enumerate_entries(...)["skills"]`: an unrecognized name is a `warn:` to stderr and skipped — never a hard error that aborts the whole run. **Precedent, attributed precisely:** the "dropped, never a hard failure" sentence belongs to `enumerate_entries`'s docstring (`tools/setup.py:597-600`: "Malformed entries are dropped (install.sh warned + counted them; the wizard simply omits them)"), not to `validate_entry` (`tools/setup.py:579-594`), which only returns a bool and prints nothing at all. Note the difference from what this plan does: the existing behavior is **silent omission** — neither function emits a warning — so the `warn:`-and-continue reporting below is **this plan's own addition**, not an existing pattern being mirrored. What IS inherited from `enumerate_entries` is only the "keep going, never abort" disposition. A `--skills` value that is non-empty but matches NO valid name (e.g. `--skills ghost`) is reported distinctly from bare `--headless` ("`--skills` matched no valid names", not "nothing requested") — see Task 3.
- `apply_additive_skills` must NEVER call `unlink_one` or otherwise remove an existing link. It only calls `link_one` for the resolved name set. Verify this with a test that pre-creates an out-of-band symlink for a skill NOT in the `--skills` list and asserts it still exists afterward. `apply_additive_skills` propagates any `OSError` `link_one` raises rather than swallowing it — `_headless_link_skills` (Task 3) is the one that catches it, so a real filesystem failure is reported and mapped to exit `1`, never silently dropped or left to crash the process with a raw traceback. `link_one`'s non-raising conflicts (`skip_foreign`/`skip_real`) are detected by the same helper through the counters — see the exit-code contract below.
- **`wire_statusline` is hardened in Task 1, not left unmodified.** It currently reads via `_read_json` (which silently collapses a malformed/unreadable `settings.json` to `{}`) and writes via the non-atomic `_write_json` — unlike `wire_hook_claude`/`wire_hook_cursor`, which already use `_read_json_checked` (three-state: absent/ok/unreadable) and `_atomic_write_json`. A headless caller requesting `--with-statusline` against a corrupted `settings.json` must refuse and leave the file byte-identical, exactly like the hook wirers already do — not silently treat "unreadable" as "empty" and overwrite it. Task 1 brings `wire_statusline` up to that same standard; its public signature `wire_statusline(settings, status_line, tty, dry, assume_overwrite=False)` and its existing confirm/decline/`assume_overwrite` semantics for interactive runs do not change. Task 1 ALSO gives `wire_statusline` parity with `detect_statusline`'s existing two-shape handling (`tools/setup.py:1614-1637`, which already treats both a dict `{"command": ...}` and a bare string as a valid `statusLine` value): before this fix `wire_statusline` recognized only the dict form, so a settings.json with a valid *string*-valued foreign `statusLine` was silently treated as if none were set and overwritten without consent — Task 1 closes that gap for both the interactive and headless callers. `--with-statusline` in `cmd_install_headless` reaches the hardened `wire_statusline(paths.settings, paths.status_line, None, dry, assume_overwrite=False)` through `_headless_wire_statusline` (the host-absence guard — see the bullet below) — `assume_overwrite` passed explicitly, never relying on the parameter's default.
- **`--examples` composes with `--headless` using the existing non-interactive primitives — it is NOT new in this plan.** `--examples=all|none|<ids>` is already a top-level flag, already documented as "governed entirely by a flag and never prompt" for non-interactive runs (README's existing example-segments section). `cmd_install_headless` accepts it as an optional `examples_flag` parameter and, when given, calls the same `discover_example_segments`/`select_examples`/`install_example_segments` primitives `cmd_install` already uses for its own `--examples` override; `select_examples` never touches `tty` on the flag-given branch, so no new headless-specific selection logic is required. `--examples` remains valid without `--headless` too (unchanged, pre-existing behavior) — it is deliberately NOT added to the "`--skills`/`--with-statusline`/`--with-hooks` require `--headless`" validation bullet below. Passing `--headless --examples=all` (with no `--skills`/`--with-statusline`/`--with-hooks`) counts toward "something was requested" — it must NOT print the bare no-op message. Task 3's README documentation reconciles the existing "Headless / scripted runs ... `--examples=all|none|<ids>`" guidance (README lines 337-340) and the "Wizard modes" paragraph (README lines 387-392) with the new `--headless` flag set so the file states ONE consistent non-interactive contract, not two overlapping ones. That reconciliation must **correct**, not merely annotate, README line 338's unqualified "`--examples=all|none|<ids>` (default `all`…)": `all` is the default for `install.sh`/`make install`/the interactive path (`select_examples` returns every example when the flag is absent, `tools/setup.py:824-832`), but bare `--headless` passes no `--examples` and installs nothing, so the claim is false for the headless path it sits two screens above. See Task 3 Step 7 item 2 and Step 8's grep for it.
- `--with-hooks` calls BOTH `wire_hook_claude(paths.settings, paths.claude_hook, dry)` and `wire_hook_cursor(paths.cursor_hooks, paths.cursor_hook, dry)` unconditionally — both already independently no-op cleanly ("skipped ... — no claude/cursor dir") when the respective config dir doesn't exist, so no host-detection logic is needed for dispatch. `_headless_wire_hooks` (Task 3) DOES still check `os.path.isdir(paths.claude_dir)` / `os.path.isdir(paths.cursor_dir)` itself — not to gate the call, but to classify the *outcome* for the exit-code contract below (an absent host dir is an expected skip; a present dir the wirer still returned `False` for is an actual failure).
- **Host absence is a benign skip for `--with-statusline` too, and it must never materialize `~/.claude/`.** `wire_hook_claude` documents and enforces a guarantee the status-line path does not have: "Never materializes `~/.claude/settings.json` when the parent directory does not exist" — it checks `if not os.path.isdir(os.path.dirname(settings) or "."):` first (`tools/setup.py:1511`) and returns `False` with a printed `skipped Claude Code SessionStart hook — no claude dir` (`tools/setup.py:1512-1513`; the function's `def` is at `:1503`). `wire_statusline` has no such guard, and `_atomic_write_json` does `os.makedirs(os.path.dirname(path) or ".", exist_ok=True)` (`tools/setup.py:1395`), so a naive `--headless --with-statusline` on a machine with no Claude Code would **create** `~/.claude/settings.json` from nothing. That contradicts this plan's "nothing touched unless asked", contradicts the exit-code contract's "only 'that host isn't present on this machine' is a benign `0` skip" rule, and makes `--with-statusline` and `--with-hooks` disagree about host absence. **Contract:** `--headless --with-statusline` when `paths.claude_dir` does not exist prints one `skipped ai-kit status line — no claude dir` line, writes nothing, creates no directory and no file, and is a benign success (contributes `True`, so the run still exits `0`). **Where it is enforced:** in a new Task 3 helper `_headless_wire_statusline(paths, dry)` that performs the `os.path.isdir(paths.claude_dir)` check and only then calls `wire_statusline` — deliberately NOT inside `wire_statusline` itself, which would add a sixth interactive-path behavior change to Task 1's scoped hardening for no benefit (the interactive wizard only ever reaches `wire_statusline` after the host dir is already known-present). This keeps Task 1's delta list at exactly the five documented items in the Goal (four in `wire_statusline`, one in `detect_statusline`). Tested both ways in Task 3: absent dir → exit `0`, nothing created; present dir → wired as before.
- `--dry-run` must compose with every new flag exactly as it already does for the interactive path (`link_one`/`wire_statusline`/`wire_hook_*`/`install_example_segments` all already respect `dry` — no new dry-run logic needed, just thread the existing `args.dry_run` through).
- **Exit code contract:** `cmd_install_headless` returns `int`, not always `0`. The organizing rule, applied with no exceptions: **an operation the caller explicitly requested that did not happen is exit `1`; only "that host/category isn't present on this machine" is a benign `0` skip.**
  - `0`: the bare no-op; an unrecognized `--skills` NAME (the name does not exist in the repo at all — a warning, in the keep-going spirit of `enumerate_entries`'s dropped-entry docstring, though the warning itself is new here); `--with-statusline` or `--with-hooks` skipping a host whose config dir doesn't exist (expected — same as the interactive path, and see the host-absence bullet below); `--examples` resolving to an empty picked set (`--examples=none`, or no bundled examples discovered); any combination of the above that completes without an actual write/link failure.
  - `1`: something explicitly requested via `--with-statusline`/`--with-hooks`/`--skills`/`--examples` could not be completed for a reason OTHER than "that host isn't configured on this machine":
    - `wire_statusline` returning `False` **while `paths.claude_dir` exists** — unreadable/non-object `settings.json`, a foreign statusLine (dict OR string form) headless mode cannot prompt to confirm, a `statusLine` value of an unsupported shape or a non-string `command` (see the statusLine-shape bullet below), or a write failure. An ABSENT `paths.claude_dir` is not this case — it is a benign `0` skip, and `wire_statusline` is not even called; see the host-absence bullet below.
    - `wire_hook_claude`/`wire_hook_cursor` returning `False` while their target config directory DOES exist (malformed config or a write failure).
    - **A requested skill that exists in the repo but could not be linked.** `link_one` never raises for a conflict — it reports one through `counts["skip_foreign"]` (the link path is a symlink pointing outside ai-kit) or `counts["skip_real"]` (the link path is a real file/dir). Both mean "you asked for this skill and it is not linked," so both are exit `1`. `_headless_link_skills` detects them by snapshotting `counts["skip_foreign"] + counts["skip_real"]` before the `apply_additive_skills` call and comparing after; `link_one`'s own `warn:` line already names the offending path, and the helper adds one summary `warn:`. (This is the only place in the headless path where a counter value, not a return value, carries the failure signal.)
    - `apply_additive_skills` raising `OSError` while linking a requested skill (a genuine filesystem error — permissions, a read-only `$CLAUDE_CONFIG_DIR`).
    - `--examples` failing: `install_example_segments` raising `OSError` (its `os.makedirs(seg_dir)` on an unwritable/blocked config dir), or returning FEWER ids than were picked (its documented per-provider skip path — an unreadable source or a bad destination). See the examples bullet below.
    - **`enumerate_entries` raising `OSError`** — it is the only one of the two resolution calls that touches the filesystem (`os.path.isdir` / `os.listdir` at `tools/setup.py:605-606`), e.g. an `AI_KIT_DIR` that exists but is unreadable. It is wrapped in a `try`/`except OSError` in `_headless_paths_and_entries`, called as the very first statement of `cmd_install_headless`, which prints a `warn:` and returns `1` before anything else runs (an explicit error boundary in the implementation, not just a documented intent — see Task 3). **`resolve_paths` sits inside that same `try` defensively only, NOT as a real failure mode:** `resolve_paths` (`tools/setup.py:49-77`) is pure `env.get` + `os.path.join` string manipulation with no filesystem I/O whatsoever, so it cannot raise `OSError` today — it is inside the boundary as belt-and-suspenders against a future edit that adds I/O to it, and because splitting the two calls across two `try` blocks would buy nothing. Do not describe a `resolve_paths` `OSError` as something an operator can actually trigger; the test that covers it (`test_resolve_paths_failure_is_reported_and_nonzero`, Task 3) proves the boundary's shape via `mock.patch`, not a reachable real-world failure.
  - `2`: unchanged — reserved for argparse's own usage errors and the existing `require_tty` fail-closed exit (see the flag-validation bullet below; `cmd_install_headless` itself never raises this).
  - Exit `1` is reported ONCE, at the end: each helper returns a bool, `cmd_install_headless` ANDs them, and a failure never short-circuits the remaining requested work (a failed statusLine must not silently skip `--with-hooks`).
- **`statusLine` shape validation (Task 1).** `settings.json`'s `statusLine` has exactly two supported shapes — a bare string, or an object with a string `"command"` (`detect_statusline`, `tools/setup.py:1614-1637`). Task 1's rewritten `wire_statusline` classifies the value BEFORE deciding anything:
  - absent, `null`, or a dict with no `"command"` key → **unset**; set/refresh silently (nothing to preserve).
  - a `str` → that string is `cur_cmd`; a dict whose `"command"` is a `str` → that string is `cur_cmd`. `cur_cmd` containing `status_line` means it is already ours (refresh silently); a non-empty `cur_cmd` that is not ours is the foreign-command guard (confirm on a tty, refuse headless).
  - **anything else — a list, a number, a bool, or a dict whose `"command"` is not a string (e.g. `{"statusLine": {"command": 1}}`) — is refused**: print one `warn:` naming the file and the offending shape, write nothing, return `False`. This replaces two current bugs: `{"statusLine": {"command": 1}}` raises `TypeError` out of `status_line not in cur_cmd`, and a list/number `statusLine` is silently overwritten because `cur_cmd` collapses to `""`.
  - The unsupported-shape refusal is **unconditional — `assume_overwrite` does NOT bypass it.** `assume_overwrite` exists because the UI already showed the user a specific foreign command and got a yes; an unsupported shape was never shown to anyone, so there is no consent to act on. `assume_overwrite` still bypasses the foreign-command guard for both supported shapes (string and dict), which is its only job.
  - **`detect_statusline`'s ACTUAL per-shape behavior today — verified by execution, not read off the docstring.** `detect_statusline` (`tools/setup.py:1614-1637`) does NOT uniformly collapse unsupported shapes to `"unset"`. Its behavior splits in two, and the split is the reason Task 1 touches it:
    - **`{"statusLine": {"command": 1}}` — a dict whose `"command"` is not a string — RAISES `TypeError`.** The `isinstance(cur, dict)` branch at `:1627` sets `cur_cmd = cur.get("command", "")` → `1` at `:1628`; `1` is **truthy**, so the `if not cur_cmd` guard at `:1633` does NOT fire; and `paths.status_line in cur_cmd` at `:1635` then raises `TypeError: argument of type 'int' is not iterable` (verified by running today's code under this repo's Python 3.12; a newer CPython words the same error "argument of type 'int' is not a container or iterable" — treat either as the expected message). Note the two near-misses, both verified the same way: `{"command": None}` and `{"command": ""}` are falsy, so they DO return `"unset"`; and a truthy non-string *container* (`{"command": ["x"]}`, `{"command": {"nested": "x"}}`) does not crash either — `in` works on a list and on a dict's keys, so it returns `{"state": "foreign", "current_command": ["x"]}`, leaking a non-string out as `current_command`. Only a truthy non-container `"command"` (`1`, `True`) raises.
    - **`{"statusLine": 42}`, `{"statusLine": ["/usr/bin/mybar"]}`, `{"statusLine": true}` — list/number/bool — DO return `{"state": "unset", "current_command": None}`**, via the `else: cur_cmd = ""` collapse at `:1631-1632` and the guard at `:1633`. For these, and only these, the original "gracefully returns unset" description was right.
  - **That `TypeError` is an uncaught crash in the INTERACTIVE path today.** `detect_statusline` is called from the wizard's context population at `tools/setup.py:2248` (`sl_state = detect_statusline(paths)`) and `:2288` (the live `status_line=lambda: detect_statusline(paths)` callable the adoption gate re-invokes). Both run BEFORE `persist_statusline`'s `if detect_statusline(paths)["state"] == "ours"` gate at `:2163` and before any `wire_statusline` call, so an interactive `install`/`reconfigure` against `{"statusLine": {"command": 1}}` dies with a traceback during wizard startup. No "the gate says unset, the user says yes, the hardened writer refuses" narrative applies to this shape — nothing ever reaches the writer.
  - **Decision: Task 1 fixes it, rather than deferring it as tech debt.** The fix is in scope under this plan's file-scope constraint (`tools/setup.py`), it is three lines, and it needs no new design: Task 1 already introduces `_statusline_command`, whose `None` return means "unsupported shape" — and `None` is falsy, so routing `detect_statusline` through it makes the EXISTING `if not cur_cmd` guard at `:1633` return `"unset"` for the dict-with-non-string-`"command"` case exactly as it already does for list/number/bool. No new `"state"` value is introduced, so **no wizard UI surface that renders `"state"` changes at all** — which was the real reason an earlier draft wanted `detect_statusline` frozen. Deferring instead would have left the plan shipping an uncaught interactive traceback while its own Goal claimed the `TypeError` was fixed. See Task 1 Step 1's `TestStatusLineDetection` additions and Step 3's `detect_statusline` patch.
  - **What REMAINS deliberately out of scope after that fix — the one place the two classifiers still disagree.** `detect_statusline` reports every unsupported shape as `"unset"`, while the hardened `wire_statusline` REFUSES it. So for `{"statusLine": ["/usr/bin/mybar"]}` (or `{"command": 1}`, post-fix) the interactive adoption gate tells the user "no status line configured", accepts their yes, and only then reaches `wire_statusline`, which refuses and returns `False` — propagated by `persist_statusline` at `tools/setup.py:2169-2170`. That residual defect is a **misleading message, not a wrong write**, and after Task 1 the outcome is genuinely safer than today's on both branches (today: a crash for the dict shape, a silent overwrite of the unreadable value for list/number/bool; after: the value is preserved and the refusal is printed). Closing it properly means giving `detect_statusline` a new `"state"` — e.g. `"unreadable"` — and teaching every wizard surface that renders `"state"` how to present it, which is a UI behavior change this plan does not make. **Do NOT add a new `"state"` value in this plan**; a follow-up wanting fully unified classifiers needs its own spec for how the wizard should present an unreadable `statusLine`.
- **`--examples` failure contract (Task 3, `_headless_install_examples`).** `install_example_segments` creates `<config_dir>/segments` with a bare `os.makedirs(..., exist_ok=True)` that can raise `OSError`, and it deliberately `continue`s past any provider whose source can't be read or whose destination is bad — returning only the ids it actually installed. Headless mode therefore: wraps the call in `try`/`except OSError` (one `warn:`, return `False`); and after a successful call compares `len(ids)` with `len(picked)` — fewer ids means at least one explicitly requested provider was skipped, so it prints one summarizing `warn:` (the per-file reason is already on stderr from `install_example_segments` itself) and returns `False`. Both map to exit `1`. An empty `picked` (`--examples=none`, or nothing discovered) is NOT a failure — nothing was asked of the filesystem — and returns `True`.
- **Pylint design limits are a hard gate — but `make lint` is NOT the gate that enforces them.** `pyproject.toml`'s `[tool.pylint.design]` sets `max-args = 5`, `max-positional-arguments = 5`, `max-locals = 15`, `max-branches = 12`, `max-returns = 6`, `max-statements = 50`, and `tools/setup.py` currently scores 10.00/10 on all six. **Where they are actually enforced, verified against this repo:** `Makefile`'s `lint` target (`Makefile:37-39`) runs ONLY `shellcheck` + `python3 -m py_compile` — it never invokes Pylint, ruff, pyright, or vulture, so a blown design limit passes `make lint` silently. Pylint runs under `make validate` (`Makefile:44-45` → `uv run pre-commit run --all-files`), whose `pylint` hook is scoped to `^tools/(status-line|statusline-doctor|setup)\.py$` (`.pre-commit-config.yaml:23-28`) — so `tools/setup.py` IS covered there — and under the **explicit `uv run pylint tools/setup.py` steps this plan schedules directly (Task 1 Step 4 and Task 3 Step 6)**, which are the earliest and most precise enforcement points. Anything over a limit blocks the Task 3 commit at `make validate` (or, earlier and better, at those explicit Pylint runs). Two consequences, both already designed into Task 3 rather than discovered during it:
  - `cmd_install_headless` takes six arguments, one over `max-args`/`max-positional-arguments`. It carries a localized `# pylint: disable=too-many-arguments,too-many-positional-arguments` on its `def` line — the file's established practice for exactly this case (`render_preview` at `:230`, `prune_stale` at `:1093`, `persist_statusline` at `:2131`, `launch_wizard` at `:2447`). No dataclass/namedtuple parameter object is introduced; a six-arg CLI entry point matching the existing `cmd_*` style is the smaller change.
  - Everything else must fit the limits WITHOUT a suppression, which is why the per-category work is split into helpers. A single inlined `cmd_install_headless` would carry ~24 locals (Pylint counts arguments as locals) against `max-locals = 15`. Task 3 states each helper's local/branch/return budget so the executor does not have to rediscover it. Because `make lint` cannot catch a miss here (see above), every task that adds or changes a function in `tools/setup.py` runs `uv run pylint tools/setup.py` itself before its commit — do not defer that to `make validate`.
  - `main()` gains a seventh `return` statement (the headless dispatch), one over `max-returns = 6`. It gets `# pylint: disable=too-many-return-statements` on its `def` line, matching `_apply_wizard_command` (`:1769`) and `layout_move` (`:1844`). Its branch count after this plan is 9 of 12, and its locals 6 of 15 — both still inside the limits.
- **Flag-combination validation** (new `main()` behavior, checked once right after `argparse.parse_args`, before any dispatch): `--skills`/`--with-statusline`/`--with-hooks` are meaningless without `--headless` and must be rejected via `parser.error(...)` (argparse's own mechanism — prints a usage error to stderr and exits `2`) rather than silently ignored. `--examples` is deliberately NOT part of this rejection — it stays valid with or without `--headless`, per the composition bullet above. `--headless` itself is only valid for the `install`/`reconfigure` subcommands and is incompatible with `--config-doctor`; both other combinations are also rejected via `parser.error(...)`.
- Tests live in `tests/test_setup.py` (no new test file), run via `uv run python3 -m unittest tests.test_setup -v`. **Fixture convention, stated precisely:** every class under test here defines its OWN `setUp`/`tearDown` using `tempfile.mkdtemp()` + `shutil.rmtree(..., ignore_errors=True)` (or `self.addCleanup(shutil.rmtree, ...)`), and calls functions with plain path strings it builds itself — there is no shared fixture class or fake `Paths` helper to reuse. `TestEnumerate`, `TestInstalledLinks`, and `TestLinkOne` are the concrete precedents to mirror one-for-one. (`TestFixture` is unrelated — it only asserts the checked-in `tests/fixtures/sample-input.json` has the keys the status-line renderer expects; it provides no temp directory and nothing here should cite it as a fixture pattern.)
- File scope for this plan: `tools/setup.py`, `tests/test_setup.py`, and `README.md` only. No changes to `tools/install.sh`, `launch_wizard`, `apply_selection`, `link_one`, `wire_hook_claude`, `wire_hook_cursor`, `discover_example_segments`, `select_examples`, `install_example_segments`, `Makefile`, or any other existing file/primitive not named above — `wire_statusline`'s internals and `detect_statusline`'s three-line shape-classification fix are the two deliberate, scoped exceptions (see the two bullets above), both changed in Task 1 before the headless dispatch that depends on the former. Do not add a Makefile target in this plan; that conflicted with this same single-file-set constraint in an earlier draft and is resolved here by dropping it, not by making it optional.
- **Completion gates:** every task below ends with its own `git commit` (scoped to exactly the files that task touched). Task 3 is the LAST task, and it is the single commit that carries the user-facing `--headless` CLI, its tests, AND its README documentation together — the repository's commit policy requires implementation, tests, and docs for one logical, user-facing change to travel together, so the README update is not deferred to a trailing docs-only commit. Before that commit, Task 3 also runs `uv run pylint tools/setup.py` (Step 6) and then `make test`, `make lint`, `make validate` — in that order. Note what each covers: `make lint` is shellcheck + `py_compile` only, `make validate` is the pre-commit suite (ruff/pylint/pyright/vulture/tests), and neither reads `README.md` — the README is verified by the manual `rg` checks in Step 8. The explicit Pylint invocation is the design-limit gate; see the Pylint bullet above.

---

### Task 1: Harden `wire_statusline` for safe headless writes (and fix `detect_statusline`'s shape crash)

**Files:**
- Modify: `tools/setup.py:1581-1611` (`wire_statusline`)
- Modify: `tools/setup.py:1625-1632` (`detect_statusline`'s read + shape classification; the function spans `:1614-1637`) — the three-line defensive fix for its uncaught `TypeError`, see Step 3
- Test: `tests/test_setup.py` (`TestWireStatusline`, lines 1401-1463)
- Test: `tests/test_setup.py` (`TestStatusLineDetection`, lines 2597-2660 — the existing `detect_statusline` class, extended with the unsupported-shape cases)

**Interfaces:**
- Modifies: `wire_statusline(settings, status_line, tty, dry, assume_overwrite=False) -> bool` — signature and documented confirm/decline/`assume_overwrite` behavior for the two SUPPORTED `statusLine` shapes are UNCHANGED. Its internal read/write primitives change (from `_read_json`/`_write_json` to `_read_json_checked`/`_atomic_write_json`), its foreign-command detection is widened to recognize a bare-string `statusLine` value (mirroring `detect_statusline`'s handling of the two supported shapes), and it gains two refusal paths: `settings.json` exists but cannot be parsed as a JSON object, and `statusLine` holds an unsupported shape (list/number/bool, or a dict whose `"command"` is not a string).
- Modifies: `detect_statusline(paths) -> dict` — its `{"state": ..., "current_command": ...}` return shape, its three `"state"` values (`"unset"`/`"ours"`/`"foreign"`), and its results for every shape it handles correctly today are ALL unchanged. The single behavior delta: a dict whose `"command"` is truthy-but-not-a-string (`{"statusLine": {"command": 1}}`) currently raises an uncaught `TypeError: argument of type 'int' is not iterable` at `tools/setup.py:1635` (`cur.get("command", "")` yields the truthy `1` at `:1628`, so the `if not cur_cmd` guard at `:1633` is passed) — afterwards it returns `{"state": "unset", "current_command": None}`, the same result `detect_statusline` ALREADY returns for list-, number-, and bool-shaped `statusLine` values via its `else: cur_cmd = ""` collapse at `:1631-1632`. Implemented by replacing that manual classification with the new `_statusline_command` helper below, whose `None` ("unsupported shape") return is falsy and therefore lands on the existing `"unset"` guard. This matters because `detect_statusline` runs in the INTERACTIVE wizard at `tools/setup.py:2248` and `:2288`, where the `TypeError` is a startup crash today — see the `detect_statusline` bullet in Global Constraints for the full verified per-shape table and for what deliberately remains out of scope (no new `"state"` value).
- Produces: `_statusline_command(value) -> str | None` — a tiny pure classifier used by `wire_statusline`: `None`/absent/dict-without-`"command"` → `""` (unset, safe to set); a `str` or a dict with a `str` `"command"` → that string; **anything else → `None`, meaning "unsupported shape, refuse."** Returning `None` vs `""` is the whole point: `""` means "nothing to preserve," `None` means "something is there that we do not understand." Keeping this out of `wire_statusline`'s body also keeps that function's branch count inside `max-branches = 12`.
- Produces: `_statusline_state(settings) -> tuple[dict | None, str | None]` — `_read_json_checked` + `_statusline_command` in one step. `(data, cur_cmd)` on success; `(None, None)` after printing one `warn:` when `settings.json` is unreadable/non-object or its `statusLine` shape is unsupported. This split is not cosmetic: with both refusal paths inlined, `wire_statusline` would carry 7 `return` statements against `max-returns = 6` and fail Step 4's `uv run pylint tools/setup.py` (and later `make validate` — not `make lint`, which runs no Pylint at all).
- Consumes: `_read_json_checked(path) -> (state, data)` and `_atomic_write_json(path, data)` (both already defined at `tools/setup.py:1363` and `:1383`, already used by `wire_hook_claude`/`wire_hook_cursor`). `JSON_STATE_ABSENT`/`JSON_STATE_OK`/`JSON_STATE_UNREADABLE` constants (already defined at `tools/setup.py:1349-1351`).

- [ ] **Step 1: Write the failing tests**

Add to `TestWireStatusline` in `tests/test_setup.py` (same class, same `setUp`/`tearDown` already there — no changes needed to those):

```python
    def test_unparseable_settings_is_refused_not_clobbered(self):
        with open(self.settings, "w", encoding="utf-8") as f:
            f.write("{ this is not json KEEP-ME-12345\n")
        with open(self.settings, "rb") as f:
            before = f.read()
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertFalse(ok)
        self.assertIn(self.settings, buf.getvalue())
        with open(self.settings, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_non_dict_settings_is_refused_not_clobbered(self):
        with open(self.settings, "w", encoding="utf-8") as f:
            json.dump(["not", "a", "dict"], f)
        with open(self.settings, "rb") as f:
            before = f.read()
        ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertFalse(ok)
        with open(self.settings, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_atomic_write_failure_leaves_target_byte_identical(self):
        with open(self.settings, "w", encoding="utf-8") as f:
            json.dump({"theme": "dark"}, f)
        with open(self.settings, "rb") as f:
            before = f.read()
        listing = sorted(os.listdir(self.tmp))

        def _boom(*_args, **_kwargs):
            raise OSError("injected replace failure")

        buf = io.StringIO()
        with mock.patch.object(os, "replace", side_effect=_boom), \
             contextlib.redirect_stderr(buf):
            ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertFalse(ok)
        self.assertTrue(buf.getvalue())
        with open(self.settings, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertEqual(sorted(os.listdir(self.tmp)), listing)

    def test_created_settings_file_is_mode_0600(self):
        self.assertFalse(os.path.isfile(self.settings))
        self.assertTrue(
            setup.wire_statusline(self.settings, self.sl, tty=None, dry=False))
        mode = stat.S_IMODE(os.stat(self.settings).st_mode)
        self.assertEqual(mode, 0o600)

    def test_foreign_string_form_headless_refuses_and_preserves(self):
        # detect_statusline (tools/setup.py:1614-1637) already treats a bare
        # string statusLine as foreign; wire_statusline must match that, not
        # just handle the dict form.
        with open(self.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": "/usr/bin/mybar"}, f)
        with open(self.settings, "rb") as f:
            before = f.read()
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertFalse(ok)
        self.assertIn("mybar", buf.getvalue())
        with open(self.settings, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_foreign_string_form_assume_overwrite_still_overwrites(self):
        # assume_overwrite must short-circuit the string-form guard exactly
        # like it already does for the dict-form guard. (Regression guard: this
        # one already passes pre-implementation — see Step 2.)
        with open(self.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": "/usr/bin/mybar"}, f)
        ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False,
                                    assume_overwrite=True)
        self.assertTrue(ok)
        with open(self.settings, encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn(self.sl, data["statusLine"]["command"])

    def test_non_string_command_is_refused_not_a_traceback(self):
        # {"command": 1} currently raises TypeError out of `status_line not in
        # cur_cmd`. It must refuse cleanly and preserve the file instead.
        with open(self.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": {"type": "command", "command": 1}}, f)
        with open(self.settings, "rb") as f:
            before = f.read()
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertFalse(ok)
        self.assertIn(self.settings, buf.getvalue())
        with open(self.settings, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_list_shaped_statusline_is_refused_not_overwritten(self):
        with open(self.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": ["/usr/bin/mybar"]}, f)
        with open(self.settings, "rb") as f:
            before = f.read()
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertFalse(ok)
        self.assertTrue(buf.getvalue())
        with open(self.settings, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_numeric_statusline_is_refused_not_overwritten(self):
        with open(self.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": 42}, f)
        with open(self.settings, "rb") as f:
            before = f.read()
        with contextlib.redirect_stderr(io.StringIO()):
            ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertFalse(ok)
        with open(self.settings, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_unsupported_shape_is_refused_even_with_assume_overwrite(self):
        # assume_overwrite means "the user already said yes to replacing the
        # command we showed them" — an unsupported shape was never shown to
        # anyone, so there is no consent to act on.
        with open(self.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": ["/usr/bin/mybar"]}, f)
        with open(self.settings, "rb") as f:
            before = f.read()
        with contextlib.redirect_stderr(io.StringIO()):
            ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False,
                                        assume_overwrite=True)
        self.assertFalse(ok)
        with open(self.settings, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_unsupported_shape_refused_before_dry_run_short_circuit(self):
        # dry must not report "would set" for a file it would actually refuse.
        with open(self.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": ["/usr/bin/mybar"]}, f)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=True)
        self.assertFalse(ok)
        self.assertNotIn("would set", out.getvalue())

    def test_dict_without_command_key_is_treated_as_unset(self):
        # Nothing to preserve: an object with no "command" is not a foreign
        # status line, so it is set silently like an absent one.
        with open(self.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": {"type": "command"}, "theme": "dark"}, f)
        self.assertTrue(
            setup.wire_statusline(self.settings, self.sl, tty=None, dry=False))
        with open(self.settings, encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn(self.sl, data["statusLine"]["command"])
        self.assertEqual(data["theme"], "dark")
```

Also add the classifier's own unit tests (a pure function — no temp dir needed), directly above `TestWireStatusline`:

```python
class TestStatuslineCommandClassifier(unittest.TestCase):
    def test_unset_shapes_return_empty_string(self):
        for value in (None, {}, {"type": "command"}):
            self.assertEqual(setup._statusline_command(value), "")

    def test_string_and_dict_command_return_the_command(self):
        self.assertEqual(setup._statusline_command("/usr/bin/mybar"), "/usr/bin/mybar")
        self.assertEqual(
            setup._statusline_command({"command": "/usr/bin/mybar"}), "/usr/bin/mybar")

    def test_unsupported_shapes_return_none(self):
        for value in (["/usr/bin/mybar"], 42, True, {"command": 1}, {"command": None},
                      {"command": ["x"]}):
            self.assertIsNone(setup._statusline_command(value))
```

And add the `detect_statusline` crash regression to the END of the EXISTING `TestStatusLineDetection` class (`tests/test_setup.py:2597-2660`), reusing that class's own `self._paths(payload)` helper — it already makes a temp `HOME`, calls `setup.resolve_paths`, creates the settings dir, and writes the payload, so no new fixture is needed:

```python
    def test_non_string_command_returns_unset_not_a_traceback(self):
        # Today this raises TypeError: argument of type 'int' is not a container
        # or iterable at tools/setup.py:1635 — cur.get("command", "") yields the
        # TRUTHY 1 at :1628, so the `if not cur_cmd` guard at :1633 is passed and
        # `paths.status_line in cur_cmd` explodes. detect_statusline runs in the
        # interactive wizard (tools/setup.py:2248, :2288), so that is a startup
        # crash, not a headless-only concern.
        paths = self._paths({"statusLine": {"type": "command", "command": 1}})
        d = setup.detect_statusline(paths)
        self.assertEqual(d["state"], "unset")
        self.assertIsNone(d["current_command"])

    def test_truthy_non_string_command_shapes_all_return_unset(self):
        for command in (1, True, ["x"], {"nested": "x"}):
            with self.subTest(command=command):
                paths = self._paths({"statusLine": {"command": command}})
                d = setup.detect_statusline(paths)
                self.assertEqual(d["state"], "unset")
                self.assertIsNone(d["current_command"])

    def test_list_number_and_bool_statusline_still_return_unset(self):
        # Regression guard, NOT a red test: these three already return "unset"
        # today via the `else: cur_cmd = ""` collapse at tools/setup.py:1631-1632.
        # Routing detect_statusline through _statusline_command must not change
        # them. See Step 2.
        for value in (["/usr/bin/mybar"], 42, True):
            with self.subTest(value=value):
                paths = self._paths({"statusLine": value})
                d = setup.detect_statusline(paths)
                self.assertEqual(d["state"], "unset")
                self.assertIsNone(d["current_command"])
```

`tests/test_setup.py` already imports `os`, `json`, `io`, `mock`, and `unittest` at the top; add `import contextlib` and `import stat` to that same import block if either is not already present (check before adding — `test_tool_substitution_hook.py` uses this exact pair for the equivalent `wire_hook_claude` tests, so the pattern is proven).

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
uv run python3 -m unittest tests.test_setup.TestStatuslineCommandClassifier tests.test_setup.TestWireStatusline tests.test_setup.TestStatusLineDetection -v
```

Expected, stated per test so no one has to guess (the current implementation is `tools/setup.py:1581-1611`, reading via `_read_json` and writing via `_write_json`):

- `TestStatuslineCommandClassifier` (all three) — **ERROR**: `module 'setup' has no attribute '_statusline_command'` (`_statusline_state` does not exist yet either; it has no direct unit test — `wire_statusline`'s refusal tests cover it).
- `test_unparseable_settings_is_refused_not_clobbered` — **FAIL**: `_read_json` collapses unparseable JSON to `{}`, so it overwrites and returns `True`.
- `test_non_dict_settings_is_refused_not_clobbered` — **FAIL**: same collapse for a non-dict top level.
- `test_atomic_write_failure_leaves_target_byte_identical` — **FAIL** on `assertFalse(ok)`: `_write_json` opens the target with `"w"` directly and never calls `os.replace`, so the patched `os.replace` is never reached; the write "succeeds," the file is rewritten, and `True` comes back.
- `test_created_settings_file_is_mode_0600` — **FAIL** under the usual `umask 022` (`open(path, "w")` yields `0o644`). It would pass only under `umask 077`; keep it either way, because after the rewrite `_atomic_write_json` makes `0o600` a guarantee rather than an accident of the caller's umask.
- `test_foreign_string_form_headless_refuses_and_preserves` — **FAIL**: `cur_cmd` is `""` for a string-shaped value, so the guard never fires and the file is overwritten.
- `test_foreign_string_form_assume_overwrite_still_overwrites` — **PASSES ALREADY**. The current code overwrites string-form values unconditionally, which is the right outcome here for the wrong reason. It is a regression guard, not a red test: after the rewrite it must still pass, proving `assume_overwrite` short-circuits the NEW string-form guard.
- `test_non_string_command_is_refused_not_a_traceback` — **ERROR**: `TypeError: argument of type 'int' is not iterable` from `status_line not in cur_cmd`.
- `test_list_shaped_statusline_is_refused_not_overwritten`, `test_numeric_statusline_is_refused_not_overwritten`, `test_unsupported_shape_is_refused_even_with_assume_overwrite`, `test_unsupported_shape_refused_before_dry_run_short_circuit` — **FAIL**: each collapses to `cur_cmd == ""` today and is silently overwritten (the dry one prints `would set`).
- `test_dict_without_command_key_is_treated_as_unset` — **PASSES ALREADY** (another regression guard: the rewrite must not start refusing a shape that has nothing to preserve).

And in `TestStatusLineDetection` (all three new tests run against `detect_statusline` as it stands TODAY, `tools/setup.py:1614-1637`, before Step 3 touches it):

- `test_non_string_command_returns_unset_not_a_traceback` — **ERROR**: `TypeError: argument of type 'int' is not iterable` raised out of `paths.status_line in cur_cmd` (`:1635`). This is the interactive-path crash Step 3 fixes; confirm the traceback you see names `:1635`, not `wire_statusline`.
- `test_truthy_non_string_command_shapes_all_return_unset` — red on all four sub-tests, in two different ways (both verified by running today's code):
  - `1` and `True` → **ERROR**, `TypeError: argument of type 'int' is not iterable` / `argument of type 'bool' is not iterable`.
  - `["x"]` and `{"nested": "x"}` → **FAIL**, not error: `in` legitimately works on a list and on a dict's keys, neither contains `paths.status_line`, so `detect_statusline` returns `{"state": "foreign", "current_command": ["x"]}` / `{"state": "foreign", "current_command": {"nested": "x"}}` and `assertEqual(d["state"], "unset")` fails. A non-string `"command"` leaking out as `current_command` is the same class of bug as the `TypeError`: the wizard would render a list where it expects a command string.
- `test_list_number_and_bool_statusline_still_return_unset` — **PASSES ALREADY.** A regression guard only: these three shapes already collapse to `cur_cmd = ""` at `:1631-1632`. After Step 3 they must still pass, proving `_statusline_command`'s `None` return lands on the same `"unset"` branch.

Do not "fix" the three already-passing tests (`test_foreign_string_form_assume_overwrite_still_overwrites`, `test_dict_without_command_key_is_treated_as_unset`, `test_list_number_and_bool_statusline_still_return_unset`) into failing ones. Every other listed test must be red before Step 3.

- [ ] **Step 3: Rewrite `wire_statusline` and route `detect_statusline` through the new classifier**

First, `wire_statusline`: replace `tools/setup.py:1581-1611` with the two helpers plus the rewritten function (both helpers go directly above `wire_statusline`; their names start with `_`, so `no-docstring-rgx` does not require docstrings — they are given anyway because the `""` vs `None` distinction is the load-bearing part):

```python
def _statusline_command(value):
    """Classify a settings.json `statusLine` value into its command string.

    Two shapes are supported (same as detect_statusline, tools/setup.py:1614):
    a bare string, or an object with a string "command". Returns:
      ""    → nothing configured (absent/None, or an object with no "command")
      str   → the configured command
      None  → an UNSUPPORTED shape (list/number/bool, or a "command" that is
              not a string). The caller must refuse and write nothing: we
              cannot describe what we would be destroying, so we don't.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "command" not in value:
            return ""
        cmd = value["command"]
        return cmd if isinstance(cmd, str) else None
    return None


def _statusline_state(settings):
    """Read settings.json for wire_statusline: returns (data, cur_cmd), or
    (None, None) after printing one warning when the file exists but is not a
    JSON object, or when its statusLine has an unsupported shape. Split out of
    wire_statusline so that function stays at 6 returns (pylint max-returns)."""
    state, data = _read_json_checked(settings)
    if state == JSON_STATE_UNREADABLE:
        print(f"warn: {settings}: cannot parse as a JSON object — ai-kit will not "
              "overwrite a config file it cannot parse", file=sys.stderr)
        return None, None
    if state == JSON_STATE_ABSENT:
        data = {}
    cur_cmd = _statusline_command(data.get("statusLine"))
    if cur_cmd is None:
        print(f"warn: {settings}: statusLine must be a string or an object with "
              "a string 'command' — ai-kit will not overwrite a statusLine it "
              "cannot read", file=sys.stderr)
        return None, None
    return data, cur_cmd


def wire_statusline(settings, status_line, tty, dry, assume_overwrite=False):
    """Point settings.json's statusLine.command at the bundled status-line.py
    (with `python3 -S`), preserving all other keys. FR-5.5 double-confirm:
      - absent / already ai-kit  → set/refresh silently
      - a DIFFERENT command      → show it and require an explicit 'y'; on a
                                   headless run (no tty) refuse and leave it.
    ``assume_overwrite`` short-circuits the foreign-command guard: the caller
    (the in-UI adoption gate) already asked the user "replace it with ai-kit?"
    and got a yes, so re-prompting on the terminal would be a redundant second
    question.

    Reads via `_read_json_checked` (absent/ok/unreadable) and writes via
    `_atomic_write_json` — the same malformed-aware, atomic primitives
    `wire_hook_claude`/`wire_hook_cursor` already use. A settings.json that
    exists but cannot be parsed as a JSON object is refused outright (never
    silently treated as "empty, safe to overwrite"), and a write failure
    leaves the file byte-identical rather than raising past the caller.

    statusLine may be a bare string or an object with a string "command" (both
    shapes are supported by Claude Code; detect_statusline classifies them
    through the same _statusline_command helper) — a foreign STRING command is
    guarded exactly like a foreign dict command, not silently treated as
    unset. Any OTHER shape (list/number/bool, or a non-string "command") is
    refused outright via _statusline_command — which is where this function and
    detect_statusline part ways: the reader reports such a shape as "unset",
    this writer refuses to touch it. The refusal happens BEFORE the assume_overwrite
    short-circuit and before the dry-run branch: assume_overwrite means a
    human already approved replacing a command we showed them, and we cannot
    show them a shape we don't understand.

    Returns True when statusLine now points at ai-kit, False when left
    untouched (foreign command declined/refused headless, unsupported
    statusLine shape, unreadable settings.json, or a write failure)."""
    desired = "python3 -S " + status_line
    data, cur_cmd = _statusline_state(settings)
    if data is None:
        return False
    if cur_cmd and status_line not in cur_cmd and not assume_overwrite:
        # a foreign status line (dict or bare-string form) — guard it
        if not is_interactive(tty):
            print(f"warn: settings.json has a foreign statusLine ({cur_cmd}) — not wiring "
                  "the ai-kit status line (headless)", file=sys.stderr)
            return False
        _tty_write(tty, f"\nsettings.json already sets a status line:\n  {cur_cmd}\n")
        if not ask_yes_no(tty, "overwrite it with the ai-kit status line?", default=False):
            print("statusLine left untouched (declined).", file=sys.stderr)
            return False
    if dry:
        print(f"would set statusLine -> {desired}")
        return True
    data["statusLine"] = {"type": "command", "command": desired}
    try:
        _atomic_write_json(settings, data)
    except OSError as exc:
        print(f"warn: failed to write {settings}: {exc}", file=sys.stderr)
        return False
    return True
```

Then, `detect_statusline`: replace its manual shape classification — `tools/setup.py:1625-1632`, i.e. the `data = _read_json(...)` line through the `else: cur_cmd = ""` block — with three lines that reuse `_statusline_command`. Nothing else in the function changes: the `if not cur_cmd` guard at `:1633` and the two `return`s at `:1635-1637` stay exactly as they are, and `_statusline_command`'s `None` ("unsupported shape") return is falsy, so it lands on that existing `"unset"` branch instead of reaching `paths.status_line in cur_cmd` and raising. Also extend the docstring's `"unset"` line, so the function's contract matches its behavior:

```python
def detect_statusline(paths):
    """Read-only: classify settings.json's statusLine for the adoption gate.

    Returns {"state": "unset"|"ours"|"foreign", "current_command": str|None}.
      - "ours"    iff the command invokes the resolved paths.status_line
                  (XDG-aware substring match — NOT a hard-coded string).
      - "foreign" iff a statusLine is configured but does not reference our script.
      - "unset"   iff absent, empty, file is missing/malformed, or the statusLine
                  holds an UNSUPPORTED shape (a list/number/bool, or an object
                  whose "command" is not a string). The unsupported case used to
                  raise TypeError out of the `in` test below for a truthy
                  non-container "command" (e.g. {"command": 1}) — an uncaught
                  crash, since the wizard calls this during context population.
                  Classification is shared with wire_statusline via
                  _statusline_command; the two differ only in what they DO about
                  it (this reports "unset", the writer refuses to overwrite).

    statusLine may be a bare string or an object with a string "command" (both
    shapes are supported by Claude Code).  Writes nothing."""
    data = _read_json(paths.settings)
    # _statusline_command returns "" for unset and None for an unsupported
    # shape; both are falsy, so both fall through to "unset" below.
    cur_cmd = _statusline_command(data.get("statusLine"))
    if not cur_cmd:
        return {"state": "unset", "current_command": None}
    if paths.status_line in cur_cmd:
        return {"state": "ours", "current_command": cur_cmd}
    return {"state": "foreign", "current_command": cur_cmd}
```

`_statusline_command` is defined above `wire_statusline` at `:1581`, so it is already in module scope before `detect_statusline` at `:1614` — no reordering needed. `detect_statusline` after this change has 1 argument, 2 locals, 3 branches and 3 returns: comfortably inside every limit, and one local fewer than before (`cur` is gone), so nothing here moves any Pylint needle.

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
uv run python3 -m unittest tests.test_setup.TestStatuslineCommandClassifier tests.test_setup.TestWireStatusline tests.test_setup.TestStatusLineDetection -v
uv run python3 -m unittest tests.test_setup -v   # full file — confirm zero regressions
```

`TestStatusLineDetection`'s seven pre-existing tests (`test_unset_when_absent`, `test_ours_when_command_invokes_resolved_status_line`, `test_foreign_when_other_command`, `test_string_form_statusline_ours`, `test_string_form_statusline_foreign`, `test_missing_settings_file_returns_unset`, `test_malformed_settings_file_returns_unset`) must ALL still pass — they are the proof that routing through `_statusline_command` changed nothing for the shapes `detect_statusline` already handled — and its three new tests go from red to green.

All of `TestWireStatusline`'s existing tests (`test_absent_sets_silently`, `test_already_ai_kit_refreshes_silently`, `test_foreign_requires_confirm_yes_overwrites`, `test_foreign_decline_leaves_untouched`, `test_foreign_headless_does_not_overwrite`, `test_preserves_other_keys`, `test_dry_run_does_not_write`) plus all twelve new `TestWireStatusline` tests added in Step 1 (count them: `test_unparseable_settings_is_refused_not_clobbered`, `test_non_dict_settings_is_refused_not_clobbered`, `test_atomic_write_failure_leaves_target_byte_identical`, `test_created_settings_file_is_mode_0600`, `test_foreign_string_form_headless_refuses_and_preserves`, `test_foreign_string_form_assume_overwrite_still_overwrites`, `test_non_string_command_is_refused_not_a_traceback`, `test_list_shaped_statusline_is_refused_not_overwritten`, `test_numeric_statusline_is_refused_not_overwritten`, `test_unsupported_shape_is_refused_even_with_assume_overwrite`, `test_unsupported_shape_refused_before_dry_run_short_circuit`, `test_dict_without_command_key_is_treated_as_unset` — twelve, matching Step 2's twelve expectations) and the three classifier tests pass. `TestRecipeAndUnwire`/`TestCmdInstall` (which exercise `wire_statusline` indirectly) are unaffected.

Also run Pylint explicitly on the changed functions (`wire_statusline`, `detect_statusline`, and the two new helpers) before committing. This is the real design-limit gate for this task: `make lint` would NOT catch a break here (it runs only `shellcheck` + `py_compile` — see the Pylint bullet in Global Constraints), and waiting for `make validate` in Task 3 Step 9 is too late to discover it:

```bash
uv run pylint tools/setup.py
```

Expected: still `10.00/10`. (`tools/setup.py` is in the pre-commit `pylint` hook's `files` scope — `^tools/(status-line|statusline-doctor|setup)\.py$` — so this is the same check `make validate` will later run, just run now and narrowed to the file you changed.) `wire_statusline` after the rewrite has 5 arguments, 4 locals (`desired`, `data`, `cur_cmd`, `exc`) + 5 args = 9, ~6 branches, and exactly 6 returns — inside `max-args = 5`, `max-locals = 15`, `max-branches = 12`, `max-returns = 6`, with no suppression anywhere in this task. It sits AT the return limit, which is why the two refusal paths live in `_statusline_state`: if a future change adds a seventh return here, move the new path into a helper rather than adding a `disable`.

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "fix(setup): refuse malformed settings.json and unsupported statusLine shapes

wire_statusline now reads via _read_json_checked and writes via
_atomic_write_json, guards a foreign bare-string statusLine, and refuses any
unsupported statusLine shape instead of raising TypeError or silently
overwriting it. detect_statusline shares the new _statusline_command
classifier, which fixes its uncaught TypeError on a non-string \"command\"
(an interactive-wizard crash, tools/setup.py:2248 and :2288) by reporting
\"unset\" — the result it already gave for list/number/bool shapes. These are
deliberate behavior changes on the interactive path, not no-ops."
```

---

### Task 2: `apply_additive_skills` helper + `--skills` flag parsing

**Files:**
- Modify: `tools/setup.py`
- Test: `tests/test_setup.py`

**Interfaces:**
- Produces: `resolve_skills_flag(flag: str | None, entries: dict) -> tuple[set[str] | None, list[str]]` — `(None, [])` means "not requested" (bare `--headless`). `flag.strip().lower() == "all"` means every name in `entries["skills"]`. Otherwise the value is tokenized with `re.split(r"[,\s]+", flag.strip())` and intersected against valid names, returned as `(chosen, unknown)` — unknown names are reported, never silently dropped. **The strip/lower and the `[,\s]+` split are deliberate, literal copies of `resolve_example_selection`'s parsing (`tools/setup.py:815`, `:820`)** so `--skills` and `--examples` accept the same spellings (`ALL`, `all`, `alpha,beta`, `"alpha beta"`); the only intended divergence is the absent `none` value — see the `--skills` bullet in Global Constraints.
- Produces: `apply_additive_skills(names: set[str], entries: dict, claude_dir: str, dry: bool, counts: dict) -> None` — links every name in `names` via `link_one`; mutates `counts` in place (the same counter dict `link_one` already threads through everywhere else in this file) and returns nothing. Unrecognized-name reporting is `resolve_skills_flag`'s job, not this function's — keeping "parse the flag" and "apply the resolved set" cleanly separated. Propagates any `OSError` `link_one` raises — the caller (`_headless_link_skills`, Task 3) is responsible for catching it and mapping it to exit `1`. It likewise does NOT interpret `counts["skip_foreign"]`/`counts["skip_real"]`: `link_one` bumps those instead of raising when a link path is a foreign symlink or a real file, and turning that into an exit code is also the caller's job (see the exit-code contract). This helper's only contract is "link these names, unlink nothing."

- [ ] **Step 1: Write the failing tests**

Add near `TestLinkOne` in `tests/test_setup.py`, following the exact `setUp`/`tearDown` convention `TestEnumerate`/`TestInstalledLinks`/`TestLinkOne` already use (own `tempfile.mkdtemp()`, own `shutil.rmtree` cleanup, plain path strings — see Global Constraints):

```python
class TestResolveSkillsFlag(unittest.TestCase):
    def setUp(self):
        self.entries = {"skills": [("alpha", "/repo/skills/alpha"),
                                    ("beta", "/repo/skills/beta")],
                         "agents": [], "commands": []}

    def test_all_returns_every_skill_name(self):
        chosen, unknown = setup.resolve_skills_flag("all", self.entries)
        self.assertEqual(chosen, {"alpha", "beta"})
        self.assertEqual(unknown, [])

    def test_specific_list_returns_only_named(self):
        chosen, unknown = setup.resolve_skills_flag("alpha", self.entries)
        self.assertEqual(chosen, {"alpha"})
        self.assertEqual(unknown, [])

    def test_unknown_name_reported_not_silently_dropped(self):
        chosen, unknown = setup.resolve_skills_flag("alpha,ghost", self.entries)
        self.assertEqual(chosen, {"alpha"})
        self.assertEqual(unknown, ["ghost"])

    def test_all_unknown_returns_empty_chosen_and_reports_all(self):
        chosen, unknown = setup.resolve_skills_flag("ghost1,ghost2", self.entries)
        self.assertEqual(chosen, set())
        self.assertEqual(unknown, ["ghost1", "ghost2"])

    def test_none_flag_returns_none_and_no_unknowns(self):
        chosen, unknown = setup.resolve_skills_flag(None, self.entries)
        self.assertIsNone(chosen)
        self.assertEqual(unknown, [])

    def test_all_is_case_insensitive_and_whitespace_tolerant(self):
        # Parity with resolve_example_selection, which does
        # flag.strip().lower() == "all" (tools/setup.py:815-817).
        for flag in ("ALL", "All", " all ", "\tALL\n"):
            chosen, unknown = setup.resolve_skills_flag(flag, self.entries)
            self.assertEqual(chosen, {"alpha", "beta"}, flag)
            self.assertEqual(unknown, [], flag)

    def test_space_separated_list_is_accepted_like_examples(self):
        # resolve_example_selection splits on re.split(r"[,\s]+", ...)
        # (tools/setup.py:820); --skills must accept the same spellings, so a
        # space-separated value is a list of names, not one unknown name.
        chosen, unknown = setup.resolve_skills_flag("alpha beta", self.entries)
        self.assertEqual(chosen, {"alpha", "beta"})
        self.assertEqual(unknown, [])
        chosen, unknown = setup.resolve_skills_flag("alpha,  beta", self.entries)
        self.assertEqual(chosen, {"alpha", "beta"})
        self.assertEqual(unknown, [])

    def test_none_literal_is_not_a_keyword_just_an_unknown_name(self):
        # --skills has no `none` value (bare --headless already means nothing),
        # so the literal string is treated as an ordinary unknown skill name.
        chosen, unknown = setup.resolve_skills_flag("none", self.entries)
        self.assertEqual(chosen, set())
        self.assertEqual(unknown, ["none"])


class TestApplyAdditiveSkills(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.install_dir = os.path.join(self.tmp, "install")
        self.claude_dir = os.path.join(self.tmp, "claude")
        for name in ("alpha", "beta"):
            skill_dir = os.path.join(self.install_dir, "skills", name)
            os.makedirs(skill_dir)
            open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8").close()
        self.entries = setup.enumerate_entries(self.install_dir)

    def test_links_only_requested_names(self):
        counts = setup.new_counts()
        setup.apply_additive_skills({"alpha"}, self.entries, self.claude_dir, False, counts)
        self.assertTrue(os.path.islink(os.path.join(self.claude_dir, "skills", "alpha")))
        self.assertFalse(os.path.exists(os.path.join(self.claude_dir, "skills", "beta")))
        self.assertEqual(counts["linked"], 1)

    def test_never_unlinks_an_out_of_band_existing_link(self):
        # 'beta' already linked from some prior run — requesting only 'alpha' must
        # leave 'beta' untouched, unlike apply_selection's reconcile-and-deselect.
        beta_link = os.path.join(self.claude_dir, "skills", "beta")
        os.makedirs(os.path.dirname(beta_link))
        os.symlink(dict(self.entries["skills"])["beta"], beta_link)
        counts = setup.new_counts()
        setup.apply_additive_skills({"alpha"}, self.entries, self.claude_dir, False, counts)
        self.assertTrue(os.path.islink(beta_link))
        self.assertEqual(counts["unlinked"], 0)

    def test_dry_run_makes_no_filesystem_changes(self):
        counts = setup.new_counts()
        setup.apply_additive_skills({"alpha"}, self.entries, self.claude_dir, True, counts)
        self.assertFalse(os.path.exists(os.path.join(self.claude_dir, "skills", "alpha")))
        self.assertEqual(counts["linked"], 1)  # counted, not applied

    def test_link_one_oserror_propagates_to_caller(self):
        # apply_additive_skills does NOT swallow link_one failures — Task 3's
        # cmd_install_headless is what catches this and maps it to exit 1.
        counts = setup.new_counts()
        with mock.patch.object(setup, "link_one", side_effect=OSError("permission denied")):
            with self.assertRaises(OSError):
                setup.apply_additive_skills({"alpha"}, self.entries, self.claude_dir,
                                             False, counts)
```

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
uv run python3 -m unittest tests.test_setup.TestResolveSkillsFlag tests.test_setup.TestApplyAdditiveSkills -v
```

Expected: FAIL with `AttributeError: module 'setup' has no attribute 'resolve_skills_flag'` (and similarly for `apply_additive_skills`).

- [ ] **Step 3: Implement `resolve_skills_flag`**

Add directly above `apply_selection` in `tools/setup.py` (keep it near the selection logic it parallels):

```python
def resolve_skills_flag(flag, entries):
    """Parse --skills' value against the live skills entries. Returns
    (chosen: set[str] | None, unknown: list[str]). `flag is None` means the
    flag was not passed at all -- (None, []), the caller's signal to skip
    skill linking entirely (bare --headless). 'all' (case-insensitive, like
    resolve_example_selection's, tools/setup.py:812) means every valid skill
    name. Otherwise the value is tokenized exactly as --examples' id list is --
    re.split(r"[,\s]+", ...), so 'alpha,beta' and 'alpha beta' both work
    (tools/setup.py:820) -- and intersected against valid names; any name not
    present is returned in `unknown` for the caller to warn about (never
    silently dropped, never a hard failure) -- this includes the case where
    EVERY requested name is unknown, which returns an empty `chosen` set
    alongside a non-empty `unknown` list (the caller must not mistake this for
    "nothing requested").

    Unlike --examples there is NO 'none' value: bare --headless already means
    "link nothing", so the literal 'none' is just an ordinary unknown name."""
    if flag is None:
        return None, []
    valid = {name for name, _ in entries.get("skills", [])}
    if flag.strip().lower() == "all":
        return set(valid), []
    requested = {t for t in re.split(r"[,\s]+", flag.strip()) if t}
    chosen = requested & valid
    unknown = sorted(requested - valid)
    return chosen, unknown
```

`re` is already imported at the top of `tools/setup.py` (`resolve_example_selection` uses `re.split` at `:820`) — do not add an import.

- [ ] **Step 4: Implement `apply_additive_skills`**

Add directly above `apply_selection`, after `resolve_skills_flag`:

```python
def apply_additive_skills(names, entries, claude_dir, dry, counts):
    """Link every name in `names` (skills category only) via link_one -- NEVER
    unlinks anything. Unlike apply_selection, there is no deselect branch: an
    existing ai-kit link for a skill NOT in `names` is left exactly as it is.
    This is the headless-path primitive -- 'nothing touched unless asked.'
    Any OSError link_one raises (e.g. a permission failure) propagates to the
    caller uncaught -- cmd_install_headless is responsible for catching it
    and mapping it to the documented exit-code-1 failure case."""
    by_name = dict(entries.get("skills", []))
    for name in sorted(names):
        target = by_name.get(name)
        if target is None:
            continue
        link_one(os.path.join(claude_dir, "skills", name), target, dry, counts)
```

- [ ] **Step 5: Run the tests and confirm they pass**

```bash
uv run python3 -m unittest tests.test_setup.TestResolveSkillsFlag tests.test_setup.TestApplyAdditiveSkills -v
uv run python3 -m unittest tests.test_setup -v   # full file — confirm zero regressions
```

All new tests pass. No existing test in the neighborhood (`TestLinkOne`, `TestEnumerate`) regresses.

- [ ] **Step 6: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): add resolve_skills_flag + apply_additive_skills helpers"
```

---

### Task 3: `--headless` CLI wiring, `cmd_install_headless`, and documentation

**Files:**
- Modify: `tools/setup.py` (module docstring line 13; new helpers + `cmd_install_headless` after `cmd_install` at `:2527`; `main()` at `:2759`)
- Modify: `README.md` (lines 82-83; lines 337-340; a NEW subsection inserted after the **entire** `### Flags & overrides` subsection ends at line 386 — i.e. immediately before the `**Wizard modes.**` paragraph that begins at line 387, NOT after the fenced `install.sh …` block that ends at line 359; and lines 387-392)
- Test: `tests/test_setup.py`

**Interfaces:**
- Consumes: `resolve_skills_flag`, `apply_additive_skills` (Task 2); the hardened `wire_statusline` (Task 1); `wire_hook_claude`, `wire_hook_cursor`, `resolve_paths`, `enumerate_entries`, `new_counts`, `discover_example_segments`, `select_examples`, `install_example_segments` (all pre-existing, unmodified).
- Produces: `cmd_install_headless(env, dry, skills_flag, with_statusline, with_hooks, examples_flag=None) -> int` — exit code per the Global Constraints exit-code contract (`0` success/benign-skip, `1` an explicitly-requested operation actually failed). Six arguments, so its `def` line carries `# pylint: disable=too-many-arguments,too-many-positional-arguments` (the file's existing practice — see the Pylint bullet in Global Constraints).
- Produces: `_headless_paths_and_entries(env) -> tuple[Paths | None, dict | None]` — `resolve_paths` + `enumerate_entries` behind one `try`/`except OSError`; `(None, None)` after printing one `warn:`. This IS the error boundary the exit-code contract names. **The reachable failure inside it is `enumerate_entries`** (`os.path.isdir`/`os.listdir`, `tools/setup.py:605-606`); `resolve_paths` (`tools/setup.py:49-77`) is pure `env.get` + `os.path.join` with no filesystem I/O and cannot raise `OSError` — it is inside the same `try` defensively, so a future edit that gives it I/O is covered without moving the boundary.
- Produces: `_headless_link_skills(skills_flag, entries, claude_dir, dry, counts) -> tuple[bool, set[str] | None]` — `(ok, chosen)`. `chosen` is `resolve_skills_flag`'s set (`None` when `--skills` was absent) so the caller can distinguish "matched nothing" from "not requested". `ok` is `False` only when a skill that EXISTS in the repo was requested and is not linked afterwards.
- Produces: `_headless_wire_statusline(paths, dry) -> bool` — the host-absence guard for `--with-statusline`: returns `True` after printing one `skipped` line when `paths.claude_dir` does not exist (nothing created — parity with `wire_hook_claude`'s "never materializes `~/.claude/settings.json`" guarantee), otherwise returns `wire_statusline(paths.settings, paths.status_line, None, dry, assume_overwrite=False)` verbatim.
- Produces: `_headless_wire_hooks(paths, dry) -> bool` — wires both hosts unconditionally; `False` only when a host whose config dir EXISTS could not be wired.
- Produces: `_headless_install_examples(paths, examples_flag, dry) -> bool` — `False` on an `OSError` from `install_example_segments` or on a partial install (fewer ids returned than picked).
- Produces: `_headless_summary(requested, skills_matched_nothing, counts) -> str` — pure message builder for the single summary line; no I/O, so it is unit-testable without a temp dir.
- Modifies: `main()`'s argparse setup (new `--headless`, `--skills`, `--with-statusline`, `--with-hooks` arguments; `--examples` already exists), a new post-`parse_args` flag-combination validation block, dispatch (a new branch before the existing `require_tty(open_tty())` call for `install`/`reconfigure`), and its `def` line (`# pylint: disable=too-many-return-statements` — the headless dispatch is its 7th `return`).
- Modifies: `tools/setup.py`'s module docstring, line 13 — `Flags: --dry-run.` must list the four new flags, or the file's own header documents a CLI that no longer matches `--help`.

- [ ] **Step 1: Write the failing tests**

Add the new test classes **immediately after `TestFailClosed` (`tests/test_setup.py:1737-1755`)**, again using each test's own `tempfile.mkdtemp()`/cleanup rather than any shared fixture.

**Placement rationale, corrected and grounded.** `TestFailClosed` is the one class in this file that already drives `main()` through the TTY gate: both of its tests mock `ensure_rich_runtime` and `open_tty` (`return_value=None`), then assert `SystemExit` code `2` for `install` and for `reconfigure` respectively. That is exactly the surface `--headless` sits beside, so the new `main()`-level class belongs next to it. (Do **not** cite `TestWizardLoop` (`:754`) or `TestTty` (`:954`) as the precedent — an earlier draft did, and it was wrong: `TestWizardLoop` drives the pure selection/wizard state model and `TestTty` exercises the `open_tty` primitive in isolation; neither calls `main()` and neither touches the fail-closed gate.) The second relevant precedent is `TestSelectExamples.test_main_parses_examples_flag` (`tests/test_setup.py:743-751`), which already proves `--examples` reaches `cmd_install` without `--headless`.

**Two guards already exist — do not re-derive them.** `TestFailClosed`'s two tests already cover "no `--headless`, no TTY ⇒ `SystemExit` 2" for both subcommands, and `test_main_parses_examples_flag` already covers "`--examples` without `--headless` reaches `cmd_install`". So the new class adds only ONE non-headless test: a call-ORDER assertion (`ensure_rich_runtime` before `open_tty`), which no existing test makes and which is the specific invariant the plan's "byte-identical dispatch" promise rests on. Everything else about the untouched interactive path is left to `TestFailClosed` and `TestSelectExamples`, which the executor must run (and keep green) rather than duplicate.

**Mocking `open_tty` is mandatory in any `main()`-level test that reaches the non-headless branch.** Both existing precedents do it — `TestFailClosed` with `mock.patch.object(setup, "open_tty", return_value=None)`, `test_main_parses_examples_flag` with `return_value=fake_tty` plus a patched `fake_tty.close`. Without it the test calls the real `open_tty()`, which opens `/dev/tty` for real when the suite runs in a terminal, and a mocked `require_tty` discards the handle, leaking it. Follow the precedent exactly.

```python
class TestHeadlessSummary(unittest.TestCase):
    def test_nothing_requested_message(self):
        msg = setup._headless_summary(False, False, setup.new_counts())
        self.assertIn("nothing requested", msg)

    def test_skills_matched_nothing_is_distinct_from_nothing_requested(self):
        msg = setup._headless_summary(True, True, setup.new_counts())
        self.assertIn("matched no valid names", msg)
        self.assertNotIn("nothing requested", msg)

    def test_counts_summary_reports_every_counter(self):
        counts = setup.new_counts()
        counts.update({"linked": 2, "relinked": 1, "skip_foreign": 1, "skip_real": 3})
        msg = setup._headless_summary(True, False, counts)
        for token in ("2 linked", "1 relinked", "1 foreign-skipped", "3 real-skipped"):
            self.assertIn(token, msg)


class TestHeadlessInstall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.install_dir = os.path.join(self.tmp, "install")
        self.claude_dir = os.path.join(self.tmp, "claude")
        self.cursor_dir = os.path.join(self.tmp, "cursor")
        skill_dir = os.path.join(self.install_dir, "skills", "alpha")
        os.makedirs(skill_dir)
        open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8").close()
        os.makedirs(os.path.join(self.install_dir, "tools", "hooks"), exist_ok=True)
        for hook in ("claude_session_start.py", "cursor_session_start.py"):
            open(os.path.join(self.install_dir, "tools", "hooks", hook),
                 "w", encoding="utf-8").close()
        open(os.path.join(self.install_dir, "tools", "status-line.py"),
             "w", encoding="utf-8").close()
        self.env = {"HOME": self.tmp, "AI_KIT_DIR": self.install_dir,
                    "CLAUDE_CONFIG_DIR": self.claude_dir,
                    "CURSOR_CONFIG_DIR": self.cursor_dir,
                    "XDG_CONFIG_HOME": os.path.join(self.tmp, ".config")}

    def test_bare_headless_links_and_wires_nothing(self):
        rc = setup.cmd_install_headless(self.env, False, None, False, False)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.isdir(os.path.join(self.claude_dir, "skills")))

    def test_headless_with_skills_all_links_everything(self):
        rc = setup.cmd_install_headless(self.env, False, "all", False, False)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.islink(os.path.join(self.claude_dir, "skills", "alpha")))

    def test_headless_unknown_skill_warns_but_exits_zero(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = setup.cmd_install_headless(self.env, False, "ghost", False, False)
        self.assertEqual(rc, 0)
        self.assertIn("ghost", buf.getvalue())

    def test_headless_all_unknown_skills_is_not_reported_as_bare(self):
        # --skills ghost (no valid names at all) must say so distinctly, not
        # print the same "nothing requested" line bare --headless prints.
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            rc = setup.cmd_install_headless(self.env, False, "ghost", False, False)
        self.assertEqual(rc, 0)
        self.assertNotIn("nothing requested", buf_out.getvalue())

    def test_requested_skill_blocked_by_foreign_symlink_is_nonzero(self):
        # link_one reports this through counts["skip_foreign"], never by raising.
        # The skill WAS requested and is NOT linked → exit 1 per the contract.
        link = os.path.join(self.claude_dir, "skills", "alpha")
        os.makedirs(os.path.dirname(link))
        os.symlink(os.path.join(self.tmp, "somewhere-else"), link)
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = setup.cmd_install_headless(self.env, False, "alpha", False, False)
        self.assertEqual(rc, 1)
        self.assertEqual(os.readlink(link), os.path.join(self.tmp, "somewhere-else"))
        self.assertIn("foreign", buf.getvalue())

    def test_requested_skill_blocked_by_real_file_is_nonzero(self):
        link = os.path.join(self.claude_dir, "skills", "alpha")
        os.makedirs(os.path.dirname(link))
        with open(link, "w", encoding="utf-8") as f:
            f.write("KEEP-ME\n")
        with contextlib.redirect_stderr(io.StringIO()):
            rc = setup.cmd_install_headless(self.env, False, "alpha", False, False)
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.islink(link))
        with open(link, encoding="utf-8") as f:
            self.assertEqual(f.read(), "KEEP-ME\n")

    def test_unrequested_skill_conflict_does_not_affect_exit_code(self):
        # A conflict on a skill nobody asked for must not turn into exit 1: only
        # REQUESTED-and-unlinked is a failure. 'alpha' is requested and links
        # fine; the blocked path belongs to a skill outside the request.
        other = os.path.join(self.install_dir, "skills", "beta")
        os.makedirs(other)
        open(os.path.join(other, "SKILL.md"), "w", encoding="utf-8").close()
        link = os.path.join(self.claude_dir, "skills", "beta")
        os.makedirs(os.path.dirname(link))
        with open(link, "w", encoding="utf-8") as f:
            f.write("KEEP-ME\n")
        rc = setup.cmd_install_headless(self.env, False, "alpha", False, False)
        self.assertEqual(rc, 0)

    def test_headless_with_statusline_wires_it(self):
        os.makedirs(self.claude_dir, exist_ok=True)
        rc = setup.cmd_install_headless(self.env, False, None, True, False)
        self.assertEqual(rc, 0)
        with open(os.path.join(self.claude_dir, "settings.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("status-line.py", data["statusLine"]["command"])

    def test_headless_statusline_absent_claude_dir_skips_and_creates_nothing(self):
        # self.claude_dir is NOT created: Claude Code is not installed here, so
        # --with-statusline is a benign exit-0 skip that must NOT materialize
        # ~/.claude/settings.json — parity with wire_hook_claude's documented
        # "never materializes settings.json when the parent dir is absent"
        # (guard at tools/setup.py:1511-1513). Without _headless_wire_statusline's
        # guard, _atomic_write_json's os.makedirs(os.path.dirname(path) or ".",
        # exist_ok=True) (tools/setup.py:1395) would create the whole tree.
        self.assertFalse(os.path.exists(self.claude_dir))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = setup.cmd_install_headless(self.env, False, None, True, False)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(self.claude_dir))
        self.assertIn("no claude dir", out.getvalue())

    def test_headless_statusline_and_hooks_agree_on_absent_host(self):
        # The two wiring flags must classify host absence identically: both are
        # benign exit-0 skips that create nothing.
        self.assertFalse(os.path.exists(self.claude_dir))
        with contextlib.redirect_stdout(io.StringIO()):
            rc = setup.cmd_install_headless(self.env, False, None, True, True)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(self.claude_dir))

    def test_headless_statusline_refusal_on_foreign_command_is_nonzero(self):
        os.makedirs(self.claude_dir, exist_ok=True)
        settings = os.path.join(self.claude_dir, "settings.json")
        with open(settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": {"type": "command", "command": "/usr/bin/mybar"}}, f)
        rc = setup.cmd_install_headless(self.env, False, None, True, False)
        self.assertEqual(rc, 1)
        with open(settings, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["statusLine"]["command"], "/usr/bin/mybar")

    def test_headless_statusline_refusal_on_foreign_string_command_is_nonzero(self):
        # Foreign statusLine as a bare string (the other shape Claude Code
        # supports, per detect_statusline) must be refused too, not overwritten.
        os.makedirs(self.claude_dir, exist_ok=True)
        settings = os.path.join(self.claude_dir, "settings.json")
        with open(settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": "/usr/bin/mybar"}, f)
        rc = setup.cmd_install_headless(self.env, False, None, True, False)
        self.assertEqual(rc, 1)
        with open(settings, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["statusLine"], "/usr/bin/mybar")

    def test_headless_statusline_unsupported_shape_is_nonzero(self):
        # Task 1's unsupported-shape refusal, seen through the exit code.
        os.makedirs(self.claude_dir, exist_ok=True)
        settings = os.path.join(self.claude_dir, "settings.json")
        with open(settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": {"type": "command", "command": 1}}, f)
        with contextlib.redirect_stderr(io.StringIO()):
            rc = setup.cmd_install_headless(self.env, False, None, True, False)
        self.assertEqual(rc, 1)
        with open(settings, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["statusLine"]["command"], 1)

    def test_headless_statusline_unparseable_settings_is_nonzero(self):
        os.makedirs(self.claude_dir, exist_ok=True)
        with open(os.path.join(self.claude_dir, "settings.json"), "w",
                  encoding="utf-8") as f:
            f.write("{ not json\n")
        rc = setup.cmd_install_headless(self.env, False, None, True, False)
        self.assertEqual(rc, 1)

    def test_headless_with_hooks_wires_claude_and_cursor_hooks(self):
        os.makedirs(self.claude_dir, exist_ok=True)
        os.makedirs(self.cursor_dir, exist_ok=True)
        rc = setup.cmd_install_headless(self.env, False, None, False, True)
        self.assertEqual(rc, 0)
        with open(os.path.join(self.claude_dir, "settings.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("SessionStart", data.get("hooks", {}))
        with open(os.path.join(self.cursor_dir, "hooks.json"), encoding="utf-8") as f:
            cdata = json.load(f)
        self.assertIn("sessionStart", cdata.get("hooks", {}))

    def test_headless_with_hooks_missing_host_dirs_is_still_exit_zero(self):
        # Neither self.claude_dir nor self.cursor_dir is created — both hosts
        # "not installed on this machine" is an expected skip, not a failure.
        rc = setup.cmd_install_headless(self.env, False, None, False, True)
        self.assertEqual(rc, 0)

    def test_headless_with_hooks_malformed_claude_settings_is_nonzero(self):
        os.makedirs(self.claude_dir, exist_ok=True)
        os.makedirs(self.cursor_dir, exist_ok=True)
        with open(os.path.join(self.claude_dir, "settings.json"), "w",
                  encoding="utf-8") as f:
            f.write("{ not json\n")
        rc = setup.cmd_install_headless(self.env, False, None, False, True)
        self.assertEqual(rc, 1)

    def test_one_failure_does_not_skip_the_other_requested_work(self):
        # A refused statusLine must not short-circuit --skills: both are
        # attempted, the skill links, and the run still exits 1.
        os.makedirs(self.claude_dir, exist_ok=True)
        with open(os.path.join(self.claude_dir, "settings.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"statusLine": "/usr/bin/mybar"}, f)
        with contextlib.redirect_stderr(io.StringIO()):
            rc = setup.cmd_install_headless(self.env, False, "all", True, False)
        self.assertEqual(rc, 1)
        self.assertTrue(os.path.islink(os.path.join(self.claude_dir, "skills", "alpha")))

    def test_dry_run_makes_no_filesystem_changes(self):
        rc = setup.cmd_install_headless(self.env, True, "all", False, False)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.lexists(os.path.join(self.claude_dir, "skills", "alpha")))

    def test_resolve_paths_failure_is_reported_and_nonzero(self):
        # Defensive-boundary test only: resolve_paths (tools/setup.py:49-77) is
        # pure env.get + os.path.join and cannot raise OSError for real, so this
        # asserts the shape of the try/except, not a reachable failure mode. The
        # reachable one is the enumerate_entries test below (os.path.isdir /
        # os.listdir, tools/setup.py:605-606). Keep both: this one pins that
        # resolve_paths stays INSIDE the boundary if it ever grows I/O.
        buf = io.StringIO()
        with mock.patch.object(setup, "resolve_paths", side_effect=OSError("boom")), \
             contextlib.redirect_stderr(buf):
            rc = setup.cmd_install_headless(self.env, False, None, False, False)
        self.assertEqual(rc, 1)
        self.assertIn("boom", buf.getvalue())

    def test_enumerate_entries_failure_is_reported_and_nonzero(self):
        buf = io.StringIO()
        with mock.patch.object(setup, "enumerate_entries", side_effect=OSError("boom")), \
             contextlib.redirect_stderr(buf):
            rc = setup.cmd_install_headless(self.env, False, None, False, False)
        self.assertEqual(rc, 1)
        self.assertIn("boom", buf.getvalue())

    def test_headless_skill_link_failure_is_reported_and_nonzero(self):
        buf = io.StringIO()
        with mock.patch.object(setup, "apply_additive_skills",
                                side_effect=OSError("permission denied")), \
             contextlib.redirect_stderr(buf):
            rc = setup.cmd_install_headless(self.env, False, "all", False, False)
        self.assertEqual(rc, 1)
        self.assertIn("permission denied", buf.getvalue())

    def test_headless_with_examples_installs_segments(self):
        with mock.patch.object(setup, "discover_example_segments",
                                return_value=[{"id": "system_memory",
                                               "filename": "system_memory",
                                               "path": "/x"}]), \
             mock.patch.object(setup, "install_example_segments",
                                return_value=["system_memory"]) as install_mock:
            rc = setup.cmd_install_headless(self.env, False, None, False, False,
                                             examples_flag="all")
        self.assertEqual(rc, 0)
        install_mock.assert_called_once()

    def test_headless_examples_makedirs_oserror_is_reported_and_nonzero(self):
        # install_example_segments' own os.makedirs(seg_dir) can raise — an
        # explicitly requested install that did not happen is exit 1.
        buf = io.StringIO()
        with mock.patch.object(setup, "discover_example_segments",
                                return_value=[{"id": "system_memory",
                                               "filename": "system_memory",
                                               "path": "/x"}]), \
             mock.patch.object(setup, "install_example_segments",
                                side_effect=OSError("read-only file system")), \
             contextlib.redirect_stderr(buf):
            rc = setup.cmd_install_headless(self.env, False, None, False, False,
                                             examples_flag="all")
        self.assertEqual(rc, 1)
        self.assertIn("read-only file system", buf.getvalue())

    def test_headless_examples_partial_install_is_nonzero(self):
        # Two picked, one installed: install_example_segments skips a provider
        # it cannot read or write and returns only the ids it managed.
        buf = io.StringIO()
        picked = [{"id": "a", "filename": "a", "path": "/x/a"},
                  {"id": "b", "filename": "b", "path": "/x/b"}]
        with mock.patch.object(setup, "discover_example_segments", return_value=picked), \
             mock.patch.object(setup, "install_example_segments", return_value=["a"]), \
             contextlib.redirect_stderr(buf):
            rc = setup.cmd_install_headless(self.env, False, None, False, False,
                                             examples_flag="all")
        self.assertEqual(rc, 1)
        self.assertIn("skipped", buf.getvalue())

    def test_headless_examples_none_installs_nothing_and_exits_zero(self):
        with mock.patch.object(setup, "discover_example_segments",
                                return_value=[{"id": "a", "filename": "a",
                                               "path": "/x/a"}]), \
             mock.patch.object(setup, "install_example_segments") as install_mock:
            rc = setup.cmd_install_headless(self.env, False, None, False, False,
                                             examples_flag="none")
        self.assertEqual(rc, 0)
        install_mock.assert_not_called()

    def test_headless_examples_dry_run_does_not_install(self):
        with mock.patch.object(setup, "discover_example_segments",
                                return_value=[{"id": "a", "filename": "a",
                                               "path": "/x/a"}]), \
             mock.patch.object(setup, "install_example_segments") as install_mock:
            rc = setup.cmd_install_headless(self.env, True, None, False, False,
                                             examples_flag="all")
        self.assertEqual(rc, 0)
        install_mock.assert_not_called()

    def test_headless_bare_examples_counts_as_requested_not_bare_noop(self):
        buf = io.StringIO()
        with mock.patch.object(setup, "discover_example_segments", return_value=[]), \
             contextlib.redirect_stdout(buf):
            rc = setup.cmd_install_headless(self.env, False, None, False, False,
                                             examples_flag="none")
        self.assertEqual(rc, 0)
        self.assertNotIn("nothing requested", buf.getvalue())


class TestHeadlessMainDispatch(unittest.TestCase):
    """Exercises --headless through main(), not cmd_install_headless() directly --
    this is what actually proves the CLI bypasses ensure_rich_runtime/open_tty/
    require_tty, which calling cmd_install_headless() in isolation cannot show."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.install_dir = os.path.join(self.tmp, "install")
        self.claude_dir = os.path.join(self.tmp, "claude")
        skill_dir = os.path.join(self.install_dir, "skills", "alpha")
        os.makedirs(skill_dir)
        open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8").close()
        self.env_patch = mock.patch.dict(
            os.environ,
            {"HOME": self.tmp, "AI_KIT_DIR": self.install_dir,
             "CLAUDE_CONFIG_DIR": self.claude_dir},
            clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_headless_install_skips_ensure_rich_runtime_and_tty(self):
        with mock.patch.object(setup, "ensure_rich_runtime") as ensure_rt, \
             mock.patch.object(setup, "open_tty") as open_tty, \
             mock.patch.object(setup, "require_tty") as require_tty:
            rc = setup.main(["install", "--headless", "--skills", "all"])
        self.assertEqual(rc, 0)
        ensure_rt.assert_not_called()
        open_tty.assert_not_called()
        require_tty.assert_not_called()
        self.assertTrue(os.path.islink(os.path.join(self.claude_dir, "skills", "alpha")))

    def test_headless_reconfigure_also_bypasses_tty(self):
        with mock.patch.object(setup, "ensure_rich_runtime") as ensure_rt, \
             mock.patch.object(setup, "require_tty") as require_tty:
            rc = setup.main(["reconfigure", "--headless"])
        self.assertEqual(rc, 0)
        ensure_rt.assert_not_called()
        require_tty.assert_not_called()

    def test_skills_flag_without_headless_is_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            setup.main(["install", "--skills", "all"])
        self.assertEqual(ctx.exception.code, 2)

    def test_with_statusline_flag_without_headless_is_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            setup.main(["install", "--with-statusline"])
        self.assertEqual(ctx.exception.code, 2)

    def test_with_hooks_flag_without_headless_is_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            setup.main(["install", "--with-hooks"])
        self.assertEqual(ctx.exception.code, 2)

    # NOTE: "--examples without --headless still reaches cmd_install" is ALREADY
    # covered by TestSelectExamples.test_main_parses_examples_flag
    # (tests/test_setup.py:743-751). Do not add a duplicate here; just keep that
    # test green — it is the regression guard for --examples staying outside the
    # "requires --headless" validation set.

    def test_headless_examples_flag_threads_through(self):
        with mock.patch.object(setup, "cmd_install_headless", return_value=0) as headless_mock:
            rc = setup.main(["install", "--headless", "--examples", "all"])
        self.assertEqual(rc, 0)
        headless_mock.assert_called_once_with(
            mock.ANY, False, None, False, False, examples_flag="all")

    def test_headless_propagates_the_nonzero_exit_code(self):
        with mock.patch.object(setup, "cmd_install_headless", return_value=1):
            rc = setup.main(["install", "--headless", "--with-statusline"])
        self.assertEqual(rc, 1)

    def test_headless_on_doctor_is_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            setup.main(["doctor", "--headless"])
        self.assertEqual(ctx.exception.code, 2)

    def test_headless_with_config_doctor_is_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            setup.main(["install", "--headless", "--config-doctor"])
        self.assertEqual(ctx.exception.code, 2)

    # NOTE: "no --headless, no TTY ⇒ SystemExit 2" is ALREADY covered, for BOTH
    # install and reconfigure, by TestFailClosed (tests/test_setup.py:1737-1755),
    # which mocks ensure_rich_runtime + open_tty=None exactly as below. Do not
    # duplicate it. The ONE thing no existing test asserts is the call ORDER the
    # "byte-identical dispatch" promise rests on, so that is the only
    # non-headless test added here:

    def test_runtime_gate_still_runs_before_the_tty_gate_without_headless(self):
        # ensure_rich_runtime MUST be mocked out (as TestFailClosed does): main()
        # calls it first, and under the system python3 that `make test` uses
        # textual is absent, so a real call would sys.exit(3) or re-exec under uv
        # and never reach the TTY gate. open_tty MUST be mocked too, for the same
        # reason TestFailClosed and test_main_parses_examples_flag mock it: an
        # unmocked call opens a real /dev/tty when the suite runs in a terminal,
        # and the mocked-out require_tty would never close the handle.
        order = []
        with mock.patch.object(setup, "ensure_rich_runtime",
                                side_effect=lambda *_a: order.append("runtime")), \
             mock.patch.object(setup, "open_tty",
                                side_effect=lambda: order.append("tty") or None), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                setup.main(["install"])
        self.assertEqual(order, ["runtime", "tty"])
```

`require_tty` calls `sys.exit(2)` directly (see `tools/setup.py:969-977`), which is why the call-order test above intercepts `SystemExit` rather than reading a return value — the same interception `TestFailClosed` already uses.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
uv run python3 -m unittest tests.test_setup.TestHeadlessSummary tests.test_setup.TestHeadlessInstall tests.test_setup.TestHeadlessMainDispatch -v
```

Expected: every test in `TestHeadlessSummary`/`TestHeadlessInstall` ERRORs with `module 'setup' has no attribute '_headless_summary'` / `'cmd_install_headless'`, and every `TestHeadlessMainDispatch` test fails on the unrecognized flags (argparse exits `2` for `--headless`, so the two `SystemExit` assertions that expect `2` for a *different* reason are the only ones that could pass by accident — confirm after Step 6 that they pass for the right reason, i.e. `parser.error`'s message mentions the flag combination). The single non-headless test (`test_runtime_gate_still_runs_before_the_tty_gate_without_headless`) describes today's behavior and PASSES before implementation — it is a regression guard for the untouched interactive dispatch, not a red test. Also run the two pre-existing guards this step deliberately does not duplicate, and confirm they are green before and after: `uv run python3 -m unittest tests.test_setup.TestFailClosed tests.test_setup.TestSelectExamples.test_main_parses_examples_flag -v`.

- [ ] **Step 3: Implement the five headless helpers + the summary builder**

Add directly after `cmd_install` in `tools/setup.py`. These exist so `cmd_install_headless` fits `max-locals = 15`/`max-branches = 12`/`max-returns = 6` without a suppression (see the Pylint bullet in Global Constraints); each one's budget is noted in its docstring so a later edit does not silently blow the limit.

```python
def _headless_paths_and_entries(env):
    """resolve_paths + enumerate_entries behind ONE error boundary. Returns
    (paths, entries), or (None, None) after printing one warning — the
    exit-code-1 path the headless contract requires instead of a traceback.

    enumerate_entries is the call that can actually raise: it does os.path.isdir
    + os.listdir on install_dir (tools/setup.py:605-606), e.g. an AI_KIT_DIR that
    exists but is not readable. resolve_paths (tools/setup.py:49-77) is pure
    env.get + os.path.join with no filesystem access and cannot raise OSError; it
    is inside this try only so the boundary still holds if it ever grows I/O."""
    try:
        paths = resolve_paths(env)
        return paths, enumerate_entries(paths.install_dir)
    except OSError as exc:
        print(f"warn: headless setup could not resolve install paths/entries: {exc}",
              file=sys.stderr)
        return None, None


def _headless_link_skills(skills_flag, entries, claude_dir, dry, counts):
    """Resolve --skills and link the result additively. Returns (ok, chosen).

    `chosen` is resolve_skills_flag's value -- None when --skills was not passed
    at all, an empty set when it named only unknown skills -- so the caller can
    tell those two apart in the summary line.

    `ok` is False only when a skill that EXISTS in the repo was requested and is
    NOT linked afterwards. Two shapes of that: link_one raising OSError (a real
    filesystem error), or link_one recording a conflict in counts -- it bumps
    skip_foreign (the link path is a symlink pointing outside ai-kit) or
    skip_real (the link path is a real file/dir) and returns normally, so the
    only way to see it is to compare the counters around the call. An unknown
    NAME keeps ok True: nothing was asked of the filesystem.

    Budget: 5 args + 5 locals = 10 of 15; 5 branches of 12; 4 returns of 6."""
    chosen, unknown = resolve_skills_flag(skills_flag, entries)
    for name in unknown:
        print(f"warn: --skills named unknown skill {name!r} — skipping", file=sys.stderr)
    if not chosen:
        return True, chosen
    blocked_before = counts["skip_foreign"] + counts["skip_real"]
    try:
        apply_additive_skills(chosen, entries, claude_dir, dry, counts)
    except OSError as exc:
        print(f"warn: failed to link one or more requested skills: {exc}",
              file=sys.stderr)
        return False, chosen
    if counts["skip_foreign"] + counts["skip_real"] > blocked_before:
        print("warn: one or more requested skills were left alone (a foreign "
              "symlink or a real file occupies the link path) — see the warnings "
              "above", file=sys.stderr)
        return False, chosen
    return True, chosen


def _headless_wire_statusline(paths, dry):
    """Wire the ai-kit status line, but only if the Claude Code config dir is
    actually there. wire_statusline has no host-presence guard of its own and
    _atomic_write_json would os.makedirs the parent, so calling it blind would
    CREATE ~/.claude/settings.json on a machine with no Claude Code installed.
    wire_hook_claude already refuses to do that ('Never materializes
    ~/.claude/settings.json when the parent directory does not exist' --
    docstring at tools/setup.py:1506-1507, guard + skip + `return False` at
    tools/setup.py:1511-1513); this gives --with-statusline the same guarantee
    without touching wire_statusline's interactive contract.

    An absent host dir is a benign skip -> True (exit 0), exactly like the hook
    wirers' 'no claude dir' case. Budget: 2 args + 0 locals = 2 of 15;
    2 branches of 12; 2 returns of 6."""
    if not os.path.isdir(paths.claude_dir):
        print("skipped ai-kit status line — no claude dir")
        return True
    return wire_statusline(paths.settings, paths.status_line, None, dry,
                           assume_overwrite=False)


def _headless_wire_hooks(paths, dry):
    """Wire the SessionStart hook for both hosts. Both wirers already no-op
    cleanly when their config dir is absent, so neither call is gated -- the
    isdir() checks only CLASSIFY the outcome: a host that isn't installed on
    this machine is an expected skip (True), a host that is installed and still
    failed is a real failure (False)."""
    claude_present = os.path.isdir(paths.claude_dir)
    cursor_present = os.path.isdir(paths.cursor_dir)
    claude_ok = wire_hook_claude(paths.settings, paths.claude_hook, dry)
    cursor_ok = wire_hook_cursor(paths.cursor_hooks, paths.cursor_hook, dry)
    return not ((claude_present and not claude_ok)
                or (cursor_present and not cursor_ok))


def _headless_install_examples(paths, examples_flag, dry):
    """Install the example segments --examples selects, reusing the same
    primitives cmd_install uses (select_examples never touches tty on the
    flag-given branch, so None is a safe tty here).

    Returns False when an explicitly requested install did not happen:
    install_example_segments raising OSError (its own os.makedirs of the
    segments dir, on an unwritable/blocked config dir), or returning FEWER ids
    than were picked -- its documented per-provider skip (unreadable source, bad
    destination), already warned about on stderr by install_example_segments
    itself, summarized once more here so the exit code has a stated reason.
    An empty selection (--examples=none, or nothing discovered) is True:
    nothing was asked of the filesystem.

    Budget: 3 args + 4 locals (examples, picked, ids, exc) = 7 of 15;
    4 branches of 12; 5 returns of 6."""
    examples = discover_example_segments(
        os.path.join(paths.install_dir, "examples", "segments"))
    picked = select_examples(examples, examples_flag, None) if examples else []
    if not picked:
        return True
    if dry:
        print(f"would install {len(picked)} external segment(s): "
              f"{', '.join(e['id'] for e in picked)}")
        return True
    try:
        ids = install_example_segments(picked, paths.config_dir)
    except OSError as exc:
        print(f"warn: examples: could not install into {paths.config_dir}: {exc}",
              file=sys.stderr)
        return False
    print(f"examples: installed {len(ids)} external segment(s): {', '.join(ids)}")
    if len(ids) < len(picked):
        print(f"warn: examples: {len(picked) - len(ids)} requested segment(s) were "
              "skipped (see the warnings above)", file=sys.stderr)
        return False
    return True


def _headless_summary(requested, skills_matched_nothing, counts):
    """The single stdout summary line for a headless run. Pure -- no I/O -- so
    the three cases are unit-testable without a temp dir. `requested` is False
    only for bare --headless; `skills_matched_nothing` distinguishes
    `--skills ghost` (asked for something, nothing valid matched) from it."""
    if not requested:
        return ("headless: nothing requested — pass --skills/--with-statusline/"
                "--with-hooks/--examples to link or wire something")
    if skills_matched_nothing:
        return ("headless: --skills matched no valid names — nothing linked "
                "(see warnings above)")
    return (f"headless summary: {counts['linked']} linked, "
            f"{counts['relinked']} relinked, {counts['skip_foreign']} foreign-skipped, "
            f"{counts['skip_real']} real-skipped")
```

- [ ] **Step 4: Implement `cmd_install_headless`**

Add directly after the helpers from Step 3:

```python
def cmd_install_headless(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        env, dry, skills_flag, with_statusline, with_hooks, examples_flag=None):
    """The --headless counterpart to cmd_install: no Textual, no tty, no
    require_tty gate. Bare (all flags falsy) is a pure no-op -- 'nothing
    touched unless asked' (and nothing fetched -- see the plan's sync note;
    this function never syncs the repo, headless or not). --skills links
    additively (apply_additive_skills, never unlinks). --with-statusline/
    --with-hooks independently opt into wiring those, reusing the existing
    tty-safe primitives (wire_statusline is now itself headless-safe -- see
    Task 1 -- and wire_hook_claude/wire_hook_cursor already were); both wiring
    flags treat an absent host config dir as a benign skip and create nothing
    (_headless_wire_statusline supplies that guard for the status line).
    --examples
    composes unchanged with the existing discover_example_segments/
    select_examples/install_example_segments primitives cmd_install already
    uses for its own --examples override.

    Exit code: 0 for success, the bare no-op, an unrecognized --skills NAME, or
    a host whose config dir doesn't exist (expected skip, not a failure). 1 when
    anything explicitly requested did not happen: a malformed/unreadable config
    file, an unsupported statusLine shape, a foreign statusLine headless mode
    cannot confirm, a write failure, a requested skill blocked by a foreign
    symlink or a real file, an OSError linking a requested skill, a failed or
    partial --examples install, or enumerate_entries raising OSError while
    resolving the checkout (the first statement below, before anything else
    runs; resolve_paths shares that boundary defensively but does no I/O).
    Every requested category is attempted even after an earlier one fails --
    a refused statusLine must not silently skip --with-hooks -- and the
    non-zero exit is reported once, at the end.

    Six arguments, one over pylint's max-args/max-positional-arguments: the
    localized disable above matches this file's existing practice for CLI-shaped
    entry points (render_preview, prune_stale, persist_statusline,
    launch_wizard). Body budget: 6 args + 7 locals (paths, entries, counts, ok,
    chosen, requested, only_invalid_skills) = 13 of 15 max-locals;
    6 branches of 12; 3 returns of 6."""
    paths, entries = _headless_paths_and_entries(env)
    if paths is None:
        return 1

    # --- deliberate omission: no prune_stale/predecessor_candidates call here.
    # See the plan's "Out of scope" section -- their behavior contradicts
    # "nothing touched unless asked." A future --prune-stale flag plugs in here.

    counts = new_counts()
    ok, chosen = _headless_link_skills(skills_flag, entries, paths.claude_dir,
                                       dry, counts)
    if with_statusline and not _headless_wire_statusline(paths, dry):
        ok = False
    if with_hooks and not _headless_wire_hooks(paths, dry):
        ok = False
    if examples_flag is not None and not _headless_install_examples(
            paths, examples_flag, dry):
        ok = False

    requested = (skills_flag is not None or with_statusline or with_hooks
                 or examples_flag is not None)
    only_invalid_skills = (skills_flag is not None and not chosen
                           and not with_statusline and not with_hooks
                           and examples_flag is None)
    print(_headless_summary(requested, only_invalid_skills, counts))
    if dry:
        print("(dry-run — no changes were made)")
    if not ok:
        print("headless: one or more requested operations could not complete "
              "(see warnings above) — exiting non-zero", file=sys.stderr)
        return 1
    return 0
```

- [ ] **Step 5: Wire the new flags, the validation, and the dispatch into `main()`**

In `main()`, add the new arguments alongside the existing `--dry-run`/`--examples`:

```python
    parser.add_argument("--headless", action="store_true",
                         help="non-interactive install/reconfigure: no wizard, "
                              "no tty required. Bare form links/wires nothing; "
                              "combine with --skills/--with-statusline/--with-hooks/"
                              "--examples.")
    parser.add_argument("--skills", default=None, metavar="all|name1,name2",
                         help="(--headless only) skills to link additively — "
                              "never unlinks anything not named.")
    parser.add_argument("--with-statusline", action="store_true",
                         help="(--headless only) wire the ai-kit status line.")
    parser.add_argument("--with-hooks", action="store_true",
                         help="(--headless only) wire SessionStart hooks "
                              "(Claude Code + Cursor).")
```

`--examples` is unchanged — it already exists on the parser and is deliberately NOT gated behind `--headless` (see the composition bullet in Global Constraints).

Immediately after `args = parser.parse_args(argv)`, add flag-combination validation (before any other use of `args`):

```python
    args = parser.parse_args(argv)
    if (args.skills is not None or args.with_statusline or args.with_hooks) \
            and not args.headless:
        parser.error("--skills/--with-statusline/--with-hooks require --headless")
    if args.headless and args.subcommand not in ("install", "reconfigure"):
        parser.error("--headless is only valid with the install/reconfigure subcommands")
    if args.headless and args.config_doctor:
        parser.error("--headless and --config-doctor cannot be combined")
```

Then, in the dispatch section, insert the new branch BEFORE the existing `if args.subcommand in ("install", "reconfigure"):` block's `require_tty` call — same `if` condition, but split on `args.headless`:

```python
    if args.subcommand in ("install", "reconfigure"):
        if args.headless:
            return cmd_install_headless(
                env, dry, args.skills, args.with_statusline, args.with_hooks,
                examples_flag=args.examples)
        ensure_rich_runtime(env)              # may re-exec; must be BEFORE open_tty
        tty = cast("_StdTty", require_tty(open_tty()))  # fail-closed (FR-W.1/B)
        try:
            return cmd_install(env, tty, dry,
                               examples_flag=args.examples)
        finally:
            tty.close()
```

This is a pure insertion — the existing `ensure_rich_runtime`/`require_tty`/`cmd_install` lines are copied verbatim into the implicit `else` branch (the code after the new `if args.headless: return ...`), never edited. `args.examples` now flows to BOTH `cmd_install` (unchanged call) and the new `cmd_install_headless` call — the same flag, same value, same meaning either way.

That new `return` is `main()`'s seventh, one over `max-returns = 6`, so change its `def` line to carry the same localized suppression `_apply_wizard_command` (`tools/setup.py:1769`) and `layout_move` (`:1844`) already use:

```python
def main(argv=None):  # pylint: disable=too-many-return-statements
    """Parse the subcommand and dispatch. Default subcommand is install."""
```

Finally, update the module docstring's flag line (`tools/setup.py:13`) so the file's own header matches `--help`:

```python
Flags: --dry-run, --examples=all|none|<ids>, --config-doctor, and the headless
set --headless / --skills=all|name1,name2 / --with-statusline / --with-hooks
(the last three require --headless).
```

- [ ] **Step 6: Run the tests and confirm they pass**

```bash
uv run python3 -m unittest tests.test_setup.TestHeadlessSummary tests.test_setup.TestHeadlessInstall tests.test_setup.TestHeadlessMainDispatch -v
uv run python3 -m unittest tests.test_setup -v   # full file — confirm zero regressions
uv run pylint tools/setup.py                     # must still be 10.00/10
```

All new tests pass; the full `test_setup.py` suite (including every existing wizard/tty/selection test) is unaffected. Pylint must report `10.00/10` with exactly two new suppressions in the file — `cmd_install_headless`'s `too-many-arguments,too-many-positional-arguments` and `main`'s `too-many-return-statements`. If any OTHER design message fires, fix it by moving work into a helper, not by widening the suppression: a third new `disable` in this task means the decomposition above was not followed.

- [ ] **Step 7: Document `--headless` in README.md**

**Insertion point — read this before typing anything.** The `### Flags & overrides` subsection starts at `README.md:351` and does **not** end at the fenced `install.sh …` block that closes on line 359. It continues for another 27 lines: the `**Try a branch without merging it.**` paragraph (`README.md:361-363`), the `install.sh` must-be-flag-aware prose (`:365-367`), the `curl … --branch` fenced block (`:369-378`), the "Simplest of all, no flag and no gotcha" sentence (`:380-381`), and the `git clone -b feat/x …` fenced block (`:383-385`). The subsection ends at **line 386** (a blank line); line 387 begins the next block, `**Wizard modes.** The interactive wizard requires a real terminal …`.

So insert the new `### Headless install (CI / containers / no TTY)` subsection **after `README.md:386`, immediately before the `**Wizard modes.**` paragraph at line 387** — i.e. at the very end of `Flags & overrides`, after all of its branch-bootstrapping content. **Do NOT insert it at line 360, right after the first fenced block**: a `###` heading there would re-parent lines 361-385 (all the `--branch` guidance) and the `Wizard modes` paragraph under the new Headless heading, which is a documentation regression, and Step 8's check would then certify it as correct.

**Blank line, both sides — this is the easiest thing to get wrong here.** Line 386 is itself the blank line that currently separates the `git clone -b feat/x …` fenced block from `**Wizard modes.**`, so inserting *after* it already leaves the new heading with a blank line above it. What the insertion must ALSO add is **a blank line after the new subsection's last line** (the closing `` `curl -fsSL .../install.sh | bash -s -- install --headless --skills all`. `` sentence), so that `**Wizard modes.**` still begins a line of its own. Without it, Markdown merges the new paragraph and `**Wizard modes.**` into one paragraph, `**Wizard modes.**` stops starting a line, and Step 8's `rg -n '^\*\*Wizard modes\.\*\*'` pattern silently stops matching. After the edit, re-read `README.md` around the seam and confirm the order is: the `git clone -b` block's closing fence, a blank line, `### Headless install (CI / containers / no TTY)`, the subsection, **a blank line**, `**Wizard modes.** The interactive wizard requires …`.

Insert exactly this (mirror the existing tone — terse, example-driven, and precise about what does and does not sync), followed by one blank line before the existing `**Wizard modes.**` paragraph:

```markdown
### Headless install (CI / containers / no TTY)

`python3 tools/setup.py install --headless` skips the interactive wizard
entirely — no TTY, no Textual. Bare `--headless` links and wires nothing (a
pure no-op). Combine with the flags below to opt into specific pieces —
nothing is touched unless explicitly requested:

- `--skills all` — link every skill (or `--skills name1,name2` for a subset).
  Additive only: never unlinks a skill already present from a prior run.
- `--with-statusline` — wire the ai-kit status line into `settings.json`. If the
  Claude Code config dir does not exist, this is skipped with a message and
  nothing is created — ai-kit never conjures a `~/.claude/` on a machine that
  has no Claude Code.
- `--with-hooks` — wire the SessionStart hook for Claude Code and Cursor. Same
  rule: a host that isn't installed here is skipped, not an error.
- `--examples=all|none|<ids>` — the same pre-existing flag `install.sh` and
  the interactive wizard use for bundled example segments; it works
  identically here, with or without `--headless`.

Example: `python3 tools/setup.py install --headless --skills all --with-statusline --with-hooks --examples all`

Exit codes: `0` success (including "nothing requested" and "that host isn't
installed here"), `1` something you asked for did not happen — a config file
ai-kit refuses to overwrite because it cannot parse it, a foreign `statusLine`
it will not replace without a human saying yes, a skill whose link path is
occupied by a real file or a non-ai-kit symlink, or a failed example-segment
copy. `2` is a usage error (bad flag combination, or the interactive path
finding no TTY). A `1` leaves every other requested step still attempted.

**This does not fetch or update the repo.** `--headless` is a flag to
`tools/setup.py`, which never syncs anything itself — syncing is
`tools/install.sh`'s job, and only in piped/bootstrap mode (`curl ... | bash`).
Running `install.sh` (or `make install`) from an existing local clone, or
invoking `tools/setup.py` directly as above, explicitly skips the fetch. For
a CI/container job that needs the latest kit, fetch or `git pull` the repo
yourself first, then run `tools/setup.py install --headless ...` against it —
or pipe the bootstrapper fresh each time if you want the fetch included:
`curl -fsSL .../install.sh | bash -s -- install --headless --skills all`.
```

Then reconcile the three existing README passages that describe non-interactive / headless behavior, so the file states ONE contract instead of contradicting itself. Note the direction words: the new subsection is inserted after `README.md:386` (immediately before the `**Wizard modes.**` paragraph — see the insertion-point note above), so it is **below** the line-82 and line-337 passages and **immediately above** the `Wizard modes` one — get these right, a pointer that says "above" while pointing down is worse than no pointer. (Line numbers in items 1-3 below are pre-insertion numbers, counted against the README as it stands today; apply them before or independently of the insertion, or re-locate each passage by its quoted text rather than by number after the insert shifts everything below 386 down.)

1. At the "**Fail-closed / interactive-only.**" paragraph (`README.md:79-84`), replace its **penultimate** sentence — "There is no plain-menu fallback and no headless-defaults mode — this is deliberate." (it wraps across `README.md:82-83`, ending mid-line 83 at "deliberate.") — with the text below. **Do not edit by position alone:** the paragraph's actual LAST sentence is "A clean `Ctrl-C`, `q`, or `esc` abort leaves the original config intact." (`README.md:83-84`, starting mid-line 83), and it must survive this edit untouched. Match on the quoted sentence text, and after the edit re-read the paragraph to confirm the `Ctrl-C`/`q`/`esc` abort sentence is still there, still last.

```markdown
There is no plain-menu fallback, and the wizard itself never falls back to
headless defaults — this is deliberate. A separate, explicit
`setup.py install --headless` exists for CI and containers (see [Headless
install](#headless-install-ci--containers--no-tty) below); it is opt-in per
piece and defaults to doing nothing, so it is not a "headless defaults" mode.
```

The paragraph must therefore end, after the edit, with the unchanged sentence "A clean `Ctrl-C`, `q`, or `esc` abort leaves the original config intact."

2. At the existing "Headless / scripted runs are governed entirely by a flag and never prompt: `--examples=all|none|<ids>` (default `all`; `<ids>` is a comma/space list of segment ids)." sentence (`README.md:337-340`), **the "default `all`" claim must be corrected, not just pointed away from.** It is true of `install.sh`/the interactive installer, but false of `setup.py install --headless`, where `--examples` is absent by default and bare `--headless` installs NO example segments (`examples_flag is None` ⇒ `_headless_install_examples` is never called). Leaving it as-is would reproduce, two screens above the new subsection, exactly the second contradicting contract this step exists to eliminate.

**What is actually on those four lines — read them before replacing them.** `README.md:337-340` reads, verbatim:

```
duplicates). Headless / scripted runs are governed entirely by a flag and never
prompt: `--examples=all|none|<ids>` (default `all`; `<ids>` is a comma/space list
of segment ids). Disable an installed provider later like any segment:
`[segments] system_memory = false`.
```

Two sentences live here, and only the first one is this plan's business. The second — "Disable an installed provider later like any segment: `[segments] system_memory = false`." — is pre-existing guidance unrelated to `--headless` and **must survive verbatim**. The replacement block below therefore re-states it; if you instead narrow the edit to just the `--examples` sentence, drop that trailing paragraph from the block so you do not duplicate it. Replace `README.md:337-340` with:

```markdown
duplicates). Scripted runs are governed entirely by a flag and never prompt:
`--examples=all|none|<ids>` (`<ids>` is a comma/space list of segment ids). The
default differs by entry point: `install.sh` / `make install` default to `all`,
while `python3 tools/setup.py install --headless` installs **no** example
segments unless you pass `--examples` explicitly — nothing is wired or copied
headlessly unless asked. See "Headless install (CI / containers / no TTY)" below
for the full non-interactive flag set (`--skills`, `--with-statusline`,
`--with-hooks`). Disable an installed provider later like any segment:
`[segments] system_memory = false`.
```

Confirm the "default `all`" phrasing survives nowhere else in the file that could be read as applying to `--headless`, and that `[segments] system_memory = false` still appears exactly once (Step 8 greps for both).

3. Replace the existing "**Wizard modes.**" paragraph (`README.md:387-392` pre-insertion; it is the paragraph the new subsection is inserted directly ABOVE, so its "see … above" pointer resolves to the adjacent block) — which currently ends "there is no plain-menu fallback. For non-interactive installs, pass `--examples=all|none|<ids>` to control which example segments are copied; the rest of the link/prune/statusline steps are always non-interactive." and so describes `--examples` as the whole non-interactive story — with:

```markdown
**Wizard modes.** The interactive wizard requires a real terminal and a
sufficiently large window (see [The install wizard](#the-install-wizard) above).
If either is missing, `install.sh`/`make install` exits non-zero with a clear
message — there is no plain-menu fallback inside the wizard itself. For a
fully non-interactive run instead, use `python3 tools/setup.py install
--headless` (see "Headless install (CI / containers / no TTY)" above) — its
flags are the one non-interactive contract: `--examples=all|none|<ids>`
controls which example segments are copied (identically whether or not
`--headless` is also passed — it is a pre-existing top-level flag), and
`--skills`/`--with-statusline`/`--with-hooks` (headless-only) control
everything else the wizard would otherwise ask about interactively.
```

- [ ] **Step 8: Verify the README change by hand**

There is no automated Markdown/prose checker in this repo's `.pre-commit-config.yaml` — it wires `ruff`, `pylint`, `pyright`, `vulture`, `shellcheck` (scoped to `\.sh$`), `py_compile`, and two `unittest` hooks, none of which reads `README.md`. `make validate` runs exactly those hooks across all files, so it will NOT catch a README formatting or content mistake — verify by hand instead:

```bash
rg -n -- '--headless|--skills|--with-statusline|--with-hooks' README.md
rg -n 'headless-defaults|plain-menu|Headless / scripted|Scripted runs|Wizard modes' README.md
rg -n 'default `all`' README.md
rg -n 'system_memory = false|Ctrl-C' README.md
rg -n '^### |^\*\*Wizard modes\.\*\*|^\*\*Try a branch' README.md
```

Confirm:

- Every flag name printed in `tools/setup.py`'s new `parser.add_argument` calls (Step 5) appears with matching spelling.
- **The new `### Headless install (CI / containers / no TTY)` heading sits at the END of the `Flags & overrides` subsection — after the `git clone -b feat/x …` fenced block and immediately before the `**Wizard modes.**` paragraph — not immediately after the `### Flags & overrides` heading's first fenced block.** The last `rg` above makes this checkable in one glance: the output must show `### Flags & overrides`, then `**Try a branch without merging it.**`, then `### Headless install (CI / containers / no TTY)`, then `**Wizard modes.**`, in that order. Read the result as TWO distinct failures, not one:
  - If `### Headless install …` appears BEFORE `**Try a branch …**`, the insertion landed at the wrong place and has re-parented the `--branch` bootstrapping guidance under the Headless heading — undo and re-insert after the `git clone -b` block.
  - **If the `**Wizard modes.**` row is MISSING from the output entirely (while `### Headless install …` is present and correctly ordered), the cause is a missing blank line, NOT a wrong position.** The new subsection's last line ran straight into `**Wizard modes.**`, so that text no longer starts a line and `^\*\*Wizard modes\.\*\*` cannot match — and Markdown is now rendering the two as one merged paragraph. Fix: insert a single blank line between the new subsection's final line and `**Wizard modes.**` (see Step 7's blank-line note), then re-run the `rg`. Do not go hunting for a misplaced heading; nothing moved.
- **Nothing was deleted as a side effect of the three rewrites.** The second `rg` above must still show `[segments] system_memory = false` (Step 7 item 2's replacement block carries it forward — see that item's verbatim quote of the original four lines) and the `A clean Ctrl-C, q, or esc abort leaves the original config intact.` sentence (Step 7 item 1 replaces only the paragraph's penultimate sentence). A missing hit for either means an edit over-reached its intended range.
- The line-82 and line-337 pointers say **below** and the `Wizard modes` one says **above**, each matching the new subsection's actual position.
- **The third `rg` returns no hit that applies to the headless path.** Item 2 of Step 7 rewrote `README.md:337-340` to drop the bare "(default `all`…)" claim and state the per-entry-point defaults instead; if "default `all`" still appears anywhere as an unqualified statement about `--examples`, the README still carries the two-contract contradiction this step exists to remove, and Step 7 item 2 was not applied.
- No passage still implies `--examples` is the only non-interactive control.
- The anchor `#headless-install-ci--containers--no-tty` matches the new heading's GitHub slug. Derivation, so a verifier computing it by hand gets the same answer: GitHub lowercases, drops `(`, `)` and `/`, and replaces each remaining space with `-`. The heading `Headless install (CI / containers / no TTY)` therefore yields `headless-install-ci--containers--no-tty`: **both doubled hyphens come from a dropped `/`, which has a space on EACH side** (`CI / containers` → `ci` + space + space + `containers`, and `no / TTY`… i.e. `containers / no` → `containers` + space + space + `no`). The dropped `(` and `)` each sit next to a single space and contribute a single hyphen, never a doubled one. Do not "correct" a correct anchor by attributing the doubling to the parenthesis.

- [ ] **Step 9: Run the full quality gate suite**

```bash
make test
make lint
make validate
```

All four checks must pass with zero regressions (the three targets above plus Step 6's `uv run pylint tools/setup.py`). What each one actually does, verified against the repo — do not assume:

- `make test` runs the full `tests.test_setup` suite (plus every other project test module) under the system `python3`. That is exactly why the `main()`-level tests mock `ensure_rich_runtime` (Step 1, and `TestFailClosed` before it): Textual is not importable there, so an unmocked call would `sys.exit(3)` or re-exec under `uv` instead of reaching the TTY gate.
- `make lint` (`Makefile:37-39`) runs **only** `shellcheck` (on `install.sh` + `tests/test_install.sh`) and `python3 -m py_compile` over the Python files. **It does NOT run Pylint, ruff, pyright, or vulture, and it therefore cannot catch a design-limit break.** A `cmd_install_headless` with 16 locals passes `make lint` cleanly. Treat this step as a syntax/shell check, nothing more.
- `make validate` (`Makefile:44-45`) is `uv run pre-commit run --all-files`, which is where `pylint`, `ruff`, `pyright`, and `vulture` actually run. Its `pylint` hook is scoped to `^tools/(status-line|statusline-doctor|setup)\.py$` (`.pre-commit-config.yaml:23-28`), so `tools/setup.py` IS in scope and the Global Constraints design limits are enforced **here** — plus, earlier and more precisely, by Step 6's explicit `uv run pylint tools/setup.py`. If a helper extraction was missed, Step 6 is where you should already have seen it; this step is the backstop.
- Neither `make lint` nor `make validate` reads `README.md` — no Markdown or prose hook exists in `.pre-commit-config.yaml`. The README correctness check is the manual `rg` step in Step 8, and it is not optional.

- [ ] **Step 10: Commit**

Commit the CLI, its tests, and its documentation together — this is the one user-facing logical change and the repository's commit policy requires implementation, tests, and docs to travel together:

```bash
git add tools/setup.py tests/test_setup.py README.md
git commit -m "feat(setup): add --headless install/reconfigure fallback with docs"
```
