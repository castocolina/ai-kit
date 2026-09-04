# Model Discovery — Consumer-Side Purpose Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `ai-kit-spec-review` and `ai-kit-spec-execute-superpowers` each prefer reviewer entries whose `purpose` field matches their own role (review vs. execute), while staying fully backward-compatible with a `review-spec.toml` that has no `purpose` field anywhere.

**Architecture:** A `purpose` field (`"review"` | `"execute"` | `"both"` | absent) already lands on `[[reviewers]]` entries once Plan A's producer-side wizard writes it — this plan does not write the field, only reads it. Add ONE shared boolean predicate, `purpose_matches(purpose, wanted)`, in `ai_kit_spec/execute_selection.py` — this is the single source of truth for what "purpose matches" means, imported by both consumers. Wrap it in two shape-specific, never-empty-producing filters that each consumer's existing narrowing point actually needs: `filter_by_purpose` (execute-side, operates on the `candidates: list[dict]` shape `resolve_execute_candidates` already narrows, mirroring `filter_by_affinity`'s shape exactly) and `_filter_ladder_by_purpose` (review-side, operates on `quota.py`'s ladder-key-list shape — a genuinely different input shape, so it stays its own small function rather than forcing one shape onto the other, per this codebase's own stated convention, see `dispatch_injection.assemble_candidates`'s docstring). Both wrappers import and call `purpose_matches` — the predicate is shared; only the shape-adapting wrapper around it is duplicated.

**Also implements the design's `task_affinity_match = 2` ranking bonus (spec §6)** — Cross-Document Consistency finding from round 2: Plan A's wizard-time ranking (`score_candidates`) deliberately has no real plan/doc scope to apply this bonus to (see Plan A's Global Constraints), but `resolve_execute_candidates` (Task 1, this plan) DOES have a real `task_type` at the moment it actually matters — real dispatch time, for a real plan/document. A hard filter alone (what `filter_by_affinity` already did before this plan) is not the same signal as the spec's additive bonus: filtering can only ever include-or-exclude, never express "this one is a slightly better fit than that untagged one." Task 1 adds a same-context tie-break term to `resolve_execute_candidates`'s existing sort key, placed AFTER `top_n_keys` rank (round-3 CRITICAL fix: placing it BEFORE rank, as an earlier draft did, made the bonus effectively unbounded — able to outrank an explicit top_n_keys #1 pick with a dead-last, merely-tagged candidate, which contradicts the spec's own "capped at +15 combined" contract). Ordered after rank, an exact `task_affinity` match only ever breaks a genuine tie — two candidates the ladder itself treats as equally ranked (both explicit ties, or both absent from `top_n_keys` sharing the same fallback rank) — never overriding a real rank distance, giving the design's bonus a real, bounded, non-fabricated home instead of leaving it unimplemented or unbounded.

**Tech Stack:** Python 3.12, stdlib only, `unittest` (this repo's existing test framework — see `tests/test_ai_kit_spec.py`).

**Spec:** `docs/superpowers/specs/2026-09-02-model-discovery-curation-design.md` (§7 "Consumer-side changes")

**Does NOT depend on** `docs/superpowers/plans/2026-09-02-ai-kit-model-discovery-config.md` (Plan A, the producer side). This plan is independently executable and testable today against a hand-written `review-spec.toml`/`.aikit/review-spec.toml` with `purpose` set by hand on a couple of entries — no catalog, fetcher, or wizard change is a prerequisite.

## Global Constraints

- Never write to `review-spec.toml` in this plan — read-only consumption of `purpose`. Writing it is Plan A's Task 8 concern — `ai-kit-spec-config/SKILL.md` Step 2.2 (CLI-sourced entries, recorded at ranked-list confirmation time) and Step 2.7 (native entries, asked explicitly since they never go through Step 2.2's catalog/ranking flow) — see this plan's own Self-Review Notes below, which cite the same two steps.
- An entry with **no** `purpose` field means "no preference" — it must pass every purpose filter, exactly like `task_affinity`/`context_limit`'s existing absent-field behavior (spec §7, §5 schema note: "missing field never blocks... only doesn't contribute").
- If filtering by purpose would empty the candidate/ladder set entirely, fall back to the **unfiltered** set — never raise, never return an empty ladder because of a curation gap (spec §7, matches `filter_by_affinity`'s own existing fallback rule verbatim).
- **`ai-kit-spec-review`'s fallback specifically must emit a one-time warning** (spec §7: "falls back to the unfiltered ladder with a one-time warning — never a hard failure"): an execute-only-curated `review-spec.toml` silently reviewing with the wrong ladder is a real misconfiguration worth surfacing, not a benign degradation to hide. `resolve_reviewers` (Task 3) prints this warning to stderr exactly once per fallback occurrence it's called for (never suppressed across repeated calls within a run — this module has no long-lived state to dedupe across calls, and repeating the warning on every actual fallback is the honest behavior; "one-time" here means "once per `resolve_reviewers` call that actually falls back," not a global process-lifetime flag). The execute-side `filter_by_purpose` fallback (Task 1) has **no** such spec-mandated warning — only the review side does; do not add one there.
- **The GSD execute adapter (`ai_kit_spec_gsd.adapter`) is deliberately out of scope for `purpose`
  filtering in this plan** — Cross-Document Consistency finding, round-review: `assemble_candidates`
  in `ai_kit_spec_gsd/adapter.py` reads the same shared `[[reviewers]]` roster
  `dispatch_injection.assemble_candidates` (Task 2) reads, and could in principle thread `purpose`
  through the same way, but the design spec (`docs/superpowers/specs/2026-09-02-model-discovery-curation-design.md`
  §7 "Consumer-side changes") names only `ai-kit-spec-review` and `ai-kit-spec-execute-superpowers`
  as consumers of `purpose` — GSD is not listed. Plan A already declined to expand this design's
  scope to GSD on the producer side (see Plan A's own Global Constraints/Task 8 — GSD is never
  mentioned as a target there either); this plan follows that same precedent on the consumer side
  rather than introducing GSD support unilaterally. A GSD-side `purpose` filter, if wanted, is a
  separate future plan's decision, not an omission here.
  **Important caveat (Cross-Document finding):** "out of scope" describes intent, not mechanism.
  `ai_kit_spec_gsd/adapter.py:92` already calls
  `resolve_execute_candidates(candidates, None, required_context, {}, top_n_keys)` — the exact
  function Task 1 of this plan modifies to filter by `purpose` first. GSD therefore mechanically
  *inherits* the new purpose-narrowing behavior; it stays inert TODAY only because
  `assemble_candidates` in `ai_kit_spec_gsd/adapter.py` never populates a `"purpose"` key on its
  candidate dicts (so every candidate's `purpose` reads as absent/`None`, which `purpose_matches`
  treats as "no preference" — nothing is ever filtered out). This is a load-bearing coincidence,
  not a designed boundary: if a future change starts writing `purpose` into GSD's candidate dicts
  (e.g. by having GSD's adapter read the same `[[reviewers]]` `purpose` field
  `dispatch_injection.assemble_candidates` already reads), GSD's execute-candidate resolution
  would silently start being filtered by `purpose="execute"` with no code change to GSD itself
  and no test in this plan catching it. Task 4's full-suite regression check adds a test making
  this explicit — see Task 4, Step 1a below.
- **`task_affinity` has no producer anywhere in this design** — Cross-Document Consistency finding:
  neither this plan nor Plan A ever writes a reviewer entry's `task_affinity` field (Plan A's Task 8
  only ever asks about/writes `purpose`/`is_router`/`batch_mode`/`fallback_quota` — never
  `task_affinity`; `ai-kit-spec-config/SKILL.md` has no `task_affinity` question anywhere today).
  Task 1's `task_affinity_match` tie-break above is real, tested code — it fires correctly whenever
  a candidate happens to carry `task_affinity` — but with no producer, no `review-spec.toml`
  reviewer entry in practice ever has it set, so the tie-break is effectively **inert** until some
  later plan adds a `task_affinity` question to `ai-kit-spec-config` (the spec's own `task_affinity`
  is an "existing field, orthogonal axis" per its Section 4 note — predating this design, and not
  something a naming heuristic can safely infer the way `is_router`/`batch_mode` are inferred from
  a model id, since "frontend/backend/mixed" is a task-scope judgment, not a naming convention any
  model id encodes). This plan implements the bonus correctly and does not fabricate a producer to
  exercise it artificially — closing the producer gap is out of scope here.
- No new dependencies. Stdlib + this repo's existing modules only.
- Follow this repo's existing test style exactly: `unittest.TestCase` subclasses, one `class Test<Thing>` per function under test, method names `test_<behavior>` — see `tests/test_ai_kit_spec.py` (e.g. `TestFilterByAffinity` around line 2417) as the literal template.
- Every commit made while executing this plan ends with:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
  ```

---

## File Structure

| File | Responsibility |
|---|---|
| `skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py` | **Modify.** Add `purpose_matches` (shared predicate) and `filter_by_purpose` (candidate-dict filter, execute-side shape); call it from `resolve_execute_candidates`. Also add the `task_affinity_match` dispatch-time ranking tie-break (spec §6) to `resolve_execute_candidates`'s existing sort key. |
| `skills/ai-kit-spec-review/ai_kit_spec/quota.py` | **Modify.** Add `_filter_ladder_by_purpose` (ladder-key-list shape, imports and reuses `execute_selection.purpose_matches`) and call it inside `resolve_reviewers` before the existing single/double walk; `resolve_reviewers` gains a `warn_fn` parameter and emits a one-time warning on fallback (spec §7). |
| `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py` | **Modify.** `assemble_candidates` gains a `"purpose": r.get("purpose")` field on each candidate dict, so the new filter has something real to read. |
| `tests/test_ai_kit_spec.py` | **Modify.** New test classes/cases for all of the above, added next to the existing `TestFilterByAffinity`/`TestResolveExecuteCandidates`/`TestDispatchExecute`-family classes. |

No new files. All three production changes are small, additive edits to existing modules that already own the narrowing logic this design extends.

---

### Task 1: Shared purpose predicate + execute-side filter

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: nothing new — operates on the same `candidates: list[dict]` shape `filter_by_affinity`/`filter_by_context` already use (dicts with a `"key"` and whatever selection fields are present).
- Produces: `purpose_matches(purpose: str | None, wanted: str) -> bool` and `filter_by_purpose(candidates: list, purpose: str) -> list` — both importable as `execute_selection.purpose_matches` / `execute_selection.filter_by_purpose`. `resolve_execute_candidates` now filters by `purpose="execute"` as its first narrowing step, before `filter_by_affinity`/`filter_by_context` (unchanged signature, unchanged callers — `dispatch_injection._narrow_and_rank` needs no edit), AND ranks an exact `task_affinity == task_type` match ahead of a same-context-tier, same-`top_n_keys`-rank candidate (the design's `task_affinity_match` bonus, applied as a BOUNDED sort-key tie-break — ordered after rank, so it only breaks genuine rank ties, never overrides an explicit rank distance — rather than an additive score, since no 0-100 score exists at this dispatch point — see this plan's Architecture note).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ai_kit_spec.py`, immediately after the existing `TestFilterByAffinity` class (around line 2440):

```python
class TestFilterByPurpose(unittest.TestCase):
    def test_keeps_only_matching_purpose_when_any_match_exists(self):
        candidates = [{"key": "a", "purpose": "execute"},
                      {"key": "b", "purpose": "review"}]
        result = execute_selection.filter_by_purpose(candidates, "execute")
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_both_purpose_always_matches(self):
        candidates = [{"key": "a", "purpose": "both"},
                      {"key": "b", "purpose": "review"}]
        result = execute_selection.filter_by_purpose(candidates, "execute")
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_candidates_with_no_declared_purpose_always_pass_through(self):
        candidates = [{"key": "a", "purpose": None},
                      {"key": "b", "purpose": "execute"}]
        result = execute_selection.filter_by_purpose(candidates, "execute")
        self.assertEqual({c["key"] for c in result}, {"a", "b"})

    def test_no_matching_purpose_returns_all_unfiltered(self):
        candidates = [{"key": "a", "purpose": "review"}]
        result = execute_selection.filter_by_purpose(candidates, "execute")
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_missing_purpose_key_entirely_treated_as_no_preference(self):
        # pre-migration review-spec.toml: the field is absent, not None
        candidates = [{"key": "a"}]
        result = execute_selection.filter_by_purpose(candidates, "execute")
        self.assertEqual([c["key"] for c in result], ["a"])
```

Also update `TestResolveExecuteCandidates.test_full_pipeline_ranks_top_n_first` and
`test_unknown_context_ranks_after_confirmed_sufficient` — no change needed to their bodies
(their candidate dicts have no `"purpose"` key, which `filter_by_purpose` must treat as
no-preference and pass through unchanged), but add one new case confirming the purpose
filter is actually wired into the pipeline:

```python
    def test_purpose_filter_excludes_review_only_candidates(self):
        candidates = [
            {"key": "reviewer-only", "purpose": "review",
             "task_affinity": "backend", "context_limit": 1_000_000},
            {"key": "both-ok", "purpose": "both",
             "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type="backend", required_context=1000,
            affinity_table={}, top_n_keys=[])
        self.assertEqual([c["key"] for c in result], ["both-ok"])


class TestTaskAffinityMatchBonus(unittest.TestCase):
    # Cross-Document Consistency CRITICAL finding (round 3): the design's task_affinity_match=2
    # bonus (spec §6) is additive on a 0-100 score, capped at +15 COMBINED with every other
    # bonus -- it can never be large enough to flip an arbitrarily-large explicit rank
    # distance. Placed BEFORE top_n_keys rank in the sort key (an earlier draft's ordering),
    # the bonus was effectively unbounded: it could outrank a top_n_keys #1 candidate with a
    # last-place, merely-tagged one, which is not what "capped at +15" means. The bonus is
    # therefore ranked AFTER top_n_keys rank in the sort key below -- a genuine tie-break that
    # only ever matters among candidates the ladder itself treats as equally ranked (both
    # explicitly tied, or both absent from top_n_keys and sharing the same fallback rank),
    # never an override of a real, distinguishing rank.
    def test_exact_affinity_match_ranks_above_an_untagged_candidate_at_equal_top_n_rank(self):
        candidates = [
            {"key": "untagged", "context_limit": 1_000_000},
            {"key": "exact-match", "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type="backend", required_context=1000,
            affinity_table={}, top_n_keys=[])  # neither is in top_n_keys -- both share the
            # same fallback rank (len(top_n_keys)), so this IS a genuine rank tie.
        self.assertEqual([c["key"] for c in result], ["exact-match", "untagged"])

    def test_top_n_rank_still_wins_when_no_affinity_tag_is_involved(self):
        # The bonus never overrides an EXPLICIT top_n_keys preference between two candidates
        # that are equally untagged -- it only ever breaks a tie in favor of an exact match.
        candidates = [{"key": "a", "context_limit": 1_000_000},
                      {"key": "b", "context_limit": 1_000_000}]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type="backend", required_context=1000,
            affinity_table={}, top_n_keys=["b", "a"])
        self.assertEqual([c["key"] for c in result], ["b", "a"])

    def test_explicit_top_n_rank_always_wins_over_the_affinity_tie_break(self):
        # CRITICAL finding: the bonus is a BOUNDED tie-break only -- it must never override a
        # real, explicit ladder-rank distance (the spec's bonus is capped at +15 on a 0-100
        # score, never large enough to flip a top_n_keys preference between two DIFFERENTLY
        # ranked candidates just because one happens to carry a matching task_affinity tag).
        candidates = [
            {"key": "top-ranked-untagged", "context_limit": 1_000_000},
            {"key": "low-ranked-match", "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type="backend", required_context=1000,
            affinity_table={}, top_n_keys=["top-ranked-untagged", "low-ranked-match"])
        self.assertEqual([c["key"] for c in result], ["top-ranked-untagged", "low-ranked-match"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest tests.test_ai_kit_spec -k TestFilterByPurpose -k test_purpose_filter_excludes -k TestTaskAffinityMatchBonus -v`
Expected: FAIL — `AttributeError: module 'ai_kit_spec.execute_selection' has no attribute 'filter_by_purpose'`. (`pytest` is NOT installed in this repo's dev environment — `pyproject.toml`'s `dev` group has no `pytest` entry, confirmed via `python3 -m pytest --version` failing with `No module named pytest`. Every test-run command in this plan uses `python3 -m unittest <module> -k <pattern> -v`; `unittest`'s CLI has supported `-k` substring matching, repeatable for an OR, since Python 3.7.)

- [ ] **Step 3: Implement**

In `skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py`, add after the module docstring and before `filter_by_affinity`:

```python
def purpose_matches(purpose: str | None, wanted: str) -> bool:
    """A candidate's `purpose` ("review" | "execute" | "both" | None) matches a consumer's
    `wanted` role ("review" or "execute") when it's unset (no preference declared -- the
    field did not exist before this design, spec 2026-09-02), equals `wanted` exactly, or is
    the explicit "both" value. Shared by filter_by_purpose (execute-side, candidate-dict
    shape) and quota.py's own ladder-key-list-shaped filter -- one predicate, two shapes."""
    return purpose is None or purpose == wanted or purpose == "both"


def filter_by_purpose(candidates: list, purpose: str) -> list:
    """Same never-empty-on-curation-gap contract as filter_by_affinity: an entry with no
    `purpose` set always passes (no preference declared); if the matching-or-unset subset is
    empty, every candidate is returned unfiltered rather than starving the whole pipeline over
    a config that simply hasn't been curated with `purpose` yet."""
    matching = [c for c in candidates if purpose_matches(c.get("purpose"), purpose)]
    return matching if matching else list(candidates)
```

Then modify `resolve_execute_candidates` to filter by purpose first:

```python
def resolve_execute_candidates(candidates: list, task_type: str, required_context: int,
                                affinity_table: dict, top_n_keys: list) -> list:
    """Full candidate-narrowing pipeline. The result's ORDER is what a caller feeds to
    quota.py's resolve_ladder_pick (via candidates_to_ladder, below) for live-availability
    escalation -- this function only narrows and ranks, it never itself probes quota.

    Ranks confirmed-sufficient-context candidates before unknown-context ones -- "unknown" must
    never look like "fits great" (matches filter_by_context's own never-drop-on-missing-data
    rule: unknown is passed through, but ranked conservatively, not favorably).

    Purpose narrowing runs FIRST (2026-09-02 design): an execute consumer only wants
    purpose in {"execute", "both", None} candidates before task_affinity/context even apply.

    Ranking also applies the design's `task_affinity_match` bonus (spec §6) as a BOUNDED
    TIE-BREAK, ordered AFTER top_n_keys rank in the sort key (CRITICAL finding, round 3: an
    earlier draft placed it BEFORE rank, which is not "capped at +15" at all -- it let an
    exact-affinity, dead-last candidate outrank an explicit top_n_keys #1 pick, an unbounded
    override rather than a small additive bonus on a 0-100 score). Placed after rank, the
    bonus only ever matters among candidates the ladder itself treats as equally ranked --
    both explicitly tied, or (the common real case) both absent from top_n_keys and sharing
    the same fallback rank -- never a real, distinguishing rank difference. This is where that
    bonus actually applies -- it needs a real task_type, which only exists here, at real
    dispatch time, never at Plan A's generic wizard-time ranking (see that plan's Global
    Constraints)."""
    narrowed = filter_by_context(
        filter_by_affinity(filter_by_purpose(candidates, "execute"), task_type, affinity_table),
        required_context)
    rank = {key: i for i, key in enumerate(top_n_keys)}
    return sorted(
        narrowed,
        key=lambda c: (c.get("context_limit") is None,
                        rank.get(c["key"], len(top_n_keys)),
                        c.get("task_affinity") != task_type),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestFilterByPurpose -k TestResolveExecuteCandidates -k TestTaskAffinityMatchBonus -v`
Expected: PASS, all cases including the pre-existing two.

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py tests/test_ai_kit_spec.py
git commit -m "$(cat <<'EOF'
feat(ai-kit-spec): add purpose filter and task_affinity_match bonus to execute candidate resolution

Adds purpose_matches/filter_by_purpose (execute_selection.py), wired into
resolve_execute_candidates as the first narrowing step. Missing purpose
field (pre-migration config) always passes -- no behavior change for
existing review-spec.toml files without purpose set. Also implements the
design's task_affinity_match=2 ranking bonus (spec Section 6) as a
dispatch-time sort-key tie-break, ordered AFTER top_n_keys rank so it only
ever breaks a genuine rank tie and never overrides an explicit rank
distance (matching the spec's own "capped at +15 combined" contract) --
this is the one point in either plan where a real task_type actually
exists, closing a round-2 cross-document finding that the bonus had been
dropped entirely.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```

---

### Task 2: Thread `purpose` through `assemble_candidates`

**Files:**
- Modify: `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:152-157`
- Test: `tests/test_ai_kit_spec_superpowers.py`

**Interfaces:**
- Consumes: `execute_selection.filter_by_purpose` (Task 1, transitively via `resolve_execute_candidates` — no direct import needed here).
- Produces: `assemble_candidates(cwd, env, cfg_resolve_fn=cfg_resolve) -> tuple` now returns candidate dicts with a `"purpose"` key populated from `r.get("purpose")` — same pattern as the existing `"task_affinity"`/`"context_limit"` keys on the line directly above it.

- [ ] **Step 1: Write the failing test**

First locate the existing `assemble_candidates` test in `tests/test_ai_kit_spec_superpowers.py` (`rg "def test.*assemble_candidates"` — follow its existing fixture-config shape) and add a case asserting the new field round-trips. If the existing test class is `TestAssembleCandidates`, add:

```python
    def test_purpose_field_is_threaded_through_from_config(self):
        def fake_cfg_resolve(cwd, env):
            return {
                "policy": {"ladder": ["a"]},
                "reviewers": [
                    {"key": "a", "model": "m", "cli": "codex", "vendor": "openai",
                     "command": "codex exec -m {model}", "purpose": "execute"},
                ],
            }
        candidates, top_n_keys = dispatch_injection.assemble_candidates(
            "/fake/cwd", {}, cfg_resolve_fn=fake_cfg_resolve)
        self.assertEqual(candidates[0]["purpose"], "execute")

    def test_missing_purpose_field_comes_back_none(self):
        def fake_cfg_resolve(cwd, env):
            return {
                "policy": {"ladder": ["a"]},
                "reviewers": [{"key": "a", "model": "m", "cli": "codex", "vendor": "openai"}],
            }
        candidates, _ = dispatch_injection.assemble_candidates(
            "/fake/cwd", {}, cfg_resolve_fn=fake_cfg_resolve)
        self.assertIsNone(candidates[0]["purpose"])
```

(Match the exact fixture/import style already used by the surrounding tests in that file —
read the file first and place these methods in whichever `TestCase` class already covers
`assemble_candidates`; if none exists yet, create `class TestAssembleCandidates(unittest.TestCase):`
next to the other dispatch_injection test classes.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_ai_kit_spec_superpowers -k purpose -v`
Expected: FAIL with `KeyError: 'purpose'`.

- [ ] **Step 3: Implement**

In `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py`, modify `assemble_candidates`'s candidate-building loop (lines 152-157):

```python
        candidates.append({
            "key": r["key"], "model": r.get("model", ""), "cli": r.get("cli"),
            "vendor": r.get("vendor", ""), "command": r.get("command"),
            "task_affinity": r.get("task_affinity"), "context_limit": r.get("context_limit"),
            "purpose": r.get("purpose"),
            "effort": r.get("effort"), "service_tier": r.get("service_tier"),
        })
```

Update the function's own docstring line that currently reads `` `task_affinity`/`context_limit`
come back `None` for today's real ai-kit-spec-config output (Global Constraints) — `.get()`,
never `KeyError`. `` to also mention `purpose`:

```python
    """Reads the SAME shared candidate roster ai_kit_spec_gsd.adapter.assemble_candidates reads
    (review-spec.toml's [[reviewers]], design spec Section 4) -- the "superpowers has no config
    surface" constraint (Global Constraints) is about a superpowers-specific config file like
    GSD's .planning/config.json, which genuinely doesn't exist; it is not about this shared
    roster, which every ai-kit-spec-execute-* adapter reads identically. Duplicated here (not
    imported from ai_kit_spec_gsd.adapter) to keep the two sibling adapters independent -- neither
    should import the other's package. `task_affinity`/`context_limit`/`purpose` come back `None`
    for a pre-2026-09-02 ai-kit-spec-config output (Global Constraints) -- `.get()`, never
    `KeyError`."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_ai_kit_spec_superpowers -k purpose -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py tests/test_ai_kit_spec_superpowers.py
git commit -m "$(cat <<'EOF'
feat(ai-kit-spec-execute-superpowers): thread purpose field through assemble_candidates

Candidate dicts now carry purpose (None when unset), giving Task 1's
filter_by_purpose a real signal to narrow on via resolve_execute_candidates.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```

---

### Task 3: Review-side ladder filter in `resolve_reviewers`

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/quota.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `execute_selection.purpose_matches` (Task 1 — the shared predicate; imported here so "purpose matches" has exactly one definition across both consumers, per the Architecture note above). Otherwise operates on `config["reviewers"]`/`config["policy"]["ladder"]`, already `resolve_reviewers`'s own inputs.
- Produces: `_filter_ladder_by_purpose(reviewers: list, ladder: list, purpose: str) -> tuple[list, bool]` (private helper in `quota.py` — the ladder-key-list-shaped sibling of `execute_selection.filter_by_purpose`'s candidate-dict shape; kept as its own function because the input SHAPE differs, not because the matching LOGIC does — that logic is `purpose_matches`, imported, not reimplemented). Returns `(resulting_ladder, fell_back: bool)` — `fell_back` is `True` exactly when narrowing emptied the ladder and it returned the unfiltered one instead, giving the caller an unambiguous signal with no re-derivation needed. `resolve_reviewers` gains a `warn_fn=lambda msg: print(msg, file=sys.stderr)` parameter and calls it exactly once when `fell_back` is `True` (spec §7's explicit requirement — the review side, unlike the execute side, must not degrade silently).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ai_kit_spec.py`, in whichever `TestCase` class already covers
`resolve_reviewers` (`rg "class.*ResolveReviewers"` — likely near
`test_resolve_reviewers_uses_cfg_resolve_local_global_merge` around line 1512; if
`resolve_reviewers`'s own direct unit tests live in a different class than that
cfg_resolve-integration test, add these next to that class instead):

```python
    def test_resolve_reviewers_filters_ladder_to_review_purpose(self):
        config = {
            "policy": {"mode": "single", "ladder": ["execute-only", "both-ok"]},
            "reviewers": [
                {"key": "execute-only", "model": "m1", "vendor": "openai", "purpose": "execute"},
                {"key": "both-ok", "model": "m2", "vendor": "xai", "purpose": "both"},
            ],
        }
        result = quota.resolve_reviewers(config, quota={}, source_vendor="", cross_ai=True)
        self.assertEqual([r.key for r in result], ["both-ok"])

    def test_resolve_reviewers_falls_back_to_full_ladder_when_purpose_filter_empties_it(self):
        config = {
            "policy": {"mode": "single", "ladder": ["execute-only"]},
            "reviewers": [
                {"key": "execute-only", "model": "m1", "vendor": "openai", "purpose": "execute"},
            ],
        }
        result = quota.resolve_reviewers(config, quota={}, source_vendor="", cross_ai=True)
        self.assertEqual([r.key for r in result], ["execute-only"])

    def test_resolve_reviewers_missing_purpose_field_always_included(self):
        config = {
            "policy": {"mode": "single", "ladder": ["legacy-entry"]},
            "reviewers": [{"key": "legacy-entry", "model": "m1", "vendor": "openai"}],
        }
        result = quota.resolve_reviewers(config, quota={}, source_vendor="", cross_ai=True)
        self.assertEqual([r.key for r in result], ["legacy-entry"])

    def test_resolve_reviewers_warns_on_fallback_but_not_otherwise(self):
        warnings = []
        config_fallback = {
            "policy": {"mode": "single", "ladder": ["execute-only"]},
            "reviewers": [
                {"key": "execute-only", "model": "m1", "vendor": "openai", "purpose": "execute"},
            ],
        }
        quota.resolve_reviewers(config_fallback, quota={}, source_vendor="", cross_ai=True,
                                 warn_fn=warnings.append)
        self.assertEqual(len(warnings), 1)
        self.assertIn("purpose", warnings[0].lower())

        warnings.clear()
        config_no_fallback = {
            "policy": {"mode": "single", "ladder": ["both-ok"]},
            "reviewers": [{"key": "both-ok", "model": "m2", "vendor": "xai", "purpose": "both"}],
        }
        quota.resolve_reviewers(config_no_fallback, quota={}, source_vendor="", cross_ai=True,
                                 warn_fn=warnings.append)
        self.assertEqual(warnings, [])


class TestFilterLadderByPurpose(unittest.TestCase):
    def test_uses_the_shared_purpose_matches_predicate(self):
        # A direct check that this ladder-shaped filter is NOT a reimplementation of the
        # matching logic -- it must agree with execute_selection.purpose_matches exactly,
        # including for a value purpose_matches alone decides (e.g. "both").
        reviewers = [{"key": "a", "purpose": "both"}]
        result, fell_back = quota._filter_ladder_by_purpose(reviewers, ["a"], "review")
        self.assertEqual(result, ["a"])
        self.assertFalse(fell_back)
        self.assertTrue(execute_selection.purpose_matches("both", "review"))

    def test_reports_fell_back_true_only_when_narrowing_emptied_the_ladder(self):
        reviewers = [{"key": "a", "purpose": "execute"}]
        result, fell_back = quota._filter_ladder_by_purpose(reviewers, ["a"], "review")
        self.assertEqual(result, ["a"])  # unfiltered fallback
        self.assertTrue(fell_back)

    def test_reports_fell_back_false_when_nothing_needed_excluding(self):
        reviewers = [{"key": "a"}]  # no purpose set -- always passes, nothing excluded
        result, fell_back = quota._filter_ladder_by_purpose(reviewers, ["a"], "review")
        self.assertEqual(result, ["a"])
        self.assertFalse(fell_back)
```

(Uses the bare `quota` module import already present at the top of this test file per the
`from ai_kit_spec import (..., quota, ...)`-style block — confirm the exact existing import
list and add `quota` to it if it is not already there; `execute_selection` is already in that
same block per Task 1.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_ai_kit_spec -k test_resolve_reviewers_filters_ladder_to_review_purpose -k test_resolve_reviewers_falls_back_to_full_ladder -k test_resolve_reviewers_warns_on_fallback -k TestFilterLadderByPurpose -v`
Expected: FAIL — `test_resolve_reviewers_filters_ladder_to_review_purpose` fails because
`resolve_ladder_pick` with the unfiltered ladder `["execute-only", "both-ok"]` picks
`"execute-only"` first (no purpose filtering yet), not `"both-ok"`; the others fail with
`AttributeError`/`TypeError` since `_filter_ladder_by_purpose` and `resolve_reviewers`'s
`warn_fn` parameter don't exist yet.

- [ ] **Step 3: Implement**

In `skills/ai-kit-spec-review/ai_kit_spec/quota.py`: add `import sys` to the file's existing
top-level stdlib import group if it isn't already there, and `from ai_kit_spec.execute_selection
import purpose_matches` alongside `quota.py`'s existing `from ai_kit_spec.<module> import (...)`
block (this repo's established per-module-import convention — see Plan A's Task 7 Step 3 note
on `cli.py`'s identical layout; run `rg -n "^import|^from ai_kit_spec" skills/ai-kit-spec-review/ai_kit_spec/quota.py`
first to place both correctly among the existing lines, never mid-file next to the function
that uses them). Then add the helper above `resolve_reviewers`:

```python
def _filter_ladder_by_purpose(reviewers: list, ladder: list, purpose: str) -> tuple:
    """Ladder-key-list-shaped sibling of execute_selection.filter_by_purpose (candidate-dict
    shaped) -- same never-empty-on-curation-gap contract and the SAME matching predicate
    (purpose_matches, imported, never reimplemented here), just adapted to a different input
    shape (a plain ordered key list, not a list of candidate dicts) -- kept as its own small
    function because the shapes differ, not because the logic does. A key with no reviewer
    entry at all (should not happen given cfg_merge_reviewers' own invariants, but never raise
    on it) is treated as unset -- passes through, same as an entry that exists but omits
    `purpose`. Returns (resulting_ladder, fell_back) -- fell_back is True exactly when
    narrowing would have emptied the ladder and the unfiltered one was returned instead, so
    the caller (resolve_reviewers) never has to re-derive that from the result alone."""
    purpose_by_key = {r["key"]: r.get("purpose") for r in reviewers if "key" in r}
    matching = [k for k in ladder if purpose_matches(purpose_by_key.get(k), purpose)]
    if matching:
        return matching, False
    return list(ladder), bool(ladder)
```

Then modify `resolve_reviewers` to apply it once, right after `ladder`/`reviewers` are read,
adding the `warn_fn` parameter (defaulting to a real stderr print, matching this repo's
existing convention of an injectable I/O parameter with a real default rather than a silent
no-op — see `local_secrets`/`model_sources`' own `fetch_fn=`/`run_fn=` pattern elsewhere in
this design):

```python
def resolve_reviewers(config: dict, quota: dict, source_vendor: str, cross_ai: bool,
                       warn_fn=lambda msg: print(msg, file=sys.stderr)) -> list:
    """... (existing docstring, plus:) Narrows `ladder` to purpose in {"review", "both", None}
    first (2026-09-02 design, spec Section 7) -- falls back to the full ladder if that empties
    it, and calls `warn_fn` exactly once in that fallback case (spec Section 7: "falls back to
    the unfiltered ladder with a one-time warning") since an execute-only-curated config
    silently reviewing with the wrong ladder is a real misconfiguration worth surfacing. No
    warning when nothing was excluded (a ladder with no purpose-tagged entries at all,
    including today's every pre-migration review-spec.toml, behaves identically to before this
    change -- no fallback ever triggers for it, so nothing to warn about)."""
    if not cross_ai:
        return [NO_CONFIG_FALLBACK]
    policy = config.get("policy", {})
    mode = policy.get("mode", "single")
    ladder = policy.get("ladder", [])
    reviewers = config.get("reviewers", [])
    ladder, fell_back = _filter_ladder_by_purpose(reviewers, ladder, "review")
    if fell_back:
        warn_fn("ai-kit-spec-review: no reviewer entry matches purpose='review' in the "
                "configured ladder -- falling back to the full, unfiltered ladder. Curate "
                "`purpose` on your review-spec.toml reviewer entries to fix this.")
    if mode == "double":
```

(Everything below `if mode == "double":` is unchanged — both branches already read the
now-narrowed `ladder` variable.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestFilterByPurpose -k TestFilterLadderByPurpose -k test_resolve_reviewers -v`
Expected: PASS, including every pre-existing `test_resolve_reviewers_*` case (a ladder with
no `purpose` fields anywhere behaves identically to before this change, and emits no warning).

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/quota.py tests/test_ai_kit_spec.py
git commit -m "$(cat <<'EOF'
feat(ai-kit-spec-review): filter reviewer ladder to review-purpose entries

resolve_reviewers narrows its ladder to purpose in {review, both, None}
(via the shared execute_selection.purpose_matches predicate) before the
existing single/double walk, falling back to the unfiltered ladder with
a one-time warning (spec-mandated, review side only) if narrowing would
empty it. No behavior change, and no warning, for a review-spec.toml
with no purpose fields set.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```

---

### Task 4: Full-suite regression check

**Files:**
- None modified — verification only.

**Interfaces:**
- Consumes: everything from Tasks 1-3.
- Produces: nothing new in production code — this task's deliverable is a passing full test run, confirming no other caller of `resolve_execute_candidates`, `assemble_candidates`, or `resolve_reviewers` broke. Step 1a below adds one regression test (test file only) locking in the GSD purpose-inertness caveat from the Global Constraints above.

- [ ] **Step 1a: Add a regression test locking in GSD's current purpose-inertness**

`ai_kit_spec_gsd/adapter.py`'s `select_candidate` (or whichever of its callers ultimately
reaches `resolve_execute_candidates`) calls the SAME `resolve_execute_candidates` Task 1
modifies — GSD mechanically inherits the new purpose filter (see Global Constraints above);
it only stays unaffected today because GSD's own `assemble_candidates` never sets a
`"purpose"` key on its candidate dicts. Add a test to `tests/test_ai_kit_spec_gsd.py` (find
the existing test module covering `adapter.py`'s candidate resolution — `rg "def test.*select_candidate|resolve_execute_candidates" tests/test_ai_kit_spec_gsd.py`) that pins this
down explicitly, so a future change that starts populating `purpose` in GSD's candidates
doesn't silently start filtering GSD's execute selection with no test catching it:

```python
    def test_purpose_filter_is_inert_for_gsd_while_purpose_stays_unset(self):
        # GSD's candidates never carry a "purpose" key (adapter.py's assemble_candidates
        # does not set one) -- purpose_matches treats an absent field as "no preference",
        # so resolve_execute_candidates' new purpose-narrowing step (Task 1) must never
        # exclude a GSD candidate on that basis alone. This pins down the load-bearing
        # coincidence noted in this plan's Global Constraints: if GSD's adapter ever starts
        # writing "purpose" onto its candidate dicts, this test's assumption (both
        # candidates pass through unfiltered) breaks and must be revisited deliberately,
        # not silently.
        candidates = [
            {"key": "review-only-tagged", "purpose": "review", "context_limit": 1_000_000},
            {"key": "gsd-style-untagged", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type=None, required_context=1000,
            affinity_table={}, top_n_keys=[])
        # Both pass -- GSD's real candidates never carry "purpose" at all, matching the
        # untagged shape here; a purpose="review"-tagged one is included too because
        # matching would otherwise empty the set (filter_by_purpose's own never-empty
        # fallback), which is exactly the degradation mode this test is pinning down.
        self.assertEqual({c["key"] for c in result},
                          {"review-only-tagged", "gsd-style-untagged"})
```

Run: `python3 -m unittest tests.test_ai_kit_spec_gsd -k test_purpose_filter_is_inert_for_gsd -v`
Expected: PASS (proves today's behavior matches the Global Constraints' claim). If this
ever starts failing after a future GSD change populates `purpose`, that is the trigger to
revisit this Global Constraints note and decide deliberately whether GSD should now be a
purpose-aware consumer — not something to silently work around.

- [ ] **Step 1: Run the full test suite**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest discover -s tests -v`

Expected: PASS, 0 failures. Pay particular attention to any test in
`TestDispatchExecute`, `TestResolveExecuteCandidates`, or the `resolve_reviewers`-covering
class — those exercise the three functions this plan touched most directly.

- [ ] **Step 2: If anything fails, fix forward**

A failure here means a caller elsewhere in the codebase constructs a candidate/reviewer
dict this plan didn't anticipate (e.g. a fixture missing `"purpose"` entirely combined with
a mock that doesn't tolerate an extra dict key). Since `filter_by_purpose`/
`_filter_ladder_by_purpose` both treat "field absent" as "no preference" by construction,
a real failure here is a genuine gap in this plan's Task 1-3 implementation, not a flaky
test — fix the implementation, not the test, unless the test itself is asserting
pre-2026-09-02 behavior that the spec explicitly changes (re-read spec §7 before altering
any assertion).

- [ ] **Step 3: Commit only if Step 2 required a fix**

```bash
git add -A
git commit -m "$(cat <<'EOF'
fix(ai-kit-spec): address full-suite regression from purpose filtering

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```
(Skip this step entirely if Step 1 passed clean — no empty commits.)

---

## Self-Review Notes

**Spec coverage (§7):** "ai-kit-spec-review filters... purpose in {review, both}... falls back
to the unfiltered ladder with a one-time warning" → Task 3, including the warning (a prior
draft covered the filter but dropped the warning — fixed). "ai-kit-spec-execute-superpowers
filters... purpose in {execute, both}... reusing filter_by_affinity/filter_by_context... one
more filter" → Tasks 1-2. "Degradation: exactly like task_affinity/context_limit today — an
absent field means no preference, never a rejection" → covered by every task's explicit
"absent purpose passes through" test case and the shared fallback-to-unfiltered rule. All of
§7 is covered; §1-6, §8-10 belong to Plan A, EXCEPT §6's `task_affinity_match` bonus, which
this plan's Task 1 implements at dispatch time (round-2 cross-document fix — see Task 1's
Architecture note and `TestTaskAffinityMatchBonus`) since Plan A's wizard-time ranking has no
real plan/doc scope to apply it to.

**Cross-document note on `purpose` absence:** this plan's "absent purpose passes every filter"
rule (Global Constraints) is a legacy-compatibility default, not an invitation for a producer
to leave `purpose` unset on a brand-new entry. Plan A's Task 8 writes an explicit `purpose` for
every entry it newly registers — CLI-sourced (Step 2.2) AND native (Step 2.7) alike (round-2
fix: an earlier draft of Plan A left native entries with no `purpose` at all, which this plan's
own absent-means-both-roles fallback would then have silently applied to an entry the user
never actually confirmed for both roles). This plan's filters still treat absence correctly
either way — the fix lives entirely on the producer side, this plan needed no code change for
it, only this note for anyone auditing the two plans together.

**Placeholder scan:** No TBD/TODO; every step has real code or a real, runnable command.

**Type consistency:** `purpose_matches(purpose: str | None, wanted: str) -> bool` and
`filter_by_purpose(candidates: list, purpose: str) -> list` names match their call sites in
`resolve_execute_candidates` exactly; `_filter_ladder_by_purpose(reviewers: list, ladder: list, purpose: str) -> tuple[list, bool]` (returning `(ladder, fell_back)`, not a bare list — a prior draft had this returning a bare list with no way for the caller to know whether a fallback happened, which is exactly what made the one-time warning impossible to implement correctly) matches its one call site in `resolve_reviewers` exactly, including the new `warn_fn` parameter both the direct call and its own tests exercise. Both `_filter_ladder_by_purpose` and `filter_by_purpose` import and call `purpose_matches` rather than reimplementing its logic — one predicate, two shape-adapting wrappers. `resolve_execute_candidates`'s signature is unchanged by the `task_affinity_match` tie-break (Task 1) — it's an added sort-key term, not a new parameter, so every existing caller keeps working unmodified. No signature drift between tasks.
`pytest` is not installed in this repo — every test-run command in this plan uses `python3 -m unittest <module> -k <pattern> -v` instead (Global Constraints).
