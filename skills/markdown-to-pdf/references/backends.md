# PDF Backend Comparison

Criteria: install ease, agent-friendliness, output quality, image/diagram handling — 1–5 each.

| Backend | Install ease | Agent-friendly | Output quality | Image/diagram | Total /20 | Notes |
|---|---|---|---|---|---|---|
| **Typst + Pandoc** | 5 | 5 | 4 | 4 | **18** | Winner: small self-contained binaries, fast, deterministic, native SVG+PNG |
| Pandoc + LaTeX (tectonic/xelatex) | 2 | 3 | 5 | 3 | 13 | Best typography; heavy; SVG needs `rsvg-convert`; noisy errors |
| WeasyPrint | 4 | 3 | 3 | 3 | 13 | Lightweight Python; needs Pango system lib; patchy SVG; 2-step |
| Headless-Chromium / md-to-pdf | 2 | 2 | 4 | 5 | 13 | Best SVG fidelity; huge Chromium; container-launch fragility |

## Selection rule

Use the best **complete pipeline** already installed, by quality order:
**Pandoc+LaTeX > Typst > WeasyPrint > Chromium**.

If no complete pipeline is installed, recommend the researched winner:
**Typst + Pandoc** — smallest footprint, most agent-friendly, native SVG.

## Install commands (exact, secure-manager only)

**Typst + Pandoc (recommended when nothing installed):**
```
cargo install --locked typst-cli
# download pandoc release binary from https://github.com/jgm/pandoc/releases
```

**Pandoc + LaTeX (tectonic):**
```
cargo install tectonic
# download pandoc release binary from https://github.com/jgm/pandoc/releases
```

**Pandoc + LaTeX (xelatex/pdflatex):**
```
# install TeX Live or MacTeX; download pandoc from https://github.com/jgm/pandoc/releases
```

**WeasyPrint:**
```
uv tool install weasyprint   # also needs the Pango system library (libpango-1.0)
# download pandoc release binary from https://github.com/jgm/pandoc/releases
```

**Headless-Chromium / md-to-pdf:**
```
pnpm add -g md-to-pdf
```

**marp-cli (deck path only):**
```
pnpm add -g @marp-team/marp-cli
```

**mmdc (mermaid renderer — required by every path):**
```
pnpm add -g @mermaid-js/mermaid-cli
```
