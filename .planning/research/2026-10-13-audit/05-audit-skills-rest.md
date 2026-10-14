# 05: Ponytail audit of the remaining skills

Method: `ponytail:ponytail-audit` and `ponytail:ponytail-review`, both loaded with the Skill tool. Order of importance: correct, safe, holds under load, tested, fast, lean.

Tree: the review worktree `review-v13` at 0acbd06 (tip of `gsd/v1.3-curated-config-v2`). The paths below are relative to that tree unless marked otherwise. Between `main` and this tip, the only change to an in-scope skill is in `ai-kit-gsd-curated-config/.../model_detect.py` (`git diff --stat main..HEAD -- <in-scope skills>`: 1 file, +9/-6).

**What these skills do.** These 14 skills are personal agent tools:
- a GSD config writer (`ai-kit-gsd-curated-config`);
- seven repo-convention checkers plus their shared core (`ai-kit-project-rules-*`, `_shared/ai_kit_rules_common`);
- a local pipeline from AI-CLI session logs to a dashboard (`ai-kit-usage-metrics`);
- an opencode provider list/remove tool;
- two Mermaid tools (`mermaid-audit`, `markdown-to-pdf`);
- two prompt-only or template skills (`commit-message`, `cst-refactor`).

**Load assumed:** one person on one workstation. Sometimes two or three agents run at once, and sometimes from a git worktree. The real data on this machine (measured below) is about 4 months of history: 3.1 GB of raw usage-metrics data and 92,520 refined rows.

Legend: **[V]** means I verified it by running something or reading the code line by line. **[I]** means inference, with the confidence stated.

---

## Findings (ranked, numbered across groups)

### Must fix

1. **The usage dashboard can run attacker-chosen script** (`skills/ai-kit-usage-metrics/ai_kit_usage_metrics/dashboard.py:2038-2040`) **[V]**
   - **What this is:** `generate` writes every refined shell command into one inline `<script>` block as JSON. `cmd_dashboard` then opens the page in the browser automatically (`cli.py:108`).
   - **Problem:** The escape is `payload.replace("</script", "<\\/script")`, which only catches lowercase. HTML closes a script tag case-insensitively, so a command such as `echo "</SCRIPT><img src=x onerror=...>"` breaks out of the block. Agents run commands built from repo and web content, so the attacker can be anyone whose text reaches a session. I reproduced it: an unescaped `</SCRIPT>` sat at byte 23925 of the generated HTML. The only existing test uses lowercase (`tests/test_ai_kit_usage_metrics.py:50`).
   - **Fix:** One line: `json.dumps(...).replace("<", "\\u003c")`. Also add one uppercase case to the existing test.
   - **If we skip it:** Opening your own dashboard runs foreign JS. That page holds your whole command history, which can contain tokens and paths, and the JS can send it off the machine with an image request.

2. **The raw store doubles every record, and `refine` loads all of it into RAM** (`capture_claude.py:27-54`; the same envelope is in the codex/opencode capture modules; `cli.py:33-46,73-82`) **[V sizes / I memory, high confidence]**
   - **What this is:** Capture appends one "envelope" record per source line to `~/.local/share/ai-kit/usage-metrics/raw/*.jsonl`. Every `refine` run then reads all raw files into one Python list.
   - **Problem:** Each envelope stores the line twice: as `raw_text` (the string) and as `payload` (the parsed JSON). In a 200-line sample, `raw_text` was 1.10 MB and `payload` 1.05 MB for claude; codex was 0.65/0.63 MB. A grep shows no module outside `capture_*` ever reads `raw_text`.
   - The store is already 3.1 GB: `claude.jsonl` 1.32 GB, `opencode.jsonl` 1.40 GB, `codex.jsonl` 0.35 GB.
   - Parsing a 108 MB slice cost 240 MB of RSS. Scaled up, `refine` needs about 7 GB of RAM today, against 12 GB available (`free -g`), and the store only grows.
   - **Fix:** Keep `raw_text` only when `parse_status == "malformed"`. That is one conditional per capture module and roughly halves the store; add a one-time compaction of the existing files. Later, refine only the sessions that got new records.
   - **If we skip it:** Within months `refine`/`run` gets OOM-killed (OOM = the kernel kills the process for using too much memory). Disk use keeps doubling for no gain.

3. **The AGENTS.md checker crashes on an image link and misses anchored links** (`skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py:82-101`) **[V]**
   - **What this is:** `resolve_instruction_text` follows each Markdown link in AGENTS.md and appends the linked file's text before the rules are checked.
   - **Problem:**
     - `_LINK_RE` also matches `![logo](docs/logo.png)`. The checker opens the PNG as UTF-8 and dies with `UnicodeDecodeError`. Reproduced: in `ai-kit-project-rules-all`, the agents domain then lands in `failed`.
     - A link like `[rules](docs/rules.md#top)` is treated as the file name `rules.md#top`, which does not exist, so it is skipped. Reproduced: R01 flips from `near_miss` to a false `missing`.
   - **Fix:** Strip `#...` from the target. Follow only `.md` files, and read with `errors="replace"`. About 3 lines.
   - **If we skip it:** Any AGENTS.md with a badge or logo makes the agents domain fail. Linked rule files reached through anchors come out as false "missing rules", and the agent is told to insert duplicate text.

4. **Worktree and branch code silently runs the installed `main` copy instead** (`skills/ai-kit-project-rules-all/ai_kit_project_rules_all/dispatch.py:43-78`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/model_detect.py:26-46`) **[V]**
   - **What this is:** Both find sibling skills through a candidate list. `~/.claude/skills/<name>` is tried before the from-checkout sibling directory.
   - **Problem:** On this machine `~/.claude/skills/*` are symlinks into the `main` checkout. Run from the v1.3 worktree:
     - `resolve_entrypoint('ai-kit-project-rules-cicd')` returns `~/.claude/skills/ai-kit-project-rules-cicd/...`;
     - `resolve_ai_kit_spec_path` returns `~/.claude/skills/ai-kit-spec-review/ai-kit-spec.py`.

     So the branch's curated-config imports `ai_kit_spec` from main (v1.2, without the Phase 16 pi/codex work). `tests/test_ai_kit_project_rules_all.py:76-92` "real dispatch" tests exercise the installed siblings, not the code under test. v2 (Phases 17/18) will lean harder on this same resolution path.
   - **Fix:** Put the from-checkout sibling first in both lists, since it is the copy that ships with the caller. Move two lines in each function.
   - **If we skip it:** v1.3 tests pass or fail based on `main`, not the branch. A Phase 17/18 bug can stay green until merge, and the reverse can happen too.

5. **`cst-refactor`'s `rename-symbol` renames every same-named identifier, which is the case it promises to handle safely** (`skills/cst-refactor/codemod_template.py:44-51`; claim at `SKILL.md:17,57-60`) **[V by code reading; could not run because libcst is not installed and installs are banned]**
   - **What this is:** The skill's selling point is safe multi-file renames "where the name appears in unrelated contexts".
   - **Problem:**
     - `RenameSymbol.leave_Name` rewrites every `cst.Name` whose value matches. In LibCST, `Attribute.attr` is a `Name` node, so the SKILL's own example, `rename-symbol --old-name connect --new-name open`, also turns `socket.connect(...)` into `socket.open(...)`. It also renames unrelated local variables and creates a name that shadows the builtin `open`.
     - `RenameParameter.leave_Name` (lines 89-94) likewise rewrites `self.timeout` inside `fetch`.
     - `_matches_call_name` keys on bare names only, so every function named `fetch` is changed.
     - The 455-line template has no tests anywhere in `tests/`.
   - **Fix:** The smallest honest fix is to skip `Name` nodes that are an `Attribute.attr` unless the user passes `--include-attributes`, and to correct the SKILL table row. The real fix is LibCST's `QualifiedNameProvider`. Add one fixture test either way.
   - **If we skip it:** Agents run a "safe" codemod across a repo and get wrong renames in unrelated code, which is exactly the false-positive class the skill exists to avoid.

### Should fix

6. **Curated-config v1 can write a cross-AI config that GSD rejects** (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:176-215`; SKILL.md:86-88) **[V against `~/.claude/gsd-core/workflows/execute-phase.md:415` and `.../detail/elaboration.md:79`]**
   - **What this is:** `apply-execution` with no detected candidate still writes `workflow.cross_ai_execution: true` and no `cross_ai_command`, and SKILL.md documents this as intended.
   - **Problem:** gsd-core's execute-phase says that when plans are marked cross-AI and `cross_ai_command` is unset, it must "error and tell the user to set it". So the "no candidate" branch produces a config that fails on the first `cross_ai: true` plan or `--cross-ai` run.
   - **Fix:** When `degraded_reason` is set, write `false`, or write nothing. One branch.
   - **If we skip it:** Users of v1 hit a GSD error later, far from the skill that caused it.

7. **Curated-config v1 `apply-review` writes keys before validating input, hardcodes the opencode lane, and can make the host review itself** (`cli.py:225-282`, `preference_match.py:47,125-132`) **[V]**
   - **What this is:** It wires the plan-review reviewer.
   - **Problem:**
     - (a) It writes `workflow.plan_review_convergence` and `review.effort.opencode` before it checks `--cli`. An unknown CLI exits 2 after two writes, and the test locks that in: it feeds two successful writes (`tests/test_ai_kit_gsd_curated_config.py:959-978`).
     - (b) It writes `review.effort.opencode=high` even when the reviewer is cursor or claude.
     - (c) With no ladder match, it adds `claude`/`opus` as the reviewer, so a Claude-hosted plan is "cross-AI" reviewed by Claude. The v2 spec forbids this ("lane ≠ host, reviewer provider ≠ planning provider", ROADMAP Phase 18 SC2).
   - **Fix:** Validate the slug first. Write `review.effort.<slug>`. Skip the reviewer, or report "no cross-AI reviewer", when the match is native.
   - **If we skip it:** Partial configs, a wrong-lane effort key, and review that is not really cross-AI.

8. **Two sibling checkers contradict each other on this very repo** (`ai-kit-project-rules-precommit` category-absence vs `ai-kit-project-rules-makefile` alias map, `makefile_checker.py:52,71`) **[V]**
   - **What this is:** Both classify lint/duplicate/dead-code tooling, but each uses its own vocabulary:
     - makefile: `formatter` / `code-smell-detector` / `duplicate-code-detector` ...;
     - precommit: the six-category taxonomy plus `_shared/tool_catalog.py`.
   - **Problem:** Run on this repo:
     - makefile says `validate-duplicate` is required because of "duplicate-code-detector category's concrete target(s): duplicat[e-code]";
     - precommit says "no duplicate-code tooling detected -- add ... pylint R0801". But `Makefile:116-117` runs exactly `pylint --enable=duplicate-code`.
     - precommit marks `pylint` as `unclassified_tool` while makefile classifies it as `code-smell-detector`.

     `ai-kit-project-rules-all` merges both into one report.
   - **Fix:** Drop makefile's private category→target-name map and resolve categories through `_shared/tool_catalog.resolve_tool_category`. Have the precommit absence check also read Makefile recipes, which the shared `makefile_parse` already supports. Add `pylint` to the catalog.
   - **If we skip it:** The merged report recommends adding tooling that exists and contradicts itself, so users stop trusting it.

9. **`remediate` throws away the fix text** (`skills/_shared/ai_kit_rules_common/remediation.py:95-109`) **[V]**
   - **What this is:** The shared builder turns findings into the `remediate` list that agents act on, and the only list `-all` returns.
   - **Problem:** It copies `summary` but not `recommendation`. Where they differ, the agent loses the fix:
     - `check` says "add a `.DEFAULT_GOAL := help`-style directive ... or a stemless catch-all rule (`%:`)";
     - `remediate` only says "no `.DEFAULT_GOAL` directive ... has no reachable help path".

     It still marks the entry `auto_apply: true`.
   - **Fix:** Add `"recommendation": finding.get("recommendation")` to the entry. One line.
   - **If we skip it:** Agents driving from `remediate`/`-all` have to guess the fix for every finding whose summary only describes the problem.

10. **The usage dashboard loads about 10 third-party ES modules (JavaScript modules) with no integrity check, into a page that holds all command history** (`dashboard.py:49-92`) **[V]**
    - **What this is:** It uses Material Web from `unpkg.com/...?module`, which rewrites transitive imports to whatever version is current when the page loads, and `@tanstack/virtual-core` from `esm.run`. Only Chart.js has `integrity=`.
    - **Problem:** A compromised CDN, or a bad transitive release, runs in the same page as finding 1's data. The file is also 90 MB with 92,520 rows (`ls -la .../dashboard.html`), and every row ships all 29 columns, including `raw_ref` and `resolved_cwd`.
    - **Fix:** Replace the Material Web controls with native `<input>`/`<select>`/`<dialog>`. That deletes 8 CDN imports and keeps only tanstack and Chart.js, pinned. Drop the unused columns from `_QUERY_COLUMNS` for the payload.
    - **If we skip it:** A supply-chain path to your private history, and a heavy page that keeps getting heavier.

11. **Docker compose parser re-implements the shared YAML helpers** (`skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/compose_parse.py:72-165`) **[V]**
    - **What this is:** Six private functions: `_is_document_separator`, `_effective_structural`, `_strip_inline_comment`, `_match_key_header`, `_find_block_end`, `_own_level_lines`.
    - **Problem:** They match `_shared/ai_kit_rules_common/yaml_text.py` apart from names and docstrings (diffed). `cicd/ci_parse.py` already uses the shared ones, but `_find_own_key` and `_lines` are still copied in both cicd and docker.
    - **Fix:** Import the shared ones and delete about 90 lines.
    - **If we skip it:** A YAML edge-case fix lands in one copy and not the other.

12. **`ai-kit-project-rules-docker` description is over the 1024-character skill limit** (`skills/ai-kit-project-rules-docker/SKILL.md:3`) **[V count / I enforcement, medium]**
    - **What this is:** The routing description is 1092 characters. The Agent Skills spec caps `description` at 1024. `mermaid-audit` is at 987 and close.
    - **Problem:** Hosts that enforce the cap (I believe codex's skill loader does; medium confidence) skip or truncate the skill. Even where it loads, its text takes up the always-on skill listing in every session.
    - **Fix:** Cut it to about 300 characters. The "routes apart from X" sentences belong in the body.
    - **If we skip it:** The skill may silently not exist on some hosts.

13. **The seven rules skills pay twice for being seven: copy installs break, and about 25k tokens of instructions** (all seven `__init__.py` + SKILL.md) **[V]**
    - **What this is:**
      - Each package's `__init__.py` has an identical 20-line `_shared` bootstrap that raises `ImportError` unless installed by symlink.
      - The agents SKILL.md admits candidates 1, 3 and 4 (plugin root, opencode dir, `~/.agents`) "raise ImportError at import time by design" (`ai-kit-project-rules-agents/SKILL.md:28`).
      - There are six re-export-only `remediation.py` shims, plus agents' `tool_presence.py`/`rule_checker.py` and two `stack_cache.py` wrappers.
      - The bodies total about 24.3k tokens across seven SKILL.md files, and the descriptions about 4.8k chars (around 1.2k tokens) are always loaded.
    - **Problem:** A kit whose goal is "multi-CLI" ships checkers that cannot run when copy-installed into opencode, `~/.agents` or a plugin root. Each skill's SKILL.md and CLI repeat the same resolve block, `check`/`remediate` contract and report-only rules.
    - **Fix:** See "Merge candidates". Make it one skill, `ai-kit-project-rules`, with `check|remediate [--domain agents|makefile|...|all]`, holding `_shared` inside it. That removes the sys.path hack and the copy-install limit.
    - **If we skip it:** Every new domain adds another always-on description and another copy of the bootstrap.

14. **Every skill's SKILL.md carries a 5-path "find my own script" loop** (11 SKILL.md files, about 12-14 lines each) **[V]**
    - **What this is:** It is the `for d in "${CLAUDE_PLUGIN_ROOT:+...}" "$HOME/.claude/skills/..." ...` block.
    - **Problem:** The agent already knows the absolute path of the SKILL.md it loaded, and the script sits next to it. For the rules skills, three of the five candidates are documented to fail anyway. The loop can also pick a different copy than the one whose instructions are loaded (same version skew as finding 4).
    - **Fix:** Use one line, "run `<dir of this SKILL.md>/<name>.py`". That saves about 150 lines of instruction text kit-wide.
    - **If we skip it:** Token cost every time a skill loads, and an instruction/code mismatch when copies diverge.

15. **`commit-message` collides with `commit-work` and imposes a foreign convention** (`skills/commit-message/SKILL.md:3,31,36-45`) **[V]**
    - **What this is:** A 65-line prompt-only skill.
    - **Problem:**
      - Its triggers ("commit message", "write a commit") overlap the installed `commit-work` skill, which is listed in this session.
      - It prescribes `type: [task-id] description` with the task ID taken from `docs/tasks/`, and has no `(scope)`. This repo's own history uses `feat(16-06): ...` and has no `docs/tasks/`. It also omits the `perf`/`ci`/`build`/`revert` types.
      - It is not linked into `~/.claude/skills` on this machine.
    - **Fix:** Delete it, or cut it to the one rule `commit-work` lacks (output only, never commit).
    - **If we skip it:** Routing is a coin-flip between the two skills, and in other repos you get messages in another project's format.

16. **Mermaid consensus eval covers 3 of 7 rules and has no recorded run** (`skills/mermaid-audit/evals/fixtures/gold.json`, `score_consensus.py:51-54`) **[V]**
    - **What this is:** The judge protocol scores C1/C2/C3/C5/S1/S3/S4. `gold.json` has only `C1`, `C3`, `S1` and one clean fixture.
    - **Problem:** `rule_well_formed` iterates only the rules present in gold, so C2/C5/S3/S4 can never come out "WEAK". The pass bar is unreachable for them, yet reported as passing. No `evals/verdicts/` exists in any commit (`git log --all -- skills/mermaid-audit/evals/verdicts*` is empty). The deterministic analyzer does agree with gold on the three fixtures.
    - **Fix:** Add one fixture per missing rule. Make `score` treat any rule named in the protocol but absent from gold as "untested" rather than passing.
    - **If we skip it:** The "rules are objective enough" claim is unproven for four of seven rules.

17. **`mmdc` runs with no timeout, no sandbox and a shared fixed work directory** (`skills/mermaid-audit/scripts/audit_mermaid.py:100-103,108,121-125`; `skills/markdown-to-pdf/scripts/render_mermaid.py:57-63`) **[V by code reading]**
    - **What this is:** Both shell out to Mermaid CLI (headless Chromium) with `--no-sandbox` and no `timeout=`. `audit_mermaid.py` defaults to `/tmp/mermaid-audit` and never deletes its `.mmd` files.
    - **Problem:**
      - A hung Chromium hangs the audit forever.
      - Two parallel agents auditing the same doc overwrite each other's `puppeteer-config.json` and `.mmd` files, and get wrong results.
      - `.mmd` files pile up in `/tmp`.
      - Untrusted diagrams render in an unsandboxed browser.
    - **Fix:** Add `timeout=120` and default `--out` to `tempfile.mkdtemp()`. Drop `--no-sandbox` unless running as root or in a container.
    - **If we skip it:** Stuck runs and rare cross-run corruption.

18. **`markdown-to-pdf` probably loses relative images** (`skills/markdown-to-pdf/scripts/markdown_to_pdf.py:67-82`) **[I, medium; I could not run it because no backend is installed here: `which pandoc typst tectonic xelatex pdflatex weasyprint md-to-pdf marp` found nothing]**
    - **What this is:** It writes the rewritten Markdown to `<tmpdir>/doc.md` and runs pandoc or md-to-pdf from the caller's current directory.
    - **Problem:** `![x](img/a.png)` in the source is now resolved against the caller's cwd (pandoc) or the temp dir (md-to-pdf), not the source file's directory.
    - **Fix:** Pass `cwd=os.path.dirname(src_md)` to `run(...)`, plus `--resource-path=<srcdir>` for pandoc. Add one test with a relative image.
    - **If we skip it:** Docs with screenshots render without them, or LaTeX aborts.

19. **The cache staleness window is "deliberately unfixed" against its own spec** (`skills/_shared/ai_kit_rules_common/stack_cache.py:27` vs `.planning/intel/constraints.md:48`; noted in `precommit/stack_cache.py:6-11`) **[V]**
    - **What this is:** Code says 30 days and the constraint says 180. Two phases noted it and left it.
    - **Problem:** The same rule has two values. Research gets re-triggered six times as often as the spec intends, or else the spec is wrong.
    - **Fix:** Pick one, change one line, and delete the "known discrepancy" paragraph.
    - **If we skip it:** The next phase notes it a third time.

20. **`cst-refactor` only resolves its template through `$CLAUDE_PLUGIN_ROOT`** (`skills/cst-refactor/SKILL.md:39-43`; README.md:536 admits it) **[V]**
    - **Problem:** With a symlink install, the variable is unset, so `cp "${CLAUDE_PLUGIN_ROOT}/skills/..."` becomes `/skills/cst-refactor/...` and fails. The template also needs `libcst`, which is not in `pyproject.toml`/`uv.lock` and not importable here.
    - **Fix:** Use "copy `<dir of this SKILL.md>/codemod_template.py`", the same fix as finding 14.
    - **If we skip it:** The skill's first step fails on the install path ai-kit itself uses.

Left out for the 20-item cap (all minor, all **[V]**). These are 9 small items:
- In `ai-kit-project-rules-all`, `check` and `remediate` are byte-identical (`cli.py:216-228`); keep one.
- In curated-config, `WORKFLOW_DEFAULTS`' docstring says "exactly five" excluded keys but lists six (`workflow_defaults.py:7-13,51-59`).
- In `markdown-to-pdf`, `WINNER = "typst"` is recommended while the quality order picks pandoc-latex (`detect_backends.py:16-25`).
- `ai-kit-opencode-providers` only looks for `opencode.jsonc`, not `opencode.json` (`config_paths.py:8-17`).
- `cross_ai_build.build_execution_command` substitutes `{model}` unquoted into a shell string (`cross_ai_build.py:60`; template `ai_kit_spec/commands.py:~268` `opencode run -m {model}`). Cursor bracket ids such as `x[effort=high]` are glob patterns.
- The `audit_mermaid.sh` no-Python fallback is dead weight in a Python-runtime kit (`scripts/audit_mermaid.sh:15-30`).
- `precommit_parse._strip_yaml_quotes` duplicates `yaml_text.strip_yaml_quotes`.
- `_shared/classification.py` and `_shared/tool_presence.py` each have one consumer (agents), so sharing them is speculative.
- `_atomic_write_text` exists in 4 places: `tools/setup.py`, `opencode-providers/atomic_write.py`, `usage-metrics/dashboard.py:2000`, and `_shared/stack_cache`. This is justified by the self-contained-skill rule, so it is not a finding.

---

## Per-skill notes

### ai-kit-gsd-curated-config (v1, and how v2 overlaps it)

**State of v1 [V]:**
- 11 subcommands, 1386 lines including SKILL.md; `cli.py` is 452 lines.
- 94 tests pass in 4.0 s. That includes 3 tests against the real installed gsd-tools (`TestRealIntegration`, `TestMergeModeEndToEnd`), which ran here because gsd-core is installed.
- So v1 is tested by the suite. It is *untested by the user*: memory note `project_curated_config_v1_untested.md` and 18-CONTEXT D-08 ("tried to cover a lot but did little").
- Bugs found: 6, 7 and 4 above.
- `cli.py` repeats the same "resolve node, call `config_set`, print the error, return 1" block about 14 times. A helper would cut about 100 lines, but deleting v1 is better.

**Does v2 duplicate v1? Yes, by design, and the spec already says which parts die [V]:**
- The v2 design (`docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md:107`) lists "Removed: `preference_match.py` name ladders, `critical_agents.py`, `workflow_defaults.py`".
- §6 and ROADMAP Phase 18 SC2 re-implement v1's `apply-execution`/`apply-review` with different rules: a role-scored lane, and lane ≠ host.
- v2 `recommend`/`apply` write the same key families v1 writes: `model_overrides.*`, `effort.agent_overrides.*`, `models.*`, `review.*`, `workflow.cross_ai_*`, `workflow.*`.
- 17-CONTEXT D-08 says "plan-managed families are authoritative (`op: unset`)". So after v2 lands, the CLI will have two writers for the same keys under conflicting rules. Example: v1 always writes `models.research: haiku` and `model_overrides.gsd-executor: haiku`; v2 derives those per rigor and unsets the rest.
- What is legitimately shared and should stay: `gsd_write.py`, `gsd_catalog.py`, `frontend_detect.py`, `claude_md_detect.py`, and the `build_execute_command` wrapper.
- **Recommendation:** Keep v1 only until Phase 19 has used it as the "v1 baseline" in its pressure scenarios. Then delete the 7 v1 apply/detect-ladder subcommands plus `preference_match.py`, `critical_agents.py` and `workflow_defaults.py`. That is about 600 code lines and most of the 94-test v1 suite.
  - Until then, SKILL.md should label the v1 subcommands "legacy, do not mix with `apply`". That way an agent never runs both writers on one project.

**SKILL.md:** 171 lines, about 3.2k tokens. The description is 834 characters and describes v1's one-question flow, so it will be wrong as soon as v2 ships. It cites planning IDs (D-01..D-10, 07-CONTEXT) 8 times, which a runtime agent cannot use. Routing vs `gsd-settings`/`gsd-config` is handled explicitly. That is fine but wordy.

### ai-kit-project-rules-* (7 skills) and `_shared/ai_kit_rules_common`

**Code [V]:**
- All suites pass: agents 21, all 13, arch 65, cicd 207, docker 151 (1 skipped), rules_common 186. The makefile and precommit suites ran OK.
- Running all six on this repo takes 0.19 s through `-all`, so speed is not an issue.
- Bugs: findings 3, 8 and 9.

**Duplication inventory [V]:**

| Item | Copies | Lines each |
|---|---|---|
| `_shared` sys.path bootstrap in `__init__.py` | 6 | ~20 |
| `remediation.py` re-export shim | 6 | 12 |
| `cli.py` `check`/`remediate`/`main` (diff shows only docstrings differ) | 5 identical + agents/makefile/precommit variants | 43-130 |
| `stack_cache.py` namespace wrapper | 2 | ~50 |
| `_split_cache_root`, `cache_update`, `validate_tooling_payload` | 2 (makefile, precommit) | — |
| YAML line helpers duplicated from `_shared/yaml_text` | docker `compose_parse.py` (6 fns) | ~90 total |
| `_find_own_key`, `_lines` | 2 (cicd, docker) | — |
| `_real_recipe_lines` | 2 (cicd, precommit) | — |
| `normalize_target_name` | 2 (arch, docker) | — |

**Is the shared core used consistently? Partly.**
- `remediation`, `makefile_parse` and `criticality` are used everywhere they apply.
- `yaml_text` is used by cicd but bypassed by docker.
- `tool_catalog` is used by precommit, cicd and docker, but makefile keeps its own category map, which causes finding 8.
- `classification` and `tool_presence` have one consumer.
- `precommit_parse` duplicates a `yaml_text` helper.

**Does `-all` add real value?**
- **Small but real:** one call instead of six, failure isolation, and one global sort. `dispatch.py` plus `aggregate.py` is about 195 lines.
- **But:**
  - its `check` and `remediate` are identical;
  - it inherits finding 9, so its whole output lacks the fix text;
  - its resolver runs the installed copy (finding 4);
  - its SKILL.md is 217 lines and about 3.5k tokens to explain about 50 lines of logic.
  - About half of that SKILL.md describes internals (dispatch resolution, D-04/D-05/D-06/SC2/SC3; 12 planning-ID references) that an agent running it does not need.
- It is worth keeping only as the default mode of a merged skill.

**SKILL.md weight [V]** (lines / words / ~tokens at chars÷4 / description chars):

| Skill | Lines | Words | ~Tokens | Desc chars |
|---|---|---|---|---|
| ai-kit-project-rules-agents | 102 | 1222 | 2258 | 268 |
| ai-kit-project-rules-makefile | 231 | 1683 | 3139 | 596 |
| ai-kit-project-rules-precommit | 245 | 2042 | 3775 | 828 |
| ai-kit-project-rules-arch | 181 | 1541 | 2692 | 537 |
| ai-kit-project-rules-docker | 251 | 2338 | 4250 | **1092** |
| ai-kit-project-rules-cicd | 299 | 2732 | 4713 | 797 |
| ai-kit-project-rules-all | 217 | 1900 | 3478 | 667 |
| **Total** | 1526 | 13458 | ~24.3k | 4785 |

**Routing overlap:**
- makefile, precommit and cicd all read the Makefile and `.pre-commit-config.yaml`.
- docker and makefile both judge `docker-*` targets.
- Each description therefore spends a sentence or two on "Routes apart from X". That is a sign the split is by file, not by user question.

### ai-kit-usage-metrics

- **Size:** 5282 lines. `dashboard.py` is 2050 lines, of which about 1950 are an HTML/JS/CSS string literal (`_HTML_HEAD` at line 44 to `_HTML_MID` at line 672 and on to about line 1990). Ruff, pyright and eslint cannot see that JS.
- The family/subfamily logic exists in both Python and JS (`tests/...:261` checks the two agree).
- **Tests:** 156 pass in 0.27 s. The 5137-line test file includes 41 `TestDashboardFull` tests, mostly `assertIn` on the HTML (115 string assertions) plus node-executed JS when `node` is present.
- **Correctness and safety:** finding 1 (XSS), finding 10 (CDN).
- `opencode.db` and `rtk/history.db` are opened read-only through `?mode=ro`, which is good. Raw/refined dirs are 0700 and files 0600 [V `ls -la`].
- **Load:** finding 2. `refine` re-reads the whole history on every run. Per 20k records it was fast (0.3 s load, 0.1 s refine), so the cost is memory, not CPU.
- `capture_claude` calls `readlines()` on every session file on every run, even when the cursor shows only a few new lines. That is O(total history) of I/O per capture. It is a nice-to-have.
- **SKILL.md:** 313 lines, about 4.1k tokens. About 40% restates the schema (`## Refined schema`, 29 columns verbatim) and the dashboard UI (`## Dashboard`, about 45 lines on filter-bar order and chart styling). An agent running `run` needs neither. The dedup rule is stated three times: the `refined_store.py` docstring, the schema section, and the NEVER list. Cut it to about 120 lines.
- No routing collision.

### ai-kit-opencode-providers

- **Code [V]:** 73 tests pass. I hand-tested the hand-rolled JSONC remover on six edge cases: a trailing comma, the only entry, comments between entries, the same key nested deeper, `//` inside a URL string, and the key inside a block comment. All six gave correct output and `validate_removal`=True.
- The atomic write keeps mode, owner and symlink target and fsyncs the directory, which is good.
- The only gap is `opencode.json` vs `.jsonc` (minor).
- **SKILL.md:** 174 lines, about 1.9k tokens; the description is 393 characters and tight. No collision. This is the healthiest skill in scope.

### mermaid-audit

- **Code:** finding 17. Fence extraction is correct for indented and tilde fences. The geometry pass degrades cleanly when `mermaid_style` is missing. 29 tests pass (`test_mermaid_style`).
- **Evals:** finding 16.
- **SKILL.md:** 273 lines, about 4.0k tokens; the description is 987 characters, close to the cap.
- **Overlap:**
  - with `mermaid-diagrams` ("fixing a diagram that looks bad" vs "create/visualize diagrams");
  - with `markdown-to-pdf`, which also triggers on "render mermaid".

  The body already defers `examples/*` to on-demand reading, which is good progressive disclosure.

### markdown-to-pdf

- **Code:** 172+91+45 lines and 26 tests pass, all through injected `which`/`run`. Finding 18 is the main risk. `render_mermaid.find_fences` is an acknowledged adapted copy of mermaid-audit's extractor; that is acceptable under the self-contained rule.
- **Reachability [V]:** No PDF backend is installed on this machine. The skill is not linked into `~/.claude/skills`, and it does not appear in this session's skill list.
- **SKILL.md:** 103 lines, about 1.3k tokens, which is fine.
- **Overlap:** with `marp-slide` ("build a deck from this markdown") and `anthropic-skills:pdf`.

### commit-message

- 65 lines, about 650 tokens, no code. Finding 15. Not installed here.
- **Delete candidate.**

### cst-refactor

- 95-line SKILL.md (about 1.2k tokens) plus a 455-line template with no tests, and `libcst` is not a dependency. Findings 5 and 20. Not installed here.
- **Fix or delete.** The "codemod vs alternatives" table and the NEVER list are good. The template does not deliver the table's key promise.

### Unused or unreachable on this machine [V `ls -la ~/.claude/skills`]

- `commit-message`, `cst-refactor` and `markdown-to-pdf` are not linked. The other 18 ai-kit skills are.
- `markdown-to-pdf` also has no backend, and `cst-refactor` has no `libcst`.
- The mermaid consensus eval has never produced a verdict file.
- The v1 curated-config subcommands are unused by the user (per memory).

---

## Delete / merge / split candidates

**Delete:**
- Curated-config v1 ladder/preset modules and their 7 subcommands, after Phase 19 records its v1 baseline. That is `preference_match.py`, `critical_agents.py`, `workflow_defaults.py` and the v1 parts of `cli.py`: about 600 code lines plus most of the v1 tests.
- `commit-message`, which is covered by `commit-work`.
- `scripts/audit_mermaid.sh`'s no-Python fallback: 15 lines.
- The 6 `remediation.py` shims, the agents `tool_presence.py`/`rule_checker.py` re-exports, and docker's private YAML helpers: about 180 lines.
- The 5-candidate resolve loop in every SKILL.md: about 150 instruction lines.
- `raw_text` in non-malformed raw envelopes: about half of a 3.1 GB store.
- The Material Web dependency in the dashboard: 8 CDN modules.

**Merge:**
- Merge the seven `ai-kit-project-rules-*` skills into one, `ai-kit-project-rules`, run as `<check|remediate> [repo] [--domain agents|makefile|precommit|arch|docker|cicd|all]`. Default to `all`.
  - Keep one package per domain as subpackages, and keep `_shared` inside the skill. This fixes the copy-install ImportError without the sys.path bootstrap.
  - Write one description of about 400 characters. The per-domain notes go in `references/<domain>.md`, loaded on demand.
  - Estimated savings: about 4.4k always-on description characters, about 15k body tokens, and about 300 code lines.
  - It also removes finding 4's sibling resolution for rules entirely, because the fan-out becomes in-process.
- Fold the makefile alias category map into `_shared/tool_catalog` (finding 8).

**Split:**
- `dashboard.py`: move the about 1950-line HTML/JS template into `dashboard_template.html` (read with `importlib.resources`/`open`). Then the JS can be linted and diffed, and Python owns only data injection. This split is by job (data vs view), not by line count.

---

## Top 5 highest-value fixes

1. **Escape `<` in the dashboard JSON payload** (finding 1). One line plus one uppercase test. It closes a real script-injection path into a page holding all your command history.
2. **Stop storing `raw_text` twice, and compact the raw store** (finding 2). About 5 lines per capture module. It halves 3.1 GB and keeps `refine` out of OOM territory.
3. **Prefer the from-checkout sibling over `~/.claude/skills`** in `dispatch.resolve_entrypoint` and `model_detect.resolve_ai_kit_spec_path` (finding 4). Four moved lines. v1.3 tests then test v1.3 code. Without it, Phases 17/18 build on main's `ai_kit_spec`.
4. **Carry `recommendation` into `remediate` entries, and unify the category vocabulary** (findings 9 and 8). One line plus a map deletion. The merged rules report then stops dropping fixes and stops contradicting itself on this repo.
5. **Fix the AGENTS.md link follower** (finding 3): strip anchors, follow `.md` only. About 3 lines. Without it, a common README-style badge crashes the agents domain.

Close behind: make `cst-refactor` attribute-aware or retract its claim (finding 5), and make v1 `apply-execution` write `false` when there is no command (finding 6).

---

Verdict: fix 1, 2 and 4 first. Finding 1 is safety; 2 is load at today's data size; 4 makes the v1.3 tests trustworthy.

Lean: about -1,100 code lines, about -150 to -15k SKILL.md lines/tokens (depending on the rules merge), -1 skill (`commit-message`), and -6 rules skills if merged; -8 CDN dependencies.

Not checked:
- The dashboard JS was not run in a browser.
- `cst-refactor` was not executed (`libcst` missing; installs banned).
- `markdown-to-pdf` was not run (no backend installed).
- Rules checkers were run only against this repo and two scratch repos, not a broad fixture corpus.
- The precommit `enable_everything`/`ruff_checks` and cicd `reuse_sources`/`gradle_tasks` logic was skimmed for structure only, not read line by line.
- Whether codex rejects descriptions over 1024 characters is medium confidence.
- The usage-metrics `refine` memory figure is extrapolated from a 108 MB slice, not measured on the full store, so as not to load about 7 GB on the user's machine.
