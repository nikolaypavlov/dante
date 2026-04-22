// Verify intermediary dedup on Purg. XIX.
//
// Two JSON connections (purg_xix_01, purg_xix_01b) cite the same Latin
// intermediary (Aen. V, 864-868, Вергілій) to transmit two different
// Odyssey passages. After dedup in scripts/render_html.py::from_json the
// rendered page should show ONE Вергілій card transmitting TWO Гомер
// primaries, not two duplicate Вергілій cards.

const { chromium } = require('playwright');

const WS_ENDPOINT = process.env.WS_ENDPOINT || 'ws://host.docker.internal:3000/';
const BASE = process.env.BASE_URL || 'http://host.docker.internal:8001';
const URL = BASE + '/html/purg_19.html';

function assert(cond, msg) {
  if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; }
  else console.log('  ok  ' + msg);
}

(async () => {
  console.log('Connecting to ' + WS_ENDPOINT);
  const browser = await chromium.connect(WS_ENDPOINT);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  console.log('Loading ' + URL);
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(500);

  const payload = await page.evaluate(() => {
    const sources = (window.CANTO && window.CANTO.sources) || [];
    const cards = Array.from(document.querySelectorAll('.card'));
    return {
      sources: sources.map(s => ({
        id: s.id, tier: s.tier, author: s.author, work: s.work,
        transmits: s.transmits
      })),
      cards: cards.map(c => ({
        id: c.dataset.id,
        ref: (c.querySelector('.ref') || {}).textContent,
        author: (c.querySelector('.auth') || {}).textContent
      })),
      arrows: Array.from(document.querySelectorAll('#tree path.link')).map(p => ({
        from: p.getAttribute('data-from'),
        to: p.getAttribute('data-to'),
      })),
    };
  });

  const verg = payload.sources.filter(
    s => s.tier === 'direct' && s.author === 'Вергілій' && /Aen\. V,/.test(s.work)
  );
  assert(verg.length === 1, `exactly one Вергілій intermediary record (got ${verg.length})`);
  assert(
    Array.isArray(verg[0] && verg[0].transmits) && verg[0].transmits.length === 2,
    `Вергілій record transmits exactly 2 primaries (got ${verg[0] && verg[0].transmits && verg[0].transmits.length})`
  );

  const homer = payload.sources.filter(
    s => s.tier === 'primary' && s.author === 'Гомер' && /Od\. XII/.test(s.work)
  );
  assert(homer.length === 2, `two Гомер primary records (got ${homer.length})`);

  const vergCards = payload.cards.filter(c => c.author === 'Вергілій' && /Aen\. V,/.test(c.ref || ''));
  assert(vergCards.length === 1, `exactly one Вергілій card in DOM (got ${vergCards.length})`);

  const homerCards = payload.cards.filter(c => c.author === 'Гомер' && /Od\. XII/.test(c.ref || ''));
  assert(homerCards.length === 2, `two Гомер cards in DOM (got ${homerCards.length})`);

  const vergId = verg[0].id;
  const primaryIds = new Set(verg[0].transmits);
  const arrowsFromVerg = payload.arrows.filter(a => a.from === vergId && primaryIds.has(a.to));
  assert(
    arrowsFromVerg.length === 2,
    `two arrows from Вергілій card to both Гомер primaries (got ${arrowsFromVerg.length})`
  );

  await context.close();
  await browser.close();
  if (process.exitCode) console.error('\nFAILED'); else console.log('\nPASSED');
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
