I can't give exact commands yet, because your message doesn't include the decision or task to send to TypeSafe. I also haven't opened the TypeSafe or jev helper, since I was told not to load skills. So the helper's path and flags below are things I'd look up, not things I know.

**What I'd do**

1. **Treat Zen as the route.** I'd read "use TypeSafe, Zen works" as: call TypeSafe's Jev model through OpenCode Zen. That route doesn't need `TYPESAFE_API_KEY`. I would not set, export or ask for that variable, and I wouldn't print or copy any key. Zen credentials stay wherever opencode keeps them, and the helper reads them itself.

2. **Find the helper without running it.** From the worktree root:
   - `rg -l -i "jev|typesafe" --glob '!.planning/**' --glob '!tmp/**'`
   - `fd 'decide.py|jev' .` (or the skill's `scripts/` directory)
   - Then I'd read its `--help` text or argparse block in the source, so I use the real flags and the Zen route selector instead of guessing them.

3. **Run one short foreground probe.** I'd send a single typed question (yes/no, a choice, or a score) to the helper with the Zen route selected. I'd use a short timeout and watch whether output arrives. That tells me whether it's slow or actually broken before I retry anything. Your memory notes say to do this.

4. **Check the exit code and response.** If Zen returns a billing or 403 error, I'd report it as a Zen problem. I wouldn't retry blindly or fall back to the direct TypeSafe route, because that route has no key.

5. **Use the answer as advice only.** A Jev answer informs my next step. I'd still check the claim myself and wouldn't treat it as satisfying a gate.

**What I need from you**

- What is the question or decision to send? If it's a batch, which items?
- If the helper has no Zen route, I'd stop and tell you rather than quietly going another way.

This involves no repo edits, so no GSD workflow is needed.

**Not checked:** I haven't confirmed the helper's location or flags, or that Zen is currently within budget (your memory notes say it was out earlier, and you say it works now).
