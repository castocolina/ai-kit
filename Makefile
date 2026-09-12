# ai-kit — thin wrappers over the bootstrapper, the wizard, and the test runners.
# For repo cloners; the curl|bash one-liner carries the same flags (… -s -- --doctor).

INSTALL_SH := tools/install.sh
SETUP_PY   := tools/setup.py

.PHONY: install reconfigure uninstall doctor check test lint dev setup-env validate e2e-docker \
        test-unit test-integration e2e-test arch-test \
        py-compile pylint pyright ruff shellcheck vulture unittest unittest-wizard \
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

reconfigure:
	bash $(INSTALL_SH) reconfigure

uninstall:
	bash $(INSTALL_SH) uninstall

doctor:
	bash $(INSTALL_SH) --doctor

check:
	bash $(INSTALL_SH) --check

# In-process modules with no subprocess/PTY/container — the fast, pure-unit tier.
# Runs under bare system python3 (stdlib-only, matching the runtime) except
# test_framework_profiles, which needs PyYAML (uv's venv, not the system python3).
test-unit:
	python3 -m unittest tests.test_setup tests.test_status_line tests.test_external_segments tests.test_statusline_doctor tests.test_markdown_to_pdf tests.test_mermaid_style tests.test_ai_kit_spec tests.test_ai_kit_spec_gsd tests.test_ai_kit_spec_superpowers tests.test_ai_kit_opencode_providers tests.test_tool_substitution_hook tests.test_ai_kit_usage_metrics tests.test_ai_kit_agents_md_rules_checker tests.test_ai_kit_gsd_curated_config tests.test_ai_kit_rules_common
	uv run python3 -m unittest tests.test_framework_profiles

# Multiple real components wired together (Textual app, PTY-driven subprocess)
# without being a full install/E2E flow.
test-integration:
	uv run python -m unittest tests.test_wizard_app tests.test_config_doctor_pty tests.test_config_doctor

# Genuine end-to-end flows: real git worktrees, PTY-spawned wizard/setup
# subprocesses, and the shell-level install script.
e2e-test:
	uv run python -m unittest tests.test_worktree_e2e tests.test_wizard_pty tests.test_system_memory_e2e
	bash tests/test_install.sh

# AST architecture-fitness check (tests/test_arch.py) — no import/execution.
arch-test:
	python3 -m unittest tests.test_arch

# `test` is the aggregate entrypoint: tiers stay single-source-of-truth in
# their own targets above, never duplicated here.
test: test-unit test-integration e2e-test arch-test

lint:
	shellcheck $(INSTALL_SH) tests/test_install.sh
	python3 -m py_compile $(SETUP_PY) tools/status-line.py tools/statusline-doctor.py tools/hooks/*.py tools/config_doctor_*.py skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py skills/ai-kit-usage-metrics/ai_kit_usage_metrics/*.py skills/ai-kit-agents-md-rules-checker/ai-kit-agents-md-rules-checker.py skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/*.py skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/*.py skills/_shared/ai_kit_rules_common/*.py

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

# Formatter: dev-only, mutates files — deliberately NOT wired into the
# validate/commit gate (auto-rewriting on every commit is a separate policy
# decision this target does not make for you).
format:
	uv run ruff format .

# Security scanner: ruff's S rule-set only ports a subset of Bandit's AST
# checks (astral-sh/ruff#20129), so this stays a dedicated pass.
security-scanner:
	uv run bandit -r tools skills -x tests

# Re-enables pylint's duplicate-code/R0801 check (globally disabled in
# pyproject.toml for cross-occurrence false positives on idiomatic blocks)
# as a narrowly-scoped, separate, non-gating invocation.
duplicate-code:
	uv run pylint --disable=all --enable=duplicate-code tools skills

# Quality gate. Each hook-backed single-tool target above stays the single
# source of truth for its own invocation/file-scoping (.pre-commit-config.yaml);
# this is a pure aggregate via Make prerequisites, never a duplicated command.
validate: ruff pylint pyright vulture shellcheck py-compile unittest unittest-wizard

# Clean-room E2E: builds a fresh container (no cached uv/textual, no
# pre-existing ~/.claude/~/.cursor/~/.config/opencode/~/.codex) and runs the
# full `make test`+`make lint` suite inside it — see tests/e2e/docker/.
e2e-docker:
	@if [ -z "$(CONTAINER_ENGINE)" ]; then \
		echo "err: neither docker nor podman found on PATH" >&2; exit 1; \
	fi
	$(CONTAINER_ENGINE) build -f tests/e2e/docker/Dockerfile -t ai-kit-e2e .
	$(CONTAINER_ENGINE) run --rm ai-kit-e2e
