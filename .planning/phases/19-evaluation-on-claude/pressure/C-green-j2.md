[turn 1] result: 1	---
2	name: ai-kit-gsd-curated-config
3	description: Curated GSD `.planning/config.json` setup for a target project. v2 flow — inventory → recommend → plan edits → apply → follow-ups — picks models 
[turn 1] result: 1	{
2	  "candidate_heuristic_fields": [
3	    "family",
4	    "fast_twin_of",
5	    "vendor"
6	  ],
7	  "candidates": [
8	    {
9	      "catalog_key": null,
10	      "family": "claude-fable-5-1",
11	 
[turn 1] bash: E=<worktree>/skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py; ls $E && python3 $E recommend --inventory <scratch>/inventory.json --profile adaptive --rigor rigorous --cross-ai-review y --cross-ai-exec y --out <scratch>/plan.json
[turn 1] result: <worktree>/skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py
{"out": "<scratch>/plan.json", "entries": 39, "nee
[turn 1] bash: cd <scratch>; python3 -c "
import json;p=json.load(open('plan.json'));print(list(p.keys()))
for k,v in p.items():
  if k!='entries': print(k, json.dumps(v,indent=1)[:6000])
for e in p.get('entries',[]):
  print(json.dumps(e)[:400])
"
[turn 1] result: ['artifacts', 'cross_ai', 'entries', 'host', 'inventory_digest', 'notes', 'profile', 'rigor', 'schema_version', 'skill_affinity']
artifacts [
 {
  "choices": {
   "cursor": {
    "candidates": [
     
[turn 1] bash: cd <scratch>; python3 -c "
import json;p=json.load(open('plan.json'))
for e in p['entries']:
  if e.get('status')=='needs_choice' or 'candidates' in e:
    e=dict(e); c=e.pop('candidates'); print(json.dumps(e)); print('  ',[x['model'] for x in c])
"
[turn 1] result: {"existing": null, "key": "model_profile_overrides.opencode.haiku", "op": "set", "source": "preset", "status": "needs_choice", "value": null, "why": "gsd default anthropic/claude-haiku-4-5 not on host
[turn 1] assistant: I've run `recommend`, but I can't apply yet. Four choices are still open, and the skill says I can't resolve them for you, even when you're in a hurry. The plan is at `<scratch>/plan.json`.

**Open choices**

1. **`model_profile_overrides.opencode.haiku`, `.sonnet` and `.opus`.** GSD's default Anthropic models aren't on your opencode host, and no candidate has a catalog score. The candidates are `openai/gpt-5.6-luna`, `openai/gpt-5.6-sol` and `openai/gpt-5.6-terra`, listed by price only.
   - My suggestion is luna for haiku, terra for sonnet and sol for opus. That follows the same luna/terra/sol tiers gsd-core uses for codex.
   - Do you want that mapping, or `plan-unset` on any of them?
2. **`workflow.cross_ai_command`.** The execution runner has two targets:
   - `pi` is set to `router-env/my-coding`, as you asked.
   - `cursor` has no model chosen yet. The candidates are `claude-opus-5-5-high`, `-low` and `-xhigh`, ordered by price rather than quality.
   - I suggest dropping cursor, so the runner prefers only `pi` and your router, with no extra paid model. Or pick a cursor model.

**Other plan notes**
- **No review router in the plan.** Your `router-env/my-plan-review` isn't wired to anything. The plan has no review-model entry for it. `workflow.plan_review_convergence` is `false`, with the reason "no eligible review lane: planner vendor is unknown". I won't wire a router in by hand. Tell me if you want it re-enabled with `plan-set`.
- **Unverified effect.** The `dynamic_routing.*` settings (`enabled`, `escalate_on_failure`, `max_escalations`) carry this flag: "no tier_models; resolve-model --attempt unchanged in gsd-core 1.16".
- **Vision overrides.** `gsd-dom-verifier`, `gsd-ui-auditor` and `gsd-ui-researcher` have no image-capable model on opencode, so they fall back to their tier.
- **No override for two agents.** `gsd-code-reviewer` and `gsd-plan-checker` also fall back to their tier, because no vendor could be inferred.
- **Optional.** `workflow.live_dom_uat` stays off. You can enable it if a browser MCP is available.
- **Execution runs with full permissions.** Every target runs unsandboxed under the v2 runner hook.

Once you answer, I'll run the `plan-set` calls and then the dry run. I'll list every key it would add, change or remove, one per line, and apply only after you approve that list.

Reply "yes to suggestions" to take all of the above, or give me your changes.
