# Decision table

Read before the first ladder call. "High" means a column's `fallback` is false (a column with
`forced: true` is neither high nor low: see Forced columns) — the
threshold of that backend's own row in the client's table (per-backend; the numbers are in
`jev-fast-decision`'s `reference.md` and `backends/`).
"Evidence" means what you verified live or what an earlier SPEC/CONTEXT locks — not what
seems plausible.

## Which answer wins

Work down the list; the first matching row decides. Columns are per backend: the local
backend's column (today `laya`) and one column per remote backend, in the client's table
order (today TypeSafe, then OpenCode Zen). A remote column is filled only when the local
rung was low or errored, or under `--second-opinion`.

**Forced columns.** A column with `forced: true` came from a truncated or oversized request
(the client's own flag, set whatever the probability). `decide.py` never names it in
`decided_by`, so the rows below apply unchanged: a forced answer never settles an item on its
own. It is advisory evidence for the row that decides, and it is logged `choice 0.NN
(forced)`; `(fb)` is only for `fallback: true` with `forced: false` (low confidence).

1. **The item would change or contradict a user-locked decision** (a decision from an earlier
   interactive CONTEXT or one the user stated): decide provisionally, flag `needs
   confirmation`, put it on the ledger. Never a silent override, whatever the models say. An
   answer that agrees with a user-locked decision is not flagged.
2. **`decided_by` is the local backend and the answer is consistent with the evidence** → take
   it. Log `choice 0.NN`.
3. **The local answer is high but contradicts the evidence** → `decide.py ladder --second-opinion`
   with the same item.
   - A remote answer that is high and on the evidence's side → override the local one. Log
     `**Laya overridden**` plus the backend that answered and the evidence.
   - The remote answer agrees with the local one → re-check the evidence (a stale doc? a
     misread?). Still contradicted → own reasoning, ledgered.
   - No high remote answer (the remote that answered is low, every remote errored, or none is
     consented) → own reasoning, ledgered. A low remote answer is final: the next remote is
     called only for items the earlier one errored on.
4. **The local rung is low, forced, errored or not called (Laya down) and `decided_by` is a remote backend** (TypeSafe or
   OpenCode Zen) → take that answer, unless it contradicts the evidence; then re-check the
   evidence and, still contradicted, own reasoning, ledgered.
5. **`decided_by` is `own_reasoning`** (every column that answered is low or forced, every called
   backend errored, a usable remote is not consented and is listed in `remote_available`, or
   there is no compatible client and `client_status` is set) → reason against the evidence
   yourself; ledger it when it blocks nothing.

An `{error}` column (for example TypeSafe `http_503` or OpenCode Zen `budget_exceeded`) is no
answer from that backend: it never settles an item, and it is logged as `error: <code>`.

Own reasoning is not a fallback of last resort in quality terms: it is the rung that reads the
actual code and docs. When the columns split (one backend each way, both low), the evidence
decides, and the log says so.

## Blocking × confidence

"Blocking" = another decision **in this run** cannot be made until this one is. An item that
blocks only later planning or execution is not blocking here; ledger it with `Blocks: <what>`.

- **Non-blocking, high** → decide and log.
- **Non-blocking, low** → decide provisionally, log "own reasoning", ledger it.
- **Blocking, high** → decide and log; dependent items follow.
- **Blocking, low** → first try to unblock: a live check, a scratch experiment, a second
  opinion. Still low → **stop** and ask the user that one question, with the ledger so far.
- **User-owned precondition** (land or shelve a branch, approve a real-token spike, consent)
  → ledger it with what it blocks; it is not a spec/discuss stop.

## Out-of-scope proposals

A model (or the analyzer) may recommend fixing something outside the phase's requirements (23
B12: Laya 0.97 "fix both" for a hooks bug next to the status-line config dir). Before deferring:
check feasibility against the confirmed architecture (size, which phases' decisions it would
change). Defer only with a real goal statement in `ROADMAP.md` §Backlog (`999.x`), and say in
the log why it is deferred.

## Ledger row

```
| Phase | Item | <backend> | <backend> | Provisional decision | Blocks |
| 23 | D-24 wizard preview | static_samples 0.35 (fb) | static_samples 0.66 (fb) | synthetic fresh cache in a temp XDG_CACHE_HOME; static samples cannot show gauge colors | nothing |
```

One `<backend>` column per backend that answered at least once in the run (the Phase 23 row
above is a labelled two-column instance).

The committed DISCUSSION-LOG marks the same row "**Own reasoning:** … (D-24, ledger)".
