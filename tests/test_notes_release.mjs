import test from 'node:test';
import assert from 'node:assert/strict';
import {buildSourceCatalog,createAnchor,createRevision,transitionRevision,projectRecords,contentDigest} from '../studio/notes-model.mjs';
import {recordNotePublication} from '../studio/notes-release.mjs';
import {contractDigest} from '../studio/release-contract.mjs';

// Simulated supplied author records exercise the non-fixture publication path.
// Every string and event below is synthetic test input, never actual approval.
const at='2026-01-01T00:00:00Z';
function setup() {
  const source={pieces:[{id:'p-test',V:[{id:'v-test',P:[['page-test',[0]]]}]}]};
  const review={pages:[{id:'page-test',blocks:[{t:'text',lines:[{id:'line-test',tx:'TECHNICAL TEST SOURCE'}]}]}]};
  const catalog=buildSourceCatalog(source,review), anchor=createAnchor(catalog,{pieceId:'p-test',versionId:'v-test',lineId:'line-test'});
  const initial=createRevision({family:'note',recordId:'test-note',revisionId:'test-0',anchor,
    author:{id:'synthetic-test-author',credit:'Synthetic test credit',provenance:'author-supplied',sourceIds:['synthetic:test-only']},
    poemDate:{certainty:'unknown',value:null},noteDate:'2026-01-01',kind:'footnote',text:'TECHNICAL TEST NOTE',fixture:false,visibility:'public-candidate'},{at});
  const accepted=transitionRevision(initial,'accept',{actor:'synthetic-test-author',at,revisionId:'test-1'});
  const cleared=transitionRevision(accepted,'clear',{actor:'synthetic-test-author',at,revisionId:'test-2'});
  const sources=[{pieceId:'p-test',versionId:'v-test',sourceFingerprint:catalog.pieces[0].versions[0].fingerprint}];
  const component={kind:'note',id:'test-note',...sources[0],revisionDigest:contentDigest(cleared),fixture:false,path:'note.json',sha256:contractDigest({text:cleared.text})};
  const body={schema:'versforms.release-output.v1',files:[{path:'note.json',bytes:1,sha256:component.sha256}],sources,components:[component],inputs:{},code:{},exposure:{testOnly:true}};
  const manifest={...body,manifestDigest:contractDigest(body)};
  const clearance={schema:'versforms.release-clearance.v1',status:'approved',manifestDigest:manifest.manifestDigest,execution_authority:false,
    author_clearance:{actor:'synthetic-test-author',source:'synthetic:test-only',at,manifestDigest:manifest.manifestDigest},
    pool_clearance:[{pieceId:'p-test',versionId:'v-test',pool:'series',source:'synthetic:test-only'}],
    evidence:Object.fromEntries(['filing_workflow','image_exposure','identity_metadata','device_acceptance'].map(k=>[k,'synthetic:test-only']))};
  const event={schema:'versforms.release-event.v1',state:'posted',manifestDigest:manifest.manifestDigest,recordedBy:'synthetic-test-author',source:'synthetic:test-only',at,channel:'site',url:'https://example.test/synthetic'};
  return {source,review,catalog,initial,accepted,cleared,snapshot:{notes:[initial,accepted,cleared],contributions:[]},manifest,clearance,event};
}
function release(f) {return recordNotePublication(f.snapshot,f.catalog,'test-note',{...f,revisionId:'test-3',at,by:'synthetic-test-author'});}
function project(f,doc,context=f) {return projectRecords([...f.snapshot.notes,doc],f.catalog,{mode:'public',versions:[{pieceId:'p-test',versionId:'v-test'}],releaseContext:context});}

test('exact clearance and observed event append a bound immutable note revision',()=>{
  const f=setup(),before=JSON.stringify(f.snapshot),result=release(f);
  assert.equal(JSON.stringify(f.snapshot),before);
  assert.deepEqual(result.revision.parents,['test-2']);
  assert.equal(project(f,result.revision).records.length,1);
  assert.equal(project(f,result.revision,{}).records.length,0);
  assert.equal(JSON.stringify(project(f,result.revision)).includes('synthetic:test-only'),false);
});
test('source edits, changed clearance, missing component and stale events are rejected',()=>{
  const f=setup(),result=release(f);
  const review=structuredClone(f.review);review.pages[0].blocks[0].lines[0].tx+=' CHANGED';
  const changed={...f,catalog:buildSourceCatalog(f.source,review)};
  assert.throws(()=>release(changed),/unconflicted/);
  assert.equal(project(changed,result.revision).records.length,0);
  assert.throws(()=>release({...f,clearance:null}),/refused/);
  assert.throws(()=>release({...f,event:{...f.event,manifestDigest:contractDigest({})}}),/refused/);
  const body=structuredClone(f.manifest);delete body.manifestDigest;body.components=[];
  assert.throws(()=>release({...f,manifest:{...body,manifestDigest:contractDigest(body)}}),/component/);
});
test('forked records and duplicate revision IDs cannot acquire a publication event',()=>{
  const f=setup(),fork={...f.cleared,revisionId:'test-fork',parents:['test-1']};
  assert.throws(()=>release({...f,snapshot:{notes:[...f.snapshot.notes,fork],contributions:[]}}),/unconflicted/);
  assert.throws(()=>recordNotePublication(f.snapshot,f.catalog,'test-note',{...f,revisionId:'test-2',at,by:'synthetic-test-author'}),/already exists/);
});
