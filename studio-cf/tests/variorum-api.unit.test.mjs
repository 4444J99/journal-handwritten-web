import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {handleApi} from '../lib/api.js';
const owner={email:'owner@example.invalid',canWrite:true};
function setup(){
 const sql=new DatabaseSync(':memory:');sql.exec(readFileSync(new URL('../schema.sql',import.meta.url),'utf8'));
 const DB={prepare(text){return {bind(...args){return {_text:text,_args:args,async first(){return sql.prepare(text).get(...args)||null;},async all(){return {results:sql.prepare(text).all(...args)};},async run(){return {meta:{changes:Number(sql.prepare(text).run(...args).changes)}};}};}};},async batch(stmts){sql.exec('BEGIN');try{const out=stmts.map(s=>{const q=sql.prepare(s._text);return q.columns().length?{results:q.all(...s._args),meta:{changes:0}}:{results:[],meta:{changes:Number(q.run(...s._args).changes)}};});sql.exec('COMMIT');return out;}catch(e){sql.exec('ROLLBACK');throw e;}}};
 const source={j:JSON.parse(readFileSync(new URL('../../site/data/j.json',import.meta.url))),review:JSON.parse(readFileSync(new URL('../../studio/data/review.json',import.meta.url)))};
 const env={DB,ASSETS:{fetch:async()=>Response.json(source)},PHOTOS:{head:async()=>null}};
 const call=(path,method='GET',body,user=owner,headers={})=>handleApi(new Request('https://studio.test/api/variorum/'+path,{method,headers:{'content-type':'application/json',...headers},body:body===undefined?undefined:JSON.stringify(body)}),env,user);
 return {sql,call,env};
}
async function draft(s){const r=await s.call('pieces/p001');assert.equal(r.status,200);const v=await r.json();return {operationId:crypto.randomUUID(),expectedHead:v.head,sourceToken:v.sourceToken,parts:v.parts};}
test('parts save preserves immutable history and exact retry',async()=>{const s=setup(),p=await draft(s);const r=await s.call('parts/p001','PUT',p);assert.equal(r.status,200,await r.clone().text());const saved=await r.json();const retry=await s.call('parts/p001','PUT',p);assert.equal(retry.status,200);assert.equal((await retry.json()).head,saved.head);assert.equal(s.sql.prepare("SELECT rev FROM vf_revs WHERE collection='parts'").get().rev,1);assert.equal(s.sql.prepare("SELECT count(*) AS n FROM vf_docs WHERE collection='parts'").get().n,2);});
test('two initial writers have one winner and no lost revision',async()=>{const s=setup(),p=await draft(s),q={...p,operationId:crypto.randomUUID()};const responses=await Promise.all([s.call('parts/p001','PUT',p),s.call('parts/p001','PUT',q)]);assert.deepEqual(responses.map(x=>x.status).sort(),[200,409]);assert.equal(s.sql.prepare("SELECT count(*) AS n FROM vf_docs WHERE collection='parts'").get().n,2);assert.equal(s.sql.prepare("SELECT rev FROM vf_revs WHERE collection='parts'").get().rev,1);});
test('publication fence rejects save without partial history',async()=>{const s=setup(),p=await draft(s);s.sql.prepare('INSERT INTO vf_docs VALUES(?,?,?,?,?)').run('publish','source-write-fence','{}','now',0);const r=await s.call('parts/p001','PUT',p);assert.equal(r.status,409);assert.equal(s.sql.prepare("SELECT count(*) AS n FROM vf_docs WHERE collection='parts'").get().n,0);});
test('source changes and changed operation retry are rejected',async()=>{const s=setup(),p=await draft(s);s.sql.prepare('INSERT INTO vf_revs VALUES(?,?)').run('reviews',1);assert.equal((await s.call('parts/p001','PUT',p)).status,409);const q=await draft(s);assert.equal((await s.call('parts/p001','PUT',q)).status,200);assert.equal((await s.call('parts/p001','PUT',{...q,expectedHead:'different'})).status,409);});
test('read-only and cross-origin writes are denied',async()=>{const s=setup(),p=await draft(s);assert.equal((await s.call('parts/p001','PUT',p,{...owner,canWrite:false})).status,403);assert.equal((await s.call('parts/p001','PUT',p,owner,{origin:'https://attacker.invalid'})).status,403);});

test('review probe: rematerialization and lost-response retry preserve frozen history',async()=>{
 const s=setup(),p=await draft(s),from=Object.keys(p.parts.maps)[0],partId=p.parts.canonicalOrder[0];p.parts.maps[from].segments[partId][0].accepted=true;
 let r=await s.call('parts/p001','PUT',p);assert.equal(r.status,200);const map=await r.json();let state=await (await s.call('pieces/p001')).json();
 const recipe=[{from,partId,occurrence:1}],op={operationId:crypto.randomUUID(),sourceToken:state.sourceToken,expectedHead:null,pieceId:'p001',partsRevisionId:map.head,recipe,caseMode:'asis'};
 r=await s.call('composites','POST',op);assert.equal(r.status,200,await r.clone().text());const saved=await r.json();const frozen=saved.revision.text;
 const line=state.catalog.pieces.find(p=>p.pieceId==='p001').versions.find(v=>v.versionId===from).lines[0];const correct=text=>{s.sql.prepare("INSERT OR REPLACE INTO vf_docs VALUES(?,?,?,?,?)").run('reviews',line.lineId,JSON.stringify({status:'corrected',original:line.originalText,text}),'now',1);s.sql.prepare("INSERT INTO vf_revs VALUES('reviews',1) ON CONFLICT(collection) DO UPDATE SET rev=rev+1").run();};
 correct('technical correction 1');r=await s.call('composites','POST',op);assert.equal(r.status,200);assert.equal((await r.json()).revision.text,frozen);
 state=await (await s.call('pieces/p001')).json();const remat={operationId:crypto.randomUUID(),sourceToken:state.sourceToken,expectedHead:saved.head};
 r=await s.call('composites/'+saved.revision.recordId+'/rematerialize','POST',remat);assert.equal(r.status,200,await r.clone().text());const next=await r.json();assert.match(next.revision.text,/technical correction 1/);assert.equal(JSON.parse(s.sql.prepare('SELECT data FROM vf_docs WHERE collection=? AND id=?').get('composites',saved.head).data).text,frozen);
 correct('technical correction 2');r=await s.call('composites/'+saved.revision.recordId+'/rematerialize','POST',remat);assert.equal(r.status,200);assert.equal((await r.json()).revision.text,next.revision.text);
});

test('photo attachment copies upload to immutable content address and retains typeset history',async()=>{
 const s=setup(),p=await draft(s),from=Object.keys(p.parts.maps)[0],partId=p.parts.canonicalOrder[0];p.parts.maps[from].segments[partId][0].accepted=true;
 const map=await (await s.call('parts/p001','PUT',p)).json();let state=await (await s.call('pieces/p001')).json();
 const first=await (await s.call('composites','POST',{operationId:crypto.randomUUID(),sourceToken:state.sourceToken,expectedHead:null,pieceId:'p001',partsRevisionId:map.head,recipe:[{from,partId,occurrence:1}],caseMode:'asis'})).json();
 const bytes=new Uint8Array([255,216,255,0]),assets=new Map([['a'.repeat(32),bytes]]);let key;
 s.env.PHOTOS={get:async id=>assets.has(id)?{arrayBuffer:async()=>assets.get(id).buffer,httpMetadata:{contentType:'image/jpeg'},size:assets.get(id).length}:null,put:async(id,value,options)=>{assert.equal(options.onlyIf.etagDoesNotMatch,'*');key=id;if(!assets.has(id))assets.set(id,new Uint8Array(value));}};
 state=await (await s.call('pieces/p001')).json();const op={operationId:crypto.randomUUID(),sourceToken:state.sourceToken,expectedHead:first.head,assetId:'a'.repeat(32)};
 const res=await s.call('composites/'+first.revision.recordId+'/photo','POST',op);assert.equal(res.status,200,await res.clone().text());const photo=await res.json();assert.match(key,/^[a-f0-9]{64}$/);assert.equal(photo.revision.photo.assetId,key);assert.equal(photo.revision.text,first.revision.text);assert.equal(photo.revision.recipe[0].from,from);assert.equal(assets.size,2);assert.equal(JSON.parse(s.sql.prepare('SELECT data FROM vf_docs WHERE collection=? AND id=?').get('composites',first.head).data).render,'typeset');
 assert.equal((await s.call('composites/'+first.revision.recordId+'/photo','POST',op)).status,200);
});
