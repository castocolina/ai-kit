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


def run_statusline_wizard(paths, tty, dry):
    """E5b stub: wire the statusLine (with FR-5.5 double-confirm), copy the recipe
    if absent, and print a note that interactive segment editing arrives in E5c.
    E5c replaces this body with the full segment-toggle / reorder / preview wizard."""
    copy_recipe_if_absent(paths.sample, paths.config_toml, dry)
    wired = wire_statusline(paths.settings, paths.status_line, tty, dry)
    if is_interactive(tty):
        _tty_write(tty, "\nStatus line: %s\n"
                   % ("wired" if wired else "left as-is"))
        _tty_write(tty, "Config lives at %s — edit colors/ramps by hand there.\n"
                   % paths.config_toml)
        _tty_write(tty, "Interactive segment editing arrives in E5c.\n")
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
