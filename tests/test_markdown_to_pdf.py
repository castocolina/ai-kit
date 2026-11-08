# tests/test_markdown_to_pdf.py
import contextlib
import io
import os
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
        def run(cmd, capture_output=True, text=True, **kwargs):
            del capture_output, kwargs
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
        def run_fail(cmd, capture_output=True, text=True, **kwargs):
            del capture_output, kwargs
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
        self.assertEqual(cmd, ["md-to-pdf", "in.md", "--basedir", os.path.abspath(os.sep),
                               "--launch-options", m2p.CHROME_LAUNCH_OPTIONS])
        self.assertEqual(m2p.CHROME_LAUNCH_OPTIONS,
                         '{"args":["--no-sandbox","--disable-setuid-sandbox"]}')

    def test_resolve_engine_prefers_tectonic(self):
        which = lambda n: "/x/" + n if n in {"tectonic", "pdflatex"} else None
        b = next(x for x in db.BACKENDS if x.name == "pandoc-latex")
        self.assertEqual(m2p._resolve_engine(b, which), "tectonic")


class TestConvert(unittest.TestCase):
    def _stub_run_writes_pdf(self):
        def run(cmd, capture_output=True, text=True, **kwargs):
            del capture_output, kwargs
            if cmd[0] == "md-to-pdf":  # md-to-pdf writes <stem>.pdf beside its input
                out = os.path.splitext(cmd[1])[0] + ".pdf"
            else:
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
        opts = m2p.ConvertOptions(which=which, run=self._stub_run_writes_pdf(),
                                  render=self._fake_render)
        res = m2p.convert(src, opts)
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
        opts = m2p.ConvertOptions(
            out_path=out,
            which=which,
            run=self._stub_run_writes_pdf(),
            render=self._fake_render,
        )
        res = m2p.convert(src, opts)
        self.assertEqual(res.out, out)

    def test_no_backend_raises_backend_unavailable(self):
        src = os.path.join(tempfile.mkdtemp(), "doc.md")
        with open(src, "w") as fh:
            fh.write("hi\n")
        with self.assertRaises(m2p.BackendUnavailable) as cm:
            m2p.convert(src, m2p.ConvertOptions(which=lambda n: None, render=self._fake_render))
        self.assertEqual(cm.exception.recommend.name, "typst")

    def test_render_failure_propagates_and_emits_nothing(self):
        d = tempfile.mkdtemp(); src = os.path.join(d, "doc.md")
        with open(src, "w") as fh:
            fh.write("```mermaid\nbad\n```\n")
        def bad_render(text, work_dir, fmt="png", run=None):
            raise render_mermaid.MermaidRenderError(1, "Parse error on line 1")
        which = lambda n: "/x/" + n if n in {"pandoc", "pdflatex"} else None
        with self.assertRaises(render_mermaid.MermaidRenderError):
            m2p.convert(
                src,
                m2p.ConvertOptions(which=which, run=self._stub_run_writes_pdf(), render=bad_render),
            )
        self.assertFalse(os.path.exists(os.path.join(d, "doc.pdf")))


class TestDeckAndMain(unittest.TestCase):
    def _stub_run_writes(self, flag="-o"):
        def run(cmd, capture_output=True, text=True, **kwargs):
            del capture_output, kwargs
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
        opts = m2p.ConvertOptions(
            out_path=out,
            which=lambda n: "/x/marp" if n == "marp" else None,
            run=self._stub_run_writes(),
            render=lambda t, _w, fmt="svg", run=None: t,
        )
        res = m2p.convert_deck(src, opts)
        self.assertEqual(res.backend, "marp-cli")
        self.assertTrue(os.path.exists(out))

    def test_deck_without_marp_raises(self):
        src = os.path.join(tempfile.mkdtemp(), "s.md")
        with open(src, "w") as fh:
            fh.write("x\n")
        with self.assertRaises(m2p.BackendUnavailable) as cm:
            m2p.convert_deck(
                src,
                m2p.ConvertOptions(
                    which=lambda n: None,
                    render=lambda t, _w, fmt="svg", run=None: t,
                ),
            )
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
        out = m2p.render_only(src, m2p.ConvertOptions(render=fake_render))
        self.assertTrue(out.endswith(".rendered.md"))
        with open(out) as fh:
            body = fh.read()
        self.assertIn("![diagram](", body)
        link = body.split("![diagram](")[1].split(")")[0]
        self.assertTrue(os.path.exists(link))          # image persisted past the call
        with open(src) as fh:
            self.assertEqual(fh.read(), "# deck\n```mermaid\nA-->B\n```\n")  # source untouched


class TestBackendFailure(unittest.TestCase):
    def _recording_run(self, record, returncode=0, stderr=""):
        def run(cmd, capture_output=True, text=True, **kwargs):
            del capture_output, kwargs
            record.append(cmd)
            if returncode == 0:
                out = cmd[cmd.index("-o") + 1]
                with open(out, "wb") as fh:
                    fh.write(b"%PDF-1.7\n")
            return type("P", (), {"returncode": returncode, "stderr": stderr, "stdout": ""})()
        return run

    def _src(self, d):
        src = os.path.join(d, "doc.md")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write("# hi\n![a](img/a.svg)\n")
        return src

    def test_resource_path_appended_for_pandoc(self):
        cmd = m2p.build_command("typst", "in.md", "out.pdf", engine="typst", resource_dir="/src")
        self.assertEqual(cmd[-2:], ["--pdf-engine=typst", "--resource-path=/src"])

    def test_convert_passes_the_source_folder(self):
        d = tempfile.mkdtemp()
        src = self._src(d)
        record = []
        which = lambda n: "/x/" + n if n in {"pandoc", "pdflatex"} else None
        m2p.convert(src, m2p.ConvertOptions(which=which, run=self._recording_run(record),
                                            render=lambda t, _w, fmt="png", run=None: t))
        self.assertIn(f"--resource-path={d}", record[0])

    def test_failing_backend_raises_backend_failed(self):
        d = tempfile.mkdtemp()
        src = self._src(d)
        which = lambda n: "/x/" + n if n in {"pandoc", "pdflatex"} else None
        opts = m2p.ConvertOptions(which=which, run=self._recording_run([], 1, "boom"),
                                  render=lambda t, _w, fmt="png", run=None: t)
        with self.assertRaises(m2p.BackendFailed) as cm:
            m2p.convert(src, opts)
        self.assertIn("pandoc-latex failed: boom", str(cm.exception))
        self.assertFalse(os.path.exists(os.path.join(d, "doc.pdf")))

    def test_main_backend_failed_returns_4_with_stderr(self):
        from unittest import mock
        src = self._src(tempfile.mkdtemp())
        err = io.StringIO()
        with mock.patch.object(m2p, "convert",
                               side_effect=m2p.BackendFailed("pandoc-latex failed: boom")), \
                contextlib.redirect_stderr(err):
            code = m2p.main([src])
        self.assertEqual(code, 4)
        self.assertIn("boom", err.getvalue())

    def test_main_does_not_catch_a_bare_runtime_error(self):
        from unittest import mock
        src = self._src(tempfile.mkdtemp())
        with mock.patch.object(m2p, "convert", side_effect=RuntimeError("x")), \
                self.assertRaises(RuntimeError):
            m2p.main([src])

    def test_backend_failed_is_a_runtime_error(self):
        self.assertTrue(issubclass(m2p.BackendFailed, RuntimeError))


class TestLocalAssets(unittest.TestCase):
    # The stubs read the copy while it still exists: the work folder is removed on return.
    def _pdf_run(self, record):
        def run(cmd, capture_output=True, text=True, **kwargs):
            del capture_output, kwargs
            with open(cmd[1], encoding="utf-8") as fh:
                record.append((cmd, fh.read()))
            out = (os.path.splitext(cmd[1])[0] + ".pdf") if cmd[0] == "md-to-pdf" \
                else cmd[cmd.index("-o") + 1]
            with open(out, "wb") as fh:
                fh.write(b"%PDF-1.7\n")
            return type("P", (), {"returncode": 0, "stderr": "", "stdout": ""})()
        return run

    def _deck_run(self, record):
        def run(cmd, capture_output=True, text=True, **kwargs):
            del capture_output, kwargs
            with open(cmd[1], encoding="utf-8") as fh:
                record.append((cmd, fh.read()))
            with open(cmd[cmd.index("-o") + 1], "w", encoding="utf-8") as fh:
                fh.write(record[-1][1])
            return type("P", (), {"returncode": 0, "stderr": "", "stdout": ""})()
        return run

    def _write(self, path, text):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def _mermaid_render(self, text, work_dir, fmt="svg", run=None):
        img = os.path.join(work_dir, "diagram-0." + fmt)
        with open(img, "wb") as fh:
            fh.write(b"<svg/>")
        return text.replace("```mermaid\nA-->B\n```\n", f"![diagram]({img})\n")

    def test_absolutize_images_rewrites_relative_links_only(self):
        d = tempfile.mkdtemp()
        text = ("![a](img/a.svg)\n![b](./b.png)\n![c](sub/deep/c.png \"T\")\n"
                "![s](<my img.png>)\n![u](https://example.com/x.png)\n"
                "![x](data:image/png;base64,AA)\n![z](/already/abs.png)\n")
        want = ("![a](" + os.path.join(d, "img", "a.svg") + ")\n"
                "![b](" + os.path.join(d, "b.png") + ")\n"
                "![c](" + os.path.join(d, "sub", "deep", "c.png") + " \"T\")\n"
                "![s](<" + os.path.join(d, "my img.png") + ">)\n"
                "![u](https://example.com/x.png)\n"
                "![x](data:image/png;base64,AA)\n"
                "![z](/already/abs.png)\n")
        self.assertEqual(m2p._absolutize_images(text, d), want)
        self.assertEqual(m2p._absolutize_images("no image here\n", d), "no image here\n")

    def test_chromium_gets_absolute_links_and_its_own_output_path(self):
        d = tempfile.mkdtemp()
        src = self._write(os.path.join(d, "doc.md"), "# hi\n![a](img/a.svg)\n")
        out = os.path.join(d, "out.pdf")
        record = []
        which = lambda n: "/x/md-to-pdf" if n == "md-to-pdf" else None
        res = m2p.convert(src, m2p.ConvertOptions(
            out_path=out, which=which, run=self._pdf_run(record),
            render=lambda t, _w, fmt="png", run=None: t))
        cmd, copy_text = record[0]
        self.assertEqual(cmd[0], "md-to-pdf")
        self.assertIn(f"![a]({os.path.join(d, 'img', 'a.svg')})", copy_text)
        self.assertEqual(res.out, out)
        self.assertEqual(sorted(os.listdir(d)), ["doc.md", "out.pdf"])

    def test_every_deck_call_allows_local_files(self):
        d = tempfile.mkdtemp()
        src = self._write(os.path.join(d, "s.md"), "# slide\n")
        which = lambda n: "/x/marp" if n == "marp" else None
        for to in ("pdf", "pptx", "html"):
            record = []
            m2p.convert_deck(src, m2p.ConvertOptions(
                out_path=os.path.join(d, "s." + to), deck_to=to, which=which,
                run=self._deck_run(record), render=lambda t, _w, fmt="svg", run=None: t))
            self.assertIn("--allow-local-files", record[0][0])

    def test_pdf_and_pptx_decks_get_absolute_image_links_html_keeps_relative(self):
        d = tempfile.mkdtemp()
        src = self._write(os.path.join(d, "s.md"), "# slide\n![a](img/a.svg)\n")
        which = lambda n: "/x/marp" if n == "marp" else None
        for to in ("pdf", "pptx"):
            out = os.path.join(d, "s." + to)
            m2p.convert_deck(src, m2p.ConvertOptions(
                out_path=out, deck_to=to, which=which, run=self._deck_run([]),
                render=lambda t, _w, fmt="svg", run=None: t))
            with open(out, encoding="utf-8") as fh:
                self.assertIn(f"![a]({os.path.join(d, 'img', 'a.svg')})", fh.read())
        out = os.path.join(d, "s.html")
        m2p.convert_deck(src, m2p.ConvertOptions(
            out_path=out, deck_to="html", which=which, run=self._deck_run([]),
            render=lambda t, _w, fmt="svg", run=None: t))
        with open(out, encoding="utf-8") as fh:
            self.assertIn("![a](img/a.svg)", fh.read())

    def test_html_deck_diagrams_survive_next_to_the_output(self):
        d = tempfile.mkdtemp()
        src = self._write(os.path.join(d, "s.md"), "# deck\n```mermaid\nA-->B\n```\n")
        out = os.path.join(d, "s.html")
        which = lambda n: "/x/marp" if n == "marp" else None
        m2p.convert_deck(src, m2p.ConvertOptions(
            out_path=out, deck_to="html", which=which, run=self._deck_run([]),
            render=self._mermaid_render))
        with open(out, encoding="utf-8") as fh:
            self.assertIn("s-assets/diagram-0.svg", fh.read())
        self.assertTrue(os.path.exists(os.path.join(d, "s-assets", "diagram-0.svg")))
        self.assertEqual(sorted(os.listdir(d)), sorted(["s.md", "s.html", "s-assets"]))

    def test_html_deck_without_diagrams_creates_no_assets(self):
        d = tempfile.mkdtemp()
        src = self._write(os.path.join(d, "s.md"), "# slide\n")
        which = lambda n: "/x/marp" if n == "marp" else None
        for to in ("html", "pdf"):
            m2p.convert_deck(src, m2p.ConvertOptions(
                out_path=os.path.join(d, "s." + to), deck_to=to, which=which,
                run=self._deck_run([]), render=lambda t, _w, fmt="svg", run=None: t))
        self.assertEqual(sorted(os.listdir(d)), sorted(["s.md", "s.html", "s.pdf"]))

    def test_two_html_decks_keep_separate_assets(self):
        d = tempfile.mkdtemp()
        src = self._write(os.path.join(d, "s.md"), "# deck\n```mermaid\nA-->B\n```\n")
        which = lambda n: "/x/marp" if n == "marp" else None
        for name in ("a", "b"):
            m2p.convert_deck(src, m2p.ConvertOptions(
                out_path=os.path.join(d, name + ".html"), deck_to="html", which=which,
                run=self._deck_run([]), render=self._mermaid_render))
        for name, other in (("a", "b"), ("b", "a")):
            self.assertTrue(os.path.exists(os.path.join(d, name + "-assets", "diagram-0.svg")))
            with open(os.path.join(d, name + ".html"), encoding="utf-8") as fh:
                body = fh.read()
            self.assertIn(f"{name}-assets/diagram-0.svg", body)
            self.assertNotIn(f"{other}-assets", body)
