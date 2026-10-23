I haven't run anything. The skill is off-limits, so I can't read its helper's exact interface, and I don't have the screening's inputs. Everything below is the plan, with those gaps marked.

**1. Find the existing Laya/TypeSafe fallback (no skill, no guessing)**
- Call `codegraph_explore` with the query "jev decide ladder Laya TypeSafe fallback 8010 TYPESAFE_API_KEY". `.codegraph/` exists, so this comes before grep.
- If that falls short: `rg -n "8010|TYPESAFE_API_KEY|unavailable/http_" --glob '!.planning/**' .`
- This should turn up the repo's decide.py/jev ladder, which my notes say is Laya, then TypeSafe, then my own reasoning. I'd then read its CLI usage and endpoint paths. I won't invent URLs or request schemas.

**2. Verify the backends are up, not just reported up**
- Laya: `curl -sS -m 5 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8010/` as a bare reachability check. I'd switch to the model-list or health path once step 1 names it.
- Key: `test -n "$TYPESAFE_API_KEY" && echo set || echo missing`. This never prints the key. I would not `echo` or `env | grep` it.

**3. Re-run the screening through the ladder, skipping Zen**
- I'd run the same batch of typed questions (yes/no, choice or score) via the helper from step 1, pointed at Laya first. Zen's 429 comes from quota, so retrying Zen is pointless.
- If the helper has no backend override flag, I'd use whatever env var or config it reads, found in step 1. I wouldn't patch the helper just to get past this.
- If Laya errors or times out, I'd fall back to TypeSafe directly using `TYPESAFE_API_KEY`. I'd use the same payload and keep any key out of the output and logs.
- If both fail, I'd do the screening with my own reasoning and say so.

**4. Treat the answers as advisory**
- I'd spot-check any answer that decides something, for example by reading the cited evidence myself.
- The report would say which backend answered each item (Laya, TypeSafe or own reasoning) and that Zen was skipped on a 429.

**Not known:** what is being screened, since I don't have the question batch or the input files. I'd need those, or the path to the pending screening file, before step 3. Also unverified: Laya's endpoint shape and TypeSafe's URL. I'm not assuming either.
