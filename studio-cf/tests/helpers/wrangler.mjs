// Boots `wrangler pages dev` against a fresh local D1/R2 simulation. Local only:
// nothing here talks to Cloudflare. Everything is written under SCRATCH.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const STUDIO_CF = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const SCRATCH = process.env.STUDIO_CF_SCRATCH || '/Volumes/Archive4T/Temporary/versforms-work/studio-cf';
const WRANGLER = process.env.WRANGLER_BIN || '/opt/homebrew/bin/wrangler';

export function wranglerEnv() {
  return {
    ...process.env,
    WRANGLER_SEND_METRICS: 'false',
    WRANGLER_LOG_PATH: path.join(SCRATCH, 'logs'),
    XDG_CONFIG_HOME: path.join(SCRATCH, 'xdg'),
    // Miniflare would otherwise fetch https://workers.cloudflare.com/cf.json (the only
    // network call of `pages dev`) and cache it in .wrangler/cache. Documented switch:
    // https://developers.cloudflare.com/workers/wrangler/system-environment-variables/
    CLOUDFLARE_CF_FETCH_ENABLED: 'false',
    MINIFLARE_CACHE_DIR: path.join(SCRATCH, 'mf-cache'),
    CI: '1',
  };
}

// `wrangler d1 execute --local` prints its result and then does not exit under
// this host's Node (observed with wrangler 4.104.0), so we stop it once it has
// reported success. A failure makes it exit on its own with an error.
export function d1Execute(persist, extraArgs) {
  const args = ['d1', 'execute', 'object-lessons-submissions', '--local', '--persist-to', persist, '--cwd', STUDIO_CF, ...extraArgs];
  return new Promise((resolve, reject) => {
    const child = spawn(WRANGLER, args, { env: wranglerEnv(), stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '', done = false;
    const finish = (err, val) => { if (done) return; done = true; clearTimeout(timer); child.kill('SIGTERM'); setTimeout(() => child.kill('SIGKILL'), 3000).unref(); err ? reject(err) : resolve(val); };
    const timer = setTimeout(() => finish(new Error('d1 execute timed out:\n' + out)), 90000);
    const onData = d => {
      out += d;
      if (/commands? executed successfully/.test(out) && /\n\]\s*$/.test(out)) finish(null, out);
    };
    child.stdout.on('data', onData); child.stderr.on('data', onData);
    child.on('exit', code => { if (code === 0) finish(null, out); else finish(new Error('d1 execute failed (' + code + '):\n' + out)); });
  });
}

export function freePort() {
  return new Promise((resolve, reject) => {
    const s = net.createServer();
    s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => resolve(p)); });
    s.on('error', reject);
  });
}

// vars: {ACCESS_TEAM_DOMAIN, ...}; they are passed as --binding KEY=VALUE, so no
// .dev.vars file is ever written inside the repository.
// opts.persist: reuse an existing persist dir (schema is applied only for a fresh one).
export async function startPagesDev(vars, label = 'run', opts = {}) {
  fs.mkdirSync(path.join(SCRATCH, 'logs'), { recursive: true });
  fs.mkdirSync(path.join(SCRATCH, 'xdg'), { recursive: true });
  const persist = opts.persist || path.join(SCRATCH, `state-${label}-${process.pid}-${Date.now()}`);
  fs.mkdirSync(persist, { recursive: true });
  const env = wranglerEnv();

  if (!opts.persist) await d1Execute(persist, ['--file', path.join(STUDIO_CF, 'schema.sql')]);

  const port = await freePort();
  const args = ['pages', 'dev', opts.dir || path.resolve(STUDIO_CF, '../studio'), '--cwd', opts.cwd || STUDIO_CF, '--ip', '127.0.0.1', '--port', String(port), '--persist-to', persist,
    '--inspector-port', String(await freePort())];
  if (opts.debug) args.push('--log-level', 'debug');
  for (const [k, v] of Object.entries(vars)) args.push('--binding', `${k}=${v}`);
  const child = spawn(WRANGLER, args, { cwd: opts.cwd || STUDIO_CF, env, stdio: ['ignore', 'pipe', 'pipe'] });
  let log = '';
  const ready = new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error('wrangler did not become ready in 90 s:\n' + log)), 90000);
    const onData = d => { log += d; if (log.includes(`Ready on http://127.0.0.1:${port}`)) { clearTimeout(t); resolve(); } };
    child.stdout.on('data', onData); child.stderr.on('data', onData);
    child.on('exit', c => { clearTimeout(t); reject(new Error('wrangler exited early (' + c + '):\n' + log)); });
  });
  await ready;
  return {
    base: `http://127.0.0.1:${port}`,
    port, persist,
    log: () => log,
    stop: () => new Promise(r => { if (child.exitCode !== null) return r(); child.removeAllListeners('exit'); child.on('exit', r); child.kill('SIGTERM'); setTimeout(() => child.kill('SIGKILL'), 5000).unref(); }),
  };
}
