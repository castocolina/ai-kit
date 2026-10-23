I can't give you the exact command line yet. The jev helper's path and backend-selection flags live in its skill docs, and you told me not to read skills. I also don't have the screening's inputs (which questions or candidates). Below is the plan, with the guesses marked.

**1. Don't retry Zen.**
A 429 from Zen means the budget is out, and per my notes on the jev backends that won't recover soon. I'd skip it and move on to the fallback ladder: Laya, then TypeSafe direct, then my own reasoning.

**2. Check Laya and the key without printing anything.**
```bash
curl -sS -m 5 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8010/v1/models
[ -n "${TYPESAFE_API_KEY:-}" ] && echo "typesafe key: set" || echo "typesafe key: MISSING"
```
- The `/v1/models` path is a guess. If it 404s, I'd treat any HTTP response as "up" and let the real call decide.
- The key is only tested for presence. It is never echoed, and I wouldn't use `set -x` or `env`.

**3. Find the helper's backend switch.**
I'd run the helper's own `--help`, not read its SKILL.md. I'd locate it first with `rg -l "jev" tools/ scripts/ 2>/dev/null` (the path is a guess). I'd look for a flag or env var that selects Laya or TypeSafe instead of Zen.

**4. Rerun only the unfinished questions on Laya.**
- Same typed questions and same batch as the failed Zen call (yes/no, choice or score).
- I'd keep the items Zen already answered, if any came back before the 429, and send only the rest.
- The command shape would be `<helper> --backend laya <same input>`. The flag name is a placeholder until step 3.

**5. Fall back to TypeSafe direct if Laya errors or times out.**
- Same input, with `TYPESAFE_API_KEY` read from the environment by the helper and never passed on the command line.
- Because it's an authenticated call to a third party, I'd use the key only for the screening payload and nothing else.

**6. Handle the results.**
- Jev answers are advisory only. I'd spot-check the borderline or high-impact items against the actual evidence before accepting them.
- If both backends fail, I'd screen the remaining items with my own reasoning and label them as such.
- I'd report per item which backend answered (Laya, TypeSafe or me) and that Zen was skipped because of the 429. Any item I screened myself would be marked.

**Not checked:** the screening's inputs, the helper's actual flags, and Laya's health endpoint are all unknown to me. Treat the `curl` path and `--backend` flag above as guesses until step 3 confirms them.
