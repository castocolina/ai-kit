# Model ids for codex and cursor, and custom entries (spec-config Step 2.4)

Read this only when a chosen lane is on codex or cursor, or is a custom entry for a CLI outside the
runtime table. A table runtime still stores only `runtime`, `model` and its knobs (SKILL.md Step 2.4).

## codex: the bare model id

**codex's `model` field must be the BARE model id — never suffix an effort/tier tag onto it.**
A live check confirmed that codex rejects an effort suffix on the model id; shown here with invented
placeholders: `codex exec -m placeholder-model-1-high` is rejected, and the correct pair is
`model = "placeholder-model-1"` with `effort = "high"` stored on the entry (the lane passes it to the
runner as `--effort`, and the runner writes codex's own effort setting, not in the model string).
For cursor below, fast and context sit in the model-id string and the runner composes the lane's
effort into it at dispatch — never carry that pattern over to codex.

codex has no `models`/`list-models` subcommand (confirmed via `codex --help`), but `detect-runtimes`
enumerates its user-selectable models from the real binary's `codex debug models` output (entries
with `visibility: "list"` only) into `clis.codex.models` — when `$RUNTIMES_JSON` carries that list,
pick the model id from it. When it does not (an older codex without `debug models`, or an
enumeration that failed and degraded to no list), treat the exact current model id as unfamiliar and
research it per SKILL.md Step 2.2's rule before proposing it to the user, rather than typing a
remembered id from training knowledge.

## cursor: fast and context inside the id

For `cursor` specifically, fast and context are encoded in the model id itself, not a runner flag —
ask the user for either, then:

```bash
python3 "$TOOLS_PY" build-model-id --runtime cursor --base-model <id> \
  [--fast true|false] [--context <c>]
```

and use the printed id as this entry's `model` field (unchanged from the plain id when no overrides
were given). `build-model-id` stays for these cursor bracket ids. Leave `--effort` out: the lane's
`effort` key is merged into the id's bracket at dispatch, and an id that already carries an effort
keeps it and prints an `ignored:` line for a different lane effort.

## A CLI outside the runtime table: the custom entry

A CLI this catalog of profiles hasn't caught up with yet, a brand-new provider, or a fully custom
local script uses the escape hatch: a custom entry with a hand-written `command` and no `runtime`,
trust-gated like any custom command. A lane entry's `command` field accepts a plain template with
just `{model}`/`{prompt}` as placeholders. Hand-written templates are split into argv the way a shell
splits words; `{model}`, `{prompt}`, and any `extra` fields each fill a whole argument (`{prompt}`
needs no quoting). Shell operators (`;`, `|`, `&&`, `>`), `$` expansions, and backticks are rejected
with an error naming the reviewer — wrap a pipeline in a script and register the script. Any
CLI/script that can be invoked non-interactively with a model and a prompt can become a reviewer
entry; it never runs as an executor (`references/wizard-flow.md` step 6).
