Judge: my-referee-one
Reviewed-sha256: ccbcea9bd76c22984a64850e1c56edc67e19d8f89daa963c012d71735e036195
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=705s out=296854 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 97
Critical: 0
Important: 4

## Dimension scores

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 17/20 | Strong project-specific knowledge: exclusion provenance, pinned injections, report preservation, runner evidence and escalation anchors. Repeated policy statements dilute it. |
| D2: Mindset + Procedures | 13/15 | Explains why permanent exclusions, quota exclusions and capability floors must remain separate. Procedures are useful, but capability selection needs a stronger decision rule. |
| D3: Anti-Pattern Quality | 14/15 | Excellent concrete NEVER list with failure mechanisms, particularly `SKILL.md:22–41`. |
| D4: Specification Compliance | 15/15 | Valid frontmatter. The description supplies WHAT, WHEN, searchable terms and an explicit exclusion for inline execution. |
| D5: Progressive Disclosure | 12/15 | Mandatory reference-loading triggers are embedded at decision points, and design notes have conditional loading guidance. The 498-line entry point still repeats substantial reference content. |
| D6: Freedom Calibration | 10/15 | Appropriately restrictive about trust and failed-dispatch recovery, but assumes preference order establishes capability and leaves some fragile shell handoffs incomplete. |
| D7: Pattern Recognition | 9/10 | Clear Tool/Process hybrid: routing, exact commands, outcome branches and conditional references. |
| D8: Practical Usability | 7/15 | Detailed normal and quota paths, weakened by path-bootstrap mismatches and an incomplete no-result failure path. |
| **Total** | **97/120** | **Grade B — valuable specialist knowledge, but important operational defects remain.** |

Estimated knowledge ratio **E:A:R = 75:10:15**. Reference sizes are 139, 107, 43 and 153 lines: **940 package lines total**. Most content is expert material; the primary waste is repetition rather than basic tutorials.

## Findings

### 1. Important — `SKILL_DIR` does not survive the documented shell handoff

**Package:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:85–94`, used at **line 117**.

Step 0 prints only `SHIM` and `TOOLS_PY`, then explicitly says subsequent calls use literal values captured through `printf` because every Bash call starts a fresh shell. The wake block nevertheless requires `$SKILL_DIR`, which was never printed or otherwise included in that handoff.

Following the blocks literally leaves it unset. The wake path then resolves relative to `.` rather than the selected skill installation, typically producing the misleading “not installed” fallback and disabling the unattended-run wake.

**Fix:** Print and record `SKILL_DIR` alongside the other two values, or derive `WAKE_SHIM` entirely from the already-recorded `SHIM`.

### 2. Important — Step 0 accepts a review-skill location that its execution shim does not bootstrap

**Package:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:74–85`.

The resolver accepts `ai-kit-spec-review` from a plugin root or `~/.claude/skills` when it is absent beside the selected execution skill. However, the named execution shim adds only its own directory and the presumed sibling review directory to `sys.path`:

**Repository evidence:** `skills/ai-kit-spec-execute-superpowers/ai-kit-spec-superpowers.py:11–15`. Its introductory documentation also identifies that sibling package root as necessary at **lines 2–6**.

The independently selected `REVIEW_SKILL_DIR` only supplies `TOOLS_PY`; it is not communicated to `SHIM`. Consequently, successful Step 0 resolution does not establish that the execution shim can use that fallback installation.

**Fix:** Resolve the execution skill’s real directory and require its actual review sibling, failing clearly when absent. Alternatively, support the selected fallback directory in the bootstrap rather than merely resolving its separate CLI path.

### 3. Important — Preference order is treated as proof of greater capability

**Package:** `skills/ai-kit-spec-execute-superpowers/references/escalation.md:22–27`.

The reference correctly observes that choosing another survivor does not guarantee a more capable model, but then defines “strictly above” in a **most-preferred-first** ladder as sufficient proof.

Preference may encode cost, latency, provider preference or availability—not capability. For example, a ladder ordered `cheap > strong` allows replacing a stuck `strong` implementer with `cheap` while claiming to satisfy the stronger-model requirement. It can also reject a genuinely stronger model positioned lower for cost reasons.

Calling the ordering a “proxy” discloses the assumption but does not make the prescribed escalation satisfy the stated requirement.

**Fix:** Require explicit owner confirmation that the ladder is capability-ordered before using this rule. Without that confirmation, ask the owner to identify the stronger candidate instead of inferring capability from preference.

### 4. Important — The empty-result branch stops before preserving recovery state

**Package:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:325–333`.

The no-JSON branch executes an unconditional shell exit after printing only a generic exit message. It occurs before `REPORT_MODE=append`, and it supplies no executable path for writing the pinned resumable state required by the later `real_error` handler at **lines 430–438**.

The comment requests relaying stderr and stopping “as real_error,” but the normal classifier cannot consume an empty result. Thus the documented refusal/missing-prompt case requires the agent to invent a separate recovery procedure, precisely where the skill otherwise demands exact handling.

**Fix:** Define a dedicated no-result handler before classification: preserve append mode, read and report the diagnostic evidence, write pinned state from the existing injection without parsing absent result fields, and report its path before stopping.

### 5. Minor — Repeated policy text reduces the benefit of the reference split

**Package:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:39–53,443–447` and `skills/ai-kit-spec-execute-superpowers/references/design-notes.md:120–139`.

The no-switch and pre-dispatch-selection rules recur in the NEVER index, caller contract, outcome branches, closing policy paragraph and design notes. Some local repetition is justified for safety, but these passages repeatedly restate the same distinction rather than add decisions.

**Fix:** Keep the concise NEVER index and branch-local prohibitions. Shorten the duplicate closing paragraphs and retain only genuinely additional rationale in design notes.

## Verification scope

The named shims, `ai-kit-cross-ai/SKILL.md`, session-wake documentation and `ai_kit_spec/config_io.py` were inspected. The review-timeout override described in the design notes is supported by `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:643–650`. The referenced Superpowers harness and implementer template could not be located in this repository, so their exact headings and integration contracts remain unverified.

Not checked: live dispatch, scheduler behavior or imported implementation files outside the permitted reading scope; no state-changing commands were run.  
Risk: the bootstrap and failure-recovery defects need resolution before relying on unattended execution.
