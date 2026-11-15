#!/usr/bin/env node
// Real Chromium acceptance for the local T09 workbench. No npm packages, Node >=22.
// Use --renders and --packet to launch a local server, or start it separately.
// This verifier accepts loopback URLs only.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { CDP, withBrowser, stopBrowser } from './cdp_client.mjs';
import silentBrowser from './silent_browser.cjs'; const {silentChromeArgs} = silentBrowser;

const args = process.argv.slice(2);
function option(name, fallback) {
  const i = args.indexOf(name);
  if (i < 0) return fallback;
  if (!args[i + 1] || args[i + 1].startsWith('--')) throw new Error(`Missing value for ${name}`);
  return args[i + 1];
}
const url = new URL(option('--url', 'http://127.0.0.1:8765/'));
if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || url.username || url.password) {
  throw new Error('--url must be an HTTP 127.0.0.1 URL without credentials');
}
const chrome = option('--chrome', process.env.CHROME_PATH);
if (!chrome) throw new Error('Supply --chrome /absolute/path/to/chromium');
const renderDirectory = option('--renders', null);
const packetDirectory = option('--packet', null);
if (Boolean(renderDirectory) !== Boolean(packetDirectory)) throw new Error('Supply both --renders and --packet');
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const scratch = await fs.mkdtemp(path.join(os.tmpdir(), 't09-browser-'));
const output = path.resolve(option('--out', path.join(scratch, 'browser.json')));
const shots = path.resolve(option('--shots', path.join(scratch, 'shots')));
await fs.mkdir(shots, { recursive: true });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const report = {
  schema: 'versforms.t09-browser-receipt.v1',
  observed_at: new Date().toISOString(),
  base_url: url.href,
  fixture_only: true,
  browser: null,
  cells: [],
  limits: [
    'Headless Chromium; no acoustic/perceptual listening claim.',
    'Mobile viewport/touch emulation is not physical iPhone or Safari acceptance.',
    'Silent switch, screen lock, phone calls, audio routing and live reader integration untested.'
  ]
};

let localServer = null;
async function startLocalServer() {
  if (!renderDirectory) return;
  let serverError = null;
  localServer = spawn(option('--python', 'python3'), [
    path.join(repo, 'audio_pilot/serve.py'), '--renders', path.resolve(renderDirectory),
    '--packet', path.resolve(packetDirectory), '--port', url.port || '80'
  ], { cwd: repo, stdio: ['ignore', 'ignore', 'pipe'] });
  let stderr = '';
  localServer.stderr.on('data', data => { stderr = (stderr + data).slice(-3000); });
  localServer.on('error', error => { serverError = error; });
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    if (serverError) throw serverError;
    if (localServer.exitCode !== null) throw new Error(`Listening server exited: ${stderr}`);
    try {
      const response = await fetch(new URL('/receipt.json', url), { signal: AbortSignal.timeout(500) });
      if (response.ok) {
        report.manifest_sha256 = (await response.json()).manifest_sha256;
        return;
      }
    } catch {}
    await pause(50);
  }
  throw new Error('Listening server did not become ready');
}

async function launch() {
  const profile = path.join(scratch, 'profile');
  await fs.mkdir(profile);
  const proc = spawn(chrome, silentChromeArgs([
    '--headless=new', '--no-sandbox', '--disable-dev-shm-usage', '--remote-debugging-port=0',
    `--user-data-dir=${profile}`, '--no-first-run', '--disable-extensions',
    '--disable-background-networking', 'about:blank'
  ]), { stdio: ['ignore', 'ignore', 'pipe'] });
  let stderr = '', spawnError = null;
  proc.stderr.on('data', data => { stderr = (stderr + data).slice(-10000); });
  proc.on('error', error => { spawnError = error; });
  try {
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline) {
      if (spawnError) throw spawnError;
      const match = stderr.match(/DevTools listening on (ws:\/\/\S+)/);
      if (match) return { proc, wsUrl: match[1] };
      if (proc.exitCode !== null) throw new Error(`Chromium exited ${proc.exitCode}: ${stderr}`);
      await pause(50);
    }
    throw new Error('Chromium did not expose its local DevTools socket');
  } catch (error) {
    await stopBrowser(proc);
    throw error;
  }
}

async function cell(cdp, mobile) {
  const result = { viewport: mobile ? '390x844 touch' : '1280x900 desktop', checks: [], errors: [], requests: [], screenshots: [] };
  report.cells.push(result);
  const { browserContextId } = await cdp.send('Target.createBrowserContext', { disposeOnDetach: true });
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank', browserContextId });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  const send = (method, params = {}) => cdp.send(method, params, sessionId);
  const evaluate = async expression => {
    const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  };
  const check = (name, pass, evidence) => {
    result.checks.push({ name, status: pass ? 'PASS' : 'FAIL', evidence });
    if (!pass) throw new Error(`${name}: ${JSON.stringify(evidence)}`);
  };
  const waitFor = async (expression, ms = 10000) => {
    const deadline = Date.now() + ms;
    while (Date.now() < deadline) {
      if (await evaluate(expression).catch(() => false)) return;
      await pause(50);
    }
    throw new Error(`Timed out: ${expression}`);
  };
  cdp.on(message => {
    if (message.sessionId !== sessionId) return;
    if (message.method === 'Runtime.exceptionThrown') result.errors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
    if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') result.errors.push(message.params.args.map(x => x.value || x.description).join(' '));
    if (message.method === 'Network.requestWillBeSent') result.requests.push(message.params.request.url);
    if (message.method === 'Network.responseReceived' && message.params.response.status >= 400 && !message.params.response.url.endsWith('/favicon.ico')) {
      result.errors.push(`HTTP ${message.params.response.status} ${message.params.response.url}`);
    }
    if (message.method === 'Network.loadingFailed' && !message.params.canceled) result.errors.push(message.params.errorText);
  });
  const tap = async selector => {
    await evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'center'})`);
    const rect = await evaluate(`(()=>{const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`);
    if (mobile) {
      await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [rect] });
      await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    } else {
      await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...rect, button: 'left', buttons: 1, clickCount: 1 });
      await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...rect, button: 'left', buttons: 0, clickCount: 1 });
    }
  };
  const shot = async name => {
    const { data } = await send('Page.captureScreenshot', { format: 'png' });
    const filename = `${mobile ? 'mobile' : 'desktop'}-${name}.png`;
    await fs.writeFile(path.join(shots, filename), Buffer.from(data, 'base64'));
    result.screenshots.push({ file: filename, sha256: crypto.createHash('sha256').update(Buffer.from(data, 'base64')).digest('hex') });
  };
  try {
    for (const domain of ['Page', 'Runtime', 'Network']) await send(`${domain}.enable`);
    await send('Emulation.setDeviceMetricsOverride', { width: mobile ? 390 : 1280, height: mobile ? 844 : 900, deviceScaleFactor: 1, mobile });
    if (mobile) await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
    await send('Page.addScriptToEvaluateOnNewDocument', { source: `
      window.__t09AudioTrace = {starts:0,stops:0};
      window.__t09Exports = [];
      const createURL=URL.createObjectURL;
      URL.createObjectURL=function(blob){
        if(blob.type==='application/json') blob.text().then(text=>window.__t09Exports.push(JSON.parse(text)));
        return createURL.call(this,blob);
      };
      const anchorClick=HTMLAnchorElement.prototype.click;
      HTMLAnchorElement.prototype.click=function(){if(!this.download)return anchorClick.call(this)};
      const audioStart=AudioBufferSourceNode.prototype.start,audioStop=AudioBufferSourceNode.prototype.stop;
      AudioBufferSourceNode.prototype.start=function(...args){window.__t09AudioTrace.starts++;return audioStart.apply(this,args)};
      AudioBufferSourceNode.prototype.stop=function(...args){window.__t09AudioTrace.stops++;return audioStop.apply(this,args)};
    ` });
    await send('Page.navigate', { url: url.href });
    await waitFor(`!!document.querySelector('#load-data')`);
    await pause(150);
    check('off before user action', (await evaluate('window.__t09AudioTrace.starts')) === 0 && !result.requests.some(x => /\/samples\//.test(x)), { trace: await evaluate('window.__t09AudioTrace'), sample_requests: result.requests.filter(x => /\/samples\//.test(x)) });
    await tap('#load-data');
    await waitFor(`document.querySelector('#sample-select').options.length > 0 && Array.from(document.querySelector('#sample-select').options).some(x=>x.value)`);
    check('fixture visible', /fixture/i.test(await evaluate(`document.querySelector('#fixture-status').textContent`)), await evaluate(`document.querySelector('#fixture-status').textContent`));
    const ids = await evaluate(`Array.from(document.querySelector('#sample-select').options).map(x=>x.value).filter(Boolean)`);
    await evaluate(`(()=>{const s=document.querySelector('#sample-select');s.value=${JSON.stringify(ids[0])};s.dispatchEvent(new Event('change',{bubbles:true}))})()`);
    check('selection does not play', (await evaluate('window.__t09AudioTrace.starts')) === 0, await evaluate('window.__t09AudioTrace'));
    await tap('#load-sample');
    await waitFor(`!document.querySelector('#start-playback').disabled`);
    check('loaded sample stays silent', (await evaluate('window.__t09AudioTrace.starts')) === 0, await evaluate(`({trace:window.__t09AudioTrace,state:document.querySelector('#playback-state').textContent})`));
    await tap('#start-playback');
    await waitFor('window.__t09AudioTrace.starts === 1');
    check('explicit Start reaches real AudioBufferSourceNode', true, await evaluate(`({trace:window.__t09AudioTrace,state:window.t09Player?.snapshot()})`));
    await tap('#stop-playback');
    await pause(100);
    check('explicit Stop stops source', (await evaluate('window.__t09AudioTrace.stops')) >= 1, await evaluate('window.__t09AudioTrace'));
    const stoppedStarts = await evaluate('window.__t09AudioTrace.starts');
    await pause(200);
    check('Stop does not resume', (await evaluate('window.__t09AudioTrace.starts')) === stoppedStarts, await evaluate('window.__t09AudioTrace'));

    // Restart the loaded buffer, then change selected context while it is active.
    await tap('#start-playback');
    await waitFor(`window.__t09AudioTrace.starts > ${stoppedStarts}`);
    const beforeChange = await evaluate('window.__t09AudioTrace.stops');
    await evaluate(`(()=>{const s=document.querySelector('#sample-select');s.value=${JSON.stringify(ids[1] || ids[0])};s.dispatchEvent(new Event('change',{bubbles:true}))})()`);
    await pause(100);
    check('sample/context change stops previous source', (await evaluate('window.__t09AudioTrace.stops')) > beforeChange, await evaluate('window.__t09AudioTrace'));
    check('provenance is inspectable', (await evaluate(`document.querySelector('#provenance').textContent`)).trim().length > 20, (await evaluate(`document.querySelector('#provenance').textContent`)).slice(0, 400));
    await tap('#export-feedback');
    await waitFor(`window.__t09Exports.some(x=>x.kind==='pilot-listening-feedback')`);
    const feedback = await evaluate(`window.__t09Exports.find(x=>x.kind==='pilot-listening-feedback')`);
    check('feedback retains sample and manifest without approval', feedback.entries.length === 1 && /^[a-f0-9]{64}$/.test(feedback.entries[0].manifest_sha256) && /^[a-f0-9]{64}$/.test(feedback.entries[0].sample_sha256) && feedback.entries[0].fixture === true && feedback.is_release_approval === false && feedback.is_acquisition_approval === false && feedback.is_sound_direction_acceptance === false && feedback.user_entered_notes_unverified === true, feedback);
    await evaluate(`document.querySelector('#listening-heading').scrollIntoView({block:'start'})`);
    await shot('playback');
    const currentPrompt = await evaluate(`document.querySelector('#prompt-card').textContent`);
    await tap('#prompt-next');
    const nextPrompt = await evaluate(`document.querySelector('#prompt-card').textContent`);
    check('prompter advances', currentPrompt !== nextPrompt, { before: currentPrompt.slice(0, 180), after: nextPrompt.slice(0, 180) });
    await tap('#prompt-prev');
    check('prompter returns to same prompt', (await evaluate(`document.querySelector('#prompt-card').textContent`)) === currentPrompt, 'Previous prompt restored');
    check('unanswered required decisions block take logging', await evaluate(`document.querySelector('#prompt-log').disabled`), await evaluate(`document.querySelector('#prompt-card .gate').textContent`));
    await tap('#prompt-repeat');
    await tap('#export-progress');
    await waitFor(`window.__t09Exports.some(x=>x.kind==='recording-prompt-progress')`);
    const progress = await evaluate(`window.__t09Exports.find(x=>x.kind==='recording-prompt-progress')`);
    check('progress retains original prompt and decision snapshot', progress.no_browser_recording === true && progress.entries.length === 1 && progress.entries[0].kind === 'repeat-needed' && /^[a-f0-9]{64}$/.test(progress.entries[0].prompts_json_sha256) && progress.entries[0].packet_id === progress.current_packet_id && progress.entries[0].prompt_snapshot.id === progress.entries[0].prompt_id && Object.keys(progress.entries[0].author_decisions_snapshot).length === 14, progress);
    const oldId = progress.current_packet_id;
    const originalPacket = await evaluate(`fetch('/prompts.json').then(r=>r.json())`);
    const replacement = { ...originalPacket, packet_id: `${oldId}-qa-replacement` };
    const replacementBytes = JSON.stringify(replacement);
    const replacementHash = crypto.createHash('sha256').update(replacementBytes).digest('hex');
    const replacementFile = path.join(scratch, `packet-${mobile ? 'mobile' : 'desktop'}.json`);
    await fs.writeFile(replacementFile, replacementBytes);
    const { root } = await send('DOM.getDocument');
    const { nodeId } = await send('DOM.querySelector', { nodeId: root.nodeId, selector: '#prompts-file' });
    await send('DOM.setFileInputFiles', { nodeId, files: [replacementFile] });
    await waitFor(`document.querySelector('#packet-status').textContent.includes(${JSON.stringify(replacement.packet_id)})`);
    await tap('#prompt-repeat');
    await tap('#export-progress');
    await waitFor(`window.__t09Exports.filter(x=>x.kind==='recording-prompt-progress').length === 2`);
    const replaced = await evaluate(`window.__t09Exports.filter(x=>x.kind==='recording-prompt-progress').at(-1)`);
    check('packet replacement preserves each progress identity', replaced.entries.length === 2 && replaced.entries[0].packet_id === oldId && replaced.entries[0].prompts_json_sha256 === progress.entries[0].prompts_json_sha256 && replaced.entries[1].packet_id === replacement.packet_id && replaced.entries[1].prompts_json_sha256 === replacementHash, replaced.entries.map(x=>({packet_id:x.packet_id,sha256:x.prompts_json_sha256})));
    await evaluate(`document.querySelector('#prompter-heading').scrollIntoView({block:'start'})`);
    await shot('prompter');
    check('no horizontal document overflow', await evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), await evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})'));
    await evaluate('scrollTo(0,0)');
    await shot('workbench');
    check('no non-loopback app requests', result.requests.every(x => x.startsWith(url.origin + '/') || x.startsWith('data:') || x.startsWith('blob:')), result.requests);
    check('no console/network exceptions', result.errors.length === 0, result.errors);
  } catch (error) {
    result.errors.push(error.message);
    await shot('failure').catch(() => {});
  } finally {
    await cdp.send('Target.disposeBrowserContext', { browserContextId });
  }
}

try {
  await startLocalServer();
  await withBrowser({ launch, connect: ws => CDP.connect(ws) }, async cdp => {
    report.browser = await cdp.send('Browser.getVersion');
    await cell(cdp, false);
    await cell(cdp, true);
  });
} catch (error) {
  report.fatal = error.message;
} finally {
  if (localServer) await stopBrowser(localServer);
}
report.ok = !report.fatal && report.cells.length === 2 && report.cells.every(x => x.errors.length === 0 && x.checks.every(c => c.status === 'PASS'));
report.code_hashes = {};
for (const rel of ['tools/verify_audio_pilot.mjs', 'tools/cdp_client.mjs', 'audio_pilot/app.js', 'audio_pilot/playback.js', 'audio_pilot/serve.py', 'audio_pilot/index.html', 'audio_pilot/style.css']) {
  report.code_hashes[rel] = crypto.createHash('sha256').update(await fs.readFile(path.join(repo, rel))).digest('hex');
}
await fs.mkdir(path.dirname(output), { recursive: true });
await fs.writeFile(output, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ ok: report.ok, report: output, screenshots: shots, cells: report.cells.map(c => ({ viewport: c.viewport, passed: c.checks.filter(x => x.status === 'PASS').length, errors: c.errors })) }, null, 2));
process.exitCode = report.ok ? 0 : 1;
