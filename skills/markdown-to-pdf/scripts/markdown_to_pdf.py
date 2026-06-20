#!/usr/bin/env python3
"""markdown-to-pdf engine: render embedded mermaid, then convert to PDF.

Non-destructive: the source .md is never modified; all work happens on a copy in
a temp dir. The final PDF lands alongside the source (or a user path)."""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from collections import namedtuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import render_mermaid
import detect_backends

_PANDOC_ENGINE = {"typst": "typst", "weasyprint": "weasyprint"}


def build_command(backend_name, in_md, out_pdf, engine=None):
    if backend_name == "chromium":
        return ["md-to-pdf", in_md, "--output", out_pdf]
    cmd = ["pandoc", in_md, "-o", out_pdf]
    eng = engine or _PANDOC_ENGINE.get(backend_name)
    if eng:
        cmd.append(f"--pdf-engine={eng}")
    return cmd


def _resolve_engine(backend, which=shutil.which):
    if backend.name == "pandoc-latex":
        for e in ("tectonic", "xelatex", "pdflatex"):
            if which(e):
                return e
        return None
    return _PANDOC_ENGINE.get(backend.name)


Result = namedtuple("Result", "backend renderer out")


class BackendUnavailable(Exception):
    def __init__(self, recommend):
        self.recommend = recommend
        super().__init__("no Markdown->PDF backend available")


def convert(src_md, out_path=None, fmt=None, backend=None,
            which=shutil.which, run=subprocess.run, render=render_mermaid.render_all):
    src_md = os.path.abspath(src_md)
    with open(src_md, encoding="utf-8") as fh:
        text = fh.read()

    if backend:
        chosen = next(b for b in detect_backends.BACKENDS if b.name == backend)
        if not detect_backends.is_available(chosen, which):
            raise BackendUnavailable(chosen)
    else:
        sel = detect_backends.select_backend(which)
        if sel.backend is None:
            raise BackendUnavailable(sel.recommend_install)
        chosen = sel.backend

    render_fmt = fmt or chosen.fmt
    work = tempfile.mkdtemp(prefix="markdown-to-pdf-")
    try:
        new_text = render(text, work, fmt=render_fmt, run=run)   # may raise MermaidRenderError
        copy_md = os.path.join(work, "doc.md")
        with open(copy_md, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        out_path = os.path.abspath(out_path or os.path.splitext(src_md)[0] + ".pdf")
        tmp_pdf = os.path.join(work, "doc.pdf")
        cmd = build_command(chosen.name, copy_md, tmp_pdf,
                            engine=_resolve_engine(chosen, which))
        p = run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"{chosen.name} failed: {(p.stderr or p.stdout).strip()}")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        shutil.move(tmp_pdf, out_path)
        return Result(chosen.name, f"mmdc({render_fmt})", out_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)


_MARP = detect_backends.Backend("marp-cli", 0, [("marp",)], "svg",
                                "pnpm add -g @marp-team/marp-cli")


def convert_deck(src_md, out_path=None, fmt="svg", to="pdf",
                 which=shutil.which, run=subprocess.run, render=render_mermaid.render_all):
    if not detect_backends.marp_available(which):
        raise BackendUnavailable(_MARP)
    src_md = os.path.abspath(src_md)
    with open(src_md, encoding="utf-8") as fh:
        text = fh.read()
    work = tempfile.mkdtemp(prefix="markdown-to-pdf-deck-")
    try:
        new_text = render(text, work, fmt=fmt, run=run)
        copy_md = os.path.join(work, "deck.md")
        with open(copy_md, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        out_path = os.path.abspath(out_path or os.path.splitext(src_md)[0] + "." + to)
        tmp_out = os.path.join(work, "deck." + to)
        p = run(["marp", copy_md, "-o", tmp_out], capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"marp failed: {(p.stderr or p.stdout).strip()}")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        shutil.move(tmp_out, out_path)
        return Result("marp-cli", f"mmdc({fmt})", out_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def render_only(src_md, out_md=None, fmt="svg",
                which=shutil.which, run=subprocess.run, render=render_mermaid.render_all):
    """Pre-render mermaid and emit a marp-ready copy for the marp-slide handoff.

    Diagrams are rendered into a PERSISTENT sibling `<out>-assets/` dir (not a
    temp dir) so the emitted image links still resolve after this returns. The
    source .md is never modified. Returns the path of the written .rendered.md."""
    src_md = os.path.abspath(src_md)
    with open(src_md, encoding="utf-8") as fh:
        text = fh.read()
    out_md = os.path.abspath(out_md or os.path.splitext(src_md)[0] + ".rendered.md")
    assets = os.path.splitext(out_md)[0] + "-assets"
    os.makedirs(assets, exist_ok=True)
    new_text = render(text, assets, fmt=fmt, run=run)   # images persist in assets/
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    return out_md


def main(argv=None):
    ap = argparse.ArgumentParser(prog="markdown-to-pdf",
        description="Render embedded mermaid and convert Markdown to PDF (or a marp deck).")
    ap.add_argument("src", help="source .md file")
    ap.add_argument("-o", "--out", help="output path (default: <src>.pdf)")
    ap.add_argument("--format", choices=["png", "svg"], help="mermaid render format override")
    ap.add_argument("--backend", choices=[b.name for b in detect_backends.BACKENDS])
    # NOTE: marp-cli is NOT a choice here — it is reachable only via --deck.
    # _MARP is intentionally excluded from detect_backends.BACKENDS so it never
    # auto-selects in the document path; the --deck flag is its sole entry point.
    ap.add_argument("--deck", action="store_true", help="build a marp deck instead of a doc PDF")
    ap.add_argument("--to", default="pdf", choices=["pdf", "pptx", "html"], help="deck output format")
    ap.add_argument("--render-only", action="store_true",
                    help="pre-render mermaid and emit a marp-ready .md (for marp-slide handoff)")
    a = ap.parse_args(argv)
    try:
        if a.render_only:
            out_md = render_only(a.src, out_md=a.out, fmt=a.format or "svg")
            print(f"Wrote {out_md}  (mermaid pre-rendered; hand this file to marp-slide)")
            return 0
        res = (convert_deck(a.src, out_path=a.out, fmt=a.format or "svg", to=a.to)
               if a.deck else
               convert(a.src, out_path=a.out, fmt=a.format, backend=a.backend))
    except render_mermaid.MermaidRenderError as e:
        print(f"ABORT: mermaid block at line {e.line} failed to render:\n{e.stderr}", file=sys.stderr)
        return 2
    except BackendUnavailable as e:
        print("No backend available — nothing was converted.", file=sys.stderr)
        if e.recommend:
            print(f"Recommended: install {e.recommend.name}:\n  {e.recommend.install}", file=sys.stderr)
        return 3
    print(f"Wrote {res.out}  (backend: {res.backend}, diagrams: {res.renderer})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
