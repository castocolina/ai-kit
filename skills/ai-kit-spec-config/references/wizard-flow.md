# Wizard question flow (spec-config Step 2.2)

This is the one place the question order lives. Ask every question of the owner in the owner's own session, never in a herdr pane or by another agent, with the host's question tool or numbered plain text (SKILL.md, Host tools). Review and execute stay separate in every question. No lane configuration is written before both sets are confirmed, and Step 3 writes only the lanes chosen here; the catalog step and the test calls still record catalog and usability data as before. Each `- Run:` command below runs as `python3 "$TOOLS_PY" <command>`; `<catalog>` is the literal path Step 1.5 printed.

Skipping the flow reproduces landmines this wizard already hit: guessing a codex id (`placeholder-model-1-high` instead of `placeholder-model-1`), dumping a ~200-id cursor list raw instead of the catalog report, proposing before unmatched confirmation, and writing every catalog candidate instead of the chosen lanes.

## 1. Preferred runtimes per purpose

Ask two questions, each `multiSelect: true` over the runtimes Step 1 found installed: which runtimes may hold review lanes, and which may hold execute lanes. Every later list is limited to the runtimes chosen for its purpose; a purpose with no runtime gets no proposal (a session-default lane can still serve it, step 7). A pair on the host's own runtime is a real option: routing runs it as a subprocess whenever the host cannot select that model per call. Claude Code's four aliases on a Claude Code host are step 7's session-default question, not this list.

## 2. Catalog inputs

When a preferred runtime has no `models` list in Step 1's output, or the catalog step printed unmatched candidates, read items 1 to 4 of [`cli-model-selection.md`](cli-model-selection.md) and follow them before step 3 (its item 6 belongs to step 6 below). Otherwise skip it.

## 3. Proposal per purpose

- Run: `propose-lanes --purpose review --catalog-path <catalog> --detect --jev --runtime <runtime-id>`
- Run: `propose-lanes --purpose execute --catalog-path <catalog> --detect --jev --runtime <runtime-id>`

Repeat `--runtime` once per runtime chosen for that purpose at step 1. Each command prints one JSON object and writes nothing; run each once and slice its output, so "show more" never reorders anything. For each purpose, show the rows as printed:

- the first `default_view` rows of `pool`, each with its rank, key, runtime, `model_id`, class, cost band, price and `ranker_reason` (who ranked it: jev or the scorer, and why); "show more" shows the next rows of `pool`, then the `wider` rows with their class label (their scores come from a separate call and are not comparable with the pool's);
- the `zero_price` group (up to 5 rows of the same ranking), titled `zero price`, each row with its price source, date and locality line;
- the `aliases` group, labelled as printed (`assumed: router-env alias naming`): owner-defined router aliases, never ranked.

One model on two runtimes is two rows; pick each pair on its own. When `empty` is true, show `message` and let the owner name a model for a preferred runtime instead (it goes through Steps 2.3 to 2.5 like any pair). On exit 2 with `model catalog is empty`, return to Step 1.5 once, unless [`catalog.md`](catalog.md)'s pending-old-roster case ruled fetching out for this run. When the catalog is still empty after that one refresh, show the fetch's failure output and do not fetch again: continue as in the no-fetch case. In the no-fetch case, add each model id the owner names with `confirm-catalog-entry` as that case says, and with none, offer the session default (step 7) as the only lane or stop (for a pending roster, name the one whose migration approval would allow discovery). The order is a proposal: jev or the scorer only orders it, and the owner picks. Ask one confirmation per set, the review set first, then the execute set; no lane configuration is written before both sets are confirmed, and nothing is labelled review or execute in the catalog. A model the owner names, or an alternative the owner adds at step 8, is confirmed for its purpose by that explicit choice. A pair kept in both sets is one lane with `purpose` `both`: the writer files one entry per role, and its per-lane answers below hold in both roles.

While the owner picks, weigh two judgment calls with them, not just the mechanics: **is this lane's quota reliable enough to be a primary pick, or only worth keeping as a fallback?** (a lane with a tight free-tier limit belongs low in its role's order, not first) — and **does the model's strength match the purpose it is chosen for?** (the proposal ranks per purpose). Registering every available model produces orders nobody can predict; the goal is a config whose fallback behavior the owner sees at a glance.

An alias row or a model the owner names has no price or effort fields: its price is unknown (never zero, so it gets no free-lane question and no `pool` key) and its effort support is unknown (step 5 offers the one probe on any runtime but `claude` and `copilot`); it still goes through the test call of step 6 before it is saved.

## 4. Free lanes

For each chosen row whose `price` state is `zero` (`data_use_needed` is true), read [`free-lanes.md`](free-lanes.md) and follow its sections a to c before any other question about that lane. A lane the owner declines there leaves the set, and no later step asks about it.

## 5. Pair and effort per chosen lane

For each chosen lane, resolve its vendor (Step 2.3), store the pair and its knobs (Step 2.4) with the row's `model_id` (or the id the owner named) as `model`; Step 2.6's one `strength` offer for the run covers its tag. Then the effort:

- A custom entry (a `command` and no `runtime`): ask no runner effort question and write no `effort` or `effort_source`, since the writer refuses an effort without a table runtime. A level the owner wants for it is one of the entry's own template fields, stored and tested with its other fields (Step 2.4).
- `claude` and `copilot`: ask no effort question; say in one line "the runner has no effort flag for <runtime> yet, so no effort is stored", and write none.
- Known levels (the row's `efforts` is not empty): offer only the row's `efforts`, in the printed order, plus "no effort" (the default). Name each pair of the row's `efforts_refused` to the owner with its reason (a level the model lists but the runner cannot pass); never offer it. The chosen level is written as `effort`.
- Unknown support (the row's `efforts` is empty and its `efforts_source` is null, or the lane is an alias row or a model the owner named; any table runtime but `claude` and `copilot`, never a custom entry): ask whether to test one level the owner names. Ask Step 2.5's write-risk question first when it applies (the test is a real call; on a skip run no call and write no effort). For a zero-price lane, say in one line before the call: "This test call spends part of the lane's allowance." Then:

- Run: `check-reviewer --key <lane-key> --model <model-id> --vendor <vendor> --runtime <runtime-id> --effort <level> [--extra-json '<json>']` (no `--vendor` for a lane saved without a vendor; `--extra-json` carries the lane's other chosen knobs, such as codex's `service_tier` or cursor's `cursor_mode`, exactly as Step 2.5's pair test passes them, so the level is tested with the settings the lane will be saved with)

  Read `effort_probe` from the printed JSON. `accepted`: write `effort` and `effort_source` set to its `label` (`accepted by a call on <YYYY-MM-DD>`; an answer shows that the call accepted the level, not its effect). `rejected`: write no effort and show its `error` line as printed. `inconclusive`: write no effort and say the call did not show acceptance (quota, auth or a timeout). `ignored`: write no effort and show its `reason`. Never add `--catalog-path` to this call: an effort test says nothing about the pair's usability, and the command refuses the two flags together. The usability record comes from step 6's own call, which carries `--catalog-path` and no `--effort`, so one lane takes two separate calls when its effort is tested.

A stored model id that already carries an effort keeps it; a different `effort` on the lane then prints an `ignored:` line on every preview and dispatch.

## 6. Test the pair

First, before any test call here and before step 9 builds either role's order, take every custom entry (a `command` and no `runtime`) out of the execute set: a custom entry never runs as an executor (the execute screen refuses it and routing answers `no_formula`). Say so, then offer a supported replacement for that role: a table-runtime pair (it goes through steps 4 to 6 like any chosen lane) or the session default (step 7), or leave the execute set empty. A custom entry the owner also approved for review stays as a review-only lane (purpose `review`, never `both`) and is tested below for review only; one chosen only for execute leaves the set.

Then run Step 2.5's write-risk question and test call for every chosen lane: a table-runtime lane with `--runtime`, and a custom entry (no `runtime`) with `--command '<template>'`. A custom command has no profile, so its write risk is unconfirmed: show its template, ask the write-risk question, and run the call only on yes; on skip, save it as untested like any other skipped lane. For a zero-price lane, say in one line before the call: "This test call spends part of the lane's allowance." On a skipped write-risk question no call runs and Step 2.5 saves the lane as untested. A lane the owner drops after a failed test leaves the set. A passing test proves the review call only (`check-reviewer` runs the review invocation).

Then, for each kept lane, run the code-index alternative check of [`cli-model-selection.md`](cli-model-selection.md) item 6 (it prints a non-null `alternative_cli` only for a CLI whose codebase-memory-mcp registration ai-kit cannot read) before step 7:

- Run: `check-code-index-alternative --runtime <runtime-id> --model <model-id> --runtimes-json <runtimes.json>`

  When `alternative_cli` is not null, tell the owner in one line, as item 6 says; the owner still decides, and nothing is replaced or dropped. A custom lane passes the id of the CLI its command wraps as `--runtime` (the table runtime whose binary the command launches); a script that wraps no known CLI skips this check, and the owner is told so in one line.

## 7. Session default

Ask Step 2.7's session-default question and its role answer. A session-default lane is a configured lane: once it is written, the review skill and the execute adapter no longer offer setup.

## 8. Alternative lane

When a role holds a usage-limited lane, follow [`free-lanes.md`](free-lanes.md) section e before step 9.

## 9. Order per role

Ask two questions: the order of the review lanes, then the order of the execute lanes. Each defaults to the order the lanes were confirmed in (the proposal's ranks), with session-default lanes where the owner placed them; the owner may reorder. Before the owner fixes an order, weigh one call with them: does a tight-quota or usage-limited lane belong first, or only as a fallback after a lane with steadier quota? Echo each order back as a numbered list before Step 3. Step 3 writes them as the `ladder` of `[lanes.policy.review]` and of `[lanes.policy.execute]`; a role with no lane gets no order. When the execute role holds a lane, ask once, default no: "When no execute lane is available (all unavailable, blocked or out of quota), run the task on this session's own model? (1) no, (2) yes (`session_fallback`)". Only a yes writes `session_fallback = true` in `[lanes.policy.execute]`; a no or a skip writes nothing. When Step 3 sends the owner back here to change an order, keep the fallback answer already given and do not ask again; when the execute role no longer holds a lane, no fallback key is written.

## 10. Escalation

Only for a role that holds two or more lanes, ask per lane, default no: "At fix rounds 4 and 5 of a stuck task, may it move from `<key>` to a more capable lane ranked above it in this role's order? (1) no, (2) only to one of another runtime (`escalate_runtime`), (3) only to one of the same runtime with another model (`escalate_model`), (4) either." Say in one line what these flags do: for execute lanes the superpowers execute adapter reads them at fix rounds 4 and 5 to pick a more capable lane of the matching kind; for review lanes they are recorded only (the runner reports them as ignored and never starts another lane from them). Write a flag only as `true` on that answer; a no or a skip writes nothing, and no ranking, proposal or default ever sets one. A role with one lane has no target, so ask nothing for it. A lane kept for both roles carries one set of flags for both, so when its two roles got different answers (or only one role was asked), Step 3 writes it as two entries with the same key, `purpose = "review"` and `purpose = "execute"`, each with only the flags approved for that role.

Whatever the number of lanes, ask once, default none: "Which lanes, if any, should run in a herdr pane you can watch (`interactive`)? Name their keys, or none." Say in one line what the marker does: a lane marked interactive may run in a herdr pane (execute and code-review lanes; spec review never uses a pane) once a recorded run verifies panes; until then it runs like any other lane, and a lane not marked never gets a pane. Only a lane the owner names gets `interactive = true`; none named writes nothing, and no ranking, proposal or default ever sets it.

## 11. Mode, strategy and timeouts

Ask Step 2.8's questions, then go to Step 3.
