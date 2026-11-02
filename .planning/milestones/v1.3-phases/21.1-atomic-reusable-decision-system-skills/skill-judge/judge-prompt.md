# In-session skill-judge prompt (both lanes; 21.1-06)

One prompt, both judged skills. The orchestrator runs it once per skill after GREEN, the
micro-tests and REFACTOR are done (no `pending (orchestrator)` marker left), on the committed
tree, with read-only tools. `<skill>` is the judged skill's directory name and `<rubric>` the
path to the orchestrator's own installed skill-judge rubric (its `SKILL.md`).

---

You are an external evaluator. Do not edit any file. Print the report to stdout. Use read-only
tools only. Read any file larger than 50 KB in chunks.

Read the rubric at `<rubric>`. Judge the skill at `skills/<skill>/` — its `SKILL.md` and every
file it points to (reference files, backend notes, scripts it names).

PART 1 — Dimensions (each on its own line, in exactly this form: `D<k> <score>/<max>`, then
the percent of maximum and, when the dimension is under its floor, the improvement that the
rubric's analysis for that dimension lists):

- D1 Knowledge Delta 20 (floor 16)
- D2 Mindset + Appropriate Procedures 15 (floor 12)
- D3 Anti-Pattern Quality 15 (floor 12)
- D4 Specification Compliance 15 (floor 12)
- D5 Progressive Disclosure 15 (floor 12)
- D6 Freedom Calibration 15 (floor 12)
- D7 Pattern Recognition 10 (floor 8)
- D8 Practical Usability 15 (floor 12)

Total maximum 120. Do not invent dimensions. Findings are listed as Critical, Important or
Minor, each with the file and line it comes from.

Special check: confirm the skill body contains a recipe line for `needs_fallback` — a line
telling the agent what to do when an answer carries `needs_fallback: true` (decide that item
with its own reasoning). A missing recipe is a Critical finding.

End lines (print exactly these):

- `CURRENT <n>/120` — the sum of D1–D8.
- `CRITICAL <n>`
- `IMPORTANT <n>`
- `FLOORS ok|fail`

PART 2 and the remaining end lines depend on `<skill>`:

## For jev-fast-decision

Activation picks first, before opening any skill body: list `skills/*/SKILL.md` yourself and
read only the YAML frontmatter `name` and `description` of each. Then read
`skill-judge/activation.jsonl` (12 lines, `{"prompt", "expect"}`) and name, for each line, the
single skill you would load (that frontmatter name) or none, with one-line reasoning, using
only those frontmatter fields.
Pass rule: every `expect jev-fast-decision` line picks jev-fast-decision; no `expect none` or
`expect typesafe-ai` line picks it.

Then open `skills/jev-fast-decision/SKILL.md` and print, each followed by the quoted line:

- `CITE_PROBE skills/jev-fast-decision/SKILL.md:<n>` — the line telling the agent to run
  `--probe` before the first call.
- `CITE_BACKEND skills/jev-fast-decision/SKILL.md:<n>` — the line telling it to read
  `backends/<selected>.md`.

Both lines must exist. Additional end lines for this skill: `ACTIVATION ok|fail` plus the two
`CITE_` lines above.

End with `VERDICT pass` only if `CURRENT >= 96`, no dimension is under its floor, the
`needs_fallback` recipe exists, Part 2's pass rule holds and both cite lines exist; otherwise
`VERDICT fail`.

## For ai-kit-gsd-spec-discuss

The 500-word body cap does not apply to this skill. Weigh especially the sections plan 21.1-03
changed: the set-up steps 3 and 5, section 3 (the decision-ladder recipe), and the two
references (`references/decision-table.md`, `references/log-formats.md`) as they now defer to
the shared client.

End with `VERDICT pass` only if `CURRENT >= 96` and no dimension is under its floor; otherwise
`VERDICT fail`.
