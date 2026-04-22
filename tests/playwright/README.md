# Playwright tests

Browser-level regression tests that run against the rendered HTML over
a live HTTP server. Not wired into CI - run locally before merging
risky changes to `scripts/render_html.py`, `static/render.js`, or
`static/dante.css`.

## Topology

Two long-running services live on the macOS host (not in the dev
container):

```
┌─────────────┐        ┌──────────┐        ┌──────────────────┐
│ dev sandbox │──ws──▶ │ macOS    │ ──ws──▶│ docker: pw server │
│ node client │        │  host    │        │ + headless chrome │
└─────────────┘        └──────────┘        └──────────────────┘
       │                     ▲
       └──http-fetch─────────┘ (pw browser → host:8001 → python http.server)
```

Both hops cross `host.docker.internal`.

### 1. HTTP server (macOS host)
```
cd /Users/quetzal/repos/dante && python3 -m http.server 8001
```

### 2. Playwright server (macOS host, docker)
```
docker run -p 3000:3000 --rm --init -it --workdir /home/pwuser --user pwuser \
  mcr.microsoft.com/playwright:v1.58.2-noble \
  /bin/sh -c "npx -y playwright@1.58.2 run-server --port 3000 --host 0.0.0.0"
```

Dies between runs sometimes — restart when `curl host.docker.internal:3000/`
gives `ECONNREFUSED`.

## Running

```
cd tests/playwright
npm install                    # one-time, installs playwright@1.58.2
npm run smoke                  # responsive.js: 4 viewports x 5 pages + overflow post-pass
npm run dedup-purg19           # payload dedup regression
npm run all                    # smoke + dedup
```

Screenshots land in `tests/playwright/shots/` (gitignored).

### Diagnose overflow

When `smoke` reports `OVERFLOW`, drill into the offending page + viewport:
```
PAGE=/html/inf_01.html VIEWPORT=360 node diagnose.js
```
Prints every element whose `getBoundingClientRect().right` exceeds the
viewport.

## Gotchas

- **Client/server version lockstep**: `playwright@1.58.2` both sides.
  Mismatch yields WS 428 "Precondition Required".
- **SVGs with `viewBox` and no `width=`** render at intrinsic size and
  ignore CSS `left/right`. Use `width: calc(100% - ...)` or `width="100%"`.
- **`body.scrollWidth > window.innerWidth`** is the reliable overflow
  signal. Don't trust screenshot PNG dimensions alone — they can be
  slightly off from scrollbar.
- Playwright's docker container can't reach this sandbox's ports, only
  the host's. Hence the HTTP server must be on the host (not in any
  container).

## Tests

| Script                    | What it checks                                                 |
|---------------------------|----------------------------------------------------------------|
| `responsive.js`           | 4 viewports x 5 pages render; no horizontal overflow           |
| `dedup-purg19.js`         | Purg. XIX: shared Latin intermediary renders once, transmits to both primaries |
| `order-par04.js`          | Par. IV: Dante cards in col 1 are sorted by first verse number |
| `mobile-arrow-styles.js`  | Mobile arrows get per-type color + stroke-width / dasharray    |
| `mobile-type-label.js`    | Mobile expanded-card "type" label colored per connection type  |
| `diagnose.js`             | Helper: print overflow offenders for a given page/viewport     |
