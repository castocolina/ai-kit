# Export dry-run implementation plan

> For agentic workers: REQUIRED SUB-SKILL: use superpowers:subagent-driven-development to run this plan task by task.

**Goal:** Add a `--dry-run` flag to the export command.

### Task 1: Parse the flag

**Files:**
- Modify: `src/export.py`

- [ ] Add `--dry-run` to the argument parser.

### Task 2: Skip the write in dry-run mode

**Files:**
- Modify: `src/export.py`

- [ ] Return before the file write when `--dry-run` is set.
