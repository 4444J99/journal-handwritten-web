// Real Pages Functions + local D1/R2. Review confirmations below are local test
// fixtures only; they are never written to the hosted author's database.
import {spawnSync} from 'node:child_process';
import {test} from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs/promises';import path from 'node:path';
import {makeKey,signRS256,claims,startJwks} from './helpers/jwt.mjs';import {startPagesDev,STUDIO_CF} from './helpers/wrangler.mjs';import {createPublishClient} from '../../studio/publish-client.mjs';
test('authenticated free build, immutable preview, confirm, and separate public reader work through local bindings', {timeout:180000},async()=>{
 const dist=path.join(STUDIO_CF,'dist');
 const readerDir=path.join(STUDIO_CF,'../.post-poem-work','public-reader-local-'+Date.now());
 const built=spawnSync('python3',[path.join(STUDIO_CF,'build_reader.py'),'--out',readerDir],{encoding:'utf8'});assert.equal(built.status,0,built.stderr);
 const pin=JSON.parse(await fs.readFile(path.join(dist,'publish/pin.json'),'utf8'));
 const source=JSON.parse(await fs.readFile(path.join(dist,'publish/source.json'),'utf8'));
 const key=makeKey('publish-local'),jwks=await startJwks({keys:[key]}),team='127.0.0.1:'+jwks.port,iss='https://'+team,owner='owner@example.test',aud='publish-local';
 function signedAssertion(email) {return signRS256(key,claims({iss,aud,email}));}let srv,reader;
 try{
  srv=await startPagesDev({ACCESS_TEAM_DOMAIN:team,ACCESS_AUD:aud,OWNER_EMAILS:owner,READONLY_EMAILS:'reader@example.test',ACCESS_JWKS_URL_TEST:'http://'+team+'/cdn-cgi/access/certs',PUBLISH_SHELL_SHA256:pin.shellSha256,PUBLISH_BUILD_MODE:'browser'},'publish',{dir:dist});
  const fetchAs=(email=owner)=>async(url,options={})=>fetch(srv.base+url,{...options,headers:{...options.headers,'Cf-Access-Jwt-Assertion':signedAssertion(email),...(options.method==='POST'?{origin:srv.base}:{})},redirect:'manual'});
  const authFetch=fetchAs();
  for(const [coll,id,data] of [['release','p001',{pool:'series'}],['decisions','gruw-policy',{choice:'skip'}],['decisions','release-numbering',{choice:'as-posted'}]]){const r=await authFetch('/api/db/'+coll+'/'+id,{method:'PUT',headers:{'content-type':'application/json'},body:JSON.stringify(data)});assert.equal(r.status,200);}
  const item=source.review.items.find(i=>i.id==='p001'),pages=new Map(source.review.pages.map(p=>[p.id,p]));
  for(const v of item.versions)for(const bi of v.blocks)for(const l of pages.get(v.page).blocks[bi].lines){const r=await authFetch('/api/db/reviews/'+l.id,{method:'PUT',headers:{'content-type':'application/json'},body:JSON.stringify({status:'confirmed',original:l.tx})});assert.equal(r.status,200);}
  assert.equal((await fetch(srv.base+'/api/publish/history')).status,403);
  assert.equal((await fetchAs('reader@example.test')('/api/publish/context',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({target:'staging'})})).status,403);
  const sourceRoute=await authFetch('/publish/shell.html');assert.equal(sourceRoute.status,308);assert.equal(sourceRoute.headers.get('location'),'/publish/shell');assert.equal((await authFetch('/publish/shell')).status,200);
  const api=createPublishClient({fetchImpl:authFetch}),candidate=await api.build({pieces:['p001'],allVersions:[],accepted:[],target:'staging'});
  assert.ok(candidate.id,JSON.stringify({gates:candidate.gates,stops:candidate.stops}));
  const preview=await authFetch(candidate.preview);assert.equal(preview.status,200);assert.equal(preview.headers.get('cache-control'),'no-store');const html=await preview.text();assert.ok(html.includes('<title>versforms</title>'));assert.ok(!html.includes('not yet checked'));
  const wrong=await authFetch('/api/publish/confirm',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({id:candidate.id,hash:'f'.repeat(64)})});assert.equal(wrong.status,409);
  const result=await api.confirm(candidate);assert.equal(result.done,true);
  const history=await api.history();assert.equal(history.pointers.staging.id,candidate.id);
  const release=await(await authFetch('/api/db/release/p001')).json();assert.equal(release.data.exposures[0].type,'site');assert.equal(release.data.exposures[0].target,'staging');assert.equal(release.data.num,undefined);
  const persist=srv.persist;await srv.stop();srv=null;
  reader=await startPagesDev({},'publish-reader',{dir:path.join(readerDir,'staging/site'),persist,cwd:path.join(readerDir,'staging')});
  const page=await fetch(reader.base+'/');assert.equal(page.status,200);assert.equal(page.headers.get('x-robots-tag'),'noindex');assert.ok((await page.text()).includes('/_snapshot/'+candidate.id+'/'),reader.log().split('\n').filter(l=>/config|wrangler|bucket|Binding|PUBLIC|staging/.test(l)).join('\n'));
  const data=await(await fetch(reader.base+'/data/j.json')).json();assert.deepEqual(data.pieces.map(p=>p.id),['p001']);
  const tile=await fetch(reader.base+'/img/a/t0.jpg');assert.equal(tile.status,200);assert.equal(tile.headers.get('content-type'),'image/png');
  for(const hidden of ['/publish/source.json','/api/db/reviews','/current.json','/drafts/'+candidate.id+'/candidate.json','/img/p/missing.jpg'])assert.equal((await fetch(reader.base+hidden)).status,404,hidden);
 }finally{if(reader)await reader.stop();if(srv)await srv.stop();await jwks.close();}
});
