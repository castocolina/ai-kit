---
name: cst-refactor
description: Use when refactoring Python with LibCST codemods — multi-file renames of classes, methods, constants, or function parameters where comments and formatting must survive and naive sed/search-replace would also hit strings and comments (codemods match by name, not by scope or type). Includes a bundled codemod_template.py.txt (copy into the project as tools/codemod_template.py) with subcommands rename-symbol, rename-parameter, add-parameter, remove-parameter, rewrite-docstring.
---

## Overview

LibCST parses source into a Concrete Syntax Tree, matches syntax nodes (not raw text), transforms them, and serializes back — comments, whitespace, and style preserved. Codemods replace naive search-and-replace for structural edits.

## Choose codemod vs alternatives

| Scope | Use | Reason |
|---|---|---|
| Single line, single file | `Edit` tool | Codemod overhead unjustified |
| Multi-line, single file | IDE refactor or `Edit` | Faster, no LibCST setup |
| Multi-file, simple rename, name unique in repo | sed + manual review | Cheap; codemod adds no value |
| Multi-file, name is a class/function/constant whose identifier appears in comments, strings, or longer identifiers | **codemod** | Matches whole `Name` nodes only, never text inside strings, comments, or other identifiers |
| Name is shared with an unrelated symbol (`connect`, `open`, `get`, a stdlib/third-party attribute) | `rename-symbol` on a narrow `--paths`, then audit, or a custom codemod with `QualifiedNameProvider` | `rename-symbol` is name-only: it has no scope or type resolution and renames every `Name` with that value |
| Signature change (add/remove/rename param) | **codemod** | Manual is error-prone across call sites |
| Dynamic refs (`getattr`, runtime-eval'd strings, configs, templates) | manual + codemod hybrid | Codemod cannot see these — audit by hand |

## Before running (MANDATORY preconditions)

- Working tree clean (`git status` shows nothing). Codemods edit in place; rollback = `git restore`.
- There is no `--dry-run` flag: run on one file or module first, inspect `git diff`, then expand `--paths`.
- Pin LibCST version: `uv add --dev "libcst>=1.5,<2"` or whatever the project lock requires. API drift breaks codemods silently.
- Tests exist for the symbol being changed, OR you accept the risk.

## NEVER

- Run on a dirty working tree — codemod edits mix with manual edits, partial fixes become unreviewable.
- Skip preview when targeting >20 files or an unfamiliar codebase. The "small subset first" rule is non-negotiable.
- Use codemod for a single-line, single-file change — overhead beats benefit. Use the `Edit` tool.
- Trust codemod for dynamic references: `getattr(obj, "old_name")`, runtime-evaluated strings, JSON/YAML configs, Jinja/string templates, dotted paths inside strings. Audit these manually.
- Point a subcommand at a name another library also defines unless every match is yours. Matching is by name only, with no scope or type resolution: `rename-symbol` renames every `Name` node with that value, attribute access included (renaming a `connect` method also turns `sqlite3.connect(...)` into `sqlite3.open(...)`), and the parameter subcommands edit every function def named `--function` and every call ending in `.<function>(...)` (`--function run` also hits `subprocess.run(...)`). `rename-parameter` renames the name only inside the target def's body (nested defs included, unless one declares its own parameter of that name) and in keywords of calls to `--function`; attribute names (`self.timeout`) and keywords of other calls (`requests.get(url, timeout=...)`) keep their spelling. Restrict `--paths`, then read the whole diff.
- Touch string literals or comments in the codemod unless the task explicitly requires it.

## What each subcommand changes

- `rename-symbol`: renames every `Name` with that value: the definition, calls, imports, attribute access (`module.old_name`) and keyword-argument names (`call(old_name=1)`); comments and string literals keep the old text; equal old and new names stop the run with a `ValueError`.
- `rename-parameter`: renames the parameter in each def named `--function`, its uses inside that body (f-strings included) and the keyword at calls to `--function`; docstrings, other calls' keywords and attributes keep their spelling; a `*args` or `**kwargs` parameter is renamed too.
- `add-parameter`: adds `<param> = <default>` to each def named `--function`, before any `*args` (which changes positional binding); without `--call-value` call sites are left alone; with it every call to `--function`, method calls included, gains the keyword; a parameter with no `--default` after a defaulted one fails validation and leaves that file untouched.
- `remove-parameter`: removes the parameter from each def and its keyword from calls; positional call arguments stay, so check each call in the diff; a trailing comma can remain; `*args` and `**kwargs` parameters are never removed.
- `rewrite-docstring`: replaces `--match` with `--replace` in the docstring of `--class`, of `--function`, or of that method when both are given; an f-string docstring is skipped silently; with neither flag the run stops with a `ValueError`.
- Every subcommand: files are rewritten one by one with no dry run, and a file is written only when its text changes; directories are walked in filesystem order; `--include-tests` adds `tests` relative to the working directory and stops with `Path does not exist: tests` when there is none; a missing path or a non-`.py` file stops the run; a file that fails to parse aborts the run after the files before it were already rewritten: run `git restore <paths>`, fix or leave out that file, and run again.

## Validation loop

1. Run the subcommand on a narrow `--paths` (one file or one module).
2. Read `git diff`.
3. Run the tests.
4. If the diff holds an unrelated match (a library name such as `connect`) or a test fails, run `git restore <paths>` and narrow `--paths`.
5. Repeat until the diff holds only intended changes, then widen `--paths` and go back to step 2; a path with no matching symbol changes nothing.
6. Run `rg -n "<old name>"` for dynamic references the codemod cannot reach (strings, `getattr`, configs, templates); a second run of the same rename changes nothing.

## Bootstrapping the Template

The codemod script lives at `tools/codemod_template.py` in any project that has it. If the
file does not exist in the current project, copy `codemod_template.py.txt` from this skill's
directory (the folder that contains this `SKILL.md`) into the project:

```bash
mkdir -p tools
cp "<this skill's directory>/codemod_template.py.txt" tools/codemod_template.py
```

On a Claude Code plugin install, that directory is
`${CLAUDE_PLUGIN_ROOT}/skills/cst-refactor`.

Then install LibCST if needed (without it the script fails at import and changes nothing):
```bash
uv add --dev "libcst>=1.5,<2"
```

## Examples

Rename a class used across modules:
```bash
uv run python tools/codemod_template.py rename-symbol --old-name OldName --new-name NewName --paths src --include-tests
```

Rename a project-specific method and its call sites (a name no imported library uses):
```bash
uv run python tools/codemod_template.py rename-symbol --old-name fetch_invoice_rows --new-name load_invoice_rows --paths src --include-tests
```

Rename a constant used in multiple modules:
```bash
uv run python tools/codemod_template.py rename-symbol --old-name DEFAULT_TIMEOUT --new-name DEFAULT_REQUEST_TIMEOUT --paths src --include-tests
```

Rename a parameter and update keyword call sites:
```bash
uv run python tools/codemod_template.py rename-parameter --function fetch_invoice_rows --old-name timeout --new-name request_timeout --paths src --include-tests
```

Add a parameter with a default (call sites stay as they are):
```bash
uv run python tools/codemod_template.py add-parameter --function run_migration --param debug --default False --paths src --include-tests
```

Add it and pass it at every call site:
```bash
uv run python tools/codemod_template.py add-parameter --function run_migration --param debug --default False --call-value False --paths src --include-tests
```

Remove a parameter and drop keyword usage:
```bash
uv run python tools/codemod_template.py remove-parameter --function deploy_release --param dry_run --paths src --include-tests
```

Rewrite a docstring within a specific class or method:
```bash
uv run python tools/codemod_template.py rewrite-docstring --class Person --function __init__ --match name --replace nickname --paths src --include-tests
```

## Notes

- Do not alter string literals or comments unless explicitly required.
- Validate changes with tests after codemod runs.
- Use the `context7:query-docs` skill (or `mcp__context7__query-docs`) to confirm LibCST APIs when needed.
- For a name another library also defines, restrict `--paths` and audit the diff (the default); write a custom codemod with `QualifiedNameProvider` only when narrowing cannot separate the two names.
- Run from the project root and ensure dev dependencies are installed (LibCST).
- Prefer `uv run python` unless your venv is already active.
- Codemods only touch `.py` files in the given paths. Check other docs only if the refactor scope demands it.
