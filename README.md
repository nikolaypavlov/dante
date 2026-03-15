# Dante Intertextual Analysis

Literary scholarship tool that systematically catalogs intertextual connections between Dante's *Divina Commedia* and pre-Dante literature (antiquity through early XIV century). The output is 100 self-contained HTML files (one per canto) with interactive d3.js force-directed tree visualizations.

All text content is in Ukrainian.

## Architecture

Three-pass pipeline per canto:

1. **Pass 1 (Generation)** - AI agent identifies intertextual connections, outputs structured JSON
2. **Pass 2 (Verification)** - Separate AI call fact-checks each connection (PASS/FIX/REJECT verdicts)
3. **Pass 3 (Rendering)** - Verified JSON to self-contained HTML with embedded d3.js visualization

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

- **D3.js v7.8.5** - force-directed horizontal tree graphs
- **Jinja2** - HTML templating
- **CSS Custom Properties** - three visual themes (Inferno, Purgatorio, Paradiso)
- **Fonts** - Cormorant Garamond (body), JetBrains Mono (labels)
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
html/                 Generated HTML visualizations (gitignored)
dist/                 Flat deployment build (gitignored)
templates/            Jinja2 templates for HTML generation
scripts/
  render_html.py      Pass 3: JSON to HTML renderer
  validate_json.py    Schema + semantic validation
  stats.py            Aggregate analytics
dante-theme.css       Shared CSS with three theme variants
dante_agent_spec_v4.md  Complete specification (source of truth)
```

## Author

Mykola Pavlov <me@nikolaypavlov.com>
