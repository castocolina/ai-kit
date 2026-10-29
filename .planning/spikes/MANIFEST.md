# Spike Manifest

## Ideas

### session-self-resume
Phase 26 (QTA-04): an orchestrating session that runs out of its own quota resumes itself through
a wake that survives the stall. The spike answers SPEC R2's questions before planning.

**Requirements:**
- Resume by session id, never `--continue` / "most recent" (26-SPEC).
- Never edit a CLI config; throwaway sessions and the cheapest lane only; quote messages, never a token.
- A wake checks the original process is gone before it resumes (spike 002).

## Spikes

| # | Idea | Name | Type | Validates | Verdict | Tags |
|---|------|------|------|-----------|---------|------|
| 001 | session-self-resume | claude-timer-resume | standard | a transient systemd user timer re-enters a claude session by id | VALIDATED | claude-code, systemd, resume |
| 002 | session-self-resume | claude-resume-while-alive | standard | a concurrent resume while the original lives | VALIDATED (hazard) | claude-code, concurrency |
| 003 | session-self-resume | pi-opencode-timer-resume | standard | pi and opencode re-entry from a timer | VALIDATED | pi, opencode, systemd |
| 004 | session-self-resume | cron-and-limit-evidence | standard | CronCreate and /goal across a usage limit | VALIDATED | claude-code, cronCreate, usage-limit |
