"""Live tool-presence detection (D-07): never assume, always verify.

Adapts `tools/hooks/detect.py`'s `shutil.which(name, path=search_path)`
resolution pattern locally (no `tools/`<->`skills/` cross-import). Every
binary is resolved through the `path=` parameter, never by mutating
`os.environ`, so tests stay hermetic on a scratch PATH.
"""

from __future__ import annotations

import os
import shutil

MODERN_CLI_TOOLS = ("rg", "bat", "sd", "fd", "eza")


def check_tool_presence(
    search_path: str | None = None, repo_root: str | None = None
) -> dict[str, bool]:
    """Return a `dict[str, bool]` keyed by `rules.py`'s condition names.

    Also includes one `f"modern-cli:{tool}"` key per `MODERN_CLI_TOOLS`
    entry, individually live-verified -- so R06 never has to collapse five
    tools' presence into one aggregate boolean.
    """
    root = repo_root or "."
    per_tool = {
        f"modern-cli:{name}": shutil.which(name, path=search_path) is not None
        for name in MODERN_CLI_TOOLS
    }
    result: dict[str, bool] = {
        "rtk": shutil.which("rtk", path=search_path) is not None,
        "modern-cli": any(per_tool.values()),
        "codegraph": os.path.isdir(os.path.join(root, ".codegraph")),
        "graphify": (
            shutil.which("graphify", path=search_path) is not None
            or os.path.isdir(os.path.join(root, "graphify-out"))
        ),
        "gsd": os.path.isdir(os.path.join(root, ".planning")),
    }
    result.update(per_tool)
    return result
