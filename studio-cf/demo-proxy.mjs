// The header-injecting proxy used by demo.mjs, kept separate so its rules can be tested.
//
// It listens on 127.0.0.1 and forwards to the local `wrangler pages dev` upstream, adding a
// freshly signed TEST token (a stand-in for Cloudflare Access) that a browser cannot send itself.
// Rules, each covered by tests/demo-proxy.test.mjs:
//  - Any request whose Host is not this proxy's own (127.0.0.1:PORT or localhost:PORT) is refused
//    with 421, so a web page that reaches the port through a rebound DNS name cannot use the token.
//  - The API refuses a browser write whose Origin differs from the origin of the URL it received
//    (its CSRF defence). Because the upstream is on another port, the proxy's OWN origin is
//    translated to the upstream's. Any other Origin is forwarded unchanged and the API rejects it.
//  - A client-supplied Access header is always overwritten.
import http from 'node:http';

export function createProxy({ upstreamPort, token }) {
  const server = http.createServer((req, res) => {
    const own = server.address().port;
    const ownHosts = new Set([`127.0.0.1:${own}`, `localhost:${own}`]);
    const ownOrigins = new Set([`http://127.0.0.1:${own}`, `http://localhost:${own}`]);
    if (!ownHosts.has(String(req.headers.host || '').toLowerCase())) {
      res.writeHead(421, { 'content-type': 'text/plain' });
      res.end('wrong host');
      return;
    }
    const headers = { ...req.headers, host: `127.0.0.1:${upstreamPort}`, 'cf-access-jwt-assertion': token() };
    if (ownOrigins.has(String(headers.origin || '').toLowerCase())) headers.origin = `http://127.0.0.1:${upstreamPort}`;
    const up = http.request({ host: '127.0.0.1', port: upstreamPort, method: req.method, path: req.url, headers }, r => {
      res.writeHead(r.statusCode, r.headers);
      r.pipe(res);
    });
    up.on('error', () => { if (!res.headersSent) res.writeHead(502); res.end('upstream error'); });
    req.pipe(up);
  });
  return server;
}
