// Responsive smoke test: render four viewports across five representative
// pages, save screenshots. Overflow detection is delegated to a post-pass
// script that inspects PNG dimensions; see README.
//
// Requires a remote Playwright server (user's docker on host) and a local
// HTTP server serving this repo over the network (again on host, because
// the docker Playwright container can reach only the host).

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const WS_ENDPOINT = process.env.WS_ENDPOINT || 'ws://host.docker.internal:3000/';
const BASE = process.env.BASE_URL || 'http://host.docker.internal:8001';
const OUT = process.env.OUT_DIR || path.join(__dirname, 'shots');

const viewports = [
  { name: 'desktop-1280', w: 1280, h: 800 },
  { name: 'tablet-768',   w: 768,  h: 1024 },
  { name: 'phone-480',    w: 480,  h: 800 },
  { name: 'small-360',    w: 360,  h: 640 },
];

const pages = [
  { label: 'landing',   url: '/html/index.html' },
  { label: 'inf26',     url: '/html/inf_26.html' },
  { label: 'purg21',    url: '/html/purg_21.html' },
  { label: 'par33',     url: '/html/par_33.html' },
  { label: 'frontPurg', url: '/html/frontispicia_purgatorio.html' },
];

function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  console.log(`Connecting to ${WS_ENDPOINT} ...`);
  const browser = await chromium.connect(WS_ENDPOINT);
  console.log('Connected. Running viewport matrix:');

  for (const vp of viewports) {
    console.log(`\n--- ${vp.name}  ${vp.w}x${vp.h} ---`);
    const context = await browser.newContext({
      viewport: { width: vp.w, height: vp.h },
      deviceScaleFactor: 1,
    });
    for (const p of pages) {
      const page = await context.newPage();
      const url = BASE + p.url;
      try {
        await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
        await wait(400);
        const fname = `${vp.name}__${p.label}.png`;
        await page.screenshot({ path: path.join(OUT, fname), fullPage: true });
        console.log(`  ok   ${p.label.padEnd(12)}  ->  ${fname}`);
      } catch (e) {
        console.log(`  FAIL ${p.label.padEnd(12)}  ${e.message.split('\n')[0]}`);
        process.exitCode = 1;
      } finally {
        await page.close();
      }
    }
    await context.close();
  }
  await browser.close();
  console.log(`\nAll screenshots saved to ${OUT}`);

  // Post-pass: flag any screenshot whose width exceeds its declared viewport
  // (accounting for a 5px scrollbar slack). PNG header parse inline.
  const { readdirSync, readFileSync } = fs;
  let overflow = 0;
  for (const f of readdirSync(OUT).sort()) {
    if (!f.endsWith('.png')) continue;
    const buf = readFileSync(path.join(OUT, f));
    // PNG IHDR: bytes 16..24 = width(4), height(4) big-endian
    const w = buf.readUInt32BE(16);
    const h = buf.readUInt32BE(20);
    const expected = parseInt(f.split('__')[0].split('-').pop(), 10);
    const over = w > expected + 5;
    if (over) {
      overflow++;
      console.log(`  OVERFLOW  ${f.padEnd(48)} ${w}x${h} (expected ≤ ${expected + 5})`);
    }
  }
  if (overflow > 0) {
    console.error(`\n${overflow} screenshot(s) show horizontal overflow`);
    process.exitCode = 1;
  } else {
    console.log(`\noverflow failures: 0`);
  }
})().catch(e => {
  console.error('FATAL:', e.message);
  process.exit(1);
});
