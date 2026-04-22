// Verify Dante column (col 1) renders passages in terzin order regardless
// of JSON connection order. Par. IV is the canonical regression case:
// its JSON lists connections as [13-15, 103-105, 22-63, 1-9, 103-108], and
// render.js must sort by first verse number so cards appear 1, 13, 22, 103, 103.

const { chromium } = require('playwright');

const WS_ENDPOINT = process.env.WS_ENDPOINT || 'ws://host.docker.internal:3000/';
const BASE = process.env.BASE_URL || 'http://host.docker.internal:8001';
const URL = BASE + '/html/par_04.html';

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; }
  else console.log('  ok  ' + msg);
}

function firstVerse(ref) {
  const m = String(ref || '').match(/\d+/);
  return m ? parseInt(m[0], 10) : 0;
}

(async () => {
  console.log('Connecting to ' + WS_ENDPOINT);
  const browser = await chromium.connect(WS_ENDPOINT);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  console.log('Loading ' + URL);
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(500);

  const refs = await page.evaluate(() =>
    Array.from(document.querySelectorAll('.col.dante .card .ref')).map(n => n.textContent)
  );

  console.log('Dante card order:', refs);
  assert(refs.length === 5, `5 Dante cards rendered (got ${refs.length})`);

  const nums = refs.map(firstVerse);
  const sorted = [...nums].sort((a, b) => a - b);
  assert(
    JSON.stringify(nums) === JSON.stringify(sorted),
    `cards are in non-decreasing verse order (got [${nums.join(', ')}])`
  );
  assert(
    JSON.stringify(nums) === JSON.stringify([1, 13, 22, 103, 103]),
    `exact expected order [1, 13, 22, 103, 103] (got [${nums.join(', ')}])`
  );

  await context.close();
  await browser.close();
  if (process.exitCode) console.error('\nFAILED'); else console.log('\nPASSED');
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
