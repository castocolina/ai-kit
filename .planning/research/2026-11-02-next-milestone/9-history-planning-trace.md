# History trace: were the owner's nine wishes asked before, and what happened?

Read-only archaeology over planning artifacts (not chat transcripts), 2026-11-02. Sources:
`.planning/milestones/` (phase CONTEXT, DISCUSSION-LOG, SPEC, VERIFICATION, SKILL-JUDGE, archived
REQUIREMENTS/ROADMAP, audits), `.planning/todos/`, `.planning/ROADMAP.md` backlog,
`.planning/research/`, `docs/prds/` (the 2026-09-07 batch), `docs/superpowers/specs|plans/` (the
pre-GSD designs, which is where several wishes were first written), the auto-memory notes, and
`git log`. Search scripts: `9-trace.sh`, `9-trace2.sh` (outputs `9-trace.out`, `9-trace2.out`).
Code claims were checked with codegraph and `rg`; file:line refs are to the current tree.

Verdict words: implemented, partly implemented, decided differently, deferred, lost (asked, never
carried into a decision or code), wrong claim (an artifact says done or decided, the code says
otherwise).

---

## 1. Model catalog from models.dev / Artificial Analysis / Arena, with tiers, class, cost, modalities, strengths, cache time

**Verdict: partly implemented.** The download and merge exist; the classification fields the owner
wants (tiers, tier shift with effort, agentic/lightweight/frontier class, video and image-edit
modalities, strengths) were never recorded in any planning artifact before 2026-11-02 and are not
in the code. The "class" idea alone was stated on 2026-08-29 and kept only in a memory note: lost.

Trail:
- First design, pre-GSD: `docs/superpowers/specs/2026-09-02-model-discovery-curation-design.md`.
  Goals: "enrichment of discovered models with reasoning/coding/agentic/intelligence indices,
  context window, pricing, and speed" and "A purpose axis (`review` / `execute` / `both`)".
  No tiers, no class, no strengths, no modalities beyond a passing "modalities" in the source list
  (line 72). Plan: `docs/superpowers/plans/2026-09-02-ai-kit-model-discovery-config.md`.
- Effort and the catalog: `docs/superpowers/specs/2026-09-05-model-catalog-effort-suffix-fallback-design.md`
  treats effort only as an id-matching problem ("models.dev lists a single bare `claude-opus-5`
  entry ... covering every effort level"), never as a tier shift.
- Image input added in v1.3 Phase 16, decision D-09: "`image_input: bool` is optional, sourced in
  order: (1) models.dev `modalities.input` ...; (2) `opencode models --verbose`"
  (`v1.3-phases/16-ai-kit-spec-extensions/16-CONTEXT.md:88-89`, `16-DISCUSSION-LOG.md:50`).
  Nothing about video, image editing or other strengths in that discussion.
- Model class: memory `ai_kit_spec_native_and_model_categorization.md` (2026-08-29): "Flagship /
  heavy-reasoning models ... best suited as reviewers. Tool-call / coding-agentic models ... best
  suited for coding/execution", and itself says "not yet fully encoded into ... Step 2.6
  `strength` field, which today only offers free-text". No phase or todo picked it up.
- Arena / ELO: zero hits anywhere in planning or docs before `NEXT-MILESTONE-INPUTS.md:472`. New.
- The owner's note "these wishes should have been recorded in the discussion log of the phase that
  built the catalog": the catalog was built outside GSD (a superpowers spec, 2026-09-02), so there
  was no discussion log to carry them; Phase 16 only extended it.

Code evidence:
- Sources: `skills/ai-kit-spec-review/ai_kit_spec/model_sources.py:13-14` (models.dev,
  Artificial Analysis), fetchers `:30`, `:41`.
- Fields: `model_catalog.py:26-50` — scores (intelligence, coding, agentic index), pricing,
  context window, tool calling, structured output, reasoning modes, speed tier, `image_input`,
  `name_declared_purpose` (review/execute). AA pricing at `catalog_build.py:210-212`; image input
  from models.dev at `catalog_build.py:81-93`; pi image input at `detection.py:474`.
- Cache time exists: `CATALOG_TTL_SECONDS = 30 days` (`model_catalog.py:11`).
- Not present: any tier, class, strengths, video or edit modality, Arena field. The superpowers
  adapter says it plainly: "The config has no capability-tier field (`strength` is free text, read
  by ...)" (`skills/ai-kit-spec-execute-superpowers/references/escalation.md:25`).

## 2. Lane TOML separating reviewers from executors with own priorities; effort per model; runtime/model escalation as opt-in flags

**Verdict: partly implemented (role marker, codex-only effort, quota ladder); separate priorities
never built; escalation flags decided differently in v1.3 and reversed by the owner on
2026-11-02; the unification itself is deferred in a pending todo.**

Trail:
- The role split was asked and designed on 2026-09-02: "both consumers share one
  undifferentiated ladder today ... correct for the ladder *mechanism* but wrong for *which
  entries* each consumer should prefer" (`2026-09-02-model-discovery-curation-design.md:29-33`),
  solved with a per-entry `purpose = "both" # "review" | "execute" | "both"` (line 178) and an
  explicit non-goal: "Changing `review-spec.toml`'s policy/ladder mechanics ... unchanged"
  (line 57). So one ladder with a filter was the decided shape; separate priorities per role were
  never designed.
- Escalation, first form: quota-driven ladder escalation in
  `docs/superpowers/specs/2026-08-28-ai-kit-spec-execute-design.md:113` and the superpowers
  rounds 4-5 "more capable model" rule.
- Escalation, v1.3 rule: "The cross-AI runner spawns one CLI per call and never switches harness,
  provider or model on its own (v1.3, Phases 25 and 25.1)" (`.planning/PROJECT.md:217`;
  `v1.3-ROADMAP.md:814,832`; `25-CONTEXT.md:299,318`). Phase 25 verification flagged the tension
  with pre-dispatch selection as an owner question (`25-VERIFICATION.md:89,196`).
- Deferred: todo `2026-10-29-unify-review-execute-lane-toml-effort-escalation-and-jev-classification.md`
  (effort detection per model, role passed by caller, runtime and model escalation as opt-in
  flags "off by default"), "Solution: TBD. Start with a spike". Backlog 999.15 (cross-AI chain
  skill) builds on it.
- Owner decision 2026-11-02 (`NEXT-MILESTONE-INPUTS.md`, Round 1): escalation flags opt-in, off by
  default, replacing the "never switch" rule as the default behaviour.

Code evidence:
- Role filter: `quota.py:103-118` (`_filter_ladder_by_purpose`, falls back to the full ladder when
  nothing matches, `:173-177`); `execute_selection.py:124-142` (purpose first for execute).
  spec-config asks `purpose` (`skills/ai-kit-spec-config/SKILL.md:302-358`).
- One ladder only: `config_io.py:18` (`DEFAULT_POLICY` with one `ladder`); known reviewer fields
  are five (`config_io.py:20`), the rest ride along as extras.
- Effort: only codex turns it into a runner flag (`runner_dispatch.py:207-211`); cursor carries it
  in the model id built at config time (`commands.py:80-90`); opencode and pi only via id suffix
  (`detection.py:84,90`).
- No escalation flag anywhere; the runner resolves one runtime per call and "A list is never
  walked" (`skills/ai-kit-spec-review/references/cross-ai.mjs:4442-4473`).

## 3. Provider/model discovery across copilot CLI, cursor-agent, pi, opencode, claude

**Verdict: implemented for pi, opencode, cursor, codex and claude; copilot is a runtime row with no
model listing (deferred by "unverified").**

Trail:
- One runtime table: 18.1 D-01 "One `RUNTIMES` mapping in `ai_kit_spec/detection.py` ... the
  model-list command" (`18.1-CONTEXT.md:20-25`).
- Claude ids from models.dev's anthropic provider: Phase 16 D-04 (`16-CONTEXT.md:59`).
- pi enumeration: Phase 18 plan 18-01 "pi RPC model enumeration" (`v1.3-ROADMAP.md:321`), Phase 22.
- copilot: "(Added 2026-10-24, owner.) The GitHub Copilot CLI is a runtime ... every row
  unverified until a real capture" (`v1.3-ROADMAP.md:890-892`); runner side in 25.1-07 commits
  (`d830892`, `e2b9352`). Curated-config refuses it as a runner
  (`skills/ai-kit-gsd-curated-config/SKILL.md:127`).

Code evidence: `detection.py:79-125` (pi RPC listing `:83`, opencode `models` `:89`, cursor `models`
`:97`, codex `debug models` `:106`, claude native selectors `:113`, copilot row with no
`list_argv` and the comment "no known host signal (unverified)" `:117-118`). Runner mirrors in
`cross-ai.mjs` `parsePiListingIds`/`parseOpencodeListingIds`/`parseCursorListingIds`/
`parseCodexListingIds`.

## 4. spec-review / spec-execute chaining into spec-config when no config exists

**Verdict: decided differently (2026-08-27 design): print a one-time hint and fall back to the
session default.**

Trail:
- `docs/superpowers/specs/2026-08-27-review-spec-cross-ai-design.md:386-390`: "Print one line
  ('No cross-AI config saved yet — run `review-spec-config` ...') and proceed with reviewer
  resolution as normal ... degrades gracefully to the current-session-only fallback". The hint
  fires only when `runtimes.json` was missing, to avoid "per-invocation nagging".
- spec-review's "never block the review" degrade path (`skills/ai-kit-spec-review/SKILL.md:151`).
- No later phase revisited it. First recorded as a wish on 2026-11-02 (`NEXT-MILESTONE-INPUTS.md`,
  Round 2).

Code evidence: hint text at `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:140`;
`NO_CONFIG_FALLBACK` session default at `quota.py:24-25,181,191`. spec-config's description
("or when ai-kit-spec-review warns no config exists") matches that hint, but the hint only fires on
a first run with no `runtimes.json`, so in practice it is rarely seen.

## 5. `ai-kit-opencode-providers` as a skill versus a shared helper

**Verdict: decided differently (as a skill) in the 2026-09-07 PRD and Phase 2 D-01; its helpers
were then copied, not shared.**

Trail:
- PRD `docs/prds/ai-kit-opencode-provider-management-v1.0-prd.md:141-144`: "New skill directory
  `skills/ai-kit-opencode-providers/` (SKILL.md + a small Python module ...)".
- Phase 2 D-01: "`ai-kit-opencode-providers` is a CLI module ... with a `SKILL.md` wrapper"
  (`v1.0-phases/02-opencode-provider-management/02-CONTEXT.md:23-26`); requirement
  `REQ-opencode-provider-list-remove` (`v1.2-REQUIREMENTS.md:31`).
- Reuse was planned: Phase 4 "Phase 2's ... surgical-edit module is a direct" reuse target
  (`v1.0-phases/04-config-doctor/04-CONTEXT.md:170`), and PROJECT.md:162 "Config Doctor reuses
  Opencode Provider Management's atomic-write/surgical-edit".
- No artifact before 2026-11-02 asks to remove the skill.

Code evidence: the "reuse" is copies with "Adapted from"/"Ported from" comments:
`tools/setup.py:1880`, `tools/config_doctor_appliers.py:26-28,146`,
`tools/config_doctor_readers.py:89,109,123`. The skill's own package:
`skills/ai-kit-opencode-providers/ai_kit_opencode_providers/`.

## 6. Curated-config: question cascade, open-gsd docs, jev agent tiers, gsd-tools writes, AGENTS.md, base branch, cross-AI confirmation

Most of these were first asked in v1.1 Phase 7 (2026-09-10) and then reshaped by the v2 design
(`docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md`, which "Supersedes Phase 07
decisions D-03 ..., D-07 ..., and the 'never more than one question' rule") and Phases 17-18.

**a. MVP / UI / granularity cascade — decided differently.**
Phase 7 had "never more than one question" (model_profile only); v2 replaced it with "four
questions" asked together (v2 design line 14). MVP exists as a rigor preset tied to coarse
granularity (v2 design line 159; `presets.py:35,55,73`). UI was never a question: Phase 7 D-08
"Frontend detection ... left as Claude's discretion ... no further user input needed"
(`07-CONTEXT.md:135`). Code: four questions in one message (`SKILL.md:90-96`); UI by heuristic
(`frontend_detect.py:3-22`).

**b. Fetch open-gsd docs — decided differently.**
The docs were read once at discussion time (Phase 7 canonical refs, `07-CONTEXT.md:202-205`), but
the skill was told to derive facts from the installed gsd-core: "derives tier/phase-type
classification from the INSTALLED gsd-core's own exported `AGENT_DEFAULT_TIERS`/
`AGENT_TO_PHASE_TYPE` at run time ... never ship a hardcoded snapshot" (Phase 7 D-03 amendment,
`07-CONTEXT.md` and `07-DISCUSSION-LOG.md` "Round 3"). No docs fetch was ever planned.

**c. jev classifying agent tiers — partly asked before, decided differently.**
Phase 7 amendment: the owner asked "for each agent to be reviewed individually against real data
... detect/discover the right classification from GSD's own components" (`07-DISCUSSION-LOG.md`,
Amendment, Round 2). Answered with gsd-core's own tier table, not jev (jev did not exist then).
Code: tiers from gsd-core's catalog (`roles.agent_tier`); jev in curated-config is only a
skill-wiring gate reading the old `JEV_API_URL`/`JEV_API_KEY` variables (`skill_scan.py:349-357`).

**d. Writing via gsd-tools instead of config.json — implemented.**
Phase 7 D-01 (write via `config-new-project`/`config-set`), kept by v2 ("D-01 ... stay", v2 design
line 6-7), requirement APP-03 (`v1.3-REQUIREMENTS.md:64`), plus `effort sync --apply` follow-up
(APP-04). Code: `apply.py:729,824`; Phase 7 verification "through `config-set` (D-01 confirmed — no
direct file write)" (`07-VERIFICATION.md:103`). Gap the owner now names (validate effort values,
run the target project's own gsd-tools) was not asked before.

**e. Prefer AGENTS.md for `claude_md_path` — implemented in v1, dropped as a write in v2.**
Phase 7 D-06: "prefers the AGENTS.md family for multi-CLI projects" (`07-CONTEXT.md:124-130`;
`07-DISCUSSION-LOG.md`: "user wants a detection helper inside the skill"). Code:
`claude_md_detect.py:9-15` (order AGENTS.md, CLAUDE.local.md, AGENTS.local.md, CLAUDE.md), v1
writer `cli.py:458-479`. v2 only reports a configured path whose file is missing
(`inventory.py:298-309`), which matches 17-SPEC.md:24 / 17-CONTEXT.md:371. No artifact records a
decision to stop writing it in v2; it fell out with the v2 key set. This repo's own config still
had `./CLAUDE.md` at Phase 17 time.

**f. Base-branch detection — never asked before.** No hit for base branch detection or
protected branches in any milestone artifact. New on 2026-11-02.

**g. Cross-AI execution needing confirmation — decided differently.**
Phase 7 put cross-AI execution on by default (D-03: "`workflow.cross_ai_execution: true` ... point
at a detected, preference-matched opencode/cursor model", `07-CONTEXT.md:89-93`). v2 made it a
question "recommended on Claude/Codex" (v2 design lines 198-205). Phase 18 D-39 (2026-10-15): "the
execution default follows SPEC R3/XAI-02 ... defaults to yes on claude and codex hosts"
(`18-CONTEXT.md:365`; requirement XAI-02, `v1.3-REQUIREMENTS.md:51`). Code: `cross_ai.py:151-156`.

**h. Related, and the most important drift: "never remove settings it did not plan".**
Phase 7 D-09: "Merge mode — the skill touches only the specific keys its curated
defaults/questions cover ... Everything else ... left exactly as found" (`07-CONTEXT.md:139-147`).
The v2 design says "D-09 (merge mode) ... stay" (line 7). But Phase 17 D-08, chosen by the owner in
discussion ("Authoritative, with a visible `op: unset` for stale entries ✓",
`17-DISCUSSION-LOG.md:50-53`; `17-CONTEXT.md:95-103`), made whole families authoritative. Code:
`presets.py:142-151` (`model_overrides.`, `dynamic_routing.`, `effort.agent_overrides.` ...) and
the leftover unset layer `recommend.py:1026,1150`. So the planner pin and `tier_models` get unset.
The owner's new wish reverses his own Phase 17 choice.

**i. Worktrees on (asked in Phase 7, lost).** See the lost list.

## 7. Spec-discuss interactive versus auto modes and flags

**Verdict: partly implemented; the two-mode split was the owner's own late addition, recorded only
in a skill-judge table; interactive discuss does not run `--analyze --all --batch`.**

Trail:
- Memory "Spec/discuss chain with jev": `/gsd-spec-phase N --auto` then
  `/gsd-discuss-phase --analyze --all --batch --assumptions N`.
- Phase 24 D-01: "The discuss step never passes `--assumptions`; the skill encodes the flags'
  intent"; D-03: "Spec runs with `--auto`; discuss runs without it" (`24-CONTEXT.md:19,31`).
  Context gathered in assumptions mode with jev screening, so these were agent decisions.
- Two modes: added at close-out, "ec6cc06 (+ owner `--auto` mode)" in the r1 row of
  `24-SKILL-JUDGE.md:65`, and "The r2 regression came from the new `--auto` mode" (`:69-71`). No
  CONTEXT decision records it.
- Leftover polish: backlog 999.11.

Code evidence: `skills/ai-kit-gsd-spec-discuss/SKILL.md` run-mode pick (lines ~78-85), auto path
uses the assumptions workflow with plain `N` (lines ~103-130), interactive path runs standard
discuss with no flags named (see `3-spec-discuss-and-jev.md` §1 for the line map).

## 8. jev-fast-decision in every skill that classifies, black-box, resilient when absent

**Verdict: partly implemented (the client exists and its two heavy users degrade without it);
"every skill" was never a phase scope; the black-box rule is recorded but the existing skills break
it.**

Trail:
- Todo 2026-10-11 (execute the System One plan) and 2026-10-14 (cross-host discovery scaffolding,
  owner intent: "Jev exists to absorb trivial-but-time-consuming structured judgments").
- Phase 21.1 D-01: "One shared client skill, `skills/jev-fast-decision/`"
  (`21.1-CONTEXT.md:23`); out of scope there: "Linking every other ai-kit skill"
  (`21.1-SPEC.md:131`).
- Black-box rule (owner): backlog 999.17, "ai-kit text says only: ask that skill, follow its own
  `SKILL.md`, the answer is advisory ... No text about how it picks local versus remote, consent,
  TypeSafe ..." (`.planning/ROADMAP.md:402-406`).
- Fallback order inside jev: backlog 999.9 (Laya, then TypeSafe, then Zen) — the owner now says Zen
  goes.
- Memory "jev at every decision point" covers autonomous runs, not skill prose.

Code evidence: only four skills mention jev (`jev-fast-decision`, `ai-kit-gsd-spec-discuss`,
`ai-kit-spec-goal-prompt`, `ai-kit-gsd-curated-config`). spec-review, spec-execute*, spec-config
and the rules family never call it. curated-config's backend check reads only `JEV_API_URL`/
`JEV_API_KEY` (`skill_scan.py:349-357`), against the black-box rule.

## 9. One shared cross-AI runner for open-gsd cross-AI and ai-kit's own review/execute

**Verdict: partly implemented. ai-kit review, ai-kit execute and open-gsd execution share one
runner; open-gsd's review lanes were explicitly left out.**

Trail:
- Phase 18.1 R7: "Which subprocess path ...? ... R7: one supervisor, the shipped runner; Python
  helpers deleted" (`18.1-SPEC.md:230`, `:159`). Out of scope: "GSD's own review lanes:
  unchanged" (`18.1-SPEC.md:143`).
- Phase 18 / XAI-02: open-gsd execute hook `workflow.cross_ai_command = node
  .planning/scripts/cross-ai.mjs` (`v1.3-REQUIREMENTS.md:51`; `18-VERIFICATION.md:144`).
- Phase 25 D-24: "GSD's `/gsd-review` and convergence lanes don't use `cross_ai_command`"
  (`25-CONTEXT.md:181`).
- Phase 25.1: one `--runtime/--model` producer contract for every caller
  (`25.1-VERIFICATION.md:120`: "`runner_flags`, curated `_runner_hook`, gsd
  `build_cross_ai_command`" all WIRED).

Code evidence: `runner_dispatch.py:200-216` (`runner_flags`), shipped template
`skills/ai-kit-spec-review/references/cross-ai.mjs` and the rendered per-project copy
`.planning/scripts/cross-ai.mjs` (same `RUNTIMES` table, `:1330` vs `:1349`). Three config sources
remain (the TOML, `.planning/config.json`, the runner's settings block), as `NEXT-MILESTONE-INPUTS`
notes.

---

## Lost or wrong claims (the ones that matter most)

Lost — asked, never carried into a decision or code:
1. **Worktrees on for GSD projects.** Phase 7 discussion notes: owner wanted "most on,
   intel+codegraph+worktrees on" (`07-DISCUSSION-LOG.md`, Write mechanism notes). D-07 turned this
   into "copy this project's config", which had no worktree key; plan 07-01 then scoped intel out
   as a "capability" (`07-01-PLAN.md:124-131`). v1 bundle has no `use_worktrees`
   (`workflow_defaults.py:19-46`); v2 never writes it. Intel came back only in v2's standard and
   rigorous presets (`presets.py:52,70,90`).
2. **Model class convention (flagship for review, coding-agentic for execution).** Stated
   2026-08-29, kept only in a memory note that says it is "not yet fully encoded". `strength` stays
   free text no code reads (`escalation.md:25`; no Python reads `strength`).
3. **Catalog classification wishes (tiers, tier shift by effort, class, strengths, video/edit
   modalities, Arena).** No planning artifact before 2026-11-02. The catalog was built in a
   superpowers spec outside GSD, so no discussion log existed to hold them. If the owner stated
   them in chat, they were lost at that point (the transcript agent can confirm).
4. **Owner's two-mode spec-discuss (`--auto`) decision.** Not lost from code, but recorded only in
   a skill-judge table row (`24-SKILL-JUDGE.md:65`), not as a CONTEXT decision; easy to miss.
5. **`claude_md_path` writing.** Asked in Phase 7 D-06 and built in v1; v2 silently stopped
   writing it with no recorded decision (only a missing-file note).

Wrong or contradicted claims:
1. **"D-09 (merge mode) ... stay"** (v2 design line 7) — contradicted by Phase 17 D-08 and the code,
   which unsets whole managed families (`presets.py:142-151`, `recommend.py:1150`). The owner chose
   that in Phase 17, but the design header still says merge mode holds.
2. **`strength` as a "schema-validated" TOML key** (`2026-09-02-model-discovery-curation-design.md:184-186`)
   — the code never validated or read it (`config_io.py:20` knows five fields; `git log -S strength`
   on `ai_kit_spec/` finds no code commit).
3. **`DYNAMIC_ROUTING_EFFECT = "unverified: no tier_models ..."`** (`presets.py:132-134`) — stale:
   the local gsd-core 1.18.0 accepts `dynamic_routing.tier_models.*` (probe in
   `2-curated-config-gap.md`).
4. **Opencode review effort verified, broken now.** Phase 7 D-03 and v1 write
   `review.effort.opencode = "high"` (`cli.py:402`), which open-gsd turns into `--variant`, rejected
   by opencode 2.x. Not a hallucination at the time; a verification that went stale after the
   opencode 1.x to 2.x move.
5. **curated-config's jev check** reads only the old `JEV_API_URL`/`JEV_API_KEY`
   (`skill_scan.py:349-357`), not the variables the jev skill documents now.

Not checked: chat transcripts (another agent), the full PRD batch beyond the providers PRD, and
plan-level SUMMARY files for every phase (only the decisions and verifications that the trail
pointed to).
