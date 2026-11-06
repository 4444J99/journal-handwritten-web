import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {contractDigest,evaluateRelease,eventChannels,validateOutputManifest,validUTCInstant} from '../studio/release-contract.mjs';

function fixture() {
  const sources=[{pieceId:'fixture-p',versionId:'fixture-v',sourceFingerprint:contractDigest({source:'café'})}];
  const component={kind:'audio',id:'fixture-audio',...sources[0],revisionDigest:contractDigest({revision:1}),fixture:false,path:'samples/a.wav',sha256:contractDigest({bytes:1})};
  const body={schema:'versforms.release-output.v1',files:[{path:component.path,bytes:1,sha256:component.sha256}],sources,components:[component],inputs:{},code:{},exposure:{}};
  const manifest={...body,manifestDigest:contractDigest(body)};
  const clearance={schema:'versforms.release-clearance.v1',status:'approved',manifestDigest:manifest.manifestDigest,execution_authority:false,
    author_clearance:{actor:'synthetic-test-author',source:'synthetic:test',at:'2026-01-01T00:00:00Z',manifestDigest:manifest.manifestDigest},
    pool_clearance:[{pieceId:'fixture-p',versionId:'fixture-v',pool:'series',source:'synthetic:test'}],
    evidence:Object.fromEntries(['filing_workflow','image_exposure','identity_metadata','device_acceptance'].map(k=>[k,'synthetic:test']))};
  return {manifest,clearance,sources,component};
}
test('Python and JavaScript bind the same UTF-8 output contract',()=>{
  const f=fixture(), module=fileURLToPath(new URL('../tools',import.meta.url));
  const run=spawnSync('python3',['-c','import sys,json;sys.path.insert(0,sys.argv[1]);import release_contract as r;x=json.load(sys.stdin);print(json.dumps(r.evaluate(x["manifest"],x["clearance"],current_sources=x["sources"],component=x["component"])))',module],{input:JSON.stringify(f),encoding:'utf8'});
  assert.equal(run.status,0,run.stderr);
  assert.deepEqual(JSON.parse(run.stdout),evaluateRelease(f.manifest,f.clearance,{currentSources:f.sources,component:f.component}));
});
test('source revisions, pronunciation, geometry or bank digests invalidate media clearance',()=>{
  const {manifest,clearance,sources,component}=fixture();
  assert.equal(evaluateRelease(manifest,clearance,{currentSources:sources,component}).eligible,true);
  for(const field of ['pronunciation','geometry','bank','text']) {
    const changed={...component,revisionDigest:contractDigest({[field]:'changed'})};
    assert.equal(evaluateRelease(manifest,clearance,{currentSources:sources,component:changed}).eligible,false);
  }
  assert.equal(evaluateRelease(manifest,null,{currentSources:sources,component}).eligible,false);
  assert.equal(evaluateRelease(manifest,clearance,{component}).eligible,false);
});
test('tampered inventories and synthetic fixtures cannot become eligible',()=>{
  const {manifest,clearance,sources,component}=fixture();
  const changed=structuredClone(manifest);changed.files[0].bytes=2;
  assert.ok(validateOutputManifest(changed).includes('output-manifest-changed'));
  assert.equal(evaluateRelease(manifest,clearance,{currentSources:sources,component:{...component,fixture:true}}).eligible,false);
});
test('hash fields reject coercible JSON values in both runtimes',()=>{
  const mutations=[
    m=>{m.components=[];m.files[0].sha256=[m.files[0].sha256];},
    m=>{m.components=[];m.sources[0].sourceFingerprint=[m.sources[0].sourceFingerprint];},
    m=>{m.components[0].revisionDigest=[m.components[0].revisionDigest];},
    m=>{m.components[0].sourceFingerprint=[m.components[0].sourceFingerprint];},
  ];
  for(const mutate of mutations){
    const {manifest,clearance}=fixture();mutate(manifest);
    const {manifestDigest,...body}=manifest;manifest.manifestDigest=contractDigest(body);
    clearance.manifestDigest=manifest.manifestDigest;clearance.author_clearance.manifestDigest=manifest.manifestDigest;
    const result=evaluateRelease(manifest,clearance,{currentSources:manifest.sources});
    const run=spawnSync('python3',['-c','import sys,json;sys.path.insert(0,sys.argv[1]);import release_contract as r;x=json.load(sys.stdin);print(json.dumps(r.evaluate(x["manifest"],x["clearance"],current_sources=x["manifest"]["sources"])))',fileURLToPath(new URL('../tools',import.meta.url))],{input:JSON.stringify({manifest,clearance}),encoding:'utf8'});
    assert.equal(run.status,0,run.stderr);assert.equal(result.eligible,false);
    assert.deepEqual(JSON.parse(run.stdout),result);
  }
});
test('legacy social event on the site keeps its original type without inventing publication classification',()=>{
  const input={type:'social',url:'https://versforms.pages.dev/'};
  assert.deepEqual(eventChannels(input),{recordedType:'social',channel:'site',url:input.url,publicationClassification:null,classificationProvenance:'author-decision-pending'});
  assert.equal('pub' in input,false);
});

test('UTC timestamps require a complete valid calendar instant in both runtimes',()=>{
  const values=['2000Z','2026-02-30T00:00:00Z','0000-01-01T00:00:00Z','2026-01-01T24:00:00Z',
    '2026-01-01T00:00:00+00:00','2026-01-01T00:00:00.1234567Z',
    '2024-02-29T23:59:59Z','2026-01-01T00:00:00.1Z','2026-01-01T00:00:00.123456Z'];
  const expected=[false,false,false,false,false,false,true,true,true];
  assert.deepEqual(values.map(validUTCInstant),expected);
  const run=spawnSync('python3',['-c','import sys,json;sys.path.insert(0,sys.argv[1]);import release_contract as r;print(json.dumps([r.instant(v) for v in json.load(sys.stdin)]))',fileURLToPath(new URL('../tools',import.meta.url))],{input:JSON.stringify(values),encoding:'utf8'});
  assert.equal(run.status,0,run.stderr);assert.deepEqual(JSON.parse(run.stdout),expected);
  for(const at of values.slice(0,6)) {
    const {manifest,clearance,sources}=fixture();clearance.author_clearance.at=at;
    assert.equal(evaluateRelease(manifest,clearance,{currentSources:sources}).eligible,false);
  }
});

test('malformed event URLs and actor evidence fail closed',()=>{
  const {manifest,clearance,sources}=fixture();
  const event={schema:'versforms.release-event.v1',state:'posted',manifestDigest:manifest.manifestDigest,
    source:'synthetic:test',recordedBy:'synthetic-test-author',at:'2026-01-01T00:00:00Z',channel:'site',url:'https://example.test/output'};
  for(const url of ['https://[','https://example.test:garbage/','https://example.test:65536/',
    ' https://example.test/','https://example.test/white space',true]) {
    const result=evaluateRelease(manifest,clearance,{currentSources:sources,event:{...event,url}});
    assert.ok(result.reasons.includes('invalid-publication-url'));
  }
  for(const field of ['source','recordedBy'])assert.equal(evaluateRelease(manifest,clearance,{currentSources:sources,event:{...event,[field]:true}}).eligible,false);
  const circular=[];circular.push(circular);
  assert.equal(evaluateRelease(manifest,clearance,{currentSources:circular}).eligible,false);
});
