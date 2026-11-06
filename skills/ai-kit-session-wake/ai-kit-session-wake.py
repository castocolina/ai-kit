#!/usr/bin/env python3
"""Entrypoint shim for ai-kit-session-wake (D-01).

Mirrors the GSD execute flow's trick (running a
script directly puts its OWN directory on sys.path[0], making
ai_kit_session_wake importable regardless of the caller's cwd) and inserts the
SIBLING skills/ai-kit-spec-review/ directory on sys.path so the package's
`ai_kit_spec.detection` imports resolve. The sibling is resolved from
`os.path.realpath(__file__)`, because pi links the skill alone into its own
skills dir (26-10); a plain relative path would break there.

Usage: python3 <this file> arm|disarm|fire|done ...   -> ai_kit_session_wake.cli.main
"""
import importlib
import os
import sys

_THIS_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, "..", "ai-kit-spec-review"))

try:
    main = importlib.import_module("ai_kit_session_wake.cli").main
except ImportError:
    sys.stderr.write(
        "ai-kit-session-wake: the ai-kit-spec-review sibling skill is missing beside "
        f"{os.path.dirname(_THIS_DIR)}\n"
    )
    sys.exit(2)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
