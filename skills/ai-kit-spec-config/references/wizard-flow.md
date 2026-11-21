# Wizard question flow (spec-config Step 2.2)

This is the one place the question order lives. Ask every question of the owner in the owner's own session, never in a herdr pane or by another agent, with the host's question tool or numbered plain text (SKILL.md, Host tools). Review and execute stay separate in every question. No lane configuration is written before both sets are confirmed, and Step 3 writes only the lanes chosen here; the catalog step and the test calls still record catalog and usability data as before. Each `- Run:` command below runs as `python3 "$TOOLS_PY" <command>`; `<catalog>` is the literal path Step 1.5 printed.

## 1. Preferred runtimes per purpose

Ask two questions, each `multiSelect: true` over the runtimes Step 1 found installed: which runtimes may hold review lanes, and which may hold execute lanes. Every later list is limited to the runtimes chosen for its purpose; a purpose with no runtime gets no proposal (a session-default lane can still serve it, step 7). A pair on the host's own runtime is a real option: routing runs it as a subprocess whenever the host cannot select that model per call. Claude Code's four aliases on a Claude Code host are step 7's session-default question, not this list.

## 2. Catalog inputs

When a preferred runtime has no `models` list in Step 1's output, or the catalog step printed unmatched candidates, read [`cli-model-selection.md`](cli-model-selection.md) completely and follow its items 1 to 4 before step 3. Otherwise skip it.

## 3. Proposal per purpose

- Run: `propose-lanes --purpose review --catalog-path <catalog> --detect --jev --runtime <runtime-id>`
- Run: `propose-lanes --purpose execute --catalog-path <catalog> --detect --jev --runtime <runtime-id>`

Repeat `--runtime` once per runtime chosen for that purpose at step 1. Each command prints one JSON object and writes nothing; run each once and slice its output, so "show more" never reorders anything. For each purpose, show the rows as printed:

- the first `default_view` rows of `pool`, each with its rank, key, runtime, class, cost band, price and `ranker_reason` (who ranked it: jev or the scorer, and why); "show more" shows the next rows of `pool`, then the `wider` rows with their class label (their scores come from a separate call and are not comparable with the pool's);
- the `zero_price` group (up to 5 rows of the same ranking), titled `zero price`, each row with its price source, date and locality line;
- the `aliases` group, labelled as printed (`assumed: router-env alias naming`): owner-defined router aliases, never ranked.

One model on two runtimes is two rows; pick each pair on its own. When `empty` is true, show `message` and let the owner name a model for a preferred runtime instead (it goes through Steps 2.3 to 2.5 like any pair). On exit 2 with `model catalog is empty`, return to Step 1.5. The order is a proposal: jev or the scorer only orders it, and the owner picks. Ask one confirmation per set, the review set first, then the execute set; no lane configuration is written before both sets are confirmed, and nothing is labelled review or execute in the catalog. A model the owner names, or an alternative the owner adds at step 8, is confirmed for its purpose by that explicit choice. A pair kept in both sets is one lane with `purpose` `both`: the writer files one entry per role, and its per-lane answers below hold in both roles.

An alias row or a model the owner names has no price or effort fields: its price is unknown (never zero, so it gets no free-lane question and no `pool` key) and its effort support is unknown (step 5 offers the one probe on any runtime but `claude` and `copilot`); it still goes through the test call of step 6 before it is saved.

## 4. Free lanes

For each chosen row whose `price` state is `zero` (`data_use_needed` is true), read [`free-lanes.md`](free-lanes.md) and follow its sections a to c before any other question about that lane. A lane the owner declines there leaves the set, and no later step asks about it.

## 5. Pair and effort per chosen lane

For each chosen lane, resolve its vendor (Step 2.3), store the pair and its knobs (Step 2.4) with the row's `model_id` (or the id the owner named) as `model`, and ask the optional `strength` (Step 2.6). Then the effort:

- `claude` and `copilot`: ask no effort question; say in one line "the runner has no effort flag for <runtime> yet, so no effort is stored", and write none.
- Known levels (the row's `efforts` is not empty): offer only the row's `efforts`, in the printed order, plus "no effort" (the default). Name each pair of the row's `efforts_refused` to the owner with its reason (a level the model lists but the runner cannot pass); never offer it. The chosen level is written as `effort`.
- Unknown support (the row's `efforts` is empty and its `efforts_source` is null, or the lane is an alias row or a model the owner named; any runtime but `claude` and `copilot`): ask whether to test one level the owner names. Ask Step 2.5's write-risk question first when it applies (the test is a real call; on a skip run no call and write no effort). For a zero-price lane, say in one line before the call: "This test call spends part of the lane's allowance." Then:

- Run: `check-reviewer --key <lane-key> --model <model-id> --vendor <vendor> --runtime <runtime-id> --effort <level>`

  Read `effort_probe` from the printed JSON. `accepted`: write `effort` and `effort_source` set to its `label` (`accepted by a call on <YYYY-MM-DD>`; an answer shows that the call accepted the level, not its effect). `rejected`: write no effort and show its `error` line as printed. `inconclusive`: write no effort and say the call did not show acceptance (quota, auth or a timeout). `ignored`: write no effort and show its `reason`. Never add `--catalog-path` to this call: an effort test says nothing about the pair's usability, and the command refuses the two flags together.

A stored model id that already carries an effort keeps it; a different `effort` on the lane then prints an `ignored:` line on every preview and dispatch.

## 6. Test the pair

Run Step 2.5's write-risk question and test call for every chosen table-runtime lane. For a zero-price lane, say in one line before the call: "This test call spends part of the lane's allowance." On a skipped write-risk question no call runs and Step 2.5 saves the lane as untested. A lane the owner drops after a failed test leaves the set.

Then, for each kept lane, run the code-index alternative check of [`cli-model-selection.md`](cli-model-selection.md) item 6 (it prints a non-null `alternative_cli` only for a CLI whose codebase-memory-mcp registration ai-kit cannot read) before step 7:

- Run: `check-code-index-alternative --runtime <runtime-id> --model <model-id> --runtimes-json <runtimes.json>`

  When `alternative_cli` is not null, tell the owner in one line, as item 6 says; the owner still decides, and nothing is replaced or dropped.

## 7. Session default

Ask Step 2.7's session-default question and its role answer. A session-default lane is a configured lane: once it is written, the review skill and the execute adapter no longer offer setup.

## 8. Alternative lane

When a role holds a usage-limited lane, follow [`free-lanes.md`](free-lanes.md) section e before step 9.

## 9. Order per role

Ask two questions: the order of the review lanes, then the order of the execute lanes. Each defaults to the order the lanes were confirmed in (the proposal's ranks), with session-default lanes where the owner placed them; the owner may reorder. Echo each order back as a numbered list before Step 3. Step 3 writes them as the `ladder` of `[lanes.policy.review]` and of `[lanes.policy.execute]`; a role with no lane gets no order.

## 10. Escalation

Only for a role that holds two or more lanes, ask per lane, default no: "Escalate from `<key>` when it fails? (1) no, (2) to the next lane of another runtime in this role's order (`escalate_runtime`), (3) to the next lane of the same runtime (`escalate_model`), (4) both." Say in one line that these flags are stored and informational; no run reads them yet. Write a flag only as `true` on that answer; a no or a skip writes nothing, and no ranking, proposal or default ever sets one. A role with one lane has no target, so ask nothing for it.

## 11. Mode, strategy and timeouts

Ask Step 2.8's questions, then go to Step 3.
