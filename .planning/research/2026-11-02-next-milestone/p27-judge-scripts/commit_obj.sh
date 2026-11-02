#!/bin/sh
# Three logical commits for the Full objective change.
cd "$(dirname "$0")/../.." || exit 1
export AI_KIT_REFUSE_REAL_HOME=1
git add skills/ai-kit-spec-goal-prompt/scripts/gp_render.py skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py \
  tests/test_ai_kit_spec_goal_prompt_objective.py tests/test_ai_kit_spec_goal_prompt_golden.py \
  tests/test_ai_kit_spec_goal_prompt_render.py tests/fixtures/goal_prompt/golden/opengsd-goal-pointer.md \
  Makefile .pre-commit-config.yaml
git commit -q -m "feat(27-goal-prompt): keep a shortened objective whole in a Full objective section" \
  -m "An objective longer than one 200-character rule line is still cut there, but the line now ends with '(full text: <path> section Full objective)' and the file gets a '## Full objective' section (before '## Full goal', wrapped at 100 columns, no line cap). Render prints full_objective. Files without a cut objective are unchanged."
git add skills/ai-kit-spec-goal-prompt/evals/evals.json tests/test_ai_kit_spec_goal_prompt_evals.py
git commit -q -m "test(27-goal-prompt): assert the Full objective section in the long-goal eval"
git add skills/ai-kit-spec-goal-prompt/SKILL.md skills/ai-kit-spec-goal-prompt/README.md \
  skills/ai-kit-spec-goal-prompt/references tests/test_ai_kit_spec_goal_prompt_skilltext.py
git commit -q -m "docs(27-goal-prompt): correct the overwrite and tmp/ statements, document the Full objective section" \
  -m "Render never overwrites (it writes a new -2 file); tmp/ is created by render only when git ignores it, and detect needs 'mkdir -p tmp' first. Drift tests tie both sentences to the code. The e2e MANDATORY read now precedes the first e2e readback."
git log --oneline | head -4
git status --short
