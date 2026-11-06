import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {sourceFingerprint,sourceFingerprintV1} from '../studio/source-fingerprint.mjs';
import {buildSourceCatalog,createAnchor,validateAnchor,createRevision,validateRevision} from '../studio/notes-model.mjs';

const {vectors}=JSON.parse(readFileSync(new URL('./fixtures/source-fingerprint-vectors.json',import.meta.url)));
test('T02 shared vectors have identical Python and JS v1/v2 logical digests',()=>{
  for(const vector of vectors){
    assert.equal(sourceFingerprint(vector.source),vector.v2,vector.name);
    assert.equal(sourceFingerprintV1(vector.source),vector.v1,vector.name);
  }
  assert.equal(vectors[0].v2,vectors[1].v2);
  assert.equal(vectors[0].v1,vectors[2].v1);
  assert.notEqual(vectors[0].v2,vectors[2].v2);
});

const site={pieces:[{id:'fixture-piece',V:[{id:'fixture-version',P:[['fixture-page',[0,1]]]}]}]};
const review={pages:[{id:'fixture-page',blocks:[
  {t:'text',lines:[{id:'fixture-line-a',tx:'[TECHNICAL FIXTURE] A 😀',breakBefore:false}]},
  {t:'text',lines:[{id:'fixture-line-b',tx:'[TECHNICAL FIXTURE] B',breakBefore:true}]}
]}]};
const selector={pieceId:'fixture-piece',versionId:'fixture-version',lineId:'fixture-line-b'};
test('catalog uses v2, preserves v1 history, and requires an explicit legacy rebind',()=>{
  const catalog=buildSourceCatalog(site,review),version=catalog.pieces[0].versions[0];
  assert.equal(version.fingerprint,vectors[0].v2);
  assert.equal(version.sourceFingerprint,vectors[0].v2);
  assert.equal(version.legacyFingerprint,vectors[0].v1);
  const current=createAnchor(catalog,selector),old=structuredClone(current);
  delete old.fingerprintVersion;
  old.versionFingerprint=version.legacyFingerprint;
  const note=createRevision({family:'note',recordId:'fixture-note',revisionId:'fixture-revision',
    author:{id:'fixture',credit:'Technical fixture',provenance:'technical-fixture',sourceIds:['test']},
    anchor:old,kind:'footnote',text:'[TECHNICAL FIXTURE]',poemDate:{certainty:'unknown',value:null},
    noteDate:'2026-11-06',fixture:true},{at:'2026-11-06T00:00:00.000Z'});
  assert.equal(validateRevision(note).valid,true);
  assert.ok(validateAnchor(catalog,old).reasons.includes('legacy-fingerprint-rebind-required'));
  assert.equal(validateAnchor(catalog,current).valid,true);
  assert.equal(note.anchor.versionFingerprint,version.legacyFingerprint);
});
test('only changing a stanza boundary invalidates a current anchor',()=>{
  const catalog=buildSourceCatalog(site,review),anchor=createAnchor(catalog,selector);
  const changed=structuredClone(review);changed.pages[0].blocks[1].lines[0].breakBefore=false;
  assert.ok(validateAnchor(buildSourceCatalog(site,changed),anchor).reasons.includes('source-version-changed'));
});
test('accepted overlays preserve raw text and a stale original cannot pass by matching corrected text',()=>{
  const embedded=structuredClone(review),line=embedded.pages[0].blocks[0].lines[0];
  embedded.acceptedReviews={[line.id]:{original:line.tx,status:'corrected',text:'[TECHNICAL FIXTURE] accepted'}};
  const catalog=buildSourceCatalog(site,embedded);
  assert.equal(catalog.pieces[0].versions[0].lines[0].text,'[TECHNICAL FIXTURE] accepted');
  assert.equal(line.tx,review.pages[0].blocks[0].lines[0].tx);
  embedded.acceptedReviews[line.id]={original:'[TECHNICAL FIXTURE] stale',status:'corrected',text:line.tx};
  assert.ok(buildSourceCatalog(site,embedded).pieces[0].versions[0].issues.includes('stale-review:'+line.id));
});
