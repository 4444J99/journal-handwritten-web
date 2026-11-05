// Headless Chrome smoke test: the real studio page, the real adapter, wrangler pages dev.
// Cloudflare Access is simulated by sending the Cf-Access-Jwt-Assertion header with
// DevTools `Network.setExtraHTTPHeaders`. Skipped (visibly) when Chrome is not installed.
// Only counters and button labels are read from the page; no page text is printed.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { makeKey, signRS256, claims, startJwks } from './helpers/jwt.mjs';
import { startPagesDev, freePort, SCRATCH } from './helpers/wrangler.mjs';

const CHROME = process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const HAVE_CHROME = fs.existsSync(CHROME);
const AUD = 'smoke-aud';
const OWNER = 'owner@example.test';
const READER = 'reader@example.test';

let jwks, srv, key, iss, chrome, wsUrl, profile;

const tok = email => signRS256(key, claims({ iss, aud: AUD, email }));
const sleep = ms => new Promise(r => setTimeout(r, ms));

class Cdp {
  constructor(url) { this.ws = new WebSocket(url); this.id = 0; this.pending = new Map(); this.opened = new Promise((res, rej) => { this.ws.onopen = res; this.ws.onerror = rej; }); this.ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id && this.pending.has(d.id)) { const { res, rej } = this.pending.get(d.id); this.pending.delete(d.id); d.error ? rej(new Error(JSON.stringify(d.error))) : res(d.result); } }; }
  send(method, params = {}, sessionId) { const id = ++this.id; return new Promise((res, rej) => { this.pending.set(id, { res, rej }); this.ws.send(JSON.stringify({ id, method, params, sessionId })); }); }
  close() { try { this.ws.close(); } catch { /* ignore */ } }
}

async function openPage(email) {
  const cdp = new Cdp(wsUrl); await cdp.opened;
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  const s = (m, p) => cdp.send(m, p, sessionId);
  await s('Page.enable'); await s('Runtime.enable'); await s('Network.enable');
  await s('Network.setExtraHTTPHeaders', { headers: { 'Cf-Access-Jwt-Assertion': tok(email) } });
  await s('Page.navigate', { url: srv.base + '/' });
  const ev = async expr => { const r = await s('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error('page error: ' + JSON.stringify(r.exceptionDetails).slice(0, 300)); return r.result.value; };
  return { cdp, s, ev, targetId };
}
async function waitFor(ev, expr, ms = 15000) {
  const end = Date.now() + ms; let last;
  while (Date.now() < end) { try { last = await ev(expr); if (last) return last; } catch { /* page still loading */ } await sleep(150); }
  throw new Error('timed out waiting for: ' + expr + ' (last: ' + JSON.stringify(last) + ')');
}

before(async () => {
  if (!HAVE_CHROME) return;
  key = makeKey('smoke-kid');
  jwks = await startJwks({ keys: [key] });
  const team = `127.0.0.1:${jwks.port}`; iss = `https://${team}`;
  srv = await startPagesDev({ ACCESS_TEAM_DOMAIN: team, ACCESS_AUD: AUD, OWNER_EMAILS: OWNER, READONLY_EMAILS: READER, ACCESS_JWKS_URL_TEST: `http://${team}/cdn-cgi/access/certs` }, 'smoke');
  profile = path.join(SCRATCH, `chrome-profile-${process.pid}-${Date.now()}`);
  fs.mkdirSync(profile, { recursive: true });
  const port = await freePort();
  chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', '--disable-gpu', '--disable-extensions', '--window-size=420,900', 'about:blank'], { stdio: 'ignore' });
  for (let i = 0; i < 100 && !wsUrl; i++) {
    await sleep(200);
    try { wsUrl = (await (await fetch(`http://127.0.0.1:${port}/json/version`)).json()).webSocketDebuggerUrl; } catch { /* not up yet */ }
  }
  if (!wsUrl) throw new Error('Chrome DevTools endpoint did not come up');
}, { timeout: 180000 });

after(async () => {
  if (chrome) { chrome.kill('SIGTERM'); setTimeout(() => chrome.kill('SIGKILL'), 3000).unref(); }
  if (srv) await srv.stop();
  if (jwks) await jwks.close();
});

test('owner: page connects, confirms a piece\'s lines through the adapter, state survives a reload', { skip: !HAVE_CHROME && 'Chrome not installed', timeout: 120000 }, async () => {
  const p = await openPage(OWNER);
  try {
    await waitFor(p.ev, `document.querySelector('#save') && document.querySelector('#save').textContent === 'Synced'`);
    const before = await p.ev(`document.querySelector('#prog').textContent`);
    assert.match(before, /^0 \/ \d+ lines/);
    // "Confirm the rest" asks for a second tap, then writes every unreviewed line of the open piece.
    await p.ev(`document.querySelector('#confirm-rest').click()`);
    await p.ev(`document.querySelector('#confirm-rest').click()`);
    await waitFor(p.ev, `/^[1-9]\\d* \\/ \\d+ lines/.test(document.querySelector('#prog').textContent)`);
    await waitFor(p.ev, `document.querySelector('#save').textContent === 'Saved'`);
    // the server holds exactly the documents the page wrote
    const r = await fetch(srv.base + '/api/db/reviews', { headers: { 'Cf-Access-Jwt-Assertion': tok(OWNER) } });
    const body = await r.json();
    const n = body.docs.length;
    assert.ok(n >= 1);
    assert.equal(body.rev, n);
    // The page renders its progress line on the next animation frame, after 'Saved' is already shown.
    // Reading it once straight away raced under load (one full run in four on a busy machine, off by one),
    // so wait, bounded, for it to catch up with what the server holds.
    await waitFor(p.ev, `new RegExp('^' + ${n} + ' / ').test(document.querySelector('#prog').textContent)`);
    // photo upload through window.claude.use('assets') and the /_blob/ URL the page builds from the id
    const up = await p.ev(`(async () => {
      const bytes = new Uint8Array(2048); bytes.set([0xff, 0xd8, 0xff, 0xe0]);
      const a = await window.claude.use('assets');
      const r = await a.upload(new Blob([bytes], { type: 'image/jpeg' }), { type: 'image/jpeg' });
      const g = await fetch('/_blob/' + r.id);
      return { id: r.id, status: g.status, type: g.headers.get('content-type'), len: (await g.arrayBuffer()).byteLength };
    })()`);
    assert.match(up.id, /^[a-f0-9]{32}$/);
    assert.deepEqual([up.status, up.type, up.len], [200, 'image/jpeg', 2048]);
    // a fresh page load shows the same progress, read back through polling
    await p.s('Page.navigate', { url: srv.base + '/' });
    await waitFor(p.ev, `document.querySelector('#save') && document.querySelector('#save').textContent === 'Synced' && /^${n} \\//.test(document.querySelector('#prog').textContent)`);
  } finally { p.cdp.close(); }
});

test('read-only email: the page shows its read-only state and cannot change data', { skip: !HAVE_CHROME && 'Chrome not installed', timeout: 60000 }, async () => {
  const p = await openPage(READER);
  try {
    await waitFor(p.ev, `document.querySelector('#save') && document.querySelector('#save').textContent === 'Read-only'`);
    const n = (await (await fetch(srv.base + '/api/db/reviews', { headers: { 'Cf-Access-Jwt-Assertion': tok(OWNER) } })).json()).docs.length;
    await waitFor(p.ev, `new RegExp('^${n} /').test(document.querySelector('#prog').textContent)`);
    const before = (await (await fetch(srv.base + '/api/db/reviews', { headers: { 'Cf-Access-Jwt-Assertion': tok(OWNER) } })).json()).rev;
    await p.ev(`document.querySelector('#confirm-rest').click(); document.querySelector('#confirm-rest').click(); true`);
    await sleep(800);
    const after = (await (await fetch(srv.base + '/api/db/reviews', { headers: { 'Cf-Access-Jwt-Assertion': tok(OWNER) } })).json()).rev;
    assert.equal(after, before, 'a read-only viewer cannot change data');
  } finally { p.cdp.close(); }
});

test('no token: the browser gets nothing', { skip: !HAVE_CHROME && 'Chrome not installed', timeout: 60000 }, async () => {
  const cdp = new Cdp(wsUrl); await cdp.opened;
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  await cdp.send('Page.enable', {}, sessionId);
  await cdp.send('Page.navigate', { url: srv.base + '/' }, sessionId);
  await sleep(1500);
  // Chrome draws its own error page for an empty 403; the studio itself must not be there.
  const r = await cdp.send('Runtime.evaluate', { expression: '[!!document.querySelector("#save"), !!document.querySelector("#piece-head"), document.documentElement.outerHTML.includes("cf-adapter")]', returnByValue: true }, sessionId);
  assert.deepEqual(r.result.value, [false, false, false]);
  cdp.close();
});
