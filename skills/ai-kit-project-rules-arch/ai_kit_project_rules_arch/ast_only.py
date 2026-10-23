"""Target-aware, AST-only-ness check for a repo's backing architecture-test
file (ROADMAP Phase 12 SC3; 12-CONTEXT D-01/D-02; this plan's D-A7/D-A8/D-A9).

Scope boundary, same as `arch_checker.py`'s: this module answers exactly one
question -- does the backing file behind an arch-test-shaped Makefile target
PARSE the module(s) it architecturally checks, or does it also IMPORT or
EXECUTE them? -- and never attempts dependency-direction or layering-
boundary enforcement over the target repo's own source tree.

D-01's whole point is TARGET-AWARENESS: a backing file that parses module X
via `ast.parse` while separately loading an UNRELATED module Y (e.g. for
incidental inventory-test helpers, the exact shape `tests/test_arch.py`
loads `tools/setup.py` in) is clean. Only a backing file that imports or
executes the SAME module it parses is flagged. This is implemented by
correlating two token sets -- the "parsed subjects" reaching `ast.parse`
(directly, or through a fixed point of parser-helper functions) and the
"executed subjects" reaching an import/execution call -- through ONE shared
normalizer, with one level of local name resolution applied on BOTH sides
(D-A8). Stated limits: no cross-module dataflow, and no resolution of a
name assigned outside the one function scope a call site lives in (or
module scope for a module-level call) -- and no dynamic/computed module
names. Where the mechanism cannot see, it emits one of D-A9's four PINNED
advisory reasons rather than a guess: `not_discoverable`, `not_python`,
`unparseable`, `no_parse_call`.

Security note (T-12-09): this module parses an untrusted backing file with
`ast.parse` ONLY. Nothing here ever imports, execs, or otherwise runs a
target repo's file -- the checker must never do the very thing it is
checking for.
"""

from __future__ import annotations

import ast
import os
import re
from typing import ClassVar

from ai_kit_rules_common.criticality import CRITICALITY_ADVISORY, CRITICALITY_MEDIUM
from ai_kit_rules_common.makefile_parse import parse_makefile_recipe

# D-A7 -- the two candidate-forming rules. (i) an existing source-extension
# suffix; (ii) a dotted identifier path (`tests.test_arch`), which is
# exactly how ai-kit's own `arch-test` recipe names its backing file.
_SOURCE_EXTENSIONS = (".py", ".ts", ".tsx", ".js", ".java", ".kt", ".go", ".rs")
_DOTTED_PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$")

# D-A8's execution-call vocabulary: `importlib.import_module`, bare
# `__import__`, `importlib.util.spec_from_file_location`, and ANY
# `exec_module` call (any object's `.exec_module(...)`, no base tracing
# required -- "any" is explicit in D-A8).
_EXECUTION_CALL_SUFFIXES = ("import_module", "spec_from_file_location", "exec_module")

_NOT_VERIFIABLE_REASON_TEXT = {
    "not_discoverable": (
        "no candidate in the arch-test target's own Makefile recipe "
        "resolved to an existing regular file inside the repo root "
        "(including a candidate rejected because it resolved outside the "
        "repo root), so this skill could not identify which file to check "
        "for AST-only-ness."
    ),
    "not_python": (
        "the backing file the arch-test recipe names is not a '.py' file, "
        "so this skill's ast-based AST-only check does not apply to it."
    ),
    "unparseable": (
        "the backing file is a '.py' file that Python's own 'ast.parse' "
        "refused to parse (a syntax error), so its AST-only-ness could not "
        "be checked."
    ),
    "no_parse_call": (
        "the backing file parsed, but contains no call reaching "
        "'ast.parse' (directly, or through a helper function), so this "
        "skill could not identify what it architecturally checks."
    ),
}


def _recipe_tokens(recipe_text: str) -> list[str]:
    """D-A7's tokenization: whitespace-split across all recipe lines,
    skipping any token beginning with `-` (a flag) or containing `=` (an
    assignment)."""
    tokens: list[str] = []
    for line in recipe_text.splitlines():
        for token in line.split():
            if token.startswith("-") or "=" in token:
                continue
            tokens.append(token)
    return tokens


def find_backing_test_file(
    repo_root: str, makefile_path: str, target_name: str
) -> tuple[str | None, bool]:
    """D-A7 -- returns `(backing_file_path_or_None, any_candidate_formed)`.

    `any_candidate_formed` is `True` when at least one recipe token matched
    one of the two candidate-forming rules (a known source extension, or a
    dotted-identifier path) -- even when that candidate ultimately failed
    to resolve. This is the signal `_find_ast_only_finding` uses to tell
    apart a recipe that plausibly points at a checkable Python file but
    can't reach it (the `not_discoverable` advisory) from a recipe that
    never looked like it referenced a source file at all (e.g. a bare
    `echo` no-op, or an external CLI tool invoked with no file-shaped
    argument) -- the FIRST candidate that is an existing regular file is
    still the backing file when one is found.

    Containment is this family's EXISTING guard, copied from
    `ai_kit_project_rules_agents/cli.py:65-69` -- `os.path.realpath` on
    BOTH sides, then an exact-match-or-`os.sep`-bounded-prefix test,
    applied BEFORE the `os.path.isfile` test. A recipe is untrusted input
    and must not be able to steer a file read outside the repo the caller
    named: `os.path.realpath` on both sides stops a `../../...`-shaped
    token and a symlink pointing out of the tree, and the `os.sep`
    boundary stops a SIBLING directory whose name merely extends the
    root's -- a bare `startswith(repo_root)` on unresolved paths would
    accept `/tmp/repo-evil/leak.py` for a repo root of `/tmp/repo`. Note
    that `os.path.join(repo_root, token)` returns the token unchanged when
    the token is absolute, so an absolute recipe token reaches this guard
    directly. A rejected-by-containment candidate still counts toward
    `any_candidate_formed` -- it WAS a plausible file reference, just one
    this skill correctly declines to open.
    """
    recipe = parse_makefile_recipe(makefile_path, target_name)
    real_repo_root = os.path.realpath(repo_root)
    any_candidate = False
    for token in _recipe_tokens(recipe):
        candidates: list[str] = []
        if token.endswith(_SOURCE_EXTENSIONS):
            candidates.append(os.path.join(repo_root, token))
        if _DOTTED_PATH_RE.match(token):
            candidates.append(os.path.join(repo_root, token.replace(".", "/") + ".py"))
        if candidates:
            any_candidate = True
        for candidate in candidates:
            real_candidate = os.path.realpath(candidate)
            if not (
                real_candidate == real_repo_root
                or real_candidate.startswith(real_repo_root + os.sep)
            ):
                continue
            if os.path.isfile(candidate):
                return candidate, True
    return None, any_candidate


def _dotted_name(node: ast.expr) -> str | None:
    """Return the full dotted name of a `Name`/`Attribute` chain (e.g.
    `importlib.util.spec_from_file_location`), or `None` when the base is
    not a simple Name/Attribute chain (a Call, a Subscript, ...)."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None


def _detect_ast_aliases(tree: ast.Module) -> tuple[str | None, str | None]:
    """The alias `ast` itself is imported under (`import ast` -> `"ast"`,
    `import ast as X` -> `"X"`), and the alias `parse` is imported under
    FROM `ast` specifically (`from ast import parse` -> `"parse"`,
    `from ast import parse as Y` -> `"Y"`, or `None` if not imported that
    way)."""
    ast_alias: str | None = None
    parse_alias: str | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "ast":
                    ast_alias = alias.asname or "ast"
        elif isinstance(node, ast.ImportFrom) and node.module == "ast":
            for alias in node.names:
                if alias.name == "parse":
                    parse_alias = alias.asname or "parse"
    return ast_alias, parse_alias


def _is_direct_ast_parse_call(
    call: ast.Call, ast_alias: str | None, parse_alias: str | None
) -> bool:
    """A direct `ast.parse(...)` call (an `Attribute` `parse` on the
    module's own `ast` alias) or a direct bare `parse(...)` call where
    `parse` was imported FROM `ast` specifically."""
    func = call.func
    if (
        ast_alias is not None
        and isinstance(func, ast.Attribute)
        and func.attr == "parse"
        and _dotted_name(func.value) == ast_alias
    ):
        return True
    return parse_alias is not None and isinstance(func, ast.Name) and func.id == parse_alias


def _is_executed_call(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Name) and func.id == "__import__":
        return True
    dotted = _dotted_name(func)
    if dotted is None:
        return False
    return dotted.rsplit(".", 1)[-1] in _EXECUTION_CALL_SUFFIXES


class _ScopeCollector(ast.NodeVisitor):
    """Tracks, for every `Call` and `Assign` in the tree, its nearest
    enclosing Module/FunctionDef scope -- D-A8's ONE LEVEL of local name
    resolution, never chasing into an enclosing or a called function's own
    scope. A `ClassDef` does not push a new scope here: a method defined
    inside a class is still a `FunctionDef` and gets its own scope exactly
    as a module-level function does, which is all D-A8 needs."""

    _VISIT_HANDLERS: ClassVar[dict[type[ast.AST], str]] = {
        ast.Module: "_visit_scope",
        ast.FunctionDef: "_visit_scope",
        ast.AsyncFunctionDef: "_visit_scope",
        ast.Assign: "_visit_assign",
        ast.Call: "_visit_call",
    }

    def __init__(self) -> None:
        self.call_scope: dict[ast.Call, ast.AST] = {}
        self.scope_assignments: dict[ast.AST, dict[str, list[ast.expr]]] = {}
        self._scope_stack: list[ast.AST] = []

    def visit(self, node: ast.AST) -> None:
        handler_name = self._VISIT_HANDLERS.get(type(node))
        if handler_name is not None:
            getattr(self, handler_name)(node)
            return
        self.generic_visit(node)

    def _push_scope(self, node: ast.AST) -> None:
        self._scope_stack.append(node)
        self.scope_assignments.setdefault(node, {})

    def _pop_scope(self) -> None:
        self._scope_stack.pop()

    def _visit_scope(self, node: ast.AST) -> None:
        self._push_scope(node)
        self.generic_visit(node)
        self._pop_scope()

    def _visit_assign(self, node: ast.Assign) -> None:
        scope = self._scope_stack[-1]
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.scope_assignments[scope].setdefault(target.id, []).append(node.value)
        self.generic_visit(node)

    def _visit_call(self, node: ast.Call) -> None:
        self.call_scope[node] = self._scope_stack[-1]
        self.generic_visit(node)


def _string_constants_in(node: ast.AST) -> set[str]:
    return {
        n.value
        for n in ast.walk(node)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }


def _collect_call_literals(call: ast.Call, assignments: dict[str, list[ast.expr]]) -> set[str]:
    """D-A8's ONE shared literal-collection helper, routed through by BOTH
    the parse-side and the execute-side extractors so neither can drift
    from the other. For each of `call`'s argument expressions: if the
    argument is a bare `Name`, resolve it against `assignments` (one level
    of local name resolution -- this is the part the execute side needs
    for the live `TestSegmentInventory._sl` shape, not only the parse
    side); otherwise, walk the ENTIRE argument expression for nested
    string constants, since a real argument is often a wrapping
    expression (e.g. `open(path).read()`) rather than a bare literal."""
    literals: set[str] = set()
    arguments = list(call.args) + [kw.value for kw in call.keywords if kw.arg is not None]
    for arg in arguments:
        if isinstance(arg, ast.Name):
            for assigned_expr in assignments.get(arg.id, []):
                literals |= _string_constants_in(assigned_expr)
        else:
            literals |= _string_constants_in(arg)
    return literals


def _normalize_module_token(token: str) -> str:
    """D-A8's ONE shared normalizer, called from both subject extractors.
    Take the last path component, strip a known source extension, take
    the last dotted component, casefold, fold `_` to `-`. So
    `tools/status-line.py`, `status-line.py` and `status_line` all
    normalize to `status-line`."""
    last_component = token.replace("\\", "/").rsplit("/", 1)[-1]
    for ext in _SOURCE_EXTENSIONS:
        if last_component.endswith(ext):
            last_component = last_component[: -len(ext)]
            break
    last_dotted = last_component.rsplit(".", 1)[-1]
    return last_dotted.casefold().replace("_", "-")


def _build_parser_helpers(
    tree: ast.Module,
    collector: _ScopeCollector,
    ast_alias: str | None,
    parse_alias: str | None,
) -> set[str]:
    """The fixed point: a function whose body directly contains a call to
    `ast.parse` (or the `from ast import parse` alias) is a parser helper;
    a function that calls a parser helper is itself one. This is what
    makes `_parse("status-line.py")` count even though `ast.parse` is one
    level down inside `_parse`."""
    function_names = {
        n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    calls_by_func: dict[str, list[ast.Call]] = {name: [] for name in function_names}
    for call, scope in collector.call_scope.items():
        is_function_scope = isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef))
        if is_function_scope and scope.name in calls_by_func:
            calls_by_func[scope.name].append(call)

    helpers: set[str] = set()
    changed = True
    while changed:
        changed = False
        for name, calls in calls_by_func.items():
            if name in helpers:
                continue
            for call in calls:
                is_direct = _is_direct_ast_parse_call(call, ast_alias, parse_alias)
                calls_helper = isinstance(call.func, ast.Name) and call.func.id in helpers
                if is_direct or calls_helper:
                    helpers.add(name)
                    changed = True
                    break
    return helpers


def _relpath(path: str | None, repo_root: str) -> str | None:
    if path is None:
        return None
    return os.path.relpath(path, repo_root)


def _not_verifiable_finding(reason: str, backing_path: str | None, repo_root: str) -> dict:
    rel = _relpath(backing_path, repo_root)
    detail = _NOT_VERIFIABLE_REASON_TEXT[reason]
    prefix = f"'{rel}': " if rel else ""
    text = f"{prefix}{detail}"
    return {
        "category": "arch-test-ast-only",
        "issue": "ast_only_not_verifiable",
        "criticality": CRITICALITY_ADVISORY,
        "summary": text,
        "recommendation": text,
        "needs_research": False,
        "advisory": True,
        "reason": reason,
    }


def _execution_finding(backing_path: str, repo_root: str, intersection: set[str]) -> dict:
    rel = _relpath(backing_path, repo_root)
    modules = ", ".join(f"'{m}'" for m in sorted(intersection))
    text = (
        f"'{rel}' both parses and imports/executes {modules} -- an "
        f"architecture-fitness check that imports or executes the module "
        f"it is checking defeats the point of a static, ast-only check. "
        f"Change '{rel}' to only 'ast.parse' {modules} and never import, "
        f"exec, or spec-load it."
    )
    return {
        "category": "arch-test-ast-only",
        "issue": "backing_file_executes_checked_target",
        "criticality": CRITICALITY_MEDIUM,
        "summary": text,
        "recommendation": text,
        "needs_research": False,
    }


def _open_backing_ast_module(
    repo_root: str, makefile_path: str, target_name: str
) -> tuple[str, ast.Module] | dict | None:
    """Success: `(backing_path, tree)`. Advisory: a finding dict. Silent skip: `None`."""
    backing_path, any_candidate = find_backing_test_file(repo_root, makefile_path, target_name)
    if backing_path is None:
        if not any_candidate:
            return None
        return _not_verifiable_finding("not_discoverable", None, repo_root)
    if not backing_path.endswith(".py"):
        return _not_verifiable_finding("not_python", backing_path, repo_root)
    try:
        with open(backing_path, encoding="utf-8") as handle:
            source = handle.read()
        return backing_path, ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return _not_verifiable_finding("unparseable", backing_path, repo_root)


def _collect_parsed_subjects(
    tree: ast.Module,
    collector: _ScopeCollector,
    ast_alias: str | None,
    parse_alias: str | None,
    helpers: set[str],
) -> tuple[set[str], bool]:
    parsed_subjects: set[str] = set()
    has_parse_call = False
    for call, scope in collector.call_scope.items():
        is_direct = _is_direct_ast_parse_call(call, ast_alias, parse_alias)
        calls_helper = isinstance(call.func, ast.Name) and call.func.id in helpers
        if not is_direct and not calls_helper:
            continue
        has_parse_call = True
        assignments = collector.scope_assignments.get(scope, {})
        for literal in _collect_call_literals(call, assignments):
            parsed_subjects.add(_normalize_module_token(literal))
    return parsed_subjects, has_parse_call


def _collect_executed_subjects(tree: ast.Module, collector: _ScopeCollector) -> set[str]:
    executed_subjects: set[str] = set()
    for call, scope in collector.call_scope.items():
        if not _is_executed_call(call):
            continue
        assignments = collector.scope_assignments.get(scope, {})
        for literal in _collect_call_literals(call, assignments):
            executed_subjects.add(_normalize_module_token(literal))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                executed_subjects.add(_normalize_module_token(alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            executed_subjects.add(_normalize_module_token(node.module))
    return executed_subjects


def _ast_only_finding_from_tree(
    backing_path: str, repo_root: str, tree: ast.Module, collector: _ScopeCollector
) -> dict | None:
    ast_alias, parse_alias = _detect_ast_aliases(tree)
    helpers = _build_parser_helpers(tree, collector, ast_alias, parse_alias)
    parsed_subjects, has_parse_call = _collect_parsed_subjects(
        tree, collector, ast_alias, parse_alias, helpers
    )
    if not has_parse_call:
        return _not_verifiable_finding("no_parse_call", backing_path, repo_root)
    executed_subjects = _collect_executed_subjects(tree, collector)
    intersection = parsed_subjects & executed_subjects
    if not intersection:
        return None
    return _execution_finding(backing_path, repo_root, intersection)


def _find_ast_only_finding(repo_root: str, makefile_path: str, target_name: str) -> dict | None:
    opened = _open_backing_ast_module(repo_root, makefile_path, target_name)
    if opened is None or isinstance(opened, dict):
        return opened
    backing_path, tree = opened
    collector = _ScopeCollector()
    collector.visit(tree)
    return _ast_only_finding_from_tree(backing_path, repo_root, tree, collector)


def build_ast_only_findings(repo_root: str, makefile_path: str, target_name: str) -> list[dict]:
    """D-A4's target-found branch calls this ONCE, passing the already-
    resolved arch-test target name -- never re-derived. Returns zero or one
    finding: the real finding when the correlation's intersection is
    non-empty, one of the four not-verifiable advisories when the check
    honestly cannot verify AST-only-ness, or an empty list when the file is
    discoverable, parseable, and clean (parses one module and does not
    import/execute it)."""
    finding = _find_ast_only_finding(repo_root, makefile_path, target_name)
    return [finding] if finding is not None else []


__all__ = ["build_ast_only_findings", "find_backing_test_file"]
