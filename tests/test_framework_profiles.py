#!/usr/bin/env python3
"""Validate framework profile frontmatter, especially revise_protocol shape."""
import fnmatch
import glob
import os
import re
import unittest

import yaml

_HERE = os.path.dirname(__file__)
_FRAMEWORKS_DIR = os.path.join(
    _HERE, "..", "skills", "reviewing-specs", "references", "frameworks"
)

_REQUIRED_FIELDS = ["id", "display_name", "doc_types", "lifecycle_order"]
_VALID_INVOKE = re.compile(r"^(skill:\S+|slash_command|surface)$")
_VALID_VALIDATE = re.compile(r"^agent:\S+$")
_ARCHETYPES = {"intent", "requirements", "design", "plan", "state", "constitution"}


def _profiles():
    """Yield (path, frontmatter_dict) for every profile file (not SCHEMA.md)."""
    for path in sorted(glob.glob(os.path.join(_FRAMEWORKS_DIR, "*.md"))):
        if os.path.basename(path) == "SCHEMA.md":
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read().replace("\r\n", "\n")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        assert m, f"{path}: no YAML frontmatter block"
        yield path, yaml.safe_load(m.group(1))


def _check_route(path, route):
    assert isinstance(route, dict), f"{path}: route is not a mapping: {route!r}"
    assert route.get("archetype") in _ARCHETYPES, \
        f"{path}: route archetype invalid: {route.get('archetype')!r}"
    invoke = str(route.get("invoke", ""))
    assert _VALID_INVOKE.match(invoke), f"{path}: route invoke invalid: {invoke!r}"
    if invoke == "slash_command":
        assert route.get("command"), f"{path}: slash_command route needs a 'command'"
    if route.get("validate") is not None:
        assert _VALID_VALIDATE.match(str(route["validate"])), \
            f"{path}: validate must be 'agent:<name>', got {route['validate']!r}"


class TestFrameworkProfiles(unittest.TestCase):
    def test_required_fields_present(self):
        for path, fm in _profiles():
            for field in _REQUIRED_FIELDS:
                self.assertIn(field, fm, f"{path}: missing required field {field!r}")

    def test_revise_protocol_shape(self):
        for path, fm in _profiles():
            rp = fm.get("revise_protocol")
            if rp is None:
                continue
            self.assertIn(rp.get("mode"), ("direct_edit", "native_command"),
                          f"{path}: revise_protocol.mode invalid: {rp.get('mode')!r}")
            if "routes" in rp:
                self.assertIsInstance(rp["routes"], list, f"{path}: routes must be a list")
                self.assertTrue(rp["routes"], f"{path}: routes must be non-empty")
                for route in rp["routes"]:
                    _check_route(path, route)
            else:
                invoke = str(rp.get("invoke", ""))
                self.assertTrue(_VALID_INVOKE.match(invoke),
                                f"{path}: flat invoke invalid: {invoke!r}")
                self.assertIsInstance(rp.get("applies_to", []), list,
                                      f"{path}: applies_to must be a list")

    def test_superpowers_routes(self):
        profiles = {fm["id"]: fm for _, fm in _profiles()}
        sp = profiles["superpowers"]["revise_protocol"]
        self.assertEqual(sp["mode"], "native_command")
        by_arch = {r["archetype"]: r for r in sp["routes"]}
        self.assertEqual(by_arch["design"]["invoke"], "skill:superpowers:brainstorming")
        self.assertEqual(by_arch["plan"]["invoke"], "skill:superpowers:writing-plans")

    def test_gsd_route_validates_with_checker(self):
        profiles = {fm["id"]: fm for _, fm in _profiles()}
        gsd = profiles["gsd"]["revise_protocol"]
        self.assertEqual(gsd["mode"], "native_command")
        plan = next(r for r in gsd["routes"] if r["archetype"] == "plan")
        self.assertEqual(plan["invoke"], "slash_command")
        self.assertEqual(plan["command"], "/gsd-plan-phase {phase_id} --reviews")
        self.assertEqual(plan["validate"], "agent:gsd-plan-checker")

    def _gsd_globs_for(self, archetype):
        profiles = {fm["id"]: fm for _, fm in _profiles()}
        return [d["glob"] for d in profiles["gsd"]["doc_types"]
                if d["archetype"] == archetype]

    def _any_glob_matches(self, globs, filename):
        # Match on basename (case-sensitive, like a POSIX filesystem) so a
        # lowercase `plan*.md` glob does NOT match an uppercase `PLAN.md` file.
        return any(fnmatch.fnmatchcase(filename, os.path.basename(g)) for g in globs)

    def test_gsd_plan_glob_matches_real_filenames(self):
        # Real GSD plans are uppercase: `.planning/phases/NN-name/NN-MM-PLAN.md`
        # and `.planning/quick/<id>/PLAN.md`. The old lowercase `plan*.md` glob
        # silently missed them on a case-sensitive filesystem (this is a regression
        # guard for that bug).
        plan_globs = self._gsd_globs_for("plan")
        self.assertTrue(self._any_glob_matches(plan_globs, "05-02-PLAN.md"),
                        f"no gsd plan glob matches a phase plan; globs={plan_globs}")
        self.assertTrue(self._any_glob_matches(plan_globs, "PLAN.md"),
                        f"no gsd plan glob matches a quick plan; globs={plan_globs}")

    def test_gsd_context_and_research_are_classified(self):
        # CONTEXT/RESEARCH must be classified so they can ground a plan review.
        intent_globs = self._gsd_globs_for("intent")
        design_globs = self._gsd_globs_for("design")
        self.assertTrue(self._any_glob_matches(intent_globs, "05-CONTEXT.md"),
                        f"no gsd intent glob matches a phase CONTEXT doc; globs={intent_globs}")
        self.assertTrue(self._any_glob_matches(design_globs, "05-RESEARCH.md"),
                        f"no gsd design glob matches a phase RESEARCH doc; globs={design_globs}")


if __name__ == "__main__":
    unittest.main()
