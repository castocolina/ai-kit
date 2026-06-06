---
name: cst-refactor
description: Use when refactoring Python with LibCST codemods — multi-file renames of classes, methods, constants, or function parameters where comments and formatting must survive and naive sed/search-replace risks false-positive matches across unrelated contexts. Includes a bundled codemod_template.py with subcommands rename-symbol, rename-parameter, add-parameter, remove-parameter, rewrite-docstring.
---

## Overview

LibCST parses source into a Concrete Syntax Tree, matches syntax nodes (not raw text), transforms them, and serializes back — comments, whitespace, and style preserved. Codemods replace naive search-and-replace for structural edits.

## Choose codemod vs alternatives

| Scope | Use | Reason |
|---|---|---|
| Single line, single file | `Edit` tool | Codemod overhead unjustified |
| Multi-line, single file | IDE refactor or `Edit` | Faster, no LibCST setup |
| Multi-file, simple rename, name unique in repo | sed + manual review | Cheap; codemod adds no value |
| Multi-file, name appears in unrelated contexts | **codemod** | False-positive risk eliminates sed |
| Signature change (add/remove/rename param) | **codemod** | Manual is error-prone across call sites |
| Dynamic refs (`getattr`, runtime-eval'd strings, configs, templates) | manual + codemod hybrid | Codemod cannot see these — audit by hand |

## Before running (MANDATORY preconditions)

- Working tree clean (`git status` shows nothing). Codemods edit in place; rollback = `git restore`.
- Dry-run on smallest target first (1 file or 1 module). Inspect diff. Then expand `--paths`.
- Pin LibCST version: `uv add --dev "libcst>=1.5,<2"` or whatever the project lock requires. API drift breaks codemods silently.
- Tests exist for the symbol being changed, OR you accept the risk.

## NEVER

- Run on a dirty working tree — codemod edits mix with manual edits, partial fixes become unreviewable.
- Skip preview when targeting >20 files or an unfamiliar codebase. The "small subset first" rule is non-negotiable.
- Use codemod for a single-line, single-file change — overhead beats benefit. Use the `Edit` tool.
- Trust codemod for dynamic references: `getattr(obj, "old_name")`, runtime-evaluated strings, JSON/YAML configs, Jinja/string templates, dotted paths inside strings. Audit these manually.
- Run inside a venv where LibCST is missing — silent partial-success leaves the tree half-converted.
- Touch string literals or comments in the codemod unless the task explicitly requires it.

## Bootstrapping the Template

The codemod script lives at `tools/codemod_template.py` in any project that has it. If the file does not exist in the current project, copy it from this skill's directory (resolved via the plugin root):

```bash
cp "${CLAUDE_PLUGIN_ROOT}/skills/cst-refactor/codemod_template.py" tools/codemod_template.py
```

Then install LibCST if needed:
```bash
uv add --dev libcst
```

## Examples

Rename a class used across modules:
```bash
uv run python tools/codemod_template.py rename-symbol --old-name OldName --new-name NewName --paths src --include-tests
```

Rename a method and update call sites:
```bash
uv run python tools/codemod_template.py rename-symbol --old-name connect --new-name open --paths src --include-tests
```

Rename a constant used in multiple modules:
```bash
uv run python tools/codemod_template.py rename-symbol --old-name DEFAULT_TIMEOUT --new-name DEFAULT_REQUEST_TIMEOUT --paths src --include-tests
```

Rename a parameter and update keyword call sites:
```bash
uv run python tools/codemod_template.py rename-parameter --function fetch --old-name timeout --new-name request_timeout --paths src --include-tests
```

Add a parameter with a default:
```bash
uv run python tools/codemod_template.py add-parameter --function run --param debug --default False --paths src --include-tests
```

Remove a parameter and drop keyword usage:
```bash
uv run python tools/codemod_template.py remove-parameter --function deploy --param dry_run --paths src --include-tests
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
