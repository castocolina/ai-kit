# Line Parser Implementation Plan

> Synthetic plan for an eval. It is not a real project plan.

**Goal:** Parse key=value lines from the sample config format.

## Tasks

### Task 1: Add the line parser

**Files:**
- Create: `src/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write the failing test for a valid line**
- [ ] **Step 2: Implement parse_line**

### Task 2: Reject malformed lines

**Files:**
- Modify: `src/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Add the missing-separator case**
- [ ] **Step 2: Raise ValueError for a line without a separator**
