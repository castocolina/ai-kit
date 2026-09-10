#!/usr/bin/env bash
# Entrypoint run INSIDE the ai-kit clean-room container (see Dockerfile).
# Runs the same suite `make test` runs on a dev box, but here HOME has never
# had ai-kit (or any AI CLI config) touch it before — this is the "does the
# installer actually work on a fresh machine" check, not a dev-box re-run.
set -euo pipefail

echo "==> clean-room HOME: $HOME"
echo "==> repo: $(pwd)"

echo "==> preflight: asserting no pre-existing AI-CLI config dirs"
for cfg_dir in "$HOME/.claude" "$HOME/.cursor" "$HOME/.config/opencode" "$HOME/.codex"; do
  if [ -e "$cfg_dir" ]; then
    echo "FATAL: $cfg_dir already exists — this container is not clean-room" >&2
    exit 1
  fi
done
echo "==> preflight: confirmed absent: \$HOME/.claude \$HOME/.cursor \$HOME/.config/opencode \$HOME/.codex"

echo "==> uv sync (dev/lint env only — runtime under test stays stdlib-only)"
uv sync

echo "==> make test"
make test

echo "==> make lint"
make lint

echo "==> ai-kit clean-room E2E: PASS"
