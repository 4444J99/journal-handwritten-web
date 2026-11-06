import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRevisionStore } from '../studio/notes-store.mjs';

function database(seed = {}) {
  const data = { notes: new Map(seed.notes || []), contributions: new Map(seed.contributions || []) };
  let writes = 0, failAt = Infinity;
  return {
    data,
    get writes() { return writes; },
    failAt(n) { failAt = n; },
    collection(name) {
      return {
        onSnapshot(callback) { callback({ docs: [...data[name]].map(([id, d]) => ({ id, exists: true, data: () => structuredClone(d) })) }); return () => {}; },
        doc(id) { return {
          async get() { return { exists: data[name].has(id), data: () => structuredClone(data[name].get(id)) }; },
          async set(value) {
            writes++;
            if (writes === failAt) throw new Error('simulated unavailable');
            if (data[name].has(id)) throw new Error('immutable');
            data[name].set(id, structuredClone(value));
          },
        }; },
      };
    },
  };
}
const revision = (id, body) => ({ revisionId: id, text: body });
const backup = (notes = [], contributions = []) => ({ format: 'versforms-notes-backup', version: 1, notes, contributions });

test('export waits for a complete initial snapshot; no false saved state without a database', () => {
  assert.throws(() => createRevisionStore({}), /database/);
  const s = createRevisionStore({ db: database(), canWrite: true });
  assert.throws(() => s.exportBackup(), /finish loading/);
  s.start();
  assert.deepEqual(s.exportBackup('2026-11-05T23:00:00Z'), { ...backup(), exportedAt: '2026-11-05T23:00:00Z' });
  s.stop();
});

test('same revision retries once; a changed revision ID collision preserves original history', async () => {
  const db = database(), s = createRevisionStore({ db, canWrite: true }); s.start();
  const old = revision('r-1', 'TECHNICAL FIXTURE — first revision');
  await s.append('notes', old);
  assert.equal((await s.append('notes', old)).unchanged, true);
  await assert.rejects(s.append('notes', revision('r-1', 'different')), /collision/);
  assert.deepEqual(db.data.notes.get('r-1'), old);
  assert.equal(db.writes, 1);
});

test('restore preflights all existing revisions before writing any new history', async () => {
  const old = revision('existing', 'original'), db = database({ notes: [['existing', old]] });
  const s = createRevisionStore({ db, canWrite: true }); s.start();
  await assert.rejects(s.restore(backup([revision('new', 'new'), revision('existing', 'collision')])), /collision/);
  assert.equal(db.writes, 0);
  assert.deepEqual(s.exportBackup('fixed').notes, [old]);
});

test('interrupted restore can be retried without losing imported or prior revisions', async () => {
  const db = database(), s = createRevisionStore({ db, canWrite: true }); s.start();
  const input = backup([revision('a', 'TECHNICAL FIXTURE A'), revision('b', 'TECHNICAL FIXTURE B')]);
  db.failAt(2);
  await assert.rejects(s.restore(input), /stopped after 1 additions/);
  assert.ok(db.data.notes.has('a'));
  assert.ok(!db.data.notes.has('b'));
  const result = await s.restore(input);
  assert.deepEqual(result, { added: 1, unchanged: 1 });
  assert.deepEqual(s.exportBackup('fixed').notes, input.notes);
});

test('read-only, unknown collection and oversized revisions cannot mutate storage', async () => {
  const db = database(), ro = createRevisionStore({ db }); ro.start();
  await assert.rejects(ro.append('notes', revision('r', 'x')), /read-only/);
  const s = createRevisionStore({ db, canWrite: true }); s.start();
  await assert.rejects(s.append('release', revision('r', 'x')), /Unknown/);
  await assert.rejects(s.append('notes', revision('r', 'x'.repeat(64 * 1024))), /64 KiB/);
  assert.equal(db.writes, 0);
});

test('a failed save leaves no optimistic revision in the exported history', async () => {
  const db = database(), s = createRevisionStore({ db, canWrite: true }); s.start(); db.failAt(1);
  await assert.rejects(s.append('notes', revision('r', 'fixture')), /unavailable/);
  assert.deepEqual(s.exportBackup('fixed').notes, []);
});
