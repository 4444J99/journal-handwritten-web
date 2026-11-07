// The final publication and ordinary Studio source writes share this D1 fence.
// It does NOT expire by time: a delayed R2 PUT must never outlive its protection.
// Recovery first invalidates the captured R2 ETag, then releases an abandoned
// fence. A late conditional PUT consequently fails rather than publishing after
// a Reserve/review edit. No new table, coordinator service or paid plan is needed.
export const SOURCE_COLLECTIONS=Object.freeze(['reviews','decisions','versions','release','batches','rconfig']);
export const SOURCE_FENCE_ID='source-write-fence';
export const NO_SOURCE_FENCE="NOT EXISTS (SELECT id FROM vf_docs WHERE collection = 'publish' AND id = 'source-write-fence')";
const REVS='SELECT collection, rev FROM vf_revs WHERE collection IN (?1, ?2, ?3, ?4, ?5, ?6) ORDER BY collection';
export const revisionStatement=env=>env.DB.prepare(REVS).bind(...SOURCE_COLLECTIONS);
export const revisionValues=rows=>Object.fromEntries(SOURCE_COLLECTIONS.map(c=>[c,rows.find(r=>r.collection===c)?.rev || 0]));

export async function readFence(env) {
  const r=await env.DB.prepare('SELECT data FROM vf_docs WHERE collection = ?1 AND id = ?2').bind('publish',SOURCE_FENCE_ID).first();
  return r?JSON.parse(r.data):null;
}
export async function acquireFence(env,intent,revisions) {
  if(!revisions)return false;
  const sql="INSERT INTO vf_docs (collection, id, data, updated_at, rev) SELECT 'publish', 'source-write-fence', ?1, ?2, 0 WHERE "+NO_SOURCE_FENCE+
    " AND COALESCE((SELECT rev FROM vf_revs WHERE collection = 'reviews'), 0) = ?3"+
    " AND COALESCE((SELECT rev FROM vf_revs WHERE collection = 'decisions'), 0) = ?4"+
    " AND COALESCE((SELECT rev FROM vf_revs WHERE collection = 'versions'), 0) = ?5"+
    " AND COALESCE((SELECT rev FROM vf_revs WHERE collection = 'release'), 0) = ?6"+
    " AND COALESCE((SELECT rev FROM vf_revs WHERE collection = 'batches'), 0) = ?7"+
    " AND COALESCE((SELECT rev FROM vf_revs WHERE collection = 'rconfig'), 0) = ?8 ON CONFLICT(collection, id) DO NOTHING";
  const result=await env.DB.prepare(sql).bind(JSON.stringify(intent),intent.at,...SOURCE_COLLECTIONS.map(c=>revisions[c])).run();
  return result.meta.changes===1;
}
export async function releaseFence(env,event) {
  await env.DB.prepare("DELETE FROM vf_docs WHERE collection = 'publish' AND id = 'source-write-fence' AND json_extract(data, '$.event') = ?1").bind(event).run();
}
