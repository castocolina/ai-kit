"""AST architecture-fitness test for tools/status-line.py (FR-8).

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
import importlib.util
import os
import re
import sys
import unittest

_TOOLS = os.path.join(os.path.dirname(__file__), "..", "tools")

# Load setup module for inventory tests.
_SETUP_SPEC = importlib.util.spec_from_file_location(
    "setup", os.path.join(_TOOLS, "setup.py")
)
_SETUP_MOD = importlib.util.module_from_spec(_SETUP_SPEC)
_SETUP_SPEC.loader.exec_module(_SETUP_MOD)
setup = _SETUP_MOD

# Banner marker: "# ═══ N. ROLE — ..." — capture the block index and the role token.
_BANNER_RE = re.compile(r"^#\s*═══\s*(\d+)\.\s*([A-Za-z_]+)")

# Config env keys carry this prefix; only these are "config env" for rule 1.
_CONFIG_ENV_PREFIX = "CC_AI_KIT_"

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
    "cmd_doctor", "cmd_check", "cmd_print_config", "validate_config_file",
    "_DOCTOR_SAMPLE", "parse_args", "_dry_render_failures", "_ENV_HELP",
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


def _config_env_literals(tree):
    """Yield ``(node, key)`` for every string literal beginning with the config
    env prefix that is read as an env lookup — either a ``Subscript`` key on a
    Name/Attribute, or a string argument to a ``.get(...)`` call. These are the
    config-env reads guarded by rule 1."""
    for node in ast.walk(tree):
        # env.get("CC_AI_KIT_...") / os.environ.get("CC_AI_KIT_...")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "get" and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                    and arg.value.startswith(_CONFIG_ENV_PREFIX):
                yield node, arg.value
        # env["CC_AI_KIT_..."] / os.environ["CC_AI_KIT_..."]
        if isinstance(node, ast.Subscript):
            key = node.slice
            if isinstance(key, ast.Constant) and isinstance(key.value, str) \
                    and key.value.startswith(_CONFIG_ENV_PREFIX):
                yield node, key.value


def check_config_env_in_cfg(tree):
    """Rule 1 (reduced): the env reader is now STRUCTURAL. cfg_source_get projects
    each typed path to its ``CC_AI_KIT_<...>`` name DYNAMICALLY (string built, then
    ``env.get(name)``), so no function reads a *literal* config-env name — except the
    bootstrap ``cfg_config_path``, which reads ``CC_AI_KIT_CONFIG_FILE`` before any
    TOML loads (chicken-and-egg). This rule now guards only that exception: every
    literal ``CC_AI_KIT_*`` read must live in ``cfg_config_path``, and the only such
    literal is ``CC_AI_KIT_CONFIG_FILE``.

    Runtime/third-party reads (``HOME``, ``XDG_*``, ``STATUSLINE_*``, ``COLUMNS``/
    ``LINES``, ``CLAUDE_CONFIG_DIR``) carry no ``CC_AI_KIT_`` prefix and are never
    matched (FR-1.8 whitelist).
    """
    bootstrap_names = {"CC_AI_KIT_CONFIG_FILE"}
    violations = []
    for node, key in _config_env_literals(tree):
        owners = _enclosing_funcdef_names(tree, node)
        if "cfg_config_path" not in owners:
            where = owners[0] if owners else "<module level>"
            violations.append(
                f"config env {key!r} read at line {node.lineno} in {where} "
                f"(only the cfg_config_path bootstrap may read a literal config-env name)"
            )
        elif key not in bootstrap_names:
            violations.append(
                f"unexpected literal config-env read {key!r} at line {node.lineno} "
                f"(only {sorted(bootstrap_names)} is a recognized bootstrap name)"
            )
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
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) \
                    and node.id in _BOOKKEEPING_ATTRS:
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
        if defaults_start <= func.lineno <= defaults_end \
                and func.name.startswith(("cfg_", "probe_")):
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
        if expected is None:
            violations.append(
                f"{func.name} lives in non-function block {index}.{role}"
            )
        elif not func.name.startswith(expected):
            violations.append(
                f"{func.name} (block {index}.{role}) lacks prefix {expected!r}"
            )
    return violations


def check_no_doctor_symbols(tree):
    """Rule 7 (FR-7): the render module defines none of the doctor/introspection
    symbols (as a FunctionDef/ClassDef or a module-level Assign target)."""
    return [
        f"render module defines doctor symbol {name!r}"
        for name in sorted(_defined_names(tree) & _DOCTOR_SYMBOLS)
    ]


# --------------------------------------------------------------------------- #
# Live-tree tests — every rule must pass against the real render module.
# --------------------------------------------------------------------------- #


class TestArchitecture(unittest.TestCase):
    """The seven FR-8.1 invariants, asserted against the live source tree."""

    @classmethod
    def setUpClass(cls):
        cls.render_tree, cls.render_src = _parse("status-line.py")
        cls.doctor_tree, cls.doctor_src = _parse("statusline-doctor.py")

    def test_rule1_config_env_only_in_bootstrap(self):
        self.assertEqual([], check_config_env_in_cfg(self.render_tree))
        # non-vacuity: the bootstrap literal actually exists in the live module
        literals = {key for _, key in _config_env_literals(self.render_tree)}
        self.assertIn("CC_AI_KIT_CONFIG_FILE", literals)

    def test_rule2_no_subscript_on_typed_models(self):
        self.assertEqual([], check_no_typed_model_subscript(self.render_tree))

    def test_rule3_only_meta_segments_read_bookkeeping(self):
        self.assertEqual([], check_bookkeeping_readers(self.render_tree))

    def test_rule4_segment_signatures(self):
        self.assertEqual([], check_seg_signature(self.render_tree))

    def test_rule5_defaults_precedes_cfg_and_is_data_only(self):
        self.assertEqual([], check_defaults_data_only(self.render_tree, self.render_src))

    def test_rule6_role_prefix_integrity(self):
        self.assertEqual(
            [], check_role_prefix_integrity(self.render_tree, self.render_src)
        )

    def test_rule7_no_doctor_symbols_in_render(self):
        self.assertEqual([], check_no_doctor_symbols(self.render_tree))

    def test_rule7b_doctor_symbols_present_in_doctor(self):
        """Companion to rule 7: the doctor symbols were EXTRACTED, not deleted.
        Every name in ``_DOCTOR_SYMBOLS`` must be defined in the doctor module
        (so rule 7's "absent from render" guarantee means "moved", not "lost")."""
        defined = _defined_names(self.doctor_tree)
        missing = sorted(_DOCTOR_SYMBOLS - defined)
        self.assertEqual(
            [], missing,
            f"doctor symbols absent from statusline-doctor.py: {missing}",
        )

    def test_seg_signature_check_is_non_empty(self):
        """Sanity: the segment-signature rule actually inspected segments (guards
        against a future rename silently emptying the seg_ population)."""
        seg_funcs = [f for f in _top_functions(self.render_tree)
                     if f.name.startswith("seg_")]
        self.assertGreater(len(seg_funcs), 5)


# --------------------------------------------------------------------------- #
# Non-vacuity tests (FR-8.3) — feed each checker a deliberately-violating
# snippet and confirm it FLAGS the violation, proving the rule has teeth. The
# real source files are never mutated.
# --------------------------------------------------------------------------- #


class TestArchNonVacuity(unittest.TestCase):
    """Prove rules 1-7 catch real violations rather than passing vacuously."""

    def test_rule1_flags_config_env_outside_cfg(self):
        bad = ast.parse(
            "def seg_oops(ctx, avail, theme):\n"
            "    return env.get('CC_AI_KIT_CONFIG_FILE')\n"
        )
        good = ast.parse(
            "def cfg_config_path(env):\n"
            "    return env.get('CC_AI_KIT_CONFIG_FILE')\n"
        )
        runtime_ok = ast.parse(
            "def seg_term(ctx, avail, theme):\n"
            "    return env.get('STATUSLINE_COLS')\n"  # not CC_AI_KIT_* → exempt
        )
        also_bad = ast.parse(
            "def cfg_config_path(env):\n"
            "    return env.get('CC_AI_KIT_GIT_CACHE_TTL')\n"  # right place, non-bootstrap name
        )
        self.assertNotEqual([], check_config_env_in_cfg(bad))
        self.assertEqual([], check_config_env_in_cfg(good))
        self.assertEqual([], check_config_env_in_cfg(runtime_ok))
        self.assertNotEqual([], check_config_env_in_cfg(also_bad))

    def test_rule1_walks_enclosing_chain(self):
        """A CC_AI_KIT_CONFIG_FILE read in a closure nested inside cfg_config_path
        PASSES (the cfg_config_path ancestor counts), while the same read nested
        inside a non-bootstrap function is FLAGGED."""
        nested_ok = ast.parse(
            "def cfg_config_path(env):\n"
            "    def inner():\n"
            "        return env.get('CC_AI_KIT_CONFIG_FILE')\n"
            "    return inner\n"
        )
        nested_bad = ast.parse(
            "def util_helper(env):\n"
            "    def inner():\n"
            "        return env.get('CC_AI_KIT_CONFIG_FILE')\n"
            "    return inner\n"
        )
        self.assertEqual([], check_config_env_in_cfg(nested_ok))
        self.assertNotEqual([], check_config_env_in_cfg(nested_bad))

    def test_rule2_flags_subscript_on_typed_model(self):
        bad = ast.parse("x = ctx['model_name']\n")
        bad_conf = ast.parse("y = line_conf['git']\n")
        good = ast.parse("x = ctx.raw['model_name']\n")  # attribute-then-subscript
        self.assertNotEqual([], check_no_typed_model_subscript(bad))
        self.assertNotEqual([], check_no_typed_model_subscript(bad_conf))
        self.assertEqual([], check_no_typed_model_subscript(good))

    def test_rule3_flags_bookkeeping_read_in_other_segment(self):
        bad = ast.parse(
            "def seg_path(ctx, avail, theme):\n"
            "    return ctx.slowest\n"
        )
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
        good_src = (
            "# ═══ 4. fmt_ — formatters ═══\n"
            "def fmt_ok(x):\n"
            "    return x\n"
        )
        self.assertEqual(
            [], check_role_prefix_integrity(ast.parse(good_src), good_src)
        )

    def test_rule6_flags_unknown_shell_entrypoint(self):
        """SHELL block (1) permits only main/safe_render; any other (non-``_``)
        def there is flagged."""
        src = (
            "# ═══ 1. SHELL — entrypoints ═══\n"
            "def run_everything():\n"  # not main/safe_render
            "    return 0\n"
        )
        self.assertNotEqual([], check_role_prefix_integrity(ast.parse(src), src))
        good_src = (
            "# ═══ 1. SHELL — entrypoints ═══\n"
            "def main():\n"
            "    return 0\n"
        )
        self.assertEqual(
            [], check_role_prefix_integrity(ast.parse(good_src), good_src)
        )

    def test_rule6_flags_def_in_non_function_block(self):
        """A role-prefixed def landing in a non-function block (DEFAULTS=1 or the
        trailing doc block=9) — blocks with no entry in ``_BLOCK_PREFIX`` — is
        flagged as living in a non-function block."""
        defaults_src = (
            "# ═══ 1. DEFAULTS — data ═══\n"
            "def cfg_stray(env):\n"  # any def at all is wrong here
            "    return env\n"
        )
        doc_src = (
            "# ═══ 9. DOCS — trailing ═══\n"
            "def seg_stray(ctx, avail, theme):\n"
            "    return ''\n"
        )
        self.assertNotEqual(
            [], check_role_prefix_integrity(ast.parse(defaults_src), defaults_src)
        )
        self.assertNotEqual(
            [], check_role_prefix_integrity(ast.parse(doc_src), doc_src)
        )

    def test_rule7_flags_doctor_symbol_in_render(self):
        bad = ast.parse("def cmd_doctor():\n    return 0\n")
        bad_assign = ast.parse("_DOCTOR_SAMPLE = {}\n")
        good = ast.parse("def core_render(ctx, cfg, theme):\n    return []\n")
        self.assertNotEqual([], check_no_doctor_symbols(bad))
        self.assertNotEqual([], check_no_doctor_symbols(bad_assign))
        self.assertEqual([], check_no_doctor_symbols(good))


class TestSegmentInventory(unittest.TestCase):
    """Segment inventory: coverage, line-mirror, and icon-mirror (Task 7)."""

    # Reviewed mirror of the seg_* inline glyphs; "" means no static icon.
    EXPECTED_ICONS = {
        "path": "", "git_branch": "🌿", "git_dirty": "", "alt_git_worktree": "⎇",
        "todo": "📝", "model": "", "alt_time_ago": "", "alt_time_clock": "⏰",
        "effort": "🧠", "lines": "📃", "alt_cost": "🪙", "alt_time_session": "💬",
        "alt_time_api": "📡", "render_time": "⏱", "slowest": "🐌",
        "alt_term_dimensions": "", "context": "📊", "chat_size": "💾",
        "alt_process_memory": "🧮", "alt_rate_limits": "⚡",
    }
    # Icon single-sourcing into the inventory is DEFERRED per the PRD; until then
    # the inventory icon is hand-mirrored and this test pins it to the reviewed map.

    def _sl(self):
        sl_path = os.path.join(_TOOLS, "status-line.py")
        spec = importlib.util.spec_from_file_location("status_line_inv", sl_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod

    def _line_index(self, sl, key):
        for i, ln in enumerate(sl.LAYOUT):
            if key in ln.segments:
                return i
        raise AssertionError(f"{key} not in LAYOUT")

    def test_coverage_every_segment_has_entry(self):
        sl = self._sl()
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH)
        for key in sl.SEGMENTS:
            self.assertIn(key, inv, f"SEGMENTS key {key} missing from inventory")

    def test_line_mirror(self):
        sl = self._sl()
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH)
        for key in sl.SEGMENTS:
            self.assertEqual(inv[key]["line"], self._line_index(sl, key),
                             f"{key} inventory line != LAYOUT line")

    def test_icon_mirror(self):
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH)
        for key, icon in self.EXPECTED_ICONS.items():
            self.assertEqual(inv[key]["icon"], icon,
                             f"{key} inventory icon != reviewed glyph")


if __name__ == "__main__":
    unittest.main()
