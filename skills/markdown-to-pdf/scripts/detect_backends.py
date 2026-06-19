#!/usr/bin/env python3
"""Detect which complete Markdown->PDF pipelines are installed and pick the best.

Pipeline-level (not per-tool) detection: a tool can be present while its pipeline
is unusable (e.g. pdflatex without pandoc). Three backends are driven through
pandoc's --pdf-engine; only md-to-pdf (Chromium) is standalone. See
references/backends.md for the scored comparison behind the quality order.
"""
import shutil
from collections import namedtuple

Backend = namedtuple("Backend", "name quality requires fmt install")
Selection = namedtuple("Selection", "backend recommend_install")

BACKENDS = [
    Backend("pandoc-latex", 4, [("pandoc",), ("tectonic", "xelatex", "pdflatex")], "png",
            "cargo install tectonic   # + download the pandoc release binary"),
    Backend("typst", 3, [("pandoc",), ("typst",)], "svg",
            "cargo install --locked typst-cli   # + the pandoc release binary"),
    Backend("weasyprint", 2, [("pandoc",), ("weasyprint",)], "png",
            "uv tool install weasyprint   # needs the Pango system lib"),
    Backend("chromium", 1, [("md-to-pdf",)], "svg",
            "pnpm add -g md-to-pdf"),
]
WINNER = "typst"


def is_available(backend, which=shutil.which):
    return all(any(which(t) for t in group) for group in backend.requires)


def available_backends(which=shutil.which):
    return [b for b in BACKENDS if is_available(b, which)]


def select_backend(which=shutil.which):
    avail = available_backends(which)
    if avail:
        return Selection(max(avail, key=lambda b: b.quality), None)
    winner = next(b for b in BACKENDS if b.name == WINNER)
    return Selection(None, winner)


def marp_available(which=shutil.which):
    return which("marp") is not None
