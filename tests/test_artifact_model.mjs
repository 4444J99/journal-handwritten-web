import test from 'node:test';
import assert from 'node:assert/strict';
import {createArtifactRevision,assertArtifact,artifactHeads,artifactDigest} from '../studio/artifact-model.mjs';
import {createArtifactStore} from '../studio/artifact-store.mjs';
import {contractDigest} from '../studio/release-contract.mjs';

const source={pieceId:'test-piece',versionId:'test-version',sourceFingerprint:contractDigest({source:'TECHNICAL TEST'})};
const first=()=>createArtifactRevision({kind:'pronunciation',recordId:'test-pronunciation',revisionId:'test-1',source,
  payload:{entries:[{lineId:'test-line',token:'TEST',pronunciation:'te\u0301st'}]},fixture:true},{at:'2026-01-01T00:00:00Z',by:'synthetic-test-only'});
const edit=(previous,id,extra={})=>createArtifactRevision({...previous,revisionId:id,parents:[previous.revisionId],...extra},{previous,at:'2026-01-02T00:00:00Z',by:'synthetic-test-only'});

test('source edits require an explicit rebind; forks and imported fixture removal stay visible',()=>{
  const original=first(),left=edit(original,'test-2'),right=edit(original,'test-fork');
  assert.equal(Object.isFrozen(original.payload.entries[0]),true);
  assert.equal(artifactHeads([original,left,right],[source])[0].heads.length,2);
  const moved={...source,sourceFingerprint:contractDigest({changed:true})};
  assert.equal(artifactHeads([original],[moved])[0].stale,true);
  assert.throws(()=>edit(original,'test-rebind',{source:moved}),/explicit/);
  const rebound=edit(original,'test-rebind',{source:moved,reason:'source-rebind'});
  assert.equal(artifactHeads([original,rebound],[moved])[0].stale,false);
  assert.throws(()=>edit(original,'test-forged',{fixture:false}),/fixture/);
  const imported={...left,fixture:false};imported.revisionDigest=artifactDigest(imported);
  assert.ok(artifactHeads([original,imported],[source])[0].errors.includes('fixture-history-removed'));
});

test('listening feedback requires exact sample, render, pronunciation and voice-bank hashes',()=>{
  const input={kind:'audio-feedback',recordId:'test-feedback',revisionId:'test-audio',source,fixture:true,
    payload:{sampleId:'test-sample',decision:'revise',notes:'TECHNICAL TEST',renderDigest:contractDigest({render:1}),pronunciationDigest:contractDigest({pronunciation:1}),bankDigest:contractDigest({bank:1})}};
  const valid=createArtifactRevision(input,{at:'2026-01-01T00:00:00Z',by:'synthetic-test-only'});
  for(const field of ['renderDigest','pronunciationDigest','bankDigest']) {
    const bad=structuredClone(valid);delete bad.payload[field];bad.revisionDigest=artifactDigest(bad);
    assert.throws(()=>assertArtifact('artifacts',bad),/Feedback/);
  }
  const bad=structuredClone(valid);bad.payload.notes+=' changed';assert.throws(()=>assertArtifact('artifacts',bad),/digest/);
});
test('artifact identities and hash references must be strings without coercion',()=>{
  const input={kind:'audio-feedback',recordId:'test-feedback',revisionId:'test-audio',source,fixture:true,
    payload:{sampleId:'test-sample',decision:'revise',notes:'TECHNICAL TEST',renderDigest:contractDigest({render:1}),pronunciationDigest:contractDigest({pronunciation:1}),bankDigest:contractDigest({bank:1})}};
  const options={at:'2026-01-01T00:00:00Z',by:'synthetic-test-only'};
  for(const field of ['renderDigest','pronunciationDigest','bankDigest']){
    const bad=structuredClone(input);bad.payload[field]=[bad.payload[field]];
    assert.throws(()=>createArtifactRevision(bad,options),/Feedback/);
  }
  for(const field of ['pieceId','versionId','sourceFingerprint']){
    const bad=structuredClone(input);bad.source[field]=[bad.source[field]];
    assert.throws(()=>createArtifactRevision(bad,options),/source binding/);
  }
  for(const field of ['recordId','revisionId']){
    const bad=structuredClone(input);bad[field]=[bad[field]];
    assert.throws(()=>createArtifactRevision(bad,options),/identity/);
  }
  const pronunciation=structuredClone(first());pronunciation.payload.entries[0].lineId=['test-line'];
  pronunciation.revisionDigest=artifactDigest(pronunciation);
  assert.throws(()=>assertArtifact('artifacts',pronunciation),/Pronunciation/);
});

test('private artifact store verifies persisted bytes and restores the whole fork without losing Unicode',async()=>{
  function database(){const data=new Map();return {data,collection(name){assert.equal(name,'artifacts');return {
    onSnapshot(cb){cb({docs:[...data].map(([id,value])=>({id,exists:true,data:()=>structuredClone(value)}))});return ()=>{};},
    doc(id){return {async get(){return {exists:data.has(id),data:()=>structuredClone(data.get(id))};},async set(value){data.set(id,structuredClone(value));}};}
  };}};}
  const db=database(),store=createArtifactStore({db,canWrite:true});store.start();
  const original=first(),left=edit(original,'test-2'),right=edit(original,'test-fork');
  for(const r of [original,left,right])await store.append('artifacts',r);
  const backup=store.exportBackup('2026-01-02T00:00:00Z');store.stop();
  const other=database(),restored=createArtifactStore({db:other,canWrite:true});restored.start();
  assert.deepEqual(await restored.restore(backup),{added:3,unchanged:0});
  assert.deepEqual(await restored.restore(backup),{added:0,unchanged:3});
  assert.deepEqual(restored.snapshot().artifacts,backup.artifacts);
  assert.equal(artifactHeads(restored.snapshot().artifacts,[source])[0].heads.length,2);
  assert.equal(restored.snapshot().artifacts[0].payload.entries[0].pronunciation,'te\u0301st');
  restored.stop();
  const readOnly=createArtifactStore({db:other,canWrite:false});readOnly.start();
  await assert.rejects(readOnly.append('artifacts',first()),/read-only/);readOnly.stop();
});

test('artifact construction rejects inputs that JSON cloning would silently change',()=>{
  const sparse=Array(1),extended=Array(1);extended.extra='would hide the hole';
  const arrayExtra=['value'];arrayExtra.extra='lost';
  const symbol={value:'kept',[Symbol('lost')]:'lost'};
  const hidden={value:'kept'};Object.defineProperty(hidden,'lost',{value:'lost',enumerable:false});
  let read=false;const getter={};Object.defineProperty(getter,'value',{enumerable:true,get(){read=true;return 'read';}});
  const payloads=[{gain:NaN},{gain:Infinity},{lost:undefined},{recorded:new Date('2026-01-01T00:00:00Z')},
    {entries:sparse},{entries:extended},{entries:arrayExtra},symbol,hidden,getter];
  const input={kind:'audio-render',recordId:'test-render',revisionId:'test-render-1',source,fixture:true};
  for(const payload of payloads)assert.throws(()=>createArtifactRevision({...input,payload},{at:'2026-01-01T00:00:00Z',by:'synthetic-test'}),/JSON/);
  assert.equal(read,false,'validation must not invoke an input getter');
  assert.throws(()=>createArtifactRevision({...input,source:{...source,lost:undefined},payload:{}},{at:'2026-01-01T00:00:00Z',by:'synthetic-test'}),/JSON/);
  const payload={gain:0.5,notes:'te\u0301st',values:[null,1,true]};
  const good=createArtifactRevision({...input,payload},{at:'2026-01-01T00:00:00.123456Z',by:'synthetic-test'});
  assert.deepEqual(good.payload,payload);assert.notEqual(good.payload,payload);
  for(const at of ['2000Z','2026-02-30T00:00:00Z'])assert.throws(()=>createArtifactRevision({...input,payload},{at,by:'synthetic-test'}),/provenance/);
});
