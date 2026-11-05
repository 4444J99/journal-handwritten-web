// Runs in front of EVERY request, static files included. Second line of defence
// behind Cloudflare Access: verifies the Access JWT itself and fails closed.
import { authenticate, AUTH } from '../lib/auth.js';

const BASE_HEADERS = {
  'x-content-type-options': 'nosniff',
  'referrer-policy': 'no-referrer',
  'x-robots-tag': 'noindex, nofollow',
};

function deny(status) {
  // No detail in the body, on purpose.
  return new Response(null, { status, headers: { 'cache-control': 'no-store', ...BASE_HEADERS } });
}

function notFound() {
  return new Response(null, { status: 404, headers: { 'cache-control': 'no-store', ...BASE_HEADERS } });
}

// False for a pathname no static file can have: a decoded NUL or control character, a
// segment longer than 255 bytes, or a path longer than 2048 characters.
function staticPathOk(pathname) {
  if (pathname.length > 2048) return false;
  let decoded;
  try { decoded = decodeURIComponent(pathname); } catch { decoded = pathname; }
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f\u007f]/.test(decoded)) return false;
  const enc = new TextEncoder();
  for (const seg of decoded.split('/')) if (enc.encode(seg).length > 255) return false;
  return true;
}

export async function onRequest(context) {
  const { request, env } = context;
  let auth;
  try { auth = await authenticate(request, env); } catch { return deny(403); }
  if (auth.status !== AUTH.OK) return deny(auth.status === AUTH.MISCONFIGURED ? 503 : 403);

  context.data.user = { email: auth.email, canWrite: auth.canWrite };
  const path = new URL(request.url).pathname;
  const isStatic = !path.startsWith('/api/') && !path.startsWith('/_blob/');

  // Only after authentication, so a stranger never learns anything from these answers.
  // Under `wrangler pages dev` the local static-file server answers 502 for paths the
  // file system cannot take (NUL byte, a name over 255 bytes, a file used as a
  // directory such as /index.html/); the hosted service answers 404. Make it a clean
  // 404 here instead of passing the simulator's error text through.
  if (isStatic && !staticPathOk(path)) return notFound();

  let res;
  try { res = await context.next(); } catch { return isStatic ? notFound() : deny(503); }
  if (isStatic && res.status === 502) return notFound(); // the studio itself never returns 502

  const headers = new Headers(res.headers);
  for (const [k, v] of Object.entries(BASE_HEADERS)) headers.set(k, v);
  if (path.startsWith('/_blob/')) {
    // the blob route sets its own private immutable caching
    if (!headers.has('cache-control')) headers.set('cache-control', 'private, no-cache');
  } else if (path.startsWith('/api/')) {
    headers.set('cache-control', 'no-store');
  } else {
    headers.set('cache-control', 'private, max-age=0, must-revalidate');
  }
  headers.append('vary', 'Cf-Access-Jwt-Assertion');
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers });
}
