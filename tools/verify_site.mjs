#!/usr/bin/env node
// Headless-Chrome verifier for the published piece in site/ (merged piece v4).
//
//   node tools/verify_site.mjs [--out REPORT.md] [--json-out REPORT.json]
//                              [--scratch DIR] [--chrome PATH] [--ready-timeout MS]
//
// The scratch directory (Chrome profile, screenshots) defaults to $VERIFY_SITE_SCRATCH, else
// a verify-site folder under the system temporary directory.
//
// Node >= 22 (global WebSocket and fetch), no npm packages.
//
// What it does
//   1. serves site/ on 127.0.0.1 (random port) with node:http: MIME types, no directory
//      listing, nothing outside site/;
//   2. launches Chrome headless with a throw-away profile under the scratch directory;
//   3. runs the matrix {desktop 1280x900, mobile 390x844 @3x with touch} x {light, dark}
//      over the Chrome DevTools Protocol, each cell in its own browser context;
//   4. per cell records console errors/warnings, exceptions, Log errors, failed requests,
//      HTTP >= 400, a screenshot (scratch only), and runs an interaction smoke that maps
//      onto the "Merged piece v4 changes" list in docs/plan.md;
//   5. prints a JSON report and a Markdown summary.
//
// Exit status is non-zero on: any console error, uncaught exception, Log error, failed
// request or HTTP >= 400 (browser-initiated /favicon.ico excluded and listed separately),
// a failed prefers-color-scheme assertion, a page that never gets body.ready, or an
// interaction check that was exercised and failed. NOT-EXERCISED never fails the run.
//
// It only observes. It never edits site/.

import http from "node:http";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import os from "node:os";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { CDP, writeThenExit } from "./cdp_client.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..");
const SITE = path.join(REPO, "site");

// ---------------------------------------------------------------- arguments
const argv = process.argv.slice(2);
const opt = (name, dflt) => { const i = argv.indexOf(name); return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : dflt; };
const SCRATCH = path.resolve(opt("--scratch", process.env.VERIFY_SITE_SCRATCH || path.join(os.tmpdir(), "verify-site")));
const CHROME = opt("--chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome");
const OUT_MD = opt("--out", null);
const OUT_JSON = opt("--json-out", null);
const READY_TIMEOUT = Number(opt("--ready-timeout", "30000"));
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ---------------------------------------------------------------- static server
const MIME = {
  ".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8", ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
  ".svg": "image/svg+xml", ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf", ".txt": "text/plain; charset=utf-8",
};
const SITE_REAL = fs.realpathSync(SITE);
function startServer() {
  const server = http.createServer(async (req, res) => {
    const deny = (code) => { res.writeHead(code, { "content-type": "text/plain" }); res.end(code + "\n"); };
    try {
      if (req.method !== "GET" && req.method !== "HEAD") return deny(405);
      let rel = decodeURIComponent(new URL(req.url, "http://x").pathname);
      if (rel.includes("\0")) return deny(400);
      if (rel.endsWith("/")) rel += "index.html";
      const abs = path.resolve(SITE_REAL, "." + path.sep + rel.replace(/^\/+/, ""));
      if (abs !== SITE_REAL && !abs.startsWith(SITE_REAL + path.sep)) return deny(403);
      let st;
      try { st = await fsp.stat(abs); } catch { return deny(404); }
      if (!st.isFile()) return deny(404); // directories are never listed
      const real = await fsp.realpath(abs);
      if (!real.startsWith(SITE_REAL + path.sep)) return deny(403); // symlink escape
      res.writeHead(200, { "content-type": MIME[path.extname(abs).toLowerCase()] || "application/octet-stream", "content-length": st.size, "cache-control": "no-store" });
      if (req.method === "HEAD") return res.end();
      fs.createReadStream(real).pipe(res);
    } catch { deny(400); }
  });
  return new Promise(resolve => server.listen(0, "127.0.0.1", () => resolve(server)));
}

// ---------------------------------------------------------------- CDP client
// The client (command time limit, rejection of waiting commands when the socket closes) is in cdp_client.mjs.

async function launchChrome() {
  const profile = path.join(SCRATCH, "profile");
  await fsp.mkdir(profile, { recursive: true });
  await fsp.rm(path.join(profile, "DevToolsActivePort"), { force: true }); // stale port file only
  const args = ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "--no-first-run", "--disable-extensions", "--disable-background-networking", "about:blank"];
  const proc = spawn(CHROME, args, { stdio: ["ignore", "ignore", "pipe"] });
  let stderr = ""; proc.stderr.on("data", d => { stderr += d; });
  const portFile = path.join(profile, "DevToolsActivePort");
  const t0 = Date.now();
  while (Date.now() - t0 < 20000) {
    try {
      const [port, wspath] = fs.readFileSync(portFile, "utf8").trim().split("\n");
      if (port && wspath) return { proc, wsUrl: `ws://127.0.0.1:${port}${wspath}`, stderrRef: () => stderr };
    } catch {}
    const m = stderr.match(/DevTools listening on (ws:\/\/\S+)/); if (m) return { proc, wsUrl: m[1], stderrRef: () => stderr };
    if (proc.exitCode !== null) throw new Error("Chrome exited early: " + stderr.slice(0, 500));
    await sleep(100);
  }
  proc.kill(); throw new Error("Chrome did not publish a DevTools port");
}

// ---------------------------------------------------------------- the matrix
const VIEWPORTS = [
  { name: "desktop", width: 1280, height: 900, dsf: 1, mobile: false, touch: false },
  { name: "mobile", width: 390, height: 844, dsf: 3, mobile: true, touch: true },
];
const SCHEMES = ["light", "dark"];

// v4 items in docs/plan.md, "Merged piece v4 changes". Keys are stable ids used in the report.
const V4 = [
  ["controls-hidden-rest", "Controls: hidden at rest"],
  ["controls-pointer-rest", "Controls: on desktop appear when the pointer rests on the bar's own place"],
  ["controls-pointer-elsewhere", "Controls: on desktop stay hidden when the pointer rests elsewhere along the bottom edge"],
  ["controls-margin", "Controls: sit 34px above the screen edge (desktop)"],
  ["controls-autohide", "Controls: hide 2.8s after use"],
  ["controls-open-poem-hides", "Controls: opening a poem hides them"],
  ["unfold-own-lines", "Unfold mode: a focused page's own lines are not dimmed"],
  ["canvas-tiles", "Canvas: tiles not yet composed drawn directly (no blank notched shapes)"],
  ["canvas-theme-frame", "Canvas: theme switch keeps last frame until the new one completes, then fades"],
  ["zoom-cap", "Closest zoom capped at about one line across the screen"],
  ["upright-close", "Close in, pages and lines turn upright; far views keep their angles; tap targets follow"],
  ["stack-reading", "Version stack: long poem opens at reading size; wheel/drag/arrows scroll; tall-poem drag scrolls instead of peeling"],
  ["focus-exit-esc", "Focus exit: Esc returns to the arrangement"],
  ["focus-exit-tap", "Focus exit: one tap outside returns to the arrangement"],
  ["focus-exit-nojump", "Focus exit: a tap that lands on another poem returns without focusing that poem"],
  ["buttons-pressed", "Content/arrangement buttons show pressed state at once"],
  ["buttons-interrupt", "Content/arrangement buttons interrupt a running camera move"],
  ["strip-labels", "Version strip: thumbnails labelled with date or n/N"],
  ["theme-switch", "Theme switching still works (regression check, not a v4 item)"],
];

function makeCell(vp, scheme) { return { id: `${vp.name}-${scheme}`, viewport: vp, scheme, console: [], exceptions: [], logErrors: [], failedRequests: [], http: [], ignored: [], checks: {}, facts: {} }; }
const setCheck = (cell, key, status, observed) => { cell.checks[key] = { status, observed }; };

async function runCell(cdp, baseUrl, cell) {
  const vp = cell.viewport;
  const { browserContextId } = await cdp.send("Target.createBrowserContext", { disposeOnDetach: true });
  const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank", browserContextId });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  const S = (m, p) => cdp.send(m, p, sessionId);
  const reqUrl = new Map();
  cdp.on(m => {
    if (m.sessionId !== sessionId) return;
    const p = m.params;
    switch (m.method) {
      case "Runtime.consoleAPICalled": if (p.type === "error" || p.type === "warning") cell.console.push({ type: p.type, text: p.args.map(a => a.value ?? a.description ?? "").join(" ").slice(0, 500) }); break;
      case "Runtime.exceptionThrown": cell.exceptions.push((p.exceptionDetails.exception?.description || p.exceptionDetails.text || "").slice(0, 500)); break;
      case "Log.entryAdded": if (p.entry.level === "error") (/\/favicon\.ico$/.test(p.entry.url || "") ? cell.ignored : cell.logErrors).push({ source: p.entry.source, text: p.entry.text.slice(0, 300), url: p.entry.url }); break;
      case "Network.requestWillBeSent": reqUrl.set(p.requestId, p.request.url); break;
      case "Network.loadingFailed": { const url = reqUrl.get(p.requestId) || "?"; (p.canceled ? cell.ignored : cell.failedRequests).push({ url, error: p.errorText, canceled: !!p.canceled }); break; }
      case "Network.responseReceived": if (p.response.status >= 400) { const e = { url: p.response.url, status: p.response.status }; (/\/favicon\.ico$/.test(e.url) ? cell.ignored : cell.http).push(e); } break;
    }
  });
  const ev = async (expr) => {
    const r = await S("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error("evaluate: " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    return r.result.value;
  };
  for (const d of ["Runtime", "Log", "Network", "Page"]) await S(d + ".enable");
  await S("Emulation.setDeviceMetricsOverride", { width: vp.width, height: vp.height, deviceScaleFactor: vp.dsf, mobile: vp.mobile });
  await S("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: cell.scheme }] });
  if (vp.touch) await S("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });

  // --- input helpers (real CDP input events)
  const mouse = (type, x, y, extra = {}) => S("Input.dispatchMouseEvent", { type, x, y, button: "none", ...extra });
  const tap = async (x, y) => {
    if (vp.touch) {
      await S("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y }] });
      await sleep(40);
      await S("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    } else {
      await mouse("mouseMoved", x, y); await mouse("mousePressed", x, y, { button: "left", buttons: 1, clickCount: 1 });
      await sleep(40); await mouse("mouseReleased", x, y, { button: "left", buttons: 0, clickCount: 1 });
    }
  };
  const key = async (k, code, vk) => { await S("Input.dispatchKeyEvent", { type: "rawKeyDown", key: k, code, windowsVirtualKeyCode: vk }); await S("Input.dispatchKeyEvent", { type: "keyUp", key: k, code, windowsVirtualKeyCode: vk }); };
  const rectOf = sel => ev(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});if(!e)return null;const r=e.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height,b:r.bottom,r:r.right}})()`);
  const uiOn = () => ev(`document.body.classList.contains("ui")`);
  const pressed = sel => ev(`document.querySelector(${JSON.stringify(sel)})?.getAttribute("aria-pressed")`);
  const tapCenter = async sel => { const r = await rectOf(sel); if (!r || !r.w) return false; await tap(r.x + r.w / 2, r.y + r.h / 2); return true; };

  // --- load
  await S("Page.navigate", { url: baseUrl + "/index.html" });
  const t0 = Date.now(); let ready = false;
  while (Date.now() - t0 < READY_TIMEOUT) { if (await ev(`document.body&&document.body.classList.contains("ready")`).catch(() => false)) { ready = true; break; } await sleep(200); }
  cell.facts.ready = ready; cell.facts.readyMs = ready ? Date.now() - t0 : null; cell.facts.readyTimeoutMs = READY_TIMEOUT;
  const env = await ev(`(()=>({dark:matchMedia("(prefers-color-scheme: dark)").matches,hoverFine:matchMedia("(hover:hover) and (pointer:fine)").matches,coarse:matchMedia("(pointer:coarse)").matches,innerWidth,innerHeight,dpr:devicePixelRatio,dataTheme:document.documentElement.getAttribute("data-theme"),ua:navigator.userAgent,touchPoints:navigator.maxTouchPoints}))()`);
  Object.assign(cell.facts, env);
  cell.facts.darkAssertionExpected = cell.scheme === "dark"; cell.facts.darkAssertionPass = env.dark === (cell.scheme === "dark");
  await fsp.mkdir(path.join(SCRATCH, "shots"), { recursive: true });
  await sleep(800);
  const shot = await S("Page.captureScreenshot", { format: "png" });
  const shotPath = path.join(SCRATCH, "shots", `${cell.id}.png`);
  await fsp.writeFile(shotPath, Buffer.from(shot.data, "base64")); cell.facts.screenshot = shotPath;

  const hooks = await ev(`typeof window.__jc==="object"`);
  cell.facts.testHooks = hooks;
  if (!ready) { for (const [k] of V4) setCheck(cell, k, "NOT-EXERCISED", "page never reached body.ready"); return finish(); }

  // observer: timestamp when body loses class "ui"
  await ev(`(()=>{window.__uiOff=null;window.__uiMo&&window.__uiMo.disconnect();window.__uiMo=new MutationObserver(()=>{if(!document.body.classList.contains("ui")&&window.__uiOff===null)window.__uiOff=performance.now()});window.__uiMo.observe(document.body,{attributes:true,attributeFilter:["class"]})})()`);

  // 1. hidden at rest
  {
    const o = await ev(`(()=>{const ov=document.querySelector("#ov");const c=getComputedStyle(ov);return{ui:document.body.classList.contains("ui"),opacity:c.opacity,pe:c.pointerEvents}})()`);
    setCheck(cell, "controls-hidden-rest", !o.ui && o.opacity === "0" && o.pe === "none" ? "EXERCISED-PASS" : "EXERCISED-FAIL", `body.ui=${o.ui} #ov opacity=${o.opacity} pointer-events=${o.pe}`);
  }

  // 2/3. pointer rest reveals + margin (fine pointer only), then auto-hide
  if (env.hoverFine) {
    const r = await rectOf("#pill");
    if (!r || !r.w) setCheck(cell, "controls-pointer-rest", "EXERCISED-FAIL", "#pill has no box");
    else {
      const cx = r.x + r.w / 2, cy = r.y + r.h / 2;
      // negative half first, with the bar still hidden: rest on the bottom edge well away from the bar
      {
        const ex = Math.max(12, Math.min(vp.width - 12, cx < vp.width / 2 ? cx + vp.width * 0.35 : cx - vp.width * 0.35)), ey = vp.height - 6;
        await mouse("mouseMoved", 20, 20); await sleep(150);
        await mouse("mouseMoved", ex - 20, ey); await mouse("mouseMoved", ex, ey);
        await sleep(1200);
        const leaked = await uiOn();
        setCheck(cell, "controls-pointer-elsewhere", !leaked ? "EXERCISED-PASS" : "EXERCISED-FAIL", `pointer moved to (${Math.round(ex)},${Math.round(ey)}), on the bottom edge ${Math.round(Math.abs(ex - cx))}px from the centre of #pill, and rested ~1.2s: body.ui=${leaked}`);
        if (leaked) { await mouse("mouseMoved", 20, 20); await sleep(3600); }
      }
      await mouse("mouseMoved", 20, 20); await sleep(150);
      await mouse("mouseMoved", cx - 30, cy); await mouse("mouseMoved", cx, cy);
      await sleep(900);
      const on = await uiOn();
      setCheck(cell, "controls-pointer-rest", on ? "EXERCISED-PASS" : "EXERCISED-FAIL", `pointer moved to the centre of #pill (${Math.round(cx)},${Math.round(cy)}) and rested ~0.9s: body.ui=${on}`);
      if (on) {
        await mouse("mouseMoved", cx + 3, cy); // pointer enters the revealed bar (the page then holds it open while hovered)
        await sleep(500);
        const ov = await rectOf("#ov"); const pill = await rectOf("#pill");
        const gap = vp.height - ov.b, pgap = vp.height - pill.b;
        setCheck(cell, "controls-margin", Math.abs(gap - 34) <= 1 ? "EXERCISED-PASS" : "EXERCISED-FAIL", `viewport height ${vp.height}; #ov bottom gap=${gap.toFixed(1)}px, #pill bottom gap=${pgap.toFixed(1)}px (documented 34px)`);
        // leave the bar: auto-hide timing from the moment the pointer leaves
        await ev(`window.__uiOff=null`);
        const t1 = await ev(`performance.now()`);
        await mouse("mouseMoved", vp.width / 2, 120);
        await sleep(2000); const still = await uiOn();
        let off = null; for (let i = 0; i < 30 && off === null; i++) { await sleep(200); off = await ev(`window.__uiOff`); }
        const el = off === null ? null : (off - t1) / 1000;
        setCheck(cell, "controls-autohide", still && el !== null && el >= 2.5 && el <= 3.6 ? "EXERCISED-PASS" : "EXERCISED-FAIL", `still visible at 2.0s after pointer left: ${still}; body.ui removed ${el === null ? "never (within 8s)" : el.toFixed(2) + "s"} after pointer left (documented 2.8s)`);
      } else { setCheck(cell, "controls-margin", "NOT-EXERCISED", "controls did not appear"); setCheck(cell, "controls-autohide", "NOT-EXERCISED", "controls did not appear"); }
    }
  } else {
    setCheck(cell, "controls-pointer-rest", "NOT-EXERCISED", "matchMedia((hover:hover) and (pointer:fine)) is false in this cell; the pointer-rest path only runs for fine pointers");
    setCheck(cell, "controls-pointer-elsewhere", "NOT-EXERCISED", "matchMedia((hover:hover) and (pointer:fine)) is false in this cell; there is no resting pointer");
    setCheck(cell, "controls-margin", "NOT-EXERCISED", "the 34px margin is declared only under (hover:hover) and (pointer:fine), which does not match here");
    if (hooks) {
      await ev(`window.__uiOff=null`); await ev(`window.__jc.ui(true)`);
      const t1 = await ev(`performance.now()`); await sleep(1900); const still = await uiOn();
      let off = null; for (let i = 0; i < 30 && off === null; i++) { await sleep(200); off = await ev(`window.__uiOff`); }
      const el = off === null ? null : (off - t1) / 1000;
      setCheck(cell, "controls-autohide", still && el !== null && el >= 2.5 && el <= 3.6 ? "EXERCISED-PASS" : "EXERCISED-FAIL", `controls shown through the page's test hook __jc.ui(true) (not by touch); still visible at 1.9s: ${still}; body.ui removed ${el === null ? "never (within 8s)" : el.toFixed(2) + "s"} later (documented 2.8s)`);
    } else setCheck(cell, "controls-autohide", "NOT-EXERCISED", "no touch path to show the bar without a poem-free tap target, and the __jc test hook is absent");
  }

  // 4. open a poem (real tap), controls hide; 5. Esc; 6. tap outside
  let itemKey = null;
  if (hooks) itemKey = await ev(`window.__jc.tallest("s")||window.__jc.tallest("f")`);
  cell.facts.itemKey = itemKey;
  const openItem = async () => {
    await ev(`window.__jc.centerOn(${JSON.stringify(itemKey)})`); await ev(`window.__jc.zoom(4)`); await sleep(700);
    const q = await ev(`window.__jc.quad(${JSON.stringify(itemKey)})`);
    await ev(`window.__jc.ui(true)`); await sleep(500);
    const uiBefore = await uiOn();
    await tap(q.cx, q.cy); await sleep(1500);
    return { q, uiBefore, focusKey: await ev(`window.__jc.focusKey()`), uiAfter: await uiOn() };
  };
  if (!itemKey) {
    for (const k of ["controls-open-poem-hides", "focus-exit-esc", "focus-exit-tap", "focus-exit-nojump"]) setCheck(cell, k, "NOT-EXERCISED", hooks ? "no tappable item key found" : "test hooks absent; cannot locate an item to tap");
  } else {
    const a = await openItem();
    const okOpen = a.focusKey !== null;
    setCheck(cell, "controls-open-poem-hides", okOpen && a.uiBefore && !a.uiAfter ? "EXERCISED-PASS" : "EXERCISED-FAIL", `item ${itemKey} located via test hook (quad cx=${Math.round(a.q.cx)} cy=${Math.round(a.q.cy)} w=${Math.round(a.q.w)} h=${Math.round(a.q.h)}) and tapped with real input; controls visible before=${a.uiBefore}; focusKey after=${a.focusKey}; controls visible after=${a.uiAfter}`);
    if (!okOpen) { for (const k of ["focus-exit-esc", "focus-exit-tap", "focus-exit-nojump"]) setCheck(cell, k, "NOT-EXERCISED", "tap did not focus the item"); }
    else {
      await key("Escape", "Escape", 27); await sleep(1500);
      const k1 = await ev(`window.__jc.focusKey()`);
      setCheck(cell, "focus-exit-esc", k1 === null ? "EXERCISED-PASS" : "EXERCISED-FAIL", `Escape key event sent; focusKey after 1.5s=${k1}`);
      const b = await openItem();
      if (b.focusKey === null) { for (const k of ["focus-exit-tap", "focus-exit-nojump"]) setCheck(cell, k, "NOT-EXERCISED", "second tap did not focus the item"); }
      else {
        // First tap: the far corner, away from the bar (proves "returns to the arrangement" only).
        const ox = vp.width - 14, oy = 14;
        await tap(ox, oy); await sleep(1500);
        const k2 = await ev(`window.__jc.focusKey()`);
        setCheck(cell, "focus-exit-tap", k2 === null ? "EXERCISED-PASS" : "EXERCISED-FAIL", `focused ${b.focusKey}; one real tap at (${ox},${oy}); focusKey after 1.5s=${k2} (null = arrangement)`);
        // Second round: look for another poem whose on-screen centre is outside the focused poem's box, tap there,
        // and require that focus is released and that poem is NOT the one now focused.
        const c = await openItem();
        const otherKey = await ev(`(()=>{const a=${JSON.stringify(itemKey)};for(const k of [window.__jc.tallest("f"),window.__jc.tallest("s")]) if(k&&k!==a) return k; return null})()`);
        if (c.focusKey === null) setCheck(cell, "focus-exit-nojump", "NOT-EXERCISED", "third tap did not focus the item");
        else if (!otherKey) setCheck(cell, "focus-exit-nojump", "NOT-EXERCISED", "no second poem key found through the test hooks");
        else {
          const fq = await ev(`window.__jc.quad(${JSON.stringify(itemKey)})`), oq = await ev(`window.__jc.quad(${JSON.stringify(otherKey)})`);
          const inView = oq && oq.cx > 8 && oq.cx < vp.width - 8 && oq.cy > 8 && oq.cy < vp.height - 8;
          const clear = fq && oq && Math.hypot(oq.cx - fq.cx, oq.cy - fq.cy) > Math.hypot(fq.w, fq.h) / 2 + 8; // outside the focused poem's box
          if (!inView || !clear) setCheck(cell, "focus-exit-nojump", "NOT-EXERCISED", `centre of ${otherKey} (${oq ? Math.round(oq.cx) + "," + Math.round(oq.cy) : "no quad"}) is ${!inView ? "off screen" : "inside the focused poem's box"}, so a tap there would not test the clause`);
          else {
            const uiPre = await uiOn();
            await tap(oq.cx, oq.cy); await sleep(1500);
            const k3 = await ev(`window.__jc.focusKey()`), uiPost = await uiOn();
            const where = `one real tap at the centre of ${otherKey}'s quad (${Math.round(oq.cx)},${Math.round(oq.cy)}), outside the focused item's quad`;
            if (k3 === c.focusKey && uiPost !== uiPre)
              // singleTap sends a tap inside the focused stack's layer box (plus a 30-unit pad) to toggleUI(); that box is larger than quad(), so this tap did not test the clause
              setCheck(cell, "focus-exit-nojump", "NOT-EXERCISED", `focused ${c.focusKey}; ${where}; focus stayed and the controls toggled (body.ui ${uiPre} -> ${uiPost}), which is the page's behaviour for a tap inside the focused stack's own area, so the tap point did not lie outside the stack`);
            else
              setCheck(cell, "focus-exit-nojump", k3 === null ? "EXERCISED-PASS" : "EXERCISED-FAIL", `focused ${c.focusKey}; ${where}; focusKey after 1.5s=${k3} (null = released, ${otherKey} not focused). Limit: the tap point comes from the page's own quad() hook; no pixel read shows ${otherKey} drawn there`);
          }
        }
      }
    }
  }

  // 7. pressed state at once; rapid second selection
  {
    await ev(`window.__jc&&window.__jc.ui(true)`); await sleep(500);
    const ensure = async sel => { let r = await rectOf(sel); if (r && !r.w) { await tapCenter("#b-cur1"); await sleep(500); r = await rectOf(sel); } return r; };
    const state0 = hooks ? await ev(`window.__jc.state`) : null;
    const pick = async (attr, vals) => { for (const v of vals) { if ((await pressed(`[${attr}="${v}"]`)) === "false") return v; } return null; };
    const c = await pick("data-c", ["pages", "lines", "unfold"]);
    const a = await pick("data-a", ["spiral", "scatter", "poem"]);
    const res = [];
    if (c && await ensure(`[data-c="${c}"]`)) {
      const prev = await ev(`document.querySelector("[data-c][aria-pressed=true]")?.dataset.c`);
      await tapCenter(`[data-c="${c}"]`); await sleep(60);
      const now = await pressed(`[data-c="${c}"]`); const old = await pressed(`[data-c="${prev}"]`);
      res.push({ ok: now === "true" && old === "false", t: `content ${prev}->${c}: new pressed=${now}, old pressed=${old} at ~60ms` });
    }
    if (a && await ensure(`[data-a="${a}"]`)) {
      const prev = await ev(`document.querySelector("[data-a][aria-pressed=true]")?.dataset.a`);
      await tapCenter(`[data-a="${a}"]`); await sleep(60);
      const now = await pressed(`[data-a="${a}"]`); const old = await pressed(`[data-a="${prev}"]`);
      res.push({ ok: now === "true" && old === "false", t: `arrangement ${prev}->${a}: new pressed=${now}, old pressed=${old} at ~60ms` });
    }
    setCheck(cell, "buttons-pressed", res.length && res.every(x => x.ok) ? "EXERCISED-PASS" : res.length ? "EXERCISED-FAIL" : "NOT-EXERCISED", res.length ? res.map(x => x.t).join("; ") : "no unpressed content/arrangement button reachable");
    // rapid second selection while the first move is running
    const a2 = await pick("data-a", ["scatter", "poem", "spiral"]);
    if (hooks && a2 && await ensure(`[data-a="${a2}"]`)) {
      await tapCenter(`[data-a="${a2}"]`); await sleep(120);
      const a3 = await pick("data-a", ["poem", "scatter", "spiral"].filter(x => x !== a2));
      if (a3 && await ensure(`[data-a="${a3}"]`)) {
        // page's own flag: settled is false while a transition is running (site/index.html: set false when a move starts)
        const running = (await ev(`window.__jc.settled`)) === false;
        await tapCenter(`[data-a="${a3}"]`); await sleep(60);
        const p = await pressed(`[data-a="${a3}"]`); await sleep(2500);
        const st = await ev(`window.__jc.state`);
        const okFinal = p === "true" && st.endsWith("-" + a3);
        const note = `second arrangement click ${a3} sent ~120ms after ${a2}: first move running at that moment (__jc.settled===false)=${running}; pressed at once=${p}; state before=${state0}, after settle=${st}. Only the flag, the final state and the pressed mark were observed; the camera path itself was not sampled`;
        setCheck(cell, "buttons-interrupt", !okFinal ? "EXERCISED-FAIL" : running ? "EXERCISED-PASS" : "NOT-EXERCISED", running || !okFinal ? note : `the first move had already finished when the second click arrived, so nothing was interrupted. ${note}`);
      } else setCheck(cell, "buttons-interrupt", "NOT-EXERCISED", "no second arrangement button available");
    } else setCheck(cell, "buttons-interrupt", "NOT-EXERCISED", "test hooks absent or arrangement button unreachable");
  }

  // 8. theme switch
  {
    await ev(`window.__jc&&window.__jc.ui(true)`); await sleep(500);
    const dk = () => ev(`getComputedStyle(document.documentElement).getPropertyValue("--blend").trim()==="screen"`);
    const d0 = await dk(); const ok1 = await tapCenter("#b-theme"); await sleep(900);
    const d1 = await dk(); const th1 = await ev(`document.documentElement.getAttribute("data-theme")`);
    await ev(`window.__jc&&window.__jc.ui(true)`); await sleep(400);
    await tapCenter("#b-theme"); await sleep(900); const d2 = await dk();
    setCheck(cell, "theme-switch", ok1 && d1 === !d0 && d2 === d0 ? "EXERCISED-PASS" : "EXERCISED-FAIL", `dark(--blend=screen): start=${d0}, after one click=${d1} (data-theme=${th1}), after second click=${d2}`);
  }

  // v4 items that need visual or internal inspection this run does not perform
  const no = (k, why) => setCheck(cell, k, "NOT-EXERCISED", why);
  no("unfold-own-lines", "needs a pixel/opacity read of line dimming in Unfold mode; no such measurement is implemented");
  no("canvas-tiles", "needs a comparison of composed vs uncomposed tiles per frame; not implemented");
  no("canvas-theme-frame", "needs frame-by-frame capture across a theme switch; only the end state of the switch is checked");
  no("zoom-cap", "no measurement of line width against screen width was implemented");
  no("upright-close", "no measurement of item rotation at close zoom was implemented");
  no("stack-reading", "needs a long multi-version poem opened and scrolled; not implemented");
  no("strip-labels", "the version strip shows in the journal (book) view and on the canvas when a multi-version stack is focused; this run opens neither the book view nor a multi-version stack");

  return finish();

  async function finish() {
    await S("Page.close").catch(() => {});
    await cdp.send("Target.disposeBrowserContext", { browserContextId }).catch(() => {});
    return cell;
  }
}

// ---------------------------------------------------------------- report
function summarize(cell) {
  const reasons = [];
  if (!cell.facts.darkAssertionPass) reasons.push(`prefers-color-scheme assertion failed (expected dark=${cell.facts.darkAssertionExpected}, got ${cell.facts.dark})`);
  if (!cell.facts.ready) reasons.push(`body.ready not reached within ${cell.facts.readyTimeoutMs}ms`);
  const ce = cell.console.filter(c => c.type === "error"); if (ce.length) reasons.push(`${ce.length} console error(s)`);
  if (cell.exceptions.length) reasons.push(`${cell.exceptions.length} exception(s)`);
  if (cell.logErrors.length) reasons.push(`${cell.logErrors.length} Log error(s)`);
  if (cell.failedRequests.length) reasons.push(`${cell.failedRequests.length} failed request(s)`);
  if (cell.http.length) reasons.push(`${cell.http.length} HTTP >= 400`);
  const f = Object.entries(cell.checks).filter(([, v]) => v.status === "EXERCISED-FAIL").map(([k]) => k); if (f.length) reasons.push(`interaction check(s) failed: ${f.join(", ")}`);
  return reasons;
}
function markdown(rep) {
  const L = [];
  L.push(`# site/ verification`, ``, `- date: ${rep.date}`, `- chrome: ${rep.chrome.product} (${rep.chrome.userAgent})`, `- site/index.html: ${rep.site.bytes} bytes, sha256 ${rep.site.sha256}`, `- node: ${rep.node}`, `- result: ${rep.ok ? "PASS" : "FAIL"}`, ``);
  L.push(`## Cells`, ``, `| cell | dark assertion | ready | console err/warn | exceptions | Log err | failed req | HTTP>=400 | reasons |`, `|---|---|---|---|---|---|---|---|---|`);
  for (const c of rep.cells) L.push(`| ${c.id} | expected ${c.facts.darkAssertionExpected}, matched ${c.facts.dark}: ${c.facts.darkAssertionPass ? "ok" : "FAIL"} | ${c.facts.ready ? c.facts.readyMs + "ms" : "NO"} | ${c.console.filter(x => x.type === "error").length}/${c.console.filter(x => x.type === "warning").length} | ${c.exceptions.length} | ${c.logErrors.length} | ${c.failedRequests.length} | ${c.http.length} | ${c.reasons.join("; ") || "none"} |`);
  L.push(``, `## Cell facts`, ``, `| cell | viewport | dpr | hover:fine | pointer:coarse | maxTouchPoints | data-theme at load | item key |`, `|---|---|---|---|---|---|---|---|`);
  for (const c of rep.cells) L.push(`| ${c.id} | ${c.facts.innerWidth}x${c.facts.innerHeight} | ${c.facts.dpr} | ${c.facts.hoverFine} | ${c.facts.coarse} | ${c.facts.touchPoints} | ${c.facts.dataTheme} | ${c.facts.itemKey} |`);
  L.push(``, `## v4 coverage`, ``, `| item | ` + rep.cells.map(c => c.id).join(" | ") + ` |`, `|---|` + rep.cells.map(() => "---").join("|") + `|`);
  for (const [k, label] of V4) L.push(`| ${label} | ` + rep.cells.map(c => c.checks[k]?.status || "NOT-EXERCISED").join(" | ") + ` |`);
  L.push(``, `## Observations`, ``);
  for (const [k, label] of V4) { L.push(`### ${label}`); for (const c of rep.cells) L.push(`- ${c.id}: ${c.checks[k]?.status} - ${c.checks[k]?.observed || "-"}`); L.push(``); }
  const ign = rep.cells.flatMap(c => c.ignored.map(i => `${c.id}: ${i.url} ${i.status ?? i.error ?? i.text} (browser-initiated /favicon.ico; the page declares no icon)`));
  const warn = rep.cells.flatMap(c => c.console.map(x => `${c.id}: [${x.type}] ${x.text}`));
  const bad = rep.cells.flatMap(c => [...c.exceptions.map(x => `${c.id}: exception ${x}`), ...c.logErrors.map(x => `${c.id}: log ${x.text} ${x.url || ""}`), ...c.failedRequests.map(x => `${c.id}: failed ${x.url} ${x.error}`), ...c.http.map(x => `${c.id}: http ${x.status} ${x.url}`)]);
  L.push(`## Console messages (errors and warnings)`, ``, ...(warn.length ? warn.map(x => `- ${x}`) : ["- none"]), ``, `## Exceptions, Log errors, failed requests, HTTP >= 400`, ``, ...(bad.length ? bad.map(x => `- ${x}`) : ["- none"]), ``, `## Ignored (not counted)`, ``, ...(ign.length ? ign.map(x => `- ${x}`) : ["- none"]), ``);
  L.push(`Screenshots are written to ${path.join(rep.scratch, "shots")} and are not committed.`, ``);
  return L.join("\n");
}

// ---------------------------------------------------------------- main
async function main() {
  await fsp.mkdir(SCRATCH, { recursive: true });
  const html = await fsp.readFile(path.join(SITE, "index.html"));
  const server = await startServer();
  const baseUrl = `http://127.0.0.1:${server.address().port}`;
  const { proc, wsUrl } = await launchChrome();
  const cdp = await CDP.connect(wsUrl);
  let rep;
  try {
    const ver = await cdp.send("Browser.getVersion");
    const cells = [];
    for (const vp of VIEWPORTS) for (const scheme of SCHEMES) {
      const cell = makeCell(vp, scheme);
      try { await runCell(cdp, baseUrl, cell); } catch (e) { cell.exceptions.push("verifier error: " + e.message); }
      cell.reasons = summarize(cell);
      cells.push(cell);
    }
    rep = {
      date: new Date().toISOString(), node: process.version, baseUrl, scratch: SCRATCH,
      chrome: { product: ver.product, userAgent: ver.userAgent, protocol: ver.protocolVersion },
      site: { bytes: html.length, sha256: crypto.createHash("sha256").update(html).digest("hex") },
      cells, ok: cells.every(c => c.reasons.length === 0),
    };
  } finally {
    cdp.close(); proc.kill("SIGTERM"); server.close();
  }
  const md = markdown(rep);
  const json = JSON.stringify(rep, null, 2);
  if (OUT_MD) await fsp.writeFile(OUT_MD, md);
  if (OUT_JSON) await fsp.writeFile(OUT_JSON, json);
  // exit only after the report has been handed to the operating system: a large report written to a pipe is cut short otherwise
  writeThenExit(process.stdout, json + "\n\n" + md + "\n", rep.ok ? 0 : 1);
}
main().catch(e => writeThenExit(process.stderr, "verifier failed: " + (e && e.stack || e) + "\n", 2));
