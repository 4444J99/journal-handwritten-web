import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {
  buildSourceCatalog, createAnchor, validateAnchor, createRevision,
  validateRevision, assertRevision, transitionRevision, heads, projectRecords,
  projectPreview, exportEnvelope, restoreEnvelope, contentDigest, sha256,
  PARTICIPATION_DEFAULT
} from '../studio/notes-model.mjs';

// All authored bodies/identities below are explicit synthetic technical fixtures.
// The compact source is independent of the author's poetry and is never emitted
// to site/. The real-repository check below only reads existing source records.
const copy = value => structuredClone(value);
const AT = '2026-11-06T01:00:00.000Z';
const source = {
  provenance:{kind:'technical-fixture',source:'tests/test_notes_model.mjs'},
  pieces:[{id:'p001',V:[
    {id:'p001-diary1-0',P:[['diary1',[0,1]]],d:'2000-01-01'},
    {id:'p001-diary2-0',P:[['diary2',[0]]],d:null}
  ]},{id:'p002',V:[{id:'p002-diary3-0',P:[['diary3',[0]]],d:null}]}]
};
const review = {
  // Deliberately opposite order: stack position must never select a version ID.
  items:[{id:'p001',versions:[{page:'diary2',blocks:[0]},{page:'diary1',blocks:[0,1]}]}],
  pages:[
    {id:'diary1',w:100,h:200,blocks:[
      {t:'text',lines:[{id:'diary1-0-0',tx:'[TECHNICAL FIXTURE] 😀 repeat repeat',box:[0,0,10,10]},{id:'diary1-0-1',tx:'[TECHNICAL FIXTURE] second source line',box:[0,20,10,10]}]},
      {t:'quotation',lines:[{id:'diary1-1-0',tx:'[TECHNICAL FIXTURE] immutable quotation block',box:[0,40,10,10]}]}
    ]},
    {id:'diary2',blocks:[{t:'text',lines:[{id:'diary2-0-0',tx:'[TECHNICAL FIXTURE] other version'}]}]},
    {id:'diary3',blocks:[{t:'text',lines:[{id:'diary3-0-0',tx:'[TECHNICAL FIXTURE] other piece'}]}]}
  ]
};
const catalog = buildSourceCatalog(source,review);
const selector = {pieceId:'p001',versionId:'p001-diary1-0',lineId:'diary1-0-0'};
const anchor = createAnchor(catalog,selector);
const versions = [{pieceId:selector.pieceId,versionId:selector.versionId}];
let sequence=0;
function note(changes={},previous=null) {
  const id='fixture-'+(++sequence);
  return createRevision({
    family:'note',recordId:previous?.recordId || id,revisionId:'rev-'+id,
    author:{id:'private-fixture-identity',credit:'Technical fixture author',provenance:'technical-fixture',sourceIds:['tests/test_notes_model.mjs']},
    poemDate:{certainty:'unknown',value:null},noteDate:'2026-11-05',anchor,
    kind:'footnote',text:'[TECHNICAL FIXTURE — not author text] Note placement test.',
    fixture:true,...changes
  },{previous,at:AT});
}
function transition(doc,action) {
  return transitionRevision(doc,action,{actor:'fixture-reviewer',at:AT,revisionId:'event-'+(++sequence)});
}
function cleared(doc) {
  const accepted=transition(doc,'accept'),clear=transition(accepted,'clear');
  return [doc,accepted,clear];
}
function preview(docs,options={}) { return projectPreview(docs,catalog,{versions,allowFixtures:true,...options}); }

test('SHA-256 agrees with the runtime for Unicode and multi-block snapshots', () => {
  for (const value of ['', 'abc', '😀'.repeat(1000), 'a'.repeat(64)]) {
    assert.equal(sha256(value),'sha256:'+createHash('sha256').update(value).digest('hex'));
  }
});

test('legacy source records without notes retain exact IDs and remain unchanged', () => {
  const old=copy(source),before=JSON.stringify(old);
  const built=buildSourceCatalog(old,review);
  assert.equal(JSON.stringify(old),before);
  assert.equal(built.pieces[0].versions[0].versionId,'p001-diary1-0');
  assert.equal(built.pieces[0].versions[0].lines[0].lineId,'diary1-0-0');
  assert.deepEqual(exportEnvelope({},AT),{format:'versforms-notes-backup',version:1,exportedAt:AT,notes:[],contributions:[]});
  assert.deepEqual(projectRecords([],built,{mode:'public',versions}).records,[]);
});

test('current repository IDs resolve by exact membership, independent of review stack order', () => {
  const s=JSON.parse(readFileSync(new URL('../studio/data/notes-versions.json',import.meta.url)));
  const r=JSON.parse(readFileSync(new URL('../studio/data/review.json',import.meta.url)));
  const before=JSON.stringify([s,r]),built=buildSourceCatalog(s,r);
  assert.equal(JSON.stringify([s,r]),before);
  assert.ok(built.pieces.length>0);
  assert.deepEqual(built.pieces.flatMap(p=>p.versions).flatMap(v=>v.issues),[]);
  const current=createAnchor(built,{pieceId:'p002',versionId:'p002-diary2-2',lineId:'diary2-2-0'});
  assert.equal(current.lineId,'diary2-2-0');
  assert.throws(()=>createAnchor(built,{pieceId:'p002',versionId:'p002-diary2-0',lineId:'diary2-2-0'}),/not a member/);
});

test('anchors survive geometry changes but invalidate for source text or membership changes', () => {
  const moved=copy(review); moved.pages[0].w=999; moved.pages[0].blocks[0].lines[0].box=[200,400,20,20];
  assert.equal(validateAnchor(buildSourceCatalog(source,moved),anchor).valid,true);
  const edited=copy(review); edited.pages[0].blocks[0].lines[0].tx+=' [changed]';
  const invalid=validateAnchor(buildSourceCatalog(source,edited),anchor);
  assert.equal(invalid.valid,false);
  assert.ok(invalid.reasons.includes('source-line-changed'));
  assert.equal(anchor.lineText,review.pages[0].blocks[0].lines[0].tx);
  const membership=copy(source); membership.pieces[0].V[0].P[0][1]=[1];
  const removed=validateAnchor(buildSourceCatalog(membership,review),anchor);
  assert.ok(removed.reasons.includes('source-membership-changed'));
  assert.ok(removed.reasons.includes('line-no-longer-in-version'));
});

test('effective author corrections invalidate old anchors; stale corrections block new anchors', () => {
  const id='diary1-0-0', original=anchor.lineText;
  const corrections={[id]:{status:'corrected',original,text:original+' [corrected]',at:AT}};
  const changed=buildSourceCatalog(source,review,{reviews:corrections});
  assert.equal(validateAnchor(changed,anchor).valid,false);
  const correctedAnchor=createAnchor(changed,selector);
  assert.equal(correctedAnchor.lineText,corrections[id].text);
  const changedAgain=copy(corrections); changedAgain[id].text+=' [again]';
  assert.equal(validateAnchor(buildSourceCatalog(source,review,{reviews:changedAgain}),correctedAnchor).valid,false);
  const stale={[id]:{status:'corrected',original:'unrelated original',text:'unrelated correction'}};
  assert.throws(()=>createAnchor(buildSourceCatalog(source,review,{reviews:stale}),selector),/stale-review/);
  stale[id].text=original;
  assert.throws(()=>createAnchor(buildSourceCatalog(source,review,{reviews:stale}),selector),/stale-review/);
  assert.equal(correctedAnchor.fingerprintVersion,2);
  const quotation={'diary1-1-0':{status:'corrected',original:'ignored',text:'ignored'}};
  assert.equal(buildSourceCatalog(source,review,{reviews:quotation}).fingerprint,catalog.fingerprint);
});

test('wrong versions, foreign lines and ambiguous quotes are blocked without retargeting', () => {
  assert.throws(()=>createAnchor(catalog,{...selector,versionId:'p001-diary2-0'}),/not a member/);
  assert.throws(()=>createAnchor(catalog,{...selector,lineId:'diary3-0-0'}),/not a member/);
  assert.throws(()=>createAnchor(catalog,{...selector,pieceId:'p002'}),/exact piece\/version/);
  assert.throws(()=>createAnchor(catalog,{...selector,word:{quote:'repeat'}}),/Ambiguous/);
  const points=Array.from(anchor.lineText),start=points.join('').lastIndexOf('repeat')-1; // one surrogate pair precedes the quote
  const chosen=createAnchor(catalog,{...selector,word:{quote:'repeat',start,end:start+6}});
  assert.equal(chosen.word.start,start);
  assert.equal(validateAnchor(catalog,chosen).valid,true);
  const emoji=createAnchor(catalog,{...selector,word:{quote:'😀'}});
  assert.equal(emoji.word.end-emoji.word.start,1);
  assert.throws(()=>createAnchor(catalog,{...selector,word:{quote:'repeat',start:start+1,end:start+7}}),/Invalid codepoint/);
  assert.throws(()=>createAnchor(catalog,{pieceId:'p001',versionId:'p001-diary1-0',word:{quote:'repeat'}}),/exact source line/);
});

test('creation is private, edits are append-only held drafts, and approval events retain original dates', () => {
  const draft=note();
  assert.equal(draft.visibility,'private'); assert.equal(draft.editorial.status,'draft'); assert.equal(draft.release.status,'held');
  const publicCandidate=note({visibility:'public-candidate'});
  const history=cleared(publicCandidate),[original,accepted,clear]=history;
  assert.equal(clear.editorial.approval.revisionId,accepted.revisionId);
  assert.equal(clear.release.clearance.revisionId,clear.revisionId);
  assert.equal(clear.noteDate,original.noteDate);
  const edit=note({text:'[TECHNICAL FIXTURE] Revised technical body.'},clear);
  assert.equal(edit.recordId,clear.recordId);
  assert.deepEqual(edit.parents,[clear.revisionId]);
  assert.equal(edit.editorial.status,'draft'); assert.equal(edit.editorial.approval,null);
  assert.deepEqual(edit.release,{status:'held',clearance:null,publication:null,revocation:null});
  assert.equal(clear.release.status,'cleared');
  assert.equal(preview([...history,edit]).records.length,0);
  assert.throws(()=>transition(clear,'release'),/separate T03/);
});

test('private dossiers, unreviewed content, uncleared content and invalidated sources never project', () => {
  assert.equal(preview([note()]).records.length,0);
  const draft=note({visibility:'public-candidate'}),accepted=transition(draft,'accept');
  assert.equal(preview([draft,accepted]).records.length,0);
  const dossier=note({kind:'research-dossier',visibility:'public-candidate'}),reviewed=transition(dossier,'accept');
  assert.throws(()=>transition(reviewed,'clear'),/dossiers stay private/);
  const history=cleared(draft);
  assert.equal(preview(history).records.length,1);
  assert.equal(projectPreview(history,catalog,{versions}).records.length,0);
  const changed=copy(review); changed.pages[0].blocks[0].lines[1].tx+=' [changed sibling line]';
  assert.equal(projectPreview(history,buildSourceCatalog(source,changed),{versions,allowFixtures:true}).records.length,0);
  const held=transition(history.at(-1),'hold'); assert.equal(preview([...history,held]).records.length,0);
  const revoked=transition(history.at(-1),'revoke'); assert.equal(preview([...history,revoked]).records.length,0);
});

test('projection whitelists display fields and excludes identity, permission evidence and history', () => {
  const history=cleared(note({visibility:'public-candidate',citations:[{label:'Technical fixture reference',url:'https://example.invalid/fixture',locator:'§1'}]}));
  const result=preview(history).records[0];
  assert.deepEqual(Object.keys(result).sort(),['id','revisionId','family','kind','pieceId','versionId','lineId','word','text','citations','credit','poemDate','noteDate','fixture'].sort());
  assert.equal(result.credit,'Technical fixture author');
  const serialized=JSON.stringify(result);
  for (const secret of ['private-fixture-identity','fixture-reviewer','sourceProvenance','versionFingerprint','parents','editorial','release']) assert.ok(!serialized.includes(secret),secret);
  assert.equal(projectRecords(history,catalog,{mode:'public',versions,allowFixtures:true}).records.length,0);
  const privateRecord=note(),withheld=projectRecords([privateRecord,...history],catalog,{mode:'public',versions});
  assert.deepEqual(withheld,{records:[],excluded:[]});
  assert.ok(!JSON.stringify(withheld).includes(privateRecord.recordId));
});

test('fixture provenance cannot be removed through edits or imported descendants', () => {
  const fixture=note();
  assert.throws(()=>note({fixture:false,author:{id:'test',credit:'test',provenance:'author-supplied'}},fixture),/cannot be removed/);
  const forged=copy(fixture); forged.fixture=false; forged.author.provenance='author-supplied'; forged.revisionId='forged-child'; forged.parents=[fixture.revisionId];
  assert.equal(validateRevision(forged).valid,true); // graph, not shape, detects the provenance loss
  assert.ok(heads([fixture,forged])[0].errors.includes('technical-fixture provenance was removed'));
  assert.throws(()=>restoreEnvelope({format:'versforms-notes-backup',version:1,notes:[fixture,forged],contributions:[]}),/provenance was removed/);
});

test('forks are retained through backup/restore and block output until an explicit merge', () => {
  const draft=note({visibility:'public-candidate'}),history=cleared(draft),base=history.at(-1);
  const left=note({text:'[TECHNICAL FIXTURE] Left edit.'},base),right=note({text:'[TECHNICAL FIXTURE] Right edit.'},base);
  const all=[...history,left,right],group=heads(all)[0];
  assert.equal(group.conflicted,true); assert.equal(group.heads.length,2);
  assert.equal(preview(all).records.length,0);
  const restored=restoreEnvelope(exportEnvelope({notes:all,contributions:[]},AT));
  assert.equal(heads(restored)[0].heads.length,2);
  const merged=note({parents:[left.revisionId,right.revisionId],text:'[TECHNICAL FIXTURE] Explicit reconciled revision.'},left);
  const resolved=heads([...all,merged])[0]; assert.equal(resolved.conflicted,false);
  assert.equal(merged.editorial.status,'draft');
});

test('export/restore preserves dates, sources, authorship, approval references and every revision', () => {
  const initial=note({visibility:'public-candidate',poemDate:{certainty:'approximate',value:'2000'},noteDate:'2026-10-26'});
  const history=cleared(initial),edited=note({text:'[TECHNICAL FIXTURE] New note revision.',noteDate:'2026-10-26'},history.at(-1));
  const snapshot={notes:[...history,edited],contributions:[]};
  const envelope=exportEnvelope(snapshot,AT),transport=JSON.parse(JSON.stringify(envelope));
  assert.deepEqual(restoreEnvelope(transport),snapshot);
  assert.deepEqual(restoreEnvelope(transport,snapshot),snapshot);
  assert.equal(envelope.notes[0].noteDate,'2026-10-26');
  assert.equal(envelope.notes[0].poemDate.value,'2000');
  assert.equal(envelope.notes[0].anchor.versionId,'p001-diary1-0');
  assert.notEqual(restoreEnvelope(transport).notes[0],initial);
  const collision=copy(envelope); collision.notes[0].text+=' [collision]';
  assert.throws(()=>restoreEnvelope(collision,snapshot),/collision/);
  assert.throws(()=>restoreEnvelope({format:'versforms-notes-backup',version:1,notes:[edited],contributions:[]}),/missing or foreign parent/);
  assert.deepEqual(snapshot.notes.map(n=>n.revisionId),[...history,edited].map(n=>n.revisionId));
});

test('foreign parents, cycles and approval transfers across histories fail closed', () => {
  const a=note(),b=note();
  const foreign=note({parents:[b.revisionId]});
  assert.ok(heads([a,b,foreign]).find(g=>g.recordId===foreign.recordId).errors.some(e=>e.includes('foreign parent')));
  const cyclicA=copy(a),cyclicB=copy(a); cyclicB.revisionId='cycle-b'; cyclicA.parents=['cycle-b']; cyclicB.parents=[a.revisionId];
  assert.ok(heads([cyclicA,cyclicB])[0].errors.includes('revision cycle'));
  const history=cleared(note({visibility:'public-candidate'}));
  const transferred=copy(history.at(-1)); transferred.editorial.approval.revisionId=b.revisionId;
  assert.equal(validateRevision(transferred).valid,true);
  assert.equal(preview([...history.slice(0,-1),transferred,b]).records.length,0);
});

test('contributions require explicit web permission and credit and never change poem count', () => {
  const original=JSON.stringify(source),before=source.pieces.length;
  const contribution=note({family:'contribution',type:'hand-copy',kind:undefined,visibility:'public-candidate',
    permission:{status:'pending',scopes:[],evidence:'',recordedBy:null,recordedAt:null}});
  assert.deepEqual(contribution.participation,PARTICIPATION_DEFAULT);
  assert.equal(contribution.participation.countsTowardsAuthor100,false);
  assert.equal(contribution.participation.provenance.authorAdopted,false);
  const accepted=transition(contribution,'accept');
  assert.throws(()=>transition(accepted,'clear'),/web permission/);
  const permitted=note({family:'contribution',type:'hand-copy',kind:undefined,visibility:'public-candidate',
    permission:{status:'granted',scopes:['web'],evidence:'[PRIVATE TECHNICAL FIXTURE] Test consent receipt',recordedBy:'private-permission-actor',recordedAt:AT}},contribution);
  const accepted2=transition(permitted,'accept'),clear=transition(accepted2,'clear');
  const projected=preview([contribution,permitted,accepted2,clear]).records[0];
  assert.equal(projected.family,'contribution'); assert.equal(projected.kind,'hand-copy');
  assert.ok(!JSON.stringify(projected).includes('Test consent receipt'));
  assert.ok(!JSON.stringify(projected).includes('private-permission-actor'));
  const noCredit=note({visibility:'public-candidate',author:{id:'private-fixture',credit:'',provenance:'technical-fixture'}});
  assert.throws(()=>transition(transition(noCredit,'accept'),'clear'),/explicit credit/);
  assert.equal(source.pieces.length,before); assert.equal(JSON.stringify(source),original);
});

test('safe structural validation rejects bad IDs, dates, scripts, unknown fields and changed approved payloads', () => {
  const valid=note();
  assert.equal(validateRevision(valid).valid,true); assertRevision('notes',valid);
  assert.throws(()=>assertRevision('contributions',valid),/family/);
  for (const modify of [
    d=>{d.revisionId='../escape';}, d=>{d.noteDate='2026-02-31';},
    d=>{d.poemDate={certainty:'recorded',value:'2026-13'};},
    d=>{d.citations=[{label:'fixture',url:'javascript:alert(1)'}];},
    d=>{d.unexpected='private metadata';},d=>{d.parents=[d.revisionId];}
  ]) { const invalid=copy(valid); modify(invalid); assert.equal(validateRevision(invalid).valid,false); }
  const unsafe=JSON.parse(JSON.stringify(valid)); unsafe.author=JSON.parse('{"__proto__":{"polluted":true},"id":"x","credit":"x","provenance":"technical-fixture","sourceIds":[]}');
  assert.equal(validateRevision(unsafe).valid,false); assert.equal({}.polluted,undefined);
  const approved=copy(cleared(note({visibility:'public-candidate'})).at(-1)); approved.text+=' tampered';
  assert.equal(validateRevision(approved).valid,false);
  assert.ok(validateRevision(approved).errors.some(e=>e.includes('does not cover')));
});

test('externally labelled released records still need the exact output contract', () => {
  // Synthetic external-contract simulation: no real release record is created.
  const seed=copy(note({visibility:'public-candidate'}));
  seed.fixture=false; seed.author.provenance='author-supplied'; seed.author.id='synthetic-contract-actor';
  const history=cleared(seed),clear=history.at(-1);
  assert.equal(projectRecords(history,catalog,{mode:'public',versions}).records.length,0);
  const released=copy(clear); released.revisionId='external-release-fixture'; released.parents=[clear.revisionId];
  released.release.status='released';
  released.release.publication={revisionId:released.revisionId,by:'synthetic-contract-actor',at:AT,contentDigest:contentDigest(released),evidence:'synthetic-external-clearance-reference'};
  const all=[...history,released];
  assert.equal(projectRecords(all,catalog,{mode:'public'}).records.length,0);
  assert.equal(projectRecords(all,catalog,{mode:'public',versions:[{pieceId:'p001',versionId:'p001-diary2-0'}]}).records.length,0);
  assert.equal(projectRecords(all,catalog,{mode:'public',versions}).records.length,0);
  // A free-form external reference cannot replace T03's bound manifest/event.
  assert.equal(source.pieces.length,2);
});
