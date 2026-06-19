---
name: markdown-to-pdf
description: >-
  Convert a Markdown document (with embedded mermaid diagrams) into a PDF — or a
  marp slide deck — in one non-destructive command; every ```mermaid block is
  auto-rendered with mmdc and embedded. Use when the user wants to turn a .md
  file into a PDF or slide deck, "export markdown to pdf", "md to pdf", "render
  mermaid and make a PDF", "build a deck from this markdown", or "export as marp
  deck". Auto-detects the best installed PDF backend (Typst+Pandoc, Pandoc+LaTeX,
  WeasyPrint, headless-Chromium) and never auto-installs. Keywords: markdown to
  pdf, md to pdf, mermaid, marp deck, slide deck, export pdf, pandoc, typst.
---

# markdown-to-pdf

Turn a Markdown document with embedded mermaid diagrams into a PDF (or a marp
deck) in one non-destructive command: every ` ```mermaid ` block is rendered to
an image with `mmdc`, substituted into a temp copy, and that copy is fed to the
best **complete** PDF pipeline installed. The source `.md` is never touched.

## Before you run, decide

- **Doc or deck?** A paginated PDF → primary flow. Slides → the marp deck path.
- **Draft or final?** Iterating → any installed backend is fine. Final → let the
  quality-ranked auto-selection pick (LaTeX > Typst > WeasyPrint > Chromium).
- **Must diagrams stay crisp when zoomed?** Vector (SVG) only survives on
  Typst/Chromium — see the SVG landmine. Otherwise the PNG-at-`-s 3` default is
  correct; don't "fix" it.

Run, then report the printed result line verbatim so the user sees which backend
and diagram format ran.

## Primary flow — document → PDF

```
python3 scripts/markdown_to_pdf.py <source.md>
# -> Wrote /path/source.pdf  (backend: <name>, diagrams: mmdc(<fmt>))
```

Flags (defaults are tuned — reach for these only when the situation demands):
- `-o <path>` — output path (default: alongside the source).
- `--backend <name>` — force `pandoc-latex|typst|weasyprint|chromium`. Only when
  the user names one; otherwise auto-selection is better-informed than a guess.
- `--format png|svg` — override diagram format. Read the SVG landmine before `svg`.

## Decision & troubleshooting

| Situation | Do this |
|---|---|
| Routine doc → PDF | Run the primary flow; report the result line. |
| User wants slides | Use the marp deck path (below). |
| Exit code 3 (no backend) | Show the printed install command as-is; never auto-install. |
| Exit code 2 (mermaid failed) | Show mmdc's error; user fixes the source block at the named line. Nothing was emitted. |
| Diagram looks low-res in the PDF | It's already `-s 3` (high-DPI PNG). For vector sharpness use `--format svg` — but ONLY if the backend is `typst` or `chromium`. |
| SVG render fails under `pandoc-latex` | That backend needs `rsvg-convert` on PATH. Re-run with `--format png` (the default) or install librsvg. |
| Chromium/`md-to-pdf` won't launch (container/CI) | Headless Chrome needs `--no-sandbox`; use an environment that allows it or pick another backend. |

## Marp deck path — slides

**Check your own available-skills list first** (this conditional is resolved by
you, not by any script — see the portability landmine):

- **`marp-slide` IS available** → pre-render diagrams, then delegate:
  ```
  python3 scripts/markdown_to_pdf.py --render-only <source.md>
  # -> writes <source>.rendered.md  (diagrams in a sibling <source>.rendered-assets/)
  ```
  Hand the `.rendered.md` to `marp-slide` for themes/polish/export. The source
  `.md` is untouched and the diagrams are already images.
- **`marp-slide` is NOT available** → self-drive marp-cli:
  ```
  python3 scripts/markdown_to_pdf.py --deck <source.md> [--to pdf|pptx|html]
  ```
  Requires marp-cli (`pnpm add -g @marp-team/marp-cli`). Deck diagrams default to SVG.

## Never

- **NEVER auto-install anything.** Print the exact command (secure managers:
  `uv` / `pnpm` / `cargo`) and let the user run it. Silent installs surprise the
  user and can pull multi-GB toolchains (LaTeX, Chromium).
- **NEVER edit the source `.md`.** All rendering happens on a temp copy; the
  original must stay byte-for-byte intact.
- **NEVER use `--format svg` with `pandoc-latex`** unless `rsvg-convert` is on
  PATH — pandoc's LaTeX path can't embed SVG and fails late. PNG is the safe
  default for exactly this reason.
- **NEVER choose a backend by single-tool presence.** `pdflatex` without `pandoc`
  is a dead pipeline; detection is deliberately pipeline-level. Trust the script's
  selection over your own read of what's installed.
- **NEVER nag for an install when a complete pipeline already works.** All four
  backends are "good enough"; only surface an install when NONE is present.
- **NEVER detect `marp-slide` with a filesystem probe** of `~/.claude/plugins/…`.
  That path-couples to Claude Code and breaks on other harnesses — read your own
  skill list instead.

## References

The script already selects and prints the backend, so a routine conversion needs
nothing else. Both paths require `mmdc` (`pnpm add -g @mermaid-js/mermaid-cli`).

**Load [`references/backends.md`](references/backends.md) ONLY** when the user
asks "which backend is best?" or wants to install one deliberately — it holds the
scored comparison and the full per-tool install matrix. **Do NOT load it for an
ordinary convert or deck run.**
