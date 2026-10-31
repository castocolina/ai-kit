---
name: ai-kit-spec-goal-prompt
description: "Builds a ready-to-paste /goal, /loop or /gsd-autonomous prompt file (one-shot goal, autonomous run) for GSD phases or superpowers plans, with rails, quota directives and e2e-based done. Use when asked for a goal prompt, a loop prompt, an autonomous run prompt or to finish phases N-M or these plans. Detects host primitives (labelled verified or unverified), picks one to three strategies, writes a committable file. Never runs the prompt."
---

# ai-kit-spec-goal-prompt

Writes one prompt file for a GSD phase range or a set of superpowers plans. The user pastes the
file's block into a **separate** session at the repository root. This skill gathers facts and
their labels, asks four questions, runs two CLI calls, relays the result and stops. It never runs
the generated prompt.

**The mindset:** you gather facts and labels; the script decides the strategy and writes the
file. Never claim more certainty than the labels say. A primitive labelled `unverified` or
`not seen` is not available, and you say so.

## 0. Set up once per run

1. **Resolve this skill's scripts dir (`S`).** Use the printed literal path in every later call.
   ```bash
   for d in "$(dirname "<absolute path of THIS SKILL.md>")" "$HOME/.claude/skills" "$HOME/.agents/skills" \
            "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills" "$HOME/.cursor/skills" "$HOME/.pi/agent/skills"; do
     for c in "$d/scripts" "$d/ai-kit-spec-goal-prompt/scripts"; do
       [ -f "$c/goal_prompt.py" ] && { printf '%s\n' "$c"; break 2; }; done; done
   ```
   If it prints nothing, **stop the run**.
2. **Resolve the GSD command** only when the repository has `.planning/PROJECT.md`. Use the
   repository's own copy: `node .claude/gsd-core/bin/gsd-tools.cjs`, run from the repository
   root. If that file does not exist, there are no GSD captures: ask for captured JSON (§2) or use
   a plans or free-text work set. Never install or update GSD.
3. **Build the `--tools` list** from the tool names you can see in your own tool list, plus one
   `ToolSearch` keyword query (`cron schedule wakeup loop`) when your host has a `ToolSearch`
   tool (unverified on hosts other than Claude). Pass only names you saw. A name you did not see
   is reported as `not seen`, never `absent`.

## 1. Ask four questions in one batch

Ask all four in one message, with the host's question tool or plain text:

1. **Work set:** a phase range (`16-17`), a phase list (`16,16.1,17`) for GSD, or superpowers plan
   files. If both `.planning/` and plans exist, ask which is meant; never merge them. Ask about
   free-text dependencies between plans here too.
2. **Target host:** default is the current host (`host.current` in the detect output).
3. **Native execution allowed?** Default no. It becomes the answers field `native_execution`; its
   effect on the rendered wording is coded for OpenGSD cross-AI and unverified in a live run.
4. **Mockups:** repository-relative paths, or none.

Never ask a fifth question. "Must outlive" and "provable" are derived (`derived` in detect) and
shown, never asked.

## 2. Detect

Run from the repository root; the output goes to `tmp/`, which is git-ignored:
```bash
python3 "$S/goal_prompt.py" detect --repo . --target-host <host> --tools "<names, comma-separated>" \
  --gsd-cmd "node .claude/gsd-core/bin/gsd-tools.cjs" --work-set "<KIND:VALUE>" > tmp/goal-detect.json
```
- `--work-set` takes `phases:16-17`, `phases:16,16.1,17`, `plans:<file>,<file>` or `free:<text>`.
- Omit `--target-host` for the current host. Omit `--gsd-cmd` only without a GSD project: a
  `.planning/PROJECT.md` with no `--gsd-cmd` and no `--roadmap` exits 2 with "a GSD work set needs
  --roadmap or --gsd-cmd" (observed).
- Exit 2 prints a JSON `error` on stderr. Relay the message, fix the input, rerun. Never guess.

Read the result back in four lines:
1. Scope: `scope.kind` and `scope.identity`.
2. E2E: the `e2e.commands` list, or "none" when `e2e.none` is true.
3. Primitives: each `primitives` row with its `availability` and `usage_source` labels.
4. Derived: `derived.must_outlive` and `derived.provable`.

If `needs` is non-empty, supply the capture and rerun: `--identity <file>` for `identity`,
`--phase-op <dir>` holding `<number>.json` files for `phase_op`. The GSD queries behind these
(`runtime-identity`, `init.phase-op`) are named in the CLI source; whether a given gsd-tools build
answers them is unverified. If `scope.ask` is set, ask that question and rerun detect with the
answer.

**MANDATORY: read [references/host-primitives.md](references/host-primitives.md) before relaying any primitive label.**
**MANDATORY: read [references/strategy-matrix.md](references/strategy-matrix.md) before overriding or explaining a strategy.**

## 3. Render

Write `tmp/goal-answers.json`. Use repository-relative paths only:
```json
{
  "work_set": {"kind": "phases", "numbers": ["16", "16.1", "17"]},
  "target_host": "claude",
  "native_execution": false,
  "mockups": [],
  "strategy": null,
  "objective": "",
  "skills": [],
  "output_dir": null
}
```
- `work_set`: `{"kind": "phases", "numbers": [...]}`, `{"kind": "plans", "files": [...]}` or
  `{"kind": "free", "text": "..."}`.
- `strategy`: `"goal"`, `"loop"` or `"autonomous"` only when the user explicitly asked for that
  one; otherwise `null`.
- `output_dir`: `null` (default: `.planning/goals` for OpenGSD, `docs/superpowers/goals` otherwise),
  or a repository-relative directory with no `..`.
- `objective`: the user's own words for the OBJECTIVE lines, or `""`. `skills`: extra skill names.

Then run:
```bash
python3 "$S/goal_prompt.py" render --repo . --detect tmp/goal-detect.json --answers tmp/goal-answers.json
```
Relay, from the render stdout and the detect output:
- `path`: the file written.
- Each strategy with its `reason` and `label` (these come from detect's `strategies`; render
  prints only `id` and `recommended`).
- Each `conditions` entry: the `/goal` condition length in characters. Render refuses a condition
  over the 4,000 code-point cap.
- Every `warnings` entry (readiness problems; stdout only, never written into the file).
- Every `dropped` entry: a requested strategy the host cannot run.

**MANDATORY: read [references/e2e-and-evidence.md](references/e2e-and-evidence.md) before reporting any e2e fact.**

Never edit the rendered file by hand. Fix the answers and render again.

For the shape of one whole run, from answers to hand-off, see [references/worked-example.md](references/worked-example.md).

## 4. Hand off

- Give the path.
- At most three sentences on why this strategy, taken from its reason.
- Tell the user to paste the block between the markers into a **new** session at the repository
  root. Name any strategy whose label is `unverified`.
- Offer to commit the file; the goals folder is committable.
- Stop. Never run the prompt and never start the phases yourself.

## NEVER

- Never run the generated prompt — this skill ends at the file; the run belongs to a session the user starts.
- Never ask a fifth question — the four-question batch is the agreed interface, and more questions stall the run.
- Never put an absolute path or a secret into `answers.json` — render refuses machine paths in `output_dir` and `work_set.files`, and the file may be committed.
- Never edit the rendered file by hand — the next render would overwrite it, and the file would then no longer match its own contract.
- Never present a primitive as available when its label is `unverified` or `not seen` — a false "available" sends the user into a run that depends on a primitive the host may not have.
- Never treat jev as a gate or as a UI or mockup judge — its answers are advisory and it has no say over the file.
- Never put anything but `--from`, `--to`, `--only` or `--converge` on the `/gsd-autonomous` line — the workflow greps all of its arguments, so any other token changes the run.
- Never write the rationale for missing tooling into the file — the paste block must hold the run's instructions only.
- Never import another skill's Python into this skill's scripts — sibling skills are reached only through their CLIs, as the detect step does.
- Never write a DONE WHEN that accepts unit tests alone — the generated prompt's done rule is e2e-based, with the count printed.
- Never advise skipping a pre-commit hook — a failing hook is fixed at its root.

## Do NOT load

- `assets/prompt-template.md` — the script renders it; reading it wastes context and invites
  hand edits. The renderer's output is the only source.
- The `tests/` files — they test the scripts, not a run.

## Unverified

Each item stays unverified until observed; the linked reference says why.

- Codex `/goal` usage text: taken from binary strings only ([host primitives](references/host-primitives.md)).
- Every non-current host's primitives: no live check of those hosts ([host primitives](references/host-primitives.md)).
- Original GSD's `/gsd-autonomous`, `runtime-identity` and `verification.status` ([strategy matrix](references/strategy-matrix.md)).
- Zero-test markers for pytest, jest, vitest, Playwright, Cypress and cargo ([e2e and evidence](references/e2e-and-evidence.md)).
- Whether a 4,000-code-point `/goal` condition is accepted by the host ([strategy matrix](references/strategy-matrix.md)).
- Whether `ToolSearch` exists on any host other than Claude.
- Whether the rendered wording changes with `native_execution` in a live run.

## When something is missing

| Missing | What happens | What you tell the user |
|---|---|---|
| The wake CLI (`ai-kit-session-wake`) | `matrix_source` reads `missing`; every primitive is `unverified` | Name the missing CLI and that the primitives are unverified |
| The spec CLI (`ai-kit-spec-review`) | `host.current` is `null`, so every primitive is `unverified` | Name the missing CLI; the current host is unknown |
| The decide CLI (`ai-kit-gsd-spec-discuss`) | `jev.usable` is `false` with reason `decide.py missing` | Nothing to decide; the file never depends on jev |
| GSD command (no `.claude/gsd-core/bin/gsd-tools.cjs`) | No phase captures; a GSD work set exits 2 | Ask for captured JSON: `--roadmap`, `--identity`, `--phase-op` |
| E2E suite (`e2e.none` is true) | The file's first task creates one (create-first) | The suite is created by the run; nothing is verified yet |
| No usable jev backend | The file says the advisory check was omitted | Nothing to decide; the file never depends on jev |
| A mockup path that is a machine path | Render refuses it (GuardError, exit 2); mockup existence is not checked | Ask for a repository-relative path |
