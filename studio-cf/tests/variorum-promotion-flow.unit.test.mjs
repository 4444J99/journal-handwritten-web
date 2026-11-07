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

test('save, promote, reload and independently sort a composite',async()=>{
 const s=setup(),p=await draft(s);
 const from=Object.keys(p.parts.maps)[0],partId=p.parts.canonicalOrder[0];
 p.parts.maps[from].segments[partId][0].accepted=true;
 let response=await s.call('parts/p001','PUT',p);assert.equal(response.status,200,await response.clone().text());const parts=await response.json();
 let current=await (await s.call('pieces/p001')).json();
 response=await s.call('composites','POST',{operationId:crypto.randomUUID(),pieceId:'p001',partsRevisionId:parts.head,sourceToken:current.sourceToken,expectedHead:null,recipe:[{from,partId,occurrence:1}],caseMode:'asis'});
 assert.equal(response.status,200,await response.clone().text());const composite=await response.json();
 current=await (await s.call('pieces/p001')).json();
 const operation={operationId:crypto.randomUUID(),sourceToken:current.sourceToken,expectedHead:composite.head};
 response=await s.call('composites/'+composite.revision.recordId+'/promote','POST',operation);
 assert.equal(response.status,200,await response.clone().text());const promoted=(await response.json()).promotion;
 response=await s.call('pieces/'+promoted.pieceId);assert.equal(response.status,200,await response.clone().text());
 const catalog=await response.json();assert.equal(catalog.piece.pieceId,promoted.pieceId);assert.equal(catalog.piece.versions[0].text,composite.revision.text);
 assert.equal(catalog.piece.versions[0].kind,'composite');assert.equal(catalog.head,null);
 const release=JSON.parse(s.sql.prepare("SELECT data FROM vf_docs WHERE collection='release' AND id=?").get(promoted.pieceId).data);assert.equal(release.pool,'unassigned');assert.equal(release.posted,false);
 const update=await handleApi(new Request('https://studio.test/api/db/release/'+promoted.pieceId,{method:'PUT',headers:{'content-type':'application/json'},body:JSON.stringify({...release,pool:'reserve'})}),s.env,owner);
 assert.equal(update.status,200,await update.clone().text());
 assert.equal(JSON.parse(s.sql.prepare("SELECT data FROM vf_docs WHERE collection='release' AND id=?").get(promoted.pieceId).data).pool,'reserve');
 assert.equal(s.sql.prepare("SELECT count(*) n FROM vf_docs WHERE collection='release' AND id='p001'").get().n,0);
 const original=await (await s.call('pieces/p001')).json();assert.equal(original.composites.length,1);assert.equal(original.composites[0].text,composite.revision.text);
});
