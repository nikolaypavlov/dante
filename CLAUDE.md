# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dante Intertextual Analysis ("Дантешопедія") — a literary scholarship tool that systematically catalogs intertextual connections between Dante's *Divina Commedia* and pre-Dante literature (antiquity through early XIV century). The output is 100 self-contained HTML files (one per canto) with interactive d3.js force-directed tree visualizations.

**Language:** All text content is in Ukrainian with Latin/English/Italian scholarly terminology.

## Architecture

The project follows a **three-pass pipeline** per canto:

1. **Pass 1 (Generation):** AI agent identifies intertextual connections, outputs structured JSON
2. **Pass 2 (Verification):** Separate AI call fact-checks each connection (PASS/FIX/REJECT verdicts)
3. **Pass 3 (Rendering):** Verified JSON → self-contained HTML with embedded d3.js visualization

Each canto is processed independently. 100 total cantos: Inferno (34) + Purgatorio (33) + Paradiso (33).

### Key Files

- `dante_agent_spec_v4.md` — Complete specification (primary source of truth for all rules, prompts, and constraints)
- `inf_xxvi_tree_v4.html` — Reference HTML template (fully annotated)
- `dante-theme.css` — Shared CSS with three theme variants via custom properties
- `json/` — Generated JSON data files (e.g., `json/inf_01.json`)
- `html/` — Generated HTML visualizations (e.g., `html/inf_01.html`); CSS path: `../dante-theme.css`
- Example outputs: `inf_20.html`, `purg_01.html`, `par_10.html` (reference, root level)

### Data Flow

```
Canto text → Pass 1 (JSON) → Pass 2 (verified JSON) → Pass 3 (HTML)
                                                          ↓
                                          html/{prefix}_{nn}.html
                                              (inf_01..inf_34,
                                               purg_01..purg_33,
                                               par_01..par_33)
```

## Tech Stack

- **D3.js v7.8.5** — force-directed horizontal tree graphs (CDN-loaded)
- **CSS Custom Properties** — three visual themes (Inferno default, Purgatorio, Paradiso)
- **Fonts:** Cormorant Garamond (body), JetBrains Mono (labels) — Google Fonts CDN
- No backend, no build toolchain — pure static site

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

## HTML Visualization Structure

Three equal-width columns: **Dante (col 0, dark)** → **Intermediaries (col 1, light)** → **Primary Sources (col 2, dark)**. Node positioning uses Y-averaging from parent connections. Tooltip shows `desc_dante` when hovering Dante nodes, `desc_source` when hovering source nodes. Navigation: hamburger side panel (100 cantos) + ← → arrows.

Key d3 constants: `nodeW=164, nodeH=46, gapY=8, gapX=140, padLeft=70, padTop=20`.

## JSON / HTML Sync

JSON and HTML are not auto-generated from each other. When editing connections, always update both `json/{canto}.json` and `html/{canto}.html` (NODES_RAW + LINKS_DATA). Run `uv run scripts/validate_json.py` after JSON changes.

## Critical Constraints

- **No LOW confidence** connections in output
- **No self-allusion** (inter-canto references or other Dante texts)
- **No theology/philosophy/chronicles/science** — secular literature + Bible only
- **Transmission chains required** for authors Dante accessed indirectly (Homer, Plato, Aristotle, Bible, Arabic philosophers) — field `chain` must be populated
- **Author palette is fixed** for major authors (Dante=gold, Virgil=purple, Ovid=pink, Lucan=cyan, Statius=blue, Homer=orange, Bible=red); new authors pick non-conflicting hues
- Each connection has exactly **one type** and **two descriptions** (`desc_dante` + `desc_source`)
- Academic indexing standards per source type (see spec §3)
