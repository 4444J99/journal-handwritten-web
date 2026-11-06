#!/usr/bin/env node
// Local conversion only: studio COLLECTION/DOCID.json <-> private notes backup.
// Existing exports and destinations are never overwritten. No database or network calls.
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { NOTE_COLLECTIONS } from '../studio/notes-store.mjs';

const SAFE_ID = /^[A-Za-z0-9_.-]{1,128}$/;
const MAX_BACKUP_BYTES = 32 * 1024 * 1024;
const decodeJSON = bytes => JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
function validId(id) { return typeof id === 'string' && SAFE_ID.test(id) && id !== '.' && id !== '..'; }

export function validateBackup(envelope, validate = () => {}) {
  if (!envelope || envelope.format !== 'versforms-notes-backup' || envelope.version !== 1) throw new Error('Unsupported notes backup.');
  for (const coll of NOTE_COLLECTIONS) {
    if (!Array.isArray(envelope[coll])) throw new Error('Missing collection: ' + coll);
    const seen = new Set();
    for (const record of envelope[coll]) {
      if (!record || !validId(record.revisionId) || seen.has(record.revisionId)) throw new Error('Invalid or duplicated revision ID in ' + coll);
      if (Buffer.byteLength(JSON.stringify(record), 'utf8') > 64 * 1024) throw new Error('Revision exceeds 64 KiB: ' + record.revisionId);
      validate(coll, record); seen.add(record.revisionId);
    }
  }
  return envelope;
}

export async function pack(directory, { at = new Date().toISOString(), validate } = {}) {
  const rootStat = await fs.lstat(directory);
  if (!rootStat.isDirectory() || rootStat.isSymbolicLink()) throw new Error('Export root must be a real directory.');
  const envelope = { format: 'versforms-notes-backup', version: 1, exportedAt: at, notes: [], contributions: [] };
  for (const coll of NOTE_COLLECTIONS) {
    const dir = path.join(directory, coll);
    let stat;
    try { stat = await fs.lstat(dir); } catch (e) { if (e.code === 'ENOENT') continue; throw e; }
    if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error('Not a collection directory: ' + coll);
    for (const name of (await fs.readdir(dir)).sort()) {
      if (!name.endsWith('.json') || !validId(name.slice(0, -5))) throw new Error('Unexpected collection entry: ' + coll + '/' + name);
      const file = path.join(dir, name), info = await fs.lstat(file);
      if (!info.isFile() || info.isSymbolicLink()) throw new Error('Not a regular document: ' + file);
      if (info.size > 1024 * 1024) throw new Error('Document file too large: ' + file);
      const record = decodeJSON(await fs.readFile(file));
      if (record.revisionId !== name.slice(0, -5)) throw new Error('Filename/revision ID mismatch: ' + file);
      envelope[coll].push(record);
    }
  }
  return validateBackup(envelope, validate);
}

export async function unpack(envelope, out, { validate } = {}) {
  validateBackup(envelope, validate);
  // mkdir without recursive is a guard: even an existing empty destination is
  // refused. Only directories created by this invocation may be cleaned up.
  await fs.mkdir(out);
  const created = [];
  try {
    for (const coll of NOTE_COLLECTIONS) {
      if (!envelope[coll].length) continue;
      const dir = path.join(out, coll); await fs.mkdir(dir); created.push(dir);
      for (const record of envelope[coll]) {
        const file = path.join(dir, record.revisionId + '.json');
        await fs.writeFile(file, JSON.stringify(record, null, 2) + '\n', { flag: 'wx' }); created.push(file);
      }
    }
  } catch (e) {
    for (const p of created.reverse()) { try { const st = await fs.lstat(p); st.isDirectory() ? await fs.rmdir(p) : await fs.unlink(p); } catch {} }
    try { await fs.rmdir(out); } catch {}
    throw e;
  }
  return Object.fromEntries(NOTE_COLLECTIONS.map(c => [c, envelope[c].length]));
}

async function main() {
  const [action, input, out] = process.argv.slice(2);
  if (!['pack', 'unpack'].includes(action) || !input || !out || process.argv.length !== 5) throw new Error('Usage: node tools/notes_backup.mjs pack EXPORT_DIR BACKUP.json | unpack BACKUP.json NEW_EXPORT_DIR');
  // Structural/semantic record validation is supplied by the content model.
  const model = await import('../studio/notes-model.mjs');
  const validate = model.assertRevision;
  if (action === 'pack') {
    const envelope = await pack(input, { validate });
    model.restoreEnvelope(envelope);
    const serialized = JSON.stringify(envelope, null, 2) + '\n';
    if (Buffer.byteLength(serialized, 'utf8') > MAX_BACKUP_BYTES) throw new Error('Backup exceeds 32 MiB. Keep the existing per-document export for larger archives.');
    await fs.writeFile(out, serialized, { flag: 'wx' });
    console.log(JSON.stringify({ notes: envelope.notes.length, contributions: envelope.contributions.length, output: out }));
  } else {
    const stat = await fs.lstat(input);
    if (!stat.isFile() || stat.isSymbolicLink()) throw new Error('Backup input must be a regular file, not a link.');
    if (stat.size > MAX_BACKUP_BYTES) throw new Error('Backup exceeds 32 MiB. Use the existing per-document importer for larger archives.');
    const envelope = decodeJSON(await fs.readFile(input));
    model.restoreEnvelope(envelope);
    console.log(JSON.stringify({ ...await unpack(envelope, out, { validate }), output: out }));
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) main().catch(e => { console.error(e.message); process.exitCode = 1; });
