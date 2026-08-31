# ai-kit-spec Dispatch Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden cross-AI reviewer dispatch (and give execute-mode the same tooling-guidance
symmetry) with tiered timeout escalation, progressive interim-progress polling, an explicit
repo-owned tooling-preference resource injected into every dispatch, and codegraph/MCP-aware
CLI selection.

**Architecture:** A new shared polling-and-tiers dispatch engine in `dispatch.py`, a new
`reviewer_dispatch.py` module + `dispatch-reviewer` CLI subcommand that wraps it for the review
path, an extension to the existing `tooling_guidance.py` for a repo-owned reference file both
execute and review consume, a `policy.timeout_tiers` config field, a best-effort
codegraph-alternative-CLI matcher, and three SKILL.md updates (`ai-kit-spec-review`,
`ai-kit-spec-review-checklist`, `ai-kit-spec-config`) that wire it all together.

**Tech Stack:** Python 3 stdlib only, `unittest`.

**Spec:** `docs/superpowers/specs/2026-08-31-ai-kit-spec-dispatch-hardening-design.md`

## Global Constraints

- `execute_dispatch.dispatch_execute`'s existing single-`timeout` call site is NOT migrated to
  the new tiered engine — out of scope (spec §11, Non-Goals). `dispatch_with_heartbeat` stays
  as-is and keeps its existing callers.
- `poll_interval` is never user-configurable — fixed at `150` seconds inside
  `dispatch_with_polling`'s own default (spec §9, §11).
- Progressive polling is informational only — never aborts a dispatch attempt early, even at
  zero growth (spec §2, §4).
- The legacy-tool-usage checklist rule is `MEDIUM` severity unconditionally once BOTH conditions
  hold (legacy tool referenced by literal invocation AND the modern equivalent is confirmed via
  `tool_availability` — never flagged on an unconfirmed presence) (spec §7).
- The codegraph-alternative-CLI note in `ai-kit-spec-config` is informational only — never a
  hard filter; the user always makes the final registration choice (spec §8).
- `policy.timeout_tiers` defaults to `[600, 1200, 1800]` (10/20/30 minutes) when absent from
  config; an individual `[[reviewers]]` entry's `extra.timeout_tiers` overrides the policy
  default for that entry only (spec §9).

---

## File Structure

```
skills/ai-kit-spec-review/
  ai_kit_spec/dispatch.py                    (Task 1: dispatch_with_polling)
  ai_kit_spec/tooling_guidance.py            (Task 2: shared_reference_path, resolver)
  ai_kit_spec/execute_dispatch.py            (Task 2: wire new param into existing call)
  ai_kit_spec/reviewer_dispatch.py           (Task 3: NEW — dispatch_reviewer)
  ai_kit_spec/cli.py                         (Task 3: dispatch-reviewer; Task 5: check-codegraph-alternative)
  ai_kit_spec/config_io.py                   (Task 4: timeout_tiers default + resolver)
  ai_kit_spec/detection.py                   (Task 5: find_codegraph_alternative)
  references/tooling-guidance.md             (Task 2: NEW)
  SKILL.md                                   (Task 8: Step 0.7, Step 1, native prompt template)

skills/ai-kit-spec-review-checklist/
  SKILL.md                                   (Task 6: legacy-tool-usage rule)

skills/ai-kit-spec-config/
  SKILL.md                                   (Task 7: Step 2.2-2.4, Step 2.8)

skills/ai-kit-spec-execute-gsd/
  ai_kit_spec_gsd/cli.py                     (Task 2: wire new param into prepare-tooling)

tests/test_ai_kit_spec.py                    (Tasks 1-5: new tests)
```

---

### Task 1: `dispatch_with_polling` (tiered timeout + progressive polling engine)

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/dispatch.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `_default_kill_process_group` (existing, same file), `_default_print_fn` (existing,
  same file).
- Produces: `dispatch_with_polling(command: str, prompt: str, timeout_tiers: list[int],
  poll_interval: int = 150, popen_fn=subprocess.Popen, time_fn=time.time, sleep_fn=time.sleep,
  kill_fn=_default_kill_process_group, print_fn=_default_print_fn,
  tmp_dir_fn=tempfile.mkdtemp, rmtree_fn=shutil.rmtree) -> dict` returning `{"returncode": int|
  None, "stdout": str, "stderr": str, "timed_out": bool, "tiers_tried": int, "final_timeout":
  int}` — used by Task 3's `dispatch_reviewer`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ai_kit_spec.py` (new `TestDispatchWithPolling` class; add `import tempfile`
near the top of the file if not already present):

```python
class TestDispatchWithPolling(unittest.TestCase):
    class _FakeProc:
        def __init__(self, returncode_after_polls):
            self._polls_left = returncode_after_polls
            self.returncode = None
            self.pid = 4242
            self.killed = False

        def poll(self):
            if self._polls_left <= 0:
                self.returncode = 0
            else:
                self._polls_left -= 1
            return self.returncode

        def wait(self, timeout=None):
            return self.returncode

    def _fake_kill(self, proc):
        proc.killed = True
        proc.returncode = -9

    def test_single_tier_success_writes_prompt_and_returns_captured_output(self):
        written = {}

        def fake_popen(command, shell, stdin, stdout, stderr, start_new_session):
            written["command"] = command
            written["prompt"] = stdin.read()
            stdout.write(b"real report text")
            stderr.write(b"")
            return self._FakeProc(returncode_after_polls=1)

        times = iter([0.0, 10.0, 20.0])
        result = dispatch.dispatch_with_polling(
            "echo hi", "the prompt", timeout_tiers=[600], poll_interval=50,
            popen_fn=fake_popen, time_fn=lambda: next(times), sleep_fn=lambda s: None,
            kill_fn=self._fake_kill, print_fn=lambda *a: None)

        self.assertEqual(written["command"], "echo hi")
        self.assertEqual(written["prompt"], "the prompt")
        self.assertEqual(result["stdout"], "real report text")
        self.assertEqual(result["returncode"], 0)
        self.assertFalse(result["timed_out"])
        self.assertEqual(result["tiers_tried"], 1)
        self.assertEqual(result["final_timeout"], 600)

    def test_first_tier_times_out_and_escalates_to_second_tier_which_succeeds(self):
        attempts = []

        def fake_popen(command, shell, stdin, stdout, stderr, start_new_session):
            attempt_index = len(attempts)
            attempts.append(attempt_index)
            if attempt_index == 0:
                # Never finishes within tier 1's budget -- polls_left huge.
                return self._FakeProc(returncode_after_polls=10_000)
            stdout.write(b"finished on tier 2")
            return self._FakeProc(returncode_after_polls=0)

        # Tier 1 (timeout=10): start=0.0, first poll check at elapsed=15 (>10 -> timeout).
        # Tier 2 (timeout=600): start=15.0, next call elapsed=16 (<600 -> proceed), proc
        # finishes on first poll() call (returncode_after_polls=0).
        times = iter([0.0, 15.0, 15.0, 16.0])
        result = dispatch.dispatch_with_polling(
            "slow-cmd", "p", timeout_tiers=[10, 600], poll_interval=50,
            popen_fn=fake_popen, time_fn=lambda: next(times), sleep_fn=lambda s: None,
            kill_fn=self._fake_kill, print_fn=lambda *a: None)

        self.assertEqual(len(attempts), 2)
        self.assertTrue(attempts_killed := attempts)  # sanity: both attempts recorded
        self.assertFalse(result["timed_out"])
        self.assertEqual(result["tiers_tried"], 2)
        self.assertEqual(result["final_timeout"], 600)
        self.assertEqual(result["stdout"], "finished on tier 2")

    def test_all_tiers_exhausted_returns_timed_out_with_last_tier_partial_output(self):
        def fake_popen(command, shell, stdin, stdout, stderr, start_new_session):
            stdout.write(b"partial from last tier")
            return self._FakeProc(returncode_after_polls=10_000)

        times = iter([0.0, 15.0, 15.0, 25.0])
        result = dispatch.dispatch_with_polling(
            "never-finishes", "p", timeout_tiers=[10, 10], poll_interval=50,
            popen_fn=fake_popen, time_fn=lambda: next(times), sleep_fn=lambda s: None,
            kill_fn=self._fake_kill, print_fn=lambda *a: None)

        self.assertTrue(result["timed_out"])
        self.assertEqual(result["tiers_tried"], 2)
        self.assertEqual(result["stdout"], "partial from last tier")

    def test_progress_lines_report_byte_growth_between_polls(self):
        printed = []

        def fake_popen(command, shell, stdin, stdout, stderr, start_new_session):
            stdout.write(b"x" * 100)
            return self._FakeProc(returncode_after_polls=10_000)

        # Two poll checks before the tier's own timeout hits.
        times = iter([0.0, 5.0, 8.0, 12.0])
        dispatch.dispatch_with_polling(
            "cmd", "p", timeout_tiers=[10], poll_interval=3,
            popen_fn=fake_popen, time_fn=lambda: next(times), sleep_fn=lambda s: None,
            kill_fn=self._fake_kill, print_fn=lambda *a: printed.append(" ".join(map(str, a))))

        self.assertTrue(any("100 bytes" in line or "total 100" in line for line in printed))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest tests.test_ai_kit_spec.TestDispatchWithPolling -v`
Expected: FAIL with `AttributeError: module 'ai_kit_spec.dispatch' has no attribute 'dispatch_with_polling'`

- [ ] **Step 3: Implement `dispatch_with_polling`**

Add to `skills/ai-kit-spec-review/ai_kit_spec/dispatch.py` (add `import shutil` and
`import tempfile` to the existing import block at the top of the file, alongside the existing
`import os`/`import signal`/etc.):

```python
def dispatch_with_polling(command: str, prompt: str, timeout_tiers: list[int],
                           poll_interval: int = 150, popen_fn=subprocess.Popen,
                           time_fn=time.time, sleep_fn=time.sleep,
                           kill_fn=_default_kill_process_group, print_fn=_default_print_fn,
                           tmp_dir_fn=tempfile.mkdtemp, rmtree_fn=shutil.rmtree) -> dict:
    """Escalates across `timeout_tiers` (seconds, in order), each tier a FRESH process -- a
    killed CLI cannot resume its own reasoning state, so a tier restart is a real, accepted
    cost (design spec §4/§14), not an oversight. `stdout`/`stderr` are redirected to real
    files (never PIPE): this removes the deadlock condition `dispatch_with_heartbeat`'s own
    docstring documents (stdin fill racing an undrained stdout pipe) because nothing routes
    through our own process's pipes here, so `prompt` is delivered via a plain file handed to
    the child as its own stdin (`stdin=<open file>`) -- no manual write, no blocking-write risk
    on our side at all. The same file-backed stdout also makes real interim progress
    inspectable while the subprocess is alive: `print_fn` gets a one-line size-delta report
    every `poll_interval` seconds. Informational ONLY -- never aborts an attempt early, even at
    zero growth (design decision: a false "stalled" verdict on a genuinely slow-but-working
    model is worse than the wasted wait)."""
    tmp_dir = tmp_dir_fn(prefix="ai-kit-spec-dispatch-")
    try:
        prompt_path = os.path.join(tmp_dir, "prompt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        stdout_path = os.path.join(tmp_dir, "stdout")
        stderr_path = os.path.join(tmp_dir, "stderr")
        last_result = None
        for tier_index, tier_timeout in enumerate(timeout_tiers, start=1):
            start = time_fn()
            last_size = 0
            with open(prompt_path, "rb") as in_f, \
                 open(stdout_path, "wb") as out_f, \
                 open(stderr_path, "wb") as err_f:
                proc = popen_fn(command, shell=True, stdin=in_f, stdout=out_f, stderr=err_f,
                                 start_new_session=True)
                timed_out = False
                while proc.poll() is None:
                    elapsed = time_fn() - start
                    remaining = tier_timeout - elapsed
                    if remaining <= 0:
                        kill_fn(proc)
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            pass
                        timed_out = True
                        break
                    sleep_fn(min(poll_interval, remaining))
                    size = os.path.getsize(stdout_path) if os.path.exists(stdout_path) else 0
                    delta = size - last_size
                    ts_elapsed = int(time_fn() - start)
                    if delta:
                        print_fn(f"tier {tier_index} ({tier_timeout}s): +{delta} bytes "
                                 f"since last check (total {size}, {ts_elapsed}s elapsed)")
                    else:
                        print_fn(f"tier {tier_index} ({tier_timeout}s): no growth "
                                 f"({ts_elapsed}s elapsed)")
                    last_size = size
            with open(stdout_path, "rb") as f:
                stdout = f.read().decode("utf-8", errors="replace")
            with open(stderr_path, "rb") as f:
                stderr = f.read().decode("utf-8", errors="replace")
            last_result = {"returncode": proc.returncode, "stdout": stdout, "stderr": stderr,
                            "timed_out": timed_out, "tiers_tried": tier_index,
                            "final_timeout": tier_timeout}
            if not timed_out:
                return last_result
            if tier_index < len(timeout_tiers):
                print_fn(f"tier {tier_index} ({tier_timeout}s) timed out -- escalating to "
                         f"tier {tier_index + 1} ({timeout_tiers[tier_index]}s)")
        return last_result
    finally:
        rmtree_fn(tmp_dir, ignore_errors=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest tests.test_ai_kit_spec.TestDispatchWithPolling -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd /var/home/bazzite/git/personal/ai-kit
git add skills/ai-kit-spec-review/ai_kit_spec/dispatch.py tests/test_ai_kit_spec.py
git commit -m "feat(ai-kit-spec-review): add dispatch_with_polling tiered-timeout engine"
```

---

### Task 2: Shared tooling-guidance reference file

**Files:**
- Create: `skills/ai-kit-spec-review/references/tooling-guidance.md`
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py`
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py`
- Modify: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `resolve_shared_tooling_reference_path() -> str` and
  `build_tooling_guidance(cli, tool_availability, agents_tooling_path, codegraph_registered,
  shared_reference_path=None) -> str` (extended signature, backward-compatible — existing
  4-positional-arg callers keep working since the new parameter defaults to `None`) — used by
  Task 3's `dispatch_reviewer` and Task 8's `ai-kit-spec-review/SKILL.md`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ai_kit_spec.py` (new test methods in the existing `TestToolingGuidance`
class if one exists — check the file first via `grep -n "class TestToolingGuidance" tests/
test_ai_kit_spec.py`; if it doesn't exist, add a new class near the other tooling-guidance
tests):

```python
    def test_resolve_shared_tooling_reference_path_points_to_a_real_file(self):
        path = tooling_guidance.resolve_shared_tooling_reference_path()
        self.assertTrue(path.endswith(
            os.path.join("references", "tooling-guidance.md")))
        self.assertTrue(os.path.isfile(path))

    def test_build_tooling_guidance_always_includes_shared_reference_when_given(self):
        guidance = tooling_guidance.build_tooling_guidance(
            "grok", {}, None, False, shared_reference_path="/fake/tooling-guidance.md")
        self.assertIn("Read /fake/tooling-guidance.md", guidance)

    def test_build_tooling_guidance_omits_shared_reference_line_when_not_given(self):
        guidance = tooling_guidance.build_tooling_guidance("grok", {}, None, False)
        self.assertNotIn("tooling-guidance.md", guidance)
```

Ensure `tooling_guidance` and `os` are imported at the top of `tests/test_ai_kit_spec.py`
(`from ai_kit_spec import tooling_guidance` or equivalent — check the existing import style in
the file via `grep -n "^import\|^from" tests/test_ai_kit_spec.py | head -20` and match it).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest tests.test_ai_kit_spec -k tooling_reference -v`
Expected: FAIL with `AttributeError: module 'ai_kit_spec.tooling_guidance' has no attribute 'resolve_shared_tooling_reference_path'`

- [ ] **Step 3: Create the reference file**

Create `skills/ai-kit-spec-review/references/tooling-guidance.md`:

```markdown
# Tool Preferences

Prefer these modern replacements when the task involves searching, listing, viewing, or
editing files. Each is confirmed installed only when this dispatch's own tool-availability
check reports it present — never assume one is available just because it's listed here.

| Instead of | Prefer | Why |
|---|---|---|
| `grep` (recursive) | `rg` | Faster, respects `.gitignore` by default, better defaults for code search. |
| `find` | `fd` | Simpler syntax, faster, respects `.gitignore` by default. |
| `cat` (for viewing code) | `bat` | Syntax highlighting, line numbers, git-diff markers in the gutter. |
| `ls` | `eza` | Clearer, more readable directory listings. |
| `sed` (in-place edits) | `sd` | Simpler find/replace syntax, fewer regex-escaping surprises. |
| `diff` | `delta` or `difftastic` | Readable, syntax-aware diffs. |

## codegraph_explore (MCP)

When `codegraph_explore` is available and confirmed registered for the CLI running this
dispatch (never assumed — confirmed via a live per-client health check), prefer it over broad
file reads for architecture, cross-reference, or "where is X used" questions. Fall back to
`rg`/`fd`/direct reads when a specific, narrow lookup is simpler than a graph query.

Use whichever of the above tools are genuinely confirmed present and useful for the task at
hand — this is a preference list, not a requirement to use every tool listed.
```

- [ ] **Step 4: Add the resolver and extend `build_tooling_guidance`**

Modify `skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py` — add `import os` at the top
(the file currently has no imports at all), then add the resolver function and update the
existing `build_tooling_guidance` signature:

```python
import os


def resolve_shared_tooling_reference_path() -> str | None:
    """Always resolves relative to this installed package -- ai-kit-spec-review/references/
    tooling-guidance.md ships as this module's own sibling in every install shape (plugin,
    ~/.claude/skills, or a dev checkout), so no 3-candidate search is needed the way SKILL.md
    prose requires elsewhere in this repo (that pattern exists only because prose has no
    __file__ equivalent). Returns None if the file doesn't actually exist on disk (a corrupted/
    partial install) -- same never-guess-if-uncertain convention resolve_agents_tooling_path
    already follows; build_tooling_guidance's `if shared_reference_path:` check already omits
    the line cleanly for a None value, no separate handling needed there."""
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(package_dir, "references", "tooling-guidance.md")
    return candidate if os.path.isfile(candidate) else None


def build_tooling_guidance(cli: str, tool_availability: dict, agents_tooling_path,
                            codegraph_registered: bool, shared_reference_path=None) -> str:
    lines = []
    if shared_reference_path:
        lines.append(
            f"Read {shared_reference_path} for this repo's confirmed tool preferences."
        )
    if agents_tooling_path:
        lines.append(f"Read {agents_tooling_path} for confirmed tool preferences on this machine.")
    # Hard-omit grok regardless of what the caller passes for codegraph_registered -- confirmed
    # unsupported (design spec, Global Constraints above). Defense in depth: check_codegraph_
    # mcp_healthy("grok") already always returns False, but this function must never emit
    # codegraph guidance for grok even if a caller passes an inconsistent/stale True by mistake.
    if cli != "grok" and codegraph_registered and tool_availability.get("codegraph"):
        lines.append(
            "codegraph_explore (MCP) is available and confirmed registered for this CLI -- "
            "prefer it over broad file reads for architecture/cross-reference questions, "
            "unless another tool is genuinely simpler for a specific lookup."
        )
    return "\n".join(lines)
```

(This replaces the existing `build_tooling_guidance` definition in place — same body except the
new `shared_reference_path=None` parameter and the new `if shared_reference_path:` block at the
top.)

- [ ] **Step 5: Wire the new parameter into both existing execute-path call sites**

In `skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py`, find the existing call:

```python
    tool_guidance = build_tooling_guidance_fn(cli, tool_availability or {}, agents_tooling_path,
                                               codegraph_registered)
```

Replace it with:

```python
    tool_guidance = build_tooling_guidance_fn(
        cli, tool_availability or {}, agents_tooling_path, codegraph_registered,
        shared_reference_path=resolve_shared_tooling_reference_path())
```

And add `resolve_shared_tooling_reference_path` to the existing
`from ai_kit_spec.tooling_guidance import build_tooling_guidance` import line at the top of the
file (change it to `from ai_kit_spec.tooling_guidance import (build_tooling_guidance,
resolve_shared_tooling_reference_path)`).

In `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py`, find the existing call (inside the
`prepare-tooling` handler):

```python
        guidance = build_tooling_guidance(args.cli, tool_availability, agents_tooling_path,
                                           codegraph_registered)
```

Replace it with:

```python
        guidance = build_tooling_guidance(
            args.cli, tool_availability, agents_tooling_path, codegraph_registered,
            shared_reference_path=resolve_shared_tooling_reference_path())
```

And change the existing `from ai_kit_spec.tooling_guidance import build_tooling_guidance`
import line to `from ai_kit_spec.tooling_guidance import (build_tooling_guidance,
resolve_shared_tooling_reference_path)`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest tests.test_ai_kit_spec tests.test_ai_kit_spec_gsd -v 2>&1 | tail -30`
Expected: PASS, all tests including the 3 new ones and every pre-existing
`build_tooling_guidance`/`prepare-tooling`/`dispatch_execute` test (the new parameter is
additive and optional, so no existing test should need changes).

- [ ] **Step 7: Commit**

```bash
cd /var/home/bazzite/git/personal/ai-kit
git add skills/ai-kit-spec-review/references/tooling-guidance.md \
        skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py \
        skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py \
        skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py \
        tests/test_ai_kit_spec.py
git commit -m "feat(ai-kit-spec-review): add shared, repo-owned tooling-guidance reference"
```

---

### Task 3: `dispatch_reviewer` + `dispatch-reviewer` CLI subcommand

**Files:**
- Create: `skills/ai-kit-spec-review/ai_kit_spec/reviewer_dispatch.py`
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/cli.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `dispatch_with_polling` (Task 1), `build_tooling_guidance` +
  `resolve_shared_tooling_reference_path` (Task 2).
- Produces: `dispatch_reviewer(command: str, prompt: str, timeout_tiers: list[int], cli:
  str | None, tool_availability: dict, agents_tooling_path, codegraph_registered: bool,
  dispatch_fn=dispatch_with_polling, build_tooling_guidance_fn=build_tooling_guidance,
  resolve_shared_reference_fn=resolve_shared_tooling_reference_path) -> dict` and the
  `dispatch-reviewer` CLI subcommand — used by Task 8's `ai-kit-spec-review/SKILL.md` Step 1.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ai_kit_spec.py`:

```python
class TestDispatchReviewer(unittest.TestCase):
    def test_composes_tooling_guidance_and_dispatches_via_the_polling_engine(self):
        captured = {}

        def fake_dispatch(command, prompt, timeout_tiers, poll_interval=150, **kw):
            captured["command"] = command
            captured["prompt"] = prompt
            captured["timeout_tiers"] = timeout_tiers
            return {"returncode": 0, "stdout": "## Review\n### Status: Approved\n",
                    "stderr": "", "timed_out": False, "tiers_tried": 1, "final_timeout": 600}

        result = reviewer_dispatch.dispatch_reviewer(
            "codex exec --sandbox read-only -m gpt-5.6-sol", "Read the checklist and review...",
            timeout_tiers=[600, 1200], cli="codex", tool_availability={"rg": True},
            agents_tooling_path=None, codegraph_registered=True,
            dispatch_fn=fake_dispatch,
            build_tooling_guidance_fn=lambda *a, **kw: "TOOLING GUIDANCE HERE",
            resolve_shared_reference_fn=lambda: "/fake/tooling-guidance.md")

        self.assertEqual(captured["timeout_tiers"], [600, 1200])
        self.assertIn("TOOLING GUIDANCE HERE", captured["prompt"])
        self.assertIn("Read the checklist and review...", captured["prompt"])
        self.assertEqual(result["stdout"], "## Review\n### Status: Approved\n")

    def test_dispatch_reviewer_cli_subcommand_stdout_only_prints_raw_report(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("review this plan")

            def fake_dispatch_reviewer(*a, **kw):
                return {"returncode": 0, "stdout": "### Status: Approved\n", "stderr": "",
                        "timed_out": False, "tiers_tried": 1, "final_timeout": 600}

            with redirect_stdout(io.StringIO()) as out:
                code = rs.main(
                    ["dispatch-reviewer", "--command", "grok -p {prompt} -m grok-4.6",
                     "--prompt-file", prompt_path, "--timeout-tiers", "600,1200",
                     "--cli", "grok", "--stdout-only"],
                    dispatch_reviewer_fn=fake_dispatch_reviewer)
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "### Status: Approved\n")
```

Add `import tempfile` near the top of `tests/test_ai_kit_spec.py` if not already present (Task
1 may have already added it), and add `from ai_kit_spec import reviewer_dispatch` to the
existing import block.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest tests.test_ai_kit_spec.TestDispatchReviewer -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ai_kit_spec.reviewer_dispatch'`

- [ ] **Step 3: Create `reviewer_dispatch.py`**

Create `skills/ai-kit-spec-review/ai_kit_spec/reviewer_dispatch.py`:

```python
"""Direct dispatch for ai-kit-spec-review's own external-CLI reviewer entries -- wraps
dispatch.dispatch_with_polling with the review-specific prompt composition (tooling guidance
only; no model-selection-override/incremental-progress/failure-reporting reinforcement, since
a reviewer's own checklist skill (ai-kit-spec-review-checklist) already owns that contract).
Read-only by construction: the `command` this module runs is always a review-mode command
string built by commands.build_reviewer_command, never an execute-mode one -- this module
itself has no read/write distinction to enforce, that lives entirely in which builder produced
`command` before it ever reaches here."""
from ai_kit_spec.dispatch import dispatch_with_polling
from ai_kit_spec.tooling_guidance import build_tooling_guidance, resolve_shared_tooling_reference_path


def dispatch_reviewer(command: str, prompt: str, timeout_tiers: list[int], cli: str | None,
                       tool_availability: dict, agents_tooling_path, codegraph_registered: bool,
                       dispatch_fn=dispatch_with_polling,
                       build_tooling_guidance_fn=build_tooling_guidance,
                       resolve_shared_reference_fn=resolve_shared_tooling_reference_path) -> dict:
    """Composes `command`'s full prompt (tooling guidance + the caller's already-built reviewer
    prompt, see ai-kit-spec-review/SKILL.md's Step 1 template) and runs it via
    `dispatch_with_polling`. `cli` may be None for a hand-written/unknown-CLI reviewer entry
    (build_tooling_guidance's own `cli != "grok"` check only ever special-cases the literal
    string "grok", so None is safe to pass through unchanged)."""
    tooling_guidance = build_tooling_guidance_fn(
        cli, tool_availability or {}, agents_tooling_path, codegraph_registered,
        shared_reference_path=resolve_shared_reference_fn())
    full_prompt = (tooling_guidance + "\n\n" + prompt) if tooling_guidance else prompt
    return dispatch_fn(command, full_prompt, timeout_tiers)
```

- [ ] **Step 4: Add the `dispatch-reviewer` CLI subcommand**

Modify `skills/ai-kit-spec-review/ai_kit_spec/cli.py`. Add the import (alongside the existing
`from ai_kit_spec.execute_dispatch import dispatch_execute` line):

```python
from ai_kit_spec.reviewer_dispatch import dispatch_reviewer
```

Add `dispatch_reviewer_fn=dispatch_reviewer` to `main`'s own signature (alongside the existing
`dispatch_execute_fn=dispatch_execute` parameter):

```python
def main(argv: list, which_fn=shutil.which, run_fn=subprocess.run,
         dispatch_execute_fn=dispatch_execute, dispatch_reviewer_fn=dispatch_reviewer) -> int:
```

Add the argparse subparser (immediately after the existing `p_dispatch = sub.add_parser(
"dispatch-execute")` block, before `p_check = sub.add_parser("check-reviewer")`):

```python
    p_dispatch_reviewer = sub.add_parser("dispatch-reviewer")
    p_dispatch_reviewer.add_argument(
        "--command", required=True,
        help="the fully-rendered reviewer command string, e.g. render-command's own stdout")
    p_dispatch_reviewer.add_argument("--prompt-file", required=True,
                                      help="pass '-' to read the prompt from this process's own stdin")
    p_dispatch_reviewer.add_argument(
        "--timeout-tiers", required=True,
        help="comma-separated seconds, e.g. '600,1200,1800' -- escalation order")
    p_dispatch_reviewer.add_argument("--cli", default=None,
                                      help="omit for a native/unknown-CLI reviewer entry")
    p_dispatch_reviewer.add_argument("--tool-availability-json", default=None)
    p_dispatch_reviewer.add_argument("--agents-tooling-path", default=None)
    p_dispatch_reviewer.add_argument("--codegraph-registered", action="store_true")
    p_dispatch_reviewer.add_argument(
        "--stdout-only", action="store_true",
        help="print ONLY the dispatched reviewer's own stdout and exit with its real "
             "returncode, same contract as dispatch-execute's own --stdout-only")
```

Add the handler (immediately after the existing `if args.command == "dispatch-execute":` block,
before `if args.command == "check-reviewer":`):

```python
    if args.command == "dispatch-reviewer":
        if args.prompt_file == "-":
            prompt = sys.stdin.read()
        else:
            with open(args.prompt_file, encoding="utf-8") as f:
                prompt = f.read()
        timeout_tiers = [int(t) for t in args.timeout_tiers.split(",")]
        tool_availability = (json.loads(args.tool_availability_json)
                              if args.tool_availability_json else {})
        result = dispatch_reviewer_fn(
            args.command, prompt, timeout_tiers, args.cli, tool_availability,
            args.agents_tooling_path, args.codegraph_registered)
        if args.stdout_only:
            sys.stdout.write(result["stdout"])
            return result["returncode"] if result["returncode"] is not None else 1
        print(json.dumps(result))
        return 0
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest tests.test_ai_kit_spec -v 2>&1 | tail -30`
Expected: PASS, all tests.

- [ ] **Step 6: Commit**

```bash
cd /var/home/bazzite/git/personal/ai-kit
git add skills/ai-kit-spec-review/ai_kit_spec/reviewer_dispatch.py \
        skills/ai-kit-spec-review/ai_kit_spec/cli.py tests/test_ai_kit_spec.py
git commit -m "feat(ai-kit-spec-review): add dispatch-reviewer CLI subcommand"
```

---

### Task 4: `policy.timeout_tiers` config schema + resolver

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/config_io.py`
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/cli.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `cfg_resolve` (existing, `config_io.py`).
- Produces: `DEFAULT_POLICY` (extended with `"timeout_tiers": [600, 1200, 1800]`),
  `resolve_timeout_tiers(reviewer_entry: dict, policy: dict) -> list[int]`, and the
  `resolve-timeout-tiers` CLI subcommand (the orchestrator prose in Task 8 has no way to call a
  raw Python function directly — it needs a subcommand, same as every other resolution step) —
  used by Task 8's `ai-kit-spec-review/SKILL.md` Step 2.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ai_kit_spec.py`:

```python
class TestTimeoutTiers(unittest.TestCase):
    def test_default_policy_includes_the_10_20_30_minute_default(self):
        self.assertEqual(config_io.DEFAULT_POLICY["timeout_tiers"], [600, 1200, 1800])

    def test_cfg_resolve_surfaces_the_default_when_config_omits_it(self):
        def fake_load(path):
            return {}
        with unittest.mock.patch.object(config_io, "cfg_load_toml", fake_load):
            resolved = config_io.cfg_resolve("/nonexistent", {})
        self.assertEqual(resolved["policy"]["timeout_tiers"], [600, 1200, 1800])

    def test_resolve_timeout_tiers_uses_reviewer_override_when_present(self):
        reviewer = {"key": "codex-sol", "extra": {"timeout_tiers": [900, 1800]}}
        policy = {"timeout_tiers": [600, 1200, 1800]}
        self.assertEqual(config_io.resolve_timeout_tiers(reviewer, policy), [900, 1800])

    def test_resolve_timeout_tiers_falls_back_to_policy_default(self):
        reviewer = {"key": "grok-flagship", "extra": {}}
        policy = {"timeout_tiers": [600, 1200, 1800]}
        self.assertEqual(config_io.resolve_timeout_tiers(reviewer, policy), [600, 1200, 1800])

    def test_resolve_timeout_tiers_cli_subcommand_uses_reviewer_override(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".aikit"))
            with open(os.path.join(d, ".aikit", "review-spec.toml"), "w", encoding="utf-8") as f:
                f.write('[policy]\nmode = "single"\nladder = []\n')
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump([{"key": "codex-sol", "model": "gpt-5.6-sol", "vendor": "openai",
                            "cli": "codex", "command": "codex exec -m {model}",
                            "extra": {"timeout_tiers": [900, 1800]}}], f)
            with redirect_stdout(io.StringIO()) as out:
                code = rs.main(
                    ["resolve-timeout-tiers", "--cwd", d, "--reviewers-json", reviewers_path,
                     "--index", "0"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().strip(), "900,1800")

    def test_resolve_timeout_tiers_cli_subcommand_falls_back_to_policy_default(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            # No .aikit/review-spec.toml at all -- cfg_resolve degrades to DEFAULT_POLICY.
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump([{"key": "grok-flagship", "model": "grok-4.6", "vendor": "xai",
                            "cli": "grok", "command": "grok -p {prompt} -m {model}",
                            "extra": {}}], f)
            with redirect_stdout(io.StringIO()) as out:
                code = rs.main(
                    ["resolve-timeout-tiers", "--cwd", d, "--reviewers-json", reviewers_path,
                     "--index", "0"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().strip(), "600,1200,1800")
```

Add `import unittest.mock` near the top of `tests/test_ai_kit_spec.py` if not already imported
(check via `grep -n "^import unittest" tests/test_ai_kit_spec.py`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest tests.test_ai_kit_spec.TestTimeoutTiers -v`
Expected: FAIL — `KeyError: 'timeout_tiers'` on the first test.

- [ ] **Step 3: Implement**

Modify `skills/ai-kit-spec-review/ai_kit_spec/config_io.py`. Change:

```python
DEFAULT_POLICY = {"mode": "single", "ladder": []}
```

to:

```python
DEFAULT_POLICY = {"mode": "single", "ladder": [], "timeout_tiers": [600, 1200, 1800]}
```

Add near the bottom of the file (after `cfg_write_toml`):

```python
def resolve_timeout_tiers(reviewer_entry: dict, policy: dict) -> list[int]:
    """A reviewer's own `extra.timeout_tiers` (set via review-spec.toml, e.g. a known-slow
    effort=high CLI/model combination) overrides the policy-wide default for that entry only.
    `policy` is expected to already carry a real `timeout_tiers` list (DEFAULT_POLICY guarantees
    this via cfg_resolve's own merge) -- this function never invents its own fallback constant,
    single source of truth stays DEFAULT_POLICY."""
    override = reviewer_entry.get("extra", {}).get("timeout_tiers")
    return override if override else policy["timeout_tiers"]
```

- [ ] **Step 4: Add the `resolve-timeout-tiers` CLI subcommand**

The orchestrator's Step 1 prose (Task 8) has no way to call a raw Python function — it needs a
subcommand, same as every other resolution step in this design. Modify
`skills/ai-kit-spec-review/ai_kit_spec/cli.py`. Add `resolve_timeout_tiers` to the existing
`from ai_kit_spec.config_io import cfg_render_toml, cfg_resolve, cfg_write_toml` import line
(change it to `from ai_kit_spec.config_io import (cfg_render_toml, cfg_resolve, cfg_write_toml,
resolve_timeout_tiers)`).

Add the subparser (after the existing `p_render = sub.add_parser("render-command")` block, since
this shares `--reviewers-json`/`--index` with it):

```python
    p_tiers = sub.add_parser("resolve-timeout-tiers")
    p_tiers.add_argument("--cwd", required=True)
    p_tiers.add_argument("--reviewers-json", required=True,
                          help="path to resolve-reviewers' saved JSON array output")
    p_tiers.add_argument("--index", type=int, required=True)
```

Add the handler (after the existing `if args.command == "render-command":` block):

```python
    if args.command == "resolve-timeout-tiers":
        with open(args.reviewers_json, encoding="utf-8") as f:
            reviewers = json.load(f)
        r = reviewers[args.index]
        config = cfg_resolve(args.cwd, dict(os.environ))
        tiers = resolve_timeout_tiers(r, config.get("policy", {}))
        print(",".join(str(t) for t in tiers))
        return 0
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest tests.test_ai_kit_spec -v 2>&1 | tail -30`
Expected: PASS, all tests (including every pre-existing `cfg_resolve`/`DEFAULT_POLICY` test —
the new key is additive, no existing assertion should reference an exhaustive policy dict
literal that would now mismatch; if one does, update that literal to include the new key rather
than changing the default).

- [ ] **Step 7: Commit**

```bash
cd /var/home/bazzite/git/personal/ai-kit
git add skills/ai-kit-spec-review/ai_kit_spec/config_io.py skills/ai-kit-spec-review/ai_kit_spec/cli.py \
        tests/test_ai_kit_spec.py
git commit -m "feat(ai-kit-spec-review): add policy.timeout_tiers config schema + resolver subcommand"
```

---

### Task 5: Codegraph-alternative-CLI matcher

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/detection.py`
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/cli.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `_SUPPORTED_CODEGRAPH_CLIENTS` (existing, same file).
- Produces: `find_codegraph_alternative(cli: str, model: str, runtimes_snapshot: dict) -> str |
  None` and the `check-codegraph-alternative` CLI subcommand — used by Task 7's
  `ai-kit-spec-config/SKILL.md` Step 2.2-2.4.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ai_kit_spec.py`:

```python
class TestFindCodegraphAlternative(unittest.TestCase):
    def test_finds_grok_model_reachable_via_cursor_agent(self):
        snapshot = {"clis": {
            "cursor-agent": {"installed": True,
                              "models": ["cursor-grok-4.6-high", "claude-opus-5-high"]},
            "opencode": {"installed": True, "models": ["opencode-go/qwen3.8-max"]},
        }}
        result = detection.find_codegraph_alternative("grok", "grok-4.6", snapshot)
        self.assertEqual(result, "cursor-agent")

    def test_returns_none_when_cli_already_supports_codegraph(self):
        snapshot = {"clis": {"cursor-agent": {"installed": True, "models": ["cursor-grok-4.6"]}}}
        result = detection.find_codegraph_alternative("cursor-agent", "cursor-grok-4.6", snapshot)
        self.assertIsNone(result)

    def test_returns_none_when_no_matching_model_found_anywhere(self):
        snapshot = {"clis": {
            "cursor-agent": {"installed": True, "models": ["claude-opus-5-high"]},
            "opencode": {"installed": True, "models": ["opencode-go/qwen3.8-max"]},
        }}
        result = detection.find_codegraph_alternative("grok", "grok-4.6", snapshot)
        self.assertIsNone(result)

    def test_skips_a_codegraph_capable_cli_that_is_not_installed(self):
        snapshot = {"clis": {"cursor-agent": {"installed": False}}}
        result = detection.find_codegraph_alternative("grok", "grok-4.6", snapshot)
        self.assertIsNone(result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest tests.test_ai_kit_spec.TestFindCodegraphAlternative -v`
Expected: FAIL with `AttributeError: module 'ai_kit_spec.detection' has no attribute
'find_codegraph_alternative'`

- [ ] **Step 3: Implement**

Add to `skills/ai-kit-spec-review/ai_kit_spec/detection.py` (after
`check_codegraph_mcp_healthy`, near the end of the file):

```python
# The two multi-provider CLIs with their own per-model catalog (KNOWN_CLIS' other three --
# claude, codex, grok -- have no "models" list in build_runtimes_snapshot's own output at all,
# so they can never be a *target* alternative here; only a *source* cli being checked).
_CODEGRAPH_CAPABLE_MULTI_PROVIDER_CLIS = ("cursor-agent", "opencode")


def find_codegraph_alternative(cli: str, model: str, runtimes_snapshot: dict) -> str | None:
    """Best-effort only (design spec §8, §14): when `cli` has no codegraph/MCP support (not in
    _SUPPORTED_CODEGRAPH_CLIENTS) but a substring match suggests the SAME base model is also
    reachable through a codegraph-capable CLI's own model catalog, return that CLI's name --
    informational only, never a hard filter. Model-id naming conventions differ across CLIs
    (e.g. "grok-4.6" vs. "cursor-grok-4.6-high") so this is a substring heuristic, not a
    guarantee; a missed match degrades silently to None, never a false claim."""
    if cli in _SUPPORTED_CODEGRAPH_CLIENTS:
        return None
    needle = model.lower()
    for candidate_cli in _CODEGRAPH_CAPABLE_MULTI_PROVIDER_CLIS:
        entry = runtimes_snapshot.get("clis", {}).get(candidate_cli, {})
        if not entry.get("installed"):
            continue
        for candidate_model in entry.get("models", []):
            if needle in candidate_model.lower():
                return candidate_cli
    return None
```

- [ ] **Step 4: Add the `check-codegraph-alternative` CLI subcommand**

Modify `skills/ai-kit-spec-review/ai_kit_spec/cli.py`. Add `find_codegraph_alternative` to the
existing `from ai_kit_spec.detection import (...)` block. Add the subparser (after the existing
`p_group = sub.add_parser("group-models")` block):

```python
    p_alt = sub.add_parser("check-codegraph-alternative")
    p_alt.add_argument("--cli", required=True)
    p_alt.add_argument("--model", required=True)
    p_alt.add_argument("--runtimes-json", required=True)
```

Add the handler (after the existing `if args.command == "group-models":` block):

```python
    if args.command == "check-codegraph-alternative":
        snapshot = cache_read_json(args.runtimes_json) or {}
        alternative = find_codegraph_alternative(args.cli, args.model, snapshot)
        print(json.dumps({"alternative_cli": alternative}))
        return 0
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest tests.test_ai_kit_spec -v 2>&1 | tail -30`
Expected: PASS, all tests.

- [ ] **Step 6: Commit**

```bash
cd /var/home/bazzite/git/personal/ai-kit
git add skills/ai-kit-spec-review/ai_kit_spec/detection.py \
        skills/ai-kit-spec-review/ai_kit_spec/cli.py tests/test_ai_kit_spec.py
git commit -m "feat(ai-kit-spec-review): add codegraph-alternative-CLI matcher"
```

---

### Task 6: `ai-kit-spec-review-checklist` — legacy-tool-usage rule

**Files:**
- Modify: `skills/ai-kit-spec-review-checklist/SKILL.md`

**Interfaces:**
- Consumes: `tool_availability` (passed in by the orchestrator, see Task 8) and the shared
  `tooling-guidance.md` reference (Task 2).
- Produces: an updated checklist prose the reviewer subagent/CLI reads — no new function
  interfaces (this is a prose-only skill).

- [ ] **Step 1: Add the legacy-tool-usage rule to the Plan checklist**

In `skills/ai-kit-spec-review-checklist/SKILL.md`, find the `## Plan checklist` section's
`**HIGH:**` bullet list, and add a new bullet after the existing HIGH list (before `**MEDIUM:**`):

```markdown
**MEDIUM (legacy-tool usage):** the plan references a legacy tool by literal command invocation
(`grep`, `find`, `cat` for search/listing, `sed`) where `tool_availability` (given to you by the
orchestrator) confirms the modern equivalent (`rg`/`fd`/`bat`/`sd`) is installed on the target
machine. Name the specific line and the exact modern replacement. Never flag this when the
modern equivalent's presence is NOT confirmed in `tool_availability` — an unconfirmed absence is
not evidence of absence.
```

- [ ] **Step 2: Add a "Tool preference during review" instruction**

Add a new small section immediately after the existing `## Operating under a turn/token budget
(external CLI dispatch)` section (before `## Output`):

```markdown
## Tool preference during review

When the orchestrator gives you a `SHARED_TOOLING_PATH`, `Read` it once before your first
search/listing/edit-adjacent tool call — it names this repo's confirmed modern tool
replacements (`rg`/`fd`/`bat`/`sd`/`eza`) and, separately, when `codegraph_explore` is preferred
over broad reads. Apply it to your OWN grounding work during this review, the same way you
already apply `FRAMEWORK_PROFILE_PATH` — this is a `Read`-and-apply reference, never inlined
prose repeated here.
```

- [ ] **Step 3: Verify the diff reads correctly**

Run: `git -C /var/home/bazzite/git/personal/ai-kit diff skills/ai-kit-spec-review-checklist/SKILL.md`
Expected: the two additions above, cleanly inserted at the described locations, no other
unintended changes.

- [ ] **Step 4: Commit**

```bash
cd /var/home/bazzite/git/personal/ai-kit
git add skills/ai-kit-spec-review-checklist/SKILL.md
git commit -m "docs(ai-kit-spec-review-checklist): add legacy-tool-usage rule + tool preference"
```

---

### Task 7: `ai-kit-spec-config` — codegraph-aware CLI preference + timeout-tiers ask

**Files:**
- Modify: `skills/ai-kit-spec-config/SKILL.md`

**Interfaces:**
- Consumes: `check-codegraph-alternative` CLI subcommand (Task 5), `policy.timeout_tiers`
  schema (Task 4).
- Produces: an updated wizard flow — no new function interfaces (prose-only skill).

- [ ] **Step 1: Add the codegraph-alternative note to Step 2.2**

In `skills/ai-kit-spec-config/SKILL.md`, find `#### Step 2.2 — Pick which CLIs and models to
register`, and add this paragraph immediately after its existing final paragraph (the one about
researching unfamiliar model families):

```markdown
**Before finalizing a CLI outside codegraph support (today: `grok`), check for a
codegraph-capable alternative.** For each model being registered on such a CLI, run:
```bash
python3 "$TOOLS_PY" check-codegraph-alternative --cli <id> --model <model-id> \
  --runtimes-json "$RUNTIMES_JSON"
```
When `alternative_cli` is non-null, tell the user in one line before they confirm: `"<model> is
also reachable via <alternative_cli>, which supports codegraph_explore (grok CLI does not) —
consider registering it through <alternative_cli> instead for grounding-heavy review/execute
work."` This is informational only (best-effort substring match, per `find_codegraph_
alternative`'s own docstring) — the user still makes the final call; never silently substitute
the CLI or drop the original option.
```

- [ ] **Step 2: Add the timeout-tiers ask to Step 2.8**

In `skills/ai-kit-spec-config/SKILL.md`, find `#### Step 2.8 — Set policy.mode, policy.ladder
order, and strategy`, and add this paragraph immediately before its existing final sentence
about the `strategy` question:

```markdown
**When at least one external-CLI reviewer is being registered** (native-only configs have no
subprocess to time out), also ask whether to customize `policy.timeout_tiers` from its default
`[600, 1200, 1800]` (10/20/30 minutes, escalated in order on a timeout) — most users should keep
the default; only ask this as an offer, don't require an answer. If the user wants a specific
reviewer entry to use different tiers (e.g. a known-slow `effort=high` combination), that goes
in that entry's own `extra.timeout_tiers` instead of the policy-wide default.
```

- [ ] **Step 3: Verify the diff reads correctly**

Run: `git -C /var/home/bazzite/git/personal/ai-kit diff skills/ai-kit-spec-config/SKILL.md`
Expected: the two additions above, cleanly inserted, no other unintended changes.

- [ ] **Step 4: Commit**

```bash
cd /var/home/bazzite/git/personal/ai-kit
git add skills/ai-kit-spec-config/SKILL.md
git commit -m "docs(ai-kit-spec-config): codegraph-aware CLI preference + timeout-tiers ask"
```

---

### Task 8: `ai-kit-spec-review/SKILL.md` — wire everything into Step 0.7 and Step 1

**Files:**
- Modify: `skills/ai-kit-spec-review/SKILL.md`

**Interfaces:**
- Consumes: `detect-tools` (existing subcommand), `dispatch-reviewer` (Task 3),
  `resolve-timeout-tiers` (Task 4), the shared `tooling-guidance.md` path (Task 2, resolved the
  same way `TOOLS_PY`/`CHECKLIST_SKILL_MD` already are — it's just `$REVIEW_SPEC_SKILL_DIR/
  references/tooling-guidance.md`, no subprocess needed).
- Produces: an updated orchestrator flow — no new function interfaces (prose-only skill).

- [ ] **Step 1: Add a `detect-tools` call to Step 0.7 point 0**

In `skills/ai-kit-spec-review/SKILL.md`'s Step 0.7 point 0, find the block that resolves
`TOOLS_PY`/`CHECKLIST_SKILL_MD`/`RUNTIMES_JSON`/`QUOTA_JSON` and prints them via the trailing
`printf`. Add one more line to that same `printf` call, and resolve `SHARED_TOOLING_PATH` the
same way (relative to `$REVIEW_SPEC_SKILL_DIR`, no subprocess needed since it's a fixed
sibling path):

```bash
   SHARED_TOOLING_PATH="$REVIEW_SPEC_SKILL_DIR/references/tooling-guidance.md"
   printf '%s\n' "$TOOLS_PY" "$CHECKLIST_SKILL_MD" "$RUNTIMES_JSON" "$QUOTA_JSON" "$SHARED_TOOLING_PATH"
```

(five lines now instead of four — update the surrounding prose that says "record ... from the
trailing printf's stdout (four lines, in that order)" to "five lines, in that order", and add
`SHARED_TOOLING_PATH` to the list of literal-path substitutions this step records.)

Immediately after this block (still within Step 0.7 point 0, before point 1's `mktemp -d`),
add a `detect-tools` call, cached the same way `ai-kit-spec-config`'s own Step 1 does it — but
since this orchestrator has no long-lived cache file for tool availability today, call it fresh
each run (cheap — a handful of `which` calls, no network, no TTL logic needed):

```bash
   TOOL_AVAILABILITY_JSON="$(python3 "$TOOLS_PY" detect-tools)"
```

Record `TOOL_AVAILABILITY_JSON` as this run's literal tool-availability JSON string, substituted
into every later `--tool-availability-json` reference.

- [ ] **Step 2: Rewrite Step 1's external-CLI dispatch block**

In `skills/ai-kit-spec-review/SKILL.md`'s Step 1, find the numbered list item 3 (the one that
executes the printed command via `Bash` with `nohup`-free direct redirection:
```bash
     <printed command> < "$RUN_TMP_DIR/iter<N>-<key>-prompt.txt" \
       > "$RUN_TMP_DIR/iter<N>-<key>.md"
```
). Replace that entire point 3 (and the surrounding prose explaining the stdin-redirect
rationale, which no longer applies once `dispatch-reviewer` owns process execution) with:

```markdown
  3. Resolve this entry's timeout tiers via the `resolve-timeout-tiers` subcommand (its own
     `extra.timeout_tiers` if `$RUN_TMP_DIR/reviewers.json`'s entry at this index has one, else
     the config's own `policy.timeout_tiers`):
     ```bash
     TIMEOUT_TIERS="$(python3 "$TOOLS_PY" resolve-timeout-tiers --cwd <CODEBASE_ROOT> \
       --reviewers-json "$RUN_TMP_DIR/reviewers.json" --index <0 for primary, 1 for secondary>)"
     ```
     Then dispatch via `dispatch-reviewer` instead of a hand-built `nohup`/redirect pipeline —
     one tested Python path builds and runs the command, never ad hoc shell assembled fresh per
     run:
     ```bash
     python3 "$TOOLS_PY" dispatch-reviewer \
       --command "<printed command from point 2>" \
       --prompt-file "$RUN_TMP_DIR/iter<N>-<key>-prompt.txt" \
       --timeout-tiers "$TIMEOUT_TIERS" \
       --cli <this entry's cli, or omit the flag entirely when cli is null> \
       --tool-availability-json "$TOOL_AVAILABILITY_JSON" \
       --codegraph-registered \
       --stdout-only \
       > "$RUN_TMP_DIR/iter<N>-<key>.md"
     ```
     Include `--codegraph-registered` only when
     `check_codegraph_mcp_healthy(<this entry's cli>)` is confirmed healthy for this CLI this
     run (same live-check the execute family already does — never assumed). This single call
     replaces the previous "write prompt file, render command, then separately execute it with
     stdin/stdout redirection" two-step: `dispatch-reviewer` reads the prompt file itself and
     composes the tooling-guidance prefix (`$SHARED_TOOLING_PATH`, resolved in Step 0.7)
     internally.
  ```

- [ ] **Step 3: Add the tooling-guidance line to the native reviewer prompt template**

In `skills/ai-kit-spec-review/SKILL.md`'s native reviewer prompt template (the one starting
`You are the reviewer.` used for `cli is null` entries), add one new line immediately after the
existing `Step 2:` block (before `Step 3:`):

```markdown
Step 2b: Read <SHARED_TOOLING_PATH> for this repo's confirmed tool preferences and apply them
during your own grounding work (prefer rg/fd/bat/sd/eza and codegraph_explore where confirmed
available, over broad reads/legacy tools).
```

- [ ] **Step 4: Verify the diff reads correctly**

Run: `git -C /var/home/bazzite/git/personal/ai-kit diff skills/ai-kit-spec-review/SKILL.md`
Expected: the three additions above, cleanly inserted, the old hand-rolled `nohup`/redirect
block fully removed from Step 1, no other unintended changes.

- [ ] **Step 5: Commit**

```bash
cd /var/home/bazzite/git/personal/ai-kit
git add skills/ai-kit-spec-review/SKILL.md
git commit -m "docs(ai-kit-spec-review): wire dispatch-reviewer + tooling-guidance into orchestrator"
```

---

### Task 9: Final validation — skill-judge + live smoke test

**Files:** none created/modified (validation only).

**Interfaces:**
- Consumes: everything from Tasks 1-8.
- Produces: nothing — this task's deliverable is a pass/fail validation report, folded into
  this plan's own completion criteria.

- [ ] **Step 1: Run the full test suite one more time**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest tests.test_ai_kit_spec tests.test_ai_kit_spec_gsd -v 2>&1 | tail -20`
Expected: PASS, every test (all of Tasks 1-5's new tests plus every pre-existing test
unaffected).

- [ ] **Step 2: Run `skill-judge` against each modified SKILL.md**

Invoke the `skill-judge` skill (via the `Skill` tool, `skill: "skill-judge"`) once per file,
passing the path as `args`:
- `skills/ai-kit-spec-review/SKILL.md`
- `skills/ai-kit-spec-review-checklist/SKILL.md`
- `skills/ai-kit-spec-config/SKILL.md`

Expected: no CRITICAL findings on any of the three (an existing skill being extended, not
authored fresh — the bar is "the new prose doesn't degrade the skill's own score," not a
from-scratch evaluation). Fix any CRITICAL finding inline before proceeding; note HIGH findings
for the user's own judgment call rather than blocking on them.

- [ ] **Step 3: Live smoke test — force at least one tier escalation for real**

Using a real installed CLI (whichever the machine has — `codex`, `grok`, `cursor-agent`, or
`opencode`), dispatch a deliberately slow real task through `dispatch-reviewer` with a
short first tier (e.g. `--timeout-tiers 15,300`) so the first tier is guaranteed to time out
and the second tier is guaranteed to actually run and complete. Example (adjust the CLI/model
to whatever is actually installed):

```bash
cd /var/home/bazzite/git/personal/ai-kit
echo "Take your time: write a 3-paragraph summary of this repo's README.md, reading it fully first." \
  > /tmp/claude-1000/smoke-prompt.txt
python3 skills/ai-kit-spec-review/ai-kit-spec.py dispatch-reviewer \
  --command "codex exec --sandbox read-only --skip-git-repo-check -m gpt-5.6-sol" \
  --prompt-file /tmp/claude-1000/smoke-prompt.txt \
  --timeout-tiers 15,300 --cli codex --stdout-only
```

Expected: stderr (visible in the terminal, not captured by `--stdout-only`) shows at least one
`"tier 1 (15s) timed out -- escalating to tier 2 (300s)"` line followed by real interim progress
lines during tier 2, and the final stdout is a real, complete response (not empty, not a stale
tier-1 fragment) — confirming a killed-and-restarted attempt produces a correct final result,
not silently corrupted or duplicated output.

- [ ] **Step 4: Report completion**

Summarize for the user: test suite status, skill-judge findings (if any), and the live
smoke-test transcript excerpt showing the tier escalation actually happened and produced a
correct final result.
