// Verify mobile vertical arrows get per-type colors and stroke variants.
//
// Regression: `.medallion.narrow .arrow-v { color: var(--ink-dim) }` had
// higher specificity than `.arrow-v.TYPE { color: ... }`, so every arrow
// rendered as dim ink regardless of type, and no stroke-width /
// stroke-dasharray was applied for STRUCTURE / THEMATIC / ONOMASTIC /
// indirect cases.
//
// Uses purg_19.html which after dedup has connection types INVERSION
// (direct + indirect), STRUCTURE, and ALLUSION on mobile.

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

  const arrows = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('.arrow-v')).map(svg => {
      const cs = getComputedStyle(svg);
      const path = svg.querySelector('path');
      const pcs = path ? getComputedStyle(path) : null;
      return {
        cls: svg.getAttribute('class'),
        color: cs.color,
        opacity: cs.opacity,
        pathStrokeWidth: pcs && pcs.strokeWidth,
        pathStrokeDasharray: pcs && pcs.strokeDasharray,
      };
    });
  });

  assert(arrows.length > 0, `at least one .arrow-v rendered on mobile (got ${arrows.length})`);

  // Group sanity — every arrow has a type class.
  const types = Object.keys(EXPECTED_COLOR);
  for (const a of arrows) {
    const cls = (a.cls || '').split(/\s+/);
    const t = types.find(x => cls.includes(x));
    assert(!!t, `arrow "${a.cls}" declares a known type class`);
    if (!t) continue;

    assert(
      a.color === EXPECTED_COLOR[t],
      `${t} arrow color is ${EXPECTED_COLOR[t]} (got ${a.color})`
    );

    if (t === 'STRUCTURE' && !cls.includes('indirect')) {
      assert(
        a.pathStrokeWidth === '2.8px',
        `STRUCTURE path stroke-width is 2.8 (got ${a.pathStrokeWidth})`
      );
    }

    if (cls.includes('indirect')) {
      assert(
        parseFloat(a.opacity) < 0.9,
        `indirect arrow opacity < 0.9 (got ${a.opacity})`
      );
      assert(
        a.pathStrokeDasharray !== 'none',
        `indirect arrow has stroke-dasharray (got ${a.pathStrokeDasharray})`
      );
    }
  }

  await context.close();
  await browser.close();
  if (process.exitCode) console.error('\nFAILED'); else console.log('\nPASSED');
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
