# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dante Intertextual Analysis ("Дантешопедія") — a literary scholarship tool that systematically catalogs intertextual connections between Dante's *Divina Commedia* and pre-Dante literature (antiquity through early XIV century). The output is 100 self-contained HTML canto pages + 3 cantica frontispicia + index hub, styled as a medieval manuscript (folio layout, rubric bands, UnifrakturMaguntia blackletter titles, card-based intertextual graph).

**Language:** All text content is in Ukrainian. Node labels (`dante_sub`, `source_sub`) must be Ukrainian paraphrases, never Italian/Latin quotes.

## Architecture

The project follows a **three-pass pipeline** per canto:

1. **Pass 1 (Generation):** AI agent identifies intertextual connections, outputs structured JSON
2. **Pass 2 (Verification):** Separate AI call fact-checks each connection (PASS/FIX/REJECT verdicts)
3. **Pass 3 (Rendering):** Verified JSON → self-contained HTML with embedded canto data and shared `static/render.js` renderer

Each canto is processed independently. 100 total cantos: Inferno (34) + Purgatorio (33) + Paradiso (33).

### Key Files

- `docs/dante_agent_spec_v4.md` — Complete specification (primary source of truth); must stay in sync with CLAUDE.md constants and rules
- `docs/inf_xxvi_tree_v4.html` — Reference HTML template (fully annotated)
- `static/dante.css` — Shared CSS: folio layout, three theme variants, connection type styles, side panel
- `static/render.js` — Client-side renderer: reads `window.CANTO`, builds 3-column card grid + SVG bezier arrows, tooltips, side-panel navigator
- `json/` — Source JSON data files (e.g., `json/inf_01.json`)
- `html/` — Generated HTML pages (gitignored, built by `render_html.py`)
- `dist/` — Flat deployment build for Cloudflare (gitignored, built by `render_html.py --dist`)
- `scripts/render_html.py` — Pass 3 automation: JSON -> HTML via Jinja2 templates
- `scripts/stats.py` — Aggregate analytics across all canto JSON files
- `scripts/validate_json.py` — Schema + semantic validation with `--check-sync` flag
- `templates/canto.html.j2` — Per-canto Jinja2 template (folio + medallion + colophon)
- `templates/index.html.j2` — Hub page with 100-canto grid + progress bar
- `templates/frontispicia.html.j2` — Per-cantica title page (switches central device via `{% if cantica %}`)
- `Makefile` — Common targets: validate, render, index, frontispicia, dist, stats, serve, watch
- Example outputs: `docs/inf_20.html`, `docs/purg_01.html`, `docs/par_10.html` (reference)

### Data Flow

```
Canto text → Pass 1 (JSON) → Pass 2 (verified JSON) → Pass 3 (render_html.py)
                                                          ↓
                                    html/{prefix}_{nn}.html  (local dev)
                                    dist/{prefix}_{nn}.html  (deployment)
```

## Tech Stack

- **Vanilla JS renderer** (`static/render.js`) — 3-column card grid + SVG bezier arrows; no charting library
- **CSS Custom Properties** — three visual themes (Inferno, Purgatorio, Paradiso) swapped via `body.theme-{slug}`
- **Fonts:** UnifrakturMaguntia (blackletter titles), Cormorant Garamond (incipit/italic), EB Garamond (body) — Google Fonts CDN
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

Applied server-side via `<body class="theme-{slug}">` where `slug` is one of `inferno`, `purgatorio`, `paradiso`. Theme is fixed per page — no client-side toggle on canto pages (theme toggle survives only on frontispicia chrome for preview).

| Cantica | CSS Class | Background | Character |
|---------|-----------|------------|-----------|
| Inferno | `.theme-inferno` | `#2a1a10` dark paper | Scorched red-gold |
| Purgatorio | `.theme-purgatorio` | `#f3e4c0` vellum | Warm ochre, dawn blue |
| Paradiso | `.theme-paradiso` | `#0f2048` deep azure | Gold-on-azure, starfield |

## JSON Schema (per canto)

Each connection object contains: `id`, `dante_ref`, `dante_sub`, `source_ref`, `source_sub`, `source_author`, `type`, `confidence` (HIGH/MEDIUM only, never LOW), `desc_dante`, `desc_source`, `chain` (array or null). See `json/inf_01.json` for a live example and spec §4.1 for the full schema.

Optional per-canto metadata (used by the folio header/colophon): `incipit`, `foliation`, `title_ua`, `subtitle_ua`, `rubric_lat`, `summary_ua`, `verses`. Missing fields render with graceful fallbacks (foliation derived from canto_num; subtitle falls back to the canto label; empty rubric/summary hide their sections).

Formal schema: `json/canto.schema.json` (JSON Schema Draft-07). Validation:

```
uv run scripts/validate_json.py              # all json/*.json
uv run scripts/validate_json.py inf_26.json  # single file
```

JSON must pass validation before proceeding to Pass 3 (HTML rendering).

Validator checks: schema structure, semantic consistency, AND Ukrainian-only text in `dante_sub`, `source_sub`, `chain[].sub`, plus optional `title_ua`, `subtitle_ua`, `summary_ua` (no Latin-script words).

## HTML Page Structure

Each canto page is a folio with:
- **Folio toolbar:** hamburger menu (opens 100-canto side panel) + prev/next arrows + link to per-cantica frontispicia
- **Header:** kicker ("Divina Commedia · Cantica Prima"), cantica name (blackletter), canto Roman, incipit (italic), subtitle (Ukrainian)
- **Medallion:** rubric band + 3-column card grid — **Dante passages (col 1)** → **Intermediaries Dante read (col 2)** → **Primary sources via intermediaries (col 3)** — connected by SVG bezier arrows colored by type
- **Colophon:** argumentum (summary), nota bene (auto-generated connection counts), type legend

Data injection: `render_html.py` bakes `window.CANTO = {...}` into each page. `static/render.js` reads it, runs `fromJson()` tier-splitting in JS mirror of Python, then builds the grid.

Server-side transform: `scripts/render_html.py::from_json()` converts raw connections into tier-split records (`tier: 'direct' | 'primary'`, linked via `transmits: primaryId`). Mirrors the spec's chain semantics.

## JSON / HTML Sync

HTML is auto-generated from JSON via `uv run scripts/render_html.py`. When editing connections, update `json/{canto}.json`, then validate, then re-render:

```
uv run scripts/validate_json.py {canto}.json   # must pass before rendering
uv run scripts/render_html.py {canto}           # regenerate HTML
```

Common commands:
- `make validate` — validate all JSON files
- `make render` — regenerate html/ from JSON
- `make index` — rebuild index hub page only
- `make frontispicia` — rebuild three per-cantica title pages
- `make dist` — build flat site (html + index + frontispicia + static/) into dist/ for deployment
- `make stats` — show aggregate analytics
- `make serve` — start local HTTP server on port 8000
- `make all` — validate + render + index + frontispicia + check-sync

## Critical Constraints

- **No LOW confidence** connections in output
- **No self-allusion** (inter-canto references or other Dante texts)
- **No theology/philosophy/chronicles/science** — secular literature + Bible only
- **Transmission chains required** for authors Dante accessed indirectly (Homer, Plato, Aristotle, Bible, Arabic philosophers) — field `chain` must be populated
- **Author palette is fixed** for major authors (Dante=gold, Virgil=purple, Ovid=pink, Lucan=cyan, Statius=blue, Homer=orange, Bible=red); new authors pick non-conflicting hues
- Each connection has exactly **one type** and **two descriptions** (`desc_dante` + `desc_source`)
- Academic indexing standards per source type (see spec §3)
