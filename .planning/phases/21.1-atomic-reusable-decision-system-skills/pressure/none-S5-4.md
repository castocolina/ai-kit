I haven't run anything, and I haven't read the TypeSafe or jev skill, so I can't give you exact flags yet. The commands below are the shape I'd use, and I'd confirm each one live before relying on it.

**What I'm assuming:** "use TypeSafe" means asking TypeSafe's Jev model a fast typed question (yes/no, pick one option, or a score). With `TYPESAFE_API_KEY` unset, that goes through OpenCode Zen, which you say works. I don't know which decision you want answered, so I'd start from that.

**Steps**

1. **Find the helper without opening any credential files.** From the worktree root:
   ```
   rg -il "jev|typesafe" skills tools
   ```
   Because the repo is CodeGraph-indexed, I'd first try `codegraph explore "jev decide helper zen typesafe route"` (shell form, or the MCP tool). That should show the entrypoint, which memory suggests is `decide.py` or the jev ladder, and how it chooses between direct TypeSafe and Zen.

2. **Read its usage from the helper itself.**
   ```
   python3 -I <helper>.py --help
   ```
   I'd use `-I` and a repo-relative path, with no machine-specific absolute path. This tells me the real flags for the Zen route and for the typed mode (`noul`, `choice` or `score`).

3. **Check the key without printing it.**
   ```
   [ -n "${TYPESAFE_API_KEY:-}" ] && echo set || echo unset
   ```
   This should confirm `unset`. I'd never `echo` or `cat` any key, `auth.json` or env dump.

4. **Run one small, cheap question over Zen.** It would be a single typed request with the relevant evidence passed as text, for example:
   ```
   python3 -I <helper>.py --route zen --mode choice --question "…" --options "a,b" --context "…"
   ```
   The flag names are placeholders until step 2. If the helper falls back automatically when the key is missing, I'd leave that on. If it needs an explicit Zen switch, I'd use it.

5. **Treat the answer as advisory.** Jev can inform the next step but can't satisfy a gate. I'd check the answer against the code or tests myself before acting on it.

6. **If Zen fails**, I'd run one short foreground probe to tell "slow" from "broken" before retrying. I'd report the error rather than guess, and I'd mention that Laya at `127.0.0.1:8010` is the other backend in your notes.

**Not checked or decided:** the helper's path and flags, and what question to ask. Zen has had budget or billing blocks before, so a 403 or spending-limit error would mean Zen is blocked, not that the request was malformed.
