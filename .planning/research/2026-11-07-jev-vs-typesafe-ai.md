# jev-fast-decision vs the official typesafe-ai skill (2026-11-07)

The owner's question: how does ai-kit's `jev-fast-decision` differ from the official
`typesafe:typesafe-ai` skill, how does ours bring the official skill into its workflow, and how
should ours check the running Laya's version and features before a call?

Short answer: the two skills do different jobs. The official skill teaches an agent to **build
TypeSafe into application code**. Its current upstream release goes further and calls an agent
asking Jev "What should the agent do next?" "the wrong layer". Ours is an **agent-side advisory
judge** with a local-first backend ladder and consent. Ours only links to four doc pages. It
never invokes or names the official skill except in one routing clause, so it has no doc flow
for learning new features. The running Laya exposes no version number over HTTP, it is 25 patch
releases behind upstream, and it serves a batch route our client does not use.

## 1. What each skill is for

**Ours: `jev-fast-decision`** (`skills/jev-fast-decision/`, files last changed 2026-11-06; no
version field). It gives an agent fast typed advisory judgments (noul, choice, score, and an
evidence-screen shorthand) through one stdlib client, `scripts/jev_review.py`. The client tries
backends in a fixed order: local Laya first, then TypeSafe, then OpenCode Zen. A remote backend
needs the user's consent first. Callers include other ai-kit skills (GSD spec-discuss, commit-fold,
goal-prompt) and a SessionStart hook. Every answer is advisory. Each answer carries a
`needs_fallback` flag, and when it is set the agent decides that item itself.

**Official: `typesafe:typesafe-ai`** (plugin `typesafe@typesafe-ai`, from the `typesafe-ai/skills`
repo, MIT). Installed: version **0.5.7** (`plugin.json`, release commit 65a39f3, 2026-09-12),
installed 2026-10-09. Upstream: **0.6.2** (raw `plugin.json` on main, fetched 2026-11-07). The
skill guides an agent through building, reviewing and debugging code that calls System One: read
the live docs (starting at `llms.txt`), choose a primitive, design the state and the questions,
compose requests, read the answers, then test against the live API with the user's permission and
a budget. It has no backend code, no Laya and no consent mechanism.

**Two installed copies.** The plugin copies (cache and marketplace) and the skills.sh copy
(`~/.claude/skills/typesafe-ai` → `~/.agents/skills/typesafe-ai`, lock entry
`~/.agents/.skill-lock.json:22-30`, source `typesafe-ai/skills`) have the same sha256
(`71ea90d7…`). Both are 0.5.7, so neither is newer, and the session shows both `typesafe-ai` and
`typesafe:typesafe-ai`. The official install page asks for one install method only, to avoid
duplicates (docs.typesafe.ai/agent-skill.md, fetched 2026-11-07).

## 2. Where they converge

- **The same three text primitives.** choice, noul and score, with the same request fields
  (`instructions`, `criteria`, `state`) and the same answer fields (reference.md:13-18 and 38-42;
  official SKILL.md:97-103; docs.typesafe.ai/primitives.md).
- **Confidence is not a gate.** Ours says "`confidence` is **not calibrated**" and gates on `top`,
  the winning probability (reference.md:48-49; `top_of`, jev_review.py:538-542). The official skill
  says confidence "is not the same as how likely the answer is to be correct" (upstream 0.6.2), and
  docs.typesafe.ai/confidence.md says to threshold the probability of the chosen option.
- **The noul threshold is the same.** Ours flags fallback when `max(p, 1-p) < 0.7`
  (jev_review.py:540-541, Laya `min_confidence` 0.7 at :905). That is the docs' starting band
  "0.7 for yes and 0.3 for no" (confidence.md).
- **Self-contained state.** Ours says "the model sees only what is in `state`" (reference.md:20).
  The official skill says "Question IDs ... are not sent to the model" (SKILL.md:108).
- **Ask before a live call.** Ours asks consent before any off-machine send (SKILL.md:44-46). The
  official skill's test step says "Ask the user for permission first" and to get a budget (0.6.2).

## 3. What ours adds (checked in code)

- **A backend ladder.** `TABLE` holds laya (local, loopback only), typesafe and opencode
  (jev_review.py:899-983). Remote rows are probed only after their consent gate
  (`_row_probe`, :1223-1241). `JEV_BACKEND` forces one row and never falls back (SKILL.md:20).
- **Consent records.** `consent grant|revoke|show`, bound to the backend's host
  (reference.md:73-75; `record_consent`, jev_review.py:1123). The client never asks for consent
  itself; the agent asks the user (SKILL.md:44-46).
- **A capability matrix with sourced cells.** Every backend × feature cell is labelled
  verified-live, documented, unsupported or unverified, with its source and date
  (jev_review.py:918-981, reference.md:117-130). An item no row supports gets
  `unsupported_feature` (`_row_supports`, :1030-1037).
- **Batching rules backed by measurement.** Laya gets one item per call, because one item's
  context bled into another's answer (0.46 → 0.86, measured 2026-10-10; backends/laya.md:18-24).
  TypeSafe gets one batched request (backends/typesafe.md:28-30).
- **Size guards and forced flags.** Laya rejects a state over 2000 characters before sending it,
  and an answer that hit truncation is marked `forced` and gets `needs_fallback`
  (jev_review.py:912, reference.md:44).
- **Receipts and an answer log.** Each result carries `request_sha256` and the model that
  answered, and every item is logged to a JSONL answer log without its context
  (reference.md:65-71).
- **Wiring for callers.** The `ladder`, `detect` and `--second-opinion` entry points
  (jev_ladder.py:1-16), an installed-skill lookup across six skills roots (reference.md:139-150),
  the `GSD_PATH_JEV` kill switch (reference.md:81), and the SessionStart probe hook
  (tools/hooks/claude_decision_probe.py:2).
- **Key handling.** A fixed order of key sources, 0600 permissions enforced on key files, and no
  key value is ever printed (reference.md:91; tests at test_jev_fast_decision.py:1278).

## 4. What ours lacks compared with the official skill

- **No doc flow.** Ours has four fixed "Required reading" links (SKILL.md:60-65). It has no
  `llms.txt` index, changelog, models page, cookbooks, patterns or fallback rule for when the docs
  are unreachable. The official skill covers all of these (SKILL.md:26-53).
- **Some recorded facts are stale.**
  - reference.md:114 and backends/typesafe.md:12-13 still say `jev-latest` "moves ... about a week
    after release". It has moved: models.md now lists `jev-latest` → `jev-1.14.0`, and our own
    answer log shows 9,133 TypeSafe answers from model `jev-1.14.0` (live count, 2026-11-07).
  - The TypeSafe score cell is still only `documented`, from 2026-10-18 (jev_review.py:948). No
    live run is recorded for it, although TypeSafe has answered 9,000+ items since then.
- **No builders for newer features.** `BUILT_FEATURES` is `{choice, noul, score}`
  (jev_review.py:86), so Box, images and long context return `unsupported_feature`
  (reference.md:112-113). Box needs `TypeSafe-Danger-Zone-Images: true` and Jev 1.14
  (images.md, models.md). This work is already planned as JEV-05 in Phase 54.
- **No question-design guidance.** The official skill teaches "one narrow, coherent judgment per
  question", "include a no-match outcome", score levels that describe concrete situations, and
  "a separate presence judgment" (SKILL.md:112-121). Ours covers only the request shape and the
  self-contained state rule.
- **No patterns or cookbooks.** Noul-screen-first, companion noul, routing by confidence,
  self-consistency and composite scoring (llms.txt) are not linked. Some apply directly to
  agent-side judging: noul-screen, self-consistency and confidence routing.
- **No update path.** Nothing in ours notices a new Jev release, a new primitive, or a new Laya
  release.

## 5. How ours includes the official skill today

- **One routing clause:** the description ends "Not for building TypeSafe into an app
  (typesafe-ai) or for editing code." (SKILL.md:3). It only tells the agent to use the other skill
  for app building.
- **Four links:** SKILL.md:60-65 links the Jev 1.14 notes, primitives, images and confidence
  pages. test_jev_fast_decision.py:2339-2342 pins these four URLs.
- **Nothing else:** grep of the repo's .md/.py/.sh/.json/.toml files finds `typesafe-ai` only in
  this SKILL.md and in archived planning files. The installer never installs it, no script calls
  it, and no doctor checks for it.

So the official skill is **referenced by name for routing only, never invoked, and never relied
on**. The four links point at doc pages, not at the official skill.

**On the premise "the official skill for jev".** Upstream 0.6.2 says that a question such as
"What should the agent do next?" "usually means the question is at the wrong layer", and that the
decision itself should be written in code. docs.typesafe.ai/introduction/coding-agents.md says Jev
is "not a drop-in replacement" for a coding agent's LLM. Our use, advisory judgments for an
agent's gray areas with `needs_fallback` and the agent deciding, sits outside the official
skill's stated purpose. The official skill is still the authority on **docs, primitives,
question design and new features**. That is exactly the part ours lacks, so it should be used as
a **reference**, not as the flow ours runs.

## 6. Laya version and feature discovery

### What the running Laya exposes (live probe, 2026-11-07 11:15 UTC, read-only GETs, 3 s timeout, no auth)

- `GET /health` → 200:
  `{"status":"ok","loaded":["multilingual"],"revisions":{"multilingual":"55cf4c4e…"},"device":"cuda",
  "idle_unload_seconds":600.0,…}`. This gives the loaded checkpoints and their Hub revisions.
  **No version field.**
- `GET /openapi.json` → 200: `info` = `{"title":"laya-serve","version":"0.1.0"}`. This is the
  serve app's version, not the package version. The paths are `/health` (GET), `/v1/systemone`
  (POST) and **`/v1/systemone/batch` (POST)**. The server header is `uvicorn`, and no header
  carries a version.
- `/`, `/version`, `/v1/models`, `/models`, `/info`, `/metrics` and `/v1/systemone/models` →
  404. `/docs` → 200 (Swagger UI).
- **Package version:** `podman exec system-one pip show laya` gives `Version: 0.4.2`. This is
  container-specific and not reachable from the client. It matches `ARG LAYA_VERSION=0.4.2` in
  llm-env `docker/system-one/Dockerfile:8`.
- **Upstream version:** PyPI `laya` is **0.4.27**, released 2026-11-06. There were eight releases
  between 2026-11-01 and 2026-11-06. Its README describes vega (images, audio, video, documents of
  up to 73k tokens, conformal sets, an abstain flag), `predict_long`, and "`predictBatch` sends
  independent states with one question set to `/v1/systemone/batch`" (PyPI JSON, fetched
  2026-11-07). Whether laya-serve 0.4.27 exposes vega over HTTP is **unverified**.
- **Answering model:** the answer log shows Laya answering as `laya-rl-agent` (4,546 items).
  The response model carries no version either.
- **The batch route** collates "states × questions" into one forward pass (installed `serve.py`
  in the container, lines 8 and 90). Each state is judged separately against one shared question
  set. **Inferred, not live-tested:** this avoids the measured context bleed between items, but
  only when items share the same instructions and criteria (for example, many evidence
  shorthands against one criterion).
- **Observation:** only `multilingual` is loaded right now. backends/laya.md:33 and the
  2000-character guard (jev_review.py:910-912) assume the English 512-token window. llm-env's
  architecture notes say non-English input goes to `multilingual` (1024 tokens).

### What ours does now before a call

`--probe` (and every ladder run) sends `GET /health` and checks only for HTTP 200
(`_laya_probe`/`_get_probe`, jev_review.py:593-624). The body is discarded. A test pins exactly
one `GET /health` and no POST (test_jev_fast_decision.py:481-487). The Laya cells cite "laya 0.4.2
server source", dated 2026-10-18 (jev_review.py:921-927). Nothing compares them with what is
actually running.

### Proposal (small, no new dependency, not on the per-call path)

1. **Read what the probe already fetches.** At `--probe`/`detect`, parse the `/health` body for
   `loaded` and `revisions` and report them in the Laya row.
2. **Add one more loopback GET, cached.** Fetch `GET /openapi.json` and keep `info.version` and the
   path list in `${XDG_STATE_HOME:-~/.local/state}/ai-kit/jev-laya-features.json` with `checked_at`.
   Re-fetch when the cache is over 24 h old, or when `/health`'s `revisions` changed (a free
   change detector, because the health check runs anyway).
3. **Compare against a recorded known-features list.** A small constant beside `TABLE` would hold
   the known Laya routes, the serve version and the response-model pattern. When the live list
   differs (a new route such as an asset or box path, a new serve version, a new checkpoint), the
   probe prints a `laya_drift` note naming the difference and the dated cell to re-verify. A cell
   never changes to verified-live on its own (AGENTS.md certainty rule).
4. **Package version.** The client cannot learn it over HTTP. Label it `unknown (not exposed)`.
   llm-env (owner's repo) already wraps the server with `phoenix_observer.py` (Dockerfile CMD), so
   it could add the package version to `/health` or a response header. That is an llm-env change
   to file there, not ai-kit code.
5. **Learning of new TypeSafe, Jev and Laya features: an on-demand `jev_review.py --check-updates`**
   with a 7-day cache. It never runs on the per-call path, and it sends only public GETs with no
   key and no question. Following the official skill's flow, it fetches `docs.typesafe.ai/llms.txt`,
   `changelog.md` and `models.md`, plus PyPI's `laya` JSON. It reports entries newer than
   reference.md's "as of" dates, model ids missing from the recorded list, and the gap between the
   running and the latest Laya. The `model` field each TypeSafe answer already logs
   (`jev-1.14.0`) is a free signal of an alias move: the check can compare it with the recorded
   id. A maintainer then reads the official skill and the changed pages and updates the cells and
   reference.md by hand.

## 7. Recommendations

**Should ai-kit require or install the official skill?** **No, ai-kit should not install it.**
Installing third-party skills belongs to tools-installer (memory "ai-kit scope vs
tools-installer"; it already installs it via skills.sh). Do this instead:
- **Delegate in our SKILL.md (Phase 32.1, with the JEV-02 re-judge).** Replace "Required reading"
  with one line: to learn current TypeSafe features or design a new item shape, follow the
  `typesafe-ai` skill's live-docs flow; without it, start at `https://docs.typesafe.ai/llms.txt`,
  then `changelog.md` and `models.md`. Keep the four links in reference.md and update the pinned
  test at test_jev_fast_decision.py:2339. Keep the routing clause in the description.
- **Correct the stale facts (Phase 32.1).** `jev-latest` = `jev-1.14.0` (models.md and the answer
  log). Move the TypeSafe score cell to verified-live only after a recorded live run. Drop the Zen
  column and the Zen wording (JEV-02).
- **Borrow the question-design rules ours lacks (Phase 32.1).** Three lines in reference.md: one
  narrow judgment per item, a no-match option, and concrete score levels. Link the noul-screen and
  self-consistency patterns. The judge loop must still pass.
- **For tools-installer, outside ai-kit:** keep one install method (the plugin or skills.sh, not
  both) and update 0.5.7 → 0.6.2. Record this in tools-installer's backlog.

**Changes to ours, by phase:**
- **Phase 34 (JEV-01, JEV-03, JEV-07):** steps 1-4 of the Laya proposal. Upgrade Laya (llm-env)
  or record the reason to stay on 0.4.2 **before** the JEV-03 calibration, and write the Laya
  version and checkpoint revision into the calibration results, so the floor is tied to a known
  server. Run a spike on `/v1/systemone/batch` for same-question screens, measuring the bleed
  against one call per item. Re-check the 2000-character guard against the checkpoint actually
  loaded.
- **Phase 34, or a small new requirement:** the `--check-updates` subcommand from step 5.
- **Phase 54 (JEV-05):** the Box and image builders. Its "Laya cell re-checked" criterion should
  name laya 0.4.27's vega image path as the thing to check.

**Proposed new requirement wording** (no existing one covers these; JEV-01 covers backend choice
and key handling only):
- *jev's probe reports the running Laya's serve version, loaded checkpoints with their revisions,
  and the routes it serves, from a cache refreshed daily or when a revision changes. It names any
  route, version or checkpoint that the recorded known-features list does not contain, without
  changing any capability cell's status, and labels the package version as not exposed when Laya
  does not report it.* → Phase 34.
- *jev-fast-decision points to the official typesafe-ai skill's live-docs flow for learning new
  TypeSafe features. An on-demand update check, never on the per-call path and sending no key or
  question, compares the docs' changelog and models page, the model ids in recent answers, and the
  latest Laya release with the dated facts the skill records, and lists each difference to
  re-verify.* → the pointer in Phase 32.1, the check in Phase 34.

## 8. Skill stack design (owner follow-up)

The owner asked: should ours adopt more of what TypeSafe now defines; is there an official Laya
skill to chain, with jev called only on low confidence; and how should our skill be used where it
is strongest, as a stack of skills rather than new programs?

### Is there an official Laya skill, plugin or MCP server?

- **Who publishes Laya:** Convai Innovations (PyPI author), repo `NandhaKishorM/laya` (a personal
  account), Apache-2.0. Its relation to TypeSafe is **protocol compatibility only**. `laya.serve`
  speaks "the same `POST /v1/systemone` wire protocol as TypeSafe's hosted Jev API", and the README
  says its Jev figures are "third-party published ... (no TypeSafe API access)". Nothing claims an
  affiliation (PyPI README and GitHub page, fetched 2026-11-07). Laya is an independent System One
  implementation, not a TypeSafe model.
- **No official Laya agent skill was found.** The repo's top level shows `AGENTS.md` (contributor
  guidance) but no `skills/`, `SKILL.md`, `.claude-plugin` or `llms.txt`. The GitHub listing was
  truncated, so this is **not fully verified**. No installed plugin mentions Laya
  (`installed_plugins.json`, `known_marketplaces.json`). The skills.sh search page did not render
  its results, so that check is **unverified**.
- **An official Laya MCP server does exist:** the `laya[mcp]` extra, a stdio server. The installed
  0.4.2 has eight tools: `laya_status`, `laya_route`, `laya_predict`, `laya_predict_batch`,
  `laya_route_batch`, `laya_shortlist`, `laya_preset`, `laya_decide` (grep of the container's
  `laya/mcp/`). The upstream README also lists `laya_predict_long` and `laya_tournament`.
  `laya_status` reports package versions for the MCP process itself, so it does not report a remote
  server's version (`laya/mcp/tools.py:919-933`). This session has no Laya MCP server registered.
- **One community skill:** `F0Rextasy/omp-laya-judge` (MIT, 12 stars), an oh-my-pi plugin with an
  MCP server and a `laya-judge` skill. It accepts an answer when Laya's `answer_confidence` is at
  least 0.6 and otherwise escalates to the LLM. The Laya README lists it as a community tool.
  It is unofficial, oh-my-pi only, and useful as prior art only.

### Does our ladder already do "Laya first, TypeSafe only on low confidence"?

Yes, with four nuances (`_ladder`/`_fold_rung`, jev_review.py:1838-1890; `_result`, :1805-1835).
- Auto mode tries Laya first, one item per call. A confident answer (`top` ≥ 0.7, not forced) is
  final. A low or forced answer is kept as provisional and goes on to the next usable rung: one
  TypeSafe batch at threshold 0.8.
- A remote answer is final even when it is low; its `needs_fallback` then tells the agent to decide.
- **Nuance 1: Laya errors also escalate.** 5xx, network errors and a 503 after its retries go to
  TypeSafe. A Laya 400/413/422 is final. Items Laya cannot run (no matching capability cell) go
  straight to the remote rows.
- **Nuance 2: TypeSafe runs only with consent and a key.** Without consent, the low Laya answer
  comes back with `needs_fallback` and `remote_available`, so the agent asks the user and re-runs.
- **Nuance 3: a confident Laya answer is never checked.** Only `--second-opinion` sends an item to
  TypeSafe while skipping Laya (reference.md:156-158), and spec-discuss's decision table chooses
  when to use it.
- **Nuance 4: our own evidence weakens "trust Laya when confident".** The 32-case live eval measured
  `accuracy_when_not_fallback` 0.5 and found no qualifying threshold (backends/laya.md:54-64). The
  local-first ladder is right for cost and privacy, but a confident Laya answer has not been shown
  to be more accurate than a coin flip on our kind of question. That fact belongs in the skill
  text and in the Phase 34 calibration.

### TypeSafe concepts our skill does not yet reflect, and who they matter to

These matter for an agent's own decisions, so ours should adopt them as skill text:
- **Jev judges, the agent decides.** Write items as observable judgments ("does this option change
  the public API?"), not "what should we do?". This is the official skill's main rule, and it
  matches our advisory stance.
- **Documented weak spots** (docs.typesafe.ai/model-jaggedness.md):
  - Never ask about arithmetic, counting, dates or durations, or with double negatives.
  - Choice "leans toward the option that comes first", so for a close choice, ask again with the
    options reordered (the self-consistency cookbooks).
  - Accuracy drops when state holds irrelevant detail.
- **A no-match option** in a choice, and noul criteria that define both yes and no (official skill,
  "Criteria").
- **Noul-screen first:** one cheap noul before an expensive step, with an explicit middle band
  (patterns/noul-screen.md). It fits an agent deciding whether a gray area needs a full analysis.
- **Several questions over one shared state.** On TypeSafe, one gray area can carry a screen noul
  plus a choice in one request (primitives.md: questions are independent and see the same state).
  Our TypeSafe batch instead merges every item's context into one state, which the "no irrelevant
  detail" guidance warns against. This is **inferred, not measured** on TypeSafe.
- **Versioned model ids in receipts.** Answers already name `jev-1.14.0`, so receipts should record
  that id rather than the alias.

These matter mostly for app code or for later phases, and the official skill keeps them:
- SDKs, pricing, the long-context header (we send summaries under a size guard), composite scoring
  and data-sharing opt-in.
- Box and images are agent-useful only for a screen-against-mockup check, which is already JEV-05
  in Phase 54.

### Division of labour, and how the skills chain without code

- **The official `typesafe-ai` skill (TypeSafe, installed by tools-installer) owns:** the docs flow,
  the primitives, question authoring, new features, and building TypeSafe into apps.
  Ours points to it with "read X when Y" lines and never calls it.
- **Laya's upstream docs and its MCP server own:** Laya's own features, versions and checkpoints.
  No official Laya skill exists to delegate to. Do **not** put the Laya MCP server into the
  decision path. A second entry point to the same server would skip our per-item rule, size guard,
  thresholds, receipts and answer log, and the two paths would drift apart. Its registration is
  host config, owned by llm-env or tools-installer; at most it is an operator tool for diagnostics.
- **Ours (`jev-fast-decision`) owns:** the agent-decision ladder (Laya → consented TypeSafe →
  the agent), consent, one item per call on Laya, size guards, the capability table, receipts, the
  answer log, the item templates for agent questions, and GSD wiring.
- **Caller skills** (spec-discuss, commit-fold, goal-prompt) keep treating jev as a black box:
  "ask jev-fast-decision and follow its SKILL.md" (JEV-06, done).
- **Run-time chaining is text only.** Our SKILL.md says:
  - when designing a new item shape, or when a capability fact looks stale, read `typesafe-ai`
    (or start at `llms.txt` when it is not installed);
  - when the probe reports a Laya version or route change, read Laya's upstream "What's new";
  - for any decision that matters, `needs_fallback` or no answer means the agent decides.
- **Scope:** ai-kit never installs either third-party artifact. tools-installer owns installing
  `typesafe-ai` (once, updated to 0.6.2), and llm-env owns the Laya server and any MCP
  registration.

### Concrete changes, by phase

- **Phase 32.1 (with JEV-02):**
  - Add to SKILL.md a three-line "Read X when Y" block for `typesafe-ai`, Laya upstream and the
    agent-decides rule. It replaces the four links in "Required reading"; the pinned test moves.
  - Add to reference.md a short "Writing an item" section: the observable-judgment rule, the weak
    spots not to ask about, the no-match option, the reordered re-ask for close choices, and the
    noul-screen pattern.
  - Refresh the Jev 1.14 facts and drop Zen.
- **Phase 34 (JEV-01, JEV-03, JEV-07):**
  - State nuance 4 in backends/laya.md and in SKILL.md's result recipe.
  - Extend the calibration so it records confident-answer accuracy with the Laya version and
    checkpoint.
  - Add the Laya version and route drift check (§6).
  - Run a spike comparing one shared state per gray area against merged contexts on TypeSafe.
  - Record the Laya MCP server as not on the decision path.
- **Proposed requirement wording** (nothing covers these):
  - *jev-fast-decision's skill text says when to read the official typesafe-ai skill (a new item
    shape, a new TypeSafe feature, a stale capability fact) and when to read Laya's upstream docs
    (a Laya version or route change). Its reference lists the documented Jev weak spots an agent
    must not ask about, and the reordered re-ask for close choice answers. No program calls either
    skill.* → Phase 32.1.
  - *The Laya calibration records how accurate confident Laya answers are on labelled agent-style
    cases, tied to the Laya version and checkpoint. While that accuracy stays under the floor, the
    skill text treats Laya answers as screens only, which escalate or leave the item to the agent,
    never a final answer.* → Phase 34, as an amendment to JEV-03.

## 9. Evidence

- Ours: `skills/jev-fast-decision/SKILL.md:3,12-20,44-54,60-67`;
  `reference.md:13-20,38-49,65-75,81-95,100-130,139-150`; `backends/laya.md:9-16,18-24,33-37`;
  `backends/typesafe.md:12-17,28-34`; `scripts/jev_review.py:59,76-86,538-542,593-624,899-983,
  1030-1037,1223-1241,1316-1340`; `scripts/jev_ladder.py:1-16`;
  `tests/test_jev_fast_decision.py:481-487,2339-2342`; `tools/hooks/claude_decision_probe.py:2`.
- Official, local: `~/.claude/plugins/cache/typesafe-ai/typesafe/0.5.7/skills/typesafe-ai/SKILL.md`
  (lines 26-53, 97-121) and `.claude-plugin/plugin.json` (0.5.7); marketplace git log
  `65a39f3 2026-09-12 Release v0.5.7`; `~/.agents/skills/typesafe-ai/SKILL.md`, the same sha256;
  `~/.agents/.skill-lock.json:22-30`.
- Official, upstream (fetched 2026-11-07): raw `typesafe-ai/skills` main `plugin.json` (0.6.2) and
  `SKILL.md` (the "wrong layer" and "Ask the user for permission first" sentences quoted above).
- Docs (fetched 2026-11-07): docs.typesafe.ai `llms.txt`, `changelog.md` (Jev 1.14, 2026-10-14,
  nothing newer listed), `models.md` (`jev-latest`/`jev-preview` → `jev-1.14.0`; 64k/32k, 262k with
  the header; Box 1.14 only), `primitives.md`, `confidence.md`, `images.md`, `agent-skill.md`,
  `introduction/coding-agents.md`; typesafe.ai/blog/jev-1-14 (2026-10-14).
- Laya, live (2026-11-07): `tmp/laya_probe.py` and `tmp/laya_openapi.py` output quoted in §6;
  `podman exec system-one pip show laya` → 0.4.2; grep of the container's `laya/serve.py` (batch
  route, lines 8, 90, 1229); PyPI `laya` JSON (`tmp/pypi_laya.py`) → 0.4.27.
- llm-env: `docker/system-one/Dockerfile:8,17,31`; `.agents/architecture.md:107-123`;
  `docker/system-one/phoenix_observer.py:54-93` (batch `states`/`results`).
- Answer log counts by (backend, model), no question text printed (`tmp/answer_log_models.py`):
  typesafe/jev-1.14.0 9,133; laya/laya-rl-agent 4,546; typesafe/null 216.
- Skill stack (§8, fetched or read 2026-11-07): PyPI `laya` README (`tmp/pypi_laya_grep2.py`:
  author, the MCP extra, TypeSafe wording, community tools); github.com/NandhaKishorM/laya top
  level; github.com/F0Rextasy/omp-laya-judge; container `laya/mcp/server.py:235-241` and
  `laya/mcp/tools.py:919-933`; docs.typesafe.ai `model-jaggedness.md` and
  `patterns/noul-screen.md`; jev_review.py:1805-1890; backends/laya.md:54-64;
  `skills/ai-kit-gsd-spec-discuss/SKILL.md:54-56,191-206,255`.
- **Inferred or unverified:** that no official Laya skill exists (truncated repo listing, and the
  skills.sh search did not render); whether a shared state beats merged contexts on TypeSafe; the
  batch route avoiding cross-item bleed (from code, not measured);
  laya-serve 0.4.27 exposing vega over HTTP; the official skill's full upstream text (read through
  a summarizing fetch, short quotes only); whether TypeSafe answers score items live (the
  cell is `documented`; the answer log's item types were not counted).
