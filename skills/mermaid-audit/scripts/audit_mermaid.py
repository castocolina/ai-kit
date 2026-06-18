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
import os
import re
import shutil
import subprocess
import sys

FENCE_OPEN = re.compile(r"^(\s*)(`{3,}|~{3,})\s*mermaid\b", re.IGNORECASE)
LINE_RE = re.compile(r"line (\d+)", re.IGNORECASE)

# Pure geometry helpers from the sibling analyzer (optional — the syntax pass
# works without it; the geometry pass simply doesn't run if it's missing).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from mermaid_style import png_size, geometry_findings, extract_style_facts
except Exception:
    png_size = geometry_findings = extract_style_facts = None


def iter_md(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in sorted(files):
                    if f.endswith((".md", ".markdown")):
                        yield os.path.join(root, f)
        else:
            yield p


def extract(md_file):
    """Yield (start_line, body) per mermaid block. start_line is 1-based."""
    with open(md_file, encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    i = 0
    while i < len(lines):
        m = FENCE_OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        indent, fence = m.group(1), m.group(2)
        close = re.compile(r"^\s*" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*$")
        start = i + 1
        body = []
        i += 1
        while i < len(lines) and not close.match(lines[i]):
            ln = lines[i]
            body.append(ln[len(indent):] if ln.startswith(indent) else ln)
            i += 1
        i += 1
        yield start, "".join(body)


def render(mmd_path, png_path, pptr):
    p = subprocess.run(["mmdc", "-p", pptr, "-i", mmd_path, "-o", png_path],
                       capture_output=True, text=True)
    return p.returncode, (p.stderr or p.stdout)


def main():
    ap = argparse.ArgumentParser(description="Audit mermaid blocks in Markdown.")
    ap.add_argument("--out", default="/tmp/mermaid-audit", help="work dir for .mmd/.png")
    ap.add_argument("--keep-png", action="store_true", help="keep rendered PNGs for the layout pass")
    ap.add_argument("--pptr", default=None, help="puppeteer config (default: a --no-sandbox one)")
    ap.add_argument("target", help="a .md file or a directory to scan")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    have_mmdc = shutil.which("mmdc") is not None
    if not have_mmdc:
        print("WARNING: mmdc not found — syntax NOT render-verified.", file=sys.stderr)
        print("  install: volta install @mermaid-js/mermaid-cli   (or: pnpm add -g @mermaid-js/mermaid-cli)",
              file=sys.stderr)

    pptr = a.pptr
    if not pptr:
        pptr = os.path.join(a.out, "puppeteer-config.json")
        with open(pptr, "w") as fh:
            fh.write('{ "args": ["--no-sandbox", "--disable-setuid-sandbox"] }\n')

    total = ok = nok = 0
    for md in iter_md([a.target]):
        for idx, (start, body) in enumerate(extract(md)):
            total += 1
            safe = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.relpath(md))
            mmd = os.path.join(a.out, f"{safe}__{idx}__L{start}.mmd")
            with open(mmd, "w", encoding="utf-8") as fh:
                fh.write(body)
            if not have_mmdc:
                print(f"{md}:{start}\tNOT-VERIFIED\t")
                continue
            png = mmd + ".png"
            rc, err = render(mmd, png, pptr)
            if rc == 0:
                ok += 1
                print(f"{md}:{start}\tOK\t")
                if geometry_findings and png_size and os.path.exists(png):
                    dims = png_size(png)
                    if dims:
                        n_nodes = len(extract_style_facts(body).nodes)
                        for g in geometry_findings(dims[0], dims[1], n_nodes):
                            print(f"{md}:{start}\tGEOMETRY\t{g.rule}\t{g.message}\t→ {g.fix}")
            else:
                nok += 1
                m = LINE_RE.search(err)
                loc = start + int(m.group(1)) - 1 if m else start
                # First useful diagnostic line; skip stack-trace lines (URLs / "at ").
                cand = [l.strip() for l in err.splitlines()
                        if re.search(r"parse error|expecting|got ", l, re.I)
                        and "http" not in l and "node:" not in l and " at " not in l]
                msg = (" ".join(cand) or (err.strip().splitlines()[0] if err.strip() else ""))[:300]
                print(f"{md}:{loc}\tSYNTAX\t{msg}")
            if not a.keep_png:
                try:
                    os.remove(png)
                except OSError:
                    pass

    print(f"--- {total} block(s): {ok} OK, {nok} broken"
          f"{' (mmdc missing)' if not have_mmdc else ''} ---", file=sys.stderr)
    sys.exit(1 if nok else 0)


if __name__ == "__main__":
    main()
