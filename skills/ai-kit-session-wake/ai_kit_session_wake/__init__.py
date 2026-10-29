"""ai-kit session wake (D-01): a systemd user timer that resumes one exact
host session id after its process dies.

Importing this package puts the sibling ``skills/ai-kit-spec-review`` skill on
``sys.path`` (resolved from this file's realpath, so a copy-installed skill
still finds the sibling beside it), so the shim, the hook (26-07) and the tests
all import ``ai_kit_spec.detection`` the same way. Fails closed with an
ImportError naming the path it looked at when the sibling is missing.
"""
import os
import sys

_SIBLING = os.path.realpath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "..", "..", "ai-kit-spec-review"
    )
)

if not os.path.isdir(_SIBLING):
    raise ImportError(
        f"ai-kit-session-wake: the ai-kit-spec-review sibling skill is missing beside {_SIBLING}"
    )
if _SIBLING not in sys.path:
    sys.path.insert(0, _SIBLING)
