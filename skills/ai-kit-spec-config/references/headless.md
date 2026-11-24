# No way to ask (spec-config headless stop)

Read this only when the host has no structured-question tool and no plain conversation with the user (a subagent, a print-mode or other headless run). Every later step needs the owner's answers, so the run stops after Step 1's two detection commands: it writes no config, cache or trust record (no runtimes snapshot, no catalog), makes no scratch folder (Step 0 makes it only on first need), and never answers a question for the owner.

Print this block, filling `<runtime-id>` and `<n>` from the `detect-runtimes` output (one entry per installed runtime: its listed model count, or `no listing`; `none` when nothing is installed):

    ai-kit-spec-config cannot ask here; no config, cache or trust record was written.
    Installed runtimes: <runtime-id>: <n> models listed, <runtime-id>: no listing
    Questions it would ask:
      1. Where to write the config, and whether to replace an existing roster.
      2. Which installed runtimes to use for review, and which for execute.
      3. Which proposed models to keep for each purpose, one confirmation per set.
      4. For each chosen zero-price model: its data-use note and whether to send project content to it, then whether it is usage-limited.
      5. The effort of each chosen lane, where its levels are known.
      6. Whether to register a session-default lane, and for which role.
      7. The priority order of the review lanes and of the execute lanes.
      8. The escalation flags, for a role with two or more lanes.
      9. The mode, the strategy of a local config and the timeout tiers.
    A person must run ai-kit-spec-config.

Then stop.
