[turn 1] result: 1	---
2	name: ai-kit-gsd-curated-config
3	description: Curated GSD `.planning/config.json` setup for a target project. v2 flow — inventory → recommend → plan edits → apply → follow-ups — picks models 
[turn 1] bash: for d in "<worktree>/skills/ai-kit-gsd-curated-config" "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-gsd-curated-config}" "$HOME/.claude/skills/ai-kit-gsd-curated-config"; do
  [ -f "$d/ai-kit-gsd-curated-config.py" ] && { printf '%s\n' "$d/ai-kit-gsd-curated-config.py"; break; }
done; WORK="$(mktemp -d)" && printf '%s\n' "$WORK"; ls -la <scratch>/project/.planning; cat <scratch>/project/.planning/config.json 2>/dev/null
[turn 1] result: <worktree>/skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py
<scratch>/tmp/tmp.pi1MCg3gb8
total 4
drwxr-xr-x. 2
[turn 1] bash: E=<worktree>/skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py; W=<scratch>/tmp/tmp.pi1MCg3gb8
cp <scratch>/project/.planning/config.json $W/config.pre-v2.json
python3 $E inventory --project-dir <scratch>/project > $W/inventory.json; echo inv=$?
python3 $E recommend --inventory $W/inventory.json --profile adaptive --rigor standard --cross-ai-review y --cross-ai-exec y --out $W/plan.json; echo rec=$?
python3 - <<EOF
import json
p=json.load(open("$W/plan.json"))
print(list(p.keys()))
for k in ("needs_choice","notes","warnings"):
    print(k, json.dumps(p.get(k),indent=1)[:6000])
EOF
[turn 1] result: inv=0
{"out": "<scratch>/tmp/tmp.pi1MCg3gb8/plan.json", "entries": 69, "needs_choice": 1, "notes": 13}
rec=0
['artifacts', 'cross_ai', 'entries', 'host', 'inventory_digest', 'notes', 'profil
[turn 1] bash: python3 - <<'EOF'
import json
p=json.load(open("<scratch>/tmp/tmp.pi1MCg3gb8/plan.json"))
print(json.dumps(p['cross_ai'],indent=1)[:2000])
for a in p['artifacts']: print(json.dumps(a,indent=1)[:5000])
for e in p['entries']:
    if e.get('needs_choice') or e.get('status')=='needs_choice' or 'choice' in json.dumps(e)[:300]: print(json.dumps(e,indent=1)[:2500])
print(set(e.get('op') or e.get('action') for e in p['entries']))
EOF
[turn 1] result: {
 "exec": {
  "answer": "y",
  "defaulted": false
 },
 "review": {
  "answer": "y",
  "defaulted": false
 }
}
{
 "choices": {},
 "config": {
  "models": {
   "cursor": "gemini-3.8-flash-low",
   "ope
[turn 1] bash: python3 - <<'EOF'
import json
p=json.load(open("<scratch>/tmp/tmp.pi1MCg3gb8/plan.json"))
for e in p['entries']:
    if e['op']=='unset': print('UNSET',e['key'],'existing=',e.get('existing'))
for e in p['entries']:
    if e['op']=='set' and e.get('status')!='needs_choice': print('SET',e['key'],json.dumps(e.get('value')),'| was',json.dumps(e.get('existing')))
EOF
[turn 1] result: UNSET effort.agent_overrides.gsd-assumptions-analyzer existing= high
UNSET effort.agent_overrides.gsd-code-reviewer existing= high
UNSET effort.agent_overrides.gsd-debug-session-manager existing= high
[turn 1] assistant: I've run the inventory and built the plan, and I'm pausing for your input before I touch the config. Nothing has been written to `.planning/config.json`. I saved a copy of it first, at `<scratch>/tmp/tmp.pi1MCg3gb8/config.pre-v2.json`.

**One decision for you: trusted skill roots.** Three global skills live outside the project and aren't covered by a trusted root: `mermaid-diagrams`, `react-dev` and `reducing-entropy`. The plan can add these roots to `agent_skills_security.trusted_global_roots`:
- `~/.agents/skills/mermaid-diagrams`
- `~/.agents/skills/react-dev`
- `~/.agents/skills/reducing-entropy`

If you approve, I add all three. If you decline, the skills stay wired, but gsd-core skips them and apply reports a warning.

**Removals that clash with "don't lose anything".** v2 manages whole key families, so it would remove 25 keys your old setup has:
- **`model_overrides`:** the `opus` pin on 10 agents (assumptions-analyzer, code-reviewer, debug-session-manager, debugger, eval-planner, framework-selector, planner, roadmapper, security-auditor, user-profiler). `gsd-executor: haiku` is re-set by the plan.
- **`effort.agent_overrides`:** the `high` setting on the same 10 agents.
- **`models`:** `models.research: haiku` and `models.execution: haiku`.
- **Other keys:** `model_policy.provider: generic`, `resolve_model_ids: omit` and `plan_review.source_grounding_authority: grep`.

`resolve_model_ids: omit` is removed because it breaks model resolution on a claude host. Your planner and reviewer `opus`/`high` pins would be replaced by the adaptive profile's own routing.

The plan also adds about 40 keys. The main ones are:
- `model_profile` goes from `balanced` to `adaptive`.
- Cross-AI execution is on, with a pi, cursor and opencode runner. This is full-permission, with no sandbox.
- Cross-AI plan review is on, through opencode.
- 13 `agent_skills` wirings.

I'll show every add, change and remove row by its full key in the dry run before I apply anything.

**What I need from you:**
1. Approve or decline the three trusted roots.
2. Tell me whether to keep any of the removed overrides. For example, I can leave the `opus`/`high` pins on the planner and code-reviewer in place. If you'd rather keep all of them, I can instead hold off on the migration until after the release.

Once you answer, I'll run the dry run and show you all the rows. I'll apply only after you confirm them.
[turn 2] bash: E=<worktree>/skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py; W=<scratch>/tmp/tmp.pi1MCg3gb8
python3 $E plan-set agent_skills_security.trusted_global_roots '["~/.agents/skills/mermaid-diagrams","~/.agents/skills/react-dev","~/.agents/skills/reducing-entropy"]' --plan $W/plan.json; echo set=$?
python3 $E apply --plan $W/plan.json --inventory $W/inventory.json --project-dir <scratch>/project --dry-run; echo dry=$?
[turn 2] result: {"key": "agent_skills_security.trusted_global_roots", "op": "set", "plan": "<scratch>/tmp/tmp.pi1MCg3gb8/plan.json", "warnings": []}
set=0
{"dry_run": true, "plan": "<scratch>/tmp/
[turn 2] assistant: I recorded the trusted-roots approval and ran the dry run. It was clean, with no warnings, and nothing has been written. Your "go ahead" came before you'd seen these rows, so I'm not applying yet. Please confirm them below.

**Removed (25):**
- `effort.agent_overrides.*` (was `high`) on `gsd-assumptions-analyzer`, `gsd-code-reviewer`, `gsd-debug-session-manager`, `gsd-debugger`, `gsd-eval-planner`, `gsd-framework-selector`, `gsd-planner`, `gsd-roadmapper`, `gsd-security-auditor` and `gsd-user-profiler`
- `model_overrides.*` (was `opus`) on those same 10 agents
- `models.execution` (was `haiku`)
- `models.research` (was `haiku`)
- `model_policy.provider` (was `generic`)
- `plan_review.source_grounding_authority` (was `grep`)
- `resolve_model_ids` (was `omit`)

**Changed:**
- `model_profile`: `balanced` → `adaptive`

**Added:**
- **Trusted roots:** `agent_skills_security.trusted_global_roots` gets `~/.agents/skills/mermaid-diagrams`, `~/.agents/skills/react-dev` and `~/.agents/skills/reducing-entropy`.
- **Effort and model:**
  - `effort.agent_overrides.gsd-code-fixer`: `medium`
  - `effort.agent_overrides.gsd-executor`: `medium`
  - `effort.routing_tier_defaults.heavy`: `xhigh`
  - `effort.routing_tier_defaults.standard`: `high`
  - `effort.routing_tier_defaults.light`: `low`
  - `model_overrides.gsd-code-fixer`: `haiku`
  - `model_overrides.gsd-ui-researcher`: `opus`
- **Workflow:**
  - `granularity`: `standard`
  - `intel.enabled`: `true`
  - `workflow.tdd_mode`: `false`
  - `workflow.ui_review`: `true`
  - `workflow.plan_review_convergence`: `true`
- **Cross-AI execution:**
  - `workflow.cross_ai_execution`: `true`
  - `workflow.cross_ai_command`: `node .planning/scripts/cross-ai.mjs`
  - `workflow.cross_ai_timeout`: `1800`
  - `manager.flags.execute`: `--cross-ai`
  - New file `.planning/scripts/cross-ai.mjs`, with prefer order pi, cursor, opencode
- **Cross-AI review:**
  - `review.default_reviewers`: `["opencode"]`
  - `review.effort.opencode`: `high`
  - `review.models.opencode`: `router-env/my-plan-review`
- **Skills, all new (`agent_skills.*`):**
  - `gsd-code-fixer`: `global:ponytail:ponytail`, `global:reducing-entropy`
  - `gsd-code-reviewer`: `global:ponytail:ponytail-review`, `global:ponytail:ponytail-audit`, `global:reducing-entropy`
  - `gsd-debug-session-manager`: `global:superpowers:systematic-debugging`
  - `gsd-debugger`: `global:superpowers:systematic-debugging`
  - `gsd-doc-writer`: `global:mermaid-diagrams`
  - `gsd-eval-auditor`: `global:ponytail:ponytail-review`, `global:ponytail:ponytail-audit`
  - `gsd-executor`: `global:ponytail:ponytail`, `global:frontend-design:frontend-design`, `global:react-dev`
  - `gsd-nyquist-auditor`: `global:ponytail:ponytail-review`, `global:ponytail:ponytail-audit`
  - `gsd-planner`: `global:ponytail:ponytail`
  - `gsd-security-auditor`: `global:ponytail:ponytail-review`, `global:ponytail:ponytail-audit`
  - `gsd-ui-auditor`: `global:ponytail:ponytail-review`, `global:ponytail:ponytail-audit`, `global:frontend-design:frontend-design`
  - `gsd-ui-researcher`: `global:frontend-design:frontend-design`, `global:react-dev`
  - `gsd-verifier`: `global:ponytail:ponytail-debt`

**Kept unchanged:** `model_overrides.gsd-executor` (`haiku`), `workflow.code_review_depth`, `workflow.nyquist_validation`, `workflow.pattern_mapper`, `workflow.plan_check`, `workflow.research`, `workflow.security_asvs_level`, `workflow.security_block_on`, `workflow.ui_phase` and `workflow.verifier`.

**Before you confirm:**
- Cross-AI execution runs every target (pi, cursor, opencode) with full permissions, with no sandbox. This is the v2 default.
- `gsd-planner` and `gsd-code-reviewer` lose their `opus`/`high` pins. The adaptive profile routes them instead.
- If anything breaks, the pre-migration config is at `<scratch>/tmp/tmp.pi1MCg3gb8/config.pre-v2.json`. Apply also makes its own backup.

Reply "apply" to write these changes. If you want any removal kept, tell me which one. For those I'd need to change the plan first.
[turn 3] bash: E=<worktree>/skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py; W=<scratch>/tmp/tmp.pi1MCg3gb8
python3 $E apply --plan $W/plan.json --inventory $W/inventory.json --project-dir <scratch>/project > $W/apply.json; echo apply=$?
python3 - <<EOF
import json
r=json.load(open("$W/apply.json"))
for k,v in r.items():
    if k not in("diff",): print(k, json.dumps(v,indent=1)[:3500])
EOF
[turn 3] result: apply=0
applied true
config_path ".planning/config.json"
created_config false
backup {
 "path": ".planning/config.json.bak-20261017T205528Z",
 "reused": false
}
reconciled []
writes [
 {
  "key": "age
[turn 3] assistant: The apply committed with exit 0 and no warnings. Config backup: `.planning/config.json.bak-20261017T205528Z`. The runner `.planning/scripts/cross-ai.mjs` was written and is active. All 13 skill wirings came back with no warnings.

I haven't run the follow-up yet. It needs your yes or no.

**Required follow-up: `effort_sync`**
- **Command:** `<home>/.volta/bin/node <worktree>/.claude/gsd-core/bin/gsd-tools.cjs effort sync --apply --runtime claude --config-dir <scratch>/project/.claude --project-dir <scratch>/project`
- **Working directory:** `<scratch>/project`
- **Purpose:** sync effort settings into agent frontmatter for this host.
- **Expected effect:** the dry run reports 0 changes.
- **Unverified:** the `--config-dir` value is inferred from the host layout.
- **Fingerprint:** `1537b8326b670b6d`

Should I run it? Since it should change nothing, skipping it is also safe.

**Suggestion:** run `/gsd-map-codebase` to build the intel index. `intel.enabled` is now on.

**Release-day notes:**
- Cross-AI execution runs every target (pi, cursor, opencode) with full permissions, and no sandbox. Print each `AIKIT-XAI status=…` line when you run with `--cross-ai`.
- To roll back, restore `.planning/config.json.bak-20261017T205528Z`. A second copy of the old config is at `<scratch>/tmp/tmp.pi1MCg3gb8/config.pre-v2.json`.
- I haven't run a GSD phase to test the new config end to end.
