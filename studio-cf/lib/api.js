import {handleVariorum} from './variorum-api.js';
// JSON API for the review studio: collections of documents in D1, photos in R2.
// Every function here runs after the middleware has authenticated the caller.
import {NO_SOURCE_FENCE,SOURCE_COLLECTIONS} from './publish-fence.js';

export const COLLECTIONS = Object.freeze(['reviews', 'decisions', 'versions', 'release', 'batches', 'rconfig', 'notes', 'contributions', 'artifacts', 'parts', 'composites']);
export const IMMUTABLE_COLLECTIONS = Object.freeze(['notes', 'contributions', 'artifacts']);
export const DOC_ID_RE = /^[A-Za-z0-9_.-]{1,128}$/;
export const ASSET_ID_RE = /^(?:[a-f0-9]{32}|[a-f0-9]{64})$/;
export const MAX_DOC_BYTES = 64 * 1024;
export const MAX_ASSET_BYTES = 15 * 1024 * 1024;
// The page (studio/index.html toUploadable) sends jpeg, png, webp and gif untouched
// (under 6 MiB) and re-encodes everything else to jpeg, so those four are required.
// heic stays accepted for direct API clients.
export const ASSET_TYPES = Object.freeze(['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/heic']);

const JSON_HEADERS = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' };

export function json(body, status = 200, extra) {
  return new Response(JSON.stringify(body), { status, headers: { ...JSON_HEADERS, ...(extra || {}) } });
}
const fail = (status, error) => json({ error }, status);

// Read a request body, counting real bytes, refusing more than `limit`.
// Returns a Uint8Array, or null when the body is larger than the limit.
export async function readLimited(request, limit) {
  const declared = Number(request.headers.get('content-length'));
  if (Number.isFinite(declared) && declared > limit) return null;
  if (!request.body) return new Uint8Array(0);
  const reader = request.body.getReader();
  const chunks = [];
  let total = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > limit) { try { await reader.cancel(); } catch { /* ignore */ } return null; }
    chunks.push(value);
  }
  const out = new Uint8Array(total);
  let o = 0;
  for (const c of chunks) { out.set(c, o); o += c.byteLength; }
  return out;
}

// Writes from a browser must come from this origin. Requests with no browser
// headers (curl, tests) are fine: the Access token is the credential.
function sameOriginOk(request) {
  const site = request.headers.get('sec-fetch-site');
  if (site && site !== 'same-origin' && site !== 'none') return false;
  const origin = request.headers.get('origin');
  if (origin && origin !== new URL(request.url).origin) return false;
  return true;
}

function storageError(e) {
  const m = String((e && e.message) || e);
  if (/no such table/i.test(m)) return fail(503, 'schema_missing');
  if (/disk is full|too large|SQLITE_FULL|storage limit/i.test(m)) return fail(507, 'quota_exceeded');
  return fail(503, 'unavailable');
}

// The D1 database is shared with another project: every table here is vf_-prefixed
// and no statement may reference anything else (tests/test_sqlguard.py scans this file).
const SQL_BUMP = 'INSERT INTO vf_revs (collection, rev) VALUES (?1, 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1';
const SQL_REV = 'SELECT rev FROM vf_revs WHERE collection = ?1';
const SQL_BUMP_FOR_NEW_DOC = 'INSERT INTO vf_revs (collection, rev) SELECT ?1, 1 WHERE NOT EXISTS (SELECT id FROM vf_docs WHERE collection = ?1 AND id = ?2) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1';
const SQL_INSERT_REVISION = 'INSERT INTO vf_docs (collection, id, data, updated_at, rev) VALUES (?1, ?2, ?3, ?4, (SELECT rev FROM vf_revs WHERE collection = ?1)) ON CONFLICT(collection, id) DO NOTHING';
const SQL_DOC = 'SELECT data FROM vf_docs WHERE collection = ?1 AND id = ?2';

// JSON object key order is not revision content. Arrays retain their order.
// Comparing after parsing also handles export files' escaped Unicode safely.
function sameDocument(a, b) {
  if (a === b) return true;
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  const ak = Object.keys(a), bk = Object.keys(b);
  return ak.length === bk.length && ak.every(k => Object.hasOwn(b, k) && sameDocument(a[k], b[k]));
}

async function putRevision(env, coll, id, doc, text, now) {
  const family = coll === 'notes' ? 'note' : coll === 'contributions' ? 'contribution' : 'artifact';
  if (doc.schemaVersion !== 1 || doc.family !== family || doc.revisionId !== id ||
      typeof doc.recordId !== 'string' || !DOC_ID_RE.test(doc.recordId) || ['.', '..'].includes(doc.recordId) ||
      !Array.isArray(doc.parents) || doc.parents.some(p => typeof p !== 'string' || !DOC_ID_RE.test(p) || ['.', '..', id].includes(p)) ||
      new Set(doc.parents).size !== doc.parents.length) return fail(400, 'invalid_revision');
  // D1 batch is transactional. The absent-ID check and insertion therefore cannot
  // race another batch into overwriting a revision; retries do not bump the feed.
  const res = await env.DB.batch([
    env.DB.prepare(SQL_BUMP_FOR_NEW_DOC).bind(coll, id),
    env.DB.prepare(SQL_INSERT_REVISION).bind(coll, id, text, now),
    env.DB.prepare(SQL_DOC).bind(coll, id),
    env.DB.prepare(SQL_REV).bind(coll),
  ]);
  if (!sameDocument(JSON.parse(res[2].results[0].data), doc)) return fail(409, 'revision_conflict');
  return json({ ok: true, rev: res[3].results[0].rev });
}

async function listCollection(env, coll, since) {
  if (since !== null) {
    // Cheap path for polling: one single-row read, no document rows unless something changed.
    const cur = await env.DB.prepare(SQL_REV).bind(coll).first();
    const curRev = cur ? cur.rev : 0;
    if (curRev === since) return json({ rev: curRev, changed: false });
  }
  const [revRes, docsRes] = await env.DB.batch([
    env.DB.prepare(SQL_REV).bind(coll),
    env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 ORDER BY id').bind(coll),
  ]);
  const rev = revRes.results.length ? revRes.results[0].rev : 0;
  const docs = docsRes.results.map(r => ({ id: r.id, data: JSON.parse(r.data) }));
  return json({ rev, docs });
}

async function getDoc(env, coll, id) {
  const row = await env.DB.prepare('SELECT data FROM vf_docs WHERE collection = ?1 AND id = ?2').bind(coll, id).first();
  if (!row) return fail(404, 'not_found');
  return json({ id, data: JSON.parse(row.data) });
}

async function putDoc(env, request, coll, id) {
  const bytes = await readLimited(request, MAX_DOC_BYTES);
  if (bytes === null) return fail(413, 'too_large');
  let doc;
  try { doc = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); } catch { return fail(400, 'invalid_json'); }
  if (doc === null || typeof doc !== 'object' || Array.isArray(doc)) return fail(400, 'not_an_object');
  const text = JSON.stringify(doc);
  const now = new Date().toISOString();
  if (IMMUTABLE_COLLECTIONS.includes(coll)) {
    // JSON.parse permits overflow such as 1e999; JSON.stringify would turn that
    // value into null. Refuse that loss before any immutable revision is stored.
    if (!sameDocument(JSON.parse(text), doc)) return fail(400, 'invalid_json');
    return await putRevision(env, coll, id, doc, text, now);
  }
  const res = await env.DB.batch([
    env.DB.prepare(SOURCE_COLLECTIONS.includes(coll)?'INSERT INTO vf_revs (collection, rev) SELECT ?1, 1 WHERE '+NO_SOURCE_FENCE+' ON CONFLICT(collection) DO UPDATE SET rev = rev + 1 WHERE '+NO_SOURCE_FENCE:SQL_BUMP).bind(coll),
    env.DB.prepare('INSERT OR REPLACE INTO vf_docs (collection, id, data, updated_at, rev) SELECT ?1, ?2, ?3, ?4, (SELECT rev FROM vf_revs WHERE collection = ?1) WHERE '+(SOURCE_COLLECTIONS.includes(coll)?NO_SOURCE_FENCE:'1')).bind(coll, id, text, now),
    env.DB.prepare(SQL_REV).bind(coll),
  ]);
  if(SOURCE_COLLECTIONS.includes(coll) && !res[1].meta.changes)return fail(409,'publication_in_progress_retry');
  return json({ ok: true, rev: res[2].results[0].rev });
}

async function deleteDoc(env, coll, id) {
  if (IMMUTABLE_COLLECTIONS.includes(coll)) return fail(409, 'immutable_revision');
  const res = await env.DB.batch([
    env.DB.prepare('DELETE FROM vf_docs WHERE collection = ?1 AND id = ?2 AND '+(SOURCE_COLLECTIONS.includes(coll)?NO_SOURCE_FENCE:'1')).bind(coll, id),
    env.DB.prepare(SOURCE_COLLECTIONS.includes(coll)?'INSERT INTO vf_revs (collection, rev) SELECT ?1, 1 WHERE '+NO_SOURCE_FENCE+' ON CONFLICT(collection) DO UPDATE SET rev = rev + 1 WHERE '+NO_SOURCE_FENCE:SQL_BUMP).bind(coll),
    env.DB.prepare(SQL_REV).bind(coll),
  ]);
  if(SOURCE_COLLECTIONS.includes(coll) && !res[1].meta.changes)return fail(409,'publication_in_progress_retry');
  return json({ ok: true, rev: res[2].results[0].rev });
}

function hasSignature(type, b) {
  if (type === 'image/jpeg') return b.length > 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff;
  if (type === 'image/png') return b.length > 8 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47;
  if (type === 'image/webp') return b.length > 12 && b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46 && b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50;
  if (type === 'image/gif') return b.length > 6 && b[0] === 0x47 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x38 && (b[4] === 0x37 || b[4] === 0x39) && b[5] === 0x61;
  if (type === 'image/heic') return b.length > 12 && b[4] === 0x66 && b[5] === 0x74 && b[6] === 0x79 && b[7] === 0x70;
  return false;
}

async function postAsset(env, request) {
  const type = (request.headers.get('content-type') || '').split(';')[0].trim().toLowerCase();
  if (!ASSET_TYPES.includes(type)) return fail(415, 'unsupported_type');
  const bytes = await readLimited(request, MAX_ASSET_BYTES);
  if (bytes === null) return fail(413, 'too_large');
  if (bytes.length === 0) return fail(400, 'empty');
  if (!hasSignature(type, bytes)) return fail(415, 'unsupported_type');
  const raw = crypto.getRandomValues(new Uint8Array(16));
  const id = Array.from(raw, x => x.toString(16).padStart(2, '0')).join('');
  await env.PHOTOS.put(id, bytes, { httpMetadata: { contentType: type }, customMetadata: { createdAt: new Date().toISOString() } });
  return json({ id }, 201);
}

// Handles /api/*. `user` is {email, canWrite} from the middleware.
export async function handleApi(request, env, user) {
  const url = new URL(request.url);
  let segs;
  try { segs = url.pathname.split('/').slice(2).filter((s, i, a) => !(s === '' && i === a.length - 1)).map(decodeURIComponent); } catch { return fail(400, 'bad_path'); }
  const method = request.method;

  try {
    if (segs[0] === 'variorum') return await handleVariorum(request, env, user, segs.slice(1), readLimited);
    if (segs[0] === 'me' && segs.length === 1) {
      if (method !== 'GET') return fail(405, 'method_not_allowed');
      return json({ email: user.email, canWrite: user.canWrite });
    }

    if (segs[0] === 'assets' && segs.length === 1) {
      if (method !== 'POST') return fail(405, 'method_not_allowed');
      if (!user.canWrite || !sameOriginOk(request)) return fail(403, 'forbidden');
      return await postAsset(env, request);
    }

    if (segs[0] === 'db' && segs.length >= 2 && segs.length <= 3) {
      const coll = segs[1];
      if (!COLLECTIONS.includes(coll)) return fail(404, 'unknown_collection');
      if (segs.length === 2) {
        if (method !== 'GET') return fail(405, 'method_not_allowed');
        let since = null;
        const sp = url.searchParams.get('since');
        if (sp !== null) {
          if (!/^[0-9]{1,15}$/.test(sp)) return fail(400, 'bad_since');
          since = Number(sp);
        }
        return await listCollection(env, coll, since);
      }
      const id = segs[2];
      if (!DOC_ID_RE.test(id) || id === '.' || id === '..') return fail(400, 'bad_id');
      if (method === 'GET') return await getDoc(env, coll, id);
      if (method === 'PUT' || method === 'DELETE') {
        if (['parts','composites'].includes(coll)) return fail(405, 'use_variorum_route');
        if (!user.canWrite || !sameOriginOk(request)) return fail(403, 'forbidden');
        return method === 'PUT' ? await putDoc(env, request, coll, id) : await deleteDoc(env, coll, id);
      }
      return fail(405, 'method_not_allowed');
    }
    return fail(404, 'not_found');
  } catch (e) {
    return storageError(e);
  }
}

// GET /_blob/ID: streams a stored photo from R2.
export async function handleBlob(request, env, id) {
  if (request.method !== 'GET' && request.method !== 'HEAD') return fail(405, 'method_not_allowed');
  if (!ASSET_ID_RE.test(id)) return new Response(null, { status: 404, headers: { 'cache-control': 'no-store' } });
  let obj;
  try { obj = await env.PHOTOS.get(id); } catch { return fail(503, 'unavailable'); }
  if (!obj) return new Response(null, { status: 404, headers: { 'cache-control': 'no-store' } });
  const type = obj.httpMetadata && ASSET_TYPES.includes(obj.httpMetadata.contentType) ? obj.httpMetadata.contentType : 'application/octet-stream';
  const headers = {
    'content-type': type,
    'cache-control': 'private, max-age=31536000, immutable',
    'x-content-type-options': 'nosniff',
    'content-length': String(obj.size),
  };
  if (obj.httpEtag) headers.etag = obj.httpEtag;
  return new Response(request.method === 'HEAD' ? null : obj.body, { status: 200, headers });
}
