# tests/e2e/docker/fixtures/ — convention (D-09)

This directory exists to hold runtime-specific E2E fixtures for later phases. It is
empty of runtime fixtures as of Phase 1.1 (Autonomous-Run Infrastructure) — per D-09,
fixture depth is deferred to the phase that actually needs it, not guessed at ahead of
that phase's own research.

## How a fixture reaches the clean-room container

`tests/e2e/docker/Dockerfile`'s existing `COPY --chown=aikit:aikit .
/home/aikit/ai-kit` already bakes any file placed under this directory into the
clean-room image at build time — the whole repo (minus `.dockerignore` exclusions)
is copied in once, before the container ever runs.

**Never** add a `podman run -v` (or `docker run -v`) volume mount to introduce a
fixture into the container. A volume mount reaches outside the image build and
defeats the entire point of a clean-room harness. For the same reason, **never**
volume-mount any of uz's real `~/.claude`, `~/.cursor`, `~/.config/opencode`, or
`~/.codex` into the container — that would corrupt the "genuinely fresh" guarantee
this harness exists to prove (see `.planning/ONESHOT-RULES.md` Rules 5/6).

## The actual fixture-usage pattern: copy into a scratch tree

A fixture file living under this directory is never read in place. Tests copy it
into a `tempfile`-rooted scratch tree before pointing environment variables
(`CLAUDE_CONFIG_DIR`, `AI_KIT_DIR`, `XDG_CONFIG_HOME`, etc.) at the scratch copy —
`shutil.copy` from a fixed repo-relative path into the scratch tree, never a live
in-place reference to this directory itself.

This follows two existing precedents already in this repo:

- `tests/test_system_memory_e2e.py:210-224` — copies from a fixed repo-relative
  path into a `tempfile.mkdtemp()`-rooted scratch tree before pointing `HOME` at it.
- `tests/test_setup.py:44-48` — the `FIXTURE_DIR = os.path.join(os.path.dirname(__file__),
  "fixtures")` constant convention for locating fixture files relative to the test
  module itself.

## Adding a fixture (future phases)

No runtime-specific fixture is added by Phase 1.1. Future phases will each add their
own fixture under `tests/e2e/docker/fixtures/<runtime>/<file>`, grounded in that
phase's own research, not guessed at now:

- **Phase 2** (Opencode Provider Management) — an `opencode.jsonc` fixture.
- **Phase 3** (Tool-Substitution Awareness Hook) — a Claude Code `settings.json`
  fixture plus a Cursor `hooks.json` fixture.
- **Phase 4** (Config Doctor) — a Codex TOML fixture.

Each of those phases should add its fixture using the copy-into-scratch-tree
pattern above, never a volume mount and never a live in-place reference.
