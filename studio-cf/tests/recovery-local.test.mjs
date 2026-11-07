// Real Wrangler/Miniflare databases, synthetic documents, loopback only.
// Proves complete-state restart/export/resumable restore and namespace isolation.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {startPagesDev,d1Execute,SCRATCH,STUDIO_CF} from './helpers/wrangler.mjs';
import {makeKey,signRS256,claims,startJwks} from './helpers/jwt.mjs';
import {createArtifactRevision,artifactHeads} from '../../studio/artifact-model.mjs';
import {contractDigest} from '../../studio/release-contract.mjs';
import {buildSourceCatalog,createAnchor,createRevision,heads} from '../../studio/notes-model.mjs';

const COLLECTIONS=['reviews','decisions','versions','release','batches','rconfig','notes','contributions','artifacts'];
function python(script,args) {
  return new Promise((resolve,reject)=>{
    const p=spawn('python3',[path.join(STUDIO_CF,script),...args],{env:process.env,stdio:['ignore','pipe','pipe']});
    let out='';p.stdout.on('data',d=>out+=d);p.stderr.on('data',d=>out+=d);
    p.on('error',reject);p.on('exit',code=>code===0?resolve(out):reject(new Error(script+' failed '+code+'\n'+out)));
  });
}
function fixtureDocuments() {
  const site={pieces:[{id:'fixture-p',V:[{id:'fixture-v',P:[['fixture-page',[0]]]}]}]};
  const review={pages:[{id:'fixture-page',blocks:[{t:'text',lines:[{id:'fixture-line',tx:'[TECHNICAL FIXTURE] source'}]}]}]};
  const catalog=buildSourceCatalog(site,review),anchor=createAnchor(catalog,{pieceId:'fixture-p',versionId:'fixture-v',lineId:'fixture-line'});
  const docs=Object.fromEntries(COLLECTIONS.map(c=>[c,{}]));
  for(const c of COLLECTIONS.slice(0,6)) docs[c]['fixture-legacy']={original:'[TECHNICAL FIXTURE] raw',status:'test-only',provenance:{fixture:true},nested:{unicode:'café',values:[1,true,null]}};
  for(const family of ['note','contribution']) {
    const base={family,recordId:family+'-fixture',revisionId:family+'-r1',anchor,text:'[TECHNICAL FIXTURE] first',fixture:true,
      author:{id:'synthetic-author',credit:'Technical fixture',provenance:'technical-fixture',sourceIds:['tests/recovery-local.test.mjs']}};
    const first=createRevision(base,{at:'2026-01-01T00:00:00.000Z'});
    const second=createRevision({...base,revisionId:family+'-r2',text:'[TECHNICAL FIXTURE] second'},{previous:first,at:'2026-01-02T00:00:00.000Z'});
    const collection=family==='note'?'notes':'contributions';
    docs[collection][first.revisionId]=first;docs[collection][second.revisionId]=second;
    if(family==='note') {
      const fork=createRevision({...base,revisionId:'note-r2-fork',text:'[TECHNICAL FIXTURE] concurrent branch'},{previous:first,at:'2026-01-02T00:00:00.000Z'});
      docs.notes[fork.revisionId]=fork;
    }
  }
  const source={pieceId:'fixture-p',versionId:'fixture-v',sourceFingerprint:catalog.pieces[0].versions[0].fingerprint};
  for(const kind of ['audio-feedback','pronunciation']) {
    const payload=kind==='audio-feedback'?{sampleId:'fixture-sample',decision:'unreviewed',notes:'[TECHNICAL FIXTURE]',renderDigest:contractDigest({render:1}),pronunciationDigest:contractDigest({pronunciation:1}),bankDigest:contractDigest({bank:1})}:{entries:[{lineId:'fixture-line',token:'TEST',pronunciation:'TEST'}]};
    const first=createArtifactRevision({kind,recordId:kind+'-record',revisionId:kind+'-r1',source,payload,fixture:true},{at:'2026-01-01T00:00:00Z',by:'technical-test'});
    const second=createArtifactRevision({...first,revisionId:kind+'-r2',parents:[first.revisionId],reason:'private-review'},{previous:first,at:'2026-01-02T00:00:00Z',by:'technical-test'});
    const fork=createArtifactRevision({...first,revisionId:kind+'-fork',parents:[first.revisionId],reason:'concurrent-review'},{previous:first,at:'2026-01-02T00:00:00Z',by:'technical-test'});
    for(const r of [first,second,fork])docs.artifacts[r.revisionId]=r;
  }
  return docs;
}

test('all collections survive save, reload, restart, export and independent resumed restore; other tables survive', {timeout:180000}, async t=>{
  fs.mkdirSync(SCRATCH,{recursive:true});
  const work=fs.mkdtempSync(path.join(SCRATCH,'recovery-'));
  const key=makeKey('recovery-key'),jwks=await startJwks({keys:[key]});
  let first,second;
  t.after(async()=>{if(first)await first.stop();if(second)await second.stop();await jwks.close();});
  const team=`127.0.0.1:${jwks.port}`,vars={ACCESS_TEAM_DOMAIN:team,ACCESS_AUD:'recovery-audience',OWNER_EMAILS:'owner@example.test',ACCESS_JWKS_URL_TEST:`http://${team}/cdn-cgi/access/certs`};
  const token=signRS256(key,claims({iss:`https://${team}`,aud:vars.ACCESS_AUD,email:vars.OWNER_EMAILS}));
  const headers={'Cf-Access-Jwt-Assertion':token,'Content-Type':'application/json'};
  const docs=fixtureDocuments();
  const write=async(srv,c,id,data)=>{
    const r=await fetch(srv.base+'/api/db/'+c+'/'+id,{method:'PUT',headers,body:JSON.stringify(data)});
    assert.equal(r.status,200,await r.text());
  };
  const snapshot=async srv=>{
    const result={};
    for(const c of COLLECTIONS) {
      const r=await fetch(srv.base+'/api/db/'+c,{headers});assert.equal(r.status,200);
      result[c]=Object.fromEntries((await r.json()).docs.map(d=>[d.id,d.data]));
    }
    return result;
  };
  first=await startPagesDev(vars,'recovery-source');
  await d1Execute(first.persist,['--command',"CREATE TABLE submissions(id TEXT PRIMARY KEY,value TEXT); INSERT INTO submissions VALUES ('sentinel','other-project-source');"]);
  for(const c of COLLECTIONS)for(const [id,data] of Object.entries(docs[c]))await write(first,c,id,data);
  assert.deepEqual(await snapshot(first),docs);
  const persist=first.persist;await first.stop();first=null;
  first=await startPagesDev(vars,'recovery-restart',{persist});
  assert.deepEqual(await snapshot(first),docs);
  const exported=path.join(work,'export');
  await python('export_db.py',['--local',persist,'--out',exported]);
  second=await startPagesDev(vars,'recovery-target');
  assert.notEqual(second.persist,persist);
  await d1Execute(second.persist,['--command',"CREATE TABLE submissions(id TEXT PRIMARY KEY,value TEXT); INSERT INTO submissions VALUES ('sentinel','other-project-target');"]);
  // Simulate interruption after one immutable revision; restore resumes by
  // create-or-identical without rewriting that revision or losing the fork.
  await write(second,'notes','note-r1',docs.notes['note-r1']);
  const restoreArgs=[exported,'--local',second.persist];
  if(process.env.WRANGLER_BIN)restoreArgs.push('--wrangler',process.env.WRANGLER_BIN);
  await python('import_export.py',restoreArgs);
  assert.deepEqual(await snapshot(second),docs);
  await python('import_export.py',restoreArgs);
  assert.deepEqual(await snapshot(second),docs);
  const snapshotDocs=await snapshot(second);
  const graph=heads(Object.values(snapshotDocs.notes));
  assert.equal(graph.length,1);assert.equal(graph[0].conflicted,true);assert.equal(graph[0].heads.length,2);
  const artifactGraph=artifactHeads(Object.values(snapshotDocs.artifacts),[Object.values(docs.artifacts)[0].source]);
  assert.equal(artifactGraph.length,2);assert.ok(artifactGraph.every(g=>g.conflicted && g.heads.length===2));
  const artifactCollision=await fetch(second.base+'/api/db/artifacts/audio-feedback-r1',{method:'PUT',headers,body:JSON.stringify({...docs.artifacts['audio-feedback-r1'],reason:'collision'})});
  assert.equal(artifactCollision.status,409);
  const collision=await fetch(second.base+'/api/db/notes/note-r1',{method:'PUT',headers,body:JSON.stringify({...docs.notes['note-r1'],text:'[TECHNICAL FIXTURE] collision'})});
  assert.equal(collision.status,409);
  assert.deepEqual((await snapshot(second)).notes,docs.notes);
  assert.match(await d1Execute(first.persist,['--command','SELECT value FROM submissions']),/other-project-source/);
  assert.match(await d1Execute(second.persist,['--command','SELECT value FROM submissions']),/other-project-target/);
  const receipt={schema:'versforms.local-recovery.v1',scope:'synthetic-loopback-only',collections:Object.fromEntries(COLLECTIONS.map(c=>[c,Object.keys(docs[c]).length])),
    restart:true,independentDatabase:true,identicalRetry:true,interruptedRestoreResumed:true,forksRetained:6,artifactCollisionsRefused:true,collisionRefused:true,unrelatedSentinelsUnchanged:true};
  fs.writeFileSync(path.join(work,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
  console.log('recovery receipt '+path.join(work,'receipt.json'));
});
