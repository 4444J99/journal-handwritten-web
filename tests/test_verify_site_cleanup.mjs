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
// port 1: nothing listens there, so the connection is refused
fs.writeFileSync(path.join(profile, 'DevToolsActivePort'), '1\\n/devtools/browser/stand-in\\n');
fs.writeFileSync(path.join(path.dirname(profile), 'stand-in.pid'), String(process.pid));
setInterval(() => {}, 1000);
`;

const alive = pid => { try { process.kill(pid, 0); return true; } catch { return false; } };
const sleep = ms => new Promise(r => setTimeout(r, ms));

test('a browser whose DevTools endpoint cannot be reached is stopped, and the run exits with status 2', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'verify-site-cleanup-'));
  const standIn = join(dir, 'chrome-stand-in');
  writeFileSync(standIn, STAND_IN);
  chmodSync(standIn, 0o755);
  const scratch = join(dir, 'scratch');
  let pid = null;
  try {
    const run = await new Promise((resolve, reject) => {
      const child = spawn(process.execPath, [VERIFIER, '--scratch', scratch, '--chrome', standIn], { stdio: ['ignore', 'pipe', 'pipe'] });
      let err = '';
      child.stderr.on('data', d => { err += d; });
      child.stdout.resume();
      const timer = setTimeout(() => { child.kill('SIGKILL'); reject(new Error('the verifier did not finish within 40 s')); }, 40000);
      child.on('close', status => { clearTimeout(timer); resolve({ status, err }); });
      child.on('error', reject);
    });
    const pidFile = join(scratch, 'stand-in.pid'); // the stand-in writes it next to its profile directory
    if (existsSync(pidFile)) pid = Number(readFileSync(pidFile, 'utf8'));
    assert.ok(pid, 'the stand-in was started');
    assert.equal(run.status, 2, run.err);
    assert.match(run.err, /verifier failed/);
    // give the SIGTERM a moment to be delivered, then the process must be gone
    for (let i = 0; i < 30 && alive(pid); i++) await sleep(100);
    assert.equal(alive(pid), false, 'the launched browser is still running after the verifier exited');
  } finally {
    // whatever happened above, never leave the stand-in running
    const pidFile = join(scratch, 'stand-in.pid');
    if (!pid && existsSync(pidFile)) pid = Number(readFileSync(pidFile, 'utf8'));
    if (pid && alive(pid)) { try { process.kill(pid, 'SIGKILL'); } catch {} }
    rmSync(dir, { recursive: true, force: true });
  }
});
