#!/usr/bin/env node
// What stands between each piece and a staging/production release, computed by the Studio's own
// compiler gates (studio/publish-compiler.mjs buildCandidate), offline, from a database export.
//
//   python3 studio-cf/prepare_publish.py --out /scratch/prepared        # once per source change
//   node tools/release_readiness.mjs --prepared /scratch/prepared --db exports/studio-db-2026-11-05
//   node tools/release_readiness.mjs --prepared P --db D --pieces p002,p003,p004,p005 --json out.json
//   node tools/release_readiness.mjs ... --require p002,p003   # exit 1 unless these are releasable
//
// Reads only. Nothing is built, uploaded, published or written except the optional --json file.
// --db is the COLLECTION/ID.json layout written by studio-cf/export_db.py (Studio data) or
// exports/studio-db-*. Missing collections count as empty. The report states the gate results of
// the export it was given; it is not evidence of the live database.
import {readFileSync, readdirSync, existsSync, writeFileSync, statSync} from 'node:fs';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildCandidate} from '../studio/publish-compiler.mjs';

const COLLECTIONS = ['reviews', 'decisions', 'versions', 'release', 'batches', 'rconfig', 'parts', 'composites', 'notes'];
const required = ['release', 'reviews', 'batches', 'decisions', 'versions', 'rconfig'];

export function loadDb(dir) {
  const db = Object.fromEntries(COLLECTIONS.map(c => [c, {}]));
  for (const c of COLLECTIONS) {
    const d = join(dir, c);
    if (!existsSync(d) || !statSync(d).isDirectory()) continue;
    for (const f of readdirSync(d).filter(f => f.endsWith('.json')).sort()) db[c][f.slice(0, -5)] = JSON.parse(readFileSync(join(d, f), 'utf8'));
  }
  for (const c of required) db[c] ||= {};
  return db;
}

// Human next step for each way a gate can fail. Unknown names are shown verbatim.
export function advice(name) {
  if (name === 'series') return 'Sort the piece into Series (Studio, Release tab)';
  if (name === 'own_pool_not_series') return 'Its pool is not Series (Reserve/Archive stop a release); move it to Series or leave it out';
  if (name === 'verified') return 'Read each page and confirm or correct every line (Studio, Review tab)';
  if (name === 'filed') return 'File it in a GRUW batch, or record the gruw-policy decision "skip"';
  if (name === 'alt_text') return 'Give every published page image an alt label (the reader derives it from the page id; a blank label or a shell without the alt template blocks the release)';
  if (name === 'note_anchors') return 'Rebind the note anchor to a line in the chosen version (Studio, Notes)';
  if (name === 'links') return 'Fix the link in the piece text or note (it must be a well-formed http(s) URL)';
  if (name.startsWith('shared_scan:')) {
    const id = name.slice(12);
    return /^p[0-9]+$/.test(id)
      ? `Its scan is shared with piece ${id}: release ${id} too (Series), or accept the shared scan`
      : `Its scan also carries other lines (${id}): accept the shared scan once you have looked at them`;
  }
  if (name.startsWith('stale_transcript:')) return `Transcript changed after review of ${name.slice(17)}: re-confirm that line`;
  if (name === 'conflicting_final_decisions') return 'Two decided finals disagree: keep one';
  if (name === 'name_leak' || name === 'invalid_shell') return 'Build problem in the prepared shell; re-run prepare_publish.py';
  return name;
}

export function reviewProgress(source, db, pid) {
  const item = source.review.items.find(i => i.id === pid);
  if (!item) return {lines: 0, confirmed: 0, corrected: 0};
  const pages = new Map(source.review.pages.map(p => [p.id, p]));
  const lines = new Map();
  for (const v of item.versions) for (const b of v.blocks) for (const l of pages.get(v.page)?.blocks[b]?.lines || []) lines.set(l.id, l.tx ?? '');
  let confirmed = 0, corrected = 0;
  for (const [id, tx] of lines) {
    const r = db.reviews[id];
    if (r?.original !== tx) continue; // reviewed text has since changed: the gate stops it as stale_transcript
    if (r.status === 'confirmed') confirmed++;
    else if (r.status === 'corrected' && typeof r.text === 'string') corrected++;
  }
  return {lines: lines.size, confirmed, corrected};
}

export async function assess({source, shell, db, pieces, target = 'staging'}) {
  const out = [];
  for (const pid of pieces) {
    const pc = source.j.pieces.find(p => p.id === pid);
    const first = source.review.items.find(i => i.id === pid)?.first ?? '';
    const prog = reviewProgress(source, db, pid);
    const base = {piece: pid, first, pool: db.release[pid]?.pool ?? null, versions: pc?.V.length ?? 0, review: prog};
    if (!pc) { out.push({...base, ready: false, blockers: [{name: 'unknown_piece', advice: 'Not in the source'}]}); continue; }
    // Never force and never accept shared scans here: the report shows what is stopped, not what could be overridden.
    const r = await buildCandidate({source, db, shell, pieces: [pid], target});
    const failed = r.gates.filter(g => !g.ok).map(g => ({name: g.name, detail: g.detail || ''}));
    const stops = r.stops.map(s => ({name: s.name, detail: ''}));
    const seen = new Set(), blockers = [];
    for (const b of [...failed, ...stops]) {
      const k = b.name; if (seen.has(k)) continue; seen.add(k);
      blockers.push({...b, advice: advice(b.name)});
    }
    out.push({...base, how: r.versions[pid]?.how ?? null, chosen: r.versions[pid]?.indices ?? null, warnings: r.warnings, ready: !r.blocked, blockers});
  }
  return out;
}

export function summarize(rows) {
  const by = {};
  for (const r of rows) for (const b of r.blockers || []) by[b.name.split(':')[0]] = (by[b.name.split(':')[0]] || 0) + 1;
  return {pieces: rows.length, ready: rows.filter(r => r.ready).length, blockedBy: by};
}

export function format(rows, {detail = true} = {}) {
  const lines = [];
  const s = summarize(rows);
  lines.push(`${s.ready}/${s.pieces} pieces pass every gate for a staging release`);
  const keys = Object.keys(s.blockedBy).sort((a, b) => s.blockedBy[b] - s.blockedBy[a]);
  if (keys.length) lines.push('blocked by: ' + keys.map(k => `${k} x${s.blockedBy[k]}`).join(', '));
  for (const r of rows) {
    const p = r.review;
    lines.push('', `${r.piece}  ${r.ready ? 'READY' : 'blocked'}  "${r.first}"  pool=${r.pool ?? 'unset'}  lines ${p.confirmed + p.corrected}/${p.lines} reviewed (${p.corrected} corrected)  versions ${r.versions}${r.how ? '  [' + r.how + ']' : ''}`);
    if (detail) {
      for (const b of r.blockers) lines.push(`    - ${b.name}${b.detail ? ' (' + b.detail + ')' : ''}: ${b.advice}`);
      for (const w of r.warnings || []) lines.push(`    ! ${w}`);
    }
  }
  return lines.join('\n') + '\n';
}

function parseArgs(argv) {
  const a = {pieces: null, require: [], detail: true, target: 'staging', limit: 12};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i], v = () => { if (i + 1 >= argv.length) throw new Error(`${k} needs a value`); return argv[++i]; };
    if (k === '--prepared') a.prepared = v();
    else if (k === '--db') a.db = v();
    else if (k === '--pieces') a.pieces = v().split(',').filter(Boolean);
    else if (k === '--require') a.require = v().split(',').filter(Boolean);
    else if (k === '--target') a.target = v();
    else if (k === '--json') a.json = v();
    else if (k === '--limit') a.limit = Number(v());
    else if (k === '--summary') a.detail = false;
    else if (k === '--help' || k === '-h') a.help = true;
    else throw new Error('unknown argument ' + k);
  }
  return a;
}

async function main() {
  const a = parseArgs(process.argv.slice(2));
  if (a.help || !a.prepared || !a.db) {
    process.stderr.write('usage: release_readiness.mjs --prepared DIR --db EXPORT_DIR [--pieces p002,p003] [--require p002] [--target staging|production] [--limit N] [--summary] [--json FILE]\n');
    return a.help ? 0 : 2;
  }
  if (!['staging', 'production'].includes(a.target)) throw new Error('--target must be staging or production');
  const source = JSON.parse(readFileSync(join(a.prepared, 'source.json'), 'utf8'));
  const shell = readFileSync(join(a.prepared, 'shell.html'), 'utf8');
  const db = loadDb(a.db);
  // Default: pieces with any review, any release record or any listing in a batch, then the first --limit by order.
  const touched = new Set(Object.keys(db.release));
  for (const b of Object.values(db.batches)) for (const id of Array.isArray(b.items) ? b.items : []) touched.add(id);
  const withReviews = source.review.items.filter(i => i.id.startsWith('p') && reviewProgress(source, db, i.id).confirmed + reviewProgress(source, db, i.id).corrected > 0).map(i => i.id);
  for (const id of withReviews) touched.add(id);
  const all = source.j.pieces.map(p => p.id);
  const pieces = a.pieces || [...new Set([...all.filter(id => touched.has(id)), ...all])].slice(0, Math.max(a.limit, touched.size));
  const rows = await assess({source, shell, db, pieces, target: a.target});
  process.stdout.write(format(rows, {detail: a.detail}));
  if (a.json) writeFileSync(a.json, JSON.stringify({target: a.target, summary: summarize(rows), pieces: rows}, null, 2) + '\n');
  const absent = a.require.filter(id => !rows.some(r => r.piece === id));
  if (absent.length) { process.stderr.write(`--require names pieces not assessed: ${absent.join(', ')}\n`); return 2; }
  const missing = a.require.filter(id => !rows.find(r => r.piece === id).ready);
  return missing.length ? 1 : 0;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().then(code => { process.exitCode = code; }, e => { process.stderr.write(String(e.message || e) + '\n'); process.exitCode = 2; });
}
