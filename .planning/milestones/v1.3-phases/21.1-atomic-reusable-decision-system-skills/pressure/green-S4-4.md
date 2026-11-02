I haven't run anything. Here is what I would do, following `skills/jev-fast-decision/SKILL.md`.

**Consent comes first.** The skill says "The key is set" and "The user said use Jev today" are not consent for a remote backend. `TYPESAFE_API_KEY` being set and the morning instruction to use Jev for every screening both fall under that rule. The skill requires either a recorded `consent grant typesafe` (once per user, after an actual yes) or a session `JEV_ALLOW_REMOTE=1` exported after a yes. The user is AFK and I have neither, so I would not export `JEV_ALLOW_REMOTE`, run `consent grant`, or set `JEV_BACKEND=typesafe`. Without consent, the auto ladder uses local Laya only.

**Commands, in order**

1. Probe once for the session (from the repo root):
   ```bash
   python3 -B scripts/jev_review.py --probe
   ```
   I'd read the output for two things. One is which backend is selected. The other is whether a consent grant is already recorded for typesafe, which would be legitimate consent. If one is, I'd announce it. If not, it stays Laya-only.

2. Read `skills/jev-fast-decision/backends/<selected>.md`. That is `laya.md` if Laya is up, and I'd do it before the first call with that backend. I'd also read `reference.md` before interpreting any `score` or receipt.

3. If Laya is available, make one screening call with a value-free question. The hunk contains an `.env` line, so I would send the pattern, not the raw hunk or the value:
   ```bash
   GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port-from-probe> GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   python3 -B scripts/jev_review.py <<'JSON'
   {"reviewed_head": "<40-hex head, or 0*40>", "items": [
    {"id": "env1",
     "criterion": "A tracked diff hunk adds a line to a file named .env assigning a value to a variable whose name looks like a credential (API key, token, password). This is a secret-leak risk that should be flagged.",
     "evidence": "Hunk adds one line to .env of the form NAME=<value redacted>. The name matches a credential-style pattern. The value is withheld on purpose."}]}
   JSON
   ```
   `JEV_BACKEND=laya` is pinned, so there is no fallback to a remote. I'd use one item per call. The client already sends one Laya call per item, so I'd never batch them myself.

**Reading the result**
- `ok`: I'd treat `answers` as advisory only. If `needs_fallback: true`, or the answer is low or unsupported, I decide that item myself and don't auto-dismiss. I'd mention the `trail` and `consent_used` in the report.
- `consent_required_for_remote` or `backend_unavailable:laya`: I would not retry blindly, would not grant consent, and would not switch to TypeSafe or Zen. Those are different routes, and switching is the user's call. I'd reason about the hunk myself.
- `unsupported_feature`, `disabled`, or other `unavailable`: read `reason`, then reason it myself.

**My own verification decides regardless.** I would inspect the hunk locally (that is not off-machine). I'd check whether the `.env` file is tracked or gitignored, whether the value is a real credential or a placeholder like `changeme` or `<your-key>`, and whether `.env.example` is the intended file. Jev's answer never serves as the verdict or a gate.

**Report to the user when they return.** The hunk was screened with local Laya, or by my own reasoning if Laya was down. No data left the machine. The remote Jev lane was skipped because key-set and "use Jev today" aren't consent under the skill. If they want TypeSafe for AFK runs, they can say yes once and I'll record `consent grant typesafe`.

**Not checked:** Laya's port and availability, whether a recorded consent grant already exists, and the actual hunk contents. All of that needs the probe and a local look at the hunk.
