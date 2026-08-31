#!/usr/bin/env python3
"""Entrypoint shim for ai-kit-spec-execute-gsd -- mirrors skills/ai-kit-spec-review/ai-kit-spec.py's
own trick (Python puts a directly-run script's OWN directory on sys.path[0] automatically, making
ai_kit_spec_gsd importable regardless of the caller's cwd), PLUS explicitly inserts the SIBLING
skills/ai-kit-spec-review/ directory onto sys.path so ai_kit_spec_gsd's own `from ai_kit_spec...`
imports resolve too. This is the ONLY thing SKILL.md ever invokes by absolute path (Task 5).

Usage: python3 <this file> resolve-dispatch ...   -> ai_kit_spec_gsd.cli.main
       python3 <this file> config-path ...         -> ai_kit_spec_gsd.cli.main
       (every ai_kit_spec_gsd.cli subcommand -- there is no separate wrapper subcommand)"""
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, "..", "ai-kit-spec-review"))

from ai_kit_spec_gsd.cli import main  # noqa: E402 -- import must follow the sys.path insert above

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
