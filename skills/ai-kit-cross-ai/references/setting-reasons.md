# Setting reasons and model preflight

The model preflight and the reason codes of the runner's `cross-ai: setting` lines, as the
ai-kit-cross-ai skill's Call settings and Settings report use them ([`../SKILL.md`](../SKILL.md)).
`--describe` prints the same closed list of reasons.

## Model preflight

An id that fails the runner's syntax floor is refused as `usage` (exit 2) before any spawn, and an unusual but valid shape only prints a note; past those, the live preflight checks it: when the runtime's model listing succeeds, an id missing from it ends the call with `bad_model` (exit 69) before any model runs. For a runtime whose ids carry a variant suffix (opencode's `#<variant>`) the preflight checks the id without the suffix and prints `cross-ai: <runtime> preflight checks <base id>; the suffix <suffix> is not validated`: a passing preflight never validates the suffix, so read the final `AIKIT-XAI` line for that. When the listing fails the runner prints `cross-ai: <runtime> model list unavailable (<reason>); not preflighted` and runs the id as given, and a runtime with no listing command runs it unchecked.

## Reasons

The reasons, a closed list that `--describe` also prints:

| Reason | Meaning |
|---|---|
| `no_form` | the runtime has no flag or id form for the setting |
| `id_carries` | the model id already holds a value, and it wins |
| `unverified_form` | a form is known but not verified, so it is not fed |
| `mode_forbids` | the role's confinement forbids it (a session resume in codex review or with `--codex-sandbox`, a pi skill by name, MCP in a review profile that turns MCP off) |
| `no_slot` | an argv-file lane whose file has no placeholder for it |
| `recorded_only` | an escalation flag: echoed, never acted on |
| `no_provider_form` | the runtime's model id has no provider part |
| `bad_value` | a context label outside the form's value kind |
| `no_herdr` | `--host auto` while herdr is not available |
| `host_failed` | herdr failed; read the `cross-ai: host:` line: `the lane runs headless` (a confirmed failure before the start, one headless run follows) or `the lane may have started, so it is not rerun` (an unclear start, no rerun); the outcome is the last `AIKIT-XAI` line, never a reason to retry |
