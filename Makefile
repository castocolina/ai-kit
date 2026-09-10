# ai-kit — thin wrappers over the bootstrapper, the wizard, and the test runners.
# For repo cloners; the curl|bash one-liner carries the same flags (… -s -- --doctor).

INSTALL_SH := tools/install.sh
SETUP_PY   := tools/setup.py

.PHONY: install reconfigure uninstall doctor check test lint dev validate e2e-docker

# Docker/podman auto-detect — prefers docker, falls back to podman.
CONTAINER_ENGINE := $(shell command -v docker 2>/dev/null || command -v podman 2>/dev/null)

install:
	bash $(INSTALL_SH)

# Provision the dev/lint environment (uv-managed, pinned via uv.lock) and install
# the pre-commit hooks so commits are gated. Runtime stays stdlib-only; venv is dev-only.
dev:
	uv sync
	uv run pre-commit install

reconfigure:
	bash $(INSTALL_SH) reconfigure

uninstall:
	bash $(INSTALL_SH) uninstall

doctor:
	bash $(INSTALL_SH) --doctor

check:
	bash $(INSTALL_SH) --check

test:
	python3 -m unittest tests.test_setup tests.test_status_line tests.test_external_segments tests.test_statusline_doctor tests.test_arch tests.test_markdown_to_pdf tests.test_worktree_e2e tests.test_wizard_pty tests.test_system_memory_e2e tests.test_ai_kit_spec tests.test_ai_kit_spec_gsd tests.test_ai_kit_opencode_providers tests.test_tool_substitution_hook
	bash tests/test_install.sh

lint:
	shellcheck $(INSTALL_SH) tests/test_install.sh
	python3 -m py_compile $(SETUP_PY) tools/status-line.py tools/statusline-doctor.py tools/hooks/*.py

# Quality gate. Runs the SAME pre-commit hooks that gate commits, across all
# files — so `make validate` and the commit hook can never drift. `uv run`
# auto-syncs the dev env first.
validate:
	uv run pre-commit run --all-files

# Clean-room E2E: builds a fresh container (no cached uv/textual, no
# pre-existing ~/.claude/~/.cursor/~/.config/opencode/~/.codex) and runs the
# full `make test`+`make lint` suite inside it — see tests/e2e/docker/.
e2e-docker:
	@if [ -z "$(CONTAINER_ENGINE)" ]; then \
		echo "err: neither docker nor podman found on PATH" >&2; exit 1; \
	fi
	$(CONTAINER_ENGINE) build -f tests/e2e/docker/Dockerfile -t ai-kit-e2e .
	$(CONTAINER_ENGINE) run --rm ai-kit-e2e
