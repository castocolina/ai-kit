# Lite executor block

MANDATORY: read this file in full before changing the block, its selector or the rail sentence. Do NOT load it while running a plan or to run the command; the project's own instruction file calls the command before the plan exists.

## The block

<!-- lite-block:start -->
# Lite executor block (unverified)

The executor picked for this plan is a lite coding model. Write every task for it:
- One file group per task; keep each task small.
- Give the exact command, path and expected output for every step.
- State every value the task needs; leave nothing to infer.
- Name the test command and its pass signal in each task.

Effect on a lite model: unverified.
<!-- lite-block:end -->

## Selector

Lite means the picked model's catalog class (`facts.class.value` of its catalog entry) is `small` or `fast`. Any other class, `unknown`, a missing class or a missing entry is not lite. The executor is the executor pick over the execute roster with the task label `plan`; with no jev pick (no jev, a low answer, a jev error or one lane) it is the default order's first lane, the one that will run, and the JSON still says `decided_by: default`. An empty roster writes no file.

## Command

`python3 <adapter skill>/ai-kit-spec-superpowers.py lite-block --cwd <project>` writes `.aikit/brief/lite-executor.md` (this block only) when that executor is lite, removes a stale one otherwise, and prints `{"lite", "key", "decided_by", "path", "removed_stale"}`. The only file it writes in the project is `.aikit/brief/lite-executor.md`. It never writes `.aikit/brief/SKILL.md`, never migrates a config and never probes a host. Exit 2 means a config error or a brief folder outside the project; nothing is handed over then.

## Rail sentence

A project hands the file over from its own instruction file, after the brief step: run the command, then hand `.aikit/brief/lite-executor.md` to the plan writer too only when it exits 0 with `"lite": true`.

## Limits

A router alias reads class `router` and is never lite, so it gets no lite block. The jev client keeps its own answer log (`jev-answers.jsonl` under the user's state home); this command does not control that file. The block's effect on a lite model is unverified.
