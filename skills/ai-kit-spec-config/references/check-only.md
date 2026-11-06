# `--check-only` branch

Read this only when `--check-only` was passed. It reports reviewer availability and stops: no
config write, no runtimes snapshot, no trust record. `$TOOLS_PY` and `$SCRATCH` are the literal
paths SKILL.md Step 0 printed.

Report which CLIs are installed (Step 1's `detect-runtimes` output). Then read the target config
file (`~/.config/ai-kit/review-spec.toml` if `--global` was passed, else
`./.aikit/review-spec.toml` by default) and note each `[[reviewers]]` entry's `key`/`runtime` (or
legacy `cli`) if it exists. (This is a raw on-disk read only, not `cfg_resolve`'s merged view.)
If any entries exist, probe their **quota availability** — the core purpose of `--check-only` —
using a throwaway path:

```bash
python3 "$TOOLS_PY" probe-quota --cwd "$(pwd)" --no-save-runtimes --quota-path "$SCRATCH/quota.json"
```

`probe-quota` makes live probe calls to each configured CLI (same mechanism as dispatch time),
but "no writes" means nothing is persisted to ai-kit's caches or config: the throwaway
`--quota-path` keeps quota rows out of the real `quota.json`, and `--no-save-runtimes` keeps
`probe-quota`'s routing step from writing the runtimes cache (a cold or stale cache is rebuilt in
memory only, and a targeted refresh is never written back).

`probe-quota` has no `--local`/`--global` flag — it always runs the full `cfg_resolve` merge, so
output may include keys from both local and global configs. Report each `key`'s `available`
boolean only for keys that also appeared in the raw-read listing above — drop any extra the merge
surfaced — so both parts describe the same set of reviewers.

Three edge cases: (1) if `--global` was passed but a local config with `strategy = "local-only"`
exists, the merge returns only local entries, shadowing the global keys the raw read listed; (2)
`probe-quota` only probes keys reachable from `policy.ladder`; (3) an untrusted local file is
ignored entirely (stderr prints `ignoring untrusted project-local config`), so none of its keys
are probed. For any raw-read key with no match in probe output, report `available: unknown (not
probed — absent from policy.ladder, shadowed by local-only strategy, the local config is
untrusted, a native/session-default entry that is never externally probed, or a permanent skip
route the probe output names)` rather than silently dropping it or guessing. When the untrusted
line appears, relay it and print the `trust-local --cwd <project root> --show` command for the
user to run later — `--check-only` never runs the trusting `trust-local` form, because that writes
a trust record.

Then run the stale-provider report (read-only; exits 0 whatever it finds, so it never stops the
check):

```bash
python3 "$TOOLS_PY" check-providers --cwd "$(pwd)"
```

Show its lines to the user as they are. A `warning:` line is a finding to relay, not an error.
Keep the certainty the line states: a warning ending `(unconfirmed: ...)`, a
`served providers: config file only; ...` line or a `served providers: not checked: ...` line is
shown with that wording, never upgraded to "verified" or called "stale".

Then `rm -rf "$SCRATCH"` and stop; do not save the runtimes snapshot, matching this skill's
`--check-only` contract.
