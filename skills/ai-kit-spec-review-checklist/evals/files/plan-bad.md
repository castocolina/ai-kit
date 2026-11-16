# Add `--draft` flag to commit-message Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Add `--draft` flag.

**Architecture:** Extend skill.

**Tech Stack:** Bash, Claude Code skills.

---

### Task 1: Argument parser

**Files:**
- Modify: TBD

- [ ] **Step 1: Parse arguments**

Implement appropriate argument parsing in the skill. Handle errors appropriately.

- [ ] **Step 2: Test it**

Write tests for the above.

- [ ] **Step 3: Commit**

Commit the changes with a good message.

### Task 2: Output sink

**Files:**
- Modify: the relevant file

- [ ] **Step 1: Add the draft branch**

Add a branch that handles the `--draft` case. The exact behavior is similar to Task 1 — see how that one works.

- [ ] **Step 2: Validate**

Validate the implementation.

### Task 3: Integration

- [ ] **Step 1: Wire it up**

Connect the draft path to the `OutputSink` interface defined earlier.

- [ ] **Step 2: Done**

Done.
