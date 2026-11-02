## Verdict

**CURRENT improves operational safety, but still has two Important correctness gaps.** It adds explicit replacement consent, private scratch files, exit-status handling, accurate reporting of the written ladder, and clearer runtime/model routing.

This was a **read-only, static review** of both complete skill packages, with relevant behavior checked against their sibling Python implementations. No commands or live probes were executed.

Both follow a **Process + Tool** pattern:
- **BASELINE:** 361-line `SKILL.md`; one 317-line reference.
- **CURRENT:** 491-line `SKILL.md`; one 344-line reference.
- Both are predominantly repository-specific expert knowledge, not general tutorials. Repeated invariants and historical explanations are their main token-efficiency weakness.

## Dimension scores

Locations below are relative to each version’s `ai-kit-spec-config/` directory.

| Rubric dimension | BASELINE | CURRENT | Evidence and rationale |
|---|---:|---:|---|
| **D1: Knowledge Delta** | **17/20** | **17/20** | Both supply valuable catalog reconciliation, provenance, quoting, timeout, and trust rules. CURRENT adds runner-specific knowledge, but repeats substantial `purpose` explanations across `SKILL.md:309–311`, `350–358`, `393–408`, and the reference. |
| **D2: Mindset + Appropriate Procedures** | **13/15** | **14/15** | Both frame selection around quota reliability and purpose fit (BASELINE `SKILL.md:144–152`; CURRENT `148–156`). CURRENT better distinguishes runtime/model pairs, session defaults, and per-call routing (`315–348`). |
| **D3: Anti-Pattern Quality** | **14/15** | **14/15** | Both have specific, reasoned prohibitions: no guessed vendor attribution, ungrouped catalogs, untested candidates, or implicit trust. CURRENT correctly replaces stored command templates with runner-owned argv (`SKILL.md:61–78`). Some prohibitions repeat later instructions. |
| **D4: Specification Compliance / Description** | **15/15** | **14/15** | Both have valid frontmatter and clear WHAT/WHEN/keyword coverage (`SKILL.md:1–4`). CURRENT’s “`--local` … without asking” wording conflicts with its mandatory replacement gate. |
| **D5: Progressive Disclosure** | **13/15** | **13/15** | Both explicitly require the model-selection reference only for selected CLIs and prohibit loading irrelevant profiles (BASELINE `SKILL.md:185–210`; CURRENT `201–234`). However, considerable CLI detail and repeated rationale remain in the always-loaded body; CURRENT is close to 500 lines. |
| **D6: Freedom Calibration** | **9/15** | **13/15** | BASELINE tightly constrains identifiers but leaves existing local files unprotected and uses shared `/tmp` files (`SKILL.md:167–169`, `299–315`). CURRENT materially improves fragile operations through replacement consent, unique scratch storage, atomic writing, and failure gates (`39–48`, `175–181`, `413–443`). |
| **D7: Pattern Recognition** | **9/10** | **9/10** | Both implement a coherent locate → detect → ask → write → report process with appropriately constrained tool operations. Repetition makes them less compact than an exemplary Process/Tool hybrid. |
| **D8: Practical Usability** | **9/15** | **11/15** | BASELINE can announce success without checking write failure and can repeat a pre-write ladder after entries were rejected (`SKILL.md:319–345`). CURRENT repairs those paths (`437–472`) and provides host-tool fallbacks (`17–21`), but global-path resolution and check-only identity remain incorrect in supported scenarios. |
| **Total** | **99/120 — B** | **105/120 — B** | CURRENT is a meaningful improvement, not yet free of material findings. |

## CURRENT findings

### Critical

**None identified.**

### Important

1. **Global configuration is resolved differently from the consumer.**  
   **Lines:** `skills/ai-kit-spec-config/SKILL.md:171–173`, `419–425`  
   The wizard always selects `~/.config/ai-kit/review-spec.toml`. The actual consumer uses an absolute `XDG_CONFIG_HOME` when set, through `cfg_global_path()` in `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:268–291`. Consequently, `--global` can successfully write a file that review dispatch never reads, while existing-config detection and `--check-only --global` inspect the wrong file.  
   **Fix:** Resolve the global target through `cfg_global_path()` and reuse that exact result throughout detection, consent, writing, and reporting.

2. **Filtering merged probe results by key does not establish which reviewer was tested.**  
   **Lines:** `skills/ai-kit-spec-config/SKILL.md:106–125`  
   A trusted local config can override a global reviewer under the same key. For example, global key `k` can identify model A while the merged config probes model B under `k`; the prescribed filter then reports B’s availability as A’s. Likewise, an untrusted local entry can share a global key and incorrectly receive that global entry’s result. The existing “missing key” handling does not catch either collision.  
   **Fix:** Verify the effective entry’s identity against the raw selected entry before attributing a result. Report overridden or ignored entries as unprobed rather than accepting key equality alone.

### Minor

1. **EXECUTE scoring retains metadata from excluded runtimes.**  
   **Lines:** `skills/ai-kit-spec-config/references/cli-model-selection.md:208–228`  
   `via()` removes review-only and runner-less runtime names, but the entries passed to `score_candidates()` retain those runtime mappings. Context scoring and displayed `ctx` can therefore use a larger window available only through a runtime omitted from the EXECUTE list.  
   **Fix:** Prune each entry’s runtime mappings for the purpose before scoring and calculating context.

2. **The description overpromises prompt-free `--local` behavior.**  
   **Line:** `skills/ai-kit-spec-config/SKILL.md:3`  
   “Force local write without asking” contradicts the replacement consent required at lines `175–181`.  
   **Fix:** Say that the flag skips the **location question**, not replacement consent.

3. **Repeated invariants consume unnecessary context.**  
   **Lines:** `skills/ai-kit-spec-config/SKILL.md:309–311`, `350–358`, `393–408`  
   The requirement for explicit `purpose`, including its legacy-default explanation, is repeatedly restated and repeated again in the reference.  
   **Fix:** Keep the full rationale once and use short carry-forward reminders elsewhere. Move detailed CLI-specific history into selectively loaded profiles.

BASELINE 99/120
CURRENT 105/120
CRITICAL 0
IMPORTANT 2
