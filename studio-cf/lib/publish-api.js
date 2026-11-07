// Owner-only publication state machine. R2 drafts and snapshots are immutable;
// only copy progress and current.json change. The pointer is compare-and-swap.
import {buildCandidate,canonical,digest,encode,hasNameLeak,hasByteNameLeak} from './publish.js';
import {json,readLimited} from './api.js';
import {revisionStatement,revisionValues,readFence,acquireFence,releaseFence} from './publish-fence.js';

const ID=/^[a-f0-9]{64}$/;
const COLLECTIONS=['reviews','decisions','versions','release','batches','rconfig','parts','composites'];
const BATCH_SIZE=4;
const MAX_FILE=16*1024*1024;
const fail=(status,code)=>{const e=new Error(code);e.status=status;throw e;};
const check=(ok,code='candidate_mismatch')=>{if(!ok)fail(409,code);};
const now=()=>new Date().toISOString();
const stamp=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const draftKey=id=>`drafts/${id}/candidate.json`;
const stateKey=id=>`drafts/${id}/state.json`;
const fileKey=(id,path)=>`drafts/${id}/files/${path}`;

function target(env,name) {
  if(!['staging','production'].includes(name))fail(400,'invalid_target');
  const bucket=name==='staging'?env.STAGING:env.PUBLIC;
  if(!bucket)fail(503,'target_not_configured');
  const url=name==='staging' ? env.PUBLISH_STAGING_URL || 'https://versforms-staging.pages.dev/' : env.PUBLISH_PUBLIC_URL || 'https://versforms.pages.dev/';
  return {bucket,url};
}
async function pointer(bucket) {
  const obj=await bucket.get('current.json');
  if(!obj)return{value:null,etag:null};
  const value=await obj.json();
  if(value.id===null && /^[a-f0-9]{64}$/.test(value.fence || ''))return{value:null,etag:obj.etag};
  if(!ID.test(value.id))fail(503,'invalid_pointer');
  const {fence,...logical}=value;
  return{value:logical,etag:obj.etag};
}
const condition=etag=>({onlyIf:etag?{etagMatches:etag}:{etagDoesNotMatch:'*'}});
async function immutable(bucket,path,body,options={}) {
  const result=await bucket.put(path,body,{...options,onlyIf:{etagDoesNotMatch:'*'}});
  if(!result) {
    const old=await bucket.get(path);
    check(old && await digest(await old.arrayBuffer())===await digest(body),'immutable_object_conflict');
  }
}
async function doc(env,id) {
  const row=await env.DB.prepare('SELECT data FROM vf_docs WHERE collection = ?1 AND id = ?2').bind('publish',id).first();
  return row ? JSON.parse(row.data) : null;
}
async function wasPublished(env,id) {
  return !!await env.DB.prepare("SELECT id FROM vf_docs WHERE collection = 'publish' AND json_extract(data, '$.state') = 'committed' AND json_extract(data, '$.action') = 'publish' AND json_extract(data, '$.to') = ?1 LIMIT 1").bind(id).first();
}
async function record(env,id,data) {
  await env.DB.batch([
    env.DB.prepare('INSERT INTO vf_revs (collection, rev) VALUES (?1, 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1').bind('publish'),
    env.DB.prepare('INSERT INTO vf_docs (collection, id, data, updated_at, rev) VALUES (?1, ?2, ?3, ?4, (SELECT rev FROM vf_revs WHERE collection = ?1)) ON CONFLICT(collection, id) DO NOTHING').bind('publish',id,JSON.stringify(data),now()),
  ]);
  check(canonical(await doc(env,id))===canonical(data),'history_conflict');
}

async function inputs(env) {
  if(!ID.test(env.PUBLISH_SHELL_SHA256 || ''))fail(503,'shell_pin_missing');
  const [s,h,rows]=await Promise.all([
    env.ASSETS.fetch(new Request('https://studio.invalid/publish/source.json')),
    env.ASSETS.fetch(new Request('https://studio.invalid/publish/shell')),
    env.DB.batch([...COLLECTIONS.map(c=>env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 ORDER BY id').bind(c)),revisionStatement(env)]),
  ]);
  if(!s.ok || !h.ok)fail(503,'prepared_assets_missing');
  const sourceText=await s.text(),shell=await h.text();
  const source=JSON.parse(sourceText);
  if(await digest(shell)!==env.PUBLISH_SHELL_SHA256 || source.shellSha256!==env.PUBLISH_SHELL_SHA256)fail(503,'shell_pin_mismatch');
  const db=Object.fromEntries(COLLECTIONS.map((c,i)=>[c,Object.fromEntries(rows[i].results.map(r=>[r.id,JSON.parse(r.data)]))]));
  return {source,shell,db,revisions:revisionValues(rows[COLLECTIONS.length].results),sourceHash:await digest(sourceText),dbHash:await digest(canonical(db))};
}

async function candidate(env,user,id,hash) {
  check(ID.test(id || '') && hash===id);
  const obj=await env.PHOTOS.get(draftKey(id));
  if(!obj)fail(404,'candidate_not_found');
  const raw=await bytesOf(obj);
  check(await digest(raw)===id,'candidate_digest_mismatch');
  const c=JSON.parse(new TextDecoder().decode(raw));
  check(c.owner===user.email,'candidate_owner_mismatch');
  return c;
}
async function progress(env,id) {
  const obj=await env.PHOTOS.get(stateKey(id));
  if(!obj)fail(503,'candidate_state_missing');
  return {value:await obj.json(),etag:obj.etag};
}
async function setProgress(env,id,old,value) {
  const result=await env.PHOTOS.put(stateKey(id),JSON.stringify(value),condition(old.etag));
  if(!result)fail(409,'candidate_busy_retry');
}

function summary(id,c) {
  return {id,hash:id,target:c.target,pieces:c.pieces,allVersions:c.allVersions,gates:c.gates,shared:c.shared,warnings:c.warnings,versions:c.versions,
    files:c.files.map(({path,size,sha256,contentType})=>({path,size,sha256,contentType})),readerStrings:c.readerStrings,
    preview:`/api/publish/preview/${id}/`,createdAt:c.createdAt};
}

async function build(env,user,body) {
  const {bucket}=target(env,body.target);
  await recoverCurrent(env,bucket);
  const base=await pointer(bucket);
  const input=await inputs(env);
  if(!Array.isArray(body.pieces) || body.pieces.length>200)fail(400,'invalid_pieces');
  // The request names the complete next release, not only the added poem.
  const result=await buildCandidate({...input,target:body.target,pieces:body.pieces,allVersions:body.allVersions || [],accepted:body.accepted || [],force:body.force===true});
  if(result.blocked)return json(result);
  const c={...result,sourceHash:input.sourceHash,dbHash:input.dbHash,revisions:input.revisions,shellSha256:env.PUBLISH_SHELL_SHA256,
    target:body.target,base:base.value,owner:user.email,createdAt:now(),nonce:crypto.randomUUID(),accepted:body.accepted || [],force:body.force===true};
  // Internal diagnostics that are already represented in the output need not
  // carry a duplicate private source model in the draft.
  const id=await digest(canonical(c));
  await immutable(env.PHOTOS,draftKey(id),canonical(c),{httpMetadata:{contentType:'application/json'}});
  await immutable(env.PHOTOS,stateKey(id),JSON.stringify({phase:'draft',cursor:0}));
  return json(summary(id,c));
}

async function bytesOf(obj) {
  if(!obj || obj.size>MAX_FILE)fail(409,'missing_or_oversize_file');
  return new Uint8Array(await obj.arrayBuffer());
}
async function checked(bytes,file) {
  check(bytes.byteLength===file.size && await digest(bytes)===file.sha256,'file_digest_mismatch');
  const text=/^(?:text\/|application\/(?:json|javascript))/.test(file.contentType || '');
  if(text?hasNameLeak(bytes):hasByteNameLeak(bytes))fail(409,'name_leak');
}
async function materialize(env,user,body) {
  const c=await candidate(env,user,body.id,body.hash),p=await progress(env,body.id);
  if(c.mode==='browser')return (await import('./publish-browser.js')).verifyAndMaterialize(env,user,body,c,p);
  if(p.value.phase!=='draft')return json({ready:true,cursor:c.files.length,total:c.files.length});
  const end=Math.min(p.value.cursor+BATCH_SIZE,c.files.length);
  for(const f of c.files.slice(p.value.cursor,end)) {
    let bytes;
    if(f.text!==undefined)bytes=encode(f.text);
    else {
      if(/^photos\/(?:[a-f0-9]{32}|[a-f0-9]{64})$/.test(f.sourcePath)) {
        bytes=await bytesOf(await env.PHOTOS.get(f.sourcePath.slice('photos/'.length)));
      } else {
        if(!/^(?:img\/[a-z]\/|tiles\/|reader-(?:features|packages)\.js$)/.test(f.sourcePath) || f.sourcePath.includes('..'))fail(409,'invalid_asset_path');
        const response=await env.ASSETS.fetch(new Request('https://studio.invalid/publish/assets/'+f.sourcePath));
        if(!response.ok)fail(409,'source_asset_missing');
        bytes=new Uint8Array(await response.arrayBuffer());
      }
    }
    await checked(bytes,f);
    await immutable(env.PHOTOS,fileKey(body.id,f.path),bytes,{httpMetadata:{contentType:f.contentType},customMetadata:{sha256:f.sha256}});
  }
  const ready=end===c.files.length;
  await setProgress(env,body.id,p,{phase:ready?'ready':'draft',cursor:ready?0:end});
  return json({ready,cursor:end,total:c.files.length});
}

function publicManifest(id,c) {
  return {id,pieces:c.pieces,allVersions:c.allVersions,createdAt:c.createdAt,files:c.files.map(f=>({path:f.path,sha256:f.sha256,size:f.size,contentType:f.contentType,
    key:f.path.startsWith('img/')?`img/${f.sha256}.jpg`:`snapshots/${id}/${f.path}`}))};
}

// Independent structural check on the stored data, after re-reading its bytes.
// Unpublished blocks must be empty; text must be an exact selected source line,
// accepted reading or attributable review correction, never an arbitrary string.
async function verifyData(env,id,c,input) {
  if(!c.pieces.length){check(c.files.length===1 && c.files[0].path==='index.html','empty_snapshot_has_assets');return;}
  const raw=await env.PHOTOS.get(fileKey(id,'data/j.json'));
  const data=JSON.parse(new TextDecoder().decode(await bytesOf(raw)));
  check(canonical(data)===canonical(c.data),'stored_data_mismatch');
  check(canonical(data.pieces.map(p=>p.id))===canonical(c.pieces),'piece_list_mismatch');
  check(Object.keys(data.prov).every(k=>['tdate','verified'].includes(k)),'private_provenance');
  const allowed=new Set(data.pieces.flatMap(p=>p.V.flatMap(v=>v.P.flatMap(([pg,bs])=>bs.map(b=>`${pg}/${b}`)))));
  const sourcePages=new Map(input.source.j.pages.map(p=>[p.id,p]));
  for(const p of data.pages) {
    const source=sourcePages.get(p.id);check(source,'unknown_output_page');
    for(const [bi,b] of p.B.entries()) {
      if(!allowed.has(`${p.id}/${bi}`)){check(b.L.length===0 && !['g','v','u','lineIds','transcriptionStatus','sourceAnchor'].some(k=>k in b),'withheld_text_leak');continue;}
      check(b.L.length===source.B[bi].L.length,'line_count_mismatch');
      for(const [li,text]of b.L.entries()) {
        const lid=`${p.id}-${bi}-${li}`,original=source.B[bi].L[li],r=input.db.reviews[lid],explicit=source.B[bi].lineIds?.[li] || lid;
        const expected=b.t===4?original:r?.status==='corrected' && typeof r.text==='string'?r.text:input.source.j.acceptedReadings?.[explicit] ?? original;
        check(text===expected,'unapproved_output_text');
      }
    }
    check(p.x.every(e=>allowed.has(`${p.id}/${e[0]}`)),'withheld_geometry');
  }
}

async function releaseAppearances(env,intent) {
  if(intent.action!=='publish')return true;
  const published=await doc(env,'snapshot.'+intent.to);
  check(published,'missing_snapshot_record');
  // Read the release collection once per continuation. Rereading completed
  // pieces individually eventually exhausts D1's free invocation budget.
  const [rows,numbering]=await Promise.all([
    env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 ORDER BY id').bind('release').all(),
    env.DB.prepare('SELECT data FROM vf_docs WHERE collection = ?1 AND id = ?2').bind('decisions','release-numbering').first(),
  ]);
  const releases=new Map(rows.results.map(r=>[r.id,r.data]));
  let nextNum=1+Math.max(0,...rows.results.map(r=>JSON.parse(r.data).num).filter(n=>Number.isSafeInteger(n) && n>0));
  let changed=0;
  for(const pid of intent.added || published.pieces) {
    const before=releases.get(pid) || null, value=before?JSON.parse(before):{};
    if((value.exposures || []).some(e=>e.publishId===intent.event))continue;
    if(changed===4)return false;
    let num=value.num;
    if(intent.target==='production' && !num && numbering && JSON.parse(numbering.data).choice==='as-posted') {
      num=nextNum++;
    }
    const exposure={type:'site',date:intent.date,at:intent.at,where:intent.target==='staging'?'versforms-staging':'versforms',url:target(env,intent.target).url,publishId:intent.event,snapshotId:intent.to,target:intent.target};
    const after={...value,...(num?{num}:{}),exposures:[...(value.exposures || []),exposure],at:intent.at};
    // The predicate compares the full prior document in the same D1 statement.
    // A concurrent Studio edit never gets overwritten by an older read. A retry
    // re-merges against the latest document and the publishId prevents duplicates.
    const res=await env.DB.batch([
      env.DB.prepare('INSERT INTO vf_revs (collection, rev) VALUES (?1, 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1').bind('release'),
      env.DB.prepare('INSERT INTO vf_docs (collection, id, data, updated_at, rev) SELECT ?1, ?2, ?3, ?4, (SELECT rev FROM vf_revs WHERE collection = ?1) WHERE (?5 IS NULL AND NOT EXISTS (SELECT id FROM vf_docs WHERE collection = ?1 AND id = ?2)) OR (SELECT data FROM vf_docs WHERE collection = ?1 AND id = ?2) = ?5 ON CONFLICT(collection, id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at, rev = excluded.rev').bind('release',pid,JSON.stringify(after),intent.at,before),
    ]);
    if(!res[1].meta.changes)fail(409,'release_record_changed_retry');
    changed++;
  }
  return true;
}

async function finishIntent(env,intent) {
  if(await doc(env,intent.event+'.done'))return true;
  if(!await releaseAppearances(env,intent))return false;
  await record(env,intent.event+'.done',{...intent,state:'committed'});
  return true;
}
async function recoverCurrent(env,bucket) {
  const cur=await pointer(bucket);
  if(cur.value?.event) {
    const intent=await doc(env,cur.value.event);
    if(!intent)fail(503,'pointer_audit_missing');
    const complete=await finishIntent(env,intent);
    if(complete)await releaseFence(env,intent.event);
    else return false;
  }
  const fence=await readFence(env);
  if(fence && target(env,fence.target).bucket===bucket && cur.value?.event!==fence.event) {
    // A fresh sender may still be finishing. Time only controls when recovery
    // is attempted; it NEVER grants source writers access to an expired lease.
    if(Date.now()-Date.parse(fence.at)<5000)return false;
    // R2 ETags are content-based. Rewriting identical bytes is not a barrier:
    // include a fresh nonce even when retaining the same published snapshot.
    const value={...(cur.value || {id:null}),fence:await digest(crypto.randomUUID())};
    const barrier=await bucket.put('current.json',JSON.stringify(value),{...condition(cur.etag),httpMetadata:{contentType:'application/json'}});
    if(!barrier)return false; // a concurrent CAS won; re-read on the next request
    await record(env,fence.event+'.cancelled',{...fence,state:'cancelled',reason:'abandoned_confirmation_recovered',recoveredAt:now()});
    await releaseFence(env,fence.event);
  }
  return true;
}
async function movePointer(env,user,c,id,bucket,action,eventId) {
  if(!await recoverCurrent(env,bucket))fail(409,'previous_release_records_pending_retry');
  const old=await pointer(bucket);
  check(canonical(old.value)===canonical(c.base),'current_snapshot_changed');
  const event=eventId || 'event.'+crypto.randomUUID();
  const previous=old.value?.id ? await doc(env,'snapshot.'+old.value.id) : null;
  const intent=await doc(env,event) || {event,action,target:c.target,from:old.value?.id || null,to:id,who:user.email,at:now(),date:stamp(),state:'prepared',added:c.pieces.filter(p=>!(previous?.pieces || []).includes(p))};
  if(!await acquireFence(env,intent,c.revisions))fail(409,(await readFence(env))?'publication_in_progress_retry':'source_changed_rebuild');
  let started=false;
  try {
    await record(env,event,intent);
    // `old` was captured BEFORE acquiring the fence. Never refresh this ETag:
    // the recovery barrier must be able to cancel even a delayed conditional PUT.
    started=true;
    const moved=await bucket.put('current.json',JSON.stringify({id,event}),{...condition(old.etag),httpMetadata:{contentType:'application/json'}});
    if(!moved){await releaseFence(env,event);fail(409,'current_snapshot_changed');}
    const complete=await finishIntent(env,intent);
    if(complete)await releaseFence(env,event);
    return {...intent,complete};
  }catch(e){
    if(!started)await releaseFence(env,event);
    // An uncertain R2 result or unfinished appearance retains the fence until
    // recovery establishes the outcome. It is never released merely by a timer.
    throw e;
  }
}

async function confirm(env,user,body) {
  const c=await candidate(env,user,body.id,body.hash),{bucket,url}=target(env,c.target);
  const recovered=await recoverCurrent(env,bucket);
  const cur=await pointer(bucket);
  if(cur.value?.id===body.id) return json({done:recovered,id:body.id,url,phase:recovered?'done':'recording'});
  const history=await doc(env,'snapshot.'+body.id);
  if(history) {
    const rows=await env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 ORDER BY id').bind('publish').all();
    if(rows.results.some(r=>r.id.endsWith('.done') && JSON.parse(r.data).action==='publish' && JSON.parse(r.data).to===body.id))return json({done:true,id:body.id,url,current:cur.value?.id || null});
  }
  check(canonical(cur.value)===canonical(c.base),'current_snapshot_changed');
  let input;
  if(c.mode==='browser')await (await import('./publish-browser.js')).assertFresh(env,c);
  else {input=await inputs(env);check(input.sourceHash===c.sourceHash && input.dbHash===c.dbHash,'source_changed_rebuild');}
  const p=await progress(env,body.id);
  check(['ready','copying','stored'].includes(p.value.phase),'candidate_not_ready');
  const manifest=publicManifest(body.id,c);
  if(p.value.phase!=='stored') {
    const end=Math.min(p.value.cursor+(c.mode==='browser'?1:BATCH_SIZE),c.files.length);
    for(const [offset,f]of c.files.slice(p.value.cursor,end).entries()) {
      const bytes=await bytesOf(await env.PHOTOS.get(fileKey(body.id,f.path)));
      await checked(bytes,f);
      const publicFile=manifest.files[p.value.cursor+offset];
      await immutable(bucket,publicFile.key,bytes,{httpMetadata:{contentType:f.contentType},customMetadata:{sha256:f.sha256}});
      // Verify the bytes actually stored, not only the upload buffer.
      await checked(await bytesOf(await bucket.get(publicFile.key)),f);
    }
    const stored=end===c.files.length;
    await setProgress(env,body.id,p,{phase:stored?'stored':'copying',cursor:end});
    if(!stored)return json({done:false,cursor:end,total:c.files.length});
  }
  if(c.mode!=='browser')await verifyData(env,body.id,c,input);
  await immutable(bucket,`snapshots/${body.id}/manifest.json`,JSON.stringify(manifest),{httpMetadata:{contentType:'application/json'}});
  await record(env,'snapshot.'+body.id,{id:body.id,target:c.target,pieces:c.pieces,allVersions:c.allVersions,createdAt:c.createdAt,owner:c.owner,hash:body.id,files:manifest.files.length});
  const moved=await movePointer(env,user,c,body.id,bucket,'publish');
  return json({done:moved.complete,id:body.id,url,phase:moved.complete?'done':'recording'});
}

async function preview(request,env,user,parts) {
  if(!['GET','HEAD'].includes(request.method))fail(405,'method_not_allowed');
  const id=parts[1],c=await candidate(env,user,id,id),state=await progress(env,id);
  check(['ready','copying','stored'].includes(state.value.phase),'candidate_not_ready');
  const path=parts.slice(2).join('/') || 'index.html',file=c.files.find(f=>f.path===path);
  if(!file)fail(404,'not_found');
  const bytes=await bytesOf(await env.PHOTOS.get(fileKey(id,path)));
  await checked(bytes,file);
  return new Response(request.method==='HEAD'?null:bytes,{headers:{'content-type':file.contentType,'cache-control':'no-store','x-robots-tag':'noindex','x-content-type-options':'nosniff'}});
}

async function rollback(env,user,body) {
  check(ID.test(body.id || ''));
  const c=await candidate(env,user,body.id,body.id),{bucket,url}=target(env,body.target);
  if(c.mode==='browser')return (await import('./publish-browser.js')).rollbackBrowser(env,user,body,c);
  check(c.target===body.target,'target_mismatch');
  check(await doc(env,'snapshot.'+body.id),'snapshot_not_confirmed');
  check(await wasPublished(env,body.id),'snapshot_not_confirmed');
  const input=await inputs(env);
  check(input.sourceHash===c.sourceHash,'source_changed_rebuild');
  // Do not silently resurrect Reserve/Archive or unaccepted shared scans.
  for(const pid of c.pieces)check(input.db.release[pid]?.pool==='series','own_pool_not_series');
  for(const pid of c.sourceDependencies || [])check(!['reserve','archive'].includes(input.db.release[pid]?.pool),'composite_source_pool_changed');
  for(const shared of c.shared)if(!c.pieces.includes(shared.id) && input.source.j.pieces.some(p=>p.id===shared.id))check(input.db.release[shared.id]?.pool==='series','shared_scan_pool_changed');
  const recordObj=await bucket.get(`snapshots/${body.id}/manifest.json`);
  check(recordObj,'snapshot_missing');
  const m=await recordObj.json();check(canonical(m)===canonical(publicManifest(body.id,c)),'snapshot_manifest_mismatch');
  // Rollback verification is batched with the same confirm-copy protocol when
  // a snapshot has many files. For the direct move, trusted immutable files must
  // retain the metadata written only after byte verification by this API.
  for(const f of m.files) {
    const h=await bucket.head(f.key);check(h && h.size===f.size && h.customMetadata?.sha256===f.sha256,'snapshot_file_missing_or_changed');
  }
  const base=(await pointer(bucket)).value;
  await movePointer(env,user,{...c,base,revisions:input.revisions},body.id,bucket,'rollback');
  return json({done:true,id:body.id,url});
}

export async function handlePublish(request,env,user) {
  const owners=String(env.OWNER_EMAILS || '').split(/[\s,;]+/).map(s=>s.toLowerCase()).filter(Boolean);
  if(!user?.canWrite || typeof user.email!=='string' || !owners.includes(user.email.toLowerCase()))return json({error:'forbidden'},403);
  const url=new URL(request.url),raw=url.pathname.slice('/api/publish/'.length),parts=raw.split('/');
  if(parts.some(p=>p.includes('%') || p==='..' || p==='.' || p.includes('\\')))return json({error:'not_found'},404);
  try {
    if(parts[0]==='preview')return await preview(request,env,user,parts);
    if(parts[0]==='history' && parts.length===1) {
      if(request.method!=='GET')fail(405,'method_not_allowed');
      const pointers={};for(const t of ['staging','production'])if(env[t==='staging'?'STAGING':'PUBLIC']) {const {bucket}=target(env,t);await recoverCurrent(env,bucket);pointers[t]=(await pointer(bucket)).value;}
      const rows=await env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 ORDER BY id').bind('publish').all();
      const records=rows.results.map(r=>({id:r.id,...JSON.parse(r.data)}));
      const committed=new Set(records.filter(r=>r.state==='committed' && r.action==='publish').map(r=>r.to));
      return json({pointers,records:records.filter(r=>!r.hash || committed.has(r.id))});
    }
    if(request.method!=='POST')fail(405,'method_not_allowed');
    if(request.headers.get('origin')!==url.origin || (request.headers.get('sec-fetch-site') && request.headers.get('sec-fetch-site')!=='same-origin') || request.headers.get('content-type')?.split(';')[0].trim()!=='application/json')fail(403,'forbidden');
    if(parts.length!==1)fail(404,'not_found');
    const bytes=await readLimited(request,parts[0]==='upload-data'?768*1024:parts[0]==='propose'?512*1024:192*1024);if(!bytes)fail(413,'too_large');
    let body;try{body=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{fail(400,'invalid_json');}
    if(!body || typeof body!=='object' || Array.isArray(body))fail(400,'invalid_json');
    switch(parts[0]) {
      case 'context':return await (await import('./publish-browser.js')).browserContext(env,user,body.target);
      case 'build':
        if(env.PUBLISH_BUILD_MODE==='browser')fail(409,'browser_build_required');
        return await build(env,user,body);
      case 'propose':return await (await import('./publish-browser.js')).proposeBrowser(env,user,body);
      case 'upload-data':return await (await import('./publish-browser.js')).uploadData(env,user,body);
      case 'materialize':return await materialize(env,user,body);
      case 'confirm':return await confirm(env,user,body);
      case 'rollback':return await rollback(env,user,body);
      case 'unpublish': {
        const {bucket}=target(env,body.target),cur=await pointer(bucket);
        if(!cur.value)fail(409,'nothing_published');
        const snapshot=await doc(env,'snapshot.'+cur.value.id);check(snapshot,'snapshot_record_missing');
        check(snapshot.pieces.includes(body.piece),'piece_not_published');
        return await build(env,user,{...body,pieces:snapshot.pieces.filter(p=>p!==body.piece),allVersions:(snapshot.allVersions || []).filter(p=>p!==body.piece)});
      }
      default:fail(404,'not_found');
    }
  } catch(e) {
    if(!e.status)console.error(JSON.stringify({event:'publish_error',code:'storage_or_input_failure'}));
    return json({error:e.status?e.message:'unavailable'},e.status || 503);
  }
}

// Shared storage primitives for the bounded free-plan verifier. Importing that
// verifier dynamically avoids adding work to unrelated Studio API requests.
export {target,pointer,condition,immutable,doc,wasPublished,record,candidate,progress,setProgress,summary,bytesOf,checked,recoverCurrent,movePointer,publicManifest,fail,check,fileKey,stateKey,draftKey};
