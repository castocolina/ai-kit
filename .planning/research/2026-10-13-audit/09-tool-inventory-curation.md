# 09 — Tool-inventory cache with per-subagent curation, and fit of `jev-fast-decision`

Date: 2026-10-13. Review tree: `review-v13` (0acbd06, `gsd/v1.3-curated-config-v2`). Paths below that start with `skills/` or `.planning/` are relative to that tree unless marked `main:`.

Confidence labels: **[V]** verified by reading code, files or command output; **[D]** verified from vendor docs (URL given); **[I]** inference.

## TL;DR

1. **Most of the plumbing already exists. Extend it; don't build a new cache.**
   - Every dispatch already gets a confirmed-only guidance block (`SHARED_TOOLING_PATH`, `TOOL_AVAILABILITY`, a codegraph line) built by `build_tooling_guidance` (`skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py:23-57`). It reaches the review template (`skills/ai-kit-spec-review/SKILL.md:312-333`), execute-gsd `prepare-tooling` (`skills/ai-kit-spec-execute-gsd/SKILL.md:213-220`) and the superpowers dispatch (`skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:283-285`). **[V]**
   - The review skill already hands cross-AI reviewers a skill *by absolute path* (`CHECKLIST_SKILL_MD`, `skills/ai-kit-spec-review/SKILL.md:166,247`). **[V]** That is the curation pattern we need: one named variable for the skills a subagent should use, emitted only for skills confirmed present.
2. **A persistent inventory cache is not worth it for speed.** A full scan of every host skill and agent dir plus the active Claude plugins finds 347 entries and parses their frontmatter in 5.6–19.4 ms. A stat-only digest takes 2.9–3.1 ms (measured below). **[V]** Rescan on every run. Persist only what is expensive or user-confirmed: role mappings for unknown skills.
3. **The token win is smaller than it looks. The real win is that the right skill shows up at all.**
   - Every host already uses progressive disclosure: only names and descriptions load up front. Claude caps the listing at 1% of the context window and drops the least-used descriptions first. Codex caps it at 2% or 8,000 chars. **[D]**
   - On this machine the Claude-visible skill descriptions total ~50k chars (46,101 for `~/.claude/skills` plus 4,374 for plugins). **[V]** So the listing is budget-truncated on smaller-context models, and a subagent sees names without descriptions. **[I]**
   - Preloading or pointing at 1–3 skills by name and path fixes that. Hiding the other ~190 saves at most the listing budget. **[I]**
4. **MCP overload is a non-issue here today.**
   - Each host has 1–2 MCP servers, by name: `codegraph` on claude/cursor/codex, plus `gsd` on opencode; pi has no MCP at all. **[V]**
   - Claude Code already defers MCP tools behind tool search; this very session shows them as deferred. **[V]**
   - Skip per-subagent MCP curation in v1. Keep the existing per-dispatch codegraph health check.
5. **`jev-fast-decision` is not a good fit for per-dispatch routing.** It is a decent *optional* fit for one config-time job: classifying unknown installed skills into a fixed list of role buckets, memoized by description hash and always confirmed by the user (Phase 18 already requires that confirmation).
   - The skill's own rules forbid letting an answer "select a route" on its own (`~/.claude/skills/jev-fast-decision/SKILL.md:41-43`). **[V]**
   - The live script is still v1 (Zen only). The three-backend Plan B with `--probe` has not been executed (`main:.planning/todos/pending/2026-10-11-execute-system-one-decision-skill-plan.md`). **[V]**
6. **Phase mapping.**
   - Put the shared skill scan in `ai_kit_spec` (a small amendment to Phase 18 SKL-01: location only, behaviour unchanged).
   - Make `skill_affinity.json` role-keyed so the execute adapters can reuse it.
   - Add one small new phase after Phase 18, "skill hints in dispatch guidance", which also absorbs the cross-host half of 999.4 (ponytail).

---

## 1. What the repo already has (do not redesign)

### 1.1 `ai_kit_spec` caches and detection [V]
- `cache_base` resolves to `$XDG_CACHE_HOME|~/.cache` + `ai-kit/spec` (`ai_kit_spec/cache.py:7-10`).
- Writes are atomic: tmp file plus `os.replace` (`cache.py:21-29`).
- Staleness is mtime-based TTL (`cache.py:32-36`).
- Existing cache files: `runtimes.json` (`detection.py:36`, 30-day TTL, `schema_version` 2 at `detection.py:11-15`), `model-catalog.json` (`model_catalog.py:56`) and the quota cache (`quota.py:28`).
- `detect_tool_availability` is a `which` check for `rg, sd, bat, eza, fd, codegraph` (`detection.py:460-466`).
- MCP: `check_codegraph_mcp_healthy` runs `claude|codex mcp get codegraph`, falling back to `mcp list` (`detection.py:512-570`).
  - It checks health on every dispatch, on purpose: a registered server can be disconnected from one moment to the next (`detection.py:501-510`).
  - **So never cache MCP health. Registration (names) is cacheable; health is not.**
- `reviewer_dispatch.dispatch_reviewer` resolves codegraph health itself and prepends the guidance block before rendering the command (`reviewer_dispatch.py:57-68`).

### 1.2 v1.3 design and Phase 17/18 (planned, not built) [V]
- Spec §3: `inventory` emits `skills [{name, form, source, description}]` (`docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md:79-83`). The modules `skills.py` and `skill_affinity.json` live inside `ai_kit_gsd_curated_config/` (`:104`).
- Spec §7 covers:
  - the skill dirs to scan, with plugin skills addressable on Claude only (`:211-212`);
  - affinity families mapped to GSD agents (`:213-222`);
  - unknown skills proposed from their descriptions and confirmed by the user (`:223-224`).
- Errata (`:321-324`) and 18-CONTEXT:
  - D-02: bare names in plan.json, translated to `global:<name>`, a project path or `global:<plugin>:<skill>` (`18-CONTEXT.md:52-63`);
  - D-03: missing skills are silently omitted (`:64-69`);
  - D-04: cap per rigor of 2/3/5, because each wired skill injects its full SKILL.md into every invocation (`:70-75`).
- 17-CONTEXT leaves "the inventory's skill-scan depth and caching" to Claude's discretion (`17-CONTEXT.md:115`).
- `recommend` must be pure, so all I/O happens in `inventory` (`17-CONTEXT.md:174-175`).
- None of it is implemented. `ai_kit_gsd_curated_config/` holds only the v1 modules (`ls` output: no `skills.py`, `recommend.py` or `skill_affinity.json`), and ROADMAP shows Phases 17/18 unchecked with `Plans: TBD` (`.planning/ROADMAP.md:68-69,153,188`).
- 999.4 (ponytail) says ponytail is a Claude plugin, addressable only as `global:ponytail:<skill>` on Claude, and asks to fold it into Phase 18 (`.planning/ROADMAP.md:332-360`).

**Consequence:** GSD runs already have a per-agent curation channel, `agent_skills.<agent>`, filled at config time by Phase 18. The gap is the **ai-kit review/execute dispatches** (native subagents and cross-AI CLIs), which today receive tooling guidance but no skill selection apart from the checklist path.

---

## 2. Cheap inventory per host (measured on this machine)

### 2.1 What each host can actually see

Skill discovery dirs, per vendor docs or local install docs:
- **Claude Code:** `~/.claude/skills`, project `.claude/skills`, plugins. **[D]** https://code.claude.com/docs/en/skills
- **opencode:** `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills`, plus project `.opencode/.claude/.agents` skills. **[D]** https://opencode.ai/docs/skills
- **Cursor:** `~/.agents/skills`, `~/.cursor/skills`, plus `.claude/skills` and `.codex/skills` for compatibility. **[D]** https://cursor.com/docs/skills (via search summary; not fetched directly)
- **Codex:** `$HOME/.agents/skills`, repo `.agents/skills`, `/etc/codex/skills`, system skills. **[D]** https://learn.chatgpt.com/docs/build-skills
- **pi 0.82.1:** `~/.pi/agent/skills`, `~/.agents/skills`, `.pi/skills`, `.agents/skills`, plus any `skills` paths in settings. **[V]** (installed `docs/skills.md:27-39,50-60`). This machine's `~/.pi/agent/settings.json` has no `skills` key. **[V]**

Counts on this machine **[V]**:

| Location | SKILL.md found | Notes |
|---|---|---|
| `~/.claude/skills` | 134 top-level (162 with nested) | 60 symlinks; 73 `gsd-*`; all 17 `ai-kit-*` live only here |
| `~/.agents/skills` | 42 | all 42 also in `~/.claude/skills` |
| `~/.pi/agent/skills` | 33 | all 33 also in `~/.agents/skills` |
| `~/.codex/skills` | 6 (`.system/*`) | codex built-ins |
| `~/.cursor/skills` / `skills-cursor` | 0 / 22 | cursor built-ins |
| `~/.config/opencode/skills` | 0 | opencode relies on the `.claude` and `.agents` compatibility dirs |
| Claude plugins (user scope, `installed_plugins.json`) | 37 | superpowers is installed from **two** marketplaces (15 + 14 skills, the same names), plus ponytail 6, frontend-design 1, typesafe 1 |
| `~/.claude/agents` | 35 (`gsd-*`) | `~/.pi/agent/agents` 10; opencode `agents`/`commands` dirs empty |

**Key fact [V]:** codex and pi cannot see any `ai-kit-*` or `gsd-*` skill, and no host other than Claude sees plugin skills. ponytail lives at `~/.claude/plugins/cache/ponytail/ponytail/5.1.0/skills/<name>/SKILL.md`. When a dispatch to codex, pi or cursor should use a skill, the only channel that works is **its absolute SKILL.md path in the prompt**. This is the concrete job the inventory does: compute `visible_to` per skill and fall back to a path.

### 2.2 MCP server names per host (names only, no values printed) [V]
- **claude:** `~/.claude.json` `mcpServers` = `[codegraph]`; the ai-kit project scope is empty. The plugin `playwright` ships a `.mcp.json`.
- **opencode:** `opencode.jsonc` `mcp` = `[codegraph, gsd]`; `agent` and `command` keys are empty.
- **cursor:** `~/.cursor/mcp.json` = `[codegraph]`.
- **codex:** `config.toml` `mcp_servers` = `[codegraph]`.
- **pi:** no MCP by design. The installed README says "**No MCP.** Build CLI tools with READMEs…" (`pi-coding-agent/README.md:495`).

### 2.3 Scan cost (measured) [V]
Script: `scratchpad/inv09/scan.py`, run with `python3 -I -B`, 5 runs each, warm page cache.
- `full` (walk every root, parse frontmatter name and description, resolve active plugin installPaths from `installed_plugins.json`): **min 5.6 ms, max 19.4 ms**, 347 entries, 78,705 description chars in total.
- `digest` (stat every SKILL.md and agent `.md` for `mtime_ns|size`, then sha256): **2.9–3.1 ms**.
- `rootdigest` (directory mtimes only): **<0.1 ms**. It misses in-place SKILL.md edits, so don't use it alone.
- Description chars by source: claude 46,101 · claude-plugin 4,374 · agents 10,586 · pi 8,188 · codex 2,060 · cursor 240.

**Conclusion [I, high]:** at 6–20 ms the cache would save nothing a human or a model would notice. A persistent `inventory.json` would add a staleness class of bugs (plugin version bumps change `installPath`) for no gain.

---

## 3. Passing a curated subset per host (main knobs only; another agent covers inheritance in depth)

The knobs fall into two kinds. A **hard** filter makes the host itself hide things. A **soft** hint puts a named line in the prompt that the subagent is told to follow.

### Claude Code: native Agent tool (subagents inside the session)
- Omitting `tools` inherits every built-in and MCP tool. The `skills` field **preloads** full skill content, but "controls which skills are preloaded, not which skills the subagent can access". Skills are not inherited from the parent. `mcpServers` can scope or inline servers per agent. **[D]** https://code.claude.com/docs/en/sub-agents
- An ad-hoc dispatch (`subagent_type: general-purpose`, as in `ai-kit-spec-review/SKILL.md:221`) cannot narrow the listing per call. **Soft hint only.** Custom agent files (GSD's 35) can use `skills:` / `tools:`; gsd-core's `agent_skills` already injects through them.

### Claude Code: `claude -p` subprocess
- `--strict-mcp-config --mcp-config <json>` gives exact MCP control.
- `--tools "Read,Grep,..."` covers built-ins only. `--disallowedTools "mcp__*"` removes all MCP tools.
- `--disable-slash-commands` disables all skills and commands.
- `--settings '{"skillOverrides":{...}}'` takes on/name-only/off per skill, but "Plugin skills are not affected by `skillOverrides`".
- `--bare` skips skills, plugins, MCP and CLAUDE.md.
- Sources **[D]**: https://code.claude.com/docs/en/cli-reference and https://code.claude.com/docs/en/skills ("Override skill visibility from settings").
- **Simplest hard mode:** `--disable-slash-commands` plus the selected SKILL.md paths in the prompt.

### opencode
- Per-agent `permission.skill` patterns: `deny` means "Skill hidden from agent, access rejected". `tools: {skill: false}` drops `<available_skills>` entirely. **[D]** https://opencode.ai/docs/skills
- This needs a named agent in config. A per-run inline config is possible in principle but **unverified**. Soft hint by default.

### codex
- `[[skills.config]] path=… enabled=false` lives in `~/.codex/config.toml`. Whether `-c` can set it per run is undocumented. **[D, partial]** https://learn.chatgpt.com/docs/build-skills
- codex cannot see `~/.claude/skills` anyway, so: **soft hint plus absolute path** (`-c` stays for model and effort, as `commands.py` already does).

### pi 0.82.1
- `--no-skills` (explicit `--skill` paths still load), `--skill <path>` (repeatable), `--tools <list>` allowlist, `--no-extensions`, `--no-context-files`. **[V]** (installed `README.md:579,652`, flags table).
- This is the **only host with an exact skill allowlist per run**, and the best fit for hard curation.

### cursor-agent
- No per-run skill knob found. `--mode plan|ask` is read-only mode, not filtering (`commands.py:117-118`). **Soft hint plus path. [I: no knob found ≠ none exists]**

---

## 4. Online evidence on the cost of large tool, skill and MCP surfaces

- **Anthropic, "Advanced tool use"** — https://www.anthropic.com/engineering/advanced-tool-use **[D]**
  - Cost of loading every tool definition up front:
    - 5 MCP servers / 58 tools ≈ 55K tokens before the conversation starts;
    - Jira alone ≈ 17K;
    - 134K tokens of definitions seen before optimization.
  - Tool Search with `defer_loading` ≈ 500 tokens up front, plus 3–5 discovered tools ≈ 3K. Claimed "85% reduction in token usage".
  - MCP-eval accuracy rose from 49% to 74% (Opus 4) and from 79.5% to 88.1% (Opus 4.5).
  - "The most common failures are wrong tool selection and incorrect parameters."
  - Advised when definitions exceed 10K tokens or there are 10+ tools; less useful under 10 tools.
- **Anthropic, Agent Skills progressive disclosure** — https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills **[D]**
  - At startup only `name` and `description` load; SKILL.md loads when it looks relevant; linked files load on demand.
  - No token figures given.
- **Claude Code skill listing budget** — https://code.claude.com/docs/en/skills §"Skill descriptions are cut short" **[D]**
  - "The budget scales at 1% of the model's context window."
  - On overflow, Claude Code drops descriptions "starting with the skills you invoke least".
  - Each entry is capped at 1,536 chars.
  - Knobs: `skillListingBudgetFraction`, `SLASH_COMMAND_TOOL_CHAR_BUDGET`, `skillOverrides: "name-only"`. `/skill-doctor` reports per-skill cost.
- **Codex skill listing budget** — https://learn.chatgpt.com/docs/build-skills **[D]**
  - "At most 2% of the model's context window, or 8,000 characters when the context window is unknown."
  - Descriptions are shortened first, and some skills may be omitted.
- **RAG-MCP** (Gan & Sun, arXiv 2505.03275) — https://arxiv.org/abs/2505.03275 **[D]**
  - Retrieving a shortlist instead of listing every schema "cuts prompt tokens (e.g., by over 50%)".
  - Tool-selection accuracy 43.13% vs a 13.62% baseline.
- **Secondary and practitioner sources** (lower confidence; thresholds vary and were not checked against the primary sources):
  - https://getunblocked.com/blog/mcp-tool-overload/
  - https://speakeasy.com/mcp/tool-design/less-is-more (cites ~30 tools as the point where descriptions overlap)
  - https://www.stackone.com/blog/agent-tool-count-ceiling/
  - OSWorld-MCP ablation (all 158 tools at once hurt performance): https://www.themoonlight.io/de/review/osworld-mcp-benchmarking-mcp-tool-invocation-in-computer-use-agents

**What this means for ai-kit [I, medium-high]:**
- The well-supported effect is that accuracy drops and tokens rise with large *tool schema* surfaces. That applies to MCP, which this machine barely has and which Claude already defers.
- Skills are already progressively disclosed. The live risk is **budget truncation**: ~200 Claude-visible skills and ~50k description chars against a 1% budget. A subagent may then see a name with no description and never pick it.
- **Pointing** a subagent at the right 1–3 skills (name plus path) delivers most of the benefit. **Hiding** the rest matters only on narrow subprocess dispatches.

---

## 5. Is `jev-fast-decision` a good fit?

### 5.1 Facts [V]
- **Live skill (v1).**
  - Zen only by default (`https://opencode.ai/zen/v1/systemone`, `jev-1.13`), with an ad-hoc `JEV_API_URL` repoint (`SKILL.md:66-76`, `reference.md` §Service behavior).
  - Kill switch: `GSD_PATH_JEV=1`. A timeout is required. Below `JEV_MIN_CONFIDENCE` (default 0.7) an answer carries `needs_fallback: true` (`scripts/jev_review.py:27-29,231`).
  - Statuses are `disabled` / `unavailable` / `ok`; it exits 0 and never retries (`reference.md` §Status handling).
- **The skill's own hard rules** (`SKILL.md:39-62`):
  - an `ok` answer "cannot … select a route" or satisfy a gate (`:41-43`);
  - text may leave the machine only with the user's go-ahead (`:44-47`);
  - never treat `unclear` or low confidence as a negative (`:53-55`);
  - Laya contaminates batches: send one item per call (`:78-81`).
- **Plan B** (`main:.planning/docs/system-one-decision-skill/PLAN.md`): backends `laya → typesafe → opencode`, `--probe`, `JEV_ALLOW_REMOTE=1` consent, Laya loopback only, per-backend `min_confidence`. **Not executed:** the todo is pending, and the reference copy lives in `scratchpad/v3/skill/` "reference only: the live skill was not modified" (`main:.planning/docs/system-one-decision-skill/README.md`).
- **The Plan B calibration came from the stub, not from live Laya [I, high]:** every case in `scratchpad/v3/skill/notes/eval-results.json` reports `top: 0.9`, exactly what `LayaStub` returns (`PLAN.md` Task 2 test code), and `calibration.json` = `{"laya": 0.6}`. So the 0.6 threshold is not evidence of real accuracy.
- **Laya, measured by llm-env (todo notes):** ~15 ms p50 sequential, ~60 req/s; 100–200 ms at 8–16 concurrent requests; ~0.4 s reload after 10 min idle; free and local; English instructions recommended. Live cases: choice 0.98/0.95, noul 0.77/0.18, score 0.99. On 14 easy cases: choice 7/8 and noul 6/6, with the wrong or borderline answers at 0.55–0.57 (`PLAN.md` fact table).
- **Availability probe I ran (read-only, free):** `curl -m1 http://127.0.0.1:8010/health` returned **200** in 6 ms: `"status":"ok","loaded":[],"idle_seconds":99726`. Laya is up, with its models unloaded, so the first call pays ~0.4 s. I made no question calls and started no service. Note that `/health` returns 200 even with nothing loaded.

### 5.2 Fit analysis

**Good fit (optional, config time, memoized):**
- **The job:** classify an *unknown installed skill* into one of ~6–8 fixed role buckets. Phase 18 SKL-03 already says these get "host-agent-proposed mappings the user confirms" (`REQUIREMENTS.md:46`).
  - One `choice` item per skill, one request per item on Laya (≈ 15 ms × ~100 skills ≈ 1.5 s). The inputs are local text (name plus description), so nothing leaves the machine.
  - Example buckets with concrete criteria: `planning, execution, review, debugging, docs, frontend, security, none`.
  - Memoize by `sha256(description)` in a user config file. The user confirms, which satisfies the "advisory only" rule.
  - Below threshold, or on `disabled`/`unavailable`: leave the skill unmapped, which means silently omitted (D-03). That is the safe default.
- **Why it beats the host LLM here:** it saves the orchestrator from reading ~100 descriptions (tens of thousands of chars) in its own context. It is deterministic enough to memoize. **[I]**

**Poor fit (do not use):**
- **Per-dispatch skill selection** for review/execute subagents. Inputs are a fixed role plus project facts plus plan file globs, which a lookup table resolves deterministically. A fuzzy model adds variance, and per `SKILL.md:41-43` it may not decide the route anyway.
- **Multi-label "pick 3 of 40".** `choice` is single-label. The workaround is 40 independent `noul` calls with no shared calibration and no ranking between them.
- **Anything that needs code reading, safety or permission gates,** or text that is not English.
- **Remote backends** (Zen/TypeSafe) during autonomous runs: each session needs consent. The repo's own history shows Zen 429 `Account budget exceeded` and an xai billing block (`PLAN.md` fact table; memory note `project_opencode_xai_billing_block`).

**Acceptance rule if used:** accept a jev label only when all of these hold:
- status is `ok`;
- `needs_fallback` is false;
- the label is not `none` or `unclear`;
- the label passes the deterministic gates (for example, `frontend` only when the project has a frontend).

Then show it to the user as a *proposal*. Every other outcome falls back to omit/unmapped. Never retry blindly, and keep the failure reason visible in the plan's `why`.

---

## 6. Design

### 6.1 Schema: in memory per run, with one persisted memo

**`ai_kit_spec/skill_inventory.py`: `scan_skills(env, project_dir=None) -> dict`**, pure I/O, ~80 lines **[I]**:
```json
{
  "schema_version": 1,
  "digest": "<sha256[:16] of path|mtime_ns|size per SKILL.md + plugin installPaths>",
  "skills": [
    {"name": "ponytail", "source": "plugin:ponytail", "path": "/home/…/5.1.0/skills/ponytail/SKILL.md",
     "desc": "<first 200 chars>", "desc_sha": "…", "visible_to": ["claude"]},
    {"name": "systematic-debugging", "source": "plugin:superpowers", "path": "…/6.4.1/…",
     "visible_to": ["claude"]},
    {"name": "react-dev", "source": "agents", "path": "~/.agents/skills/react-dev/SKILL.md",
     "visible_to": ["claude","opencode","cursor","codex","pi"]}
  ],
  "mcp_names": {"claude": ["codegraph"], "opencode": ["codegraph","gsd"], "cursor": ["codegraph"],
                "codex": ["codegraph"], "pi": []}
}
```
- `visible_to` comes from the host discovery rules in §2.1, encoded as one small dict of host to dirs. Project `skills/` and `.claude/skills` dirs are added when `project_dir` is given.
- **Plugins:** read `installed_plugins.json`, keep `scope == "user"` entries, and dedupe by skill name. Prefer `claude-plugins-official` and the newest version; this machine has superpowers twice (§2.1). Never cache `installPath`, because it changes with each plugin version.
- `mcp_names` holds names only, parsed from config (`~/.claude.json`, `opencode.jsonc`, `~/.cursor/mcp.json`, `~/.codex/config.toml`). **Never** values. Health stays with `check_codegraph_mcp_healthy`, run per dispatch.
- No commands inventory in v1: nothing consumes it (see §7).
- **Location:** none on disk. A CLI subcommand prints the JSON, and prose orchestrators save it into their existing `RUN_TMP_DIR`, which serves as the "in-memory cache" for the run.
- **Persisted memo only:** `~/.config/ai-kit/skill-roles.json` = `{desc_sha: {role, source: user|jev, confirmed: bool}}`. It is user-confirmed data, so it belongs in config, not cache, because a cache can be wiped. Invalidation is natural: a changed description means a new `desc_sha`, which means unmapped again.

### 6.2 Who builds it, and when
- `python3 ai-kit-spec.py inventory-skills [--project-dir D]` is a new subcommand next to `detect-tool-availability` (cli.py ~880). It runs once per orchestrator run, in the same step that resolves `TOOL_AVAILABILITY_JSON` (review Step 0.7, execute-gsd `prepare-tooling`, superpowers `dispatch-task`).
- curated-config `inventory` (Phase 17/18) calls the same function. That makes the Phase 18 `skills.py` a thin adapter: role → GSD agent names, plus D-02 reference forms.

### 6.3 Deterministic selection
- **`skill_affinity.json`** (Phase 18, dated and editable) becomes **role-keyed**: `planning`, `execution`, `review`, `debugging`, `docs`, `frontend`, `security`.
  - Each role holds an ordered list of skill names plus gates: `tdd_mode`, `frontend`, `db`, plus `file_globs` for per-plan gating.
  - A tiny `role_of_agent` map translates GSD agents, so `gsd-executor` maps to `execution`. The spec §7 families map 1:1 onto roles.
- **`select_skills(inventory, affinity, role, facts, host, cap) -> [ {name, path, how: "native"|"path"} ]`** is pure. The algorithm:
  1. Start from the role's ordered list.
  2. Drop entries whose gate fails.
  3. Drop entries that are not installed (D-03: silent).
  4. Mark `how = native` if `host ∈ visible_to`, else `path`.
  5. Truncate to `cap`.
  - Ties are impossible because the table is ordered (same spirit as Phase 17 D-06).
  - Unknown skills enter only through user-confirmed `skill-roles.json` entries, appended after the curated ones.
- **Cap:** reuse Phase 18 D-04 (2/3/5 by rigor). Outside GSD, the default is 2.

### 6.4 How skills consume it
- **`build_tooling_guidance` gains one optional argument, `skill_hints`, and emits:**
  ```
  SKILL_HINTS = [{"name":"ponytail","path":"/…/SKILL.md"},{"name":"test-driven-development","path":"/…"}]
  Before starting, invoke (or, if not available as a skill, Read) each SKILL_HINTS entry; ignore other installed skills unless the task clearly needs one.
  ```
  It is a named variable, for the same reason `TOOL_AVAILABILITY` is: a rule keyed on a name only fires if the prompt uses that name (`tooling_guidance.py:27-30,38-46`). It is emitted only for confirmed-present skills.
- **Consumers:**
  - **execute-gsd** `prepare-tooling`: role `execution`, facts from the project, globs from the plan's files list.
  - **execute-superpowers** `dispatch-task`: same.
  - **ai-kit-spec-review**: the reviewer already receives the checklist by path. Add hints only for code-adjacent reviews (for example `ponytail-review`) and keep it optional.
  - **GSD itself:** unchanged. Phase 18 writes `agent_skills.<agent>` from the same `select_skills`.

### 6.5 How the selection reaches each host
- **Default everywhere:** soft hint (`SKILL_HINTS` with paths). It works on all six hosts, including those that cannot see the skill natively.
- **Hard mode, opt-in** (only where the dispatch is narrow, and added in `commands.py` builders behind a flag):
  - **pi:** `--no-skills --skill <path>…` (exact).
  - **claude -p:** `--disable-slash-commands` plus paths in the prompt; `--strict-mcp-config --mcp-config` only when the plan needs a specific MCP server.
  - **opencode/codex/cursor:** no reliable per-run knob found or verified, so soft only.
- **Native Claude subagents:** soft only. The `skills:` preload applies to custom agent files, which GSD already handles.

### 6.6 jev position
- It is used only in the curated-config "unknown skills" step: `JEV_BACKEND=laya`, local, one item per call, English instructions. Its output is a *proposal* the user confirms, written to `skill-roles.json`.
- It is off unless `GSD_PATH_JEV=1`. On `disabled`/`unavailable`/`needs_fallback`, the skill is not proposed (D-03 silent), and the reason goes into plan `why`.
- Gate it on Plan B being executed, so that `--probe` and the Laya backend exist. Until then, the host agent proposes mappings exactly as spec §7 already says.

---

## 7. YAGNI cuts (ponytail lens)

**The smallest version that delivers most of the benefit:** (a) `scan_skills` in `ai_kit_spec`, (b) a role-keyed `skill_affinity.json` plus a pure `select_skills`, (c) one `SKILL_HINTS` line in `build_tooling_guidance`, wired into the three existing dispatch points. Estimated at ~150 lines plus tests **[I]**.

Cut, each with its reason:
- **Persistent inventory cache, TTL and digest invalidation.** A rescan takes 6–20 ms (§2.3). Keep the digest only as a `plan.json` `inventory_digest` field, which Phase 17 already allows (`17-CONTEXT.md:113-114`).
- **Commands inventory.** `~/.claude/commands` is missing, and the opencode `commands`/`agent` config is empty. Subagents don't invoke slash commands.
- **Per-subagent MCP curation.** There are 1–2 servers per host, Claude defers MCP tools, and pi has no MCP. Revisit once a host has 10+ tools or more than 10K tokens of definitions (Anthropic's own threshold, §4).
- **Per-interaction re-decision and an in-memory object across turns.** Prose orchestrators keep no state between turns. Selection happens per dispatch, from a static table plus facts.
- **Hard filters on opencode/codex/cursor.** They are unverified; soft hints with paths work everywhere.
- **jev for per-dispatch routing.** The skill forbids it, it adds variance, and the deterministic table already answers. Keep jev for the optional config-time classifier only.
- **`skillOverrides` writes.** They mutate the user's Claude settings, which the rules forbid, and they don't cover plugin skills.

---

## 8. Risks

1. **Hints aren't enforcement.** Native Claude subagents still see the full listing and may ignore the hint. Mitigation: wording ("invoke before starting"), and the RED/GREEN pressure scenarios already planned in Phase 19. **[I]**
2. **Plugin paths drift.** Each version bump changes the `installPath` (superpowers 6.2.0 → 6.4.1 both on disk). Resolve paths every run from `installed_plugins.json`; never persist them. **[V]**
3. **Name collisions.** superpowers is installed from two marketplaces with the same 14 skill names, plus a project-scope 6.2.0. Dedupe deterministically, or a hint may point at a stale copy. **[V]**
4. **Cross-vendor readability.** A codex/cursor sandbox might not read paths under `~/.claude/plugins/…`. That needs a live check per host in Phase 20/21. Fallback: inline the first N lines of SKILL.md (costs tokens). **[I, unverified]**
5. **Prompt egress.** A path hint makes another vendor's CLI read third-party skill text. This is the same trust class as the prompts sent today, but worth noting for skills that carry internal content. **[I]**
6. **Over-pruning in hard mode.** `--no-skills`/`--disable-slash-commands` can strip a skill the subagent needed mid-task (for example `systematic-debugging` after a test fails). Keep hard mode opt-in and narrow. **[I]**
7. **Counts drift.** 18-CONTEXT recorded "112 in `~/.agents/skills`" (`18-CONTEXT.md:187`); today there are 42. Nothing may hardcode counts or lists; the table holds names only, filtered by presence. **[V]**
8. **jev specific.**
   - The stub-derived threshold (0.6) is not a real calibration.
   - Laya batch contamination.
   - English-only instruction quality.
   - The remote backends need consent and have hit 429 budget blocks.
   - `/health` returns 200 with no models loaded.
   - The live skill is still v1, so the `laya`/`--probe` interface does not exist until Plan B runs. **[V]/[I]** as marked in §5.1.
9. **Spec conflict.** Moving `skills.py` logic into `ai_kit_spec` changes spec §3's module placement (`design.md:104`). It needs an errata line, not a re-decision. **[V]**

---

## 9. Mapping onto v1.3 phases

### Phase 18 (amend before planning; no new requirements)
- **SKL-01:** implement the scan as `ai_kit_spec/skill_inventory.py:scan_skills` (shared), called by curated-config `inventory`. Add `visible_to`, plugin dedupe and an `installed_plugins.json` user-scope filter. Add a spec §11 errata line ("skills scan lives in ai_kit_spec; curated-config `skills.py` adapts it").
- **SKL-02:** make `skill_affinity.json` role-keyed, with a `role_of_agent` map. Behaviour for GSD is unchanged (D-02/D-03/D-04 hold).
- **999.4 (ponytail):** fold it in, as ROADMAP already prefers (`ROADMAP.md:359-360`). The core `ponytail` skill goes to `planning`/`execution`; `ponytail-review`/`ponytail-audit` go to `review`. On the claude host, emit `global:ponytail:<skill>`. On other hosts, gsd `agent_skills` cannot address plugin skills, so no entry (D-03 silent). The execute adapters' path hints cover those hosts instead (new phase below).
- **SKL-03 unknown skills:** unchanged ("host agent proposes; user confirms"). Add an optional note: when the Plan B jev skill is present and `GSD_PATH_JEV=1`, use it as the proposer; it is local only and memoized in `~/.config/ai-kit/skill-roles.json`.

### Phase 17: no change
`inventory` already owns the I/O. It now calls `scan_skills`. Put the digest in `plan.json` (`inventory_digest`, already "Claude's discretion").

### New phase (proposed: "23 — Skill hints in ai-kit dispatch guidance", after 18, independent of 19–22)
- **Goal:** ai-kit review/execute dispatches pass a capped, role-selected `SKILL_HINTS` list (name plus absolute path) to every native or cross-AI subagent, emitted only for confirmed-present skills.
- **Scope:**
  - `select_skills`, plus a `skill_hints` parameter on `build_tooling_guidance`;
  - wiring in execute-gsd `prepare-tooling`, superpowers `dispatch-task`, and optionally review;
  - opt-in hard mode for pi (`--no-skills --skill`) and `claude -p` (`--disable-slash-commands`).
- **Success criteria:**
  - unit tests for gates, cap, visibility and dedupe;
  - one live smoke per host on readability of the path hint (claude, codex, opencode now; cursor and pi with Phases 21/22);
  - `/skill-judge` on the touched SKILL.md files (project rule).
- **Not in scope:** MCP curation, a commands inventory, jev routing.

Should the user prefer fewer phases, the new phase can fold into Phase 18 as a final plan. It touches different modules (`ai_kit_spec` and the execute adapters), though, so a separate phase keeps Phase 18's apply pipeline review smaller. **[I]**

---

## Evidence index (commands run)
- Scan timing: `python3 -I -B scratchpad/inv09/scan.py` (results quoted in §2.3).
- Directory counts: `find -L … -name SKILL.md`, `comm` overlap (§2.1).
- MCP names: a Python one-off that parses `~/.claude.json`, `opencode.jsonc`, `~/.cursor/mcp.json`, `~/.codex/config.toml` and prints sorted key names only (§2.2).
- Plugin actives: `installed_plugins.json` user-scope entries counted (§2.1).
- Laya probe: `curl -s -m 1 http://127.0.0.1:8010/health` → 200, 6 ms (§5.1).
- pi flags: the installed `@earendil-works/pi-coding-agent` 0.82.1 `README.md:495,579,652` and `docs/skills.md:27-60`.
