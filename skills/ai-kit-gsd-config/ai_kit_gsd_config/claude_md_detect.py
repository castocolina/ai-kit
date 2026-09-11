"""Instruction-file path detection (07-CONTEXT.md D-06). `detect_claude_md_path` is a pure,
dependency-injected function -- it never fabricates a default when none of the four candidate
filenames exist in the target repo, matching `gsd_catalog.py`'s own `isfile_fn=os.path.isfile`
DI convention so this module's priority-order logic is testable against a fake filesystem with
zero real I/O.
"""
import os

# IN THIS EXACT ORDER -- AGENTS.md family preferred over CLAUDE.md family for multi-CLI
# projects (D-06). The first filename that exists under `project_dir` wins; never a tie-break,
# never a fabricated default when none exist.
_CANDIDATE_FILENAMES = ("AGENTS.md", "CLAUDE.local.md", "AGENTS.local.md", "CLAUDE.md")


def detect_claude_md_path(project_dir, isfile_fn=os.path.isfile):
    """Checks `_CANDIDATE_FILENAMES` in priority order directly under `project_dir`. Returns the
    first hit as a `"./<name>"`-prefixed relative string -- matching ai-kit's own config.json's
    existing `"./CLAUDE.md"` literal convention -- or `None` when none of the four exist. Never
    raises."""
    for filename in _CANDIDATE_FILENAMES:
        candidate = os.path.join(project_dir, filename)
        if isfile_fn(candidate):
            return f"./{filename}"
    return None
