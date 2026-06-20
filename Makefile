# ai-kit — thin wrappers over the bootstrapper, the wizard, and the test runners.
# For repo cloners; the curl|bash one-liner carries the same flags (… -s -- --doctor).

INSTALL_SH := tools/install.sh
SETUP_PY   := tools/setup.py

.PHONY: install reconfigure uninstall doctor check test lint

install:
	bash $(INSTALL_SH)

reconfigure:
	bash $(INSTALL_SH) reconfigure

uninstall:
	bash $(INSTALL_SH) uninstall

doctor:
	bash $(INSTALL_SH) --doctor

check:
	bash $(INSTALL_SH) --check

test:
	python3 -m unittest tests.test_setup tests.test_status_line tests.test_external_segments tests.test_markdown_to_pdf tests.test_worktree_e2e tests.test_wizard_pty
	bash tests/test_install.sh

lint:
	shellcheck $(INSTALL_SH) tests/test_install.sh
	python3 -m py_compile $(SETUP_PY) tools/status-line.py
