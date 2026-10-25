Judge: opus
Reviewed-sha256: ee1794d8f5e1b061433573bd295203633909ba9675b7da446cfd4a399675f4dd
Lane: native subagent completed
Score: 99
Critical: 0
Important: 2

# Skill evaluation report: ai-kit-spec-review (round 3)

**Score: 99/120 (82%), grade B.** The skill follows the Process pattern and runs long. Knowledge ratio is about E:A:R = 75:18:7.

**Verdict:** The skill points at the new `ai-kit-cross-ai` policy and describes the template-8 hard tier correctly. It never re-dispatches a failed lane. Two problems remain: one quoted runner message is stale, and the pre-dispatch probe walk conflicts with the canonical never-switch rule.

## Dimension scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 16 | 20 | Dense expert landmines (`.exit` as the completion signal, the backslash-comment redirect trap, the merge lock). Some narrative padding (the temp-dir backstory, the SEEDS_DIR aside). |
| D2 Mindset + Procedures | 13 | 15 | "Before X, ask yourself" prompts at Steps 0.5, 0.7, 3 and 5, plus domain procedures for resume and merge. |
| D3 Anti-Patterns | 12 | 15 | The hard-rules table gives reasons. The never-switch rule is present at SKILL.md:477 and :352. The NEVER list in the body is short. |
| D4 Spec / Description | 14 | 15 | WHAT, WHEN and keywords are all present, and the name is valid. |
| D5 Progressive Disclosure | 11 | 15 | MANDATORY and Do-NOT-load triggers are present. But a 385-line reference must be read in full on every run, SKILL.md is 492 lines, and one referent dangles. |
| D6 Freedom Calibration | 13 | 15 | Fragile dispatch has low freedom (exact argv, no shell). The Step 1 exit-branch paragraph is hard to follow. |
| D7 Pattern | 8 | 10 | A clear Process pattern, oversized for it. |
| D8 Practical Usability | 12 | 15 | Strong edge-case coverage (both lanes pending, resume, fail-closed merge). It is let down by a stale runner quote, a policy tension and a stale CLI profile. |

## Findings

1. **Important.** The skill quotes a runner message that template 8 no longer prints, and keeps reasoning about trying several CLIs.
   - Evidence: `references/cross-ai-dispatch.md:330-334` quotes "`...(tree=unknown); no other CLI runs after one has run`" and adds "Once one CLI has run, it never tries another: there is no proof that the first one wrote nothing".
   - Template 8 prints only `cross-ai: <cwd> is not inside a git work tree; running without the tree check (tree=unknown)` (`references/cross-ai.mjs:9959-9960`).
   - The runner now starts exactly one runtime per call (`../ai-kit-cross-ai/references/subprocess-quota-policy.md:12-20`). The old text suggests the runner can still walk to another CLI.
   - Fix: replace the quote with the real message and delete the "never tries another" sentence. If needed, add one line: "the runner runs one runtime per call".

2. **Important.** The pre-dispatch probe walk contradicts the canonical never-switch rule.
   - Evidence: `SKILL.md:157-170` moves to the next configured entry, "which may be another provider", when a probe fails "for any reason, a timeout included". When every entry is unavailable it ends on the session default.
   - `../ai-kit-cross-ai/SKILL.md:146-148` says "Never switch harness, provider or model, on any failure, in the runner or in a caller. Never move the work to the native session." It has no pre-dispatch exception.
   - The skill does admit that two parts of the walk are not owner-ruled: walking past a non-quota probe failure, and the implicit session default. But it still does both by default.
   - Fix: either (a) get an owner ruling and write the pre-dispatch-selection exception into `ai-kit-cross-ai` section 8, or (b) until then, on a non-quota probe failure or when only the implicit session default is left, notify and stop instead of walking on.

3. **Minor.** One sentence points at the policy file without saying which file.
   - Evidence: `SKILL.md:153` says "the policy file describes the ladder" with no link. The policy file has moved to `ai-kit-cross-ai`, and "ladder" now means two things: the reviewer ladder and the runner's soft ladder.
   - Fix: link `../ai-kit-cross-ai/references/subprocess-quota-policy.md` and write "the runner's soft ladder".

4. **Minor.** The exit 69/75 rules are copied in three places, which the policy file itself forbids.
   - Evidence: the rules appear at `SKILL.md:330-352`, `references/cross-ai-dispatch.md:244-258` and `:317-326`. The policy says "A skill links here; it does not copy the rules" (`subprocess-quota-policy.md:7`). SKILL.md:330-343 is a 14-line run-on paragraph.
   - Fix: replace SKILL.md:330-343 with a four-row table:
     - exit 75 with `retry_after_s=` → pending lane
     - exit 69 → quote the evidence lines and stop
     - bare exit 75 → owner stop
     - any other nonzero exit → delete the report
   - Keep the detail only in `cross-ai-dispatch.md`.

5. **Minor.** The "read the entire file on every run" rule loads failure-only content.
   - Evidence: `SKILL.md:153` requires reading all of `cross-ai-dispatch.md` (385 lines) on every run, `--no-cross-ai` runs included. That includes the pending-lane section (`:260-326`) and the status table (`:340-368`), which are only needed after a nonzero exit.
   - Fix: move those two sections into a separate reference, loaded from Step 1 only on exit 69 or 75.

6. **Minor.** The CLI profiles are stale or missing for the new model grammars.
   - Evidence: `references/cli-profiles/opencode.md:31-34` says the `#variant` suffix "is not validated". `OPENCODE_MODEL_ID` (`cross-ai.mjs:1297`) now validates `#[A-Za-z0-9._-]+`, allows only one variant and refuses bare ids.
   - There is no profile for pi or copilot, although both are runner runtimes (`ai_kit_spec/detection.py`, copilot row).
   - Fix: correct opencode.md. Either add short notes for pi (`provider/model[:thinking]`) and copilot (prompt on argv, error patterns unverified), or state that the profiles are not exhaustive and the runner owns grammars.

7. **Minor.** The mandatory pointer to `ai-kit-cross-ai` has no fallback.
   - Evidence: `SKILL.md:350-351` requires reading `../ai-kit-cross-ai/SKILL.md`. The installer has no skill-dependency mechanism (`tools/setup.py`), so a selective install can leave this path dangling. The checklist sibling, by contrast, has a fail-closed rule (`cross-ai-dispatch.md:55-64`).
   - Fix: add one line: "If absent, apply the inline rules (quote the evidence lines, schedule only on a hinted 75, never switch) and tell the user to install `ai-kit-cross-ai`."

8. **Minor.** The hard-tier Surface row assumes a sibling lane always exists.
   - Evidence: the "Hard-tier wait" row (`SKILL.md:452`) always says "Its sibling lane is merged now as single mode". That is wrong with one reviewer (Step 2, `:395`) and when both lanes are pending (`cross-ai-dispatch.md:272-273`).
   - Fix: make the sibling clause conditional ("when a sibling ran and is not pending").

I read the code but did not run the runner's `--self-test`, or any eval.

DIGEST ee1794d8f5e1b061
CURRENT 99/120
CRITICAL 0 IMPORTANT 2
