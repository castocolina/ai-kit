"""AGENTS.md/CLAUDE.md house-rule checker (provisional package name)."""

import os
import sys

_PKG_DIR = os.path.dirname(os.path.realpath(__file__))
_SKILL_DIR = os.path.dirname(_PKG_DIR)
_SKILLS_ROOT = os.path.dirname(_SKILL_DIR)
_SHARED_DIR = os.path.join(_SKILLS_ROOT, "_shared")

if not os.path.isdir(os.path.join(_SHARED_DIR, "ai_kit_rules_common")):
    raise ImportError(
        f"ai-kit-agents-md-rules-checker requires skills/_shared/"
        f"ai_kit_rules_common to exist beside this skill; looked for it at "
        f"{_SHARED_DIR!r} (resolved from this installed copy's own real "
        f"path) and found nothing there. This directory is only present "
        f"when the skill is reached via the `~/.claude/skills` symlink "
        f"install (`tools/setup.py`) or a direct git checkout of this "
        f"repo -- a copy-install into a different host (e.g. a Claude "
        f"Code plugin root, an opencode skills dir, or ~/.agents) does "
        f"not carry the shared package. Re-run `python3 tools/setup.py` "
        f"or reinstall from a checkout."
    )

if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)
