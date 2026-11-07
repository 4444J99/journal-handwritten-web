// Local CLI tests. Authored note/contribution bodies are technical fixtures;
// anchors read the existing repository source without changing it.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import * as Model from '../studio/notes-model.mjs';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const CLI = path.join(ROOT, 'tools/notes_backup.mjs');
const AT = '2026-11-06T01:00:00.000Z';
const readJSON = async file => JSON.parse(await fs.readFile(file, 'utf8'));
const catalog = Model.buildSourceCatalog(
  JSON.parse(readFileSync(path.join(ROOT, 'studio/data/notes-versions.json'), 'utf8')),
  JSON.parse(readFileSync(path.join(ROOT, 'studio/data/review.json'), 'utf8')),
);
const source = catalog.pieces.flatMap(p => p.versions).find(v => !v.issues.length && v.lines.length);
const anchor = Model.createAnchor(catalog, {
  pieceId: source.pieceId, versionId: source.versionId, lineId: source.lines[0].lineId,
});

function technicalRecord(family, revisionId, recordId = 'backup-' + family) {
  return Model.createRevision({
    family, recordId, revisionId, anchor,
    author: { id: 'technical-backup-author', credit: 'Technical backup fixture', provenance: 'technical-fixture', sourceIds: ['tests/test_notes_backup.mjs'] },
    fixture: true, text: '[TECHNICAL FIXTURE — not author text] Backup metadata check.',
    poemDate: { certainty: 'approximate', value: '2000' }, noteDate: '2026-10-26',
    editedBy: 'technical-backup-author', visibility: 'public-candidate',
    citations: [{ label: 'Technical fixture reference', url: 'https://example.invalid/backup', locator: 'fixture-1' }],
    ...(family === 'note' ? { kind: 'reflection' } : {
      type: 'hand-copy',
      permission: { status: 'granted', scopes: ['web'], evidence: '[TECHNICAL FIXTURE] Test permission receipt', recordedBy: 'technical-fixture-reviewer', recordedAt: AT },
    }),
  }, { at: AT });
}

function history(family) {
  const initial = technicalRecord(family, 'backup-' + family + '-00');
  const accepted = Model.transitionRevision(initial, 'accept', { actor: 'technical-fixture-reviewer', at: AT, revisionId: 'backup-' + family + '-01' });
  const cleared = Model.transitionRevision(accepted, 'clear', { actor: 'technical-fixture-reviewer', at: AT, revisionId: 'backup-' + family + '-02' });
  const edited = Model.createRevision({
    revisionId: 'backup-' + family + '-03', editedBy: 'technical-backup-author',
    text: '[TECHNICAL FIXTURE — not author text] Revised backup metadata check.',
    changeReason: 'Technical fixture revision',
  }, { previous: cleared, at: '2026-11-06T02:00:00.000Z' });
  return [initial, accepted, cleared, edited];
}

function fixtureBackup() {
  return Model.exportEnvelope({ notes: history('note'), contributions: history('contribution') }, AT);
}

async function temporary(t) {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 't05-notes-backup-'));
  t.after(() => fs.rm(dir, { recursive: true, force: true }));
  return dir;
}
async function writeJSON(file, value) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
}
async function writeExport(dir, envelope) {
  await fs.mkdir(dir, { recursive: true });
  for (const collection of ['notes', 'contributions']) for (const doc of envelope[collection]) {
    await writeJSON(path.join(dir, collection, doc.revisionId + '.json'), doc);
  }
}
function run(action, input, output) {
  const result = spawnSync(process.execPath, [CLI, action, input, output], { cwd: ROOT, encoding: 'utf8', timeout: 15000 });
  assert.equal(result.error, undefined, result.error?.message);
  return result;
}
function succeeds(result) {
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}
function fails(result, pattern) {
  assert.notEqual(result.status, 0, 'CLI unexpectedly accepted invalid input');
  if (pattern) assert.match(result.stderr, pattern);
}
async function absent(file) { await assert.rejects(fs.lstat(file), { code: 'ENOENT' }); }

test('pack/unpack CLI preserves every revision, source, date, identity and approval field', async t => {
  const dir = await temporary(t), expected = fixtureBackup();
  const input = path.join(dir, 'source-export'), backup = path.join(dir, 'backup.json'), output = path.join(dir, 'restored-export');
  await writeExport(input, expected);
  assert.deepEqual(succeeds(run('pack', input, backup)), { notes: 4, contributions: 4, output: backup });
  const packed = await readJSON(backup);
  assert.deepEqual(packed.notes, expected.notes);
  assert.deepEqual(packed.contributions, expected.contributions);
  assert.equal(Model.restoreEnvelope(packed).notes.length, 4);
  assert.deepEqual(succeeds(run('unpack', backup, output)), { notes: 4, contributions: 4, output });
  for (const collection of ['notes', 'contributions']) for (const doc of expected[collection]) {
    const name = doc.revisionId + '.json';
    assert.deepEqual(await readJSON(path.join(output, collection, name)), doc);
    assert.deepEqual(await readJSON(path.join(input, collection, name)), doc, 'original export remains unchanged');
  }
  const repackedFile = path.join(dir, 'repacked.json');
  succeeds(run('pack', output, repackedFile));
  const repacked = await readJSON(repackedFile);
  assert.deepEqual(Model.restoreEnvelope(repacked), Model.restoreEnvelope(packed));
});

test('an old export without notes or contributions packs and restores as empty collections', async t => {
  const dir = await temporary(t), input = path.join(dir, 'legacy'), backup = path.join(dir, 'empty.json'), output = path.join(dir, 'empty-restored');
  await writeJSON(path.join(input, 'reviews', 'legacy-line.json'), { original: '[TECHNICAL FIXTURE] Old review without notes', at: AT });
  await fs.writeFile(path.join(input, 'README.md'), 'Technical legacy export\n');
  succeeds(run('pack', input, backup));
  const packed = await readJSON(backup);
  assert.deepEqual(Model.restoreEnvelope(packed), { notes: [], contributions: [] });
  succeeds(run('unpack', backup, output));
  assert.deepEqual(await fs.readdir(output), []);
  assert.deepEqual(await fs.readdir(input), ['README.md', 'reviews']);
});

test('existing output files, empty directories, populated directories and symlinks are never overwritten', async t => {
  const dir = await temporary(t), input = path.join(dir, 'input'), backup = path.join(dir, 'valid.json');
  await writeExport(input, fixtureBackup());
  await writeJSON(backup, fixtureBackup());
  const sentinel = path.join(dir, 'sentinel.json');
  await fs.writeFile(sentinel, 'UNCHANGED');
  fails(run('pack', input, sentinel), /EEXIST/);
  assert.equal(await fs.readFile(sentinel, 'utf8'), 'UNCHANGED');
  const empty = path.join(dir, 'empty'), populated = path.join(dir, 'populated');
  await fs.mkdir(empty); await fs.mkdir(populated);
  await fs.writeFile(path.join(populated, 'keep'), 'UNCHANGED');
  const link = path.join(dir, 'output-link'); await fs.symlink(populated, link, 'dir');
  for (const output of [sentinel, empty, populated, link]) fails(run('unpack', backup, output), /EEXIST/);
  assert.deepEqual(await fs.readdir(empty), []);
  assert.equal(await fs.readFile(path.join(populated, 'keep'), 'utf8'), 'UNCHANGED');
  assert.equal((await fs.lstat(link)).isSymbolicLink(), true);
});

test('pack and unpack reject non-directory exports and symlinked inputs', async t => {
  const dir = await temporary(t), valid = path.join(dir, 'valid'), backup = path.join(dir, 'valid-backup.json');
  await writeExport(valid, fixtureBackup()); await writeJSON(backup, fixtureBackup());
  fails(run('pack', backup, path.join(dir, 'from-file.json')), /real directory/);
  const rootLink = path.join(dir, 'root-link'); await fs.symlink(valid, rootLink, 'dir');
  fails(run('pack', rootLink, path.join(dir, 'from-root-link.json')), /real directory/);
  const collectionLinkRoot = path.join(dir, 'collection-link-export'); await fs.mkdir(collectionLinkRoot);
  await fs.symlink(path.join(valid, 'notes'), path.join(collectionLinkRoot, 'notes'), 'dir');
  fails(run('pack', collectionLinkRoot, path.join(dir, 'from-collection-link.json')), /collection directory/);
  const documentLinkRoot = path.join(dir, 'document-link-export'); await fs.mkdir(path.join(documentLinkRoot, 'notes'), { recursive: true });
  const name = fixtureBackup().notes[0].revisionId + '.json';
  await fs.symlink(path.join(valid, 'notes', name), path.join(documentLinkRoot, 'notes', name));
  fails(run('pack', documentLinkRoot, path.join(dir, 'from-document-link.json')), /regular document/);
  const badCollection = path.join(dir, 'collection-file-export'); await fs.mkdir(badCollection);
  await fs.writeFile(path.join(badCollection, 'notes'), '{}');
  fails(run('pack', badCollection, path.join(dir, 'from-collection-file.json')), /collection directory/);
  const backupLink = path.join(dir, 'backup-link.json'); await fs.symlink(backup, backupLink);
  const out = path.join(dir, 'from-backup-link');
  fails(run('unpack', backupLink, out), /regular|symlink|symbolic|real file/i);
  await absent(out);
});

test('unsafe revision IDs, unexpected entries and filename/ID mismatches produce no output', async t => {
  const dir = await temporary(t), badBackup = fixtureBackup();
  badBackup.notes[0].revisionId = '../escape';
  const input = path.join(dir, 'unsafe.json'), output = path.join(dir, 'unsafe-output');
  await writeJSON(input, badBackup);
  fails(run('unpack', input, output), /revisionId|revision ID|parents/);
  await absent(output); await absent(path.join(dir, 'escape.json'));
  const unsafeExport = path.join(dir, 'unsafe-export');
  await writeJSON(path.join(unsafeExport, 'notes', '..json'), fixtureBackup().notes[0]);
  const unsafePacked = path.join(dir, 'unsafe-packed.json');
  fails(run('pack', unsafeExport, unsafePacked), /Unexpected collection entry/);
  await absent(unsafePacked);
  const mismatch = path.join(dir, 'mismatch');
  await writeJSON(path.join(mismatch, 'notes', 'different-id.json'), fixtureBackup().notes[0]);
  const mismatchPacked = path.join(dir, 'mismatch.json');
  fails(run('pack', mismatch, mismatchPacked), /Filename\/revision ID mismatch/);
  await absent(mismatchPacked);
});

test('missing parents and revision collisions fail full graph validation before pack/unpack writes', async t => {
  const dir = await temporary(t);
  const missing = fixtureBackup(); missing.notes = missing.notes.slice(1);
  const collision = fixtureBackup();
  collision.contributions = [technicalRecord('contribution', collision.notes[0].revisionId, 'collision-contribution')];
  for (const [label, envelope, expected] of [['missing', missing, /missing or foreign parent/], ['collision', collision, /collision/i]]) {
    const exportDir = path.join(dir, label + '-export'), packed = path.join(dir, label + '-packed.json');
    await writeExport(exportDir, envelope);
    fails(run('pack', exportDir, packed), expected); await absent(packed);
    const input = path.join(dir, label + '.json'), out = path.join(dir, label + '-restored');
    await writeJSON(input, envelope);
    fails(run('unpack', input, out), expected); await absent(out);
  }
});

test('invalid backup and revision shapes are rejected before a destination is created', async t => {
  const dir = await temporary(t), invalidRecord = fixtureBackup();
  invalidRecord.notes[0].unexpected = 'TECHNICAL FIXTURE invalid metadata';
  const cases = [null, [], { format: 'wrong', version: 1, notes: [], contributions: [] },
    { format: 'versforms-notes-backup', version: 1, notes: [] }, invalidRecord];
  for (const [i, value] of cases.entries()) {
    const input = path.join(dir, 'invalid-' + i + '.json'), out = path.join(dir, 'invalid-' + i);
    await writeJSON(input, value);
    fails(run('unpack', input, out)); await absent(out);
  }
  const input = path.join(dir, 'invalid-export'), out = path.join(dir, 'invalid-packed.json');
  await writeJSON(path.join(input, 'notes', 'array-record.json'), []);
  fails(run('pack', input, out)); await absent(out);
});

test('malformed UTF-8 in a document or backup is rejected without replacing author text', async t => {
  const dir = await temporary(t), doc = technicalRecord('note', 'invalid-utf8-revision');
  function invalidBytes(value) {
    const bytes = Buffer.from(JSON.stringify(value));
    const marker = bytes.indexOf('Backup metadata check.');
    assert.ok(marker >= 0, 'technical text marker must be present');
    bytes[marker] = 0xff; // Invalid UTF-8; permissive decoding would silently write U+FFFD.
    return bytes;
  }
  const exportDir = path.join(dir, 'invalid-export'), document = path.join(exportDir, 'notes', doc.revisionId + '.json');
  await fs.mkdir(path.dirname(document), { recursive: true });
  const rawDocument = invalidBytes(doc); await fs.writeFile(document, rawDocument);
  const packed = path.join(dir, 'invalid-packed.json');
  fails(run('pack', exportDir, packed), /UTF.?8|encod/i);
  await absent(packed);
  assert.deepEqual(await fs.readFile(document), rawDocument);
  const backup = path.join(dir, 'invalid-backup.json'), output = path.join(dir, 'invalid-restored');
  const rawBackup = invalidBytes(Model.exportEnvelope({ notes: [doc], contributions: [] }, AT));
  await fs.writeFile(backup, rawBackup);
  fails(run('unpack', backup, output), /UTF.?8|encod/i);
  await absent(output);
  assert.deepEqual(await fs.readFile(backup), rawBackup);
});

test('pack refuses an envelope larger than the 32 MiB unpack limit before creating output', async t => {
  const dir = await temporary(t), seed = technicalRecord('note', 'size-fixture-seed');
  const notes = Array.from({ length: 560 }, (_, i) => Model.createRevision({
    ...seed, recordId: 'size-fixture-record-' + i, revisionId: 'size-fixture-revision-' + i,
    text: '[TECHNICAL FIXTURE — not author text] Size boundary. ' + 'x'.repeat(62000),
  }, { at: AT }));
  const envelope = Model.exportEnvelope({ notes, contributions: [] }, AT);
  assert.ok(Buffer.byteLength(JSON.stringify(envelope, null, 2) + '\n') > 32 * 1024 * 1024);
  const input = path.join(dir, 'large-export'), output = path.join(dir, 'large-backup.json');
  await writeExport(input, envelope);
  fails(run('pack', input, output), /32 MiB/);
  await absent(output);
  assert.equal((await fs.readdir(path.join(input, 'notes'))).length, notes.length);
});
