/* Render engine — vertical tree inside medallion + via-routing + interactions */

(function () {
  const TYPE_UA = {
    ALLUSION:  'Пряма алюзія',
    STRUCTURE: 'Структурне запозичення',
    THEMATIC:  'Тематична паралель',
    INVERSION: 'Навмисна інверсія',
    ONOMASTIC: 'Іменна референція'
  };
  const TYPE_LAT = {
    ALLUSION:  'allusio directa',
    STRUCTURE: 'structura',
    THEMATIC:  'parallela thematica',
    INVERSION: 'inversio',
    ONOMASTIC: 'nominis relatio'
  };
  const ROMAN_TO_CANTICA = {
    inferno: 'Cantica Prima',
    purgatorio: 'Cantica Secunda',
    paradiso: 'Cantica Tertia'
  };

  const state = {
    theme: null,
    dataset: null
  };
  const $ = id => document.getElementById(id);

  function themeFromBody() {
    const m = (document.body.className || '').match(/theme-(\w+)/);
    return m ? m[1] : 'inferno';
  }

  function render() {
    state.theme = themeFromBody();

    const d = window.CANTO;
    state.dataset = d;

    $('kicker').textContent = 'Divina Commedia · ' + ROMAN_TO_CANTICA[state.theme];
    $('cantica').textContent = d.cantica;
    if ($('canto')) {
      const abbrev = { Inferno: 'Inf.', Purgatorio: 'Purg.', Paradiso: 'Par.' }[d.cantica] || d.cantica;
      $('canto').textContent = abbrev + ' ' + d.cantoRoman;
    }
    $('foliation').textContent = d.foliation;
    $('versesInfo').textContent = d.verses;
    $('summaryText').innerHTML = d.summaryUa;

    const typeCounts = d.sources.reduce((a, s) => (a[s.type] = (a[s.type] || 0) + 1, a), {});
    const counts = Object.keys(typeCounts).map(k =>
      `<span style="color:var(--gold)">${typeCounts[k]}</span> ${TYPE_UA[k].toLowerCase()}`
    ).join(' · ');
    const primaryCount = d.sources.filter(s => s.tier === 'primary').length;
    $('notaText').innerHTML =
      `Це дерево показує <strong>${d.sources.length}</strong> ідентифікованих джерел (${counts}). ` +
      (primaryCount ? `<strong>${primaryCount}</strong> з них — <em>первинні</em>: Данте знав їх лише через латинських посередників (він не читав грецької). ` : '') +
      `Товщина й стиль ліній кодують тип зв'язку.`;

    drawTree(d);
  }

  // ---------- TREE (horizontal card graph) ----------
  function drawTree(d) {
    drawTreeCards(d);
  }

  function drawTreeCards(d) {
    const graph = $('graph');
    const svg   = $('tree');
    const medallion = $('medallion');
    if (!graph) return;
    graph.innerHTML = '';
    svg.innerHTML = '';

    const byId = {};
    d.sources.forEach(s => byId[s.id] = s);

    // Dante-side: unique passages (by lineDante) with the connections that touch them
    // Each source has exactly one Dante passage, so we group sources by lineDante.
    const danteMap = new Map();
    d.sources.forEach(s => {
      const key = s.lineDante;
      if (!danteMap.has(key)) {
        danteMap.set(key, { line: s.lineDante, note: s.note, sourceIds: [] });
      }
      danteMap.get(key).sourceIds.push(s.id);
    });
    const dantePassages = Array.from(danteMap.values()).map((p, i) => ({
      ...p,
      uid: 'd_' + i
    }));

    // Partition sources: direct (col 2 — what Dante actually read)
    // vs primary (col 3 — the original source transmitted through an intermediary)
    const directs  = d.sources.filter(s => s.tier === 'direct');
    const primaries = d.sources.filter(s => s.tier === 'primary');

    // Columns per spec §4.2: Dante → Посередники → Джерела
    const colD = buildCol('dante',   'Данте',        'Divina Commedia · ' + d.cantoRoman);
    const colS = buildCol('sources', 'Посередники',  'fontes quos Dantes legit');
    const colI = buildCol('indirect','Первинні джерела', 'fontes primarii · per latinum');

    // Dante cards
    dantePassages.forEach(p => {
      const c = makeCard({
        id: p.uid,
        refText: p.line,
        descText: shortenDesc(p.note, 110),
        authText: d.cantica + ' · ' + d.cantoRoman,
        cls: 'dante',
        src: null,
        dantePassage: p
      });
      colD.body.appendChild(c);
    });

    // Intermediary / directly-read source cards (col 2) — tag with parent dante passage
    directs.forEach(s => {
      const c = makeCard({
        id: s.id,
        refText: s.work,
        descText: s.quoteLat,
        authText: s.author,
        cls: s.type,
        src: s
      });
      const passage = dantePassages.find(p => p.line === s.lineDante);
      if (passage) c.dataset.parent = passage.uid;
      colS.body.appendChild(c);
    });

    // Primary source cards (col 3) — tag with the direct that transmits them
    primaries.forEach(s => {
      const c = makeCard({
        id: s.id,
        refText: s.work,
        descText: s.quoteLat,
        authText: s.author,
        cls: s.type + ' indirect',
        src: s
      });
      // find the direct that transmits THIS primary
      const transmitter = directs.find(d => d.transmits === s.id);
      if (transmitter) c.dataset.parent = transmitter.id;
      colI.body.appendChild(c);
    });

    graph.appendChild(colD.el);
    graph.appendChild(colS.el);
    // Only render col 3 if there are primary (chain-transmitted) sources
    if (primaries.length > 0) {
      graph.appendChild(colI.el);
      graph.classList.remove('two-col');
    } else {
      graph.classList.add('two-col');
    }

    // After layout, align cards to their parents (short arrows, less scrolling)
    // then draw arrows as SVG paths
    requestAnimationFrame(() => {
      alignCardsToParents();
      drawArrows(d, dantePassages, directs, primaries);
    });
    // Also redraw on resize
    if (!drawTreeCards._boundResize) {
      drawTreeCards._boundResize = true;
      window.addEventListener('resize', () => {
        if (state.dataset) {
          alignCardsToParents();
          drawArrows(state.dataset, state.dantePassages, state.directs, state.primaries);
        }
      });
    }
    state.dantePassages = dantePassages;
    state.directs = directs;
    state.primaries = primaries;
  }

  function buildCol(cls, title, sub) {
    const el = document.createElement('div');
    el.className = 'col ' + cls;
    const head = document.createElement('div');
    head.className = 'col-head';
    head.innerHTML = title + '<span class="sub">' + sub + '</span>';
    el.appendChild(head);
    const body = document.createElement('div');
    body.className = 'col-body';
    body.style.display = 'flex';
    body.style.flexDirection = 'column';
    body.style.gap = '14px';
    el.appendChild(body);
    return { el, body, head };
  }

  function makeCard({id, refText, descText, authText, cls, src, dantePassage}) {
    const c = document.createElement('div');
    c.className = 'card ' + cls;
    c.dataset.id = id;
    c.innerHTML = `
      <div class="ref">${escapeHtml(refText)}</div>
      <div class="desc">${escapeHtml(descText || '')}</div>
      <div class="auth">${escapeHtml(authText || '')}</div>
    `;
    if (src) {
      c.addEventListener('mouseenter', e => {
        const viaSrc = resolveChainPartner(src);
        showTip(e, src, viaSrc);
        highlightChain(src);
      });
      c.addEventListener('mousemove', moveTip);
      c.addEventListener('mouseleave', () => { hideTip(); clearHighlight(); });
    } else if (dantePassage) {
      // dante card — highlight all connections + show passage tooltip
      c.addEventListener('mouseenter', e => {
        showDanteTip(e, dantePassage);
        highlightDantePassage(id);
      });
      c.addEventListener('mousemove', moveTip);
      c.addEventListener('mouseleave', () => { hideTip(); clearHighlight(); });
    }
    return c;
  }

  // Align cards in cols 2 and 3 so that each source sits at the same Y as its
  // parent (Dante passage for directs, transmitter for primaries). Stacks multiple
  // cards sharing a parent with a small vertical offset. Uses absolute positioning
  // within each column body so total column height adapts to content.
  function alignCardsToParents() {
    const graph = $('graph');
    if (!graph) return;
    const colD = graph.querySelector('.col.dante .col-body');
    const colS = graph.querySelector('.col.sources .col-body');
    const colI = graph.querySelector('.col.indirect .col-body');
    if (!colD || !colS) return;

    // Preserve existing gap as base row unit; 6px breathing room between stacked siblings.
    const STACK_GAP = 8;

    // Reset any absolute-positioning from previous calls so we can re-measure fresh.
    [colS, colI].forEach(col => {
      if (!col) return;
      col.style.position = 'relative';
      col.style.display = 'block';
      col.style.minHeight = '0';
      [...col.children].forEach(c => {
        c.style.position = '';
        c.style.top = '';
        c.style.left = '';
        c.style.right = '';
        c.style.width = '';
        c.style.marginBottom = '';
      });
    });

    // Force reflow so Dante column has real positions
    colD.offsetHeight;

    const graphTop = graph.getBoundingClientRect().top;

    // Measure parent Y (top edge, relative to its column) for each Dante passage uid.
    const parentY = {};
    [...colD.children].forEach(c => {
      const r = c.getBoundingClientRect();
      parentY[c.dataset.id] = { top: r.top - graphTop, h: r.height };
    });

    // Position col 2 (directs) absolutely aligned to parent Dante passage.
    // Multiple directs sharing a parent stack downward from the parent top.
    const colSRect = colS.getBoundingClientRect();
    const stackCount = {};
    const directPos = {};  // id -> {top, h} — for primaries to chain onto
    const colSOffset = colSRect.top - graphTop;
    [...colS.children].forEach(card => {
      const parent = card.dataset.parent;
      const parentInfo = parentY[parent];
      card.style.position = 'absolute';
      card.style.left = '0';
      card.style.right = '0';
      if (!parentInfo) {
        card.style.top = '0';
        return;
      }
      const idx = (stackCount[parent] = (stackCount[parent] || 0));
      stackCount[parent] = idx + 1;
      const localTop = parentInfo.top - colSOffset;
      const y = Math.max(0, localTop + idx * (estimateCardH(card) + STACK_GAP));
      card.style.top = y + 'px';
    });

    // Resolve overlaps: sweep top-to-bottom, push any card below if it overlaps
    // its predecessor. Preserves order but guarantees non-overlap.
    resolveOverlaps(colS, STACK_GAP, directPos);

    // Size colS to the deepest card
    const colSHeight = Math.max(
      ...[...colS.children].map(c =>
        (parseFloat(c.style.top) || 0) + estimateCardH(c)
      ),
      0
    );
    colS.style.minHeight = (colSHeight + 4) + 'px';

    // Position col 3 (primaries) aligned to their transmitter direct.
    if (colI) {
      const colIRect = colI.getBoundingClientRect();
      const colIOffset = colIRect.top - graphTop;
      const pStack = {};
      [...colI.children].forEach(card => {
        const parent = card.dataset.parent;
        const transmitterPos = directPos[parent];
        card.style.position = 'absolute';
        card.style.left = '0';
        card.style.right = '0';
        if (!transmitterPos) {
          card.style.top = '0';
          return;
        }
        const idx = (pStack[parent] = (pStack[parent] || 0));
        pStack[parent] = idx + 1;
        const y = Math.max(0, transmitterPos.top + idx * (estimateCardH(card) + STACK_GAP));
        card.style.top = y + 'px';
      });
      resolveOverlaps(colI, STACK_GAP);
      const colIHeight = Math.max(
        ...[...colI.children].map(c =>
          (parseFloat(c.style.top) || 0) + estimateCardH(c)
        ),
        0
      );
      colI.style.minHeight = (colIHeight + 4) + 'px';
    }
  }

  // Resolve overlaps within a column by pushing each card down past the bottom
  // of the previous one (after sorting by current top). Optionally records final
  // positions into `posOut` (keyed by card id) for downstream columns to use.
  function resolveOverlaps(col, gap, posOut) {
    const cards = [...col.children].sort((a, b) =>
      (parseFloat(a.style.top) || 0) - (parseFloat(b.style.top) || 0)
    );
    let cursor = 0;
    cards.forEach(card => {
      const h = estimateCardH(card);
      const desired = parseFloat(card.style.top) || 0;
      const y = Math.max(cursor, desired);
      card.style.top = y + 'px';
      cursor = y + h + gap;
      if (posOut) posOut[card.dataset.id] = { top: y, h };
    });
  }

  function estimateCardH(card) {
    // Prefer real measured height; fall back to a reasonable default.
    const h = card.getBoundingClientRect().height;
    return h > 0 ? h : 92;
  }

  function findById(id) {
    return (state.dataset.sources || []).find(s => s.id === id);
  }

  // For a source card, find its "chain partner" for tooltip display.
  // - If src is an intermediary (direct tier) that transmits a primary, return the primary.
  // - If src is a primary, return the first intermediary that transmits it (if any).
  function resolveChainPartner(src) {
    if (!src) return null;
    if (src.tier === 'direct' && src.transmits) {
      return findById(src.transmits) || null;
    }
    if (src.tier === 'primary') {
      return (state.dataset.sources || []).find(
        s => s.tier === 'direct' && s.transmits === src.id
      ) || null;
    }
    return null;
  }

  function drawArrows(d, dantePassages, directs, primaries) {
    const svg = $('tree');
    const medallion = $('medallion');
    if (!svg || !medallion) return;
    svg.innerHTML = '';
    const rect = medallion.getBoundingClientRect();
    const W = rect.width;
    const H = rect.height;
    svg.setAttribute('width',  W);
    svg.setAttribute('height', H);
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);

    // Dante passage lookup by line
    const passageByLine = {};
    dantePassages.forEach(p => { passageByLine[p.line] = p.uid; });

    // 1. Dante → Direct (intermediary or direct-access source) — solid
    directs.forEach(s => {
      const fromId = passageByLine[s.lineDante];
      if (!fromId) return;
      appendArrow(svg, fromId, s.id, s.type, false);
    });

    // 2. Direct (intermediary) → Primary — same style as Dante → Direct
    directs.forEach(s => {
      if (!s.transmits) return;
      appendArrow(svg, s.id, s.transmits, s.type, false);
    });
  }

  function appendArrow(svg, fromId, toId, type, dashed) {
    if (!fromId || !toId) return;
    const a = document.querySelector('.card[data-id="' + cssEscape(fromId) + '"]');
    const b = document.querySelector('.card[data-id="' + cssEscape(toId)   + '"]');
    if (!a || !b) return;
    const medallion = $('medallion');
    const mRect = medallion.getBoundingClientRect();
    const ar = a.getBoundingClientRect();
    const br = b.getBoundingClientRect();
    const x1 = ar.right - mRect.left;
    const y1 = ar.top + ar.height/2 - mRect.top;
    const x2 = br.left  - mRect.left;
    const y2 = br.top  + br.height/2 - mRect.top;

    // Control-point offset proportional to horizontal distance
    const dx = Math.max(40, (x2 - x1) * 0.55);
    const d  = `M ${x1},${y1} C ${x1+dx},${y1} ${x2-dx},${y2} ${x2},${y2}`;

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', d);
    path.setAttribute('fill', 'none');
    path.setAttribute('class', 'link ' + type + (dashed ? ' indirect' : ''));
    path.setAttribute('data-from', fromId);
    path.setAttribute('data-to',   toId);
    path.setAttribute('stroke', colorCss(type));
    path.setAttribute('stroke-width', typeWidth(type));
    if (dashed) {
      path.setAttribute('stroke-dasharray', '4 5');
      path.setAttribute('opacity', '0.55');
    } else {
      if (type === 'THEMATIC')  path.setAttribute('stroke-dasharray', '5 4');
      if (type === 'ONOMASTIC') path.setAttribute('stroke-dasharray', '1.5 4');
      path.setAttribute('opacity', '0.85');
    }
    svg.appendChild(path);
  }

  function typeWidth(t) {
    return t === 'STRUCTURE' ? 2.6 : 1.8;
  }

  function colorCss(t) {
    const map = {
      ALLUSION:  '#d4a72c',
      STRUCTURE: '#3e7a3a',
      THEMATIC:  '#7e4a9e',
      INVERSION: '#c43a14',
      ONOMASTIC: '#3a6ba8'
    };
    return map[t] || '#999';
  }

  function cssEscape(s) { return String(s).replace(/"/g,'\\"'); }

  function shortenDesc(t, n) {
    t = String(t || '');
    if (t.length <= n) return t;
    return t.slice(0, n-1).replace(/\s+\S*$/, '') + '…';
  }

  function highlightChain(src) {
    const medallion = $('medallion');
    medallion.classList.add('dim');
    const ids = new Set([src.id]);
    const partner = resolveChainPartner(src);
    if (partner) ids.add(partner.id);
    // also the dante passage card
    const passageUid = (state.dantePassages || []).find(p => p.line === src.lineDante);
    if (passageUid) ids.add(passageUid.uid);
    // If src is a primary, include its dante passage via transmitter
    if (src.tier === 'primary' && partner) {
      const partnerPassage = (state.dantePassages || []).find(p => p.line === partner.lineDante);
      if (partnerPassage) ids.add(partnerPassage.uid);
    }
    document.querySelectorAll('.card').forEach(c => {
      if (ids.has(c.dataset.id)) c.classList.add('active');
      else c.classList.add('dim');
    });
    // activate arrows touching these ids
    document.querySelectorAll('#tree path.link').forEach(p => {
      const f = p.getAttribute('data-from');
      const t = p.getAttribute('data-to');
      if (ids.has(f) && ids.has(t)) p.classList.add('active');
      else p.classList.add('fade');
    });
  }

  function highlightDantePassage(uid) {
    const medallion = $('medallion');
    medallion.classList.add('dim');
    const passage = (state.dantePassages || []).find(p => p.uid === uid);
    if (!passage) return;
    const touchedSourceIds = new Set(passage.sourceIds);
    // also include primaries transmitted by those sources
    passage.sourceIds.forEach(sid => {
      const s = findById(sid);
      if (s && s.transmits) touchedSourceIds.add(s.transmits);
    });
    const allIds = new Set([uid, ...touchedSourceIds]);
    document.querySelectorAll('.card').forEach(c => {
      if (allIds.has(c.dataset.id)) c.classList.add('active');
      else c.classList.add('dim');
    });
    document.querySelectorAll('#tree path.link').forEach(p => {
      const f = p.getAttribute('data-from');
      const t = p.getAttribute('data-to');
      if (allIds.has(f) && allIds.has(t)) p.classList.add('active');
      else p.classList.add('fade');
    });
  }

  function clearHighlight() {
    const medallion = $('medallion');
    medallion.classList.remove('dim');
    document.querySelectorAll('.card.active, .card.dim').forEach(c => c.classList.remove('active','dim'));
    document.querySelectorAll('#tree path.link').forEach(p => p.classList.remove('active','fade'));
  }


  function shortenWork(w) {
    if (w.length <= 26) return w;
    return w.substring(0, 24) + '…';
  }

  function getTypeColor(t) {
    switch (t) {
      case 'ALLUSION':  return 'var(--c-allusion)';
      case 'STRUCTURE': return 'var(--c-structure)';
      case 'THEMATIC':  return 'var(--c-thematic)';
      case 'INVERSION': return 'var(--c-inversion)';
      case 'ONOMASTIC': return 'var(--c-onomastic)';
    }
    return 'var(--ink)';
  }

  // ---------- TOOLTIP ----------
  function showDanteTip(e, passage) {
    const tip = $('tip');
    const d = state.dataset;
    const touched = (passage.sourceIds || []).map(id => findById(id)).filter(Boolean);
    const directCount  = touched.filter(s => s.tier !== 'primary').length;
    const primaryCount = touched.filter(s => s.tier === 'primary').length;

    $('tipHead').textContent = d.cantica + ' · ' + d.cantoRoman;
    $('tipSub').textContent  = passage.line;
    const typeEl = $('tipType');
    typeEl.textContent = 'locus dantescus · Дантова терцина';
    typeEl.style.color = 'var(--gold)';
    typeEl.style.borderColor = 'var(--gold)';

    // Render list of touched sources
    const srcList = touched.map(s => {
      const col = getTypeColor(s.type);
      return `<div style="margin: 4px 0; padding-left: 10px; border-left: 2px solid ${col};">
        <div style="font-weight:600; color: var(--ink);">${escapeHtml(s.author)}<span style="color:var(--ink-dim); font-weight:400;"> · ${escapeHtml(s.work)}</span>${s.tier === 'primary' ? ' <span style="color:var(--ink-dim); font-style:italic;">(фонт)</span>' : ''}</div>
        <div style="color: var(--ink-dim); font-size: 11px; font-style:italic;">${escapeHtml(s.quoteLat || '')}</div>
      </div>`;
    }).join('');

    $('tipQuote').innerHTML = srcList || '<em style="color:var(--ink-dim)">Немає пов\'язаних джерел</em>';
    $('tipLines').innerHTML =
      `<strong>${touched.length}</strong> ${touched.length === 1 ? 'джерело' : 'джерел'}` +
      (directCount  ? ` · <span style="color:var(--gold);">${directCount}</span> прямих/посередницьких` : '') +
      (primaryCount ? ` · <span style="color:var(--ink-dim);">${primaryCount}</span> первинних` : '');
    $('tipNote').textContent = passage.note || '';
    tip.classList.add('visible');
    moveTip(e);
  }

  function showTip(e, src, viaSrc) {
    const tip = $('tip');
    $('tipHead').textContent = src.author;
    $('tipSub').textContent = `${src.work} · ${src.yearUa}`;
    const typeEl = $('tipType');
    typeEl.textContent = TYPE_LAT[src.type] + '  ·  ' + TYPE_UA[src.type] +
      (viaSrc ? '  ·  per ' + viaSrc.author : '');
    typeEl.style.color = getTypeColor(src.type);
    typeEl.style.borderColor = getTypeColor(src.type);
    $('tipQuote').innerHTML =
      `<span style="color:var(--ink-dim); font-style:italic">« ${escapeHtml(src.quoteLat)} »</span>
       <div style="margin-top:6px; font-style:normal; font-size:12px;">${escapeHtml(src.quoteUa)}</div>`;
    $('tipLines').innerHTML =
      `Dante: <strong>${src.lineDante}</strong> &nbsp;·&nbsp; Fons: <strong>${src.lineSource}</strong>` +
      (viaSrc ? `<br/><span style="color:var(--ink-dim); font-style:italic;">опосередковано через ${viaSrc.author}, ${viaSrc.work}</span>` : '');
    $('tipNote').textContent = src.note || '';
    tip.classList.add('visible');
    moveTip(e);

    $('medallion').classList.add('dim');
    // highlight whole chain: this source + its via-ancestor (if any) + root link
    const ids = [src.id];
    if (viaSrc) ids.push(viaSrc.id);
    ids.forEach(id => {
      document.querySelectorAll('.link[data-id="'+id+'"], .node-group[data-id="'+id+'"]').forEach(el => el.classList.add('active'));
    });
  }

  function moveTip(e) {
    const tip = $('tip');
    const pad = 16;
    let x = e.clientX + pad;
    let y = e.clientY + pad;
    const r = tip.getBoundingClientRect();
    if (x + r.width > window.innerWidth - 10) x = e.clientX - r.width - pad;
    if (y + r.height > window.innerHeight - 10) y = e.clientY - r.height - pad;
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
  }

  function hideTip() {
    $('tip').classList.remove('visible');
    $('medallion').classList.remove('dim');
    document.querySelectorAll('.link.active, .node-group.active').forEach(el => el.classList.remove('active'));
  }

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  }

  function el(name, attrs) {
    const n = document.createElementNS('http://www.w3.org/2000/svg', name);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function textAt(x, y, content, cls) {
    const t = el('text', { x, y, 'class': cls });
    t.textContent = content;
    return t;
  }

  function buildSidePanel() {
    const panel = document.getElementById('panelContent');
    if (!panel) return;
    const currentFile = document.body.dataset.currentFile || '';
    const sections = [
      { name: 'Inferno',    prefix: 'inf',  count: 34 },
      { name: 'Purgatorio', prefix: 'purg', count: 33 },
      { name: 'Paradiso',   prefix: 'par',  count: 33 }
    ];
    sections.forEach(s => {
      const section = document.createElement('div');
      section.className = 'side-panel-section';
      const h = document.createElement('h3');
      h.textContent = s.name;
      section.appendChild(h);
      const links = document.createElement('div');
      links.className = 'side-panel-links';
      for (let i = 1; i <= s.count; i++) {
        const stem = s.prefix + '_' + String(i).padStart(2, '0');
        const a = document.createElement('a');
        a.href = stem + '.html';
        a.textContent = String(i);
        if (stem === currentFile) a.className = 'current';
        links.appendChild(a);
      }
      section.appendChild(links);
      panel.appendChild(section);
    });
  }

  function togglePanel() {
    const p = document.getElementById('sidePanel');
    const o = document.getElementById('overlay');
    if (p) p.classList.toggle('open');
    if (o) o.classList.toggle('open');
  }
  window.togglePanel = togglePanel;

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      const p = document.getElementById('sidePanel');
      if (p && p.classList.contains('open')) togglePanel();
    }
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { buildSidePanel(); render(); });
  } else {
    buildSidePanel();
    render();
  }
})();
