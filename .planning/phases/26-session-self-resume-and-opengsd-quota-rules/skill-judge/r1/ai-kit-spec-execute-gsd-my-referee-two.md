Judge: my-referee-two
Reviewed-sha256: 7a8c37b5cbcbe91d4d4326f05113ce1aa111481093e50b9afa9606b85192cf02
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=635s out=581122 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 100
Critical: 0
Important: 1

# Skill Evaluation Report: ai-kit-spec-execute-gsd

## Summary
- **Total Score**: 100/120 (83%) — Grade B
- **Pattern**: Process (phased workflow with checkpoints), with Tool-pattern verbatim code blocks
- **Knowledge Ratio**: E:A:R ≈ 80:10:10
- **Verdict**: A dense, near-fully-verified operational skill whose every checkable factual claim matches the repository; its one real defect is a misattributed reason description in Step 1 that would make an agent report the wrong stop cause to the owner.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 16 | 20 | Nearly pure project-expert knowledge (ownership sidecar, hook allowlist, exit-code contracts, trust model); costs: 9-per-call JSON one-liners, ~5× repetition of the "no native fallback without owner decision" rule |
| D2: Mindset + Procedures | 13 | 15 | Explicit "Mindset before writing anything here" (SKILL.md:188-194); non-obvious orderings (opt-in check before any write incl. `ensure-runner`, cleanup before Step 3, producer status before runner render) |
| D3: Anti-Pattern Quality | 14 | 15 | NEVER list (SKILL.md:8-45) is specific and experienced: never re-resolve after a failed dispatch (rewrites the hook), never answer `skip` (native fallback = harness switch), untrusted-repo JS execution warning (SKILL.md:32-39) |
| D4: Specification Compliance | 14 | 15 | Valid frontmatter; description has WHAT + three numbered WHEN triggers + keywords (GSD, `.planning`, `cross_ai`, `model_profile_overrides`, `workflow.cross_ai_command`) |
| D5: Progressive Disclosure | 11 | 15 | 543-line SKILL.md (over the ~500 guidance); one reference file with a clear "Not needed to execute" header (dispatch-notes.md:3-4) and two anchored optional-load triggers (SKILL.md:234-236, 433-435); no explicit "Do NOT load" list |
| D6: Freedom Calibration | 13 | 15 | Low freedom (verbatim bash, exact wake prompt text) for genuinely fragile config surgery; owner-decision points left to judgment — appropriate |
| D7: Pattern Recognition | 8 | 10 | Clear Process pattern; deviations: length and interleaved verbatim scripts |
| D8: Practical Usability | 11 | 15 | Exhaustive mode/exit-code/fallback coverage; hurt by the misattributed reason taxonomy, a dangling cross-reference, and reliance on the agent re-substituting captured literals across fresh shells (explained, but error-prone) |

## Findings

1. **Important — SKILL.md:174-177**: The permanent-reason taxonomy misattributes `no_usable_dispatch`'s description to the four other reasons, and the pointer "see Step 2, `no_usable_dispatch`" is dangling — Step 2 (SKILL.md:181-357) never mentions `no_usable_dispatch`. As written, "no candidate has a native GSD tier or a CLI with an execute builder, so the execute-CLI screen skipped them all" is presented as the meaning of `no_configured_candidate`, `all_candidates_context_rejected`, `unsafe_hook_token` and `unsupported_model_id`, which is wrong: it is exactly the `no_usable_dispatch` message (`ai_kit_spec_gsd/adapter.py:288-292`), while `unsafe_hook_token` means a disallowed character (`adapter.py:243-245`), `unsupported_model_id` a grammar mismatch (`adapter.py:238-242`), `all_candidates_context_rejected` a context-limit rejection (`adapter.py:293-297`). The STOP action is the same for all, so no harmful action follows — but an agent relaying the stop cause to the owner would report the wrong diagnosis (and the wrong fix). **Fix**: list `no_usable_dispatch` as a fifth permanent reason carrying that description, delete "see Step 2", and optionally give each remaining reason its own one-line meaning.

Minor (not counted):
2. **Minor — SKILL.md:241-251 vs 341-351**: the clear-hook JSON check is duplicated verbatim (function vs. standalone block); they can drift apart. Factor the second into a reference to the first.
3. **Minor — SKILL.md:106-114**: nine separate `python3 -c` processes to unpack one JSON object; one small python loop (or a `summarize` subcommand in the shipped `ai_kit_spec_gsd` package) would be shorter and safer to retype.
4. **Minor — SKILL.md (length)**: 543 lines; Step 1/2 shell choreography could partly move into the package's CLI, thinning the body.
5. **Minor — SKILL.md:42-44, 505-506**: `Skill` tool and `CronCreate` are Claude Code specific; the gap is explicitly flagged with fallbacks (sanctioned by repo policy), but portability remains limited.
6. **Minor — SKILL.md:161**: `RESUME_VIA=skill  # Step 3's router stop runs this block with gsd-execute-phase` reads as self-contradictory without the prose at SKILL.md:153-158.

## Factual claims checked against the repository (all verified)

- CLI surface: all seven subcommands used (resolve-dispatch, config-path, write-workflow-keys, clear-workflow-keys, prepare-tooling, print-dispatch-guidance, write-resumable-state) — `ai_kit_spec_gsd/cli.py:459-469, 396-456`.
- Exit codes: exit 2 on node-missing/no-gsd-tools/no-config-path (`cli.py:78-106`), ConfigError → 2 (`cli.py:482-488`), `write_failed` → exit 1 with JSON (`cli.py:184`); `purpose="execute"` unexecutable entry raises → exit 2 (`execute_selection.py:75-108`, `cli.py:179-181`).
- `ai-kit: gsd-core <version> at <path>` stderr banner — `cli.py:107-108`.
- gsd-core root order (`<root>/gsd-core`, `.claude/gsd-core`, `.codex/gsd-core`; root = `RUNTIME_DIR` or git toplevel) — `ai_kit_spec/gsd_tools.py:38-47, 85-101`.
- All fallback reasons exist (`no_configured_candidate` adapter.py:276; `all_candidates_context_rejected` :294; `unsafe_hook_token` :244; `unsupported_model_id` :240; `quota_exhausted` :256; `no_usable_dispatch` :290; `malformed_config` cli.py:119).
- Provenance values `existing_gsd_config`/`resolved_candidate` — `adapter.py:164, 187, 196, 216`.
- `--min cross_ai_timeout=1800` floor semantics (value ≥ floor kept user-owned) — `cli.py:239-242`; curated floor 1800 — `ai_kit_gsd_curated_config/cross_ai.py:47`.
- `clear-workflow-keys` clears only adapter-owned keys; `revert_failed` always in output — `cli.py:258-264`, `gsd_config.py:102-149`.
- Hook allowlist `^[A-Za-z0-9._:/@+=,#-]+$`, `node .planning/scripts/cross-ai.mjs`, `--no-preamble --prepend-file .planning/scripts/cross-ai-guidance.md`, cursor-bracket/glob rationale — `runner_dispatch.py:32-36, 185-199`.
- pi/copilot exec notes printed before the hook is written — `runner_dispatch.py:170-182`, `adapter.py:217-221`.
- claude aliases fable/opus/sonnet/haiku; claude `review_only=True`; grok `runner=False` — `detection.py:109-125`.
- `prepare-tooling` = detect → tooling path → probe_codegraph (report-only, 15 s, skipped without `--runtime`) → index (`sync` then `init`) — `cli.py:267-294`, `detection.py:1203, 1238-1242, 1313-1327`; install line relayed, never run — `detection.py:1240-1242`, `cli.py:271-274`.
- Siblings exist: `ai-kit-cross-ai/SKILL.md` with sections 4/6/7/8 as cited (section 6 holds the whole-minute and under-60 s wake rules, :151-156); `ai-kit-session-wake.py` with `arm`/`done`, `--ref`, `armed <host>-<session_id>`/`refreshed` output, exit 3 no-primitive, session-id refusal — session-wake `cli.py:45-84`, `arm.py:480, 548-557` (the `%%-*`/`#*-` parsing in SKILL.md:458-460 correctly survives hyphenated UUID ids).
- `ensure-runner --guidance-file`, exit 1 not-ready with `.new`, exit 2 error — curated `cli.py:225-281, 783-785`, `cross_ai_script.py:195, 302, 425-429`.
- `trust-local --cwd/--show`, `cache-path --kind quota`, "ignoring untrusted project-local config" — ai-kit-spec `cli.py:142-143, 266-269`, `config_io.py:410`.
- Step 0's "same pattern ai-kit-spec-review/SKILL.md uses" — `ai-kit-spec-review/SKILL.md:193-203`.
- dispatch-notes.md:17 allowlist, :54-57 custom-entry exception (`routing.py:138, 177-178`), :59 `ai_kit_spec.dispatch_guidance` module — all exist.
- Could not verify directly (gsd-core not in this checkout): GSD's unquoted `${CROSS_AI_CMD}` expansion, the plan-frontmatter `cross_ai: true` delegation gate, Node 24 as GSD's declared floor (consistent with `.planning/phases/18.1-one-runtime-model/18.1-CONTEXT.md:136`), and `<project>/.claude/commands/gsd-execute-phase.md` install location. Each is hedged in the skill text where live verification is open.
