#!/usr/bin/env node
// Loopback-only, real-browser checks for source navigation and feature cleanup.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const arg = name => { const i = process.argv.indexOf(name); return i >= 0 ? process.argv[i + 1] : null; };
const out = path.resolve(arg('--out') || path.join(root, 'reader-evidence'));
if (fs.existsSync(out) && fs.readdirSync(out).length) throw new Error('Evidence directory must be empty.');
fs.mkdirSync(out, {recursive:true});
const require = createRequire(import.meta.url), {chromium} = require(arg('--playwright') || path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES || '', 'playwright'));
const chrome = arg('--chrome') || process.env.CHROME_BIN;
if (!chrome) throw new Error('Supply --chrome.');
const filtered = arg('--filtered');
const inputFiles = ['site/index.html','site/data/j.json','site/reader-features.js','studio/notes-reader.mjs'];
const inputHash = file => createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex');
const sourceHashes = Object.fromEntries(inputFiles.map(file => [file,inputHash(file)]));
const mime = {'.html':'text/html', '.js':'text/javascript', '.mjs':'text/javascript', '.json':'application/json', '.jpg':'image/jpeg', '.woff2':'font/woff2', '.css':'text/css'};
const wave = Buffer.alloc(44 + 16000); wave.write('RIFF',0); wave.writeUInt32LE(wave.length-8,4); wave.write('WAVEfmt ',8); wave.writeUInt32LE(16,16); wave.writeUInt16LE(1,20); wave.writeUInt16LE(1,22); wave.writeUInt32LE(8000,24); wave.writeUInt32LE(16000,28); wave.writeUInt16LE(2,32); wave.writeUInt16LE(16,34); wave.write('data',36); wave.writeUInt32LE(16000,40);
const server = http.createServer((req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  if (pathname === '/fixture.html') { res.setHeader('content-type','text/html'); return res.end('<!doctype html><title>Technical fixture</title><button id="outside">Outside</button><div id="fixture"></div>'); }
  if (pathname === '/fixture.wav') { res.setHeader('content-type','audio/wav'); return res.end(wave); }
  if (pathname === '/slow-fixture.wav') { res.setHeader('content-type','audio/wav'); return setTimeout(() => res.end(wave),150); }
  if (pathname === '/realization.html') { res.setHeader('content-type','text/html'); return res.end('<!doctype html><title>Technical realization fixture</title><p>Technical fixture</p>'); }
  const useFiltered = pathname.startsWith('/filtered/') && filtered;
  const base = useFiltered ? path.resolve(filtered) : root;
  const relative = (useFiltered ? pathname.slice('/filtered/'.length) : pathname.slice(1)) || 'site/index.html';
  const file = path.resolve(base, relative);
  if (!file.startsWith(base + path.sep)) { res.writeHead(403); return res.end(); }
  try { const data = fs.readFileSync(file); res.setHeader('content-type', mime[path.extname(file)] || 'application/octet-stream'); res.end(data); } catch { res.writeHead(404); res.end(); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = 'http://127.0.0.1:' + server.address().port, checks = [], errors = [];
let browser;
function pass(name, detail = true) { checks.push({name, pass:true, detail}); console.log('PASS ' + name); }
try {
  browser = await chromium.launch({executablePath:chrome, headless:true, args:['--no-sandbox','--disable-dev-shm-usage']});
  const context = await browser.newContext({viewport:{width:1280,height:900}, reducedMotion:'reduce'});
  await context.route('**/*', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort());
  const page = await context.newPage(); page.on('pageerror', e => errors.push(e.message));
  await page.goto(base + '/site/index.html');
  await page.waitForFunction(() => window.__jc?.items() > 0);
  assert.equal(await page.locator('[aria-label="Private feature preview"]').count(), 0);
  pass('private reader starts without feature controls or mounted media');
  const interrupted = await page.evaluate(async () => { const state = __jc.state; __jc.setState('lines','spiral'); __jc.setState('lines','poem'); await Promise.resolve(); await Promise.resolve(); return {before:state,after:__jc.state}; });
  assert.deepEqual(interrupted,{before:'lines-poem',after:'lines-poem'});
  pass('Spiral interrupted by the current layout cannot land late');
  await page.evaluate(() => __jc.setState('type','poem',{animate:false}));
  await page.waitForFunction(() => __jc.state === 'type-poem');
  const stack = await page.evaluate(() => { __jc.focusOn(__jc.tallest('f')); return {stack:__jc.stack(), bounds:__jc.stackBounds()}; });
  assert.ok(stack.stack?.n > 1);
  await page.evaluate(() => __jc.peel(1));
  const selected = await page.evaluate(() => ({stack:__jc.stack(), bounds:__jc.stackBounds(), source:__jc.source(), link:__jc.sourceLink()}));
  assert.notEqual(selected.stack.front, stack.stack.front);
  assert.equal(selected.stack.front, selected.source.versionId);
  assert.ok(selected.link.startsWith('#piece/'));
  assert.ok(Number.isFinite(selected.bounds.height) && selected.bounds.height > 0);
  assert.notEqual(selected.bounds.height, stack.bounds.height);
  pass('selected stack version drives source link and measured reading bounds', {before:stack,after:selected});
  await page.mouse.move(640,450); await page.mouse.wheel(0,100000);
  await page.waitForFunction(() => { const b = __jc.stackBounds(); return Math.abs(__jc.cam.y - b.bottom) < 1; });
  await page.keyboard.press('ArrowDown');
  assert.equal(await page.evaluate(() => __jc.cam.y <= __jc.stackBounds().bottom + .001),true);
  pass('wheel and keyboard scrolling stop at the selected version boundary');
  await page.goto(base + '/site/index.html' + selected.link);
  await page.reload();
  await page.waitForFunction(() => __jc?.side === 'book');
  assert.deepEqual(await page.evaluate(() => __jc.source()), selected.source);
  assert.equal(await page.evaluate(() => __jc.focusKey()), null);
  pass('stable source link reloads the exact version and clears canvas focus');
  await page.evaluate(() => { Object.defineProperty(document.fonts,'check',{configurable:true,value:()=>false}); __jc.setMode('hf'); });
  await page.getByText('Handwriting shown; font rendering is unavailable.',{exact:true}).waitFor();
  assert.equal(await page.locator('#hfplay').isDisabled(),true);
  await page.evaluate(() => { delete document.fonts.check; __jc.setMode('journal'); });
  assert.equal(await page.locator('#hfstage').count(),0);
  pass('Hand ↔ Font keeps handwriting available when the font fails and cleans up when leaving');
  assert.equal(await page.evaluate(async () => { try { await __jc.mountFeatures({fixture:true}); return false; } catch { return true; } }),true);
  await page.goto(base + '/site/index.html?private-features=1' + selected.link);
  await page.waitForFunction(() => __jc?.side === 'book');
  const actualBinding = await page.evaluate(() => __jc.sourceBinding());
  const actualData = JSON.parse(fs.readFileSync(path.join(root,'site/data/j.json'),'utf8'));
  assert.deepEqual(actualBinding, actualData.sourceBindings[selected.source.pieceId + '/' + selected.source.versionId]);
  assert.equal(await page.evaluate(async () => {
    const source = {...__jc.sourceBinding(),sourceFingerprint:'sha256:'+'f'.repeat(64)};
    try { await __jc.mountFeatures({fixture:true,source,audio:{url:'/fixture.wav',source}}); return false; } catch { return true; }
  }),true);
  assert.equal(await page.evaluate(async () => {
    const source = __jc.sourceBinding(), pending = __jc.mountFeatures({fixture:true,source,audio:{url:'/fixture.wav',source}});
    __jc.setMode('journal'); try { await pending; return false; } catch { return true; }
  }),true);
  await page.evaluate(async () => { const source = __jc.sourceBinding(); return __jc.mountFeatures({fixture:true, source,audio:{url:'/fixture.wav',source}}); });
  await page.getByRole('button',{name:'Audio',exact:true}).click();
  assert.equal(await page.locator('audio').evaluate(e => e.paused),true);
  await page.evaluate(() => { location.hash = '#piece/withheld/version-withheld'; });
  await page.getByText('This source version is unavailable in this release.',{exact:true}).waitFor();
  assert.equal(await page.locator('audio').count(),0);
  assert.equal(await page.getByRole('button',{name:'Audio',exact:true}).isDisabled(),true);
  pass('reader feature adapter checks the actual canonical fingerprint and rejects source changes during load');
  const missingBindingData = structuredClone(actualData);
  delete missingBindingData.sourceBindings[selected.source.pieceId + '/' + selected.source.versionId];
  await page.route('**/site/data/j.json', route => route.fulfill({json:missingBindingData}),{times:1});
  await page.goto(base + '/site/index.html?private-features=1&binding-fixture=missing' + selected.link);
  await page.waitForFunction(() => __jc?.side === 'book');
  assert.equal(await page.evaluate(() => __jc.sourceBinding()),null);
  assert.equal(await page.evaluate(async source => { try { await __jc.mountFeatures({fixture:true,source,audio:{url:'/fixture.wav',source}}); return false; } catch { return true; } },actualBinding),true);
  pass('missing canonical source binding refuses private features while stable navigation remains available');
  const unavailableAnchorData = structuredClone(actualData);
  unavailableAnchorData.sourceAnchors = {...unavailableAnchorData.sourceAnchors, 'diary1-0-0':{status:'unavailable',reason:'technical-browser-fixture'}};
  assert.ok(unavailableAnchorData.pages.find(p => p.id === 'diary1').x.some(row => row[0] === 0 && row[1] === 0));
  await page.route('**/site/data/j.json', route => route.fulfill({json:unavailableAnchorData}),{times:1});
  await page.goto(base + '/site/index.html?anchor-fixture=unavailable#study-diary1');
  await page.waitForFunction(() => __jc?.side === 'book');
  assert.equal(await page.locator('#bstage rect[data-k="0-0"]').count(),0);
  assert.equal(await page.locator('#bstage .ln[data-k="0-0"]').evaluate(e => e.classList.contains('has')),false);
  pass('canonical unavailable anchors suppress alignment even when a preserved geometry row exists');
  await page.goto(base + '/site/index.html#piece/withheld/version-withheld');
  await page.getByText('This source version is unavailable in this release.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(() => location.hash), '#piece/withheld/version-withheld');
  pass('unavailable stable source link remains explicit and does not substitute another version');
  await page.goto(base + '/fixture.html');
  await page.evaluate(async () => {
    const features = await import('/site/reader-features.js'), notes = await import('/studio/notes-reader.mjs');
    window.F = features; window.fixtureSource = {pieceId:'fixture-piece',versionId:'fixture-version',sourceFingerprint:'sha256:'+'a'.repeat(64)};
    const host = document.getElementById('fixture');
    window.preview = features.mountPrivateFeaturePreview(host,{source:fixtureSource});
    window.disabledEmpty = host.childNodes.length === 0;
    window.bindingRejections = [];
    for (const descriptor of [{url:'/fixture.wav'}, {url:'/fixture.wav',source:{...fixtureSource,versionId:'other-version'}}, {url:'/fixture.wav',source:{...fixtureSource,sourceFingerprint:'sha256:'+'b'.repeat(64)}}]) {
      try { features.mountPrivateFeaturePreview(host,{enabled:true,source:fixtureSource,audio:descriptor}); bindingRejections.push(false); } catch { bindingRejections.push(true); }
    }
    window.preview = features.mountPrivateFeaturePreview(host,{enabled:true, source:fixtureSource, audio:{url:'/fixture.wav',source:fixtureSource}, realization:{url:'/realization.html',source:fixtureSource}, regions:{url:'/never-load.jpg',source:fixtureSource,sourceAnchor:{status:'unavailable',box:null}}, notes:[{id:'fixture-note',revisionId:'fixture-revision',family:'note',kind:'footnote',pieceId:'fixture-piece',versionId:'fixture-version',lineId:null,word:null,text:'TECHNICAL FIXTURE note',citations:[],credit:'Technical fixture',poemDate:{certainty:'unknown',value:null},noteDate:'2026-11-06',fixture:true}],renderNotes:notes.mountNotesReader});
  });
  assert.equal(await page.evaluate(() => disabledEmpty),true);
  assert.deepEqual(await page.evaluate(() => bindingRejections),[true,true,true]);
  pass('missing, foreign, and stale asset source bindings fail before mount');
  await page.getByRole('button',{name:'Notes',exact:true}).click();
  await page.getByText('TECHNICAL FIXTURE note',{exact:true}).waitFor();
  await page.keyboard.press('Escape');
  assert.equal(await page.getByText('TECHNICAL FIXTURE note',{exact:true}).count(),0);
  assert.equal(await page.evaluate(() => document.activeElement.textContent),'Notes');
  pass('shared notes lifecycle reveals only on request and restores focus on Escape');
  await page.getByRole('button',{name:'Audio',exact:true}).click();
  const media = await page.locator('audio').evaluateHandle(e => e);
  assert.equal(await media.evaluate(e => e.paused && !e.autoplay),true);
  await media.evaluate(e => e.play());
  await page.keyboard.press('Escape');
  assert.equal(await media.evaluate(e => e.paused && !e.hasAttribute('src')),true);
  pass('audio requires explicit play and unloads on close');
  await page.getByRole('button',{name:'Source regions',exact:true}).click();
  assert.equal(await page.locator('img').count(),0);
  await page.getByText('Source line geometry is unavailable. No region has been substituted.',{exact:true}).waitFor();
  await page.locator('#outside').click();
  pass('unavailable source geometry does not load or invent an anchor');
  await page.getByRole('button',{name:'Realization',exact:true}).click();
  assert.equal(await page.locator('iframe').count(),0);
  await page.getByRole('button',{name:'Start realization'}).click();
  assert.equal(await page.locator('iframe').count(),1);
  await page.locator('#outside').click();
  assert.equal(await page.locator('iframe').count(),0);
  pass('realization starts explicitly and outside dismissal destroys its frame');
  const waveDigest = 'sha256:' + createHash('sha256').update(wave).digest('hex');
  await page.evaluate(() => { preview.destroy(); preview = F.mountPrivateFeaturePreview(document.getElementById('fixture'), {enabled:true,source:fixtureSource,audio:{url:'/fixture.wav',source:fixtureSource,sha256:'sha256:'+'f'.repeat(64)}}); });
  await page.getByRole('button',{name:'Audio',exact:true}).click();
  await page.getByText('Preview asset digest does not match.',{exact:true}).waitFor();
  assert.equal(await page.locator('audio').count(),0);
  await page.evaluate(digest => { preview.destroy(); preview = F.mountPrivateFeaturePreview(document.getElementById('fixture'), {enabled:true,source:fixtureSource,audio:{url:'/fixture.wav',source:fixtureSource,sha256:digest}}); },waveDigest);
  await page.getByRole('button',{name:'Audio',exact:true}).click(); await page.locator('audio').waitFor();
  assert.equal(await page.locator('audio').evaluate(e => e.paused && e.src.startsWith('blob:')),true);
  await page.evaluate(digest => { preview.destroy(); preview = F.mountPrivateFeaturePreview(document.getElementById('fixture'), {enabled:true,source:fixtureSource,audio:{url:'/slow-fixture.wav',source:fixtureSource,sha256:digest}}); },waveDigest);
  await page.getByRole('button',{name:'Audio',exact:true}).click(); await page.keyboard.press('Escape'); await page.waitForTimeout(200);
  assert.equal(await page.locator('audio').count(),0); assert.equal(await page.evaluate(()=>preview.lifecycle.isOpen),false);
  pass('audio digest mismatch refuses mount; verified bytes remain paused; dismissal cancels a pending load');
  const cleanup = await page.evaluate(async () => {
    preview.destroy(); const host = document.getElementById('fixture'); const trigger = document.getElementById('outside');
    const life = F.createReaderLifecycle({host}); let cleaned = 0, late = 0, aborted = false;
    const render = scope => { scope.own(() => cleaned++); scope.signal.addEventListener('abort',()=>aborted=true); scope.delay(()=>late++,100); };
    life.open({trigger,render,timeout:20}); await new Promise(r=>setTimeout(r,50));
    const timedOut = !life.isOpen && cleaned===1 && aborted;
    life.open({trigger,render}); document.dispatchEvent(new CustomEvent('reader:sourcechange'));
    const switched = !life.isOpen && cleaned===2;
    life.open({trigger,render}); Object.defineProperty(document,'hidden',{configurable:true,value:true}); document.dispatchEvent(new Event('visibilitychange')); delete document.hidden;
    const hidden = !life.isOpen && cleaned===3;
    life.open({trigger,render}); life.destroy(); await new Promise(r=>setTimeout(r,130));
    let rejected = false; try {life.open({render});} catch {rejected=true;}
    return {timedOut,switched,hidden,destroyed:cleaned===4,rejected,late,failures:life.cleanupErrors.length};
  });
  assert.deepEqual(cleanup,{timedOut:true,switched:true,hidden:true,destroyed:true,rejected:true,late:0,failures:0});
  pass('timeout/source/visibility/destroy cancel owned work and reject reopen',cleanup);
  if (filtered) {
    await page.goto(base + '/filtered/index.html'); await page.waitForFunction(()=>__jc?.items()>0);
    await page.evaluate(()=>{__jc.open();__jc.setMode('rev');});
    await page.getByText('Revisions are unavailable in this release.',{exact:true}).waitFor();
    await page.evaluate(()=>__jc.setMode('hf'));
    await page.getByText('Hand ↔ Font is unavailable for this source.',{exact:true}).waitFor();
    await page.goto(base + '/filtered/index.html#piece/p001/p001-diary1-0'); await page.waitForFunction(()=>__jc?.side==='book');
    assert.equal(await page.evaluate(()=>__jc.source()?.versionId),'p001-diary1-0');
    await page.goto(base + '/filtered/index.html#piece/p002/p002-diary1-1');
    await page.getByText('This source version is unavailable in this release.',{exact:true}).waitFor();
    pass('nonempty filtered release handles empty PAL/HF and rejects withheld versions');
  }
  await context.close();
  const mobile = await browser.newContext({viewport:{width:390,height:844}, deviceScaleFactor:3, isMobile:true, hasTouch:true, colorScheme:'dark', reducedMotion:'reduce'});
  await mobile.route('**/*', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort());
  const touch = await mobile.newPage(); touch.on('pageerror', error => errors.push(error.message));
  await touch.goto(base + '/site/index.html'); await touch.waitForFunction(() => __jc?.items() > 0);
  await touch.evaluate(() => __jc.setState('type','poem',{animate:false})); await touch.waitForFunction(() => __jc.state === 'type-poem');
  const beforeTouch = await touch.evaluate(() => { __jc.focusOn(__jc.tallest('f')); return {y:__jc.cam.y,front:__jc.stack().front}; });
  const cdp = await mobile.newCDPSession(touch);
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:190,y:620}]});
  await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:190,y:360}]});
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  assert.equal(await touch.evaluate(y => __jc.cam.y > y, beforeTouch.y),true);
  assert.equal(await touch.evaluate(() => __jc.stack().front),beforeTouch.front);
  await touch.setViewportSize({width:844,height:390});
  await touch.waitForFunction(() => innerWidth === 844 && __jc.stackBounds()?.width > 0);
  await touch.waitForTimeout(150);
  await touch.evaluate(() => __jc.ui(true));
  const bounds = await touch.locator('#pill').boundingBox();
  assert.ok(bounds.x >= 0 && bounds.x + bounds.width <= 845 && bounds.y + bounds.height <= 391);
  assert.equal(await touch.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true);
  await touch.evaluate(() => { __jc.ui(false); __jc.zoom(1.1); });
  await touch.keyboard.press('Escape'); assert.equal(await touch.evaluate(() => __jc.focusKey()),null);
  pass('mobile dark/reduced-motion touch scroll preserves selected version; rotation, control bounds, zoom and focus exit stay usable');
  await mobile.close();
  assert.deepEqual(Object.fromEntries(inputFiles.map(file => [file,inputHash(file)])),sourceHashes);
  assert.deepEqual(errors,[]);
  pass('no uncaught browser exceptions');
} finally {
  if (browser) await browser.close(); await new Promise(resolve=>server.close(resolve));
  fs.writeFileSync(path.join(out,'reader-integration.json'),JSON.stringify({checks,errors,sourceHashes,filteredArtifact:filtered || null,physicalDevices:'not tested'},null,2)+'\n');
}
