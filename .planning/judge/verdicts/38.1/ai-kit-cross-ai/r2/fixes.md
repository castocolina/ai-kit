# Loop 38.1 round 2 fixes: ai-kit-cross-ai

Four high findings (referee-one; referee-two had none), more than three, so `decide.py met 4 2` gave
`next-round`: they are fixed here and the skill gets round 3. Each was checked against the runner
template `skills/ai-kit-spec-review/references/cross-ai.mjs` first.

- referee-one D8-1 (SKILL.md:52): confirmed (`SESSION_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/`, cross-ai.mjs:6612). The `--session-id` row now states the exact shape: an ASCII letter or digit first, then up to 127 of the allowed characters; any other shape is a usage error. File: skills/ai-kit-cross-ai/SKILL.md.
- referee-one D8-2 (subprocess-quota-policy.md:37): confirmed (`routeOf`, cross-ai.mjs:2677-2689: the flag wins; `routerBacked[cli] === true` confirms only when the model equals the pinned `CONFIG.models[cli]` or none is pinned). The quota bullet now names the pinned-model condition, the flag's precedence and tells the caller to read `route=` first. File: skills/ai-kit-cross-ai/references/subprocess-quota-policy.md.
- referee-one D8-3 (SKILL.md:149): confirmed (`max_retries` bounds the soft series only; the hard tier follows `hard_waits_s` and `hard_every_s`). The idle watchdog paragraph and the matching sentence at the end of the hard-tier schedule now say `max_retries` only shortens retries inside a call, and an earlier end of the episode needs a short `hard_waits_s` list with `hard_every_s = 0`. File: skills/ai-kit-cross-ai/SKILL.md.
- referee-one D8-4 (SKILL.md:328): accepted (an unconfirmed `CronCreate` can still have created the job, and a hand re-invoke would then run the lane twice). Section 6 now has the caller look for the job in `CronList` and confirm its time or delete it before the print-and-stop handoff, and, when neither can be confirmed, tell the owner a wake may be armed and not to start the lane by hand. File: skills/ai-kit-cross-ai/SKILL.md.
