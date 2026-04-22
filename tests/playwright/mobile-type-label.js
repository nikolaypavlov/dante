// Verify the expanded "connection type" label under the author (card-details
// .type) is colored the same as the connection's auth/border on mobile.
// Was hardcoded to var(--accent) (theme's default), so all expanded cards
// showed the same accent color regardless of their actual INVERSION /
// STRUCTURE / ALLUSION / ... type.

const { chromium } = require('playwright');

const WS_ENDPOINT = process.env.WS_ENDPOINT || 'ws://host.docker.internal:3000/';
const BASE = process.env.BASE_URL || 'http://host.docker.internal:8001';
const URL = BASE + '/html/purg_19.html';

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; }
  else console.log('  ok  ' + msg);
}

const EXPECTED_COLOR = {
  ALLUSION:  'rgb(212, 167, 44)',
  STRUCTURE: 'rgb(62, 122, 58)',
  THEMATIC:  'rgb(126, 74, 158)',
  INVERSION: 'rgb(196, 58, 20)',
  ONOMASTIC: 'rgb(58, 107, 168)',
};

(async () => {
  console.log('Connecting to ' + WS_ENDPOINT);
  const browser = await chromium.connect(WS_ENDPOINT);
  const context = await browser.newContext({ viewport: { width: 480, height: 800 } });
  const page = await context.newPage();
  console.log('Loading ' + URL + ' @ 480x800');
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(500);

  // Force-expand every card so card-details are visible.
  await page.evaluate(() => {
    document.querySelectorAll('.medallion.narrow .card').forEach(c => c.classList.add('expanded'));
  });
  await page.waitForTimeout(150);

  const rows = await page.evaluate(() => {
    const types = ['ALLUSION', 'STRUCTURE', 'THEMATIC', 'INVERSION', 'ONOMASTIC'];
    return Array.from(document.querySelectorAll('.medallion.narrow .card')).map(card => {
      const type = types.find(t => card.classList.contains(t)) || null;
      const typeRow = card.querySelector('.card-details .type');
      if (!type || !typeRow) return null;
      return { type, color: getComputedStyle(typeRow).color };
    }).filter(Boolean);
  });

  assert(rows.length > 0, `at least one card type-label rendered (got ${rows.length})`);

  let seen = new Set();
  for (const r of rows) {
    seen.add(r.type);
    assert(
      r.color === EXPECTED_COLOR[r.type],
      `${r.type} label color is ${EXPECTED_COLOR[r.type]} (got ${r.color})`
    );
  }
  // Purg. XIX after dedup exercises INVERSION, STRUCTURE, ALLUSION — sanity.
  assert(seen.has('INVERSION'), 'INVERSION observed on Purg. XIX');
  assert(seen.has('STRUCTURE'), 'STRUCTURE observed on Purg. XIX');
  assert(seen.has('ALLUSION'),  'ALLUSION observed on Purg. XIX');

  await context.close();
  await browser.close();
  if (process.exitCode) console.error('\nFAILED'); else console.log('\nPASSED');
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
