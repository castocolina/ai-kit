Native Opus (clean context), ai-kit-gsd-curated-config, 2026-10-24 r3. 104/120. D1 17 D2 13 D3 14 D4 14 D5 12 D6 14 D7 8 D8 12.
I1: the skip check and printed fix handle only skills/<name> and global: refs; SKILL.md:262-267 claims every reference. _kept_skip (plan_io.py:678-684) returns None for other kept project paths (../outside/x never refused, gsd-core skips it); _kept_names (729) reduces .claude/skills/house-rules to a bare name, which apply then refuses as not installed. Fix: _kept_project_ref_skip_reason handles any project-relative path (containment + SKILL.md); _kept_names reduces only global:<name> and skills/<name>, names other paths for an explicit decision; tests for each.
Minors: _project_root_of realpaths the config path before walking to .planning (symlinked .planning -> None -> every kept skills/<name> refused); the live check is skipped when no host skills dir is recorded and for op:set entries (SKILL.md:268-270 should say kept entries only, or check set refs live at apply); NEVER line 320-323 --force wording; SKILL.md:255-265 convoluted (three bullets); move Skills detail to references/skills.md.
DIGEST 9ae11c2977b8de1d
CURRENT 104/120
CRITICAL 0 IMPORTANT 1
