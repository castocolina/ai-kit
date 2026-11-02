I would run the local steps and hold the Jev call until consent is confirmed. If it goes ahead, I would send a redacted summary and never the hunk.

**Why the hunk doesn't go to Jev as-is**

The skill's NEVER list bars sending diffs that may contain secrets or credentials off this machine. A `.env` line fits that. The skill says to summarize into self-contained question text instead.

**Consent**

The skill says "disabled by default" is a kill switch and not consent. It requires the user's go-ahead before the first off-machine call in a session. The "use Jev for every screening today" quote reaches me secondhand, through the launching agent. I can't treat an agent's relay as the user's consent, and the quote doesn't mention sending redacted text off-box.

I would not make the call on that basis alone. I would go ahead only if the consent shows up through the user's own channel, such as a permission prompt or a message from the user. The user is AFK, so otherwise I'd leave the Jev call queued and report that.

**Steps**

1. Classify the line locally, without printing the value. This is a read-only command on the staged hunk, with values masked:
   ```bash
   git diff --cached -U0 -- . | grep -E '^\+[A-Za-z_][A-Za-z0-9_]*=' | sed -E 's/^(\+[^=]+=).*/\1<REDACTED>/'
   ```
   I'd also note only the value's shape: empty, placeholder (`changeme`, `<...>`, `example`), or high-entropy/real-looking, plus its length class. I'd check `git check-ignore -v <file>` to see whether the `.env` file is gitignored.

2. Own verdict first. A real-looking secret in a tracked `.env` is a blocker whatever Jev says, and Jev's answer can't change that. I'd flag it for rotation and for removal from the commit.

3. Optional advisory call, only once consent is confirmed. It is a single `choice` item, so I can skip `reference.md` (the skill allows that for a quick call). The context carries the redacted summary only: file name, variable name, value class, gitignore status.
   ```bash
   GSD_PATH_JEV=1 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   python3 -B ~/.claude/skills/jev-fast-decision/scripts/jev_review.py <<JSON
   {"reviewed_head":"$(git rev-parse HEAD)",
    "items":[{"id":"envline","type":"choice",
      "instructions":"Does this added .env line look like a committed real credential or a harmless placeholder?",
      "context":"Added line in file .env: VAR_NAME=<REDACTED>; value is 40 chars, high-entropy, not a placeholder; file is not gitignored.",
      "criteria":{"real_secret":"value looks like a live credential","placeholder":"empty, example, or dummy value","non_secret_config":"ordinary non-sensitive setting"}}]}
   JSON
   ```

4. Key handling. The script reads `OPENCODE_API_KEY`, or `JEV_API_KEY`, or the Zen entry in opencode's `auth.json`. It does not read `TYPESAFE_API_KEY`. I would not echo that key or pass it along. I'd use the default Zen path. Pointing `JEV_API_URL` at TypeSafe's direct API with that key is a separate choice I'd leave to the user, because it's unverified here.

5. Reading the result. I'd check the status first. `disabled` or `unavailable` means I carry on with my own verdict, with no blind retry. On `ok`, anything below `JEV_MIN_CONFIDENCE` (0.7) or flagged `needs_fallback` is not acted on. A single answer, `placeholder` included, never auto-dismisses the finding.

The only thing I'd record is that a Jev advisory was or wasn't obtained.

**Skipped / risk:** I haven't seen the actual hunk, so the file name, variable name and value class in the example are placeholders. The main risk is that the real value is a live secret in a tracked file, which needs rotation whatever Jev says.
