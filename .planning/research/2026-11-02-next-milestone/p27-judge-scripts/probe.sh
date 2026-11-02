#!/bin/sh
# PONG probe of one referee through pi; usage: probe.sh my-referee-two
cd "$(dirname "$0")/../.." || exit 1
echo "Reply with exactly PONG" | timeout 180 env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT \
  -u CLAUDE_CODE_SSE_PORT -u OPENCODE -u CURSOR_AGENT -u PI_CODING_AGENT -u CODEX_THREAD_ID \
  -u CODEX_SANDBOX -u GROK_AGENT \
  pi -p --model "router-env/$1" --no-session --no-skills --no-extensions --offline
echo "probe-exit=$?"
