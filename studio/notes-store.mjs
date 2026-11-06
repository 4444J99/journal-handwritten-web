// Notes use the studio's existing collection/document interface. No localStorage
// fallback: an unavailable database must never masquerade as a successful save.
export const NOTE_COLLECTIONS = Object.freeze(['notes', 'contributions']);
export const MAX_REVISION_BYTES = 64 * 1024;

export function stableJSON(value) {
  if (Array.isArray(value)) return '[' + value.map(stableJSON).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + stableJSON(value[k])).join(',') + '}';
  }
  return JSON.stringify(value);
}

export function createRevisionStore({ db, canWrite = false, validate = () => {}, onChange = () => {}, onError = () => {} }) {
  if (!db || typeof db.collection !== 'function') throw new Error('A connected studio database is required.');
  const state = Object.fromEntries(NOTE_COLLECTIONS.map(c => [c, new Map()]));
  const ready = new Set(), unsubscribers = [], chains = new Map();
  let stopped = false;
  function assertCollection(collection) {
    if (!NOTE_COLLECTIONS.includes(collection)) throw new Error('Unknown notes collection.');
  }
  function notify() { onChange(snapshot(), ready.size === NOTE_COLLECTIONS.length); }
  function snapshot() {
    return Object.fromEntries(NOTE_COLLECTIONS.map(c => [c, [...state[c].values()].map(x => structuredClone(x))]));
  }
  function start() {
    if (unsubscribers.length || stopped) throw new Error('This store has already been started or stopped.');
    for (const collection of NOTE_COLLECTIONS) {
      const unsub = db.collection(collection).onSnapshot(snap => {
        if (stopped) return;
        try {
          const next = new Map();
          for (const d of snap.docs) {
            if (!d.exists) continue;
            const data = d.data();
            validate(collection, data);
            if (data.revisionId !== d.id) throw new Error('Revision/document ID mismatch in ' + collection + '.');
            next.set(d.id, structuredClone(data));
          }
          // A poll started before our verified append can arrive afterwards.
          // These collections are append-only; never discard acknowledged
          // history just because that older snapshot does not contain it yet.
          for (const [id, data] of next) {
            if (state[collection].has(id) && stableJSON(state[collection].get(id)) !== stableJSON(data)) throw new Error('Stored revision changed unexpectedly: ' + id);
            state[collection].set(id, data);
          }
          ready.add(collection);
          notify();
        } catch (error) { ready.delete(collection); onError(error); }
      }, error => { ready.delete(collection); onError(error); });
      unsubscribers.push(typeof unsub === 'function' ? unsub : () => {});
    }
    return stop;
  }
  function stop() { stopped = true; for (const fn of unsubscribers.splice(0)) fn(); }
  async function append(collection, revision) {
    assertCollection(collection);
    if (stopped || !canWrite) throw new Error('This view is read-only.');
    if (ready.size !== NOTE_COLLECTIONS.length) throw new Error('Wait for both collections to finish loading before saving.');
    validate(collection, revision);
    const id = revision.revisionId;
    if (typeof id !== 'string' || !/^[A-Za-z0-9_.-]{1,128}$/.test(id) || id === '.' || id === '..') throw new Error('Invalid revision ID.');
    const copy = structuredClone(revision), text = stableJSON(copy);
    if (new TextEncoder().encode(JSON.stringify(copy)).length > MAX_REVISION_BYTES) throw new Error('A revision exceeds the studio document limit (64 KiB).');
    const key = collection + '/' + id;
    const run = (chains.get(key) || Promise.resolve()).then(async () => {
      const ref = db.collection(collection).doc(id);
      const prior = await ref.get();
      if (prior.exists) {
        if (stableJSON(prior.data()) !== text) throw new Error('Revision collision: the stored history was preserved.');
        state[collection].set(id, copy); notify(); return { id, unchanged: true };
      }
      await ref.set(copy);
      const saved = await ref.get();
      if (!saved.exists || stableJSON(saved.data()) !== text) throw new Error('Save could not be verified. Keep the current draft and retry.');
      state[collection].set(id, copy); notify();
      return { id, unchanged: false };
    });
    const tail = run.catch(() => {});
    chains.set(key, tail);
    try { return await run; } finally { if (chains.get(key) === tail) chains.delete(key); }
  }
  async function restore(envelope) {
    if (stopped || !canWrite) throw new Error('This view is read-only.');
    if (!envelope || envelope.format !== 'versforms-notes-backup' || envelope.version !== 1) throw new Error('Unsupported notes backup.');
    const entries = [], seen = new Map();
    for (const collection of NOTE_COLLECTIONS) {
      if (!Array.isArray(envelope[collection])) throw new Error('Missing backup collection: ' + collection);
      for (const record of envelope[collection]) {
        validate(collection, record);
        if (typeof record.revisionId !== 'string' || !/^[A-Za-z0-9_.-]{1,128}$/.test(record.revisionId) || record.revisionId === '.' || record.revisionId === '..') throw new Error('Invalid backup revision ID.');
        if (new TextEncoder().encode(JSON.stringify(record)).length > MAX_REVISION_BYTES) throw new Error('Backup revision exceeds the studio document limit (64 KiB).');
        const key = collection + '/' + record.revisionId;
        if (seen.has(key) && seen.get(key) !== stableJSON(record)) throw new Error('Conflicting duplicate revision in backup.');
        if (!seen.has(key)) { entries.push([collection, structuredClone(record)]); seen.set(key, stableJSON(record)); }
      }
    }
    // Preflight the full import before making any write. A retry is idempotent;
    // an interrupted restore keeps both existing history and completed imports.
    for (const [collection, record] of entries) {
      const prior = await db.collection(collection).doc(record.revisionId).get();
      if (prior.exists && stableJSON(prior.data()) !== stableJSON(record)) throw new Error('Restore collision: ' + record.revisionId + '. Nothing was overwritten.');
    }
    let added = 0, unchanged = 0;
    for (const [collection, record] of entries) {
      try { const result = await append(collection, record); result.unchanged ? unchanged++ : added++; }
      catch (error) { error.message = `Restore stopped after ${added} additions and ${unchanged} identical revisions. Retry the same backup safely. ${error.message}`; throw error; }
    }
    return { added, unchanged };
  }
  function exportBackup(at = new Date().toISOString()) {
    if (ready.size !== NOTE_COLLECTIONS.length) throw new Error('Wait for both collections to finish loading before export.');
    return { format: 'versforms-notes-backup', version: 1, exportedAt: at, ...snapshot() };
  }
  return { start, stop, append, restore, snapshot, exportBackup, get ready() { return ready.size === NOTE_COLLECTIONS.length; } };
}
