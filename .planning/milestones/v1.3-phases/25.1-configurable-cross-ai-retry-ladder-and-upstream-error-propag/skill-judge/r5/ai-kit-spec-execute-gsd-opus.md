Judge: opus
Reviewed-sha256: bd7a28b0f98eae983d4f0c7252cb0ccd9c2227ca791501964979fbd630fcc088
Lane: native subagent completed
Score: 105
Critical: 0
Important: 0

## Skill evaluation: ai-kit-spec-execute-gsd

**Total:** 105/120, Grade B. **Pattern:** Process with low-freedom Tool blocks. **E:A:R** about 75:17:8.

The Phase 25.1 changes are described correctly:
- Step 3 points to `../ai-kit-cross-ai/SKILL.md` sections 4 and 6-8 as a MANDATORY read, and STOPs if that skill is missing.
- Only an exit 75 that carries `retry_after_s=` gets a one-shot wake on the same lane, CLI and model. A bare 75, 69 (including `stopped=hard-waits` and `stopped=cap`), 1, 2, 124 and 127 get `abort`.
- `skip` is never answered, and "never switch harness, provider or model" is stated twice (SKILL.md:44-45, 459).
- The redacted upstream lines are relayed from GSD's `$ERROR_LOG`. I checked that against gsd-core `execute-phase/detail/elaboration.md:99`.
- The new `unsupported_model_id` reason matches `adapter.py:238-242` and `runner_dispatch.model_id_ok`.
- The copilot exec note matches `COPILOT_EXEC_NOTE`.
- No stale pointer to `ai-kit-spec-review/references/subprocess-quota-policy.md` is left.

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Dense project-specific contract (hook globbing, ownership-aware cleanup, wake branches); some rationale repeated |
| D2 Mindset + Procedures | 13 | 15 | Good domain procedures; the mindset block is down to two bullets |
| D3 Anti-Patterns | 14 | 15 | Specific NEVER list with non-obvious reasons (skip = native fallback, re-running Step 1 rewrites the hook) |
| D4 Spec / Description | 14 | 15 | Clear WHAT and WHEN in 835 chars; no stop/retry keywords, but ai-kit-cross-ai owns those |
| D5 Progressive Disclosure | 12 | 15 | 487 lines, close to the limit; about 35 inline Python lines in Step 3; reference triggers are good ("read only if", MANDATORY at the stop) |
| D6 Freedom Calibration | 14 | 15 | Low freedom where config writes and hooks are fragile |
| D7 Pattern | 8 | 10 | Clear Process pattern, heavier than ideal |
| D8 Usability | 13 | 15 | Thorough exit and error handling; a few edge-case gaps below |

### Findings

1. **Minor:** The stop rules miss two GSD failure cases. SKILL.md:457-458 lists only runner exit codes. GSD also shows retry/skip/abort on exit 0 with a summary it rejects (elaboration.md:113-120), and on 128+n (a signal). **Fix:** add "an exit 0 whose summary GSD rejected, and 128+n" to the `abort` list.
2. **Minor:** "State file" means two different files. SKILL.md:157-158 says "after a hard-tier stop, first deleting the state file the runner named", inside the paragraph about the resumable state file (`gsd-resume-*.json`). SKILL.md:479-481 repeats this and leaves out the stale-record exit from cross-ai section 6. **Fix:** say "the runner's cycle state file (`…/ai-kit/spec/cycles/…`, named in its `lane stopped=` line), never `RESUME_STATE_PATH`", and add "or the record goes stale (4 h cap)".
3. **Minor:** The NEVER bullet at SKILL.md:26-28 says "the one-shot wake waits that delay" for any exit 75 with `retry_after_s=`. Under 60 s, or with no scheduler, cross-ai section 6 schedules nothing and the owner answers. **Fix:** append "(none under 60 s or without a scheduler: Step 3's print path)".
4. **Minor:** SKILL.md:455 says "(transient ladder exhausted or confirmed-router quota)". The policy calls it the soft series, and a deadline-cut series also gets `retry_after_s=` (subprocess-quota-policy.md:49-50, 97). **Fix:** "(soft series spent or cut by the deadline, transient or confirmed-router quota)".
5. **Minor:** The cleanup rationale appears three times (SKILL.md:192-194, 196-199, 333-337), and SKILL.md:183 is one unwrapped line of about 400 chars. **Fix:** keep the rationale only at the cleanup block and wrap line 183.
6. **Minor:** Step 3's inline marker-guard Python (SKILL.md:383-405) inflates the body. **Fix:** move it into a shim subcommand (`append-tooling-guidance`) or `scripts/` and keep the exit-code table in SKILL.md.

I did not run the skill or `make test`, and I did not check that the installer ships `ai-kit-cross-ai` as a sibling directory. If it does not, Step 3's MANDATORY read hits its STOP path.

DIGEST bd7a28b0f98eae98
CURRENT 105/120
CRITICAL 0 IMPORTANT 0
