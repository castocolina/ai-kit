# Mermaid audit report — `<target>`

Render-verified with `mmdc`: **yes / no** (if no, layout notes are static-only).

## `<relative/path/file.md>`

| Location | Status | Problem | Suggested fix |
|---|---|---|---|
| `file.md:42` | ✅ OK | — | — |
| `file.md:88` | 🔴 SYNTAX | Parse error (block line 3): unquoted `(` in node label | quote it: `A["Deploy (prod)"]` |
| `file.md:140` | 🟡 LAYOUT | 19 nodes in one `LR` graph → wide/cramped on mobile | switch to `graph TD`; group the build steps in `subgraph SG_BUILD` and connect subgraphs, not inner nodes |

(Repeat one section per file.)

## Summary

- Blocks found: **N**
- ✅ OK: **N**
- 🔴 Syntax-broken: **N**
- 🟡 Layout-flagged: **N**
- Verification: render-verified / static-only

Offer to apply the fixes; edit the `.md` only if the user agrees.
