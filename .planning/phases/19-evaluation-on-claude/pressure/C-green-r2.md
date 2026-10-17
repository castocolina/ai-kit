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
[turn 1] bash: E=<worktree>/skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py; ls "$E" && python3 "$E" recommend --inventory <scratch>/inventory.json --profile adaptive --rigor rigorous --cross-ai-review y --cross-ai-exec y --out <scratch>/plan.json | head -c 6000; echo; echo exit=$?
[turn 1] result: <worktree>/skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py
{"out": "<scratch>/plan.json", "entries": 39, "nee
[turn 1] bash: python3 -I -c '
import json
p=json.load(open("<scratch>/plan.json"))
print(list(p.keys()))
for k in ("needs_choice","notes","warnings"):
    print(k, json.dumps(p.get(k),indent=1)[:5000])
print(json.dumps(p.get("artifacts"),indent=1)[:4000])
'
[turn 1] result: ['artifacts', 'cross_ai', 'entries', 'host', 'inventory_digest', 'notes', 'profile', 'rigor', 'schema_version', 'skill_affinity']
needs_choice null
notes [
 {
  "key": "manager.flags.execute",
  "kind
[turn 1] bash: python3 -I -c '
import json
p=json.load(open("<scratch>/plan.json"))
print(json.dumps(p["cross_ai"],indent=1))
for e in p["entries"]:
    print(e.get("key"), "|", e.get("status"), "|", json.dumps(e.get("value")) [:150], "|", e.get("why","")[:120] if isinstance(e.get("why"),str) else "")
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
code_quality.fallow.enabled | None | true | rigor rigorous preset (spec §5)
code_quality.
[turn 1] bash: python3 -I -c '
import json
p=json.load(open("<scratch>/plan.json"))
for e in p["entries"]:
    if e.get("status")=="needs_choice":
        print(json.dumps(e,indent=1)[:3000])
'
[turn 1] result: {
 "candidates": [
  {
   "model": "openai/gpt-5.6-luna",
   "price": null,
   "runtime": "opencode",
   "score": null,
   "why": "no scores; ordered by price, not quality"
  },
  {
   "model": "opena
[turn 1] assistant: I've run `recommend` and written the plan to `<scratch>/plan.json`. It has 39 entries and 4 open choices. The skill says I can't resolve these myself even when you're in a hurry, so I need your pick on each before I run the dry run.

Nothing is applied yet. The project config is untouched.

**Open choices**

1. **`model_profile_overrides.opencode.haiku`**: GSD's default `anthropic/claude-haiku-4-5` isn't on this host. The candidates are `openai/gpt-5.6-luna`, `openai/gpt-5.6-sol` and `openai/gpt-5.6-terra`. None have catalog scores, so they're ordered by price, which is unknown. My suggestion is `openai/gpt-5.6-luna`.
2. **`model_profile_overrides.opencode.sonnet`**: the default `anthropic/claude-sonnet-5` is also missing. It has the same three candidates, and I'd pick `openai/gpt-5.6-terra`.
3. **`model_profile_overrides.opencode.opus`**: the default `anthropic/claude-opus-4-8` is missing too. It has the same three candidates, and I'd pick `openai/gpt-5.6-sol`.
4. **`workflow.cross_ai_command`**: this sets `node .planning/scripts/cross-ai.mjs`, but the runner artifact still needs a model for the `cursor` target. The candidates are:
   - `claude-opus-5-5-high`
   - `claude-opus-5-5-low`
   - `claude-opus-5-5-xhigh`

   The `pi` target already uses `router-env/my-coding`. Alternatively, I can drop `cursor` with `plan-set script:cross-ai.prefer '["pi"]'`. That would leave the runner on `pi` only, with no `cursor` fallback, and it wouldn't need a cursor model.

   Because you're offline, I'd rather drop `cursor`. Say if you'd prefer a specific cursor model instead.

**Things you should know about**

- **Review router not wired:** `workflow.plan_review_convergence` is `false` because no review lane is eligible (the planner's vendor is unknown). Your `router-env/my-plan-review` router is not used anywhere in the plan yet. I can try wiring it with `plan-set review.models.opencode router-env/my-plan-review` and re-enabling convergence, but the plan doesn't propose it. Tell me if you want that.
- **Vision specialists keep their tier:** there is no image-input model on opencode, so `gsd-dom-verifier`, `gsd-ui-auditor` and `gsd-ui-researcher` fall back to their tier.
- **Specialist reviewers keep their tier:** `gsd-code-reviewer` and `gsd-plan-checker` keep their tier because no vendor could be inferred.
- **`live_dom_uat` is off:** it can be enabled via `plan-set` if you have a browser MCP.
- **Full permissions:** the runner is set up with no sandbox flags, so every exec target runs with full permissions.

Reply with your picks, for example "take your suggestions, drop cursor". I'll apply them and then show the dry-run rows by full key for your approval before the real apply.
