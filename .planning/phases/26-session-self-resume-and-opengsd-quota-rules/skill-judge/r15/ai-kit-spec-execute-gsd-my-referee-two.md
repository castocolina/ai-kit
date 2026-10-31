Judge: my-referee-two
Reviewed-sha256: 087fb33173e1a99aa9009e1d2573ea6d90bc206f2c639b29ac81a01a62811b71
Lane: AIKIT-XAI status=ok cli=pi model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=228s out=8455 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 101
Critical: 0
Important: 2

# Skill Evaluation Report: ai-kit-spec-execute-gsd

## Summary
- **Total Score**: 101/120 (84%)
- **Grade**: B
- **Pattern**: Process (phased workflow with fail-closed checkpoints)
- **Knowledge Ratio**: E:A:R ≈ 80:15:5
- **Verdict**: A dense, expert, fail-closed GSD dispatch adapter whose procedure is mostly verified against the repo, but one exit-code rule would drop a real config error on the floor and one wake parse would close the wrong session.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Ownership, unquoted-hook, trust, and quota-wake rules are not model knowledge. |
| D2: Mindset vs Mechanics | 13 | 15 | Strong "why this stop is terminal" framing plus exact domain procedures. |
| D3: Anti-Pattern Quality | 14 | 15 | NEVER list is specific and reasoned; a few bans are repeated later. |
| D4: Specification Compliance | 14 | 15 | Frontmatter valid; description has WHAT, WHEN, and trigger terms. |
| D5: Progressive Disclosure | 12 | 15 | Triggers are mandatory and conditional; no "Do NOT Load" for the rationale file. |
| D6: Freedom Calibration | 14 | 15 | Low freedom matches config writes and live hooks; judgment left where it belongs. |
| D7: Pattern Recognition | 8 | 10 | Clear Process pattern, longer and more nested than the ideal. |
| D8: Practical Usability | 8 | 15 | Two instructions disagree with the code an agent would actually run. |

## Critical Issues

None. The mismatches are wrong recovery behavior, not a procedure that writes a hook or dispatches GSD incorrectly on the happy path.

## Top 3 Improvements

1. Make Step 1's exit-2 handling match `cli.py`: a `purpose = "execute"` refusal exits 2 with stderr and no JSON, and the agent must relay that text, not treat it as a silent crash.
2. Parse the wake id as the remainder after the first hyphen, and say so next to the arm block, so a session id that itself contains hyphens is not truncated.
3. Add one "Do NOT Load" line for `dispatch-notes.md` inside Step 2, and state that a user-owned `cross_ai_timeout` below 1800 is left in place by cleanup.

## Detailed Analysis

### D1 (18/20)

Expert content dominates: adapter-owned keys, the unquoted `${CROSS_AI_CMD}` expansion, `trust-local` consent, native-tier pins that outlive cleanup, and the rule that only the scheduled wake may answer `retry`. Checked against the repo: `CLAUDECODE` is a truthy claude signal (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:111`, `:231-237`); gsd-tools search order matches (`gsd_tools.py:4-8`, `:86-93`); `cache-path --kind quota` exists (`cli.py:142`); `ensure-runner --cwd --guidance-file` exists (`ai-kit-gsd-curated-config` `cli.py:781-785`); tiers are only `opus`/`sonnet`/`haiku` (`gsd_config.py:27-31`); codegraph probe timeout is 15 s (`detection.py:1203`). A little prose restates the same fail-closed rule in three places.

### D2 (13/15)

The mindset ("resolve fresh every run; clear a stale hook even when this mode is native") is paired with procedures the model cannot invent: workstream-aware `config-path`, `write-workflow-keys --min`, and the Skill-tool handoff. Some later paragraphs restate the NEVER list instead of adding a decision.

### D3 (14/15)

The NEVER list at `SKILL.md:9-29` names the landmines with reasons: no subprocess GSD, no raw vendor CLI in the hook, no second `trust-local` ask, no re-resolve after a cross-AI stop, never answer `skip`, never treat `fallback_notice` as permission to continue. That is experience, not generic caution.

### D4 (14/15)

`name` is lowercase and within 64 characters. The description states the function, three trigger situations, and the keywords GSD, `.planning/PROJECT.md`, `cross_ai`, `/gsd-execute-phase`, and Claude Code. It is one long sentence, but an agent can decide whether to load it.

### D5 (12/15)

`SKILL.md` is about 400 lines, under the 500-line cap, and the four references are pulled in at real decision points: `resumable-state.md` on `quota_exhausted` (`SKILL.md:169-171`), `cross-ai-hook-setup.md` only after the opt-in check (`SKILL.md:243-245`), `session-wake.md` Arm only for two or more pending plans (`SKILL.md:356-358`). `dispatch-notes.md` is correctly labeled background (`references/dispatch-notes.md:3-4`) but Step 2 never says not to load it. There is no explicit "Do NOT Load" anywhere.

### D6 (14/15)

Config writes, hook cleanup, and retry answers are low-freedom and should be. Owner consent for `trust-local` and for falling through to native execution is left open. The pasted bash matches the CLI flags I checked.

### D7 (8/10)

This is a Process skill: Step 0–3, mode branch, cleanup gate, invoke, close. Deviations are length and a mode machine that is restated in Step 1, Step 2, and the hook-setup reference.

### D8 (8/15)

Edge coverage is otherwise strong (malformed markers, user-owned hooks, missing scheduler, Node disappearing mid-wave). Two instructions contradict the implementation:

**Finding 1 — Important.** `skills/ai-kit-spec-execute-gsd/SKILL.md:148-152`.
The exit-2 causes listed there are a cwd mismatch, a shim crash with no JSON, missing `node`, missing `gsd-tools.cjs`, no config path, a malformed `review-spec.toml`, "or an entry with `purpose = "execute"` that can never execute (a custom `command` entry, grok, or claude with a model outside its alias set)." The last item is not an exit-2 cause. `resolve_execute_candidates` calls `screen_execute_clis`, which raises `ExecuteSelectionError` for `purpose == "execute"` (`execute_selection.py:96-108`), and `_cmd_resolve_dispatch` turns that `ValueError` into exit 2 with stderr only (`cli.py:178-182`). A custom `command`, grok, or non-alias claude entry with `purpose` unset or `"both"` is skipped with a warning and the ladder continues (`execute_selection.py:91-106`). An agent that treats this exit 2 as "no JSON, crash" will not relay the refusal that names the reviewer key, so the owner cannot fix the entry that blocked the whole resolve.
Fix: split the sentence. Exit 2 with stderr and no JSON includes a `purpose = "execute"` entry that can never execute; relay that stderr. A custom `command`, grok, or claude entry that is not explicitly `purpose = "execute"` is skipped, not a hard stop.

**Finding 2 — Important.** `skills/ai-kit-spec-execute-gsd/references/session-wake.md:39-41`.
The arm block does `WAKE_HOST="${WAKE_HOST_ID%%-*}"` and `WAKE_ID="${WAKE_HOST_ID#*-}"` on a line the wake CLI prints as `armed <host>-<session_id>` (`arm.py:480`). `${var#*-}` removes the shortest prefix through the first hyphen, so the first hyphen inside the session id is treated as the host separator and `WAKE_ID` loses its tail. Close (`session-wake.md:122-124`) and the quota-wake prompt then call `done` and re-arm with that truncated id. `arm.py:566` treats an existing state for the real id as `refreshed`, which this skill maps to `WAKE_OWNED=0`, so the run neither owns nor closes the wake it created.
Fix: document and parse host as the token before the first hyphen only, and session id as everything after it (`${WAKE_HOST_ID#*-}` is already that form — the bug is using the same split when the id itself contains hyphens; take the id from the remainder after stripping the known host prefix, and state that session ids may contain hyphens). Add a one-line example `armed claude-sid-c1` → host `claude`, id `sid-c1`.

### Minor (not counted)

- `SKILL.md:278-279` says cleanup deletes a `cross_ai_timeout` below 1800 that Step 2 raised and does not restore the user's lower value. `clear-workflow-keys` only unsets adapter-owned keys (`cli.py:259-268`). A user-owned value under 1800 is kept. The raised-and-owned case is correctly described in `cross-ai-hook-setup.md:80-83`; the Step 2 sentence should say "adapter-owned" only.
- `cross-ai-hook-setup.md:92-93` says Node 24 is "GSD's floor, unverified: the installed gsd-core declares none." The skill flags it unverified, and this checkout has no gsd-core `package.json` to check. Research notes record `@opengsd/gsd-core` engines `node >=24` (`.planning/phases/18.1-one-runtime-model/18.1-RESEARCH.md:231`). Soften "declares none" to "not declared in this checkout."
- `SKILL.md:352-353` claims GSD reads CONTEXT.md and RESEARCH.md only at `context_window` 500000, and only from a commit in worktree mode. No file in this repo supports that. Label it unverified or drop it.
