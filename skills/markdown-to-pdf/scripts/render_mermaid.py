#!/usr/bin/env python3
"""Extract ```mermaid fences from Markdown and render them with mmdc.

The fence-extraction + mmdc-render mechanism (regex + subprocess call) is ADAPTED
from skills/mermaid-audit/scripts/audit_mermaid.py — the canonical origin — into a
small string-based API (find_fences / render_one / render_all). It is not a verbatim
copy of the origin's file-path `extract()` / `render()` functions. Kept stdlib-only
and self-contained per the markdown-to-pdf design (FR-6.4): the same proven
mechanism, not a divergent re-implementation.
"""
import os
import re
import subprocess

FENCE_OPEN = re.compile(r"^(\s*)(`{3,}|~{3,})\s*mermaid\b", re.IGNORECASE)
LINE_RE = re.compile(r"line (\d+)", re.IGNORECASE)


def find_fences(md_text):
    """Return a fence dict per ```mermaid block.

    Each dict: {"start_line": 1-based open-fence line, "body": str,
    "start": char idx, "end": char idx exclusive past the closing fence line}.
    """
    lines = md_text.splitlines(keepends=True)
    offsets, acc = [], 0
    for ln in lines:
        offsets.append(acc)
        acc += len(ln)
    fences, i = [], 0
    while i < len(lines):
        m = FENCE_OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        indent, fence = m.group(1), m.group(2)
        close = re.compile(r"^\s*" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*$")
        start_idx, start_line = offsets[i], i + 1
        body, i = [], i + 1
        while i < len(lines) and not close.match(lines[i]):
            ln = lines[i]
            body.append(ln[len(indent):] if ln.startswith(indent) else ln)
            i += 1
        end_idx = (offsets[i] + len(lines[i])) if i < len(lines) else acc
        i += 1
        fences.append({"start_line": start_line, "body": "".join(body),
                       "start": start_idx, "end": end_idx})
    return fences


class MermaidRenderError(Exception):
    """A mermaid block failed to render. Carries source line + mmdc stderr."""
    def __init__(self, line, stderr):
        self.line, self.stderr = line, stderr
        super().__init__(f"mermaid render failed at line {line}: {stderr}")


def _puppeteer_config(work_dir):
    path = os.path.join(work_dir, "puppeteer-config.json")
    with open(path, "w") as fh:
        fh.write('{ "args": ["--no-sandbox", "--disable-setuid-sandbox"] }\n')
    return path


def render_one(body, out_path, pptr, scale=3, run=subprocess.run):
    mmd_path = out_path + ".mmd"
    with open(mmd_path, "w", encoding="utf-8") as fh:
        fh.write(body)
    p = run(["mmdc", "-p", pptr, "-i", mmd_path, "-o", out_path, "-s", str(scale)],
            capture_output=True, text=True)
    return p.returncode, (p.stderr or p.stdout)


def render_all(md_text, work_dir, fmt="png", scale=3, run=subprocess.run):
    fences = find_fences(md_text)
    if not fences:
        return md_text
    pptr = _puppeteer_config(work_dir)
    rendered = []
    for n, f in enumerate(fences):
        img = os.path.join(work_dir, f"diagram-{n}.{fmt}")
        rc, err = render_one(f["body"], img, pptr, scale=scale, run=run)
        if rc != 0:
            m = LINE_RE.search(err or "")
            loc = f["start_line"] + int(m.group(1)) - 1 if m else f["start_line"]
            raise MermaidRenderError(loc, (err or "").strip())
        rendered.append((f, img))
    out = md_text
    for f, img in reversed(rendered):            # back-to-front keeps spans valid
        out = out[:f["start"]] + f"![diagram]({img})\n" + out[f["end"]:]
    return out
