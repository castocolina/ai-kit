# Lane failure, ping, partial status and jev

Read this when a review keeps a round log, `$RUN_TMP_DIR/lanes.jsonl`: the active cross-AI path, from `size-review` on. Without a round log, read only the [Commands](#commands) section for SKILL.md Step 1's fold check (`check-fold-step` runs under `--no-cross-ai` too), and [jev classes and sizing](#jev-classes-and-sizing) with Commands when Step 4 classifies a fixer's escalated or skipped findings (`classify-disagreements`). `--no-cross-ai` and the session-default answers keep none: they run neither sizing nor ping, and their one report still passes the fold check (`merge-reports` with `--extra-findings` and one report). Every command below except `check-fold-step` takes the same `--cwd` as `resolve-reviewers`: the first document's root for a labelled cross-repo review. Python's config resolution in these commands never migrates; the runner's own legacy check runs as on every dispatch.

## Ping before a round

Before round 1, `ping-lanes` probes every chosen non-native lane of `reviewers.json` at once, even right after the probe-quota walk, each probe with its own timeout (30 s unless `--timeout` says otherwise). Before a later round it skips only a lane whose last state in the previous round is judged and whose judged event is younger than the quota cache TTL (one hour), and prints `ping <key>: fresh` for it; every other chosen lane is probed again. The round log decides that skip, never the quota file. A native entry is never probed and counts as available. Two entries with the same key are pinged once. Every probe the ping runs is written back to the quota file. A probe that raises an error records the lane `failed` with `real_error`; a probe still running at its deadline records `ping_timeout`.

A blocked lane is replaced by the next lane of the owner's review order that is not flagged `usage_limited`, not in the blocked lane's pool, not already chosen, failed or replaced in this round, and whose route dispatches; the candidate is pinged the same way, a candidate that fails is logged `failed` with its own reason and the next one is tried, and the replacement takes the blocked lane's index in `reviewers.json`. Only blocked lanes are replaced. A blocked lane with no replacement, or whose key is not in the review order (such as a judge lane file), is recorded `failed`, removed from `reviewers.json`, and the round runs on the lanes left.

Each lane prints one line: `ping <key>: ok`, `ping <key>: fresh`, `ping <key>: replaced by <new> (<reason>)` or `ping <key>: failed (<reason>)`. With no lane left, an empty `reviewers.json` included, `ping-lanes` exits 3, prints `ai-kit-spec: no lane left: <key> (<reason>), ...` on stderr (`ai-kit-spec: no lane left: (empty reviewers file)` for an empty one) and leaves `reviewers.json` unchanged; the review stops before any dispatch, so a round never runs on zero lanes. Exit 2 is a configuration error or an unreadable `reviewers.json`, round log or quota file: the review stops with its stderr line, before any dispatch.

## Flagged-lane switch

A lane the owner flagged `usage_limited` that fails after dispatch with reason `quota` switches once to its fallback: the first lane of the review order that is not flagged, not in the same pool, and not already chosen, failed or replaced in this round. `switch-lane` writes the fallback at the failed lane's index in `reviewers.json`, records the switch in the round log and prints `switched <old> -> <new>`; the orchestrator dispatches the new lane at once, in the same iteration. With no eligible fallback it prints `not switched <old>: <reason or state>`, exits 1 and the lane stays failed. Any other nonzero exit (2 on a bad `--round` or `--index`, an unreadable `reviewers.json` or round log, or a round log it cannot append to) also leaves the lane failed; the switch is logged before `reviewers.json` is rewritten, so a failed log write changes neither file.

Every other failure leaves the lane failed with its reason, and no other lane takes its place in that round: an unflagged lane never switches, on any reason; a refused lane (exit 65, reason `configuration`) never switches; billing, auth, permission and transient failures never switch. The owner decides from the partial report.

The switch is tried on any nonzero exit of a flagged lane, whatever the exit code, so it needs no exit-code rule of its own; `switch-lane` itself switches only a lane whose dispatch recorded reason `quota`. For reference, the runner's caller contract (ai-kit-cross-ai SKILL.md section 4) gives a quota stop on a router lane exit 75 with `retry_after_s=` after its soft series, and a quota stop off a router lane a bare exit 75 after one call, with `stopped=class`. `switch-lane` runs before the hard-tier and owner-stop handling of SKILL.md Step 1, so a switched lane schedules nothing. Run `switch-lane` for one lane at a time and re-read `reviewers.json` after each call, because each call rewrites the file.

A flagged lane with a pool is dispatched with `--pool <provider>:free`, so an ok run clears that pool's blocked-until record. Before a ping, and in the probe-quota walk, the record is read through the runner's `--blocked-status <pool>`: while its time is later than now the lane is skipped without a probe (replaced at a ping, unavailable in the walk); at or after that time one lane of the pool is tried once (a second failure renews the record under the runner's rule), and at a ping the pool's other chosen lanes wait for that result: probed when it succeeds, recorded `quota` when it fails (the walk records them unavailable with reason `quota`). No runner, no node, or a missing or malformed record reads as no record and never blocks a lane.

## Partial status

`merge-reports --lane-log <file> --round <N>` merges every lane that judged, and one lane's failure never cancels another lane's result. After the cross-ai merged line it prints `Judged by: <keys>` and, for each other lane, `; not judged: <key> (<reason>[, by <key>][, round <r>])`, keys in the owner's review order read from the configuration under `--cwd` (a key outside it follows in log order), never in `reviewers.json` order. A replaced lane shows `by <new key>`, and its replacement is among the judged lanes. A lane that failed, was replaced or never resolved in the round never turns judged because a report file is readable; only a later successful dispatch of that lane in the same round (a resume) supersedes its failed attempt: `dispatch-reviewer --lane-log` then appends a `chosen` event, and the merge judges its report.

| Outcome | Status line |
|---|---|
| every lane of every round judged, findings clean | `### Status: Approved` |
| a lane replaced, failed or never resolved in any round, findings clean | `### Status: Approved (partial)` |
| findings open | `### Status: Issues Found — fix and re-invoke` (the `Judged by:` line still names the lanes) |
| no lane judged | `### Status: Failure — not reviewed: <key> (<reason>), ...` (exit 1) |

A review with a replaced, failed or never-resolved lane is never reported as a clean run. Without `--lane-log` the merge keeps its fail-closed rule: any failed lane fails the whole merge.

## Reasons

One closed list, `REASONS` in `ai_kit_spec/error_classifier.py`, covers every ping, switch and lane failure. A failure the list cannot classify records `real_error`, never an empty reason. A missing runtime records `dispatch_unavailable`.

| Reason | Meaning |
|---|---|
| `quota` | usage or rate limit, already retried by the runner on a router lane |
| `auth` | authentication, entitlement or setup; never fixed by waiting |
| `timeout` | the invocation itself hung |
| `configuration` | malformed or missing command template, unknown model, or a pre-spawn refusal |
| `dispatch_unavailable` | the binary or the runner could not be invoked |
| `real_error` | anything else: a real, non-time-bound failure; the default |
| `capacity` | provider overloaded |
| `billing_or_access` | billing or entitlement |
| `git_timeout` | the runner's git work-tree check timed out, not the CLI |
| `replaced` | the lane was replaced in this round; its cause is recorded separately |
| `never_resolved` | the lane was chosen but left no readable report |
| `no_lane_left` | a ping or a switch found no lane to run |
| `ping_timeout` | a ping reached its deadline |

## jev classes and sizing

jev is advisory and never gates. It receives summaries only: never code, diffs, file contents, config values or secrets. A missing jev, an error, needs_fallback or a low answer takes today's path. A confident answer has no reason and a top score of at least 0.80.

`classify-disagreements` runs whenever the Fix Summary lists an escalated or skipped finding, whatever its Status line says, and when the loop reaches the cap with findings open: one item per finding, its severity taken from the matching report finding (a summary item with no single match goes to the owner), its title (at most 80 characters) and the fixer's stated reason (at most 160), with code spans, quoted strings, path-like or key=value tokens and long hex or digit runs dropped and secret shapes redacted. It runs with the reviewed root as `--cwd`.

| Class | Route |
|---|---|
| owner_decision | the owner, with jev's class shown as advisory |
| mechanical | one more fixer pass inside the iteration cap (the fixer prompt's `Mechanical re-pass:` line); at the cap, the owner |
| reviewer_wrong | MEDIUM or LOW only: listed as skipped with `jev: reviewer_wrong (<top>)` |

A CRITICAL, HIGH, cross-document or unheaded finding always reaches the owner, whatever jev says, and a non-confident answer reaches the owner. Each call appends its owner items to `$RUN_TMP_DIR/owner-items.json` through `--owner-out`, so an owner item from a classification after an Edits Applied summary still reaches the final Surface, whatever the outcome. Without jev the JSON output carries `"jev": "absent"` and every item goes to the owner: today's message. No item means no jev call. At most one re-pass per iteration: after a re-pass, a finding the fixer still escalates or skips goes to the user without a second classification.

`size-review` runs once, after `resolve-reviewers`. A deterministic signal in the plan (security, data, irreversible operations) forces two lanes (a security or irreversible word that a rule word such as "never" or "do not" forbids on its line, or a temp-dir cleanup, is no signal); when `reviewers.json` holds one, the first lane of the double-mode pick of `resolve-reviewers` (same quota file, routes, source vendor and cross-AI flag) that is not already in it joins it (with none, one lane stays and the sizing line says so). Otherwise jev, when present, picks one or two lanes and the reviewer among the candidate lanes (the lanes of `reviewers.json`, then the lane the double-mode pick would add), from plan facts only (task, file and step counts, a complexity bucket, the archetype and the framework). A confident answer applies (on one lane, the picked candidate reviews alone), a pick outside the candidates is discarded, and no jev or a low answer keeps the configured count and order. It prints `sizing: <lanes> lane(s): <reason>` and writes the round-0 sizing event.

## Commands

Substitute each path as its own double-quoted argument.

```bash
python3 "$TOOLS_PY" size-review --cwd "<CODEBASE_ROOT>" \
  --reviewers-json "$RUN_TMP_DIR/reviewers.json" \
  --doc "<DOC_PATHS entry>" --archetype "<ARCHETYPE>" \
  --framework "<framework id from Step 0.5, or none>" \
  --lane-log "$RUN_TMP_DIR/lanes.jsonl" --quota-path "$QUOTA_JSON" \
  --source-vendor "<the --source-vendor value passed to resolve-reviewers>" --cross-ai
```

Repeat `--doc` once per document; pass the same `--source-vendor` and `--cross-ai` as `resolve-reviewers` (without `--cross-ai` no second lane is ever added). A nonzero exit leaves `reviewers.json` unchanged: continue with the resolved list as it is and say "sizing failed: <stderr line>" in the Step 5 message; the ping still runs before round 1 and starts the round log.

```bash
python3 "$TOOLS_PY" ping-lanes --cwd "<CODEBASE_ROOT>" \
  --reviewers-json "$RUN_TMP_DIR/reviewers.json" \
  --lane-log "$RUN_TMP_DIR/lanes.jsonl" --round <N> --quota-path "$QUOTA_JSON"
```

```bash
python3 "$TOOLS_PY" switch-lane --cwd "<CODEBASE_ROOT>" \
  --reviewers-json "$RUN_TMP_DIR/reviewers.json" --index <this entry's index> \
  --lane-log "$RUN_TMP_DIR/lanes.jsonl" --round <N>
```

```bash
python3 "$TOOLS_PY" check-fold-step --doc "<DOC_PATHS entry>" \
  --framework "<framework id from Step 0.5, or none>" --archetype "<ARCHETYPE>" \
  >> "$RUN_TMP_DIR/iter<N>-fold.md"
```

Run it once per document; the iteration's first call starts the file empty (an iteration re-entered after a resume starts it empty again). Exit 2 means the document was not checked: stop the review with that stderr line, never a clean approval.

```bash
python3 "$TOOLS_PY" classify-disagreements --cwd "<CODEBASE_ROOT>" \
  --report "<EFFECTIVE_REPORT_PATH>" --fix-summary "$RUN_TMP_DIR/iter<N>-fix.md" \
  --iteration <N> --cap <cap> --owner-out "$RUN_TMP_DIR/owner-items.json"
```

At the cap with no fixer in this iteration, drop `--fix-summary` and add `--cap-reached`. Without `TOOLS_PY`, or on a nonzero exit, keep today's path: every finding goes to the owner.

```bash
python3 "$TOOLS_PY" merge-reports --cwd "<CODEBASE_ROOT>" --doc-paths "<DOC_PATHS>" \
  --lane-log "$RUN_TMP_DIR/lanes.jsonl" --round <N> \
  --extra-findings "$RUN_TMP_DIR/iter<N>-fold.md" \
  "<key1>=$RUN_TMP_DIR/iter<N>-<key1>.md" "<key2>=$RUN_TMP_DIR/iter<N>-<key2>.md" \
  > "$RUN_TMP_DIR/iter<N>-merged.md"
```

Drop `--extra-findings` when the fold file is empty or absent, and `--cwd`, `--lane-log` and `--round` when no round log exists; with one entry, pass its one key=path.

`dispatch-reviewer` takes `--lane-log "$RUN_TMP_DIR/lanes.jsonl" --round <N>` after the flags of SKILL.md Step 1: a dispatch that ends with a reason appends a `failed` event for that lane, and a successful dispatch appends a `chosen` event, which supersedes an earlier failed attempt of the same lane in the same round (a resumed lane), so the merge judges its report.

## Evidence

- The flagged-lane switch, the ping cadence, the partial status, jev's disagreement classes, review sizing and the blocked-until reading at selection follow the owner's answers to the lane-failure question batch.
