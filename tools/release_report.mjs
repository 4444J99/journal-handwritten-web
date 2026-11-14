#!/usr/bin/env node
// A private, self-contained HTML page that shows tools/release_readiness.mjs output where the owner
// reads it: per piece, what blocks a release, which Studio step clears it, and a page-by-page review
// queue. Read-only: it assesses an export with the Studio's own gates and writes one local HTML file.
// No network, no Cloudflare credentials, no build, no upload, no deploy.
//
//   python3 studio-cf/prepare_publish.py --out /scratch/prepared
//   node tools/release_report.mjs --prepared /scratch/prepared --db exports/studio-db-2026-11-05 \
//        --pieces p002,p003,p004,p005 --out readiness-report/index.html
//
// The page carries line text from unpublished pieces, so it is private: --out must be outside the
// repository or git-ignored (readiness-report/ is), and the page says noindex.
import {readFileSync, writeFileSync, mkdirSync, realpathSync, existsSync} from 'node:fs';
import {join, dirname, resolve, relative, isAbsolute, basename} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {assess, loadDb, summarize, reviewProgress} from './release_readiness.mjs';

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

// Page-by-page review state of one piece: every page any of its versions touches, with how many of
// the lines the versions use are confirmed or corrected, and the first line still waiting.
export function reviewQueue(source, db, pid) {
  const item = source.review.items.find(i => i.id === pid);
  if (!item) return [];
  const pages = new Map(source.review.pages.map(p => [p.id, p]));
  const order = [], by = new Map();
  for (const v of item.versions) {
    const pg = pages.get(v.page);
    if (!pg) continue;
    if (!by.has(v.page)) { by.set(v.page, {page: v.page, seen: new Set(), lines: 0, confirmed: 0, corrected: 0, next: null, nextId: null}); order.push(v.page); }
    const row = by.get(v.page);
    for (const b of v.blocks) for (const l of pg.blocks[b]?.lines || []) {
      if (row.seen.has(l.id)) continue;
      row.seen.add(l.id); row.lines++;
      const r = db.reviews[l.id];
      // A review of text that has since changed no longer counts: the gate stops it as stale_transcript.
      const fresh = r && r.original === (l.tx ?? '');
      if (fresh && r.status === 'confirmed') row.confirmed++;
      else if (fresh && r.status === 'corrected' && typeof r.text === 'string') row.corrected++;
      else if (row.next === null) { row.next = l.tx ?? ''; row.nextId = l.id; }
    }
  }
  return order.map(p => { const {seen, ...rest} = by.get(p); return {...rest, waiting: rest.lines - rest.confirmed - rest.corrected}; });
}

// Ordered by how much owner effort each step costs, so the cheapest blockers read first.
const STEP_ORDER = ['series', 'own_pool_not_series', 'filed', 'shared_scan', 'stale_transcript', 'conflicting_final_decisions', 'verified', 'name_leak', 'invalid_shell', 'unknown_piece'];
const stepRank = n => { const i = STEP_ORDER.indexOf(n.split(':')[0]); return i < 0 ? STEP_ORDER.length : i; };

export function plan(rows) {
  const steps = new Map();
  for (const r of rows) for (const b of r.blockers || []) {
    // One step per complete blocker name: shared_scan:p8 and shared_scan:p11 need different actions.
    if (!steps.has(b.name)) steps.set(b.name, {name: b.name, advice: b.advice, pieces: []});
    steps.get(b.name).pieces.push(r.piece);
  }
  return [...steps.values()].sort((a, b) => stepRank(a.name) - stepRank(b.name));
}

export function renderHtml({rows, queues, meta}) {
  const s = summarize(rows);
  const pct = (a, b) => b ? Math.round(100 * a / b) : 0;
  const cards = rows.map(r => {
    const p = r.review, done = p.confirmed + p.corrected;
    const q = (queues[r.piece] || []);
    return `<article class="card ${r.ready ? 'ok' : 'stop'}" id="${esc(r.piece)}">
<header><h3>${esc(r.piece)} <span class="first">${esc(r.first)}</span></h3><span class="badge">${r.ready ? 'Ready' : 'Blocked'}</span></header>
<p class="meta">pool ${esc(r.pool ?? 'unset')} · ${r.versions} version${r.versions === 1 ? '' : 's'}${r.how ? ' · publishes ' + esc(r.how) : ''}</p>
<div class="bar" role="img" aria-label="${done} of ${p.lines} lines reviewed"><i style="width:${pct(done, p.lines)}%"></i></div>
<p class="meta">${done}/${p.lines} lines reviewed${p.corrected ? `, ${p.corrected} corrected` : ''}</p>
${r.blockers.length ? '<ul class="blockers">' + r.blockers.map(b => `<li><code>${esc(b.name)}</code>${b.detail ? ' <span class="detail">' + esc(b.detail) + '</span>' : ''}<br>${esc(b.advice)}</li>`).join('') + '</ul>' : '<p>Every gate passes for this export.</p>'}
${(r.warnings || []).map(w => `<p class="warn">${esc(w)}</p>`).join('')}
${q.length ? `<table><thead><tr><th>Page</th><th>Reviewed</th><th>Next line waiting</th></tr></thead><tbody>${q.map(x => `<tr><td>${esc(x.page)}</td><td>${x.confirmed + x.corrected}/${x.lines}</td><td>${x.next === null ? 'none' : esc(x.next || '(blank line)')}</td></tr>`).join('')}</tbody></table>` : ''}
</article>`;
  }).join('\n');
  const steps = plan(rows).map(st => `<li><strong>${esc(st.advice)}</strong><br><span class="detail">${esc(st.name)}: ${st.pieces.map(esc).join(', ')}</span></li>`).join('');
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Release readiness</title>
<style>
:root{--bg:#f6f3ec;--fg:#1d1b17;--mut:#6b665c;--line:#d8d2c4;--card:#fffdf8;--ok:#2d6a3e;--stop:#9a3b2a}
@media (prefers-color-scheme:dark){:root{--bg:#16140f;--fg:#ece7da;--mut:#a29c8c;--line:#38342a;--card:#1d1a14;--ok:#7bbf8e;--stop:#e08a76}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif;padding:24px 16px}
main{max-width:860px;margin:0 auto}h1{font-size:1.4rem;margin:0 0 4px}h2{font-size:1.1rem;margin:28px 0 8px}h3{font-size:1.05rem;margin:0}
.meta,.detail,.note{color:var(--mut);font-size:.9rem;margin:4px 0}.first{font-weight:400;color:var(--mut)}
.card{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--stop);border-radius:6px;padding:12px 14px;margin:12px 0}
.card.ok{border-left-color:var(--ok)}.card header{display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.badge{font-size:.8rem;border:1px solid currentColor;border-radius:99px;padding:0 8px;color:var(--stop)}.ok .badge{color:var(--ok)}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden;margin:6px 0}.bar i{display:block;height:100%;background:var(--ok)}
.blockers{padding-left:18px;margin:8px 0}.blockers li{margin:6px 0}.warn{color:var(--stop);font-size:.9rem}
table{width:100%;border-collapse:collapse;font-size:.9rem;margin-top:8px}th,td{text-align:left;padding:4px 6px;border-top:1px solid var(--line);vertical-align:top}
ol.plan{padding-left:20px}ol.plan li{margin:8px 0}code{font-size:.85rem}
</style></head><body><main>
<h1>Release readiness</h1>
<p class="note">${s.ready} of ${s.pieces} pieces pass every gate for a ${esc(meta.target)} release. Private page: it shows line text from unpublished pieces. It describes the export <code>${esc(meta.db)}</code>, not the live database, and publishes nothing.</p>
${s.pieces - s.ready ? `<h2>What to do next, cheapest first</h2><ol class="plan">${steps}</ol>` : ''}
<h2>Pieces</h2>
${cards}
<p class="note">Generated by tools/release_report.mjs with the Studio's own publish gates. Gates are never forced and shared scans are never accepted here.</p>
</main></body></html>
`;
}

// The page holds private line text. Refuse any destination inside the repository that git would track.
export function checkOutputPath(out, repoRoot) {
  // Resolve symlinks through the deepest existing ancestor (and the file itself if it exists), because
  // writeFileSync follows them: an outside path that links into the repository is a repository path.
  const lexical = resolve(out), tail = [];
  let probe = lexical;
  while (!existsSync(probe) && dirname(probe) !== probe) { tail.unshift(basename(probe)); probe = dirname(probe); }
  const abs = join(realpathSync(probe), ...tail);
  repoRoot = realpathSync(repoRoot);
  const rel = relative(repoRoot, abs);
  if (rel.startsWith('..') || isAbsolute(rel)) return {ok: true};
  const ignored = spawnSync('git', ['-C', repoRoot, 'check-ignore', '-q', '--', abs]).status === 0;
  return ignored ? {ok: true} : {ok: false, reason: `${rel} is inside the repository and not git-ignored; use readiness-report/ or a path outside it`};
}

function parseArgs(argv) {
  const a = {pieces: null, target: 'staging', limit: 12};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i], v = () => { if (i + 1 >= argv.length) throw new Error(`${k} needs a value`); return argv[++i]; };
    if (k === '--prepared') a.prepared = v();
    else if (k === '--db') a.db = v();
    else if (k === '--pieces') a.pieces = v().split(',').filter(Boolean);
    else if (k === '--target') a.target = v();
    else if (k === '--limit') a.limit = Number(v());
    else if (k === '--out') a.out = v();
    else if (k === '--help' || k === '-h') a.help = true;
    else throw new Error('unknown argument ' + k);
  }
  return a;
}

async function main() {
  const a = parseArgs(process.argv.slice(2));
  if (a.help || !a.prepared || !a.db || !a.out) {
    process.stderr.write('usage: release_report.mjs --prepared DIR --db EXPORT_DIR --out FILE.html [--pieces p002,p003] [--target staging|production] [--limit N]\n');
    return a.help ? 0 : 2;
  }
  if (!['staging', 'production'].includes(a.target)) throw new Error('--target must be staging or production');
  const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const guard = checkOutputPath(a.out, repoRoot);
  if (!guard.ok) throw new Error(guard.reason);
  const source = JSON.parse(readFileSync(join(a.prepared, 'source.json'), 'utf8'));
  const shell = readFileSync(join(a.prepared, 'shell.html'), 'utf8');
  const db = loadDb(a.db);
  const all = source.j.pieces.map(p => p.id);
  const touched = new Set(Object.keys(db.release));
  for (const b of Object.values(db.batches)) for (const id of Array.isArray(b.items) ? b.items : []) touched.add(id);
  for (const id of all) { const p = reviewProgress(source, db, id); if (p.confirmed + p.corrected > 0) touched.add(id); }
  const pieces = a.pieces || [...new Set([...all.filter(id => touched.has(id)), ...all])].slice(0, Math.max(a.limit, touched.size));
  const rows = await assess({source, shell, db, pieces, target: a.target});
  const queues = Object.fromEntries(pieces.map(id => [id, reviewQueue(source, db, id)]));
  mkdirSync(dirname(resolve(a.out)), {recursive: true});
  writeFileSync(a.out, renderHtml({rows, queues, meta: {target: a.target, db: basename(resolve(a.db))}}));
  process.stdout.write(`wrote ${a.out}: ${summarize(rows).ready}/${rows.length} pieces ready for ${a.target}\n`);
  return 0;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().then(code => { process.exitCode = code; }, e => { process.stderr.write(String(e.message || e) + '\n'); process.exitCode = 2; });
}
