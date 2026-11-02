#!/bin/sh
# Run every goal-prompt test module under the uv venv interpreter (Python 3.12) and print counts.
cd "$(dirname "$0")/../.." || exit 1
export AI_KIT_REFUSE_REAL_HOME=1
.venv/bin/python --version
for m in tests/test_ai_kit_spec_goal_prompt_*.py; do
  n=$(basename "$m" .py)
  printf '%s ' "$n"
  timeout 400 .venv/bin/python -m unittest "tests.$n" 2>&1 | grep -E '^(Ran|OK|FAILED)' | tr '\n' ' '
  echo
done
