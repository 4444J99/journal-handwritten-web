// A browser that was launched must be stopped even when the run fails before it starts working.
//
// The stand-in below is not Chrome. It does what a Chrome that cannot be driven does: it starts, writes the
// DevToolsActivePort file that advertises a DevTools endpoint, and stays alive, but nothing listens on that port,
// so the verifier's connection setup fails. The verifier must exit with status 2 and the stand-in must be gone.
//
//   node --test tests/test_verify_site_cleanup.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import net from 'node:net';
import { mkdtempSync, writeFileSync, chmodSync, readFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const VERIFIER = join(here, '..', 'tools', 'verify_site.mjs');

const STAND_IN = `#!${process.execPath}
const fs = require('fs'), path = require('path');
const arg = process.argv.find(a => a.startsWith('--user-data-dir='));
const profile = arg.slice('--user-data-dir='.length);
fs.mkdirSync(profile, { recursive: true });
// by default port 1: nothing listens there, so the connection is refused (STAND_IN_PORT names another port)
fs.writeFileSync(path.join(profile, 'DevToolsActivePort'), (process.env.STAND_IN_PORT || '1') + '\\n/devtools/browser/stand-in\\n');
fs.writeFileSync(path.join(path.dirname(profile), 'stand-in.pid'), String(process.pid));
setInterval(() => {}, 1000);
`;

const alive = pid => { try { process.kill(pid, 0); return true; } catch { return false; } };
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function runWithStandIn({ env = {}, args = [], timeoutMs = 40000 }) {
  const dir = mkdtempSync(join(tmpdir(), 'verify-site-cleanup-'));
  const standIn = join(dir, 'chrome-stand-in');
  writeFileSync(standIn, STAND_IN);
  chmodSync(standIn, 0o755);
  const scratch = join(dir, 'scratch');
  const pidFile = join(scratch, 'stand-in.pid'); // the stand-in writes it next to its profile directory
  let pid = null;
  try {
    const run = await new Promise((resolve, reject) => {
      const child = spawn(process.execPath, [VERIFIER, '--scratch', scratch, '--chrome', standIn, ...args], { stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, ...env } });
      let err = '';
      child.stderr.on('data', d => { err += d; });
      child.stdout.resume();
      const timer = setTimeout(() => { child.kill('SIGKILL'); reject(new Error(`the verifier did not finish within ${timeoutMs / 1000} s`)); }, timeoutMs);
      child.on('close', status => { clearTimeout(timer); resolve({ status, err }); });
      child.on('error', reject);
    });
    if (existsSync(pidFile)) pid = Number(readFileSync(pidFile, 'utf8'));
    assert.ok(pid, 'the stand-in was started');
    // give the SIGTERM a moment to be delivered, then the process must be gone
    for (let i = 0; i < 30 && alive(pid); i++) await sleep(100);
    return { ...run, standInAlive: alive(pid) };
  } finally {
    // whatever happened above, never leave the stand-in running
    if (!pid && existsSync(pidFile)) pid = Number(readFileSync(pidFile, 'utf8'));
    if (pid && alive(pid)) { try { process.kill(pid, 'SIGKILL'); } catch {} }
    rmSync(dir, { recursive: true, force: true });
  }
}

test('a browser whose DevTools endpoint cannot be reached is stopped, and the run exits with status 2', { timeout: 60000 }, async () => {
  const run = await runWithStandIn({});
  assert.equal(run.status, 2, run.err);
  assert.match(run.err, /verifier failed/);
  assert.equal(run.standInAlive, false, 'the launched browser is still running after the verifier exited');
});

test('a browser that accepts the DevTools connection and never completes the handshake is stopped too, within the connect time limit', { timeout: 60000 }, async () => {
  // a TCP server that accepts and never answers, advertised as the browser's DevTools port
  const sockets = [];
  const server = net.createServer(sock => { sockets.push(sock); sock.on('error', () => {}); sock.resume(); });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  try {
    const t0 = Date.now();
    const run = await runWithStandIn({ env: { STAND_IN_PORT: String(server.address().port) }, args: ['--connect-timeout', '500'], timeoutMs: 25000 });
    assert.equal(run.status, 2, run.err);
    assert.match(run.err, /no WebSocket handshake within 500 ms/);
    assert.ok(Date.now() - t0 < 20000, 'finished long before any hang limit');
    assert.equal(run.standInAlive, false, 'the launched browser is still running after the verifier exited');
  } finally { sockets.forEach(x => x.destroy()); await new Promise(r => server.close(r)); }
});
