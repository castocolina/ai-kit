I'd treat the Jev answer as weak, advisory input and check F3 directly. `unsupported` with a max probability of 0.55 doesn't say F3 is real or fake. It only says Jev couldn't confirm it from the evidence it was given. AGENTS.md also says not to dismiss a finding as out of scope or pre-existing without verifying. A verdict from Jev alone would be a guess either way.

**Steps (nothing run yet)**

1. **Find F3's claim and its file:line.**
   ```
   rg -n "F3" .planning/phases/21.1-*/ --glob '*REVIEW*' --glob '*.md'
   ```
   If that finds nothing, I'd check the review output I was given. I'd also run `codegraph explore "<symbol named in F3>"` for the cited code.

2. **Read the cited code and its callers.** This uses `codegraph explore`, or `Read` on the cited range. I'm checking whether the code path F3 describes can actually be reached with inputs the callers produce.

3. **Try to reproduce it with a failing test** (red-green, which AGENTS.md allows). I'd put it next to the existing tests for that module, with synthetic fixtures in a tmpdir and no real user config. For example:
   ```
   uv run python -m unittest tests.test_<module>.<NewTestCase> -v
   ```
   - **If the test fails as F3 predicts**, it's a real bug. I'd fix the root cause once in the shared code. Then I'd run `make test` (the aggregate) and `make validate`, and commit the fix and test together as one logical commit.
   - **If the test passes**, F3 is a false positive. I'd keep the test as a regression guard only if it adds value. I'd record "F3 not a bug: <one-line evidence>" in the review file, with no code change.

4. **If I can't tell within a few minutes** (for example, F3 depends on a live CLI or API), I would not guess. I'd mark F3 "unverified" in the review file with what I tried and what's missing, and tell you. I'd also say whether it blocks closing the plan.

**Skipped on purpose:** a second Jev call, an extra reviewer, and a spike. A direct repro is faster than any of them.

**Risk:** I haven't seen F3 yet, so its location and the test module name above are placeholders. If the bug needs a live host (a real opencode or typesafe call), the repro could take longer than a quick unit test.
