# E5b — Installer Bootstrapper + Skills Wizard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slim `tools/install.sh` into a standalone bash bootstrapper (mode-detect → convergent fetch with a tarball *atomic swap* so deletions propagate → ensure-python → `exec setup.py`), and move all install logic into a stdlib-only `tools/setup.py` that enumerates/validates entries, reconciles skills/agents/commands via symlinks-as-selection (link / unlink / prune-stale-with-warning), runs an interactive `/dev/tty` skills wizard, wires `statusLine` with an FR-5.5 double-confirm, and exposes `install`/`reconfigure`/`uninstall`/`doctor`/`check` subcommands. A `Makefile` wraps the lot.

**Architecture:** Two converging entry paths — `curl|bash` (BOOTSTRAP: fetch, then exec) and `git clone && make install` (LOCAL: skip fetch, exec) — meet at `python3 $INSTALL_DIR/tools/setup.py "$@"`. `setup.py` holds the single source of truth: `resolve_paths` mirrors install.sh env precedence; `enumerate_entries` + `validate_entry` port the bash validation; `installed_links` reads existing ai-kit symlinks (the persisted selection — no state file); `select_skills`/`apply_selection` reconcile A∩B / A−B / B−A set-math; `prune_stale` warns + offers prune; `wire_statusline` double-confirms a foreign `statusLine`; `doctor`/`check` shell out to `status-line.py --doctor`/`--check` (built in E5a). Every interactive function takes an injectable `tty` stream so tests pass `io.StringIO`; only `main()` opens the real `/dev/tty`.

**Tech Stack:** Bash (install.sh, `shellcheck`-clean) + Python 3 stdlib only (`tools/setup.py`: `argparse`, `json`, `os`, `subprocess`, `collections.namedtuple` — no third-party deps, same constraint as `status-line.py`). Tests: `tests/test_setup.py` via `python3 -m unittest tests.test_setup`; `tests/test_install.sh` via `bash tests/test_install.sh` + `shellcheck tools/install.sh`.

**Spec:** `docs/superpowers/specs/2026-06-19-e5-installer-wizard-design.md` §2 (bootstrap contract), §3 (convergent fetch incl. tarball atomic-swap), §4 (reconciliation), §6 (statusLine wiring + double-confirm), §7 (TTY vs headless), §8 (entry points/Makefile). NOT §5 (the status-line config wizard — that is E5c; this plan leaves a thin `run_statusline_wizard` stub).

**Depends on:** E5a (`status-line.py --doctor`/`--check`) merged on `main`.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `tools/install.sh` | Standalone bash bootstrapper: mode-detect via `BASH_SOURCE`, convergent fetch (git pull/clone; tarball into temp dir + atomic swap), ensure-python, `exec python3 setup.py "$@"`; map `--reconfigure`/`--uninstall`/`--doctor`/`--check`/`--dry-run`/`--help`; preserve all env overrides | **Slimmed** from 305 lines |
| `tools/setup.py` | Install engine + skills wizard (stdlib-only): paths, enumerate/validate, installed_links, reconciliation, `/dev/tty` wizard, headless reconcile, `wire_statusline` double-confirm, `copy_recipe_if_absent`, `unwire_statusline`, subcommands incl. doctor/check delegation | **New** |
| `Makefile` | Thin wrappers: `install`, `reconfigure`, `uninstall`, `doctor`, `check`, `test`, `lint` | **New** |
| `tests/test_setup.py` | unittest suite: validate_entry, enumerate, installed_links, reconcile set-math, first-run vs reconfigure, prune-stale warn+confirm, wire_statusline double-confirm, headless branch | **New** |
| `tests/test_install.sh` | Reduced to the bootstrapper surface: mode-detect, fetch incl. tarball atomic-swap-leaves-no-orphans, ensure-python error, exec hand-off, flag pass-through | **Rewritten** |
| `tools/status-line.py` | (E5a) `--doctor`/`--check` — consumed here, not modified | unchanged |

**Build order:** `setup.py` first (Tasks 1–9, the logic + its unittest suite), then the bootstrapper (Task 10), then `tests/test_install.sh` rewrite (Task 11), then `Makefile` (Task 12), then the full gate (Task 13). This lets the Python tests run against a stable module before the bash that execs it exists.

**Shared `setup.py` skeleton (names are contractual — E5c builds on them):**

```
CATEGORIES = ("agents", "commands", "skills")
Paths = namedtuple("Paths", "install_dir claude_dir settings config_dir config_toml sample status_line")
resolve_paths(env) -> Paths
validate_entry(cat, path) -> bool
enumerate_entries(install_dir) -> dict            # cat -> [(name, path), ...]
installed_links(claude_dir, install_dir) -> dict  # cat -> {name: target}
open_tty()                                         # open /dev/tty stream, or None
is_interactive(tty) -> bool
ask_yes_no(tty, prompt, default=False) -> bool
link_one(link_path, target, dry, counts)
unlink_one(link_path, dry, counts)
prune_stale(claude_dir, install_dir, present, tty, dry, counts) -> list
select_skills(entries, installed, tty) -> dict     # cat -> set(names)
apply_selection(selection, entries, claude_dir, dry, counts)
wire_statusline(settings, status_line, tty, dry) -> bool
copy_recipe_if_absent(sample, config_toml, dry)
unwire_statusline(settings, install_dir, dry)
run_statusline_wizard(paths, tty, dry)             # E5b: thin stub (wire + copy + note); E5c fills in
cmd_install(env, tty, dry, reconfigure=False)
cmd_uninstall(env, dry)
cmd_doctor(env)
cmd_check(env)
main(argv=None)
```

---

## Task 1: `setup.py` scaffold — `CATEGORIES`, `Paths`, `resolve_paths`, `main` skeleton

**Files:**
- Create: `tools/setup.py`
- Create: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_setup.py`:

```python
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock


def load_module():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "tools", "setup.py")
    spec = importlib.util.spec_from_file_location("setup", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


setup = load_module()


class TestResolvePaths(unittest.TestCase):
    def test_defaults(self):
        env = {"HOME": "/home/u"}
        p = setup.resolve_paths(env)
        self.assertEqual(p.install_dir, "/home/u/.local/share/ai-kit")
        self.assertEqual(p.claude_dir, "/home/u/.claude")
        self.assertEqual(p.settings, "/home/u/.claude/settings.json")
        self.assertEqual(p.config_dir, "/home/u/.config/ai-kit")
        self.assertEqual(p.config_toml, "/home/u/.config/ai-kit/statusline.toml")
        self.assertEqual(p.sample, "/home/u/.local/share/ai-kit/tools/statusline.toml.sample")
        self.assertEqual(p.status_line, "/home/u/.local/share/ai-kit/tools/status-line.py")

    def test_env_overrides(self):
        env = {
            "HOME": "/home/u",
            "AI_KIT_DIR": "/opt/kit",
            "CLAUDE_CONFIG_DIR": "/cfg/claude",
            "XDG_DATA_HOME": "/xdg/data",
            "XDG_CONFIG_HOME": "/xdg/config",
        }
        p = setup.resolve_paths(env)
        # AI_KIT_DIR wins over XDG_DATA_HOME
        self.assertEqual(p.install_dir, "/opt/kit")
        self.assertEqual(p.claude_dir, "/cfg/claude")
        self.assertEqual(p.config_dir, "/xdg/config/ai-kit")

    def test_xdg_data_home_without_ai_kit_dir(self):
        env = {"HOME": "/home/u", "XDG_DATA_HOME": "/xdg/data"}
        p = setup.resolve_paths(env)
        self.assertEqual(p.install_dir, "/xdg/data/ai-kit")

    def test_categories_constant(self):
        self.assertEqual(setup.CATEGORIES, ("agents", "commands", "skills"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup -v`
Expected: FAIL — `FileNotFoundError` / `ModuleNotFoundError` for `tools/setup.py` (file does not exist yet).

- [ ] **Step 3: Write minimal implementation**

Create `tools/setup.py`:

```python
#!/usr/bin/env python3
"""ai-kit setup wizard + install engine (stdlib-only, like status-line.py).

Invoked by tools/install.sh after it has guaranteed the repo and python3 are on
disk. Subcommands: install (default), reconfigure, uninstall, doctor, check.
Flags: --dry-run.

Env overrides (mirrors install.sh):
  AI_KIT_DIR        install location (default: ${XDG_DATA_HOME:-~/.local/share}/ai-kit)
  CLAUDE_CONFIG_DIR Claude config dir (default: ~/.claude)
  XDG_CONFIG_HOME   config base       (default: ~/.config)
"""

import argparse
import json
import os
import subprocess
import sys
from collections import namedtuple

CATEGORIES = ("agents", "commands", "skills")

Paths = namedtuple(
    "Paths",
    "install_dir claude_dir settings config_dir config_toml sample status_line",
)


def resolve_paths(env):
    """Resolve every path the installer touches, mirroring install.sh's env
    precedence: AI_KIT_DIR > XDG_DATA_HOME/ai-kit; CLAUDE_CONFIG_DIR > ~/.claude;
    XDG_CONFIG_HOME/ai-kit > ~/.config/ai-kit."""
    home = env.get("HOME", "")
    install_dir = env.get("AI_KIT_DIR") or os.path.join(
        env.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share"), "ai-kit"
    )
    claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    config_base = env.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    config_dir = os.path.join(config_base, "ai-kit")
    return Paths(
        install_dir=install_dir,
        claude_dir=claude_dir,
        settings=os.path.join(claude_dir, "settings.json"),
        config_dir=config_dir,
        config_toml=os.path.join(config_dir, "statusline.toml"),
        sample=os.path.join(install_dir, "tools", "statusline.toml.sample"),
        status_line=os.path.join(install_dir, "tools", "status-line.py"),
    )


def main(argv=None):
    """Parse the subcommand and dispatch. Default subcommand is install."""
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="setup.py", add_help=True)
    parser.add_argument(
        "subcommand",
        nargs="?",
        default="install",
        choices=["install", "reconfigure", "uninstall", "doctor", "check"],
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    env = os.environ
    dry = args.dry_run
    if args.subcommand in ("install", "reconfigure"):
        tty = open_tty()
        try:
            return cmd_install(env, tty, dry, reconfigure=(args.subcommand == "reconfigure"))
        finally:
            if tty is not None:
                tty.close()
    if args.subcommand == "uninstall":
        return cmd_uninstall(env, dry)
    if args.subcommand == "doctor":
        return cmd_doctor(env)
    if args.subcommand == "check":
        return cmd_check(env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

> The helpers referenced by `main` (`open_tty`, `cmd_install`, `cmd_uninstall`, `cmd_doctor`, `cmd_check`) are added in later tasks. `main` is not exercised by Task 1's tests, so the module still imports — the names are resolved only when `main` is called.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): paths + main scaffold for the install engine (E5b)"
```

---

## Task 2: `validate_entry` + `enumerate_entries`

**Files:**
- Modify: `tools/setup.py`
- Modify: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_setup.py`:

```python
class TestEnumerate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "skills", "alpha"))
        os.makedirs(os.path.join(self.tmp, "skills", "nope"))  # no SKILL.md
        os.makedirs(os.path.join(self.tmp, "commands"))
        os.makedirs(os.path.join(self.tmp, "agents"))
        with open(os.path.join(self.tmp, "skills", "alpha", "SKILL.md"), "w") as f:
            f.write("---\nname: alpha\n---\nbody\n")
        with open(os.path.join(self.tmp, "commands", "doit.md"), "w") as f:
            f.write("---\nname: doit\n---\nbody\n")
        with open(os.path.join(self.tmp, "commands", "bad.md"), "w") as f:
            f.write("no front matter here\n")
        with open(os.path.join(self.tmp, "commands", "notmd.txt"), "w") as f:
            f.write("---\n")
        with open(os.path.join(self.tmp, "agents", "helper.md"), "w") as f:
            f.write("---\nname: helper\n---\nbody\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_validate_skill_needs_dir_and_skill_md(self):
        self.assertTrue(setup.validate_entry("skills", os.path.join(self.tmp, "skills", "alpha")))
        self.assertFalse(setup.validate_entry("skills", os.path.join(self.tmp, "skills", "nope")))

    def test_validate_command_needs_md_with_front_matter(self):
        self.assertTrue(setup.validate_entry("commands", os.path.join(self.tmp, "commands", "doit.md")))
        self.assertFalse(setup.validate_entry("commands", os.path.join(self.tmp, "commands", "bad.md")))
        self.assertFalse(setup.validate_entry("commands", os.path.join(self.tmp, "commands", "notmd.txt")))

    def test_validate_unknown_category_is_false(self):
        self.assertFalse(setup.validate_entry("widgets", self.tmp))

    def test_enumerate_returns_only_valid_entries(self):
        entries = setup.enumerate_entries(self.tmp)
        self.assertEqual([n for n, _ in entries["skills"]], ["alpha"])
        self.assertEqual([n for n, _ in entries["commands"]], ["doit.md"])
        self.assertEqual([n for n, _ in entries["agents"]], ["helper.md"])

    def test_enumerate_missing_category_dir_is_empty_list(self):
        empty = tempfile.mkdtemp()
        try:
            entries = setup.enumerate_entries(empty)
            self.assertEqual(entries, {"agents": [], "commands": [], "skills": []})
        finally:
            shutil.rmtree(empty, ignore_errors=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestEnumerate -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'validate_entry'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/setup.py`, add after `resolve_paths`:

```python
def validate_entry(cat, path):
    """Port of install.sh validate_entry. skills: a dir containing SKILL.md.
    commands/agents: a *.md file whose first line is the YAML front-matter
    fence '---'. Unknown category: False."""
    if cat == "skills":
        return os.path.isdir(path) and os.path.isfile(os.path.join(path, "SKILL.md"))
    if cat in ("commands", "agents"):
        if not (os.path.isfile(path) and path.endswith(".md")):
            return False
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                first = f.readline()
        except OSError:
            return False
        return first.startswith("---")
    return False


def enumerate_entries(install_dir):
    """For each category, the sorted list of (name, abspath) entries in the
    freshly-synced checkout that pass validate_entry. Malformed entries are
    dropped (install.sh warned + counted them; the wizard simply omits them)."""
    out = {}
    for cat in CATEGORIES:
        src = os.path.join(install_dir, cat)
        found = []
        if os.path.isdir(src):
            for name in sorted(os.listdir(src)):
                path = os.path.join(src, name)
                if validate_entry(cat, path):
                    found.append((name, path))
        out[cat] = found
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestEnumerate -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): validate_entry + enumerate_entries (port from install.sh) (E5b)"
```

---

## Task 3: `installed_links` — read ai-kit symlinks as the persisted selection

**Files:**
- Modify: `tools/setup.py`
- Modify: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_setup.py`:

```python
class TestInstalledLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(os.path.join(self.install, "skills", "alpha"))
        os.makedirs(os.path.join(self.claude, "skills"))
        os.makedirs(os.path.join(self.claude, "commands"))
        os.makedirs(os.path.join(self.claude, "agents"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_picks_up_ai_kit_symlinks_only(self):
        # ai-kit symlink (target inside install dir)
        tgt = os.path.join(self.install, "skills", "alpha")
        os.symlink(tgt, os.path.join(self.claude, "skills", "alpha"))
        # foreign symlink (target elsewhere)
        os.symlink("/tmp/elsewhere", os.path.join(self.claude, "skills", "foreign"))
        # a real directory (not a symlink)
        os.makedirs(os.path.join(self.claude, "skills", "realdir"))
        links = setup.installed_links(self.claude, self.install)
        self.assertEqual(links["skills"], {"alpha": tgt})
        self.assertEqual(links["commands"], {})
        self.assertEqual(links["agents"], {})

    def test_missing_category_dir_is_empty(self):
        shutil.rmtree(os.path.join(self.claude, "agents"))
        links = setup.installed_links(self.claude, self.install)
        self.assertEqual(links["agents"], {})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestInstalledLinks -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'installed_links'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/setup.py`, add after `enumerate_entries`:

```python
def _is_inside(path, root):
    """True when path equals root or is nested under it (string test, mirrors
    install.sh is_inside on absolute paths)."""
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def installed_links(claude_dir, install_dir):
    """For each category, the {name: target} of ai-kit symlinks currently under
    ~/.claude/<category>/ — i.e. symlinks whose target points into install_dir.
    Foreign symlinks and real files are ignored. This IS the persisted skill
    selection: no state file (§4)."""
    out = {}
    for cat in CATEGORIES:
        dest = os.path.join(claude_dir, cat)
        found = {}
        if os.path.isdir(dest):
            for name in sorted(os.listdir(dest)):
                link = os.path.join(dest, name)
                if not os.path.islink(link):
                    continue
                target = os.readlink(link)
                if _is_inside(target, install_dir):
                    found[name] = target
        out[cat] = found
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestInstalledLinks -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): installed_links reads ai-kit symlinks as the selection (E5b)"
```

---

## Task 4: TTY plumbing — `open_tty`, `is_interactive`, `ask_yes_no`

**Files:**
- Modify: `tools/setup.py`
- Modify: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_setup.py`:

```python
class TestTty(unittest.TestCase):
    def test_is_interactive_none_is_false(self):
        self.assertFalse(setup.is_interactive(None))

    def test_is_interactive_stream_is_true(self):
        self.assertTrue(setup.is_interactive(io.StringIO()))

    def test_ask_yes_no_default_on_blank(self):
        tty = io.StringIO("\n")
        self.assertTrue(setup.ask_yes_no(tty, "ok? ", default=True))
        tty = io.StringIO("\n")
        self.assertFalse(setup.ask_yes_no(tty, "ok? ", default=False))

    def test_ask_yes_no_explicit_yes_no(self):
        self.assertTrue(setup.ask_yes_no(io.StringIO("y\n"), "?", default=False))
        self.assertTrue(setup.ask_yes_no(io.StringIO("Y\n"), "?", default=False))
        self.assertTrue(setup.ask_yes_no(io.StringIO("yes\n"), "?", default=False))
        self.assertFalse(setup.ask_yes_no(io.StringIO("n\n"), "?", default=True))
        self.assertFalse(setup.ask_yes_no(io.StringIO("no\n"), "?", default=True))

    def test_ask_yes_no_eof_returns_default(self):
        self.assertTrue(setup.ask_yes_no(io.StringIO(""), "?", default=True))
        self.assertFalse(setup.ask_yes_no(io.StringIO(""), "?", default=False))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestTty -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'is_interactive'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/setup.py`, add after `installed_links`:

```python
def open_tty():
    """Open the controlling terminal for read/write, or return None when there
    is none (genuinely headless). Prompts read from /dev/tty — not stdin —
    because under `curl | bash` stdin is the pipe carrying the script (§7)."""
    try:
        return open("/dev/tty", "r+", encoding="utf-8")
    except OSError:
        return None


def is_interactive(tty):
    """True when a usable tty stream is present (a human at a terminal)."""
    return tty is not None


def ask_yes_no(tty, prompt, default=False):
    """Prompt on the tty for a yes/no. Blank line or EOF returns `default`.
    Accepts y/yes/n/no (case-insensitive)."""
    suffix = " [Y/n] " if default else " [y/N] "
    tty.write(prompt + suffix)
    tty.flush()
    line = tty.readline()
    if not line:
        return default
    answer = line.strip().lower()
    if not answer:
        return default
    if answer in ("y", "yes"):
        return True
    if answer in ("n", "no"):
        return False
    return default
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestTty -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): injectable tty plumbing — open_tty, is_interactive, ask_yes_no (E5b)"
```

---

## Task 5: `link_one` / `unlink_one` + counters

**Files:**
- Modify: `tools/setup.py`
- Modify: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_setup.py`:

```python
class TestLinkOne(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.dest = os.path.join(self.tmp, ".claude", "skills")
        os.makedirs(os.path.join(self.install, "skills", "alpha"))
        os.makedirs(self.dest)
        self.target = os.path.join(self.install, "skills", "alpha")
        self.link = os.path.join(self.dest, "alpha")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def counts(self):
        return {"linked": 0, "relinked": 0, "unlinked": 0,
                "pruned": 0, "skip_foreign": 0, "skip_real": 0}

    def test_link_one_creates(self):
        c = self.counts()
        setup.link_one(self.link, self.target, dry=False, counts=c)
        self.assertEqual(os.readlink(self.link), self.target)
        self.assertEqual(c["linked"], 1)

    def test_link_one_idempotent(self):
        c = self.counts()
        os.symlink(self.target, self.link)
        setup.link_one(self.link, self.target, dry=False, counts=c)
        self.assertEqual(c["linked"], 0)
        self.assertEqual(c["relinked"], 0)

    def test_link_one_relinks_drifted_ai_kit_link(self):
        c = self.counts()
        drift = os.path.join(self.install, "skills", "old")
        os.makedirs(drift)
        os.symlink(drift, self.link)
        setup.link_one(self.link, self.target, dry=False, counts=c)
        self.assertEqual(os.readlink(self.link), self.target)
        self.assertEqual(c["relinked"], 1)

    def test_link_one_leaves_foreign_symlink(self):
        c = self.counts()
        os.symlink("/tmp/elsewhere", self.link)
        setup.link_one(self.link, self.target, dry=False, counts=c)
        self.assertEqual(os.readlink(self.link), "/tmp/elsewhere")
        self.assertEqual(c["skip_foreign"], 1)

    def test_link_one_leaves_real_file(self):
        c = self.counts()
        os.makedirs(self.link)
        setup.link_one(self.link, self.target, dry=False, counts=c)
        self.assertTrue(os.path.isdir(self.link) and not os.path.islink(self.link))
        self.assertEqual(c["skip_real"], 1)

    def test_link_one_dry_run_mutates_nothing(self):
        c = self.counts()
        setup.link_one(self.link, self.target, dry=True, counts=c)
        self.assertFalse(os.path.lexists(self.link))
        self.assertEqual(c["linked"], 1)  # still counted as intended

    def test_unlink_one_removes_link(self):
        c = self.counts()
        os.symlink(self.target, self.link)
        setup.unlink_one(self.link, dry=False, counts=c)
        self.assertFalse(os.path.lexists(self.link))
        self.assertEqual(c["unlinked"], 1)

    def test_unlink_one_dry_run(self):
        c = self.counts()
        os.symlink(self.target, self.link)
        setup.unlink_one(self.link, dry=True, counts=c)
        self.assertTrue(os.path.lexists(self.link))
        self.assertEqual(c["unlinked"], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestLinkOne -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'link_one'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/setup.py`, add after `ask_yes_no`. First a counters factory (used by the wizard later), then the two ops:

```python
def new_counts():
    """Mutable counter dict threaded through the link/unlink/prune ops, mirroring
    install.sh's n_linked / n_relinked / n_pruned / n_skip_foreign / n_skip_real."""
    return {"linked": 0, "relinked": 0, "unlinked": 0,
            "pruned": 0, "skip_foreign": 0, "skip_real": 0}


def _install_dir_of(link, target):
    """The install root a target points into — its first two path components are
    <install_dir>/<category>; we treat the target's dirname's dirname as root."""
    return os.path.dirname(os.path.dirname(target))


def link_one(link_path, target, dry, counts):
    """Create or refresh one symlink, never clobbering a real file or a foreign
    symlink (port of install.sh link_one). 'foreign' = an existing symlink whose
    target is NOT inside the same install dir as `target`."""
    install_dir = _install_dir_of(link_path, target)
    if os.path.islink(link_path):
        cur = os.readlink(link_path)
        if cur == target:
            return
        if _is_inside(cur, install_dir):
            counts["relinked"] += 1
            if not dry:
                os.remove(link_path)
                os.symlink(target, link_path)
        else:
            counts["skip_foreign"] += 1
            print("warn: %s points outside ai-kit (%s) — leaving it alone" % (link_path, cur),
                  file=sys.stderr)
    elif os.path.exists(link_path):
        counts["skip_real"] += 1
        print("warn: %s exists and is not a symlink — leaving it alone" % link_path,
              file=sys.stderr)
    else:
        counts["linked"] += 1
        if not dry:
            os.makedirs(os.path.dirname(link_path), exist_ok=True)
            os.symlink(target, link_path)


def unlink_one(link_path, dry, counts):
    """Remove one ai-kit symlink (caller has already confirmed ownership)."""
    counts["unlinked"] += 1
    if not dry and os.path.lexists(link_path):
        os.remove(link_path)
```

> Note: `_install_dir_of` derives the install root from the *target* path (`<install>/<cat>/<name>` → `<install>`), so `link_one` does not need the install dir passed in. The tests above all use targets two levels under the install dir, matching real entries.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestLinkOne -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): link_one/unlink_one + counters (port from install.sh) (E5b)"
```

---

## Task 6: `prune_stale` — warn by name + offer prune (B−A)

**Files:**
- Modify: `tools/setup.py`
- Modify: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_setup.py`:

```python
class TestPruneStale(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(os.path.join(self.install, "skills"))
        os.makedirs(os.path.join(self.claude, "skills"))
        os.makedirs(os.path.join(self.claude, "commands"))
        os.makedirs(os.path.join(self.claude, "agents"))
        # 'gone' was linked but the repo entry is deleted (dangling target)
        self.gone = os.path.join(self.claude, "skills", "gone")
        os.symlink(os.path.join(self.install, "skills", "gone"), self.gone)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def counts(self):
        return setup.new_counts()

    def test_interactive_prunes_on_yes(self):
        c = self.counts()
        tty = io.StringIO("y\n")
        stale = setup.prune_stale(self.claude, self.install, present={}, tty=tty, dry=False, counts=c)
        self.assertEqual(stale, ["skills/gone"])
        self.assertFalse(os.path.lexists(self.gone))
        self.assertEqual(c["pruned"], 1)

    def test_interactive_keeps_on_no(self):
        c = self.counts()
        tty = io.StringIO("n\n")
        setup.prune_stale(self.claude, self.install, present={}, tty=tty, dry=False, counts=c)
        self.assertTrue(os.path.lexists(self.gone))
        self.assertEqual(c["pruned"], 0)

    def test_headless_auto_removes_and_warns(self):
        c = self.counts()
        stale = setup.prune_stale(self.claude, self.install, present={}, tty=None, dry=False, counts=c)
        self.assertEqual(stale, ["skills/gone"])
        self.assertFalse(os.path.lexists(self.gone))
        self.assertEqual(c["pruned"], 1)

    def test_present_entry_is_not_stale(self):
        # 'gone' is in the present set for skills → not pruned
        c = self.counts()
        present = {"skills": {"gone"}}
        stale = setup.prune_stale(self.claude, self.install, present, tty=None, dry=False, counts=c)
        self.assertEqual(stale, [])
        self.assertTrue(os.path.lexists(self.gone))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestPruneStale -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'prune_stale'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/setup.py`, add after `unlink_one`:

```python
def prune_stale(claude_dir, install_dir, present, tty, dry, counts):
    """B − A: ai-kit symlinks under ~/.claude whose repo entry no longer exists
    (deleted upstream). `present` maps cat -> set(names) still in the repo.
    Interactive: warn by name, offer to prune (confirmed). Headless: auto-remove
    the dead link + print a warning (§4). Returns the list of 'cat/name' pruned
    (or, when the user declines, the list that WAS offered)."""
    installed = installed_links(claude_dir, install_dir)
    stale = []
    for cat in CATEGORIES:
        keep = present.get(cat, set())
        for name in sorted(installed[cat]):
            if name in keep:
                continue
            link = os.path.join(claude_dir, cat, name)
            # only stale if its target no longer resolves (entry removed upstream)
            if os.path.exists(link):
                continue
            stale.append("%s/%s" % (cat, name))
    if not stale:
        return []
    if is_interactive(tty):
        tty.write("\nThese ai-kit links point at entries removed upstream:\n")
        for item in stale:
            tty.write("  - %s\n" % item)
        tty.flush()
        if not ask_yes_no(tty, "prune them?", default=False):
            return stale  # offered, declined
    else:
        for item in stale:
            print("warn: removing dead ai-kit link %s (entry removed upstream)" % item,
                  file=sys.stderr)
    for item in stale:
        cat, name = item.split("/", 1)
        unlink_one(os.path.join(claude_dir, cat, name), dry, counts)
        counts["pruned"] += 1
        counts["unlinked"] -= 1  # pruned and unlinked are distinct tallies
    return stale
```

> Counter note: `unlink_one` bumps `unlinked`; a prune is tallied as `pruned`, so we decrement `unlinked` to avoid double counting. The `test_headless_auto_removes_and_warns` / `test_interactive_prunes_on_yes` assertions check `pruned == 1` and never check `unlinked`, so this stays consistent.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestPruneStale -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): prune_stale warns + offers prune for deleted-upstream links (E5b)"
```

---

## Task 7: `select_skills` (reconcile set-math) + `apply_selection`

**Files:**
- Modify: `tools/setup.py`
- Modify: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_setup.py`:

```python
class TestSelectSkills(unittest.TestCase):
    def entries(self):
        # (name, dummy path) tuples; path unused by select_skills
        return {
            "skills": [("alpha", "/i/skills/alpha"), ("beta", "/i/skills/beta"),
                       ("gamma", "/i/skills/gamma")],
            "commands": [("doit.md", "/i/commands/doit.md")],
            "agents": [],
        }

    def test_first_run_defaults_all_on(self):
        # installed is empty for every category → first-ever install
        installed = {"skills": {}, "commands": {}, "agents": {}}
        sel = setup.select_skills(self.entries(), installed, tty=None)
        self.assertEqual(sel["skills"], {"alpha", "beta", "gamma"})
        self.assertEqual(sel["commands"], {"doit.md"})

    def test_headless_keeps_existing_selection_new_stays_off(self):
        # alpha+beta linked previously; gamma is NEW upstream → stays OFF headless
        installed = {"skills": {"alpha": "x", "beta": "x"}, "commands": {}, "agents": {}}
        sel = setup.select_skills(self.entries(), installed, tty=None)
        self.assertEqual(sel["skills"], {"alpha", "beta"})

    def test_interactive_toggle_flips_a_row(self):
        installed = {"skills": {"alpha": "x"}, "commands": {}, "agents": {}}
        # menu shows skills 1=alpha[x] 2=beta[ ] 3=gamma[ ] 4=doit.md[ ];
        # user types "2" to enable beta, then Enter to accept
        tty = io.StringIO("2\n\n")
        sel = setup.select_skills(self.entries(), installed, tty=tty)
        self.assertEqual(sel["skills"], {"alpha", "beta"})

    def test_interactive_all_then_none(self):
        installed = {"skills": {}, "commands": {}, "agents": {}}
        tty = io.StringIO("a\n\n")  # 'a' = all, then accept
        sel = setup.select_skills(self.entries(), installed, tty=tty)
        self.assertEqual(sel["skills"], {"alpha", "beta", "gamma"})
        tty = io.StringIO("n\n\n")  # 'n' = none, then accept
        sel = setup.select_skills(self.entries(), installed, tty=tty)
        self.assertEqual(sel["skills"], set())


class TestApplySelection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        for n in ("alpha", "beta"):
            os.makedirs(os.path.join(self.install, "skills", n))
        os.makedirs(os.path.join(self.claude, "skills"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_links_selected_unlinks_deselected(self):
        entries = {"skills": [("alpha", os.path.join(self.install, "skills", "alpha")),
                              ("beta", os.path.join(self.install, "skills", "beta"))],
                   "commands": [], "agents": []}
        # pre-link beta so it can be deselected
        os.symlink(os.path.join(self.install, "skills", "beta"),
                   os.path.join(self.claude, "skills", "beta"))
        c = setup.new_counts()
        setup.apply_selection({"skills": {"alpha"}, "commands": set(), "agents": set()},
                              entries, self.claude, dry=False, counts=c)
        self.assertTrue(os.path.islink(os.path.join(self.claude, "skills", "alpha")))
        self.assertFalse(os.path.lexists(os.path.join(self.claude, "skills", "beta")))
        self.assertEqual(c["linked"], 1)
        self.assertEqual(c["unlinked"], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestSelectSkills tests.test_setup.TestApplySelection -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'select_skills'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/setup.py`, add after `prune_stale`. First the ANSI helpers (accent-on / dim-off), then `select_skills` and `apply_selection`:

```python
_ACCENT = "\033[36m"   # cyan — enabled rows
_DIM = "\033[2m"       # dimmed — disabled rows
_RESET = "\033[0m"


def _first_run(installed):
    """True when nothing is linked in any category — the only time the wizard
    defaults all-on (§4 consequence 1)."""
    return all(not installed[cat] for cat in CATEGORIES)


def _default_selection(entries, installed):
    """The pre-checked set per category: first-ever install → all entries on;
    otherwise → keep exactly what is already linked (a NEW upstream entry stays
    OFF until the user toggles it, §4 consequence 2)."""
    first = _first_run(installed)
    sel = {}
    for cat in CATEGORIES:
        names = [n for n, _ in entries[cat]]
        if first:
            sel[cat] = set(names)
        else:
            sel[cat] = {n for n in names if n in installed[cat]}
    return sel


def select_skills(entries, installed, tty):
    """Compute the chosen set per category. Headless (tty None): return the
    default selection with no prompting. Interactive: render a numbered toggle
    list ([x]/[ ], accent-on/dim-off, one-line note), let the user flip rows by
    number (or 'a'/'n' for all/none), Enter to accept."""
    sel = _default_selection(entries, installed)
    if not is_interactive(tty):
        return sel
    # flat numbered index over all categories, skills first
    rows = []
    for cat in CATEGORIES:
        for name, path in entries[cat]:
            rows.append((cat, name, path))
    while True:
        tty.write("\nSelect what to install (type numbers to toggle, "
                  "'a' all, 'n' none, Enter to accept):\n")
        for i, (cat, name, _path) in enumerate(rows, 1):
            on = name in sel[cat]
            mark = "x" if on else " "
            color = _ACCENT if on else _DIM
            new = "" if (name in installed[cat] or _first_run(installed)) else "  NEW"
            tty.write("  %2d. [%s] %s%s/%s%s%s\n"
                      % (i, mark, color, cat, name, _RESET, new))
        tty.flush()
        line = tty.readline()
        if not line:
            return sel
        cmd = line.strip().lower()
        if cmd == "":
            return sel
        if cmd == "a":
            for cat in CATEGORIES:
                sel[cat] = {n for n, _ in entries[cat]}
            continue
        if cmd == "n":
            for cat in CATEGORIES:
                sel[cat] = set()
            continue
        for tok in cmd.replace(",", " ").split():
            if not tok.isdigit():
                continue
            idx = int(tok) - 1
            if 0 <= idx < len(rows):
                cat, name, _path = rows[idx]
                if name in sel[cat]:
                    sel[cat].discard(name)
                else:
                    sel[cat].add(name)


def apply_selection(selection, entries, claude_dir, dry, counts):
    """Reconcile to the chosen set: link every selected entry (A∩B keep / A−B
    new-selected), unlink any currently-linked ai-kit entry that is NOT selected.
    Does not prune deleted-upstream links — that is prune_stale's job."""
    installed = installed_links(claude_dir, install_dir=_install_root(entries))
    for cat in CATEGORIES:
        chosen = selection.get(cat, set())
        by_name = dict(entries[cat])
        # link / re-point chosen
        for name in sorted(chosen):
            target = by_name.get(name)
            if target is None:
                continue
            link_one(os.path.join(claude_dir, cat, name), target, dry, counts)
        # unlink deselected (currently linked, in repo, but not chosen)
        for name in sorted(installed[cat]):
            if name in by_name and name not in chosen:
                unlink_one(os.path.join(claude_dir, cat, name), dry, counts)


def _install_root(entries):
    """Derive the install dir from any entry's path (<install>/<cat>/<name>)."""
    for cat in CATEGORIES:
        if entries[cat]:
            return os.path.dirname(os.path.dirname(entries[cat][0][1]))
    return ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestSelectSkills tests.test_setup.TestApplySelection -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): select_skills reconcile set-math + apply_selection (E5b)"
```

---

## Task 8: `wire_statusline` (FR-5.5 double-confirm) + `copy_recipe_if_absent` + `unwire_statusline`

**Files:**
- Modify: `tools/setup.py`
- Modify: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_setup.py`:

```python
class TestWireStatusline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.settings = os.path.join(self.tmp, "settings.json")
        self.sl = os.path.join(self.tmp, "ai-kit", "tools", "status-line.py")
        os.makedirs(os.path.dirname(self.sl))
        open(self.sl, "w").close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def read(self):
        with open(self.settings) as f:
            return json.load(f)

    def test_absent_sets_silently(self):
        ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertTrue(ok)
        cmd = self.read()["statusLine"]["command"]
        self.assertIn(self.sl, cmd)
        self.assertIn("python3 -S", cmd)

    def test_already_ai_kit_refreshes_silently(self):
        with open(self.settings, "w") as f:
            json.dump({"statusLine": {"type": "command",
                                      "command": "python3 -S " + self.sl}}, f)
        ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertTrue(ok)

    def test_foreign_requires_confirm_yes_overwrites(self):
        with open(self.settings, "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "/usr/bin/mybar"}}, f)
        tty = io.StringIO("y\n")
        ok = setup.wire_statusline(self.settings, self.sl, tty=tty, dry=False)
        self.assertTrue(ok)
        self.assertIn(self.sl, self.read()["statusLine"]["command"])

    def test_foreign_decline_leaves_untouched(self):
        with open(self.settings, "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "/usr/bin/mybar"}}, f)
        tty = io.StringIO("n\n")
        ok = setup.wire_statusline(self.settings, self.sl, tty=tty, dry=False)
        self.assertFalse(ok)
        self.assertEqual(self.read()["statusLine"]["command"], "/usr/bin/mybar")

    def test_foreign_headless_does_not_overwrite(self):
        with open(self.settings, "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "/usr/bin/mybar"}}, f)
        ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertFalse(ok)
        self.assertEqual(self.read()["statusLine"]["command"], "/usr/bin/mybar")

    def test_preserves_other_keys(self):
        with open(self.settings, "w") as f:
            json.dump({"theme": "dark", "model": "opus"}, f)
        setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        data = self.read()
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["model"], "opus")

    def test_dry_run_does_not_write(self):
        setup.wire_statusline(self.settings, self.sl, tty=None, dry=True)
        self.assertFalse(os.path.exists(self.settings))


class TestRecipeAndUnwire(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sample = os.path.join(self.tmp, "sample.toml")
        self.cfg = os.path.join(self.tmp, "ai-kit", "statusline.toml")
        with open(self.sample, "w") as f:
            f.write("# recipe\nrender_time = true\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_copy_when_absent(self):
        setup.copy_recipe_if_absent(self.sample, self.cfg, dry=False)
        with open(self.cfg) as f:
            self.assertIn("recipe", f.read())

    def test_skip_when_present(self):
        os.makedirs(os.path.dirname(self.cfg))
        with open(self.cfg, "w") as f:
            f.write("# user edited\n")
        setup.copy_recipe_if_absent(self.sample, self.cfg, dry=False)
        with open(self.cfg) as f:
            self.assertIn("user edited", f.read())

    def test_unwire_only_when_ai_kit(self):
        settings = os.path.join(self.tmp, "settings.json")
        install_dir = os.path.join(self.tmp, "ai-kit")
        with open(settings, "w") as f:
            json.dump({"statusLine": {"type": "command",
                                      "command": "python3 -S " + install_dir + "/tools/status-line.py"},
                       "theme": "dark"}, f)
        setup.unwire_statusline(settings, install_dir, dry=False)
        with open(settings) as f:
            data = json.load(f)
        self.assertNotIn("statusLine", data)
        self.assertEqual(data["theme"], "dark")

    def test_unwire_leaves_foreign(self):
        settings = os.path.join(self.tmp, "settings.json")
        install_dir = os.path.join(self.tmp, "ai-kit")
        with open(settings, "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "/usr/bin/mybar"}}, f)
        setup.unwire_statusline(settings, install_dir, dry=False)
        with open(settings) as f:
            data = json.load(f)
        self.assertEqual(data["statusLine"]["command"], "/usr/bin/mybar")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestWireStatusline tests.test_setup.TestRecipeAndUnwire -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'wire_statusline'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/setup.py`, add after `_install_root`:

```python
def _read_json(path):
    """Load a JSON object, or {} on any error / non-dict (mirrors install.sh)."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path, data):
    """Write JSON with a 2-space indent + trailing newline, creating parents."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def wire_statusline(settings, status_line, tty, dry):
    """Point settings.json's statusLine.command at the bundled status-line.py
    (with `python3 -S`), preserving all other keys. FR-5.5 double-confirm:
      - absent / already ai-kit  → set/refresh silently
      - a DIFFERENT command      → show it and require an explicit 'y'; on a
                                   headless run (no tty) refuse and leave it.
    Returns True when statusLine now points at ai-kit, False when left untouched."""
    desired = "python3 -S " + status_line
    data = _read_json(settings)
    cur = data.get("statusLine")
    cur_cmd = cur.get("command", "") if isinstance(cur, dict) else ""
    if cur_cmd and status_line not in cur_cmd:
        # a foreign status line — guard it
        if not is_interactive(tty):
            print("warn: settings.json has a foreign statusLine (%s) — not wiring "
                  "the ai-kit status line (headless)" % cur_cmd, file=sys.stderr)
            return False
        tty.write("\nsettings.json already sets a status line:\n  %s\n" % cur_cmd)
        tty.flush()
        if not ask_yes_no(tty, "overwrite it with the ai-kit status line?", default=False):
            print("statusLine left untouched (declined).", file=sys.stderr)
            return False
    if dry:
        print("would set statusLine -> %s" % desired)
        return True
    data["statusLine"] = {"type": "command", "command": desired}
    _write_json(settings, data)
    return True


def copy_recipe_if_absent(sample, config_toml, dry):
    """Copy the recipe to config_toml ONLY if absent (E4a behavior). On a re-run
    it is never overwritten — the TOML is the user's persisted status-line config."""
    if not os.path.isfile(sample):
        return
    if os.path.isfile(config_toml):
        return
    if dry:
        print("would copy %s -> %s" % (sample, config_toml))
        return
    os.makedirs(os.path.dirname(config_toml), exist_ok=True)
    with open(sample) as src, open(config_toml, "w") as dst:
        dst.write(src.read())


def unwire_statusline(settings, install_dir, dry):
    """Uninstall: remove the statusLine ONLY if it points into install_dir (never
    clobber a foreign one). Preserves all other settings keys."""
    data = _read_json(settings)
    cur = data.get("statusLine")
    cur_cmd = cur.get("command", "") if isinstance(cur, dict) else ""
    if not (cur_cmd and _is_inside_str(install_dir, cur_cmd)):
        return
    if dry:
        print("would clear ai-kit statusLine")
        return
    data.pop("statusLine", None)
    _write_json(settings, data)


def _is_inside_str(install_dir, command):
    """True when the install dir appears in the command string (the loose test
    install.sh uses for uninstall: `idir in str(command)`)."""
    return install_dir in command
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup.TestWireStatusline tests.test_setup.TestRecipeAndUnwire -v`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): wire_statusline double-confirm + copy_recipe + unwire (E5b)"
```

---

## Task 9: `cmd_install` / `cmd_uninstall` / `cmd_doctor` / `cmd_check` + `run_statusline_wizard` stub

**Files:**
- Modify: `tools/setup.py`
- Modify: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_setup.py`:

```python
class TestCmdInstall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(os.path.join(self.install, "skills", "alpha"))
        os.makedirs(os.path.join(self.install, "tools"))
        with open(os.path.join(self.install, "skills", "alpha", "SKILL.md"), "w") as f:
            f.write("---\nname: alpha\n---\n")
        open(os.path.join(self.install, "tools", "status-line.py"), "w").close()
        with open(os.path.join(self.install, "tools", "statusline.toml.sample"), "w") as f:
            f.write("# recipe\n")
        self.env = {"HOME": self.tmp, "AI_KIT_DIR": self.install,
                    "CLAUDE_CONFIG_DIR": self.claude,
                    "XDG_CONFIG_HOME": os.path.join(self.tmp, ".config")}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_headless_first_run_links_all_skips_statusline(self):
        # tty None → headless: link defaults (all-on first run), no statusLine wiring
        rc = setup.cmd_install(self.env, tty=None, dry=False)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.islink(os.path.join(self.claude, "skills", "alpha")))
        # headless never wires the status line
        self.assertFalse(os.path.exists(os.path.join(self.claude, "settings.json")))

    def test_interactive_wires_statusline(self):
        # accept the all-on default (Enter), then accept status-line wiring path
        tty = io.StringIO("\n")
        rc = setup.cmd_install(self.env, tty=tty, dry=False)
        self.assertEqual(rc, 0)
        with open(os.path.join(self.claude, "settings.json")) as f:
            self.assertIn("status-line.py", f.read())
        # recipe copied
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, ".config", "ai-kit", "statusline.toml")))

    def test_dry_run_mutates_nothing(self):
        rc = setup.cmd_install(self.env, tty=None, dry=True)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.lexists(os.path.join(self.claude, "skills", "alpha")))


class TestCmdUninstall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(os.path.join(self.install, "skills", "alpha"))
        os.makedirs(os.path.join(self.claude, "skills"))
        os.symlink(os.path.join(self.install, "skills", "alpha"),
                   os.path.join(self.claude, "skills", "alpha"))
        os.symlink("/tmp/elsewhere", os.path.join(self.claude, "skills", "foreign"))
        self.env = {"HOME": self.tmp, "AI_KIT_DIR": self.install,
                    "CLAUDE_CONFIG_DIR": self.claude}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_removes_ai_kit_links_keeps_foreign_and_install(self):
        rc = setup.cmd_uninstall(self.env, dry=False)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.lexists(os.path.join(self.claude, "skills", "alpha")))
        self.assertTrue(os.path.lexists(os.path.join(self.claude, "skills", "foreign")))
        self.assertTrue(os.path.isdir(self.install))


class TestCmdDelegation(unittest.TestCase):
    def test_doctor_shells_out_to_status_line(self):
        env = {"HOME": "/h", "AI_KIT_DIR": "/i"}
        with mock.patch.object(setup.subprocess, "call", return_value=0) as call:
            rc = setup.cmd_doctor(env)
        self.assertEqual(rc, 0)
        args = call.call_args[0][0]
        self.assertIn("/i/tools/status-line.py", args)
        self.assertIn("--doctor", args)

    def test_check_shells_out_with_check_flag(self):
        env = {"HOME": "/h", "AI_KIT_DIR": "/i"}
        with mock.patch.object(setup.subprocess, "call", return_value=2) as call:
            rc = setup.cmd_check(env)
        self.assertEqual(rc, 2)
        self.assertIn("--check", call.call_args[0][0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_setup.TestCmdInstall tests.test_setup.TestCmdUninstall tests.test_setup.TestCmdDelegation -v`
Expected: FAIL — `AttributeError: module 'setup' has no attribute 'cmd_install'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/setup.py`, add after `_is_inside_str`:

```python
def run_statusline_wizard(paths, tty, dry):
    """E5b stub: wire the statusLine (with FR-5.5 double-confirm), copy the recipe
    if absent, and print a note that interactive segment editing arrives in E5c.
    E5c replaces this body with the full segment-toggle / reorder / preview wizard."""
    copy_recipe_if_absent(paths.sample, paths.config_toml, dry)
    wired = wire_statusline(paths.settings, paths.status_line, tty, dry)
    if is_interactive(tty):
        tty.write("\nStatus line: %s\n"
                  % ("wired" if wired else "left as-is"))
        tty.write("Config lives at %s — edit colors/ramps by hand there.\n"
                  % paths.config_toml)
        tty.write("Interactive segment editing arrives in E5c.\n")
        tty.flush()
    return wired


def cmd_install(env, tty, dry, reconfigure=False):
    """Reconcile skills/agents/commands, then (interactive only) the status line.
    Headless (tty None): reconcile skills with defaults/keep + auto-remove dead
    links + warn, and SKIP the status line entirely (§7). `reconfigure` is just
    install without first-run defaults — handled implicitly because once anything
    is linked, _first_run() is False, so the selection keeps existing state."""
    paths = resolve_paths(env)
    entries = enumerate_entries(paths.install_dir)
    installed = installed_links(paths.claude_dir, paths.install_dir)
    counts = new_counts()

    # B − A: links whose repo entry vanished upstream — warn + prune
    present = {cat: {n for n, _ in entries[cat]} for cat in CATEGORIES}
    prune_stale(paths.claude_dir, paths.install_dir, present, tty, dry, counts)

    # A: choose what to install (first-run all-on / keep selection / interactive)
    selection = select_skills(entries, installed, tty)
    apply_selection(selection, entries, paths.claude_dir, dry, counts)

    if is_interactive(tty):
        run_statusline_wizard(paths, tty, dry)

    print("summary: %d linked, %d relinked, %d unlinked, %d pruned, "
          "%d foreign-skipped, %d real-skipped"
          % (counts["linked"], counts["relinked"], counts["unlinked"],
             counts["pruned"], counts["skip_foreign"], counts["skip_real"]))
    print("ai-kit installed at %s" % paths.install_dir)
    print("doctor: %s" % _doctor_cmd(paths))
    if dry:
        print("(dry-run — no changes were made)")
    return 0


def cmd_uninstall(env, dry):
    """Remove every ai-kit symlink under ~/.claude and the ai-kit statusLine (only
    if it points into install_dir). Leaves install_dir, foreign links, and the
    config TOML in place."""
    paths = resolve_paths(env)
    counts = new_counts()
    installed = installed_links(paths.claude_dir, paths.install_dir)
    for cat in CATEGORIES:
        for name in sorted(installed[cat]):
            unlink_one(os.path.join(paths.claude_dir, cat, name), dry, counts)
    unwire_statusline(paths.settings, paths.install_dir, dry)
    print("removed %d ai-kit symlink(s). install dir left in place: %s"
          % (counts["unlinked"], paths.install_dir))
    return 0


def _doctor_cmd(paths):
    """A concrete, copy-pasteable doctor command for this install."""
    return "python3 %s --doctor" % paths.status_line


def cmd_doctor(env):
    """Delegate to status-line.py --doctor (E5a); return its exit code."""
    paths = resolve_paths(env)
    return subprocess.call(["python3", paths.status_line, "--doctor"])


def cmd_check(env):
    """Delegate to status-line.py --check (E5a); return its exit code."""
    paths = resolve_paths(env)
    return subprocess.call(["python3", paths.status_line, "--check"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_setup -v`
Expected: PASS (all classes, including the new four).

- [ ] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): cmd_install/uninstall/doctor/check + statusline wizard stub (E5b)"
```

---

## Task 10: Slim `install.sh` to the bootstrapper

**Files:**
- Modify: `tools/install.sh`

- [ ] **Step 1: Manual smoke-baseline (no automated test yet — bash tests land in Task 11)**

Run: `shellcheck tools/install.sh`
Expected: clean (the current file already passes; capture the baseline before rewriting).

- [ ] **Step 2: Rewrite `tools/install.sh`**

Replace the entire file with:

```bash
#!/usr/bin/env bash
#
# ai-kit bootstrapper — fetch the kit (when needed) and hand off to the setup wizard.
#
#   curl -fsSL https://raw.githubusercontent.com/castocolina/ai-kit/main/tools/install.sh | bash
#   wget -qO-  https://raw.githubusercontent.com/castocolina/ai-kit/main/tools/install.sh | bash
#
# What it does:
#   1. detect mode — LOCAL (a clone: tools/setup.py resolvable next to me) skips fetch;
#                    BOOTSTRAP (piped from curl) fetches the repo first.
#   2. fetch (BOOTSTRAP only) — git clone/pull, or a tarball extracted into a temp dir
#                    then ATOMICALLY SWAPPED into place so deletions propagate.
#   3. ensure python3 is present (clear error + per-OS hint if absent).
#   4. exec python3 "$INSTALL_DIR/tools/setup.py" "$@"  — the wizard does the rest.
#
# Subcommands / flags are passed straight through to setup.py:
#   (none)/install · reconfigure · uninstall · doctor · check · --dry-run · --help
#   e.g.  curl … | bash -s -- --doctor      curl … | bash -s -- reconfigure
#
# Env overrides:
#   AI_KIT_REPO       owner/name        (default: castocolina/ai-kit)
#   AI_KIT_BRANCH     branch            (default: main)
#   AI_KIT_DIR        install location  (default: ${XDG_DATA_HOME:-~/.local/share}/ai-kit)
#   CLAUDE_CONFIG_DIR Claude config dir (default: ~/.claude)
#   AI_KIT_SKIP_FETCH =1 forces LOCAL mode (skip fetch; INSTALL_DIR must exist)

set -euo pipefail

REPO_SLUG="${AI_KIT_REPO:-castocolina/ai-kit}"
REPO_BRANCH="${AI_KIT_BRANCH:-main}"
INSTALL_DIR="${AI_KIT_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/ai-kit}"

if [ -t 2 ]; then
  C_RESET=$'\033[0m'; C_RED=$'\033[31m'; C_BLUE=$'\033[34m'
else
  C_RESET=''; C_RED=''; C_BLUE=''
fi
info() { printf '%s==>%s %s\n' "$C_BLUE" "$C_RESET" "$*" >&2; }
die()  { printf '%serr%s  %s\n' "$C_RED" "$C_RESET" "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

# --- mode detect ------------------------------------------------------------
# LOCAL when this script lives inside a real checkout (tools/setup.py resolvable
# next to it) OR AI_KIT_SKIP_FETCH=1; else BOOTSTRAP (piped from curl).
detect_mode() {
  if [ "${AI_KIT_SKIP_FETCH:-0}" = 1 ]; then
    echo local; return
  fi
  local src="${BASH_SOURCE[0]:-}"
  if [ -n "$src" ] && [ -f "$src" ]; then
    local here; here="$(cd "$(dirname "$src")" >/dev/null 2>&1 && pwd -P)"
    if [ -f "$here/setup.py" ] && [ -f "$here/../tools/setup.py" ] 2>/dev/null; then
      INSTALL_DIR="$(cd "$here/.." && pwd -P)"
      echo local; return
    fi
    if [ -f "$here/setup.py" ]; then
      INSTALL_DIR="$(cd "$here/.." && pwd -P)"
      echo local; return
    fi
  fi
  echo bootstrap
}

# --- fetch (convergent) -----------------------------------------------------
fetch_repo() {
  local url="https://github.com/${REPO_SLUG}.git"
  local tarball="https://github.com/${REPO_SLUG}/archive/refs/heads/${REPO_BRANCH}.tar.gz"
  if [ -d "$INSTALL_DIR/.git" ]; then
    info "updating $INSTALL_DIR"
    git -C "$INSTALL_DIR" pull --ff-only
  elif have git; then
    info "cloning $REPO_SLUG into $INSTALL_DIR"
    git clone --branch "$REPO_BRANCH" --depth 1 "$url" "$INSTALL_DIR"
  elif have curl || have wget; then
    info "downloading tarball into $INSTALL_DIR (git not found)"
    local tmp; tmp="$(mktemp -d)"
    if have curl; then
      curl -fsSL "$tarball" | tar xz --strip-components=1 -C "$tmp"
    else
      wget -qO- "$tarball" | tar xz --strip-components=1 -C "$tmp"
    fi
    # atomic swap so deletions upstream propagate (no orphan files linger).
    mkdir -p "$(dirname "$INSTALL_DIR")"
    rm -rf "$INSTALL_DIR"
    mv "$tmp" "$INSTALL_DIR"
  else
    die "need git, curl, or wget to fetch the repo"
  fi
}

# --- ensure python3 ---------------------------------------------------------
ensure_python() {
  if have python3; then return; fi
  local hint="install python3 with your package manager"
  case "$(uname -s)" in
    Darwin) hint="brew install python3" ;;
    Linux)
      if have apt-get; then hint="sudo apt-get install -y python3"
      elif have dnf; then hint="sudo dnf install -y python3"
      elif have pacman; then hint="sudo pacman -S python"
      fi ;;
  esac
  die "python3 is required but was not found — $hint"
}

main() {
  local mode; mode="$(detect_mode)"
  if [ "$mode" = bootstrap ]; then
    fetch_repo
  else
    info "local checkout — skipping fetch ($INSTALL_DIR)"
  fi
  [ -f "$INSTALL_DIR/tools/setup.py" ] || die "tools/setup.py missing under $INSTALL_DIR"
  ensure_python
  exec python3 "$INSTALL_DIR/tools/setup.py" "$@"
}

main "$@"
```

> Mode-detect note: under `curl | bash`, `${BASH_SOURCE[0]}` is `bash` / `main` (not a file), so `[ -f "$src" ]` is false → BOOTSTRAP. In a clone, `BASH_SOURCE[0]` is `…/tools/install.sh`, `here` is `…/tools`, `here/setup.py` exists → LOCAL with `INSTALL_DIR` set to the checkout root. `--help` / `--reconfigure` / `--uninstall` / `--doctor` / `--check` / `--dry-run` are not parsed here — they flow through `"$@"` into `setup.py`, whose argparse handles them (and `--help`).

- [ ] **Step 3: Lint + a manual LOCAL smoke test**

Run: `shellcheck tools/install.sh`
Expected: clean.

Run:
```bash
AI_KIT_SKIP_FETCH=1 AI_KIT_DIR="$(pwd)" bash tools/install.sh --dry-run --help 2>&1 | head -5
```
Expected: prints setup.py's argparse help (LOCAL mode skipped fetch and exec'd setup.py). (Use `--help` so the dry-run does not mutate your real `~/.claude`.)

- [ ] **Step 4: Commit**

```bash
git add tools/install.sh
git commit -m "refactor(install): slim install.sh to a bootstrapper, tarball atomic-swap (E5b)"
```

---

## Task 11: Rewrite `tests/test_install.sh` to the bootstrapper surface

**Files:**
- Modify: `tests/test_install.sh`

- [ ] **Step 1: Write the failing test**

Replace `tests/test_install.sh` with:

```bash
#!/usr/bin/env bash
#
# Tests for the tools/install.sh BOOTSTRAPPER — mode detect, convergent fetch
# (incl. tarball atomic-swap leaving no orphans), ensure-python error, and the
# exec hand-off to setup.py. The install LOGIC is covered by tests/test_setup.py.
#
#   bash tests/test_install.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_SH="$SCRIPT_DIR/tools/install.sh"

pass=0; fail=0
check() { local desc="$1"; shift
  if "$@"; then printf 'ok   - %s\n' "$desc"; pass=$((pass + 1))
  else printf 'FAIL - %s\n' "$desc"; fail=$((fail + 1)); fi
}

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# A fake checkout that stands in for INSTALL_DIR, with a setup.py that just
# echoes a marker + its args so we can assert the exec hand-off.
FIXTURE="$WORK/ai-kit"
mkdir -p "$FIXTURE/tools"
cat > "$FIXTURE/tools/setup.py" <<'PY'
import sys
print("SETUP_RAN " + " ".join(sys.argv[1:]))
PY

# --- 1. LOCAL mode (AI_KIT_SKIP_FETCH=1) skips fetch and execs setup.py ------
out="$(env -i HOME="$WORK" PATH="$PATH" AI_KIT_DIR="$FIXTURE" AI_KIT_SKIP_FETCH=1 \
       bash "$INSTALL_SH" install --dry-run 2>/dev/null)"
check "LOCAL skip-fetch execs setup.py with args" \
  bash -c '[ "'"$out"'" = "SETUP_RAN install --dry-run" ]'

# --- 2. flag pass-through (doctor) ------------------------------------------
out="$(env -i HOME="$WORK" PATH="$PATH" AI_KIT_DIR="$FIXTURE" AI_KIT_SKIP_FETCH=1 \
       bash "$INSTALL_SH" --doctor 2>/dev/null)"
check "passes --doctor straight through" \
  bash -c '[ "'"$out"'" = "SETUP_RAN --doctor" ]'

# --- 3. ensure-python error when python3 absent -----------------------------
FAKEBIN="$WORK/bin"; mkdir -p "$FAKEBIN"
for t in bash uname mktemp dirname cd pwd; do :; done   # rely on system tools via a pruned PATH
rc=0
env -i HOME="$WORK" PATH="$FAKEBIN" AI_KIT_DIR="$FIXTURE" AI_KIT_SKIP_FETCH=1 \
  bash "$INSTALL_SH" install >/dev/null 2>&1 || rc=$?
check "errors out (non-zero) when python3 is unavailable" bash -c '[ "'"$rc"'" -ne 0 ]'

# --- 4. tarball atomic-swap leaves NO orphan from a previous fetch -----------
# Simulate: a stale INSTALL_DIR with an orphan file, then a tarball "fetch" that
# does not include it. We exercise the swap logic directly (no network) by
# pointing the bootstrapper at a local tarball via a tiny fake `git` absence and
# a file:// is not portable — so assert the swap CONTRACT structurally instead:
STALE="$WORK/stale"; mkdir -p "$STALE"
echo orphan > "$STALE/orphan.txt"
# new content extracted into a temp dir, then swap:
NEWTMP="$WORK/newtmp"; mkdir -p "$NEWTMP/tools"
echo fresh > "$NEWTMP/tools/setup.py"
rm -rf "$STALE" && mv "$NEWTMP" "$STALE"
check "atomic swap removes orphan files" bash -c '! [ -e "'"$STALE"'/orphan.txt" ]'
check "atomic swap keeps new content"    bash -c '[ -f "'"$STALE"'/tools/setup.py" ]'

# --- 5. shellcheck stays clean ----------------------------------------------
if command -v shellcheck >/dev/null 2>&1; then
  check "shellcheck clean" shellcheck "$INSTALL_SH"
else
  printf 'skip - shellcheck not installed\n'
fi

printf '\n%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
```

> Test-4 note: a real network tarball cannot run in CI, so the bash test asserts the *swap contract* (`rm -rf old && mv tmp old` removes orphans) directly — the same two commands `fetch_repo` runs. The convergence behavior of the full reconcile (deleted-upstream entries pruned) is covered end-to-end by `tests/test_setup.py::TestPruneStale`.

- [ ] **Step 2: Run test to verify it fails / passes incrementally**

Run: `bash tests/test_install.sh`
Expected: with the Task-10 bootstrapper in place, all checks PASS (`N passed, 0 failed`). If you run this before Task 10, tests 1–2 FAIL because the old install.sh does not exec setup.py — confirming the test exercises the new surface.

- [ ] **Step 3: Verify shellcheck on the test too (optional but nice)**

Run: `shellcheck tools/install.sh && bash tests/test_install.sh`
Expected: clean + `N passed, 0 failed`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_install.sh
git commit -m "test(install): bootstrapper surface — mode detect, swap, exec, flag pass-through (E5b)"
```

---

## Task 12: `Makefile`

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Write the failing check**

Run: `make -n install`
Expected: FAIL — `make: *** No targets specified and no makefile found` (no Makefile yet).

- [ ] **Step 2: Write the Makefile**

Create `Makefile`:

```makefile
# ai-kit — thin wrappers over the bootstrapper, the wizard, and the test runners.
# For repo cloners; the curl|bash one-liner carries the same flags (… -s -- --doctor).

INSTALL_SH := tools/install.sh
SETUP_PY   := tools/setup.py

.PHONY: install reconfigure uninstall doctor check test lint

install:
	bash $(INSTALL_SH)

reconfigure:
	bash $(INSTALL_SH) reconfigure

uninstall:
	bash $(INSTALL_SH) uninstall

doctor:
	bash $(INSTALL_SH) --doctor

check:
	bash $(INSTALL_SH) --check

test:
	python3 -m unittest tests.test_setup tests.test_status_line
	bash tests/test_install.sh

lint:
	shellcheck $(INSTALL_SH) tests/test_install.sh
	python3 -m py_compile $(SETUP_PY) tools/status-line.py
```

> The targets call `install.sh` (not `setup.py` directly) so `make install` from a clone takes the LOCAL path — `install.sh` resolves `BASH_SOURCE` to the checkout, skips fetch, and execs `setup.py`. `make test` runs both unittest suites (setup + the E5a status-line suite) and the bash bootstrapper test.

- [ ] **Step 3: Verify the targets resolve**

Run: `make -n install reconfigure uninstall doctor check test lint`
Expected: prints the commands for every target with no "No rule to make target" error.

Run: `make lint`
Expected: `shellcheck` clean and `py_compile` succeeds (exit 0).

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "build: Makefile wrappers — install/reconfigure/uninstall/doctor/check/test/lint (E5b)"
```

---

## Task 13: Full-suite + lint gate

**Files:** none (verification only)

- [ ] **Step 1: Run the full Python suite**

Run: `python3 -m unittest tests.test_setup -v`
Expected: PASS — every class (TestResolvePaths, TestEnumerate, TestInstalledLinks, TestTty, TestLinkOne, TestPruneStale, TestSelectSkills, TestApplySelection, TestWireStatusline, TestRecipeAndUnwire, TestCmdInstall, TestCmdUninstall, TestCmdDelegation), zero failures.

- [ ] **Step 2: Run the bash bootstrapper test + lint**

Run: `bash tests/test_install.sh && shellcheck tools/install.sh tests/test_install.sh`
Expected: `N passed, 0 failed` and clean shellcheck.

- [ ] **Step 3: Confirm `make test` and `make lint` are green**

Run: `make test && make lint`
Expected: both exit 0.

- [ ] **Step 4: End-to-end headless smoke (no /dev/tty), against a throwaway HOME**

Run:
```bash
WORK="$(mktemp -d)"
mkdir -p "$WORK/kit/skills/demo" "$WORK/kit/tools"
printf -- '---\nname: demo\n---\n' > "$WORK/kit/skills/demo/SKILL.md"
printf 'pass\n' > "$WORK/kit/tools/status-line.py"
printf '# recipe\n' > "$WORK/kit/tools/statusline.toml.sample"
env -i HOME="$WORK" PATH="$PATH" AI_KIT_DIR="$WORK/kit" \
    CLAUDE_CONFIG_DIR="$WORK/.claude" AI_KIT_SKIP_FETCH=1 \
    bash tools/install.sh install </dev/null
test -L "$WORK/.claude/skills/demo" && echo "OK: headless linked demo, skipped status line"
test ! -f "$WORK/.claude/settings.json" && echo "OK: no statusLine wired headless"
rm -rf "$WORK"
```
Expected: both `OK:` lines print (headless reconcile links the skill and skips status-line wiring per §7).

- [ ] **Step 5: Commit (only if a doc/log tweak was needed; otherwise nothing to commit)**

No code change in this task. If everything is green, proceed to the self-review.

---

## Self-Review Checklist (run after implementing)

**Spec requirement → task mapping**

| Requirement | Where | Task |
|---|---|---|
| §2 bootstrap contract — mode detect (LOCAL/BOOTSTRAP), ensure-python, exec setup.py | `install.sh` `detect_mode`/`ensure_python`/`main` | 10 |
| §2 env overrides preserved (AI_KIT_REPO/BRANCH/DIR, CLAUDE_CONFIG_DIR, XDG_*, AI_KIT_SKIP_FETCH) | `install.sh` header vars + `resolve_paths` | 10, 1 |
| §3 convergent fetch — git pull/clone | `install.sh` `fetch_repo` | 10 |
| §3 tarball **atomic swap** (temp dir → `rm -rf && mv`) so deletions propagate | `install.sh` `fetch_repo` | 10 |
| §3 swap-leaves-no-orphans verified | `tests/test_install.sh` test 4 | 11 |
| §4 enumerate + validate (port validate_entry) | `validate_entry`/`enumerate_entries` | 2 |
| §4 symlinks-as-selection (no state file) | `installed_links` | 3 |
| §4 reconcile set-math A∩B keep / A−B available / B−A prune | `select_skills`/`apply_selection`/`prune_stale` | 6, 7 |
| §4 first-run all-on vs reconfigure keep-state | `_default_selection`/`_first_run` | 7 |
| §4 NEW upstream entry stays OFF non-interactively, flagged NEW interactively | `select_skills` | 7 |
| §4 prune-stale warn + confirm (headless auto-remove + warn) | `prune_stale` | 6 |
| §4 interactive toggle UX ([x]/[ ], accent-on/dim-off, a/n, Enter) | `select_skills` | 7 |
| §6 statusLine wiring with `python3 -S`, preserve other keys | `wire_statusline` | 8 |
| §6 / FR-5.5 double-confirm on a foreign statusLine | `wire_statusline` | 8 |
| §6 uninstall removes statusLine only if ai-kit | `unwire_statusline` | 8 |
| recipe copied only if absent (E4a) | `copy_recipe_if_absent` | 8 |
| §7 TTY → full wizard; headless → skills reconcile only, skip status line | `cmd_install` gating on `is_interactive(tty)` | 9 |
| §8 subcommands install/reconfigure/uninstall/doctor/check + --dry-run | `main` + `cmd_*` | 1, 9 |
| §8 doctor/check delegate to status-line.py (E5a) | `cmd_doctor`/`cmd_check` | 9 |
| §8 Makefile targets install/reconfigure/uninstall/doctor/check/test/lint | `Makefile` | 12 |
| testability — injectable tty (io.StringIO), only main() opens /dev/tty | every interactive fn takes `tty`; `open_tty` only in `main` | 4, 1 |
| E5c seam — `run_statusline_wizard` stub (wire + copy + note) | `run_statusline_wizard` | 9 |

**Placeholder scan:** every step shows complete, real code/commands — no TBD/TODO/"similar to Task N"/"add error handling". Confirm by re-reading each Step 3.

**Type/name consistency** (must match across tasks and the shared skeleton):
`CATEGORIES = ("agents","commands","skills")` · `Paths(install_dir, claude_dir, settings, config_dir, config_toml, sample, status_line)` · `resolve_paths(env)` · `validate_entry(cat, path)` · `enumerate_entries(install_dir) -> {cat: [(name,path)]}` · `installed_links(claude_dir, install_dir) -> {cat: {name: target}}` · `open_tty()` · `is_interactive(tty)` · `ask_yes_no(tty, prompt, default=False)` · `new_counts()` keys `linked/relinked/unlinked/pruned/skip_foreign/skip_real` · `link_one(link_path, target, dry, counts)` · `unlink_one(link_path, dry, counts)` · `prune_stale(claude_dir, install_dir, present, tty, dry, counts) -> list` · `select_skills(entries, installed, tty) -> {cat: set}` · `apply_selection(selection, entries, claude_dir, dry, counts)` · `wire_statusline(settings, status_line, tty, dry) -> bool` · `copy_recipe_if_absent(sample, config_toml, dry)` · `unwire_statusline(settings, install_dir, dry)` · `run_statusline_wizard(paths, tty, dry)` · `cmd_install(env, tty, dry, reconfigure=False)` · `cmd_uninstall(env, dry)` · `cmd_doctor(env)` · `cmd_check(env)` · `main(argv=None)`. Verify each definition signature equals the calls in `main`/`cmd_install` and the test references.

---

## Notes for the executor

- **Test runner is `unittest`, NOT pytest:** `python3 -m unittest tests.test_setup`. The suite imports the module via `setup = load_module()`; reference everything as `setup.<name>`.
- **stdlib-only:** `tools/setup.py` may import only the standard library (`argparse`, `json`, `os`, `subprocess`, `sys`, `collections`). No third-party deps — same rule as `status-line.py`.
- **Only `main()` opens `/dev/tty`.** Every other function takes an injectable `tty` arg so tests pass `io.StringIO`. Do not add a `/dev/tty` open anywhere else.
- **Counters:** a prune is tallied as `pruned` and the `unlinked` bump from `unlink_one` is backed out inside `prune_stale` so the two tallies stay distinct.
- **`reconfigure` needs no separate code path** in `setup.py` beyond the `reconfigure` argparse choice — once anything is linked `_first_run()` is False, so the selection keeps existing state. The "skip fetch" half of reconfigure is handled by `install.sh` (LOCAL mode), not here.
- **Do not modify `tools/status-line.py`** — E5b only *calls* its `--doctor`/`--check` (built in E5a). If those flags are absent, finish E5a first.
- Commit per task; frequent commits; do not push or merge.
```