# 39-05 Summary: the runner's skill flags use the validator's control-character set

Status: complete. Commits 94c3d01 (`feat(39-05): skill-path values checked against the prompt control set`, Task 1) and 75c75c4
(`test(39-05): resolved skill dir and skill-name control set, fixture-pinned`, Task 2). Executed through two cross-AI lanes
(pi router-env/my-coding), one per task, each status=ok on its first run (294 s and 261 s).

## What changed

- `skills/ai-kit-spec-review/references/cross-ai.mjs`: `PROMPT_CONTROL_RE` (Cc, Zl, Zp and the R8 format ranges, U+FEFF) beside the
  unchanged `CONTROL_CHAR_RE`; used by the `--skill-path` parse check (conditional form; `--mcp-config` and `--argv-file` keep the C0/C1
  rule), the `--skill-name` check and both `loadSkills` checks (value and resolved directory); every message text unchanged; both
  constants exported. Template version stays 11.
- `skills/ai-kit-spec-review/references/cross-ai-selftest.mjs`: `PROMPT_CONTROL_FIXTURE` and four logic cases:
  `skillpath-bidi-rejected`, `skillpath-resolved-dir-rejected`, `skillpath-name-control`, `skillpath-pure-control-set` (the 87-member
  set equals 39-03's `tests/fixtures/prompt_control_chars.json`).

## Verification (run by the chunk agent)

- Acceptance greps: `const PROMPT_CONTROL_RE` 1, `CONTROL_CHAR_RE` constant 1, message 1, `PROMPT_CONTROL_RE.test(` 3, old `loadSkills`
  checks 0, `skillpath-` cases 4.
- Self-test: the four new cases plus `skill-prose-claude-stdin`, `skill-prose-copilot-argv`, `pure-skill-forms-verified`,
  `cap-print-argv-table`, `mcp-review-lanes-applied`, `cap-pi-review-line` print `self-test ok`; `--self-test-list` 912 -> 916, the four
  listed as `logic`; `node --check` ok.
- `--print-argv` of 17 calls (the 14 base calls plus pi/claude/copilot review with a clean skill pair) byte-equal to 6679707 (exit,
  stdout, stderr).
- tests.test_runner_skills_argv (14), tests.test_cross_ai_render_sync (11), tests.test_prompt_guard (14),
  tests.test_arch_hardcoded_models (23): pass under a scratch HOME. Lanes: ruff, pyright, vulture, pylint exit 0; hooks 136/136 each.
- detection.py, the model baseline and the live runner copy unchanged.

## Deviations

- None in the code. The Task 2 lane first ran two wrapper calls in parallel, which shared and removed one scratch HOME (ENOENT); both
  passed when re-run one after the other.
- The four new cases are not yet in `tests/fixtures/cross_ai_selftest_secs.json` (39-17 refreshes the times).
