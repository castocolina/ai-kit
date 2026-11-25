# Status line label plan

### Task 1: Rename the status line label

**Files:**
- Modify: `src/statusline/label.py`

- [ ] Rename the label constant and update its callers

Shell rules for every executor:
- One simple command per shell call: a single program with plain arguments and absolute paths.
- Never use heredocs, command substitution, subshells, process substitution or `eval`.
- Never use `sed -i` or another in-place editor on a file; use the file-edit tool.
- Never delete outside `tmp/`, and never use `rm -rf` on a variable path.
- Do not force push, and never run `git reset --hard` without the owner.
- English only. Never print or write a secret, never print a process environment, and do not copy real credentials.
- No secrets and no machine paths in fixtures; you must not change file permissions.

Scratch work cleans up after itself:

    WORK="$(mktemp -d)"
    trap 'rm -rf "$WORK"' EXIT
    rm -rf "$TMPDIR/label-scratch"
    rm -rf tmp/label-run
