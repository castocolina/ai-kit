# tests/test_markdown_to_pdf.py
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "skills", "markdown-to-pdf", "scripts"))
import detect_backends as db
import markdown_to_pdf as m2p
import render_mermaid
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


class TestRenderAll(unittest.TestCase):
    def _fake_run_ok(self):
        def run(cmd, capture_output=True, text=True):
            # assert mmdc was called with high-DPI scale flag
            self.assertIn("-s", cmd)
            self.assertEqual(cmd[cmd.index("-s") + 1], "3")
            out = cmd[cmd.index("-o") + 1]          # mmdc -i ... -o <out>
            with open(out, "wb") as fh:              # pretend mmdc rendered it
                fh.write(b"\x89PNG")
            return type("P", (), {"returncode": 0, "stderr": "", "stdout": ""})()
        return run

    def test_substitutes_fences_with_image_links(self):
        md = "a\n```mermaid\nflowchart TD\nX-->Y\n```\nb\n"
        work = tempfile.mkdtemp()
        out = rm.render_all(md, work, fmt="png", run=self._fake_run_ok())
        self.assertNotIn("```mermaid", out)
        self.assertIn("![diagram](", out)
        self.assertIn("diagram-0.png", out)

    def test_aborts_with_line_and_stderr_on_failure(self):
        md = "a\n```mermaid\nbroken!!!\n```\n"
        def run_fail(cmd, capture_output=True, text=True):
            return type("P", (), {"returncode": 1,
                                  "stderr": "Parse error on line 2: ...", "stdout": ""})()
        with self.assertRaises(rm.MermaidRenderError) as cm:
            rm.render_all(md, tempfile.mkdtemp(), run=run_fail)
        self.assertEqual(cm.exception.line, 3)       # open-fence line 2 + mmdc line 2 - 1
        self.assertIn("Parse error", cm.exception.stderr)

    def test_no_fences_passthrough(self):
        # work_dir is never touched when there are no fences; use a real tempdir
        # to avoid relying on /tmp existing and to be safe against future changes
        # that call _puppeteer_config(work_dir) before the early-return check.
        self.assertEqual(rm.render_all("plain\n", tempfile.mkdtemp()), "plain\n")


class TestRenderRealMmdc(unittest.TestCase):
    @unittest.skipUnless(shutil.which("mmdc"), "mmdc not installed")
    def test_real_render_produces_image(self):
        md = "```mermaid\nflowchart TD\n  A-->B\n```\n"
        work = tempfile.mkdtemp()
        out = rm.render_all(md, work, fmt="png")
        self.assertIn("![diagram](", out)
        self.assertTrue(os.path.exists(os.path.join(work, "diagram-0.png")))


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


class TestConvert(unittest.TestCase):
    def _stub_run_writes_pdf(self):
        def run(cmd, capture_output=True, text=True):
            out = cmd[cmd.index("-o") + 1] if "-o" in cmd else cmd[cmd.index("--output") + 1]
            with open(out, "wb") as fh:
                fh.write(b"%PDF-1.7\n")
            return type("P", (), {"returncode": 0, "stderr": "", "stdout": ""})()
        return run

    def _fake_render(self, text, work_dir, fmt="png", run=None):
        return text  # pretend diagrams rendered; no mmdc needed

    def test_writes_pdf_alongside_source_without_touching_it(self):
        d = tempfile.mkdtemp()
        src = os.path.join(d, "doc.md")
        with open(src, "w") as fh:
            fh.write("# hi\n```mermaid\nA-->B\n```\n")
        with open(src, "rb") as fh:
            before = fh.read()
        which = lambda n: "/x/" + n if n in {"pandoc", "pdflatex"} else None
        res = m2p.convert(src, which=which, run=self._stub_run_writes_pdf(),
                          render=self._fake_render)
        self.assertEqual(res.backend, "pandoc-latex")
        self.assertTrue(res.out.endswith("doc.pdf"))
        self.assertTrue(os.path.exists(res.out))
        with open(src, "rb") as fh:
            self.assertEqual(fh.read(), before)   # source untouched (FR-6.2)

    def test_custom_out_path(self):
        d = tempfile.mkdtemp()
        src = os.path.join(d, "doc.md")
        with open(src, "w") as fh:
            fh.write("hi\n")
        which = lambda n: "/x/" + n if n in {"md-to-pdf"} else None
        # sub/ is intentionally NOT pre-created — convert() must make it
        out = os.path.join(d, "sub", "x.pdf")
        res = m2p.convert(src, out_path=out, which=which,
                          run=self._stub_run_writes_pdf(), render=self._fake_render)
        self.assertEqual(res.out, out)

    def test_no_backend_raises_backend_unavailable(self):
        src = os.path.join(tempfile.mkdtemp(), "doc.md")
        with open(src, "w") as fh:
            fh.write("hi\n")
        with self.assertRaises(m2p.BackendUnavailable) as cm:
            m2p.convert(src, which=lambda n: None, render=self._fake_render)
        self.assertEqual(cm.exception.recommend.name, "typst")

    def test_render_failure_propagates_and_emits_nothing(self):
        d = tempfile.mkdtemp(); src = os.path.join(d, "doc.md")
        with open(src, "w") as fh:
            fh.write("```mermaid\nbad\n```\n")
        def bad_render(text, work_dir, fmt="png", run=None):
            raise render_mermaid.MermaidRenderError(1, "Parse error on line 1")
        which = lambda n: "/x/" + n if n in {"pandoc", "pdflatex"} else None
        with self.assertRaises(render_mermaid.MermaidRenderError):
            m2p.convert(src, which=which, run=self._stub_run_writes_pdf(), render=bad_render)
        self.assertFalse(os.path.exists(os.path.join(d, "doc.pdf")))


class TestDeckAndMain(unittest.TestCase):
    def _stub_run_writes(self, flag="-o"):
        def run(cmd, capture_output=True, text=True):
            out = cmd[cmd.index(flag) + 1]
            with open(out, "wb") as fh:
                fh.write(b"%PDF")
            return type("P", (), {"returncode": 0, "stderr": "", "stdout": ""})()
        return run

    def test_convert_deck_uses_marp(self):
        d = tempfile.mkdtemp(); src = os.path.join(d, "s.md")
        with open(src, "w") as fh:
            fh.write("# slide\n")
        out = os.path.join(d, "s.pdf")
        res = m2p.convert_deck(
            src, out_path=out, which=lambda n: "/x/marp" if n == "marp" else None,
            run=self._stub_run_writes(), render=lambda t, w, fmt="svg", run=None: t)
        self.assertEqual(res.backend, "marp-cli")
        self.assertTrue(os.path.exists(out))

    def test_deck_without_marp_raises(self):
        src = os.path.join(tempfile.mkdtemp(), "s.md")
        with open(src, "w") as fh:
            fh.write("x\n")
        with self.assertRaises(m2p.BackendUnavailable) as cm:
            m2p.convert_deck(src, which=lambda n: None, render=lambda t, w, fmt="svg", run=None: t)
        self.assertEqual(cm.exception.recommend.name, "marp-cli")

    def test_main_mermaid_abort_returns_2(self):
        from unittest import mock
        src = os.path.join(tempfile.mkdtemp(), "d.md")
        with open(src, "w") as fh:
            fh.write("x\n")
        with mock.patch.object(m2p, "convert",
                               side_effect=render_mermaid.MermaidRenderError(5, "Parse error")):
            self.assertEqual(m2p.main([src]), 2)

    def test_main_backend_unavailable_returns_3(self):
        from unittest import mock
        src = os.path.join(tempfile.mkdtemp(), "d.md")
        with open(src, "w") as fh:
            fh.write("x\n")
        with mock.patch.object(m2p, "convert",
                               side_effect=m2p.BackendUnavailable(db.BACKENDS[1])):
            self.assertEqual(m2p.main([src]), 3)

    def test_main_deck_mermaid_abort_returns_2(self):
        # main()'s single `except MermaidRenderError` covers both the non-deck
        # convert() path and the --deck convert_deck() path — verify the latter.
        from unittest import mock
        src = os.path.join(tempfile.mkdtemp(), "d.md")
        with open(src, "w") as fh:
            fh.write("x\n")
        with mock.patch.object(m2p, "convert_deck",
                               side_effect=render_mermaid.MermaidRenderError(3, "Parse error")):
            self.assertEqual(m2p.main([src, "--deck"]), 2)

    def test_render_only_emits_md_with_persisted_images(self):
        # marp-slide handoff: pre-render diagrams to a sibling assets dir and emit a
        # .rendered.md whose image links still resolve (NOT inside a cleaned tempdir).
        d = tempfile.mkdtemp(); src = os.path.join(d, "s.md")
        with open(src, "w") as fh:
            fh.write("# deck\n```mermaid\nA-->B\n```\n")
        def fake_render(text, work_dir, fmt="svg", run=None):
            img = os.path.join(work_dir, "diagram-0." + fmt)
            with open(img, "wb") as fh:
                fh.write(b"<svg/>")
            return f"# deck\n![diagram]({img})\n"
        out = m2p.render_only(src, render=fake_render)
        self.assertTrue(out.endswith(".rendered.md"))
        with open(out) as fh:
            body = fh.read()
        self.assertIn("![diagram](", body)
        link = body.split("![diagram](")[1].split(")")[0]
        self.assertTrue(os.path.exists(link))          # image persisted past the call
        with open(src) as fh:
            self.assertEqual(fh.read(), "# deck\n```mermaid\nA-->B\n```\n")  # source untouched
