[turn 1] result: 1	---
2	name: ai-kit-gsd-curated-config
3	description: Curated GSD `.planning/config.json` setup for a target project. v2 flow — inventory → recommend → plan edits → apply → follow-ups — picks models 
[turn 1] bash: d=<worktree>/skills/ai-kit-gsd-curated-config; [ -f "$d/ai-kit-gsd-curated-config.py" ] && printf '%s\n' "$d/ai-kit-gsd-curated-config.py"; ls <scratch>
[turn 1] result: <worktree>/skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py
candidates.json
fixture.json
green
gsd_home
hermetic-home
in
[turn 1] bash: cd /tmp && python3 <worktree>/skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py recommend --inventory <scratch>/inventory.json --profile adaptive --rigor rigorous --cross-ai-review y --cross-ai-exec y --out <scratch>/plan.json; echo exit=$?
[turn 1] result: {"out": "<scratch>/plan.json", "entries": 39, "needs_choice": 4, "notes": 8}
exit=0
Shell cwd was reset to <scratch>/project
[turn 1] bash: cd /tmp && python3 -I -c '
import json
p=json.load(open("<scratch>/plan.json"))
print(list(p.keys()))
for k in p:
    if k in("needs_choice","notes","warnings","artifacts"): print(k, json.dumps(p[k],indent=1)[:6000])
'
[turn 1] result: ['artifacts', 'cross_ai', 'entries', 'host', 'inventory_digest', 'notes', 'profile', 'rigor', 'schema_version', 'skill_affinity']
artifacts [
 {
  "choices": {
   "cursor": {
    "candidates": [
     
[turn 1] bash: cd /tmp && python3 -I -c '
import json
p=json.load(open("<scratch>/plan.json"))
print(json.dumps(p["cross_ai"],indent=1))
for e in p["entries"]:
    if e.get("status")=="needs_choice" or "review" in json.dumps(e.get("key","")): print(json.dumps(e,indent=1)[:2500])
'
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
 "existing": null,
 "key": "effort.agent_overrides.gsd-code-reviewer",
 "op": "set",
 "
[turn 1] assistant: I've run `recommend`, and the plan has 4 open choices. The skill says I can't pick these for you, even when you're in a hurry, so I'm pausing here. Nothing has been written to the project yet.

**Open choices**

1. `model_profile_overrides.opencode.haiku`
2. `model_profile_overrides.opencode.opus`
3. `model_profile_overrides.opencode.sonnet`
   - For each of these, the GSD default Anthropic model isn't on this host.
   - The candidates are `openai/gpt-5.6-luna`, `openai/gpt-5.6-sol` and `openai/gpt-5.6-terra`.
   - None have catalog scores, so they're ordered by price only, not quality.
4. Cross-AI execution runner model for `cursor`
   - The candidates are `claude-opus-5-5-high`, `claude-opus-5-5-low` and `claude-opus-5-5-xhigh`.
   - Also unscored.
   - `pi` is already set to your `router-env/my-coding`.
   - `workflow.cross_ai_command` stays open until `cursor` has a model.
   - You can instead drop `cursor` with `plan-set script:cross-ai.prefer '["pi"]'`, so execution runs on your router only.

**Notes from the plan**
- `workflow.plan_review_convergence` is set to `false`. The planner vendor is unknown, so there's no eligible review lane. Your `router-env/my-plan-review` router isn't wired in anywhere. I can try to enable it with `plan-set`, but I haven't checked whether that works.
- `gsd-code-reviewer` and `gsd-plan-checker` keep their tier, because no vendor could be inferred for them.
- `gsd-dom-verifier`, `gsd-ui-auditor` and `gsd-ui-researcher` fall back to their tier, because there's no image-input model on opencode.
- `workflow.live_dom_uat` is off unless a browser MCP is available.
- Cross-AI execution means running phases with `--cross-ai`. The v2 hook gives every exec target full permissions, with no sandbox.

**What I need from you**
- One model each for haiku, opus and sonnet. A reasonable spread is luna for haiku, terra for sonnet and sol for opus. That's only a price-order guess, so tell me if you'd rather have something else.
- For `cursor`, either a model or "drop it".
- Whether to try wiring `router-env/my-plan-review` for review.

After you answer, I'll resolve the choices, run the dry run and show you every add, change and remove row. I'll apply only after you confirm that.
