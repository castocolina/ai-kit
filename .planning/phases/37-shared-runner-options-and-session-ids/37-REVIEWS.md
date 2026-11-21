---
phase: 37
cycle: 1
reviewers: [referee-one]
reviewed_at: 2026-11-21T07:52:30-03:00
plans_reviewed: [37-01-PLAN.md, 37-02-PLAN.md, 37-03-PLAN.md, 37-04-PLAN.md, 37-05-PLAN.md, 37-06-PLAN.md, 37-07-PLAN.md, 37-08-PLAN.md, 37-09-PLAN.md, 37-10-PLAN.md, 37-11-PLAN.md, 37-12-PLAN.md, 37-13-PLAN.md, 37-14-PLAN.md, 37-15-PLAN.md, 37-16-PLAN.md, 37-17-PLAN.md, 37-18-PLAN.md, 37-19-PLAN.md, 37-20-PLAN.md, 37-21-PLAN.md, 37-22-PLAN.md, 37-23-PLAN.md, 37-24-PLAN.md, 37-26-PLAN.md]
models:
  referee-one: "router-env/my-referee-one"
model_sources:
  referee-one: "pinned"
---

# Cross-AI Plan Review — Phase 37

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

> Note: one reviewer lane only (referee-one, owner instruction 2026-11-20); its findings are single-reviewer.

## Cycle 1 (referee-one)

### Review conditions (cycle 1)

- 37-25 was created in the fix pass by splitting the failure-path cases out of the reviewed 37-20 (lane budget); its
  content was reviewed as part of 37-20 in batch H and was not reviewed again on its own.
- Reviewer: referee-one (opencode, `router-env/my-referee-one`), probed READY at 06:44; review-lane invoke in 9
  batches (A 37-01/02/11, B 03/04/05, C 06/07/10, D 08/09, E 13/15, F 12/14, G 16/18, H 17/19/20, I 21-24), every
  batch exit 0 in 69-119 s, 07:32-07:44. Batches ran as soon as their planner had written its plans; three plans
  (37-10, 37-19, 37-20) did not exist yet when batches A, D, E, F and G ran, so 'missing plan' findings are moot.
- One targeted fix pass by the plan authors answered the findings (accepted items applied in place, each rejected or
  recorded item carries a 'Review c1 (disposition):' line in the plan's must_haves.truths). Cycle 2 was not run: the
  run's TIME RULE caps planning at 90 minutes; the plan-checker checked the fix pass instead.

### Cycle 1 triage (orchestrator, 2026-11-21) — how the plans answer referee-one's cycle 1 findings

Review files: `tmp/p37-review/c1/run/<batch>/gsd-review-referee-one.md` (batches A 01/02/11, B 03/04/05, C 06/07/10,
D 08/09, E 13/15, F 12/14, G 16/18, H 17/19/20, I 21-24). "Moot" = raised because a plan file did not exist yet when the
batch ran (37-10, 37-19, 37-20 were still being written).

**Cross-cutting rule (STUB RULE, fixes every "new module not registered" finding).** 37-02 Task 1 creates EVERY new test
module of the phase as a stub (mirroring `.planning/phases/36-spec-config-as-the-hub/36-01-PLAN.md` Task 1: a docstring naming
the filling plan and one `unittest.TestCase` whose single test is skipped with the reason `filled by plan 37-NN`), runs
`python3 tools/gen_test_groups.py` once and stages `Makefile` and `.pre-commit-config.yaml` (the one full unit+arch commit of
the phase before 37-18). Stubs: `tests/test_runner_settings_argv.py` (37-04), `tests/test_runner_status_group.py` (37-06),
`tests/test_runner_claude_exec.py` (37-10), `tests/test_cross_ai_render_sync.py` (37-11), `tests/test_runner_flags.py`
(37-12), `tests/test_runner_skills_argv.py` (37-13), `tests/test_runner_preview.py` (37-14), `tests/test_runner_mcp_argv.py`
(37-15), `tests/test_runner_describe.py` (37-17), `tests/test_runner_facts.py` (37-18), `tests/test_runner_host_protocol.py`
(37-19), `tests/test_cross_ai_settings_text.py` (37-21, only if new), `tests/test_cross_ai_docs_text.py` (37-22), plus any
module 37-20 adds. Every other plan FILLS its stub (replaces the whole file) and never touches `Makefile`,
`.pre-commit-config.yaml` or `tools/gen_test_groups.py` output; 37-18 still regenerates the listings because it deletes
`tests/test_ai_kit_spec_exec_formula_e2e.py` (its exception-set entry in `tools/run_unittest_parallel.py`, if any, goes in the
same commit).

**Execution note (same-wave findings in E, G):** plans of one wave run one after another in the one checkout (the
orchestrator's execution order), so a same-wave plan never tests a half-edited runner. Recorded, no plan change.

**37-01:** accepted: kill only the process groups this spike started (pgids recorded under `tmp/run-2026-11-19/p37-spike/`)
and close only tab ids it created; reuse `tools/record_cli_help.py`'s environment scrub (`OPENCODE_*` and other host
overrides removed, cwd the scratch home) for every capture; `secret_shapes.redact(text, marker)` with an explicit marker;
`out/` mode 0700, raw probe output removed by 37-01 itself after it copies only the help and version files into
`out/help/` (the 37-02 handoff); a failed capture for one host writes `help-refresh: not recorded <host>` and the spike
continues; the audit adds the copilot root; the consent line must name the residual risk (an unsandboxed model in the
scratch repo with full permissions under the real HOME). Rejected: none.
**37-02:** accepted: the flag test is command-aware (each formula's flags checked against the help file of the command that
takes them: codex `exec` -> `exec-help.txt`, `exec resume` -> `exec-resume-help.txt`, opencode `run` -> `run-help.txt`, main
command -> `help.txt`), reusing the pattern of `tests/test_opencode_help_flags.py:30-43`; a missing subcommand record is a test
failure, never a silent union; the STUB RULE above. Rejected with reason: refreshing phase 35's opencode fixtures (dated
2026-11-20, one day old; phase 35's own test owns them; a refresh happens with that test). Deferred: label-version vs
`meta.json` equality (recorded open; labels name the 2026-11-21 read).
**37-11:** moot: 37-10 missing. Accepted: normalize only the generated pi session UUID in the no-id case (no global UUID
scrub); state the PATH precisely (the node directory is appended, `--print-argv` never spawns a host); STUB RULE (no listing
edit, no full-groups commit).
**37-08:** accepted: the floor also checks the model resolved from `CONFIG.models` after resolution; option maps are
null-prototype objects (or `Object.hasOwn` lookups) and a test covers a runtime named `constructor`; a test with an unusual id
reaching the spawn for every runtime with a formula; scratch cleanup on every exit path. Kept with reason: one trailing
bracket only (D-06: the floor is "the existing ASCII charset"; a second bracket is outside it).
**37-09:** accepted all: retry with a `{session}` slot reuses the same filled argv (no fresh id), no slot shows `session=-`,
slot-specific proof (the exact substituted element) instead of a substring check, malformed JSON gives a named content-free
usage error, the wording distinguishes the argv-file boundary (cwd tree) from the command's resolution (PATH, by D-05), an id
whose row lacks the selected role's formula may use `--argv-file`, tests for each.
**37-13:** moot: 37-10 missing. Accepted: `confirmReport` checks the prompt actually composed and sent (one composition
function used by the run path and `--print-argv`); the copilot retry oracle accounts for `RESUME_MSG` on later rungs while
proving the skill bytes survive; expected forms come from one table in the test module that the executor fills from
`37-SPIKE.md`'s label lines (mechanical, both branches covered); reader errors are redacted before printing; a static check
that the runner source names no host skill or MCP settings path. Rejected with reason: a read tripwire on the fake config
dir (no portable read sentinel; the static check plus byte-equality covers the prohibition).
**37-15:** accepted: `readCallFile(..., { mode: 0o077 })`; a constant content-free error for MCP parse failures and a
duplicate-key error naming no value; an empty `mcpServers` refusal; textual key order kept by `strictJson`; the fake host
reads the file at the given path and prints only the server count; STUB RULE. Rejected with reason: snapshotting the file
(locked: the host gets the caller's file by its absolute path, never a re-serialised copy; the file is run-scoped, caller
owned and mode-checked; the threat model records the replace-after-check risk as accepted).
**37-12:** moot: 37-10 missing. Accepted: a positive timeout in the tracer; `tests/test_curated_config_script.py:61-66`
updated to 9 with a regression test that an edited version-8 runner is not ready; `context` and `session_id` reach
`spec_with_effort` from the lane (state the source; if no lane key exists in phase 36's lane settings, say so and pass
`None`, the adoption is Phases 40 and 41); STUB RULE.
**37-14:** accepted: baseline lines removed in the task that removes their hits; the preview requires exit 0; the preview
runs in the same cwd as the call it qualifies; context and session fields preserved; the grep test's claim narrowed to the
patterns it detects. Recorded risk: lane budget.
**37-16:** accepted: stored-config validation uses the runner floor including one trailing bracket, while the hook builder
keeps `HOOK_TOKEN_RE` (two different boundaries, both stated and tested); the `apply-execution` precedence spelled out with no
undefined variable; the completeness claim narrowed to model-shape validation (the `RUNNER_IDS` gate is the recorded gap).
**37-18:** accepted: freshness enforced at the routing boundary (a fact whose template sha differs from the current one is
treated as absent); `detect-runtimes --if-stale` refreshes the fact when the template sha changed; a describe that did not
exit 0 or has no template hash is never stored as a refusal fact and is retried at the next detection; scoped grep checks per
task; the constant and the drift test removed in one green commit; a synthetic node path token. Recorded risk: lane budget
(full-groups commit).

**37-03:** accepted: the forbidden-bit mask `0o077` is the one interface (callers pass it; tests cover group and other read
and write bits); open with `O_RDONLY | O_NONBLOCK`, `fstat`, refuse a non-regular file (a FIFO case under a deadline); a
dev/ino comparison between the realpath's stat and the fd's fstat closes the check/open swap; the `codex-effort-bogus` case
edit lands in the task that changes the parse. Rejected with reason: "parsed flags silently unused between waves 2 and 3"
(intermediate commits are never shipped; the unit ships after 37-23; every flag is reported from 37-04 on).
**37-04:** accepted: the claude review closure becomes `(m, c)` with a no-setting and an effort dry run; the `cross-ai:
model-id` line is control-stripped and key-shape redacted (planted-key test); `confirmReport` uses a proof per setting (model
slot, adjacent flag pair, config pair, composed id in the model slot, the role's closure) or narrows its claim; `statusGroup`
redacts `skill:`/`mcp:` members; depends_on adds 37-02; the test child env sets `AI_KIT_REFUSE_REAL_HOME=1`; STUB RULE.
**37-05:** accepted: the final `ctx.sid`/`newSessionArgv` shape is stated for 37-07 to target; the claude no-resume test row is
named for 37-10 to flip; the run path adopts the planned first argv in 37-06 (no session reported applied that the spawn does
not use); depends_on adds 37-01 and 37-02; a probe whose evidence cannot be represented with a recorded flag leaves the form
unverified.
**37-06:** accepted: the first attempt of a real run uses the planned argv (sessionId and resume decision passed into
`runCli`); exit-trap cleanup of scratch dirs; STUB RULE. Recorded risk: lane budget.
**37-07:** accepted: a persisted `last_sid` is validated before re-entry, logging or saving (regression test); a chosen row's
pinned retry reuses the create-or-continue form with the same id (copilot transient-failure test); the unshown-id case checks
the saved record and a persisted invalid id; exit-trap cleanup; targets 37-05's resulting code.
**37-10:** accepted: 37-05's claude session test row flipped in the same commit and run; `CLAUDE_EXEC_PROBE_RECORD` flips only
the permission-flag label, `execLabel` verified only when the spike records the exact formula; exit-trap cleanup; STUB RULE.
**37-21:** accepted: parent directory created before the config write; the eval input carries the model id; STUB RULE.
**37-22:** accepted: moved to wave 17 after 37-21 (37-23 wave 18, 37-24 wave 19); MCP flags documented as formula flags, not
`reviewExtras` entries (37-15 keeps `reviewExtras` unchanged); exact per-runtime allowlist mapping with mutations. The reviewed
text predated the planner's final version; the committed plan is authoritative.
**37-23:** accepted: read-only verification after the live render; case names compared with timing keys; only the documented
`_upgrade_config` migrations allowed; hunk-based grok scan with listed expected edits; scratch HOME and XDG for the recorder.
Recorded risk: lane budget.
**37-17:** accepted: `formula_labels` and `listing_label` beside the kept `formulas` booleans (37-18 reads them), labels from
the recorded help; explicit staging and stub-fill wording.
**37-19:** accepted: escaped slash in `HOST_PATH_SAFE` and a whole-runner parse check; launch.sh never holds prompt text
(an argv prompt is read from the prompt file before deletion; sentinel test); the clean re-exec marker carries the run token;
arch-rule non-vacuity for a stray spawn and a dynamic verb; every claimed protocol field compared to the fixture; exact
commit boundaries.
**37-20 (split into 37-20 and 37-25):** accepted: fail closed on ambiguous `pane run` admission (headless fallback only on a
definite error with no `pid` file); tab id and non-secret `run.json` kept until close is confirmed; the launcher establishes
its own process group and the runner group-signals only on a matching pgid and start time; normalized pair comparison;
create-refusal, lost-create and dead-before-pid cases; finalizer installed before `tab create`; two overlapping hosted calls.
The failure-path cases move to the new plan 37-25 (wave 16) so each plan fits the lane.
**37-24:** accepted: a final orchestrator `make test` gate after the judge fixes (df check, TMPDIR under the repo's tmp/,
cleanup) and a re-run of the grok scan; in-order material-change comparison with a reordered-lines case; scratch HOME and XDG
exported before every driver; the tmp/judge-36 driver recovery path stated (stop and report).

### referee-one

#### Batch A (37-01, 37-02, 37-11)

### Plan review

**Scope:** GSD implementation plans 37-01, 37-02 and 37-11. I read the plans from disk and checked the cited source and relevant neighboring plans. This was a read-only review; I did not run tests, make targets, or live host probes.

**Status: Issues found — revise before execution.**

#### 37-01

##### Summary

The spike has a useful consent gate and records unverified defaults when live probes do not run. Its cleanup and isolation provisions, however, do not yet support its safety claims, and one prescribed probe calls the redaction helper with the wrong signature.

##### Strengths

- The anchored consent check distinguishes an actual permission line from a decision mentioning permission, and specifies what to record when consent is absent: `.planning/phases/37-shared-runner-options-and-session-ids/37-01-PLAN.md:138-146`.
- The no-probe defaults and machine-readable handoff give later plans a way to preserve uncertainty rather than infer success: `.planning/phases/37-shared-runner-options-and-session-ids/37-01-PLAN.md:19-29`.
- The help refresh uses a scratch HOME, consistent with the existing recorder’s approach: `.planning/phases/37-shared-runner-options-and-session-ids/37-01-PLAN.md:114-119`; `tools/record_cli_help.py:26-42`.

##### Concerns

- **HIGH — Cleanup can kill processes this spike did not start.** Task 3 selects *every* process whose current directory is under the fixed spike path and sends signals without establishing ownership, recording child PIDs or verifying process identity: `.planning/phases/37-shared-runner-options-and-session-ids/37-01-PLAN.md:182-184`. A pre-existing process or another agent working there can be terminated. The same step proposes closing any matching `p37-spike` tab, rather than only the ID created by this run.
- **HIGH — Consented model probes can modify real host state, despite the plan’s no-write claim.** The permission probes run an unsandboxed model with real HOME and full-permission flags: `.planning/phases/37-shared-runner-options-and-session-ids/37-01-PLAN.md:146-155`. Having the scripts themselves write only to `tmp/` does not confine the model or host. The audit is detection after the fact, not prevention; it also checks mtimes of existing files and omits a Copilot root: `tmp/run-2026-11-19/audit_real_config.py:14-40`.
- **HIGH — The intended scratch environment is incomplete.** The plan sets HOME and XDG variables but does not clear inherited host-specific config and home overrides: `.planning/phases/37-shared-runner-options-and-session-ids/37-01-PLAN.md:115-118`. The existing recorder additionally removes inherited `OPENCODE_*` variables and runs captures with the scratch home as cwd: `tools/record_cli_help.py:26-42,58-67`. The planned calls run from the checkout root, so HOME alone does not establish the claimed isolation.
- **HIGH — The error-channel probe cannot use the specified redaction call as written.** It calls `secret_shapes.redact` without specifying a marker: `.planning/phases/37-shared-runner-options-and-session-ids/37-01-PLAN.md:153`. The helper requires both `text` and `marker`: `skills/ai-kit-spec-review/ai_kit_spec/secret_shapes.py:99-102`.
- **MEDIUM — Sensitive probe output is retained with no specified private permissions or final removal.** The plan keeps `out/`, including raw host probe stdout and stderr, for 37-02: `.planning/phases/37-shared-runner-options-and-session-ids/37-01-PLAN.md:146,183-186,236-239`. Plan 37-02 copies only the help and version files and does not remove this directory: `.planning/phases/37-shared-runner-options-and-session-ids/37-02-PLAN.md:143-148,220`. The document scrub does not protect the raw retained output.
- **MEDIUM — Failure handling contradicts the fallback.** A failed help capture is simultaneously a task failure and an allowed `help-refresh: not recorded` handoff: `.planning/phases/37-shared-runner-options-and-session-ids/37-01-PLAN.md:119-125`. It is unclear whether the orchestrator should stop or continue to the fallback used by 37-02.
- **MEDIUM — Scope of same-wave check:** 37-01 is the only listed wave-1 plan, so I found no same-wave file overlap in the supplied map.

##### Suggestions

- Track the exact processes and tab IDs this invocation creates; verify identity before signaling or closing them. Report unrelated matching resources without touching them.
- State explicitly that consent permits the host/model to access real configuration, or use a verified isolation mechanism if the prohibition is intended to be absolute. Expand the audit only as a detection measure, not as proof of non-modification.
- Build a sanitized child environment, select a scratch cwd, specify a redaction marker, and set private permissions on raw captures. Remove them after the fixture handoff on success and failure.
- Make an incomplete refresh a mechanically defined successful fallback or a blocking failure, not both.

##### Risk assessment

**HIGH.** The consent gate is valuable, but the execution and cleanup mechanisms can affect real state beyond the spike’s own artifacts.

##### Ponytail findings

- **MEDIUM — Needed:** the spike is required by D-17 and 0b-9/0b-11. Reuse `tools/record_cli_help.py:26-42,58-73` for environment and capture behavior instead of recreating a weaker variant.
- **HIGH — Cleanup reach:** keeping all raw output is unnecessary for 37-02’s allowlisted help-file handoff. Retain only what that handoff needs, for a bounded period.

#### 37-02

##### Summary

The plan establishes a useful recorded-help regression check and reuses the existing whole-token flag extractor. It does not fully guarantee that the evidence matches the form being claimed, and the planned early registration of all new phase test modules is not present in this version.

##### Strengths

- It reuses `extract_flags` rather than introducing a competing flag tokenizer: `.planning/phases/37-shared-runner-options-and-session-ids/37-02-PLAN.md:136-140`; `tests/test_opencode_help_flags.py:16-20`.
- The plan includes stale-flag, missing-record and scrub non-vacuity cases: `.planning/phases/37-shared-runner-options-and-session-ids/37-02-PLAN.md:165-186`.
- The supplied wave map lists 37-03 alongside it in wave 2, but their declared modified files do not overlap: `.planning/phases/37-shared-runner-options-and-session-ids/37-02-PLAN.md:5-28`; `.planning/phases/37-shared-runner-options-and-session-ids/37-03-PLAN.md:5-8`.

##### Concerns

- **HIGH — The help check can validate a flag in the wrong command context.** `recorded_flags` unions all a host’s help files, then `host_problems` checks a row against that union: `.planning/phases/37-shared-runner-options-and-session-ids/37-02-PLAN.md:139-140`. A flag documented for a top-level command can therefore “verify” its use on a subcommand, or vice versa. The existing opencode test already distinguishes `run` and `models` command flags: `tests/test_opencode_help_flags.py:30-43`. This weakens the 0b-9 claim that the form’s actual invocation is backed by recorded help.
- **HIGH — The fallback omits a required subcommand record.** When the refresh fails, the plan intentionally skips `codex/exec-resume-help.txt`: `.planning/phases/37-shared-runner-options-and-session-ids/37-02-PLAN.md:143-146,155-158`. Yet the runner has a distinct `codex exec resume` formula: `skills/ai-kit-spec-review/references/cross-ai.mjs:1394-1400`; 0b-9 explicitly includes its subcommand help: `.planning/phases/37-shared-runner-options-and-session-ids/37-RESEARCH.md:253-258`. The union-based test can still pass without that evidence.
- **HIGH — The early generated-listing alignment is missing.** Task 1 creates and registers only this plan’s module: `.planning/phases/37-shared-runner-options-and-session-ids/37-02-PLAN.md:125-127,149`. Later 37-04 creates `tests/test_runner_settings_argv.py` without declaring the generated listings among its files: `.planning/phases/37-shared-runner-options-and-session-ids/37-04-PLAN.md:6-9,161-164`. `tests/test_gate_scope.py:570-583` requires every discovered module in both generated listings. This can break intermediate gates and contradicts the review’s locked decision to create all stubs and regenerate once.
- **MEDIUM — Stale opencode evidence is not refreshed.** Plan 37-01 captures current opencode help, but this plan explicitly never copies it: `.planning/phases/37-shared-runner-options-and-session-ids/37-02-PLAN.md:143-146`. The retained fixture is dated 2026-11-20: `tests/fixtures/cli_help/opencode/meta.json:2-8`. The test consequently does not establish that all six rows match the refresh’s dated evidence.
- **MEDIUM — The 1,800-second lane cap is at risk.** Task 1 stages shared machinery and the plan itself estimates a 10–13 minute commit; it then requires two more commits plus four make gates and module checks: `.planning/phases/37-shared-runner-options-and-session-ids/37-02-PLAN.md:48,149,187,220-231`. `tools/run_unittest_parallel.py:217-223` confirms that the two generated-listing files trigger the broad staged selection. Completion within the cap is not demonstrated.
- **MEDIUM — Provenance labels are fixed even if the refresh comes from newer versions.** The copy script records the refreshed versions and date, but later form examples embed fixed host versions and dates: `.planning/phases/37-shared-runner-options-and-session-ids/37-02-PLAN.md:143-148`; `.planning/phases/37-shared-runner-options-and-session-ids/37-04-PLAN.md:153-158`. The flag test compares tokens, not the label to fixture metadata, so a refreshed fixture can be attributed to the wrong version.

##### Suggestions

- Associate each verified form with the command-specific help file that supports it, and add a non-vacuity case where a flag exists only in the wrong subcommand.
- Require a resume-help capture or explicitly leave the resume form unverified when it is unavailable.
- Implement the early stub/listing registration in one plan, and make later plans fill those stubs. Add an explicit dependency where later work assumes the fixture check exists.
- Either refresh opencode consistently or label its fixture and dependent forms as older evidence; validate version/date labels against metadata.
- Split or time the work against the actual lane cap, including hooks, before unattended dispatch.

##### Risk assessment

**HIGH.** The planned check can report unsupported invocation forms as verified, and the generated-listing omission threatens green intermediate commits.

##### Ponytail findings

- **MEDIUM — Needed:** 0b-9 requires recorded help and a non-vacuous flag check. Reuse the command-aware extraction pattern in `tests/test_opencode_help_flags.py:30-43` rather than relying only on a host-wide union.
- **HIGH — Reach:** creating one module is insufficient for the locked phase-wide listing strategy; later test modules and both generated listings must be covered together.

#### 37-11

##### Summary

The byte comparison and mutation tests are well aligned with RUN-06, and the plan reuses the installer’s actual render path. The behavioral matrix depends on a plan that is not present in this checkout, and its normalization and execution constraints need tighter specification.

##### Strengths

- It exercises the real `ensure_runner` and canonical render logic, rather than a second implementation: `.planning/phases/37-shared-runner-options-and-session-ids/37-11-PLAN.md:120-124`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:116-144,265-272,358-368`.
- It includes negative tests for changed bytes and code hidden in the config block, plus a config-only success case: `.planning/phases/37-shared-runner-options-and-session-ids/37-11-PLAN.md:175-191`.
- The supplied map declares no other listed wave-9 plan with overlapping files. The absent 37-10 plan prevents a complete same-wave check, however.

##### Concerns

- **HIGH — A required predecessor is absent from the phase plan set.** This plan anticipates 37-10 in the same wave and accepts either Claude execute outcome: `.planning/phases/37-shared-runner-options-and-session-ids/37-11-PLAN.md:28-30`. No `37-10-PLAN.md` exists in the phase directory, while 37-12 depends on it and assumes plans 37-03 through 37-10 supplied the runner behavior: `.planning/phases/37-shared-runner-options-and-session-ids/37-12-PLAN.md:6,64`. The current Claude row still has `exec: null` and `resume: null`: `skills/ai-kit-spec-review/references/cross-ai.mjs:1420-1425`. The same gap leaves the wave overlap and downstream execution order uncheckable.
- **HIGH — The matrix can conceal a meaningful session mismatch.** `normalized` replaces **every** UUID-shaped token in both stdout and stderr, not just the generated pi fresh-session token: `.planning/phases/37-shared-runner-options-and-session-ids/37-11-PLAN.md:149-160`. A template and copy that emit different UUID session values would compare equal, even though session output is part of the promised behavioral comparison.
- **MEDIUM — The hermetic PATH claim is stronger than the helper provides.** The plan says the child PATH contains only node and git: `.planning/phases/37-shared-runner-options-and-session-ids/37-11-PLAN.md:31-36,143-145`. `runner_env` also appends the real node executable’s directory: `tests/cross_ai_selftest.py:80-89`. That directory may contain host executables. The dry-run branch is intended not to call them, but PATH isolation alone does not prove the prohibition.
- **MEDIUM — Generated listing work conflicts with the locked early-stub approach.** Task 1 creates a new module and regenerates both shared listings: `.planning/phases/37-shared-runner-options-and-session-ids/37-11-PLAN.md:108-110,120-125`. The review’s locked decision assigns that registration to one early plan, after which later plans fill stubs. `tests/test_gate_scope.py:570-583` explains why registration is necessary, but not why this later plan should repeat it.
- **MEDIUM — The 1,800-second cap is not established.** The plan estimates a 10–13 minute first commit, then specifies two more commits, matrix runs and four make gates: `.planning/phases/37-shared-runner-options-and-session-ids/37-11-PLAN.md:84-86,125,160-165,189-204`. It may exceed the cap, especially with the matrix’s per-process 60-second timeout.
- **LOW — The mutation test omits creation of its destination directory.** It instructs writing to `<tmp>/mutated/cross-ai.mjs` without first creating `<tmp>/mutated`: `.planning/phases/37-shared-runner-options-and-session-ids/37-11-PLAN.md:160`. The executor must infer an extra step.

##### Suggestions

- Restore or explicitly replace 37-10 and establish its dependency/wave relationship before execution; do not treat either Claude outcome as a substitute for the missing formula work.
- Normalize only the known nondeterministic generated field, or inject a deterministic UUID source. Add a test proving that differing reported session IDs fail comparison.
- Use a PATH whose contents are actually constrained, or state and verify the narrower dry-run guarantee.
- Fill the early registered stub rather than regenerate listings here; provide the mutation-directory creation step and verify the plan’s total duration against the lane cap.

##### Risk assessment

**HIGH.** The structural test is valuable, but the absent predecessor blocks a complete dependency review, and broad UUID normalization weakens its session comparison.

##### Ponytail findings

- **LOW — Needed and reused:** RUN-06 and 0b-1 justify this test. `cross_ai_script.ensure_runner` and `tools/check_dogfood.py:_outside_config` are appropriate existing seams: `tools/check_dogfood.py:64-74`.
- **MEDIUM — Keep the assertion precise:** avoid a general UUID scrub when only one generated token needs normalization; this preserves the test’s value without adding a new abstraction.

#### Cross-plan coverage and limitations

- **Missing plan artifacts:** the checkout has `37-05-PLAN.md`, although 37-05 is omitted from the supplied wave map. I could not find `37-10-PLAN.md`, `37-19-PLAN.md` or `37-20-PLAN.md` in the phase directory. In particular, 37-12 depends on 37-10, and later plans depend on 37-20. I therefore cannot verify those plans’ edge/prohibition coverage or their same-wave overlaps. The research assigns 0b-2, 0b-3, 0b-4 and 0b-6 to 37-19/20: `.planning/phases/37-shared-runner-options-and-session-ids/37-RESEARCH.md:198-224,233-236`.
- **Coverage is not exhaustive:** I reviewed the three manifest plans and selected dependencies, not every phase plan. I cannot certify that every SPEC edge, prohibition and 0b item lands somewhere, nor that all intermediate commits remain green.
- **No files or scratch artifacts were created.** No test suites, make targets, host probes, or judge runs were performed; the safety and timing concerns above require resolution before unattended execution.

#### Batch B (37-03, 37-04, 37-05)

#### 37-03

##### Summary

The plan covers the requested argument vocabulary and introduces shared readers for the later file-based inputs. It has executable pieces and uses the existing self-test case table, but the reader’s security contract and the per-task commit sequence need correction before unattended execution.

##### Strengths

- The alias-conflict checks run after parsing, so argument order does not change the outcome (`37-03-PLAN.md:129–142`).
- The reader tests cover size boundaries, invalid UTF-8, BOMs, nested duplicate keys and static symlink escapes (`37-03-PLAN.md:174–184`).
- The plan reuses the runner’s existing `migrationScratch()` and pure self-test pattern instead of introducing a separate test framework (`37-03-PLAN.md:169–184`).

##### Concerns

- **HIGH — The MCP permission-mask contract is incompatible with its consumer.** This plan defines `mode` as a forbidden-bit mask and checks `st.mode & mode` (`37-03-PLAN.md:182`). Plan 37-15 passes `{ mode: true }`, not `0o077` (`37-15-PLAN.md:130`). JavaScript converts `true` to `1`, so files such as `0640` and `0604` can pass despite being accessible to other users. The later usage-error tests should fail. Specify and use one interface in both plans, with tests for group and other read **and write** bits.
- **HIGH — The bounded reader can block before it verifies the file type.** The plan opens the path synchronously before `fstat` (`37-03-PLAN.md:182`). Opening a FIFO for reading can block indefinitely before the regular-file check. This affects the later argv, skill and MCP inputs. Use an opening strategy that cannot block on a FIFO, and test it under a deadline.
- **HIGH — Path confinement is subject to a check/open race.** `realpathSync` and `path.relative` precede a separate `openSync` (`37-03-PLAN.md:182`). A path component can be replaced between those operations, so the descriptor is not necessarily the file whose location was checked. `fstat` verifies its type, not its location. Define a race-resistant approach or explicitly constrain the trust model and fail closed when confinement cannot be established.
- **HIGH — The first task commit is not independently green.** Task 1 changes the existing `codex-effort-bogus` case but adds the broader vocabulary cases only in Task 3 (`37-03-PLAN.md:141–144,199–217`), while the objective requires one commit per task (`37-03-PLAN.md:76`). More importantly, the plan exposes new flags that are accepted but silently unused until later plans (`37-03-PLAN.md:49`), contradicting the requested intermediate-state requirement that named settings not silently disappear. Either land parsing with its reporting/behavior atomically, or explicitly gate unavailable flags until their implementation lands.
- **MEDIUM — Wave 2 has a shared-workspace race with 37-02.** There is no declared file-write overlap, but 37-02 reads the runner while creating and running its help test and regenerating shared listings (`37-02-PLAN.md:125–149`), while 37-03 changes that runner and runs broad checks (`37-03-PLAN.md:223–234`). If both execute in the same checkout, checks and commits can observe another executor’s incomplete changes. Isolate the work or serialize integration; also avoid running their heavy suites concurrently.
- **MEDIUM — The 1,800-second budget is at risk.** The plan adds 31 self-tests, edits several distant regions, runs eight shard modules and four broad lint/type gates, and requires three hook-running commits (`37-03-PLAN.md:76,199–234`). There is no measured budget for that combined workload. Split the work or provide measured timing and an explicit stop/retry boundary.

##### Suggestions

- Align `readCallFile` and all callers around a single explicit permission-mask API; test the actual 37-15 call, not only the helper in isolation.
- Add FIFO and replacement-race coverage to the reader’s negative tests.
- Reconcile task-level commits with the requirement for usable, truthful intermediate states.

##### Risk assessment

**HIGH.** The permission mismatch is a concrete secret-file protection failure; the reader can also hang on an untrusted file type.

##### Ponytail findings

- **LOW —** The shared reader and duplicate-key check serve locked R4/R13/R14 requirements; the existing self-test infrastructure is an appropriate reuse (`cross-ai.mjs:6422–6423`, referenced by `37-03-PLAN.md:169–171`).
- **MEDIUM —** Adding all future flags before their behavior exists increases transitional surface. Prefer smaller complete slices if the green-commit and truthful-reporting constraints can be preserved.

---

#### 37-04

##### Summary

The row-driven planner is required by D-11 and gives later plans a clear integration point. However, the planned edits contain a direct runtime error, miss test registration, and introduce an unredacted output path. The handoff to later run-path and session work also needs stronger proof.

##### Strengths

- The planner’s ordered handlers and explicit reason list make report ordering and later extension testable (`37-04-PLAN.md:143–151`).
- Golden argv tests and `CONFIG.effort` precedence cases are useful checks against accidental formula changes (`37-04-PLAN.md:137–140,224–238`).
- It reuses the existing `runner_env` and real-node discovery helpers (`tests/cross_ai_selftest.py:39–60`).

##### Concerns

- **HIGH — Claude’s review formula is instructed to use an undefined variable.** The existing closure is `review: (m) => ...` (`cross-ai.mjs:1420–1425`). The plan says to append `...(c.adds?.effort || [])` but does not change the closure signature to `(m, c)` (`37-04-PLAN.md:159`). As written, even an ordinary Claude review dry run raises `ReferenceError: c is not defined`. Specify the signature change and check both the no-setting and effort cases.
- **HIGH — The new test module is not registered in generated listings.** The plan creates `tests/test_runner_settings_argv.py` (`37-04-PLAN.md:161`) without regenerating `Makefile` and `.pre-commit-config.yaml`. The gate explicitly requires every discovered test module in both listings (`tests/test_gate_scope.py:570–583`). Contrary to the stated early-stub strategy, 37-02 creates only its own test before regeneration (`37-02-PLAN.md:125–149`). Arrange for the early plan to create and register this stub, or regenerate the listings as part of a safely ordered plan.
- **HIGH — `cross-ai: model-id` can print a secret unredacted.** The plan calls `log(\`cross-ai: model-id ${plan.model}\`)` directly (`37-04-PLAN.md:160`); `log` writes its argument unchanged (`cross-ai.mjs:1243–1245`). The current model grammar admits key-shaped strings (`cross-ai.mjs:1295–1304`), and the existing redactor explicitly recognizes key shapes (`cross-ai.mjs:1530–1531,1600–1622`). A caller-supplied key-shaped model therefore appears in stderr. Redact this line and test a planted key; account for consumers such as 37-14 that expect the composed ID.
- **HIGH — `confirmReport` does not prove all of its stated guarantees.** Entries without proof are explicitly accepted (`37-04-PLAN.md:191,202`), and the `role` entry is one such applied entry (`37-04-PLAN.md:148`). For model/provider and ID-composed settings, replacing proof with `[plan.model]` (`37-04-PLAN.md:150`) only proves that an equal argument occurs somewhere, not that it occupies the intended model slot. Define proof appropriate to each setting and test misleading occurrences.
- **HIGH — The session status list can expose key-shaped skill or server names.** `statusGroup` inserts raw `skill:<value>` and `mcp:<value>` (`37-04-PLAN.md:203`), whereas the existing key-shape redactor recognizes strings beginning `sk-` (`cross-ai.mjs:1530`). Later skill and MCP name grammars permit such names (`37-03-PLAN.md:128`, `37-15-PLAN.md:130`). Redact status-list values as well as individual setting lines, and add a key-shaped name test.
- **MEDIUM — Stated dependency on 37-02 is not explicit.** This plan runs `tests.test_cli_help_flags` and relies on its recorded-help behavior (`37-04-PLAN.md:98,164`), but frontmatter lists only 37-03 (`37-04-PLAN.md:5–6`). Wave ordering alone is insufficient if the executor uses the dependency graph to select work. Add 37-02 as a dependency.
- **MEDIUM — Timeout risk is material.** Two files and three tasks look small by count, but the plan adds a multi-handler planner, six row changes, several formula changes, ten tests, self-tests, broad gates and three hook-running commits (`37-04-PLAN.md:94,143–161,241–253`). No timing establishes that this fits the 1,800-second cap.
- **MEDIUM — Test child environment omits the required refusal flag.** The proposed helper uses `runner_env(tmp)` (`37-04-PLAN.md:161`), whose returned dictionary does not include `AI_KIT_REFUSE_REAL_HOME` (`tests/cross_ai_selftest.py:85–100`). HOME is scratch, but the required defense-in-depth flag is absent from the actual Node child. Set it explicitly.

##### Suggestions

- Fix the Claude closure and registration before executing the plan.
- Use one redaction-safe composed-ID interface for the preview consumer and stderr, with a planted-secret regression test.
- Strengthen report confirmation to prove the actual semantic slot, rather than merely matching an arbitrary argv subsequence.

##### Risk assessment

**HIGH.** The prescribed Claude edit can break the dry-run path immediately, the new test leaves generated gates stale, and the proposed output can leak a key-shaped value.

##### Ponytail findings

- **LOW —** The planner and row fields are required by D-11 and 0b-12, rather than speculative abstraction (`37-04-PLAN.md:66–69`).
- **MEDIUM —** `confirmReport` adds complexity without yet establishing its advertised invariant. Either make its proofs complete for the covered settings or narrow its claim and tests; do not ship a false assurance.

---

#### 37-05

##### Summary

The context forms correctly reflect the locked 0b-7 and 0b-8 amendments, and the plan distinguishes chosen from minted sessions. Its session changes nevertheless leave concrete downstream contradictions and a misleading intermediate run state.

##### Strengths

- Context conversion and invalid-value cases cover the three locked value kinds, including decimal `k`/`m` conversion and bounds (`37-05-PLAN.md:123–142`).
- The plan preserves explicit `mode_forbids` behavior for Codex review and sandboxed execution (`37-05-PLAN.md:167–175`).
- It keeps the planner pure by receiving a generated ID from the caller rather than generating it inside the handler (`37-05-PLAN.md:175`).

##### Concerns

- **HIGH — The handoff to 37-07 targets code this plan removes.** This plan replaces `if (name === 'pi') ctx.sid = crypto.randomUUID();` with the chosen-row condition (`37-05-PLAN.md:184`); the original code is visible at `cross-ai.mjs:4096–4103`. Plan 37-07 later instructs the executor to replace that original line again (`37-07-PLAN.md:161–162`). The exact target will no longer exist, and the later plan’s “stop if it cannot be done as written” rule prevents completion. Make 37-07 update the actual 37-05 result and specify the desired final implementation once.
- **HIGH — The Claude no-resume test becomes stale when 37-10 adds resume.** This plan adds `test_minted_without_resume_formula`, expecting Claude review to report `no_form` (`37-05-PLAN.md:171,187`). Plan 37-10 changes Claude’s `resume` from null to a function for both roles (`37-10-PLAN.md:132`) but does not list or update `tests/test_runner_settings_argv.py`. The existing test will then expect the opposite of the new behavior. Include the test update in the handoff and run the module in 37-10’s gates.
- **HIGH — The intermediate run can report a session applied without using it.** This plan deliberately limits session application to `--print-argv` (`37-05-PLAN.md:54–55`); 37-06 then says a minted-host call reports the resume argv while `runCli` still starts fresh until 37-07 (`37-06-PLAN.md:37,134–138`). That is an explicit false `applied` claim at an intermediate commit. Combine the run-path report and actual first-argv change, or report the session as not applied until it is actually used.
- **MEDIUM — Spike and fixture dependencies are implicit.** The plan reads 37-01’s spike and 37-02’s fixtures and test (`37-05-PLAN.md:64,145,209–217`), but declares only 37-04 (`37-05-PLAN.md:5–6`). Add the producing plans to the dependency graph or make their transitively guaranteed ordering explicit and enforce it.
- **MEDIUM — The spike-label instruction may discard material evidence.** It says to drop any flag token missing from recorded help while retaining a verified source label (`37-05-PLAN.md:217`). A flag could be the very fact that was probed; deleting it makes the label less auditable rather than resolving a discrepancy. Require a separately recorded probe source or leave the form unverified when the evidence cannot be represented faithfully.
- **MEDIUM — The requested cap remains unproven.** The plan changes six row regions, formulas, retry construction, print-argv, two existing self-tests and ten Python tests, then runs eight shards, four broad gates and three commits (`37-05-PLAN.md:82,130–142,174–187,221–233`). This is enough distributed work to risk the 1,800-second unattended limit; provide measured timing or split the work.

##### Suggestions

- Update 37-07 and 37-10 alongside this plan’s final artifact contract.
- Make the first actual spawned argv and the session report change together.
- Treat missing or contradictory probe evidence as an explicit stop or unverified result, not as text to silently remove.

##### Risk assessment

**HIGH.** The downstream retry edit and Claude test are concrete integration blockers, and the planned intermediate state can report a session as applied while starting a different one.

##### Ponytail findings

- **LOW —** The context and session row fields are required by the locked decisions; reusing `planSettings`, `bracketValue`, `mergeBracket` and existing formula closures is appropriate (`37-05-PLAN.md:119–120,130–142`).
- **MEDIUM —** The plan’s separation of dry-run session construction from actual spawning saves no complete feature at the intermediate boundary. Merge the dependent behavior rather than carrying a knowingly misleading report.

---

##### Review status

**Issues found — revise the plans and re-review.** The three manifest plans received individual sections; same-wave checks found no declared file-write overlap for 37-04 or 37-05. I did not exhaustively verify every phase-wide SPEC edge or every path and command in all 23 plans, so this report is not a phase-wide coverage certification.

No files were created or changed, and no test suites or make targets were run. Scratch cleanup was not needed; the execution-time estimates remain unmeasured.

#### Batch C (37-06, 37-07, 37-10)

#### 37-06

##### Summary

The plan covers the required settings report, status-line group, effort defaults, and escalation echo. It reuses the existing status parser and self-test harness, but the proposed run-path confirmation can report a session as applied before the runner actually uses it. The plan is also large for the unattended executor’s time budget.

##### Strengths

- The new group is positioned where the locked Phase 38 handoff expects it, and the plan accounts for `statusTail`’s capture-index shift: `.planning/phases/37-shared-runner-options-and-session-ids/37-06-PLAN.md:132-133`; existing parser at `skills/ai-kit-spec-review/references/cross-ai.mjs:6099`.
- Testing `_trailer_counts` without changing it protects the existing caller contract: `.planning/phases/37-shared-runner-options-and-session-ids/37-06-PLAN.md:204-207`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:573-579`.
- There is no other plan in wave 5, and its dependency on 37-05 also orders the 37-04 planner transitively.

##### Concerns

- **HIGH — The first-argv proof is not proof of the spawned argv.** Task 1 constructs and confirms a prospective resume argv, but passes neither the planned session ID nor the resume decision to `runCli`; the plan explicitly defers that wiring to 37-07. Thus an explicit minted ID can be reported `applied` while the actual process starts fresh. Chosen hosts can likewise receive a different UUID because `runCli` creates its own context ID. See `.planning/phases/37-shared-runner-options-and-session-ids/37-06-PLAN.md:136-138` and `skills/ai-kit-spec-review/references/cross-ai.mjs:4762-4769,4783-4787`. This is a misleading, buildable intermediate commit, not merely a missing status field.
- **MEDIUM — Scratch scripts do not clean up.** The prescribed script creates a fixed scratch directory and has no exit trap, despite the mandatory per-run cleanup rule. The other script is copied from it. See `.planning/phases/37-shared-runner-options-and-session-ids/37-06-PLAN.md:143-144,183`.
- **MEDIUM — Executor budget risk.** Task 1 changes several distant runner regions; Task 2 adds nine cases; Task 3 adds a Python module and runs the eight self-test shards plus four whole-project gates. See `.planning/phases/37-shared-runner-options-and-session-ids/37-06-PLAN.md:130-144,179-183,209-213`. This exceeds the requested “many regions” risk threshold; completion inside 1,800 seconds is unproven.

##### Suggestions

- Land the session argv wiring with the report, or report the session as not yet applied until the actual first argv is known. Add a spawn-level assertion comparing the reported ID with the ID the fake receives.
- Give each scratch run an owned directory and cleanup on every exit; state how the executor verifies cleanup.
- Split or budget the runner integration and spawned-case work so that verification and hooks fit the lane cap.

##### Ponytail findings

- **LOW — Required scope, existing seams reused.** The work is required by R2/R3/R10 and 0b-5; `parse_status_line` and the existing self-test case table are appropriate reuse rather than new infrastructure. The transitional false report above should not be accepted merely to keep this plan smaller.

##### Risk Assessment

**HIGH** — The intermediate runner can assert a session was applied when it was not, and the plan’s execution size adds delivery risk.

#### 37-07

##### Summary

The plan addresses the core session round trip and covers multiple hosts, rejected IDs, retries, and reporting. However, its prescribed retry and persisted-state handling leave material gaps in the session guarantees, and one test expectation conflicts with its own ladder logic.

##### Strengths

- It reuses `sameSessionArgv` and its existing codex confinement checks instead of inventing a second resume formula: `skills/ai-kit-spec-review/references/cross-ai.mjs:4087-4094`.
- It tests generated and caller-selected IDs and preserves the user prompt on a first resume: `.planning/phases/37-shared-runner-options-and-session-ids/37-07-PLAN.md:114-116,153-159`.
- There is no other plan in wave 6; 37-06 transitively supplies the earlier planner and vocabulary.

##### Concerns

- **HIGH — Persisted IDs bypass the new validation.** Task 1 adds `sessionShown` for parsed host IDs but leaves the persisted re-entry path passing `persisted.last_sid` directly to `sameSessionArgv`. Existing persisted state is read before that path and is not validated there. A malformed or key-shaped legacy or edited ID can therefore be sent back despite the plan’s prohibition. See `.planning/phases/37-shared-runner-options-and-session-ids/37-07-PLAN.md:120,124-125` and `skills/ai-kit-spec-review/references/cross-ai.mjs:4807,4953-4964`. Validate before re-entry and before logging or saving, with a pre-existing-record regression test.
- **HIGH — Copilot’s chosen session cannot use the promised same-session retry.** Plan 37-05 retains copilot `resume: null`, while this plan pins explicit IDs and refuses a `new` rung. `ladderNext` selects `new` when `canResume` is false, so a transient failure on a pinned copilot session stops rather than retrying its documented create-or-continue form. See `.planning/phases/37-shared-runner-options-and-session-ids/37-05-PLAN.md:183-184`, `.planning/phases/37-shared-runner-options-and-session-ids/37-07-PLAN.md:122-127`, and `skills/ai-kit-spec-review/references/cross-ai.mjs:4057-4066,4087-4094`. The copilot test only exercises success, not this path.
- **HIGH — `session-host-id-unshown` expects a retry that the prescribed code refuses.** With cursor’s invalid printed ID, `hostSid` and `attemptSid` are both null; `sameSessionArgv` returns null and the ladder chooses a fresh `new` attempt. The case expects two rows with no ID, which is possible only because this run is unpinned—but the plan’s stronger statement that an invalid host ID is never passed back does not test a *persisted* invalid ID. More importantly, the case’s fake returns `badsid-503` on both attempts, so the implementation must explicitly preserve the intended fresh retry and check the resulting state record; the prescribed assertions check neither the saved record nor a re-entry. See `.planning/phases/37-shared-runner-options-and-session-ids/37-07-PLAN.md:125-127,187-195` and `skills/ai-kit-spec-review/references/cross-ai.mjs:4908-4913,5050-5077`. This is a coverage gap rather than evidence that the stated two-row case necessarily fails.
- **MEDIUM — The scratch scripts have no cleanup, and the plan is too broad for the lane budget without evidence.** It changes the retry ladder and four fake implementations and adds eleven spawned cases before running the shards and lint gates: `.planning/phases/37-shared-runner-options-and-session-ids/37-07-PLAN.md:118-131,161-167,191-197`. The fixed scratch directory has no exit cleanup.

##### Suggestions

- Gate persisted IDs with the same validation as host-output IDs and test an invalid and a key-shaped `last_sid`.
- Define a chosen-host same-session retry using the existing chosen ID and test a transient copilot failure with an explicit ID.
- Assert the invalid-ID cycle record and a subsequent re-entry, not only the first run’s output.
- Split the fake/test work if needed to fit the 1,800-second executor cap; use per-run scratch cleanup.

##### Ponytail findings

- **LOW — The feature is required, and the existing retry machinery is the right seam.** R7 requires the behavior; `ladderNext`, `sameSessionArgv`, and the existing fake harness already provide the appropriate integration points. A separate session framework is not needed.

##### Risk Assessment

**HIGH** — An unchecked persisted ID crosses the host-argv boundary, and the chosen-session retry path does not deliver the stated behavior.

#### 37-10

##### Summary

The plan adds the required Claude execute and resume formulas, a source label, fake execution, and golden argv tests. It misses an earlier plan’s test that explicitly asserts Claude has no resume formula, so the prescribed change cannot leave the intermediate suite green as written.

##### Strengths

- It preserves review’s existing plan-mode formula and uses the existing JSON parser: `.planning/phases/37-shared-runner-options-and-session-ids/37-10-PLAN.md:132`; `skills/ai-kit-spec-review/references/cross-ai.mjs:1420-1432`.
- It records the temporary Python mirror mismatch rather than silently changing routing, and preserves a drift check for the opposite mismatch: `.planning/phases/37-shared-runner-options-and-session-ids/37-10-PLAN.md:137`; `tests/test_ai_kit_spec_exec_formula_e2e.py:29-47`.
- **Same-wave check:** 37-11 edits the sync-test module and generated listings, not 37-10’s listed files. Its matrix explicitly tolerates Claude execute before or after 37-10, so I found no same-wave file overlap or required dependency there: `.planning/phases/37-shared-runner-options-and-session-ids/37-11-PLAN.md:5-10,25-30`.

##### Concerns

- **HIGH — The earlier Claude session test is not updated.** Plan 37-05 creates `test_minted_without_resume_formula`, requiring Claude review with `--session-id` to report `ignored reason=no_form` and leave argv unchanged. Plan 37-10 adds `resume`, making the same planner report `applied` and append `--resume`. The plan does not list or update `tests/test_runner_settings_argv.py`, nor run it among its named gates. See `.planning/phases/37-shared-runner-options-and-session-ids/37-05-PLAN.md:171,175-181,187` and `.planning/phases/37-shared-runner-options-and-session-ids/37-10-PLAN.md:7-11,132,204`. The next full unit run fails unless that test is changed in the same commit.
- **HIGH — Successful permission probe is treated as verification of the entire execute formula.** A record that a flag wrote a file flips `execLabel` to `verified`, although the planned formula also includes JSON output, model and resume behavior. The recorded evidence described in the plan establishes the permission-flag result, not necessarily the complete formula or error-classification behavior. See `.planning/phases/37-shared-runner-options-and-session-ids/37-10-PLAN.md:130-134` and the separate output-channel question in `.planning/phases/37-shared-runner-options-and-session-ids/37-RESEARCH.md:280-283`. Require the record to identify and support the exact formula and scope of the verification; otherwise retain the unverified label.
- **MEDIUM — Scratch cleanup and lane budget are unspecified.** The scripts create a fixed scratch directory without an exit trap, and the plan edits the runner, fake, existing drift test, documentation, and a new test module before running the shard and lint gates: `.planning/phases/37-shared-runner-options-and-session-ids/37-10-PLAN.md:129-139,200-204`. The 1,800-second limit is not demonstrated.

##### Suggestions

- Update the 37-05 Claude test to assert the new review-resume argv and applied report, add its file to the plan’s explicit staging list, and include the module in the gates.
- Tie a verified label to a recorded probe of the actual selected command and distinguish permission-flag evidence from error-pattern evidence.
- Add owned scratch cleanup and, if needed, split the work to leave time for hooks.

##### Ponytail findings

- **MEDIUM — One necessary caller/test is missing.** Adding `resume` is required by R6, but the smallest *complete* change includes updating the test 37-05 creates. The existing `reviewArgvProblem` and shared Claude parser are appropriate reuse; no separate execution framework is warranted.

##### Risk Assessment

**HIGH** — A known predecessor test will fail, and the verification label can claim more than the recorded probe establishes.

---

##### Document Type

GSD · implementation plans

##### Status: Issues Found — fix and re-invoke

**Review limits:** I did not run tests or make targets, as requested, and did not exhaustively audit all 24 plans or every phase-wide edge. No files or scratch artifacts were created.

#### Batch D (37-08, 37-09)

#### 37-08

##### Summary

This plan addresses the required runtime-gate and model-ID changes and reuses the runner’s existing self-test framework. It needs revision before unattended execution: the selected model is not consistently checked against the safety floor, and newly permitted runtime names can interact badly with inherited object properties.

##### Strengths

- The unknown-runtime refusal is separated from the subsequent argv-file implementation, and the dependency on 37-07 is serial (`37-08-PLAN.md:5-6`, `:121`).
- The plan retains live-listing rejection rather than treating a seed regex as proof that a model is available (`37-08-PLAN.md:160-162`; existing listing check at `skills/ai-kit-spec-review/references/cross-ai.mjs:12735-12745`).
- Generic classification reuses the existing wildcard-row filter rather than adding a second classifier (`37-08-PLAN.md:201`; `cross-ai.mjs:1744-1756`).

##### Concerns

- **HIGH — The safety floor does not cover models from `CONFIG`.** The plan validates only `--model` and `--model-<cli>` at parse time, then removes the selected model’s existing runtime check (`37-08-PLAN.md:160-162`). But the selected model can also come from `CONFIG.models[name]` (`cross-ai.mjs:12578-12583`). A hand-edited or rendered config can therefore pass a leading-dash, whitespace, or control-character model to the runner without the universal refusal. Validate the selected value after resolution as well, without restoring the per-runtime veto.
- **HIGH — Valid runtime names can collide with inherited object properties.** The new name grammar permits `constructor`, but the options store models and routes in ordinary `{}` objects (`37-08-PLAN.md:118-120`; `cross-ai.mjs:5259-5262`). Model resolution uses `o.models[name]` without an own-property check (`cross-ai.mjs:12581`). Once 37-09 allows such an unknown runtime to run, an omitted model can resolve to the inherited `Object` constructor rather than reaching `no_model`, causing incorrect behavior or an internal error. Use null-prototype maps or own-property checks, and test `constructor` with and without an explicit model.
- **MEDIUM — The regex is narrower than the stated acceptance floor.** The plan deliberately rejects `a[x=1][y=2]` (`37-08-PLAN.md:157,160`), although the phase acceptance criterion says the floor refuses a leading dash, whitespace and control characters “and nothing else” (`37-SPEC.md:494`). The detailed R5 text also refers to the existing charset, so this is a locked-document inconsistency that needs an explicit resolution before asserting both requirements are satisfied.
- **MEDIUM — The target safety checks are incomplete for the executor.** Task 2 covers several invalid CLI inputs, but has no selected-`CONFIG` model test and does not test an unusual ID reaching a spawn for every runtime as R5 acceptance asks (`37-08-PLAN.md:149-167`; `37-SPEC.md:245-254`).
- **MEDIUM — Execution budget and cleanup are not demonstrated.** The plan edits several separate regions of the runner, adds or changes 22 cases, runs eight shards and four repository-wide checks, and commits under a 1,800-second cap (`37-08-PLAN.md:64`, `:203-220`). It also leaves its scratch scripts and directory without an exit-path cleanup step (`:123`, `:271`), contrary to the mandatory temporary-file rule. The cap is a risk, not a measured failure.
- **LOW — The hardcoding instruction conflicts with the explicit review rail.** Task 2 directs retaining a real model literal in a rewritten case (`37-08-PLAN.md:150,163`), while the request prohibits such names in plan instructions and new test expectations. Resolve the baseline migration rather than relying on the old hit remaining unchanged.

##### Suggestions

- Add a single selected-model floor check after precedence resolution, with tests for config-only valid, invalid and empty values.
- Add prototype-collision tests for the options maps before 37-09 builds on the new runtime grammar.
- Resolve the floor wording and regex together; split verification or provide timing evidence if the plan is to remain a single capped dispatch.
- Give the scratch helper an owned temporary directory and cleanup on every exit path.

##### Risk Assessment

**HIGH.** The plan removes a runtime safety check before covering all model sources, and 37-09 exposes additional valid names to existing plain-object lookups. No same-wave file overlap is shown in the supplied wave map; 37-07 is the declared immediate predecessor.

##### Ponytail findings

- **LOW — Tasks 1–3 are required** by R4/R5 and reuse `parseArgs`, `resolveRuntime`, `classifyStop` and the existing self-test table (`cross-ai.mjs:5258-5365`, `:6422-6475`). No new abstraction is needed for the missing floor check.
- **MEDIUM — Reach is incomplete:** the selected `CONFIG.models` path is an existing caller of the changed gate and needs coverage before the old gate is removed.

---

#### 37-09

##### Summary

The argv-file lane is required by R4 and correctly aims to reuse the runner’s process supervision, strict reader and tree checks. The proposed adapter has several blocking integration defects: its session and report wiring conflicts with predecessor plans, and the proposed checks do not fully prove the claimed trust-boundary behavior.

##### Strengths

- File validation explicitly covers size, UTF-8, BOM, array shape, placeholders and symlink escape (`37-09-PLAN.md:120,151-170`), reusing the strict reader specified by 37-03 (`37-03-PLAN.md:180-183`).
- The same runner path is intended to handle classification and tree comparison; the existing classifier supports wildcard rows (`cross-ai.mjs:1744-1756`) and the existing tree snapshot includes untracked files (`cross-ai.mjs:4465-4488`).
- The declared dependency on 37-08 follows the serial runner-file sequence (`37-09-PLAN.md:5-6`). No same-wave overlap is shown in the supplied wave map.

##### Concerns

- **HIGH — Explicit session retries conflict with 37-07’s pinned-session logic.** The synthetic row has `resume: null`, yet an explicit `{session}` is reported applied (`37-09-PLAN.md:121-125,197`). Plan 37-07 pins applied explicit sessions and refuses a fresh `new` or `reset` rung (`37-07-PLAN.md:121-126`); `sameSessionArgv` cannot resume a row with no resume formula (`cross-ai.mjs:4087-4093`). Thus a transient failure can stop instead of retrying the declared command with the same session. The read-once retry test has **no** session slot (`37-09-PLAN.md:201`) and misses this combination. Define and test the retry behavior for an explicitly slotted session, including no silent session replacement.
- **HIGH — The report can claim a setting reached the command based on an unrelated substring.** `confirmReport` is weakened to accept `entry.value` anywhere in any argv element (`37-09-PLAN.md:125`), whereas the existing planned contract requires proof tied to the built argument (`37-04-PLAN.md:189-202`). For example, an unrelated argument containing `high` could validate an effort report after the actual effort substitution is lost. Preserve slot-specific provenance—expected element/index or exact substituted argument—and add a mutation test.
- **HIGH — The no-session-slot path can expose an ID that was reported ignored.** `planArgvFile` clears `plan.sessionId` when there is no slot (`37-09-PLAN.md:122`), but 37-07 separately initializes `liveSettings.sessionId` from the caller’s supplied ID before execution (`37-07-PLAN.md:121`). The plan only conditionally fixes display when a slot *is* present (`37-09-PLAN.md:125`). A call without `{session}` can therefore report `ignored no_slot` while printing the caller’s ID as the used session. Set the displayed ID from actual execution and test both slot-present and slot-absent cases.
- **HIGH — Malformed JSON is not guaranteed to produce the promised named error.** `strictJson` propagates `JSON.parse` errors (`37-03-PLAN.md:183`), and 37-09 returns `e.message` unchanged (`37-09-PLAN.md:120,126`). A syntax error therefore need not name `--argv-file`. The refusal matrix tests a non-array but no invalid JSON (`:151-167`). Wrap parse failures in a flag-named, safely redacted usage error and test malformed JSON.
- **HIGH — The stated command-path boundary is not what the plan enforces.** The plan constrains the **argv file** to the cwd tree, but deliberately allows the command element to resolve through `PATH` or a slash-containing path (`37-09-PLAN.md:21,120-121`). Its purpose and success criterion instead claim a declared command cannot leave the cwd tree (`:58,264`). The chosen command behavior may be intentional under D-05, but the plan must distinguish the file boundary from executable location; otherwise its security claim and tests are misleading.
- **MEDIUM — The known-row refusal is broader than “no formula.”** `Object.hasOwn(RUNTIMES, name)` rejects every table row even when the selected role lacks a formula (`37-09-PLAN.md:126`). The current Claude row, for example, has `exec: null` (`cross-ai.mjs:1420-1425`), though a later plan is intended to change it. Either support a declared command for a row lacking the selected formula or explicitly reconcile the narrower contract with R4; test the missing-role-formula case.
- **MEDIUM — Retry/read-once test is not a complete test of the boundary.** The fake modifies an ignored directory, then retries without an explicit session (`37-09-PLAN.md:127,192-201`). This proves one retry scenario, not the pinned-session scenario above. It also intentionally relies on the tree checker skipping fully ignored directories (`cross-ai.mjs:4485-4489`), so the review-tree check must not be described as a general filesystem confinement mechanism.
- **MEDIUM — Scratch cleanup, isolation and execution time need concrete steps.** The helper sets `TMPDIR` but does not itself set the required scratch `HOME` or remove its owned directory (`37-09-PLAN.md:79-81,129,206-223`). The objective requires those properties, but the executable instructions do not show how they are established and cleaned on failure. The broad runner changes, 22 cases, shards and four whole-repo checks also create an unmeasured risk against the 1,800-second cap.
- **LOW — The task contains unresolved implementation branches.** Instructions such as “if `confirmReport` would reject” and “if the status line … would print `-`” leave behavioral decisions to the unattended executor (`37-09-PLAN.md:124-125`). Resolve these against the predecessor interfaces in the plan.

##### Suggestions

- Specify the exact session-slot behavior across first attempt, transient retry, rejection and status reporting; add fake-CLI cases for each.
- Keep confirmation tied to the substituted argument rather than searching arbitrary argv text.
- Add a named malformed-JSON test and clarify that only the **declaration file**, not the executable, is confined to the cwd tree.
- Add a scratch-HOME setup and cleanup that run on success, failure and interruption; assess or split the capped execution work.

##### Risk Assessment

**HIGH.** The core feature reaches a process-spawning trust boundary, and the session/report defects can make execution or its evidence disagree with the requested settings. The issues are derivable from the plans and current source; the future integrated implementation was not run.

##### Ponytail findings

- **LOW — Tasks 1–3 are needed** for R4; reuse of `readCallFile`, `runCli`, `sameSessionArgv`, the wildcard classifier and the existing case table is appropriate (`37-03-PLAN.md:180-183`; `cross-ai.mjs:4090-4104`, `:4753-4787`, `:6422-6475`).
- **MEDIUM — Avoid a new substring-proof exception:** the existing report-proof mechanism should be extended with exact slot evidence, not bypassed. Later skill delivery must also continue to reach the synthetic row (`37-13-PLAN.md:156-171`).

##### Status: Issues Found — fix and re-review

**Review limits:** Read-only review; no test suites, make targets, files, or scratch artifacts were created. Phase-wide edge and prohibition coverage outside these two plans was not exhaustively audited; other plans were read only where relevant to these findings.

#### Batch E (37-13, 37-15)

#### 37-13

##### Summary

This plan addresses the required skill-delivery behavior and gives the executor concrete row data, validation rules, report formats and tests. It is **not ready for unattended execution**: its confirmation check does not establish that prose reached the actual lane, its retry test conflicts with the existing retry protocol, and its registration and spike-dependent expectations need correction.

##### Strengths

- **R13 is substantially mapped to actionable tests.** The plan covers per-host forms, name/path deduplication, call order, strict decoding, size boundaries and the argv-file lane (`.planning/phases/37-shared-runner-options-and-session-ids/37-13-PLAN.md:160–172`).
- **It reuses the existing runner seams.** The proposed formulas use the existing `ctx` and review-base pattern; the current review guard compares against the runtime’s own formula (`skills/ai-kit-spec-review/references/cross-ai.mjs:4771–4786`).
- **The paired plan has no declared same-wave file overlap.** 37-13 edits the runner and its new test, while 37-14’s declared edits are Python and Python tests (`37-13-PLAN.md:5–9`; `.planning/phases/37-shared-runner-options-and-session-ids/37-14-PLAN.md:5–19`). There is still a shared-workspace execution risk noted below.

##### Concerns

- **HIGH — “Applied” is confirmed against a proposed prefix, not the prompt sent.** Task 1 passes `plan.promptPrefix` to `confirmReport`, then tests that this same string contains each generated block (`37-13-PLAN.md:132–133`). Actual prompt composition is added separately in Task 3 (`37-13-PLAN.md:198`), after the current dry-run branch returns (`skills/ai-kit-spec-review/references/cross-ai.mjs:12629–12652`). Thus the check can succeed if the final stdin or `-p` prompt omits the block. It also lets Task 1 report prose applied before Task 3 wires delivery. This does not meet the prohibition against reporting applied when the **sent prompt** lacks the skill.

- **HIGH — The copilot retry oracle conflicts with the existing fresh-session prompt.** The plan expects the last of three transient calls to contain only the skill block plus the original prompt (`37-13-PLAN.md:195`). The existing retry path can prepend `RESUME_MSG` to the prompt for a later series (`skills/ai-kit-spec-review/references/cross-ai.mjs:5155–5161`), and `newSessionArgv` uses that supplied prompt for `-p` (`cross-ai.mjs:4097–4103`). The oracle must account for the actual rung and resume text while still proving the original skill bytes survived.

- **HIGH — Spike-success branches contradict fixed test expectations.** Task 1 permits Q4/Q5 to make Claude name or Copilot path verified (`37-13-PLAN.md:130`); Task 2 generally requires prose for both hosts and requires a matching Claude name/path to use prose (`37-13-PLAN.md:161–163`). The single exception for Claude name-only does not cover the matching-name/path case, the name boundaries, or a Copilot skill in the probed `.github/skills` layout. Plan 37-01 explicitly permits both flips (`.planning/phases/37-shared-runner-options-and-session-ids/37-01-PLAN.md:154–155`). A successful authorized probe can therefore make required tests disagree with required behavior.

- **HIGH — New-test registration is not actually supplied by the stated early plan.** Task 1 creates `tests/test_runner_skills_argv.py` but does not update generated listings (`37-13-PLAN.md:135`). The referenced 37-02 creates its help test and regenerates listings; it does **not** create the later test stubs (`37-02-PLAN.md:125–149`). `tests/test_gate_scope.py:570–583` requires every discovered module in both listings. The requested “early stubs, regenerate once” arrangement must be made real before this plan runs.

- **HIGH — A prerequisite plan is absent from this checkout.** 37-12 depends on 37-10 (`.planning/phases/37-shared-runner-options-and-session-ids/37-12-PLAN.md:5–6`), and 37-13 relies on its Claude execute formula (`37-13-PLAN.md:98`), but `37-10-PLAN.md` is not present in the phase directory. The 37-13 dependency chain cannot be executed or independently verified as written.

- **MEDIUM — Same-wave shared-state risk despite disjoint declared edits.** 37-14 executes runner dry-runs while 37-13 edits that runner (`37-14-PLAN.md:95`; `37-13-PLAN.md:117`). In a shared checkout, its tests can observe intermediate runner edits. Use isolated execution checkouts or sequence these plans; the wave map alone does not ensure isolation.

- **MEDIUM — The advertised host-config test only proves files are unchanged.** `hostFilesDigest` compares contents and metadata (`37-13-PLAN.md:200–201`); an unauthorized read leaves that digest unchanged. It therefore cannot establish the stated “never reads” prohibition (`37-13-PLAN.md:40`). Add a read tripwire or equivalent targeted instrumentation.

- **MEDIUM — Path-error redaction is incomplete.** The loader rethrows `readCallFile` errors unchanged when they already start with `--skill-path` (`37-13-PLAN.md:131`). The earlier reader’s error includes the supplied path (`.planning/phases/37-shared-runner-options-and-session-ids/37-03-PLAN.md:182`), bypassing the loader’s `shown` redaction. A path containing a key-shaped value can reach stderr on a reader failure.

- **MEDIUM — Lane-cap risk.** Task 1 alone specifies eight new helpers, multiple row and formula changes, parser changes, reporting and a test module (`37-13-PLAN.md:129–135`); Task 3 adds fake changes, two spawn-level cases and four whole-project static gates (`37-13-PLAN.md:197–217`). The plan’s own estimate is 95,000 tokens (`37-13-PLAN.md:14–18`). Completion within the 1,800-second cap is unproven and risky for the specified executor.

##### Suggestions

- Confirm prose against the **actual per-attempt input or `-p` element**, and test both normal and resume/retry paths; keep dry-run reporting explicitly distinguishable from delivery proof.
- Give the Q4/Q5 verified and unverified outcomes separate, mechanically specified test expectations.
- Add the promised early test stubs and listing regeneration, restore or otherwise resolve 37-10, and serialize same-checkout runner reads and writes.
- Redact reader errors before logging, and add negative tests for secret-shaped paths and attempted host-config reads.
- Split the work into independently green, smaller execution units if it cannot be demonstrated to fit the lane cap.

##### Risk Assessment

**HIGH.** The plan covers the intended feature, but currently permits a false delivery report and contains test and prerequisite conditions that can block unattended execution.

##### Ponytail findings

- **MEDIUM — Tasks 1–3 are required by R13 and 0b-13**, not speculative scope. Reuse the existing strict reader planned by 37-03 and the existing runner review formula/guard (`cross-ai.mjs:4540–4559`, `4771–4776`), but avoid the second independent `planSkills` computation in Task 3 (`37-13-PLAN.md:198`) when the already-built plan result can be carried to prompt construction.
- **HIGH — The change does not yet reach all required integration points:** generated test listings are missing, and the dependency on the absent 37-10 is unresolved. The later `--describe` handoff is explicitly planned in 37-17 (`.planning/phases/37-shared-runner-options-and-session-ids/37-17-PLAN.md:149–163`).

#### 37-15

##### Summary

The plan correctly isolates MCP delivery to verified per-call host forms and keeps the configuration JSON out of argv. However, its specified reader call does not enforce the required permissions, its parser errors can disclose input, and several edge and execution checks cannot pass or do not prove their stated guarantees.

##### Strengths

- **The review-formula approach fits the existing guard.** Keeping the flags in the base formula rather than `reviewExtras` avoids the guard’s requirement that an allowed extra flag have a following value (`skills/ai-kit-spec-review/references/cross-ai.mjs:4540–4557`).
- **The plan tests the main host distinctions and retains existing confinement flags**, including Pi’s `--no-mcp` and Copilot’s review profile (`37-15-PLAN.md:160–168`; `cross-ai.mjs:1384–1388`, `1453–1457`).
- **No declared same-wave file overlap** exists with 37-16: the latter’s declared modifications are Python and Python tests (`37-15-PLAN.md:5–9`; `.planning/phases/37-shared-runner-options-and-session-ids/37-16-PLAN.md:5–19`). 37-15 explicitly depends on 37-13.

##### Concerns

- **HIGH — The permission check is called with the wrong type.** 37-15 calls `readCallFile(..., { mode: true })` (`37-15-PLAN.md:130`). The earlier plan defines `mode` as a **bit mask**, and checks `st.mode & mode` (`37-03-PLAN.md:177,182`). In JavaScript, `true` coerces to `1`, so a group-readable file such as `0640` is accepted instead of rejected. The planned mode tests will fail, and the trust boundary is unprotected if they are bypassed. Pass `0o077` and retain the descriptor-based check.

- **HIGH — Malformed JSON can print server values.** 37-15 prefixes and rethrows `strictJson` errors (`37-15-PLAN.md:130`). The proposed reader starts with native `JSON.parse` and emits duplicate key text (`37-03-PLAN.md:178,183`). Parser errors can include excerpts or duplicate keys from inside server values; the plan tests planted secrets in valid JSON but not malformed JSON or secret-shaped duplicate keys (`37-15-PLAN.md:165–168`). Use a constant, content-free error for MCP parse failures and test both cases.

- **HIGH — Passing the original path does not make the host’s input immutable.** The runner validates and discards the parsed values, then passes the pathname to the child (`37-15-PLAN.md:130–131`). A caller or another process can replace or change the file after validation and before the host opens it; permissions and server names in the report can then differ from what the host receives. This also qualifies the claimed read-once guarantee (`37-15-PLAN.md:30`) and the “applied” proof, which checks only argv. The locked requirement to pass the caller’s original file makes this a design constraint that needs an explicit safe resolution, not an assertion of snapshot semantics.

- **HIGH — The mandated self-test invocation names a nonexistent case.** The plan runs `copilot-argv-review` in its selective script (`37-15-PLAN.md:200`), while the actual case is `copilot-argv-review` only if spelled exactly as shown in the plan; that one does exist. **The remaining problem is the test’s Copilot scenario:** the plan invokes `runCaseProcess` without specifying the synthetic file and process context contract sufficiently to establish that the host actually reads the supplied MCP file (`37-15-PLAN.md:194–199`). The fake currently only records argv and does not open or validate MCP configuration (`skills/ai-kit-spec-review/references/cross-ai.mjs:5999–6033`). Consequently, this proves flag construction and review-guard admission, **not** that the named servers reach the host or that values cannot be echoed by it. Add a fake that reads the file and exercises safe handling of its contents.

- **HIGH — Empty server objects are not rejected by the specified loader.** Task 1 checks that `mcpServers` is an object, then obtains `Object.keys`, but gives no `names.length === 0` refusal (`37-15-PLAN.md:130`). Task 2 requires an empty object to fail (`37-15-PLAN.md:168`), matching the locked edge (`37-SPEC.md:582`). Specify the missing check.

- **MEDIUM — Integer-like server names violate required file order.** The plan explicitly uses `Object.keys` and accepts its integer-key reordering as a shortcut (`37-15-PLAN.md:130`). Names such as `"2"` and `"1"` satisfy the allowed regex, but JavaScript enumerates integer-like keys numerically. This contradicts the locked file-order edge (`37-SPEC.md:584`). Preserve textual key order in the strict parser and test numeric names.

- **MEDIUM — Host-config digest cannot prove no reads.** Like 37-13, the test only compares file content and metadata (`37-15-PLAN.md:194–199`); the prohibition also forbids reads (`37-15-PLAN.md:38`). Add read instrumentation or a failing read sentinel.

- **MEDIUM — The new test module lacks the required generated-listing registration.** The plan creates `tests/test_runner_mcp_argv.py` (`37-15-PLAN.md:134`) without registering it; 37-02 does not create the promised stub (`37-02-PLAN.md:125–149`). The gate explicitly checks all discovered modules against both generated blocks (`tests/test_gate_scope.py:570–583`).

- **MEDIUM — Lane-cap risk.** The plan specifies a new loader and planner, six row changes, formula changes, nine test methods, a spawn-level case and four static gates (`37-15-PLAN.md:129–134`, `171–172`, `197–215`), with an 85,000-token estimate (`37-15-PLAN.md:14–18`). Its completion within 1,800 seconds, including hooks, is unproven.

##### Suggestions

- Call the existing reader with `mode: 0o077`; explicitly reject empty `mcpServers`; sanitize **all** parser error messages without echoing input.
- Resolve the original-file race while honoring the locked per-invocation contract, and test replacement or mutation between validation and host open.
- Preserve JSON textual server-key order, including numeric-looking names.
- Make the fake host actually open the passed file, and distinguish “argv contains the flag” from “the host accepted and loaded these servers.”
- Register the test through the early-stub/listing plan and split the work if it cannot fit the lane cap.

##### Risk Assessment

**HIGH.** The permission-mask mismatch is a concrete confidentiality defect, and the plan’s proofs currently cannot establish that the host consumed the validated server configuration.

##### Ponytail findings

- **LOW — Tasks 1–3 are required by R14 and D-33.** The plan appropriately reuses 37-03’s strict file reader and 37-13’s report-proof helper rather than introducing a dependency; retain those seams, correcting their contracts (`37-03-PLAN.md:182–183`; `37-13-PLAN.md:132–133`).
- **HIGH — Completeness beats the smaller diff:** correct the permission mask, ordering, empty-object check and host-open proof rather than documenting them as shortcuts. The new test also needs the generated listings; `--describe` is covered by the later 37-17 plan (`37-17-PLAN.md:149–163`).

##### Status

**Issues found — revise and re-review.** Both manifest plans are covered. No test suites or make targets were run, and no files were changed. Full phase-wide edge and prohibition coverage was not independently established; the findings above are limited to these two plans and their inspected dependencies.

#### Batch F (37-12, 37-14)

#### 37-12

##### Summary

The plan moves Python dispatch toward the shared runner vocabulary and retains the existing hook-token safety gate. It is **not ready to execute as written**: its required predecessor is absent from this checkout, its tracer cannot pass with the specified arguments, and its version bump leaves an existing test pinned to version 8.

##### Strengths

- The fixed flag order and golden tests make the Python-to-runner interface explicit, while preserving positional `RunnerSpec` callers (`37-12-PLAN.md:126–134`; current type at `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:87–99`).
- Reusing `lane_escalation` preserves its named error for non-boolean settings (`37-12-PLAN.md:165–175`; `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:96–113`).
- The plan retains the existing hook-token gate rather than introducing a second shell-safety policy (`skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:198–210`).

##### Concerns

- **HIGH — Required predecessor is missing.** `37-12-PLAN.md:6` depends on `37-10`, and `37-12-PLAN.md:64` assumes it has landed. There is no `37-10-PLAN.md` in the phase directory. The review therefore cannot verify the promised Claude execute formula, its ordering, or the transitive dependency chain. Restore that plan or provide its actual location before scheduling 37-12.

- **HIGH — The tracer always supplies an invalid timeout.** `37-12-PLAN.md:126,129` constructs `FULL` with `timeout_s=0` and passes it through `build_runner_argv`; that helper emits `--timeout 0` (`skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:266–274`). The runner rejects that value before reaching `--print-argv` (`skills/ai-kit-spec-review/references/cross-ai.mjs:5292`). Use a positive timeout for the subprocess tracer.

- **HIGH — Version bump breaks a required test, with no permitted fix.** `37-12-PLAN.md:136–142` changes the template to 9 and runs `tests.test_curated_config_script`, but `tests/test_curated_config_script.py:61–66` explicitly asserts `shipped == 8`. The plan neither includes that file in its task’s editable files nor instructs the executor to update the assertion. Add the version-pin update and an explicit regression test that an *edited version-8* runner is not ready under the new floor.

- **HIGH — Context and session settings do not reach normal lane dispatch.** The plan adds fields and tests direct construction of `RunnerSpec` (`37-12-PLAN.md:126–134`), but its `spec_with_effort` change passes only escalation fields (`37-12-PLAN.md:172–175`). Existing review and execute calls construct their specs through that helper (`skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:102–121`; `skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py:99–103`). Thus a `context` or `session_id` present in lane knobs is discarded. Plan 37-14 repeats that omission at `37-14-PLAN.md:176`. Specify the source and propagation of both fields and test the real review and execute paths, not only `runner_flags(FULL(...))`.

- **HIGH — The new test is not registered in generated listings.** The plan creates `tests/test_runner_flags.py` at `37-12-PLAN.md:138`, but does not update `Makefile` or `.pre-commit-config.yaml`. The proposed early stub-registration change has **not** been made in the checked-in 37-02 plan: it creates only its own test and regenerates then (`37-02-PLAN.md:136–149`). `tests/test_gate_scope.py:570–583` requires every discovered module in both listings. Resolve registration centrally before this plan creates the module.

- **HIGH — The 1,800-second execution envelope is at risk.** The plan changes 12 listed files across Python, the runner header, and tests (`37-12-PLAN.md:7–19`), with three task verifications plus four repository-wide lint/type gates (`37-12-PLAN.md:141–143,179–180,211–220`). That exceeds the supplied executor-sizing heuristic. Split or measure the work, including hook time, rather than assuming it fits.

##### Suggestions

- Fix the predecessor and test-registration dependencies before dispatch.
- Make the tracer use a positive timeout and update all version-9 readiness tests in the same logical change.
- Add end-to-end tests from lane knobs through review/execute spec creation to emitted flags.
- **Same-wave check:** The supplied wave map has no other wave-10 plan. The missing 37-10 plan prevents a complete dependency check.

##### Risk Assessment

**HIGH.** There are deterministic verification failures and an incomplete settings path, in addition to the missing dependency.

##### Ponytail findings

- **Task 1 — HIGH:** Required by R1/R12; reuse `runner_flags` and `HOOK_TOKEN_RE`, but include the generated listings and version-pinned tests in scope.
- **Task 2 — HIGH:** Required by R10; reusing `lane_escalation` is appropriate, but the same spec-building path must also carry the newly claimed context and session settings.
- **Task 3 — MEDIUM:** Builder parity is required; reuse `project_runner_command` rather than adding another composer. Keep the parity test, but divide the oversized plan if the executor cannot finish within its cap.

#### 37-14

##### Summary

The intended removal of duplicated Python effort composition is required by D-01 and is a sound direction. The implementation plan nevertheless has blocking test and integration gaps: the new preview module is unregistered, the hardcoding baseline is repaired too late, and the proposed preview can treat failed subprocess output as trustworthy.

##### Strengths

- The plan identifies the existing duplicated composers and replaces them with the runner’s preview (`37-14-PLAN.md:65–71`; current composers at `skills/ai-kit-spec-review/ai_kit_spec/lane_effort.py:80–121` and `skills/ai-kit-spec-review/ai_kit_spec/commands.py:83–111`).
- It preserves an explicit inconclusive outcome when no preview or setting line exists (`37-14-PLAN.md:130–136,172,180`).
- It supplies a non-vacuity case for the composer scan rather than merely asserting an empty scan (`37-14-PLAN.md:206–211`).

##### Concerns

- **HIGH — The baseline repair is scheduled after the gate that needs it.** Task 1 deletes existing model-bearing tests at `37-14-PLAN.md:138–143` and immediately runs `tests.test_arch_hardcoded_models`, but baseline entries are not removed until Task 3 (`37-14-PLAN.md:211–215`). The existing baseline includes `tests/test_ai_kit_spec.py` (`tests/fixtures/no_hardcoded_models_baseline.json:1094`), and the guard scans tracked test text (`tests/test_arch_hardcoded_models.py:170–200,203–235`). Repair each affected baseline entry in the same task that removes its hit, before that task’s verification or commit.

- **HIGH — The preview ignores the subprocess exit status.** `37-14-PLAN.md:136` specifies `check=False` and returns output without checking `proc.returncode`. A runner that emits an `applied` or `model-id` line and then exits nonzero can be treated as a successful preview; `_preview_outcome` can consequently proceed to a real probe (`37-14-PLAN.md:180`). Require a successful exit before accepting preview lines, and test nonzero exits both with and without plausible output.

- **HIGH — The new preview test is not registered.** `37-14-PLAN.md:140` creates `tests/test_runner_preview.py`, but no task updates the generated listings. The assumed early stub registration is absent from `37-02-PLAN.md:136–149`, while `tests/test_gate_scope.py:570–583` requires every discovered test module in both listings. Arrange a single early registration of all planned stubs, or explicitly register this module without creating a same-wave conflict.

- **HIGH — The plan drops context and session values from normal spec construction.** The exact replacement for `spec_with_effort` at `37-14-PLAN.md:176` does not forward either field added by 37-12 (`37-12-PLAN.md:132`). Consequently, passing them through review/execute knobs still produces no flags. Preserve and test those fields as part of this replacement.

- **HIGH — Preview and actual probe can run in different working directories.** The proposed `subprocess.run` at `37-14-PLAN.md:136` omits `cwd`, although `RunnerSpec` has one (`skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:92`). The actual quota probe deliberately uses a private working directory (`skills/ai-kit-spec-review/ai_kit_spec/quota.py:231–267`). This weakens the claim that the preview describes the actual invocation when cwd-dependent behavior matters. Define which cwd the preview uses and test parity with the call it is qualifying.

- **MEDIUM — The test cannot prove the claimed broad composer prohibition.** The three literal regexes in `37-14-PLAN.md:206–211` detect selected spellings, not every way to construct those strings—for example, single-quoted f-strings or concatenation. Either narrow the claim to those patterns or extend the guard and non-vacuity cases to cover the intended prohibited forms.

- **HIGH — The 1,800-second execution envelope is at risk.** The plan modifies 12 listed files (`37-14-PLAN.md:7–19`), deletes and replaces several interconnected interfaces, and runs multiple test groups plus four full static gates (`37-14-PLAN.md:142–143,186–187,214–224`). It exceeds the stated sizing heuristic; split it into buildable pieces or provide measured evidence that the full sequence, including hooks, fits.

##### Suggestions

- Make baseline updates part of Tasks 1 and 2, before their gates.
- Fail the preview closed on nonzero exit, and add an injected subprocess test for misleading output.
- Specify and test cwd and context/session propagation across preview and real dispatch.
- **Same-wave check:** 37-13 and 37-14 do not declare a shared edited file (`37-13-PLAN.md:5–9`; `37-14-PLAN.md:5–19`). They do share the runner interface: 37-14 launches the template while 37-13 edits it (`37-14-PLAN.md:136`; `37-13-PLAN.md:64–70`). If waves share a checkout rather than isolated worktrees, serialize them or test against a fixed snapshot.

##### Risk Assessment

**HIGH.** The proposed sequence has a likely failing intermediate gate, a missing generated-listing update, and an unsafe preview-success assumption.

##### Ponytail findings

- **Task 1 — HIGH:** Required by D-01. Reuse `RunnerSeams` and the existing template resolver (`skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:286–295`); also check exit status and include affected baseline/listing updates.
- **Task 2 — HIGH:** Required by R3. Removing the duplicated composers is worthwhile, but it must preserve every setting already added to `RunnerSpec` and every caller’s behavior.
- **Task 3 — MEDIUM:** A regression guard is justified, but its stated guarantee must match what its patterns actually detect; reuse the existing source-scan pattern rather than adding a more elaborate framework.

##### Review status

**Issues found — revise and re-review.** Both requested plan IDs were reviewed against the available checkout. The missing `37-10`, `37-19`, and `37-20` plan files prevent a complete phase-wide edge, prohibition, and handoff coverage audit; no exhaustive phase-coverage claim is made.

No files were written and no test suites or make targets were run. Scratch cleanup was not needed; the principal remaining risk is that unreviewable missing plans contain further dependencies or conflicts.

#### Batch G (37-16, 37-18)

#### 37-16

##### Summary

The plan removes the per-runtime Python grammar mirror and retains the separate hook-token safety check. That is required by R5 and D-06, but the proposed curated-config validator is narrower than the runner’s planned floor, and one stated CLI test cannot reach the behavior the plan expects.

##### Strengths

- It preserves the existing hook-string boundary rather than treating argv safety and shell-expansion safety as the same thing. `HOOK_TOKEN_RE` already excludes brackets and shell metacharacters (`skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:33-36`).
- It identifies the guarded sibling import and the four curated-config call sites that must stop using the mirror (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py:29-59`, `.planning/phases/37-shared-runner-options-and-session-ids/37-16-PLAN.md:123-128`).
- Its dependency on 37-14 transitively follows the runner and builder changes; no direct `files_modified` overlap with same-wave 37-15 is listed.

##### Concerns

- **HIGH — The selected “floor” rejects IDs that the runner accepts.** Plan 37-16 directs curated callers to use `cross_ai.model_id_problem` (`.planning/phases/37-shared-runner-options-and-session-ids/37-16-PLAN.md:109,123-127`). That helper’s regex excludes brackets (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py:28-43`), whereas 37-08 explicitly permits one trailing bracket, including for an unusual pi ID (`.planning/phases/37-shared-runner-options-and-session-ids/37-08-PLAN.md:149-160`). Consequently plan validation, editing and upgrade can still refuse or drop a runner-valid ID, contrary to the claim that they use the runner’s floor. Hook construction may separately reject brackets because of shell globbing; stored runner configuration is not the same boundary.

- **HIGH — The specified `apply-execution` test has the wrong refusal precedence.** The plan says to change the grammar check while retaining the preceding `unsafe_hook_token` check, yet expects `-placeholder-model-1` to produce `unsupported_model_id` and “must match” (`.planning/phases/37-shared-runner-options-and-session-ids/37-16-PLAN.md:116-124`). The current hook allowlist accepts a leading dash (`skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:33-36`), so that particular example can reach the floor check; however, IDs outside **both** checks, such as one containing a space, still take the earlier `unsafe_hook_token` branch (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:271-281`). The plan claims curated callers uniformly apply the floor but does not specify or test this precedence. More importantly, its action says the following `if` “keeps” returning `floor` without explicitly changing `if grammar:`; followed literally, it leaves an undefined name. Specify the complete replacement block.

- **MEDIUM — The known curated runtime gate qualifies the plan’s completeness claim.** The plan says curated-config refuses a model ID only for the floor (`.planning/phases/37-shared-runner-options-and-session-ids/37-16-PLAN.md:140`), but `_model_row_problem` still rejects a runtime outside `RUNNER_IDS` before checking its model (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:1129-1135`). This is the owner-recorded deferred gap, not a request to expand the phase; narrow the claim and tests to model-shape validation for supported curated rows.

- **MEDIUM — Executor budget is at risk.** The plan changes 12 listed paths across two packages and multiple test modules (`.planning/phases/37-shared-runner-options-and-session-ids/37-16-PLAN.md:7-19`), then runs four broad static gates (`:190-200`) and commit hooks. That exceeds the requested approximately five-file sizing heuristic for a single 1,800-second lane. The estimate is marked low-confidence (`:24-28`), not measured evidence that it will finish.

- **MEDIUM — Same-wave verification can observe an in-progress runner.** 37-15 modifies `cross-ai.mjs` in wave 12 (`.planning/phases/37-shared-runner-options-and-session-ids/37-15-PLAN.md:5-9`), while 37-16 runs tests and gates against the checkout (`.planning/phases/37-shared-runner-options-and-session-ids/37-16-PLAN.md:130-132,163-165,190-200`). There is no direct declared-file overlap, but parallel execution in one checkout can make 37-16’s checks observe a partial 37-15 edit. Isolated execution or serialized verification is needed.

##### Suggestions

- Use a validator that matches 37-08’s **actual** universal floor for stored IDs; retain `HOOK_TOKEN_RE` as an additional hook-only check. Add a bracketed ID to plan-validation and upgrade tests, plus a hook test proving that the same ID remains unsafe for the unquoted hook.
- Give the exact replacement for `_model_refusal`, including the variable tested and the intended error precedence.
- Split the implementation into independently green units or provide measured lane-budget evidence, and define how parallel wave-12 checks are isolated.

##### Risk assessment

**HIGH.** The mismatch can reject or discard valid stored configuration, and the exact implementation instructions leave a branch with an undefined variable if followed literally.

##### Ponytail findings

- **HIGH — Task 1 is required, but the existing helper is not equivalent to the required floor.** Reuse `cross_ai.model_id_problem` only after aligning its accepted language with the runner, or use an existing shared floor if one is introduced; do not remove the distinct hook safety check (`cross_ai.py:28-43`, `runner_dispatch.py:33-36`).
- **LOW — Tasks 2 and 3 are justified by D-06.** The planned non-vacuous scan reuses the existing source enumeration and test pattern (`tests/test_no_seed_refusal.py:18-33,60-71`); no additional abstraction is needed.

#### 37-18

##### Summary

The plan moves formula knowledge to `--describe` and reuses the existing atomic cache writer. Its intended stale-fact and green-commit guarantees are not yet achieved: several instructed paths can consume or retain stale facts, and the plan’s own task ordering and acceptance checks conflict.

##### Strengths

- The proposed reader accepts only a boolean `formulas.exec` and preserves unknown top-level describe keys, providing a narrow consumer contract for the 38.1 extension (`.planning/phases/37-shared-runner-options-and-session-ids/37-18-PLAN.md:131-145`).
- It reuses `cache_write_json`, whose implementation writes a temporary file, fsyncs and replaces the target (`skills/ai-kit-spec-review/ai_kit_spec/cache.py:23-45`).
- The 37-17 dependency supplies the documented `runtimes.<id>.formulas.exec` shape (`.planning/phases/37-shared-runner-options-and-session-ids/37-17-PLAN.md:23-27`), and 37-16 is explicitly named as a dependency.

##### Concerns

- **HIGH — A stale fact can still refuse through `route`.** The plan says an absent **or stale** fact never refuses (`.planning/phases/37-shared-runner-options-and-session-ids/37-18-PLAN.md:69-70`), but `inventory_from_snapshot` copies any dictionary-valued `runner` unchanged and `route` passes it straight to `runner_has_exec`; that helper checks only nested types, not the hash (`:144-146`). The normal loader refreshes first, but a directly constructed inventory or snapshot bypasses it; the plan’s own tests pass a fabricated `"0" * 64` fact as authoritative (`:131,135`). Validate freshness at the inventory/routing boundary, or make the validated-fact contract explicit and enforce it at every entry point. Test a stale `exec: false` fact, not only a stale loader refresh.

- **HIGH — `detect-runtimes --if-stale` skips the hash refresh.** The prescribed addition occurs after snapshot construction (`.planning/phases/37-shared-runner-options-and-session-ids/37-18-PLAN.md:146-147`), but the existing CLI returns early for a fresh cache before reaching that block (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:521-536`). A newly installed template can therefore leave the recorded fact unchanged through the detection command, contrary to D-10’s hash-triggered refresh. Cover the early-return path with a changed-template-hash test.

- **HIGH — Failed or unverifiable describe results can be cached as current.** The specified reader parses stdout without requiring a zero subprocess return code, and `fact_is_current` compares hashes even when the current template hash is `None` (`.planning/phases/37-shared-runner-options-and-session-ids/37-18-PLAN.md:140-145`). A failed process that emits valid JSON can become a refusal fact; a missing or unreadable template and a cached null hash can also compare equal. In addition, the plan explicitly treats a current-hash `describe: None` as current (`:133`), so transient Node or timeout failures are not retried until another refresh condition occurs. Require a successful describe and a non-null verified hash for a refusal; specify a retry policy for failed descriptions.

- **HIGH — Task 2’s acceptance criterion cannot pass in its prescribed sequence.** It requires no `SUPPORTED_EXECUTE_CLIS` occurrence anywhere in `skills tools tests` (`.planning/phases/37-shared-runner-options-and-session-ids/37-18-PLAN.md:195-198`), but the existing drift test still uses that symbol (`tests/test_ai_kit_spec_exec_formula_e2e.py` is deleted only in Task 3, and related table tests also contain it: `tests/test_ai_kit_spec_runtimes_table.py:161-162`). Task 3 then deliberately adds the same literal to its scan and planted test (`37-18-PLAN.md:215,223`), so the unqualified grep remains inconsistent even after Task 3. Define scoped, task-appropriate checks and commit the removal with all dependent changes.

- **HIGH — The planned intermediate commits and test registration are not mechanically green.** Task 1 creates `tests/test_runner_facts.py` (`.planning/phases/37-shared-runner-options-and-session-ids/37-18-PLAN.md:151`), while regeneration is deferred to Task 3 (`:219-224`). The repository’s gate requires every discovered test module in both generated listings (`tests/test_gate_scope.py:570-583`). The owner’s proposed early-stub alignment has not landed in the referenced 37-02 plan: it registers only its own new module (`.planning/phases/37-shared-runner-options-and-session-ids/37-02-PLAN.md:76-82,149`). Thus a full unit/arch check between those steps can fail. Separately, Task 2 removes the shared execute constant while the drift test remains until Task 3, so the stated first-two-task commit boundary needs a dependency-complete test check.

- **MEDIUM — The test fixture hardcodes a machine path.** The plan instructs the fake `which_fn` to return `/usr/bin/node` (`.planning/phases/37-shared-runner-options-and-session-ids/37-18-PLAN.md:151`), contrary to the repository’s no-machine-specific-absolute-path rule. A synthetic relative token is sufficient because the fake never spawns Node.

- **MEDIUM — Scope and runtime budget are too large for the declared lane.** The plan lists 18 paths (`.planning/phases/37-shared-runner-options-and-session-ids/37-18-PLAN.md:7-25`), requires multiple test batches and four static gates (`:154-156,191-193,226-236`), and estimates the last commit hook alone at 10–13 minutes (`:224`). Under a 1,800-second hard cap, that leaves little time for implementation and earlier commits. Split around independently green boundaries or provide measured end-to-end evidence.

##### Suggestions

- Make freshness and successful provenance part of the fact consumed by routing; add tests for stale direct inventories, missing templates, nonzero describe exits, transient failure followed by recovery, and `detect-runtimes --if-stale` after a template change.
- Land the complete stub-and-listing registration in an earlier plan, or regenerate and commit listings with each new module. Combine removal of the constant with its dependent test changes, and scope grep checks to exclude intentional non-vacuity fixtures.
- Split the plan into smaller green commits/plans while retaining the existing cache helper and fake-runner seams.

##### Risk assessment

**HIGH.** Stale or failed evidence can become a routing veto, and the prescribed execution sequence has failing or mutually inconsistent checks before considering the lane timeout.

##### Ponytail findings

- **HIGH — Tasks 1–3 are required by R9/D-10, but freshness must be enforced rather than assumed.** Reuse the existing loader and atomic cache helper (`routing.py:255-277`, `cache.py:23-45`); avoid a second authority that can accept an unchecked snapshot.
- **MEDIUM — The new fact module is justified as the single runner-description reader, but the work is not yet a small executable unit.** Registration and removal must reach the test runner and generated listings at the same green boundary (`tests/test_gate_scope.py:570-583`), rather than relying on a later task.

##### Status

**Issues found — revise and re-review.** Both manifest plans were reviewed. The same-wave file map shows no direct 37-16/37-15 file overlap and no other listed wave-14 plan.

**Not checked:** I did not run tests or make targets, or exhaustively audit the other 19 plans and every phase-wide edge. The remaining phase-wide coverage is therefore not certified. No scratch files were created.

#### Batch H (37-17, 37-19, 37-20)

##### Review status

**Issues found — revision required.** All three plans in the manifest are covered below. This is a read-only GSD plan review; no files were changed and no test suites or Make targets were run.

#### 37-17

##### Summary

The plan establishes a useful offline contract between the runner and Python, but its proposed `--describe` output loses some of the source information required by R9. Its test-module registration also relies on a triage change that is not present in the checked-in upstream plan.

##### Strengths

- The early branch avoids the existing overlay load and runtime selection, making an offline description feasible: `37-17-PLAN.md:126-130`; current ordering is visible at `skills/ai-kit-spec-review/references/cross-ai.mjs:12551-12570`.
- The open-stdin test and fake-herdr marker test target meaningful side effects, while the golden file provides a useful drift check: `37-17-PLAN.md:117-134`, `:156-165`, `:187-195`.
- Generic copying of setting forms gives Phase 39 an extension point without a new Python mirror: `37-17-PLAN.md:163`.

##### Concerns

- **HIGH — Formula and listing facts have no meaningful source labels.** The plan emits formula booleans and listing argv, then substitutes a single row-level `"unverified"` when `row.source` is absent (`37-17-PLAN.md:31`, `:163`). Earlier rows attach labels to *setting forms*, not to exec, review, resume, or listing facts (`37-04-PLAN.md:152-158`; current row structure at `skills/ai-kit-spec-review/references/cross-ai.mjs:1336-1460`). R9 requires those facts to carry source labels; the proposed `test_rows_carry_formulas_and_labels` explicitly skips `formulas`, `listing`, and `source` when checking form labels (`37-17-PLAN.md:157-165`). **Required:** define and test a labeled representation for each formula and listing fact, and align 37-18’s consumer with it.

- **HIGH — The stated stub rule is not implemented in the upstream file on disk.** The supplied triage says 37-02 creates and registers every new module, but the actual `37-02-PLAN.md:125-149` creates and registers only `tests/test_cli_help_flags.py`; `:275` likewise names only that module. This plan creates `tests/test_runner_describe.py` without regenerating the listings (`37-17-PLAN.md:131-134`), while `tests/test_gate_scope.py:570-583` checks every discovered module against both generated listings. **Required:** put the agreed stub creation, staging, and one-time listing regeneration in 37-02’s executable task text, then make 37-17 explicitly fill its stub.

- **MEDIUM — The executor cannot rely on the manifest alone to know the commit scope.** The lane receives objective and tasks, not frontmatter or artifact blocks. The objective says to commit “only the files of this plan” (`37-17-PLAN.md:88`) but does not give an explicit final staging command, and Task 1 says to create a file rather than replace the triaged stub (`:131`). **Required:** state the exact allowed staged paths and stub replacement in the objective or tasks.

- **LOW — No same-wave overlap was found for wave 13 in the supplied wave map.** The stated dependency on 37-15 carries the runner-form changes transitively; the registration issue above is a separate upstream contract failure.

##### Suggestions

- Preserve provenance alongside each described fact and add a negative test that removes one formula or listing label.
- Amend 37-02 before execution, rather than asking each later plan to regenerate shared listings.

##### Risk assessment

**HIGH:** the description is a routing input, so missing provenance affects confidence in the fact Python consumes; the unregistered module can also make the gate fail.

##### Ponytail findings

- **MEDIUM:** The describe contract is required by R9 and is appropriately small. Reuse the existing executable lookup, `which` (`skills/ai-kit-spec-review/references/cross-ai.mjs:2989-3000`), and keep one generic form serializer; do not add a second Python formula table.
- **HIGH:** Completing the small change includes the generated listings and downstream fact schema, not just the runner and golden file.

#### 37-19

##### Summary

The plan sensibly separates launcher protocol construction from transport, and reuses the existing atomic state writer. As written, however, it contains a JavaScript syntax error and does not meet its prompt-secrecy or green-commit claims.

##### Strengths

- `writeCycleState` already provides a private temporary file and atomic rename (`skills/ai-kit-spec-review/references/cross-ai.mjs:4183-4195`); reusing it for `run.json` is preferable to another writer.
- The launcher tests exercise hostile argv through a real shell rather than relying only on string comparisons (`37-19-PLAN.md:191-200`).
- The protocol fixture and architecture-rule non-vacuity tests are appropriate for the locked Phase 38/42 handoffs (`37-19-PLAN.md:165`, `:235-247`).

##### Concerns

- **HIGH — The prescribed `HOST_PATH_SAFE` is invalid JavaScript.** `37-19-PLAN.md:138` specifies `/^[A-Za-z0-9._/-]+$/`; the unescaped `/` terminates a JavaScript regex literal even inside a character class. The runner cannot parse, so neither the tracer nor its verify command can pass. **Required:** escape the slash in the literal and test the complete runner parses, not only lifted functions.

- **HIGH — The launcher persists argv-carried prompt text.** `buildLauncher` serializes every element of `[lane.bin, ...lane.argv]` into `launch.sh` (`37-19-PLAN.md:148-164`). Copilot’s existing formula puts `c.promptArg` directly on argv (`skills/ai-kit-spec-review/references/cross-ai.mjs:1441-1448`), so the private launcher retains the prompt for the lane’s duration even after the prompt file is deleted. This contradicts the plan’s assertion that the launcher holds no prompt or secret (`37-19-PLAN.md:41`, `:287-289`) and the short-lived secret-file amendment. **Required:** specify a transport that preserves the host’s required argv without leaving prompt content in `launch.sh`, or explicitly resolve this conflict with the locked security contract; add a copilot prompt sentinel test.

- **HIGH — Clean-environment re-exec can be bypassed by the pane environment.** The launcher skips `env -i` whenever the inherited `AIKIT_HOST_CLEAN=1` (`37-19-PLAN.md:149-152`). A pane with that variable already set keeps its ambient environment, contradicting the promised equivalence with the runner’s child environment (`:32`). The current test only plants a different variable (`:133-135`). **Required:** use a re-exec marker that cannot be supplied by the inherited environment, and test this exact collision.

- **HIGH — The new module is not registered by the actual 37-02 plan.** `37-19-PLAN.md:166-171` creates and immediately tests `tests/test_runner_host_protocol.py`, but the upstream stub is absent from `37-02-PLAN.md:125-149`; `tests/test_gate_scope.py:570-583` requires its listing. **Required:** fix the upstream stub/listing task and have this plan fill it.

- **MEDIUM — The architecture guard does not prove what it claims.** The planned regex counts occurrences of `spawn(HERDR_BIN, ...)` but does not establish that the one occurrence is *inside* `herdrCall`; it also only recognizes literal single-quoted calls to `herdrCall` (`37-19-PLAN.md:241-245`). A dynamic verb or moving the one spawn elsewhere can pass the purported ownership rule. **Required:** add non-vacuity cases for those violations and implement a check that actually rejects them.

- **MEDIUM — The protocol fixture is only partially locked.** The claimed fixture lock covers label grammar, modes, typed line, verdict, `rc` grammar, and done line (`37-19-PLAN.md:30`), but the specified comparison checks only files, verbs, and prefix (`:201`, `:211`). Other tests exercise some values independently, without comparing them to the fixture. **Required:** compare each claimed protocol field to the generated behavior or narrow the claim and provide the missing Phase 42 contract test.

- **MEDIUM — Executor budget and commit instructions are inconsistent.** Three tasks span four files, many runner regions, eleven tests, self-test shards, and four whole-project gates (`37-19-PLAN.md:137-168`, `:205-211`, `:250-262`). This exceeds the review’s approximate 300-new-line threshold and is risky under the 1,800-second cap. Also, the objective says to commit the plan’s files (`:100`), while Task 3 requires the last commit to contain only `tests/test_arch.py` (`:267`) without explicitly directing earlier commits. **Required:** split the work into independently green, bounded plans or give exact commit boundaries and verified timing.

- **LOW — Same-wave check:** 37-18 and 37-19 declare no common modified file (`37-18-PLAN.md:5-25`; `37-19-PLAN.md:5-11`), and 37-19 depends on 37-17, whose host helper it reads. No direct same-wave file collision found.

##### Suggestions

- Correct the regex and add a whole-template syntax check before introducing transport.
- Treat prompt handling and environment isolation as explicit end-to-end protocol tests, not just launcher-text tests.
- Split protocol helpers, architecture checks, and their commits only if each boundary remains green and retains the complete security behavior.

##### Risk assessment

**HIGH:** the current literal prevents execution; prompt retention and environment inheritance create security-contract violations even if the syntax is repaired.

##### Ponytail findings

- **HIGH:** The launcher and private record are required by R12 and 0b-2/0b-3. Reusing `writeCycleState` is justified; the partial fixture lock and elaborate source-lifting test must not substitute for actual whole-runner and prompt-secrecy checks.
- **MEDIUM:** The change reaches the runner and tests, but misses generated test registration. Its scope should be divided for the lane budget rather than dropping required behavior.

#### 37-20

##### Summary

The plan addresses the required file-based transport and tests several useful headless/hosted pairs. Its failure handling currently assumes ambiguous herdr responses prove that nothing started, and its cleanup can discard the only record of a still-open tab. Those are material execution-safety risks.

##### Strengths

- The plan preserves the existing capture and classification path rather than deriving a verdict from pane text (`37-20-PLAN.md:138-144`; existing shared callbacks at `skills/ai-kit-spec-review/references/cross-ai.mjs:4614-4679`).
- The fake checks foreign-tab isolation, file permissions, and a successful tab-before-directory cleanup order (`37-20-PLAN.md:123-126`, `:147-157`).
- The `none` precedence and no-herdr path are explicit (`37-20-PLAN.md:220-229`).

##### Concerns

- **HIGH — A failed or timed-out `pane run` is not proof that the lane never started.** The plan falls back headless on *any* non-success result from `pane run` (`37-20-PLAN.md:137`, `:144`). A timeout, lost response, or error after admission can occur after the launcher began; the fake models only a rejection before running the line (`:149`). Closing the tab is not proof that all effects or detached descendants stopped. This can execute a write-capable lane twice, contrary to the no-rerun prohibition. **Required:** fail closed on ambiguous admission; permit fallback only when non-admission is positively established, with a fake that starts the launcher and then times out or returns an error.

- **HIGH — Failed close loses both ownership and recovery evidence.** `closeTab` deletes the ID from `openTabs` *before* attempting the close (`37-20-PLAN.md:129-130`), and `finalize` removes the run directory regardless of close result (`:141`). If herdr returns an error while the tab remains open, neither `exitFlushed` nor Phase 38’s future sweep can find it. The `host-dead-launcher` fake explicitly makes close fail but expects the directory removed (`:186-197`). **Required:** retain the tab ID and nonsecret `run.json` until closure is confirmed or recovery is possible; separately remove secret remnants. Test a close failure where the tab genuinely remains open.

- **HIGH — The launcher PID is assumed to be a process-group leader without establishing it.** The fake uses `detached: true`, guaranteeing the fake launcher’s PID is its process-group ID (`37-20-PLAN.md:149`), whereas the real transport types `sh <path>` into an existing pane (`:135-137`). The launcher in 37-19 merely writes `$$` (`37-19-PLAN.md:155`); it does not create or verify a new group. Existing `killGroup` sends to `-child.pid`, falling back to the single PID (`skills/ai-kit-spec-review/references/cross-ai.mjs:4224-4227`). A real pane shell without the assumed job-control behavior may leave descendants running. **Required:** establish and verify a dedicated group before group signalling, and test a pane launcher that does not start detached; document the separately locked `setsid` descendant limitation.

- **HIGH — PID-reuse protection is not enforced in all branches.** The prescribed finalize condition permits group signalling when the recorded start time is `'-'` **or when `pidAlive` is false** (`37-20-PLAN.md:140-141`). That does not prove the target group belongs to this run; the current `killGroup` can signal a negative PID and fall back to a positive PID (`cross-ai.mjs:4224-4227`). It contradicts the plan’s own “only after … start time still matches” claim (`37-20-PLAN.md:29`). **Required:** fail safely when identity cannot be verified and cover PID reuse and unreadable start times.

- **HIGH — The success-pair oracle compares different status lines literally.** The first run reports `host=herdr applied`, the second `host=none applied` (`37-20-PLAN.md:124-125`), so those two cases can share `applied=host`; however, the proposed fallback path changes the first entry to `ignored=host` (`:143`) while `hostPairCheck` performs its stdout and lane-call comparisons before deciding it is in the unsafe-path fallback (`:156`). More directly, the fallback branch uses `statusLineOk(...)` on the first result only after these equality checks, but does not compare its status fields to the headless result. **Required:** compare normalized, explicitly selected contract fields in both hosted and fallback cases, and assert the expected host-state difference separately. This is a coverage defect, not proof that every pair necessarily fails.

- **MEDIUM — Tab creation and startup failure coverage is incomplete.** A successful `tab create` whose response is lost or malformed can leave a tab open while the plan drops the directory and falls back (`37-20-PLAN.md:135`). The fake has a `create` failure switch (`:147-148`) but the eleven listed cases contain no `host-create-failed` case (`:220-224`). Also, a launcher that exits before producing `pid` and `rc` is not detected as dead by `tick`, because the dead check requires a non-null PID (`:140`); it waits for the deadline. **Required:** specify safe handling and tests for ambiguous create, explicit create refusal, and death before PID publication.

- **MEDIUM — Signal cleanup does not cover all startup windows.** `currentFinalize` is installed only after synchronous tab creation, record rewrite, and `pane run` return (`37-20-PLAN.md:135-142`). The existing signal path invokes `currentFinalize` when present and otherwise relies on the backstop (`skills/ai-kit-spec-review/references/cross-ai.mjs:4562-4580`). Test and specify signals and exceptions at each startup boundary, including failed record rewrites and file opens, without deleting a live tab’s recovery record.

- **MEDIUM — Parallel-lane coverage is claimed but not demonstrated.** The concurrency truth cites one signalled lane, and the two-run case executes sequentially (`37-20-PLAN.md:25`, `:186-197`); the existing `runTwice` helper also awaits the first before starting the second (`skills/ai-kit-spec-review/references/cross-ai.mjs:6284-6298`). **Required:** add two overlapping hosted calls with independent records, tabs, outputs, and cleanup.

- **MEDIUM — The executor budget is a substantial risk.** Task 1 alone introduces a transport, signal lifecycle, fake CLI, and multiple harness helpers in several runner regions (`37-20-PLAN.md:128-158`); Tasks 2–3 add ten more cases and multiple project-wide gates (`:189-199`, `:226-248`). The plan estimates 120,000 tokens (`:13-17`) and exceeds the requested approximately 300-new-line threshold. **Required:** divide into independently green plans with explicit ownership and time budget, retaining the complete transport behavior.

- **LOW — Same-wave check:** the supplied map lists no other wave-15 plan, and 37-20 explicitly depends on 37-19’s protocol. No same-wave collision identified.

##### Suggestions

- Make “definitely not admitted” versus “admission unknown” an explicit transport result; only the former may fall back.
- Keep recovery records on unresolved close failures while deleting env and prompt remnants immediately.
- Test real process-group assumptions independently of the fake’s `detached` spawn, and add startup fault injection and concurrent-lane tests.

##### Risk assessment

**HIGH:** ambiguous admission can duplicate an execute lane, and failed cleanup can leave an untracked tab or descendants.

##### Ponytail findings

- **HIGH:** The transport itself is required by R12; the added failure-state distinctions are not speculative abstraction, because they protect against duplicate execution and lost ownership. Reuse the existing `runChild` capture, `killGroup`, and `writeCycleState` seams (`cross-ai.mjs:4183-4195`, `:4224-4227`, `:4259-4345`) where their guarantees actually apply.
- **MEDIUM:** The single-file implementation avoids a new package, but its current plan exceeds the executor’s stated capacity. Splitting the implementation is safer than omitting cleanup or evidence cases.

##### Coverage limits

The three assigned plans were read from disk and checked against their relevant source and handoffs. This review did **not** independently audit every edge and prohibition across all 24 phase plans, nor every referenced command or path; absence of an additional finding is not a phase-wide coverage certification.

No tests or live herdr calls were run, as requested. No scratch files were created.

#### Batch I (37-21, 37-22, 37-23, 37-24)

#### 37-21

##### Summary

The documentation and eval work is required by SPEC R11 and uses the existing fake-runner infrastructure. The plan is not executable as written: its capture script omits a required directory creation, its new test is not registered by the earlier plan on disk, and the supplied plan differs materially from the same-wave plan currently on disk.

##### Strengths

- The three-way reason and setting-name lock ties the documentation to both source and `--describe`, with mutation checks for the reason table (`.planning/phases/37-shared-runner-options-and-session-ids/37-21-PLAN.md:130-132`).
- The proposed sample capture reuses the existing fake opencode, including its `ses_1`, auth, and capacity behaviors (`tests/test_cross_ai_runner_e2e.py:70-108`).
- Hosted-process limitations are explicitly documented, as required by the later-unit amendment (`.planning/phases/37-shared-runner-options-and-session-ids/37-RESEARCH.md:218-224`).

##### Concerns

- **HIGH — Capture fails before any sample is produced.** The prescribed script writes `<tmp>/home/.config/ai-kit/config.toml` but does not create its parent directories (`.planning/phases/37-shared-runner-options-and-session-ids/37-21-PLAN.md:126`). `runner_env()` creates `home` and sets `XDG_CONFIG_HOME`; it does not create `.config/ai-kit` (`tests/cross_ai_selftest.py:85-100`). The first write therefore raises `FileNotFoundError`. Create the parent directory explicitly before writing.
- **HIGH — The stated stub rule is not in the earlier plan on disk.** This plan creates `tests/test_cross_ai_settings_text.py` (`.planning/phases/37-shared-runner-options-and-session-ids/37-21-PLAN.md:131`), but the current `37-02-PLAN.md` Task 1 creates its help test and regenerates listings without creating the promised phase-wide stubs (`.planning/phases/37-shared-runner-options-and-session-ids/37-02-PLAN.md:125-149`). `tests/test_gate_scope.py:570-583` requires every discovered module in both generated listings. Without the stub or a listing update, a later full gate will fail.
- **MEDIUM — Same-wave test dependency is not safe under parallel execution.** Plan 37-21 runs `tests/test_cross_ai_skill_text.py` (`.planning/phases/37-shared-runner-options-and-session-ids/37-21-PLAN.md:135-137`); the current on-disk 37-22 modifies that same test (`.planning/phases/37-shared-runner-options-and-session-ids/37-22-PLAN.md:147-162`). There is no common file *write* between the plans, but one can test a partially edited file if the wave is parallelized. The supplied execution note says sequential execution; encode that constraint in the actual execution schedule or dependencies.
- **MEDIUM — The prescribed effort explanation cannot be derived from its eval input.** The prompt supplies only `effort=low ignored reason=id_carries`, while the expected answer demands the specific `#high` suffix (`.planning/phases/37-shared-runner-options-and-session-ids/37-21-PLAN.md:199`). The line establishes that the ID carries a value, not which value. Include the model ID or require only what the line proves.
- **MEDIUM — Lane budget risk.** Three commits, capture runs, 15 new test methods, four eval files and four repository-wide lint/type targets are combined in one plan (`.planning/phases/37-shared-runner-options-and-session-ids/37-21-PLAN.md:125-133`, `:161-168`, `:193-215`). This exceeds the requested five-file sizing heuristic; no timing evidence shows it fits the 1,800-second cap.

##### Suggestions

- Add `mkdir(parents=True, exist_ok=True)` for the capture config parent.
- Put the stub-and-listing work in 37-02’s actual task instructions, then fill the stub here.
- Order 37-21 and 37-22 explicitly, or ensure their tests do not read files while the other plan edits them.
- Split eval creation and its gates into a separate lane if measured hook time leaves insufficient budget.

##### Risk Assessment

**HIGH:** the first task has a deterministic setup failure, and the missing test registration threatens the aggregate gates.

##### Ponytail findings

- **MEDIUM:** The documentation, evals and lock are required; reuse of `runner_env()` and the existing fake is appropriate. The extra new test module is reasonable only if the promised shared stub/listing work is actually implemented. No unrelated feature is needed.

#### 37-22

##### Summary

This plan appropriately updates documentation that becomes stale when the runner changes. However, the supplied plan and the checked-out plan are different versions, and both retain an incorrect claim about MCP flags in `reviewExtras`. Execution must use one reconciled version before its checks can be trusted.

##### Strengths

- The marker test exercises the actual guard implementation rather than a duplicate scanner (`tests/test_arch_hardcoded_models.py:149-155`, `:170-199`).
- The current on-disk plan updates template-floor prose and its existing pins together (`.planning/phases/37-shared-runner-options-and-session-ids/37-22-PLAN.md:147-168`), addressing the version bump in `37-12-PLAN.md:131-137`.
- The baseline procedure refuses new violations and checks shrink-only behavior, consistent with the existing counter-based guard (`tests/test_arch_hardcoded_models.py:247-286`).

##### Concerns

- **HIGH — The submitted and on-disk plans disagree about the work and test ownership.** The supplied 37-22 says not to edit `tests/test_cross_ai_skill_text.py` or template-floor text; the checked-out plan explicitly edits that test, `runner.md`, README, and curated-config’s `SKILL.md` (`.planning/phases/37-shared-runner-options-and-session-ids/37-22-PLAN.md:147-168`). These are not interchangeable execution plans. The former leaves the version-8 pins and documentation stale after 37-12; the latter materially changes another skill and must include it in judging. Select and commit one authoritative version before dispatch.
- **HIGH — The allowlist premise contradicts 37-15.** Plan 37-22 says MCP flags will be added to `reviewExtras` and directs the executor to list them there (`.planning/phases/37-shared-runner-options-and-session-ids/37-22-PLAN.md:34`, `:128`). But 37-15 explicitly leaves every `reviewExtras` list unchanged and places MCP flags in the formulas (`.planning/phases/37-shared-runner-options-and-session-ids/37-15-PLAN.md:129-145`). The parenthetical is either false documentation or impossible to satisfy alongside the instructions to inspect the actual list.
- **MEDIUM — The allowlist test does not prove equality or runtime attribution.** Its helper unions flags from every row and the test only checks that each appears somewhere in the paragraph (`.planning/phases/37-shared-runner-options-and-session-ids/37-22-PLAN.md:129`). Extra documented flags and flags assigned to the wrong runtime pass. Compare an exact per-runtime mapping, with a mutation for an extra or misattributed flag.
- **MEDIUM — The same-wave ordering assumption needs enforcement.** On disk, this plan edits `tests/test_cross_ai_skill_text.py` while 37-21 runs it (`.planning/phases/37-shared-runner-options-and-session-ids/37-21-PLAN.md:135-137`). The supplied sequential-execution note mitigates this only if the orchestrator actually serializes the wave.
- **MEDIUM — 1,800-second budget risk.** The current on-disk plan changes more than five files, makes three commits and runs multiple broad gates (`.planning/phases/37-shared-runner-options-and-session-ids/37-22-PLAN.md:116-129`, `:147-168`, `:186-196`). It has no measured upper-bound evidence.

##### Suggestions

- Reconcile the prompt, file contents, manifest and stub rule into one committed revision.
- Document the formula-provided MCP flags separately from `CONFIG.extraArgs`’s allowlist.
- Pin the exact runtime-to-allowlist mapping and include a negative mutation.
- Preserve the floor updates from the current on-disk version and include every materially changed skill in 37-24’s judge set.

##### Risk Assessment

**HIGH:** plan-version drift and the contradictory MCP instruction can leave incorrect documentation or stop an unattended executor.

##### Ponytail findings

- **MEDIUM:** The existing `scan_text()` and current documentation tests are the right reuse points. The baseline script’s subset protection is justified; avoid adding a second allowlist source merely to make the documentation test pass.

#### 37-23

##### Summary

The scratch-first render and live-copy verification are warranted by RUN-06 and D-18. Several verification steps cannot pass as written, and the phase-wide prohibition scan is weaker than the conclusion it reports.

##### Strengths

- The scratch render checks the actual installer path and compares the live result to it before accepting the upgrade (`.planning/phases/37-shared-runner-options-and-session-ids/37-23-PLAN.md:112-117`).
- `check_runner_copy()` already checks the template version, pristine state and bytes outside the config block (`tools/check_dogfood.py:91-117`).
- The timing recorder uses the existing case list and shard infrastructure rather than introducing another benchmark format (`tests/cross_ai_selftest.py:211-263`, `:319-345`).

##### Concerns

- **HIGH — Re-running the live verification expects an upgrade result from an already upgraded runner.** `render.py live` requires `runner == "change"` (`.planning/phases/37-shared-runner-options-and-session-ids/37-23-PLAN.md:113-114`), then the automated verification calls the same live mode again (`:119-121`). For an identical pristine render, `plan_runner_upgrade()` returns `keep-pristine`, not `change` (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:282-289`). The verification consequently fails after a successful first run. Make verification read-only and accept the appropriate current-state result.
- **HIGH — The timing coverage check compares different types.** The plan asks to compare `set(list_cases())` with `recorded_secs()` keys (`.planning/phases/37-shared-runner-options-and-session-ids/37-23-PLAN.md:145`). `list_cases()` returns `(name, kind)` tuples, whereas the timing keys are names (`tests/cross_ai_selftest.py:211-237`). Compare `{name for name, _kind in list_cases()}` to the keys.
- **HIGH — The promised all-config-keys equality can reject the installer’s documented upgrade.** The dry run requires every old key and value unchanged (`.planning/phases/37-shared-runner-options-and-session-ids/37-23-PLAN.md:113`), but `_upgrade_config()` deliberately removes `prefer`, may derive `runtime`, and replaces `scrubEnv` (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:245-258`). Specify which migrations are permitted and require explicit review of any actual change rather than claiming all keys are preserved.
- **MEDIUM — The prohibition scan does not prove an added line is an edit of an existing line.** It compares only per-file counts (`.planning/phases/37-shared-runner-options-and-session-ids/37-23-PLAN.md:172`). Removing one unrelated line and adding a new prohibited test in the same file passes. Compare corresponding diff hunks and allow only explicitly identified pre-existing expected-message edits.
- **MEDIUM — The recorder’s shell does not establish the required scratch HOME.** The objective requires a scratch HOME for every helper (`.planning/phases/37-shared-runner-options-and-session-ids/37-23-PLAN.md:80`), but `record.sh` sets only `TMPDIR` and `AI_KIT_REFUSE_REAL_HOME` (`:144`). Although individual `run_cases()` children use `runner_env()` (`tests/cross_ai_selftest.py:273-287`), the recorder itself still inherits the caller’s HOME. Set HOME and XDG paths explicitly for the whole script.
- **MEDIUM — Cap risk:** the recorder is estimated at 4–6 minutes, the quiet wait can take 10 minutes, and eight shard runs, hooks and four broad gates follow (`.planning/phases/37-shared-runner-options-and-session-ids/37-23-PLAN.md:143-146`, `:180-187`). Those bounded waits alone can consume most of the 1,800-second lane.

##### Suggestions

- Separate one-time mutation from idempotent, read-only verification.
- Fix the case-name projection and add a deliberately missing/extra timing-entry check.
- Record permitted CONFIG migrations and compare all other fields explicitly.
- Split timing/quiet-machine work from rendering, or run the long wait outside the capped lane.
- Re-run the phase prohibition scan after judge fixes, not only before 37-24.

##### Risk Assessment

**HIGH:** two automated checks deterministically fail after the requested work, and the CONFIG assertion may reject a legitimate upgrade.

##### Ponytail findings

- **MEDIUM:** The installer and `check_runner_copy()` should remain the sole render mechanisms. The separate scan is justified, but its count-only heuristic is insufficient evidence for the stated prohibition; tighten it rather than adding another broad scanner.

#### 37-24

##### Summary

The orchestrator-only judge loop covers the required judge bar, regression comparison and recorded fixes. It has a material scope-selection risk and depends on machine-local, untracked drivers. The phase also lacks a planned aggregate `make test` run.

##### Strengths

- The frozen-tree check and two-judge pool checks provide useful controls around external reviews (`.planning/phases/37-shared-runner-options-and-session-ids/37-24-PLAN.md:127-132`, `:152-171`).
- The fix decision table explicitly covers both met and unmet bars and the three-round limit (`tmp/judge-36/decide.py:10-25`).
- The plan uses the existing judge reporting and gate tools rather than changing the rubric (`.planning/phases/37-shared-runner-options-and-session-ids/37-24-PLAN.md:181-194`).

##### Concerns

- **HIGH — The phase has no planned aggregate test gate.** Plan 37-24 explicitly runs no `make test` (`.planning/phases/37-shared-runner-options-and-session-ids/37-24-PLAN.md:95`), and the preceding ship plan runs shards and lint targets but not the aggregate (`.planning/phases/37-shared-runner-options-and-session-ids/37-23-PLAN.md:143-153`, `:177-187`). SPEC R11 and the repository instructions require `make test`, including installer behavior. Add a final orchestrator gate after all fixes, with the required temp isolation and cleanup.
- **HIGH — Material-change selection can miss a changed skill.** The proposed `material()` sorts removed and added lines before comparing them (`.planning/phases/37-shared-runner-options-and-session-ids/37-24-PLAN.md:128`). Reordering identical instructions can materially change scope or precedence while producing equal sorted lists, so a changed skill can be classified fact-only and never judged. Compare normalized full old and new file contents in order, and add a reordered-lines non-vacuity case.
- **MEDIUM — Scratch-driver copying is an unreproducible execution dependency.** The plan stops if fourteen untracked `tmp/judge-36` files are missing (`.planning/phases/37-shared-runner-options-and-session-ids/37-24-PLAN.md:111-122`), and copies them with textual version replacement (`:127`). Those files are available in this checkout, but they are not committed phase inputs; a clean checkout or cleaned scratch area cannot execute the plan. Provide a durable, versioned driver source or an explicit owner-approved recovery path.
- **MEDIUM — The documented scratch-HOME guarantee is not established by the reused driver itself.** The plan requires scratch HOME for helpers (`.planning/phases/37-shared-runner-options-and-session-ids/37-24-PLAN.md:89`), while `tmp/judge-36/lanes.py:47-48` simply inherits `os.environ` and adds the guard. Unless the orchestrator exports the scratch HOME and XDG variables before starting every driver, the promise is not enforced. The allowed reviewer-config exception should be documented separately from helper isolation.
- **MEDIUM — Judge fixes can invalidate the earlier prohibition scan.** 37-23 scans before the judge loop (`.planning/phases/37-shared-runner-options-and-session-ids/37-23-PLAN.md:172-175`); 37-24 can subsequently edit skill files and tests (`.planning/phases/37-shared-runner-options-and-session-ids/37-24-PLAN.md:193-194`). The stated no-new-target guarantee is not mechanically rechecked after those edits.

##### Suggestions

- Add a post-fix phase gate for `make test`, plus the final prohibition scan and cleanup verification.
- Use ordered, normalized file-content comparison for materiality and test insertion, deletion, reordering and template-number-only edits.
- Make driver provenance and recovery reproducible; explicitly set and verify the environment passed to helpers.

##### Risk Assessment

**HIGH:** the phase can otherwise close without its required aggregate test and can omit a materially changed skill from judging.

##### Ponytail findings

- **MEDIUM:** The judge loop is required by JDG-04, and reusing `judge_loop.py` and the existing decision table is appropriate. Fourteen copied scratch drivers introduce a substantial maintenance and availability dependency; a durable existing driver is preferable if it can preserve the same locked behavior.

---

##### Cross-plan coverage and review limits

All four requested plan IDs are covered above. The cited 0b items assigned to this batch—0b-4, 0b-5, 0b-8, 0b-1 and 0b-14—have plan carriers, but the findings above identify failures in their execution or verification. I did **not** exhaustively verify every SPEC edge or every earlier plan’s commands and Python complexity limits, so I cannot certify phase-wide coverage.

**Status: Issues Found — revise and re-review.**

No files were changed, no scratch files were created, and no test suites or make targets were run. The repository plans were untracked and differed from the supplied 37-22 text during this review; reconciling that version drift is the principal execution risk.


## Plan 37-26 review (referee-one, one cycle, 2026-11-21)

### Review conditions (37-26)

- 37-26 (curated-config's closed effort set) was added after cycle 1 of the other plans; it had one review cycle of its
  own, referee-one only (opencode, `router-env/my-referee-one`), with the cycle 1 drivers reused in
  `tmp/p37-review-26/` (locked note: the `RUNNER_IDS` gates stay an owner-recorded deferral). Exit 0 in 88 s,
  08:11-08:12. One fix pass applied the accepted findings; each carries a `Review c1 (...)` line in the plan's
  must_haves.truths. No second cycle (orchestrator instruction).

### 37-26 triage

- HIGH, plan absent from the roadmap schedule: accepted; ROADMAP.md lists 37-26 in wave 13 and says 26 plans.
- HIGH, the token refusal echoed the stored value (`{level!r}`) to CLI stderr: accepted; the message names the field and
  the pattern only, and the exact-text test proves the value is not echoed. The suggested CLI planted-secret test is not
  added (the exact message already excludes the value).
- MEDIUM, the final `EFFORT_LEVELS` scan over `tests` contradicts the negative `hasattr` assert: accepted; the scan covers
  `skills tools` only.
- MEDIUM, modes outside the effort ladder get no pin: accepted in part; the policy (no order, no pin, the runtime keeps
  its default) is stated in the `exec_effort` docstring and tested with `["off"]`; no order is invented.
- MEDIUM, no render-to-runner test: rejected; the render copies `config.effort` verbatim (cross_ai_script.py:106, pinned
  by tests/test_curated_config_script.py:84-87) and plan 37-06's self-test pins `CONFIG.effort` for a new runtime.
- MEDIUM, executor budget: recorded as a risk (small edits, no full-groups commit).

### referee-one (37-26)

Using the plan-review checklist and Ponytail to check 37-26 against its dependencies and the source, without modifying files or running tests.
## 37-26

### Summary

**Issues found; revise before execution.** The plan addresses a real D-07 gap and reuses the existing curated-config selection and validation paths. Its central edits are specific, but the phase roadmap does not schedule the new plan, one final acceptance check cannot pass as written, and the proposed selection and error-reporting paths have untested edge cases.

### Strengths

- **The dependency direction is sound.** The plan waits for 37-14 and 37-16 (`.planning/phases/37-shared-runner-options-and-session-ids/37-26-PLAN.md:5–6`), while 37-03 introduces the runner’s token regex and 37-06 makes `CONFIG.effort` a default for every runtime (`.planning/phases/37-shared-runner-options-and-session-ids/37-03-PLAN.md:129–135`; `.planning/phases/37-shared-runner-options-and-session-ids/37-06-PLAN.md:29–31`).
- **The validation boundary is explicit.** The replacement rejects non-strings and malformed tokens while retaining the model-presence check (`.planning/phases/37-shared-runner-options-and-session-ids/37-26-PLAN.md:154–171`). The existing plan validator reaches that function before validating artifact targets (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:1054–1065`).
- **The same-wave file lists do not overlap.** 37-26 edits curated-config files and its tests; 37-17 edits the runner and its describe test/fixture (`.planning/phases/37-shared-runner-options-and-session-ids/37-26-PLAN.md:7–14`; `.planning/phases/37-shared-runner-options-and-session-ids/37-17-PLAN.md:5–10`).

### Concerns

- **HIGH — The new plan is absent from the phase schedule.** 37-26 declares wave 13 and its dependencies (`.planning/phases/37-shared-runner-options-and-session-ids/37-26-PLAN.md:3–6`), but `.planning/ROADMAP.md:818` still says 25 plans, and its wave-13 list contains only 37-17 (`.planning/ROADMAP.md:859–863`). No later plan names 37-26 as a dependency; for example, 37-18 depends on 37-17 and 37-16 (`.planning/phases/37-shared-runner-options-and-session-ids/37-18-PLAN.md:5–6`). A roadmap- or dependency-driven run can therefore close without the curated-config fix.

- **HIGH — The proposed validation error can disclose secrets.** The replacement interpolates an arbitrary invalid `level` with `{level!r}` (`.planning/phases/37-shared-runner-options-and-session-ids/37-26-PLAN.md:163–169`). Plan files are read from disk and validation errors propagate through `_load_doc` (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:379–392`) to CLI stderr (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:598–600`). A pasted API key, including one nested in a non-string JSON value, can therefore be printed despite the plan’s “never print or write a secret” rule (`37-26-PLAN.md:86`).

- **MEDIUM — Final verification contradicts the test the plan requires.** The new test explicitly contains `hasattr(cross_ai, "EFFORT_LEVELS")` (`.planning/phases/37-shared-runner-options-and-session-ids/37-26-PLAN.md:255–261`), while the final verification requires `rg -n "EFFORT_LEVELS|cannot pin effort" skills tools tests` to print nothing (`37-26-PLAN.md:365–366`). It will find that test line even after the implementation is correct. This final check is also outside the objective and tasks that the stated executor receives.

- **MEDIUM — “Every runner” selection is not proved for host-listed modes outside the ladder.** The proposed `exec_effort` calls `roles.clamp_effort` and returns `None` unless its result is in the model’s modes (`.planning/phases/37-shared-runner-options-and-session-ids/37-26-PLAN.md:140–149`). `_nearest_effort` only orders tokens in `EFFORT_LADDER` (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/roles.py:15,65–83`); for a model listing only `["off"]` or another valid token outside that ladder, `clamp_effort("medium", modes)` returns `"medium"` and the proposed function silently drops the effort. The planned test uses only recognized ladder entries (`37-26-PLAN.md:214–223`). This falls short of the plan’s claim that a model with modes gets a clamped pin, though manually stored valid tokens would still pass validation.

- **MEDIUM — The test stops at the artifact, not the rendered runner.** Task 1 asserts the `config.effort` dictionary (`.planning/phases/37-shared-runner-options-and-session-ids/37-26-PLAN.md:214–223`), while the actual boundary is the rendered `CONFIG.effort`; the renderer copies that field in `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:93–106`. Existing 37-06 coverage exercises a configured default, but 37-26 does not connect its newly selected cursor/opencode effort through rendering to the runner report or argv. A regression at that handoff could satisfy its tests.

- **MEDIUM — The executor budget is a material risk.** The plan names six substantive source/test/doc files plus a possible baseline edit (`.planning/phases/37-shared-runner-options-and-session-ids/37-26-PLAN.md:7–14`), runs nine test modules and four repository-wide gates (`37-26-PLAN.md:307–308,331–339`), and must also wait for commit hooks (`37-26-PLAN.md:88`). That exceeds the review request’s “about five files” warning threshold; no timing evidence establishes that the whole plan, including hooks, fits the 1,800-second cap.

### Suggestions

- Add 37-26 to `.planning/ROADMAP.md` wave 13 and update the plan count; make phase closeout explicitly require its completion or summary.
- Do not echo arbitrary invalid values in validation errors. Add a planted-secret test through `load_plan` and the CLI error path, while preserving a useful field-and-pattern diagnostic.
- Restrict the final `EFFORT_LEVELS` scan to production code, or explicitly exclude the negative test; put the check in a task or objective so the executor receives it.
- Define and test the intended behavior for valid, host-listed modes outside the ordering ladder, including `off` and a new token. Do not invent an ordering for an unfamiliar level without stating that policy.
- Add a scratch render-and-dry-run test for at least one newly supported runtime, asserting the stored pin reaches `CONFIG.effort` and produces the expected setting report/argv.
- Measure the selected test and hook path, or split the gates/documentation work if it cannot reliably fit the lane cap.

##### Ponytail findings

- **LOW — Task 1 is needed and mostly reuses existing code.** D-07 requires removal of the refusal; the proposed edit uses `roles.clamp_effort` and the existing `script_artifact` path (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/roles.py:111–113`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py:370–388`). The two production callers are identified, but the rendered-runner handoff and unfamiliar-mode behavior need the checks above.
- **LOW — Task 2 is needed and proportionate.** The existing skill text explicitly limits pinning to pi and codex (`skills/ai-kit-gsd-curated-config/SKILL.md:126–133`). The later judge loop’s material-change rule covers this skill (`.planning/phases/37-shared-runner-options-and-session-ids/37-24-PLAN.md:25–27`).
- **MEDIUM — Task 3 adds no feature, but its execution cost needs proof.** The four gates follow repository policy; they are not speculative abstraction. Their combined cost, together with hooks, is the unresolved lane-time risk above. Existing test modules are reused, so no generated Makefile or pre-commit test listing change is needed.

### Risk assessment

**HIGH** until scheduling and secret-safe error handling are fixed. The implementation scope is otherwise focused, but the contradictory verification and incomplete selection-to-runner coverage could prevent unattended completion or conceal a functional gap.

### Status: Issues Found — fix and re-invoke

**Not checked:** I did not run tests or make targets, modify files, or perform an exhaustive phase-wide audit of the other 25 plans. Same-wave analysis is limited to 37-17 and 37-26; concurrent edits to the runner could still make 37-26’s template-reading test timing-sensitive.
