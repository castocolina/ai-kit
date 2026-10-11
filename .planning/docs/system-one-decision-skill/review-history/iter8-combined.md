## Reviewer cursor-sol
### Document Type
superpowers · plan (both documents)

### HIGH
- **Runtime dependency is undeclared** — Location: Provisioning Task 9, lines 1352–1362. Required: remove the runtime `sd` dependency or add it to prerequisite and tooling checks. Why: `make prerequisites` does not install or verify `sd`, so `make check-setup` can fail on a valid installation.
- **Live evaluation can silently calibrate from incomplete data** — Location: Decision-skill Task 5, lines 1203–1247; Task 8, lines 1420–1423. Required: fail unless all 32 cases return `status: ok`, and assert `n == 32` before recording or calibrating. Why: unavailable cases are currently skipped, allowing thresholds and final metrics to use a partial dataset.

### MEDIUM
- **GPU vendor detection lacks a direct test** — Location: Provisioning Task 6, lines 672–679 and 790–794. Required: add `tests/test_detect.py` coverage proving `list_gpus()` reads `device/vendor` and handles a missing vendor file. Why: shell tests stub the `vendor` result and cannot catch an incorrect sysfs implementation.
- **Log-count gates are timestamp-racy** — Location: Decision-skill Task 8, lines 1401–1430 and 1484–1509. Required: isolate each request count without second-resolution wall-clock overlap. Why: `date ... +%SZ` can include a preceding request from the same second, causing false failures for expected counts of zero or three.

### Cross-Document Consistency
- No cross-document contradictions found.

### Status: Issues Found — fix and re-invoke

## Reviewer opencode-glm53
### Document Type
superpowers · plan (both)

### Files Read
- docs/superpowers/plans/2026-10-10-system-one-provisioning.md (1583) — reviewed
- docs/superpowers/plans/2026-10-10-system-one-decision-skill.md (1528) — reviewed
- Grounding, llm-env: setup/setup.sh (269), scripts/start.sh (164), tools/lib.sh (331), setup/render-unit.sh (179), scripts/gpu-status.sh (200), scripts/check-setup.sh (293), scripts/check-server.sh (411), scripts/clean.sh (82), scripts/print-endpoints.sh (63), scripts/help.sh, Makefile, models.yml.example, docker-compose.yml.example, .agents/architecture.md, AGENTS.md, setup/prerequisites.sh, pylib/{config,compose,resources,budget,detect,gguf}.py, llmenv.py (verbatim via codegraph)
- Grounding, tests: tests/test_shell.py (11673; helper bodies at 571/682/1338/4063/4496/6776/10883), tests/test_config.py, tests/test_compose.py, tests/test_budget.py, tests/test_cli.py
- Grounding, skill: scripts/jev_review.py (305), SKILL.md (139), reference.md (126), skill-judge/SKILL.md (dimensions), ~/.local/share/opencode/auth.json (exists)
- Grounding, image: `localhost/laya-rocm` (laya 0.4.2 — serve knobs, `DEFAULT_MODELS`, `normalise_name`, `resolve_revision`→55cf4c4…, `allow_patterns` identical to the plan's, uvicorn access logging); `docker/laya-rocm/Dockerfile` untracked; research container `laya` present but stopped

Every line-number claim in both plans was verified against current disk state and found exact (setup.sh 36-58/60/101/103-208/210/217; start.sh:16-20; tools/lib.sh:324; check-setup.sh 53-57/83/233-237; check-server.sh `REQUEST_BODY_FILE`; test_shell.py 571/682/1338/4063/4496/4573/6776/10883; llmenv.py 282/320/436/603; resources.py four `ResourceError` strings; budget.py:119-120; architecture.md sections). All laya-package factual claims (version, knobs, model table, revision pin, download patterns) verified inside the image.

### HIGH
- **Undeclared `sd` runtime dependency in a validation gate** — Location: provisioning plan, Task 9 Step 3, `system_one_render_matches` (`sd '.*/dev/dri/([^:/]+).*' '$1'` pipeline). Required: the render-node check must behave correctly on any host that passes today's `make prerequisites` — extract the node with the repo's existing shell convention (as `presets_value` does with awk, tools/lib.sh:257) or declare `sd` in check-setup.sh's Tooling/`require_cmd` set and install it in `setup/prerequisites.sh`. Why: no script in the repo invokes `sd` and prerequisites installs it nowhere; under check-setup.sh's `set -uo pipefail` + `set +e`, a missing `sd` silently empties `$pinned` and records a false "system-one render node" FAIL whose stated reason (node mismatch) never occurred — a wrong diagnostic from the offline gate, invisible to tooling.

### MEDIUM
- **OmniRoute wait inherits the System One timeout** — Location: provisioning plan, Task 7 Step 3, the `LLM_ENV_HEALTH_TIMEOUT_SECONDS="$LLM_ENV_SYSTEM_ONE_HEALTH_TIMEOUT_SECONDS" wait_for_health "$system_one_port"` call added to scripts/start.sh. Required: the subsequent OmniRoute `wait_for_tcp_port` (scripts/start.sh:140) and its failure message (scripts/start.sh:163) must still use the llm-server `LLM_ENV_HEALTH_TIMEOUT_SECONDS` value. Why: bash persists a variable assignment prefixed to a *function* call after the function returns (unlike external commands), so after the System One wait the variable stays at 120s and the OmniRoute wait and its "did not become reachable within …s" message use the wrong timeout.
- **18.2 GB research image orphaned** — Location: provisioning plan, Task 11 Step 1 (and Task 10's clean scope). Required: after the plan completes, no research artifact remains — Task 11 must remove `localhost/laya-rocm` (verified present, 18.2 GB) or retag that already-verified image to `localhost/llm-env-system-one:rocm` instead of rebuilding 18.2 GB from the same Dockerfile. Why: Step 1 removes only the `laya` container; `make clean` removes only the configured `system_one.image`, so the research image is left on the host with no task that ever removes it.
- **LIVE check 3 rests on an unstated determinism assumption** — Location: decision-skill plan, Task 8 Step 2, LIVE check 3 ("answers.vague.probabilities from the two runs differ by at most 1e-3"). Required: the premise that two identical single-item requests return identical probabilities must be stated and grounded — e.g. run the twice-identical comparison once during Task 5's live eval and pin the tolerance from that measurement — or the check must be relaxable so an uncontaminated but slightly stochastic server can pass. Why: nothing in the spec table measures repeatability (only latency/accuracy); if inference is nondeterministic, LIVE 3 fails on every round while the FIX prompt (skill files only) can never repair it, burning all three rounds to a hard stop.
- **FIX-lane model id is the only one never verified** — Location: decision-skill plan, Task 8 Step 3, the `--model grok-4.7-high-fast` FIX invocation, versus the pre-round checks that confirm only `glm-5.2-max` and `gemini-3.1-pro`. Required: `grok-4.7-high-fast` must pass the same `cursor-agent --list-models | rg -x` confirmation before round 1, or be substituted with a confirmed id. Why: the plan's own discipline is verifying model ids before dispatch; the fixer id escapes it, and its unavailability aborts a failed round's fix step loudly but avoidably.
- **Kill-switch return moved after the stdin read** — Location: decision-skill plan, Task 3 Step 3, opening lines of `screen()`. Required: with `GSD_PATH_JEV != "1"`, `screen()` must return `{"status": "disabled"}` without reading stdin, as the current script does (jev_review.py:254-255) and as the Global Constraints state. Why: the new ordering runs `json.load(sys.stdin)` before the disabled return, so a disabled call with interactive (tty) stdin blocks awaiting EOF instead of returning immediately — a deviation from the stated contract that neither tests nor tooling will surface.

### Cross-Document Consistency
- Verified consistent: both headers' paired-plan execution orders agree (Plan B Tasks 0–4 Laya-free; Tasks 5–8 gated on Plan A Task 11 ending with `system_one.enabled: true` and healthy `http://127.0.0.1:8010`; Task 6 consumes Task 5's `notes/eval-results.json`; Task 8 Parts 1–2 parallel, Part 3 serialized glm→gemini). Plan A's print-endpoints skill line, appendix health JSON, and decision body (`model: jev-1`) match Plan B's `BACKENDS`/`JEV_LAYA_URL` defaults, `jev-1` request model, and Laya response contract; Plan A Task 11 Step 9 leaves the state Plan B Task 8 Step 1 requires.

### Status: Issues Found — fix and re-invoke

