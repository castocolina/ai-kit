# `--check-only` branch

Read this only when `--check-only` was passed. It reports reviewer availability and stops: no
config write, no runtimes snapshot, no trust record. `$TOOLS_PY` and `$CLI_PROFILES_DIR` are
the literal paths SKILL.md Step 0 printed, `$SCRATCH` is made only by the probe below, and
`<project root>` is the one path
Step 0 resolved (`./.aikit/config.toml` below means `<project root>/.aikit/config.toml`).

Report which CLIs are installed (Step 1's `detect-runtimes` output). Then read the target config
file (the user `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml` if `--global` was passed, else
`./.aikit/config.toml` by default) and note each `[[lanes.review]]` and `[[lanes.execute]]` entry's `key`/`runtime` (or
legacy `cli`) with its role, if it exists. (This is a raw on-disk read only, not `cfg_resolve`'s merged view.) When that
config.toml has no `[lanes]` table and an old `review-spec.toml` sits beside it, report that the old roster migrates on
the next command that reads it (unless a lane names a removed runtime: such a roster is never migrated by a read, and its
lanes are re-saved through the full setup), and list its `[[reviewers]]` entries (read-only).
Whatever the raw read found (none in this file can still mean lanes in the other layer), the
lanes' **quota availability** is the core purpose of `--check-only`, but the
probe is a live call to each CLI, so check write risk first, exactly as SKILL.md Step 2.5 does,
over exactly the keys `probe-quota` will spawn for. That set comes from the merged view (project
over user) and both roles' orders, not the raw read above, so always list it first. This snippet makes the same resolve and
route calls `probe-quota` makes before it probes, with no model call and no write. When it prints
an empty list, nothing would be probed: say so, report each raw-read key as `available: unknown`
with the reasons the edge cases below list, and skip to the stale-provider report:

```bash
python3 -c "
import json, sys
sys.path.insert(0, sys.argv[1])
from ai_kit_spec import routing
from ai_kit_spec.cli import CliDeps, _probe_lanes, _route_reviewers
from ai_kit_spec.config_io import cfg_resolve
deps = CliDeps()
config = cfg_resolve(sys.argv[2], deps.env_fn(), migrate=False)
lanes = _probe_lanes(config, 'both')
routes = _route_reviewers(config, deps, persist=False, lanes=lanes)
keys = routing.probe_keys([e['key'] for e in lanes], routes)
by_key = {e['key']: e for e in lanes}
print(json.dumps([{'key': k, 'runtime': by_key[k].get('runtime'), 'model': by_key[k].get('model', ''), 'command': by_key[k].get('command'), 'custom': 'command' in by_key[k]}
                  for k in keys if k in by_key]))
" "$(dirname "$TOOLS_PY")" "<project root>"
```

Both paths reach Python as arguments, never inside its source, so a quote in a path cannot break
it. Limit: the snippet imports the review module's private helpers (no subcommand prints this list
yet), so a rename there breaks it. When the snippet exits nonzero or prints no JSON list, run no probe: show its stderr and report
every raw-read key as `available: unknown (the probe preflight failed)`, then continue with the
stale-provider report.

For each printed entry with a `runtime`, read `read_only` from `$CLI_PROFILES_DIR/<runtime>.md`
(only those profiles). An entry whose profile says `read_only: unconfirmed`, a runtime with no
profile file and a custom entry (`custom: true`) all run with the CLI's normal write permissions.
The probe starts each from a private temporary directory, not the working tree, but nothing confines
those permissions to it; the throwaway paths below keep ai-kit's caches clean, not your files. When
any such entry exists, use `AskUserQuestion` before any live call: "Note: `<key>` (`<model>` through `<runtime>` or `<command>`) have no
confirmed read-only invocation — the quota probe runs them from a private temporary directory with
their normal write permissions, which nothing confines to that directory. Run the probe now, or skip it?" — with "skip the probe" first/default.
List every such entry with the model and command the snippet printed, so the owner sees the exact lane the probe runs.
`probe-quota` cannot probe a subset, so the answer covers the whole probe. On skip, run no
`probe-quota` call and report every raw-read and printed key as
`available: unknown (not probed — the write-risk probe was declined)`, then continue with the
stale-provider report below. The snippet and `probe-quota` resolve separately, so on yes first run
the snippet again: when its list differs from the one the owner saw (an added key, or another
runtime, model or command for a key), show the new list and ask again instead of probing. Limit: the re-run compares the printed key,
runtime, model and command only; a custom command's placeholder filled from another lane field can
change the launched argv without changing the list, so this check cannot prove the probe runs
exactly what the owner saw. On yes
with an unchanged list, or when every printed entry is confirmed read-only (or none was printed),
probe using a throwaway path:

```bash
SCRATCH="$(mktemp -d -t ai-kit-spec-config-XXXXXX)"; printf '%s\n' "$SCRATCH"
python3 "$TOOLS_PY" probe-quota --cwd "<project root>" --role both --no-save-runtimes --no-migrate --quota-path "$SCRATCH/quota.json"
```

`probe-quota` makes live probe calls to each configured CLI (same mechanism as dispatch time),
but "no writes" means nothing is persisted to ai-kit's caches or config: the throwaway
`--quota-path` keeps quota rows out of the real `quota.json`, and `--no-save-runtimes` keeps
`probe-quota`'s routing step from writing the runtimes cache (a cold or stale cache is rebuilt in
memory only, and a targeted refresh is never written back). It does not make the probe side-effect
free: each table-runtime probe runs through the cross-AI runner, which keeps its own run state under
`${XDG_STATE_HOME:-~/.local/state}/ai-kit/` and may clear a dead run's leftovers there, and the CLI
behaves as its profile says; say so when reporting the probe. `--no-migrate` reads an old roster read-only: it is used in memory, `migration pending` (or `migration held`, when it names a removed runtime) is printed, and nothing is written.

`--role both` probes the review order, then each execute lane not already listed (the execute order first, then the other execute lanes the execute selector can still pick), once per key. A key that names different lanes in the review and execute roles is probed as its review lane, and `probe-quota` prints one line naming the key and saying its execute lane is not probed; relay that line and suggest renaming one of the two lanes. Report such a key per role: its review lane takes the probed `available` value, and its execute lane is `available: unknown (not probed — the key names a different review lane)`, even though the key appears in the output. A lane marked `usage_limited = true` is probed like any other. Quota records are reused for an hour only within one quota file; this check passes a throwaway `--quota-path`, so every `--check-only` run spends one probe per probed lane, including part of a usage-limited lane's allowance.

`probe-quota` has no `--local`/`--global` flag — it always runs the full `cfg_resolve` merge, so
output holds the keys printed above, from both local and global configs. Report each probed
`key`'s `available` boolean, and mark a probed key missing from the raw-read listing
`(from the merged view)`, so the user sees which reviewers came from the other layer.

Three edge cases: (1) if `--global` was passed but a local config with `strategy = "local-only"`
exists, the merge returns only local entries, shadowing the global keys the raw read listed; (2)
`probe-quota` probes a review lane only when the review order names it (`[lanes.policy.review]` `ladder`, or a shared `[lanes.policy]` `ladder` read for the review lanes), and every execute lane; (3) a project file whose command-bearing lanes are untrusted is
ignored entirely (stderr prints `ignoring untrusted project-local config`), so none of its keys
are probed. For any raw-read key with no match in probe output, report `available: unknown (not
probed — a review lane absent from the review order, shadowed by local-only strategy, the local config is
untrusted, a native/session-default entry that is never externally probed, or a permanent skip
route the probe output names)` rather than silently dropping it or guessing. When the untrusted
line appears, relay it and print the `trust-local --cwd <project root> --show` command for the
user to run later — `--check-only` never runs the trusting `trust-local` form, because that writes
a trust record.

Then run the stale-provider report (read-only; exits 0 whatever it finds, so it never stops the
check):

```bash
python3 "$TOOLS_PY" check-providers --cwd "<project root>"
```

Show its lines to the user as they are. A `warning:` line is a finding to relay, not an error.
Keep the certainty the line states: a warning ending `(unconfirmed: ...)`, a
`served providers: config file only; ...` line or a `served providers: not checked: ...` line is
shown with that wording, never upgraded to "verified" or called "stale".

Then, when the probe made `$SCRATCH`, `rm -rf "$SCRATCH"`, and stop; do not save the runtimes snapshot, matching this skill's
`--check-only` contract.
