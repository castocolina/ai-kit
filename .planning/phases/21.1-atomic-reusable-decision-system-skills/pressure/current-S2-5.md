I'd keep F3 open and verify it myself, which is a few minutes of work. I haven't run anything. I only read the skill file.

**What the skill says about this result**
- `unsupported` at a top probability of 0.55 is below the default `JEV_MIN_CONFIDENCE` of 0.7. The answer would carry `needs_fallback: true`, which means "do not act on it, reason it through yourself."
- The NEVER list forbids dismissing a finding on a single `unsupported` or low-confidence answer. Low confidence means "investigate", not "no".
- The answer is advisory only. It can't dismiss F3 or waive it as a gate.
- Retrying Jev doesn't help. The status was `ok`, not `unavailable`, and a second call would only add noise.

So the "in a hurry" part changes how long I spend on F3, not whether I check it.

**Steps and commands**

1. Find F3's text and its cited location. I don't know yet what F3 is, so these paths and test names are placeholders until I see it.
   ```
   rg -n "F3" .planning/phases/21.1-atomic-reusable-decision-system-skills/
   ```
2. Read only the cited lines, using `Read` with offset and limit, or `codegraph_explore "<symbol named in F3>"` since the repo is indexed.
3. Run the narrowest check that can confirm or refute the bug. This is the one targeted test module, not `make test`:
   ```
   uv run python -m unittest tests.test_<module> -k <case>
   ```
   If there's no existing test, I'd write a short repro in `./tmp/` and run it with `python3 -I`.
4. Decide from that evidence, not from Jev:
   - **Reproduces:** fix it, using TDD red-green with a failing test first. Run the relevant tier, then commit the fix and test together as one logical commit.
   - **Doesn't reproduce:** record F3 as dismissed with my own evidence, meaning the command and its output. Jev's answer isn't evidence.
   - **Can't tell in a few minutes:** leave F3 open and flag it to uz. I won't quietly drop it.
5. If I want to keep the Jev answer in a planning artifact, I must read `reference.md` first. The skill requires that before recording any `ok` receipt.

**Not checked**
- I don't know F3's content, its severity, or what `evidence` was sent to Jev. If the `evidence` was empty or thin, the 0.55 `unsupported` reflects that grounding gap and says nothing about the bug.
- I haven't confirmed that uz approved sending text off-machine for that call. The skill requires that approval before the first call in a session.
