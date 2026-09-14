---
phase: 12
reviewers: [opencode]
reviewed_at: 2026-09-14T13:09:14Z
plans_reviewed: [12-01-PLAN.md, 12-02-PLAN.md, 12-03-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 12

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
(none)
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

Using the review brief as-is: I'll ground each plan against live source, starting with `_sl` and the shared parsers the cycle-1 HIGH depends on.
`_sl` matches the variable-then-pass shape. Next I'll check the shared parsers, the containment guard, and whether the cycle-1 ledger edits actually landed in the plan bodies.
Using the review brief against live source. Cycle-1 HIGH is checked against `tests/test_arch.py:605-611`.

## 12-01

**Summary.** Wave-1 plan still matches the live shared package and Makefile fixtures. Cycle-1 MEDIUMs on anchoring/non-vacuity and the `target`-key prohibition are in the task body, not only the ledger. SC1/SC2 are achievable. Residual risk is leftover "two calls" wording and a files list that omits Task 2's shared-suite file.

**Strengths**
- D-A3 prohibition matches `build_remediation` at `skills/_shared/ai_kit_rules_common/remediation.py:86` (`finding.get("target", finding.get("category"))`) and the Makefile sibling's `target` field at `makefile_checker.py:463`.
- Ordered-reader addition copies the existing pair at `makefile_parse.py:33-67`; `_TARGET_HEADER_RE` at line 16 already yields declaration order; `parse_makefile_targets` at 19-30 currently throws that order away in a set.
- D-A4's two-sided gate is in the decision text (found → AST-only finding; missing → SC4 recommendation text), so an executor following D-A4 will not hide SC4.
- Positive fixture is live: `Makefile:61` `arch-test:`, `Makefile:66` `test: … arch-test`. Skill directory does not exist yet, so the `test ! -e` precondition holds.
- `__init__.py` pattern is copyable from `skills/ai-kit-project-rules-precommit/ai_kit_project_rules_precommit/__init__.py:7-27` (realpath, named ImportError, `sys.path.append`).

**Concerns**
- **LOW — cycle-1 leftover.** `key_links` still says 12-02 "extends this function by exactly two calls." D-A4 now says one *call* on the found branch and recommendation *text* on the missing branch. Tasks are correct; the link is not.
- **LOW — `files_modified` omits `tests/test_ai_kit_rules_common.py`**, which Task 2 edits. Task `<files>` is right; frontmatter is not.
- **LOW — cycle-1 "one commit"** still unsplit. Ledger's "observability via SUMMARY" is real; inversion risk remains.

**Cycle-1 ledger vs body**
| Finding | Verdict | Body evidence |
|---|---|---|
| MEDIUM non-vacuity/`fullmatch`+$ | **Addressed** | D-A1 one mechanism; Task 2 mutation per mechanism; T-12-05 names the hollow check |
| MEDIUM `target` key | **Addressed** | Prohibition paragraph; tracer asserts key absence and distinct remediate ids |
| LOW breadth cap | **Addressed** | D-A2 visited + depth 8 + breadth 512; fall through to (iii) |
| suggestion ordered reader | **Addressed** | Shared `parse_makefile_targets_ordered`, not a private scan |
| LOW one-commit | **Partial** | Not split; SUMMARY must record the observed mutation |

**Suggestions**
- Change the key_link from "two calls" to "one append in the found branch + recommendation text on the missing finding."
- Add `tests/test_ai_kit_rules_common.py` to plan-level `files_modified`.

**Risk Assessment.** **LOW.** Shared-API claims check out. Cycle-1 schema/anchoring pins are in the tasks. No new HIGH.

## 12-02

**Summary.** Cycle-1 HIGH is **FULLY RESOLVED**, verified against live `_sl`. The rewritten CLEAN/NAMED fixtures are the same one-level join-then-pass shape, not a cosmetic rename. SC3/SC4 and D-01/D-02 are executable. One leftover Interfaces sentence still says "two calls inside that branch."

**Cycle-1 HIGH — FULLY RESOLVED**

Live `tests/test_arch.py:605-611`:

```605:611:tests/test_arch.py
    def _sl(self):
        sl_path = os.path.join(_TOOLS, "status-line.py")
        spec = importlib.util.spec_from_file_location("status_line_inv", sl_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod
```

Parse side is `_parse("status-line.py")` at `tests/test_arch.py:87` / `374-375`. Unrelated load is `setup.py` at `34-40`.

Tracer `byname` (`12-02-PLAN.md` ~463-466):

| Live `_sl` | NAMED fixture |
|---|---|
| `sl_path = os.path.join(_TOOLS, "status-line.py")` | `q = os.path.join(SRC, "target_mod.py")` |
| dir Name + filename string in `join` | same |
| `spec_from_file_location(alias, path_name)` | same (`target_alias_zz`, `q`) |
| alias ≠ module (`status_line_inv` → `status-line-inv`) | `target_alias_zz` → `target-alias-zz` |
| `module_from_spec` + `exec_module` | same |

Without execute-side name resolution, the only inline literal is the alias; intersection with `target_mod`/`status-line` is empty. Tracer requires `inm.count(AST)==1`, module named, alias absent. CLEAN uses the same shape on `helper_mod.py` and must *not* flag — that is D-01, not a blanket scan.

`sys.modules[spec.name] = mod` at line 609 is extra in live code; D-A8 does not use it. Not a hole.

SC1 live wording at `ROADMAP.md:369` is existence/chaining only. An `arch-test-ast-only` hit on this repo does not break SC1.

**Strengths**
- Containment copy matches `ai_kit_project_rules_agents/cli.py:65-69` (`realpath` both sides, `os.sep` prefix, then isfile at 70). Sibling-prefix fixture is the case a bare `startswith` accepts.
- Reason enum is pinned (`not_discoverable` / `not_python` / `unparseable` / `no_parse_call`) and the tracer maps fixture → token.
- Canonical-tool keys match `stack_detect.py:15-26` (`go`, `python`, `node`, `java`, `rust`).
- `auto_apply = not finding.get("advisory", False)` at `remediation.py:96` is why advisories must set `advisory: True`.
- D-01 correction is honest vs live `_sl`; prohibition on narrowing the checker is load-bearing.

**Concerns**
- **LOW — cycle-1 leftover.** Interfaces still: "This plan appends two calls inside that branch." Task 1 appends one AST-only call on the found branch; Task 2 extends the missing-target recommendation. Must-haves/D-A4/Task 2 are correct; Interfaces can still mislead a skim.
- **LOW — `fails_when` "byte-for-byte the shape."** Same dataflow, not the same bytes (`q` vs `sl_path`, no `sys.modules`). Pattern match is what matters; the phrase overclaims.

**Cycle-1 ledger vs body**
| Finding | Verdict |
|---|---|
| HIGH `_sl` fixture | **FULLY RESOLVED** (live source + tracer `byname`) |
| MEDIUM D-A4 vs SC4 | **Addressed** in D-A4/must-haves/Task 2; Interfaces sentence not updated |
| MEDIUM reason enum | **Addressed** |
| LOW norm + two-level helper in tracer | **Addressed** (`inr`, `idp`) |
| LOW containment `realpath`+`os.sep` | **Addressed** + sibling fixture |

**Suggestions**
- Rewrite Interfaces to: one call in the found branch (AST-only); SC4 text on the missing-target finding.
- Drop "byte-for-byte"; keep "same join-then-pass dataflow as `_sl`."

**Risk Assessment.** **LOW.** Cycle-1 HIGH is closed against source. Remaining issues are stale sentences, not fixture holes.

## 12-03

**Summary.** Docs/closeout plan is still the right wave-3 scope: SKILL.md, README row, skill-judge evidence, naming confirmation, SC5, append-only D-01 correction. Cycle-1 MEDIUM on limits-softening is in Task 2 and `<output>` (verbatim post-loop quote). No code surface. House-style opener `Scouting claim corrected by Phase 12:` matches `ROADMAP.md:326` / `REQUIREMENTS.md:76-77`.

**Strengths**
- Doc-vs-code gates (`DOC-MATCHES-CODE-OK`, `TWO-SUBCOMMANDS-OK` on the runnable surface) match T-12-16.
- Cache/classify scan is scoped to fenced blocks + entrypoint lines, so the required "no research/cache step" sentence is allowed.
- SC5: note already in all three PLAN objectives; stub at `ROADMAP.md:494-514` is compared to `42c8f8e`; plan does not touch `ROADMAP.md`.
- D-01 correction constraints (opener, inside D-01, cite 374 and 605-611, SC1 unaffected) match live file layout.
- Rename is confirm-only; Phases 13-15 name this skill.

**Concerns**
- **LOW — residual description floor.** Cycle-1 asked to bound routing by content, not `len>=120`. Content assert (`arch-test` / `architecture`) is in; `>=120` remains. Action says report rather than pad — residual padding temptation, not a revert.
- **LOW.** Phase 999.3 stub has no dated 2026-09-13 resolution note; that framing lives on Phase 12's goal (`ROADMAP.md:364`). 12-03 should quote Phase 12's goal / 12-02-SUMMARY, not a missing stub date. Does not break the byte-identity check.

**Cycle-1 ledger vs body**
| Finding | Verdict |
|---|---|
| MEDIUM judge-loop limits | **Addressed** (verbatim post-final quote + `SKILL-SHAPE-OK` after each iter) |
| LOW `git log -3` | **Addressed** (`git log -1 --format=%H --` this PLAN) |
| LOW description padding | **Mostly addressed** (content bound + floor kept) |
| LOW `cache-update` whole-doc scan | **Addressed** (command-surface scan) |

**Suggestions**
- Point Task 3's "dated 2026-09-13 note" at Phase 12's goal paragraph, or at 12-02-SUMMARY, not the unchanged 999.3 stub.

**Risk Assessment.** **LOW.** Process-heavy on purpose. Cycle-1 limits backstop is in the task, not only the ledger.

---

## Cross-plan

Cycle-1 HIGH on 12-02 is **FULLY RESOLVED** against `tests/test_arch.py:605-611`. All six cycle-1 MEDIUM/LOW items are in the plan bodies except: (1) 12-02 Interfaces / 12-01 key_links still say "two calls inside the found branch" — **partial leftover of the D-A4 MEDIUM**, tasks are correct; (2) 12-01 one-commit LOW stays partial by design.

No new HIGH from the cycle-1 edits. New issues are LOW stale sentences.

SC split still holds: 12-01 SC1/SC2 (`Makefile:61,66`, `ROADMAP.md:369-370`), 12-02 SC3/SC4, 12-03 SC5. Skill dir absent; Phases 9-11 artifacts the plans copy are present.

**Overall risk: LOW.** Ready to execute. Optional: fix the two leftover "two calls" sentences before wave 1 so a cheap executor cannot re-hide SC4.

---

## Consensus Summary

Single-reviewer cycle (opencode only) — no cross-reviewer consensus to synthesize. All findings below are from the single opencode (xai/grok-4.6, reasoning=high) pass, which re-verified the cycle-1 HIGH and all six cycle-1 MEDIUM/LOW findings against live source (`tests/test_arch.py:605-611`, `makefile_parse.py`, `remediation.py`, `stack_detect.py`) rather than re-reading plan prose.

### Agreed Strengths
N/A — single reviewer.

### Agreed Concerns
N/A — single reviewer.

### Divergent Views
N/A — single reviewer.
