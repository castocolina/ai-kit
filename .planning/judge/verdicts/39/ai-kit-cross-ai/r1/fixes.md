# Loop 39 round 1 fixes: ai-kit-cross-ai

decide.py row: fix (1 high finding, bar met); no further judge round (AGENTS.md fix rule).

- D8-1 (referee-one, high): "The role confines the child" overstated the guarantee. The sentence now says the role picks each runtime's own restriction (opencode's review formula selects `--agent plan`, cross-ai.mjs:1799), that it is not a sandbox, that the capabilities line can report write, shell or MCP reach as `unknown`, that the review's git tree check finds checkout changes only after the call and sees nothing outside the checkout, and that a review whose child must not write needs containment verified on that host or the isolated checkout. File: skills/ai-kit-cross-ai/SKILL.md (section 2, before the launch block).
