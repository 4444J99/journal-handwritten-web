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

export async function onRequest(context) {
  const { request, env } = context;
  let auth;
  try { auth = await authenticate(request, env); } catch { return deny(403); }
  if (auth.status !== AUTH.OK) return deny(auth.status === AUTH.MISCONFIGURED ? 503 : 403);

  context.data.user = { email: auth.email, canWrite: auth.canWrite };
  const res = await context.next();

  const headers = new Headers(res.headers);
  for (const [k, v] of Object.entries(BASE_HEADERS)) headers.set(k, v);
  const path = new URL(request.url).pathname;
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
