"""LibCST codemod template for safe, multi-file refactors.

Why: Avoid naive replace while preserving formatting and comments.
Who: Use this when renames span multiple files or when refs are hard to audit.
How: Run this file with a subcommand and explicit file paths.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import libcst as cst
import libcst.matchers as m


@dataclass(frozen=True)
class RenameSpec:
    """Defines the rename pair for a single symbol change."""

    old_name: str
    new_name: str


@dataclass(frozen=True)
class RunConfig:
    """Runtime configuration for a codemod run."""

    mode: str
    spec: RenameSpec | None
    function_name: str | None
    param_name: str | None
    new_param_name: str | None
    param_default: str | None
    call_value: str | None
    docstring_match: str | None
    docstring_replace: str | None
    class_name: str | None
    paths: Sequence[Path]


class RenameSymbol(cst.CSTTransformer):
    def __init__(self, spec: RenameSpec) -> None:
        self._spec = spec

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        if original_node.value == self._spec.old_name:
            return updated_node.with_changes(value=self._spec.new_name)
        return updated_node


class RenameParameter(cst.CSTTransformer):
    def __init__(self, function_name: str, old_name: str, new_name: str) -> None:
        self._function_name = function_name
        self._old_name = old_name
        self._new_name = new_name
        self._function_stack: list[bool] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        self._function_stack.append(node.name.value == self._function_name)
        return True

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if self._function_stack:
            self._function_stack.pop()
        if original_node.name.value != self._function_name:
            return updated_node
        return updated_node.with_changes(
            params=_rename_param_in_params(updated_node.params, self._old_name, self._new_name)
        )

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if not _matches_call_name(original_node, self._function_name):
            return updated_node
        new_args = []
        for arg in updated_node.args:
            if arg.keyword and arg.keyword.value == self._old_name:
                new_args.append(arg.with_changes(keyword=cst.Name(self._new_name)))
            else:
                new_args.append(arg)
        return updated_node.with_changes(args=tuple(new_args))

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        if not self._function_stack or not self._function_stack[-1]:
            return updated_node
        if original_node.value == self._old_name:
            return updated_node.with_changes(value=self._new_name)
        return updated_node


class AddParameter(cst.CSTTransformer):
    def __init__(
        self,
        function_name: str,
        param_name: str,
        default_expr: str | None,
        call_value: str | None,
    ) -> None:
        self._function_name = function_name
        self._param_name = param_name
        self._default_expr = default_expr
        self._call_value = call_value

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if original_node.name.value != self._function_name:
            return updated_node
        return updated_node.with_changes(
            params=_add_param_to_params(updated_node.params, self._param_name, self._default_expr)
        )

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if not _matches_call_name(original_node, self._function_name):
            return updated_node
        if self._call_value is None:
            return updated_node
        if _call_has_keyword(updated_node, self._param_name):
            return updated_node
        value_expr = cst.parse_expression(self._call_value)
        new_arg = cst.Arg(keyword=cst.Name(self._param_name), value=value_expr)
        return updated_node.with_changes(args=(*updated_node.args, new_arg))


class RemoveParameter(cst.CSTTransformer):
    def __init__(self, function_name: str, param_name: str) -> None:
        self._function_name = function_name
        self._param_name = param_name

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if original_node.name.value != self._function_name:
            return updated_node
        return updated_node.with_changes(
            params=_remove_param_from_params(updated_node.params, self._param_name)
        )

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if not _matches_call_name(original_node, self._function_name):
            return updated_node
        new_args = [
            arg
            for arg in updated_node.args
            if not (arg.keyword and arg.keyword.value == self._param_name)
        ]
        return updated_node.with_changes(args=tuple(new_args))


class RewriteDocstring(cst.CSTTransformer):
    def __init__(
        self, class_name: str | None, function_name: str | None, match: str, replace: str
    ) -> None:
        self._class_name = class_name
        self._function_name = function_name
        self._match = match
        self._replace = replace
        self._class_stack: list[str] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self._class_stack.append(node.name.value)
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        _ = original_node
        class_name = self._class_stack.pop()
        if self._class_name and self._function_name is None and class_name == self._class_name:
            return updated_node.with_changes(
                body=_rewrite_docstring_in_body(updated_node.body, self._match, self._replace)
            )
        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if self._function_name is None or original_node.name.value != self._function_name:
            return updated_node

        if self._class_name is None:
            return updated_node.with_changes(
                body=_rewrite_docstring_in_body(updated_node.body, self._match, self._replace)
            )

        in_target_class = bool(self._class_stack and self._class_stack[-1] == self._class_name)
        if in_target_class:
            return updated_node.with_changes(
                body=_rewrite_docstring_in_body(updated_node.body, self._match, self._replace)
            )

        return updated_node


def iter_python_files(explicit_paths: Sequence[Path]) -> Iterable[Path]:
    """Yield Python files from explicit file or directory paths."""
    seen: set[Path] = set()
    for path in explicit_paths:
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")
        if path.is_dir():
            for candidate in path.rglob("*.py"):
                resolved = candidate.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield candidate
            continue
        if path.suffix != ".py":
            raise ValueError(f"Path is not a Python file: {path}")
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            yield path


def apply_transformer(paths: Iterable[Path], transformer: cst.CSTTransformer) -> None:
    """Apply the transformer and rewrite files only when changes occur."""
    for path in paths:
        source = path.read_text(encoding="utf-8")
        module = cst.parse_module(source)
        updated = module.visit(transformer)
        if updated.code != source:
            path.write_text(updated.code, encoding="utf-8")


def _matches_call_name(call: cst.Call, name: str) -> bool:
    return m.matches(call.func, m.Name(name) | m.Attribute(attr=m.Name(name)))


def _call_has_keyword(call: cst.Call, keyword: str) -> bool:
    return any(arg.keyword and arg.keyword.value == keyword for arg in call.args)


def _rewrite_docstring_in_body(body: cst.BaseSuite, match: str, replace: str) -> cst.BaseSuite:
    if not isinstance(body, cst.IndentedBlock):
        return body

    statements = list(body.body)
    if not statements:
        return body

    first_statement = statements[0]
    if not isinstance(first_statement, cst.SimpleStatementLine):
        return body

    if len(first_statement.body) != 1:
        return body

    expr = first_statement.body[0]
    if not isinstance(expr, cst.Expr):
        return body

    value = expr.value
    if not isinstance(value, cst.SimpleString):
        return body

    if match not in value.value:
        return body

    new_literal = value.value.replace(match, replace)
    new_expr = expr.with_changes(value=value.with_changes(value=new_literal))
    new_statement = first_statement.with_changes(body=[new_expr])
    statements[0] = new_statement
    return body.with_changes(body=tuple(statements))


def _rename_param_in_params(params: cst.Parameters, old: str, new: str) -> cst.Parameters:
    return params.with_changes(
        posonly_params=_rename_param_list(params.posonly_params, old, new),
        params=_rename_param_list(params.params, old, new),
        kwonly_params=_rename_param_list(params.kwonly_params, old, new),
        star_arg=params.star_arg,
        star_kwarg=params.star_kwarg,
    )


def _rename_param_list(params: Sequence[cst.Param], old: str, new: str) -> Sequence[cst.Param]:
    renamed: list[cst.Param] = []
    for param in params:
        if param.name.value == old:
            renamed.append(param.with_changes(name=cst.Name(new)))
        else:
            renamed.append(param)
    return tuple(renamed)


def _add_param_to_params(
    params: cst.Parameters, name: str, default_expr: str | None
) -> cst.Parameters:
    default_value = cst.parse_expression(default_expr) if default_expr else None
    new_param = cst.Param(name=cst.Name(name), default=default_value)
    return params.with_changes(params=(*params.params, new_param))


def _remove_param_from_params(params: cst.Parameters, name: str) -> cst.Parameters:
    return params.with_changes(
        posonly_params=_remove_param_list(params.posonly_params, name),
        params=_remove_param_list(params.params, name),
        kwonly_params=_remove_param_list(params.kwonly_params, name),
        star_arg=params.star_arg,
        star_kwarg=params.star_kwarg,
    )


def _remove_param_list(params: Sequence[cst.Param], name: str) -> Sequence[cst.Param]:
    kept = [param for param in params if param.name.value != name]
    return tuple(kept)


def parse_args() -> RunConfig:
    parser = ArgumentParser(description="Run a LibCST codemod across Python files.")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    rename_symbol = subparsers.add_parser("rename-symbol", help="Rename a symbol across files.")
    rename_symbol.add_argument("--old-name", required=True, help="Symbol name to replace.")
    rename_symbol.add_argument("--new-name", required=True, help="Replacement symbol name.")
    _add_common_args(rename_symbol)

    rename_param = subparsers.add_parser("rename-parameter", help="Rename a function parameter.")
    rename_param.add_argument("--function", required=True, help="Function or method name.")
    rename_param.add_argument("--old-name", required=True, help="Parameter name to replace.")
    rename_param.add_argument("--new-name", required=True, help="Replacement parameter name.")
    _add_common_args(rename_param)

    add_param = subparsers.add_parser("add-parameter", help="Add a parameter to a function.")
    add_param.add_argument("--function", required=True, help="Function or method name.")
    add_param.add_argument("--param", required=True, help="Parameter name to add.")
    add_param.add_argument(
        "--default",
        default=None,
        help="Optional default expression (example: 'None' or '0').",
    )
    add_param.add_argument(
        "--call-value",
        default=None,
        help="Optional expression for call-site keyword args (example: 'None').",
    )
    _add_common_args(add_param)

    remove_param = subparsers.add_parser("remove-parameter", help="Remove a parameter.")
    remove_param.add_argument("--function", required=True, help="Function or method name.")
    remove_param.add_argument("--param", required=True, help="Parameter name to remove.")
    _add_common_args(remove_param)

    rewrite_docstring = subparsers.add_parser(
        "rewrite-docstring", help="Rewrite a docstring within a specific scope."
    )
    rewrite_docstring.add_argument(
        "--class",
        dest="class_name",
        default=None,
        help="Class name to target for docstring updates.",
    )
    rewrite_docstring.add_argument(
        "--function",
        default=None,
        help="Function or method name to target for docstring updates.",
    )
    rewrite_docstring.add_argument("--match", required=True, help="Text to match.")
    rewrite_docstring.add_argument("--replace", required=True, help="Replacement text.")
    _add_common_args(rewrite_docstring)

    args = parser.parse_args()
    paths = [Path(path_str) for path_str in args.paths]
    if args.include_tests and Path("tests") not in paths:
        paths.append(Path("tests"))
    spec = None
    if args.mode in {"rename-symbol", "rename-parameter"}:
        spec = RenameSpec(old_name=str(args.old_name), new_name=str(args.new_name))
        if spec.old_name == spec.new_name:
            raise ValueError("Old and new names must differ.")

    return RunConfig(
        mode=str(args.mode),
        spec=spec,
        function_name=getattr(args, "function", None),
        param_name=getattr(args, "param", None),
        new_param_name=getattr(args, "new_name", None),
        param_default=getattr(args, "default", None),
        call_value=getattr(args, "call_value", None),
        docstring_match=getattr(args, "match", None),
        docstring_replace=getattr(args, "replace", None),
        class_name=getattr(args, "class_name", None),
        paths=paths,
    )


def _add_common_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--paths",
        nargs="+",
        required=True,
        help="Explicit list of Python files or directories to update.",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include the tests directory in the update scope.",
    )


def main() -> None:
    config = parse_args()
    if config.mode == "rename-symbol":
        if config.spec is None:
            raise ValueError("Rename spec is required for rename-symbol.")
        transformer: cst.CSTTransformer = RenameSymbol(config.spec)
    elif config.mode == "rename-parameter":
        if config.spec is None or config.function_name is None:
            raise ValueError("Function and rename spec are required for rename-parameter.")
        transformer = RenameParameter(
            config.function_name, config.spec.old_name, config.spec.new_name
        )
    elif config.mode == "add-parameter":
        if config.function_name is None or config.param_name is None:
            raise ValueError("Function and param are required for add-parameter.")
        transformer = AddParameter(
            config.function_name,
            config.param_name,
            config.param_default,
            config.call_value,
        )
    elif config.mode == "remove-parameter":
        if config.function_name is None or config.param_name is None:
            raise ValueError("Function and param are required for remove-parameter.")
        transformer = RemoveParameter(config.function_name, config.param_name)
    elif config.mode == "rewrite-docstring":
        if config.docstring_match is None or config.docstring_replace is None:
            raise ValueError("Match and replace are required for rewrite-docstring.")
        if config.function_name is None and config.class_name is None:
            raise ValueError("Provide --class or --function for rewrite-docstring.")
        transformer = RewriteDocstring(
            config.class_name,
            config.function_name,
            config.docstring_match,
            config.docstring_replace,
        )
    else:
        raise ValueError(f"Unsupported mode: {config.mode}")

    apply_transformer(iter_python_files(config.paths), transformer)


if __name__ == "__main__":
    main()
