# markdown-to-pdf Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `markdown-to-pdf` skill that turns a Markdown doc with embedded mermaid into a PDF (and, secondarily, a marp deck) in one non-destructive command.

**Architecture:** Three stdlib-only Python scripts under `skills/markdown-to-pdf/scripts/` — `render_mermaid.py` (fence-extraction + mmdc-render mechanism adapted from mermaid-audit), `detect_backends.py` (complete-pipeline detection + ranking), `markdown_to_pdf.py` (the engine: temp-copy → render fences → substitute → backend → emit PDF). A `SKILL.md` orchestration layer adds capability-conditional marp-slide delegation and install guidance. Three of four PDF backends (Typst, WeasyPrint, LaTeX) are driven through pandoc's `--pdf-engine`; only `md-to-pdf` (Chromium) is standalone.

**Tech Stack:** Python 3 (stdlib only), `mmdc` (mermaid render), pandoc + a PDF engine (Typst/LaTeX/WeasyPrint) or `md-to-pdf`, `marp-cli` (decks). Tests: `unittest`.

## Global Constraints

- **Scripts are stdlib-only** — no pip dependencies in any `skills/markdown-to-pdf/scripts/*.py`.
- **Python 3.8+**, all output text in **English**.
- **Never modify the source `.md`** — all work happens on a copy in a temp dir (FR-6.2).
- **Never auto-install** — detect + print exact commands using **`uv` / `pnpm` / `cargo`** (FR-6.6).
- **Tests use `unittest`**, run via `python3 -m unittest tests.test_markdown_to_pdf`; load skill scripts via `sys.path.insert` (mirror `tests/test_mermaid_style.py`).
- **Render failure aborts** the whole conversion and surfaces `mmdc`'s stderr (no PDF emitted) (design §Error handling).
- **Adapted origin**: `render_mermaid.py` carries a header comment naming `skills/mermaid-audit/scripts/audit_mermaid.py` as canonical (FR-6.4). The origin file is 141 lines total; `render_mermaid.py` adapts the fence-extraction + mmdc-render mechanism (regex + subprocess call) from `audit_mermaid.py` into a small string-based API (`find_fences`/`render_one`/`render_all`) — not a verbatim copy of the origin's `extract()`/`render()` functions.
- Spec: `docs/superpowers/specs/2026-06-19-e6-markdown-to-pdf-design.md`.

## File Structure

| File | Responsibility |
|---|---|
| `skills/markdown-to-pdf/SKILL.md` | Orchestration prose: backend decision, marp-slide delegation, install guidance |
| `skills/markdown-to-pdf/scripts/render_mermaid.py` | Adapted fence extraction + `mmdc` render + substitution (mechanism from mermaid-audit); `MermaidRenderError` |
| `skills/markdown-to-pdf/scripts/detect_backends.py` | `Backend` table, complete-pipeline availability, selection, marp detection |
| `skills/markdown-to-pdf/scripts/markdown_to_pdf.py` | Engine: `build_command`, `convert`, `convert_deck`, `main` CLI |
| `skills/markdown-to-pdf/references/backends.md` | Scored comparison + exact install commands |
| `skills/markdown-to-pdf/examples/sample-with-mermaid.md` | Reference input |
| `tests/test_markdown_to_pdf.py` | unittest suite for all three scripts |
| `Makefile` | Add the new test module to the `test` target |

---

### Task 1: Scaffold skill + mermaid fence extraction/substitution

**Files:**
- Create (scaffold via skill-creator): `skills/markdown-to-pdf/SKILL.md`, `skills/markdown-to-pdf/scripts/`, `references/`, `examples/`
- Create: `skills/markdown-to-pdf/scripts/render_mermaid.py`
- Test: `tests/test_markdown_to_pdf.py`

**Interfaces:**
- Produces: `find_fences(md_text) -> list[dict]` where each dict is `{"start_line": int (1-based open-fence line), "body": str, "start": int (char idx), "end": int (char idx, exclusive, past the closing fence line)}`.

- [ ] **Step 1: Scaffold the skill with skill-creator**

Run `/skill-creator:skill-creator` to create the `skills/markdown-to-pdf/` skeleton (SKILL.md stub + `scripts/`, `references/`, `examples/` dirs). This is the authoring tool of record for this skill; later tasks flesh out the files it scaffolds. If skill-creator is unavailable, create the directories manually.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_markdown_to_pdf.py
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "skills", "markdown-to-pdf", "scripts"))
import render_mermaid as rm


class TestFindFences(unittest.TestCase):
    def test_finds_fence_with_line_body_and_span(self):
        md = "intro\n\n```mermaid\nflowchart TD\n  A-->B\n```\n\noutro\n"
        fences = rm.find_fences(md)
        self.assertEqual(len(fences), 1)
        f = fences[0]
        self.assertEqual(f["start_line"], 3)
        self.assertEqual(f["body"], "flowchart TD\n  A-->B\n")
        # span covers the whole fence incl. delimiters
        self.assertEqual(md[f["start"]:f["end"]], "```mermaid\nflowchart TD\n  A-->B\n```\n")

    def test_no_fences_returns_empty(self):
        self.assertEqual(rm.find_fences("# just text\n"), [])

    def test_two_fences(self):
        md = "```mermaid\nA\n```\ntext\n```mermaid\nB\n```\n"
        fences = rm.find_fences(md)
        self.assertEqual([f["body"] for f in fences], ["A\n", "B\n"])
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestFindFences -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'render_mermaid'`

- [ ] **Step 4: Write minimal implementation**

```python
#!/usr/bin/env python3
"""Extract ```mermaid fences from Markdown and render them with mmdc.

Adapted from skills/mermaid-audit/scripts/audit_mermaid.py (canonical origin) —
the fence-extraction + mmdc-render mechanism (regex + subprocess call) re-expressed
as a string-based API (`find_fences`/`render_one`/`render_all`). Kept stdlib-only
and self-contained per the markdown-to-pdf design (FR-6.4): the same proven
mechanism, not a divergent re-implementation.
"""
import os
import re
import subprocess

FENCE_OPEN = re.compile(r"^(\s*)(`{3,}|~{3,})\s*mermaid\b", re.IGNORECASE)
LINE_RE = re.compile(r"line (\d+)", re.IGNORECASE)


def find_fences(md_text):
    """Return a fence dict per ```mermaid block (see plan for the shape)."""
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestFindFences -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add skills/markdown-to-pdf/ tests/test_markdown_to_pdf.py
git commit -m "feat(markdown-to-pdf): scaffold skill + mermaid fence extraction"
```

---

### Task 2: mermaid render + substitution with abort-on-failure

**Files:**
- Modify: `skills/markdown-to-pdf/scripts/render_mermaid.py`
- Test: `tests/test_markdown_to_pdf.py`

**Interfaces:**
- Consumes: `find_fences` (Task 1).
- Produces:
  - `class MermaidRenderError(Exception)` with attributes `.line: int`, `.stderr: str`.
  - `render_one(body, out_path, pptr, run=subprocess.run) -> (rc: int, stderr: str)`.
  - `render_all(md_text, work_dir, fmt="png", run=subprocess.run) -> str` (Markdown with each fence replaced by `![diagram](<abs png/svg path>)`; raises `MermaidRenderError` on the first failure; returns input unchanged when no fences).

- [ ] **Step 1: Write the failing test**

```python
class TestRenderAll(unittest.TestCase):
    def _fake_run_ok(self):
        def run(cmd, capture_output=True, text=True):
            # assert mmdc was called with high-DPI scale flag
            self.assertIn("-s", cmd)
            self.assertEqual(cmd[cmd.index("-s") + 1], "3")
            out = cmd[cmd.index("-o") + 1]          # mmdc -i ... -o <out>
            open(out, "wb").write(b"\x89PNG")        # pretend mmdc rendered it
            return type("P", (), {"returncode": 0, "stderr": "", "stdout": ""})()
        return run

    def test_substitutes_fences_with_image_links(self):
        import tempfile
        md = "a\n```mermaid\nflowchart TD\nX-->Y\n```\nb\n"
        work = tempfile.mkdtemp()
        out = rm.render_all(md, work, fmt="png", run=self._fake_run_ok())
        self.assertNotIn("```mermaid", out)
        self.assertIn("![diagram](", out)
        self.assertIn("diagram-0.png", out)

    def test_aborts_with_line_and_stderr_on_failure(self):
        import tempfile
        md = "a\n```mermaid\nbroken!!!\n```\n"
        def run_fail(cmd, capture_output=True, text=True):
            return type("P", (), {"returncode": 1,
                                  "stderr": "Parse error on line 2: ...", "stdout": ""})()
        with self.assertRaises(rm.MermaidRenderError) as cm:
            rm.render_all(md, tempfile.mkdtemp(), run=run_fail)
        self.assertEqual(cm.exception.line, 3)       # open-fence line 2 + mmdc line 2 - 1
        self.assertIn("Parse error", cm.exception.stderr)

    def test_no_fences_passthrough(self):
        import tempfile
        # work_dir is never touched when there are no fences; use a real tempdir
        # to avoid relying on /tmp existing and to be safe against future changes
        # that call _puppeteer_config(work_dir) before the early-return check.
        self.assertEqual(rm.render_all("plain\n", tempfile.mkdtemp()), "plain\n")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestRenderAll -v`
Expected: FAIL — `AttributeError: module 'render_mermaid' has no attribute 'render_all'`

- [ ] **Step 3: Write minimal implementation** (append to `render_mermaid.py`)

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestRenderAll -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Add a real-mmdc integration smoke test (skipped when absent)**

```python
import shutil
class TestRenderRealMmdc(unittest.TestCase):
    @unittest.skipUnless(shutil.which("mmdc"), "mmdc not installed")
    def test_real_render_produces_image(self):
        import tempfile
        md = "```mermaid\nflowchart TD\n  A-->B\n```\n"
        work = tempfile.mkdtemp()
        out = rm.render_all(md, work, fmt="png")
        self.assertIn("![diagram](", out)
        self.assertTrue(os.path.exists(os.path.join(work, "diagram-0.png")))
```

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestRenderRealMmdc -v`
Expected: PASS (or SKIPPED if `mmdc` absent)

- [ ] **Step 6: Commit**

```bash
git add skills/markdown-to-pdf/scripts/render_mermaid.py tests/test_markdown_to_pdf.py
git commit -m "feat(markdown-to-pdf): mmdc render + substitution, abort on failure"
```

---

### Task 3: Backend detection & selection (complete-pipeline)

**Files:**
- Create: `skills/markdown-to-pdf/scripts/detect_backends.py`
- Test: `tests/test_markdown_to_pdf.py`

**Interfaces:**
- Produces:
  - `Backend = namedtuple("Backend", "name quality requires fmt install")` where `requires` is a list of alternative-groups (tuples); available iff at least one tool in EVERY group resolves.
  - `BACKENDS: list[Backend]`, `WINNER = "typst"`.
  - `is_available(backend, which=shutil.which) -> bool`
  - `available_backends(which=shutil.which) -> list[Backend]`
  - `select_backend(which=shutil.which) -> Selection(backend|None, recommend_install|None)`
  - `marp_available(which=shutil.which) -> bool`

- [ ] **Step 1: Write the failing test**

```python
import detect_backends as db

class TestBackendSelection(unittest.TestCase):
    def _which(self, present):
        return lambda name: ("/usr/bin/" + name) if name in present else None

    def test_picks_highest_quality_available(self):
        # pandoc-latex (q4) and typst (q3) both available -> latex wins
        sel = db.select_backend(self._which({"pandoc", "pdflatex", "typst"}))
        self.assertEqual(sel.backend.name, "pandoc-latex")
        self.assertIsNone(sel.recommend_install)

    def test_pandoc_without_engine_is_unavailable(self):
        # pandoc present but NO tex engine / typst / weasyprint -> latex pipeline incomplete
        sel = db.select_backend(self._which({"pandoc"}))
        self.assertIsNone(sel.backend)
        self.assertEqual(sel.recommend_install.name, "typst")

    def test_chromium_only(self):
        sel = db.select_backend(self._which({"md-to-pdf"}))
        self.assertEqual(sel.backend.name, "chromium")

    def test_nothing_recommends_winner(self):
        sel = db.select_backend(self._which(set()))
        self.assertIsNone(sel.backend)
        self.assertEqual(sel.recommend_install.name, "typst")

    def test_marp_detection(self):
        self.assertTrue(db.marp_available(self._which({"marp"})))
        self.assertFalse(db.marp_available(self._which(set())))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestBackendSelection -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'detect_backends'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestBackendSelection -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/markdown-to-pdf/scripts/detect_backends.py tests/test_markdown_to_pdf.py
git commit -m "feat(markdown-to-pdf): complete-pipeline backend detection + selection"
```

---

### Task 4: Backend command construction

**Files:**
- Create: `skills/markdown-to-pdf/scripts/markdown_to_pdf.py`
- Test: `tests/test_markdown_to_pdf.py`

**Interfaces:**
- Consumes: `detect_backends.Backend`, `is_available` (Task 3).
- Produces:
  - `build_command(backend_name, in_md, out_pdf, engine=None) -> list[str]`
  - `_resolve_engine(backend, which=shutil.which) -> str|None` (for `pandoc-latex`: first of `tectonic/xelatex/pdflatex` present; else the pandoc `--pdf-engine` value for typst/weasyprint; `None` for chromium).

- [ ] **Step 1: Write the failing test**

```python
# At the top of tests/test_markdown_to_pdf.py, ensure these module-level imports
# are present (add after the existing `import render_mermaid as rm` and
# `import detect_backends as db` lines — both were added in earlier tasks):
import markdown_to_pdf as m2p
# (db was imported as `import detect_backends as db` in Task 3 — confirm it exists)

class TestBuildCommand(unittest.TestCase):
    def test_pandoc_latex_with_tectonic(self):
        cmd = m2p.build_command("pandoc-latex", "in.md", "out.pdf", engine="tectonic")
        self.assertEqual(cmd, ["pandoc", "in.md", "-o", "out.pdf", "--pdf-engine=tectonic"])

    def test_typst(self):
        cmd = m2p.build_command("typst", "in.md", "out.pdf", engine="typst")
        self.assertEqual(cmd[-1], "--pdf-engine=typst")

    def test_chromium_is_standalone(self):
        cmd = m2p.build_command("chromium", "in.md", "out.pdf")
        self.assertEqual(cmd, ["md-to-pdf", "in.md", "--output", "out.pdf"])

    def test_resolve_engine_prefers_tectonic(self):
        which = lambda n: "/x/" + n if n in {"tectonic", "pdflatex"} else None
        b = next(x for x in db.BACKENDS if x.name == "pandoc-latex")
        self.assertEqual(m2p._resolve_engine(b, which), "tectonic")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestBuildCommand -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'markdown_to_pdf'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestBuildCommand -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/markdown-to-pdf/scripts/markdown_to_pdf.py tests/test_markdown_to_pdf.py
git commit -m "feat(markdown-to-pdf): backend command construction + engine resolution"
```

---

### Task 5: `convert()` orchestration (non-destructive, hermetic)

**Files:**
- Modify: `skills/markdown-to-pdf/scripts/markdown_to_pdf.py`
- Test: `tests/test_markdown_to_pdf.py`

**Interfaces:**
- Consumes: `render_mermaid.render_all`, `MermaidRenderError`; `detect_backends.select_backend`, `is_available`, `BACKENDS`; `build_command`, `_resolve_engine` (Task 4).
- Produces:
  - `Result = namedtuple("Result", "backend renderer out")`
  - `class BackendUnavailable(Exception)` with `.recommend: Backend|None`.
  - `convert(src_md, out_path=None, fmt=None, backend=None, which=shutil.which, run=subprocess.run, render=render_mermaid.render_all) -> Result`. Default `out_path` = `<src>.pdf` alongside source. Reads source but never writes it. Raises `MermaidRenderError` (abort) or `BackendUnavailable`.

- [ ] **Step 1: Write the failing test**

```python
# Ensure `import render_mermaid` (un-aliased) is present at module level in
# tests/test_markdown_to_pdf.py — Task 1 used `import render_mermaid as rm`,
# but TestConvert below refers to `render_mermaid.MermaidRenderError` directly.
# Add this import alongside the existing ones at the top of the file:
import render_mermaid

class TestConvert(unittest.TestCase):
    def _stub_run_writes_pdf(self):
        def run(cmd, capture_output=True, text=True):
            out = cmd[cmd.index("-o") + 1] if "-o" in cmd else cmd[cmd.index("--output") + 1]
            open(out, "wb").write(b"%PDF-1.7\n")
            return type("P", (), {"returncode": 0, "stderr": "", "stdout": ""})()
        return run

    def _fake_render(self, text, work_dir, fmt="png", run=None):
        return text  # pretend diagrams rendered; no mmdc needed

    def test_writes_pdf_alongside_source_without_touching_it(self):
        import tempfile
        d = tempfile.mkdtemp()
        src = os.path.join(d, "doc.md")
        open(src, "w").write("# hi\n```mermaid\nA-->B\n```\n")
        before = open(src, "rb").read()
        which = lambda n: "/x/" + n if n in {"pandoc", "pdflatex"} else None
        res = m2p.convert(src, which=which, run=self._stub_run_writes_pdf(),
                          render=self._fake_render)
        self.assertEqual(res.backend, "pandoc-latex")
        self.assertTrue(res.out.endswith("doc.pdf"))
        self.assertTrue(os.path.exists(res.out))
        self.assertEqual(open(src, "rb").read(), before)   # source untouched (FR-6.2)

    def test_custom_out_path(self):
        import tempfile
        d = tempfile.mkdtemp()
        src = os.path.join(d, "doc.md"); open(src, "w").write("hi\n")
        which = lambda n: "/x/" + n if n in {"md-to-pdf"} else None
        # sub/ is intentionally NOT pre-created — convert() must make it
        out = os.path.join(d, "sub", "x.pdf")
        res = m2p.convert(src, out_path=out, which=which,
                          run=self._stub_run_writes_pdf(), render=self._fake_render)
        self.assertEqual(res.out, out)

    def test_no_backend_raises_backend_unavailable(self):
        import tempfile
        src = os.path.join(tempfile.mkdtemp(), "doc.md"); open(src, "w").write("hi\n")
        with self.assertRaises(m2p.BackendUnavailable) as cm:
            m2p.convert(src, which=lambda n: None, render=self._fake_render)
        self.assertEqual(cm.exception.recommend.name, "typst")

    def test_render_failure_propagates_and_emits_nothing(self):
        import tempfile
        d = tempfile.mkdtemp(); src = os.path.join(d, "doc.md")
        open(src, "w").write("```mermaid\nbad\n```\n")
        def bad_render(text, work_dir, fmt="png", run=None):
            raise render_mermaid.MermaidRenderError(1, "Parse error on line 1")
        which = lambda n: "/x/" + n if n in {"pandoc", "pdflatex"} else None
        with self.assertRaises(render_mermaid.MermaidRenderError):
            m2p.convert(src, which=which, run=self._stub_run_writes_pdf(), render=bad_render)
        self.assertFalse(os.path.exists(os.path.join(d, "doc.pdf")))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestConvert -v`
Expected: FAIL — `AttributeError: module 'markdown_to_pdf' has no attribute 'convert'`

- [ ] **Step 3: Write minimal implementation** (append to `markdown_to_pdf.py`)

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestConvert -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/markdown-to-pdf/scripts/markdown_to_pdf.py tests/test_markdown_to_pdf.py
git commit -m "feat(markdown-to-pdf): non-destructive convert() orchestration"
```

---

### Task 6: CLI `main()` + marp deck path + `--render-only` handoff

**Files:**
- Modify: `skills/markdown-to-pdf/scripts/markdown_to_pdf.py`
- Test: `tests/test_markdown_to_pdf.py`

**Interfaces:**
- Consumes: `convert`, `BackendUnavailable`, `Result`, `MermaidRenderError`; `detect_backends.marp_available`.
- Produces:
  - `_MARP = Backend("marp-cli", 0, [("marp",)], "svg", "pnpm add -g @marp-team/marp-cli")`
  - `convert_deck(src_md, out_path=None, fmt="svg", to="pdf", which=shutil.which, run=subprocess.run, render=render_mermaid.render_all) -> Result` (pre-renders diagrams, then `marp <copy> -o <out>`). Raises `BackendUnavailable(_MARP)` when `marp` absent.
  - `render_only(src_md, out_md=None, fmt="svg", which=shutil.which, run=subprocess.run, render=render_mermaid.render_all) -> str` (pre-renders mermaid and writes a marp-ready `<src>.rendered.md`; diagrams persist in a sibling `<out>-assets/` dir so the emitted links resolve after handoff; source untouched). This is the `marp-slide` delegation entry point — unlike `convert_deck`, it does NOT run any backend or clean the diagrams. Raises `MermaidRenderError` on a bad diagram.
  - `main(argv=None) -> int` (0 ok, 2 mermaid abort, 3 backend unavailable).

- [ ] **Step 1: Write the failing test**

```python
class TestDeckAndMain(unittest.TestCase):
    def _stub_run_writes(self, flag="-o"):
        def run(cmd, capture_output=True, text=True):
            out = cmd[cmd.index(flag) + 1]
            open(out, "wb").write(b"%PDF")
            return type("P", (), {"returncode": 0, "stderr": "", "stdout": ""})()
        return run

    def test_convert_deck_uses_marp(self):
        import tempfile
        d = tempfile.mkdtemp(); src = os.path.join(d, "s.md"); open(src, "w").write("# slide\n")
        out = os.path.join(d, "s.pdf")
        res = m2p.convert_deck(src, out_path=out, which=lambda n: "/x/marp" if n == "marp" else None,
                               run=self._stub_run_writes(), render=lambda t, w, fmt="svg", run=None: t)
        self.assertEqual(res.backend, "marp-cli")
        self.assertTrue(os.path.exists(out))

    def test_deck_without_marp_raises(self):
        import tempfile
        src = os.path.join(tempfile.mkdtemp(), "s.md"); open(src, "w").write("x\n")
        with self.assertRaises(m2p.BackendUnavailable) as cm:
            m2p.convert_deck(src, which=lambda n: None, render=lambda t, w, fmt="svg", run=None: t)
        self.assertEqual(cm.exception.recommend.name, "marp-cli")

    def test_main_mermaid_abort_returns_2(self):
        import tempfile
        from unittest import mock
        src = os.path.join(tempfile.mkdtemp(), "d.md"); open(src, "w").write("x\n")
        with mock.patch.object(m2p, "convert",
                               side_effect=render_mermaid.MermaidRenderError(5, "Parse error")):
            self.assertEqual(m2p.main([src]), 2)

    def test_main_backend_unavailable_returns_3(self):
        import tempfile
        from unittest import mock
        src = os.path.join(tempfile.mkdtemp(), "d.md"); open(src, "w").write("x\n")
        with mock.patch.object(m2p, "convert",
                               side_effect=m2p.BackendUnavailable(db.BACKENDS[1])):
            self.assertEqual(m2p.main([src]), 3)

    def test_main_deck_mermaid_abort_returns_2(self):
        # main()'s single `except MermaidRenderError` covers both the non-deck
        # convert() path and the --deck convert_deck() path — verify the latter.
        import tempfile
        from unittest import mock
        src = os.path.join(tempfile.mkdtemp(), "d.md"); open(src, "w").write("x\n")
        with mock.patch.object(m2p, "convert_deck",
                               side_effect=render_mermaid.MermaidRenderError(3, "Parse error")):
            self.assertEqual(m2p.main([src, "--deck"]), 2)

    def test_render_only_emits_md_with_persisted_images(self):
        # marp-slide handoff: pre-render diagrams to a sibling assets dir and emit a
        # .rendered.md whose image links still resolve (NOT inside a cleaned tempdir).
        import tempfile
        d = tempfile.mkdtemp(); src = os.path.join(d, "s.md")
        open(src, "w").write("# deck\n```mermaid\nA-->B\n```\n")
        def fake_render(text, work_dir, fmt="svg", run=None):
            img = os.path.join(work_dir, "diagram-0." + fmt)
            open(img, "wb").write(b"<svg/>")
            return f"# deck\n![diagram]({img})\n"
        out = m2p.render_only(src, render=fake_render)
        self.assertTrue(out.endswith(".rendered.md"))
        body = open(out).read()
        self.assertIn("![diagram](", body)
        link = body.split("![diagram](")[1].split(")")[0]
        self.assertTrue(os.path.exists(link))          # image persisted past the call
        self.assertEqual(open(src).read(), "# deck\n```mermaid\nA-->B\n```\n")  # source untouched
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestDeckAndMain -v`
Expected: FAIL — `AttributeError: module 'markdown_to_pdf' has no attribute 'convert_deck'`

- [ ] **Step 3: Write minimal implementation** (append to `markdown_to_pdf.py`)

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_markdown_to_pdf.TestDeckAndMain -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Run the full module suite**

Run: `python3 -m unittest tests.test_markdown_to_pdf -v`
Expected: PASS (all classes; real-mmdc test PASS or SKIPPED)

- [ ] **Step 6: Commit**

```bash
git add skills/markdown-to-pdf/scripts/markdown_to_pdf.py tests/test_markdown_to_pdf.py
git commit -m "feat(markdown-to-pdf): CLI main() + marp deck path"
```

---

### Task 7: SKILL.md orchestration, references, example, Makefile wiring

**Files:**
- Modify: `skills/markdown-to-pdf/SKILL.md`
- Create: `skills/markdown-to-pdf/references/backends.md`
- Create: `skills/markdown-to-pdf/examples/sample-with-mermaid.md`
- Modify: `Makefile` (add test module to `test` target)

**Interfaces:**
- Consumes: all three scripts (Tasks 1–6).

- [ ] **Step 1: Write `references/backends.md`**

Create `skills/markdown-to-pdf/references/backends.md` with the following exact content (drawn from the design spec §"Backend selection"):

```markdown
# PDF Backend Comparison

Criteria: install ease, agent-friendliness, output quality, image/diagram handling — 1–5 each.

| Backend | Install ease | Agent-friendly | Output quality | Image/diagram | Total /20 | Notes |
|---|---|---|---|---|---|---|
| **Typst + Pandoc** | 5 | 5 | 4 | 4 | **18** | Winner: small self-contained binaries, fast, deterministic, native SVG+PNG |
| Pandoc + LaTeX (tectonic/xelatex) | 2 | 3 | 5 | 3 | 13 | Best typography; heavy; SVG needs `rsvg-convert`; noisy errors |
| WeasyPrint | 4 | 3 | 3 | 3 | 13 | Lightweight Python; needs Pango system lib; patchy SVG; 2-step |
| Headless-Chromium / md-to-pdf | 2 | 2 | 4 | 5 | 13 | Best SVG fidelity; huge Chromium; container-launch fragility |

## Selection rule

Use the best **complete pipeline** already installed, by quality order:
**Pandoc+LaTeX > Typst > WeasyPrint > Chromium**.

If no complete pipeline is installed, recommend the researched winner:
**Typst + Pandoc** — smallest footprint, most agent-friendly, native SVG.

## Install commands (exact, secure-manager only)

**Typst + Pandoc (recommended when nothing installed):**
```
cargo install --locked typst-cli
# download pandoc release binary from https://github.com/jgm/pandoc/releases
```

**Pandoc + LaTeX (tectonic):**
```
cargo install tectonic
# download pandoc release binary from https://github.com/jgm/pandoc/releases
```

**Pandoc + LaTeX (xelatex/pdflatex):**
```
# install TeX Live or MacTeX; download pandoc from https://github.com/jgm/pandoc/releases
```

**WeasyPrint:**
```
uv tool install weasyprint   # also needs the Pango system library (libpango-1.0)
# download pandoc release binary from https://github.com/jgm/pandoc/releases
```

**Headless-Chromium / md-to-pdf:**
```
pnpm add -g md-to-pdf
```

**marp-cli (deck path only):**
```
pnpm add -g @marp-team/marp-cli
```
```

- [ ] **Step 2: Write `examples/sample-with-mermaid.md`**

A short Markdown doc with headings, prose, and one ` ```mermaid ` flowchart — used as the smoke-test input and as a copy-paste example in SKILL.md.

- [ ] **Step 3: Write `SKILL.md`**

Replace the stub content in `skills/markdown-to-pdf/SKILL.md` with the following verbatim:

````markdown
# markdown-to-pdf

Convert a Markdown document with embedded mermaid diagrams to a PDF (or a marp
deck) in a single non-destructive command. Every ` ```mermaid ` block is
extracted, rendered to an image with `mmdc`, substituted back into a copy of the
document, and the rewritten copy is fed to the best available PDF backend.

**Triggers:** "convert markdown to pdf", "render mermaid and export pdf", "md to
pdf", "make a PDF from this doc", "build a deck from this markdown", "export as
marp deck", or any request to turn a `.md` file into a PDF or slide deck.

---

## Primary flow — document to PDF

```
python3 scripts/markdown_to_pdf.py <source.md>
```

On success the script prints:

```
Wrote /path/to/source.pdf  (backend: <name>, diagrams: mmdc(<fmt>))
```

Report this line to the user verbatim so they know which backend ran and what
diagram format was used.

Optional flags:
- `-o <path>` — write PDF to a specific path instead of alongside the source.
- `--format png|svg` — override the mermaid render format (default: determined
  by backend; PNG at `-s 3` is the default for most backends).
- `--backend <name>` — force a specific backend (`pandoc-latex`, `typst`,
  `weasyprint`, `chromium`). Use only when the user explicitly requests one;
  otherwise let auto-selection run.

**Non-destructive guarantee**: the source `.md` is NEVER modified. All work
happens on a temp copy; the temp dir is cleaned up on both success and failure.

**Output location**: PDF lands alongside the source by default, or at the `-o`
path if supplied.

---

## Backend guidance — exit code 3 (BackendUnavailable)

If the script exits with code 3, no PDF was produced. The script printed the
exact install command. Show it to the user as-is and do not attempt to auto-install:

```
No backend available — nothing was converted.
Recommended: install typst:
  cargo install --locked typst-cli   # + the pandoc release binary
```

Selection order (highest quality first): **Pandoc+LaTeX > Typst > WeasyPrint >
Chromium**. The script picks the best **complete pipeline** already installed —
do not nag the user to install a different backend if any complete pipeline works.
Only surface an install recommendation when NO backend is available.

---

## Mermaid abort — exit code 2 (render failure)

If the script exits with code 2, a mermaid block failed to render. The script
printed `mmdc`'s own error, for example:

```
ABORT: mermaid block at line 14 failed to render:
Parse error on line 2: ...
```

No PDF was emitted (correctness-first, all-or-nothing). Tell the user to fix
the block at the indicated source line and re-run.

---

## Marp deck path — secondary output

**Check your available skills first:**

- **If `marp-slide` appears in your available skills**: pre-render the mermaid
  diagrams with `python3 scripts/markdown_to_pdf.py --render-only <source.md>`,
  which writes a marp-ready `<source>.rendered.md` (diagrams rendered to a sibling
  `<source>.rendered-assets/` dir; the source `.md` is untouched) — then delegate
  the full deck build (themes, polish, final export) to `marp-slide`, handing it
  the `.rendered.md`. This gives the user `marp-slide`'s richer theme and layout
  support while the diagrams are already resolved to images.

- **If `marp-slide` is NOT available**: run the deck path directly:

  ```
  python3 scripts/markdown_to_pdf.py --deck <source.md>
  ```

  This drives `marp-cli` directly (must be installed: `pnpm add -g @marp-team/marp-cli`).

Optional deck flags:
- `-o <path>` — output path (default: `<source>.pdf`).
- `--to pdf|pptx|html` — deck output format (default: `pdf`).
- `--format png|svg` — mermaid render format for the deck (default: `svg`).

**This capability conditional is resolved by you reading your own skill list** —
not by any script probe. A Python probe of `~/.claude/plugins/…` is
Claude-Code-specific path coupling that breaks cross-harness portability.

---

## Install commands (secure managers only — never auto-install)

Show these to the user; never run them without explicit user approval.

| Tool | Command |
|---|---|
| Typst | `cargo install --locked typst-cli` |
| Pandoc | download from https://github.com/jgm/pandoc/releases |
| Tectonic (LaTeX) | `cargo install tectonic` |
| WeasyPrint | `uv tool install weasyprint` |
| md-to-pdf (Chromium) | `pnpm add -g md-to-pdf` |
| marp-cli | `pnpm add -g @marp-team/marp-cli` |
| mmdc | `pnpm add -g @mermaid-js/mermaid-cli` |
````

- [ ] **Step 4: Wire the test into the Makefile**

In `Makefile`, extend the `test` target's unittest line to include the new module:

```makefile
test:
	python3 -m unittest tests.test_setup tests.test_status_line tests.test_markdown_to_pdf
	bash tests/test_install.sh
```

Note: `tests.test_framework_profiles` is intentionally omitted here — it is absent from the existing `test` target too (consistent with current repo practice). Do not add it; that is a separate concern outside E6 scope. Similarly, `tests.test_mermaid_style` is also absent from the pre-existing `test` target (matching current repo practice for the mermaid-audit script tests); do not add it here.

- [ ] **Step 5: Verify the suite via the Makefile**

Run: `make test`
Expected: all unittest modules PASS (markdown-to-pdf real-mmdc test PASS or SKIPPED); install tests unaffected.

- [ ] **Step 6: Commit**

```bash
git add skills/markdown-to-pdf/SKILL.md skills/markdown-to-pdf/references/ \
        skills/markdown-to-pdf/examples/ Makefile
git commit -m "feat(markdown-to-pdf): SKILL.md orchestration, references, example, make wiring"
```

---

### Task 8: skill-judge evaluation gate

**Files:**
- Modify (as findings require): any `skills/markdown-to-pdf/` file.

**Interfaces:**
- Consumes: the complete skill (Tasks 1–7).

- [ ] **Step 1: Run skill-judge**

Run `/skill-judge:skill-judge` against `skills/markdown-to-pdf/`. It scores the skill's design (description/trigger quality, structure, clarity, completeness) against the spec.

- [ ] **Step 2: Triage findings**

List each finding with a decision: fix now, or record as out-of-scope with a one-line rationale. Anything that blocks correct triggering or contradicts the spec is fix-now.

- [ ] **Step 3: Apply fixes and re-verify**

Apply fix-now findings. Re-run `make test` (Expected: PASS) and, if SKILL.md prose changed materially, re-run `/skill-judge` once to confirm the blocking findings cleared.

- [ ] **Step 4: Commit**

```bash
git add skills/markdown-to-pdf/
git commit -m "fix(markdown-to-pdf): address skill-judge findings"
```

---

## Self-Review

**Spec coverage** (each FR → task):

| FR | Task |
|---|---|
| FR-6.1 primary MD→PDF | 5 (convert) + 6 (main) |
| FR-6.2 non-destructive temp copy | 5 (source-untouched test) |
| FR-6.3 output alongside / user path | 5 (default + custom-out tests) |
| FR-6.4 adapted extract/render mechanism (header names origin) | 1–2 (render_mermaid + origin header) |
| FR-6.5 backend auto-selection | 3 (select_backend) |
| FR-6.6 detect + secure-install guidance, never auto-install | 6 (exit-3 message) + 7 (SKILL.md) |
| FR-6.7 prefer capable installed | 3 (select returns recommend=None when any available) |
| FR-6.8 marp deck path + marp-slide cooperation | 6 (convert_deck + render_only handoff) + 7 (SKILL.md delegation) |
| FR-6.9 graceful degradation + transparency | 6 (exit codes, prints backend+renderer used) |
| Execution tooling: skill-creator / skill-judge | 1 (scaffold) / 8 (evaluate) |

No gaps.

**Placeholder scan:** no TBD/TODO; every code step shows complete code; the only prose-authoring steps (Task 7 SKILL.md/references) describe exact content sourced from the committed spec.

**Type consistency:** `Backend`/`Selection`/`Result` namedtuples, `MermaidRenderError(.line,.stderr)`, `BackendUnavailable(.recommend)`, `render_all(md, work, fmt, run)`, `convert(...)/convert_deck(...)` signatures, and `build_command(name,in,out,engine)` are used identically across Tasks 2–8. `which`/`run`/`render` injection points are consistent (hermetic tests). Backend names (`pandoc-latex`, `typst`, `weasyprint`, `chromium`, `marp-cli`) match between `detect_backends.BACKENDS`, `build_command`, and tests.
