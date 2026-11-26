# Step 3 — Apply findings (full detail)

### Step 3 — Apply findings (when Issues Found, iter < cap)

The reviewer's report is already at `EFFECTIVE_REPORT_PATH` (Step 1.5) — no separate save needed here.

**Round context.** Step 3 runs after SKILL.md Step 1 pinged the chosen lanes (`ping-lanes`) and switched a flagged lane that hit quota (`switch-lane`), and after Step 1.5 merged the lanes that judged. A report whose `Judged by:` line names a lane that did not judge is a partial review: fix its findings like any other. An `Approved (partial)` report never reaches Step 3, and a loop that ends clean after a partial round reports `Approved (partial)` ([lane-failure.md](lane-failure.md)).

**Resolve a revise route per flagged archetype.** A report may flag findings across more than one archetype (a fused superpowers design doc, or a doc set). For each archetype with at least one CRITICAL/HIGH/actionable finding, resolve its route from the profile's `revise_protocol`:

1. `revise_protocol.routes` exists → pick the entry whose `archetype` equals the flagged archetype.
2. Else a flat `revise_protocol` exists (shorthand `mode`/`invoke`/`command`/`applies_to`) and `applies_to` contains the archetype → treat it as one route `{archetype, invoke, command, validate: null}`.
3. Else (no `revise_protocol`, `mode: direct_edit`, or the archetype isn't covered) → the route is **direct edit**.

Dispatch per the route's `invoke`:

| `invoke` | Handler |
|---|---|
| (direct edit / archetype not covered) | **Step 3a** — generic `ai-kit-spec-review-fixer` fixer |
| `skill:<name>` | **Step 3b-skill** — hybrid native-skill revise; surface if it stalls |
| `slash_command` | **Step 3b-cmd** — invoke it if the command/backing skill is installed this session (e.g. global GSD), else surface |
| `surface` | **Step 3b-surface** — always hand the user the pre-filled command, then stop |

If findings span a native-owned archetype AND a direct-edit archetype, handle the direct-edit ones via 3a and the native one via the appropriate 3b variant (3b-skill / 3b-cmd / 3b-surface per the route's `invoke`) in the same iteration; note both in the eventual Surface message. Each handler gets only its own findings: bind every finding to its document by the document path its `Location` leads with (both reviewer templates require that path whenever more than one file is under review, references/reviewer-prompts.md) and to that document's archetype (its `<path>=<archetype(s)>` line when documents differ; on a fused document, the `[<archetype>]` the Location names after the path), copy the report's `### Status:` line and that handler's findings verbatim into `$RUN_TMP_DIR/iter<N>-<route>.md`, and pass that file as the handler's report (the fixer's `Review report`, a route's `{report_path}` or note) with `<DOC_PATHS>` narrowed to the documents its findings locate. A finding whose document or archetype cannot be told (no leading path in a multi-document run, or no archetype on a fused document whose archetypes resolve to different routes) goes to neither handler: surface it to the owner, never dispatch it. Dispatch these **sequentially, never in parallel**: run the Step 3a generic fixer to completion first (with its Step 4 parse), then the 3b native revise (with **Step 3c** when its route declares `validate: agent:<name>`). Two handlers editing the same document concurrently would corrupt it. If they target entirely separate files you may still keep them sequential for simplicity. **Each handler returns its result to Step 3 and never advances the iteration itself.** A result that ends the loop (Escalation Required, No Edits, Failure, Needs Input, a handoff, a blocked validator) ends the round there: the remaining handlers do not run, and the Surface message names the edits already made. When every authorized handler has returned without ending the loop, Step 3 increments iter exactly once and re-reviews (Step 1).

#### Step 3a — Generic fixer (direct edit)

Dispatch through SKILL.md Step 1's **fresh-context delegation** (a new agent, empty context):

- On Claude Code: `subagent_type`: `general-purpose`, `model`: `sonnet`. On another host: its own
  subagent tool, session default model (say so in the Surface message).
- `description` (where the tool takes one): `ai-kit-spec-review iter N fixer`
- `prompt`: template below
- No delegation tool on this host: never fix inline in this conversation; go to Step 3b-surface
  with the report path instead (the user edits, then re-runs).

Fixer prompt template — use VERBATIM, substituting `<FIXER_SKILL_MD>` with the
`ai-kit-spec-review-fixer/SKILL.md` beside `CHECKLIST_SKILL_MD`'s skill directory (same
`skills/` parent):

```
You are the fixer.

Step 1: Load the ai-kit-spec-review-fixer skill and follow it exactly: invoke it by name with
your skill tool, or, with none, Read <FIXER_SKILL_MD>.

Inputs:
- Document(s) to edit: <DOC_PATHS>
- Review report: <EFFECTIVE_REPORT_PATH>
- Codebase root: <CODEBASE_ROOT>
- FRAMEWORK_PROFILE_PATH: <FRAMEWORK_PROFILE_PATH>  (a file path on disk, or "none"). If a path,
  Read it and respect the framework's conventions while editing — keep EARS phrasing / RFC-2119
  SHALL, the task-checkbox format, delta section headers; never introduce implementation detail
  into a spec/requirements doc the framework keeps behavior-only.
- Mechanical re-pass: <MECHANICAL_TITLES>  (only on a re-pass after classify-disagreements: process only these findings and leave every other finding of the report as it is; your escalation conditions still take precedence; omit this whole line otherwise)

Apply the skill. Edit the document(s) in place. Emit the structured Fix Summary at the end.

Do not assume any context outside what you read. Do not edit the review report.
```

`<MECHANICAL_TITLES>` is the fixer list of `classify-disagreements`, finding titles joined by "; ".

Then parse the fixer's Status (Step 4).

**Whenever the Fix Summary lists an escalated or skipped finding** (whatever its Status line), and at a cap stop, run `classify-disagreements` on `EFFECTIVE_REPORT_PATH` and the Fix Summary saved as `$RUN_TMP_DIR/iter<N>-fix.md`; SKILL.md Step 4 routes its items by the rules in [lane-failure.md](lane-failure.md#jev-classes-and-sizing) (command in [lane-failure.md](lane-failure.md#commands)). A re-pass is one more Step 3a dispatch with the same direct-edit report and documents as the pass it follows, its `Mechanical re-pass:` line naming the `fixer` titles; the fixer's own escalation conditions still take precedence over jev's class. jev receives summaries only: never code, diffs, file contents, config values or secrets.

#### Step 3b-skill — Hybrid native-skill revise (surface if it stalls)

The document was authored by a framework skill that owns its house style (superpowers `brainstorming` for design docs, `writing-plans` for plans). Revise through that skill so the structure survives — but those skills can expect human input, so fall back to surfacing if the subagent stalls.

Dispatch through fresh-context delegation, as in Step 3a (on Claude Code `general-purpose`,
`model: sonnet`). It needs the host to load `<SKILL_NAME>` by name; a host without that skill or
a skill tool goes to Step 3b-surface.

- `description` (where the tool takes one): `ai-kit-spec-review iter N native-revise (<SKILL_NAME>)`
- `prompt`: VERBATIM, substitute `<SKILL_NAME>` (the route's `invoke` minus the `skill:` prefix, e.g. `superpowers:writing-plans`), `<DOC_PATHS>`, `<EFFECTIVE_REPORT_PATH>`, `<CODEBASE_ROOT>`:

```
You are revising an existing document to address review findings, using its own authoring skill.

Step 1: Load the skill named "<SKILL_NAME>" with your skill tool and follow it.

Step 2: This is a REVISE, not a fresh authoring pass. Your inputs:
- Document(s) to revise (edit in place, SAME path): <DOC_PATHS>
- Review report (the findings to resolve): <EFFECTIVE_REPORT_PATH>
- Codebase root for grounding: <CODEBASE_ROOT>
Treat the existing document plus the findings as your brief. Regenerate or edit the document so
every CRITICAL and HIGH finding is resolved, preserving the skill's required structure and house
style. Write the result to the same path(s).

Step 3: If you cannot proceed without interactive input a human must provide (the skill needs a
decision you cannot infer from the document or the findings), DO NOT guess. Stop and emit:
### Status: Needs Input
followed by the one or two questions you would ask.
Otherwise, when done, emit exactly one of:
### Status: Edits Applied
### Status: No Edits

Do not assume any context beyond what you read.
```

Parse the subagent's `### Status:` line:

| Status | Action |
|---|---|
| `### Status: Edits Applied` | If the route has `validate`, run Step 3c; then return the result to Step 3, which advances the iteration once. |
| `### Status: Needs Input` | The authoring skill stalled. Go to **Step 3b-surface**, including the subagent's questions, and stop the loop. |
| `### Status: No Edits` | Loop ends. Surface (escalation — the authoring skill made no progress). |
| No Status line, or any other status | Loop ends. Surface failure: "Native-revise subagent did not emit a Status line." (or quote the unrecognized status). Never re-review. |

**The fold finding.** A superpowers plan's `Plan has no fold step` finding (reviewer tag `fold-check`, from SKILL.md's fold check) has the Location `<doc path>, last ### Task`, so it binds to that one plan like any other finding: it reaches `superpowers:writing-plans` in that plan's handler report only, and two plans missing the step give two findings. Its Required part names the exact final task to add, `### Task <n>: Fold the plan's commits (ai-kit-commit-fold)` with one checkbox, so the authoring skill adds it in the plan's own style. The generic fixer gets no fold rule.

#### Step 3b-cmd — Native slash-command revise

Following the route's `command` (substitute `{phase_id}`/ids from the doc path or roadmap):

**A `slash_command` route is "available" when the command — or the skill/agent backing it — is
installed and invocable this session.** This is decided by what is INSTALLED, not by whether the
project itself uses that framework: GSD installed at the user/global level (its `gsd-*` skills and
`/gsd-plan-phase` command present this session) makes the route invocable even when reviewing a
plan in an unrelated repo. Check for the backing skill/command (e.g. `gsd-plan-phase`) before
deciding.

- **Available** → before invoking, check the command's write and commit scope in the installed
  workflow and its configuration (GSD's planner may regenerate every plan of the phase, update
  `STATE.md` and `ROADMAP.md`, and commit them when `commit_docs` is on). When that scope reaches
  beyond the named documents, or commits, invoke only after the owner's explicit yes to that scope;
  without it, or when the host cannot hold the command to the approved scope, go to
  **Step 3b-surface** instead. Then invoke it, passing the findings: substitute the report path for a `{report_path}`
  placeholder if the `command` has one; otherwise append a trailing `(findings: <EFFECTIVE_REPORT_PATH>)`
  note. Invoke via the slash command if a slash-command tool exists, else via its backing skill
  through the host's skill tool (e.g. `gsd-plan-phase`). The command must end successfully and the
  named document must be regenerated (its content changed since the review); when it fails, refuses
  (a closed GSD phase's gate exits without regenerating) or regenerates nothing, stop the loop, keep
  the report and surface the command's reason (for a closed phase, point the owner to a follow-up
  phase or issue, not another `--reviews` run); never validate the old file as if it were rewritten.
  Then if the route has `validate` run **Step 3c**, then return the result to Step 3, which advances
  the iteration once.
  **A `--reviews` command (the GSD route) reads its findings only from the phase's `REVIEWS.md`.**
  GSD's planner exits with `No REVIEWS.md found` when the phase folder has none
  (`plan-phase/steps/reviews-prerequisite.md`), and the trailing note never reaches it. Invoke it
  only when that file exists and already carries this report's findings (the owner wrote or
  approved it); never write or overwrite `REVIEWS.md` yourself. Otherwise go to **Step 3b-surface**,
  and say that the planner needs `REVIEWS.md` (`/gsd-review --phase <N>` writes it).
- **Not installed this session** (no command and no backing skill) → fall back to **Step 3b-surface**.

#### Step 3b-surface — Surface the native command

Hand the user the pre-filled `command` + the report path and **stop the loop** (do not edit files yourself). Use the Surface "Native revise handed off" row.

A `--reviews` route (GSD) reads findings only from the phase's `REVIEWS.md` (`<NN>-REVIEWS.md` or a plain `REVIEWS.md` in the phase folder), so when that file is missing or does not carry this report's findings, the command alone does nothing: name the file's path and ask the owner to put this report's findings there (or to approve the file once it carries them, or to run `/gsd-review --phase <N>`, which writes it) before rerunning the planner; never write it yourself. Example: `This plan is owned by the GSD planner, which reads findings only from .planning/phases/<phase dir>/<NN>-REVIEWS.md (missing, or without this report's findings). Put the findings of EFFECTIVE_REPORT_PATH there, or run /gsd-review --phase 2 to write it; then run /gsd-plan-phase 2 --reviews and re-run /ai-kit-spec-review.`

#### Step 3c — Validate the regenerated doc (route has `validate: agent:<name>`)

The native planner regenerated the doc; validate with the framework's own checker before spending another review iteration. Dispatch the named agent (on Claude Code, the `Agent` tool with this `subagent_type`). A host that cannot dispatch a named agent skips this step: return to the calling route and say "validator `<name>` not run on this host" in the Surface message — never claim the plan was validated.

- `subagent_type`: `<name>` (from `validate: agent:<name>`, e.g. `gsd-plan-checker`)
- `description`: `ai-kit-spec-review iter N validate (<name>)`
- `prompt`: `Validate the regenerated document(s) at: <DOC_PATHS>. Codebase root: <CODEBASE_ROOT>. Report whether the plan is sound and ready, or list the blocking problems.`

- Validator reports **sound** (or the host skipped it) → return to the calling route, which returns the result to Step 3 (Step 3 advances the iteration once).
- Validator reports **blocking problems** → **surface** to the user with the validator's reasons + the report path, and stop the loop (do not burn a review iteration on a plan its own checker rejects). Do **not** feed the validator's text into the reviewer prompt — the reviewer stays clean-context. (use the Step 5 "Validator blocked" row)
