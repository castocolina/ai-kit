# Phase 18.1: independent skill-judge, round 3

Same rubric (`~/.claude/skills/skill-judge/SKILL.md`, 8 dimensions, 120 points), applied to
SKILL.md plus `references/` at HEAD `c6334ef`. The baseline is still `a8e24c3`, so baseline
scores are carried over from round 1. Fix range reviewed: `baa4f54..c6334ef` (R2 head to now,
which includes `0b9b92c` `probe-quota --no-save-runtimes`).

How I checked (offline): scratch HOME under `./tmp/sj181r3/` (removed afterwards), `--help` for
every subcommand named, and reading the code. Commands run on synthetic input, none of which
spawns an AI CLI:
- `render-toml --out` with stdout captured (was the file it wrote byte-identical to stdout?);
- superpowers `write-resumable-state` with `last_dispatched_key`, and `resume-exclusions`;
- the GSD Step 3 guidance-block script, run three times: a fresh write, a re-run that
  replaces the block, and a file holding the legacy marker (exit 2).

The only argparse change since round 2 is `probe-quota --no-save-runtimes` (present). Neither
`./tmp/judge` nor `pi-r1/` was touched.

---

## 1. ai-kit-spec-review

Lines: SKILL.md 465 (baseline 533); new `references/reviewer-prompts.md` 103.
Baseline 101, current **106**.

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| D1 Knowledge delta | 16 | 16 | unchanged core; Cleanup narrative trimmed |
| D2 Mindset + procedures | 13 | 13 | unchanged |
| D3 Anti-patterns | 13 | 13 | "never review or fix inline without a clean-context tool" added in-line, not in the NEVER list |
| D4 Spec/description | 14 | 14 | unchanged |
| D5 Progressive disclosure | 11 | 13 | Body under 500. Templates moved to a MANDATORY-read reference; `--no-cross-ai` now says which points to skip |
| D6 Freedom calibration | 14 | 14 | unchanged |
| D7 Pattern | 7 | 8 | Closer to Process size |
| D8 Usability | 13 | 15 | Host-neutral delegation with a stated no-tool fallback, `.exit` completion instead of "file stopped growing", fixer named correctly |

Re-verified:
- `dispatch-reviewer --cwd` and the other flags in the snippet exist.
- `.exit` capture is `...; echo "$?" > iter<N>-<key>.exit`, which records dispatch-reviewer's own
  exit code.
- `ai-kit-spec-review-fixer/SKILL.md` exists beside the checklist.
- The exit-code fallback table in `cross-ai-dispatch.md:276-284` (0, 2, 124, 127, other) matches
  `error_classifier._EXIT_FALLBACK`.
- The sibling-first resolution order is the same in the four skills that resolve the shim.

R2 Minor (exit-code fallback rows missing): **resolved**.

Open findings: none.

Verdict: **PASS**.

BASELINE 101/120
CURRENT 106/120
CRITICAL 0
IMPORTANT 0

## 2. ai-kit-spec-config

Lines: SKILL.md 476 (baseline 361); references 335 (baseline 317). Baseline 103, current **106**.

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| D1 | 15 | 15 | unchanged |
| D2 | 12 | 12 | unchanged |
| D3 | 13 | 13 | unchanged |
| D4 | 14 | 14 | unchanged |
| D5 | 14 | 14 | "no profile file (pi)" case added; Do-NOT-load kept |
| D6 | 14 | 15 | mktemp 0700 `$SCRATCH`, no fixed `/tmp` names; `render-toml` exit checked before trust |
| D7 | 8 | 8 | unchanged |
| D8 | 13 | 15 | Host-tool fallback for hosts without a structured ask; `--check-only` really write-free; EXECUTE list screened; ladder read from the written file |

Re-verified:
- `probe-quota --no-save-runtimes` exists, and its help matches the claim.
- `mktemp -d` creates the directory with mode 0700.
- `render-toml --out` writes the file and echoes it on stdout; on a rejected entry it prints a
  `WARNING:` line and still exits 0.
- The EXECUTE snippet's `RUNTIMES` import and its `row.review_only` / `row.runner` fields exist.
- `cli-profiles/` has no `pi.md`, as the new "no profile file" note says.
- Commit `f9b6405` makes `fetch-model-catalog` discover a custom grok entry's model by its
  binary, which matches the new item-3 wording.

Open findings:
- **Minor** — `SKILL.md` Step 3 says "`$SCRATCH/rendered.toml` holds the exact bytes written".
  The stdout copy has one extra trailing newline (`print`), so `cmp` against the target file
  fails at EOF. Harmless for reading the `policy.ladder` line. Write "the same TOML as written",
  or `diff` the files instead of `cmp`.

Verdict: **PASS**.

BASELINE 103/120
CURRENT 106/120
CRITICAL 0
IMPORTANT 0

## 3. ai-kit-spec-execute-superpowers

Lines: SKILL.md 344 (baseline 290); references 432 (baseline 388). Baseline 108, current **110**.

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| D1 | 17 | 17 | The stuck-key anchor (`$LAST_DISPATCHED_KEY`), with the A > B resume example, is real expert content |
| D2 | 13 | 13 | unchanged |
| D3 | 14 | 14 | unchanged |
| D4 | 14 | 14 | unchanged |
| D5 | 14 | 14 | unchanged |
| D6 | 14 | 14 | unchanged |
| D7 | 9 | 9 | unchanged |
| D8 | 13 | 15 | Floor survives resumes; non-Claude native rounds 4–5 handled with an unblock path; state is printed after every change |

Re-verified:
- `write-resumable-state` stores `last_dispatched_key` verbatim (the state is a free-form JSON
  dump).
- `resume-exclusions` drops `quota` keys (`["a","c"]` with a=quota, c=auth gives `["c"]`).
- The `escalation.md` snippet computes the floor from `$LAST_DISPATCHED_KEY` with the
  `len(ladder)` not-found fallback.
- `QUOTA_PATH` is now printed in Step 2, which `state-management.md`'s `RESUME_STATE_PATH` needs.

R2 Minor (heartbeat sentence breaking the numbered list): **resolved** (now indented under
step 3).

Open findings: none.

Verdict: **PASS**.

BASELINE 108/120
CURRENT 110/120
CRITICAL 0
IMPORTANT 0

## 4. ai-kit-spec-execute-gsd

Lines: SKILL.md 412 (baseline 296); references 67 (baseline 46). Baseline 101, current **103**.

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| D1 | 15 | 15 | unchanged |
| D2 | 12 | 12 | unchanged |
| D3 | 12 | 12 | unchanged |
| D4 | 14 | 14 | unchanged |
| D5 | 13 | 13 | unchanged |
| D6 | 14 | 14 | unchanged |
| D7 | 8 | 8 | unchanged |
| D8 | 13 | 15 | Cleanup parses the JSON and gates Step 3; legacy single-marker block detected |

Re-verified:
- `clear-workflow-keys` prints `ApplyResult._asdict()`, which always has `failed` (null on
  success) and `revert_failed` (a list), and returns 1 on `failed`. The new JSON check is
  correct.
- The Step 3 guidance script (the marker-guarded Python block, extracted from SKILL.md and run
  as-is) behaved as follows:
  - a fresh write adds the block;
  - a re-run replaces it (one block left, v2 content);
  - a file with the legacy marker exits 2 with the documented message.

Correction to my R2 score: the old `grep -q 'revert_failed'` matched on every successful
cleanup, because the field is always present. A cleanup that succeeded therefore exited 1. That
was a real defect, and I missed it in R1/R2. It is fixed here.

Open findings: none.

Verdict: **PASS**.

BASELINE 101/120
CURRENT 103/120
CRITICAL 0
IMPORTANT 0

## 5. ai-kit-gsd-curated-config

Lines: SKILL.md 285 (baseline 295); new `references/runner.md` 53 and `references/v1-path.md`
40. Baseline 101, current **106**.

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| D1 | 16 | 16 | unchanged |
| D2 | 11 | 11 | unchanged |
| D3 | 13 | 13 | unchanged |
| D4 | 14 | 14 | unchanged |
| D5 | 12 | 14 | v1 and runner detail in references with explicit "read only when" triggers |
| D6 | 14 | 14 | unchanged |
| D7 | 8 | 9 | Clean Process plus reference split |
| D8 | 13 | 15 | Per-flow permissions stated precisely; reporting rule now keeps every warning and approval row verbatim without dumping JSON |

Re-verified:
- v2 writes the bare `CROSS_AI_COMMAND = "node .planning/scripts/cross-ai.mjs"`
  (`cross_ai.py:12`, `recommend.py:880`).
- Without `--codex-sandbox`, the runner's codex exec uses
  `--dangerously-bypass-approvals-and-sandbox` (`cross-ai.mjs:354-356`).
- The v1 hook adds `--codex-sandbox workspace-write` for codex (`cross_ai_build._runner_hook`)
  and no `--prepend-file`.
- Fallback happens only on a `fallback` status with `tree=clean` (`cross-ai.mjs:219,398`).
  Every flag in the v1 reference and the subcommand table exists.

Open findings: none.

Verdict: **PASS**.

BASELINE 101/120
CURRENT 106/120
CRITICAL 0
IMPORTANT 0
