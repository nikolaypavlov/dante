# Dante Intertextual Analysis

Literary scholarship tool that systematically catalogs intertextual connections between Dante's *Divina Commedia* and pre-Dante literature (antiquity through early XIV century). The output is 100 per-canto HTML pages + 3 per-cantica frontispicia + 1 index hub, styled as a medieval manuscript (folio layout, rubric bands, blackletter titles, card-based intertextual graph with bezier arrows).

All text content is in Ukrainian.

## Architecture

Three-pass pipeline per canto:

1. **Pass 1 (Generation)** - AI agent identifies intertextual connections, outputs structured JSON
2. **Pass 2 (Verification)** - Separate AI call fact-checks each connection (PASS/FIX/REJECT verdicts)
3. **Pass 3 (Rendering)** - Verified JSON to self-contained HTML with embedded `window.CANTO` payload, rendered client-side by `static/render.js`

```
Canto text --> Pass 1 (JSON) --> Pass 2 (verified JSON) --> Pass 3 (render_html.py)
                                                              |
                                        html/{prefix}_{nn}.html  (local dev)
                                        dist/{prefix}_{nn}.html  (deployment)
```

100 cantos total: Inferno (34) + Purgatorio (33) + Paradiso (33).

## Five Connection Types

| Type | Code | Color | Line Style |
|------|------|-------|------------|
| Direct allusion/quote | `ALLUSION` | gold | solid |
| Structural borrowing | `STRUCTURE` | green | thick solid |
| Thematic parallel | `THEMATIC` | purple | dashed |
| Deliberate inversion | `INVERSION` | red | solid |
| Name/character reference | `ONOMASTIC` | blue | dotted |

## Tech Stack

- **Vanilla JS renderer** (`static/render.js`) - 3-column card grid + SVG bezier arrows; no charting library
- **Jinja2** - HTML templating (canto, index, frontispicia)
- **CSS Custom Properties** - three visual themes (Inferno, Purgatorio, Paradiso) swapped via `body.theme-{slug}`
- **Fonts** - UnifrakturMaguntia (blackletter titles), Cormorant Garamond (incipit), EB Garamond (body)
- **Deployment** - Cloudflare Workers (auto-deploy from GitHub on push to main)

## Quick Start

```bash
# Install dependencies
uv sync

# Validate all JSON files
make validate

# Render HTML from JSON
make render

# Build flat site for deployment
make dist

# Start local server
make serve

# Watch for changes and re-render
make watch

# Show aggregate statistics
make stats
```

## Project Structure

```
json/                 Canto JSON data files (e.g. inf_01.json)
json/canto.schema.json  JSON Schema for validation
html/                 Generated HTML pages (gitignored)
dist/                 Flat deployment build (gitignored)
templates/
  canto.html.j2       Per-canto folio template
  index.html.j2       100-canto hub with progress bar
  frontispicia.html.j2  Per-cantica title page (switches device via cantica variable)
static/
  dante.css           Shared CSS (folio, themes, side panel, frontispicia)
  render.js           Client-side renderer (cards + bezier arrows + tooltips + nav)
scripts/
  render_html.py      Pass 3: JSON to HTML renderer
  validate_json.py    Schema + semantic validation
  stats.py            Aggregate analytics
docs/
  dante_agent_spec_v4.md  Complete specification (source of truth)
  inf_xxvi_tree_v4.html   Reference HTML template (fully annotated)
  inf_20.html             Example output (Inferno)
  purg_01.html            Example output (Purgatorio)
  par_10.html             Example output (Paradiso)
```

## Author

Mykola Pavlov <me@nikolaypavlov.com>
