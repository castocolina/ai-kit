#!/usr/bin/env python3
"""markdown-to-pdf engine: render embedded mermaid, then convert to PDF.

Non-destructive: the source .md is never modified; all work happens on a copy in
a temp dir. The final PDF lands alongside the source (or a user path)."""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import namedtuple
from collections.abc import Callable
from typing import NamedTuple

import detect_backends
import render_mermaid

_PANDOC_ENGINE = {"typst": "typst", "weasyprint": "weasyprint"}
# the same sandbox flags render_mermaid gives mmdc
CHROME_LAUNCH_OPTIONS = '{"args":["--no-sandbox","--disable-setuid-sandbox"]}'
# a markdown image destination: `<...>` or a run of non-space, non-`)` characters
_IMAGE = re.compile(r"(!\[[^\]]*\]\()(<[^>]*>|[^)\s]+)")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def build_command(backend_name, in_md, out_pdf, engine=None, resource_dir=None):
    if backend_name == "chromium":
        # md-to-pdf has no output flag: it writes <stem>.pdf beside its input
        return ["md-to-pdf", in_md, "--basedir", os.path.abspath(os.sep),
                "--launch-options", CHROME_LAUNCH_OPTIONS]
    cmd = ["pandoc", in_md, "-o", out_pdf]
    eng = engine or _PANDOC_ENGINE.get(backend_name)
    if eng:
        cmd.append(f"--pdf-engine={eng}")
    if resource_dir:
        cmd.append(f"--resource-path={resource_dir}")
    return cmd


def _resolve_engine(backend, which=shutil.which):
    if backend.name == "pandoc-latex":
        for e in ("tectonic", "xelatex", "pdflatex"):
            if which(e):
                return e
        return None
    return _PANDOC_ENGINE.get(backend.name)


def _absolutize_images(text, src_dir):
    """Rewrite relative local image links to absolute paths under src_dir.

    The copy the converter renders lives in a temp folder, so a relative link would
    resolve there. URLs, data URIs, absolute paths and `#` anchors pass through."""
    def fix(m):
        dest = m.group(2)
        inner = dest[1:-1] if dest.startswith("<") else dest
        if not inner or inner[0] in "/#" or _SCHEME.match(inner):
            return m.group(0)
        path = os.path.normpath(os.path.join(src_dir, inner))
        if " " in path:
            path = f"<{path}>"
        return m.group(1) + path
    return _IMAGE.sub(fix, text)


Result = namedtuple("Result", "backend renderer out")


class BackendUnavailable(Exception):
    def __init__(self, recommend):
        self.recommend = recommend
        super().__init__("no Markdown->PDF backend available")


class BackendFailed(RuntimeError):
    """A backend ran and failed; main() prints its error and returns 4."""


class ConvertOptions(NamedTuple):
    out_path: str | None = None
    fmt: str | None = None
    backend: str | None = None
    deck_to: str = "pdf"
    which: Callable = shutil.which
    run: Callable = subprocess.run
    render: Callable = render_mermaid.render_all


def _select_backend(backend_name, which):
    if backend_name:
        chosen = next(b for b in detect_backends.BACKENDS if b.name == backend_name)
        if not detect_backends.is_available(chosen, which):
            raise BackendUnavailable(chosen)
        return chosen
    sel = detect_backends.select_backend(which)
    if sel.backend is None:
        raise BackendUnavailable(sel.recommend_install)
    return sel.backend


def _run_pdf_command(name, cmd, run):
    p = run(cmd, capture_output=True, text=True, check=False)
    if p.returncode != 0:
        raise BackendFailed(f"{name} failed: {(p.stderr or p.stdout).strip()}")


def _finalize_output(tmp_path, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    shutil.move(tmp_path, out_path)


def convert(src_md, options=None):
    opts = options or ConvertOptions()
    return _convert_with_options(src_md, opts)


def _convert_with_options(src_md, opts):
    src_md = os.path.abspath(src_md)
    with open(src_md, encoding="utf-8") as fh:
        text = fh.read()

    chosen = _select_backend(opts.backend, opts.which)
    render_fmt = opts.fmt or chosen.fmt
    work = tempfile.mkdtemp(prefix="markdown-to-pdf-")
    try:
        new_text = opts.render(text, work, fmt=render_fmt, run=opts.run)
        if chosen.name == "chromium":
            new_text = _absolutize_images(new_text, os.path.dirname(src_md))
        copy_md = os.path.join(work, "doc.md")
        with open(copy_md, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        out_path = os.path.abspath(opts.out_path or os.path.splitext(src_md)[0] + ".pdf")
        tmp_pdf = os.path.join(work, "doc.pdf")
        cmd = build_command(
            chosen.name,
            copy_md,
            tmp_pdf,
            engine=_resolve_engine(chosen, opts.which),
            resource_dir=os.path.dirname(src_md),
        )
        _run_pdf_command(chosen.name, cmd, opts.run)
        _finalize_output(tmp_pdf, out_path)
        return Result(chosen.name, f"mmdc({render_fmt})", out_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)


_MARP = detect_backends.Backend("marp-cli", 0, [("marp",)], "svg",
                                "pnpm add -g @marp-team/marp-cli")


def _persist_deck_assets(work, new_text, out_path, fmt):
    """Copy the rendered diagrams of an HTML deck beside its output, linked relatively."""
    assets = os.path.splitext(out_path)[0] + "-assets"
    os.makedirs(assets, exist_ok=True)
    for name in os.listdir(work):
        if name.startswith("diagram-") and name.endswith("." + fmt):
            shutil.copyfile(os.path.join(work, name), os.path.join(assets, name))
    return new_text.replace(work + os.sep, os.path.basename(assets) + "/")


def convert_deck(src_md, options=None):
    opts = options or ConvertOptions(fmt="svg")
    return _convert_deck_with_options(src_md, opts)


def _convert_deck_with_options(src_md, opts):
    if not detect_backends.marp_available(opts.which):
        raise BackendUnavailable(_MARP)
    src_md = os.path.abspath(src_md)
    with open(src_md, encoding="utf-8") as fh:
        text = fh.read()
    work = tempfile.mkdtemp(prefix="markdown-to-pdf-deck-")
    try:
        new_text = opts.render(text, work, fmt=opts.fmt or "svg", run=opts.run)
        out_path = os.path.abspath(
            opts.out_path or os.path.splitext(src_md)[0] + "." + opts.deck_to,
        )
        if opts.deck_to in ("pdf", "pptx"):
            new_text = _absolutize_images(new_text, os.path.dirname(src_md))
        if opts.deck_to == "html" and render_mermaid.find_fences(text):
            new_text = _persist_deck_assets(work, new_text, out_path, opts.fmt or "svg")
        copy_md = os.path.join(work, "deck.md")
        with open(copy_md, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        tmp_out = os.path.join(work, "deck." + opts.deck_to)
        p = opts.run(
            ["marp", copy_md, "-o", tmp_out, "--allow-local-files"],
            capture_output=True,
            text=True,
            check=False,
        )
        if p.returncode != 0:
            raise BackendFailed(f"marp failed: {(p.stderr or p.stdout).strip()}")
        _finalize_output(tmp_out, out_path)
        return Result("marp-cli", f"mmdc({opts.fmt or 'svg'})", out_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def render_only(src_md, options=None):
    """Pre-render mermaid and emit a marp-ready copy for the marp-slide handoff.

    Diagrams are rendered into a PERSISTENT sibling `<out>-assets/` dir (not a
    temp dir) so the emitted image links still resolve after this returns. The
    source .md is never modified. Returns the path of the written .rendered.md."""
    opts = options or ConvertOptions(fmt="svg")
    return _render_only_with_options(src_md, opts)


def _render_only_with_options(src_md, opts):
    src_md = os.path.abspath(src_md)
    with open(src_md, encoding="utf-8") as fh:
        text = fh.read()
    out_md = os.path.abspath(opts.out_path or os.path.splitext(src_md)[0] + ".rendered.md")
    assets = os.path.splitext(out_md)[0] + "-assets"
    os.makedirs(assets, exist_ok=True)
    new_text = opts.render(text, assets, fmt=opts.fmt or "svg", run=opts.run)
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    return out_md


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="markdown-to-pdf",
        description="Render embedded mermaid and convert Markdown to PDF (or a marp deck).",
    )
    ap.add_argument("src", help="source .md file")
    ap.add_argument("-o", "--out", help="output path (default: <src>.pdf)")
    ap.add_argument("--format", choices=["png", "svg"], help="mermaid render format override")
    ap.add_argument("--backend", choices=[b.name for b in detect_backends.BACKENDS])
    # NOTE: marp-cli is NOT a choice here — it is reachable only via --deck.
    # _MARP is intentionally excluded from detect_backends.BACKENDS so it never
    # auto-selects in the document path; the --deck flag is its sole entry point.
    ap.add_argument(
        "--deck",
        action="store_true",
        help="build a marp deck instead of a doc PDF",
    )
    ap.add_argument(
        "--to",
        default="pdf",
        choices=["pdf", "pptx", "html"],
        help="deck output format",
    )
    ap.add_argument(
        "--render-only",
        action="store_true",
        help="pre-render mermaid and emit a marp-ready .md (for marp-slide handoff)",
    )
    a = ap.parse_args(argv)
    try:
        if a.render_only:
            out_md = render_only(
                a.src,
                ConvertOptions(out_path=a.out, fmt=a.format or "svg"),
            )
            print(f"Wrote {out_md}  (mermaid pre-rendered; hand this file to marp-slide)")
            return 0
        if a.deck:
            opts = ConvertOptions(out_path=a.out, fmt=a.format or "svg", deck_to=a.to)
            res = convert_deck(a.src, opts)
        else:
            res = convert(
                a.src,
                ConvertOptions(out_path=a.out, fmt=a.format, backend=a.backend),
            )
    except render_mermaid.MermaidRenderError as e:
        print(
            f"ABORT: mermaid block at line {e.line} failed to render:\n{e.stderr}",
            file=sys.stderr,
        )
        return 2
    except BackendUnavailable as e:
        print("No backend available — nothing was converted.", file=sys.stderr)
        if e.recommend:
            print(
                f"Recommended: install {e.recommend.name}:\n  {e.recommend.install}",
                file=sys.stderr,
            )
        return 3
    except BackendFailed as e:
        print(str(e), file=sys.stderr)
        return 4
    print(f"Wrote {res.out}  (backend: {res.backend}, diagrams: {res.renderer})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
