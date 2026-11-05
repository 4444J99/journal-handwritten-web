/* alive prototype: architecture / spiral / reading over the author's own scans.
   Vanilla JS, Canvas 2D, no network beyond same-origin. See README.md.
   Rule 4 (data): every pixel read from a page image goes through readRegion(), which refuses any
   rectangle that is not inside one of the registered line boxes (p001: atoms-p001.json; city=all58:
   city-all58.json). Words, glyphs and marks are sub-rectangles of a line box; sprites in READING only
   ever come from p001's lines on diary1. Each p001 line also carries a `region` polygon (the area between its two
   seams, see segment.py partition()); the atlas keeps only that line's pixels inside it, so a crop of line N cannot
   carry pixels of line N-1 or N+1 whatever its rectangle. The polygon only restricts the rectangle further. */
(() => {
"use strict";

// ------------------------------------------------------------------ parameters
const Q = new URLSearchParams(location.search);
const CITY = Q.get("city") === "all58" ? "all58" : "p001";
const VIEWS = ["architecture", "spiral", "reading"];
const UNITS = ["poem", "stanza", "line", "word", "glyph"];
const SPIRAL_UNITS = ["line", "page"];
const SEED = Number.isFinite(parseInt(Q.get("seed"), 10)) ? parseInt(Q.get("seed"), 10) : 1;
const T_PARAM = Q.has("t") && Number.isFinite(parseFloat(Q.get("t"))) ? Math.max(0, parseFloat(Q.get("t"))) : null;
const DT = 1 / 30;          // fixed simulation step (seconds)
const CAP = 400;            // live sprite cap
const RAMP = 12;            // seconds from empty paper to the dense field
const REDUCED_T = 14;       // the one static frame under prefers-reduced-motion
const FH = 64, FG = 2, SB = 34, BGAP = 160; // floor height, floor gap, stanza setback, gap between buildings (world units)

let VIEW = VIEWS.includes(Q.get("view")) ? Q.get("view") : "architecture";
let PIN = UNITS.includes(Q.get("unit")) && VIEW !== "spiral" ? Q.get("unit") : null;
let SPUNIT = VIEW === "spiral" && SPIRAL_UNITS.includes(Q.get("unit")) ? Q.get("unit") : "line";
let PREV_VIEW = "architecture";
let selOpen = false;

const cv = document.getElementById("c");
const ctx = cv.getContext("2d");
const selEl = document.getElementById("sel");
let vw = 0, vh = 0, dpr = 1;

// ------------------------------------------------------------------ theme
const TH = { dark: false, desk: "#e6e0d2", sheet: "#f7f4ec", ink: "#2b2a27", ink2: "#7a7262", wall: "#ede8dc" };
function hexRgb(h) { h = h.trim(); if (h[0] !== "#") return [128, 128, 128]; if (h.length === 4) h = "#" + h[1] + h[1] + h[2] + h[2] + h[3] + h[3]; return [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)); }
function mix(a, b, t) { const A = hexRgb(a), B = hexRgb(b); return "rgb(" + A.map((v, i) => Math.round(v + (B[i] - v) * t)).join(",") + ")"; }
function readTheme() {
  const cs = getComputedStyle(document.documentElement), g = n => cs.getPropertyValue(n).trim();
  const dm = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const th = document.documentElement.getAttribute("data-theme");
  TH.dark = th === "dark" || (th !== "light" && dm);
  TH.desk = g("--desk"); TH.sheet = g("--sheet"); TH.ink = g("--ink"); TH.ink2 = g("--ink-2");
  TH.wall = mix(TH.desk, TH.sheet, 0.45);
}

// ------------------------------------------------------------------ rule 4 registry
const ALLOWED = new Map();           // page id -> [[x0,y0,x1,y1], ...] line boxes in page pixels
const READS = [];                    // every region read from a page image
function allow(page, box) { if (!ALLOWED.has(page)) ALLOWED.set(page, []); ALLOWED.get(page).push(box); }
function readRegion(page, r) {       // r = [x0,y0,x1,y1] in page pixels (tolerance 1.5 px for tier rounding)
  const ok = (ALLOWED.get(page) || []).some(b => r[0] >= b[0] - 1.5 && r[1] >= b[1] - 1.5 && r[2] <= b[2] + 1.5 && r[3] <= b[3] + 1.5);
  if (!ok) throw new Error("rule 4: refused region outside the registered boxes of " + page);
  READS.push({ page, box: r.map(v => Math.round(v * 10) / 10) });
}

// ------------------------------------------------------------------ data
let PIECES = [];                     // buildings in order
let P001 = null;
let RULES = null;
const failed = [];

function mkLine(id, b, l, box, extra) {
  return Object.assign({ id, b, l, box, w: box[2] - box[0], h: box[3] - box[1] }, extra || {});
}
function pieceFromAtoms(a) {
  const p = { id: "p001", page: "diary1", tier: "p", pageSize: a.meta.source_page.size, stanzas: [], lines: [], hasAtoms: true, words: [], glyphs: [] };
  for (const st of a.stanzas) {
    const S = { block: st.block, lines: [] };
    for (const ln of st.lines) {
      const L = mkLine("diary1-" + st.block + "-" + ln.line, st.block, ln.line, ln.box.slice(), {
        gi: ln.index, region: Array.isArray(ln.region) && ln.region.length >= 3 ? ln.region.map(q => [q[0], q[1]]) : null,
        words: (ln.words || []).map(w => ({ box: w.box.slice(), glyphs: (w.glyphs || []).map(g => g.box.slice()) })),
        marks: (ln.marks || []).map(m => m.box.slice()), piece: p });
      S.lines.push(L); p.lines.push(L);
      allow("diary1", L.box);
    }
    p.stanzas.push(S);
  }
  for (const L of p.lines) {
    for (const w of L.words) { p.words.push({ ln: L, box: w.box }); for (const g of w.glyphs) p.glyphs.push({ ln: L, box: g }); }
    for (const m of L.marks) p.glyphs.push({ ln: L, box: m });
  }
  return p;
}
function pieceFromCity(c) {
  const p = { id: c.id, page: c.page, tier: "i", pageSize: c.size, stanzas: [], lines: [], hasAtoms: false, words: [], glyphs: [] };
  let cur = null;
  for (const ln of c.lines) {
    if (!ln.box) continue;                               // unboxed lines are omitted, never stood in for
    if (!cur || cur.block !== ln.b) { cur = { block: ln.b, lines: [] }; p.stanzas.push(cur); }
    const L = mkLine(c.page + "-" + ln.b + "-" + ln.l, ln.b, ln.l, ln.box.slice(), { piece: p, words: [], marks: [] });
    cur.lines.push(L); p.lines.push(L);
    allow(c.page, L.box);
  }
  return p;
}
function finest(p) { return CITY === "p001" && p.hasAtoms ? 4 : 2; }   // index into UNITS
function availUnits(p) { return UNITS.slice(0, finest(p) + 1); }

// ------------------------------------------------------------------ ink atlases
function lumOf(d, i) { return 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]; }
function inkAlpha(l) { const a = Math.min(1, Math.max(0, (236 - l) / (236 - 95))); return a * a * (3 - 2 * a); }

// Pixels of the line rectangle whose centre lies inside the line's region polygon (page pixels): even-odd
// crossings of the vertical line through each pixel-column centre, half-open on y (top <= y < bottom). Regions
// of different lines never overlap by construction, so the masks of neighbouring lines are disjoint.
function regionMask(L, w, h) {
  const poly = L.region, sc = L.piece.sc, m = new Uint8Array(w * h), n = poly.length, ys = [];
  for (let xx = 0; xx < w; xx++) {
    const px = (L.sx0 + xx + 0.5) / sc;
    ys.length = 0;
    for (let i = 0; i < n; i++) {
      const a = poly[i], b = poly[i + 1 === n ? 0 : i + 1];
      if ((a[0] <= px) !== (b[0] <= px)) ys.push(a[1] + (px - a[0]) * (b[1] - a[1]) / (b[0] - a[0]));
    }
    ys.sort((p, q) => p - q);
    for (let k = 0; k + 1 < ys.length; k += 2) {
      const y0 = Math.max(0, Math.ceil(ys[k] * sc - 0.5 - L.sy0)), y1 = Math.min(h, Math.ceil(ys[k + 1] * sc - 0.5 - L.sy0));
      for (let yy = y0; yy < y1; yy++) m[yy * w + xx] = 1;
    }
  }
  return m;
}

function processLine(img, w, h, L, useRules) {           // img: ImageData of the line box; returns alpha array
  const d = img.data, n = w * h, lum = new Uint8Array(n), al = new Float32Array(n);
  for (let i = 0; i < n; i++) { const l = lumOf(d, i * 4); lum[i] = l; al[i] = inkAlpha(l); }
  if (useRules && RULES) {
    const probe = (x, y) => { if (x < 0 || x >= w || y < 0 || y >= h) return true; return lum[y * w + x] < 171; }; // outside the box counts as ink: keep
    const x0 = L.box[0], y0 = L.box[1];
    for (const rc of RULES.rules) {
      for (let x = 0; x < w; x++) {
        const yc = rc - RULES.pad + RULES.slope * (x0 + x) - y0;
        if (yc < -3 || yc > h + 3) continue;
        const yr = Math.round(yc), up = yr - 5, dn = yr + 5;
        const keep = probe(x - 1, up) || probe(x, up) || probe(x + 1, up) || probe(x - 1, dn) || probe(x, dn) || probe(x + 1, dn);
        if (keep) continue;
        for (let y = Math.max(0, Math.ceil(yc - 2.5)); y <= Math.min(h - 1, Math.floor(yc + 2.5)); y++) al[y * w + x] = 0;
      }
    }
  }
  if (L.piece.hasAtoms) {                                // keep only ink inside this line's own glyph / mark boxes
    const m = new Uint8Array(n), pad = 2;
    const fill = b => { const a0 = Math.max(0, b[0] - L.box[0] - pad), a1 = Math.min(w, b[2] - L.box[0] + pad), c0 = Math.max(0, b[1] - L.box[1] - pad), c1 = Math.min(h, b[3] - L.box[1] + pad); for (let y = c0; y < c1; y++) for (let x = a0; x < a1; x++) m[y * w + x] = 1; };
    for (const wd of L.words) for (const g of wd.glyphs) fill(g);
    for (const mk of L.marks) fill(mk);
    for (let i = 0; i < n; i++) if (!m[i]) al[i] = 0;
  }
  if (L.region) {                                        // bake the seam region in: nothing outside it is ever drawn
    const rm = regionMask(L, w, h);
    let before = 0, after = 0;
    for (let i = 0; i < n; i++) { if (al[i] > 0) before++; if (!rm[i]) al[i] = 0; if (al[i] > 0) after++; }
    L.rmask = rm; L.clip = { inkBefore: before, inkAfter: after };
  }
  return al;
}

async function fetchBitmap(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error("fetch " + url + " " + r.status);
  return createImageBitmap(await r.blob());
}

function recolor(p) {                                    // atlas = theme ink with the stored alpha master (exact on every switch); mips rebuilt
  const c = p.atlas, x = c.getContext("2d"), rgb = hexRgb(TH.ink), img = x.createImageData(c.width, c.height), m = p.master, d = img.data;
  for (let i = 0; i < m.length; i++) { d[i * 4] = rgb[0]; d[i * 4 + 1] = rgb[1]; d[i * 4 + 2] = rgb[2]; d[i * 4 + 3] = m[i]; }
  x.putImageData(img, 0, 0);
  p.mips = [{ c, k: 1 }];
  for (const k of [0.5, 0.25]) {
    const m = document.createElement("canvas"); m.width = Math.max(1, Math.ceil(c.width * k)); m.height = Math.max(1, Math.ceil(c.height * k));
    const mx = m.getContext("2d"); mx.imageSmoothingEnabled = true; mx.imageSmoothingQuality = "high";
    mx.drawImage(p.mips[p.mips.length - 1].c, 0, 0, m.width, m.height);
    p.mips.push({ c: m, k });
  }
}

async function buildPiece(p) {
  const bmp = await fetchBitmap("/site/img/" + p.tier + "/" + p.page + ".jpg");
  const sc = bmp.width / p.pageSize[0];
  p.sc = sc;
  // shelf packing of the line rectangles
  const RW = 1100; let x = 0, y = 0, rowH = 0, maxW = 0;
  for (const L of p.lines) {
    L.sx0 = Math.floor(L.box[0] * sc); L.sy0 = Math.floor(L.box[1] * sc);
    L.aw = Math.ceil(L.box[2] * sc) - L.sx0; L.ah = Math.ceil(L.box[3] * sc) - L.sy0;
    if (x + L.aw + 2 > RW && x > 0) { x = 0; y += rowH + 2; rowH = 0; }
    L.ax = x; L.ay = y; x += L.aw + 2; rowH = Math.max(rowH, L.ah); maxW = Math.max(maxW, x);
  }
  const atlas = document.createElement("canvas"); atlas.width = Math.max(maxW, 4); atlas.height = Math.max(y + rowH + 2, 4);
  p.master = new Uint8ClampedArray(atlas.width * atlas.height);
  const tmp = document.createElement("canvas"), tx = tmp.getContext("2d", { willReadFrequently: true });
  for (const L of p.lines) {
    readRegion(p.page, [L.sx0 / sc, L.sy0 / sc, (L.sx0 + L.aw) / sc, (L.sy0 + L.ah) / sc]);
    tmp.width = L.aw; tmp.height = L.ah;
    tx.drawImage(bmp, L.sx0, L.sy0, L.aw, L.ah, 0, 0, L.aw, L.ah);
    const img = tx.getImageData(0, 0, L.aw, L.ah);
    const al = processLine(img, L.aw, L.ah, L, p.hasAtoms && p.tier === "p");
    for (let yy = 0; yy < L.ah; yy++) for (let xx = 0; xx < L.aw; xx++) p.master[(L.ay + yy) * atlas.width + L.ax + xx] = Math.round(al[yy * L.aw + xx] * 255);
  }
  bmp.close && bmp.close();
  p.atlas = atlas;
  recolor(p);
  p.ready = true;
}

// draw a sub-rectangle (atlas units) of a piece's atlas into the current transform; screen scale picks the mip
let SCR = 1;                                              // screen pixels per destination unit (set by callers)
function blit(p, sx, sy, sw, sh, dx, dy, dw, dh) {
  const ratio = (dw * SCR) / sw;
  const m = ratio < 0.34 ? p.mips[2] : ratio < 0.68 ? p.mips[1] : p.mips[0];
  const k = m.k;
  ctx.drawImage(m.c, sx * k, sy * k, Math.max(0.5, sw * k), Math.max(0.5, sh * k), dx, dy, dw, dh);
}
function subRect(L, box) {                                // sub-rectangle of a line, clamped to the line's box
  const x0 = Math.max(box[0], L.box[0]), y0 = Math.max(box[1], L.box[1]), x1 = Math.min(box[2], L.box[2]), y1 = Math.min(box[3], L.box[3]);
  if (x1 - x0 < 1 || y1 - y0 < 1) return null;
  const sc = L.piece.sc;
  return { sx: L.ax + x0 * sc - L.sx0, sy: L.ay + y0 * sc - L.sy0, sw: (x1 - x0) * sc, sh: (y1 - y0) * sc, box: [x0, y0, x1, y1], pw: x1 - x0, ph: y1 - y0 };
}
function wholeLine(L) { return subRect(L, L.box); }

// ------------------------------------------------------------------ architecture
let CITYB = [];                                           // buildings: {p, cx, W, H, x0, x1}
let CITYW = 0, CITYH = 0;
function layoutBuildings() {
  let x = 0; CITYB = []; CITYH = 0;
  for (const p of PIECES) {
    if (!p.lines.length) continue;
    let y = 0, first = true;
    for (const S of p.stanzas) {
      if (!first) y += SB; first = false;
      S.fy0 = y;
      for (const L of S.lines) { L.fy = y; y += FH + FG; }
      S.fy1 = y - FG;
    }
    const H = y - FG, W = Math.max(...p.lines.map(l => l.w));
    CITYB.push({ p, W, H, x0: x, x1: x + W, cx: x + W / 2 });
    x += W + BGAP; CITYH = Math.max(CITYH, H);
    p.bld = CITYB[CITYB.length - 1];
  }
  CITYW = Math.max(1, x - BGAP);
}

const cam = { x: 0, y: 0, z: 1 };                         // architecture camera (world centre, screen px per world unit)
const scam = { x: 0, y: 0, z: 1 };                        // spiral camera
function zFitArch() {
  if (CITY === "p001" || CITYB.length === 1) { const b = CITYB[0]; return Math.min(vw * 0.88 / b.W, vh * 0.84 / b.H); }
  return vw * 0.94 / CITYW;
}
function archLimits() { return { zmin: zFitArch() * (CITY === "all58" ? 0.6 : 0.1), zmax: (CITY === "all58" ? 100 : 360) / FH }; }
function fitArch() {
  cam.z = zFitArch();
  if (CITY === "p001") { cam.x = CITYB[0].cx; cam.y = -CITYB[0].H / 2; }
  else { cam.x = CITYW / 2; cam.y = -CITYH * 0.5; }
}
function unitByFloorPx(fh) { return fh < 4 ? "poem" : fh < 10 ? "stanza" : fh < 48 ? "line" : fh < 110 ? "word" : "glyph"; }
function effUnit(p, fh) {
  const want = PIN || unitByFloorPx(fh);
  const i = Math.min(UNITS.indexOf(want), finest(p));
  return UNITS[i];
}
function floorWorld(b, L) { return { x0: b.cx - L.w / 2, y0: -b.H + L.fy }; }

function drawBuilding(b, unit) {
  const p = b.p, g = ctx, z = cam.z;
  const hair = 1 / z;
  g.lineWidth = hair; g.strokeStyle = TH.ink2;
  const ground = 0, top = -b.H;
  const rects = [];                                       // contiguous floors (stanza / poem)
  if (unit === "poem" || unit === "stanza") {
    const polyFloors = (arr) => {
      if (!arr.length) return;
      g.beginPath();
      for (const r of arr) { g.lineTo(r.x0, r.y0); g.lineTo(r.x0, r.y1); }
      for (let i = arr.length - 1; i >= 0; i--) { g.lineTo(arr[i].x1, arr[i].y1); g.lineTo(arr[i].x1, arr[i].y0); }
      g.closePath();
    };
    const floorsOf = (S) => S.lines.map(L => { const f = floorWorld(b, L); return { x0: f.x0, x1: f.x0 + L.w, y0: f.y0, y1: f.y0 + FH + FG, L }; });
    if (unit === "poem") {
      const all = []; let prev = null;
      for (const S of p.stanzas) {
        const fl = floorsOf(S);
        if (prev && fl.length) { const w = Math.min(prev.x1 - prev.x0, fl[0].x1 - fl[0].x0), cx = b.cx; all.push({ x0: cx - w / 2, x1: cx + w / 2, y0: prev.y1, y1: fl[0].y0 }); }
        all.push(...fl); prev = fl[fl.length - 1];
      }
      polyFloors(all); g.fillStyle = TH.sheet; g.fill();
      for (const r of all) if (r.L) { const s = wholeLine(r.L); const dh = Math.min(FH, r.L.h); SCR = z * dpr; blit(p, s.sx, s.sy, s.sw, s.sh, r.x0, r.y0 + (FH - r.L.h) / 2, r.L.w, r.L.h); }
      polyFloors(all); g.stroke();
    } else {
      for (const S of p.stanzas) {
        const fl = floorsOf(S); polyFloors(fl); g.fillStyle = TH.sheet; g.fill();
        for (const r of fl) { const s = wholeLine(r.L); SCR = z * dpr; blitFloor(p, r.L, s, r.x0, r.y0, 0); }
        polyFloors(fl); g.stroke();
      }
    }
    return;
  }
  // line / word / glyph: floors one by one, ledge at each setback
  for (const S of p.stanzas) {
    if (S !== p.stanzas[0] && S.lines.length) {
      const L0 = S.lines[0], f = floorWorld(b, L0);
      g.fillStyle = TH.ink2; g.fillRect(b.cx - L0.w / 2 - 8, f.y0 - 7, L0.w + 16, 4);
    }
    for (const L of S.lines) {
      const f = floorWorld(b, L);
      if (f.y0 > cull.y1 || f.y0 + FH < cull.y0 || f.x0 > cull.x1 || f.x0 + L.w < cull.x0) continue;
      if (unit === "line") {
        g.fillStyle = TH.sheet; g.fillRect(f.x0, f.y0, L.w, FH);
        SCR = z * dpr; blitFloor(p, L, wholeLine(L), f.x0, f.y0, 8);
        g.strokeRect(f.x0, f.y0, L.w, FH);
      } else {
        g.fillStyle = TH.wall; g.fillRect(f.x0, f.y0, L.w, FH); g.strokeRect(f.x0, f.y0, L.w, FH);
        const cells = unit === "word" ? L.words.map(w => w.box) : L.words.flatMap(w => w.glyphs).concat(L.marks);
        if (!cells.length) { g.fillStyle = TH.sheet; g.fillRect(f.x0, f.y0, L.w, FH); SCR = z * dpr; blitFloor(p, L, wholeLine(L), f.x0, f.y0, 8); continue; }
        const pad = unit === "word" ? 4 : 2;
        for (const cb of cells) {
          const s = subRect(L, cb); if (!s) continue;
          const dx = f.x0 + (s.box[0] - L.box[0]), dy = f.y0 + (FH - L.h) / 2 + (s.box[1] - L.box[1]);
          g.fillStyle = TH.sheet; g.fillRect(dx - pad, Math.max(f.y0 + 1, dy - pad), s.pw + 2 * pad, Math.min(FH - 2, s.ph + 2 * pad));
          SCR = z * dpr; blitFloor(p, L, s, f.x0, f.y0, 8, true);
          g.strokeRect(dx - pad, Math.max(f.y0 + 1, dy - pad), s.pw + 2 * pad, Math.min(FH - 2, s.ph + 2 * pad));
        }
      }
    }
  }
}
// blit a sub-rectangle of line L placed in its floor (floor-local offset = native, vertically centred), clipped to the floor +- ovf
function blitFloor(p, L, s, fx, fy, ovf, sub) {
  if (!s) return;
  let dx = fx + (s.box[0] - L.box[0]), dy = fy + (FH - L.h) / 2 + (s.box[1] - L.box[1]), dw = s.pw, dh = s.ph;
  let sx = s.sx, sy = s.sy, sw = s.sw, sh = s.sh;
  const k = sh / dh, lo = fy - ovf, hi = fy + FH + ovf;
  if (dy < lo) { const c = lo - dy; dy += c; dh -= c; sy += c * k; sh -= c * k; }
  if (dy + dh > hi) { const c = dy + dh - hi; dh -= c; sh -= c * k; }
  if (dh < 0.5 || sh < 0.5) return;
  blit(p, sx, sy, sw, sh, dx, dy, dw, dh);
}

let cull = { x0: 0, y0: 0, x1: 0, y1: 0 };
function drawArchitecture() {
  const z = cam.z;
  ctx.setTransform(dpr * z, 0, 0, dpr * z, dpr * (vw / 2 - cam.x * z), dpr * (vh / 2 - cam.y * z));
  cull = { x0: cam.x - vw / 2 / z - 10, x1: cam.x + vw / 2 / z + 10, y0: cam.y - vh / 2 / z - 10, y1: cam.y + vh / 2 / z + 10 };
  // ground line
  ctx.strokeStyle = TH.ink2; ctx.lineWidth = 1 / z; ctx.beginPath();
  const gx0 = Math.min(cull.x0, -BGAP), gx1 = Math.max(cull.x1, CITYW + BGAP);
  ctx.moveTo(Math.max(gx0, -BGAP * 2), 0); ctx.lineTo(Math.min(gx1, CITYW + BGAP * 2), 0); ctx.stroke();
  for (const b of CITYB) {
    if (b.x1 < cull.x0 || b.x0 > cull.x1 || 0 < cull.y0 || -b.H > cull.y1) continue;
    if (!b.p.ready) continue;
    drawBuilding(b, effUnit(b.p, FH * z));
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

// ------------------------------------------------------------------ spiral
let SP = { lines: null, pages: null };
function spiralPlace(items, spacing, r0, upright) {
  const b = spacing / (2 * Math.PI), r = th => r0 + b * th;
  const adv = (th, L) => { let t = th; while (L > 1e-6) { const rr = r(t), d = Math.min(0.04, L / rr); t += d; L -= d * rr; } return t; };
  let th = 0, path = [];
  for (const it of items) {
    const len = upright ? Math.max(it.w, it.h) * 1.06 : it.w * 1.04 + spacing * 0.12;
    const tc = adv(th, len / 2), tn = adv(th, len);
    it.x = r(tc) * Math.cos(tc); it.y = r(tc) * Math.sin(tc); it.ang = upright ? 0 : tc + Math.PI / 2;
    th = tn;
  }
  const R = r(th);
  for (let t = 0; t <= th + 0.1; t += 0.05) path.push([r(t) * Math.cos(t), r(t) * Math.sin(t)]);
  return { items, R: R + spacing * 2, path };
}
function buildSpiral() {
  const kl = CITY === "p001" ? 0.5 : 0.24;
  const li = [];
  for (const p of PIECES) for (const L of p.lines) li.push({ p, L, w: L.w * kl, h: L.h * kl, k: kl });
  const hmax = Math.max(...li.map(i => i.h));
  SP.lines = spiralPlace(li, hmax * 1.3, hmax * 4, false);
  SP.lk = kl;
  SP.pages = null;
}
function ensurePages() {
  if (SP.pages) return;
  const kp = CITY === "p001" ? 0.42 : 0.2, items = [];
  for (const p of PIECES) {
    if (!p.ready || !p.lines.length) continue;
    const bx0 = Math.min(...p.lines.map(l => l.box[0])), by0 = Math.min(...p.lines.map(l => l.box[1]));
    const bx1 = Math.max(...p.lines.map(l => l.box[2])), by1 = Math.max(...p.lines.map(l => l.box[3]));
    items.push({ p, bx0, by0, bx1, by1, w: (bx1 - bx0) * kp, h: (by1 - by0) * kp, k: kp });
  }
  const ts = CITY === "p001" ? 0.4 : 0.22;
  for (const it of items) {                                // tile canvas: sheet colour + only this piece's own line boxes
    const c = document.createElement("canvas"); c.width = Math.ceil((it.bx1 - it.bx0) * ts); c.height = Math.ceil((it.by1 - it.by0) * ts);
    const x = c.getContext("2d"); x.fillStyle = TH.sheet; x.fillRect(0, 0, c.width, c.height);
    x.imageSmoothingQuality = "high";
    const save = ctx;
    for (const L of it.p.lines) {
      const s = wholeLine(L); const r = (L.w * ts) / s.sw; const m = r < 0.34 ? it.p.mips[2] : r < 0.68 ? it.p.mips[1] : it.p.mips[0];
      x.drawImage(m.c, s.sx * m.k, s.sy * m.k, s.sw * m.k, s.sh * m.k, (L.box[0] - it.bx0) * ts, (L.box[1] - it.by0) * ts, L.w * ts, L.h * ts);
    }
    it.tile = c;
  }
  const maxd = Math.max(...items.map(i => Math.max(i.w, i.h)));
  SP.pages = spiralPlace(items, maxd * 1.12, maxd * 1.2, true);
}
function spiralSet() { if (SPUNIT === "page") { ensurePages(); return SP.pages; } return SP.lines; }
function spiralBox(s) {
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  for (const it of s.items) { const r = Math.hypot(it.w, it.h) / 2; x0 = Math.min(x0, it.x - r); y0 = Math.min(y0, it.y - r); x1 = Math.max(x1, it.x + r); y1 = Math.max(y1, it.y + r); }
  return { x0, y0, x1, y1, cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, w: x1 - x0, h: y1 - y0 };
}
function zFitSpiral() { const b = spiralBox(spiralSet()); return Math.min(vw * 0.9 / b.w, vh * 0.9 / b.h); }
function spiralLimits() { const zf = zFitSpiral(); return { zmin: zf * 0.6, zmax: Math.max(zf * 1.5, (CITY === "p001" ? 2.2 : 1.6) / (SPUNIT === "page" ? (CITY === "p001" ? 0.42 : 0.2) : SP.lk)) }; }
function fitSpiral() { const b = spiralBox(spiralSet()); scam.x = b.cx; scam.y = b.cy; scam.z = zFitSpiral(); }
function drawSpiral() {
  const s = spiralSet(), z = scam.z;
  ctx.setTransform(dpr * z, 0, 0, dpr * z, dpr * (vw / 2 - scam.x * z), dpr * (vh / 2 - scam.y * z));
  ctx.strokeStyle = TH.ink2; ctx.globalAlpha = 0.35; ctx.lineWidth = 1 / z; ctx.beginPath();
  s.path.forEach((q, i) => i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1])); ctx.stroke(); ctx.globalAlpha = 1;
  const x0 = scam.x - vw / 2 / z, x1 = scam.x + vw / 2 / z, y0 = scam.y - vh / 2 / z, y1 = scam.y + vh / 2 / z;
  for (const it of s.items) {
    const rad = Math.hypot(it.w, it.h) / 2;
    if (it.x + rad < x0 || it.x - rad > x1 || it.y + rad < y0 || it.y - rad > y1) continue;
    if (!it.p.ready) continue;
    ctx.save(); ctx.translate(it.x, it.y); ctx.rotate(it.ang);
    if (SPUNIT === "page") {
      ctx.fillStyle = TH.sheet; ctx.fillRect(-it.w / 2, -it.h / 2, it.w, it.h);
      ctx.imageSmoothingQuality = "high"; ctx.drawImage(it.tile, -it.w / 2, -it.h / 2, it.w, it.h);
    } else {
      SCR = z * dpr; const sr = wholeLine(it.L); ctx.fillStyle = TH.sheet; ctx.fillRect(-it.w / 2, -it.h / 2, it.w, it.h);
      blit(it.p, sr.sx, sr.sy, sr.sw, sr.sh, -it.w / 2, -it.h / 2, it.w, it.h);
    }
    ctx.restore();
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
function spiralHit(wx, wy) {
  const s = spiralSet();
  for (let i = s.items.length - 1; i >= 0; i--) {
    const it = s.items[i], dx = wx - it.x, dy = wy - it.y, c = Math.cos(-it.ang), n = Math.sin(-it.ang);
    const lx = dx * c - dy * n, ly = dx * n + dy * c;
    if (Math.abs(lx) <= it.w / 2 + 4 && Math.abs(ly) <= it.h / 2 + 4) return it;
  }
  return null;
}

// ------------------------------------------------------------------ reading + animation
function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
let PB = [40, 15, 1128, 1600];                            // p001 poem box; replaced by atoms-p001.json "box" at boot
let RG = null;                                            // reading geometry
function readingGeom() {
  const pw = PB[2] - PB[0], ph = PB[3] - PB[1];
  const colW = vw < 640 ? vw * 0.8 : Math.min(vw * 0.44, 640);
  const k = Math.min(colW / pw, vh * 0.84 / ph);
  const ox = (vw - pw * k) / 2, oy = (vh - ph * k) / 2, m = Math.max(22, 0.04 * Math.min(vw, vh));
  RG = { k, ox, oy, w: pw * k, h: ph * k, keep: { x0: ox - m, y0: oy - m, x1: ox + pw * k + m, y1: oy + ph * k + m } };
  return RG;
}
const sim = { rng: null, t: 0, n: 0, acc: 0, live: [], nseq: 0 };
function simReset() { sim.rng = mulberry32(SEED); sim.t = 0; sim.n = 0; sim.acc = 0; sim.live = []; sim.nseq = 0; }
const smooth = x => x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x);
function spawn() {
  const r = sim.rng, p = P001, K = RG.keep;
  const u = r(), kind = u < 0.18 ? "line" : u < 0.70 ? "word" : "glyph";
  let L, s, tag;
  if (kind === "line") { L = p.lines[Math.floor(r() * p.lines.length)]; s = wholeLine(L); }
  else { const arr = kind === "word" ? p.words : p.glyphs; const e = arr[Math.floor(r() * arr.length)]; L = e.ln; s = subRect(L, e.box); }
  if (!s) return;
  const ang = r() < 0.7 ? (r() + r() + r() - 1.5) * 0.9 : (r() * 2 - 1) * Math.PI;
  const rel = Math.min(1.3, Math.max(0.5, RG.k / 0.5));
  const sc0 = (kind === "line" ? 0.2 + r() * 0.35 : kind === "word" ? 0.5 + r() * 1.1 : 0.8 + r() * 2.4) * rel;
  const a0 = 0.12 + r() * 0.43, life = 5 + r() * 6;
  let placed = null;
  for (let tries = 0; tries < 12 && !placed; tries++) {
    const x = r() * vw, y = r() * vh;
    let sc = sc0;
    for (let j = 0; j < 7; j++) {
      const cs = Math.abs(Math.cos(ang)), sn = Math.abs(Math.sin(ang));      // half extents of the rotated sprite's bounding box
      const hx = (cs * s.pw + sn * s.ph) / 2 * sc, hy = (sn * s.pw + cs * s.ph) / 2 * sc;
      if (x + hx <= K.x0 || x - hx >= K.x1 || y + hy <= K.y0 || y - hy >= K.y1) { placed = { x, y, sc }; break; }
      sc *= 0.8;
    }
  }
  if (!s || !placed) return;
  sim.live.push({ kind, L, s, ang, sc: placed.sc, x: placed.x, y: placed.y, a0, born: sim.t, life, id: sim.nseq++ });
}
function simStep() {
  sim.n++; sim.t = sim.n / 30;
  sim.live = sim.live.filter(s => sim.t - s.born < s.life);
  const target = Math.round(CAP * smooth(sim.t / RAMP));
  for (let n = 0; n < 3 && sim.live.length < target; n++) spawn();
}
function simAdvance(dt) { sim.acc += dt; while (sim.acc >= DT) { sim.acc -= DT; simStep(); } }
function simTo(t) { readingGeom(); simReset(); const n = Math.round(t / DT); for (let i = 0; i < n; i++) simStep(); }
let frozen = T_PARAM !== null;
let simTarget = T_PARAM !== null ? T_PARAM : 0;           // time the sim should be at after a reset

function spriteAlpha(s) { const age = sim.t - s.born; const fin = Math.min(1, age / 0.7); const fo = age < s.life * 0.55 ? 1 : Math.max(0, (s.life - age) / (s.life * 0.45)); return s.a0 * fin * fo; }
function drawReading() {
  const g = ctx; g.setTransform(dpr, 0, 0, dpr, 0, 0);
  // animation in the dead space
  g.globalCompositeOperation = TH.dark ? "screen" : "multiply";
  for (const s of sim.live) {
    const a = spriteAlpha(s); if (a <= 0.002) continue;
    const c = Math.cos(s.ang) * s.sc, n = Math.sin(s.ang) * s.sc;
    g.globalAlpha = a; g.setTransform(dpr * c, dpr * n, -dpr * n, dpr * c, dpr * s.x, dpr * s.y);
    SCR = dpr * s.sc; blit(s.L.piece, s.s.sx, s.s.sy, s.s.sw, s.s.sh, -s.s.pw / 2, -s.s.ph / 2, s.s.pw, s.s.ph);
  }
  g.globalAlpha = 1; g.globalCompositeOperation = "source-over"; g.setTransform(dpr, 0, 0, dpr, 0, 0);
  // clear paper under the poem (nothing animates here)
  const m = 10;
  g.fillStyle = TH.sheet; g.fillRect(RG.ox - m, RG.oy - m, RG.w + 2 * m, RG.h + 2 * m);
  // the poem: each line crop at its native place in the poem box
  SCR = dpr * RG.k;
  for (const L of P001.lines) { const s = wholeLine(L); blit(P001, s.sx, s.sy, s.sw, s.sh, RG.ox + (L.box[0] - PB[0]) * RG.k, RG.oy + (L.box[1] - PB[1]) * RG.k, L.w * RG.k, L.h * RG.k); }
}

// ------------------------------------------------------------------ view control
let ready = false, raf = 0, last = 0, frames = 0, dirty = true;
const rmq = window.matchMedia("(prefers-reduced-motion: reduce)");
const reduced = () => rmq.matches;
function animating() { return ready && VIEW === "reading" && !reduced() && !frozen && !document.hidden; }
function schedule() { if (!raf) raf = requestAnimationFrame(tick); }
function tick(ts) {
  raf = 0; frames++;
  if (document.hidden) { last = 0; return; }
  const dt = last ? Math.min(0.1, (ts - last) / 1000) : 0; last = ts;
  if (animating()) simAdvance(dt); else last = 0;
  render();
  if (animating()) schedule();
}
function invalidate() { dirty = true; schedule(); }
function render() {
  dirty = false;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over";
  ctx.fillStyle = TH.desk; ctx.fillRect(0, 0, vw, vh);
  if (!ready) return;
  ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "medium";
  if (VIEW === "architecture") drawArchitecture(); else if (VIEW === "spiral") drawSpiral(); else drawReading();
}
function setView(v) {
  if (!VIEWS.includes(v) || v === VIEW) { return; }
  if (v === "reading") { PREV_VIEW = VIEW; }
  VIEW = v; selOpen = false; refreshSel();
  if (v === "reading") enterReading(); else if (v === "spiral") { if (!scam.z || scam.z === 1) fitSpiral(); }
  invalidate();
}
function enterReading() {
  readingGeom();
  simTo(reduced() ? REDUCED_T : frozen ? simTarget : 0);
  last = 0;
}
function openReading() { if (!P001 || !P001.ready) return; if (VIEW !== "reading") PREV_VIEW = VIEW; VIEW = "reading"; selOpen = false; refreshSel(); enterReading(); invalidate(); }
function leaveReading() { VIEW = PREV_VIEW === "reading" ? "architecture" : PREV_VIEW; refreshSel(); invalidate(); }

// ------------------------------------------------------------------ selector (hidden until tapped)
function refreshSel() {
  selEl.hidden = !selOpen || VIEW === "reading";
  if (selEl.hidden) return;
  const names = VIEW === "spiral" ? SPIRAL_UNITS : UNITS;
  const fp = VIEW === "architecture" ? Math.max(...PIECES.map(finest)) : 1;
  selEl.textContent = "";
  names.forEach((n, i) => {
    const b = document.createElement("button"); b.type = "button"; b.textContent = n; b.dataset.unit = n;
    const avail = VIEW === "spiral" || i <= fp;
    b.disabled = !avail;
    b.setAttribute("aria-pressed", String(VIEW === "spiral" ? SPUNIT === n : PIN === n));
    b.addEventListener("click", ev => { ev.stopPropagation(); if (VIEW === "spiral") setSpiralUnit(n); else setUnit(n); });
    selEl.appendChild(b);
  });
}
function toggleSel() { selOpen = !selOpen; if (!selOpen && VIEW === "architecture") PIN = null; refreshSel(); invalidate(); }
function setUnit(u) { if (u !== null && !UNITS.includes(u)) return; PIN = u; refreshSel(); invalidate(); }
function setSpiralUnit(u) { if (!SPIRAL_UNITS.includes(u)) return; SPUNIT = u; if (u === "page") ensurePages(); fitSpiral(); refreshSel(); invalidate(); }

// ------------------------------------------------------------------ input
const ptrs = new Map();
let tapInfo = null, lastEmptyTap = { t: 0, x: 0, y: 0 }, overZoom = 1;
function curCam() { return VIEW === "spiral" ? scam : cam; }
function limits() { return VIEW === "spiral" ? spiralLimits() : archLimits(); }
function zoomAt(f, sx, sy) {
  if (VIEW === "reading") return;
  const c = curCam(), L = limits(), zn = Math.min(L.zmax, Math.max(L.zmin, c.z * f));
  const wx = (sx - vw / 2) / c.z + c.x, wy = (sy - vh / 2) / c.z + c.y;
  if (VIEW === "architecture" && f > 1 && c.z >= L.zmax * 0.999 && zn >= L.zmax * 0.999) {
    overZoom *= f;                                        // pushing past the finest viable unit: opens READING for p001
    if (overZoom > 1.6) { const b = buildingAt(wx, wy); overZoom = 1; if (b && b.p.id === "p001") return openReading(); }
  } else if (f < 1) overZoom = 1;
  c.z = zn; c.x = wx - (sx - vw / 2) / zn; c.y = wy - (sy - vh / 2) / zn; clampCam(); invalidate();
}
function clampCam() {
  if (VIEW === "architecture") { cam.x = Math.min(CITYW + BGAP, Math.max(-BGAP, cam.x)); cam.y = Math.min(CITYH * 0.6, Math.max(-CITYH * 1.2, cam.y)); }
  else { const b = spiralBox(spiralSet()); scam.x = Math.min(b.x1, Math.max(b.x0, scam.x)); scam.y = Math.min(b.y1, Math.max(b.y0, scam.y)); }
}
function buildingAt(wx, wy) { return CITYB.find(b => wx >= b.x0 - 6 && wx <= b.x1 + 6 && wy <= 6 && wy >= -b.H - 6) || null; }
function tapAt(x, y) {
  if (VIEW === "reading") {
    const K = RG.keep; if (x < K.x0 || x > K.x1 || y < K.y0 || y > K.y1) leaveReading(); return;
  }
  const c = curCam(), wx = (x - vw / 2) / c.z + c.x, wy = (y - vh / 2) / c.z + c.y;
  let hit = null;
  if (VIEW === "architecture") {
    const b = buildingAt(wx, wy);
    if (b) { if (b.p.id === "p001") return openReading(); const z = Math.min(vw * 0.88 / b.W, vh * 0.84 / b.H, archLimits().zmax); cam.z = z; cam.x = b.cx; cam.y = -b.H / 2; clampCam(); return invalidate(); }
  } else {
    hit = spiralHit(wx, wy);
    if (hit) { if (hit.p.id === "p001") return openReading(); const b = hit.p.bld; PREV_VIEW = "architecture"; VIEW = "architecture"; cam.z = Math.min(vw * 0.88 / b.W, vh * 0.84 / b.H, archLimits().zmax); cam.x = b.cx; cam.y = -b.H / 2; clampCam(); refreshSel(); return invalidate(); }
  }
  // empty space: second tap quickly after the first switches architecture <-> spiral; a single tap toggles the selector
  const now = performance.now(), dbl = now - lastEmptyTap.t < 320 && Math.hypot(x - lastEmptyTap.x, y - lastEmptyTap.y) < 40;
  lastEmptyTap = { t: dbl ? 0 : now, x, y };
  if (dbl) { toggleSel(); setView(VIEW === "architecture" ? "spiral" : "architecture"); }
  else toggleSel();
}
cv.addEventListener("pointerdown", e => {
  cv.setPointerCapture(e.pointerId);
  ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY });
  tapInfo = ptrs.size === 1 ? { t: performance.now(), moved: 0 } : null;
});
cv.addEventListener("pointermove", e => {
  const p = ptrs.get(e.pointerId); if (!p) return;
  const dx = e.clientX - p.x, dy = e.clientY - p.y;
  if (ptrs.size === 1) {
    if (tapInfo) tapInfo.moved = Math.max(tapInfo.moved, Math.hypot(e.clientX - p.sx, e.clientY - p.sy));
    if (VIEW !== "reading" && (!tapInfo || tapInfo.moved > 6)) { const c = curCam(); c.x -= dx / c.z; c.y -= dy / c.z; clampCam(); invalidate(); }
  } else if (ptrs.size === 2) {
    const o = [...ptrs.values()], d0 = Math.hypot(o[0].x - o[1].x, o[0].y - o[1].y);
    p.x = e.clientX; p.y = e.clientY;
    const o2 = [...ptrs.values()], d1 = Math.hypot(o2[0].x - o2[1].x, o2[0].y - o2[1].y);
    if (d0 > 0 && d1 > 0) zoomAt(d1 / d0, (o2[0].x + o2[1].x) / 2, (o2[0].y + o2[1].y) / 2);
    return;
  }
  p.x = e.clientX; p.y = e.clientY;
});
function endPtr(e, cancelled) {
  const p = ptrs.get(e.pointerId); if (!p) return;
  const single = ptrs.size === 1; ptrs.delete(e.pointerId);
  if (single && tapInfo && !cancelled && tapInfo.moved <= 6 && performance.now() - tapInfo.t < 450) tapAt(e.clientX, e.clientY);
  if (!ptrs.size) tapInfo = null;
}
cv.addEventListener("pointerup", e => endPtr(e, false));
cv.addEventListener("pointercancel", e => endPtr(e, true));
cv.addEventListener("wheel", e => { e.preventDefault(); const f = Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0016) * (e.deltaMode === 1 ? 16 : 1)); zoomAt(f, e.clientX, e.clientY); }, { passive: false });
document.getElementById("hot").addEventListener("click", () => { if (VIEW !== "reading") toggleSel(); });
window.addEventListener("keydown", e => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key;
  if (k === "Escape") {
    if (selOpen) { selOpen = false; if (VIEW === "architecture") PIN = null; refreshSel(); invalidate(); }
    else if (PIN && VIEW === "architecture") { PIN = null; invalidate(); }
    else if (VIEW === "reading") leaveReading();
  } else if (k === "s" || k === "S") { if (VIEW !== "reading") toggleSel(); }
  else if (k === "a") setView("architecture"); else if (k === "b") setView("spiral");
  else if (k === "Enter") openReading();
  else if (k === "+" || k === "=") zoomAt(1.25, vw / 2, vh / 2); else if (k === "-") zoomAt(0.8, vw / 2, vh / 2);
});
document.addEventListener("visibilitychange", () => { last = 0; if (!document.hidden) invalidate(); });
rmq.addEventListener && rmq.addEventListener("change", () => { if (VIEW === "reading") enterReading(); invalidate(); });
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => themeChanged());
function themeChanged() { readTheme(); for (const p of PIECES) if (p.atlas) recolor(p); SP.pages = null; invalidate(); }

function resize() {
  dpr = Math.min(2, window.devicePixelRatio || 1);
  vw = window.innerWidth; vh = window.innerHeight;
  cv.width = Math.round(vw * dpr); cv.height = Math.round(vh * dpr);
  if (ready) {
    if (VIEW === "reading") { const t = sim.t; readingGeom(); simTo(reduced() ? REDUCED_T : t); }
  }
  invalidate();
}
window.addEventListener("resize", resize);

// ------------------------------------------------------------------ hooks
function spriteList() { return sim.live.map(s => ({ piece: s.L.piece.id, source: s.kind, blockId: s.L.b, lineIndex: s.L.l })); }
window.__alive = {
  ready: false,
  setView(v) { setView(v); render(); return VIEW; },
  setUnit(u) { setUnit(u); render(); return PIN; },
  setSpiralUnit(u) { setSpiralUnit(u); render(); return SPUNIT; },
  setTime(t) { frozen = true; simTarget = Math.max(0, +t || 0); if (P001 && P001.ready) { readingGeom(); simTo(simTarget); } invalidate(); render(); return sim.t; },
  state() {
    const c = curCam(), l = spriteList(), by = { line: 0, word: 0, glyph: 0 };
    l.forEach(s => by[s.source]++);
    const b0 = VIEW === "architecture" ? (CITYB.slice().sort((a, b) => Math.abs(a.cx - cam.x) - Math.abs(b.cx - cam.x))[0]) : null;
    const fh = FH * cam.z;
    return {
      view: VIEW, city: CITY, pinned: VIEW === "spiral" ? null : PIN,
      unit: VIEW === "spiral" ? SPUNIT : VIEW === "architecture" ? (b0 ? effUnit(b0.p, fh) : null) : "line",
      zoom: c.z, floorPx: fh, cam: { x: c.x, y: c.y, z: c.z },
      selectorOpen: selOpen && VIEW !== "reading", time: sim.t, frozen, reduced: reduced(), animating: animating(), frames, dark: TH.dark,
      sprites: l, spriteCount: l.length, spriteSources: by, keepOut: RG ? RG.keep : null, viewport: { w: vw, h: vh, dpr },
      pieces: PIECES.length, readyPieces: PIECES.filter(p => p.ready).length, failed: failed.slice(),
    };
  },
  sourcesUsed() { return [...new Set(sim.live.map(s => s.L.id))].sort(); },
  spriteGeoms() {                                         // crop box (page px) and the sprite's rotated screen AABB
    return sim.live.map(s => {
      const c = Math.abs(Math.cos(s.ang)), n = Math.abs(Math.sin(s.ang)), hx = (c * s.s.pw + n * s.s.ph) / 2 * s.sc, hy = (n * s.s.pw + c * s.s.ph) / 2 * s.sc;
      return { source: s.kind, line: s.L.id, page: s.L.piece.page, crop: s.s.box, lineBox: s.L.box, aabb: [s.x - hx, s.y - hy, s.x + hx, s.y + hy] };
    });
  },
  regionsRead() { return READS.slice(); },
  // per p001 line: atlas pixels with non-zero alpha outside the line's region (must be 0), those inside, and how many
  // ink pixels the region clip removed from the glyph-box mask (the partition's own cut, not a leak)
  atlasLeak() {
    const p = P001; if (!p || !p.ready) return null;
    return p.lines.map(L => {
      let outside = 0, inside = 0; const aw = p.atlas.width;
      for (let yy = 0; yy < L.ah; yy++) for (let xx = 0; xx < L.aw; xx++) {
        if (!p.master[(L.ay + yy) * aw + L.ax + xx]) continue;
        if (L.rmask && !L.rmask[yy * L.aw + xx]) outside++; else inside++;
      }
      return { id: L.id, region: !!L.region, outside, inside, clipRemoved: L.clip ? L.clip.inkBefore - L.clip.inkAfter : null };
    });
  },
  lineRegions() { return P001 ? P001.lines.map(L => ({ id: L.id, box: L.box.slice(), region: L.region ? L.region.map(q => q.slice()) : null })) : null; },
  allowedBoxes() { const o = {}; ALLOWED.forEach((v, k) => { o[k] = v.length; }); return o; },
  zoomToFloorPx(fh, wx) { cam.z = Math.min(archLimits().zmax, Math.max(archLimits().zmin, fh / FH)); if (wx !== undefined) cam.x = wx; clampCam(); invalidate(); render(); return cam.z; },
  setCamera(x, y, z) { const c = curCam(); c.x = x; c.y = y; c.z = z; clampCam(); invalidate(); render(); },
  focus(id) { const b = CITYB.find(q => q.p.id === id); if (!b) return false; cam.x = b.cx; cam.y = -b.H / 2; cam.z = Math.min(vw * 0.88 / b.W, vh * 0.84 / b.H); invalidate(); render(); return true; },
  fit() { if (VIEW === "spiral") fitSpiral(); else fitArch(); invalidate(); render(); },
  buildings() { return CITYB.map(b => ({ id: b.p.id, x0: b.x0, x1: b.x1, h: b.H, lines: b.p.lines.length })); },
  tap(x, y) { tapAt(x, y); render(); },
  render() { render(); },
};

// ------------------------------------------------------------------ boot
async function boot() {
  readTheme();
  resize();
  const j = async u => { const r = await fetch(u, { cache: "no-store" }); if (!r.ok) throw new Error(u + " " + r.status); return r.json(); };
  const [atoms, rules] = await Promise.all([j("/atoms-p001.json"), j("/rules-diary1.json")]);
  RULES = rules;
  P001 = pieceFromAtoms(atoms);
  if (Array.isArray(atoms.box) && atoms.box.length === 4) PB = atoms.box.slice();
  if (CITY === "p001") PIECES = [P001];
  else {
    const city = await j("/city-all58.json");
    PIECES = city.pieces.map(c => c.id === "p001" ? P001 : pieceFromCity(c));
  }
  layoutBuildings();
  fitArch();
  buildSpiral();
  fitSpiral();
  refreshSel();
  // p001 first (it is the only piece with reading content), then the rest, two at a time
  await buildPiece(P001).catch(e => failed.push("p001:" + e.message));
  ready = CITY === "p001";
  invalidate();
  if (CITY === "all58") {
    const rest = PIECES.filter(p => p !== P001);
    let i = 0;
    const worker = async () => { while (i < rest.length) { const p = rest[i++]; try { await buildPiece(p); } catch (e) { failed.push(p.id + ":" + e.message); } invalidate(); } };
    ready = true;                                         // views render with what exists; pieces appear as they finish
    await Promise.all([worker(), worker()]);
  }
  if (VIEW === "reading") { PREV_VIEW = "architecture"; enterReading(); }
  else if (T_PARAM !== null) { readingGeom(); simTo(simTarget); }
  if (VIEW === "spiral" && SPUNIT === "page") { SP.pages = null; ensurePages(); fitSpiral(); }
  invalidate();
  render();
  window.__alive.ready = true;
  document.body.dataset.ready = "1";
}
boot().catch(e => { failed.push("boot:" + e.message); window.__alive.error = e.message; document.body.dataset.error = "1"; });
})();
