---
name: mermaid-audit
description: >-
  Audit Mermaid diagrams embedded in Markdown (.md) files — extract every
  ```mermaid block, render each with the Mermaid CLI (mmdc) to catch syntax
  errors, and review four axes: layout/readability, color palette, node shapes,
  and aspect ratio. Flags flat default-gray or garish/low-contrast color and
  emits ready-to-paste `classDef` palettes; flags wrong node shapes (a decision
  drawn as a rectangle, a datastore not a cylinder); flags diagrams too wide
  (low height/width ratio — shrinks below legibility in GitHub's reading column)
  or too tall (endless scroll). Use this whenever the user mentions Mermaid
  diagrams, a diagram that won't render or shows a broken/"bomb" image,
  validating or reviewing diagrams in docs/README/Markdown, or fixing a diagram
  that looks bad — won't render, too wide/tall, cramped, tangled, flat/gray,
  garish, badly colored, wrong shapes, or hard to read. Also use before
  publishing docs with diagrams. Targets Markdown specifically, not
  HTML-embedded diagrams.
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

**Before flagging anything, ask:** *who renders this, and at what width?* A diagram
is only "bad" relative to where it's read. The default target is a Markdown reading
column (GitHub/GitLab/docs: ~900px, centered, scaled-to-fit) — so the failure that
matters most is not "ugly" but "**illegible or unscannable in that column**": text
shrunk below reading size, a layout that forces sideways scroll, or color that adds
no signal. Diagnose the *cause* (structure the engine couldn't lay out, a shape that
lies about a node's role, a palette with no semantics), not just the symptom — the
fix is almost always restructuring, never nudging pixels.

## Workflow

1. Check the toolchain (`mmdc`) — **Setup**.
2. Run the mechanical pass — `python3 scripts/audit_mermaid.py <target.md | dir>`
   extracts every block, renders it, and reports syntax status with `file:line`.
3. For blocks that render, do the qualitative pass — **Syntax pitfalls**,
   **Flowchart layout & readability**, and **Color & shape** (run
   `python3 scripts/mermaid_style.py <target>`; read the PNGs with `--keep-png`
   for the geometry/aspect-ratio rules).
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

## Color & shape (palette + semantics pass)

A diagram can render and lay out fine yet still read flat or misleading: default
gray everywhere, garish rainbow fills, low-contrast pastels, or shapes that fight
their meaning (a rectangle where a decision diamond belongs). Run the static
analyzer, then apply judgment for the two fuzzy rules.

**Mechanical pass:** `python3 scripts/mermaid_style.py <target.md | dir>` — emits one
TSV line per finding: `file:line  RULE  severity  message  → fix`. Stdlib only;
flowchart/`graph` blocks only (other diagram types are skipped).

Rules (a hit is an objective gate — independent reviewers should agree):

| Rule | Fires when | Fix |
|------|-----------|-----|
| **C1** | ≥6 nodes, zero `classDef`/`style` — flat default gray | apply a palette from `references/palettes.md` by role |
| **C2** | a fill's contrast < 3:1 vs white canvas *and* its stroke | darken fill or add a darker stroke |
| **C3** | >6 distinct fills — garish | collapse to ≤6 semantic classes |
| **C4** *(judgment)* | color isn't semantic — same role ≠ same fill, or unrelated nodes share one | assign classes by role, not by node |
| **C5** | red & green are the only distinguishing fills | add a second channel (shape/label/accent) |
| **S1** | a labeled branch (out-degree ≥2) drawn as a rectangle | make it a diamond `X{...}` |
| **S3** | a datastore-named node isn't a cylinder | use `X[(...)]` |
| **S4** | >4 distinct shapes, no class system — shape noise | reserve shapes for roles |
| **S5** *(judgment)* | same-role nodes use different shapes | normalize shape per role |

**Geometry / aspect ratio (the "forma" axis — needs the render).** A diagram's
*shape on screen* is the biggest readability lever. Markdown viewers like GitHub render
Mermaid into a **fixed, centered reading column** (~900px) and **scale the SVG to fit**,
preserving aspect ratio — so a wide diagram is shrunk (text becomes unreadable until you
expand), and an extremely tall one buries the reader in scroll. Aim **vertical-leaning,
in band**: not flatter than ratio 0.4, not taller than ~3 pages. These come from the
render loop (`audit_mermaid.py` measures each rendered PNG); they need `mmdc` and report
as `not measured` without it.

| Rule | Fires when | Fix |
|------|-----------|-----|
| **R1** | rendered height/width ratio < 0.4 — too horizontal | `graph TD`; fold parallel branches into stacked subgraphs connected at boundaries |
| **R2** | width > reading column → text scales below ~11px (legible only when expanded) | reduce width: `TD`, fewer side-by-side branches, subgraphs |
| **R3** | rendered height > ~3 viewport pages — too vertical | split into multiple diagrams (one idea each); collapse long chains |
| **R4** *(judgment)* | big boxes, little text — wasted vertical space | shorten labels or merge nodes; don't pad height with near-empty boxes |

The lever for all of R1–R3 is the same Mermaid reality from *Flowchart layout* above:
you can't place nodes, so use **`direction` + `subgraph`s + boundary connections** to
trade a too-wide layout for a balanced, vertical-leaning one — and split when one diagram
is carrying more than one idea.

**Palettes (load on demand):** **only when you are emitting a color fix (C1–C5)**,
read `references/palettes.md` — three sober, contrast-checked palettes
(structural/layer, status/accent, old-vs-new) with ready `classDef` blocks and combining
guidance (one accent against mostly neutral). Copy a `classDef` block from it as the fix —
**recommend, don't auto-edit** (consistent with audit-don't-edit). Accessibility checks
(C2/C5) are **advisory**.

**Do NOT load** `references/palettes.md` for a syntax-only or layout-only audit, and do
**not** read `examples/*` unless you need a worked good/bad pair to show the user — they
are illustrative, not required to run the audit. The two scripts plus the rule tables
above are everything the audit itself needs.

## NEVER (landmines, with the non-obvious reason)

- **NEVER report a Chromium/sandbox error as a diagram defect.** `mmdc` failing to
  launch (no-sandbox, missing Chrome, CI permissions) happens *before* parsing — the
  diagram was never evaluated. Fix the toolchain (`-p puppeteer-config.json`), don't
  file a finding.
- **NEVER trust a clean exit code alone.** Mermaid can exit 0 and still render the red
  **"Syntax error" bomb card** into the PNG. For a clean exit, glance at the image
  before declaring OK.
- **NEVER auto-edit the diagram.** This is an auditor — emit the `file:line · fix` (and
  for color, the ready `classDef`). Edit the `.md` only when the user explicitly asks.
- **NEVER use HTML entities** (`&quot;`, `&gt;`) in a Markdown mermaid block — they
  render literally and break the label. Quote with real characters inside `"…"`.
- **NEVER link an *inner* node of one subgraph to an inner node of another.** Mermaid's
  rule: if any of a subgraph's nodes connect outside, that subgraph's `direction` is
  silently ignored and it inherits the parent's — you lose layout control with no error.
  Connect subgraph-to-subgraph instead.
- **NEVER "fix" a cramped/too-wide diagram by widening it or switching to `LR`.** In a
  fixed reading column, extra width is *scaled down*, shrinking text below legibility
  (R2). Trade width for height: `graph TD` + stacked subgraphs + boundary connections.
- **NEVER treat color/contrast as a hard gate.** C2/C5 (contrast, color-blind safety)
  are **advisory** — surface them, don't block on them.
- **NEVER escalate an `(judgment)` rule (C4/S5/R4) to an automatic flag.** They need a
  human call; the analyzer can't decide them and neither should you without evidence.

## Report

Use `template.md`. Group by file; one line per block with `file:line`, status
(✅ OK / 🔴 SYNTAX / 🟡 LAYOUT), the problem, and a concrete fix. End with a
summary (found / OK / syntax-broken / layout-flagged, and whether render-verified
or static-only), then offer to apply fixes — editing the `.md` only on request.
