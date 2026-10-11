I have sufficient grounding now. Let me compile the review report. Both plans are `plan` archetype under the superpowers framework. I verified all major factual claims against the codebase.

## Review: 2026-10-10-system-one-provisioning.md, 2026-10-10-system-one-decision-skill.md

### Document Type
superpowers · plan (both documents)

### Files Read
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md (1440 lines)
- /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md (890 lines)
- /var/home/bazzite/git/llm-env/scripts/start.sh, pylib/config.py, pylib/compose.py, pylib/resources.py, pylib/budget.py, pylib/detect.py, setup/setup.sh, setup/render-unit.sh, tools/lib.sh, scripts/check-setup.sh, scripts/check-server.sh, scripts/clean.sh, scripts/help.sh, llmenv.py, models.yml.example, .agents/architecture.md, AGENTS.md, docker/laya-rocm/Dockerfile, tests/test_config.py, tests/test_shell.py (grounding)
- /home/bazzite/.claude/skills/jev-fast-decision/scripts/jev_review.py, SKILL.md, reference.md (grounding)
- /home/bazzite/.claude/skills/skill-judge/SKILL.md (grounding)

### CRITICAL
(none)

### HIGH
- **`dispatch()` interface insufficient for `request_sha256` contract** — Location: Plan B, Task 3, Interfaces + Step 3 prose. Required: Specify how `screen()` obtains the wire bodies `send()` transmits, so `request_sha256` can be computed as the hash of their concatenation per `test_request_sha256_is_the_wire_bodies`. Why: The stated interface `dispatch(name, payload, timeout) -> (raw_responses: list[dict], specs)` returns only responses and specs — no wire bodies. `send(name, body, timeout) -> dict` returns only the response. The test asserts `result["request_sha256"]` equals `hashlib.sha256` of the concatenated wire bodies (`LayaStub.bodies`), but neither `dispatch()` nor `send()` exposes those bodies to `screen()`. The plan's prose says "request_sha256 is the hash of the exact bytes send() transmits" but never specifies the mechanism (a third return element from `dispatch()`, a side-channel from `send()`, or reconstruction via `request_body()` in `screen()`). A zero-context engineer cannot derive a passing implementation from the stated interfaces alone.

### MEDIUM
- **Unverified `cursor-agent` model names in live evaluation** — Location: Plan B, Task 8, Step 3. Required: Confirm `glm-5.2-max` and `gemini-3.1-pro` are valid `cursor-agent --model` values on the target host before the round dispatches, or substitute confirmed-available models. Why: The plan states "Owner asked for `glm-5.3`; cursor only offers `glm-5.2-high` and `glm-5.2-max`" for the GLM lane (acknowledged substitution), but `gemini-3.1-pro` is stated without any verification. If either model name is rejected by `cursor-agent`, both lanes fail to start and the round produces no report. This is a live-execution risk the plan can't catch at review time, but it should be confirmable with `cursor-agent --help` or a dry-run before committing to 3 rounds.

### Cross-Document Consistency
- Both plans declare a paired execution order with a clear boundary: Plan A Tasks 1–10 (or equivalent healthy Laya on port 8010) must complete before Plan B's Task 5 live eval, Task 7 calibration, and Task 8 final evaluation. Plan B's Tasks 0–4 and 6 run without Laya. The boundary is consistent and unambiguous.
- Plan B's default `JEV_LAYA_URL=http://127.0.0.1:8010` matches Plan A's `DEFAULT_SYSTEM_ONE_PORT = 8010`. Plan B's `system_one.port` reference matches Plan A's config key. Plan B's `system_one.enabled` reference matches Plan A's config key. No drift detected.
- Plan A's `docker/laya-rocm/Dockerfile` (untracked, confirmed on disk) is the source the plan moves to `docker/system-one/Dockerfile`. The move is grounded — the existing file has nearly identical content (the plan adds a version pin `laya[serve]==0.4.2` and a comment header). No conflict.

### Status: Issues Found — fix and re-invoke
