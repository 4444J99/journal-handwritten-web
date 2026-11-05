#!/usr/bin/env node
/* Bounded local browser acceptance for the generated T03 packet.
 * Requires the existing Playwright runtime and a supplied Chromium binary.
 * Never connects to an account or hosts outside 127.0.0.1. Screenshots/JSON
 * stay in the supplied new output folder. Physical-phone acceptance is separate.
 */
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const { chromium } = require('playwright');

async function main() {
  const args = Object.fromEntries(process.argv.slice(2).reduce((r, x, i, all) => {
    if (x.startsWith('--')) r.push([x.slice(2), all[i + 1]]);
    return r;
  }, []));
  if (!args.packet || !args.out || !args.chrome) throw Error('Required: --packet DIR --out NEW_DIR --chrome PATH');
  const root = await fs.realpath(args.packet), out = path.resolve(args.out);
  await fs.mkdir(out, { recursive: false });
  const data = JSON.parse(await fs.readFile(path.join(root, 'preview/data/j.json'), 'utf8'));
  const packet = JSON.parse(await fs.readFile(path.join(root, 'packet.json'), 'utf8'));
  const server = http.createServer(async (req, res) => {
    try {
      const rel = decodeURIComponent(new URL(req.url, 'http://127.0.0.1').pathname);
      if (rel === '/favicon.ico') { res.writeHead(204); res.end(); return; }
      let filename = path.resolve(root, '.' + rel);
      if (filename !== root && !filename.startsWith(root + path.sep)) throw Error('Outside root');
      if ((await fs.stat(filename)).isDirectory()) filename = path.join(filename, 'index.html');
      const real = await fs.realpath(filename);
      if (real !== root && !real.startsWith(root + path.sep)) throw Error('Outside root');
      const mime = { '.html': 'text/html', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png' }[path.extname(real)] || 'text/plain';
      res.writeHead(200, { 'Content-Type': mime, 'Cache-Control': 'no-store' });
      res.end(await fs.readFile(real));
    } catch { res.writeHead(404); res.end('Not found'); }
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const base = `http://127.0.0.1:${server.address().port}`;
  let browser;
  const result = { source_revision: packet.tested_source_revision, source_code_sha256: packet.code_sha256,
    preview_files: packet.preview.files, browser: null, physical_phone: 'not tested',
    remote_deployment: 'not performed', public_header_runtime: 'not tested; _headers checked as output bytes', viewports: [] };
  try {
    browser = await chromium.launch({ executablePath: args.chrome, headless: true,
      args: ['--no-sandbox', '--disable-dev-shm-usage', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
    result.browser = await browser.version();
    for (const spec of [{ name: 'desktop', width: 1280, height: 900, touch: false },
                        { name: 'phone-emulation', width: 390, height: 844, touch: true }]) {
      const context = await browser.newContext({ viewport: { width: spec.width, height: spec.height },
        hasTouch: spec.touch, isMobile: spec.touch, reducedMotion: 'reduce' });
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.protocol === 'data:' || url.origin === base) return route.continue();
        return route.abort();
      });
      const page = await context.newPage(), errors = [], failed = [], requested = new Set();
      page.on('pageerror', e => errors.push(e.message));
      page.on('requestfailed', r => failed.push({ url: r.url(), error: r.failure()?.errorText }));
      page.on('request', r => { const u = new URL(r.url()); if (u.origin === base) requested.add(u.pathname); });
      await page.goto(base + '/preview/', { waitUntil: 'networkidle' });
      await page.waitForFunction(expected => document.querySelector('#i-src').textContent.includes(`${expected} pages`), data.pages.length);
      await page.evaluate(() => document.fonts.ready);
      const initial = await page.evaluate(() => ({ title: document.title,
        noindex: document.querySelector('meta[name="robots"]')?.content,
        fontLoaded: document.fonts.check('16px "ajp-scribbles"'), infoHidden: document.querySelector('#infop').hidden,
        width: innerWidth, documentWidth: document.documentElement.scrollWidth }));
      await page.keyboard.press('Space');
      if (await page.locator('#b-more').isVisible()) await page.locator('#b-more').click();
      await page.locator('#b-info').click();
      await page.locator('#infop').waitFor({ state: 'visible' });
      const info = await page.locator('#infop').innerText();
      const infoBounds = await page.locator('#infop').boundingBox();
      await page.keyboard.press('Escape');
      await page.keyboard.press('b');
      await page.waitForFunction(() => !document.querySelector('#book').hidden && document.querySelector('#bstage').childElementCount > 0);
      await page.waitForTimeout(300);
      await page.screenshot({ path: path.join(out, `reader-${spec.name}.png`) });
      const book = await page.evaluate(() => ({ visible: !document.querySelector('#book').hidden,
        text: document.querySelector('#bstage').innerText, width: innerWidth,
        documentWidth: document.documentElement.scrollWidth }));
      result.viewports.push({ ...spec, initial, info, infoBounds, book,
        pageErrors: errors, failedRequests: failed, requestedPaths: [...requested].sort(),
        pass: initial.title === 'versforms' && initial.noindex.includes('noindex') && initial.fontLoaded &&
          initial.infoHidden && errors.length === 0 && failed.length === 0 && book.visible &&
          book.documentWidth <= book.width });
      await context.close();
    }
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    await page.goto(base + '/', { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(out, 'decision-preview.png') });
    if (await page.locator('.compare').count()) {
      await page.locator('.compare').screenshot({ path: path.join(out, 'version-exposure.png') });
    }
    result.absentRoutes = [];
    const includedPages = new Set(data.pages.map(p => p.id));
    const omittedPages = Object.keys(packet.input_sha256).map(p => p.match(/^site\/img\/p\/(.+)\.jpg$/)?.[1])
      .filter(p => p && !includedPages.has(p));
    const omittedPage = omittedPages.includes('diary62a') ? 'diary62a' : omittedPages[0];
    const absentPaths = omittedPage ? ['p', 'i', 'm'].map(tier => `/preview/img/${tier}/${omittedPage}.jpg`) : [];
    for (const url of absentPaths) {
      const response = await context.request.get(base + url);
      result.absentRoutes.push({ path: url, status: response.status(), pass: response.status() === 404 });
    }
    await context.close();
    result.pieceIds = data.pieces.map(p => p.id);
    result.versionIds = data.pieces.flatMap(p => p.V.map(v => v.id));
    result.pass = result.viewports.every(r => r.pass) && result.absentRoutes.every(r => r.pass) &&
      JSON.stringify(result.pieceIds) === JSON.stringify([packet.candidate]);
  } catch (e) { result.pass = false; result.error = e.stack; }
  finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
    result.verifier_sha256 = crypto.createHash('sha256').update(await fs.readFile(__filename)).digest('hex');
    await fs.writeFile(path.join(out, 'browser-results.json'), JSON.stringify(result, null, 2) + '\n');
  }
  console.log(JSON.stringify({ pass: result.pass, browser: result.browser, viewports: result.viewports.map(r => ({ name: r.name, pass: r.pass })), error: result.error || null, out }, null, 2));
  if (!result.pass) process.exitCode = 1;
}
main().catch(e => { console.error(e.stack); process.exitCode = 1; });
