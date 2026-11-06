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
import functools
import hashlib
import importlib.util
import io
import json
import os
import re
import shlex
import subprocess
import sys
import textwrap
import tokenize
import unittest
from typing import NamedTuple, TypeGuard

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


@functools.cache
def _read_tree(path):
    """``(tree, source)`` of one repo file, read and parsed once per run. Rules only read the
    tree; the non-vacuity snippets call ast.parse themselves and never come through here."""
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    return ast.parse(source, filename=path), source


def tearDownModule():
    # Freeing the cached trees during interpreter exit cost about 3 s; free them here instead.
    _read_tree.cache_clear()


def _parse(name):
    """Parse a tools/ module into an AST, attaching its banner block map.

    Returns ``(tree, source)`` so callers can inspect both the parse tree and
    the raw text (the banner blocks are comments and thus not in the AST).
    """
    return _read_tree(os.path.join(_TOOLS, name))


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


# SPEC R1 / D-11: the one folding policy. Each rule is pinned by a stable phrase, not by Markdown
# layout, so re-wrapping, reordering and a list turned into a paragraph keep the check green, while
# a removed rule is named.
_FOLD_SKILL = "skills/ai-kit-commit-fold"
_FOLD_POLICY = os.path.join(_REPO_ROOT, _FOLD_SKILL, "references", "folding-policy.md")
POLICY_RULES = {
    "FOLD-1": r"one commit per logical feature",
    "FOLD-2": r"never one squash per plan or per phase",
    "FOLD-3": r"code with its tests and docs",
    "FOLD-4": r"tree equals the tested tree before the branch moves",
    "FOLD-5": r"local backup tag before the branch moves",
    "FOLD-6": r"deleted when the unit's pr merges",
    "FOLD-7": r"no `?reset --hard`?",
    "FOLD-8": r"reachable from main .* never rewritten",
    "FOLD-9": r"only with `?--force-with-lease`?",
    "FOLD-10": r"primary remote only",
    "FOLD-11": r"needs no confirmation",
}


def normalize_policy(text):
    """Lowercase, drop emphasis, headings and list markers, and collapse all whitespace."""
    plain = text.lower().replace("*", "").replace("#", "")
    return " ".join(re.sub(r"(?m)^\s*- ", "", plain).split())


def missing_policy_rules(text):
    """The rule ids whose stable phrase does not appear in the policy text."""
    plain = normalize_policy(text)
    return [rule for rule, phrase in POLICY_RULES.items() if not re.search(phrase, plain)]


def drop_policy_bullet(text, rule):
    """The policy text with one rule's single-line bullet removed."""
    return "\n".join(line for line in text.splitlines() if f"**{rule}**" not in line)


def reverse_policy_bullets(text):
    """The policy text with its rule bullets in reverse order and every other line in place."""
    lines = text.splitlines()
    slots = [i for i, line in enumerate(lines) if re.match(r"- \*\*FOLD-\d+\*\*", line)]
    for slot, bullet in zip(slots, [lines[i] for i in reversed(slots)], strict=True):
        lines[slot] = bullet
    return "\n".join(lines)


def rewrap_policy(text):
    """The policy text re-wrapped at 40 columns and joined into one paragraph."""
    wrapper = textwrap.TextWrapper(width=40, break_on_hyphens=False, break_long_words=False)
    return " ".join(wrapper.fill(text).splitlines())


# SPEC R4 / FOLD-7: fold code and instructions never reset hard. Flags the words in text, and the
# argv form in a list or tuple literal (`["git", "reset", "--hard", tip]`), so `update-ref` passes.
_RESET_HARD_TEXT = re.compile(r"\breset\s+--hard\b", re.IGNORECASE)


def check_no_reset_hard(relpath, text, tree=None):
    violations = []
    for match in _RESET_HARD_TEXT.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        violations.append(f"{relpath}:{line}: reset --hard")
    nodes = list(ast.walk(tree)) if tree is not None else []
    for node in nodes:
        if not isinstance(node, (ast.List, ast.Tuple)):
            continue
        words = [
            elt.value.lower()
            for elt in node.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        ]
        if "reset" in words and "--hard" in words[words.index("reset") + 1 :]:
            violations.append(f"{relpath}:{node.lineno}: argv reset --hard")
    return violations


# SPEC R1, R5, R8 / FLOW-02, FLOW-03: the unit flow's core (flow_*.py, fold_engine.py and
# fold_group.py) pushes only with a lease, from one site, to the primary remote, never squash,
# rebase or auto merges, and never names a framework. Each check walks string constants (or the
# text, for names) so a form is caught wherever it is written. The fold scripts are checked as
# files, not as a shell; the forms they can take are pinned by TestArchNonVacuity.
_FLOW_FORCE_FLAGS = frozenset({"--force", "-f"})
_FLOW_MERGE_FLAGS = frozenset({"--squash", "--rebase", "--auto"})
_FLOW_FRAMEWORK_NAME = re.compile(r"gsd|superpowers", re.IGNORECASE)


def _str_consts(tree):
    """(node, text) for every string constant in `tree`; empty when there is no tree."""
    found: list[tuple[ast.Constant, str]] = []
    for node in ast.walk(tree) if tree is not None else []:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.append((node, node.value))
    return found


def check_flow_force(relpath, text, tree=None):
    violations = []
    for node, value in _str_consts(tree):
        if value in _FLOW_FORCE_FLAGS or value.startswith("--force="):
            violations.append(f"{relpath}:{node.lineno}: forced push flag {value}")
        elif value.startswith("+") and ":" in value:
            violations.append(f"{relpath}:{node.lineno}: forced refspec {value}")
    for node in ast.walk(tree) if tree is not None else []:
        if not isinstance(node, ast.JoinedStr) or not node.values:
            continue
        head = node.values[0]
        if isinstance(head, ast.Constant) and str(head.value).startswith("+"):
            violations.append(f"{relpath}:{node.lineno}: forced refspec f-string")
    return violations


def check_flow_push_site(relpath, text, tree=None):
    if os.path.basename(relpath) == "flow_git.py":
        return []
    return [
        f"{relpath}:{node.lineno}: push outside flow_git.py"
        for node, value in _str_consts(tree)
        if value == "push"
    ]


def _flow_remote_allowed(relpath, tree):
    """ids of the origin literals that are allowed: the settings default and primary_remote."""
    allowed: set[int] = set()
    if tree is None:
        return allowed
    name = os.path.basename(relpath)
    if name == "flow_record.py":
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values, strict=True):
                if (isinstance(key, ast.Constant) and key.value == "remote"
                        and isinstance(value, ast.Constant)):
                    allowed.add(id(value))
    if name == "flow_git.py":
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "primary_remote":
                allowed.update(id(child) for child in ast.walk(node))
    return allowed


def check_flow_remote(relpath, text, tree=None):
    allowed = _flow_remote_allowed(relpath, tree)
    violations = [
        f"{relpath}:{node.lineno}: literal remote origin"
        for node, value in _str_consts(tree)
        if value == "origin" and id(node) not in allowed
    ]
    for node in ast.walk(tree) if tree is not None else []:
        if not isinstance(node, ast.List) or len(node.elts) < 3:
            continue
        first, second, third = node.elts[:3]
        if (isinstance(first, ast.Constant) and first.value == "git"
                and isinstance(second, ast.Constant) and second.value == "push"
                and isinstance(third, ast.Constant) and isinstance(third.value, str)):
            violations.append(f"{relpath}:{node.lineno}: git push to a constant remote")
    return violations


def check_flow_merge_method(relpath, text, tree=None):
    return [
        f"{relpath}:{node.lineno}: merge flag {value}"
        for node, value in _str_consts(tree)
        if value in _FLOW_MERGE_FLAGS
    ]


def check_flow_framework_names(relpath, text, tree=None):
    violations = []
    for match in _FLOW_FRAMEWORK_NAME.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        violations.append(f"{relpath}:{line}: framework name {match.group(0)}")
    return violations


def _flow_core_violations(check, framework=False):
    """One flow rule over the unit flow's code: flow_*.py, plus fold_engine and fold_group when
    `framework` is set (the framework-name rule covers the whole fold core)."""
    scripts = os.path.join(_REPO_ROOT, _FOLD_SKILL, "scripts")
    extra = {"fold_engine.py", "fold_group.py"} if framework else set()
    violations = []
    for filename in sorted(os.listdir(scripts)):
        if not filename.endswith(".py"):
            continue
        if not (filename.startswith("flow_") or filename in extra):
            continue
        tree, text = _read_tree(os.path.join(scripts, filename))
        violations.extend(check(f"{_FOLD_SKILL}/scripts/{filename}", text, tree))
    return violations


# SPEC R9 / D-13: no test builds a path into the repo's .planning/. A repo root is a name (or
# self/cls attribute) assigned from __file__ or from the cwd, the runner's cwd being the checkout.
# A temp project's own .planning/ is never flagged, because its root is not a repo root.
# This list must stay empty: a reader is moved to a temp copy or a frozen fixture, never listed.
PLANNING_READER_EXCEPTIONS: dict[str, str] = {}
_PLANNING_TEXT = re.compile(r"/?\.planning(/|$)")
_RELATIVE_PLANNING = re.compile(r"\.planning(/|$)")
_CWD_CALLS = frozenset({"Path.cwd", "pathlib.Path.cwd", "os.getcwd"})
_PATH_CALLS = frozenset({"Path", "pathlib.Path", "PurePath", "pathlib.PurePath"})
_JOIN_CALLS = frozenset({"os.path.join", "posixpath.join"})
_ROOT_WRAPPERS = _PATH_CALLS | _JOIN_CALLS | frozenset({
    "str", "os.fspath", "os.path.abspath", "os.path.realpath", "os.path.dirname",
    "os.path.normpath", "os.path.expanduser",
})
_FS_CALLS = _PATH_CALLS | frozenset({
    "open", "os.listdir", "os.scandir", "os.walk", "os.path.exists", "os.path.isfile",
    "os.path.isdir", "glob.glob", "glob.iglob", "shutil.copy", "shutil.copy2",
    "shutil.copyfile", "shutil.copytree",
})
_FS_METHODS = frozenset({
    "read_text", "read_bytes", "open", "exists", "is_file", "is_dir", "iterdir", "glob",
    "rglob", "stat", "write_text", "write_bytes", "unlink",
})


def _dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def _is_str_const(node, pattern):
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and pattern.match(node.value) is not None
    )


def _is_repo_rooted(node, roots, attrs):
    """True when the expression is a repo root or a path expression built on one."""
    if isinstance(node, ast.Name):
        return node.id in roots or node.id == "__file__"
    if isinstance(node, ast.Attribute):
        is_self_attr = (
            isinstance(node.value, ast.Name)
            and node.value.id in ("self", "cls")
            and node.attr in attrs
        )
        if is_self_attr:
            return True
        return _is_repo_rooted(node.value, roots, attrs)
    if isinstance(node, ast.Subscript):
        return _is_repo_rooted(node.value, roots, attrs)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _is_repo_rooted(node.left, roots, attrs)
    if isinstance(node, ast.Call):
        dotted = _dotted_name(node.func)
        if dotted in _CWD_CALLS:
            return True
        if dotted in _ROOT_WRAPPERS:
            return any(_is_repo_rooted(arg, roots, attrs) for arg in node.args)
        # a method on a rooted receiver: Path(__file__).resolve(), REPO_ROOT.joinpath("x")
        return isinstance(node.func, ast.Attribute) and _is_repo_rooted(
            node.func.value, roots, attrs
        )
    return False


def _is_relative_planning(node):
    """True for a relative .planning path expression (it resolves against the cwd)."""
    if _is_str_const(node, _RELATIVE_PLANNING):
        return True
    if isinstance(node, ast.Call) and _dotted_name(node.func) in _PATH_CALLS | _JOIN_CALLS:
        return bool(node.args) and _is_str_const(node.args[0], _RELATIVE_PLANNING)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _is_relative_planning(node.left)
    return False


def _planning_path_offence(node, roots, attrs):
    """True when this expression joins a repo root with a .planning part (any join form)."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _is_repo_rooted(node.left, roots, attrs) and _is_str_const(
            node.right, _PLANNING_TEXT
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return (
            _is_repo_rooted(node.left, roots, attrs) and _is_str_const(node.right, _PLANNING_TEXT)
        ) or (
            _is_repo_rooted(node.right, roots, attrs) and _is_str_const(node.left, _PLANNING_TEXT)
        )
    if isinstance(node, ast.JoinedStr):
        return any(
            isinstance(prev, ast.FormattedValue)
            and _is_repo_rooted(prev.value, roots, attrs)
            and _is_str_const(nxt, _PLANNING_TEXT)
            for prev, nxt in zip(node.values, node.values[1:], strict=False)
        )
    if not isinstance(node, ast.Call):
        return False
    dotted = _dotted_name(node.func)
    joins_root = dotted in _JOIN_CALLS | _PATH_CALLS and bool(node.args)
    if joins_root and _is_repo_rooted(node.args[0], roots, attrs):
        return any(_is_str_const(arg, _PLANNING_TEXT) for arg in node.args[1:])
    if isinstance(node.func, ast.Attribute) and node.func.attr == "joinpath":
        return _is_repo_rooted(node.func.value, roots, attrs) and any(
            _is_str_const(arg, _PLANNING_TEXT) for arg in node.args
        )
    return False


def _relative_planning_use(node):
    """True when a filesystem call (or a Path method) takes a relative .planning path."""
    if not isinstance(node, ast.Call):
        return False
    if _dotted_name(node.func) in _FS_CALLS:
        return bool(node.args) and _is_relative_planning(node.args[0])
    if isinstance(node.func, ast.Attribute) and node.func.attr in _FS_METHODS:
        return _is_relative_planning(node.func.value)
    return False


def _rooted_bindings(nodes, roots, attrs):
    """Names bound by plain assignment to a repo-rooted value (two passes: chained names)."""
    found = set(roots)
    assigns = [node for node in nodes if isinstance(node, ast.Assign)]
    for _ in range(2):
        for node in assigns:
            if _is_repo_rooted(node.value, found, attrs):
                found.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return frozenset(found)


def _class_repo_attrs(classdef, roots):
    """self.X / cls.X attributes a class assigns from a repo-rooted value (setUpClass too)."""
    attrs = set()
    for node in ast.walk(classdef):
        if not isinstance(node, ast.Assign) or not _is_repo_rooted(node.value, roots, attrs):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Attribute) or not isinstance(target.value, ast.Name):
                continue
            if target.value.id in ("self", "cls"):
                attrs.add(target.attr)
    return frozenset(attrs)


def _scan_planning_scope(node, roots, attrs, violations):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local = _rooted_bindings(ast.walk(child), roots, attrs)
            _scan_planning_scope(child, local, attrs, violations)
            continue
        if isinstance(child, ast.ClassDef):
            _scan_planning_scope(child, roots, attrs | _class_repo_attrs(child, roots), violations)
            continue
        if isinstance(child, ast.expr) and (
            _planning_path_offence(child, roots, attrs) or _relative_planning_use(child)
        ):
            violations.append(f"line {child.lineno}: {ast.unparse(child)[:80]}")
        _scan_planning_scope(child, roots, attrs, violations)


def planning_reader_exception_problems(exceptions):
    """SPEC R9: the exception list stays empty; each entry is a problem by itself."""
    return [f"{path}: {reason}" for path, reason in sorted(exceptions.items())]


def check_no_planning_reader(tree):
    """SPEC R9 / D-13: flag a path expression that joins a repo root (or the cwd) with the
    repo's .planning/, or a relative .planning path passed to a filesystem call. It sees literal
    path forms only; its run-time backstop is plan 28-08's long-path matrix environment, whose
    clone has no .planning/, so a reader this rule misses shows as a matrix difference."""
    module_roots = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            module_roots.update(
                alias.asname or alias.name
                for alias in node.names
                if re.search(r"ROOT|REPO", alias.name)
            )
    module_roots = _rooted_bindings(tree.body, module_roots, frozenset())
    violations = []
    _scan_planning_scope(tree, module_roots, frozenset(), violations)
    return violations


# SPEC R5 / D-05 static layer: no test names a host CLI as the program of a process-spawning call
# outside tests/host_fakes.py. Where each spawning API keeps its program: "argv" (subprocess
# family: element 0 of an argv list or tuple, or the first shlex word of a string), "arg0" or
# "arg1" (a string constant at that argument), "cmd" (the first shlex word of a command string).
HOST_FAKES_PATH = "tests/host_fakes.py"
_RUNNER_PATH = os.path.join(_REPO_ROOT, "tools", "run_unittest_parallel.py")
_SUBPROCESS_EXECUTABLE_CALLS = frozenset({
    "subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_call",
    "subprocess.check_output", "asyncio.create_subprocess_exec",
    "asyncio.create_subprocess_shell",
})
SPAWN_PROGRAM_POSITION = {
    **dict.fromkeys(
        ("subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_call",
         "subprocess.check_output"),
        "argv",
    ),
    **dict.fromkeys(
        (f"os.{name}" for name in (
            "execv", "execve", "execvp", "execvpe", "execl", "execle", "execlp", "execlpe",
            "posix_spawn", "posix_spawnp")),
        "arg0",
    ),
    "asyncio.create_subprocess_exec": "arg0",
    **dict.fromkeys(
        (f"os.{name}" for name in (
            "spawnv", "spawnve", "spawnvp", "spawnvpe", "spawnl", "spawnle", "spawnlp",
            "spawnlpe")),
        "arg1",
    ),
    **dict.fromkeys(("os.system", "os.popen", "asyncio.create_subprocess_shell"), "cmd"),
}


def _host_cli_names():
    """The runner's HOST_CLI_NAMES set, read with ast so the runner is never imported here."""
    tree = _read_tree(_RUNNER_PATH)[0]
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "HOST_CLI_NAMES" for t in node.targets):
            continue
        call = node.value
        if (isinstance(call, ast.Call) and _dotted_name(call.func) == "frozenset"
                and len(call.args) == 1):
            return frozenset(ast.literal_eval(call.args[0]))
        raise AssertionError(f"{_RUNNER_PATH}: HOST_CLI_NAMES must be frozenset({{literal set}})")
    raise AssertionError(f"{_RUNNER_PATH} has no module-level HOST_CLI_NAMES assignment")


def _constant_str(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _shell_program(text):
    """Basename of the first word of a command string; None when it is not a command."""
    try:
        words = shlex.split(text)
    except ValueError:
        return None
    return os.path.basename(words[0]) if words else None


def _program_argument(call, position):
    """The AST node holding the program of a spawning call, or None when it is not fixed."""
    if position == "argv":
        if call.args:
            return call.args[0]
        return next((kw.value for kw in call.keywords if kw.arg == "args"), None)
    index = 1 if position == "arg1" else 0
    return call.args[index] if len(call.args) > index else None


def _program_name(node, position):
    if position == "argv" and isinstance(node, (ast.List, ast.Tuple)):
        first = _constant_str(node.elts[0]) if node.elts else None
        return os.path.basename(first) if first else None
    text = _constant_str(node)
    if text is None:
        return None
    if position in ("argv", "cmd"):
        return _shell_program(text)
    return os.path.basename(text)


def _spawned_programs(call, bare_which):
    """(form, program basename) pairs that one call spawns, in the forms the rule names."""
    found = []
    callee = _dotted_name(call.func) or ""
    position = SPAWN_PROGRAM_POSITION.get(callee)
    if position is not None:
        program = _program_name(_program_argument(call, position), position)
        if program:
            found.append(("program", program))
    if callee in _SUBPROCESS_EXECUTABLE_CALLS:
        for kw in call.keywords:
            executable = _constant_str(kw.value) if kw.arg == "executable" else None
            if executable:
                found.append(("executable=", os.path.basename(executable)))
    if callee == "shutil.which" or (bare_which and callee == "which"):
        target = _constant_str(call.args[0]) if call.args else None
        if target:
            found.append(("shutil.which", os.path.basename(target)))
    return found


def check_no_host_cli_calls(tree, names):
    """SPEC R5 / D-05 static layer: flag a call that spawns a host CLI (basename in `names`) at
    its program position, through a literal `executable=` keyword, or through shutil.which.

    Only these call shapes are checked, so a host name in a data list or an assertion argument is
    never flagged. Known gap: an argv or an `executable=` value built in a variable is not seen
    statically; the run-time tripwire catches it when it resolves through PATH. An absolute host
    path built at run time is caught by neither, and tests/host_fakes.py is the sanctioned way to
    get host behaviour.
    """
    bare_which = any(
        isinstance(node, ast.ImportFrom) and node.module == "shutil"
        and any(alias.name == "which" for alias in node.names)
        for node in ast.walk(tree)
    )
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for form, program in _spawned_programs(node, bare_which):
            if program in names:
                violations.append(f"line {node.lineno}: {form} {program}")
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
    return _read_tree(path)[0]


def _iter_skill_python(rel_skill):
    """Every .py under one skill directory, sorted, stable."""
    root = os.path.join(_REPO_ROOT, rel_skill)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for filename in sorted(filenames):
            if filename.endswith(".py"):
                yield os.path.join(dirpath, filename)


# Phase 29 ruling 2 (SPEC R9): no skill or hook reaches into another skill's folder. A reach is
# a literal import of another skill's module, a sys.path shim onto its folder, a path string or
# joined path segment naming its folder, or a decide.py name (deleted in Phase 29). The one
# sanctioned reach is the installed-skill lookup: the value of a module-level JEV_ENTRY_REL
# assignment. Only literal forms are seen (a name held in a variable and joined later is not).
# skills/_shared/ is not a skill and is out of this rule (its reach is DIST-03's, Phase 52).
_LOOKUP_NAME = "JEV_ENTRY_REL"
_SYS_PATH_CALLS = frozenset({"sys.path.insert", "sys.path.append"})
_PATH_JOINERS = frozenset(
    {"os.path.join", "posixpath.join", "Path", "pathlib.Path", "PurePath", "pathlib.PurePath"}
)
_DECIDE_NAME = "decide.py"


def skill_folders(repo_root):
    """Every skill folder under skills/; names starting with `_` are not skills."""
    base = os.path.join(repo_root, "skills")
    return sorted(
        name
        for name in os.listdir(base)
        if not name.startswith("_") and os.path.isdir(os.path.join(base, name))
    )


def skill_modules(repo_root):
    """Top-level importable name -> skill folder: a package dir with __init__.py directly under
    skills/<s>/, or a .py stem directly under skills/<s>/ or skills/<s>/scripts/. First owner
    of a name wins."""
    base = os.path.join(repo_root, "skills")
    modules = {}
    for skill in skill_folders(repo_root):
        skill_dir = os.path.join(base, skill)
        for name in sorted(os.listdir(skill_dir)):
            path = os.path.join(skill_dir, name)
            if os.path.isdir(path) and os.path.isfile(os.path.join(path, "__init__.py")):
                modules.setdefault(name, skill)
            elif name.endswith(".py"):
                modules.setdefault(name[:-3], skill)
        scripts = os.path.join(skill_dir, "scripts")
        if os.path.isdir(scripts):
            for name in sorted(os.listdir(scripts)):
                if name.endswith(".py"):
                    modules.setdefault(name[:-3], skill)
    return {name: skill for name, skill in modules.items() if name.isidentifier()}


def _lookup_value(node):
    """The value of a module-level JEV_ENTRY_REL assignment, or None."""
    if isinstance(node, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == _LOOKUP_NAME for t in node.targets
    ):
        return node.value
    if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == _LOOKUP_NAME:
        return node.value
    return None


def _cross_skill_skip(tree):
    """ids of nodes the reach rule does not read: docstring strings and the whole value of each
    module-level JEV_ENTRY_REL assignment (the sanctioned lookup)."""
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and _is_text(first.value):
                skip.add(id(first.value))
    for node in tree.body:
        value = _lookup_value(node)
        if value is not None:
            skip.update(id(sub) for sub in ast.walk(value))
    return skip


def _is_text(node: object) -> TypeGuard[ast.Constant]:
    """A string constant; the guard lets callers read `.value` and `.lineno` as typed."""
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _mentions_skill(text, other):
    """`<other>/` at a word start: `skills/beta/x` and `../beta/x` match, `alpha-beta/` does not."""
    return re.search(r"(?<![\w-])" + re.escape(other) + "/", text) is not None


def _import_roots(node):
    if isinstance(node, ast.Import):
        names = [alias.name for alias in node.names]
    elif node.module and not node.level:
        names = [node.module]
    else:
        return []
    return [name.split(".")[0] for name in names]


_IMPORT_CALLS = {"importlib.import_module", "import_module", "__import__"}


def _leading_literal(node):
    """The literal text a string argument starts with: a plain string, or an f-string's head."""
    if _is_text(node):
        return str(node.value)
    if isinstance(node, ast.JoinedStr) and node.values and _is_text(node.values[0]):
        return str(node.values[0].value)
    return None


def check_cross_skill_refs(relpath, tree, modules, skills):
    """Ruling 2 / SPEC R9: one hit `(relpath, other skill or "decide.py", line)` per literal
    reach into another skill: an import of its module (also `import_module("pkg.x")` or an
    f-string starting with the module), a sys.path call naming its folder, any
    string holding `<other>/`, a bare folder name passed to a path join or used in a `/`
    expression, or a decide.py name. Docstrings and the JEV_ENTRY_REL lookup are not read."""
    parts = relpath.split("/")
    own = parts[1] if parts[0] == "skills" and len(parts) > 2 else None
    others = [name for name in skills if name != own]
    skip = _cross_skill_skip(tree)
    hits = []
    for node in ast.walk(tree):
        if id(node) in skip:
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for root in _import_roots(node):
                owner = modules.get(root)
                if owner is not None and owner != own:
                    hits.append((relpath, owner, node.lineno))
        if isinstance(node, ast.Call) and _dotted_name(node.func) in _IMPORT_CALLS and node.args:
            head = _leading_literal(node.args[0])
            owner = modules.get(head.split(".")[0]) if head else None
            if owner is not None and owner != own:
                hits.append((relpath, owner, node.lineno))
        if _is_text(node):
            if _DECIDE_NAME in str(node.value):
                hits.append((relpath, _DECIDE_NAME, node.lineno))
            for other in others:
                if _mentions_skill(node.value, other):
                    hits.append((relpath, other, node.lineno))
        if isinstance(node, ast.Call) and _dotted_name(node.func) in _SYS_PATH_CALLS:
            for arg in node.args:
                for sub in ast.walk(arg):
                    if id(sub) in skip or not _is_text(sub):
                        continue
                    for other in others:
                        if sub.value == other or _mentions_skill(sub.value, other):
                            hits.append((relpath, other, node.lineno))
        if isinstance(node, ast.Call) and _dotted_name(node.func) in _PATH_JOINERS:
            candidates = node.args
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            candidates = [node.left, node.right]
        else:
            candidates = []
        for cand in candidates:
            if id(cand) not in skip and _is_text(cand) and cand.value in others:
                hits.append((relpath, cand.value, getattr(node, "lineno", 0)))
    return hits


def cross_skill_hits():
    """Live scan over every skills/<s>/**/*.py (not _shared) and tools/hooks/*.py. Returns
    `(hits, scanned file count)`."""
    modules = skill_modules(_REPO_ROOT)
    skills = skill_folders(_REPO_ROOT)
    paths = []
    for skill in skills:
        paths.extend(_iter_skill_python(os.path.join("skills", skill)))
    hooks = os.path.join(_REPO_ROOT, "tools", "hooks")
    paths.extend(os.path.join(hooks, n) for n in sorted(os.listdir(hooks)) if n.endswith(".py"))
    hits = []
    for path in paths:
        rel = os.path.relpath(path, _REPO_ROOT).replace(os.sep, "/")
        hits.extend(check_cross_skill_refs(rel, _parse_path(path), modules, skills))
    return hits, len(paths)


# Ruling 2: the cross-skill reaches the tree already has, one key per (file, other skill) with a
# one-line reason. Backlog 999.19 removes them (the installed-skill lookup, or vendoring that
# survives copy installs: DIST-03). The list may only shrink: _CROSS_SKILL_FROZEN is the set it is
# checked against, and an entry leaves both when its reference goes away.
CROSS_SKILL_ALLOWLIST: dict[tuple[str, str], str] = {
    (
        "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec from the spec-review package (backlog 999.19)",
    (
        "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec after a sys.path shim onto spec-review (backlog 999.19)",
    (
        "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/preference_match.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec.detection after a sys.path shim onto spec-review (backlog 999.19)",
    (
        "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py",
        "ai-kit-spec-review",
    ): "importlib.import_module of ai_kit_spec.<name> after a sys.path shim (backlog 999.19)",
    (
        "skills/ai-kit-session-wake/ai-kit-session-wake.py",
        "ai-kit-spec-review",
    ): "sys.path shim onto the spec-review folder (backlog 999.19)",
    (
        "skills/ai-kit-session-wake/ai_kit_session_wake/__init__.py",
        "ai-kit-spec-review",
    ): "path join naming the spec-review folder for its sys.path shim (backlog 999.19)",
    (
        "skills/ai-kit-session-wake/ai_kit_session_wake/arm.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec.detection from the spec-review package (backlog 999.19)",
    (
        "skills/ai-kit-session-wake/ai_kit_session_wake/cli.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec.detection from the spec-review package (backlog 999.19)",
    (
        "skills/ai-kit-session-wake/ai_kit_session_wake/hosts.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec.detection from the spec-review package (backlog 999.19)",
    (
        "skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py",
        "ai-kit-spec-review",
    ): "sys.path shim onto the spec-review folder (backlog 999.19)",
    (
        "skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/adapter.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec from the spec-review package (backlog 999.19)",
    (
        "skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec from the spec-review package (backlog 999.19)",
    (
        "skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cross_ai_guidance.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec from the spec-review package (backlog 999.19)",
    (
        "skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_config.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec from the spec-review package (backlog 999.19)",
    (
        "skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_cross_ai.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec from the spec-review package (backlog 999.19)",
    (
        "skills/ai-kit-spec-execute-superpowers/ai-kit-spec-superpowers.py",
        "ai-kit-spec-review",
    ): "sys.path shim onto the spec-review folder (backlog 999.19)",
    (
        "skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec from the spec-review package (backlog 999.19)",
    (
        "skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py",
        "ai-kit-spec-review",
    ): "imports ai_kit_spec from the spec-review package (backlog 999.19)",
    (
        "skills/ai-kit-spec-goal-prompt/scripts/gp_host.py",
        "ai-kit-session-wake",
    ): "WAKE_CLI names the session-wake CLI path (backlog 999.19)",
    (
        "skills/ai-kit-spec-goal-prompt/scripts/gp_host.py",
        "ai-kit-spec-review",
    ): "SPEC_CLI names the spec-review CLI path (backlog 999.19)",
    (
        "tools/hooks/claude_session_wake.py",
        "ai-kit-session-wake",
    ): "path join naming the session-wake skill folder for its CLI (backlog 999.19)",
}
# Written out literally on purpose: deriving this from the allowlist would make the frozen check
# vacuous. A key added to the allowlist and missing here fails cross_skill_allowlist_problems.
_CROSS_SKILL_FROZEN = frozenset(
    {
        ("skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py", "ai-kit-spec-review"),
        (
            "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py",
            "ai-kit-spec-review",
        ),
        (
            "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/preference_match.py",
            "ai-kit-spec-review",
        ),
        (
            "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py",
            "ai-kit-spec-review",
        ),
        ("skills/ai-kit-session-wake/ai-kit-session-wake.py", "ai-kit-spec-review"),
        (
            "skills/ai-kit-session-wake/ai_kit_session_wake/__init__.py",
            "ai-kit-spec-review",
        ),
        ("skills/ai-kit-session-wake/ai_kit_session_wake/arm.py", "ai-kit-spec-review"),
        ("skills/ai-kit-session-wake/ai_kit_session_wake/cli.py", "ai-kit-spec-review"),
        ("skills/ai-kit-session-wake/ai_kit_session_wake/hosts.py", "ai-kit-spec-review"),
        ("skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py", "ai-kit-spec-review"),
        ("skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/adapter.py", "ai-kit-spec-review"),
        ("skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py", "ai-kit-spec-review"),
        (
            "skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cross_ai_guidance.py",
            "ai-kit-spec-review",
        ),
        ("skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_config.py", "ai-kit-spec-review"),
        ("skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_cross_ai.py", "ai-kit-spec-review"),
        ("skills/ai-kit-spec-execute-superpowers/ai-kit-spec-superpowers.py", "ai-kit-spec-review"),
        (
            "skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py",
            "ai-kit-spec-review",
        ),
        (
            "skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py",
            "ai-kit-spec-review",
        ),
        ("skills/ai-kit-spec-goal-prompt/scripts/gp_host.py", "ai-kit-session-wake"),
        ("skills/ai-kit-spec-goal-prompt/scripts/gp_host.py", "ai-kit-spec-review"),
        ("tools/hooks/claude_session_wake.py", "ai-kit-session-wake"),
    }
)


def cross_skill_allowlist_problems(allowlist):
    """Problems with an allowlist: a key outside the frozen set, or a reason that is empty or not
    one line. The live test separately requires every key to have a live hit."""
    problems = []
    for key, reason in allowlist.items():
        if key not in _CROSS_SKILL_FROZEN:
            problems.append(f"{key[0]} -> {key[1]}: not in the frozen set (the list only shrinks)")
        if not reason.strip() or "\n" in reason:
            problems.append(f"{key[0]} -> {key[1]}: reason must be one non-empty line")
    return problems


# Phase 29 D-13 (SPEC R9 ordering): every copy of the installed-skill lookup follows the order of
# jev's documented table (skills/jev-fast-decision/reference.md `## Installed-skill lookup`, rows
# 2-6). Each copy is parsed from its own text, never executed. The fold-step copy is a shell block
# that names the fold skill as its suffix; its roots are the same five rows.
LOOKUP_COPIES = (
    "skills/jev-fast-decision/scripts/jev_ladder.py",
    "skills/ai-kit-commit-fold/scripts/fold_group.py",
    "skills/ai-kit-spec-goal-prompt/scripts/gp_host.py",
    "tools/hooks/precompact_core.py",
    "skills/ai-kit-commit-fold/gsd/ai-kit-commit-fold/ai-kit-fold.cjs",
    "skills/ai-kit-spec-execute-superpowers/references/fold-step.md",
)
_LOOKUP_NAMES = frozenset({"JEV_ENTRY_REL", "SKILLS_ROOTS"})
_DOC_ROOT_BRACED = re.compile(r"^\$\{(\w+):-\$HOME/([^}]+)\}/(.+)$")
_DOC_ROOT_PLAIN = re.compile(r"^\$HOME/(.+)$")
_JS_SKILLS_ROOTS = re.compile(r"^const SKILLS_ROOTS = (\[.*\]);$", re.MULTILINE)
_SHELL_ROOT = re.compile(
    r'\$\{(\w+):-\$HOME/([^}]+)\}/([^"\s]+?)/ai-kit-commit-fold'
    r'|"\$HOME/([^"$/]+)/([^"\s]+?)/ai-kit-commit-fold"'
)


def documented_roots(text):
    """reference.md `## Installed-skill lookup`, rows 2-6, as (variable or None, fallback,
    suffix) tuples in table order. Row 1 is the caller's own root and is not compared."""
    section = text.split("## Installed-skill lookup", 1)[1].split("\n## ", 1)[0]
    roots = []
    for line in section.splitlines():
        if not line.startswith("| ") or line.startswith(("| Order", "| ---")):
            continue
        order, root = (cell.strip() for cell in line.strip().strip("|").split("|")[:2])
        if order == "1":
            continue
        root = root.strip("`")
        braced = _DOC_ROOT_BRACED.match(root)
        if braced:
            roots.append((braced.group(1), braced.group(2), braced.group(3)))
        else:
            plain = _DOC_ROOT_PLAIN.match(root)
            assert plain is not None, root
            fallback, suffix = plain.group(1).rsplit("/", 1)
            roots.append((None, fallback, suffix))
    return roots


def python_roots(tree):
    """The module-level SKILLS_ROOTS literal (ast.literal_eval) as a list of tuples, or None."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "SKILLS_ROOTS" for t in node.targets
        ):
            return [tuple(row) for row in ast.literal_eval(node.value)]
    return None


def js_roots(text):
    """The one `const SKILLS_ROOTS = [...];` line of a JS file, JSON-decoded, or None."""
    match = _JS_SKILLS_ROOTS.search(text)
    if match is None:
        return None
    return [tuple(row) for row in json.loads(match.group(1))]


def shell_roots(text):
    """The host roots of a shell block, in order: each `${VAR:-$HOME/<fallback>}/<suffix>` or
    `"$HOME/<fallback>/<suffix>"` in front of `/ai-kit-commit-fold`."""
    roots = []
    for match in _SHELL_ROOT.finditer(text):
        if match.group(1):
            roots.append((match.group(1), match.group(2), match.group(3)))
        else:
            roots.append((None, match.group(4), match.group(5)))
    return roots


def _lookup_copy_roots(relpath):
    path = os.path.join(_REPO_ROOT, relpath)
    if relpath.endswith(".py"):
        return python_roots(_parse_path(path))
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    return js_roots(text) if relpath.endswith(".cjs") else shell_roots(text)


def lookup_drift_problems(documented, copies):
    """Problems where a copy's roots are not the documented rows in documented order."""
    problems = []
    if len(documented) != 5:
        problems.append(f"documented lookup has {len(documented)} rows, expected 5")
    for relpath, roots in copies.items():
        if roots is None:
            problems.append(f"{relpath}: no SKILLS_ROOTS found")
        elif [tuple(row) for row in roots] != [tuple(row) for row in documented]:
            problems.append(f"{relpath}: order {roots} differs from the documented {documented}")
    return problems


def _assigns_lookup_name(tree):
    """True when any assignment in the tree binds JEV_ENTRY_REL or SKILLS_ROOTS."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if any(isinstance(t, ast.Name) and t.id in _LOOKUP_NAMES for t in targets):
            return True
    return False


def uncompared_lookup_files(assigners, copies):
    """Files that assign a lookup name but are not one of the compared copies."""
    return sorted(set(assigners) - set(copies))


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
        # (post-install UI) a doctor bug after the install notifies instead of crashing Done.
        ("tools/wizard_app.py", "_key_done"),
        ("tools/common_render.py", "core_safe_build"),
        ("tools/common_render.py", "core_render_checked"),
        ("tools/statusline-doctor.py", "cmd_doctor"),
        ("tools/config_doctor_checks.py", "apply_row"),
        ("tools/run_unittest_parallel.py", "_staged_selection"),
        # (pushed-tests) from skipping an over-budget e2e module at push: any failure of the
        # proof or the mapper runs every over-budget module, so the catch-all is the fail-safe.
        ("tools/run_unittest_parallel.py", "_pushed_modules"),
        # (queue-checkout) the post-checkout seed hook is arbitrary code; its failure only logs,
        # and the outer detach suppresses everything, so a git worktree add never fails (30-01).
        ("skills/ai-kit-commit-fold/scripts/flow_index.py", "_queue_checkout"),
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
        # the live agent's process name, matched in /proc command lines (not a runtime id)
        "tools/cursor_probes.py",
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
        # the index job runner (30-01) is detached from the git hook that starts it, so it must
        # outlive that hook's process group; it runs index jobs, not a cross-AI run, and it is
        # the only other start_new_session caller.
        "skills/ai-kit-commit-fold/scripts/flow_index.py",
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
            if not (skill_dir.startswith("ai-kit-spec-") or skill_dir == "ai-kit-commit-fold"):
                continue
            for dirpath, _dirnames, filenames in os.walk(os.path.join(skills_root, skill_dir)):
                for filename in filenames:
                    if not filename.endswith(".py"):
                        continue
                    path = os.path.join(dirpath, filename)
                    tree = _read_tree(path)[0]
                    for msg in check_no_shell_true(tree):
                        violations.append(f"{os.path.relpath(path, repo_root)}: {msg}")
        self.assertEqual([], violations)

    def test_folding_policy_states_every_rule(self):
        with open(_FOLD_POLICY, encoding="utf-8") as fh:
            self.assertEqual([], missing_policy_rules(fh.read()))

    def test_fold_skill_never_resets_hard(self):
        skill_root = os.path.join(_REPO_ROOT, _FOLD_SKILL)
        violations = []
        for dirpath, dirnames, filenames in os.walk(skill_root):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for filename in sorted(filenames):
                path = os.path.join(dirpath, filename)
                rel = os.path.relpath(path, skill_root).replace(os.sep, "/")
                if rel == "references/folding-policy.md" or rel.startswith("evals/"):
                    continue
                with open(path, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                tree = _read_tree(path)[0] if filename.endswith(".py") else None
                violations.extend(check_no_reset_hard(f"{_FOLD_SKILL}/{rel}", text, tree))
        self.assertEqual([], violations)

    def test_flow_core_never_forces_a_push_without_a_lease(self):
        self.assertEqual([], _flow_core_violations(check_flow_force))

    def test_flow_core_has_one_push_site(self):
        self.assertEqual([], _flow_core_violations(check_flow_push_site))

    def test_flow_core_pushes_only_to_the_primary_remote(self):
        self.assertEqual([], _flow_core_violations(check_flow_remote))

    def test_flow_core_never_merges_by_squash_rebase_or_auto(self):
        self.assertEqual([], _flow_core_violations(check_flow_merge_method))

    def test_flow_core_never_names_a_framework(self):
        self.assertEqual([], _flow_core_violations(check_flow_framework_names, framework=True))

    def test_agents_md_points_to_the_folding_policy(self):
        with open(os.path.join(_REPO_ROOT, "AGENTS.md"), encoding="utf-8") as fh:
            agents = fh.read()
        self.assertIn(f"{_FOLD_SKILL}/references/folding-policy.md", agents)
        self.assertIn("compaction", agents)
        self.assertNotIn("logically-grouped, buildable commits", agents)

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
                    tree = _read_tree(path)[0]
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
                    tree = _read_tree(path)[0]
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
            tree = _read_tree(os.path.join(tests_root, filename))[0]
            violations += check_main_guard_last(f"tests/{filename}", tree)
            guarded += any(_is_main_guard(node) for node in tree.body)
        self.assertEqual([], violations)
        self.assertGreater(guarded, 0)

    def test_no_test_reads_planning(self):
        # SPEC R9: every direct tests/*.py file; tests/fixtures/ is data and is not walked.
        tests_root = os.path.dirname(os.path.abspath(__file__))
        violations, still_reading = [], set()
        for filename in sorted(os.listdir(tests_root)):
            if not filename.endswith(".py"):
                continue
            relpath = f"tests/{filename}"
            tree = _read_tree(os.path.join(tests_root, filename))[0]
            found = check_no_planning_reader(tree)
            if found and relpath in PLANNING_READER_EXCEPTIONS:
                still_reading.add(relpath)
            elif found:
                violations.extend(f"{relpath} {problem}" for problem in found)
        self.assertEqual([], violations)
        # A listed file that no longer reads .planning/ is a stale entry; remove it.
        self.assertEqual(sorted(PLANNING_READER_EXCEPTIONS), sorted(still_reading))

    def test_planning_reader_exceptions_stay_empty(self):
        self.assertEqual([], planning_reader_exception_problems(PLANNING_READER_EXCEPTIONS))

    def test_no_test_calls_a_host_cli(self):
        # SPEC R5 / D-05: no test spawns a host CLI by name; tests/host_fakes.py is exempt.
        tests_root = os.path.dirname(os.path.abspath(__file__))
        names = _host_cli_names()
        violations = []
        for filename in sorted(os.listdir(tests_root)):
            relpath = f"tests/{filename}"
            if not filename.endswith(".py") or relpath == HOST_FAKES_PATH:
                continue
            tree = _read_tree(os.path.join(tests_root, filename))[0]
            violations.extend(f"{relpath} {problem}"
                              for problem in check_no_host_cli_calls(tree, names))
        self.assertEqual([], violations)

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
                    src = _read_tree(path)[1]
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

    def test_no_cross_skill_reach_outside_the_allowlist(self):
        """Ruling 2 / SPEC R9: every literal cross-skill reach is in the frozen allowlist, and
        every allowlist key still has a live hit (an entry whose reference is gone fails)."""
        hits, scanned = cross_skill_hits()
        self.assertGreater(scanned, 0)
        keys = {(relpath, other) for relpath, other, _line in hits}
        listed = set(CROSS_SKILL_ALLOWLIST)
        self.assertEqual([], sorted(keys - listed), "unlisted cross-skill reach")
        self.assertEqual([], sorted(listed - keys), "stale allowlist entry: no live hit")

    def test_cross_skill_allowlist_is_frozen(self):
        self.assertEqual([], cross_skill_allowlist_problems(CROSS_SKILL_ALLOWLIST))

    def test_lookup_copies_match_the_documented_order(self):
        """D-13: every lookup copy lists its roots in jev's documented order."""
        reference = os.path.join(_REPO_ROOT, "skills", "jev-fast-decision", "reference.md")
        with open(reference, encoding="utf-8") as handle:
            documented = documented_roots(handle.read())
        self.assertEqual(5, len(documented))
        copies = {relpath: _lookup_copy_roots(relpath) for relpath in LOOKUP_COPIES}
        self.assertEqual([], lookup_drift_problems(documented, copies))

    def test_every_lookup_copy_is_compared(self):
        """Every skills/ or tools/hooks/ Python file that assigns JEV_ENTRY_REL or SKILLS_ROOTS
        is a compared copy, so a new copy cannot escape the drift check."""
        scanned, assigners = 0, []
        for folder in ("skills", os.path.join("tools", "hooks")):
            for path in _iter_skill_python(folder):
                scanned += 1
                if _assigns_lookup_name(_parse_path(path)):
                    assigners.append(os.path.relpath(path, _REPO_ROOT).replace(os.sep, "/"))
        self.assertGreater(scanned, 0)
        self.assertGreater(len(assigners), 0)
        self.assertEqual([], uncompared_lookup_files(assigners, LOOKUP_COPIES))


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
    "cursor_probes",
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

    def test_policy_rule_removal_is_caught(self):
        with open(_FOLD_POLICY, encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual([], missing_policy_rules(text))
        for rule in POLICY_RULES:
            with self.subTest(rule=rule):
                self.assertEqual([rule], missing_policy_rules(drop_policy_bullet(text, rule)))

    def test_policy_rules_survive_reordering(self):
        with open(_FOLD_POLICY, encoding="utf-8") as fh:
            text = fh.read()
        reordered = reverse_policy_bullets(text)
        self.assertNotEqual(text, reordered)
        self.assertEqual([], missing_policy_rules(reordered))

    def test_policy_rules_survive_rewrapping(self):
        with open(_FOLD_POLICY, encoding="utf-8") as fh:
            text = fh.read()
        rewrapped = rewrap_policy(text)
        self.assertNotEqual(text, rewrapped)
        self.assertEqual([], missing_policy_rules(rewrapped))

    def test_reset_hard_flags_each_form(self):
        for source in ("git reset --hard HEAD\n", "git  reset   --HARD\n"):
            with self.subTest(source=source):
                self.assertNotEqual([], check_no_reset_hard("skills/x.md", source))
        argv = 'cmd = ["git", "reset", "--hard", tip]\n'
        self.assertNotEqual([], check_no_reset_hard("skills/x.py", argv, ast.parse(argv)))

    def test_reset_hard_allows_update_ref(self):
        argv = 'cmd = ["git", "update-ref", ref, new, old]\n'
        self.assertEqual([], check_no_reset_hard("skills/x.py", argv, ast.parse(argv)))

    def test_flow_force_flags_each_form(self):
        path = "skills/ai-kit-commit-fold/scripts/flow_git.py"
        for source in (
            'flag = "--force"\n',
            'flag = "-f"\n',
            'flag = "--force=refs/heads/x"\n',
            'cmd = ["git", "push", remote, "+HEAD:refs/heads/unit"]\n',
            'cmd = f"+{src}:refs/heads/{branch}"\n',
        ):
            with self.subTest(source=source):
                self.assertNotEqual([], check_flow_force(path, source, ast.parse(source)))
        compliant = 'flag = "--force-with-lease=refs/heads/b:" + sha\n'
        self.assertEqual([], check_flow_force(path, compliant, ast.parse(compliant)))

    def test_flow_push_site_flags_outside_flow_git(self):
        path = "skills/ai-kit-commit-fold/scripts/flow_stack.py"
        for source in ('argv = ["git", "push", remote, ref]\n', 'verb = "push"\n'):
            with self.subTest(source=source):
                self.assertNotEqual([], check_flow_push_site(path, source, ast.parse(source)))
        self.assertEqual([], check_flow_push_site(
            "skills/ai-kit-commit-fold/scripts/flow_git.py", 'verb = "push"\n',
            ast.parse('verb = "push"\n')))

    def test_flow_remote_flags_literal_origin(self):
        path = "skills/ai-kit-commit-fold/scripts/flow_stack.py"
        for source in ('remote = "origin"\n', 'argv = ["git", "push", "backup", ref]\n'):
            with self.subTest(source=source):
                self.assertNotEqual([], check_flow_remote(path, source, ast.parse(source)))
        compliant = 'argv = ["git", "push", remote, ref]\n'
        self.assertEqual([], check_flow_remote(path, compliant, ast.parse(compliant)))

    def test_flow_merge_method_flags_each_flag(self):
        path = "skills/ai-kit-commit-fold/scripts/flow_merge.py"
        for flag in ("--squash", "--rebase", "--auto"):
            with self.subTest(flag=flag):
                source = f'argv = ["gh", "pr", "merge", "{flag}"]\n'
                self.assertNotEqual([], check_flow_merge_method(path, source, ast.parse(source)))
        compliant = 'argv = ["gh", "pr", "merge", "--merge", "--match-head-commit", sha]\n'
        self.assertEqual([], check_flow_merge_method(path, compliant, ast.parse(compliant)))

    def test_flow_framework_names_flags_each_name(self):
        path = "skills/ai-kit-commit-fold/scripts/flow_unit.py"
        for source in ("# GSD phase\n", 'label = "superpowers plan"\n', "x = 1  # SuperPowers\n"):
            with self.subTest(source=source):
                self.assertNotEqual([], check_flow_framework_names(path, source))
        self.assertEqual([], check_flow_framework_names(path, "# a phase plan\n"))

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
            # SPEC R9: .planning/ is history that check_legacy_references never reads (it is in
            # the history prefixes), so it is skipped before the open, not after.
            if relpath.startswith(".planning/"):
                continue
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

    def test_planning_reader_flags_each_join_form(self):
        # One synthetic offender per join form (SPEC R9 encoding); each must fail.
        setup = (
            "import os\nfrom pathlib import Path\n"
            "REPO_ROOT = Path(__file__).resolve().parent.parent\n"
        )
        offenders = (
            'open(REPO_ROOT / ".planning" / "STATE.md")\n',
            'open(os.path.join(REPO_ROOT, ".planning", "STATE.md"))\n',
            'Path(REPO_ROOT, ".planning")\n',
            'p = f"{REPO_ROOT}/.planning/STATE.md"\n',
            'p = str(REPO_ROOT) + "/.planning/STATE.md"\n',
            'open(".planning/STATE.md")\n',
            '(Path(".planning") / "STATE.md").read_text()\n',
            'open(os.path.join(".planning", "STATE.md"))\n',
            'p = Path.cwd() / ".planning"\n',
            'p = os.path.join(os.getcwd(), ".planning", "STATE.md")\n',
        )
        for body in offenders:
            with self.subTest(body=body):
                self.assertNotEqual([], check_no_planning_reader(ast.parse(setup + body)))

    def test_planning_reader_tracks_class_and_function_roots(self):
        class_case = (
            "from pathlib import Path\n"
            "class T:\n"
            "    @classmethod\n"
            "    def setUpClass(cls):\n"
            "        cls.repo = Path(__file__).resolve().parent.parent\n"
            "    def test_read(self):\n"
            '        open(self.repo / ".planning" / "STATE.md")\n'
        )
        function_case = (
            "from pathlib import Path\n"
            "def read():\n"
            "    root = Path(__file__).resolve().parent\n"
            '    return open(root / ".planning" / "STATE.md")\n'
        )
        self.assertNotEqual([], check_no_planning_reader(ast.parse(class_case)))
        self.assertNotEqual([], check_no_planning_reader(ast.parse(function_case)))

    def test_host_cli_flags_each_spawning_family_and_form(self):
        # SPEC R5 / D-05: one synthetic caller per form and per spawning family; each must fail.
        names = _host_cli_names()
        self.assertIn("claude", names)
        offenders = (
            'subprocess.run(["claude", "--version"])\n',
            'subprocess.run(args=["/usr/bin/claude", "--version"])\n',
            'subprocess.check_output(["claude", "--version"])\n',
            'subprocess.run("claude --version", shell=False)\n',
            'subprocess.Popen("claude --version", shell=True)\n',
            'os.system("claude --version")\n',
            'os.popen("claude --version")\n',
            'os.execvp("claude", ["claude", "--version"])\n',
            'os.execv("/usr/bin/claude", ["claude", "--version"])\n',
            'os.posix_spawnp("claude", ["claude"], {})\n',
            'os.spawnvp(os.P_WAIT, "claude", ["claude", "--version"])\n',
            'os.spawnl(os.P_WAIT, "/usr/bin/claude", "claude")\n',
            'asyncio.create_subprocess_exec("claude", "--version")\n',
            'asyncio.create_subprocess_shell("claude --version")\n',
            'shutil.which("claude")\n',
            'subprocess.run(["innocent-name", "--version"], executable="/usr/bin/claude")\n',
            'subprocess.Popen("x --version", shell=True, executable="claude")\n',
            'asyncio.create_subprocess_exec("x", executable="/usr/bin/claude")\n',
        )
        for source in offenders:
            with self.subTest(source=source):
                self.assertNotEqual([], check_no_host_cli_calls(ast.parse(source), names))

    def test_host_cli_bare_which_import_is_flagged(self):
        source = "from shutil import which\nwhich('claude')\n"
        self.assertNotEqual([], check_no_host_cli_calls(ast.parse(source), _host_cli_names()))

    def test_host_cli_clean_forms_are_not_flagged(self):
        # Data lists, assertion arguments, variable programs and a non-constant executable pass.
        names = _host_cli_names()
        clean = (
            'ARGV = ["claude", "codex"]\n',
            'self.assertEqual(argv, ["codex", "exec"])\n',
            "subprocess.run([program, '--version'])\n",
            "subprocess.run(cmd)\n",
            'subprocess.run([sys.executable, "-c", "pass"], executable=sys.executable)\n',
        )
        for source in clean:
            with self.subTest(source=source):
                self.assertEqual([], check_no_host_cli_calls(ast.parse(source), names))

    def test_planning_reader_exception_list_rejects_an_entry(self):
        self.assertNotEqual(
            [], planning_reader_exception_problems({"tests/test_x.py": "reads the live project"})
        )
        self.assertEqual([], planning_reader_exception_problems({}))

    def test_planning_reader_allows_temp_projects_and_other_paths(self):
        clean = (
            "import os, tempfile\nfrom pathlib import Path\n"
            'temp = Path(tempfile.mkdtemp()) / ".planning"\n'
            'ok = path.endswith(os.path.join(".planning", "config.json"))\n'
            'def f(project):\n    return open(project / ".planning" / "x")\n'
        )
        self.assertEqual([], check_no_planning_reader(ast.parse(clean)))

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

    @staticmethod
    def _xs_hits(source):
        """Hits of the ruling-2 rule for a synthetic skills/alpha/x.py; beta is the other skill."""
        modules = {"beta_pkg": "beta", "alpha_mod": "alpha"}
        return check_cross_skill_refs(
            "skills/alpha/x.py", ast.parse(source), modules, ["alpha", "beta"]
        )

    def test_cross_skill_rule_flags_each_form(self):
        # One synthetic violation per form the ruling-2 rule names, with the other skill it reports.
        forms = {
            "import": ("import beta_pkg\n", "beta"),
            "from import": ("from beta_pkg.sub import f\n", "beta"),
            "sys.path.insert": (
                'import sys\nsys.path.insert(0, os.path.join(r, "..", "beta"))\n',
                "beta",
            ),
            "sys.path.append": ('import sys\nsys.path.append("../beta/scripts")\n', "beta"),
            "path string": ('p = "../beta/scripts/x.py"\n', "beta"),
            "os.path.join segment": ('p = os.path.join(root, "beta")\n', "beta"),
            "Path segment": ('p = Path(root, "beta")\n', "beta"),
            "slash expression": ('p = Path(root) / "beta"\n', "beta"),
            "decide.py name": ('p = "scripts/decide.py"\n', "decide.py"),
            "import_module f-string": (
                'import importlib\nimportlib.import_module(f"beta_pkg.{name}")\n',
                "beta",
            ),
            "import_module string": ('import_module("beta_pkg.sub")\n', "beta"),
            "__import__ string": ('__import__("beta_pkg")\n', "beta"),
        }
        for form, (source, other) in forms.items():
            with self.subTest(form=form):
                self.assertIn(other, [hit[1] for hit in self._xs_hits(source)])

    def test_cross_skill_rule_allows_clean_forms(self):
        # Own-skill import, the JEV_ENTRY_REL lookup (its value names beta/ and is exempt),
        # a docstring naming beta/, a relative import and a stdlib import are not reaches.
        clean = {
            "own-skill import": "import alpha_mod\n",
            "lookup assignment": 'JEV_ENTRY_REL = os.path.join("..", "beta", "scripts", "x.py")\n',
            "docstring": '"""Mentions beta/scripts only in prose."""\n',
            "relative import": "from . import sibling\n",
            "stdlib import": "import json\n",
            "own-skill import_module": 'import_module(f"alpha_mod.{name}")\n',
            "computed import_module": "import_module(name)\n",
        }
        for form, source in clean.items():
            with self.subTest(form=form):
                self.assertEqual([], self._xs_hits(source))

    def test_cross_skill_allowlist_rejects_a_new_entry(self):
        self.assertEqual([], cross_skill_allowlist_problems(CROSS_SKILL_ALLOWLIST))
        grown = dict(CROSS_SKILL_ALLOWLIST)
        grown[("skills/alpha/x.py", "beta")] = "a reach added after the freeze"
        self.assertNotEqual([], cross_skill_allowlist_problems(grown))
        multi_line = dict(CROSS_SKILL_ALLOWLIST)
        first = next(iter(multi_line))
        multi_line[first] = "two\nlines"
        self.assertNotEqual([], cross_skill_allowlist_problems(multi_line))

    def test_lookup_drift_flags_a_swapped_row(self):
        rows = [
            ("CLAUDE_CONFIG_DIR", ".claude", "skills"),
            (None, ".agents", "skills"),
            ("XDG_CONFIG_HOME", ".config", "opencode/skills"),
            ("CURSOR_CONFIG_DIR", ".cursor", "skills"),
            ("PI_CODING_AGENT_DIR", ".pi/agent", "skills"),
        ]
        swapped = [rows[1], rows[0], *rows[2:]]
        self.assertEqual([], lookup_drift_problems(rows, {"copy.py": rows}))
        self.assertNotEqual([], lookup_drift_problems(rows, {"copy.py": swapped}))
        # Each parser reads its own syntax back to the same rows.
        self.assertEqual(rows, python_roots(ast.parse(f"SKILLS_ROOTS = {rows!r}\n")))
        js_text = "const SKILLS_ROOTS = " + json.dumps([list(r) for r in rows]) + ";"
        self.assertEqual(rows, js_roots(js_text))
        shell_text = (
            '  "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ai-kit-commit-fold" \\\n'
            '  "$HOME/.agents/skills/ai-kit-commit-fold" \\\n'
            '  "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-commit-fold" \\\n'
            '  "${CURSOR_CONFIG_DIR:-$HOME/.cursor}/skills/ai-kit-commit-fold" \\\n'
            '  "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills/ai-kit-commit-fold"; do\n'
        )
        self.assertEqual(rows, shell_roots(shell_text))
        doc = (
            "## Installed-skill lookup\n\n| Order | Skills root |\n| --- | --- |\n"
            "| 1 | the caller's own root |\n"
            "| 2 | `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills` |\n"
            "| 3 | `$HOME/.agents/skills` |\n\n## Next\n"
        )
        self.assertEqual(rows[:2], documented_roots(doc))

    def test_lookup_drift_flags_an_uncompared_copy(self):
        self.assertTrue(_assigns_lookup_name(ast.parse('JEV_ENTRY_REL = "jev/x.py"\n')))
        self.assertTrue(_assigns_lookup_name(ast.parse("SKILLS_ROOTS: tuple = ()\n")))
        self.assertFalse(_assigns_lookup_name(ast.parse('NAME = "x"\n')))
        self.assertEqual(
            ["skills/new-skill/x.py"],
            uncompared_lookup_files(["skills/new-skill/x.py"], LOOKUP_COPIES),
        )
        self.assertEqual([], uncompared_lookup_files([LOOKUP_COPIES[0]], LOOKUP_COPIES))


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
    # 30.2 D-07: path, git_dirty, model, alt_time_ago and alt_term_dimensions carry icons.
    EXPECTED_ICONS = {
        "path": "📂",
        "git_branch": "🌿",
        "git_dirty": "✏",
        "alt_git_worktree": "⎇",
        "todo": "📝",
        "model": "🤖",
        "alt_time_ago": "⌛",
        "alt_time_clock": "⏰",
        "effort": "🧠",
        "lines": "📃",
        "alt_cost": "🪙",
        "alt_time_session": "💬",
        "alt_time_api": "📡",
        "render_time": "⏱",
        "slowest": "🐌",
        "alt_term_dimensions": "📐",
        "context": "📊",
        "chat_size": "💾",
        "alt_process_memory": "🧮",
        "alt_h_rate_limit": "⚡",
        "alt_w_rate_limit": "⚡",
    }
    # Icon single-sourcing into the inventory is DEFERRED per the PRD; until then
    # the inventory icon is hand-mirrored and this test pins it to the reviewed map.

    # Cursor-only built-ins reviewed against the Cursor oracle vocabulary (D-04, 30.2 D-07).
    EXPECTED_CURSOR_ICONS = {
        "cursor_included": "⚡",
        "cursor_api": "⚡",
        "cursor_extra": "🪙",
        "cursor_reset": "↺",
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
