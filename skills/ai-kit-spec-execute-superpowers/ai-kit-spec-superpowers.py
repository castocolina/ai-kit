#!/usr/bin/env python3
"""Shim: `python3 ai-kit-spec-superpowers.py <subcommand> ...` from any cwd, adding this file's
own directory to sys.path first (Python only auto-adds it for `python3 <path>.py`, but this shim
must also add Plan 1's ai-kit-spec-review package root, which lives one level up under a sibling
skill directory -- neither is on the default path when invoked via an absolute path from a
different cwd)."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "ai-kit-spec-review"))

from ai_kit_spec_superpowers.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
