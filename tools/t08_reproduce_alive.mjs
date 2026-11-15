#!/usr/bin/env node
// Reproduce the owner lane's segmentation/atlas behaviour, read-only.
//
//   node tools/t08_reproduce_alive.mjs \
//     --repo /path/to/journal-handwritten-web--alive-proto \
//     --atoms /path/to/atoms-p001.json \
//     --out docs/pilots/t08-p001/evidence/alive-runtime.json
//
// It starts the owner's 127.0.0.1-only server, opens proto/alive in headless
// Chrome through tools/cdp_client.mjs, and records:
//   - the page reached ready;
//   - window.__alive.state() / sourcesUsed() / lineRegions() / regionsRead();
//   - atlasLeak() outside-pixel counts (must all be zero);
//   - every source line id used exists in the atoms artifact.
// It writes no screenshots and no poem text. Exit 0 only if every check holds.

import fs from "node:fs";
import fsp from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { CDP, withBrowser } from "./cdp_client.mjs";
import silentBrowser from './silent_browser.cjs'; const {silentChromeArgs} = silentBrowser;

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const DEFAULT_REPO = "/Volumes/Archive4T/Projects/journal-handwritten-web--alive-proto";
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const READY_TIMEOUT_MS = 30000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : fallback;
}

async function startServer(repo) {
  const serve = path.join(repo, "proto/alive/serve.mjs");
  if (!fs.existsSync(serve)) throw new Error(`owner server not found: ${serve}`);
  const proc = spawn(process.execPath, [serve, "--port", "0"], {
    cwd: repo, stdio: ["ignore", "pipe", "pipe"],
  });
  let stderr = "";
  proc.stderr.on("data", (d) => { stderr += d; });
  const url = await new Promise((resolve, reject) => {
    let out = "";
    const timer = setTimeout(() => reject(new Error(`server did not start: ${stderr.slice(0, 400)}`)), 15000);
    proc.stdout.on("data", (d) => {
      out += d;
      const m = out.match(/http:\/\/127\.0\.0\.1:\d+\//);
      if (m) { clearTimeout(timer); resolve(m[0]); }
    });
    proc.once("exit", (code) => { clearTimeout(timer); reject(new Error(`server exited ${code}: ${stderr.slice(0, 400)}`)); });
  });
  return { proc, url };
}

async function launchChrome(profile) {
  await fsp.mkdir(profile, { recursive: true });
  await fsp.rm(path.join(profile, "DevToolsActivePort"), { force: true });
  const args = silentChromeArgs([
    "--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
    "--no-first-run", "--disable-extensions", "--disable-background-networking", "about:blank",
  ]);
  const proc = spawn(CHROME, args, { stdio: ["ignore", "ignore", "pipe"] });
  let stderr = "";
  proc.stderr.on("data", (d) => { stderr += d; });
  const portFile = path.join(profile, "DevToolsActivePort");
  const t0 = Date.now();
  while (Date.now() - t0 < 20000) {
    try {
      const [port, wspath] = fs.readFileSync(portFile, "utf8").trim().split("\n");
      if (port && wspath) return { proc, wsUrl: `ws://127.0.0.1:${port}${wspath}` };
    } catch {}
    const m = stderr.match(/DevTools listening on (ws:\/\/\S+)/);
    if (m) return { proc, wsUrl: m[1] };
    if (proc.exitCode !== null) throw new Error("Chrome exited early: " + stderr.slice(0, 500));
    await sleep(100);
  }
  proc.kill();
  throw new Error("Chrome did not publish a DevTools port");
}

function gitHead(repo) {
  return new Promise((resolve) => {
    const p = spawn("git", ["-C", repo, "rev-parse", "HEAD"], { stdio: ["ignore", "pipe", "ignore"] });
    let out = "";
    p.stdout.on("data", (d) => { out += d; });
    p.once("exit", () => resolve(out.trim() || null));
  });
}

async function main() {
  const repo = path.resolve(arg("repo", DEFAULT_REPO));
  const atomsPath = path.resolve(arg("atoms", path.join(repo, "proto/alive/atoms-p001.json")));
  const outPath = path.resolve(arg("out", path.join(ROOT, "docs/pilots/t08-p001/evidence/alive-runtime.json")));
  const atoms = JSON.parse(await fsp.readFile(atomsPath, "utf8"));
  const expectedLines = new Set(atoms.stanzas.flatMap((s) => s.lines.map((l) => `diary1-${s.block}-${l.line}`)));

  const { proc: server, url } = await startServer(repo);
  const profile = await fsp.mkdtemp(path.join(os.tmpdir(), "t08-alive-profile-"));
  const report = {
    schema: "versforms.t08-alive-reproduction.v1",
    date: new Date().toISOString(),
    scope: "read-only; owner lane reused, not modified",
    owner_repo: repo,
    owner_head: await gitHead(repo),
    atoms: {
      path: path.relative(repo, atomsPath).startsWith("..") ? atomsPath : path.relative(repo, atomsPath),
      sha256: null,
      line_count: expectedLines.size,
    },
    server_url: url,
    checks: {},
    facts: {},
  };
  try {
    const crypto = await import("node:crypto");
    report.atoms.sha256 = crypto.createHash("sha256").update(await fsp.readFile(atomsPath)).digest("hex");
    await withBrowser({
      launch: () => launchChrome(profile),
      connect: (wsUrl) => CDP.connect(wsUrl, { connectTimeoutMs: 15000 }),
    }, async (cdp) => {
      const ver = await cdp.send("Browser.getVersion");
      report.chrome = { product: ver.product, userAgent: ver.userAgent, protocol: ver.protocolVersion };
      const { browserContextId } = await cdp.send("Target.createBrowserContext", { disposeOnDetach: true });
      const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank", browserContextId });
      const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
      const S = (m, p) => cdp.send(m, p, sessionId);
      const errors = [];
      cdp.on((m) => {
        if (m.sessionId !== sessionId) return;
        if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text || "exception");
        if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") errors.push(m.params.args.map((a) => a.value ?? a.description ?? "").join(" "));
      });
      const ev = async (expr) => {
        const r = await S("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
        if (r.exceptionDetails) throw new Error("evaluate: " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
        return r.result.value;
      };
      for (const d of ["Runtime", "Page", "Log"]) await S(d + ".enable");
      await S("Page.navigate", { url });
      const t0 = Date.now();
      let ready = false;
      while (Date.now() - t0 < READY_TIMEOUT_MS) {
        if (await ev(`!!(window.__alive && window.__alive.ready)`).catch(() => false)) { ready = true; break; }
        await sleep(200);
      }
      report.checks.ready = { pass: ready, observed: ready ? `${Date.now() - t0}ms` : `timeout ${READY_TIMEOUT_MS}ms` };
      if (!ready) { report.errors = errors; return; }

      await ev(`(()=>{window.__alive.setView("architecture");window.__alive.setUnit("line");window.__alive.fit();return true})()`);
      await sleep(500);
      const state = await ev(`window.__alive.state()`);
      // `sourcesUsed()` reports the reading animation's live sprites; sample a
      // few frozen times and union the ids so more than one line is exercised.
      const sourcesUsed = [];
      const readingTimes = [0, 2, 6, 12, 24, 48];
      for (const t of readingTimes) {
        await ev(`(()=>{window.__alive.setView("reading");window.__alive.setTime(${t});return true})()`);
        await sleep(120);
        for (const id of await ev(`window.__alive.sourcesUsed()`)) {
          if (!sourcesUsed.includes(id)) sourcesUsed.push(id);
        }
      }
      sourcesUsed.sort();
      const leak = await ev(`window.__alive.atlasLeak()`);
      const lineRegions = await ev(`window.__alive.lineRegions()`);
      const regionsRead = await ev(`window.__alive.regionsRead()`);
      const buildings = await ev(`window.__alive.buildings()`);

      report.facts = {
        state: {
          view: state.view, city: state.city, unit: state.unit, pieces: state.pieces,
          readyPieces: state.readyPieces, failed: state.failed, spriteCount: state.spriteCount,
          spriteSources: state.spriteSources, viewport: state.viewport,
        },
        sources_used: sourcesUsed,
        sources_used_count: sourcesUsed.length,
        sources_used_reading_times: readingTimes,
        atlas_leak_lines: leak.length,
        atlas_leak_outside_total: leak.reduce((n, l) => n + l.outside, 0),
        atlas_leak_outside_per_line: leak.map((l) => l.outside),
        line_regions: lineRegions.length,
        line_regions_with_polygon: lineRegions.filter((l) => l.region).length,
        regions_read: regionsRead.length,
        buildings: buildings.map((b) => ({ id: b.id, lines: b.lines, x0: b.x0, x1: b.x1 })),
      };
      const unknown = sourcesUsed.filter((id) => !expectedLines.has(id));
      report.checks.city = { pass: state.city === "p001" && state.failed.length === 0, observed: `${state.city}; failed=${JSON.stringify(state.failed)}` };
      report.checks.atlas_leak = {
        pass: leak.length === expectedLines.size && leak.every((l) => l.outside === 0 && l.region === true),
        observed: `${leak.length} lines; outside total ${report.facts.atlas_leak_outside_total}; regions ${leak.filter((l) => l.region).length}`,
      };
      report.checks.sources_used = {
        pass: sourcesUsed.length > 0 && unknown.length === 0,
        observed: `${sourcesUsed.length} ids, ${unknown.length} unknown${unknown.length ? ": " + unknown.join(", ") : ""}`,
      };
      report.checks.line_regions = {
        pass: lineRegions.length === expectedLines.size && lineRegions.every((l) => l.region),
        observed: `${lineRegions.length} regions, ${report.facts.line_regions_with_polygon} with polygons`,
      };
      report.checks.console = { pass: errors.length === 0, observed: errors.length ? errors.slice(0, 5) : "no console errors or exceptions" };
      report.errors = errors;
    });
  } finally {
    server.kill("SIGTERM");
    await fsp.rm(profile, { recursive: true, force: true });
  }
  report.ok = Object.values(report.checks).every((c) => c.pass);
  await fsp.mkdir(path.dirname(outPath), { recursive: true });
  await fsp.writeFile(outPath, JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify({ ok: report.ok, out: outPath, checks: report.checks }, null, 2));
  process.exit(report.ok ? 0 : 1);
}

main().catch((e) => { console.error("t08 reproduction failed: " + (e && e.stack || e)); process.exit(2); });
