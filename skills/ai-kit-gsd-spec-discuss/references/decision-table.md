# Decision table

Read before the first jev request. "High" means jev's answer is confident (`needs_fallback`
false); "low" means `needs_fallback` true. The confidence bands are jev's to define (its
SKILL.md and reference.md); this table does not restate them.
"Evidence" means what you verified live or what an earlier SPEC/CONTEXT locks — not what
seems plausible.

## Which answer wins

Work down the list; the first matching row decides. jev gives one advisory answer per item, and
you use that answer as evidence, never as the decision.

1. **The item would change or contradict a user-locked decision** (a decision from an earlier
   interactive CONTEXT or one the user stated): decide provisionally, flag `needs
   confirmation`, put it on the ledger. Never a silent override, whatever jev says. An
   answer that agrees with a user-locked decision is not flagged.
2. **jev's answer is confident and consistent with the evidence** → take it provisionally.
   Log `choice 0.NN`.
3. **jev's answer is confident but contradicts the evidence** → ask jev for a second opinion on
   the same item (its SKILL.md says how).
   - A confident second opinion on the evidence's side → take it, log it as
     `choice 0.NN (second opinion)`, and log that the first answer was **jev overridden** by the
     evidence.
   - A second opinion that agrees with the first → re-check the evidence (a stale doc? a
     misread?). Still contradicted → own reasoning, ledgered.
   - No confident second opinion (low, `needs_fallback`, an error or no answer) → own reasoning,
     ledgered. A low answer is final: do not ask again for a better one.
4. **jev gave no confident answer** (`needs_fallback`, an error or no answer) → own reasoning
   against the evidence. Log the low answer as `low 0.NN`, or the error as `error: <code>`. The
   answer is one input, not the decision.
   - A forced answer (`forced` true: the item or its request passed jev's size guard, so the answer is no real judgment) → own reasoning, logged `forced`; next time, shorten the item or split the request.
5. **jev is not installed or was not asked** → own reasoning against the evidence; ledger it
   when it blocks nothing.
   - jev reports `no_client` (no jev client found) → this row; log `not installed`.
   - jev reports `incompatible_client` (the client found is too old for jev's ladder) → this row; log `error: incompatible_client`, and tell the user to re-run the ai-kit installer.

Own reasoning is not a fallback of last resort in quality terms: it is the step that reads the
actual code and docs. When jev's first answer and its second opinion split, the evidence decides,
and the log says so.

## Blocking × confidence

"Blocking" = another decision **in this run** cannot be made until this one is. An item that
blocks only later planning or execution is not blocking here; ledger it with `Blocks: <what>`.

- **Non-blocking, high** → decide and log.
- **Non-blocking, low** → decide provisionally, log "own reasoning", ledger it.
- **Blocking, high** → decide and log; dependent items follow.
- **Blocking, low** → first try to unblock: a live check, a scratch experiment, a second
  opinion. Still low → **stop** and ask the user that one question, with the ledger so far.
- **User-owned precondition** (land or shelve a branch, approve a real-token spike, an approval
  a skill asks for) → ledger it with what it blocks; it is not a spec/discuss stop.

## Out-of-scope proposals

A model (or the analyzer) may recommend fixing something outside the phase's requirements (23
B12: jev 0.97 "fix both" for a hooks bug next to the status-line config dir). Before deferring:
check feasibility against the confirmed architecture (size, which phases' decisions it would
change). Defer only with a real goal statement in `ROADMAP.md` §Backlog (`999.x`), and say in
the log why it is deferred.

## Ledger row

```
| Phase | Item | jev | Provisional decision | Blocks |
| 23 | D-<n> wizard preview | low 0.35 | synthetic fresh cache in a temp XDG_CACHE_HOME; static samples cannot show gauge colors | nothing |
```

The `jev` column holds the answer in the cell format of `log-formats.md` (`choice 0.NN`,
`low 0.NN`, `error: <code>`), or `not installed`.

The committed DISCUSSION-LOG marks the same row "**Own reasoning:** … (D-<n>, ledger)".
