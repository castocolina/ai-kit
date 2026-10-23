## Assessment

**CURRENT improves the runtime/model mental model, but retains operational and portability gaps.** Both versions are **Process/Tool hybrids** and earn **B grades**.

I read both complete `SKILL.md` files and their `references/cli-model-selection.md` files. I also source-checked relevant command, configuration, routing, and ranking behavior. No commands were executed or files changed.

In the table, **S** means that version’s `SKILL.md`; **R** means its `references/cli-model-selection.md`.

## Dimension scores

| Dimension | BASELINE | CURRENT | Evidence and rationale |
|---|---:|---:|---|
| **D1: Knowledge Delta /20** | **17** | **17** | High-value project-specific knowledge: model-family grouping, unmatched-candidate confirmation, canonical catalog keys, trust, and cumulative timeout tiers. Both repeat historical explanations and invariants more than necessary (S:42–64; R’s repeated purpose explanations). |
| **D2: Mindset + Appropriate Procedures /15** | **13** | **14** | Both combine quota reliability/model suitability judgments with the non-obvious group → confirm → rank sequence. CURRENT improves the conceptual framework by separating configured pairs, session defaults, and per-call routing (CURRENT S:301–335); BASELINE overgeneralizes other hosts’ native selectors (BASELINE S:252–254). |
| **D3: Anti-Pattern Quality /15** | **14** | **14** | Both have specific, reasoned prohibitions against guessed model IDs, ungrouped catalogs, untested entries, silent global changes, and unconsented trust (S:66 onward). Strong experiential knowledge, although some absolute claims remain overbroad. |
| **D4: Specification Compliance /15** | **15** | **15** | Valid frontmatter and name. Both descriptions clearly state what the skill does, explicit activation scenarios, `review-spec.toml`, and supported flags (S:1–4). |
| **D5: Progressive Disclosure /15** | **13** | **13** | Excellent conditional loading: mandatory complete reference reading plus explicit “Do NOT load” branches, and selected-profile-only loading. However, the main files remain dense, with historical rationale and duplicated contracts that belong in narrower references. |
| **D6: Freedom Calibration /15** | **9** | **10** | Both correctly constrain fragile config operations through factories and explicit consent. CURRENT reduces hand-authored command risk by storing runtime/model pairs (S:225–232). Fixed scratch files, incomplete failure checkpoints, and host-specific interaction mandates remain poorly calibrated. |
| **D7: Pattern Recognition /10** | **8** | **8** | Clear locate → detect → ask → write → report process, with tool-level rigor and scenario navigation. Repetition and implementation-history commentary prevent a particularly economical application of the pattern. |
| **D8: Practical Usability /15** | **8** | **8** | Common paths are actionable, including failed probes and untrusted local files. Both still have consequential target-path, execution-eligibility, scratch-file, and reporting gaps. CURRENT’s clearer architecture does not fully propagate through candidate selection and reporting. |
| **Total /120** | **97** | **99** | CURRENT gains two points without a dimension-level regression. |

Estimated knowledge mix, **Expert : Activation : Redundant**: BASELINE approximately **75:17:8**; CURRENT approximately **78:15:7**.

## CURRENT findings

### Critical

None identified.

### Important

1. **Global writes can target a file the consumer never reads.**  
   **Lines:** `skills/ai-kit-spec-config/SKILL.md:173–177` and `:405–409`.  
   The instructions hardcode `~/.config/ai-kit/review-spec.toml`, but `cfg_global_path()` honors an absolute `XDG_CONFIG_HOME`. With a non-default XDG directory, the wizard checks and writes the wrong global location. Resolve the target through the consumer’s configuration-path logic and reuse it throughout detection, announcement, writing, and reporting.

2. **The workflow requires host-specific interaction tools without a fallback.**  
   **Lines:** `skills/ai-kit-spec-config/SKILL.md:51–60`, `:186–188`; `skills/ai-kit-spec-config/references/cli-model-selection.md:40–42`.  
   Mandatory `Bash` and `AskUserQuestion` calls, including the exact `multiSelect: true` interface, have no defined equivalent on hosts without those tools. Specify capabilities rather than mandatory tool names: use the host’s shell/question interface, or ordinary conversational multi-selection, while preserving consent and selection semantics.

3. **Excluding the current runtime prevents valid runtime/model configuration.**  
   **Lines:** `skills/ai-kit-spec-config/SKILL.md:186–193` and `:331–335`.  
   Step 2.2 excludes the hosting runtime, while Step 2.7 offers only Claude aliases or the session default. Consequently, an opencode or pi host cannot normally configure another model through that same runtime, even though the newly documented routing architecture supports that pair as a subprocess. Include every installed runtime in candidate selection, and offer the session default separately.

4. **EXECUTE ranking does not screen executable runtime/model pairs.**  
   **Lines:** `skills/ai-kit-spec-config/references/cli-model-selection.md:206–207` and `:272–276`.  
   The same candidate pool is ranked for both purposes, then list membership becomes the persisted `purpose`. This can advertise Grok/custom-command entries or Claude subprocess pairs as executors, although execution routing rejects them. A successful review-mode `check-reviewer` does not validate execution. Filter eligible **pairs/routes**, not merely model keys, before presenting EXECUTE choices; preserve the supported Claude-native exception.

5. **Predictable shared scratch files permit collisions and symlink-following writes.**  
   **Lines:** `skills/ai-kit-spec-config/SKILL.md:400–402`; `skills/ai-kit-spec-config/references/cli-model-selection.md:53`, `:90`, `:143`, `:311`.  
   Concurrent runs share filenames such as `/tmp/filtered-runtimes.json` and `/tmp/render-toml-stderr.txt`. One run can consume another’s candidates or diagnostics; ordinary redirection also follows existing symlinks. Allocate a private per-invocation temporary directory, retain its literal path across calls, and clean it up.

6. **The report can claim success or confirm a ladder that was not written.**  
   **Lines:** `skills/ai-kit-spec-config/SKILL.md:420–436`.  
   Absence of `WARNING:` is treated as sufficient for success, without requiring a successful command exit. Fatal failures can lack that prefix. Additionally, the writer removes rejected entries from the ladder, but the report is told to repeat the pre-write list “now confirmed as written.” Require successful completion, then derive the final policy and ladder from the saved TOML.

### Minor

1. **Some reporting instructions still describe the legacy schema.**  
   **Lines:** `skills/ai-kit-spec-config/SKILL.md:107` and `:451–454`.  
   `--check-only` asks for `key`/`cli` instead of `key`/`runtime`. The trust preview description covers only stored commands, although the implementation also displays runtime-backed runner argv. Update both descriptions and distinguish stdin prompt delivery from custom-command placeholders.

2. **Availability and permission claims exceed their evidence.**  
   **Lines:** `skills/ai-kit-spec-config/SKILL.md:286` and `:321–322`.  
   An unconfirmed read-only guarantee does not establish “normal write permissions”; the runner may still request restrictive permissions. Likewise, avoiding an external CLI does not establish that host-native work is never rate-limited. Describe the uncertainty and dependency difference rather than asserting either guarantee.

3. **The ranking snippet omits required runtime attribution for scored candidates.**  
   **Lines:** `skills/ai-kit-spec-config/references/cli-model-selection.md:224`, compared with `:234–237`.  
   Name-declared candidates print `via <runtime>`, but numbered candidates do not. Include the chosen/current runtime mappings directly in every scored output line.

4. **The weight explanation is stale.**  
   **Lines:** `skills/ai-kit-spec-config/references/cli-model-selection.md:265–268`.  
   The documented EXECUTE weights are `coding_index = 0.30` and `intelligence_index = 0.15`; the bundled defaults use **0.25** and **0.10**. Correct the explanation or avoid duplicating numeric defaults.

5. **Repeated rationale consumes context without adding decisions.**  
   **Lines:** `skills/ai-kit-spec-config/SKILL.md:42–64`; `skills/ai-kit-spec-config/references/cli-model-selection.md:272–283`.  
   Keep the operational invariant once, with a short reason. Move installation-history explanations and repeated legacy-purpose rationale out of the main execution path.

BASELINE 97/120
CURRENT 99/120
CRITICAL 0
IMPORTANT 6
