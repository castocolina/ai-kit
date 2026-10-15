---
name: cst-refactor
description: Use when refactoring Python with LibCST codemods — multi-file renames of classes, methods, constants, or function parameters where comments and formatting must survive and naive sed/search-replace risks false-positive matches across unrelated contexts. Includes a bundled codemod_template.py.txt (copy into the project as tools/codemod_template.py) with subcommands rename-symbol, rename-parameter, add-parameter, remove-parameter, rewrite-docstring.
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
- Point a subcommand at a name another library also defines unless every match is yours. Matching is by name only, with no scope or type resolution: `rename-symbol` renames every `Name` node with that value, attribute access included (renaming a `connect` method also turns `sqlite3.connect(...)` into `sqlite3.open(...)`), and the parameter subcommands edit every function def named `--function` and every call ending in `.<function>(...)` (`--function run` also hits `subprocess.run(...)`). `rename-parameter` renames the name only inside the target def's body and in keywords of calls to `--function`; attribute names (`self.timeout`) and keywords of other calls (`requests.get(url, timeout=...)`) keep their spelling. Restrict `--paths`, then read the whole diff.
- Touch string literals or comments in the codemod unless the task explicitly requires it.

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

Add a parameter with a default (add `--call-value <expr>` to also pass it as a keyword at every call site that lacks it):
```bash
uv run python tools/codemod_template.py add-parameter --function run_migration --param debug --default False --paths src --include-tests
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
- Tighten matchers or use LibCST metadata when you need to avoid false positives.
- Run from the project root and ensure dev dependencies are installed (LibCST).
- Prefer `uv run python` unless your venv is already active.
- Codemods only touch `.py` files in the given paths. Check other docs only if the refactor scope demands it.
