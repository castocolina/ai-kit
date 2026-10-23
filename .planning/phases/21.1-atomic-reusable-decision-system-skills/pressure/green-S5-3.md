I haven't run any commands. I only read `skills/jev-fast-decision/SKILL.md`. I would not switch to Zen on my own, and I would not send anything off-machine until you say yes.

**Why I would stop and ask**
- `typesafe` and `opencode` (Zen) are different routes. The skill says "use TypeSafe" is not "use Zen". With `TYPESAFE_API_KEY` unset, `typesafe` is unavailable, and switching routes is your call.
- Your "Zen works" tells me Zen is available. It does not tell me to use it.
- "The user said use Jev today" is not consent for a remote backend either.

**Steps, in order**
1. From the skill directory (`skills/jev-fast-decision/`), probe the backends:
   `python3 -B scripts/jev_review.py --probe`
   I expect `typesafe` to show as unavailable because the key is missing, with `opencode` available.
2. Read `backends/typesafe.md` to confirm the missing key is the blocker. I would also read `backends/opencode.md` so I can describe the Zen route accurately. I would read `reference.md` only before interpreting a `score` or receipt.
3. Ask you one question: "TypeSafe can't be used because `TYPESAFE_API_KEY` is unset. Do you want me to use OpenCode Zen (`jev-1.13-free`, then `jev-1.13`) instead? That sends value-free question text off-machine. Do you consent, either once per user or just for this session?"
4. If you say no, I would not call Jev at all. I would reason the judgment myself.
5. If you say yes, I would record consent:
   - Either run the client's `consent grant opencode` subcommand, if it takes that form. I'd confirm that from the client's `--help` first rather than guess.
   - Or, for this session only, run the call with `JEV_ALLOW_REMOTE=1`.
6. Then I would make the call with the route pinned, so it can't silently fall back:
   ```bash
   GSD_PATH_JEV=1 JEV_BACKEND=opencode GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   python3 -B scripts/jev_review.py <<'JSON'
   {"reviewed_head": "<40 hex>", "items": [ ...value-free typed items... ]}
   JSON
   ```
   Zen makes one call per item, so I would not wrap items together.

**Reading the result**
- On `ok`, I would announce `consent_used` and the `trail`. Each answer is advisory input only.
- If an item comes back `needs_fallback: true`, I decide that item with my own reasoning.
- On any other `unavailable` result, I would read the `reason` and not retry blindly.
- No Jev answer would be treated as a verdict or gate, and one low answer would not dismiss anything.

**Missing input:** you gave no question or evidence to judge. I need that, written as English, pattern-only text with no raw hunks, secrets or `.env` values, before I can build the payload.

Skipped: I didn't check the client's exact `consent grant` syntax or the contents of `backends/*.md`. The probe result is assumed, not observed.
