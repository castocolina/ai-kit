The four findings weren't in your message, only the instruction to triage them. I haven't invented any. Paste them (file, line, claim, evidence) and I'll apply the plan below.

## Plan

**1. Check the Laya endpoint.** I'd run one short foreground probe, with no key printed and no retries:
- `curl -sS -m 5 http://127.0.0.1:8010/v1/models` (or `/health`). I haven't verified that Laya serves this path, so I'd adjust to whatever it actually exposes.
- If it's down, I'd fall back to TypeSafe via the existing `decide.py` ladder, then to my own reasoning, and tell you which rung answered.
- To find the existing ladder helper: `rg -n "decide\.py|8010" --glob '!.planning/**'`, and I'd read how it formats requests instead of hand-rolling curl.

**2. Verify each finding myself first, one per file.** Laya's output is advisory only. For each finding:
- Locate the code with `codegraph_explore` (the repo has `.codegraph/`). I'd run `codegraph sync` first if the index may be stale, and use `rg` plus Read only if that falls short.
- Check the evidence against the real file at HEAD: does the line exist, and does the claimed behavior hold?
- Decide with `git log -L` or `git blame` whether the finding is about code this branch changed or code that was already there.
- Run the narrowest test or repro that would show it, for example `uv run python -m unittest tests.test_x`. Where possible I'd use a temp dir and synthetic fixtures, never your real config files.

**3. Ask Laya for a typed judgment per finding, as a screen.** Each finding gets its own small batch item with the verbatim evidence snippet. The question is a choice among valid, invalid, or needs-more-evidence, plus a severity score. Findings have different evidence, so I'd send them as four independent items and not one blended prompt. I'd compare each answer with my step 2 result. If they disagree, my verified result wins, and I'd note the disagreement.

**4. Classify each finding as one of:**
- **Confirmed.** I fix the root cause once in shared code, after grepping all callers. A failing test goes in first (red, then green).
- **Refuted.** I record the one-line evidence that refutes it.
- **Pre-existing or out of scope.** I say so explicitly. If it's real, it goes to `.planning/ROADMAP.md` §Backlog with a goal statement, not silently dropped.

**5. Apply and verify confirmed fixes:**
- `make test` (covers unit, integration, e2e and arch) and `make validate`.
- If a finding touches `tools/status-line.py`, I'd extend `tests/test_arch.py`.
- If a finding touches a `SKILL.md`, it needs the skill-judge loop.
- Commit as one logical change per coherent fix, with its tests and docs. Hooks run, no `--no-verify`, and the Co-Authored-By trailer goes on.
- English only in everything written to files. No absolute paths in source or tests.

**6. Report back.** One short line per finding: verdict, evidence, action taken, and whether Laya agreed.

Not done: nothing ran, and I haven't confirmed that Laya's API shape or `decide.py` exists at the path I'd expect. Step 1 settles both.
