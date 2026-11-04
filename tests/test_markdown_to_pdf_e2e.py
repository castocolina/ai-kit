# tests/test_markdown_to_pdf_e2e.py
"""The real Mermaid render, e2e tier only.

Chrome comes from the caller's Puppeteer cache, which the runner forwards into the pinned
HOME (`tool_cache_forwards`). Availability is decided by one real probe render, so a partial
cache or a wrong browser path skips with a name instead of failing.
"""
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "skills", "markdown-to-pdf", "scripts"))
import render_mermaid as rm

# The two browser-missing texts Puppeteer printed on 2026-11-03 (mermaid-cli 11.17.0): an empty
# or partial cache, and a PUPPETEER_EXECUTABLE_PATH that points at no file.
BROWSER_MISSING = re.compile(
    r"Could not find (Chrome|chrome-headless-shell)"
    r"|Tried to find the browser at the configured path"
)
DIAGRAM = "flowchart TD\n  A-->B\n"


class TestRenderRealMmdc(unittest.TestCase):
    probe_error = None

    @classmethod
    def setUpClass(cls):
        if not shutil.which("mmdc"):
            raise unittest.SkipTest("mmdc not installed")
        with tempfile.TemporaryDirectory() as work:
            rc, err = rm.render_one(DIAGRAM, os.path.join(work, "probe.png"),
                                    rm._puppeteer_config(work))
        if rc == 0:
            return
        if BROWSER_MISSING.search(err or ""):
            raise unittest.SkipTest(
                "headless Chrome not found (PUPPETEER_EXECUTABLE_PATH or the Puppeteer cache)"
            )
        cls.probe_error = err

    def test_real_render_produces_image(self):
        self.assertIsNone(self.probe_error, f"probe render failed: {self.probe_error}")
        md = f"```mermaid\n{DIAGRAM}```\n"
        work = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, work, ignore_errors=True)
        out = rm.render_all(md, work, fmt="png")
        self.assertIn("![diagram](", out)
        self.assertTrue(os.path.exists(os.path.join(work, "diagram-0.png")))


if __name__ == "__main__":
    unittest.main()
