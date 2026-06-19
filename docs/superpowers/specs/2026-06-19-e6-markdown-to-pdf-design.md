# E6 — `markdown-to-pdf` skill — Design

**Status**: design ready · **Branch**: `feat/e6-doc-to-pdf` · **Created**: 2026-06-19
**Source requirements**: `docs/prds/000-ai-kit-overhaul-requirements.md` §E6 (FR-6.1 … FR-6.9)

## Intent

Turning a Markdown document with embedded mermaid diagrams into a good PDF is a
repeated manual chore: extract each diagram, render it to an image, build a
text-plus-placeholders template, link the images, run a converter, and re-figure-out
image inclusion every time. The same friction hits producing a **marp** deck from
Markdown that contains mermaid. E6 is a **single skill that automates this end to
end**, reusing the diagram extract/render mechanism `mermaid-audit` already has and
cooperating with the `marp-slide` skill for decks — without reinventing either.

The skill is named **`markdown-to-pdf`**: the source is always Markdown, so the name
states the input and the primary output. The secondary marp path can also emit
PPTX/HTML, but PDF is the headline target.

## Scope

- **Primary**: Markdown document → PDF, every embedded ` ```mermaid ` block rendered
  and embedded automatically (FR-6.1).
- **Secondary**: Markdown-with-mermaid → marp deck (PDF/PPTX/HTML) (FR-6.8).
- **Out of scope**: editing/authoring Markdown, diagram *quality* auditing (that is
  `mermaid-audit`), and any modification of the source file.

## Architecture

A single self-contained skill under `skills/markdown-to-pdf/`, structured like the
kit's other skills (self-contained, portable across harnesses — no shared package
tree, no cross-skill filesystem coupling):

```
skills/markdown-to-pdf/
  SKILL.md                  # orchestration prose: decision logic, marp delegation, install guidance
  scripts/
    render_mermaid.py       # adapted fence-extraction + mmdc-render from mermaid-audit (stdlib-only, ~40 lines)
    markdown_to_pdf.py      # engine: temp-copy -> render fences -> substitute -> backend -> emit PDF
    detect_backends.py      # complete-pipeline detection + ranking
  references/
    backends.md             # scored backend comparison + exact install commands
  examples/
    sample-with-mermaid.md  # reference input
```

`markdown_to_pdf.py` is the engine. `SKILL.md` is the thin orchestration layer that
handles capability-conditional behavior (marp-slide delegation) and surfaces install
recommendations to the user. Scripts are stdlib-only where possible; the only hard
*external* dependency is `mmdc` (for diagram render) plus whichever backend is selected.

## Core pipeline — non-destructive by contract (FR-6.1 / 6.2 / 6.3)

1. **Copy** the source `.md` into a temporary working directory. The source is
   **never modified** — byte-for-byte intact (FR-6.2).
2. **Extract** each ` ```mermaid ` fence via `render_mermaid.find_fences()`; **render**
   each with `mmdc` into the temp dir via `render_mermaid.render_all()`.
3. **Substitute** each fence with an image link **in the copy only** (placeholder →
   image-link substitution).
4. **Convert** the rewritten copy with the selected backend → PDF.
5. **Emit** the PDF **alongside the source** by default, or to a user-specified
   path/dir (FR-6.3). Clean up the temp dir.

**Diagram render format**: **PNG at high DPI (`mmdc -s 3`) by default** — the universal
lowest-common-denominator across every backend. SVG is used only when the *selected*
backend handles it well (Typst native; headless-Chromium). SVG is avoided for
Pandoc+LaTeX (needs `rsvg-convert`) and WeasyPrint (incomplete SVG renderer).

## Backend selection — pipeline-level detection (FR-6.5 / 6.7)

`detect_backends.py` tests **complete pipelines**, not individual tools. This is a hard
requirement, not a nicety: a tool can be present while its pipeline is unusable — e.g.
`pdflatex` installed but `pandoc` absent yields **no** working Markdown→PDF path. The
detector reports only pipelines whose every component resolves on `PATH`.

**Researched candidates and scores** (full table in `references/backends.md`; criteria:
install ease, agent-friendliness, output quality, image/diagram handling — 1–5 each):

| Backend | Total /20 | Notes |
|---|---|---|
| **Typst (+ Pandoc)** | **18** | Winner: small self-contained binaries, fast, deterministic, native SVG+PNG |
| Pandoc + LaTeX (tectonic/xelatex) | 13 | Best typography; heavy; SVG needs `rsvg-convert`; noisy errors |
| WeasyPrint | 13 | Lightweight Python; needs Pango system lib; patchy SVG; 2-step |
| Headless-Chromium / md-to-pdf | 13 | Best SVG fidelity; huge Chromium; container-launch fragility |

**Selection rule**:
- **Use the best *complete* pipeline already installed**, by quality order
  **Pandoc+LaTeX > Typst > WeasyPrint > Chromium** (all "good enough"). Don't nag the
  user to install something when an installed backend is fully capable and the quality
  gap is small (FR-6.7).
- **If no complete pipeline is installed**, recommend installing the researched
  winner, **Typst + Pandoc** — smallest footprint, most agent-friendly, native SVG.

## Install guidance — never auto-install (FR-6.6 / 6.9)

The skill **detects + recommends; it never installs** (FR-6.6). When a required tool is
missing it prints the **exact non-interactive command** using secure/modern managers,
preferring **`uv`** (Python), **`pnpm`** (Node), **`cargo`** (native) — falling back to
`brew`/`npm`/`pip` only when the preferred manager is absent. The user runs it.

If a clearly superior backend exists but isn't installed, surface it as a
recommendation — but prefer a fully-capable installed backend when the gap is small
(FR-6.7). If no backend is available and the user declines to install, the skill states
**exactly what is missing and what it would have run** (FR-6.9). On success it reports
**which backend and diagram renderer were used**.

## Marp secondary path — `marp-cli` backbone + opportunistic delegation (FR-6.8)

Marp support is a **hybrid** that always works and improves when `marp-slide` is present:

- **Backbone**: E6 self-owns the deck flow via **`marp-cli`** — detect + recommend-install
  like any other backend. The deck path works without any external plugin.
- **Opportunistic delegation**: `SKILL.md` checks **its own available-skills list** for
  `marp-slide`; if present, it **delegates the deck build to `marp-slide`** (for its
  themes/polish); if absent, it self-drives `marp-cli`.

This delegation is expressed at the **orchestration layer** (the agent reading its
capability list), **not** as a script-level plugin-path probe. Rationale: skill
availability is reliably knowable only to the orchestrating agent; a Python probe of
`~/.claude/plugins/…` is Claude-Code-specific path coupling that breaks the kit's
cross-harness portability. Either way the diagrams are pre-rendered first (same
mechanism as the PDF path), then handed to the deck builder.

## Sharing the extract/render mechanism — adapted from mermaid-audit (FR-6.4)

`render_mermaid.py` adapts the fence-extraction + mmdc-render mechanism (regex +
subprocess call) from `mermaid-audit`'s `audit_mermaid.py`
(`skills/mermaid-audit/scripts/audit_mermaid.py`, a 141-line **stdlib-only** file)
into a small string-based API (`find_fences`/`render_one`/`render_all`) — not a
verbatim copy of the origin's `extract()`/`render()` functions. A header comment
names that file as the **canonical origin**.

Rationale for vendoring over the alternatives:
- **Invoking the whole `mermaid-audit` skill is rejected** — E6 needs ~20% of it and
  would load an unrelated audit surface, risking an unintended full audit workflow.
- **A shared Python package is not idiomatic here** — skills are self-contained, not a
  shared module tree; importing across skills breaks portability.
- **The snippet is tiny and stable** — mermaid fence grammar + the `mmdc` CLI rarely
  change, so drift risk is near-zero. Vendoring keeps E6 self-contained and portable,
  while honoring "don't write a *divergent* extractor" (it is the *same* mechanism).

## Error handling

- **Diagram render failure → abort.** If any mermaid block fails to render, the skill
  **stops the whole conversion** and surfaces **`mmdc`'s own stderr** (e.g.
  `Parse error on line N`) so the user fixes the source. Correctness-first,
  all-or-nothing — no PDF is emitted with a broken or placeholder diagram.
- **Missing backend** → detection reports it; install guidance per above; never a crash.
- **Temp cleanup** runs on both success and failure; the source is never touched.

## Testing & build tooling

**TDD** with fixtures covering: a valid mermaid doc, an invalid mermaid block
(abort + `mmdc` error surfaced), a no-mermaid doc (passthrough), missing-backend
(guidance, no crash), and each backend present (selection order honored).

**Execution steps (carried into the implementation plan):**

1. **Research checkpoint** — the backend comparison and sharing decision are already
   resolved in this design (`references/backends.md` captures the scored table +
   install commands); the plan confirms them against the live environment.
2. **Author with `/skill-creator:skill-creator`** — scaffold and write the skill
   (`SKILL.md`, scripts, references, examples) per this design.
3. **Implement the engine TDD-first** — `render_mermaid.py` (adapted from mermaid-audit), then
   `detect_backends.py`, then `markdown_to_pdf.py`, then the marp path.
4. **Evaluate with `/skill-judge:skill-judge`** — score the skill's design against this
   spec; address findings before the skill is considered done.

## Requirements traceability

| FR | Covered by |
|---|---|
| FR-6.1 primary MD→PDF | Core pipeline |
| FR-6.2 non-destructive temp copy | Core pipeline step 1/3 |
| FR-6.3 output alongside source / user path | Core pipeline step 5 |
| FR-6.4 reuse extract/render, sharing open | Adapted `render_mermaid.py` (names origin in header) |
| FR-6.5 backend auto-selection | `detect_backends.py` + selection rule |
| FR-6.6 detect + secure-install guidance, never auto-install | Install guidance |
| FR-6.7 winner-vs-installed heuristic | Selection rule (prefer capable installed) |
| FR-6.8 marp deck path | Marp hybrid (`marp-cli` + `marp-slide` delegation) |
| FR-6.9 graceful degradation & transparency | Install guidance + error handling |

## Decisions resolved in this design (previously "open")

- **Sharing mechanism (FR-6.4)** → **adapt** the stdlib snippet from `audit_mermaid.py` into a string-based API (not invoke the skill, not a shared package).
- **Backend winner (FR-6.5)** → **Typst + Pandoc** when nothing installed; otherwise
  best installed complete pipeline by quality order.
- **Detection granularity** → **complete-pipeline**, not per-tool (new, from research).
- **Mermaid format** → **PNG `-s 3`** default, SVG only on SVG-friendly backends (new).
- **Marp cooperation (FR-6.8)** → **hybrid**: `marp-cli` backbone + orchestration-layer
  `marp-slide` delegation when available (new).
- **Render-failure policy** → **abort + surface `mmdc` error** (new).
- **Name** → **`markdown-to-pdf`** (source-accurate; replaces working title "doc-to-pdf").
