DIGEST f0c43a5da52a587d
Pre-change baseline (clean-context native Opus subagent), skill at 0e17b22.
Pattern: Process. D1 17/20, D2 13/15, D3 14/15, D4 14/15, D5 13/15, D6 14/15, D7 8/10, D8 12/15.
Critical: none.
Important: SKILL.md lines 276-277 with 99-101 — "never resolve a needs_choice yourself, whatever the user says" does not say whether a user-stated rule (e.g. "take the first candidate; turn off anything with no candidate") counts as the user's choice, while the bundled evals/04-just-apply-it.md expects the agent to apply exactly that rule and report the chosen review pass.
Minor: line 17 undercounts non-config writes (marker, backup, runner snapshot, cross-ai.mjs.new); lines 60-63 give no signal for "last written by v1"; the dry-run rule stated three times (136-146, 276-279, 304); runner git_timeout/git_error text sits under config failure states (183-189); line 212 AIKIT-XAI rule has no trigger; lines 241-242 GSD_PATH_JEV values unstated; Limits table points to internal planning docs (254, 257); line 269 repeats runner.md 38-46; line 270 understates required flags; ".new is not active" and "never run v1 on a v2 config" repeated.
CURRENT 105/120
CRITICAL 0
IMPORTANT 1
