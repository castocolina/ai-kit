#!/usr/bin/env python3
"""Read-only branch checks before the first unit start of a spec-discuss run.

Exit 0 proceeds (prints `preflight: ok`). Exit 1 is a refusal: one
`refused <reason>: <detail>` line per check that applies. Exit 2 means the
checks cannot run; the script fails closed and writes the reason to stderr.
It never writes and never runs a command that can write config. Every command
is an argv list, never a shell.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys

import secret_shapes

_PHASE = re.compile(r"\d+(\.\d+)?")
_UNIT_LINE = re.compile(
    r"unit \S+ branch (\S+) parent \S+ state \S+ exists (yes|no) tip ([0-9a-f]{12}|none)")
_TOKEN = re.compile(r"\{[^{}]*\}")
_STRATEGIES = ("none", "phase", "milestone")
_DEFAULT_TEMPLATE = "gsd/phase-{phase}-{slug}"
# Cyrillic to ASCII, applied before the ASCII slug filter. Soft and hard signs drop.
_CYRILLIC: dict[str, str] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
    "є": "ye", "і": "i", "ї": "yi", "ґ": "g", "ў": "u",
}


class CannotCheck(Exception):
    """A check cannot be completed; the caller fails closed."""


def _run(argv, repo, run=subprocess.run):
    try:
        proc = run(argv, cwd=repo, capture_output=True, text=True, check=False, timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        raise CannotCheck(f"{argv[0]} did not run") from error
    if proc.returncode != 0:
        raise CannotCheck(f"{' '.join(argv[-4:])} exited {proc.returncode}")
    return proc.stdout


def _last_line(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _config(gsd, repo, key, default, run=subprocess.run):
    argv = [*shlex.split(gsd), "query", "config-get", key, "--default", default, "--raw"]
    return _last_line(_run(argv, repo, run))


def padded(phase):
    """Zero-pad the integer part of a phase number; keep a decimal suffix."""
    whole, dot, decimal = phase.partition(".")
    return whole.zfill(2) + dot + decimal


def phase_dir_name(root, phase):
    """The one directory under `root` whose name starts with the padded phase."""
    try:
        names = os.listdir(root)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise CannotCheck(f"cannot read {root}") from error
    prefix = f"{padded(phase)}-"
    found = [name for name in names
             if name.startswith(prefix) and os.path.isdir(os.path.join(root, name))]
    if not found:
        return None
    if len(found) > 1:
        raise CannotCheck(f"{len(found)} directories for phase {phase}")
    return found[0]


def phase_slug(repo, phase):
    """The raw directory suffix after the padded phase, or None when no directory exists."""
    root = os.path.join(repo, ".planning", "phases")
    name = phase_dir_name(root, phase)
    if name is None:
        return None
    slug = name[len(padded(phase)) + 1:]
    if not slug:
        raise CannotCheck(f"empty slug for phase {phase}")
    return slug


def _latin(char):
    mapped = _CYRILLIC.get(char)
    return char if mapped is None else mapped


def gsd_slug(raw):
    """Transliterate, then keep only ASCII slug characters (first-pass, no truncation)."""
    text = "".join(_latin(char) for char in raw.lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def gsd_name(template, phase, slug):
    """Render a branch name by replacing the first `{phase}` and the first `{slug}`."""
    return template.replace("{phase}", padded(phase), 1).replace("{slug}", slug, 1)


def fold_name(template, phase, slug):
    """Render a branch name with the fold rule (named `{phase}` and `{slug}` only)."""
    try:
        return template.format(phase=padded(phase), slug=slug)
    except (ValueError, IndexError, KeyError) as error:
        raise CannotCheck("the branch template cannot be formatted") from error


def bad_token(template):
    """The first brace token that is neither `{phase}` nor `{slug}`, or None."""
    for match in _TOKEN.finditer(template):
        token = match.group(0)
        if token not in ("{phase}", "{slug}"):
            return token
    return None


def mismatch_line(phase, gsd, unit):
    """The refusal line when the two rendered names differ, else None."""
    if gsd == unit:
        return None
    return (f"refused gsd_branch_mismatch: phase {phase}: GSD branch {gsd} "
            f"differs from unit branch {unit} (strategy phase)")


def _settings(gsd, repo, run=subprocess.run):
    """Strategy plus the two templates. A nested strategy wins over the flat key."""
    flat = _config(gsd, repo, "branching_strategy", "none", run)
    strategy = _config(gsd, repo, "git.branching_strategy", flat, run)
    if strategy not in _STRATEGIES:
        raise CannotCheck(f"unknown branching strategy {strategy!r}")
    if strategy == "none":
        return strategy, None, None
    fold_template = _config(gsd, repo, "git.phase_branch_template", _DEFAULT_TEMPLATE, run)
    gsd_template = _config(gsd, repo, "phase_branch_template", fold_template, run)
    return strategy, gsd_template, fold_template


def _name_refusals(strategy, gsd_template, fold_template, phase, slug):
    unit = fold_name(fold_template, phase, slug)
    if strategy == "milestone":
        return [f"refused gsd_branch_mismatch: phase {phase}: strategy milestone puts "
                f"the phase on one milestone branch, not unit branch {unit}"]
    normal = gsd_slug(slug)
    if not normal:
        return [f"refused gsd_branch_mismatch: phase {phase}: "
                f"GSD reads no slug from directory suffix {slug}"]
    line = mismatch_line(phase, gsd_name(gsd_template, phase, normal), unit)
    return [line] if line else []


def _deferred(phase):
    return f"deferred {phase}: no phase directory yet"


def _workstream_refusal(phase, ws):
    return (f"refused gsd_branch_mismatch: phase {phase}: unit flow cannot see the phase "
            f"directory under .planning/workstreams/{ws}/phases")


def _collect_slugs(repo, phases, ws):
    """Per phase: a workstream refusal, a deferral, or the directory slug."""
    refusals, deferred, found = [], [], {}
    for phase in phases:
        if ws is not None:
            root = os.path.join(repo, ".planning", "workstreams", ws, "phases")
            if phase_dir_name(root, phase) is not None:
                refusals.append(_workstream_refusal(phase, ws))
                continue
        slug = phase_slug(repo, phase)
        if slug is None:
            deferred.append(_deferred(phase))
            continue
        found[phase] = slug
    return refusals, deferred, found


def _template_refusal(gsd_template, fold_template):
    token = bad_token(gsd_template) or bad_token(fold_template)
    if token is None:
        return None
    return f"refused gsd_branch_mismatch: template has a token the unit flow cannot render: {token}"


def check_names(gsd, repo, phases, ws=None, run=subprocess.run):
    """Refusals and deferrals for the named phases. Strategy `none` skips name checks."""
    refusals, deferred, found = _collect_slugs(repo, phases, ws)
    strategy, gsd_template, fold_template = _settings(gsd, repo, run)
    if strategy == "none" or not found:
        return refusals, deferred
    token = _template_refusal(gsd_template, fold_template)
    if token is not None:
        return [*refusals, token], deferred
    for phase, slug in found.items():
        refusals += _name_refusals(strategy, gsd_template, fold_template, phase, slug)
    return refusals, deferred


def _fold_remote(fold_py, repo, run=subprocess.run):
    out = _run([sys.executable, fold_py, "settings", "show", "--repo", repo], repo, run)
    values = dict(line.split(": ", 1) for line in out.splitlines() if ": " in line)
    remote = values.get("remote", "").strip()
    targets = values.get("targets", "").strip()
    if not remote or not targets:
        raise CannotCheck("fold settings show printed no remote or targets line")
    return remote, targets.split(",")[0].strip()


def _head_rows(repo, remote, target, recorded, run):
    held = [f"refs/heads/{branch}" for branch, exists in recorded.items() if exists]
    trunk = f"refs/remotes/{remote}/{target}"
    found = _run(["git", "-C", repo, "for-each-ref", "--count=1", "--format=%(refname)", trunk],
                 repo, run).strip()
    # no tracking ref yet: count what no remote ref and no listed unit holds
    excluded = [trunk] if found else ["--remotes"]
    log = _run(["git", "-C", repo, "log", "--format=%H%x09%s", "HEAD", "--not", *excluded, *held],
               repo, run)
    return [line.split("\t", 1) for line in log.splitlines() if "\t" in line]


def _redact(subject):
    return secret_shapes.redact(subject, "[redacted]")


def _head_line(head, rows):
    shown = "; ".join(f"{sha[:12]} {_redact(subject)}" for sha, subject in rows[:10])
    if len(rows) > 10:
        shown += f"; and {len(rows) - 10} more"
    return (f"refused unrecorded_head: HEAD branch {head} is not a recorded unit and holds "
            f"{len(rows)} commit(s) the trunk lacks: {shown}")


def check_head(fold_py, repo, recorded, run=subprocess.run):
    """At most one refusal when HEAD is an unrecorded branch holding local commits."""
    head = _run(["git", "-C", repo, "branch", "--show-current"], repo, run).strip()
    if not head or head in recorded:
        return []
    remote, target = _fold_remote(fold_py, repo, run)
    remotes = _run(["git", "-C", repo, "remote"], repo, run).split()
    # no remote: start refuses no_remote and the unit flow is off
    if remote not in remotes:
        return []
    rows = _head_rows(repo, remote, target, recorded, run)
    return [_head_line(head, rows)] if rows else []


def read_units(path):
    """Map each listed branch to whether it exists. `units: none` is an empty map."""
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        raise CannotCheck(f"cannot read {path}") from error
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines == ["units: none"]:
        return {}
    if not lines:
        raise CannotCheck("bad units line: (empty)")
    recorded = {}
    for line in lines:
        match = _UNIT_LINE.fullmatch(line)
        if match is None:
            raise CannotCheck(f"bad units line: {line}")
        recorded[match.group(1)] = match.group(2) == "yes"
    return recorded


def _bad_args(args, phases):
    if not phases:
        return "no phase given"
    for item in phases:
        if not _PHASE.fullmatch(item):
            return f"bad phase {item}"
    if args.ws is not None and ("/" in args.ws or "\\" in args.ws or ".." in args.ws):
        return "bad workstream name"
    try:
        shlex.split(args.gsd)
    except ValueError:
        return "--gsd cannot be split"
    return None


def _report(deferred, refusals):
    for line in deferred:
        print(line)
    for line in refusals:
        print(line)
    if refusals:
        return 1
    print("preflight: ok")
    return 0


def main(argv=None) -> int:
    """Run the read-only checks. Exit 0 proceed, 1 refused, 2 cannot check."""
    parser = argparse.ArgumentParser(prog="branch_preflight.py")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--gsd", required=True)
    parser.add_argument("--fold-py", required=True)
    parser.add_argument("--phases", required=True)
    parser.add_argument("--units", required=True)
    parser.add_argument("--ws", default=None)
    args = parser.parse_args(argv)
    phases = [item.strip() for item in args.phases.split(",") if item.strip()]
    problem = _bad_args(args, phases)
    if problem is not None:
        print(f"preflight: cannot check: {problem}", file=sys.stderr)
        return 2
    try:
        recorded = read_units(args.units)
        refusals, deferred = check_names(args.gsd, args.repo, phases, args.ws)
        refusals += check_head(args.fold_py, args.repo, recorded)
    except CannotCheck as error:
        print(f"preflight: cannot check: {error}", file=sys.stderr)
        return 2
    return _report(deferred, refusals)


if __name__ == "__main__":
    sys.exit(main())
