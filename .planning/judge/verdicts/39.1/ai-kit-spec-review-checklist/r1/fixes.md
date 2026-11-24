# Loop 39.1 round 1 fixes: ai-kit-spec-review-checklist

One critical, important or high finding across the pool and the advisory lane (AGENTS.md: 3 or
fewer are fixed in the skill's own files; no further judge round). The skill's digest is stale by
design until its next loop.

- opencode:router-env/my-referee-one D8-1 (high): the Requirements checklist HIGH item now flags an OpenSpec requirement with no RFC-2119 keyword (SHALL or MUST for mandatory behavior, per the resolved profile) or a keyword weaker than the behavior needs, instead of any requirement missing "SHALL"; the Common Mistakes row says MUST is valid OpenSpec syntax. Matches the `rfc2119-shall` rule and `references/frameworks/openspec.md:33`. File: `skills/ai-kit-spec-review-checklist/SKILL.md`.
