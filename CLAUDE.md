# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dante Intertextual Analysis ("Дантешопедія") — a literary scholarship tool that systematically catalogs intertextual connections between Dante's *Divina Commedia* and pre-Dante literature (antiquity through early XIV century). The output is 100 self-contained HTML files (one per canto) with interactive d3.js force-directed tree visualizations.

**Language:** All text content is in Ukrainian. Node labels (`dante_sub`, `source_sub`) must be Ukrainian paraphrases, never Italian/Latin quotes.

## Architecture

The project follows a **three-pass pipeline** per canto:

1. **Pass 1 (Generation):** AI agent identifies intertextual connections, outputs structured JSON
2. **Pass 2 (Verification):** Separate AI call fact-checks each connection (PASS/FIX/REJECT verdicts)
3. **Pass 3 (Rendering):** Verified JSON → self-contained HTML with embedded d3.js visualization

Each canto is processed independently. 100 total cantos: Inferno (34) + Purgatorio (33) + Paradiso (33).

### Key Files

- `docs/dante_agent_spec_v4.md` — Complete specification (primary source of truth); must stay in sync with CLAUDE.md constants and rules
- `docs/inf_xxvi_tree_v4.html` — Reference HTML template (fully annotated)
- `dante-theme.css` — Shared CSS with three theme variants via custom properties
- `json/` — Generated JSON data files (e.g., `json/inf_01.json`)
- `html/` — Generated HTML visualizations (gitignored, built by `render_html.py`)
- `dist/` — Flat deployment build for Cloudflare (gitignored, built by `render_html.py --dist`)
- `scripts/render_html.py` — Pass 3 automation: JSON -> HTML via Jinja2 templates
- `scripts/stats.py` — Aggregate analytics across all canto JSON files
- `scripts/validate_json.py` — Schema + semantic validation with `--check-sync` flag
- `templates/canto.html.j2` — Jinja2 template for canto HTML pages
- `templates/index.html.j2` — Jinja2 template for index/navigation page
- `Makefile` — Common targets: validate, render, dist, stats, serve, watch
- Example outputs: `docs/inf_20.html`, `docs/purg_01.html`, `docs/par_10.html` (reference)

### Data Flow

```
Canto text → Pass 1 (JSON) → Pass 2 (verified JSON) → Pass 3 (render_html.py)
                                                          ↓
                                    html/{prefix}_{nn}.html  (local dev)
                                    dist/{prefix}_{nn}.html  (deployment)
```

## Tech Stack

- **D3.js v7.8.5** — force-directed horizontal tree graphs (CDN-loaded)
- **CSS Custom Properties** — three visual themes (Inferno default, Purgatorio, Paradiso)
- **Fonts:** Cormorant Garamond (body), JetBrains Mono (labels) — Google Fonts CDN
- **Jinja2** — HTML templating for Pass 3 rendering
- **Deployment:** Cloudflare Workers (auto-deploy from GitHub on push to main)
- **CI:** GitHub Actions validates JSON and renders HTML on push/PR

## Five Connection Types

| Type | Code | Color | Line Style |
|------|------|-------|------------|
| Direct allusion/quote | `ALLUSION` | `#d4a853` gold | solid |
| Structural borrowing | `STRUCTURE` | `#7ea88e` green | thick solid |
| Thematic parallel | `THEMATIC` | `#8a7eb8` purple | dashed |
| Deliberate inversion | `INVERSION` | `#c45c5c` red | solid |
| Name/character reference | `ONOMASTIC` | `#5c8ab8` blue | dotted |

## Three Visual Themes

| Cantica | CSS Class | Background | Character |
|---------|-----------|------------|-----------|
| Inferno | *(default)* | `#0f0e0d` dark | Gold on black |
| Purgatorio | `.theme-purgatorio` | `#0a1a0f` dark green | Green accents only (text stays warm beige) |
| Paradiso | `.theme-paradiso` | `#f4f1ec` light cream | Light, luminous |

**Purgatorio rule:** Green color only in backgrounds, borders, and UI accents — never in text or node labels.

## JSON Schema (per canto)

Each connection object contains: `id`, `dante_ref`, `dante_sub`, `source_ref`, `source_sub`, `source_author`, `type`, `confidence` (HIGH/MEDIUM only, never LOW), `desc_dante`, `desc_source`, `chain` (array or null). See `json/inf_01.json` for a live example and spec §4.1 for the full schema.

Formal schema: `json/canto.schema.json` (JSON Schema Draft-07). Validation:

```
uv run scripts/validate_json.py              # all json/*.json
uv run scripts/validate_json.py inf_26.json  # single file
```

JSON must pass validation before proceeding to Pass 3 (HTML rendering).

Validator checks: schema structure, semantic consistency, AND Ukrainian-only text in `dante_sub`, `source_sub`, `chain[].sub` (no Latin-script words).

## HTML Visualization Structure

Three equal-width columns: **Dante (col 0, dark)** → **Intermediaries (col 1, light)** → **Primary Sources (col 2, dark)**. Node positioning uses Y-averaging from parent connections. Tooltip shows `desc_dante` when hovering Dante nodes, `desc_source` when hovering source nodes. Navigation: hamburger side panel (100 cantos) + ← → arrows.

Key d3 constants: `nodeW=230, nodeH=60, gapY=11, gapX=130, padLeft=70, padTop=20`.

SVG text is auto-truncated with ellipsis at `nodeW-12` px via `trunc()` in the template.

## JSON / HTML Sync

HTML is auto-generated from JSON via `uv run scripts/render_html.py`. When editing connections, update `json/{canto}.json`, then validate, then re-render:

```
uv run scripts/validate_json.py {canto}.json   # must pass before rendering
uv run scripts/render_html.py {canto}           # regenerate HTML
```

Common commands:
- `make validate` — validate all JSON files
- `make render` — regenerate html/ from JSON
- `make dist` — build flat site into dist/ for deployment
- `make stats` — show aggregate analytics
- `make serve` — start local HTTP server on port 8000

## Critical Constraints

- **No LOW confidence** connections in output
- **No self-allusion** (inter-canto references or other Dante texts)
- **No theology/philosophy/chronicles/science** — secular literature + Bible only
- **Transmission chains required** for authors Dante accessed indirectly (Homer, Plato, Aristotle, Bible, Arabic philosophers) — field `chain` must be populated
- **Author palette is fixed** for major authors (Dante=gold, Virgil=purple, Ovid=pink, Lucan=cyan, Statius=blue, Homer=orange, Bible=red); new authors pick non-conflicting hues
- Each connection has exactly **one type** and **two descriptions** (`desc_dante` + `desc_source`)
- Academic indexing standards per source type (see spec §3)
