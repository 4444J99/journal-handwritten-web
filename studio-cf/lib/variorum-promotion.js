// Explicit Sort promotion. The canonical catalogue and originating composite
// remain untouched; publication assembles this independent piece from its origin.
import {stableJSON,sha256} from '../../studio/source-fingerprint.mjs';
import {SOURCE_COLLECTIONS,NO_SOURCE_FENCE} from './publish-fence.js';
const fail=(message,status=409)=>{const e=new Error(message);e.status=status;throw e;};
const answer=body=>new Response(JSON.stringify(body),{headers:{'content-type':'application/json','cache-control':'no-store'}});
export async function promoteComposite(env,user,input,recordId,payload){
 if(!user?.canWrite)fail('forbidden',403);
 const id='promotion.'+payload.operationId,requestHash=sha256(stableJSON({recordId,payload}));
 const replay=input.db.composites?.[id];
 if(replay){if(replay.requestHash!==requestHash)fail('operation_conflict');return answer({ok:true,promotion:replay,replayed:true});}
 if(payload.sourceToken!==input.sourceToken)fail('source_changed');
 const head=input.db.composites?.['h.'+recordId],origin=input.db.composites?.[head?.revisionId];
 if(!origin||origin.family!=='composite')fail('not_found',404);
 if(head.revisionId!==payload.expectedHead)fail('head_changed');
 if(Object.values(input.db.composites||{}).some(d=>d.family==='promotion'&&d.originComposite?.recordId===recordId))fail('already_promoted');
 const ids=[...input.catalog.pieces.map(p=>p.pieceId),...Object.keys(input.db.release||{}),...Object.values(input.db.composites||{}).map(d=>d.pieceId)].filter(id=>/^p\d+$/.test(id));
 const next=Math.max(0,...ids.map(id=>Number(id.slice(1))))+1;
 if(!Number.isSafeInteger(next))fail('piece_identity_exhausted');
 const pieceId='p'+String(next).padStart(3,'0'),at=new Date().toISOString();
 const promotion={schemaVersion:1,family:'promotion',revisionId:id,pieceId,originComposite:{recordId,revisionId:origin.revisionId,versionId:origin.versionId},at,by:user.email,requestHash};
 // This is an independent release record. No original clearance, filing,
 // numbering, verification or publication status is copied into it.
 const release={pool:'unassigned',posted:false,exposures:[],originComposite:promotion.originComposite};
 const guards=SOURCE_COLLECTIONS.map((c,i)=>`COALESCE((SELECT rev FROM vf_revs WHERE collection = '${c}'),0) = ?${i+6}`).join(' AND ');
 const condition=NO_SOURCE_FENCE+' AND '+guards+" AND NOT EXISTS (SELECT id FROM vf_docs WHERE collection='release' AND id=?5)";
 const result=await env.DB.batch([
  env.DB.prepare(`INSERT INTO vf_docs(collection,id,data,updated_at,rev) SELECT 'composites',?1,?2,?3,0 WHERE ${condition} AND NOT EXISTS(SELECT id FROM vf_docs WHERE collection='composites' AND id=?1)`).bind(id,JSON.stringify(promotion),at,null,pieceId,...SOURCE_COLLECTIONS.map(c=>input.revisions[c]||0)),
  env.DB.prepare("INSERT INTO vf_docs(collection,id,data,updated_at,rev) SELECT 'release',?1,?2,?3,0 WHERE changes()=1").bind(pieceId,JSON.stringify(release),at),
  env.DB.prepare("INSERT INTO vf_revs(collection,rev) SELECT 'composites',1 WHERE changes()=1 ON CONFLICT(collection) DO UPDATE SET rev=rev+1").bind(),
  env.DB.prepare("INSERT INTO vf_revs(collection,rev) SELECT 'release',1 WHERE changes()=1 ON CONFLICT(collection) DO UPDATE SET rev=rev+1").bind(),
 ]);
 if(result.some(r=>r.meta.changes!==1))fail('head_or_source_changed');
 return answer({ok:true,promotion});
}
