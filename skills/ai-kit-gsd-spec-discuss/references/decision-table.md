# Decision table

Read before the first ladder call. "High" means the winning probability `top` ≥ 0.7 and
`fallback` false (the jev client's own threshold). "Evidence" means what you verified live or
what an earlier SPEC/CONTEXT locks — not what seems plausible.

## Which answer wins

Work down the list; the first matching row decides.

1. **The item touches a user-locked decision** (an earlier interactive CONTEXT, a decision the
   user stated): decide provisionally, flag `needs confirmation`, put it on the ledger. Never a
   silent override, whatever the models say.
2. **Laya high, consistent with the evidence** → take it. Log `choice 0.NN`.
3. **Laya high, contradicting the evidence** → `decide.py ladder --second-opinion` with the
   same item.
   - TypeSafe high and on the evidence's side → override Laya. Log `**Laya overridden**` plus
     the evidence.
   - TypeSafe agrees with Laya → re-check the evidence (a stale doc? a misread?). Still
     contradicted → own reasoning, ledgered.
   - TypeSafe low → own reasoning, ledgered.
4. **Laya low or errored, TypeSafe high** → take TypeSafe, unless it contradicts the evidence
   (then row 3's logic applies to TypeSafe).
5. **Both low, or no backend at all** → own reasoning against the evidence. Ledger it when it
   blocks nothing.

Own reasoning is not a fallback of last resort in quality terms: it is the rung that reads the
actual code and docs. When the models split (Laya one way, TypeSafe the other, both low), the
evidence decides, and the log says so.

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
| Phase | Item | Laya | TypeSafe | Provisional decision | Blocks |
| 23 | D-24 wizard preview | static_samples 0.35 (fb) | static_samples 0.66 (fb) | synthetic fresh cache in a temp XDG_CACHE_HOME; static samples cannot show gauge colors | nothing |
```

The committed DISCUSSION-LOG marks the same row "**Own reasoning:** … (D-24, ledger)".
