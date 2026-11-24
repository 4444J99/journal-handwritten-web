import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {readdirSync} from 'node:fs';
import {CDP, withBrowser} from '../tools/cdp_client.mjs';
import {freePort} from '../studio-cf/tests/helpers/wrangler.mjs';
import silentBrowser from '../tools/silent_browser.cjs'; const {silentChromeArgs} = silentBrowser;

function chromeBin(){
  if (process.env.CHROME_BIN) return process.env.CHROME_BIN;
  const base = path.join(os.homedir(), '.cache', 'ms-playwright');
  try {
    const hits = readdirSync(base).filter(d => d.startsWith('chromium_headless_shell-')).sort();
    if (hits.length){
      return path.join(base, hits[hits.length - 1], 'chrome-headless-shell-linux64', 'chrome-headless-shell');
    }
  } catch {}
  return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
}

function slice(src, startMarker, endMarker){
  const a = src.indexOf(startMarker);
  assert.notEqual(a, -1, 'missing ' + startMarker);
  const b = endMarker ? src.indexOf(endMarker, a) : src.length;
  assert.notEqual(b, -1, 'missing end for ' + startMarker);
  return src.slice(a, b);
}

test('reader deep links #pNNN resolve, refuse Reserve, and never crash on unknown numbers', {timeout: 30000}, async () => {
  const source = await fs.readFile(new URL('../site/index.html', import.meta.url), 'utf8');
  // The pool helpers, itemForPiece and readHash, sliced out of the live page
  // (same technique as reader-permalink.test.mjs slices setHash).
  const poolHelpers = slice(source, 'function poolEntry(id){', 'function itemForPiece(pc){');
  const itemForPiece = slice(source, 'function itemForPiece(pc){', 'function prepData(d){');
  const readHash = slice(source, 'function readHash(){', 'function applyHash(h, animate){');
  const page = '<!doctype html><script>'
    + 'const PIECES = ['
    + '{id:"p001", V:[{id:"v1", s:"j", P:[["diary1",[0]]]}], top:0, g:0, n:1},'
    + '{id:"p002", V:[{id:"v2", s:"j", P:[["diary2",[0]]]}], top:0, g:1, n:1},'
    + '{id:"p003", V:[{id:"v3", s:"j", P:[["diary3",[0]]]}], top:0, g:2, n:1}];'
    + 'const BYID = {diary1:{id:"diary1", i:0, B:[{L:["x"]}], sourceStatus:"ok"},'
    + 'diary2:{id:"diary2", i:1, B:[{L:["x"]}], sourceStatus:"ok"},'
    + 'diary3:{id:"diary3", i:2, B:[{L:["x"]}], sourceStatus:"ok"}};'
    + 'const BY = {p0:{k:"p0", pi:0}, p1:{k:"p1", pi:1}, p2:{k:"p2", pi:2}};'
    + 'const SCANS = [], FONTS = [], PAL = [], HF = [];'
    + 'const CONTENTS = ["lines","pages","unfold","type"], ARRS = ["poem","scatter","spiral"];'
    + 'const LNK = {};'
    + 'let POOLS = {pools:{p001:{pool:"series", num:1, order:0}, p002:{pool:"reserve"}, p003:{pool:"series"}, p200:{pool:"series"}}};'
    + poolHelpers + itemForPiece + readHash
    + 'window.__t = {readHash, poolOfId, isReserve, pieceStamp, pieceNum, itemForPiece};'
    + '</script>';
  const server = http.createServer((req, res) => { res.setHeader('content-type', 'text/html'); res.end(page); });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const base = 'http://127.0.0.1:' + server.address().port;
  const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'reader-deeplink-'));
  try {
    await withBrowser({connect: CDP.connect, launch: async () => {
      const port = await freePort();
      const proc = spawn(chromeBin(), silentChromeArgs(['--headless=new', '--no-sandbox', '--remote-debugging-port=' + port, '--user-data-dir=' + profile, '--no-first-run', '--disable-gpu', 'about:blank']), {stdio: 'ignore'});
      for (let i = 0; i < 60; i++){
        try { const j = await (await fetch('http://127.0.0.1:' + port + '/json/version')).json(); return {proc, wsUrl: j.webSocketDebuggerUrl}; }
        catch { await new Promise(r => setTimeout(r, 100)); }
      }
      proc.kill(); throw Error('Chrome did not start');
    }}, async cdp => {
      const {targetId} = await cdp.send('Target.createTarget', {url: 'about:blank'}), {sessionId} = await cdp.send('Target.attachToTarget', {targetId, flatten: true});
      const send = (m, p = {}) => cdp.send(m, p, sessionId);
      await send('Page.enable'); await send('Runtime.enable');
      await send('Page.navigate', {url: base + '/'});
      const ev = async (expression) => {
        const r = await send('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
        if (r.exceptionDetails) throw new Error('eval failed: ' + JSON.stringify(r.exceptionDetails).exception?.description || expression);
        return r.result.value;
      };
      await ev(`new Promise(r => { const t = setInterval(() => window.__t ? (clearInterval(t), r(1)) : 0, 50); })`);
      // A known Series piece opens in the journal with its canvas item.
      assert.deepEqual(await ev(`location.hash = "#p001"; (() => { const h = readHash(); return {side: h.side, pid: h.pid, k: h.k, it: h.it ? h.it.k : null}; })()`),
        {side: 'book', pid: 'diary1', k: '0-0', it: 'p0'});
      // One- and two-digit numbers pad to the same piece; case is ignored.
      assert.equal(await ev(`location.hash = "#p01"; readHash().pid`), 'diary1');
      assert.equal(await ev(`location.hash = "#P003"; readHash().pid`), 'diary3');
      // An unknown number shows the constellation: no crash, no content.
      assert.deepEqual(await ev(`location.hash = "#p999"; (() => { const h = readHash(); return {side: h.side, c: h.c}; })()`),
        {side: 'canvas', c: 'lines'});
      // A Reserve number refuses: no text or scan is ever opened from it.
      assert.equal(await ev(`location.hash = "#p002"; readHash().unavailable`), true);
      // A Series number the pool map names but the piece model lacks (a
      // ghost slot) also refuses: there is no version to open. A number
      // the map never names still shows the constellation.
      assert.equal(await ev(`location.hash = "#p200"; readHash().unavailable`), true);
      assert.equal(await ev(`poolOfId("p200")`), 'series');
      // The pool gate is the exact-value rule: only 'reserve' refuses.
      assert.equal(await ev(`poolOfId("p001")`), 'series');
      assert.equal(await ev(`poolOfId("p999")`), 'unknown');
      assert.equal(await ev(`isReserve("p002")`), true);
      assert.equal(await ev(`isReserve("p001")`), false);
      // The n/100 stamp takes the release number from the map when it
      // knows one, else the piece-model number.
      assert.equal(await ev(`pieceStamp("p001")`), '1/100');
      assert.equal(await ev(`pieceStamp("p003")`), '3/100');
      assert.equal(await ev(`pieceNum("p999")`), 999);
    });
  } finally {
    await new Promise(r => server.close(r));
    await fs.rm(profile, {recursive: true, force: true});
  }
});
