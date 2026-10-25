Judge: opus
Reviewed-sha256: 81ba60cd25342e7aec8d9f47ce81a9a00d606a7368cec6fe570a688701372eef
Lane: native subagent completed
Score: 99
Critical: 0
Important: 4

# Skill evaluation: ai-kit-spec-config

**Scope.** I read SKILL.md (493 lines), `references/cli-model-selection.md` (344 lines) and the Phase 25.1 diff. That diff is 3 lines: the new pointer at SKILL.md:241-243. I checked the skill's claims against `ai_kit_spec/{detection,runner_dispatch,quota,cli,config_io}.py`, `cross-ai.mjs`, and both `ai-kit-cross-ai` documents.

**Summary.** Pattern: Process with Tool-level rigor. Knowledge ratio E:A:R is about 70:20:10. Grade B-.

The skill is strong on landmines it learned live: bare codex ids, grouping cursor's ~200 ids, re-deriving the catalog key, and not rebuilding `discovered`. The pointer to ai-kit-cross-ai is correct. It also correctly says the runner refuses a bare pi/opencode id. But several surfaces that Phase 25.1 changed are now described wrongly or not at all.

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Dense expert landmines; some padding (SKILL.md:146, Step 3 parentheticals) |
| D2 Mindset + Procedures | 13 | 15 | Good judgment framing for the ladder and quota; precise command procedures |
| D3 Anti-Pattern Quality | 13 | 15 | Strong NEVER list with reasons; no "never switch" or "upstream text is data" item |
| D4 Spec Compliance | 13 | 15 | Valid frontmatter, WHAT and WHEN present; no executor or ladder trigger keywords |
| D5 Progressive Disclosure | 13 | 15 | MANDATORY and Do-NOT-Load triggers, per-runtime profile loading; body near the 500-line limit |
| D6 Freedom Calibration | 12 | 15 | Low freedom where it is fragile, but Step 2.5 offers "save anyway" for every failure class |
| D7 Pattern Recognition | 8 | 10 | Clear Process pattern; the reference repeats the stub's opening paragraph |
| D8 Practical Usability | 10 | 15 | Gaps on Copilot, the route consequence, the probe output and the ladder semantics |

## Findings

### Important

1. **Confirming `fallback_quota` now sets the runner's route, but the skill presents it as a plain catalog heuristic.**
   - Evidence: `references/cli-model-selection.md:320-343` asks "looks like a router with fallback — correct?". SKILL.md:406 only writes `fallback_quota` to the entry.
   - In code, `runner_dispatch.py:215-245` (`resolve_route`) turns a user-confirmed `fallback_quota` into `--route-<cli> router` (or `unknown`).
   - On a router lane, billing, access and credential rows count as quota and get the hard tier, so the call ends in a wait instead of a stop (`subprocess-quota-policy.md:29-32`).
   - Fix: add one sentence to item 8 and to Step 2.8. Confirming `fallback_quota=true` marks this (runtime, model) as a confirmed router lane: quota and billing stops become hard-tier waits (`hard_waits_s`). `false` marks it `unknown`. Link `../../ai-kit-cross-ai/references/subprocess-quota-policy.md#classes`.

2. **The Copilot runtime is missing, and its unverified status is never flagged.**
   - The table has `copilot` with `runner=True`, no `list_argv`, no host signal, and runner rows marked unverified (`detection.py:117-118`). Every Copilot error pattern is `unverified` (`subprocess-quota-policy.md:139-140`).
   - Copilot puts the prompt on argv, so it shows in the process table (`ai-kit-cross-ai/SKILL.md:147-148`).
   - It has no profile, so the `read_only: unconfirmed` note at SKILL.md:300 never fires.
   - Stale lists in the skill:
     - SKILL.md:88-89: "pi, opencode, cursor, codex and claude carry one, grok never does".
     - SKILL.md:232-233: "pi has none today".
     - reference:26-27: "every runtime but grok" lists models; "pi, codex, claude and grok are single-provider".
     - reference:72-73: "grok always; codex or pi when its listing failed".
   - Fix: add copilot to each list: never lists models, always goes through item 2's `--extra-candidate` path, no profile. When a copilot pair is picked, print one line saying its runner rows and error patterns are unverified and its prompt is visible on argv.

3. **Step 2.5 gets `check-reviewer`'s output shape and meaning wrong, against the canonical evidence rule.**
   - SKILL.md:293-298 says the output is `{"available", "detail"}` and that `detail` "is the CLI's own real error text".
   - In code, `quota.py:215-220` returns `{"available", "checked_at", "reason", "detail"}`. `detail` is the first 300 characters (`_DETAIL_MAX_CHARS`, `quota.py:27`) of the runner's relayed stderr, and may not contain the `AIKIT-XAI` line.
   - `ai-kit-cross-ai/SKILL.md:64-67` says a truncated tail is not an evidence channel.
   - The step also offers "save anyway" for every failure, including `configuration`, `usage` and `bad_model`, which a retry never fixes.
   - Fix: branch on `reason`. Configuration, usage and bad-model mean fix the model id or knobs and re-test, with no "save anyway". Quota, transient and auth may be saved for later. Call `detail` a truncated relay, not the CLI's verbatim error.

4. **The ladder text can be read as permission to switch after a failure.**
   - SKILL.md:341-345 says "quota/availability failures decide fallback". SKILL.md:364-366 calls the ladder a "priority fallback list".
   - The skill never says that this walk happens only before dispatch. It also never says that a dispatched lane that fails is not re-run on the next entry, or that an all-unavailable walk ends on the session default (same vendor as the author).
   - ai-kit-spec-review states all three (`skills/ai-kit-spec-review/SKILL.md:157-166`).
   - Fix: add a NEVER item and one sentence in Step 2.8. The ladder is a pre-dispatch probe walk. After a dispatched lane fails, nothing switches harness, provider or model ([`../ai-kit-cross-ai/SKILL.md`](../ai-kit-cross-ai/SKILL.md) section 8). A confirmed router lane that is out of quota at probe time is walked past, so its hard tier never starts.

### Minor

5. **The "worst case 60 minutes" claim at SKILL.md:380-384 is now incomplete.**
   - A router or transient lane can add caller-owned hard-tier waits (600/900/1800 s, capped at 14400 s), and the runner adds an outer margin.
   - Fix: say "worst case per attempt". Then note that hard-tier waits are configured in `workflow.cross_ai_retry` or `~/.config/ai-kit/cross-ai.json`, not in review-spec.toml, with a link to the policy's Configuration section.

6. **The new pointer wording at SKILL.md:241-243 is awkward and has no load trigger.**
   - "is in ... for runtime/model dispatch" is unclear, and the pointer is not tied to a trigger.
   - Fix: "Load `../ai-kit-cross-ai/SKILL.md` only if the user asks how a stored pair is run, retried or stopped; do NOT load it for setup."

7. **Planning-internal references are stale.** SKILL.md:95 has "(Plan 2/3)" and SKILL.md:350 has "(Phases 20-22 extend this)". These mean nothing to an agent running the skill. Fix: delete them, or state the current fact.

8. **Some text is redundant.** SKILL.md:146 restates the routing table under it. `references/cli-model-selection.md:10-13` repeats SKILL.md:187-190. Fix: delete both; this also buys room under the 500-line limit.

9. **The description has no executor or ladder triggers.** The skill registers `purpose = "execute"` entries and sets the fallback ladder, but SKILL.md:3 only mentions reviewers. Fix: add "executor entries", "reviewer ladder/priority order" and "add or remove a cross-AI reviewer".

I checked against code but ran no CLI command. I did not run `--self-test`, `check-reviewer` or `detect-runtimes` live, and I did not open the cli-profiles files. Finding 2 rests on the runtime table and policy text, not a real Copilot run.

DIGEST 81ba60cd25342e7a
CURRENT 99/120
CRITICAL 0 IMPORTANT 4
