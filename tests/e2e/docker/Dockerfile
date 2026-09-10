# ai-kit clean-room E2E harness — runs the FULL local test suite (unit tests +
# the PTY wizard E2E scenarios + tests/test_install.sh) inside a genuinely
# fresh container: no cached uv/textual, no pre-existing ~/.claude, ~/.cursor,
# ~/.config/opencode, or ~/.codex. Proves the installer works on a machine
# that has never run it before, not just on uz's already-provisioned dev box.
#
# Runtime code under test stays stdlib-only (see AGENTS.md); this image only
# provisions the DEV/lint/test toolchain (uv + its pinned deps), matching the
# project's own runtime/dev split.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      bash git curl ca-certificates shellcheck make \
    && rm -rf /var/lib/apt/lists/*

# Non-root scratch user — the whole point of this harness is that HOME here
# has never seen ai-kit, Claude Code, opencode, Cursor, or Codex config.
RUN useradd -m -s /bin/bash aikit
USER aikit
WORKDIR /home/aikit
ENV HOME=/home/aikit
ENV PATH="/home/aikit/.local/bin:${PATH}"

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY --chown=aikit:aikit . /home/aikit/ai-kit
WORKDIR /home/aikit/ai-kit

ENTRYPOINT ["bash", "tests/e2e/docker/run.sh"]
