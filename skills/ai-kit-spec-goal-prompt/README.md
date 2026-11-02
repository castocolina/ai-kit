# ai-kit-spec-goal-prompt

Builds one committable Markdown file that holds a ready-to-paste prompt for a SEPARATE agent session. You name a set of GSD or OpenGSD phases, or superpowers plans; the skill detects the host's goal, loop and schedule primitives, picks one to three strategies (`/goal`, `/loop`, `/gsd-autonomous --converge`) and writes the prompt with rails, quota directives and a definition of done that needs real end-to-end evidence. It never runs the prompt.

## What it is

- A skill (`SKILL.md`) plus a stdlib-only generator, `scripts/goal_prompt.py`, with two subcommands: `detect` and `render`.
- Every host primitive carries two labels (availability here, usage source). Anything not observed is labelled `unverified`; a non-current target host is unverified everywhere.
- jev, when usable, is advisory and text-only: never a gate, never a judge of UI or mockups.

## When to use

- You want phases or plans to run unattended and need the prompt, not the run.
- You are unsure whether `/goal`, `/loop` or `/gsd-autonomous` fits the work.

Not for: running a phase now (use the GSD execute commands or `ai-kit-spec-execute`), summarizing phases, `/loop` pacing without a goal, or reviewing a plan (`ai-kit-spec-review`).

## Install

From the repository root:

```bash
python3 tools/setup.py install --headless --skills ai-kit-spec-goal-prompt
```


## Usage

Ask your agent, for example: "build a goal prompt for phases 16 to 18". The skill asks four questions in one batch (work set, target host, native execution, mockups), runs `detect`, then `render`, and hands you the file path.

The scripts run without prompts, print JSON on stdout, and exit 0 (ok) or 2 (bad input, with a JSON error on stderr):

```bash
python3 skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py detect --repo . --work-set phases:16-18 --gsd-cmd "node .claude/gsd-core/bin/gsd-tools.cjs" --tools "" > tmp/detect.json
python3 skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py render --repo . --detect tmp/detect.json --answers tmp/answers.json
```

`tmp/answers.json` holds `{"work_set": {"kind": "phases", "numbers": ["16", "17", "18"]}, "target_host": "claude", "native_execution": false, "mockups": [], "strategy": null, "objective": "one plain sentence", "goal_style": "auto", "output_dir": null}`.

A `/goal` condition over 1,000 characters does not go on the `/goal` line. The first block line is then a short pointer (`/goal read document <this file> at section Full goal ...`) and the file ends with a `## Full goal` section that holds the condition. `goal_style` is `auto` (default), `inline` or `pointer`; `render` prints the chosen `goal_form`. That the host follows the pointer is unverified. An objective longer than one rule line is cut there and kept whole in a `## Full objective` section (`full_objective` in the render output).

Tests: `python3 -m unittest tests.test_ai_kit_spec_goal_prompt_evals` checks that the evals and trigger queries are well formed and that the scripts behave as documented. It calls no model.

## Links

- [SKILL.md](SKILL.md) - the skill itself
- [references/host-primitives.md](references/host-primitives.md), [references/strategy-matrix.md](references/strategy-matrix.md), [references/e2e-and-evidence.md](references/e2e-and-evidence.md), [references/worked-example.md](references/worked-example.md), [references/evidence.md](references/evidence.md) - loaded on demand
- [evals/evals.json](evals/evals.json) and [evals/trigger-queries.json](evals/trigger-queries.json) - output evals and trigger queries
- [tests/test_ai_kit_spec_goal_prompt_evals.py](../../tests/test_ai_kit_spec_goal_prompt_evals.py) - structure and script smoke tests
