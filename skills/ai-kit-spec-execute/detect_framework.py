"""Framework detection for ai-kit-spec-execute's router. GSD's marker is confirmed
(.planning/PROJECT.md, per skills/ai-kit-spec-review-checklist/references/frameworks/gsd.md).
superpowers' marker is defined by Plan 3 (ai-kit-spec-execute-superpowers) -- this stub only
wires the GSD branch; Plan 3 fills in the superpowers check in this same function.

Also runnable directly: `python3 detect_framework.py <cwd>` prints the result on stdout."""
import os
import sys


def detect_framework(cwd: str, isfile_fn=os.path.isfile, isdir_fn=os.path.isdir) -> str:
    if isfile_fn(os.path.join(cwd, ".planning", "PROJECT.md")):
        return "gsd"
    return "unknown"


if __name__ == "__main__":
    print(detect_framework(sys.argv[1]))
