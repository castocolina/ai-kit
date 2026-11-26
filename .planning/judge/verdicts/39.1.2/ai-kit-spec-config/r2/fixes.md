# Loop 39.1.2 round 2 fixes: ai-kit-spec-config

Round 2 left 3 high findings (referee-one D8-1, D8-2, D8-4; referee-two B 88.8 and advisory referee-three B 88.8 had
none), 3 or fewer, so by AGENTS.md's judge-loop rule each was checked against the text and code and fixed in the skill's
own files, and no further judge round runs: the skill's digest is stale by design until its next loop. Two cheap
findings that cite real text are fixed too. No code changed; no feature was removed (trusting a file whose entry has no
own preview line stays possible, with "leave it untrusted" as the default).

- referee-one D8-1 (high): `references/trust-flow.md` showed only the `command` text of an entry the `--show` preview
  does not render and re-checked only that text, so a change to another field (one that fills the placeholders) could
  slip between preview and trust. Step 4 now shows every field of such an entry (and of the inherited user entry), and
  step 7 re-reads the file after the trusting call, compares every field and revokes on any difference. The digest is
  the file's command-bearing entries with every field (`trust.command_lanes_bytes`), so unchanged entries mean the
  trusted bytes are the approved ones; the one stated limit left is a change made and undone during the call.
- referee-one D8-2 (high): SKILL.md routed only a literal `--check-only` to the check branch, while the shipped eval
  `casual-check-only` asks in plain words ("Just check which reviewers are available, and do not change anything.").
  A plain-words request only to check and change nothing now counts as the flag.
- referee-one D8-4 (high): SKILL.md said `--catalog-path` makes `check-reviewer` record the result, but
  `cli._cmd_check_reviewer` records only for a pair with a runtime and prints `usability.recorded` (with a `problem`
  when not), or no `usability` object. The text now reports a catalog update only when `recorded` is true and says a
  custom entry's test records nothing.
- referee-one D8-5 (medium): Step 4's capability lines come from `config_status.capability_lines` over the resolved,
  merged roster; the text now labels them as that project's effective roster and names the global-write case a
  `local-only` project file hides.
- referee-one D4-1 (low): the description's check-only clause now says "no config writes".

Left for a later loop: moving Step 1.6, 2.1 and 2.7 detail out of SKILL.md (referee-one D5-1, referee-three D5-1,
D8-1, D1-2), eval fixtures and graded outputs (referee-one D7-1, referee-two D7-1, D7-2, referee-three D7-1), the
scratch-folder guard (referee-one D6-1), the catalog-entry example (referee-one D8-3), the probe-key subcommand
(referee-two D6-1, backlog 999.29), the claude/copilot effort wording (referee-two D8-1, needs a runner check) and the
remaining lows.
