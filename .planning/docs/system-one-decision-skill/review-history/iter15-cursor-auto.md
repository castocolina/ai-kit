I'll follow the review-checklist skill exactly and read the skill, framework profile, and both plans from disk first.Using **ai-kit-spec-review-checklist** to review both plans as `plan` against the superpowers profile. Reading the profile and both documents next.Plan A is loaded; reading Plan B in chunks and grounding key claims against both codebases.Codegraph was blocked; grounding with direct file reads. Continuing Plan B and checking the referenced code.Confirming one more grounding detail on the Task 6 GPU persistence gap, then emitting the report.## Review: `docs/superpowers/plans/2026-10-10-system-one-provisioning.md`, `docs/superpowers/plans/2026-10-10-system-one-decision-skill.md`
### Document Type
superpowers · plan (both)
### Files Read
- `/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-provisioning.md` (1673 lines)
- `/var/home/bazzite/git/llm-env/docs/superpowers/plans/2026-10-10-system-one-decision-skill.md` (1582 lines)
- `/home/bazzite/.claude/skills/ai-kit-spec-review-checklist/references/frameworks/superpowers.md` (52 lines)
- `/home/bazzite/.claude/skills/jev-fast-decision/scripts/jev_review.py` (305 lines)
- `/var/home/bazzite/git/llm-env/setup/setup.sh` (269 lines)
- `/var/home/bazzite/git/llm-env/pylib/resources.py` (159 lines)
- `/var/home/bazzite/git/llm-env/pylib/compose.py` (297 lines)
- `/var/home/bazzite/git/llm-env/pylib/config.py` (migrate/validate sections)
- `/var/home/bazzite/git/llm-env/pylib/detect.py` (list_gpus / processes_on_render_node)
- `/var/home/bazzite/git/llm-env/tools/lib.sh` (331 lines)
- `/var/home/bazzite/git/llm-env/scripts/check-setup.sh` (293 lines)
- `/var/home/bazzite/git/llm-env/scripts/check-server.sh` (request_record / REQUEST_BODY_FILE)
- `/var/home/bazzite/git/llm-env/scripts/start.sh`, `scripts/gpu-status.sh` (200 lines)
- `/var/home/bazzite/git/llm-env/docker/laya-rocm/Dockerfile` (21 lines)
- `/var/home/bazzite/git/llm-env/llmenv.py` (cmd_budget / cmd_resources)
- `/var/home/bazzite/git/llm-env/tests/test_shell.py` (helper line anchors)
- `/home/bazzite/.claude/skills/jev-fast-decision/SKILL.md` (frontmatter + NEVER)
### CRITICAL
- **Task 8 LIVE check 6 gates on ambiguous “accuracy”** — Location: Plan B Task 8 Step 3 LIVE prompt, check 6 (~line 1494). Required: the pass rule names the metric field `accuracy_when_not_fallback` (Task 7’s calibrate rule) and does not treat the separate report field `accuracy` as the ≥ 0.95 gate. Why: check 6 records both `accuracy` and `accuracy_when_not_fallback`, then says “Task 7’s rule holds: that accuracy >= 0.95”; Task 5 defines `accuracy` as clear-case correctness and Task 7’s rule as `accuracy_when_not_fallback >= 0.95` with `len(not_fallback) >= max(10, ceil(0.3*n))`. Those two readings pass/fail opposite live corpora.
### HIGH
- **system_one-only setup drops measured VRAM fields** — Location: Plan A Task 6 Step 3 layout (~lines 951–992), early `PCI_ADDRESS` write vs skipped Step 6. Required: whenever Step 2 selects a GPU for System One (including `llm_server.enabled: false`), persist the Step 2-measured `gpu.vram_total_mib` and `gpu.vram_budget_ceiling_mib` (same values Step 6 writes today at `setup/setup.sh:170-177`), not only `gpu.pci_address`. Why: today those fields are written only in Step 6 (Vulkan); the plan skips Step 6 when llm-server is off, so Review Focus mode leaves template `vram_total_mib: 0` / ceiling derived from that zero despite a successful detect.
### MEDIUM
- **`rocr_visible_index` can raise StopIteration** — Location: Plan A Task 3 Step 3 `rocr_visible_index` snippet. Required: a missing `drm_render_minor` in a KFD node’s `properties` becomes `ValueError` (same family as “no KFD GPU node…”), not an uncaught `StopIteration`. Why: `next(...)` over an empty generator is not converted; zero-context implementers will ship the paste as-is.
### Cross-Document Consistency
- Paired gates agree: Plan B Tasks 5–8 need System One enabled and healthy on 8010; Plan A Task 11 idle-CPU is not that gate; both assume port 8010 and stop when it is not.
- Activation line agrees: Plan A `print-endpoints` and Plan B Task 6 / Global Constraints use `GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port> GSD_PATH_JEV_TIMEOUT_SECONDS=20`.
- Plan B LIVE check 6’s metric ambiguity is internal to Plan B but is the gate that consumes Plan A’s live System One — fix Plan B before relying on paired E2E.
### Status: Issues Found — fix and re-invoke

Skipped: full live Laya/Zen re-probe; did not re-simulate Task 8 lanes. Risk: if check 6 is “fixed” by requiring overall `accuracy >= 0.95`, a corpus that only meets Task 7’s `accuracy_when_not_fallback` rule will still fail LIVE.
