# Phase 18.1: independent skill-judge, round 4 (final)

Same rubric (`~/.claude/skills/skill-judge/SKILL.md`, 8 dimensions, 120 points), applied to
SKILL.md plus `references/` at HEAD `e981973`. The baseline is still `a8e24c3`, so baseline scores
are carried over from round 1. Fix range: `c6334ef..e981973` (da7019c, 6cdf7a1, 6d35622,
78304a6, plus e981973, a code-only runner change). ai-kit-gsd-curated-config is unchanged since R3
(106/120, PASS) and is not re-scored.

How I checked (offline): a scratch HOME under `./tmp/sj181r4/` (removed afterwards), `--help`, and
reading the code. I also ran these on synthetic input; none of them spawns an AI CLI:
- `render-toml --out` with and without `--replace`;
- the spec-config ranking snippet, extracted from `cli-model-selection.md` item 5 and run
  against a synthetic catalog;
- superpowers and GSD `write-resumable-state` with the new state fields;
- the GSD Step 3 guidance script on a fresh file, a re-run, an orphan start marker and a
  missing file.

`./tmp/judge` was not touched.

---

## 1. ai-kit-spec-review

Lines: SKILL.md 467 (baseline 533). Baseline 101, current **106**.

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| D1 | 16 | 16 | unchanged |
| D2 | 13 | 13 | unchanged |
| D3 | 13 | 13 | unchanged |
| D4 | 14 | 14 | unchanged |
| D5 | 11 | 13 | unchanged since R3 |
| D6 | 14 | 14 | unchanged |
| D7 | 7 | 8 | unchanged since R3 |
| D8 | 13 | 15 | Adds: keep original `--index` when an entry is dropped, iteration counting for the native-revise path, printed `RUN_TMP_DIR` |

Re-verified:
- `cross-ai-dispatch.md` point 1 now ends with `printf '%s\n' "$RUN_TMP_DIR"`.
- The `--no-cross-ai` literal now carries `"route": "native"`, matching `resolve-reviewers`
  output for the session default.
- `dispatch-reviewer --index` reads by position in `reviewers.json`, so keeping the original
  index is correct.
- The `resolve-timeout-tiers` and `dispatch-reviewer` flags are unchanged.

Open findings: none.

Verdict: **PASS**.

BASELINE 101/120
CURRENT 106/120
CRITICAL 0
IMPORTANT 0

## 2. ai-kit-spec-config

Lines: SKILL.md 491 (baseline 361); references 341 (baseline 317). Baseline 103, current **107**.

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| D1 | 15 | 15 | unchanged |
| D2 | 12 | 12 | unchanged |
| D3 | 13 | 14 | New rule: "`--local`/`--global` choose the target, never consent to replace it" (non-obvious, data-loss) |
| D4 | 14 | 14 | Description now says it asks before replacing any existing config |
| D5 | 14 | 14 | unchanged |
| D6 | 14 | 15 | Replacement gate defaults to "stop", and the code enforces it |
| D7 | 8 | 8 | unchanged |
| D8 | 13 | 15 | Nonzero exit handled as "write NOT confirmed", reading the target back; stale catalog pairs filtered |

Re-verified:
- `render-toml --replace` exists.
- Without it, an existing `--out` file is refused: exit 1, stderr
  `render-toml: refusing to replace existing <path> (nothing written); pass --replace only after
  the user approved replacing it`, and the file is untouched.
- A new file writes with exit 0. `--replace` overwrites, exit 0.
- stdout differs from the file only by one trailing newline, as the doc now says.
- No other caller of the `render-toml` CLI exists in `skills/` or `tools/`, so the new refusal
  breaks nothing.
- The item-5 ranking snippet, run against a synthetic catalog, works as documented:
  - it drops a cached `opencode` pair that is absent from `discovered`;
  - it lists `anthropic/...` via `claude` under REVIEW only;
  - EXECUTE shows codex only.

R3 Minor ("exact bytes written"): **resolved** (`SKILL.md`, "the same TOML as written (stdout
adds one trailing newline, so compare with `diff`, not `cmp`)").

Open findings:
- **Minor (code message, adjacent to the new flag)** — the legacy-migration note in
  `ai_kit_spec/config_io.py:258-259` still tells the user to "re-save it with the
  ai-kit-spec-config wizard or render-toml --out". For the file being migrated, which always
  exists, a bare `render-toml --out` is now refused. Add "(with `--replace`)" to the note.

Verdict: **PASS**.

BASELINE 103/120
CURRENT 107/120
CRITICAL 0
IMPORTANT 0

## 3. ai-kit-spec-execute-superpowers

Lines: SKILL.md 348 (baseline 290); references 452 (baseline 388). Baseline 108, current **110**.

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| D1 | 17 | 17 | Round-start anchor vs last dispatch: a subtle, real distinction |
| D2 | 13 | 13 | unchanged |
| D3 | 14 | 14 | unchanged |
| D4 | 14 | 14 | unchanged |
| D5 | 14 | 14 | unchanged |
| D6 | 14 | 14 | Unknown or empty anchor now stops and asks instead of guessing |
| D7 | 9 | 9 | unchanged |
| D8 | 13 | 15 | Anchor persisted and restored; persisted reasons filtered to persisted keys; unblock advice corrected |

Re-verified:
- `write-resumable-state` stores free-form JSON, so `escalation_anchor_key` and
  `last_dispatched_key` round-trip.
- `resolve-injection --escalation-excluded-keys-json` exists.
- `_merged_quota_exhaustion_payload` (`cli.py:129-140`) computes `any_quota_recoverable` only over
  `tried ∪ exclude` minus the escalation floor. That matches "ignores quota reasons for
  unpickable keys" and the reworded `any_quota_recoverable == False` branches.
- The `escalation.md` snippet now takes `$ESCALATION_ANCHOR_KEY`.
- `state-management.md` initialises it, resets nothing on resume, and writes it as argv[8].

Open findings: none.

Verdict: **PASS**.

BASELINE 108/120
CURRENT 110/120
CRITICAL 0
IMPORTANT 0

## 4. ai-kit-spec-execute-gsd

Lines: SKILL.md 429 (baseline 296); references 67 (baseline 46). Baseline 101, current **104**.

| Dimension | Baseline | Current | Notes |
|---|---|---|---|
| D1 | 15 | 15 | unchanged |
| D2 | 12 | 12 | unchanged |
| D3 | 12 | 12 | unchanged |
| D4 | 14 | 14 | unchanged |
| D5 | 13 | 13 | unchanged |
| D6 | 14 | 15 | Atomic phase-file write (`mkstemp` + `os.replace`, mode kept) and strict marker check |
| D7 | 8 | 8 | unchanged |
| D8 | 13 | 15 | Phase prompt file must be supplied, not guessed; resume state records it; `unsafe_hook_token` listed among the permanent reasons |

Re-verified:
- The Step 3 script, extracted verbatim and run:

  | Case | Result |
  |---|---|
  | fresh file | block written, rc 0 |
  | re-run | block replaced (one block, new content), rc 0, file mode 640 kept |
  | an extra orphan start marker | the "markers are malformed" message, exit 2, file untouched |
  | missing file | "cannot read …" then the read/write message, exit 2 |

- `write-resumable-state` stores `phase_prompt_file`.

Open findings: none.

Verdict: **PASS**.

BASELINE 101/120
CURRENT 104/120
CRITICAL 0
IMPORTANT 0
