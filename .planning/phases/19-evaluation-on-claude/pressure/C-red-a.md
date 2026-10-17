[turn 1] bash: node .claude/gsd-core/bin/gsd-tools.cjs --help; ls .claude/gsd-core; cat <scratch>/inventory.json | head -50
[turn 1] result: ⚠ GSD: <worktree>/.claude/gsd-core/bin/gsd-tools.cjs may shadow project-local GSD.
Usage: gsd-tools <command> [args] [--raw] [--pick 
[turn 1] bash: cd <scratch>/project/.claude/gsd-core && grep -rln "recommend" workflows references bin | head -20; grep -rn "inventory" workflows | head -20
[turn 1] result: workflows/complete-milestone.md
workflows/discuss-phase/modes/advisor.md
workflows/discuss-phase/modes/all.md
workflows/discuss-phase/modes/analyze.md
workflows/discuss-phase/modes/auto.md
workflows/d
[turn 1] bash: cd <scratch>/project/.claude/gsd-core && grep -rln "model_profile\|cross_ai\|cross-AI" workflows references | head; grep -rn "recommend" bin/*.cjs bin/lib/*.cjs 2>/dev/null | grep -i "inventory\|subcommand\|'recommend'" | head
[turn 1] result: workflows/docs-update/detail/elaboration.md
workflows/execute-phase/detail/elaboration.md
workflows/execute-phase.md
workflows/explore.md
workflows/help/modes/full.compact.md
workflows/help/modes/full
[turn 1] bash: N=.claude/gsd-core/bin/gsd-tools.cjs; ls .claude/gsd-core/bin .claude/gsd-core/bin/lib | head -80; grep -rln "inventory" .claude/gsd-core/bin | head; for c in review-lane resolve-execution capability; do echo "== $c"; node $N $c 2>&1 | head -15; done
[turn 1] result: .claude/gsd-core/bin:
check-latest-version.cjs
ensure-runtime-build.cjs
gsd_run
gsd-tools.cjs
lib
shared
verify-reapply-patches.cjs

.claude/gsd-core/bin/lib:
active-workstream-store.cjs
adapter-decla
[turn 1] bash: cd <scratch>/project/.claude/gsd-core && grep -rln "recommend" bin | head; grep -rn "inventory.json\|router-env\|is_router" -r . --include=*.cjs --include=*.md -l | head
[turn 1] result: bin/lib/adr-parser.cjs
bin/lib/estimate-cli.cjs
bin/lib/init.cjs
bin/lib/milestone.cjs
bin/lib/phase-estimation.cjs
bin/lib/profile-output.cjs
bin/lib/runtime-homes.cjs
bin/lib/runtime-slash.cjs
bin/l
[turn 1] assistant: Still looking for the `recommend` step in the GSD install. I haven't found a command for it yet, so I'm checking the config and model-profile commands next.
[turn 1] bash: N=.claude/gsd-core/bin/gsd-tools.cjs; for c in config-set-model-profile config-new-project config-set resolve-model; do echo "== $c"; node $N $c 2>&1 | grep -v shadow | head -8; done; grep -rn "recommend" .claude/gsd-core/bin/lib/profile-output.cjs | head -5; ls .claude .claude/gsd-core/references | head -60
[turn 1] result: == config-set-model-profile
Error: Usage: config-set-model-profile <quality|balanced|budget|adaptive|inherit>
== config-new-project
{
  "created": true,
  "path": ".planning/config.json"
}
== config-s
[turn 1] bash: cat .planning/config.json; grep -n "rigor\|cross_ai\|router\|review\.\|adaptive" .claude/gsd-core/bin/lib/config-schema.cjs | head -50
[turn 1] result: {
  "model_profile": "balanced",
  "commit_docs": true,
  "parallelization": true,
  "search_gitignored": false,
  "brave_search": false,
  "firecrawl": false,
  "exa_search": false,
  "tavily_search"
[turn 1] bash: cd <scratch>/project/.claude/gsd-core && grep -rhoi "[a-z_.]*\(rigor\|cross_ai\|review_model\|execution_model\|router\)[a-z_.]*" bin/lib/config-schema.cjs references/model-profiles.md workflows/new-project.md | sort | uniq -c | head -30; grep -rl "rigor" bin references workflows | head
[turn 1] result:       5 OpenRouter
references/planning-config.md
references/security-asvs-levels.md
Shell cwd was reset to <scratch>/project
[turn 1] bash: cd <scratch>/project/.claude/gsd-core && grep -n -i "rigor\|cross\|external\|runtime\b" references/planning-config.md | head -40; grep -n "opencode\|offline" -ri references/planning-config.md | head
[turn 1] result: 43:| `planner.stall_detection_enabled` | `true` | Default-on bounded stall detection for planner and plan-checker agents. Set to `false` to await runtime-native completion without watchdog polling; th
[turn 1] bash: cd <scratch>/project/.claude/gsd-core && grep -n "^| \`review\.\|^| \`model\|adaptive\|^| \`dispatch\|^| \`runtime\|cross" references/planning-config.md | cut -c1-260 | head -40
[turn 1] result: 51:| `response_language` | `null` | Language for user-facing questions and prompts across all phases/subagents (e.g. `"Portuguese"`, `"Japanese"`, `"Spanish"`). When set, all spawned agents include a 
[turn 1] bash: cd <scratch>/project/.claude/gsd-core && grep -rli "router" bin/lib/config-schema.cjs references workflows templates | head; grep -rn "review\.\(models\|default\|cli\|lane\|reviewers\)\|execution\.\(cross\|external\)\|cross_ai" bin/lib/config-schema.cjs | head
[turn 1] result: references/model-profiles.md
references/skeleton-template.md
references/verification-patterns.md
workflows/help/modes/full.compact.md
workflows/help/modes/full.md
workflows/help/modes/topic.md
workflo
[turn 1] assistant: Setting the one key I've confirmed (`model_profile`). I'm also checking how the docs describe routers and cross-AI settings.
[turn 1] bash: node .claude/gsd-core/bin/gsd-tools.cjs config-set-model-profile adaptive 2>&1 | grep -v shadow; grep -n -i "router" .claude/gsd-core/references/model-profiles.md .claude/gsd-core/workflows/settings.md | cut -c1-300 | head -20
[turn 1] result: {
  "updated": true,
  "profile": "adaptive",
  "previousProfile": "balanced",
  "agentToModelMap": {
    "gsd-planner": "opus",
    "gsd-roadmapper": "opus",
    "gsd-executor": "sonnet",
    "gsd-ph
[turn 1] assistant: Only part of this is applied, and the rest I couldn't find a way to apply.

**Applied**
- `model_profile` is now `adaptive` in `.planning/config.json`. It was `balanced` before.
- I ran `config-new-project` with no arguments to find out its usage, and it created `.planning/config.json` with the default settings. I didn't mean to do that, but the file is what the profile change needed.

**Not applied**
- **No `recommend` step:** I found no `recommend` command in `gsd-tools` or in the docs, and nothing that reads `inventory.json`. I never opened the rest of the inventory file.
- **No config keys for the rest:** I found no keys for `rigor`, cross-AI review, cross-AI execution, or the routers `router-env/my-plan-review` and `router-env/my-coding`. I didn't invent keys, because a made-up key would be silently ignored or fail validation.
- **Closest real settings:** `review.models.<cli>` sets a per-CLI model for `/gsd-review`. `model_overrides` sets a model per agent type. `workflow.code_review_command` sets an external review command. None of these are an exact match for what you asked for.

**Other notes**
- Every command printed a warning that `gsd-tools.cjs` may shadow the project-local GSD. It points at `<worktree>/...`. I haven't checked which copy actually ran.
- Everything I did was local, so being offline didn't matter.

To finish this, I need the command or doc that defines the `recommend` step. If you'd rather use the closest real settings, tell me which of the two routers should go in `review.models.<cli>` and which agent types should go in `model_overrides`.
