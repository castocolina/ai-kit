Native Opus (clean context), ai-kit-gsd-curated-config, 2026-10-24 r1. 104/120. D1 17 D2 12 D3 14 D4 14 D5 13 D6 14 D7 8 D8 12.
1. Important: plan_io.py:633-636 _kept_names drops every kept item containing ':' (so a fine kept global:ok-skill vanishes from the printed plan-set fix, silently unwiring it); the "re-resolves by name" note is wrong; docstring 629-631 disagrees; test 1149 covers only the plugin form. Fix: reduce global:<name> (one colon) to <name> like skills/<name>; omit only global:<plugin>:<name>; fix the note and docstring; test a valid kept global:a beside a skipped global:b. (Probe: _kept_names(["global:ok-skill","global:bad","skills/proj"],["bad"]) -> (['proj'], ...).)
2. Minor: "No edit or apply keeps a skipped reference" overclaims: _kept_skip (590-598) misses kept global:<plugin>:<name> on non-claude hosts and other project-relative paths. Fix: check them or narrow the wording.
3. Minor: the trusted-root decline rule is written twice (SKILL.md:122-128, 253-258). Fix: keep it in Skills with a one-line pointer.
4. Minor: Skills bullets overloaded (241-263); the "configured roots never dropped without --force" rule is tacked on. Fix: split.
5. Minor: "needs a trusted root configured by hand" does not say how (plan accepts only ~/ roots; NEVER hand-write config.json). Fix: name gsd-settings or gsd-tools config-set agent_skills_security.trusted_global_roots, then re-run inventory and recommend.
DIGEST a7baccdc7bd3a6f1
CURRENT 104/120
CRITICAL 0 IMPORTANT 1
