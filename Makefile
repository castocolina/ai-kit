# ai-kit — thin wrappers over the bootstrapper, the wizard, and the test runners.
# For repo cloners; the curl|bash one-liner carries the same flags (… -s -- --doctor).

INSTALL_SH := tools/install.sh
SETUP_PY   := tools/setup.py

# BEGIN GENERATED test groups
# arch: tests.test_arch
# unit-uv: tests.test_framework_profiles
# integration: tests.test_config_doctor tests.test_config_doctor_pty tests.test_doctor_screen tests.test_wizard_app_1 tests.test_wizard_app_2 tests.test_wizard_app_3 tests.test_wizard_pty
# e2e: tests.test_ai_kit_commit_fold_e2e tests.test_ai_kit_gsd_curated_config_matrix tests.test_ai_kit_gsd_spec_discuss_e2e tests.test_ai_kit_project_rules_all_e2e tests.test_ai_kit_spec_e2e tests.test_ai_kit_spec_goal_prompt_e2e tests.test_cross_ai_runner_e2e tests.test_cross_ai_selftest_logic_1_e2e tests.test_cross_ai_selftest_logic_2_e2e tests.test_cross_ai_selftest_logic_3_e2e tests.test_cross_ai_selftest_logic_4_e2e tests.test_cross_ai_selftest_runtime_1_e2e tests.test_cross_ai_selftest_runtime_2_e2e tests.test_cross_ai_selftest_runtime_3_e2e tests.test_cross_ai_selftest_runtime_4_e2e tests.test_curated_config_apply_e2e tests.test_curated_config_e2e tests.test_flow_index_e2e tests.test_hook_registry_e2e tests.test_jev_skill_install_e2e tests.test_markdown_to_pdf_e2e tests.test_precompact_shims_e2e tests.test_staged_commit_e2e tests.test_system_memory_e2e tests.test_worktree_e2e
# unit: tests.test_ai_kit_caller_text tests.test_ai_kit_commit_fold tests.test_ai_kit_commit_fold_adapters tests.test_ai_kit_gsd_curated_config tests.test_ai_kit_gsd_spec_discuss tests.test_ai_kit_opencode_providers tests.test_ai_kit_project_rules_agents tests.test_ai_kit_project_rules_all tests.test_ai_kit_project_rules_arch tests.test_ai_kit_project_rules_cicd tests.test_ai_kit_project_rules_docker tests.test_ai_kit_project_rules_makefile tests.test_ai_kit_project_rules_precommit tests.test_ai_kit_rules_common tests.test_ai_kit_session_wake tests.test_ai_kit_session_wake_fire tests.test_ai_kit_session_wake_reset tests.test_ai_kit_spec tests.test_ai_kit_spec_env_scrub tests.test_ai_kit_spec_goal_prompt_cli tests.test_ai_kit_spec_goal_prompt_common tests.test_ai_kit_spec_goal_prompt_evals tests.test_ai_kit_spec_goal_prompt_golden tests.test_ai_kit_spec_goal_prompt_host tests.test_ai_kit_spec_goal_prompt_matrix tests.test_ai_kit_spec_goal_prompt_objective tests.test_ai_kit_spec_goal_prompt_pointer tests.test_ai_kit_spec_goal_prompt_render tests.test_ai_kit_spec_goal_prompt_scope tests.test_ai_kit_spec_goal_prompt_signals tests.test_ai_kit_spec_goal_prompt_skilltext tests.test_ai_kit_spec_goal_prompt_strategies tests.test_ai_kit_spec_goal_prompt_variants tests.test_ai_kit_spec_gsd tests.test_ai_kit_spec_gsd_tools tests.test_ai_kit_spec_legacy_config tests.test_ai_kit_spec_routing tests.test_ai_kit_spec_runner_dispatch tests.test_ai_kit_spec_runtimes_table tests.test_ai_kit_spec_superpowers tests.test_ai_kit_spec_trust tests.test_ai_kit_usage_metrics tests.test_check_dogfood tests.test_claude_precompact tests.test_claude_session_wake_hook tests.test_cross_ai_catalog tests.test_cross_ai_skill_text tests.test_curated_config_apply tests.test_curated_config_cross_ai tests.test_curated_config_followups tests.test_curated_config_golden tests.test_curated_config_inventory tests.test_curated_config_plan_edit tests.test_curated_config_recommend tests.test_curated_config_script tests.test_curated_config_skills tests.test_cursor_agents tests.test_cursor_fakes tests.test_cursor_quota tests.test_cursor_status_line tests.test_decision_probe tests.test_doctor_apply_safety tests.test_env_matrix tests.test_external_segments tests.test_flow_boundary tests.test_flow_brief tests.test_flow_checkpoint tests.test_flow_contract tests.test_flow_docs tests.test_flow_index tests.test_flow_stack tests.test_gate_scope tests.test_global_rules tests.test_gsd_curated_eval tests.test_hook_registry tests.test_jev_fast_decision tests.test_markdown_to_pdf tests.test_marked_block tests.test_mermaid_style tests.test_phase26_owner_captures tests.test_pi_live_tools tests.test_precompact_core tests.test_quota_policy_text tests.test_rules_docs tests.test_run_unittest_parallel tests.test_setup tests.test_setup_dev tests.test_sibling_resolution tests.test_skill_evals_shape tests.test_staged_mapper tests.test_status_line tests.test_statusline_doctor tests.test_time_prepush tests.test_tool_advisor_core tests.test_tool_advisor_state tests.test_tool_substitution_hook
# END GENERATED test groups

.PHONY: install reconfigure uninstall doctor check test lint dev setup-env setup-dev validate e2e-docker \
        test-unit test-integration e2e-test arch-test test-env-matrix \
        py-compile pylint pyright ruff shellcheck vulture unittest unittest-wizard check-dogfood \
        format security-scanner duplicate-code

# Docker/podman auto-detect — prefers docker, falls back to podman.
CONTAINER_ENGINE := $(shell command -v docker 2>/dev/null || command -v podman 2>/dev/null)

install:
	bash $(INSTALL_SH)

# Provision the uv-managed dev/lint venv only (no hook install) — the part of
# `dev` that CI/agents need without also gating the repo's own commits.
# `uv sync` creates .venv if absent and is a no-op to re-run otherwise — no
# separate `uv venv` step (which errors on a venv that already exists).
setup-env:
	uv sync

# setup-env, plus install the pre-commit hooks so commits are gated.
# Runtime stays stdlib-only; venv is dev-only.
dev: setup-env
	uv run pre-commit install

# uv sync, the flow's missing tools, then the hooks (post-checkout included), each guarded: exits 0 when a step cannot finish.
setup-dev:
	python3 tools/setup_dev.py

reconfigure:
	bash $(INSTALL_SH) reconfigure

uninstall:
	bash $(INSTALL_SH) uninstall

doctor:
	bash $(INSTALL_SH) --doctor

check:
	bash $(INSTALL_SH) --check

# In-process modules with no subprocess/PTY/container — the fast, pure-unit tier.
# `unit` runs under bare system python3 (stdlib-only, matching the runtime);
# `unit-uv` needs PyYAML from uv.
test-unit:
	python3 tools/run_unittest_parallel.py --group unit
	uv run python3 tools/run_unittest_parallel.py --group unit-uv

# The `integration` group: Textual app and PTY-driven subprocesses wired
# together, without being a full install/E2E flow.
test-integration:
	uv run python tools/run_unittest_parallel.py --group integration

# The `e2e` group: real git worktrees, memory checks and real `node` runs
# against the checkout-local gsd-core, plus the shell-level install script.
e2e-test:
	uv run python tools/run_unittest_parallel.py --group e2e
	bash tests/test_install.sh

# AST architecture-fitness check (the runner's `arch` group) — no import/execution.
arch-test:
	python3 tools/run_unittest_parallel.py --group arch

# `test` is the aggregate entrypoint: tiers stay single-source-of-truth in
# their own targets above, never duplicated here.
test: test-unit test-integration e2e-test arch-test

# shellcheck + py-compile hooks (pre-commit, all files) — aggregate like validate.
lint: shellcheck py-compile
# Single-tool targets — each a thin delegate to its .pre-commit-config.yaml
# hook (never a duplicated file-scope regex) so a dev can run one check alone.
py-compile:
	uv run pre-commit run py-compile --all-files

pylint:
	uv run pre-commit run pylint --all-files

# stages: [pre-push] in .pre-commit-config.yaml — `pre-commit run` defaults to
# the pre-commit stage, so these four need --hook-stage pre-push to fire at all.
pyright:
	uv run pre-commit run pyright --all-files --hook-stage pre-push

ruff:
	uv run pre-commit run ruff --all-files

shellcheck:
	uv run pre-commit run shellcheck --all-files

vulture:
	uv run pre-commit run vulture --all-files --hook-stage pre-push

unittest:
	uv run pre-commit run unittest --all-files --hook-stage pre-push

unittest-wizard:
	uv run pre-commit run unittest-wizard --all-files --hook-stage pre-push

# The live-project check (dogfood runner copy pristine); the only reader of `.planning/`.
check-dogfood:
	uv run pre-commit run check-dogfood --all-files --hook-stage pre-push

# The six-environment proof (SPEC R7): all four tiers in six environments, compared module by
# module. Slow and not a gate: not part of `test`, `validate` or any hook (test_gate_scope pins it).
test-env-matrix:
	python3 tools/env_matrix.py

# Formatter: dev-only, mutates files — deliberately NOT wired into the
# validate/commit gate (auto-rewriting on every commit is a separate policy
# decision this target does not make for you).
format:
	uv run ruff format .

# Security scanner: ruff's S rule-set only ports a subset of Bandit's AST
# checks (astral-sh/ruff#20129), so this stays a dedicated pass.
# Informational/non-gating — not wired into validate; currently reports pre-existing findings unrelated to this plan.
security-scanner:
	uv run bandit -r tools skills

# Re-enables pylint's duplicate-code/R0801 check (globally disabled in
# pyproject.toml for cross-occurrence false positives on idiomatic blocks)
# as a narrowly-scoped, separate, non-gating invocation.
# Informational/non-gating — not wired into validate; currently reports pre-existing findings unrelated to this plan.
duplicate-code:
	uv run pylint --disable=all --enable=duplicate-code tools skills

# Quality gate. Each hook-backed single-tool target above stays the single
# source of truth for its own invocation/file-scoping (.pre-commit-config.yaml);
# this is a pure aggregate via Make prerequisites, never a duplicated command.
validate: ruff pylint pyright vulture shellcheck py-compile unittest unittest-wizard check-dogfood

# Clean-room E2E: builds a fresh container (no cached uv/textual, no
# pre-existing ~/.claude/~/.cursor/~/.config/opencode/~/.codex) and runs the
# full `make test`+`make lint` suite inside it — see tests/e2e/docker/.
e2e-docker:
	@if [ -z "$(CONTAINER_ENGINE)" ]; then \
		echo "err: neither docker nor podman found on PATH" >&2; exit 1; \
	fi
	$(CONTAINER_ENGINE) build -f tests/e2e/docker/Dockerfile -t ai-kit-e2e .
	$(CONTAINER_ENGINE) run --rm ai-kit-e2e
