---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 16
executor: cross-ai (pi router-env/my-coding; three runs timed out before committing, orchestrator committed)
requirements-completed: [STL-05]
orchestrator_verify: "VERIFY 23-16: 3/3 passed"
---

# 23-16 Summary: host-keyed wizard seam, Cursor HostView, per-host commit

- Task 1 and Task 2 (5777656): final-form `HostView` seam including zero-host and Cursor-only
  contexts; Cursor defaults through lazy host config, per-host segment inventory and providers,
  a sample Cursor payload fixture and the synthetic-cache preview. pylint findings fixed by
  refactoring (no disables).
- Task 3 (this plan's last commit): per-host commit with independent outcomes; a declined host's
  files stay byte-identical; TOML save validation is offline (structural check plus a
  synthetic-quota dry render), with tests asserting no fetch and no detached spawn; a failed
  publication leaves no partial file; `write_toml_preserving` validates for the named host.
- Verification: tests.test_setup, tests.test_arch, tests.test_wizard_app, tests.test_wizard_pty
  4/4; pyright 0 errors; pylint 10.00; the plan's three verify blocks pass.
- Execution note: three cross-AI runs hit the 3600 s deadline without committing; the
  orchestrator verified the working tree each time and committed the finished tasks.
