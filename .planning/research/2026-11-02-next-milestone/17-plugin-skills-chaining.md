# Plugin skills as review lenses, and curated-config wiring them (research, 2026-11-02)

Read-only. Scripts beside this file: `17_inventory.sh`, `17_inventory2.sh`, `17_inventory3.sh`
(skill inventory across hosts, outputs `17_inventory*.out`), `17_history_planning.sh` (planning
docs, `17_history_planning.out`), `17_owner_msgs.py`, `17_owner_msgs2.py`, `17_owner_ctx.py`
(owner-message snippets from the Claude logs, outputs `17_owner_msgs*.out`). Builds on
`9-history-planning-trace.md`, `12-herdr-and-review-lanes.md` and `16-code-review-chain-and-gsd-removal.md`;
none of those covered these lens skills.

## 1. Live inventory

Ponytail plugin root: `~/.claude/plugins/cache/ponytail/ponytail/5.1.0/`.

### ponytail 5.1.0: installed, on four of five hosts

Skills (all six have only `name` and `description` in their frontmatter, plus `argument-hint`/`license` on
`ponytail`; no Claude-only tool names in the body, so they follow the Agent Skills standard):

- `ponytail`: the smallest change that fully solves the task (YAGNI). Fits **planning, execute, fixer**.
- `ponytail-review`: reviews a change for correct, safe, holds under load, tested, fast, lean. Reads the
  connected code, not only the diff. Fits **code review** (not spec review: it expects a change).
- `ponytail-audit`: audits the whole repo for bugs, holes, load, untested risk and what to delete. Report
  only. Fits **milestone audit, verifier**.
- `ponytail-debt`: lists every `shortcut:` comment as a debt ledger. Fits **verifier, milestone close**.
- `ponytail-gain`: prints the benchmark savings. No review value.
- `ponytail-help`: quick reference. No review value.

Per host:

- Claude: plugin `ponytail@ponytail`, enabled in `~/.claude/settings.json`. Its SubagentStart hook already
  injects "PONYTAIL MODE ACTIVE, level full" into every Claude subagent (seen in this research session's
  own context). So on Claude the core lens is always on, whatever `agent_skills` says.
- opencode: `@dietrichgebert/ponytail` in `opencode.jsonc` `plugin`. The package declares
  `skills: ["./skills"]`, and its `.opencode/plugins/ponytail-frontmatter.cjs` feeds them to opencode's skill
  transform, so the six skills are visible there.
- Codex: `[plugins."ponytail@ponytail"] enabled = true` in `~/.codex/config.toml`, cache under
  `~/.codex/plugins/cache/ponytail/`.
- Cursor: only mode-flag files (`~/.cursor/.ponytail-active` = `full`, `~/.cursor/ponytail-modes`). No
  skills dir. Not confirmed as a real install.
- pi: **not installed**. `~/.pi/agent/settings.json` `packages` lists only superpowers, though the npm
  package ships a `pi-extension` and a `pi.skills` entry, so `pi install` would work.

### simplify, code-review, security-review: Claude Code built-ins

None of them exists as a file under `~/.claude`. Their text is bundled in the Claude binary
(`~/.local/share/claude/versions/2.1.316`: the simplify description matches once, code-review twice,
`security-review` 7 times). **Claude-only**, no SKILL.md path to hand another host. `simplify` edits files
(it applies fixes), so as a review lens it must run as a post-review pass, never inside a read-only reviewer.

### naming-analyzer: not installed (was in the past)

- Missing from `~/.claude/skills`, `~/.agents/skills`, all plugin caches, opencode and pi.
- It was installed during v1.1/v1.2: phase 11's CONTEXT cites `~/.claude/skills/naming-analyzer/`, and
  phases 6-15 ran `/naming-analyzer` as the naming step (`.planning/STATE.md:341-408`).
- Its source is in the owner's own repo: `~/git/github/agent-toolkit/skills/naming-analyzer/SKILL.md`
  (portable frontmatter), plus a built plugin at `dist/plugins/naming-analyzer`. The other agent-toolkit
  skills arrived through `npx skills` (`~/.agents/.skill-lock.json`, source `castocolina/agent-toolkit`),
  but naming-analyzer is not among them. Reinstalling it the same way would make it visible to every host.

### reducing-entropy: installed, portable

`~/.agents/skills/reducing-entropy` (from `castocolina/agent-toolkit`), linked into `~/.claude/skills`.
Its description says "use only when users explicitly ask", so a lens prompt has to name it outright, or a
model will not load it on its own.

### impeccable (any spelling): not on this machine

Not found in any skills dir, plugin cache, marketplace, catalog cache or `~/git` checkout. The UI lenses
that do exist: `frontend-design` (Claude plugin, enabled; already in curated-config's frontend family)
and `ui-ux-principles` / `react-dev` in agent-toolkit (not installed). Which "impeccable" the owner means
is an open question: name the source (repo or marketplace) before any design work.

### Other review-relevant skills

- superpowers 7.0.0 `requesting-code-review` and `receiving-code-review`: Claude plugin, opencode plugin
  (`superpowers@git+...`) and pi package. Portable.
- `skill-judge`, `writing-clearly-and-concisely`, `mermaid-diagrams`: `~/.agents/skills`, portable.
- `jev-fast-decision`: `~/.claude/skills` and `~/.pi/agent/skills`; not in opencode's skills dir.

## 2. curated-config today

Paths relative to `skills/ai-kit-gsd-curated-config/`.

- **Discovery** (`ai_kit_gsd_curated_config/skill_scan.py`): `scan_skills` (`:265-290`) reads the project's
  `skills/`, the host's global skills root, and on Claude only `plugin_skills` (`:232-262`). That one reads
  `installed_plugins.json` plus the layered `enabledPlugins` and scans `<installPath>/skills/*/SKILL.md`
  (custom `plugin.json` skill paths are not scanned, `:260`). `ponytail_visibility` (`:293`) reports which
  ponytail skills each host's global root shows; the names are hardcoded in `PONYTAIL_SKILLS` (`:22-28`).
- **Mapping** is a static table, `skill_affinity.json` (as_of 2026-10-15):
  - `ponytail` -> gsd-planner, gsd-executor, gsd-code-fixer (`:4-15`)
  - `ponytail-review`, `ponytail-audit` -> gsd-code-reviewer, gsd-security-auditor, gsd-nyquist-auditor,
    gsd-eval-auditor, gsd-ui-auditor (`:16-30`)
  - `ponytail-debt` -> gsd-verifier (`:31-40`)
  - `jev-fast-decision` -> gsd-advisor-researcher, gsd-assumptions-analyzer, only when a System One
    backend is detected (`:41-51`)
  - `test-driven-development` -> executor, planner when `tdd_mode` (`:52-62`)
  - `frontend-design`, `react-dev` -> ui-researcher, executor, ui-auditor when the project is frontend (`:63-75`)
  - `database-schema-designer` -> planner, executor when the project has a db (`:76-86`)
  - `systematic-debugging` -> gsd-debugger, gsd-debug-session-manager (`:87-97`)
  - `reducing-entropy` -> gsd-code-reviewer, gsd-code-fixer (`:98-108`)
  - `mermaid-diagrams` -> gsd-doc-writer (`:109-118`)
  - There is no naming-analyzer, simplify, impeccable, `requesting-code-review` or `security-review` row.
- **Resolution** (`ai_kit_gsd_curated_config/skills.py`): `resolve` (`:320-346`) walks the families in file
  order, applies the `when` facts from `skill_facts` (`:100-120`: tdd_mode, frontend, db,
  system_one_backend), drops uninstalled skills silently (18-CONTEXT D-03) and caps each agent at
  `SKILL_CAPS = {"mvp": 2, "standard": 3, "rigorous": 5}` (`presets.py:17`). A plugin skill becomes
  `global:<plugin>:<skill>` (`reference_for`, `skills.py:156-167`). Installed skills not in the table get at
  most 10 `skill_proposal` notes built from their description, for the user to confirm (`proposals`,
  `skills.py:419-457`).
- **jev's part:** only as a skill wired into two discuss agents. jev never chooses a mapping; unknown
  skills are proposed from the description text alone.
- **What gsd-core does with `agent_skills`** (local `.claude/gsd-core`, VERSION 1.18.0):
  `references/planning-config.md:408` defines `agent_skills.<agent-type>` as a path or a list of paths.
  `buildAgentSkillsBlock` (`bin/lib/init.cjs:3649`) turns them into an `<agent_skills>` block of
  `@<path>/SKILL.md` includes (`:3764-3776`). A namespaced `global:<plugin>:<skill>` becomes a Skill-tool
  directive **on Claude only** and is skipped with a warning on every other runtime (`:3695-3705`).
  `references/agent-skills-bootstrap.md` adds a self-load step for runtimes where the orchestrator does
  not inject the block.
- **Plugin skills on other hosts:** the plugin-namespaced form cannot work outside Claude. The opencode
  and Codex ponytail installs are not in any root curated-config scans, so on those hosts ponytail is wired
  nowhere.
- **This repo's own `.planning/config.json`:** wires only `skills/jev-fast-decision` for the two discuss
  agents (commit `c4171ff`). No ponytail at all, so the plan-review and code-review ponytail lens of the
  v1.3 runs came from the session rails and the Claude hook, not from config.

## 3. History of the request

- **2026-10-11** (session `e987e526`, `/gsd-capture`): "when I do a gsd-setup, one of the plugins to add to
  the skill list is ponytail, with a lot of emphasis; it has commands for planning, audit, execution and
  review." **Built**: the three ponytail families in `skill_affinity.json` (Phase 18, SPEC item 8,
  amended 2026-10-14, D-33).
- **2026-10-13** (session `e987e526`), the request this file is about: "if our review/fix/execution skills
  can decide which skills, MCPs and commands their subagents get, then take an inventory of what is
  available at each interaction, so no subagent is overwhelmed with options ... keep a short cache of
  tool/MCP/command/skill and decide what to pass to each subagent ... we have a fast-decision skill, we
  could involve it to decide quickly."
  - It became research report `.planning/research/2026-10-13-audit/09-tool-inventory-curation.md`, summed
    up in `00-SYNTHESIS.md:181-200`. Findings: no cache needed (a full scan takes 6-19 ms); the real problem
    is visibility; jev is a poor fit for routing each dispatch, but a good optional fit at config time for
    sorting unknown skills into role buckets, cached by description hash, with the user confirming. The
    smallest version proposed: `select_skills(role)` emits one `SKILL_HINTS` line in
    `build_tooling_guidance`, fed by a role-keyed `skill_affinity.json`, as a new phase after 18.
  - **What happened: partly built, the rest lost.** Built: the inventory and the static table (Phase 18),
    plus unknown-skill proposals from the description, with no jev. Never built, and in no roadmap entry
    or todo: `SKILL_HINTS`, a role-keyed table that the execute and review adapters reuse, jev sorting
    skills into roles, `skill-roles.json`. A search for `SKILL_HINTS|skill-roles|select_skills(role)`
    outside `tmp/` finds nothing.
- **2026-11-02** (session `4f4fa173`): the wish behind this research, now in
  `.planning/milestones/NEXT-MILESTONE-INPUTS.md:690-707` (Round 5).
- Side note: the "ponytail in plan review and code review" rail appears in every autonomous prompt from
  2026-10-14 to 2026-10-30. On 2026-10-24 it became "the ponytail lens goes into the reviewers' prompt".
  It was never moved into config or code.

## 4. spec-review, checklist, fixer, superpowers adapter: lens hook points

**Today, none of them chains a plugin skill.** A search for ponytail, simplify, naming-analyzer,
reducing-entropy, impeccable, frontend-design, security-review and requesting-code-review in
`ai-kit-spec-review*`, `ai-kit-spec-execute*` and `ai-kit-spec-config` finds only one comment
(`references/cross-ai.mjs:2406`). The only skill a reviewer receives is the checklist, by absolute path
(`CHECKLIST_SKILL_MD`, `ai-kit-spec-review/SKILL.md:155`). Every prompt also gets the tooling-guidance
prefix (`ai_kit_spec/tooling_guidance.py:30-64`), and `reviewer_dispatch._reviewer_full_prompt`
(`ai_kit_spec/reviewer_dispatch.py:46-59`) prepends it.

Where a lens could plug in, best fit first:

1. **Into the reviewer prompt, as a named path list.** Add a `LENS_SKILLS = <name>: <abs SKILL.md path>`
   line to `build_tooling_guidance`, next to `SHARED_TOOLING_PATH`. It is the same pattern as
   `CHECKLIST_SKILL_MD`, so the checklist needs one rule that keys off that name: "read each lens and add
   its findings under your severities". One seam reaches the native, subprocess and execute paths, since
   `execute_dispatch.build_execute_guidance` already calls the same builder. This is what the 2026-10-13
   research proposed (`SKILL_HINTS`). Fit by stage:
   - intent, requirements and plan archetypes get `ponytail` (scope and YAGNI) and `reducing-entropy`
   - a UI phase gets `frontend-design` (or impeccable once found)
   - code review gets `ponytail-review` and naming-analyzer
   - milestone audit gets `ponytail-audit` and `ponytail-debt`
2. **As an extra review lane.** A separate reviewer whose only job is the lens: it writes its own
   `iter<N>-<key>.md`, and Step 1.5's merge takes it in. This costs one more dispatch per iteration, and the
   owner already removed a separate ponytail lane on 2026-10-24 ("no 4th my-plan-review ponytail lane, the
   lens goes into the reviewers' prompt"). Keep it only for a lens too large to inline.
3. **As a post-review pass.** For skills that edit (`simplify`, or `ponytail` in fix mode) or that only
   fit after approval (naming-analyzer on new names). They run once, after `### Status: Approved` and
   before Surface, natively on the host. They are not reviewers, because the reviewer contract is read-only.
   Execute uses the same idea at its decision points: when a task is unclear, the adapter can point the
   implementer at `ponytail`. The superpowers adapter only injects a (runtime, model) pair at the
   implementer dispatch, so a lens would ride the same guidance block, not a new seam.

**Cross-AI reviewers and Claude-only skills:**

- A reviewer on another runtime cannot load a Claude plugin skill by name. gsd-core skips `global:<plugin>:<skill>`
  off Claude (`init.cjs:3703`), and the runner turns host skill discovery off on purpose: opencode runs
  with `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` (`cross-ai.mjs:1365`), pi with `--no-skills --no-extensions`
  (`:1370-1373`).
- What works is a path: the prompt names the SKILL.md file under `~/.claude/plugins/cache/...`, and the
  reviewer reads it as a file. The ponytail skills are plain markdown with no Claude-only tools, so this
  works. pi's review mode also accepts `--skill <path>` as its one allowed extra argument (`reviewExtras`,
  `cross-ai.mjs:1385`; self-checks `:5739-5742`, `:9388-9395`).
- Built-ins (`simplify`, `code-review`, `security-review`) have no file. Off Claude they can only be
  copied into the prompt as rules, or left to the native Claude lane.
- Preferred order:
  - a portable copy of the skill (`~/.agents/skills` or the opencode/Codex plugin install) when the
    target host has one
  - otherwise the Claude plugin path, read as a file
  - otherwise skip the lens and say so in the Surface message, never silently
- Where the lens reached a lane matters, so it belongs in the merged report.

## Open questions for the next milestone

- Which "impeccable" is meant (source repo or marketplace)? Nothing by that name exists on this machine.
- Reinstall naming-analyzer from agent-toolkit through `npx skills`, so every host sees it?
- Install ponytail on pi (`pi install` of the npm package), or rely on path hints only?
- Should curated-config read the opencode and Codex plugin installs as skill roots, or keep plugin wiring
  Claude-only and use path hints elsewhere?
- Bring back the 2026-10-13 design (a role-keyed table shared by curated-config, spec-review and execute,
  with jev sorting unknown skills at config time and the user confirming), or keep a static table only?
