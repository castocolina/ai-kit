#!/usr/bin/env python3
"""Claude Code status-line entry point."""
# pyright: strict
# pylint: disable=invalid-name  # installed script name is hyphenated

import claude_host
import common_render

if __name__ == "__main__":
    common_render.main(claude_host.HOST)
