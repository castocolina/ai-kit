# Mermaid audit report — `<target>`

Render-verified with `mmdc`: **yes / no** (if no, layout notes are static-only).

## `<relative/path/file.md>`

| Location | Status | Problem | Suggested fix |
|---|---|---|---|
| `file.md:42` | ✅ OK | — | — |
| `file.md:88` | 🔴 SYNTAX | Parse error (block line 3): unquoted `(` in node label | quote it: `A["Deploy (prod)"]` |
| `file.md:140` | 🟡 LAYOUT | 19 nodes in one `LR` graph → wide/cramped on mobile | switch to `graph TD`; group the build steps in `subgraph SG_BUILD` and connect subgraphs, not inner nodes |
| `file.md:140` | 🎨 COLOR (C1) | 11 nodes, no classDef — flat default gray | apply a role palette from `references/palettes.md` |
| `file.md:140` | 🔷 SHAPE (S1) | `Validate` branches (2 labeled edges) but is a rectangle | make it a diamond `Validate{...}` |
| `file.md:140` | 📐 GEOMETRY (R1) | rendered 1400×360px, ratio 0.26 < 0.4 — too horizontal | `graph TD` + stacked subgraphs to trade width for height |

(Repeat one section per file.)

## Summary

- Blocks found: **N**
- ✅ OK: **N**
- 🔴 Syntax-broken: **N**
- 🟡 Layout-flagged: **N**
- 🎨 Color-flagged: **N**
- 🔷 Shape-flagged: **N**
- 📐 Geometry-flagged: **N** (render-measured; "not measured" without `mmdc`)
- Verification: render-verified / static-only

Offer to apply the fixes; edit the `.md` only if the user agrees.
