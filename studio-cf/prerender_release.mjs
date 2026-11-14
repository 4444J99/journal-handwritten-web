#!/usr/bin/env node
// Build-time pre-render of one release into a static Cloudflare Pages site.
//
// Why: the public reader (lib/public-reader.js) runs a Worker on every request: it reads the
// pointer, the manifest and the file from R2, parses JSON, and rewrites index.html. On the free
// plan every one of those invocations is held to the 10 ms CPU limit. A pre-rendered release has
// no Worker at all: the output directory holds only files, a `_headers` file and nothing under
// `functions/`, so Pages answers every request from its static asset store. Static asset
// requests do not invoke Pages Functions.
//
//   python3 studio-cf/prepare_publish.py --out /scratch/prepared
//   node studio-cf/prerender_release.mjs --prepared /scratch/prepared --db exports/studio-db-2026-11-05 \
//        --pieces p001 --target staging --out /scratch/static-release [--json report.json]
//
// The candidate comes from the Studio's own compiler (studio/publish-compiler.mjs buildCandidate), so
// every gate, stop, name-leak scan and public projection applies unchanged; a blocked candidate
// writes nothing. Reads only the prepared directory and the database export. Makes no network call
// and has no Cloudflare credential. It never deploys; deploying the output is a separate owner step.
import {readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync, lstatSync} from 'node:fs';
import {join, dirname, extname, resolve, posix} from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildCandidate, canonical, digest, encode, hasNameLeak, hasByteNameLeak} from '../studio/publish-compiler.mjs';

// Pages limits: 20,000 files per deployment, 25 MiB per file, 100 rules in _headers.
export const LIMITS = {files: 20000, fileBytes: 25 * 1024 * 1024, headerRules: 100};

const SAFE_PATH = /^(?:index\.html|data\/j\.json|reader-(?:features|packages)\.js|img\/[a-z]\/[A-Za-z0-9_.-]+\.jpg)$/;
// What Pages infers from the extension. A file whose real type differs needs a Content-Type rule.
const INFERRED = {'.html': 'text/html', '.json': 'application/json', '.js': 'text/javascript', '.jpg': 'image/jpeg'};
const baseType = t => String(t || '').split(';')[0].trim().toLowerCase();
const BASE_HEADERS = {
  'X-Robots-Tag': 'noindex',
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
  // Asset URLs such as img/a/t0.jpg name different bytes in different releases, so nothing may be
  // reused without revalidation. Pages revalidates static assets by ETag at no Worker cost.
  'Cache-Control': 'public, max-age=0, must-revalidate',
};

function fail(code, detail = '') { const e = new Error(detail ? `${code}: ${detail}` : code); e.code = code; return e; }

// Content-Type rules for files whose bytes are not what their extension suggests (the atlas
// tiles are lossless PNG bytes under .jpg routes). One splat rule per directory when every file
// there agrees, per-file rules otherwise; the total must fit Pages' 100 rule limit.
export function contentTypeRules(files) {
  const odd = files.filter(f => baseType(f.contentType) !== INFERRED[extname(f.path)]);
  const byDir = new Map();
  for (const f of files) {
    const dir = posix.dirname(f.path);
    if (!byDir.has(dir)) byDir.set(dir, []);
    byDir.get(dir).push(f);
  }
  const rules = new Map();
  const handled = new Set();
  for (const [dir, list] of byDir) {
    if (dir === '.') continue;
    const types = new Set(list.map(f => f.contentType));
    const allOdd = list.every(f => odd.includes(f));
    if (allOdd && types.size === 1) {
      rules.set(`/${dir}/*`, [...types][0]);
      for (const f of list) handled.add(f.path);
    }
  }
  for (const f of odd) if (!handled.has(f.path)) rules.set('/' + f.path, f.contentType);
  return rules;
}

export function headersFile(files) {
  const rules = contentTypeRules(files);
  if (rules.size + 1 > LIMITS.headerRules) throw fail('too_many_header_rules', `${rules.size + 1} > ${LIMITS.headerRules}`);
  let out = '/*\n' + Object.entries(BASE_HEADERS).map(([k, v]) => `  ${k}: ${v}\n`).join('');
  // Rules for more specific paths come later; Pages merges every matching rule.
  for (const [path, type] of [...rules].sort((a, b) => a[0].localeCompare(b[0]))) out += `${path}\n  Content-Type: ${type}\n`;
  return out;
}

// The release id is the digest of the sorted path/hash list, so the same release always
// pre-renders to the same id and a different release never shares one.
export async function releaseId(files) {
  return digest(canonical(files.map(f => ({path: f.path, sha256: f.sha256, size: f.size, contentType: f.contentType}))));
}

// candidate: result of buildCandidate (not blocked). readAsset(sourcePath) -> Uint8Array.
// Returns {id, entries:[{path,bytes,sha256,size,contentType}], headers}. Writes nothing.
export async function render(candidate, readAsset) {
  if (!candidate || candidate.blocked || !Array.isArray(candidate.files)) throw fail('candidate_blocked');
  if (candidate.files.length > LIMITS.files) throw fail('too_many_files');
  const entries = [];
  for (const f of candidate.files) {
    if (!SAFE_PATH.test(f.path) || f.path.includes('..')) throw fail('unsafe_path', f.path);
    const bytes = f.text !== undefined ? encode(f.text) : await readAsset(f.sourcePath || f.path);
    if (bytes.length > LIMITS.fileBytes) throw fail('file_too_large', f.path);
    if (bytes.length !== f.size || await digest(bytes) !== f.sha256) throw fail('asset_hash_mismatch', f.path);
    // The compiler scans text files itself; binary files get the byte scan the Python path uses.
    // Same split as lib/publish-api.js checked(): text-like content gets the decoding scan (JavaScript
    // escapes, entities, base64), only true binaries get the byte scan.
    const textLike = f.text !== undefined || /^(?:text\/|application\/(?:json|javascript))/i.test(f.contentType || '');
    if (textLike ? hasNameLeak(f.text !== undefined ? f.text : new TextDecoder().decode(bytes)) : hasByteNameLeak(bytes)) throw fail('name_leak', f.path);
    entries.push({path: f.path, bytes, sha256: f.sha256, size: f.size, contentType: f.contentType});
  }
  if (!entries.some(e => e.path === 'index.html')) throw fail('missing_index');
  const meta = entries.map(({path, sha256, size, contentType}) => ({path, sha256, size, contentType}));
  return {id: await releaseId(meta), entries, headers: headersFile(meta)};
}

// Writes the site. The directory must not exist or must be empty, so a stale file from an
// earlier release can never be deployed with this one.
export function write(rendered, outDir) {
  outDir = resolve(outDir);
  if (existsSync(outDir) && readdirSync(outDir).length) throw fail('output_not_empty', outDir);
  mkdirSync(outDir, {recursive: true});
  for (const e of rendered.entries) {
    const target = join(outDir, e.path);
    mkdirSync(dirname(target), {recursive: true});
    writeFileSync(target, e.bytes);
  }
  writeFileSync(join(outDir, '_headers'), rendered.headers);
  return outDir;
}

// Static check of a written site, independent of how it was produced: no Worker entry point, no
// Functions directory, nothing outside the manifest, every byte matches its recorded hash.
export async function verifySite(outDir, rendered) {
  outDir = resolve(outDir);
  const problems = [];
  const walk = (d, prefix = '') => readdirSync(d).flatMap(n => {
    const p = join(d, n), rel = prefix + n;
    return lstatSync(p).isDirectory() ? walk(p, rel + '/') : [rel];
  });
  const present = new Set(walk(outDir));
  for (const forbidden of ['_worker.js', '_routes.json', 'functions'])
    if (existsSync(join(outDir, forbidden))) problems.push('worker_entry_present:' + forbidden);
  const expected = new Set([...rendered.entries.map(e => e.path), '_headers']);
  for (const p of present) if (!expected.has(p)) problems.push('unexpected_file:' + p);
  for (const e of rendered.entries) {
    if (!present.has(e.path)) { problems.push('missing_file:' + e.path); continue; }
    if (await digest(readFileSync(join(outDir, e.path))) !== e.sha256) problems.push('hash_mismatch:' + e.path);
  }
  return problems;
}

// photosDir holds uploaded photo bytes named by asset id (the Studio keeps them in R2 `photos/`).
// Photographed composites cannot be pre-rendered without it; render() verifies each file's hash.
export async function loadPrepared(prepared, photosDir = null) {
  const source = JSON.parse(readFileSync(join(prepared, 'source.json'), 'utf8'));
  const shell = readFileSync(join(prepared, 'shell.html'), 'utf8');
  // The compiler's glyph-approval check trusts source.shellSha256; the bytes must match it.
  if (await digest(shell) !== source.shellSha256) throw fail('shell_hash_mismatch');
  const readAsset = async p => {
    const photo = /^photos\/([A-Za-z0-9_.-]+)$/.exec(p);
    if (photo) {
      if (!photosDir || photo[1].startsWith('.')) throw fail('photo_input_missing', p);
      return new Uint8Array(readFileSync(join(photosDir, photo[1])));
    }
    if (!source.assets[p] && !/^tiles\//.test(p)) throw fail('unknown_asset', p);
    return new Uint8Array(readFileSync(join(prepared, 'assets', p)));
  };
  return {source, shell, readAsset};
}

function parse(argv) {
  const a = {pieces: [], allVersions: [], accepted: [], target: 'staging'};
  const list = v => v.split(',').map(s => s.trim()).filter(Boolean);
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i], v = () => argv[++i];
    if (k === '--prepared') a.prepared = v();
    else if (k === '--db') a.db = v();
    else if (k === '--pieces') a.pieces = list(v());
    else if (k === '--all-versions') a.allVersions = list(v());
    else if (k === '--accept') a.accepted = list(v());
    else if (k === '--target') a.target = v();
    else if (k === '--photos') a.photos = v();
    else if (k === '--out') a.out = v();
    else if (k === '--json') a.json = v();
    else if (k === '--help' || k === '-h') a.help = true;
    else throw fail('bad_argument', k);
  }
  return a;
}

export async function main(argv) {
  const a = parse(argv);
  if (a.help || !a.prepared || !a.db || !a.out || !a.pieces.length) {
    process.stderr.write('usage: prerender_release.mjs --prepared DIR --db EXPORT_DIR --pieces p001[,p002] --out EMPTY_DIR [--target staging|production] [--all-versions p001] [--photos DIR] [--accept ID] [--json FILE]\n');
    return a.help ? 0 : 2;
  }
  const {loadDb} = await import('../tools/release_readiness.mjs');
  const {source, shell, readAsset} = await loadPrepared(a.prepared, a.photos);
  const db = loadDb(a.db);
  const candidate = await buildCandidate({source, db, shell, pieces: a.pieces, allVersions: a.allVersions, accepted: a.accepted, target: a.target});
  if (candidate.blocked) {
    const why = [...candidate.stops, ...candidate.gates.filter(g => !g.ok)].map(g => `${g.piece || '-'}:${g.name}`);
    process.stderr.write('blocked, nothing written: ' + why.join(', ') + '\n');
    return 1;
  }
  const rendered = await render(candidate, readAsset);
  const out = write(rendered, a.out);
  const problems = await verifySite(out, rendered);
  if (problems.length) { process.stderr.write('site check failed: ' + problems.join(', ') + '\n'); return 1; }
  const report = {id: rendered.id, pieces: candidate.pieces, target: a.target, files: rendered.entries.length,
    bytes: rendered.entries.reduce((n, e) => n + e.size, 0), workerEntryPoints: 0,
    manifest: rendered.entries.map(({path, sha256, size, contentType}) => ({path, sha256, size, contentType}))};
  if (a.json) writeFileSync(a.json, JSON.stringify(report, null, 2) + '\n');
  process.stdout.write(`pre-rendered ${report.files} files (${report.bytes} bytes), release ${report.id}, no Worker entry point -> ${out}\n`);
  return 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then(c => process.exit(c), e => { process.stderr.write(String(e.message || e) + '\n'); process.exit(2); });
}
