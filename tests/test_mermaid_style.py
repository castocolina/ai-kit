import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "skills", "mermaid-audit", "scripts"))
import mermaid_style as ms


class TestExtract(unittest.TestCase):
    def test_parses_nodes_shapes_classdefs_edges(self):
        block = (
            "flowchart TD\n"
            "    A[Start] --> B{Choose?}\n"
            "    B -->|yes| C([Done])\n"
            "    B -->|no| D[(user db)]\n"
            "    classDef warn fill:#fee,stroke:#900\n"
            "    class C warn\n"
        )
        f = ms.extract_style_facts(block)
        shapes = {n.id: n.shape for n in f.nodes}
        self.assertEqual(shapes["A"], "rect")
        self.assertEqual(shapes["B"], "rhombus")
        self.assertEqual(shapes["C"], "stadium")
        self.assertEqual(shapes["D"], "cylinder")
        self.assertEqual(f.classdefs["warn"]["fill"], "#fee")
        self.assertEqual(f.node_class["C"], "warn")
        self.assertEqual(f.out_degree["B"], 2)
        self.assertTrue(f.has_labeled_out["B"])
        self.assertEqual(f.out_degree["A"], 1)
        self.assertFalse(f.has_labeled_out["A"])


class TestColorMath(unittest.TestCase):
    def test_parse_hex_3_and_6_digit(self):
        self.assertEqual(ms.parse_hex("#fff"), (255, 255, 255))
        self.assertEqual(ms.parse_hex("#900"), (153, 0, 0))
        self.assertEqual(ms.parse_hex("ffeeee"), (255, 238, 238))
        self.assertIsNone(ms.parse_hex("rgb(1,2,3)"))

    def test_contrast_black_on_white_is_21(self):
        self.assertAlmostEqual(ms.contrast((0, 0, 0), (255, 255, 255)), 21.0, places=1)

    def test_contrast_is_symmetric_and_low_for_similar(self):
        self.assertAlmostEqual(
            ms.contrast((255, 238, 238), (255, 255, 255)),
            ms.contrast((255, 255, 255), (255, 238, 238)), places=6)
        self.assertLess(ms.contrast((255, 238, 238), (255, 255, 255)), 3.0)


def _rules(block):
    f = ms.extract_style_facts(block)
    return {x.rule for x in ms.color_findings(f)}


class TestColorRules(unittest.TestCase):
    def test_C1_large_unstyled_flowchart_flags(self):
        body = "flowchart TD\n" + "\n".join(
            f"    N{i} --> N{i+1}" for i in range(7))
        self.assertIn("C1", _rules(body))

    def test_C1_not_flagged_when_styled(self):
        block = ("flowchart TD\n" + "\n".join(f"    N{i} --> N{i+1}" for i in range(7))
                 + "\n    classDef hot fill:#2e7d32,stroke:#1b5e20,color:#fff\n"
                 + "    class N0 hot\n")
        self.assertNotIn("C1", _rules(block))

    def test_C2_low_contrast_fill_flags(self):
        block = ("flowchart TD\n    A[x] --> B[y]\n"
                 "    classDef faint fill:#ffeeee,stroke:#fff5f5\n    class A faint\n")
        self.assertIn("C2", _rules(block))

    def test_C3_too_many_distinct_fills_flags(self):
        defs = "\n".join(
            f"    classDef c{i} fill:#{h}" for i, h in
            enumerate(["111", "222", "333", "444", "555", "666", "777"]))
        cls = "\n".join(f"    class A{i} c{i}" for i in range(7))
        block = "flowchart TD\n    A0 --> A1\n" + defs + "\n" + cls + "\n"
        self.assertIn("C3", _rules(block))

    def test_C5_red_green_only_channel_flags(self):
        block = ("flowchart TD\n    A[ok] --> B[bad]\n"
                 "    classDef good fill:#2e7d32,color:#fff\n"
                 "    classDef bad fill:#c62828,color:#fff\n"
                 "    class A good\n    class B bad\n")
        self.assertIn("C5", _rules(block))


def _shape_rules(block):
    f = ms.extract_style_facts(block)
    return {x.rule for x in ms.shape_findings(f)}


class TestShapeRules(unittest.TestCase):
    def test_S1_branching_rect_should_be_diamond(self):
        block = ("flowchart TD\n"
                 "    A[Check] -->|yes| B[Go]\n"
                 "    A -->|no| C[Stop]\n")
        self.assertIn("S1", _shape_rules(block))

    def test_S1_not_flagged_when_diamond(self):
        block = ("flowchart TD\n"
                 "    A{Check} -->|yes| B[Go]\n"
                 "    A -->|no| C[Stop]\n")
        self.assertNotIn("S1", _shape_rules(block))

    def test_S3_datastore_word_not_cylinder(self):
        block = "flowchart TD\n    A[Service] --> B[user database]\n"
        self.assertIn("S3", _shape_rules(block))

    def test_S3_not_flagged_when_cylinder(self):
        block = "flowchart TD\n    A[Service] --> B[(user database)]\n"
        self.assertNotIn("S3", _shape_rules(block))

    def test_S4_shape_overload_flags(self):
        block = ("flowchart TD\n"
                 "    A[r] --> B(ro)\n    B --> C([st])\n    C --> D{rh}\n"
                 "    D --> E{{hex}}\n")
        self.assertIn("S4", _shape_rules(block))


import struct, zlib, tempfile, subprocess, re

_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "skills",
                       "mermaid-audit", "scripts", "mermaid_style.py")


class TestCli(unittest.TestCase):
    def test_cli_reports_rule_lines_with_file_and_line(self):
        md = ("# doc\n\n```mermaid\nflowchart TD\n"
              "    A[Check] -->|yes| B[Go]\n    A -->|no| C[Stop]\n```\n")
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
            fh.write(md)
            path = fh.name
        try:
            out = subprocess.run([sys.executable, _SCRIPT, path],
                                 capture_output=True, text=True)
            self.assertIn("S1", out.stdout)
            self.assertRegex(out.stdout, rf"{re.escape(path)}:\d+\tS1\t")
            self.assertEqual(out.returncode, 1)
        finally:
            os.remove(path)

    def test_cli_clean_diagram_exits_zero(self):
        md = ("```mermaid\nflowchart TD\n    A{Check} -->|yes| B[Go]\n"
              "    A -->|no| C[Stop]\n```\n")
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
            fh.write(md)
            path = fh.name
        try:
            out = subprocess.run([sys.executable, _SCRIPT, path],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0)
        finally:
            os.remove(path)


def _make_png(width, height):
    """Minimal valid PNG with a given IHDR width/height (stdlib only)."""
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\x00\x00\x00")
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


class TestGeometry(unittest.TestCase):
    def test_png_size_reads_ihdr(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
            fh.write(_make_png(1280, 360))
            path = fh.name
        try:
            self.assertEqual(ms.png_size(path), (1280, 360))
        finally:
            os.remove(path)

    def test_R1_too_horizontal(self):
        # 1280x360 -> ratio 0.28 < 0.4
        self.assertIn("R1", {f.rule for f in ms.geometry_findings(1280, 360, 8)})

    def test_R2_text_shrinks_below_legible_when_fit_to_column(self):
        # width 1600 -> scale 900/1600=0.56 -> font 16*0.56=9px < 11px
        self.assertIn("R2", {f.rule for f in ms.geometry_findings(1600, 1200, 8)})

    def test_R3_too_tall(self):
        # height 3400 > 3000 (≈3 pages)
        self.assertIn("R3", {f.rule for f in ms.geometry_findings(700, 3400, 30)})

    def test_vertical_in_band_is_clean(self):
        # 760x1100 -> ratio 1.45, width under column, height under 3 pages
        self.assertEqual([], ms.geometry_findings(760, 1100, 10))


class TestPalettes(unittest.TestCase):
    PALETTES = os.path.join(os.path.dirname(__file__), "..", "skills",
                            "mermaid-audit", "references", "palettes.md")

    def _classdef_lines(self):
        with open(self.PALETTES, encoding="utf-8") as fh:
            text = fh.read()
        return [m for m in ms._CLASSDEF_RE.finditer(text)]

    def test_palettes_file_has_classdefs(self):
        self.assertGreaterEqual(len(self._classdef_lines()), 4)

    def test_every_recommended_fill_passes_contrast_gate(self):
        for m in self._classdef_lines():
            props = ms._parse_props(m.group("props"))
            fill = ms.parse_hex(props.get("fill"))
            if not fill:
                continue
            stroke = ms.parse_hex(props.get("stroke"))
            ok = ms.contrast(fill, ms.CANVAS) >= ms.MIN_CONTRAST or (
                stroke is not None and ms.contrast(fill, stroke) >= ms.MIN_CONTRAST)
            self.assertTrue(
                ok, f"recommended classDef {m.group('name')} fails C2 contrast gate")


class TestSkillDocs(unittest.TestCase):
    ROOT = os.path.join(os.path.dirname(__file__), "..", "skills", "mermaid-audit")

    def test_skill_documents_color_shape_pass_and_script(self):
        with open(os.path.join(self.ROOT, "SKILL.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("mermaid_style.py", text)
        self.assertIn("Color & shape", text)
        for rid in ("C1", "C2", "C3", "S1", "S3", "R1", "R2", "R3"):
            self.assertIn(rid, text)

    def test_template_has_color_shape_geometry_status(self):
        with open(os.path.join(self.ROOT, "template.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("COLOR", text)
        self.assertIn("SHAPE", text)
        self.assertIn("GEOMETRY", text)

    def test_bad_examples_are_flagged_and_good_is_clean(self):
        def block(name):
            with open(os.path.join(self.ROOT, "examples", name), encoding="utf-8") as fh:
                return fh.read()
        self.assertIn("C1", {f.rule for f in ms.audit_block(block("bad-no-style.mmd"))})
        self.assertIn("C3", {f.rule for f in ms.audit_block(block("bad-garish.mmd"))})
        self.assertIn("S1", {f.rule for f in ms.audit_block(block("bad-decision-rect.mmd"))})
        self.assertEqual([], ms.audit_block(block("good-palette.mmd")))


import json

_SCORER = os.path.join(os.path.dirname(__file__), "..", "skills",
                       "mermaid-audit", "evals", "score_consensus.py")
sys.path.insert(0, os.path.dirname(_SCORER))


class TestConsensusScorer(unittest.TestCase):
    def setUp(self):
        import score_consensus
        self.sc = score_consensus

    def test_high_agreement_when_judges_concur(self):
        gold = {"01-flat-gray.md": ["C1"], "04-clean.md": []}
        verdicts = [
            {"01-flat-gray.md": ["C1"], "04-clean.md": []},
            {"01-flat-gray.md": ["C1"], "04-clean.md": []},
            {"01-flat-gray.md": ["C1"], "04-clean.md": ["C1"]},  # one false positive
        ]
        report = self.sc.score(gold, verdicts, threshold=0.8)
        self.assertGreaterEqual(report["agreement"]["01-flat-gray.md"]["C1"], 0.99)
        self.assertTrue(report["rule_well_formed"]["C1"])
        self.assertEqual(report["false_positive_rate"]["04-clean.md"], 1 / 3)

    def test_rule_not_well_formed_on_split_judges(self):
        gold = {"03-decision-rect.md": ["S1"]}
        verdicts = [
            {"03-decision-rect.md": ["S1"]},
            {"03-decision-rect.md": []},
            {"03-decision-rect.md": []},  # only 1/3 agree -> below 0.8
        ]
        report = self.sc.score(gold, verdicts, threshold=0.8)
        self.assertFalse(report["rule_well_formed"]["S1"])

    def test_load_verdicts_from_dir(self):
        with tempfile.TemporaryDirectory() as d:
            for i, v in enumerate([{"x.md": ["C1"]}, {"x.md": ["C1"]}]):
                with open(os.path.join(d, f"judge{i}.json"), "w") as fh:
                    json.dump(v, fh)
            loaded = self.sc.load_verdicts(d)
            self.assertEqual(len(loaded), 2)


if __name__ == "__main__":
    unittest.main()
