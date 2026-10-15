#!/usr/bin/env python3
"""Audit Mermaid blocks in Markdown: extract -> render (mmdc) -> report.

Recommended entrypoint. Stdlib only (no Python deps); needs `mmdc` for the
render step. For every ```mermaid block in a .md file — or every .md under a
directory — this extracts the block, renders it with mmdc, and reports

    <file>:<line>\t<OK|SYNTAX|NOT-VERIFIED>\t<message>

The debug signal is mmdc's own stderr: a `Parse error on line N…` is captured
and N is mapped back to the real .md line. Pass --keep-png to also keep the
rendered images for the visual / layout pass (and the rare "bomb" error card).

Usage:
    audit_mermaid.py [--out DIR] [--keep-png] [--pptr FILE] <target.md | dir>
"""
import argparse
import contextlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass

from mermaid_style import (
    extract,
    extract_style_facts,
    geometry_findings,
    iter_md,
    png_size,
)

LINE_RE = re.compile(r"line (\d+)", re.IGNORECASE)


@dataclass
class RunConfig:
    out_dir: str
    pptr: str
    have_mmdc: bool
    keep_png: bool


@dataclass
class BlockJob:
    md: str
    start: int
    body: str
    idx: int
    cfg: RunConfig


def render(mmd_path, png_path, pptr):
    p = subprocess.run(
        ["mmdc", "-p", pptr, "-i", mmd_path, "-o", png_path],
        capture_output=True,
        text=True,
        check=False,
    )
    return p.returncode, (p.stderr or p.stdout)


def _syntax_message(err):
    """First useful diagnostic line from mmdc stderr."""
    cand = [
        line.strip()
        for line in err.splitlines()
        if re.search(r"parse error|expecting|got ", line, re.I)
        and "http" not in line
        and "node:" not in line
        and " at " not in line
    ]
    if cand:
        return " ".join(cand)[:300]
    lines = err.strip().splitlines()
    return (lines[0] if lines else "")[:300]


def _print_geometry(md, start, body, png):
    if not os.path.exists(png):
        return
    dims = png_size(png)
    if not dims:
        return
    n_nodes = len(extract_style_facts(body).nodes)
    for g in geometry_findings(dims[0], dims[1], n_nodes):
        print(f"{md}:{start}\tGEOMETRY\t{g.rule}\t{g.message}\t→ {g.fix}")


def _maybe_remove_png(png, keep_png):
    if not keep_png:
        with contextlib.suppress(OSError):
            os.remove(png)


def _audit_one_block(job):
    cfg = job.cfg
    if not cfg.have_mmdc:
        print(f"{job.md}:{job.start}\tNOT-VERIFIED\t")
        return None

    safe = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.relpath(job.md))
    mmd = os.path.join(cfg.out_dir, f"{safe}__{job.idx}__L{job.start}.mmd")
    with open(mmd, "w", encoding="utf-8") as fh:
        fh.write(job.body)

    png = mmd + ".png"
    rc, err = render(mmd, png, cfg.pptr)
    if rc == 0:
        print(f"{job.md}:{job.start}\tOK\t")
        _print_geometry(job.md, job.start, job.body, png)
        _maybe_remove_png(png, cfg.keep_png)
        return True

    m = LINE_RE.search(err)
    loc = job.start + int(m.group(1)) - 1 if m else job.start
    msg = _syntax_message(err)
    print(f"{job.md}:{loc}\tSYNTAX\t{msg}")
    _maybe_remove_png(png, cfg.keep_png)
    return False


def _default_puppeteer(out_dir, pptr_arg):
    if pptr_arg:
        return pptr_arg
    pptr = os.path.join(out_dir, "puppeteer-config.json")
    with open(pptr, "w", encoding="utf-8") as fh:
        fh.write('{ "args": ["--no-sandbox", "--disable-setuid-sandbox"] }\n')
    return pptr


def _warn_missing_mmdc():
    print("WARNING: mmdc not found — syntax NOT render-verified.", file=sys.stderr)
    print(
        "  install: volta install @mermaid-js/mermaid-cli   "
        "(or: pnpm add -g @mermaid-js/mermaid-cli)",
        file=sys.stderr,
    )


def main():
    ap = argparse.ArgumentParser(description="Audit mermaid blocks in Markdown.")
    ap.add_argument("--out", default="/tmp/mermaid-audit", help="work dir for .mmd/.png")
    ap.add_argument(
        "--keep-png",
        action="store_true",
        help="keep rendered PNGs for the layout pass",
    )
    ap.add_argument("--pptr", default=None, help="puppeteer config (default: a --no-sandbox one)")
    ap.add_argument("target", help="a .md file or a directory to scan")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    have_mmdc = shutil.which("mmdc") is not None
    if not have_mmdc:
        _warn_missing_mmdc()

    pptr = _default_puppeteer(a.out, a.pptr)
    cfg = RunConfig(a.out, pptr, have_mmdc, a.keep_png)

    total = ok = nok = 0
    for md in iter_md([a.target]):
        for idx, (start, body) in enumerate(extract(md)):
            total += 1
            job = BlockJob(md, start, body, idx, cfg)
            result = _audit_one_block(job)
            if result is True:
                ok += 1
            elif result is False:
                nok += 1

    suffix = " (mmdc missing)" if not have_mmdc else ""
    print(f"--- {total} block(s): {ok} OK, {nok} broken{suffix} ---", file=sys.stderr)
    sys.exit(1 if nok else 0)


if __name__ == "__main__":
    main()
