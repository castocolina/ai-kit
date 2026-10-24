#!/usr/bin/env python3
"""Cursor CLI status-line entry point."""
# pyright: strict
# pylint: disable=invalid-name  # installed script name is hyphenated

import common_render
import cursor_host

if __name__ == "__main__":
    common_render.main(cursor_host.HOST)
