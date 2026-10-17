# Step 3 — Apply findings (full detail)

### Step 3 — Apply findings (when Issues Found, iter < cap)

The reviewer's report is already at `EFFECTIVE_REPORT_PATH` (Step 1.5) — no separate save needed here.

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

If findings span a native-owned archetype AND a direct-edit archetype, handle the direct-edit ones via 3a and the native one via the appropriate 3b variant (3b-skill / 3b-cmd / 3b-surface per the route's `invoke`) in the same iteration, then re-review once; note both in the eventual Surface message. Dispatch these **sequentially, never in parallel**: run the Step 3a generic fixer to completion first, then the 3b native revise. Two handlers editing the same document concurrently would corrupt it. If they target entirely separate files you may still keep them sequential for simplicity. After ANY successful native revise (3b-skill / 3b-cmd) whose route declares `validate: agent:<name>`, run **Step 3c** before re-reviewing.

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

Apply the skill. Edit the document(s) in place. Emit the structured Fix Summary at the end.

Do not assume any context outside what you read. Do not edit the review report.
```

Then parse the fixer's Status (Step 4).

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
| `### Status: Edits Applied` | If the route has `validate`, run Step 3c; then increment iter and re-review (Step 1). |
| `### Status: Needs Input` | The authoring skill stalled. Go to **Step 3b-surface**, including the subagent's questions, and stop the loop. |
| `### Status: No Edits` | Loop ends. Surface (escalation — the authoring skill made no progress). |
| No Status line | Loop ends. Surface failure: "Native-revise subagent did not emit a Status line." |

#### Step 3b-cmd — Native slash-command revise

Following the route's `command` (substitute `{phase_id}`/ids from the doc path or roadmap):

**A `slash_command` route is "available" when the command — or the skill/agent backing it — is
installed and invocable this session.** This is decided by what is INSTALLED, not by whether the
project itself uses that framework: GSD installed at the user/global level (its `gsd-*` skills and
`/gsd-plan-phase` command present this session) makes the route invocable even when reviewing a
plan in an unrelated repo. Check for the backing skill/command (e.g. `gsd-plan-phase`) before
deciding.

- **Available** → invoke it, passing the findings: substitute the report path for a `{report_path}`
  placeholder if the `command` has one; otherwise append a trailing `(findings: <EFFECTIVE_REPORT_PATH>)`
  note. Invoke via the slash command if a slash-command tool exists, else via its backing skill
  through the host's skill tool (e.g. `gsd-plan-phase`). Then if the route has `validate` run **Step 3c**,
  then increment iter once and re-review (Step 1).
- **Not installed this session** (no command and no backing skill) → fall back to **Step 3b-surface**.

#### Step 3b-surface — Surface the native command

Hand the user the pre-filled `command` + the report path and **stop the loop** (do not edit files yourself). Use the Surface "Native revise handed off" row. Example: `This plan is owned by the GSD planner. Run: /gsd-plan-phase 2 --reviews  (findings: EFFECTIVE_REPORT_PATH), then re-run /ai-kit-spec-review.`

#### Step 3c — Validate the regenerated doc (route has `validate: agent:<name>`)

The native planner regenerated the doc; validate with the framework's own checker before spending another review iteration. Dispatch the named agent (on Claude Code, the `Agent` tool with this `subagent_type`). A host that cannot dispatch a named agent skips this step: re-review (Step 1) and say "validator `<name>` not run on this host" in the Surface message — never claim the plan was validated.

- `subagent_type`: `<name>` (from `validate: agent:<name>`, e.g. `gsd-plan-checker`)
- `description`: `ai-kit-spec-review iter N validate (<name>)`
- `prompt`: `Validate the regenerated document(s) at: <DOC_PATHS>. Codebase root: <CODEBASE_ROOT>. Report whether the plan is sound and ready, or list the blocking problems.`

- Validator reports **sound** (or the host skipped it) → return to the calling route, which increments iter once and re-reviews (Step 1).
- Validator reports **blocking problems** → **surface** to the user with the validator's reasons + the report path, and stop the loop (do not burn a review iteration on a plan its own checker rejects). Do **not** feed the validator's text into the reviewer prompt — the reviewer stays clean-context. (use the Step 5 "Validator blocked" row)
