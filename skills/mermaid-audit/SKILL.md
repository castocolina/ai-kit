---
name: mermaid-audit
description: >-
  Audit Mermaid diagrams embedded in Markdown (.md) files — extract every
  ```mermaid block, render each with the Mermaid CLI (mmdc) to catch syntax
  errors, and do a qualitative review of layout and readability (especially
  flowcharts: grouping, subgraph direction, node distribution, naming). Use this
  whenever the user mentions Mermaid diagrams, a diagram that won't render or
  shows a broken/"bomb" image, validating or reviewing diagrams in
  docs/README/Markdown, or fixing a diagram that looks bad — too wide, too tall,
  cramped, tangled, or illogically ordered. Also use before publishing docs with
  diagrams. Targets Markdown specifically, not HTML-embedded diagrams.
---

# Mermaid Audit

Find and explain what is wrong with Mermaid diagrams inside Markdown — both
**syntax** errors (won't render) and **layout** problems (renders but reads
badly). This is a qualitative, analytical pass: unlike a typed pre-commit
validator that just gates input, the goal here is a human-useful diagnosis of
*why* a diagram is broken or hard to read, and how to restructure it.

In Markdown a diagram is plain fenced code, so there are no HTML entities to
worry about — the failure modes are Mermaid's own grammar and how the graph is
shaped. Flowcharts get special attention because **you cannot place nodes** in a
flowchart: the layout engine decides positions, and your only levers are
subgraphs, per-subgraph `direction`, and declaration order. Most "ugly diagram"
complaints are really "the engine laid it out badly because the structure didn't
guide it."

**Audit, don't edit.** Report findings as `file:line · status · problem · fix`.
Apply fixes only if the user asks.

## Workflow

1. Check the toolchain (`mmdc`) — **Setup**.
2. Run the mechanical pass — `python3 scripts/audit_mermaid.py <target.md | dir>`
   extracts every block, renders it, and reports syntax status with `file:line`.
3. For blocks that render, do the qualitative pass — **Syntax pitfalls** and
   **Flowchart layout & readability** (read the PNGs with `--keep-png`).
4. Emit the report using `template.md`.

The render is ground truth: `mmdc` runs the real Mermaid parser, so it catches
exactly what the user's renderer will. Reserve static heuristics for when the
tool is unavailable.

## Setup: mmdc

```bash
command -v mmdc || echo "mmdc not found"
```

`mmdc` is `@mermaid-js/mermaid-cli`; it bundles **puppeteer** (a headless
Chromium for rendering). If missing, recommend a manager that gives control over
dependency lifecycle scripts — the usual npm supply-chain risk is arbitrary
`pre/postinstall` scripts:

- **volta** — `volta install @mermaid-js/mermaid-cli` (pins a clean toolchain).
- **pnpm** — `pnpm add -g @mermaid-js/mermaid-cli` (pnpm asks before running a
  dependency's build scripts) or ephemeral `pnpm dlx @mermaid-js/mermaid-cli …`.

Puppeteer normally needs its `postinstall` to fetch Chromium; if you hard-disable
install scripts, set `PUPPETEER_EXECUTABLE_PATH` to an existing Chrome instead.

**Sandbox config.** As root, in containers, or in CI, Chromium's sandbox fails
and `mmdc` errors before parsing. The bundled script writes a default; by hand,
create `puppeteer-config.json` with
`{ "args": ["--no-sandbox", "--disable-setuid-sandbox"] }` and pass `-p` to mmdc.
A Chromium/sandbox error is **not** a diagram problem — don't report it as one.

If `mmdc` can't be installed, fall back to the **Syntax pitfalls** checklist as a
best-effort static review and say clearly the diagrams were not render-verified.

## Extract & render (mechanical pass)

**Recommended:** `scripts/audit_mermaid.py` (stdlib only, no Python deps; needs
`mmdc` for the render step). It does extract → render → report in one shot, on a
single file or a whole tree, mapping each result back to `file.md:line`:

```bash
python3 scripts/audit_mermaid.py --keep-png path/to/docs/   # dir scan
python3 scripts/audit_mermaid.py README.md                  # single file
```

`--keep-png` keeps the rendered images for the visual/layout pass. Output is one
TSV line per block: `file:line  OK|SYNTAX|NOT-VERIFIED  message`.

**Fallback:** `scripts/audit_mermaid.sh` is a thin wrapper — it execs the `.py`
when `python3` exists, else runs a minimal `awk` + `mmdc` pass (no line mapping)
so the skill still works without Python.

How it reads mmdc's outcome (this is the real debug signal — not just an image):
a non-zero exit with `Parse error on line N…` is a definitive syntax error, and
the script maps Mermaid's block-relative line N back to the `.md` line and prints
the message. The PNG is only needed for the layout pass, or — rarely — when the
exit code is clean but the image shows Mermaid's red **"Syntax error"** bomb card.

## Syntax pitfalls (Markdown-specific)

Markdown mermaid blocks are raw text — **don't use HTML entities** (`&quot;`,
`&gt;`); they render literally and break the diagram. The real traps:

- **Quote labels with special characters.** `( ) [ ] { } < > " | ; #` collide
  with node/edge syntax and must sit inside a quoted label.
  `A[Deploy (prod)]` breaks → `A["Deploy (prod)"]`.
- **Line breaks: `<br/>`, not `\n`.** In a normal string label a literal `\n`
  does nothing — use `<br/>` to break a line. Better, use a **markdown string**
  (below), where a real newline works.
- **Markdown strings** wrap the label in `"` + backticks and give you formatting
  plus auto-wrap. Inside them, `**bold**` and `*italic*` work, and a real newline
  starts a new line (no `<br/>` needed). Example:
  `A["` `` `**Build** step` `` `"] --> B`. Prefer these for any label needing
  emphasis or multiple lines — more readable, and they avoid the `\n` trap.
- **`end` (lowercase) is reserved** in flowcharts/subgraphs → capitalize `End` or
  quote it.
- **First non-empty line declares the diagram type** (`graph`/`flowchart`,
  `sequenceDiagram`, `classDiagram`, `stateDiagram-v2`, `erDiagram`, …). A typo
  there fails the whole block.
- **Node IDs are bare identifiers**; human text goes in the shape brackets/quotes.
  `my node --> other` is invalid; `n1["my node"] --> n2` works.

## Flowchart layout & readability

The recurring complaint — "it renders but looks terrible" — is almost always a
flowchart whose structure didn't guide the engine. Reasoning and fixes:

- **You can't position nodes; structure is your only lever.** Influence layout
  with subgraphs, per-subgraph `direction`, and declaration order — not by
  trying to place things.

- **Group at ~10+ elements.** When a diagram has roughly ten or more nodes and
  starts looking tangled or poorly distributed, group related nodes into
  `subgraph`s. This both clarifies meaning and gives the engine structure.

- **Connect subgraphs at the boundary; avoid cross-subgraph internal edges.**
  Draw edges *between subgraphs* (or subgraph↔node), not from a node buried in
  one subgraph straight to a node buried in another. There's a concrete reason
  beyond aesthetics: Mermaid's rule is **"if any of a subgraph's nodes are linked
  to the outside, the subgraph's `direction` is ignored and it inherits the
  parent's direction."** So cross-subgraph internal edges silently destroy your
  control over that subgraph's internal layout. Keep internal nodes internal;
  wire the groups together.

- **Use `direction` to distribute — globally and per subgraph.** Set the parent
  direction (`graph TD`/`LR`) and give a subgraph its own `direction` to shape
  its internal flow (e.g. an overall `TD` with one `LR` subgraph for a short
  parallel step) — valid only while that subgraph has no internal node linked
  outside (see above). Prefer top-down (`TD`) overall for docs/mobile (≤768px);
  reserve `LR` for genuinely short, horizontal flows.

- **Name coherently and correlated.** Give subgraphs and their nodes correlated
  IDs so big diagrams stay navigable and diffs readable: `SG_AUTH`/`SG_BILLING`
  for subgraphs, `NODE_AUTH_login`/`NODE_BILLING_charge` for their nodes. The
  prefix makes it obvious which group a node belongs to.

- **Watch the shape.** A long single chain (very tall `TD` or wide `LR` snake) or
  an aspect ratio more extreme than ~3–4:1 reads poorly — break into phases with
  subgraphs or split into multiple diagrams. Many crossing/back edges mean the
  declaration order fights the flow; declare nodes in reading order and keep the
  primary path monotonic.

- **One idea per diagram.** Architecture *and* sequence *and* data model in one
  picture is the real defect — recommend splitting.

See `examples/good-and-bad.md` and the runnable `examples/*.mmd`
(`examples/good-subgraphs.mmd` shows grouping + correlated naming + per-subgraph
`direction`).

## Report

Use `template.md`. Group by file; one line per block with `file:line`, status
(✅ OK / 🔴 SYNTAX / 🟡 LAYOUT), the problem, and a concrete fix. End with a
summary (found / OK / syntax-broken / layout-flagged, and whether render-verified
or static-only), then offer to apply fixes — editing the `.md` only on request.
