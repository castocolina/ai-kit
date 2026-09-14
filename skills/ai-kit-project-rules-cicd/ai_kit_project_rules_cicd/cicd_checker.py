"""This skill's aggregator (REQ-rules-cicd), plan 14-01's tracer subject.

Scope boundary: this skill checks whether CI config reuses commands the
repo already defines, never runs a CI job or any command it reads, never
edits the target repo, and evaluates root-level CI config only.

`check_cicd_rules(repo_root)` evaluates D-C1's applicability gate FIRST
and returns an empty list immediately when it does not hold. Otherwise it
builds the reuse inventory ONCE and discovers the CI files ONCE, then for
every command site of every CI file, for every segment of every command
line, classifies it: a reuse invocation is skipped; a direct invocation
with no matching reuse source is skipped; a direct invocation whose key
matches a usable reuse source produces one finding carrying D-C12's exact
field set, in D-C13's order.

Structured so plans 14-02 and 14-03 extend this by APPENDING a CI-file
source and a reuse-source surface inside the applicable branch, never by
adding a check ahead of the gate.
"""

from __future__ import annotations

import os

from ai_kit_rules_common.command_text import (
    has_heredoc,
    split_top_level_segments,
    strip_leading_noise,
    truncate_at_unquoted_pipe,
)
from ai_kit_rules_common.criticality import CRITICALITY_MEDIUM

from . import ci_parse, reuse_sources

_CATEGORY = "cicd-command-reuse"
_ISSUE = "ci_duplicates_existing_command"


def _build_finding(ci_file: str, job: str, command: str, tool_key: str, source: dict) -> dict:
    recommendation = (
        f"CI job '{job}' in {ci_file} runs '{command}' directly, duplicating "
        f"the existing '{source['reuse_command']}' command -- call "
        f"'{source['reuse_command']}' instead of running '{command}' directly."
    )
    return {
        "category": _CATEGORY,
        "issue": _ISSUE,
        "criticality": CRITICALITY_MEDIUM,
        "summary": recommendation,
        "recommendation": recommendation,
        "needs_research": False,
        "ci_file": ci_file,
        "job": job,
        "command": command,
        "tool": tool_key,
        "reuse_surface": source["surface"],
        "reuse_command": source["reuse_command"],
    }


def _find_matching_source(key: str, by_key: dict[str, dict]) -> dict | None:
    """Exact key lookup first (O(1), always preferred over a widened
    match); otherwise a linear scan applying D-C5's widening rule."""
    if key in by_key:
        return by_key[key]
    for candidate_key, record in by_key.items():
        if reuse_sources.keys_match(key, candidate_key):
            return record
    return None


def check_cicd_rules(repo_root: str) -> list[dict]:
    """Return a flat list of findings for `repo_root`, in D-C13's
    deterministic order: CI files in discovery order, then command sites
    in file-declaration order, then segments in line order. Never
    raises."""
    if not ci_parse.repo_has_ci_config(repo_root):
        return []

    inventory = reuse_sources.build_reuse_inventory(repo_root)
    by_key: dict[str, dict] = {}
    for record in inventory:
        by_key.setdefault(record["key"], record)

    findings: list[dict] = []
    for ci_file in ci_parse.discover_ci_files(repo_root):
        abs_path = os.path.join(repo_root, ci_file)
        text = ci_parse.read_ci_text(abs_path)
        for site_name, command_lines in ci_parse.iter_command_sites(text):
            for command_line in command_lines:
                if has_heredoc(command_line):
                    continue
                for raw_segment in split_top_level_segments(command_line):
                    segment = truncate_at_unquoted_pipe(raw_segment)
                    # `stop_check` lets a reuse-invocation shape this
                    # skill recognizes (e.g. `pre-commit run <id>`) halt
                    # stripping the moment it appears -- otherwise the
                    # generic `<runner> run <rest>` rule below would
                    # consume "pre-commit run " as if it were a runner
                    # wrapper before the table ever saw it intact.
                    stripped = strip_leading_noise(
                        segment,
                        stop_check=lambda s: reuse_sources.classify_reuse_invocation(s)
                        is not None,
                    )
                    if not stripped.strip():
                        continue
                    if reuse_sources.classify_reuse_invocation(stripped) is not None:
                        continue
                    key, _known = reuse_sources.compute_command_key(stripped)
                    if not key:
                        continue
                    source = _find_matching_source(key, by_key)
                    if source is None:
                        continue
                    findings.append(
                        _build_finding(ci_file, site_name, raw_segment.strip(), key, source)
                    )
    return findings


__all__ = ["check_cicd_rules"]
