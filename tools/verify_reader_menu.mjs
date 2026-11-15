#!/usr/bin/env node
// Loopback-only browser acceptance for discovery, real artwork, input and palettes.
// Run against the private source or pass --html to verify a prepared reader shell.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import silentBrowser from './silent_browser.cjs'; const {silentLaunch, silentChromeArgs} = silentBrowser;

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const arg = name => { const i = process.argv.indexOf(name); return i < 0 ? null : process.argv[i + 1]; };
const output = path.resolve(arg('--out') || path.join(root, 'menu-evidence'));
if (fs.existsSync(output) && fs.readdirSync(output).length) throw new Error('Evidence directory must be new or empty.');
fs.mkdirSync(output, {recursive:true});
const require = createRequire(import.meta.url);
const playwright = require(arg('--playwright') || path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES || '', 'playwright'));
const engine = arg('--browser') || 'chromium';
if (!['chromium', 'webkit', 'firefox'].includes(engine)) throw new Error('Unknown browser engine.');
const viewportCases = [
  {name:'phone', width:390, height:844, touch:true},
  {name:'desktop', width:1280, height:900, touch:false},
  {name:'narrow-phone', width:320, height:568, touch:true},
  {name:'landscape', width:844, height:390, touch:true},
];
const selectedViewports = arg('--viewports')?.split(',') || viewportCases.map(v => v.name);
assert.ok(selectedViewports.length && selectedViewports.every(name => viewportCases.some(v => v.name === name)), 'Unknown viewport selection.');
const html = arg('--html') ? path.resolve(arg('--html')) : path.join(root, 'site/index.html');
const htmlBytes = fs.readFileSync(html), sha = bytes => createHash('sha256').update(bytes).digest('hex');
const checks = [], pageErrors = [], assetErrors = [];
const report = {engine, viewports:selectedViewports, readerSha256:sha(htmlBytes), checks, pageErrors, assetErrors, physicalDevices:'not tested'};
const types = {'.html':'text/html; charset=utf-8', '.json':'application/json', '.js':'text/javascript', '.mjs':'text/javascript', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.png':'image/png', '.svg':'image/svg+xml', '.webp':'image/webp', '.woff2':'font/woff2', '.css':'text/css'};
const server = http.createServer((req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  const file = path.resolve(root, '.' + pathname);
  if (!file.startsWith(root + path.sep)) { res.writeHead(403); res.end(); return; }
  try {
    res.setHeader('content-type', types[path.extname(file)] || 'application/octet-stream');
    res.end(pathname === '/site/index.html' ? htmlBytes : fs.readFileSync(file));
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = 'http://127.0.0.1:' + server.address().port;
const pass = (name, details) => { checks.push({name, pass:true, ...(details ? {details} : {})}); console.log('PASS ' + name); };
const screenshot = (page, name) => page.screenshot({path:path.join(output, name + '.png')});
const activate = async (locator, touch) => { await locator.scrollIntoViewIfNeeded(); await (touch ? locator.tap() : locator.click()); };
const readerState = page => page.evaluate(() => ({hash:location.hash, focus:__jc.focusKey(), cam:{...__jc.cam}, book:__jc.book()}));
const visible = locator => locator.isVisible();
let browser, activePage;

async function assertReaderShortcutsBlocked(page, context) {
  const snapshot = () => page.evaluate(() => {
    const stack = __jc.stack();
    return {side:__jc.side, transfer:__jc.xfer, hash:location.hash, focus:__jc.focusKey(), cam:{...__jc.cam}, book:__jc.book(), version:stack ? {front:stack.front, target:stack.pt} : null};
  });
  const before = await snapshot();
  for (const key of ['ArrowRight', 'b', '=', '-', '[', ']']) {
    await page.keyboard.press(key);
    assert.deepEqual(await snapshot(), before, context + ': ' + key + ' must not change the reader underneath open controls.');
  }
}

async function assertVisibleLabels(menu) {
  const labels = await menu.locator('button').evaluateAll(buttons => {
    const shown = buttons.filter(b => b.getClientRects().length);
    return {count:shown.length, missing:shown.filter(b => !b.textContent.trim()).map(b => b.id || b.getAttribute('aria-label'))};
  });
  assert.ok(labels.count > 0, 'The open menu contains command buttons.');
  assert.deepEqual(labels.missing, [], 'Visible menu commands, including dynamic draft selectors, need visible text.');
}

// Content records can be ready hundreds of milliseconds before atlas images paint.
// Sample the actual canvas so blank screenshots cannot count as loaded-work evidence.
async function waitForWork(page) {
  await page.waitForFunction(() => window.__jc?.items() > 0);
  await page.waitForFunction(() => {
    const c = document.querySelector('#cv');
    if (!c?.width || !c.height || !__jc.stats.drawn) return false;
    const p = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
    let different = 0;
    for (let i = 0; i < p.length; i += 64) {
      if (p[i] !== p[0] || p[i+1] !== p[1] || p[i+2] !== p[2]) different++;
      if (different >= 100) return true;
    }
    return false;
  }, null, {timeout:20000});
  await page.waitForFunction(() => __jc.settled && __jc.mem().pend === 0);
}

async function assertClosedFocus(page, launcher) {
  assert.equal(await launcher.getAttribute('aria-expanded'), 'false');
  assert.equal(await visible(page.locator('#ov')), false);
  assert.equal(await page.locator('#b-info').evaluate(e => { e.focus(); return e === document.activeElement; }), false, 'A closed menu cannot receive focus.');
  await launcher.focus();
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => !!document.activeElement.closest('#ov,.panel')), false, 'Tab must skip hidden navigation and panels.');
  }
  await launcher.focus();
}

async function assertPalette(page, name) {
  const colors = await page.evaluate(() => {
    const resolve = variable => {
      const swatch = document.createElement('span');
      swatch.style.color = 'var(' + variable + ')'; document.body.appendChild(swatch);
      const color = getComputedStyle(swatch).color; swatch.remove(); return color;
    };
    const read = element => {
      const cs = getComputedStyle(element);
      return {color:cs.color, background:cs.backgroundColor, fill:cs.fill, filter:cs.filter, blend:cs.mixBlendMode};
    };
    return {
      canvas:resolve('--desk'), ink:resolve('--ink'),
      launcher:read(document.querySelector('#b-menu')),
      glyph:read(document.querySelector('#b-menu .author-menu-mark')),
      // WebKit defers restyling previously rendered display:none descendants.
      // Inspect painted marks here; each palette is also tested with About open.
      badges:[...document.querySelectorAll('.author-badge')].filter(e => e.getClientRects().length).map(read),
      crowns:[...document.querySelectorAll('.author-crown-mark')].filter(e => e.getClientRects().length).map(read)
    };
  });
  assert.equal(colors.launcher.background, colors.ink, name + ': launcher backing uses the current text color.');
  assert.equal(colors.launcher.color, colors.canvas, name + ': launcher uses the current canvas color.');
  assert.equal(colors.glyph.fill, colors.canvas, name + ': author glyph uses the current canvas color.');
  assert.ok(colors.badges.length && colors.crowns.length, 'Author crown must be present.');
  for (const badge of colors.badges) {
    assert.equal(badge.background, colors.ink);
    assert.equal(badge.color, colors.canvas);
  }
  for (const crown of colors.crowns) assert.equal(crown.fill, colors.canvas);
  for (const part of [colors.launcher, colors.glyph, ...colors.badges, ...colors.crowns]) {
    assert.equal(part.filter, 'none', 'Palette inversion must not apply an RGB inversion filter.');
    assert.equal(part.blend, 'normal', 'Palette inversion must not depend on the underlying artwork.');
  }
  pass(name + ': launcher and crown swap the selected canvas/text colors', colors);
}

async function checkPanel(page, touch, launcher, {trigger, panel, close, name}) {
  if (await launcher.getAttribute('aria-expanded') !== 'true') await activate(launcher, touch);
  await activate(page.locator(trigger), touch);
  await page.locator(panel).waitFor({state:'visible'});
  assert.equal(await page.locator(panel).evaluate(e => e.contains(document.activeElement)), true, name + ' must receive focus.');
  await assertReaderShortcutsBlocked(page, name);
  await page.keyboard.press('Escape');
  assert.equal(await visible(page.locator(panel)), false, 'Escape closes the active panel first.');
  assert.equal(await launcher.getAttribute('aria-expanded'), 'true', 'Closing a panel preserves the open menu.');
  assert.equal(await page.evaluate(() => document.activeElement.id), trigger.slice(1));
  await activate(page.locator(trigger), touch);
  await activate(page.locator(close), touch);
  assert.equal(await visible(page.locator(panel)), false);
  assert.equal(await page.evaluate(() => document.activeElement.id), trigger.slice(1));
  pass(name + ': keyboard isolation, Escape and close restore the opener');
}

try {
  browser = await silentLaunch(playwright[engine], {headless:true, ...(arg('--executable') ? {executablePath:arg('--executable')} : {})});
  for (const size of viewportCases.filter(v => selectedViewports.includes(v.name))) {
    const context = await browser.newContext({viewport:{width:size.width, height:size.height}, hasTouch:size.touch, isMobile:size.touch, reducedMotion:'reduce', colorScheme:'light'});
    await context.route('**/*', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort());
    const page = activePage = await context.newPage();
    page.setDefaultTimeout(10000);
    page.on('pageerror', e => pageErrors.push({viewport:size.name, message:e.message}));
    page.on('response', r => { if (r.status() >= 400) assetErrors.push({viewport:size.name, status:r.status(), url:r.url().replace(base,'')}); });
    await page.goto(base + '/site/index.html');
    await waitForWork(page);
    pass(size.name + ': actual artwork has painted', await page.evaluate(() => ({items:__jc.items(), drawn:__jc.stats.drawn, memory:__jc.mem()})));

    const launcher = page.getByRole('button', {name:'Menu', exact:true});
    assert.equal(await visible(launcher), true, 'The Menu button must be visible without prior interaction.');
    const id = await launcher.getAttribute('id');
    assert.ok(id, 'The menu launcher needs a stable identity for focus restoration.');
    assert.equal(await launcher.getAttribute('aria-controls'), 'ov');
    const bounds = await launcher.boundingBox();
    assert.ok(bounds.width >= 48 && bounds.height >= 48, 'Launcher is at least 48 × 48 CSS pixels.');
    assert.ok(bounds.x >= 0 && bounds.y >= 0 && bounds.x + bounds.width <= size.width && bounds.y + bounds.height <= size.height);
    assert.equal(await launcher.evaluate(e => { const r=e.getBoundingClientRect(); return e.contains(document.elementFromPoint(r.x+r.width/2, r.y+r.height/2)); }), true, 'The launcher is not covered by reader content.');
    assert.equal(await visible(page.locator('#b-info')), false);
    await assertClosedFocus(page, launcher);
    await screenshot(page, size.name + '-closed');
    pass(size.name + ': visible unobstructed launcher and no hidden tab stops', bounds);

    await activate(launcher, size.touch);
    assert.equal(await launcher.getAttribute('aria-expanded'), 'true');
    const menu = page.locator('#ov');
    await menu.waitFor({state:'visible'});
    assert.match(await page.locator('#b-info').innerText(), /about/i);
    assert.match(await page.locator('#b-help').innerText(), /how to explore/i);
    assert.match(await page.locator('#b-search').innerText(), /search/i);
    assert.equal(await visible(page.locator('#b-more')), false);
    const menuBounds = await menu.boundingBox();
    assert.ok(menuBounds.x >= 0 && menuBounds.y >= 0 && menuBounds.x + menuBounds.width <= size.width + 1 && menuBounds.y + menuBounds.height <= size.height + 1, 'Open menu stays within the viewport.');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Menu cannot create page-level horizontal overflow.');
    await assertVisibleLabels(menu);
    const untitledGroups = await menu.locator('[role="group"]').evaluateAll(groups => groups.filter(g => getComputedStyle(g).display !== 'none' && !g.getAttribute('aria-label') && !g.getAttribute('aria-labelledby')).map(g => g.id || g.className));
    assert.deepEqual(untitledGroups, [], 'Control groups have identifiable purposes.');
    await screenshot(page, size.name + '-menu');
    pass(size.name + ': one action exposes grouped labeled controls within the viewport');
    await page.locator('#menu-close').focus();
    await page.keyboard.press('Shift+Tab');
    assert.equal(await menu.evaluate(e => e.contains(document.activeElement)), true, 'Backward Tab remains inside the open modal menu.');
    assert.notEqual(await page.evaluate(() => document.activeElement.id), 'menu-close');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'menu-close', 'Forward Tab wraps to the menu close control.');

    if (size.name === 'phone') {
      // This exceeds both historical auto-dismiss timers (2.8 and 6 seconds).
      await page.waitForTimeout(6500);
      assert.equal(await launcher.getAttribute('aria-expanded'), 'true');
      pass('menu stays open while the reader is deciding');
      await activate(page.locator('[data-c="pages"]'), true);
      await page.waitForFunction(() => __jc.state.startsWith('pages-') && __jc.settled);
      assert.equal(await page.locator('[data-c="pages"]').getAttribute('aria-pressed'), 'true');
      assert.equal(await launcher.getAttribute('aria-expanded'), 'true');
      pass('display selection changes the artwork and keeps its controls available');
    }

    await activate(page.locator('[data-a="spiral"]'), size.touch);
    await page.waitForFunction(() => __jc.state.endsWith('-spiral') && __jc.settled);
    assert.equal(await page.locator('[data-a="spiral"]').getAttribute('aria-pressed'), 'true');
    await page.locator('[data-a="spiral"]').focus();
    await assertReaderShortcutsBlocked(page, size.name + ' menu');
    await page.keyboard.press('Escape');
    assert.equal(await launcher.getAttribute('aria-expanded'), 'false');
    assert.equal(await page.evaluate(() => document.activeElement.id), id);
    await page.keyboard.press('Escape');
    assert.equal(await launcher.getAttribute('aria-expanded'), 'false', 'Escape must not reopen a closed menu.');
    pass(size.name + ': selection works, keys stay in the menu and Escape restores focus');
    if (size.name === 'desktop') {
      const beforePan = await page.evaluate(() => __jc.cam.x);
      await page.keyboard.press('ArrowRight');
      const afterPan = await page.evaluate(() => __jc.cam.x);
      assert.ok(afterPan > beforePan, 'ArrowRight must resume canvas navigation while the closed launcher retains focus after Escape.');
      const beforeZoom = await page.evaluate(() => __jc.cam.s);
      await page.keyboard.press('=');
      const afterZoom = await page.evaluate(() => __jc.cam.s);
      assert.ok(afterZoom > beforeZoom, 'Zoom-in shortcut remains available after Escape.');
      await page.keyboard.press('-');
      assert.ok(await page.evaluate(() => __jc.cam.s) < afterZoom, 'Zoom-out shortcut remains available after Escape.');
      assert.equal(await page.evaluate(() => document.activeElement.id), id);
      assert.equal(await launcher.getAttribute('aria-expanded'), 'false');
      pass('closed launcher resumes canvas navigation and zoom after Escape', {beforePan, afterPan, beforeZoom, afterZoom});
    }

    await launcher.press('Enter');
    assert.equal(await launcher.getAttribute('aria-expanded'), 'true');
    await page.keyboard.press('Escape');
    await launcher.press('Space');
    assert.equal(await launcher.getAttribute('aria-expanded'), 'true');
    await page.locator('#menu-close').press('Enter');
    assert.equal(await launcher.getAttribute('aria-expanded'), 'false');
    assert.equal(await page.evaluate(() => document.activeElement.id), id);
    pass(size.name + ': native Enter/Space open once and explicit close restores focus');
    if (size.name === 'desktop') {
      const beforePan = await page.evaluate(() => __jc.cam.x);
      await page.keyboard.press('ArrowRight');
      assert.ok(await page.evaluate(() => __jc.cam.x) > beforePan, 'ArrowRight remains available after explicit Close.');
      const beforeZoom = await page.evaluate(() => __jc.cam.s);
      await page.keyboard.press('=');
      assert.ok(await page.evaluate(() => __jc.cam.s) > beforeZoom, 'Zoom remains available after explicit Close.');
      await page.keyboard.press('-');
      assert.equal(await page.evaluate(() => document.activeElement.id), id);
      assert.equal(await launcher.getAttribute('aria-expanded'), 'false');
      pass('closed launcher resumes canvas navigation and zoom after Close');

      await page.keyboard.press('b');
      await page.waitForFunction(() => __jc.side === 'book' && !__jc.xfer);
      assert.equal(await page.evaluate(() => document.activeElement.id), id);
      await page.keyboard.press('Home');
      await page.waitForFunction(() => __jc.book().pid === 'diary1');
      const firstPage = await page.evaluate(() => __jc.book().pid);
      await page.keyboard.press('ArrowRight');
      await page.waitForFunction(pid => __jc.book().pid !== pid, firstPage);
      assert.equal(await launcher.getAttribute('aria-expanded'), 'false');
      await page.keyboard.press('b');
      await page.waitForFunction(() => __jc.side === 'canvas' && !__jc.xfer);
      assert.equal(await page.evaluate(() => document.activeElement.id), id);
      pass('closed launcher preserves B switching and journal keyboard navigation');
    }
    if (size.touch) {
      await launcher.tap();
      await page.locator('#menu-close').tap();
      assert.equal(await launcher.getAttribute('aria-expanded'), 'false');
      assert.equal(await page.evaluate(() => document.activeElement.id), id);
      pass(size.name + ': real touch opens and explicitly closes the menu');
    }
    if (size.name === 'desktop') {
      await launcher.press('/');
      assert.equal(await page.locator('#q').evaluate(e => e === document.activeElement), true, 'Search shortcut works after focus returns to the closed launcher.');
      await page.keyboard.type('a/b');
      assert.equal(await page.locator('#q').inputValue(), 'a/b', 'A slash typed in a search field remains text.');
      await page.keyboard.press('Escape');
      await page.keyboard.press('Escape');
      pass('search shortcut remains available after keyboard dismissal');
    }

    await checkPanel(page, size.touch, launcher, {trigger:'#b-info', panel:'#infop', close:'#i-x', name:size.name + ' About'});
    assert.equal(await visible(page.locator('#about-author')), false);
    assert.equal((await page.locator('#about-author').textContent()).trim(), '');
    assert.equal(await page.locator('#i-src').count(), 1);
    assert.equal(await page.locator('#i-tr').count(), 1);
    await checkPanel(page, size.touch, launcher, {trigger:'#b-help', panel:'#helpp', close:'#h-x', name:size.name + ' Help'});
    if (size.name === 'phone') {
      await activate(page.locator('#b-info'), true); await screenshot(page, 'phone-about'); await activate(page.locator('#i-x'), true);
      await activate(page.locator('#b-help'), true); await screenshot(page, 'phone-help'); await activate(page.locator('#h-x'), true);
    }
    pass(size.name + ': author About remains empty and distinct from technical Help');

    await activate(page.locator('#b-search'), size.touch);
    assert.equal(await page.locator('#q').evaluate(e => e === document.activeElement), true);
    await page.keyboard.press('Escape');
    assert.equal(await visible(page.locator('#searchp')), false);
    assert.equal(await page.evaluate(() => document.activeElement.id), 'b-search');
    await activate(page.locator('#b-search'), size.touch);
    await activate(page.locator('#q-x'), size.touch);
    assert.equal(await visible(page.locator('#searchp')), false);
    assert.equal(await page.evaluate(() => document.activeElement.id), 'b-search');
    pass(size.name + ': Search receives input focus and restores it on dismissal');

    const beforeOutside = await readerState(page);
    if (size.touch) await page.locator('#menu-backdrop').tap({position:{x:2,y:2}}); else await page.mouse.click(2, 2);
    // The former canvas gesture dispatcher delayed single taps; catch click-through.
    await page.waitForTimeout(400);
    assert.equal(await launcher.getAttribute('aria-expanded'), 'false');
    assert.deepEqual(await readerState(page), beforeOutside);
    pass(size.name + ': outside dismissal does not also activate or move the reader');

    if (size.name === 'desktop') {
      await activate(launcher, false);
      await activate(page.locator('#b-search'), false);
      await page.locator('#q').fill('the');
      await page.locator('#results .go').first().waitFor({state:'visible'});
      await page.locator('#results .go').first().click();
      await page.waitForFunction(() => __jc.focusKey() || __jc.side === 'book');
      assert.equal(await visible(page.locator('#searchp')), false);
      assert.equal(await launcher.getAttribute('aria-expanded'), 'false');
      assert.equal(await page.evaluate(() => !!document.activeElement.closest('#ov,.panel')), false, 'A search result cannot leave focus inside the dismissed controls.');
      pass('search result enters existing work and dismisses its controls cleanly');
    }

    if (size.name === 'phone') {
      await activate(launcher, true);
      const markBounds = await page.locator('#b-menu .author-menu-mark').evaluate(e => { const b=e.getBBox(); return {width:b.width,height:b.height}; });
      assert.ok(markBounds.width > 0 && markBounds.height > 0, 'The supplied menu mark must contain rendered geometry.');
      const crownBounds = await page.locator('.author-crown-mark').evaluateAll(els => els.filter(e => e.getClientRects().length).map(e => { const b=e.getBBox(); return {width:b.width,height:b.height}; }));
      assert.ok(crownBounds.length && crownBounds.every(b => b.width > 0 && b.height > 0), 'The visible supplied crown must contain rendered geometry.');
      await assertPalette(page, 'light palette');
      await activate(page.locator('#b-info'), true);
      await assertPalette(page, 'light About palette');
      await activate(page.locator('#i-x'), true);
      await activate(page.locator('#b-theme'), true);
      await page.waitForFunction(() => document.documentElement.dataset.theme === 'dark');
      await assertPalette(page, 'dark palette');
      await page.waitForFunction(() => !document.querySelector('#veil'));
      await screenshot(page, 'phone-dark-menu');
      await activate(page.locator('#b-info'), true);
      await assertPalette(page, 'dark About palette');
      await activate(page.locator('#i-x'), true);
      await page.evaluate(() => { document.documentElement.style.setProperty('--desk','#17365b'); document.documentElement.style.setProperty('--ink','#f4bc53'); });
      // The existing theme action rereads the overridden palette for canvas paint.
      await activate(page.locator('#b-theme'), true);
      await page.waitForFunction(() => !document.querySelector('#veil'));
      await assertPalette(page, 'custom blue/gold palette');
      await screenshot(page, 'phone-custom-palette');
      await activate(page.locator('#b-info'), true);
      await assertPalette(page, 'custom blue/gold About palette');
      await activate(page.locator('#i-x'), true);
      await page.reload();
      await waitForWork(page);
    }

    await page.goto(base + '/site/index.html#study-diary1');
    await page.waitForFunction(() => window.__jc?.side === 'book' && !__jc.xfer);
    await activate(launcher, size.touch);
    assert.equal(await visible(page.locator('[data-c="pages"]')), false);
    assert.equal(await visible(page.locator('[data-v="study"]')), true);
    assert.match(await page.locator('[data-v="study"]').innerText(), /scan|text|study/i);
    await activate(page.locator('[data-v="scan"]'), size.touch);
    await page.waitForFunction(() => __jc.book().view === 'scan');
    assert.equal(await visible(page.locator('#b-clean')), false);
    assert.equal(await visible(page.locator('#b-outline')), false);
    await activate(page.locator('[data-v="words"]'), size.touch);
    await page.waitForFunction(() => __jc.book().view === 'words');
    assert.equal(await visible(page.locator('#b-clean')), true);
    await activate(page.locator('[data-v="study"]'), size.touch);
    await page.waitForFunction(() => __jc.book().view === 'study');
    assert.equal(await visible(page.locator('#b-hand')), true);
    await assertVisibleLabels(menu);
    await screenshot(page, size.name + '-journal-menu');
    pass(size.name + ': journal view controls change correctly with reading context');

    if (size.name === 'phone' || size.name === 'desktop') {
      await activate(page.locator('[data-m="rev"]'), size.touch);
      await page.waitForFunction(() => __jc.book().mode === 'rev');
      assert.equal(await visible(page.locator('#dock-rev')), true);
      assert.equal(await visible(page.locator('#b-hand')), false);
      assert.equal(await visible(page.locator('#b-clean')), false);
      await assertVisibleLabels(menu);
      await activate(page.locator('[data-m="hf"]'), size.touch);
      await page.waitForFunction(() => __jc.book().mode === 'hf');
      assert.equal(await visible(page.locator('#dock-hf')), true);
      assert.equal(await visible(page.locator('[data-v="study"]')), false);
      await page.locator('#hfrange').focus();
      const rangeBefore = await page.locator('#hfrange').inputValue(), bookBefore = await page.evaluate(() => __jc.book());
      await page.keyboard.press('ArrowRight');
      assert.notEqual(await page.locator('#hfrange').inputValue(), rangeBefore, 'Native range keyboard input remains usable.');
      assert.deepEqual(await page.evaluate(() => __jc.book()), bookBefore, 'Range keyboard input cannot turn a journal page.');
      await assertVisibleLabels(menu);
      pass(size.name + ': Revisions and Hand to font retain context controls and native input');
    }
    if (size.name === 'desktop') {
      await page.goto(base + '/site/index.html#study-diary37');
      await page.waitForFunction(() => window.__jc?.side === 'book' && !__jc.xfer && __jc.book().mode === 'journal' && __jc.book().view === 'study' && __jc.book().pid === 'diary37');
      if (await launcher.getAttribute('aria-expanded') !== 'true') await activate(launcher, false);
      assert.equal(await page.locator('#b-spread').isEnabled(), true);
      await activate(page.locator('#b-spread'), false);
      assert.equal(await page.locator('#b-spread').getAttribute('aria-pressed'), 'true');
      assert.equal(await page.locator('#b-outline').isDisabled(), true);
      await activate(page.locator('#b-spread'), false);
      assert.equal(await page.locator('#b-outline').isEnabled(), true);
      pass('notebook spread retains its context-specific outline restriction');

      await page.goto(base + '/site/index.html#type-poem');
      await waitForWork(page);
      await page.evaluate(() => __jc.focusOn(__jc.pieceItem('p020','f')));
      await page.waitForFunction(() => __jc.focusKey() && __jc.settled);
      for (const hold of [50, 650]) {
        await page.locator('#cv').focus();
        await page.mouse.move(640, 450);
        await page.mouse.down();
        await page.keyboard.press('Space');
        assert.equal(await launcher.getAttribute('aria-expanded'), 'true');
        const paused = await readerState(page);
        await page.waitForTimeout(hold);
        await page.mouse.move(600, 420);
        await page.mouse.up();
        await page.waitForTimeout(350);
        assert.equal(await launcher.getAttribute('aria-expanded'), 'true', 'An older canvas gesture cannot dismiss the menu.');
        assert.deepEqual(await readerState(page), paused, 'A held canvas pointer cannot move, select or open work behind modal controls.');
        await page.keyboard.press('Escape');
      }
      pass('opening Menu cancels both short and long active canvas gestures');

      const originalVersion = await page.evaluate(() => __jc.stack()?.front);
      assert.ok(originalVersion && await page.evaluate(() => __jc.stack().n > 1), 'Version-shortcut check uses an existing multiversion work.');
      assert.equal(await page.evaluate(() => document.activeElement.id), id);
      await page.keyboard.press('[');
      await page.waitForFunction(front => __jc.stack()?.front !== front, originalVersion);
      await page.keyboard.press(']');
      await page.waitForFunction(front => __jc.stack()?.front === front, originalVersion);
      assert.equal(await launcher.getAttribute('aria-expanded'), 'false');
      assert.equal(await page.evaluate(() => document.activeElement.id), id);
      pass('closed launcher retains earlier/later version shortcuts after dismissal');

      await launcher.press('Enter');
      await assertReaderShortcutsBlocked(page, 'focused-version menu');
      await page.locator('#b-info').click();
      await assertReaderShortcutsBlocked(page, 'focused-version About');
      await page.locator('#i-x').click();
      await page.keyboard.press('Escape');
      pass('open menu and About still suppress navigation, zoom and version shortcuts');
    }
    await context.close(); activePage = null;
  }
  assert.deepEqual(pageErrors, [], 'No browser script errors.');
  assert.deepEqual(assetErrors, [], 'No missing reader assets.');
  assert.equal(sha(fs.readFileSync(html)), report.readerSha256, 'The reader source must remain unchanged throughout verification.');
  report.pass = true;
  console.log('OK: ' + checks.length + ' browser acceptance checks');
} catch (error) {
  report.pass = false; report.error = error.stack || String(error);
  if (activePage) {
    await screenshot(activePage, 'failure').catch(() => {});
    report.failureState = await activePage.evaluate(() => ({active:document.activeElement?.id, body:document.body.className, hash:location.hash, menu:document.querySelector('#b-menu')?.getAttribute('aria-expanded'), panels:[...document.querySelectorAll('.panel')].map(e => ({id:e.id,hidden:e.hidden}))})).catch(() => null);
  }
  console.error(report.error); process.exitCode = 1;
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
  fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(report, null, 2) + '\n');
}
