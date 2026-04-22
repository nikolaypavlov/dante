// Overflow diagnostician. Point it at a page + viewport, dumps every
// element whose right edge extends past the viewport.
//
// Usage:
//   PAGE=/html/inf_01.html VIEWPORT=360 node diagnose.js

const { chromium } = require('playwright');

const WS = process.env.WS_ENDPOINT || 'ws://host.docker.internal:3000/';
const BASE = process.env.BASE_URL || 'http://host.docker.internal:8001';
const PAGE = process.env.PAGE || '/html/index.html';
const VP_W = parseInt(process.env.VIEWPORT || '360', 10);
const VP_H = parseInt(process.env.VIEWPORT_H || '640', 10);

(async () => {
  const browser = await chromium.connect(WS);
  const ctx = await browser.newContext({ viewport: { width: VP_W, height: VP_H } });
  const page = await ctx.newPage();
  const url = BASE + PAGE;
  console.log(`${url}  (${VP_W}x${VP_H})`);
  await page.goto(url, { waitUntil: 'networkidle' });

  const offenders = await page.evaluate(() => {
    const vw = window.innerWidth;
    const all = Array.from(document.querySelectorAll('*'));
    const wide = [];
    for (const el of all) {
      const r = el.getBoundingClientRect();
      if (r.right > vw + 1) {
        const cs = getComputedStyle(el);
        wide.push({
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          cls: (el.getAttribute('class') || '').slice(0, 60),
          L: Math.round(r.left),
          R: Math.round(r.right),
          W: Math.round(r.width),
          pos: cs.position,
          overflow: cs.overflow,
          minWidth: cs.minWidth,
          maxWidth: cs.maxWidth,
          width: cs.width,
          transform: cs.transform !== 'none' ? cs.transform : '-',
        });
      }
    }
    return { vw, bodyScrollWidth: document.body.scrollWidth, wide: wide.slice(0, 20) };
  });

  console.log('vw=', offenders.vw, 'body.scrollWidth=', offenders.bodyScrollWidth);
  for (const o of offenders.wide) {
    console.log(`${o.tag}${o.id ? '#' + o.id : ''}.${o.cls}`);
    console.log(`   L=${o.L} R=${o.R} W=${o.W}   pos=${o.pos}  width=${o.width}  max=${o.maxWidth}  transform=${o.transform}`);
  }

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
