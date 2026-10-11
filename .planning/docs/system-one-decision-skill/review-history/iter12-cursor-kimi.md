## Review: system-one-provisioning + system-one-decision-skill

### Document Type
superpowers · plan (both documents; ARCHETYPE = plan is the ceiling — judged on zero-context executability, exact files/code/commands, bite-sized verified steps)

### Files Read
Documents under review (fresh from disk):
- `docs/superpowers/plans/2026-10-10-system-one-provisioning.md` — 1640 lines ("Plan A")
- `docs/superpowers/plans/2026-10-10-system-one-decision-skill.md` — 1576 lines ("Plan B")

Grounding (llm-env): `pylib/compose.py`, `pylib/config.py`, `pylib/resources.py`, `pylib/budget.py`, `pylib/detect.py`, `pylib/gguf.py`, `llmenv.py`, `models.yml.example`, `scripts/start.sh`, `scripts/gpu-status.sh`, `scripts/check-setup.sh`, `scripts/check-server.sh`, `scripts/clean.sh`, `scripts/print-endpoints.sh`, `scripts/help.sh`, `tools/lib.sh`, `setup/setup.sh`, `setup/render-unit.sh`, `Makefile`, `docker/laya-rocm/Dockerfile`, `docker-compose.yml.example`, `tests/test_shell.py`, `tests/test_compose.py`, `tests/test_config.py`, `tests/test_detect.py`, `tests/test_resources.py`, `tests/test_cli.py`.

Grounding (skill): `/home/bazzite/.claude/skills/jev-fast-decision/SKILL.md`, `reference.md`, `scripts/jev_review.py`; `/home/bazzite/.claude/skills/skill-judge/SKILL.md`.

### CRITICAL
**Plan A**

- **GPU-pin provenance cites the wrong source** — Location: measured-facts table, line 19 ("Working pin: `/dev/kfd` and `/dev/dri:/dev/dri` (llm-server, `pylib/compose.py:80`)"). Required: correct the citation to the actual source — the 2026-10-11 live `podman run` measurement, corroborated by the run comment in `docker/laya-rocm/Dockerfile` (`--device /dev/kfd --device /dev/dri --group-add keep-groups --security-opt label=disable`). Why: `pylib/compose.py:80` is `"devices": ["/dev/dri:/dev/dri"]` and nothing else — llm-server is Vulkan and has no `/dev/kfd`, no `keep-groups`, no `label=disable` anywhere in `compose.py`. A zero-context engineer verifying the "VERIFIED LIVE" claim against the cited line finds it contradicted; the pin values themselves are correct (Task 3's test asserts exactly them), only the attribution is false.

### HIGH
None — in both documents. Task steps are bite-sized, TDD-ordered, carry exact code/commands, and every paste-range, helper signature, fixture line number, and test-math claim I spot-checked against the codebase resolved correctly (setup.sh 60–217/103–208, `llmenv.py:282/320`, `test_shell.py` 571/682/786/855/1338/4063/4476/4496/6776, the 4-branch `ResourceError` matrix, the 23008-MiB reservation math, jev_review.py monkeypatch surfaces, skill-judge dimension maxima 20/15×6/10=120 and grade-B band 96–107).

### MEDIUM
**Plan A**

- **Test comment contradicts the plan's own stub** — Location: Task 6, line 763 (`# GPU detection is not stubbed in this helper: reaching it is the assertion.`) vs the same task's helper change (line 710f) adding a `*' detect'*)` arm to `run_setup_no_gpu`'s uv stub. Required: reword the comment (e.g. "detection is stubbed; the assertion is that setup reached the detect path"), since the test passes precisely because the stub logs `uv ... detect` to `$CALLS` while returning fixture JSON. Why: as written the comment describes the opposite of the mechanism the plan installs; a maintainer "fixing" the comment's claim could delete the detect arm and silently void the test.

- **`validate-gguf` tripwire's stated mechanism is wrong for this fixture** — Location: Task 8, line 1295 ("Real `llmenv validate-gguf` returns exit 1 and `not found:` for those paths"). Required: correct the sentence (or add `gpu.backend`/`vram_total_mib`/`reserve_mode` to the fixture) so the described failure mode is real. Why: `run_check_setup_with_stubs`' written config (`tests/test_shell.py:4178-4182`) has no `gpu.backend`, `vram_total_mib`, or `reserve_mode`; `migrate_config` doesn't default them and `validate_config` rejects them (`pylib/config.py:256-260`), so `cmd_validate_gguf` dies in `require_valid_config` (`llmenv.py:483`) before `validate_gguf` ever runs — exit is nonzero but the message is a config-validation error, never `not found:`. Not CRITICAL because the tripwire the plan actually builds (nonzero exit when the Model-files section still runs) still fires; the cited function `pylib/gguf.py:validate_gguf` does return `not found:` — only the end-to-end CLI claim is false.

**Plan B**

None. The three-backend rework's claims about `jev_review.py` (constants, module-level `urllib` imports enabling the monkeypatches, `_opencode_auth_key`, receipt printing), `SKILL.md`/`reference.md` rewrite targets, the sha256/flaky-send logic, consent gates, free→paid retry matrix, and the owner-ruled calibration-corpus shape (composition rules + six exemplars + authoring step — not re-raised per ruling) all verified against the authoritative skill directory.

### Cross-Document Consistency
No findings. Port 8010, the activation line (`GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=... GSD_PATH_JEV_TIMEOUT_SECONDS=20`), the Task 11 health gate ordering, and the `notes/eval-results.json` handoff (Plan B Task 5 → 6) match across both documents.

### Status: Issues Found — fix and re-invoke

Skipped: re-running the plans' live-only gates (Laya latency/VRAM, idle-CPU A/B, eval CLI availability) — unverifiable offline; both plans self-gate on them. Risk: the CRITICAL is a one-line citation fix, but the table it sits in is the doc's trust anchor, so it's worth the re-invoke.
