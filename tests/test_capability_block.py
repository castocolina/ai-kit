"""39-10: the lane capability block (SPEC R4, D-04 to D-06)."""

import json
import os
import pathlib
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parents[1] / "skills" / "ai-kit-spec-review")
)

from ai_kit_spec.capability_block import (
    ENABLED_INDEX_LINE,
    NO_INDEX_LINE,
    NO_PREVIEW_REASON,
    NO_SHELL_LINE,
    NO_TOOL_LINE,
    SECTIONS,
    SHELL_IF,
    UNKNOWN_TEXT,
    BlockInput,
    LaneFacts,
    build_block,
    child_path,
    summary_line,
    unknown_facts,
)
from ai_kit_spec.lens_delivery import mcp_pick
from ai_kit_spec.tooling_guidance import _code_index_line


def fact(value, source="from argv", state="verified"):
    return {"value": value, "label": {"state": state, "source": source}}


def make_bin(root, names):
    folder = pathlib.Path(root) / "bin"
    folder.mkdir()
    for name in names:
        path = folder / name
        path.write_text("#!/bin/sh\nexit 0\n")
        os.chmod(path, 0o755)
    return folder


PI_FACTS = LaneFacts(
    write=fact("none", "from argv"), shell=fact("no", "from argv --tools"),
    skills=fact("path", "from argv --skill"), mcp=fact("none", "from argv --no-mcp"),
    prompt={"channel": "stdin", "max_bytes": None},
    skill_settings=({"name": "lens-a", "state": "applied", "reason": None, "form": "path"},),
    settings=({"name": "model", "value": "fake/placeholder-model-1"},),
)


class TestBlock(unittest.TestCase):
    def test_pi_review_block_golden(self):
        with tempfile.TemporaryDirectory() as root:
            folder = make_bin(root, ("rg", "codebase-memory-mcp"))
            lane = BlockInput(
                PI_FACTS, {"PATH": str(folder), "HOME": root}, {"skills": [], "mcp": []},
                [{"name": "lens-a", "path": "/fake/skills/lens-a", "note": None,
                  "skill_name": "lens-a"}], "review", "pi", "fake/placeholder-model-1",
            )
            self.assertEqual(build_block(lane), (
                "LANE\nruntime: pi\nmodel: fake/placeholder-model-1\nrole: review\n\n"
                "ACCESS\nwrite: none (read-only) [verified: from argv]\n"
                "shell: no (no shell tool) [verified: from argv --tools]\n"
                "skills: path (your host loads skills passed by path) "
                "[verified: from argv --skill]\n"
                "mcp: none (no MCP tools) [verified: from argv --no-mcp]\n\n"
                "TOOLS\nnone: this lane has no shell tool\n\n"
                "CODE INDEX\nnone: no code index for this lane\n\n"
                "SKILLS\nlens-a: delivered by path, loaded by your host from "
                "/fake/skills/lens-a\n\n"
                "SETTINGS\nmodel: fake/placeholder-model-1 (applied)"
            ))

    def test_summary_line(self):
        base = "write=none shell=no skills=path mcp=none prompt=stdin"
        self.assertEqual(summary_line(PI_FACTS, "pi", "fake/placeholder-model-1", "review"), base)
        argv = PI_FACTS._replace(prompt={"channel": "argv", "max_bytes": 102000})
        self.assertEqual(summary_line(argv, "pi", "fake/placeholder-model-1", "review"),
                         base.replace("stdin", "argv max_bytes=102000"))
        full = PI_FACTS._replace(write=fact("full"))
        self.assertTrue(summary_line(full, "pi", "fake/placeholder-model-1", "execute")
                        .endswith(" soft-confinement=prose"))
        self.assertEqual(summary_line(unknown_facts(NO_PREVIEW_REASON), "placeholder-cli-1",
                                      "placeholder-model-1", "review"),
                         "write=unknown shell=unknown skills=unknown mcp=unknown prompt=unknown ("
                         + NO_PREVIEW_REASON + ")")
        notes = ("guidance omitted: AGENTS_TOOLING_PATH (path_outside_roots)",
                 "documents from other worktrees: 1 (/fake/wt-2)")
        suffix = "".join("; note: " + note for note in notes)
        self.assertEqual(summary_line(PI_FACTS, "pi", "fake/placeholder-model-1", "review", notes),
                         base + suffix)
        self.assertEqual(summary_line(None, "claude", "placeholder-model-1", "review"),
                         "native lane, no tool claims")
        self.assertEqual(summary_line(None, "claude", "placeholder-model-1", "review", notes),
                         "native lane, no tool claims" + suffix)


class TestBlockEdges(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.bin = make_bin(self.root, ())
        self.lane = BlockInput(PI_FACTS, {"HOME": str(self.root), "PATH": str(self.bin)},
                               {"skills": [], "mcp": []}, [], "review", "claude",
                               "placeholder-model-1")

    def add_tool(self, name):
        path = self.bin / name
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)

    def section(self, lane, header):
        return next(part.splitlines() for part in build_block(lane).split("\n\n")
                    if part.splitlines()[0] == header)

    def config(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"mcpServers": {"codebase-memory-mcp":
                                                  {"command": "fake-cmd"}}}))

    def test_claude_review_mcp_only_when_registered(self):
        self.add_tool("codebase-memory-mcp")
        lane = self.lane._replace(facts=PI_FACTS._replace(shell=fact("unknown"),
                                                          mcp=fact("unknown")))
        self.assertEqual(self.section(lane, "CODE INDEX"),
                         ["CODE INDEX", SHELL_IF + _code_index_line(False, "claude")])
        self.config(self.root / ".claude.json")
        self.assertEqual(self.section(lane, "CODE INDEX"),
                         ["CODE INDEX", _code_index_line(True, "claude")])
        self.assertNotIn("codebase-memory-mcp cli", build_block(lane))

    def test_route_one_enabled_for_this_call(self):
        self.add_tool("codebase-memory-mcp")
        facts = PI_FACTS._replace(mcp=fact("call_file"), mcp_settings=(
            {"name": "codebase-memory-mcp", "state": "applied", "reason": None},))
        lane = self.lane._replace(runtime="copilot", facts=facts)
        self.config(self.root / ".copilot" / "mcp-config.json")
        for shell in ("no", "unknown"):
            current = lane._replace(facts=facts._replace(shell=fact(shell)))
            self.assertEqual(self.section(current, "CODE INDEX"),
                             ["CODE INDEX", ENABLED_INDEX_LINE])
            sections = [s for s in build_block(current).split("\n\n")
                        if not s.startswith("TOOLS\n")]
            self.assertEqual(sum("codebase-memory-mcp" in line for s in sections
                                 for line in s.splitlines()), 1)

    def test_cbm_absent_from_child_path(self):
        parent = self.root / "parent"
        parent.mkdir()
        parent_bin = make_bin(parent, ("codebase-memory-mcp",))
        lane = self.lane._replace(facts=PI_FACTS._replace(shell=fact("yes")))
        with patch.dict(os.environ, {"PATH": str(parent_bin)}):
            self.assertEqual(self.section(lane, "CODE INDEX"), ["CODE INDEX", NO_INDEX_LINE])
            self.assertNotIn("codebase-memory-mcp", build_block(lane))

    def test_tools_follow_child_path_not_parent(self):
        parent = self.root / "parent"
        parent.mkdir()
        parent_bin = make_bin(parent, ("fd", "rg"))
        self.add_tool("rg")
        facts = PI_FACTS._replace(shell=fact("yes", "from argv ghp_" + "a" * 30))
        lane = self.lane._replace(facts=facts)
        with patch.dict(os.environ, {"PATH": str(parent_bin)}):
            self.assertIn('TOOL_AVAILABILITY = {"rg":true}', self.section(lane, "TOOLS"))
            self.assertIn("If you have a shell, these tools are on its PATH: rg.",
                          build_block(lane))
            self.assertIn("<redacted>", self.section(lane, "ACCESS")[2])
            self.add_tool("fd")
            self.assertIn('TOOL_AVAILABILITY = {"fd":true,"rg":true}', build_block(lane))
            self.assertIn("PATH: fd, rg.", build_block(lane))
            no_path = lane._replace(child_env={"HOME": str(self.root)})
            self.assertEqual(self.section(no_path, "TOOLS"), ["TOOLS", NO_TOOL_LINE])
            relative = lane._replace(child_env={"PATH": "bin"})
            self.assertEqual(self.section(relative, "TOOLS"), ["TOOLS", NO_TOOL_LINE])
            self.assertEqual(self.section(relative._replace(cwd=str(self.root)), "TOOLS"),
                             ["TOOLS", NO_TOOL_LINE])
        path = str(self.root / "agents")
        self.assertIn("AGENTS_TOOLING_PATH = " + path, build_block(lane._replace(agents_path=path)))
        omitted = lane._replace(tooling_omitted=(("AGENTS_TOOLING_PATH", "path_outside_roots"),))
        self.assertIn("AGENTS_TOOLING_PATH: omitted (path_outside_roots)", build_block(omitted))
        self.assertNotIn("AGENTS_TOOLING_PATH = ", build_block(omitted))
        self.assertEqual(self.section(omitted._replace(facts=PI_FACTS), "TOOLS"),
                         ["TOOLS", NO_SHELL_LINE])

    def test_empty_and_relative_path_entries_find_nothing_in_cwd(self):
        cwd = self.root / "work"
        cwd.mkdir()
        sub = make_bin(cwd, ("rg", "codebase-memory-mcp"))
        for name in ("rg", "codebase-memory-mcp"):
            (cwd / name).write_text("#!/bin/sh\nexit 0\n")
            (cwd / name).chmod(0o755)
        lane = self.lane._replace(facts=PI_FACTS._replace(shell=fact("yes")), cwd=str(cwd))
        for env in ({"HOME": str(self.root)}, {"PATH": ""}, {"PATH": os.pathsep},
                    {"PATH": str(self.bin) + os.pathsep}, {"PATH": os.pathsep + str(self.bin)},
                    {"PATH": "bin"}, {"PATH": "."}):
            with self.subTest(env=env):
                current = lane._replace(child_env=env)
                self.assertEqual(self.section(current, "TOOLS"), ["TOOLS", NO_TOOL_LINE])
                self.assertEqual(self.section(current, "CODE INDEX"),
                                 ["CODE INDEX", NO_INDEX_LINE])
                path = child_path(env.get("PATH") or "", str(cwd))
                self.assertEqual(mcp_pick({"skills": [], "mcp": "unknown"}, path), [])
        self.assertEqual(child_path(str(self.bin) + os.pathsep + "bin" + os.pathsep + str(sub),
                                    str(cwd)), str(self.bin) + os.pathsep + str(sub))

    def test_pi_review_has_no_shell_tool(self):
        self.add_tool("rg")
        self.add_tool("codebase-memory-mcp")
        block = build_block(self.lane._replace(runtime="pi"))
        for prefix in ("TOOL_AVAILABILITY", "SHARED_TOOLING_PATH", "AGENTS_TOOLING_PATH"):
            self.assertFalse(any(line.startswith(prefix) for line in block.splitlines()))
        self.assertTrue({"rg", "bash"}.isdisjoint(re.findall(r"[A-Za-z0-9_-]+", block)))
        self.assertNotIn("codebase-memory-mcp cli", block)

    def test_unknown_facts_block(self):
        self.add_tool("codebase-memory-mcp")
        lane = self.lane._replace(runtime="placeholder-cli-1",
                                  facts=unknown_facts(NO_PREVIEW_REASON))
        access = self.section(lane, "ACCESS")
        for name in ("write", "shell", "skills", "mcp"):
            self.assertIn(f"{name}: {UNKNOWN_TEXT} [unknown: {NO_PREVIEW_REASON}]", access)
        self.assertEqual(self.section(lane, "SETTINGS"), ["SETTINGS", UNKNOWN_TEXT])
        self.assertEqual(self.section(lane, "CODE INDEX"),
                         ["CODE INDEX", SHELL_IF + _code_index_line(False, "placeholder-cli-1")])

    def test_soft_confinement_from_write(self):
        for role in ("execute", "review"):
            for value in ("full", "unknown", "workspace", "none"):
                lane = self.lane._replace(role=role, soft_confinement="fake confinement sentence",
                                          facts=PI_FACTS._replace(write=fact(value)))
                self.assertEqual("fake confinement sentence" in self.section(lane, "ACCESS"),
                                 role == "execute" and value in ("full", "unknown"))
        self.assertNotIn("fake confinement sentence", build_block(self.lane))
        self.add_tool("codebase-memory-mcp")
        self.config(self.root / ".claude.json")
        facts = PI_FACTS._replace(mcp=fact("call_file"), mcp_settings=(
            {"name": "fake-other", "state": "applied", "reason": None},))
        self.assertEqual(self.section(self.lane._replace(facts=facts), "CODE INDEX"),
                         ["CODE INDEX", NO_INDEX_LINE])

    def test_native_lane_lens_lines_only(self):
        lane = self.lane._replace(facts=None, lens_report=[
            {"name": "lens-a", "path": "/fake/skills/lens-a", "note": None}])
        self.assertEqual(build_block(lane), "SKILLS\nlens-a: load the skill lens-a by name "
                         "if your host provides it (unverified)")
        self.assertEqual(build_block(lane._replace(lens_report=[])), "")

    def test_skills_section_forms(self):
        settings = tuple({"name": name, "state": state, "reason": None, "form": form}
                         for name, state, form in (("lens-a", "applied", "prose"),
                                                   ("lens-b", "ignored", None),
                                                   ("edit-a", "unknown", "prose"),
                                                   ("lens-d", "applied", "path")))
        facts = PI_FACTS._replace(skill_settings=settings, skill_blocks=(
            {"name": "lens-a", "bytes": 120, "sha256": "a" * 64},))
        rows = [{"name": name, "path": "/fake/skills/" + name, "note": note}
                for name, note in (("lens-a", None), ("lens-b", None), ("edit-a", None),
                                   ("Lens_D", None), ("ui-a", "over_window"), ("other-a", None))]
        rows[3]["skill_name"] = "lens-d"
        lane = self.lane._replace(facts=facts, lens_report=rows)
        self.assertEqual(self.section(lane, "SKILLS"), [
            "SKILLS", "lens-a: inlined in this prompt between <skill> delimiters "
            "(path /fake/skills/lens-a, sha256 " + "a" * 64 + ", 120 bytes)",
            "lens-b: skipped (host_cannot_load)", "edit-a: skipped (host_cannot_load)",
            "Lens_D: delivered by path, loaded by your host from /fake/skills/Lens_D",
            "other-a: " + UNKNOWN_TEXT, "ui-a: skipped (over_window)"])
        self.assertNotIn("SKILLS", build_block(lane._replace(lens_report=[])).splitlines())

    def test_block_matrix(self):
        self.add_tool("rg")
        self.add_tool("codebase-memory-mcp")
        fixture = pathlib.Path(__file__).parent / "fixtures" / "runner_capabilities.json"
        for entry in json.loads(fixture.read_text())["lanes"]:
            with self.subTest(runtime=entry["runtime"], mode=entry["mode"], extra=entry["extra"]):
                caps = entry["capabilities"]
                facts = LaneFacts(*(fact(caps[k] if isinstance(caps[k], str) else caps[k]["value"],
                                          "fixture") for k in ("write", "shell", "skills", "mcp")),
                                  prompt=caps["prompt"])
                lane = self.lane._replace(facts=facts, runtime=entry["runtime"],
                                          role="review" if entry["mode"] == "review" else "execute")
                access = self.section(lane, "ACCESS")
                for key in ("write", "shell", "skills", "mcp"):
                    line = next(line for line in access if line.startswith(key + ":"))
                    self.assertEqual(UNKNOWN_TEXT in line, caps[key] == "unknown")
                if caps["shell"] == "no":
                    self.assertEqual(self.section(lane, "TOOLS"), ["TOOLS", NO_SHELL_LINE])
                    self.assertNotIn("codebase-memory-mcp cli", build_block(lane))
                else:
                    self.assertIn("If you have a shell, these tools are on its PATH:",
                                  build_block(lane))
                self.assertLessEqual(sum("codebase-memory-mcp" in line for line in
                                         self.section(lane, "CODE INDEX")), 1)

    def test_present_not_enabled_line(self):
        rows = [{"name": "fake-index", "role": "code_index"},
                {"name": "fake-other", "role": "unsorted"}]
        lane = self.lane._replace(table_host={"skills": [], "mcp": rows})
        self.assertIn("MCP server fake-index: present in the host config, "
                      "not enabled for this call", self.section(lane, "CODE INDEX"))
        self.assertNotIn("fake-other", build_block(lane))
        self.assertNotIn("MCP server", build_block(lane._replace(table_host={"mcp": "unknown"})))
        rows[0]["name"] = "codebase-memory-mcp"
        self.assertNotIn("codebase-memory-mcp", build_block(lane))
        rows[0]["name"] = "fake-index\nx"
        self.assertIn("fake-index\\u000ax", build_block(lane))

    def test_section_order(self):
        notes = ("documents from other worktrees: 1 (/fake/wt-2)",
                 "guidance omitted: AGENTS_TOOLING_PATH (path_outside_roots)")
        lane = self.lane._replace(facts=PI_FACTS._replace(shell=fact("yes")), notes=notes,
                                  lens_report=[{"name": "lens-a", "path": "/fake/skills/lens-a",
                                                "note": None}])
        lines = build_block(lane).splitlines()
        indexes = [lines.index(header) for header in SECTIONS]
        self.assertEqual(indexes, sorted(indexes))
        self.assertEqual(self.section(lane, "LANE")[-2:], ["note: " + n for n in notes])
        self.assertIn("note: fake\\u000aline", build_block(lane._replace(notes=("fake\nline",))))

    def test_two_lanes_independent(self):
        first = self.lane
        self.add_tool("rg")
        second = first._replace(facts=unknown_facts(NO_PREVIEW_REASON), child_env={})
        expected = [build_block(first), build_block(second)]
        self.assertEqual([build_block(second), build_block(first)], expected[::-1])
