"""Compile the error catalog into the runner's patterns block.

The runner's validateRow is the only row schema. This module loads the JSON
file, renders the block and splices it. Paths resolve from this file.
"""

import argparse
import contextlib
import json
import os
import sys
import tempfile

_REFERENCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references")
CATALOG_PATH = os.path.join(_REFERENCES, "cross-ai-errors.json")
TEMPLATE_PATH = os.path.join(_REFERENCES, "cross-ai.mjs")
_START = "// <patterns>\n"
_END = "\n// </patterns>"


def load_rows(path):
    """Return the catalog rows from a JSON array file."""
    with open(path, encoding="utf-8") as handle:
        rows = json.load(handle)
    if not isinstance(rows, list):
        raise ValueError(f"{path} is not a JSON array")
    return rows


def render_block(rows):
    """Return the runner assignment for these rows."""
    return "const PATTERNS = " + json.dumps(rows, indent=2) + ";"


def splice(template_text, block):
    """Replace the text between the patterns markers."""
    start = template_text.find(_START)
    end = template_text.find(_END, start if start >= 0 else 0)
    if start < 0 or end < 0:
        raise ValueError("patterns block missing")
    inner_start = start + len(_START)
    return template_text[:inner_start] + block + template_text[end:]


def _write_template(text):
    directory = os.path.dirname(os.path.abspath(TEMPLATE_PATH))
    mode = os.stat(TEMPLATE_PATH).st_mode & 0o777
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".cross-ai-catalog-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, TEMPLATE_PATH)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def main(argv):
    """Check the rendered block against the template, or rewrite it."""
    parser = argparse.ArgumentParser(prog="ai_kit_spec.cross_ai_catalog")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    rows = load_rows(CATALOG_PATH)
    block = render_block(rows)
    with open(TEMPLATE_PATH, encoding="utf-8") as handle:
        template = handle.read()
    rendered = splice(template, block)
    if args.check:
        if rendered != template:
            print(
                "catalog drift: run python3 -m ai_kit_spec.cross_ai_catalog --write",
                file=sys.stderr,
            )
            return 1
        print(f"catalog ok {len(rows)} rows")
        return 0
    _write_template(rendered)
    print(f"catalog wrote {len(rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
