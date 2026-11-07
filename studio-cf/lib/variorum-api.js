import {projectPromotionsIntoCatalog} from '../../studio/variorum-promotions.mjs';
import {promoteComposite} from './variorum-promotion.js';
import {buildVariorumCatalog,provisionalParts,validateParts,materializeComposite} from '../../studio/variorum-model.mjs';
import {stableJSON,sha256} from '../../studio/source-fingerprint.mjs';
import {SOURCE_COLLECTIONS,NO_SOURCE_FENCE,revisionStatement,revisionValues} from './publish-fence.js';
const ID=/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/;
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;
const response=(x,status=200)=>new Response(JSON.stringify(x),{status,headers:{'content-type':'application/json','cache-control':'no-store'}});
const assert=(ok,error,status=400)=>{if(!ok){const e=new Error(error);e.status=status;throw e;}};
async function inputs(env){
 const res=await env.ASSETS.fetch(new Request('https://studio.invalid/publish/source.json'));assert(res.ok,'source_unavailable',503);const source=await res.json();
 const names=SOURCE_COLLECTIONS;const rows=await env.DB.batch([...names.map(c=>env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 ORDER BY id').bind(c)),revisionStatement(env)]);
 const db=Object.fromEntries(names.map((c,i)=>[c,Object.fromEntries(rows[i].results.map(r=>[r.id,JSON.parse(r.data)]))]));
 const revisions=revisionValues(rows[names.length].results),sourceHash=sha256(stableJSON(source));
 const supplement=source.variorumSupplement||{schemaVersion:1,sources:[]};
 const catalog=projectPromotionsIntoCatalog(buildVariorumCatalog({versionMap:source.j,review:source.review,reviews:db.reviews,supplement}),db.composites);
 for(const [id,version]of Object.entries(db.versions||{})){const piece=catalog.pieces.find(p=>p.pieceId===version.pieceId);if(piece&&!piece.versions.some(v=>v.versionId===id))piece.versions.push({pieceId:piece.pieceId,versionId:id,kind:'notebook',available:false,members:[],lines:[],issues:['staged-untranscribed'],photo:{assetId:version.assetId},sourceFingerprint:null});}
 for(const piece of catalog.pieces)for(const version of piece.versions)version.exposures=[...new Map([...(version.exposures||[]),...(db.release[piece.pieceId]?.exposures||[]),...Object.entries(db.versions||{}).filter(([id,v])=>id===version.versionId||v.versionId===version.versionId).flatMap(([,v])=>v.exposures||v.exposure||[])].map(e=>[stableJSON(e),structuredClone(e)])).values()];
 return {db,revisions,catalog,sourceHash,sourceToken:sha256(stableJSON({sourceHash,revisions}))};
}
async function save(env,user,input,coll,recordId,payload,derived){
 const revisionId='r.'+payload.operationId,headId='h.'+recordId;
 const requestHash=sha256(stableJSON(payload));
 const old=input.db[coll]?.[revisionId];
 if(old){assert(old.requestHash===requestHash&&old.recordId===recordId,'operation_conflict',409);return response({ok:true,head:revisionId,revision:old,replayed:true});}
 assert(payload.sourceToken===input.sourceToken,'source_changed',409);
 const head=input.db[coll]?.[headId];assert((head?.revisionId||null)===(payload.expectedHead||null),'head_changed',409);
 const revision={...derived,schemaVersion:1,family:coll==='parts'?'parts':'composite',recordId,revisionId,parent:head?.revisionId||null,at:new Date().toISOString(),by:user.email,requestHash};
 const data=JSON.stringify(revision);assert(new TextEncoder().encode(data).length<=65536,'too_large',413);
 const guards=SOURCE_COLLECTIONS.map((c,i)=>`COALESCE((SELECT rev FROM vf_revs WHERE collection = '${c}'), 0) = ?${i+8}`).join(' AND ');
 const condition=NO_SOURCE_FENCE+' AND COALESCE((SELECT json_extract(data, \'$.revisionId\') FROM vf_docs WHERE collection = ?1 AND id = ?5), \'\') = ?6 AND '+guards;
 const now=revision.at;
 const results=await env.DB.batch([
  env.DB.prepare(`INSERT INTO vf_docs (collection,id,data,updated_at,rev) SELECT ?1,?2,?3,?4,0 WHERE ${condition} AND NOT EXISTS (SELECT id FROM vf_docs WHERE collection=?1 AND id=?2)`).bind(coll,revisionId,data,now,headId,payload.expectedHead||'',null,...SOURCE_COLLECTIONS.map(c=>input.revisions[c])),
  env.DB.prepare('INSERT INTO vf_docs (collection,id,data,updated_at,rev) SELECT ?1,?2,?3,?4,0 WHERE changes() = 1 ON CONFLICT(collection,id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at').bind(coll,headId,JSON.stringify({schemaVersion:1,recordId,revisionId}),now),
  env.DB.prepare('INSERT INTO vf_revs (collection,rev) SELECT ?1,1 WHERE changes() = 1 ON CONFLICT(collection) DO UPDATE SET rev=rev+1').bind(coll),
 ]);
 assert(results[0].meta.changes===1,'head_or_source_changed',409);
 return response({ok:true,head:revisionId,revision});
}
export async function handleVariorum(request,env,user,path,readLimited){
 try{
  const method=request.method,writing=!['GET','HEAD'].includes(method);
  assert(!writing||user.canWrite,'forbidden',403);
  if(writing){assert(!request.headers.get('origin')||request.headers.get('origin')===new URL(request.url).origin,'forbidden',403);assert(!request.headers.get('sec-fetch-site')||['same-origin','none'].includes(request.headers.get('sec-fetch-site')),'forbidden',403);}
  const input=await inputs(env);
  if(method==='GET'&&path[0]==='pieces'&&path.length===2){const pieceId=path[1];assert(ID.test(pieceId),'invalid_piece');const piece=input.catalog.pieces.find(p=>p.pieceId===pieceId);assert(piece,'not_found',404);const head=input.db.parts?.['h.'+pieceId];const parts=head?input.db.parts[head.revisionId]:provisionalParts(input.catalog,pieceId);return response({catalog:input.catalog,piece,parts,head:head?.revisionId||null,sourceToken:input.sourceToken,composites:Object.values(input.db.composites||{}).filter(x=>x.family==='composite'&&x.pieceId===pieceId)});}
  const bytes=await readLimited(request,65536);assert(bytes,'too_large',413);let p;try{p=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{assert(false,'invalid_json');}
  assert(p&&UUID.test(p.operationId),'invalid_operation');
  const writeCollection=path[0]==='parts'?'parts':path[0]==='composites'?'composites':null;
  const replay=writeCollection&&input.db[writeCollection]?.['r.'+p.operationId];
  if(replay){assert(replay.requestHash===sha256(stableJSON(p)),'operation_conflict',409);return response({ok:true,head:replay.revisionId,revision:replay,replayed:true});}
  if(method==='PUT'&&path[0]==='parts'&&path.length===2){const record=Object.fromEntries(['pieceId','parts','canonicalOrder','linkedPieces','maps','provisional'].filter(k=>Object.hasOwn(p.parts||{},k)).map(k=>[k,structuredClone(p.parts[k])]));assert(record?.pieceId===path[1],'piece_mismatch');validateParts(input.catalog,record);return await save(env,user,input,'parts',path[1],p,record);}
  if(method==='POST'&&path[0]==='composites'&&path.length===1){assert(ID.test(p.pieceId),'invalid_piece');const parts=input.db.parts?.[p.partsRevisionId];assert(parts?.pieceId===p.pieceId,'parts_revision_missing');assert(p.title===undefined||typeof p.title==='string','invalid_title');const result=materializeComposite(input.catalog,parts,p.recipe,p.caseMode);const recordId=p.recordId||'c-'+p.operationId;assert(ID.test(recordId),'invalid_record');return await save(env,user,input,'composites',recordId,p,{pieceId:p.pieceId,versionId:'c-'+p.operationId,title:p.title?.trim()||new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date()),partsRevisionId:p.partsRevisionId,...result});}
  if(method==='POST'&&path[0]==='composites'&&path.length===3&&path[2]==='promote')return await promoteComposite(env,user,input,path[1],p);
  if(method==='POST'&&path[0]==='composites'&&path.length===3){const recordId=path[1],head=input.db.composites?.['h.'+recordId],old=input.db.composites?.[head?.revisionId];assert(old,'not_found',404);
   if(path[2]==='rematerialize'){assert(old.render==='typeset','photographed_composite',409);const parts=input.db.parts?.[old.partsRevisionId];const result=materializeComposite(input.catalog,parts,old.recipe,old.caseMode);return await save(env,user,input,'composites',recordId,p,{pieceId:old.pieceId,versionId:'c-'+p.operationId,partsRevisionId:old.partsRevisionId,...result});}
   if(path[2]==='photo'){assert(/^(?:[a-f0-9]{32}|[a-f0-9]{64})$/.test(p.assetId),'invalid_asset');const asset=await env.PHOTOS.get(p.assetId);assert(asset,'missing_asset');const photoBytes=await asset.arrayBuffer();const photoHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',photoBytes))).map(x=>x.toString(16).padStart(2,'0')).join('');const contentType=asset.httpMetadata?.contentType;await env.PHOTOS.put(photoHash,photoBytes,{onlyIf:{etagDoesNotMatch:'*'},httpMetadata:{contentType}});const {revisionId,parent,at,by,requestHash,...frozen}=old;return await save(env,user,input,'composites',recordId,p,{...frozen,versionId:'c-'+p.operationId,render:'photo',photo:{assetId:photoHash,uploadedAssetId:p.assetId,sha256:photoHash,size:photoBytes.byteLength,contentType},geometryStatus:'unavailable'});}
  }
  return response({error:'not_found'},404);
 }catch(e){return response({error:e.status?e.message:'invalid_variorum',detail:e.status?undefined:e.message},e.status||400);}
}
