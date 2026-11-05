// Tests for tools/cdp_client.mjs: no Chrome needed.
//
//   node --test tests/test_cdp_client.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { CDP, writeThenExit } from '../tools/cdp_client.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const MODULE = join(here, '..', 'tools', 'cdp_client.mjs');

// A stand-in for a browser WebSocket: an EventTarget that records what was sent.
class FakeSocket extends EventTarget {
  constructor() { super(); this.sent = []; this.throwOnSend = false; this.closed = false; }
  send(text) { if (this.throwOnSend) throw new Error('socket is not open'); this.sent.push(JSON.parse(text)); }
  close() { this.closed = true; }
  reply(msg) { this.dispatchEvent(Object.assign(new Event('message'), { data: JSON.stringify(msg) })); }
  drop(type = 'close') { this.dispatchEvent(new Event(type)); }
}

test('a command resolves with the matching result and events reach the handlers', async () => {
  const ws = new FakeSocket(), cdp = new CDP(ws);
  const events = []; cdp.on(m => events.push(m.method));
  const p = cdp.send('Browser.getVersion', {}, 'sess-1');
  assert.deepEqual(ws.sent[0], { id: 1, method: 'Browser.getVersion', params: {}, sessionId: 'sess-1' });
  ws.reply({ method: 'Log.entryAdded', params: {} });
  ws.reply({ id: 1, result: { product: 'Chrome/x' } });
  assert.deepEqual(await p, { product: 'Chrome/x' });
  assert.deepEqual(events, ['Log.entryAdded']);
  assert.equal(cdp.pending.size, 0);
});

test('an error answer rejects with the method name', async () => {
  const ws = new FakeSocket(), cdp = new CDP(ws);
  const p = cdp.send('Page.navigate');
  ws.reply({ id: 1, error: { message: 'bad url' } });
  await assert.rejects(p, /Page\.navigate: bad url/);
});

test('when the socket closes every waiting command is rejected at once and later ones are not sent', async () => {
  const ws = new FakeSocket(), cdp = new CDP(ws, { timeoutMs: 60000 }); // the long limit proves the close, not the timer, ends the wait
  const a = cdp.send('Page.navigate'), b = cdp.send('Runtime.evaluate');
  ws.drop('close');
  await assert.rejects(a, /Page\.navigate: DevTools connection closed/);
  await assert.rejects(b, /Runtime\.evaluate: DevTools connection closed/);
  assert.equal(cdp.pending.size, 0);
  const sentBefore = ws.sent.length;
  await assert.rejects(cdp.send('Page.close'), /Page\.close: DevTools connection closed/);
  assert.equal(ws.sent.length, sentBefore, 'nothing is sent on a dead connection');
});

test('a socket error rejects waiting commands the same way', async () => {
  const ws = new FakeSocket(), cdp = new CDP(ws, { timeoutMs: 60000 });
  const a = cdp.send('Input.dispatchMouseEvent');
  ws.drop('error');
  await assert.rejects(a, /DevTools connection error/);
  await assert.rejects(cdp.send('Input.dispatchKeyEvent'), /DevTools connection error/);
});

test('a command with no answer is rejected after its time limit, and a late answer is ignored', async () => {
  const ws = new FakeSocket(), cdp = new CDP(ws);
  const p = cdp.send('Runtime.evaluate', {}, undefined, 40);
  await assert.rejects(p, /Runtime\.evaluate: no answer from Chrome within 40 ms/);
  assert.equal(cdp.pending.size, 0);
  ws.reply({ id: 1, result: { late: true } }); // must not throw
  const q = cdp.send('Runtime.evaluate');
  ws.reply({ id: 2, result: { ok: true } });
  assert.deepEqual(await q, { ok: true });
});

test('the default time limit comes from the constructor', async () => {
  const cdp = new CDP(new FakeSocket(), { timeoutMs: 30 });
  await assert.rejects(cdp.send('Page.navigate'), /within 30 ms/);
});

test('a socket that throws on send rejects that command and leaves nothing pending', async () => {
  const ws = new FakeSocket(), cdp = new CDP(ws);
  ws.throwOnSend = true;
  await assert.rejects(cdp.send('Page.navigate'), /Page\.navigate: socket is not open/);
  assert.equal(cdp.pending.size, 0);
});

test('a message that is not JSON is ignored', () => {
  const ws = new FakeSocket(); new CDP(ws);
  ws.dispatchEvent(Object.assign(new Event('message'), { data: 'not json' }));
});

// ---- writeThenExit: the whole report reaches a reader on a pipe, and the exit code survives

function runChild(code, bytes, readDelayMs) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ['--input-type=module', '-e',
      `import { writeThenExit } from ${JSON.stringify(MODULE)}; writeThenExit(process.stdout, "x".repeat(${bytes}), ${code});`], { stdio: ['ignore', 'pipe', 'inherit'] });
    let n = 0;
    child.stdout.pause();
    setTimeout(() => { child.stdout.on('data', d => { n += d.length; }); child.stdout.resume(); }, readDelayMs); // a slow reader forces back-pressure on the pipe
    child.on('error', reject);
    child.on('close', status => resolve({ status, n }));
  });
}

test('a report much larger than the pipe buffer arrives whole and the exit code is kept', async () => {
  const bytes = 6 * 1024 * 1024;
  const r = await runChild(7, bytes, 300);
  assert.equal(r.n, bytes);
  assert.equal(r.status, 7);
});

test('exit code 0 is kept for a large report', async () => {
  const r = await runChild(0, 2 * 1024 * 1024, 100);
  assert.equal(r.n, 2 * 1024 * 1024);
  assert.equal(r.status, 0);
});

test('writeThenExit calls exit exactly once, with the code, also when write throws', () => {
  const calls = [];
  const ok = { write(_t, cb) { setImmediate(cb); } };
  writeThenExit(ok, 'x', 3, c => calls.push(c));
  const bad = { write() { throw new Error('closed'); } };
  writeThenExit(bad, 'x', 5, c => calls.push(c));
  return new Promise(res => setTimeout(() => { assert.deepEqual(calls.sort(), [3, 5]); res(); }, 30));
});
