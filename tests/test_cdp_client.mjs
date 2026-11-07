// Tests for tools/cdp_client.mjs: no Chrome needed.
//
//   node --test tests/test_cdp_client.mjs
import { test, mock } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import net from 'node:net';
import { EventEmitter } from 'node:events';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { CDP, withBrowser, writeThenExit } from '../tools/cdp_client.mjs';

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

// ---- withBrowser: a launched browser is always stopped

const fakeLaunch = () => { const proc = { kills: [], kill(sig) { this.kills.push(sig); } }; return { proc, wsUrl: 'ws://x', launch: async () => ({ proc, wsUrl: 'ws://x' }) }; };

test('withBrowser stops the browser when the connection cannot be made, and the error reaches the caller', async () => {
  const f = fakeLaunch();
  await assert.rejects(withBrowser({ launch: f.launch, connect: async () => { throw new Error('websocket error'); } }, async () => 'unreachable'), /websocket error/);
  assert.deepEqual(f.proc.kills, ['SIGTERM']);
});

test('withBrowser stops the browser and closes the connection when the work throws', async () => {
  const f = fakeLaunch(); const conn = { closed: 0, close() { this.closed++; } };
  await assert.rejects(withBrowser({ launch: f.launch, connect: async () => conn }, async () => { throw new Error('boom'); }), /boom/);
  assert.deepEqual(f.proc.kills, ['SIGTERM']);
  assert.equal(conn.closed, 1);
});

test('withBrowser returns the result of the work and stops the browser once', async () => {
  const f = fakeLaunch(); const conn = { closed: 0, close() { this.closed++; } };
  const r = await withBrowser({ launch: f.launch, connect: async (url) => { assert.equal(url, 'ws://x'); return conn; } }, async (cdp, launched) => {
    assert.equal(cdp, conn); assert.equal(launched.wsUrl, 'ws://x'); return 42;
  });
  assert.equal(r, 42);
  assert.deepEqual(f.proc.kills, ['SIGTERM']);
  assert.equal(conn.closed, 1);
});

test('withBrowser does not try to stop a browser that never launched', async () => {
  let connected = false;
  await assert.rejects(withBrowser({ launch: async () => { throw new Error('Chrome exited early'); }, connect: async () => { connected = true; } }, async () => {}), /Chrome exited early/);
  assert.equal(connected, false);
});

test('withBrowser still stops the browser when closing the connection or killing throws', async () => {
  const proc = { killed: 0, kill() { this.killed++; throw new Error('already gone'); } };
  const conn = { close() { throw new Error('socket gone'); } };
  const r = await withBrowser({ launch: async () => ({ proc, wsUrl: 'ws://x' }), connect: async () => conn }, async () => 'ok');
  assert.equal(r, 'ok');
  assert.equal(proc.killed, 1);
});

// ---- withBrowser: cleanup waits until the browser has really exited (otherwise it stays a zombie when this process
// ends straight afterwards, e.g. as PID 1 of a container that does not reap children)

// A browser stand-in that behaves like a child process: it emits 'exit' some time after the signal it obeys.
class FakeChild extends EventEmitter {
  constructor({ obeys = ['SIGTERM', 'SIGKILL'], exitAfterMs = 50 } = {}) {
    super(); this.kills = []; this.obeys = obeys; this.exitAfterMs = exitAfterMs; this.exitCode = null; this.signalCode = null;
  }
  kill(sig) {
    this.kills.push(sig);
    if (this.obeys.includes(sig) && this.exitCode === null && this.signalCode === null) {
      setTimeout(() => { this.signalCode = sig; this.emit('exit', null, sig); }, this.exitAfterMs);
    }
    return true;
  }
}
const withChild = (proc, extra = {}) => withBrowser({ launch: async () => ({ proc, wsUrl: 'ws://x' }), connect: async () => ({ close() {} }), ...extra }, async () => 'ok');

test('withBrowser does not return until the browser has exited after SIGTERM', async () => {
  const child = new FakeChild({ exitAfterMs: 150 });
  const t0 = Date.now();
  assert.equal(await withChild(child), 'ok');
  assert.ok(Date.now() - t0 >= 140, 'returned before the browser had exited');
  assert.notEqual(child.signalCode, null, 'the browser had not exited when withBrowser returned');
  assert.deepEqual(child.kills, ['SIGTERM']);
});

test('withBrowser escalates to SIGKILL when the browser ignores SIGTERM, and waits for that exit too', async () => {
  const child = new FakeChild({ obeys: ['SIGKILL'], exitAfterMs: 30 });
  assert.equal(await withChild(child, { stopGraceMs: 100, stopKillMs: 2000 }), 'ok');
  assert.deepEqual(child.kills, ['SIGTERM', 'SIGKILL']);
  assert.equal(child.signalCode, 'SIGKILL');
});

test('withBrowser gives up after the time limits when the browser cannot be stopped, and does not hang', { timeout: 8000 }, async () => {
  const child = new FakeChild({ obeys: [] });
  const t0 = Date.now();
  assert.equal(await withChild(child, { stopGraceMs: 100, stopKillMs: 100 }), 'ok');
  assert.ok(Date.now() - t0 < 3000);
  assert.deepEqual(child.kills, ['SIGTERM', 'SIGKILL']);
});

test('withBrowser does not signal a browser that has already exited', async () => {
  const child = new FakeChild(); child.exitCode = 0;
  assert.equal(await withChild(child), 'ok');
  assert.deepEqual(child.kills, []);
});

test('withBrowser also waits for the exit when the connection could not be made', async () => {
  const child = new FakeChild({ exitAfterMs: 120 });
  const t0 = Date.now();
  await assert.rejects(withBrowser({ launch: async () => ({ proc: child, wsUrl: 'ws://x' }), connect: async () => { throw new Error('websocket error'); } }, async () => 'unreachable'), /websocket error/);
  assert.ok(Date.now() - t0 >= 110);
  assert.notEqual(child.signalCode, null);
});

// ---- connect: a DevTools endpoint that accepts the connection and never completes the WebSocket handshake

const sleep = ms => new Promise(r => setTimeout(r, ms));

// A TCP server that accepts connections and never answers: what a stuck browser looks like to a client.
async function silentServer() {
  const sockets = []; const state = { accepted: 0, closed: 0 };
  const server = net.createServer(sock => {
    state.accepted++; sockets.push(sock);
    sock.on('close', () => { state.closed++; }); sock.on('error', () => {}); sock.resume();
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  return { port: server.address().port, state, stop: async () => { sockets.forEach(x => x.destroy()); await new Promise(r => server.close(r)); } };
}

test('connect gives up when the endpoint accepts the connection but never completes the handshake, and closes the socket', { timeout: 8000 }, async () => {
  const srv = await silentServer();
  const t0 = Date.now();
  try {
    await assert.rejects(CDP.connect(`ws://127.0.0.1:${srv.port}/devtools/browser/x`, { connectTimeoutMs: 300 }), /no WebSocket handshake within 300 ms/);
    assert.ok(Date.now() - t0 < 4000, 'rejected promptly');
    // How many TCP connections a native WebSocket makes before it gives up depends on the Node version (24.x opens
    // and at once closes a second one when the connecting socket is aborted), so wait until every accepted
    // connection has closed, and stays that way, rather than expecting a particular count.
    for (let i = 0; i < 60; i++) {
      await sleep(50);
      if (srv.state.accepted >= 1 && srv.state.closed === srv.state.accepted) { await sleep(150); if (srv.state.closed === srv.state.accepted) break; }
    }
    assert.ok(srv.state.accepted >= 1, 'the client never connected');
    assert.equal(srv.state.closed, srv.state.accepted, 'a connection to the stuck endpoint was left open by the client');
  } finally { await srv.stop(); }
});

test('withBrowser stops the launched browser when the handshake never completes', { timeout: 8000 }, async () => {
  const srv = await silentServer();
  const proc = { kills: [], kill(sig) { this.kills.push(sig); } };
  try {
    await assert.rejects(
      withBrowser({ launch: async () => ({ proc, wsUrl: `ws://127.0.0.1:${srv.port}/x` }), connect: url => CDP.connect(url, { connectTimeoutMs: 300 }) }, async () => 'unreachable'),
      /no WebSocket handshake within 300 ms/);
    assert.deepEqual(proc.kills, ['SIGTERM']);
  } finally { await srv.stop(); }
});

test('connect: the default time limit is 15 s and it is overridable', () => {
  assert.equal(CDP.DEFAULT_CONNECT_TIMEOUT_MS, 15000);
});

// A socket that opens when told to, to test the timer without a server.
class OpeningSocket extends EventTarget {
  constructor() { super(); this.closed = false; this.sent = []; }
  send(t) { this.sent.push(t); }
  close() { this.closed = true; }
  open() { this.dispatchEvent(new Event('open')); }
}

test('connect: the time limit is cleared once the socket opens, so it cannot close a working connection later', async () => {
  mock.timers.enable({ apis: ['setTimeout'] });
  try {
    const ws = new OpeningSocket();
    const p = CDP.connect('ws://x', { connectTimeoutMs: 1000, WebSocketImpl: function () { return ws; } });
    ws.open();
    const cdp = await p;
    mock.timers.tick(60000);
    assert.equal(ws.closed, false, 'a timer that outlived the handshake closed the connection');
    assert.ok(cdp instanceof CDP);
  } finally { mock.timers.reset(); }
});

test('connect: the time limit is cleared when the socket reports an error first', async () => {
  mock.timers.enable({ apis: ['setTimeout'] });
  try {
    const ws = new OpeningSocket();
    const p = CDP.connect('ws://x', { connectTimeoutMs: 1000, WebSocketImpl: function () { return ws; } });
    ws.dispatchEvent(new Event('error'));
    await assert.rejects(p, /websocket error/);
    mock.timers.tick(60000);
    assert.equal(ws.closed, false, 'the timer fired after the error and closed the socket again');
  } finally { mock.timers.reset(); }
});
