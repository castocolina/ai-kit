---
created: 2026-10-30T02:03:59Z
title: Unify the review/execute lane TOML, add effort and escalation, classify with jev
area: tooling
severity: major
resolves_phase: 36
files:
  - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
  - skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py
  - skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py
  - skills/ai-kit-spec-review/references/cross-ai.mjs
---

## Problem

The TOML that lists the models of the review and execute lanes should be reviewed for how it is
built. Today `config_io.py` writes `[[reviewers]]` for reviewers; the owner saw a project where
the same `[[reviewers]]` table is used whether the lane is a reviewer or an executor. Whether this
repo should adopt one table with a role field is an open design question, not a settled one.

Wanted changes (owner, 2026-10-30):
1. **Effort support per target model.** Detect whether the target model supports an effort setting
   before passing one; do not pass it blindly. How support is detected is unverified (model catalog
   metadata versus a live probe) and must be checked per runtime first.
2. **Execution and review script adjustments.** The caller states the role (review or execute) and
   passes the runtime, the model and the effort together.
3. **Runtime escalation.** A flag says whether a lane may escalate to another runtime, following the
   declared order. This interacts with the owner rule "never switch harness, provider or model on
   failure" and with the Phase 25/25.1 retry ladder, so escalation must be opt-in per lane and
   off by default.
4. **Model escalation inside one runtime.** A separate flag for stepping up to another model of the
   same runtime.
5. **jev classification of the input.** The review and execute skills classify the incoming prompt
   through the jev decision system to choose the effort level the task needs (advisory only, as
   everywhere jev is used).
6. **jev classification of the output.** Classify a review or execute result: did it really
   succeed; do the reported issues need another round or can the flow continue; is the severity
   right given the kind of problem (runtime, scripts, tests: unit, e2e, integration, mutation),
   whether it is reproducible, whether it reaches the end user, and whether the code is an MVP or
   already in production.

## Solution

TBD. Start with a spike on how each runtime exposes effort and how the model catalog could record
it, then a design pass on the TOML shape (one table with a role versus two), then a phase plan.
jev output classification needs a rubric and a no-network test path (no paid remote calls by
tasks). Related: the atomic decision-system skills todo (2026-10-18) and the cross-AI executor
retry ladder (Phase 25.1).

## Addendum 2026-10-30: the decision system is optional and switchable

The jev classification (items 5 and 6) must never be a hard dependency:
- **Backends are optional.** Local Laya, or the remote jev client against TypeSafe or OpenCode Zen
  (paid or free). The system must also allow swapping to another classification system (OpenAI,
  Vercel or one of the many that have appeared), so the backend is a pluggable seam, not a fixed
  choice.
- **A knob in the TOML turns classification on or off** (and names the backend). Some machines will
  not have a backend or will not be authorized to use one.
- **Skill flow, first step:** check whether the knob exists in the TOML. If it does not, ask the
  user explicitly whether to use a classification system ("System One" or similar wording) and
  record the answer in the TOML. With the knob off, the skills behave exactly as today.
- **Then verify reachability without printing anything secret:** for Laya, that its local URL is
  configured and answers; for a remote server, that both the URL and a key are present (report
  presence only, never the key). A missing piece degrades to "classification off" with a visible
  note, not to a failure.
- Consent rules stay as they are: no paid remote calls by tasks or executors; remote use needs the
  user's consent recorded by that knob.

## Related backlog

The xai execute/review script lessons (script versus agent causes, a bundled-script skill, role and output classification) are captured as backlog 999.15; see its LESSONS file.
