"""Shared per-language tool-knowledge catalog for the ai-kit rules-checker
skill family (11-CONTEXT D-01/D-02/D-03).

Lives here rather than inside `ai-kit-project-rules-precommit` because D-01
converges per-language tool knowledge into ONE catalog so a correction
benefits every checker at once: Phases 12-15 classify their own findings
against these same six names, and a second, independently-maintained copy
inside any one skill would be exactly the split-ownership defect D-01
exists to prevent.

Everything this module carries beyond the six category names/definitions is
LOCKED, already-researched content transcribed verbatim from
`docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`'s
"Tooling taxonomy (cross-language, generalized)" section -- never
re-derived, never re-litigated (D-03). What this module adds over plan
11-01's vocabulary-only stub:

- `BASELINE_STACKS`: the design spec's "Baseline stacks by language" table
  (five stacks x six categories), transcribed per this module's own
  five transcription rules (see below). The single hand-written tool
  dataset.
- `TOOL_CATEGORY_INDEX`: the tool-name-to-category reverse index, DERIVED
  from `BASELINE_STACKS` at import time (D-T1) plus four cited
  supplementary entries (D-T7) -- never a second hand-typed copy.
- `AMBIGUOUS_TOOL_DEFAULTS`: D-T3's small, cited defaults map for a bare
  tool name whose baseline entries exist only in suffixed forms (today:
  bare `ruff` -> `linting`).
- `OUT_OF_TAXONOMY_GROUPS`: D-T4's marker groups (test-runner ids, standard
  `pre-commit-hooks` hygiene ids) that are a real third outcome, not a gap.
- `MAKEFILE_CATEGORY_ALIAS`: D-02's reconciliation between these
  six taxonomy names and the sibling `ai-kit-project-rules-makefile`
  skill's five `RESEARCH_CATEGORIES` names. `type-checking` maps to `None`
  -- recorded as a fact (there is no `REQUIRED_STATIC_TARGETS` entry for
  type-checking today), never papered over with an invented target name. A
  drift guard in `tests/test_ai_kit_rules_common.py` pins this table's five
  mapped values against the sibling's real `RESEARCH_CATEGORIES` tuple
  (read via `ast`, never imported).
- `REDUNDANT_VS_COMPLEMENTARY_PAIRS`: D-03's ten-row "Confirmed
  redundant-vs-complementary pairs" table, transcribed verbatim, plus
  `resolve_tool_category` (D-T7) and an import-time reachability guard so
  every pairs-table tool-token member is answerable by this catalog.

Deliberately NOT carried here: the design spec's "Fast-vs-slow ordering
guidance" paragraph. It already ships as the sibling
`ai-kit-project-rules-makefile` skill's own speed-tier table
(`ai_kit_project_rules_makefile.makefile_checker._SPEED_TIERS` and
`speed_tier()`) -- duplicating it here would be the second half of D-03
silently dropped rather than placed. Stated here so a reader can see the
decision was made, not missed.
"""

from __future__ import annotations

from typing import cast

TAXONOMY_CATEGORIES = (
    "formatting",
    "type-checking",
    "linting",
    "security",
    "duplicate-code",
    "dead-code",
)

TAXONOMY_DEFINITIONS = {
    "formatting": (
        "Deterministic, opinionated code-shape rewriting. No semantic judgment."
    ),
    "type-checking": (
        "Static type/contract verification requiring a type system or annotations."
    ),
    "linting": (
        "Syntactic/semantic rule-based checks for bugs, anti-patterns, complexity."
    ),
    "security": (
        "Pattern/taint-based detection of exploitable vulnerability classes."
    ),
    "duplicate-code": "Clone/copy-paste detection via token or AST matching.",
    "dead-code": "Reachability/usage analysis for unused symbols, exports, files, deps.",
}

# ---------------------------------------------------------------------------
# Baseline stacks by language (design.md "Baseline stacks by language" table,
# D-03 locked content). Transcribed per FIVE rules:
#
#   1. Alternatives (a primary and an "or" option, or a slash) become
#      MULTIPLE entries in the same category -- a repo using the alternative
#      must classify, not fall through to unclassified.
#   2. A "+"-joined pair (two tools named together, both run) becomes TWO
#      entries, never one combined string -- nobody runs the combined string
#      as a hook command; it is the spec's shorthand for "both of these".
#   3. Parenthetical qualifications stay adjacent commentary (a Python
#      comment near the literal), never part of a matchable entry string.
#      This is the rule that keeps the Go linting cell's default-linter list
#      (which names `staticcheck`) out of the index -- D-T7 puts that one
#      tool back in deliberately, via a cited supplement, not via this
#      table.
#   4. A "this is NOT that category" note (e.g. ruff's `ANN` rules are not
#      type-checking) is a comment, never an entry. A don't-use note (e.g.
#      "not `ts-prune` -- unmaintained") is likewise a comment here; the
#      named tool reaches the index through D-T7's pairs pass instead.
#   5. An inherent, tool-less category (`N/A` in the spec, e.g. type-checking
#      covered by the compiler itself) is an EMPTY entry tuple with a
#      comment naming the compiler -- empty is a fact, omitting the key
#      would make the table's shape uneven.
#
# Transcription footgun (cross-AI review cycle 3, LOW): the Java dead-code
# cell's SpotBugs half is transcribed as the distinct string `SpotBugs UC_*`,
# never shortened to bare `SpotBugs` -- shortening it would collide with the
# Java security cell's `SpotBugs` entry and trip the collision guard below on
# a transcription error rather than a real ambiguity.
# ---------------------------------------------------------------------------

BASELINE_STACKS: dict[str, dict[str, tuple[str, ...]]] = {
    "python": {
        "formatting": ("ruff format",),
        # `pyright` and `mypy` are both named; ruff's `ANN` rules are
        # explicitly NOT type-checking per the spec -- a comment, not an
        # entry.
        "type-checking": ("mypy", "pyright"),
        # "(curated `extend-select`)" is a configuration qualifier, stays a
        # comment.
        "linting": ("ruff check",),
        # "(+ruff `S` for speed)" names the pairs-table row (ruff `S` rules
        # vs bandit) -- that pairing is DATA in the pairs table below, not a
        # second baseline entry here.
        "security": ("bandit",),
        # Slash alternative -> two entries.
        "duplicate-code": ("jscpd", "pylint R0801"),
        "dead-code": ("vulture",),
    },
    "node": {
        # Slash alternative -> two entries.
        "formatting": ("prettier", "biome format"),
        "type-checking": ("tsc --noEmit",),
        # "+"-joined pair -> two entries. "(or `biome`)" is a parenthetical
        # alternative note, stays a comment (rule 3) rather than a third
        # entry -- see this plan's SUMMARY for the recorded judgment call.
        "linting": ("eslint", "typescript-eslint"),
        # "(+`semgrep` in CI)" names the pairs-table row (eslint-plugin-
        # security vs semgrep); `semgrep` reaches the index via D-T7's
        # cited supplement, not as a second baseline entry here.
        "security": ("eslint-plugin-security",),
        "duplicate-code": ("jscpd",),
        # "(not `ts-prune` -- unmaintained)" is a don't-use note, stays a
        # comment; `ts-prune` reaches the index via D-T7's cited supplement.
        "dead-code": ("knip",),
    },
    "java": {
        # "+"-joined pair -> two entries.
        "formatting": ("spotless", "google-java-format"),
        # N/A in the spec -- `javac` is inherent, no tool. Empty is a fact.
        "type-checking": (),
        # "+"-joined pair -> two entries. "(curated ruleset)" stays a
        # comment.
        "linting": ("checkstyle", "PMD"),
        # "+"-joined pair -> two entries.
        "security": ("SpotBugs", "find-sec-bugs"),
        "duplicate-code": ("PMD CPD",),
        # Slash alternative -> two entries. The SpotBugs half is the
        # DISTINCT string "SpotBugs UC_*" (never bare "SpotBugs") -- see the
        # module-level footgun note above.
        "dead-code": ("PMD unused-code rules", "SpotBugs UC_*"),
    },
    "rust": {
        "formatting": ("rustfmt",),
        # N/A in the spec -- `rustc` is inherent, no tool.
        "type-checking": (),
        # "(default groups; `pedantic` opt-in)" stays a comment.
        "linting": ("clippy",),
        # "(supersedes `cargo-audit` on the advisory axis)" names the
        # pairs-table row; `cargo-audit` reaches the index via D-T7's cited
        # supplement, not as a second baseline entry here.
        "security": ("cargo-deny",),
        # "(jscpd-rs emerging, unproven)" is a qualifier about a DIFFERENT,
        # not-yet-confirmed tool -- stays a comment, no second entry.
        "duplicate-code": ("jscpd",),
        # "`rustc`/clippy `dead_code` + `cargo-machete`(fast)/
        # `cargo-udeps`(deep) for unused deps" -- a bare (non-parenthesized)
        # "+" joining two independent tool-pairs, each itself a slash
        # alternative -> FOUR entries. "(fast)"/"(deep)" are speed
        # qualifiers, stay comments.
        "dead-code": ("rustc dead_code", "clippy dead_code", "cargo-machete", "cargo-udeps"),
    },
    "go": {
        "formatting": ("goimports",),
        # N/A in the spec -- the Go compiler is inherent, no tool.
        "type-checking": (),
        # "(errcheck/govet/ineffassign/staticcheck/unused defaults)" is a
        # parenthetical default-linter list -- stays a comment. This is the
        # rule that keeps bare `staticcheck` out of this table; D-T7 puts it
        # back into the index deliberately, via a cited supplement.
        "linting": ("golangci-lint",),
        # "+"-joined pair -> two entries. "(code patterns)" / "(dependency
        # CVEs -- different scope, run both)" are qualifiers, stay comments.
        "security": ("gosec", "govulncheck"),
        # "(via golangci-lint)" stays a comment.
        "duplicate-code": ("dupl",),
        # "(+`x/tools/cmd/deadcode` for function-only, narrower)" is a
        # PARENTHESIZED qualifier about scope -- unlike Rust's bare "+"
        # above, this one stays a comment, not a second entry.
        "dead-code": ("staticcheck unused",),
    },
}


def _derive_tool_category_index() -> dict[str, str]:
    """D-T1: derive the tool-name-to-category index from `BASELINE_STACKS`.

    Never a second hand-typed copy. Raises `ImportError` at import time if
    one entry string is transcribed under two different categories -- that
    is a transcription defect, and a silent pick would make every
    downstream classification untrustworthy. (The Python formatter/linter's
    two entries, `"ruff format"` and `"ruff check"`, are distinct strings
    and are not a collision under this rule.)
    """
    index: dict[str, str] = {}
    for categories in BASELINE_STACKS.values():
        for category, entries in categories.items():
            for entry in entries:
                existing = index.get(entry)
                if existing is not None and existing != category:
                    raise ImportError(
                        f"tool_catalog: transcription collision -- {entry!r} "
                        f"is transcribed under both {existing!r} and "
                        f"{category!r}"
                    )
                index[entry] = category
    return index


TOOL_CATEGORY_INDEX: dict[str, str] = _derive_tool_category_index()

# D-T7: four EXPLICIT, individually-cited supplementary index entries. Each
# is a fact the spec's own baseline cells state in PROSE (a defaults list, a
# don't-use note, or a parenthetical) but do not carry as a matchable entry
# (rule 3 above keeps parenthetical/prose content out of BASELINE_STACKS).
# Without these four, the four pairs-table rows they belong to would be
# unreachable (D-T7's whole rationale) -- this is a four-entry CITED
# reconciliation, not the hand-written flat mapping `INDEX-DERIVED-OK`
# forbids (that guard trips at 8+ entries).
_SUPPLEMENTARY_INDEX_ENTRIES: dict[str, str] = {
    # Go linting cell: "golangci-lint (errcheck/govet/ineffassign/
    # staticcheck/unused defaults)" -- bare `staticcheck` is that same
    # linter run standalone, precisely what the pairs row below is about.
    "staticcheck": "linting",
    # Node dead-code cell's don't-use note: "knip (not `ts-prune` --
    # unmaintained)" names `ts-prune` as the superseded alternative.
    "ts-prune": "dead-code",
    # Rust security cell: "cargo-deny (supersedes `cargo-audit` on the
    # advisory axis)".
    "cargo-audit": "security",
    # Node security cell: "eslint-plugin-security (+`semgrep` in CI)".
    "semgrep": "security",
}

for _entry, _category in _SUPPLEMENTARY_INDEX_ENTRIES.items():
    _existing = TOOL_CATEGORY_INDEX.get(_entry)
    if _existing is not None and _existing != _category:
        raise ImportError(
            f"tool_catalog: supplementary entry collision -- {_entry!r} is "
            f"already {_existing!r}, cannot also be {_category!r}"
        )
    TOOL_CATEGORY_INDEX[_entry] = _category
del _entry, _category, _existing

_TOOL_CATEGORY_INDEX_CASEFOLD: dict[str, str] = {
    entry.casefold(): category for entry, category in TOOL_CATEGORY_INDEX.items()
}

# D-T3: ambiguous-tool defaults (the `inferred` confidence path). Exactly
# one entry is justified today -- do not speculatively add more; an entry
# without a citable convention is a guess wearing a data structure.
AMBIGUOUS_TOOL_DEFAULTS: dict[str, str] = {
    # The upstream `ruff-pre-commit` repository's hook id for the LINTER is
    # the bare name `ruff`, while the formatter's hook id is suffixed
    # (`ruff-format`). A bare `ruff` hook with no disambiguating entry is
    # therefore the linter, at `inferred` confidence -- never indexed
    # directly (see resolve_tool_category's docstring for why).
    "ruff": "linting",
}

# D-T4: out-of-taxonomy markers. The six categories describe static
# analysis; a test runner or a file-hygiene fixer is a real THIRD outcome,
# never unclassified-needing-research. Deliberately conservative: a marker
# that is arguably an analyzer belongs in BASELINE_STACKS, not here.
OUT_OF_TAXONOMY_GROUPS: dict[str, dict[str, object]] = {
    "test-runner": {
        "markers": (
            "pytest",
            "unittest",
            "jest",
            "vitest",
            "go test",
            "cargo test",
            "mvn test",
        ),
        "reason": (
            "runs the test suite -- exercises behavior, not a static "
            "analyzer; the six-category taxonomy describes static analysis "
            "only"
        ),
    },
    "pre-commit-hooks-hygiene": {
        "markers": (
            "trailing-whitespace",
            "end-of-file-fixer",
            "check-yaml",
            "check-json",
            "check-toml",
            "check-added-large-files",
            "check-merge-conflict",
            "mixed-line-ending",
            "check-case-conflict",
            "check-executables-have-shebangs",
            "detect-private-key",
            "requirements-txt-fixer",
            "name-tests-test",
        ),
        "reason": (
            "a standard pre-commit-hooks whitespace/file-hygiene fixer, not "
            "a static analyzer"
        ),
    },
}

# D-02: the 6-to-5 category reconciliation with the sibling
# `ai-kit-project-rules-makefile` skill's `RESEARCH_CATEGORIES`. Five of the
# six taxonomy names map onto the sibling's five research-category names;
# `type-checking` maps to `None` -- the sibling's `REQUIRED_STATIC_TARGETS`
# tuple has no type-checking entry today, so there is no Makefile-target
# equivalent to alias it to. That is D-02's recorded finding, not an
# omission -- inventing a target name to fill the slot would be exactly the
# false-certainty PROJECT.md forbids. A drift guard in
# `tests/test_ai_kit_rules_common.py` reads the sibling's own
# `RESEARCH_CATEGORIES` literal via `ast` (never imported) and pins these
# five mapped values against it.
MAKEFILE_CATEGORY_ALIAS: dict[str, str | None] = {
    "formatting": "formatter",
    "type-checking": None,
    "linting": "code-smell-detector",
    "security": "security-scanner",
    "duplicate-code": "duplicate-code-detector",
    "dead-code": "dead-code-detector",
}

# D-03: the "Confirmed redundant-vs-complementary pairs" table, transcribed
# verbatim -- ten rows, each carrying its ecosystem, its two tool-name
# members, its relationship, and the spec's own reason in the spec's own
# words. ROW SHAPE is a mapping with these pinned keys (never a
# tuple-of-positional-fields -- three probes in this plan and plan 11-03's
# evaluation all read rows directly):
#   - "ecosystem": the language ecosystem string.
#   - "tools": a two-element tuple of the member names exactly as the spec
#     writes them.
#   - "rule_family_members": a possibly-empty tuple naming those members
#     that are RULE FAMILIES (a rule selector inside another tool's
#     configuration, e.g. "ruff `S` rules") rather than tools a repo could
#     run as a hook -- exempt from D-T7's resolve requirement. Exactly one
#     row today carries one.
#   - "relationship": one of the CLOSED set of four values below.
#   - "reason": the spec's own sentence, verbatim.
#
# Relationship vocabulary (closed set, exactly these four): "redundant" and
# "supersession" are what plan 11-03 flags and what the import-time guard
# below holds to the same-category requirement; "complementary" and
# "overlapping" emit nothing.
REDUNDANT_VS_COMPLEMENTARY_PAIRS: tuple[dict[str, object], ...] = (
    {
        "ecosystem": "Python",
        "tools": ("ruff S rules", "bandit"),
        "rule_family_members": ("ruff S rules",),
        "relationship": "overlapping",
        "reason": (
            "Overlapping — ruff S is a partial/stale port; bandit has 5 "
            "checks ruff lacks. Keep both: ruff S at edit-speed, bandit in "
            "CI for full coverage."
        ),
    },
    {
        "ecosystem": "Python",
        "tools": ("ruff", "vulture"),
        "rule_family_members": (),
        "relationship": "complementary",
        "reason": (
            "Complementary — ruff only catches locally-unused imports/vars; "
            "vulture does whole-project reachability."
        ),
    },
    {
        "ecosystem": "Node/TS",
        "tools": ("eslint-plugin-security", "semgrep"),
        "rule_family_members": (),
        "relationship": "complementary",
        "reason": (
            "Complementary — plugin is single-file/AST pattern match (fast, "
            "shallow); semgrep does cross-file taint (slower, deeper). Keep "
            "both."
        ),
    },
    {
        "ecosystem": "Node/TS",
        "tools": ("knip", "ts-prune"),
        "rule_family_members": (),
        "relationship": "supersession",
        "reason": (
            "Supersession, not complementary — ts-prune is unmaintained; "
            "knip is the strict superset. Don't run both."
        ),
    },
    {
        "ecosystem": "Java",
        "tools": ("checkstyle", "PMD"),
        "rule_family_members": (),
        "relationship": "overlapping",
        "reason": (
            "Overlapping on style/naming, complementary elsewhere (PMD adds "
            "bug-pattern/design/security PMD-specific rules). Keep both."
        ),
    },
    {
        "ecosystem": "Java",
        "tools": ("PMD", "SpotBugs"),
        "rule_family_members": (),
        "relationship": "complementary",
        "reason": (
            "Complementary — PMD analyzes source pre-compile; SpotBugs "
            "analyzes compiled bytecode (different failure classes "
            "entirely)."
        ),
    },
    {
        "ecosystem": "Rust",
        "tools": ("cargo-audit", "cargo-deny"),
        "rule_family_members": (),
        "relationship": "redundant",
        "reason": (
            "Redundant on the advisory axis once cargo-deny is adopted — "
            "cargo-deny's check advisories covers the same RustSec DB. Pick "
            "one (deny, if adopting its broader scope)."
        ),
    },
    {
        "ecosystem": "Rust",
        "tools": ("cargo-machete", "cargo-udeps"),
        "rule_family_members": (),
        "relationship": "complementary",
        "reason": (
            "Complementary — machete is fast/narrow (text-scan, no compile, "
            "every-push gating); udeps is slow/wide (full nightly compile, "
            "periodic deep sweep). Keep both."
        ),
    },
    {
        "ecosystem": "Go",
        "tools": ("staticcheck", "golangci-lint"),
        "rule_family_members": (),
        "relationship": "redundant",
        "reason": (
            "Fully redundant — golangci-lint bundles staticcheck verbatim. "
            "Don't run both."
        ),
    },
    {
        "ecosystem": "Go",
        "tools": ("gosec", "govulncheck"),
        "rule_family_members": (),
        "relationship": "complementary",
        "reason": (
            "Complementary — different scope entirely (code-pattern SAST "
            "vs. dependency-CVE reachability scanning). Keep both."
        ),
    },
)

_PAIR_RELATIONSHIPS = ("redundant", "supersession", "complementary", "overlapping")
_SAME_CATEGORY_REQUIRED_RELATIONSHIPS = ("redundant", "supersession")


def resolve_tool_category(tool_name: str) -> str | None:
    """D-T7: the SINGLE definition of "this catalog can answer this tool
    name". Returns a category name, or `None`.

    Implements the chain: an exact, case-folded hit in the derived
    `TOOL_CATEGORY_INDEX` (baseline entries + the four cited supplements),
    then a hit in `AMBIGUOUS_TOOL_DEFAULTS`. This function is called by the
    import-time pairs-reachability guard below, by this module's own tests,
    and by plan 11-02/11-03's classifier and pair-evaluation code alike --
    the four cannot disagree about what "resolving" means.

    WHY the chain has a second link: exactly one pairs-row member (bare
    `ruff`) is a name `AMBIGUOUS_TOOL_DEFAULTS` deliberately keeps OUT of
    `TOOL_CATEGORY_INDEX` -- its two baseline entries exist only in the
    suffixed forms `"ruff format"`/`"ruff check"`, and indexing the bare
    name would either trip the collision guard above (formatting vs
    linting) or forge a `baseline` confidence D-T3 reserves for an
    inference. An index-membership-only answer would therefore be
    UNSATISFIABLE for that row. This chain does not weaken the guard: the
    defaults map has exactly one cited entry today, and an unknown name
    resolves to `None` either way.

    This function does NOT do longest-first/token-bounded haystack matching
    (D-T2) -- that stays the classifier's job. This answers one
    already-isolated tool name.
    """
    if not isinstance(tool_name, str) or not tool_name:
        return None
    key = tool_name.strip().casefold()
    if key in _TOOL_CATEGORY_INDEX_CASEFOLD:
        return _TOOL_CATEGORY_INDEX_CASEFOLD[key]
    return AMBIGUOUS_TOOL_DEFAULTS.get(key)


def _validate_pairs_reachability(rows: tuple[dict[str, object], ...]) -> None:
    """D-T7's import-time guard. Every tool-token member of every row must
    resolve THROUGH `resolve_tool_category` -- never by asking whether the
    name is an index key, which is the version of this check that cannot
    pass (see `resolve_tool_category`'s own docstring). A member marked in
    `rule_family_members` is exempt. Any row whose `relationship` is
    `"redundant"` or `"supersession"` must have every resolved member share
    the SAME category; a `"complementary"`/`"overlapping"` row resolving
    cross-category is fine and must not raise.
    """
    for row in rows:
        tools = cast("tuple[str, ...]", row["tools"])
        rule_family = cast("tuple[str, ...]", row.get("rule_family_members", ()))
        token_members = [t for t in tools if t not in rule_family]
        resolved: dict[str, str] = {}
        for member in token_members:
            category = resolve_tool_category(member)
            if category is None:
                raise ImportError(
                    f"tool_catalog: pairs row {tools!r} has an unresolved "
                    f"tool-token member {member!r} -- resolve_tool_category "
                    "answers neither the index nor the ambiguous-tool "
                    "defaults for it"
                )
            resolved[member] = category
        if row["relationship"] in _SAME_CATEGORY_REQUIRED_RELATIONSHIPS and (
            len(token_members) == 2
        ):
            categories = {resolved[m] for m in token_members}
            if len(categories) > 1:
                raise ImportError(
                    f"tool_catalog: pairs row {tools!r} "
                    f"({row['relationship']!r}) resolves to different "
                    f"categories {sorted(categories)!r} -- a confirmed "
                    "redundancy/supersession must share one category"
                )


_validate_pairs_reachability(REDUNDANT_VS_COMPLEMENTARY_PAIRS)


def find_pair_relationship(tool_a: str, tool_b: str) -> dict[str, object] | None:
    """D-04's mechanism: return the pairs-table row naming both `tool_a` and
    `tool_b` (in EITHER order), or `None` for an unresearched pair. Plan
    11-03 treats `None` as presumed-complementary and never flags it."""
    wanted = {tool_a, tool_b}
    for row in REDUNDANT_VS_COMPLEMENTARY_PAIRS:
        if set(cast("tuple[str, ...]", row["tools"])) == wanted:
            return row
    return None


__all__ = [
    "AMBIGUOUS_TOOL_DEFAULTS",
    "BASELINE_STACKS",
    "MAKEFILE_CATEGORY_ALIAS",
    "OUT_OF_TAXONOMY_GROUPS",
    "REDUNDANT_VS_COMPLEMENTARY_PAIRS",
    "TAXONOMY_CATEGORIES",
    "TAXONOMY_DEFINITIONS",
    "TOOL_CATEGORY_INDEX",
    "find_pair_relationship",
    "resolve_tool_category",
]
