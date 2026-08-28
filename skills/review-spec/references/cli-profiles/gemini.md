---
id: gemini
display_name: Gemini CLI
status: stub (carried over from the existing `gemini` skill's documented flags — not installed on the reference machine)
read_only: "partial (--sandbox per the gemini skill's own flag list, 'run in sandbox mode for isolation' — the container/no-write-to-real-tree characterization is unverified)"
detect: "which gemini"
last_verified: 2026-08-27
---

# gemini — reviewer profile (STUB — unverified live on this machine)

Per the existing `gemini` skill (`~/.claude/skills/gemini/SKILL.md`):
model via `-m/--model <MODEL>`; **background/non-interactive runs require
`--approval-mode yolo`** (the `default` approval mode hangs indefinitely in
a non-interactive shell — do not use it here); that skill also documents
`-s`/`--sandbox` as "run in sandbox mode for isolation" (no further detail
on what's isolated) — include it always here regardless, since `yolo`
alone grants unrestricted write access to whatever it runs against and
`--sandbox` is the only mitigation this profile can point to; confirm its
actual isolation scope live before marking this profile `status:
confirmed`.

```bash
gemini -m {model} --sandbox --approval-mode yolo {prompt}
```

(`{model}`/`{prompt}` are bare config `command` template placeholders,
unquoted; `{prompt}` is `shlex.quote`d by `render_reviewer_command`
before substitution, so never wrap it in your own quotes here.)

Quota/context-window introspection: unconfirmed syntax — research during
implementation.
