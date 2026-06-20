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
import re
import subprocess
import sys
import tempfile
import tomllib
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


# ── Status-line config defaults (mirrors status-line.py SEGMENTS/LAYOUT) ───────
# Duplicated here, not imported: status-line.py's hyphenated filename isn't an
# importable module, and the wizard must run even while the renderer is mid-edit.
# TestTomlRead.test_segment_defaults_match_recipe_drift pins these to the recipe.
SEGMENT_DEFAULTS = {
    "path": True, "branch": True, "dirty": True, "worktree": True, "todo": True,
    "model": True, "time_ago": True, "clock": True, "effort": True,
    "lines": True, "cost": False, "total_time": True, "api_time": True,
    "render_time": True, "slowest": True, "dimensions": False, "context": True,
    "chat_size": True, "memory": True, "rate_limits": True,
}
LAYOUT_DEFAULTS = [
    {"min_rows": 0, "segments": ["path", "branch", "dirty", "todo"]},
    {"min_rows": 20, "segments": ["model", "time_ago", "clock", "effort", "lines",
                                  "cost", "total_time", "api_time"]},
    {"min_rows": 30, "segments": ["render_time", "dimensions", "context",
                                  "chat_size", "memory", "rate_limits", "slowest"]},
]


def read_toml(path):
    """Parse the TOML at `path`. Missing / empty / malformed → {} (never raises).
    Read-only — the wizard writes back via surgical text patch, not re-emit."""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, IsADirectoryError):
        return {}
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def current_segments(path):
    """Resolved {key: bool}: SEGMENT_DEFAULTS merged with the file's [segments].
    Unknown keys and non-bool values in the file are ignored (defaults win), the
    same lenient policy the renderer applies."""
    seg = dict(SEGMENT_DEFAULTS)
    for k, v in (read_toml(path).get("segments") or {}).items():
        if k in seg and isinstance(v, bool):
            seg[k] = v
    return seg


def current_layout(path):
    """Resolved layout as a list of {"min_rows": int, "segments": [str]} dicts.
    Any [[line]] block in the file REPLACES the whole layout (all-or-nothing,
    matching the renderer); otherwise the default 3-row layout (deep-copied)."""
    raw = read_toml(path).get("line")
    if not raw:
        return [{"min_rows": r["min_rows"], "segments": list(r["segments"])}
                for r in LAYOUT_DEFAULTS]
    return [{"min_rows": int(item.get("min_rows", 0)),
             "segments": list(item.get("segments", []))} for item in raw]


def _bool_env(value):
    return "1" if value else "0"


def render_preview(status_line, segments, sample_json, env):
    """Render the status line with the given segment toggles, for the live preview.

    Shells out to `python3 status-line.py` feeding `sample_json` on stdin and the
    toggles as CC_AI_KIT_SEGMENT_<KEY> env overrides (so it reflects in-memory
    edits before they are written). `env` carries only the keys to override
    (e.g. forced terminal size); it is merged ON TOP OF os.environ so the
    subprocess inherits PATH, HOME, and PYTHONPATH.
    Returns the rendered text ("" on any failure — the preview is best-effort
    and must never crash the wizard)."""
    child = {**os.environ, **env}   # inherit full env; overrides layer on top
    # Force a wide, tall terminal so all rows/segments render in the preview
    # regardless of the wizard's own window size.
    child.setdefault("STATUSLINE_COLS", "200")
    child.setdefault("STATUSLINE_LINES", "40")
    for key, on in segments.items():
        child[f"CC_AI_KIT_SEGMENT_{key.upper()}"] = _bool_env(on)
    try:
        proc = subprocess.run(
            [sys.executable, "-S", status_line],
            input=sample_json, capture_output=True, text=True,
            env=child, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.rstrip("\n")


# One-line doc notes carried when a managed key is appended (keeps the recipe
# self-documenting). Lifted verbatim from tools/statusline.toml.sample comments.
_SEGMENT_NOTES = {
    "path": "📂 working directory, ~-relative   (pinned)",
    "branch": "git branch name",
    "dirty": "working-tree dirty marker",
    "worktree": "⎇ active linked-worktree name",
    "todo": "📝 current TODO  (📝 in-progress / ⏸ pending)",
    "model": "active model name (e.g. Opus)",
    "time_ago": "time since the session's first message",
    "clock": "⏰ current wall-clock time",
    "effort": "🧠 reasoning-effort ladder + level ([auto] when auto)",
    "lines": "📃 lines added / removed this session",
    "cost": "🪙 session cost in USD            (OFF by default)",
    "total_time": "💬 total session duration",
    "api_time": "📡 cumulative API response time",
    "render_time": "⏱ status-line's own render time, SLO/SLA-colored",
    "slowest": "🐌 slowest single segment this render (name + duration)",
    "dimensions": "terminal size cols×lines (? if assumed)  (debug; OFF by default)",
    "context": "📊 context-window % used (and max) (pinned)",
    "chat_size": "💾 transcript file size on disk",
    "memory": "🧮 status-line process memory (RSS)",
    "rate_limits": "⚡ rate-limit buckets with reset time",
}

# A managed key line, optionally commented, capturing key + trailing comment:
#   "# cost = false   # 🪙 ..."   ->  key="cost", trailing="# 🪙 ..."
_KEY_RE = re.compile(
    r"^(?P<indent>\s*)#?\s*(?P<key>\w+)\s*=\s*[^#\n]*?(?P<trail>\s*#.*)?$")


def _header_name(line):
    """The bracketed header name on `line` (commented or not), else None.
    "# [segments]" -> "segments"; "[ramp.context]" -> "ramp.context"."""
    m = re.match(r"^\s*#?\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*$", line)
    return m.group(1) if m else None


def patch_segments(text, changes):
    """Surgically set the given {key: bool} segment toggles in `text`'s raw TOML.

    Key-granularity: rewrites ONLY each changed key's `key = value` line in place
    (uncommenting it and the [segments] header), appends a missing key with its
    doc note, and leaves every other byte — comments, [palette], [ramp.*],
    [external], the version line — untouched. Returns the patched text."""
    if not changes:
        return text
    lines = text.splitlines(keepends=True)
    out = []
    in_seg = False
    seg_header_idx = None          # index in `out` of the [segments] header line
    written = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        name = _header_name(line)
        if name is not None:                       # a section header
            if in_seg:                             # leaving [segments]: append rest
                _append_missing(out, changes, written)
                in_seg = False
            if name == "segments":
                in_seg = True
                seg_header_idx = len(out)
                out.append(line)                   # may be uncommented below
                i += 1
                continue
            out.append(line)
            i += 1
            continue
        if in_seg:
            m = _KEY_RE.match(line)
            if m and m.group("key") in changes:
                key = m.group("key")
                trail = m.group("trail") or ""
                nl = "\n" if line.endswith("\n") else ""
                out.append(f"{m.group('indent')}{key} = "
                           f"{'true' if changes[key] else 'false'}{trail}{nl}")
                written.add(key)
                i += 1
                continue
        out.append(line)
        i += 1
    if in_seg:                                     # [segments] ran to EOF
        _append_missing(out, changes, written)
    # If we wrote any live key, the [segments] header must be live too.
    if written and seg_header_idx is not None:
        out[seg_header_idx] = re.sub(r"^(\s*)#\s*", r"\1", out[seg_header_idx], count=1)
    return "".join(out)


def _append_missing(out, changes, written):
    """Append any not-yet-written changed segment keys to the end of the
    [segments] block, each with its recipe doc note."""
    for key, val in changes.items():
        if key in written:
            continue
        note = _SEGMENT_NOTES.get(key, "")
        comment = f"          # {note}" if note else ""
        out.append(f"{key} = {'true' if val else 'false'}{comment}\n")
        written.add(key)


def _render_line_blocks(lines):
    """The full [[line]] section as live TOML text (all-or-nothing).

    Emits ONLY the TOML [[line]] blocks — no ## comment headers — so the
    output is byte-identical across re-runs (idempotent)."""
    chunks = []
    for row in lines:
        segs = ", ".join(f'"{s}"' for s in row["segments"])
        chunks.append(f"[[line]]\nmin_rows = {int(row['min_rows'])}\n"
                      f"segments = [{segs}]\n")
    return "".join(chunks)


def patch_layout(text, lines):
    """Replace the file's [[line]] layout with `lines` (all-or-nothing), preserving
    every other section byte-for-byte. `lines` is a list of
    {"min_rows": int, "segments": [str]} dicts.

    Idempotent: running patch_layout twice yields a byte-identical result. Any
    prior wizard-authored `##` comment lines immediately preceding the [[line]]
    region are stripped during the parse pass so they do not accumulate."""
    src = text.splitlines(keepends=True)
    out = []
    block = _render_line_blocks(lines)
    region_start = None
    i = 0
    n = len(src)
    while i < n:
        name = _header_name(src[i])
        if name == "line":
            # Consume the whole contiguous [[line]] region: this header, its body,
            # and any immediately-following [[line]] headers + bodies.
            if region_start is None:
                # Also strip any wizard-authored ## header lines that immediately
                # precede this [[line]] block (they would accumulate on re-runs).
                while out and out[-1].lstrip().startswith("##"):
                    out.pop()
                region_start = len(out)
            i += 1
            while i < n:
                nm = _header_name(src[i])
                if nm == "line":
                    i += 1
                    continue
                if nm is None:
                    # a body line (min_rows / segments / blank) — part of the region
                    if src[i].strip() == "" or re.match(r"^\s*#?\s*(min_rows|segments)\b",
                                                         src[i]):
                        i += 1
                        continue
                break
            continue
        out.append(src[i])
        i += 1
    if region_start is None:                 # no [[line]] region existed: append
        if out and not out[-1].endswith("\n"):
            out.append("\n")
        out.append(block)
    else:
        out.insert(region_start, block)
    return "".join(out)


def write_toml_preserving(path, text, status_line):
    """Atomically write `text` to `path`, then self-validate via the doctor.

    Writes to a sibling temp file and os.replace()s it into place (atomic). Then
    runs `status-line.py --doctor` against the result (CC_AI_KIT_CONFIG=path); if
    the doctor reports problems, the previous file content is restored and False
    is returned — the wizard must never leave a broken config (§5.1). Returns True
    on success."""
    prev = None
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            prev = f.read()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        return False
    env = dict(os.environ)
    env["CC_AI_KIT_CONFIG"] = path
    try:
        proc = subprocess.run([sys.executable, "-S", status_line, "--doctor"],
                              capture_output=True, text=True, env=env, timeout=10)
        ok = proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    if not ok:
        if prev is None:
            os.unlink(path)
        else:
            # Restore the prior (already-valid) content atomically too, so an
            # interrupted revert can't leave a truncated config behind.
            rfd, rtmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".",
                                         suffix=".tmp")
            try:
                with os.fdopen(rfd, "w", encoding="utf-8") as f:
                    f.write(prev)
                os.replace(rtmp, path)
            except OSError:
                if os.path.exists(rtmp):
                    os.unlink(rtmp)
        return False
    return True


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


def _tty_write(tty, text):
    """Write to the tty without consuming pending input. An io.StringIO shares
    one buffer for reads and writes; a naive write at the read cursor would
    clobber seeded test input. We append the prompt at the END of the buffer and
    restore the read cursor, so seeded input survives. A real /dev/tty is not
    seekable (separate read/write underneath), so we just write."""
    try:
        read_pos = tty.tell()
        tty.seek(0, 2)  # end of buffer
        tty.write(text)
        tty.seek(read_pos)
    except (IOError, OSError, ValueError):
        tty.write(text)
    tty.flush()


def ask_yes_no(tty, prompt, default=False):
    """Prompt on the tty for a yes/no. Blank line or EOF returns `default`.
    Accepts y/yes/n/no (case-insensitive)."""
    suffix = " [Y/n] " if default else " [y/N] "
    _tty_write(tty, prompt + suffix)
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
        banner = "\nThese ai-kit links point at entries removed upstream:\n"
        banner += "".join("  - %s\n" % item for item in stale)
        _tty_write(tty, banner)
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


def predecessor_candidates(claude_dir, install_dir, entries):
    """List (cat, name, old_target, new_target) for links left by a PREVIOUS
    ai-kit install (e.g. a renamed repo uz-kit -> ai-kit). A candidate is a
    symlink at <claude>/<cat>/<name> that is foreign to the CURRENT install_dir
    yet carries the ai-kit <root>/<cat>/<name> shape (target basename == name,
    its parent dir name == cat) AND whose <name> is a current repo entry, so it
    can be re-pointed. Unrelated foreign symlinks (different shape, or no current
    entry) are excluded — we never touch a link that isn't recognizably ours."""
    out = []
    for cat in CATEGORIES:
        by_name = dict(entries.get(cat, []))
        dest = os.path.join(claude_dir, cat)
        if not os.path.isdir(dest):
            continue
        for name in sorted(os.listdir(dest)):
            link = os.path.join(dest, name)
            if not os.path.islink(link):
                continue
            old = os.readlink(link)
            if _is_inside(old, install_dir):
                continue                       # already a current ai-kit link
            if os.path.basename(old) != name:
                continue                       # not the ai-kit <cat>/<name> shape
            if os.path.basename(os.path.dirname(old)) != cat:
                continue
            if name not in by_name:
                continue                       # nothing current to re-point to
            out.append((cat, name, old, by_name[name]))
    return out


def adopt_predecessor_links(claude_dir, install_dir, entries, tty, dry, counts):
    """Resolve links from a previous ai-kit install. Interactive: list them and
    ask whether to re-point to THIS install (default) or drop them. Headless:
    warn only and leave them alone — never silently clobber a foreign link.
    Returns the list of 'cat/name' candidates found."""
    cands = predecessor_candidates(claude_dir, install_dir, entries)
    items = ["%s/%s" % (cat, name) for cat, name, _, _ in cands]
    if not cands:
        return []
    if not is_interactive(tty):
        for it in items:
            print("warn: %s links to a previous ai-kit install — run setup "
                  "interactively to re-point or drop it" % it, file=sys.stderr)
        return items
    banner = "\nThese links point at a PREVIOUS ai-kit install (e.g. a renamed repo):\n"
    banner += "".join("  - %s\n" % it for it in items)
    _tty_write(tty, banner)
    repoint = ask_yes_no(tty, "re-point them to this install? ('n' = drop them)",
                         default=True)
    for cat, name, _old, new_target in cands:
        link = os.path.join(claude_dir, cat, name)
        if not dry:
            if os.path.lexists(link):
                os.remove(link)
            if repoint:
                os.symlink(new_target, link)
        counts["relinked" if repoint else "pruned"] += 1
    return items


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
    # flat numbered index over all categories, skills first (the row order the
    # wizard presents; CATEGORIES itself stays alphabetical for storage).
    _row_order = ("skills", "commands", "agents")
    rows = []
    for cat in _row_order:
        for name, path in entries[cat]:
            rows.append((cat, name, path))
    while True:
        menu = ("\nSelect what to install (type numbers to toggle, "
                "'a' all, 'n' none, Enter to accept):\n")
        for i, (cat, name, _path) in enumerate(rows, 1):
            on = name in sel[cat]
            mark = "x" if on else " "
            color = _ACCENT if on else _DIM
            new = "" if (name in installed[cat] or _first_run(installed)) else "  NEW"
            menu += ("  %2d. [%s] %s%s/%s%s%s\n"
                     % (i, mark, color, cat, name, _RESET, new))
        _tty_write(tty, menu)
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
        _tty_write(tty, "\nsettings.json already sets a status line:\n  %s\n" % cur_cmd)
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


def _segment_changes_vs_recipe(path, segments):
    """The {key: bool} subset of `segments` that DIFFERS from what `path` currently
    resolves to — the minimal set of segment keys to patch (key granularity)."""
    current = current_segments(path)
    return {k: v for k, v in segments.items() if current.get(k) != v}


def save_statusline_config(path, seg_changes, layout, status_line):
    """Apply the managed edits to the file at `path` via surgical text patches,
    then atomically write + doctor-validate. `seg_changes` is the minimal changed
    {key: bool}; `layout` is None (unchanged) or the full list of line dicts.
    Returns True on success."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if seg_changes:
        text = patch_segments(text, seg_changes)
    if layout is not None:
        text = patch_layout(text, layout)
    return write_toml_preserving(path, text, status_line)


def _find_line(layout, seg):
    for li, row in enumerate(layout):
        if seg in row["segments"]:
            return li, row["segments"].index(seg)
    return None, None


def _apply_wizard_command(state, cmd):
    """Pure state transition for one wizard command. Returns (new_state, error):
    on success error is None; on a bad command new_state is `state` unchanged and
    error is a human message. Recognized: a segment number, `move <seg> up|down`,
    `move <seg> line <n>`."""
    import copy
    cmd = cmd.strip()
    st = copy.deepcopy(state)
    order = sorted(st["segments"])
    if cmd.isdigit():
        n = int(cmd)
        if not (1 <= n <= len(order)):
            return state, f"no segment #{n}"
        key = order[n - 1]
        st["segments"][key] = not st["segments"][key]
        st["dirty"] = True
        return st, None
    parts = cmd.split()
    if len(parts) >= 3 and parts[0] == "move":
        seg = parts[1]
        li, pos = _find_line(st["layout"], seg)
        if li is None or pos is None:        # _find_line returns both-or-neither
            return state, f"segment '{seg}' is not in the layout"
        if parts[2] == "up" and pos > 0:
            row = st["layout"][li]["segments"]
            row[pos - 1], row[pos] = row[pos], row[pos - 1]
            st["dirty"] = True
            return st, None
        if parts[2] == "down" and pos < len(st["layout"][li]["segments"]) - 1:
            row = st["layout"][li]["segments"]
            row[pos + 1], row[pos] = row[pos], row[pos + 1]
            st["dirty"] = True
            return st, None
        if parts[2] == "line" and len(parts) == 4 and parts[3].isdigit():
            dst = int(parts[3]) - 1
            if not (0 <= dst < len(st["layout"])):
                return state, f"no line #{parts[3]}"
            st["layout"][li]["segments"].remove(seg)
            st["layout"][dst]["segments"].append(seg)
            st["dirty"] = True
            return st, None
        return state, f"can't move '{seg}' {' '.join(parts[2:])}"
    return state, f"unknown command: {cmd!r}"


def _print_segments(tty, state):
    """Render the numbered segment list with [x]/[ ] + accent/dim + note."""
    accent, dim, reset = "\033[36m", "\033[90m", "\033[0m"
    for i, key in enumerate(sorted(state["segments"]), start=1):
        on = state["segments"][key]
        box = "[x]" if on else "[ ]"
        color = accent if on else dim
        note = _SEGMENT_NOTES.get(key, "")
        print(f"  {i:2}. {box} {color}{key}{reset}  {dim}{note}{reset}", file=tty)


def run_statusline_wizard(paths, tty, dry):
    """Interactive status-line editor: toggle segments, reorder/move across lines,
    live-preview after each change, write back via surgical patch + doctor
    self-validate. Replaces the E5b stub.

    Preamble (preserved from E5b): drop the recipe at config_toml if absent and
    wire settings.json's statusLine at the bundled renderer (FR-5.5 double-confirm)
    before the editor runs."""
    copy_recipe_if_absent(paths.sample, paths.config_toml, dry)
    wire_statusline(paths.settings, paths.status_line, tty, dry)
    cfg = paths.config_toml
    state = {
        "segments": current_segments(cfg),
        "layout": current_layout(cfg),
        "dirty": False,
    }
    with open(_sample_input_path()) as f:
        sample_json = f.read()

    def show_preview():
        out = render_preview(paths.status_line, state["segments"], sample_json, {})
        print("\n  ── live preview ──", file=tty)
        print(out or "  (preview unavailable)", file=tty)

    print("\nStatus-line configuration", file=tty)
    while True:
        _print_segments(tty, state)
        show_preview()
        print("\n  commands: <n> toggle · move <seg> up|down · move <seg> line <n>"
              " · p preview · s save · q quit", file=tty)
        tty.write("  > ")
        tty.flush()
        cmd = tty.readline()
        if not cmd:
            cmd = "q"
        cmd = cmd.strip()
        if cmd in ("q", "quit", ""):
            break
        if cmd in ("p", "preview"):
            continue
        if cmd in ("s", "save"):
            _save_and_report(paths, state, tty, dry)
            state["dirty"] = False
            continue
        new_state, err = _apply_wizard_command(state, cmd)
        if err:
            print(f"  ! {err}", file=tty)
        else:
            state = new_state

    if state["dirty"]:
        _save_and_report(paths, state, tty, dry)
    else:
        _print_closing(paths, tty)


def _save_and_report(paths, state, tty, dry):
    if dry:
        print("  [dry-run] would write status-line config — no changes made",
              file=tty)
        _print_closing(paths, tty)
        return
    seg_changes = _segment_changes_vs_recipe(paths.config_toml, state["segments"])
    layout = state["layout"] if state["layout"] != current_layout(paths.config_toml) \
        else None
    if not (seg_changes or layout is not None):
        _print_closing(paths, tty)
        return
    ok = save_statusline_config(paths.config_toml, seg_changes, layout,
                                paths.status_line)
    if ok:
        print("  ✓ saved", file=tty)
    else:
        print("  ! the doctor rejected the change — file left unchanged", file=tty)
    _print_closing(paths, tty)


def _print_closing(paths, tty):
    print(f"\n  config: {paths.config_toml}", file=tty)
    print(f"  edit colors / ramps / palette by hand in that file.", file=tty)
    # _doctor_cmd(paths) is defined in E5b — reuse it; do NOT redefine it here.
    print(f"  validate any time:  {_doctor_cmd(paths)}", file=tty)


def _sample_input_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "tests", "fixtures", "sample-input.json")


def cmd_install(env, tty, dry, reconfigure=False):
    """Reconcile skills/agents/commands, then (interactive only) the status line.
    Headless (tty None): reconcile skills with defaults/keep + auto-remove dead
    links + warn, and SKIP the status line entirely (§7). `reconfigure` is just
    install without first-run defaults — handled implicitly because once anything
    is linked, _first_run() is False, so the selection keeps existing state."""
    paths = resolve_paths(env)
    entries = enumerate_entries(paths.install_dir)
    counts = new_counts()

    # B − A: links whose repo entry vanished upstream — warn + prune
    present = {cat: {n for n, _ in entries[cat]} for cat in CATEGORIES}
    prune_stale(paths.claude_dir, paths.install_dir, present, tty, dry, counts)

    # Links from a PREVIOUS ai-kit install (renamed repo) — offer re-point / drop.
    # Re-pointed links become current ai-kit links, so refresh `installed` after.
    adopt_predecessor_links(paths.claude_dir, paths.install_dir, entries, tty, dry, counts)
    installed = installed_links(paths.claude_dir, paths.install_dir)

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
    return "%s %s --doctor" % (os.path.basename(sys.executable) or "python3",
                               paths.status_line)


def cmd_doctor(env):
    """Delegate to status-line.py --doctor (E5a); return its exit code. Run under
    THIS interpreter (not a bare 'python3' PATH lookup) so the doctor validates
    with the same Python the wizard writes/validates the config with."""
    paths = resolve_paths(env)
    return subprocess.call([sys.executable, "-S", paths.status_line, "--doctor"])


def cmd_check(env):
    """Delegate to status-line.py --check (E5a); return its exit code."""
    paths = resolve_paths(env)
    return subprocess.call([sys.executable, "-S", paths.status_line, "--check"])


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
