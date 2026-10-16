---
id: codex
display_name: OpenAI Codex CLI
status: confirmed
read_only: "confirmed (--sandbox read-only)"
detect: "which codex"
last_verified: 2026-08-28
source: codex --help + live smoke test against a real installed codex CLI
---

# codex — reviewer profile

A codex reviewer stores the pair `runtime = "codex"` and the bare `model`, plus
optional `effort` and `service_tier` knobs. It stores no `command`. Dispatch
runs the pair through the supervised runner, which builds the argv.

Non-interactive: `codex exec`. Model: `-m <model>`. Reasoning effort and the
service-speed tier are separate knobs (`--codex-effort`, `--codex-service-tier`
on the runner), never a suffix on the model id. Confirmed live 2026-08-29:
`codex exec -m gpt-5.6-sol-high` is rejected; the pair is `model = "gpt-5.6-sol"`
with `effort = "high"`.

**Review** runs read-only:

```text
codex exec --sandbox read-only --skip-git-repo-check -C <cwd> -m <model>
```

The runner adds `--json`, an output file and `-` (the prompt on stdin).

**Exec has two branches, and only one of them confines writes.**

- ai-kit's own exec dispatch passes `--codex-sandbox workspace-write`. The
  runner then uses `--sandbox workspace-write` instead of the bypass, so writes
  stay inside the target dir plus `/tmp` and `$TMPDIR`, which workspace-write
  always allows. Whether that sandbox also allows writes inside `.git` is
  unverified.
- A runner call that does not pass the flag (GSD's own hook, and any other
  caller that leaves the default) uses `--dangerously-bypass-approvals-and-sandbox`.
  That branch has no confinement.

The prompt arrives on stdin (`-`), so a table-runtime entry has no `{prompt}`
placeholder.

**Quota probe — confirmed live**: a low-effort/fast-tier call against an
exhausted quota returns a usage-limit error. Availability is classified from
the runner's `AIKIT-XAI status=` line, not from a dedicated quota subcommand.
