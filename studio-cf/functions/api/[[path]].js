// Catch-all for /api/*; routing and validation live in lib/api.js.
import { handleApi } from '../../lib/api.js';

export async function onRequest(context) {
  const user = context.data && context.data.user;
  // The middleware always sets this; if it is somehow absent, refuse.
  if (!user) return new Response(null, { status: 403 });
  return handleApi(context.request, context.env, user);
}
