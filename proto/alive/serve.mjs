#!/usr/bin/env node
// Tiny static server for the alive prototype. Binds 127.0.0.1 only, GET/HEAD only.
//
//   node proto/alive/serve.mjs [--port 8765]          (--port 0 picks a free port)
//
// Serves an explicit whitelist and nothing else:
//   /                     proto/alive/index.html
//   /alive.js, /atoms-p001.json, /rules-diary1.json, /city-all58.json     (files next to this script)
//   /site/img/p/diary1.jpg                                                (full-resolution page of p001)
//   /site/img/i/<page>.jpg                                                (keyed 0.75 tier, city=all58 only)
// Path traversal, encoded separators, NUL bytes, symlinks that leave the repository, directory
// listings and every other path are refused. The repository holds the author's private archive:
// keep this on 127.0.0.1 and never put it behind a tunnel or a public host.

import http from "node:http";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = fs.realpathSync(path.resolve(HERE, "..", ".."));
const ALIVE = fs.realpathSync(HERE);

const argv = process.argv.slice(2);
const pi = argv.indexOf("--port");
const PORT = pi >= 0 ? Number(argv[pi + 1]) : Number(process.env.ALIVE_PORT || 8765);
if (!Number.isInteger(PORT) || PORT < 0 || PORT > 65535) { console.error("bad --port"); process.exit(2); }

const OWN = new Map([
  ["/", "index.html"], ["/index.html", "index.html"], ["/alive.js", "alive.js"],
  ["/atoms-p001.json", "atoms-p001.json"], ["/rules-diary1.json", "rules-diary1.json"], ["/city-all58.json", "city-all58.json"],
]);
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8", ".jpg": "image/jpeg" };

// returns [absolute path, allowed root] or null
function resolve(pathname) {
  if (OWN.has(pathname)) return [path.join(ALIVE, OWN.get(pathname)), ALIVE];
  let m = /^\/site\/img\/(p|i)\/([A-Za-z0-9_-]+)\.jpg$/.exec(pathname);
  if (m) {
    if (m[1] === "p" && m[2] !== "diary1") return null; // only p001's page at full resolution
    return [path.join(REPO, "site", "img", m[1], m[2] + ".jpg"), path.join(REPO, "site", "img", m[1])];
  }
  return null;
}

const server = http.createServer(async (req, res) => {
  const deny = (code) => { res.writeHead(code, { "content-type": "text/plain", "cache-control": "no-store" }); res.end(code + "\n"); };
  try {
    if (req.method !== "GET" && req.method !== "HEAD") return deny(405);
    const raw = req.url.split("?")[0].split("#")[0];
    if (raw.includes("\0") || raw.includes("%00") || /%2e|%2f|%5c/i.test(raw) || raw.includes("..") || raw.includes("\\")) return deny(400);
    const r = resolve(raw);
    if (!r) return deny(404);
    const [abs, root] = r;
    let st;
    try { st = await fsp.stat(abs); } catch { return deny(404); }
    if (!st.isFile()) return deny(404);
    const real = await fsp.realpath(abs);
    const rootReal = await fsp.realpath(root);
    if (!(real === rootReal || real.startsWith(rootReal + path.sep)) || !(real === REPO || real.startsWith(REPO + path.sep))) return deny(403);
    res.writeHead(200, { "content-type": MIME[path.extname(real).toLowerCase()] || "application/octet-stream", "content-length": st.size, "cache-control": "no-store", "x-content-type-options": "nosniff", "cross-origin-resource-policy": "same-origin" });
    if (req.method === "HEAD") return res.end();
    fs.createReadStream(real).pipe(res);
  } catch { deny(400); }
});

server.listen(PORT, "127.0.0.1", () => {
  const a = server.address();
  console.log(`alive: http://127.0.0.1:${a.port}/  (127.0.0.1 only; private archive, do not expose)`);
});
