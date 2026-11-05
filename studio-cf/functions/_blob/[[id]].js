// GET /_blob/ID streams a stored photo from R2 (reached only after the middleware).
import { handleBlob } from '../../lib/api.js';

export async function onRequest(context) {
  if (!(context.data && context.data.user)) return new Response(null, { status: 403 });
  const p = context.params.id;
  const id = Array.isArray(p) ? (p.length === 1 ? p[0] : '') : String(p || '');
  return handleBlob(context.request, context.env, id);
}
