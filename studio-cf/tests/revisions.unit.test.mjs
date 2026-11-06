// Synthetic revision persistence against real local SQLite; no remote resources.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import { handleApi } from '../lib/api.js';

const { createAdapter, dbCode } = createRequire(import.meta.url)('../../studio/cf-adapter.js');
const schema = fs.readFileSync(new URL('../schema.sql', import.meta.url), 'utf8');

function localD1() {
  const sqlite = new DatabaseSync(':memory:');
  sqlite.exec(schema);
  const env = { DB: {
    prepare(sql) {
      return { sql, args: [], bind(...args) { this.args = args; return this; },
        async first() { return sqlite.prepare(this.sql).get(...this.args) || null; } };
    },
    async batch(statements) {
      sqlite.exec('BEGIN IMMEDIATE');
      try {
        const out = statements.map(s => ({ results: sqlite.prepare(s.sql).all(...s.args) }));
        sqlite.exec('COMMIT');
        return out;
      } catch (e) { sqlite.exec('ROLLBACK'); throw e; }
    },
  } };
  const call = (collection, id, method = 'GET', value, canWrite = true) => handleApi(
    new Request(`https://studio.example.test/api/db/${collection}${id ? '/' + id : ''}`, {
      method, ...(value === undefined ? {} : { body: JSON.stringify(value) }),
    }), env, { email: 'synthetic-owner@example.test', canWrite });
  return { sqlite, env, call };
}

function revision(collection, id = 'fixture-revision-1') {
  return { schemaVersion: 1, family: collection === 'notes' ? 'note' : collection === 'contributions' ? 'contribution' : 'artifact',
    recordId: 'fixture-record', revisionId: id, parents: [],
    source: { pieceId: 'fixture-piece', versionId: 'fixture-version' },
    author: { id: 'fixture-author', name: 'Technical fixture' },
    poemDate: '2020-01-01', noteDate: '2026-11-05', text: 'Technical persistence fixture — café',
    visibility: 'private', nested: { b: [1, true, null], a: 'test' } };
}

for (const collection of ['notes', 'contributions', 'artifacts']) {
  test(`${collection}: append, semantic retry, immutable collision and forbidden delete`, async t => {
    const h = localD1(); t.after(() => h.sqlite.close());
    const doc = revision(collection);
    assert.deepEqual(await (await h.call(collection, doc.revisionId, 'PUT', doc)).json(), { ok: true, rev: 1 });
    const before = h.sqlite.prepare('SELECT * FROM vf_docs WHERE collection = ?').get(collection);
    const reordered = Object.fromEntries(Object.entries(doc).reverse());
    reordered.nested = { a: 'test', b: [1, true, null] };
    assert.deepEqual(await (await h.call(collection, doc.revisionId, 'PUT', reordered)).json(), { ok: true, rev: 1 });
    assert.equal((await h.call(collection, doc.revisionId, 'PUT', { ...doc, text: 'Changed fixture' })).status, 409);
    assert.equal((await h.call(collection, doc.revisionId, 'DELETE')).status, 409);
    assert.deepEqual(h.sqlite.prepare('SELECT * FROM vf_docs WHERE collection = ?').get(collection), before);
    const next = { ...doc, revisionId: 'fixture-revision-2', parents: [doc.revisionId], noteDate: '2026-11-06', text: 'Revised technical fixture' };
    assert.equal((await h.call(collection, next.revisionId, 'PUT', next)).status, 200);
    const snap = await (await h.call(collection)).json();
    assert.equal(snap.rev, 2);
    assert.deepEqual(snap.docs.map(d => d.data), [doc, next]);
  });

  test(`${collection}: concurrent same-ID writes preserve exactly one winner`, async t => {
    const h = localD1(); t.after(() => h.sqlite.close());
    const a = revision(collection), b = { ...a, text: 'Competing technical fixture' };
    const responses = await Promise.all([h.call(collection, a.revisionId, 'PUT', a), h.call(collection, b.revisionId, 'PUT', b)]);
    assert.deepEqual(responses.map(r => r.status).sort(), [200, 409]);
    const snap = await (await h.call(collection)).json();
    assert.equal(snap.rev, 1);
    assert.equal(snap.docs.length, 1);
    assert.deepEqual(snap.docs[0].data, responses[0].status === 200 ? a : b);
  });
}

test('persistence envelope and writer permission are enforced before writing', async t => {
  const h = localD1(); t.after(() => h.sqlite.close());
  const doc = revision('notes');
  for (const bad of [{ ...doc, revisionId: 'other' }, { ...doc, family: 'contribution' },
    { ...doc, recordId: '../bad' }, { ...doc, parents: [doc.revisionId] },
    { ...doc, parents: ['previous', 'previous'] }, { ...doc, schemaVersion: 2 }]) {
    assert.equal((await h.call('notes', doc.revisionId, 'PUT', bad)).status, 400);
  }
  assert.equal((await h.call('notes', doc.revisionId, 'PUT', doc, false)).status, 403);
  assert.equal(h.sqlite.prepare('SELECT count(*) AS n FROM vf_docs').get().n, 0);
});

test('six legacy collections retain full replacement and deletion', async t => {
  const h = localD1(); t.after(() => h.sqlite.close());
  for (const c of ['reviews', 'decisions', 'versions', 'release', 'batches', 'rconfig']) {
    assert.equal((await h.call(c, 'legacy', 'PUT', { before: true })).status, 200);
    assert.equal((await h.call(c, 'legacy', 'PUT', { after: true })).status, 200);
    assert.deepEqual((await (await h.call(c, 'legacy')).json()).data, { after: true });
    assert.equal((await h.call(c, 'legacy', 'DELETE')).status, 200);
    assert.equal((await h.call(c, 'legacy')).status, 404);
  }
});

test('browser adapter exposes all immutable collections and reports collisions without retrying', async t => {
  const h = localD1(); t.after(() => h.sqlite.close());
  const adapter = createAdapter({
    fetch: (path, init = {}) => handleApi(new Request('https://studio.example.test' + path, init), h.env, { canWrite: true }),
    setTimeout, clearTimeout, isHidden: () => false, onVisible: () => {},
  });
  const db = await adapter.use('db');
  for (const c of ['notes', 'contributions', 'artifacts']) {
    const doc = revision(c);
    await db.collection(c).doc(doc.revisionId).set(doc);
    assert.deepEqual((await db.collection(c).doc(doc.revisionId).get()).data(), doc);
    await assert.rejects(db.collection(c).doc(doc.revisionId).set({ ...doc, text: 'Changed' }), e => e.code === 'conflict' && e.status === 409);
  }
  assert.equal(dbCode(409), 'conflict');
});
