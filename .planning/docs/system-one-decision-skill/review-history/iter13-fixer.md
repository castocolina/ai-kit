## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md

### Findings addressed
- **GPU-pin provenance cites the wrong source** — Severity: CRITICAL. Status: addressed. Edit: The working pin is now attributed to the 2026-10-11 live `podman run` measurement and the run comment in `docker/laya-rocm/Dockerfile` (`--device /dev/kfd --device /dev/dri --group-add keep-groups --security-opt label=disable`); llm-server is described as mapping only `/dev/dri:/dev/dri` at `pylib/compose.py:80`, with no `/dev/kfd`. Section: measured-facts table, GPU pin row.
- **Test comment contradicts the plan's own stub** — Severity: MEDIUM. Status: addressed. Edit: Reworded the comment to say detection is stubbed and the assertion is that setup reached the detect path. Section: Task 6, `test_setup_system_one_runs_gpu_detection_even_without_llm_server`.
- **`validate-gguf` tripwire's stated mechanism is wrong for this fixture** — Severity: MEDIUM. Status: addressed. Edit: The tripwire sentence now says real `llmenv validate-gguf` exits 1 from `require_valid_config` (`llmenv.py:483`) with a config-validation error because the fixture has no `gpu.backend`, `vram_total_mib`, or `reserve_mode`, and never prints `not found:`. Section: Task 8, `test_check_setup_skips_model_files_when_llm_server_disabled_and_gguf_absent`.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None.

### Findings not yet addressed
None.

### Status: Edits Applied

## Fix Summary: /var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Document
/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md

### Findings addressed
- **Task 8 hardcoded judge lanes** — Severity: owner ruling (not in the report). Status: addressed. Edit: Added Step 0 so the owner fills `LANES`, `VERIFY`, and `FIX_CMD` in `notes/eval-lanes.md` (illustrative `sol|cursor-agent … --model <model>` is a comment; the assignments start empty) and verifies each lane before round 1. Parts 1–2 loop over `LANES` in parallel, one pid each; Part 3 runs them in array order. Pass rule is every chosen lane, lowest Part 1 total ≥ 96. Report names are `eval-<lane>-<round>.md`. Removed `glm-5.3`, `gemini-3.1-pro`, `grok-4.7-high-fast`, `opencode-go`, and the opencode judge notes from Task 8 and the header execution note. Section: header execution note and Task 8.

### Findings escalated
None.

### Findings skipped (with disagreement noted)
None.

### Findings not yet addressed
None. The report had no Plan B findings. The full 32-case corpus was not added.

### Status: Edits Applied

Net growth: Plan A +0 lines (1640), Plan B +10 lines (1576 → 1586). The two generic lane loops are 48 lines against the old 51-line pair of hardcoded lanes.

Skipped the Laya image, skill-judge, and writing-skills reads; this report did not flag those. Risk: a judge or FIX command is split on spaces, so an argument that itself contains a space will not survive; `VERIFY` is run with `bash -c`, so that listing command may be a pipeline.
