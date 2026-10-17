# v1 path (kept, secondary)

Read only when running the v1 flow. Never run v1 `apply-execution`/`apply-review` on a project
v2 `apply` configured: `apply-execution` overwrites `workflow.cross_ai_command` with its own
single-runtime runner command, dropping the prefer order and models v2 chose.

One curated question (`model_profile`) plus detected and preset steps. Use it only for a
project v2 has never configured. Order and safeguards:

1. `ensure-project` first, always: without it `config-set` silently creates a sparse
   one-key config.
2. `apply-profile`, then `apply-critical-agents`.
3. Run each `detect-*-candidate`, show the result, and pass its `{cli, model}` through
   unchanged: `apply-execution` flags are optional (omit both when nothing matched);
   `apply-review` flags are required.
4. `detect-claude-md-path`: skip `apply-claude-md-path` when it prints `null`.
5. `detect-frontend`, then `apply-workflow-defaults` with that boolean for both UI flags.
6. `apply-execution` can exit 0 without configuring execution. Read its JSON:
   `cross_ai_command_written` false with a `degraded_reason` (`runner_not_ready`,
   `no_candidate`, `no_model`, `unsafe_hook_token`, `no_builder`) means the command was left
   absent or unchanged. Report the reason and the printed notes; for `runner_not_ready`, fix the
   runner `ensure-runner` reported and re-run before telling the user execution is configured.
   `unsafe_hook_token`: the model id holds a character GSD's unquoted hook would split or glob
   (nothing was rendered; pick another id). `no_builder`: the `ai-kit-spec-review` sibling is
   missing.

```bash
python3 "$ENTRYPOINT" ensure-project --project-dir <target>
python3 "$ENTRYPOINT" apply-profile --project-dir <target> --profile <profile>
python3 "$ENTRYPOINT" apply-critical-agents --project-dir <target>
python3 "$ENTRYPOINT" detect-execution-candidate
python3 "$ENTRYPOINT" apply-execution --project-dir <target> --cli <detected cli> --model <detected model>
python3 "$ENTRYPOINT" detect-review-candidate
python3 "$ENTRYPOINT" apply-review --project-dir <target> --cli <detected cli> --model <detected model>
python3 "$ENTRYPOINT" detect-claude-md-path --project-dir <target>
python3 "$ENTRYPOINT" apply-claude-md-path --project-dir <target> --path <detected path>
python3 "$ENTRYPOINT" detect-frontend --project-dir <target>
python3 "$ENTRYPOINT" apply-workflow-defaults --project-dir <target> --ui-phase <true|false> --ui-review <true|false>
```

