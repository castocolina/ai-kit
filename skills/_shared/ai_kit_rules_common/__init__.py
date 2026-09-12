"""Domain-agnostic infrastructure shared across the ai-kit rules-checker
skill family (AGENTS.md/CLAUDE.md, Makefile, pre-commit, arch, Docker
Compose, CI/CD). Each consuming skill reaches this package via its own
`sys.path` insert computed from `os.path.realpath(__file__)` -- see any
consuming skill's `__init__.py` for the exact pattern. This package itself
has no opinion on any specific skill's rule content or cache namespace.
"""
