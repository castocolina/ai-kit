"""AST architecture-fitness test for tools/claude-status-line.py (FR-8).

This module enforces the seven structural invariants of FR-8.1 by parsing the
render module (and the extracted doctor module) with the stdlib ``ast`` module
and asserting properties of the parse tree. No source code is imported or
executed; the checks are purely structural.

Each rule is a ``TestArchitecture`` method that runs against the live tree, and
each rule's *checker* is factored to operate on a passed-in AST so its logic can
also be exercised against a tiny deliberately-violating snippet (the
``TestArchNonVacuity`` class). Those negative checks satisfy FR-8.3 — they prove
a rule actually catches the violation it claims to, rather than passing
vacuously.

Conventions parsed from the source:

* The render module is divided into nine banner blocks, each opened by a comment
  line of the form ``# ═══ N. <ROLE> — ...``.  Block boundaries are parsed
  dynamically from those comments (line numbers drift; the banners do not).
* Top-level functions carry a role prefix (``cfg_``/``probe_``/``fmt_``/
  ``util_``/``core_``/``seg_``) matching the block they live in, except the two
  SHELL entrypoints ``main`` and ``safe_render`` (the SHELL block is now last,
  after ``seg_``) which are unprefixed by design.
"""

import ast
import hashlib
import importlib.util
import io
import os
import re
import subprocess
import sys
import tokenize
import unittest
from typing import NamedTuple

_TOOLS = os.path.join(os.path.dirname(__file__), "..", "tools")
if os.path.abspath(_TOOLS) not in sys.path:
    sys.path.insert(0, os.path.abspath(_TOOLS))
import claude_host
import cursor_host

_AUDIT_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "statusline_split", "audit.md")
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_AUDIT_VOCABULARY = re.compile(
    r"claude|CC_AI_KIT|rate_limits|settings\.json|\.claude", re.IGNORECASE
)


class AuditRow(NamedTuple):
    number: int
    name: str
    kind: str
    base_line: int
    base_ast: str
    stage: str
    module: str
    target: str
    new_name: str
    neutral: str
    fate: str
    taint: str
    reason: str


def audit_rows(text):
    """Parse audit metadata and position-keyed data rows."""
    headers = {}
    rows = []
    for line in text.splitlines():
        if line.startswith("| ") and not line.startswith("| # |") and not line.startswith("|---"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 13:
                rows.append(
                    AuditRow(
                        int(cells[0]), cells[1], cells[2], int(cells[3]), cells[4], *cells[5:13]
                    )
                )
        elif ": " in line and not line.startswith("#"):
            key, value = line.split(": ", 1)
            headers[key] = value
    return headers, rows


def base_definitions(source):
    """Return top-level definitions in source order, preserving duplicate names."""
    definitions = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef):
            definitions.append((node.name, "function", node.lineno, node))
        elif isinstance(node, ast.ClassDef):
            definitions.append((node.name, "class", node.lineno, node))
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            definitions.append((node.targets[0].id, "assign", node.lineno, node))
    return definitions


NONE = {
    "AnnAssign": {"value"},
    "Assert": {"msg"},
    "Assign": {"type_comment"},
    "AsyncFor": {"type_comment"},
    "AsyncFunctionDef": {"returns", "type_comment"},
    "AsyncWith": {"type_comment"},
    "Constant": {"kind"},
    "ExceptHandler": {"name", "type"},
    "For": {"type_comment"},
    "FormattedValue": {"format_spec"},
    "FunctionDef": {"returns", "type_comment"},
    "ImportFrom": {"level", "module"},
    "Interpolation": {"format_spec"},
    "MatchAs": {"name", "pattern"},
    "MatchMapping": {"rest"},
    "MatchStar": {"name"},
    "ParamSpec": {"default_value"},
    "Raise": {"cause", "exc"},
    "Return": {"value"},
    "Slice": {"step", "lower", "upper"},
    "TypeVar": {"default_value", "bound"},
    "TypeVarTuple": {"default_value"},
    "With": {"type_comment"},
    "Yield": {"value"},
    "alias": {"asname"},
    "arg": {"annotation", "type_comment"},
    "arguments": {"kwarg", "vararg"},
    "keyword": {"arg"},
    "match_case": {"guard"},
    "withitem": {"optional_vars"},
}
LISTS = {
    "Assign": {"targets"},
    "AsyncFor": {"body", "orelse"},
    "AsyncFunctionDef": {"body", "decorator_list", "type_params"},
    "AsyncWith": {"body", "items"},
    "BoolOp": {"values"},
    "Call": {"args", "keywords"},
    "ClassDef": {"body", "decorator_list", "bases", "keywords", "type_params"},
    "Compare": {"comparators", "ops"},
    "Delete": {"targets"},
    "Dict": {"keys", "values"},
    "DictComp": {"generators"},
    "ExceptHandler": {"body"},
    "For": {"body", "orelse"},
    "FunctionDef": {"body", "decorator_list", "type_params"},
    "FunctionType": {"argtypes"},
    "GeneratorExp": {"generators"},
    "Global": {"names"},
    "If": {"body", "orelse"},
    "Import": {"names"},
    "ImportFrom": {"names"},
    "Interactive": {"body"},
    "JoinedStr": {"values"},
    "List": {"elts"},
    "ListComp": {"generators"},
    "Match": {"cases"},
    "MatchClass": {"kwd_attrs", "patterns", "kwd_patterns"},
    "MatchMapping": {"keys", "patterns"},
    "MatchOr": {"patterns"},
    "MatchSequence": {"patterns"},
    "Module": {"body", "type_ignores"},
    "Nonlocal": {"names"},
    "Set": {"elts"},
    "SetComp": {"generators"},
    "TemplateStr": {"values"},
    "Try": {"body", "finalbody", "handlers", "orelse"},
    "TryStar": {"body", "finalbody", "handlers", "orelse"},
    "Tuple": {"elts"},
    "TypeAlias": {"type_params"},
    "While": {"body", "orelse"},
    "With": {"body", "items"},
    "arguments": {"kw_defaults", "posonlyargs", "kwonlyargs", "args", "defaults"},
    "comprehension": {"ifs"},
    "match_case": {"body"},
}


def _dump_hide_empty(node):
    """ast.dump(show_empty=False) for interpreters that always print empty fields.

    The audit hashes were taken on Python 3.14, whose dump omits None defaults
    and empty lists. The uv test runner is 3.12 and has no show_empty flag.
    """

    def _format(node):
        if isinstance(node, ast.AST):
            cls = type(node).__name__
            skip_none = NONE.get(cls, ())
            skip_list = LISTS.get(cls, ())
            args = []
            for name in node._fields:
                value = getattr(node, name)
                if value is None and name in skip_none:
                    continue
                if value == [] and name in skip_list:
                    continue
                args.append(f"{name}={_format(value)}")
            return f"{cls}({', '.join(args)})"
        if isinstance(node, list):
            return "[" + ", ".join(_format(item) for item in node) + "]"
        return repr(node)

    return _format(node)


def ast_hash(node):
    if sys.version_info >= (3, 14):
        dumped = ast.dump(node, show_empty=False)
    else:
        dumped = _dump_hide_empty(node)
    return hashlib.sha256(dumped.encode()).hexdigest()[:12]


def taint_map(source):
    """Compute pinned-vocabulary taint and name-reference propagation."""
    definitions = base_definitions(source)
    result = {}
    for name, _, _, node in definitions:
        segment = ast.get_source_segment(source, node) or ""
        if _AUDIT_VOCABULARY.search(segment):
            result[name] = "seed"
    while True:
        prior = set(result)
        for name, _, _, node in definitions:
            if name not in result and any(
                isinstance(child, ast.Name) and child.id in prior for child in ast.walk(node)
            ):
                result[name] = "prop"
        if set(result) == prior:
            break
    return [result.get(name, "-") for name, _, _, _ in definitions]


def check_audit_against_base(rows, definitions):
    violations = []
    if len(rows) != len(definitions):
        violations.append(f"row count {len(rows)} != base definition count {len(definitions)}")
    for position, (row, definition) in enumerate(zip(rows, definitions, strict=False), 1):
        name, kind, line, node = definition
        if row.number != position or (row.name, row.kind, row.base_line, row.base_ast) != (
            name,
            kind,
            line,
            ast_hash(node),
        ):
            violations.append(f"row {position} differs from base definition {name}")
    return violations


def check_audit_reasons(rows):
    violations = []
    for row in rows:
        if (
            row.taint in {"seed", "prop"}
            and row.neutral == "y"
            and "taint-override:" not in row.reason
        ):
            violations.append(f"row {row.number} needs a taint override")
        if row.taint == "-" and row.neutral == "n" and "data-source:" not in row.reason:
            violations.append(f"row {row.number} needs a data-source reason")
        if len(row.reason.strip()) < 12:
            violations.append(f"row {row.number} reason is too short")
    return violations


def check_audit_columns(rows, modules):
    violations = []
    valid_targets = set(modules)
    for row in rows:
        if (
            row.stage not in {"1", "2", "3"}
            or row.module not in modules
            or row.target not in valid_targets
            or row.neutral not in {"y", "n"}
            or row.fate not in {"reused", "generalized", "split", "deleted"}
            or row.taint not in {"seed", "prop", "-"}
        ):
            violations.append(f"row {row.number} has an invalid classification column")
    return violations


# Load setup module for inventory tests.
_SETUP_SPEC = importlib.util.spec_from_file_location("setup", os.path.join(_TOOLS, "setup.py"))
assert _SETUP_SPEC is not None and _SETUP_SPEC.loader is not None
_SETUP_MOD = importlib.util.module_from_spec(_SETUP_SPEC)
_SETUP_SPEC.loader.exec_module(_SETUP_MOD)
setup = _SETUP_MOD

# Banner marker: "# ═══ N. ROLE — ..." — capture the block index and the role token.
_BANNER_RE = re.compile(r"^#\s*═══\s*(\d+)\.\s*([A-Za-z_]+)")

# Block-index → expected role prefix for a top-level FunctionDef (rule 6).
# Blocks 1 (DEFAULTS, data-only) and 9 (trailing doc) define no role functions;
# the SHELL block (now block 8) is matched by its ROLE name, not a fixed index.
_BLOCK_PREFIX = {
    2: "cfg_",
    3: "probe_",
    4: "fmt_",
    5: "util_",
    6: "core_",
    7: "seg_",
}

# The unprefixed SHELL entrypoints permitted in the SHELL block (FR-A.1).
_SHELL_ENTRYPOINTS = {"main", "safe_render"}

# Doctor / introspection symbols that must NOT live in the render module (FR-7).
_DOCTOR_SYMBOLS = {
    "cmd_doctor",
    "cmd_check",
    "cmd_print_config",
    "validate_config_file",
    "_DOCTOR_SAMPLE",
    "parse_args",
    "_dry_render_failures",
    "_ENV_HELP",
    "_NO_CHECK",
}

# The only two segments allowed to read render bookkeeping (rule 3).
_BOOKKEEPING_READERS = {"seg_render_time", "seg_slowest"}
# Render-bookkeeping attribute names guarded by rule 3.
_BOOKKEEPING_ATTRS = {"slowest", "t_start"}

# Required segment signature (rule 4).
_SEG_SIGNATURE = ["ctx", "avail", "theme"]

# Typed-model roots whose members must be reached by attribute, not subscript
# (rule 2 / D4).  Subscripting these names directly is the violation. Illustrative
# exempt forms the rule would allow — attribute-then-subscript such as
# ``ctx.raw[...]`` or ``ctx.rate_limits[...]`` — are shown for shape only and may
# not appear verbatim in the live source; rule 2's teeth come from the snippet
# suite (TestArchNonVacuity), not from the live tree.
_TYPED_MODEL_NAMES = {"ctx", "line_conf"}


def _parse(name):
    """Parse a tools/ module into an AST, attaching its banner block map.

    Returns ``(tree, source)`` so callers can inspect both the parse tree and
    the raw text (the banner blocks are comments and thus not in the AST).
    """
    path = os.path.join(_TOOLS, name)
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    return ast.parse(source, filename=name), source


def _banner_blocks(source):
    """Map banner comments to ``[(index, role, start_line, end_line), ...]``.

    ``start_line`` is the banner's own line; ``end_line`` is the line before the
    next banner (or +inf for the final block). Line numbers are 1-based to match
    ``ast`` node ``lineno`` values.
    """
    marks = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        match = _BANNER_RE.match(line)
        if match:
            marks.append((int(match.group(1)), match.group(2).upper(), lineno))
    blocks = []
    for pos, (index, role, start) in enumerate(marks):
        end = marks[pos + 1][2] - 1 if pos + 1 < len(marks) else float("inf")
        blocks.append((index, role, start, end))
    return blocks


def _block_for_line(blocks, lineno):
    """Return ``(index, role)`` of the banner block containing ``lineno``, or None."""
    for index, role, start, end in blocks:
        if start <= lineno <= end:
            return index, role
    return None


def _top_functions(tree):
    """Yield top-level FunctionDef/AsyncFunctionDef nodes of a module."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _defined_names(tree):
    """Set of names a module defines: FunctionDef/ClassDef names plus the targets
    of module-level ``Assign``/``AnnAssign`` statements. Used by rule 7 (symbols
    absent from render) and its companion (symbols present in doctor)."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


# --------------------------------------------------------------------------- #
# Rule checkers — each takes an AST (+ optional source) and returns a list of
# human-readable violation strings. An empty list means the rule holds. Keeping
# them pure lets the non-vacuity suite feed them deliberately-broken snippets.
# --------------------------------------------------------------------------- #


def _enclosing_funcdef_names(tree, target):
    """All enclosing FunctionDef names of ``target``, innermost-first.

    Walking the full ancestor chain (not just the innermost function) lets a
    caller pass if ANY enclosing scope bears the wanted role prefix — so a read
    inside a closure nested in a ``cfg_`` function is correctly attributed to the
    ``cfg_`` ancestor. Returns ``[]`` when ``target`` is at module level.
    """
    enclosing = []
    for func in ast.walk(tree):
        if isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(func):
                if child is target:
                    enclosing.append(func)
                    break
    # ast.walk yields outer functions before inner ones; reverse to innermost-first.
    return [f.name for f in reversed(enclosing)]


def _import_modules_from_node(node):
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module:
        return [f"urllib.{alias.name}" if node.module == "urllib" else node.module
                for alias in node.names]
    return []


def _imported_modules(tree):
    """Yield imported module names from every scope in an AST."""
    for node in ast.walk(tree):
        yield from _import_modules_from_node(node)


def _module_family(relpath):
    basename = os.path.basename(relpath)
    return next(
        (family for family in ("common", "claude", "cursor")
         if basename.startswith(f"{family}_") and basename.endswith(".py")),
        None,
    )


def check_import_direction(relpath, tree):
    """Enforce one-way shared-to-host dependency direction between module families."""
    family = _module_family(relpath) or ""
    forbidden = {
        "common": ("claude_", "cursor_"),
        "claude": ("cursor_",),
        "cursor": ("claude_",),
    }.get(family, ())
    return [
        f"{relpath}: forbidden import {module} from {family} family"
        for module in _imported_modules(tree)
        if module.startswith(forbidden)
    ]


_HOST_IMPORTERS = frozenset(
    {
        "tools/claude-status-line.py",
        "tools/cursor-status-line.py",
        "tools/setup.py",
        "tools/statusline-doctor.py",
    }
)


def check_host_importers(relpath, tree):
    """Only entrypoints and setup/doctor may import a host assembly module."""
    if relpath in _HOST_IMPORTERS:
        return []
    return [
        f"{relpath}: host module import {module} outside allowed entrypoints"
        for module in _imported_modules(tree)
        if module in {"claude_host", "cursor_host"}
    ]


def check_segment_ids(common_tree, host_tree):
    """Reject duplicate seg_* function names shared by common and one host."""
    common = {node.name for node in _top_functions(common_tree) if node.name.startswith("seg_")}
    host = {node.name for node in _top_functions(host_tree) if node.name.startswith("seg_")}
    return [f"duplicate segment id {name}" for name in sorted(common & host)]


def _inside_function(tree, target):
    return any(
        isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(child is target for child in ast.walk(parent))
        for parent in ast.walk(tree)
    )


def check_networking_imports(relpath, tree):
    """Keep networking imports inside Cursor quota functions only."""
    networking = {"urllib.request", "http.client", "http.server", "socket", "ssl"}
    violations = []
    for node in ast.walk(tree):
        modules = _import_modules_from_node(node)
        if (
            isinstance(node, ast.Call)
            and node.args
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            modules.append(node.args[0].value)
        for module in modules:
            if module in networking and not (
                relpath == "tools/cursor_quota.py" and _inside_function(tree, node)
            ):
                violations.append(
                    f"{relpath}:{getattr(node, 'lineno', 0)}: networking import {module}"
                )
    return violations


def check_legacy_references(files):
    """Find tracked references to retired entry/config names outside history."""
    entry = "status-" + "line" + r"\.py"
    config = "statusline" + r"\.toml"
    pattern = re.compile(r"(?<![\w-])(" + entry + "|" + config + ")")
    history = (
        ".planning/", "docs/superpowers/", "docs/prds/", "docs/refactor/",
        "docs/wizard-redesign/", "tests/fixtures/statusline_split/",
    )
    allow_line = re.compile(r"^_LEGACY_(ENTRY|TOML) = ")
    # A TEST constructing a legacy-named fixture (migration/pre-rename
    # coverage) names the retired entry on the same line as its 'legacy'
    #/'bak'/'backup' marker — that fixture is the point of the test, not a
    # stray retired reference.
    legacy_fixture = re.compile(r"legacy|\.bak|\.backup", re.IGNORECASE)
    hits = []
    for relpath, text in files:
        if relpath.startswith(history):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if relpath == "tools/setup.py" and allow_line.match(line):
                continue
            if relpath.startswith("tests/") and legacy_fixture.search(line):
                continue
            if pattern.search(line):
                hits.append(f"{relpath}:{number}: retired reference")
    return hits


def split_target_problems(rows=None):
    """Rows live at their target, except the documented ramp-default split."""
    if rows is None:
        with open(_AUDIT_PATH, encoding="ascii") as handle:
            _headers, rows = audit_rows(handle.read())
    return [
        f"{row.name}: module {row.module} differs from target {row.target}"
        for row in rows
        if row.module != row.target and row.name != "_RAMP_DEFAULTS"
    ]


def check_host_prefix_literals(relpath, tree):
    """Rule 1: host env-prefix code literals belong only in host modules."""
    if not relpath.startswith("tools/") or not relpath.endswith(".py"):
        return []
    host_module = relpath.endswith("_host.py")
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if (
            node.value.startswith(("CC_AI_KIT_", "AI_KIT_CURSOR_", "AI_KIT_SEGMENT_"))
            and not host_module
        ):
            violations.append(f"{relpath}:{node.lineno}: host prefix literal outside host module")
    return violations


def check_no_typed_model_subscript(tree):
    """Rule 2 (D4): no ``Subscript`` *load* whose value is a bare typed-model Name
    (``ctx``/``line_conf``). Attribute-then-subscript (illustratively ``ctx.raw[...]``)
    is exempt because the subscript's value is an Attribute, not a guarded Name —
    that exempt form is shown for shape and need not appear in the live source."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.ctx, ast.Load):
            continue
        value = node.value
        if isinstance(value, ast.Name) and value.id in _TYPED_MODEL_NAMES:
            violations.append(
                f"subscript on typed model {value.id!r} at line {node.lineno} "
                f"(use attribute access — D4)"
            )
    return violations


def check_bookkeeping_readers(tree):
    """Rule 3: only ``seg_render_time``/``seg_slowest`` may read render
    bookkeeping (``ctx.slowest``/``ctx.t_start``, or a bare ``t_start`` Name).
    Asserts no *other* ``seg_*`` function references them."""
    violations = []
    for func in _top_functions(tree):
        if not func.name.startswith("seg_"):
            continue
        if func.name in _BOOKKEEPING_READERS:
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.Attribute) and node.attr in _BOOKKEEPING_ATTRS:
                violations.append(
                    f"{func.name} reads bookkeeping .{node.attr} at line {node.lineno}"
                )
            elif (
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id in _BOOKKEEPING_ATTRS
            ):
                violations.append(
                    f"{func.name} reads bookkeeping Name {node.id} at line {node.lineno}"
                )
    return violations


def check_seg_signature(tree):
    """Rule 4: every top-level ``seg_*`` (including ``seg_alt_*``) takes exactly
    ``(ctx, avail, theme)`` positional args."""
    violations = []
    for func in _top_functions(tree):
        if not func.name.startswith("seg_"):
            continue
        names = [arg.arg for arg in func.args.args]
        if names != _SEG_SIGNATURE:
            violations.append(f"{func.name} has args {names}, expected {_SEG_SIGNATURE}")
    return violations


def check_defaults_data_only(tree, source):
    """Rule 5: the DEFAULTS banner precedes the first ``cfg_`` def, and the
    DEFAULTS block defines no ``cfg_``/``probe_`` function (it is data-only —
    constants and type declarations, no config/probe logic)."""
    violations = []
    blocks = _banner_blocks(source)
    defaults = next((b for b in blocks if b[1] == "DEFAULTS"), None)
    if defaults is None:
        return ["no DEFAULTS banner block found"]
    _, _, defaults_start, defaults_end = defaults

    first_cfg = min(
        (f.lineno for f in _top_functions(tree) if f.name.startswith("cfg_")),
        default=None,
    )
    if first_cfg is None:
        violations.append("no cfg_ function found")
    elif defaults_start >= first_cfg:
        violations.append(
            f"DEFAULTS banner (line {defaults_start}) does not precede the first "
            f"cfg_ def (line {first_cfg})"
        )

    for func in _top_functions(tree):
        if defaults_start <= func.lineno <= defaults_end and func.name.startswith(
            ("cfg_", "probe_")
        ):
            violations.append(
                f"DEFAULTS block contains non-data def {func.name} at line {func.lineno}"
            )
    return violations


def check_defaults_where_present(tree, source):
    """Rule 5 for a module that may not have both a DEFAULTS banner and cfg_ defs.

    No DEFAULTS banner is vacuously fine. A banner that exists must contain no
    cfg_ or probe_ def. The banner-before-cfg_ order is checked only when the
    module also defines a cfg_ function, by reusing check_defaults_data_only.
    """
    blocks = _banner_blocks(source)
    defaults = next((block for block in blocks if block[1] == "DEFAULTS"), None)
    if defaults is None:
        return []
    has_cfg = any(func.name.startswith("cfg_") for func in _top_functions(tree))
    if has_cfg:
        return check_defaults_data_only(tree, source)
    violations = []
    _, _, defaults_start, defaults_end = defaults
    for func in _top_functions(tree):
        if defaults_start <= func.lineno <= defaults_end and func.name.startswith(
            ("cfg_", "probe_")
        ):
            violations.append(
                f"DEFAULTS block contains non-data def {func.name} at line {func.lineno}"
            )
    return violations


def check_role_prefix_integrity(tree, source):
    """Rule 6: each top-level function's prefix matches the banner block it lives
    in. SHELL (now the last named block) permits exactly ``main``/``safe_render``;
    DEFAULTS (1) and the trailing doc block (9) permit no role-prefixed defs.

    A single bare-underscore private helper (``_memo``) is exempt: a leading ``_``
    is Python's "private internal" convention, and role prefixes govern the public
    role surface, not one-off internals. (Dunder names are likewise exempt.)
    """
    violations = []
    blocks = _banner_blocks(source)
    for func in _top_functions(tree):
        # Private internal helper (`_x`) or dunder — not a role-bearing function.
        if func.name.startswith("_"):
            continue
        located = _block_for_line(blocks, func.lineno)
        if located is None:
            violations.append(f"{func.name} (line {func.lineno}) is in no banner block")
            continue
        index, role = located
        if role == "SHELL":
            if func.name not in _SHELL_ENTRYPOINTS:
                violations.append(
                    f"{func.name} in SHELL block must be a known entrypoint "
                    f"{sorted(_SHELL_ENTRYPOINTS)}"
                )
            continue
        expected = _BLOCK_PREFIX.get(index)
        # New split modules use role labels directly where their block numbering
        # differs from the original renderer's fixed layout.
        expected = {
            "UTIL": "util_",
            "CORE": "core_",
            "PROBE": "probe_",
            "DEFAULTS": None,
        }.get(role, expected)
        if role == "SHELL":
            expected = None
        if expected is None:
            violations.append(f"{func.name} lives in non-function block {index}.{role}")
        elif not func.name.startswith(expected):
            violations.append(f"{func.name} (block {index}.{role}) lacks prefix {expected!r}")
    return violations


def check_no_doctor_symbols(tree):
    """Rule 7 (FR-7): the render module defines none of the doctor/introspection
    symbols (as a FunctionDef/ClassDef or a module-level Assign target)."""
    return [
        f"render module defines doctor symbol {name!r}"
        for name in sorted(_defined_names(tree) & _DOCTOR_SYMBOLS)
    ]


def check_no_shell_true(tree):
    """Rule 8: no ``shell=`` keyword on a Call unless the value is the constant False."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg != "shell":
                continue
            allowed = isinstance(kw.value, ast.Constant) and kw.value.value is False
            if not allowed:
                violations.append(f"line {kw.lineno}: shell= must be constant False")
    return violations


# D-25: AST isolation between the session wake (Phase 26) and Phase 25's
# subprocess ladder. The wake package never imports the ladder's modules nor
# names its state writer or wait paths; the ladder's code never imports the
# wake package. Both directions get non-vacuity cases below.
_WAKE_SKILL = "skills/ai-kit-session-wake"
_PHASE25_SKILLS = (
    "skills/ai-kit-spec-review",
    "skills/ai-kit-spec-execute-gsd",
    "skills/ai-kit-spec-execute-superpowers",
    "skills/ai-kit-cross-ai",
)
_PHASE25_LADDER_PKGS = frozenset({"ai_kit_spec_gsd", "ai_kit_spec_superpowers"})
_WAKE_STATE_TOKEN = "write_resumable_state"


def _import_targets(node):
    """Module names one Import/ImportFrom node binds (the module, per alias
    for plain imports)."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module:
        return [node.module]
    return []


def check_wake_isolation(tree):
    """D-25 (wake side): no Phase 25 ladder import, no reference to its state
    writer (substring, so `write_resumable_state_fn` and
    `_cmd_write_resumable_state` are caught), no wait-path string (`cycles`
    or anything containing `spec/cycles`)."""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for target in _import_targets(node):
                root = target.split(".")[0]
                forbidden = (
                    root in _PHASE25_LADDER_PKGS
                    or target == "ai_kit_spec.cache"
                    or target.startswith("ai_kit_spec.cache.")
                )
                if forbidden:
                    violations.append(f"line {node.lineno}: forbidden import {target}")
            for alias in node.names:
                for name in (alias.name, alias.asname):
                    if name and _WAKE_STATE_TOKEN in name:
                        violations.append(f"line {node.lineno}: forbidden alias {name}")
            continue
        if isinstance(node, ast.Name) and _WAKE_STATE_TOKEN in node.id:
            violations.append(f"line {node.lineno}: forbidden name {node.id}")
        elif isinstance(node, ast.Attribute) and _WAKE_STATE_TOKEN in node.attr:
            violations.append(f"line {node.lineno}: forbidden attribute {node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _WAKE_STATE_TOKEN in node.value:
                violations.append(f"line {node.lineno}: forbidden Phase 25 name {node.value!r}")
            elif node.value == "cycles" or "spec/cycles" in node.value:
                violations.append(
                    f"line {node.lineno}: forbidden Phase 25 wait path {node.value!r}"
                )
    return violations


def check_no_wake_import(tree):
    """D-25 (ladder side): Phase 25's code never imports the session wake
    package or any submodule."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for target in _import_targets(node):
            if target == "ai_kit_session_wake" or target.startswith("ai_kit_session_wake."):
                violations.append(f"line {node.lineno}: session wake import {target}")
    return violations


def _parse_path(path):
    """Parse any repo file into an AST (never import or execute it)."""
    with open(path, encoding="utf-8") as handle:
        return ast.parse(handle.read(), filename=path)


def _iter_skill_python(rel_skill):
    """Every .py under one skill directory, sorted, stable."""
    root = os.path.join(_REPO_ROOT, rel_skill)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for filename in sorted(filenames):
            if filename.endswith(".py"):
                yield os.path.join(dirpath, filename)


# Rule 9: the only places allowed to swallow every exception. Each is a documented
# backstop that keeps one failure from blanking the status line or killing a TUI, or
# (curated-config apply) from crashing a committed apply, where SPEC R13 says only warn, or
# (staged-tests) from passing a commit on zero tests: a mapper failure runs the full groups.
_CURATED_APPLY = "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py"
_BROAD_EXCEPT_BACKSTOPS = frozenset(
    {
        (_CURATED_APPLY, "_cleanup_committed"),
        (_CURATED_APPLY, "_execute_apply"),
        ("tools/wizard_app.py", "_apply_housekeeping"),
        ("tools/wizard_app.py", "_run_commit"),
        ("tools/common_render.py", "core_safe_build"),
        ("tools/common_render.py", "core_render_checked"),
        ("tools/statusline-doctor.py", "cmd_doctor"),
        ("tools/config_doctor_checks.py", "apply_row"),
        ("tools/run_unittest_parallel.py", "_staged_selection"),
    }
)


def broad_except_sites(src):
    """Rule 9 helper: (line, enclosing function or None) for every comment that
    disables pylint's broad-exception-caught."""
    tree = ast.parse(src)
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    sites = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type != tokenize.COMMENT or "broad-exception-caught" not in tok.string:
            continue
        line = tok.start[0]
        enclosing = [f for f in funcs if f.lineno <= line <= (f.end_lineno or f.lineno)]
        inner = max(enclosing, key=lambda f: f.lineno, default=None)
        sites.append((line, inner.name if inner else None))
    return sites


def check_broad_except_allowlist(relpath, src):
    """Rule 9: a broad-exception-caught suppression only inside an allowlisted backstop."""
    return [
        f"{relpath}:{line}: broad-exception-caught suppressed outside a listed backstop"
        for line, func in broad_except_sites(src)
        if (relpath, func) not in _BROAD_EXCEPT_BACKSTOPS
    ]


# Built by concatenation so this file never contains a retired literal as a string constant.
_RETIRED_CURSOR = "cursor" + "-agent"
_RETIRED_FIELD = "native" + "_runtime"
_RETIRED_MODE = "native" + "_claude"
_RETIRED_LITERALS = {
    _RETIRED_CURSOR: frozenset({
        "skills/ai-kit-spec-review/ai_kit_spec/detection.py",
        # the tripwire stubs every host binary name, cursor-agent included
        "tools/run_unittest_parallel.py",
    }),
    _RETIRED_FIELD: frozenset({"skills/ai-kit-spec-review/ai_kit_spec/config_io.py"}),
    _RETIRED_MODE: frozenset(),
}


def check_retired_literals(relpath, tree):
    """Rule 10: retired runtime literals occur only in their explicit legacy map."""
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        allowed = _RETIRED_LITERALS.get(node.value)
        if allowed is not None and relpath not in allowed:
            hits.append(f"{relpath}:{node.lineno}: retired literal {node.value!r}")
    return hits


# Rule 11: one supervision core. A new process session is how a supervisor owns a
# killable group, so it may appear only in the runner and the two probes that are not
# supervisors (the opencode server probe, and the curated-config catalog probe).
_START_NEW_SESSION_ALLOWED = frozenset(
    {
        "skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py",
        "skills/ai-kit-spec-review/ai_kit_spec/detection.py",
        "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py",
        # Detached quota refresher; not a supervisor (D-13).
        "tools/cursor_quota.py",
        # The wake's single resume runs in its own session so the fire can
        # kill its whole group on RESUME_TIMEOUT_S (D-10 step 6; 26-02).
        "skills/ai-kit-session-wake/ai_kit_session_wake/fire.py",
        # The StopFailure hook's `arm --only-if-armed` child runs in its own session so the
        # hook can kill the whole group at its 8 s deadline (26-07; the same pattern as fire).
        "tools/hooks/claude_session_wake.py",
        # The test runner starts each module in its own session so a deadline or an interrupt
        # stops the module's whole group (SIGTERM, then SIGKILL); it supervises tests, not a
        # cross-AI run (28-02).
        "tools/run_unittest_parallel.py",
        # check-dogfood runs its three guard tests in one child session so a timeout stops the
        # whole group; it supervises tests, not a cross-AI run (28-04).
        "tools/check_dogfood.py",
    }
)
_SUPERVISOR_OWNER = "skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py"


def supervisor_spawn_count(tree):
    """How many calls start a new session with the constant True."""
    return len(check_one_supervisor("", tree))


def check_one_supervisor(relpath, tree):
    """Rule 11: a `start_new_session=True` call outside the allowlist is a second supervisor."""
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg != "start_new_session":
                continue
            if not (isinstance(kw.value, ast.Constant) and kw.value.value is True):
                continue
            hits.append(f"{relpath}:{kw.lineno}: start_new_session=True")
    if relpath in _START_NEW_SESSION_ALLOWED:
        return []
    return hits


def _is_main_guard(node):
    test = node.test if isinstance(node, ast.If) else None
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )


def check_thin_entry(tree):
    """Allow only imports, the module docstring, and the main guard."""
    return [
        f"unexpected top-level {type(node).__name__} at line {node.lineno}"
        for node in tree.body
        if not isinstance(node, (ast.Import, ast.ImportFrom, ast.If))
        and not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
    ]


def check_main_guard_last(relpath, tree):
    """Rule 12: a test module's `__main__` guard is its last statement, so running the file
    as a script never calls `unittest.main()` before the classes below it exist."""
    return [
        f"{relpath}:{node.lineno}: __main__ guard is not the last statement"
        for node in tree.body[:-1]
        if _is_main_guard(node)
    ]


# --------------------------------------------------------------------------- #
# Live-tree tests — every rule must pass against the real render module.
# --------------------------------------------------------------------------- #


class TestArchitecture(unittest.TestCase):
    """The seven FR-8.1 invariants, asserted against the live source tree."""

    @classmethod
    def setUpClass(cls):
        cls.render_tree, cls.render_src = _parse("common_config.py")
        cls.doctor_tree, cls.doctor_src = _parse("statusline-doctor.py")

    def test_rule1_host_prefix_literals_stay_in_host(self):
        violations = []
        for name, tree, _source in present_split_modules():
            violations.extend(check_host_prefix_literals(f"tools/{name}", tree))
        self.assertEqual([], violations)
        host_tree, _ = _parse("claude_host.py")
        self.assertEqual([], check_host_prefix_literals("tools/claude_host.py", host_tree))
        source_tree = ast.parse("value = 'CC_AI_KIT_CONFIG_FILE'")
        self.assertNotEqual([], check_host_prefix_literals("tools/common_config.py", source_tree))

    def test_rule2_to_7_on_each_split_module(self):
        for name, tree, source in present_split_modules():
            self.assertEqual([], check_no_typed_model_subscript(tree), name)
            self.assertEqual([], check_bookkeeping_readers(tree), name)
            self.assertEqual([], check_seg_signature(tree), name)
            self.assertEqual([], check_defaults_where_present(tree, source), name)
            self.assertEqual([], check_role_prefix_integrity(tree, source), name)
            self.assertEqual([], check_no_doctor_symbols(tree), name)

    def test_dependency_direction(self):
        violations = []
        for name, tree, _source in present_split_modules():
            violations.extend(check_import_direction(f"tools/{name}.py", tree))
        self.assertEqual([], violations)

    def test_host_importers(self):
        violations = []
        for filename in sorted(os.listdir(_TOOLS)):
            if filename.endswith(".py"):
                tree, _source = _parse(filename)
                violations.extend(check_host_importers(f"tools/{filename}", tree))
        self.assertEqual([], violations)
        self.assertEqual(2, sum(
            module.endswith("_host")
            for filename in ("claude-status-line.py", "cursor-status-line.py")
            for module in _imported_modules(_parse(filename)[0])
        ))

    def test_entry_is_thin(self):
        entry_tree, _source = _parse("claude-status-line.py")
        self.assertEqual([], check_thin_entry(entry_tree))

    def test_rule8_no_shell_true_in_spec_family(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        skills_root = os.path.join(repo_root, "skills")
        violations = []
        for skill_dir in sorted(os.listdir(skills_root)):
            if not skill_dir.startswith("ai-kit-spec-"):
                continue
            for dirpath, _dirnames, filenames in os.walk(os.path.join(skills_root, skill_dir)):
                for filename in filenames:
                    if not filename.endswith(".py"):
                        continue
                    path = os.path.join(dirpath, filename)
                    with open(path, encoding="utf-8") as handle:
                        tree = ast.parse(handle.read(), filename=path)
                    for msg in check_no_shell_true(tree):
                        violations.append(f"{os.path.relpath(path, repo_root)}: {msg}")
        self.assertEqual([], violations)

    def test_rule10_retired_literals_only_in_allowlist(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        violations = []
        seen_allowlist = set()
        for top in ("skills", "tools"):
            for dirpath, _dirnames, filenames in os.walk(os.path.join(repo_root, top)):
                for filename in filenames:
                    if not filename.endswith(".py"):
                        continue
                    path = os.path.join(dirpath, filename)
                    relpath = os.path.relpath(path, repo_root).replace(os.sep, "/")
                    with open(path, encoding="utf-8") as handle:
                        tree = ast.parse(handle.read(), filename=path)
                    violations.extend(check_retired_literals(relpath, tree))
                    strings = {
                        node.value
                        for node in ast.walk(tree)
                        if isinstance(node, ast.Constant) and isinstance(node.value, str)
                    }
                    # An allowlist entry counts only while its file still holds the literal.
                    if any(
                        relpath in allowed and literal in strings
                        for literal, allowed in _RETIRED_LITERALS.items()
                    ):
                        seen_allowlist.add(relpath)
        self.assertEqual([], violations)
        expected = set().union(*_RETIRED_LITERALS.values())
        self.assertEqual(expected, seen_allowlist)

    def test_rule11_one_supervisor(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        violations = []
        owner_count = 0
        for top in ("skills", "tools"):
            for dirpath, _dirnames, filenames in os.walk(os.path.join(repo_root, top)):
                for filename in filenames:
                    if not filename.endswith(".py"):
                        continue
                    path = os.path.join(dirpath, filename)
                    relpath = os.path.relpath(path, repo_root).replace(os.sep, "/")
                    with open(path, encoding="utf-8") as handle:
                        tree = ast.parse(handle.read(), filename=path)
                    violations.extend(check_one_supervisor(relpath, tree))
                    if relpath == _SUPERVISOR_OWNER:
                        owner_count = supervisor_spawn_count(tree)
        self.assertEqual([], violations)
        self.assertGreaterEqual(owner_count, 1)

    def test_rule12_main_guard_is_the_last_statement(self):
        tests_root = os.path.dirname(os.path.abspath(__file__))
        violations, guarded = [], 0
        for filename in sorted(os.listdir(tests_root)):
            if not (filename.startswith("test_") and filename.endswith(".py")):
                continue
            with open(os.path.join(tests_root, filename), encoding="utf-8") as handle:
                tree = ast.parse(handle.read(), filename=filename)
            violations += check_main_guard_last(f"tests/{filename}", tree)
            guarded += any(_is_main_guard(node) for node in tree.body)
        self.assertEqual([], violations)
        self.assertGreater(guarded, 0)

    def test_rule9_broad_except_only_in_listed_backstops(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        violations, seen = [], set()
        for top in ("tools", "skills"):
            for dirpath, _dirnames, filenames in os.walk(os.path.join(repo_root, top)):
                for filename in filenames:
                    if not filename.endswith(".py"):
                        continue
                    path = os.path.join(dirpath, filename)
                    relpath = os.path.relpath(path, repo_root).replace(os.sep, "/")
                    with open(path, encoding="utf-8") as handle:
                        src = handle.read()
                    violations += check_broad_except_allowlist(relpath, src)
                    seen.update((relpath, func) for _, func in broad_except_sites(src))
        self.assertEqual([], violations)
        # A listed backstop that no longer suppresses anything is a stale entry.
        self.assertEqual(set(), _BROAD_EXCEPT_BACKSTOPS - seen)

    def test_rule7b_doctor_symbols_present_in_doctor(self):
        """Companion to rule 7: the doctor symbols were EXTRACTED, not deleted.
        Every name in ``_DOCTOR_SYMBOLS`` must be defined in the doctor module
        (so rule 7's "absent from render" guarantee means "moved", not "lost")."""
        defined = _defined_names(self.doctor_tree)
        missing = sorted(_DOCTOR_SYMBOLS - defined)
        self.assertEqual(
            [],
            missing,
            f"doctor symbols absent from statusline-doctor.py: {missing}",
        )

    def test_seg_signature_check_is_non_empty(self):
        """Sanity: the segment-signature rule actually inspected segments (guards
        against a future rename silently emptying the seg_ population)."""
        seg_funcs = [
            func
            for module in ("common_segments.py", "claude_segments.py")
            for func in _top_functions(_parse(module)[0])
            if func.name.startswith("seg_")
        ]
        self.assertGreater(len(seg_funcs), 5)


# --------------------------------------------------------------------------- #
# Non-vacuity tests (FR-8.3) — feed each checker a deliberately-violating
# snippet and confirm it FLAGS the violation, proving the rule has teeth. The
# real source files are never mutated.
# --------------------------------------------------------------------------- #


def _git_binary_available():
    """Whether a git executable is runnable at all (clean-room containers lack one)."""
    try:
        proc = subprocess.run(["git", "--version"], capture_output=True, text=True,
                              check=False, cwd=_REPO_ROOT)
    except OSError:
        return False
    return proc.returncode == 0


def _pinned_blob_available():
    """Whether the audit's pinned historical base blob is reachable from the
    repository root. An installer shallow clone (`git clone --depth 1`) is a
    perfectly good work tree but cannot `git show` old blobs — history-dependent
    checks must skip there while current-tree checks stay active."""
    proc = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                          capture_output=True, text=True, check=False, cwd=_REPO_ROOT)
    if proc.returncode != 0 or proc.stdout.strip() != "true":
        return False
    try:
        with open(_AUDIT_PATH, encoding="ascii") as handle:
            headers, _rows = audit_rows(handle.read())
    except (OSError, UnicodeError, ValueError):
        return False
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{headers['base']}:{headers['base_path']}"],
        capture_output=True, text=True, check=False, cwd=_REPO_ROOT,
    )
    return probe.returncode == 0


def _inside_work_tree():
    """Whether the repo root is a git work tree (the clean-room container copies the tree
    without `.git`, so the binary alone is not enough for `git ls-files`)."""
    proc = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                          capture_output=True, text=True, check=False, cwd=_REPO_ROOT)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


GIT_BINARY_AVAILABLE = _git_binary_available()
GIT_WORK_TREE_AVAILABLE = GIT_BINARY_AVAILABLE and _inside_work_tree()
GIT_HISTORY_AVAILABLE = GIT_WORK_TREE_AVAILABLE and _pinned_blob_available()
CLEAN_ROOM_GIT_SKIP = "requires git history; unavailable in the clean-room container"
GIT_WORK_TREE_SKIP = "requires a git work tree; the clean-room container has no .git"


def _load_audit_fixture():
    with open(_AUDIT_PATH, encoding="ascii") as handle:
        headers, rows = audit_rows(handle.read())
    proc = subprocess.run(
        ["git", "show", f"{headers['base']}:{headers['base_path']}"],
        check=False,
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
    )
    if proc.returncode:
        raise AssertionError(f"git show failed: {proc.stderr}")
    return rows, base_definitions(proc.stdout)


_SPLIT_MODULES = (
    "common_types",
    "common_fmt",
    "common_config",
    "common_probe",
    "common_render",
    "common_segments",
    "claude_probes",
    "claude_payload",
    "claude_segments",
    "claude_host",
    "cursor_payload",
    "cursor_quota",
    "cursor_segments",
    "cursor_host",
)


def _rename_names(text, mapping):
    """Replace NAME tokens only. Same rule the stage mover uses to reverse renames."""
    if not text or not mapping:
        return text
    edits = []
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.NAME and tok.string in mapping and tok.start[0] == tok.end[0]:
            edits.append((tok.start, tok.end, mapping[tok.string]))
    if not edits:
        return text
    lines = text.splitlines(keepends=True)
    for (start_line, start_col), (_end_line, end_col), new in reversed(edits):
        line = lines[start_line - 1]
        lines[start_line - 1] = line[:start_col] + new + line[end_col:]
    return "".join(lines)


def _split_sources():
    """Source of each split module that exists, plus the monolith."""
    sources = {}
    for name in _SPLIT_MODULES:
        if name.startswith("cursor_"):
            continue
        path = os.path.join(_TOOLS, f"{name}.py")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                sources[name] = handle.read()
    with open(os.path.join(_TOOLS, "claude-status-line.py"), encoding="utf-8") as handle:
        sources["status-line"] = handle.read()
    host_path = os.path.join(_TOOLS, "claude_host.py")
    with open(host_path, encoding="utf-8") as handle:
        sources["claude_host"] = handle.read()
    return sources


def _public_name(row):
    return row.name if row.new_name == "-" else row.new_name


def _defs_by_name(source):
    return {name: node for name, _kind, _line, node in base_definitions(source)}


def split_hash_mismatches(include_generalized=False, rows=None, modules=None):
    """Moved rows whose AST, after reversing renames, differs from ``base_ast``.

    ``include_generalized=False`` checks ``reused`` rows. ``True`` also checks
    ``generalized`` and ``split`` rows.
    """
    if rows is None:
        with open(_AUDIT_PATH, encoding="ascii") as handle:
            _headers, rows = audit_rows(handle.read())
    if modules is None:
        modules = _split_sources()
    fates = {"reused", "generalized", "split"} if include_generalized else {"reused"}
    rename = {row.new_name: row.name for row in rows if row.new_name != "-"}
    restored = {
        name: _defs_by_name(_rename_names(source, rename)) for name, source in modules.items()
    }
    problems = []
    for row in rows:
        if row.fate not in fates:
            continue
        node = restored.get(row.module, {}).get(row.name)
        if node is None:
            problems.append(f"{row.name} missing from {row.module}")
            continue
        digest = ast_hash(node)
        if digest != row.base_ast:
            problems.append(f"{row.name} hash {digest} != {row.base_ast}")
    return problems


def split_location_problems(rows=None, modules=None):
    """Rows that are missing, duplicated, or stored in the wrong module."""
    if rows is None:
        with open(_AUDIT_PATH, encoding="ascii") as handle:
            _headers, rows = audit_rows(handle.read())
    if modules is None:
        modules = _split_sources()
    defined = {name: set(_defs_by_name(source)) for name, source in modules.items()}
    problems = []
    for row in rows:
        names = {row.name, _public_name(row)}
        hits = sorted(module for module, have in defined.items() if names & have)
        expected = [row.module]
        if hits != expected:
            problems.append(f"{row.name} found in {hits}, expected {expected}")
    return problems


def present_split_modules():
    """``(name, tree, source)`` for each split module that exists on disk."""
    found = []
    for name in _SPLIT_MODULES:
        path = os.path.join(_TOOLS, f"{name}.py")
        if os.path.isfile(path):
            tree, source = _parse(f"{name}.py")
            found.append((name, tree, source))
    return found


@unittest.skipUnless(GIT_HISTORY_AVAILABLE, CLEAN_ROOM_GIT_SKIP)
class TestSplitAudit(unittest.TestCase):
    """Keep the reviewed move map complete against its pinned source blob."""

    @classmethod
    def setUpClass(cls):
        with open(_AUDIT_PATH, encoding="ascii") as handle:
            cls.audit_text = handle.read()
        cls.headers, cls.rows = audit_rows(cls.audit_text)
        proc = subprocess.run(
            ["git", "show", f"{cls.headers['base']}:{cls.headers['base_path']}"],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode:
            raise AssertionError(f"git show failed: {proc.stderr}")
        cls.base_source = proc.stdout
        cls.definitions = base_definitions(cls.base_source)
        cls.modules = cls.headers["modules"].split()

    def test_complete_rows_and_source_order(self):
        self.assertEqual(182, len(self.rows))
        self.assertEqual(list(range(1, 183)), [row.number for row in self.rows])
        self.assertEqual([], check_audit_against_base(self.rows, self.definitions))

    def test_reviewed_classification_and_taint(self):
        self.assertEqual([], check_audit_columns(self.rows, self.modules))
        self.assertEqual([row.taint for row in self.rows], taint_map(self.base_source))
        self.assertEqual(134, sum(row.kind == "function" for row in self.rows))
        self.assertEqual(7, sum(row.kind == "class" for row in self.rows))
        self.assertEqual(41, sum(row.kind == "assign" for row in self.rows))
        theme = next(row for row in self.rows if row.name == "core_default_theme")
        self.assertEqual("generalized", theme.fate)
        self.assertIn("parameterless theme/config builders", theme.reason)
        self.assertIn("Plan 23-06 adds host/spec parameters", theme.reason)

    def test_table_is_ascii(self):
        self.assertTrue(self.audit_text.encode("ascii"))


class TestSplitModuleRules(unittest.TestCase):
    """Rules 2, 3, 4, 5, 6 and 7 on every split module that exists."""

    def test_rules_2_3_4_6_7(self):
        for name, tree, source in present_split_modules():
            self.assertEqual([], check_no_typed_model_subscript(tree), name)
            self.assertEqual([], check_bookkeeping_readers(tree), name)
            self.assertEqual([], check_seg_signature(tree), name)
            self.assertEqual([], check_role_prefix_integrity(tree, source), name)
            self.assertEqual([], check_no_doctor_symbols(tree), name)

    def test_rule5_where_present(self):
        for name, tree, source in present_split_modules():
            self.assertEqual([], check_defaults_where_present(tree, source), name)


class TestSplitConformance(unittest.TestCase):
    """Every moved definition matches the base blob and lives in one module."""

    def test_reused_hashes_match(self):
        self.assertEqual([], split_hash_mismatches())

    def test_locations(self):
        self.assertEqual([], split_location_problems())


class TestArchNonVacuity(unittest.TestCase):
    """Prove rules 1-7 catch real violations rather than passing vacuously."""

    def test_split_hash_flags_a_changed_statement(self):
        source = "def kept():\n    return 1\n"
        node = base_definitions(source)[0][3]
        row = AuditRow(
            1,
            "kept",
            "function",
            1,
            ast_hash(node),
            "1",
            "common_types",
            "common_types",
            "-",
            "y",
            "reused",
            "-",
            "snippet row for the hash twin",
        )
        changed = "def kept():\n    return 2\n"
        self.assertNotEqual([], split_hash_mismatches(False, [row], {"common_types": changed}))
        self.assertEqual([], split_hash_mismatches(False, [row], {"common_types": source}))

    def test_common_importing_host_is_flagged_in_all_scopes(self):
        for source in (
            "import claude_host\n",
            "def helper():\n    import cursor_host\n",
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import claude_payload\n",
        ):
            tree = ast.parse(source)
            self.assertNotEqual([], check_import_direction("tools/common_render.py", tree))
        clean = ast.parse("import os\n")
        self.assertEqual([], check_import_direction("tools/common_render.py", clean))

    def test_claude_importing_cursor_is_flagged(self):
        self.assertNotEqual(
            [], check_import_direction("tools/claude_host.py", ast.parse("import cursor_quota\n"))
        )

    def test_cursor_importing_claude_is_flagged(self):
        self.assertNotEqual(
            [], check_import_direction("tools/cursor_host.py", ast.parse("import claude_host\n"))
        )

    def test_foreign_host_importer_is_flagged(self):
        tree = ast.parse("from cursor_host import HOST\n")
        self.assertNotEqual([], check_host_importers("tools/common_render.py", tree))
        self.assertEqual([], check_host_importers("tools/setup.py", tree))

    def test_legacy_reference_checker_boundaries(self):
        old_entry = "status-" + "line.py"
        old_config = "statusline" + ".toml"
        examples = [
            ("docs/x.md", "mention " + old_entry),
            ("tools/setup.py", "_LEGACY_ENTRY = " + repr(old_entry)),
            ("tools/setup.py", "example = " + repr(old_entry)),
            ("docs/ok.md", "claude-status-line.py and cursor-statusline.toml"),
            (".planning/history.md", old_entry),
            ("docs/refactor/history.md", old_config),
        ]
        hits = check_legacy_references(examples)
        self.assertEqual(2, len(hits))
        self.assertTrue(any("docs/x.md" in hit for hit in hits))
        self.assertTrue(any("tools/setup.py" in hit for hit in hits))

    def test_legacy_fixture_lines_in_tests_are_allowed_but_not_unmarked_ones(self):
        # The allowance must have teeth BOTH ways: a test line that names the
        # retired entry AS a legacy/.bak fixture is the point of the test,
        # while a bare retired reference in a test is still flagged.
        old_entry = "status-" + "line.py"
        allowed = check_legacy_references([
            ("tests/test_setup.py", f'legacy = join(dir, "{old_entry}")'),
            ("tests/test_setup.py", f'backup = join(dir, "{old_entry}.bak")'),
        ])
        self.assertEqual([], allowed)
        flagged = check_legacy_references([
            ("tests/test_setup.py", f'path = "{old_entry}"'),
        ])
        self.assertEqual(1, len(flagged))

    def test_thin_entry_flags_a_definition(self):
        tree = ast.parse('"entry"\ndef extra():\n    return None\n')
        self.assertNotEqual([], check_thin_entry(tree))

    def test_split_location_flags_the_wrong_module(self):
        row = AuditRow(
            1,
            "kept",
            "function",
            1,
            "unused-hash",
            "1",
            "common_types",
            "common_types",
            "-",
            "y",
            "reused",
            "-",
            "snippet row for the location twin",
        )
        wrong = {"common_fmt": "def kept():\n    return 1\n"}
        self.assertNotEqual([], split_location_problems([row], wrong))
        right = {"common_types": "def kept():\n    return 1\n"}
        self.assertEqual([], split_location_problems([row], right))

    def test_split_module_rule_flags_a_doctor_symbol(self):
        tree = ast.parse("def cmd_doctor():\n    return 1\n")
        self.assertNotEqual([], check_no_doctor_symbols(tree))

    @unittest.skipUnless(GIT_HISTORY_AVAILABLE, CLEAN_ROOM_GIT_SKIP)
    def test_audit_detects_removed_row(self):
        rows, definitions = _load_audit_fixture()
        self.assertTrue(check_audit_against_base(rows[:-1], definitions))

    @unittest.skipUnless(GIT_HISTORY_AVAILABLE, CLEAN_ROOM_GIT_SKIP)
    def test_audit_detects_wrong_hash(self):
        rows, definitions = _load_audit_fixture()
        rows[0] = rows[0]._replace(base_ast="000000000000")
        self.assertTrue(check_audit_against_base(rows, definitions))

    @unittest.skipUnless(GIT_HISTORY_AVAILABLE, CLEAN_ROOM_GIT_SKIP)
    def test_audit_detects_swapped_order(self):
        rows, definitions = _load_audit_fixture()
        rows[0], rows[1] = rows[1], rows[0]
        self.assertTrue(check_audit_against_base(rows, definitions))

    def test_audit_keeps_same_named_definitions_adjacent(self):
        definitions = base_definitions("def x(): pass\nclass x: pass\n")
        self.assertEqual(
            [("x", "function"), ("x", "class")], [(name, kind) for name, kind, _, _ in definitions]
        )

    @unittest.skipUnless(GIT_HISTORY_AVAILABLE, CLEAN_ROOM_GIT_SKIP)
    def test_audit_checks_disagreement_prefixes(self):
        row = _load_audit_fixture()[0][0]
        tainted = row._replace(taint="seed", neutral="y", reason="missing")
        untainted = row._replace(taint="-", neutral="n", reason="missing")
        self.assertTrue(check_audit_reasons([tainted]))
        self.assertTrue(check_audit_reasons([untainted]))

    def test_segment_ids_are_unique_per_host(self):
        common, _ = _parse("common_segments.py")
        for host_name in ("claude_segments.py", "cursor_segments.py"):
            host, _ = _parse(host_name)
            self.assertEqual([], check_segment_ids(common, host), host_name)

    def test_networking_imports_are_confined(self):
        violations = []
        for filename in sorted(os.listdir(_TOOLS)):
            if filename.endswith(".py"):
                tree, _source = _parse(filename)
                violations.extend(check_networking_imports(f"tools/{filename}", tree))
        self.assertEqual([], violations)
        quota_tree, _ = _parse("cursor_quota.py")
        self.assertTrue(any(
            "urllib.request" in module and _inside_function(quota_tree, node)
            for node in ast.walk(quota_tree)
            for module in (
                [node.args[0].value]
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "import_module"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                else _import_modules_from_node(node)
            )
        ))

    def test_cursor_host_prefix_literals(self):
        for name, tree, _source in present_split_modules():
            if name.startswith("cursor_"):
                self.assertEqual([], check_host_prefix_literals(f"tools/{name}.py", tree))
        bad = ast.parse("value = 'AI_KIT_CURSOR_CONFIG_FILE'\n")
        self.assertNotEqual([], check_host_prefix_literals("tools/cursor_segments.py", bad))

    def test_audit_rows_are_at_their_target(self):
        self.assertEqual([], split_target_problems())

    @unittest.skipUnless(GIT_WORK_TREE_AVAILABLE, GIT_WORK_TREE_SKIP)
    def test_legacy_references_live_tree(self):
        repo_root = _REPO_ROOT
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=repo_root, check=True, capture_output=True, text=True
        ).stdout.splitlines()
        pairs = []
        for relpath in tracked:
            path = os.path.join(repo_root, relpath)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            try:
                with open(path, encoding="utf-8") as handle:
                    pairs.append((relpath, handle.read()))
            except (OSError, UnicodeError):
                continue
        self.assertEqual([], check_legacy_references(pairs))

    def test_rule2_flags_subscript_on_typed_model(self):
        bad = ast.parse("x = ctx['model_name']\n")
        bad_conf = ast.parse("y = line_conf['git']\n")
        good = ast.parse("x = ctx.raw['model_name']\n")  # attribute-then-subscript
        self.assertNotEqual([], check_no_typed_model_subscript(bad))
        self.assertNotEqual([], check_no_typed_model_subscript(bad_conf))
        self.assertEqual([], check_no_typed_model_subscript(good))

    def test_rule3_flags_bookkeeping_read_in_other_segment(self):
        bad = ast.parse("def seg_path(ctx, avail, theme):\n    return ctx.slowest\n")
        bad_bare_name = ast.parse(
            "def seg_path(ctx, avail, theme):\n"
            "    return t_start\n"  # bare Name read — the .attr-less branch
        )
        allowed = ast.parse(
            "def seg_slowest(ctx, avail, theme):\n"
            "    return ctx.slowest\n"  # one of the two permitted readers
        )
        self.assertNotEqual([], check_bookkeeping_readers(bad))
        self.assertNotEqual([], check_bookkeeping_readers(bad_bare_name))
        self.assertEqual([], check_bookkeeping_readers(allowed))

    def test_rule4_flags_wrong_segment_signature(self):
        bad = ast.parse("def seg_bad(ctx, theme):\n    return ''\n")
        good = ast.parse("def seg_ok(ctx, avail, theme):\n    return ''\n")
        self.assertNotEqual([], check_seg_signature(bad))
        self.assertEqual([], check_seg_signature(good))

    def test_rule5_where_present_ignores_a_module_without_a_banner(self):
        src = "def cfg_real(env):\n    return env\n"
        self.assertEqual([], check_defaults_where_present(ast.parse(src), src))
        banner = "# ═══ 1. DEFAULTS — data ═══\ndef probe_sneaky():\n    return 1\n"
        self.assertNotEqual([], check_defaults_where_present(ast.parse(banner), banner))

    def test_rule5_flags_cfg_def_inside_defaults(self):
        src = (
            "# ═══ 2. DEFAULTS — data ═══\n"
            "X = 1\n"
            "def cfg_sneaky(env):\n"
            "    return env\n"
            "# ═══ 3. cfg_ — config ═══\n"
            "def cfg_real(env):\n"
            "    return env\n"
        )
        bad = ast.parse(src)
        self.assertNotEqual([], check_defaults_data_only(bad, src))
        good_src = (
            "# ═══ 2. DEFAULTS — data ═══\n"
            "X = 1\n"
            "# ═══ 3. cfg_ — config ═══\n"
            "def cfg_real(env):\n"
            "    return env\n"
        )
        self.assertEqual([], check_defaults_data_only(ast.parse(good_src), good_src))

    def test_rule6_flags_misplaced_prefix(self):
        src = (
            "# ═══ 4. fmt_ — formatters ═══\n"
            "def util_misplaced(x):\n"  # util_ in the fmt_ block
            "    return x\n"
        )
        bad = ast.parse(src)
        self.assertNotEqual([], check_role_prefix_integrity(bad, src))
        good_src = "# ═══ 4. fmt_ — formatters ═══\ndef fmt_ok(x):\n    return x\n"
        self.assertEqual([], check_role_prefix_integrity(ast.parse(good_src), good_src))

    def test_rule6_flags_unknown_shell_entrypoint(self):
        """SHELL block (1) permits only main/safe_render; any other (non-``_``)
        def there is flagged."""
        src = (
            "# ═══ 1. SHELL — entrypoints ═══\n"
            "def run_everything():\n"  # not main/safe_render
            "    return 0\n"
        )
        self.assertNotEqual([], check_role_prefix_integrity(ast.parse(src), src))
        good_src = "# ═══ 1. SHELL — entrypoints ═══\ndef main():\n    return 0\n"
        self.assertEqual([], check_role_prefix_integrity(ast.parse(good_src), good_src))

    def test_rule6_flags_def_in_non_function_block(self):
        """A role-prefixed def landing in a non-function block (DEFAULTS=1 or the
        trailing doc block=9) — blocks with no entry in ``_BLOCK_PREFIX`` — is
        flagged as living in a non-function block."""
        defaults_src = (
            "# ═══ 1. DEFAULTS — data ═══\n"
            "def cfg_stray(env):\n"  # any def at all is wrong here
            "    return env\n"
        )
        doc_src = "# ═══ 9. DOCS — trailing ═══\ndef seg_stray(ctx, avail, theme):\n    return ''\n"
        self.assertNotEqual([], check_role_prefix_integrity(ast.parse(defaults_src), defaults_src))
        self.assertNotEqual([], check_role_prefix_integrity(ast.parse(doc_src), doc_src))

    def test_rule7_flags_doctor_symbol_in_render(self):
        bad = ast.parse("def cmd_doctor():\n    return 0\n")
        bad_assign = ast.parse("_DOCTOR_SAMPLE = {}\n")
        good = ast.parse("def core_render(ctx, cfg, theme):\n    return []\n")
        self.assertNotEqual([], check_no_doctor_symbols(bad))
        self.assertNotEqual([], check_no_doctor_symbols(bad_assign))
        self.assertEqual([], check_no_doctor_symbols(good))

    def test_rule8_flags_shell_true(self):
        bad_true = ast.parse("subprocess.run(x, shell=True)\n")
        bad_var = ast.parse("run(x, shell=flag)\n")
        good = ast.parse("run(x, shell=False)\n")
        self.assertEqual(1, len(check_no_shell_true(bad_true)))
        self.assertEqual(1, len(check_no_shell_true(bad_var)))
        self.assertEqual([], check_no_shell_true(good))

    def test_rule10_flags_retired_literal(self):
        bad = ast.parse(f'x = "{_RETIRED_CURSOR}"')
        binary = ast.parse(f'x = "{_RETIRED_CURSOR} -p"')
        allowlisted = "skills/ai-kit-spec-review/ai_kit_spec/detection.py"
        self.assertEqual(1, len(check_retired_literals("skills/other.py", bad)))
        self.assertEqual([], check_retired_literals(allowlisted, bad))
        self.assertEqual([], check_retired_literals("skills/other.py", binary))
        retired = ast.parse(f'x = "{_RETIRED_FIELD}"')
        config_io = "skills/ai-kit-spec-review/ai_kit_spec/config_io.py"
        self.assertEqual(1, len(check_retired_literals("skills/other.py", retired)))
        self.assertEqual([], check_retired_literals(config_io, retired))
        mode = ast.parse(f'x = "{_RETIRED_MODE}"')
        dispatch = (
            "skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py"
        )
        self.assertEqual(1, len(check_retired_literals(dispatch, mode)))
        self.assertEqual(1, len(check_retired_literals("skills/other.py", mode)))

    def test_rule11_flags_a_second_supervisor(self):
        bad = ast.parse('subprocess.Popen(["x"], start_new_session=True)\n')
        self.assertEqual(1, len(check_one_supervisor("skills/other.py", bad)))
        self.assertEqual([], check_one_supervisor(_SUPERVISOR_OWNER, bad))
        self.assertEqual(0, supervisor_spawn_count(ast.parse("x = 1\n")))
        variable = ast.parse('subprocess.Popen(["x"], start_new_session=flag)\n')
        self.assertEqual([], check_one_supervisor("skills/other.py", variable))

    def test_rule12_flags_an_early_main_guard(self):
        early = ast.parse('if __name__ == "__main__":\n    main()\n\nclass TestLate:\n    pass\n')
        last = ast.parse('class TestA:\n    pass\n\nif __name__ == "__main__":\n    main()\n')
        self.assertEqual(1, len(check_main_guard_last("tests/test_x.py", early)))
        self.assertEqual([], check_main_guard_last("tests/test_x.py", last))
        self.assertEqual([], check_main_guard_last("tests/test_x.py", ast.parse("x = 1\n")))

    def test_rule9_flags_unlisted_broad_except(self):
        src = (
            "def apply_row():\n"
            "    try:\n"
            "        pass\n"
            "    except Exception:  # pylint: disable=broad-exception-caught\n"
            "        pass\n"
        )
        self.assertEqual([], check_broad_except_allowlist("tools/config_doctor_checks.py", src))
        self.assertEqual(1, len(check_broad_except_allowlist("tools/other.py", src)))
        renamed = src.replace("apply_row", "helper")
        flagged = check_broad_except_allowlist("tools/config_doctor_checks.py", renamed)
        self.assertEqual(1, len(flagged))

    def test_wake_isolation_flags_phase25_reach(self):
        # Each shape the D-25 rule exists to catch, including the two real
        # Phase 25 names caught only by substring (the attribute and the
        # string literal).
        flagged = (
            "from ai_kit_spec_gsd.cli import write_resumable_state\n",
            "import ai_kit_spec.cache\n",
            "x = state.write_resumable_state\n",
            "deps.write_resumable_state_fn(path, state)\n",
            'f = "_cmd_write_resumable_state"\n',
            'p = os.path.join(root, "spec", "cycles")\n',
            'p = "ai-kit/spec/cycles/x"\n',
        )
        for source in flagged:
            self.assertNotEqual([], check_wake_isolation(ast.parse(source)))
        for clean in (
            "from ai_kit_spec.detection import RUNTIMES\n",
            "x = state.write_json_atomic\n",
        ):
            self.assertEqual([], check_wake_isolation(ast.parse(clean)))

    def test_no_wake_import_flags_phase25_code(self):
        self.assertNotEqual(
            [], check_no_wake_import(ast.parse("import ai_kit_session_wake.cli\n"))
        )
        self.assertNotEqual(
            [], check_no_wake_import(ast.parse("from ai_kit_session_wake import fire\n"))
        )
        self.assertEqual([], check_no_wake_import(ast.parse("import json\n")))


class TestSessionWakeIsolation(unittest.TestCase):
    """D-25 live-tree checks: the session wake and Phase 25's subprocess
    ladder never reach into each other's state. AST only: parse, never
    import the checked modules."""

    def test_wake_package_never_reaches_phase25(self):
        scanned, violations = 0, []
        for path in _iter_skill_python(_WAKE_SKILL):
            scanned += 1
            for problem in check_wake_isolation(_parse_path(path)):
                violations.append(f"{os.path.relpath(path, _REPO_ROOT)}: {problem}")
        self.assertGreater(scanned, 0)
        self.assertEqual([], violations)

    def test_phase25_never_imports_the_wake(self):
        scanned, violations = 0, []
        for skill in _PHASE25_SKILLS:
            for path in _iter_skill_python(skill):
                scanned += 1
                for problem in check_no_wake_import(_parse_path(path)):
                    violations.append(f"{os.path.relpath(path, _REPO_ROOT)}: {problem}")
        self.assertGreater(scanned, 0)
        self.assertEqual([], violations)

    def test_runner_template_names_no_wake(self):
        template = os.path.join(
            _REPO_ROOT, "skills", "ai-kit-spec-review", "references", "cross-ai.mjs"
        )
        with open(template, encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn("ai_kit_session_wake", text)
        self.assertNotIn("ai-kit-session-wake", text)

    def test_rule8_covers_wake_and_hooks(self):
        # Rule 8 extended: the wake package and every tools/hooks/*.py script
        # (the 26-07 hook joins with no edit here). The scanned set must be
        # non-empty, so the rule is never vacuous.
        hook_paths = sorted(
            os.path.join(_REPO_ROOT, "tools", "hooks", name)
            for name in os.listdir(os.path.join(_REPO_ROOT, "tools", "hooks"))
            if name.endswith(".py")
        )
        paths = list(_iter_skill_python(_WAKE_SKILL)) + hook_paths
        self.assertGreater(len(paths), 0)
        violations = []
        for path in paths:
            for problem in check_no_shell_true(_parse_path(path)):
                violations.append(f"{os.path.relpath(path, _REPO_ROOT)}: {problem}")
        self.assertEqual([], violations)


class TestSegmentInventory(unittest.TestCase):
    """Segment inventory: coverage, line-mirror, and icon-mirror (Task 7)."""

    # Reviewed mirror of the seg_* inline glyphs; "" means no static icon.
    EXPECTED_ICONS = {
        "path": "",
        "git_branch": "🌿",
        "git_dirty": "",
        "alt_git_worktree": "⎇",
        "todo": "📝",
        "model": "",
        "alt_time_ago": "",
        "alt_time_clock": "⏰",
        "effort": "🧠",
        "lines": "📃",
        "alt_cost": "🪙",
        "alt_time_session": "💬",
        "alt_time_api": "📡",
        "render_time": "⏱",
        "slowest": "🐌",
        "alt_term_dimensions": "",
        "context": "📊",
        "chat_size": "💾",
        "alt_process_memory": "🧮",
        "alt_h_rate_limit": "⚡",
        "alt_w_rate_limit": "⚡",
    }
    # Icon single-sourcing into the inventory is DEFERRED per the PRD; until then
    # the inventory icon is hand-mirrored and this test pins it to the reviewed map.

    # Cursor-only built-ins reviewed against the Cursor oracle vocabulary (D-04).
    EXPECTED_CURSOR_ICONS = {
        "cursor_included": "",
        "cursor_api": "",
        "cursor_extra": "",
        "cursor_reset": "",
    }

    def _line_index(self, layout, key):
        for i, ln in enumerate(layout):
            if key in ln.segments:
                return i
        raise AssertionError(f"{key} not in LAYOUT")

    def test_coverage_every_segment_has_entry(self):
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH, "claude")
        for key in claude_host.SEGMENTS:
            self.assertIn(key, inv, f"SEGMENTS key {key} missing from inventory")

    def test_line_mirror(self):
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH, "claude")
        for key in claude_host.SEGMENTS:
            self.assertEqual(
                inv[key]["line"], self._line_index(claude_host.LAYOUT, key),
                f"{key} inventory line != LAYOUT line")

    def test_icon_mirror(self):
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH, "claude")
        for key, icon in self.EXPECTED_ICONS.items():
            self.assertEqual(inv[key]["icon"], icon, f"{key} inventory icon != reviewed glyph")

    def test_cursor_coverage_every_segment_has_entry(self):
        # D-04: the per-host inventory dimension — every Cursor SEGMENTS key
        # must have an entry listing hosts = ["cursor"] (or both hosts).
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH, "cursor")
        for key in cursor_host.SEGMENTS:
            self.assertIn(key, inv, f"cursor SEGMENTS key {key} missing from inventory")

    def test_cursor_line_mirror(self):
        # Each Cursor entry's `line` must be the Cursor layout row (from
        # `cursor_line`, or the shared `line` when both hosts list the entry).
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH, "cursor")
        for key in cursor_host.SEGMENTS:
            self.assertEqual(
                inv[key]["line"], self._line_index(cursor_host.LAYOUT, key),
                f"{key} cursor inventory line != cursor LAYOUT line")

    def test_cursor_icon_mirror(self):
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH, "cursor")
        for key, icon in self.EXPECTED_CURSOR_ICONS.items():
            self.assertEqual(inv[key]["icon"], icon,
                             f"{key} cursor inventory icon != reviewed glyph")

    def test_hosts_dimension_filters_entries(self):
        # A Claude-only entry never leaks into the Cursor view and vice versa.
        claude_inv = setup.load_segment_inventory(setup.INVENTORY_PATH, "claude")
        cursor_inv = setup.load_segment_inventory(setup.INVENTORY_PATH, "cursor")
        self.assertNotIn("todo", cursor_inv)   # claude-only
        for key in self.EXPECTED_CURSOR_ICONS:
            self.assertNotIn(key, claude_inv)  # cursor-only


if __name__ == "__main__":
    unittest.main()
