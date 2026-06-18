#!/usr/bin/env python3
"""Static color/shape audit for Mermaid flowchart blocks (stdlib only).

Parses a flowchart block into "style facts" — node shapes, classDef fills,
per-node class assignments, edge out-degrees — then runs near-binary color (C*)
and shape (S*) rules. Companion to audit_mermaid.py (which owns syntax/render).
Scope: flowchart/graph blocks. Other diagram types are skipped (returns no facts).
"""
import re
from dataclasses import dataclass, field

# Node shapes — ORDER MATTERS: match multi-bracket forms before single-bracket.
_NODE_RE = re.compile(r"""
    (?P<id>\b[A-Za-z0-9_]+)\s*
    (?:
        \[\( (?P<cylinder>.*?) \)\]   |
        \[\[ (?P<subroutine>.*?) \]\] |
        \(\[ (?P<stadium>.*?) \]\)    |
        \(\( (?P<circle>.*?) \)\)     |
        \{\{ (?P<hexagon>.*?) \}\}    |
        \[/  (?P<lean_r>.*?) /\]      |
        \{   (?P<rhombus>.*?) \}      |
        \(   (?P<round>.*?) \)        |
        \[   (?P<rect>.*?) \]
    )
""", re.S | re.X)

_EDGE_RE = re.compile(
    r"(?P<src>\b[A-Za-z0-9_]+\b)\s*"
    r"(?:--+>|--+|-\.->|==+>|--[xo])\s*"
    r"(?:\|(?P<lbl>[^|]*)\|\s*)?"
    r"(?P<dst>\b[A-Za-z0-9_]+\b)")

_CLASSDEF_RE = re.compile(r"^\s*classDef\s+(?P<name>\w+)\s+(?P<props>.+?)\s*$", re.M)
_STYLE_RE = re.compile(r"^\s*style\s+(?P<id>\w+)\s+(?P<props>.+?)\s*$", re.M)
_CLASS_RE = re.compile(r"^\s*class\s+(?P<ids>[\w, ]+?)\s+(?P<name>\w+)\s*$", re.M)
_TRIPLE_RE = re.compile(r"(?P<id>\b[A-Za-z0-9_]+)(?:\[[^\]]*\]|\([^)]*\))?:::(?P<name>\w+)")
_SHAPE_NAMES = ("cylinder", "subroutine", "stadium", "circle", "hexagon",
                "lean_r", "rhombus", "round", "rect")


@dataclass
class Node:
    id: str
    shape: str
    label: str


@dataclass
class StyleFacts:
    is_flowchart: bool = False
    nodes: list = field(default_factory=list)
    classdefs: dict = field(default_factory=dict)   # name -> {fill,stroke,color,...}
    node_style: dict = field(default_factory=dict)  # id -> {fill,...} (inline style)
    node_class: dict = field(default_factory=dict)  # id -> classname
    out_degree: dict = field(default_factory=dict)
    has_labeled_out: dict = field(default_factory=dict)


def _parse_props(text):
    props = {}
    for part in text.split(","):
        if ":" in part:
            k, v = part.split(":", 1)
            props[k.strip().lower()] = v.strip()
    return props


def _skeleton(block):
    """Strip shape/label brackets so edges read as bare `ID <link> ID`.

    Removes innermost `[...]`, `(...)`, `{...}` repeatedly (handles nested forms
    like `[(db)]` and `([x])`). Edge labels `|...|` sit outside brackets and are
    preserved, so out-degree and labeled-edge detection survive node decorations.
    """
    prev, s = None, block
    while prev != s:
        prev = s
        s = re.sub(r"\[[^\[\]]*\]", " ", s)
        s = re.sub(r"\([^()]*\)", " ", s)
        s = re.sub(r"\{[^{}]*\}", " ", s)
    return s


def extract_style_facts(block):
    first = next((ln.strip() for ln in block.splitlines() if ln.strip()), "")
    is_flow = bool(re.match(r"(flowchart|graph)\b", first, re.I))
    f = StyleFacts(is_flowchart=is_flow)
    if not is_flow:
        return f

    seen = set()
    for m in _NODE_RE.finditer(block):
        shape = next(s for s in _SHAPE_NAMES if m.group(s) is not None)
        nid = m.group("id")
        if nid in seen:
            continue
        seen.add(nid)
        f.nodes.append(Node(id=nid, shape=shape, label=(m.group(shape) or "").strip()))

    for m in _CLASSDEF_RE.finditer(block):
        f.classdefs[m.group("name")] = _parse_props(m.group("props"))
    for m in _STYLE_RE.finditer(block):
        f.node_style[m.group("id")] = _parse_props(m.group("props"))
    for m in _CLASS_RE.finditer(block):
        for nid in (x.strip() for x in m.group("ids").split(",") if x.strip()):
            f.node_class[nid] = m.group("name")
    for m in _TRIPLE_RE.finditer(block):
        f.node_class[m.group("id")] = m.group("name")

    for m in _EDGE_RE.finditer(_skeleton(block)):
        src, dst = m.group("src"), m.group("dst")
        f.out_degree[src] = f.out_degree.get(src, 0) + 1
        if m.group("lbl") is not None:
            f.has_labeled_out[src] = True
        f.has_labeled_out.setdefault(src, False)
        f.out_degree.setdefault(dst, f.out_degree.get(dst, 0))
        # Bare ids referenced only in edges render as default rectangles — capture
        # them so node counts and shape rules see the whole graph.
        for nid in (src, dst):
            if nid not in seen:
                seen.add(nid)
                f.nodes.append(Node(id=nid, shape="rect", label=""))
    return f


def parse_hex(color):
    """'#abc' / '#aabbcc' / 'aabbcc' -> (r,g,b); None if not a hex literal."""
    if color is None:
        return None
    c = color.strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in c):
        return None
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _linear(channel):
    v = channel / 255.0
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (_linear(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(rgb1, rgb2):
    """WCAG contrast ratio in [1, 21]."""
    l1, l2 = luminance(rgb1), luminance(rgb2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


CANVAS = (255, 255, 255)          # default Mermaid background
MIN_CONTRAST = 3.0                # WCAG non-text/graphics threshold
MAX_DISTINCT_FILLS = 6
MIN_NODES_FOR_EMPHASIS = 6


@dataclass
class Finding:
    rule: str
    severity: str   # "flag"
    node: str       # node id or "" for diagram-level
    message: str
    fix: str


def _is_red(rgb):
    r, g, b = rgb
    return r >= 120 and r - g >= 60 and r - b >= 60


def _is_green(rgb):
    r, g, b = rgb
    return g >= 90 and g - r >= 40 and g - b >= 20


def _fills(facts):
    """All fills actually applied (via classDef-used or inline style)."""
    out = {}
    used = set(facts.node_class.values())
    for name in used:
        props = facts.classdefs.get(name)
        if props and "fill" in props:
            out[f"class:{name}"] = props["fill"]
    for nid, props in facts.node_style.items():
        if "fill" in props:
            out[f"node:{nid}"] = props["fill"]
    return out


def color_findings(facts):
    if not facts.is_flowchart:
        return []
    findings = []
    styled = bool(facts.classdefs or facts.node_style or facts.node_class)

    # C1 — large diagram, zero emphasis
    if len(facts.nodes) >= MIN_NODES_FOR_EMPHASIS and not styled:
        findings.append(Finding(
            "C1", "flag", "",
            f"{len(facts.nodes)} nodes with no classDef/style — flat default gray, "
            "no emphasis or semantic grouping",
            "add a sober classDef palette (see references/palettes.md) and assign "
            "classes by role"))

    # C2 — low contrast per used fill (vs stroke and vs canvas)
    for name in set(facts.node_class.values()):
        props = facts.classdefs.get(name, {})
        fill = parse_hex(props.get("fill"))
        if not fill:
            continue
        stroke = parse_hex(props.get("stroke"))
        if contrast(fill, CANVAS) < MIN_CONTRAST and (
                stroke is None or contrast(fill, stroke) < MIN_CONTRAST):
            findings.append(Finding(
                "C2", "flag", f"class:{name}",
                f"fill {props.get('fill')} has contrast "
                f"{contrast(fill, CANVAS):.1f}:1 vs white canvas (< {MIN_CONTRAST}:1)",
                "darken the fill or add a darker stroke so the node reads against "
                "the background"))

    # C3 — too many distinct fills
    distinct = {v.lower() for v in _fills(facts).values() if parse_hex(v)}
    if len(distinct) > MAX_DISTINCT_FILLS:
        findings.append(Finding(
            "C3", "flag", "",
            f"{len(distinct)} distinct fills — garish; color stops encoding meaning",
            f"collapse to ≤ {MAX_DISTINCT_FILLS} semantic classes (one fill per role)"))

    # C5 — red & green are the only distinguishing fills
    rgbs = [parse_hex(v) for v in distinct]
    rgbs = [c for c in rgbs if c]
    if rgbs and all(_is_red(c) or _is_green(c) for c in rgbs) \
            and any(_is_red(c) for c in rgbs) and any(_is_green(c) for c in rgbs):
        findings.append(Finding(
            "C5", "flag", "",
            "red and green are the only distinguishing fills — indistinguishable "
            "for red-green color blindness (~8% of men)",
            "add a second channel (shape, label, or a blue/orange accent) so meaning "
            "doesn't rely on red-vs-green alone"))
    return findings


DATASTORE_WORDS = ("db", "database", "datastore", "store", "cache", "queue",
                   "bucket", "table", "s3", "redis", "kafka")
MAX_DISTINCT_SHAPES = 4


def shape_findings(facts):
    if not facts.is_flowchart:
        return []
    findings = []
    by_id = {n.id: n for n in facts.nodes}

    # S1 — labeled branch drawn as a rectangle instead of a diamond
    for nid, deg in facts.out_degree.items():
        node = by_id.get(nid)
        if node and deg >= 2 and facts.has_labeled_out.get(nid) and node.shape == "rect":
            findings.append(Finding(
                "S1", "flag", nid,
                f"`{nid}` has {deg} labeled out-edges (a decision) but is a rectangle",
                f"make it a diamond: `{nid}{{{node.label or 'decision?'}}}`"))

    # S3 — datastore label not drawn as a cylinder
    for node in facts.nodes:
        low = node.label.lower()
        if node.shape != "cylinder" and any(
                re.search(rf"\b{re.escape(w)}\b", low) for w in DATASTORE_WORDS):
            findings.append(Finding(
                "S3", "flag", node.id,
                f"`{node.id}` looks like a data store (\"{node.label}\") but isn't a cylinder",
                f"use a cylinder: `{node.id}[({node.label})]`"))

    # S4 — too many distinct shapes with no class system
    distinct_shapes = {n.shape for n in facts.nodes}
    if len(distinct_shapes) > MAX_DISTINCT_SHAPES and not facts.classdefs:
        findings.append(Finding(
            "S4", "flag", "",
            f"{len(distinct_shapes)} distinct node shapes and no class system — "
            "shape stops carrying meaning",
            f"reserve shapes for roles (rect=step, diamond=decision, cylinder=store, "
            f"stadium=start/end); keep to ≤ {MAX_DISTINCT_SHAPES}"))
    return findings


import struct as _struct

READING_COLUMN_PX = 900     # GitHub markdown content column (approx, centered)
DEFAULT_FONT_PX = 16        # Mermaid default node font
MIN_LEGIBLE_FONT_PX = 11    # below this, text reads only when expanded
PAGE_PX = 1000              # one viewport page (approx)
MAX_PAGES = 3
TOO_WIDE_RATIO = 0.4        # height/width below this == too horizontal (user's bar)


def png_size(path):
    """(width, height) from a PNG's IHDR; None if not a PNG."""
    with open(path, "rb") as fh:
        head = fh.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    width, height = _struct.unpack(">II", head[16:24])
    return (width, height)


def geometry_findings(width, height, node_count):
    """R-rules over rendered pixel dimensions. Pure + deterministic."""
    findings = []
    if width <= 0 or height <= 0:
        return findings
    ratio = height / width

    # R1 — too horizontal
    if ratio < TOO_WIDE_RATIO:
        findings.append(Finding(
            "R1", "flag", "",
            f"rendered {width}x{height}px, height/width ratio {ratio:.2f} < "
            f"{TOO_WIDE_RATIO} — too horizontal; forces sideways scroll",
            "switch to `graph TD` and fold parallel branches into stacked "
            "`subgraph`s connected at their boundaries to trade width for height"))

    # R2 — fit-to-column shrinks text below legibility
    if width > READING_COLUMN_PX:
        eff_font = DEFAULT_FONT_PX * (READING_COLUMN_PX / width)
        if eff_font < MIN_LEGIBLE_FONT_PX:
            findings.append(Finding(
                "R2", "flag", "",
                f"{width}px wide — GitHub scales it to its ~{READING_COLUMN_PX}px "
                f"reading column, shrinking node text to ~{eff_font:.0f}px "
                f"(< {MIN_LEGIBLE_FONT_PX}px; legible only when expanded)",
                "reduce width: prefer `TD`, fewer side-by-side branches, and "
                "subgraphs so the diagram fits the column at full size"))

    # R3 — too tall (more than ~3 pages of scroll)
    if height > MAX_PAGES * PAGE_PX:
        findings.append(Finding(
            "R3", "flag", "",
            f"rendered {height}px tall (> {MAX_PAGES} viewport pages) — too vertical, "
            "endless scroll",
            "split into multiple diagrams (one idea each) or collapse long single "
            "chains; very large boxes with little text waste vertical space"))
    return findings


import argparse
import os as _os
import sys as _sys


def audit_block(block):
    facts = extract_style_facts(block)
    return color_findings(facts) + shape_findings(facts)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Color/shape audit of Mermaid flowcharts.")
    ap.add_argument("target", help="a .md file or a directory to scan")
    a = ap.parse_args(argv)

    # Lazy import (inside main) of the proven fence extractor — keeps module load
    # free of a cycle, since audit_mermaid imports this module at its top.
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    from audit_mermaid import extract as _extract_blocks, iter_md as _iter_md

    total = 0
    for md in _iter_md([a.target]):
        for start, body in _extract_blocks(md):
            for fnd in audit_block(body):
                total += 1
                where = f"{md}:{start}"
                node = f" [{fnd.node}]" if fnd.node else ""
                print(f"{where}\t{fnd.rule}\t{fnd.severity}\t{fnd.message}{node}\t→ {fnd.fix}")
    print(f"--- {total} color/shape finding(s) ---", file=_sys.stderr)
    _sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
