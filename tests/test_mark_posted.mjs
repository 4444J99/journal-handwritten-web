// Logic test for the Release tab "Mark posted" helpers. No DOM, no browser.
// It slices the real helper block out of studio/index.html and runs it in a vm,
// so the test exercises the code the page ships, not a copy.
//
//   node --test tests/test_mark_posted.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, '..', 'studio', 'index.html'), 'utf8');
const begin = '/* mark-posted helpers begin */';
const end = '/* mark-posted helpers end */';
const i = html.indexOf(begin), j = html.indexOf(end);
assert.ok(i >= 0 && j > i, 'helper block markers not found in studio/index.html');
assert.equal(html.indexOf(begin, i + 1), -1, 'helper block appears more than once');

const ctx = vm.createContext({ URL });
vm.runInContext(html.slice(i + begin.length, j) + '\nthis.POST_DEFAULTS = POST_DEFAULTS; this.checkPostUrl = checkPostUrl; this.postedEntry = postedEntry; this.EXPO_CHOICES = EXPO_CHOICES; this.expoChoice = expoChoice; this.expoChoiceId = expoChoiceId; this.exposureEntry = exposureEntry;', ctx);
const { POST_DEFAULTS, checkPostUrl, postedEntry, EXPO_CHOICES, expoChoice, expoChoiceId, exposureEntry } = ctx;

test('defaults', () => {
  assert.equal(POST_DEFAULTS.where, 'versforms.pages.dev');
  assert.equal(POST_DEFAULTS.account, 'vers.forms');
});

test('empty or blank url is valid and stored empty', () => {
  for (const v of ['', '   ', null, undefined]) assert.deepEqual({ ...checkPostUrl(v) }, { ok: true, url: '' });
});

test('http and https are accepted and the trimmed string is kept as typed', () => {
  assert.deepEqual({ ...checkPostUrl('  https://versforms.pages.dev/p/1  ') }, { ok: true, url: 'https://versforms.pages.dev/p/1' });
  assert.equal(checkPostUrl('http://example.org').ok, true);
  assert.equal(checkPostUrl('HTTPS://Example.org/x').ok, true);
});

test('other schemes and non-urls are rejected', () => {
  for (const v of ['javascript:alert(1)', 'data:text/html,x', 'ftp://example.org', 'mailto:a@b.c', 'versforms.pages.dev', '/relative', 'not a url', 'https://'])
    assert.equal(checkPostUrl(v).ok, false, v);
});

test('host-less and scheme-relative http(s) strings are rejected (they would resolve against the studio origin)', () => {
  for (const v of ['https:x', 'http:/x', 'https:///x', 'https://?x', 'http://#x', 'https://a b', 'https:\\\\x', ' https:x '])
    assert.equal(checkPostUrl(v).ok, false, v);
});

test('control and zero-width characters are rejected, and a rejected url is never stored', () => {
  const withChar = c => 'https://x' + String.fromCharCode(c) + 'y.com';
  for (const c of [0x00, 0x01, 0x1f, 0x7f, 0xad, 0x61c, 0x200b, 0x200c, 0x200d, 0x200e, 0x200f, 0x202a, 0x202e, 0x2028, 0x2029, 0x2060, 0x2066, 0xfeff])
    assert.equal(checkPostUrl(withChar(c)).ok, false, 'U+' + c.toString(16));
  assert.equal(checkPostUrl('https://studio.test@' + String.fromCharCode(0x200b) + 'example.com').ok, false);
  assert.equal(postedEntry({ where: 'w', account: 'a', url: 'javascript:alert(1)' }, 'D', 'T').url, '');
  assert.equal(postedEntry({ where: 'w', account: 'a', url: 'https:x' }, 'D', 'T').url, '');
});

test('every accepted url is absolute: it resolves to itself against any base', () => {
  const base = 'https://studio.test/studio/index.html';
  for (const v of ['https://versforms.pages.dev/', 'http://example.org/a?b#c', 'HTTPS://Example.org/x'])
    assert.equal(new URL(v, base).host.toLowerCase(), new URL(v).host.toLowerCase(), v);
});

test('entry from defaults keeps the existing shape plus account', () => {
  const e = postedEntry({ where: POST_DEFAULTS.where, account: POST_DEFAULTS.account, url: '' }, '2026-11-05', '2026-11-05T00:00:00.000Z');
  assert.deepEqual({ ...e }, { type: 'social', where: 'versforms.pages.dev', account: 'vers.forms', date: '2026-11-05', url: '', ver: 'final', at: '2026-11-05T00:00:00.000Z' });
});

test('entry trims fields, stores the post url, tolerates missing fields', () => {
  const e = postedEntry({ where: ' versforms.pages.dev ', account: ' vers.forms ', url: ' https://versforms.pages.dev/a ' }, 'D', 'T');
  assert.equal(e.where, 'versforms.pages.dev');
  assert.equal(e.account, 'vers.forms');
  assert.equal(e.url, 'https://versforms.pages.dev/a');
  assert.equal(e.type, 'social');
  const g = postedEntry({}, 'D', 'T');
  assert.equal(g.where, ''); assert.equal(g.account, ''); assert.equal(g.url, '');
});

// ---- Exposure log: the site and the Instagram account are both choices ----

test('exactly two exposure choices: the site and the Instagram account', () => {
  assert.deepEqual([...EXPO_CHOICES].map(c => c.id), ['site', 'instagram']);
  const site = EXPO_CHOICES[0], ig = EXPO_CHOICES[1];
  assert.deepEqual({ type: site.type, where: site.where, account: site.account }, { type: 'site', where: 'versforms.pages.dev', account: '' });
  assert.deepEqual({ type: ig.type, where: ig.where, account: ig.account }, { type: 'social', where: 'Instagram', account: 'vers.forms' });
});

test('a choice sets type, where and account and keeps the other fields; it never mutates the draft', () => {
  const draft = { type: 'journal', where: 'x', account: 'y', date: '2026-11-05', url: 'https://example.org/', ver: 'draft' };
  const before = JSON.stringify(draft);
  const s = expoChoice(draft, 'site');
  assert.equal(JSON.stringify(draft), before);
  assert.deepEqual({ ...s }, { type: 'site', where: 'versforms.pages.dev', account: '', date: '2026-11-05', url: 'https://example.org/', ver: 'draft' });
  const g = expoChoice(draft, 'instagram');
  assert.deepEqual({ type: g.type, where: g.where, account: g.account, ver: g.ver }, { type: 'social', where: 'Instagram', account: 'vers.forms', ver: 'draft' });
  assert.equal(expoChoice(draft, 'nope'), draft);
});

test('the pressed choice follows the draft: set by a choice, cleared by any edit', () => {
  const blank = { type: 'social', where: '', account: '', date: '', url: '', ver: '' };
  assert.equal(expoChoiceId(blank), null);
  for (const id of ['site', 'instagram']) assert.equal(expoChoiceId(expoChoice(blank, id)), id);
  const edited = { ...expoChoice(blank, 'instagram'), where: 'Instagram stories' };
  assert.equal(expoChoiceId(edited), null);
  assert.equal(expoChoiceId({ ...expoChoice(blank, 'site'), type: 'social' }), null);
  assert.equal(expoChoiceId({ type: 'site', where: ' versforms.pages.dev ' }), 'site');
});

test('exposure entry without an account keeps the old shape exactly', () => {
  const e = exposureEntry({ type: 'journal', where: ' Some Review ', date: '', url: ' https://example.org/a ', ver: ' final ' }, '2026-11-05', 'T');
  assert.deepEqual({ ...e }, { type: 'journal', where: 'Some Review', date: '2026-11-05', url: 'https://example.org/a', ver: 'final', at: 'T' });
  assert.equal('account' in e, false);
  assert.equal('account' in exposureEntry({ type: 'social', where: 'w', account: '   ', date: 'D', url: '', ver: '' }, 'X', 'T'), false);
});

test('exposure entry from each choice carries the account only when there is one', () => {
  const draft = { type: 'social', where: '', account: '', date: '2026-11-04', url: '', ver: 'final' };
  const site = exposureEntry(expoChoice(draft, 'site'), 'X', 'T');
  assert.deepEqual({ ...site }, { type: 'site', where: 'versforms.pages.dev', date: '2026-11-04', url: '', ver: 'final', at: 'T' });
  const ig = exposureEntry(expoChoice(draft, 'instagram'), 'X', 'T');
  assert.deepEqual({ ...ig }, { type: 'social', where: 'Instagram', account: 'vers.forms', date: '2026-11-04', url: '', ver: 'final', at: 'T' });
});
