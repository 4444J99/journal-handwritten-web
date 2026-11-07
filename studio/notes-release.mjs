// Bind an immutable notes revision to supplied exact-output clearance and an
// observed publication event. This records history; it never posts anything.
import { assertRevision, contentDigest, projectPreview } from './notes-model.mjs';
import { evaluateRelease, contractDigest } from './release-contract.mjs';

export function noteReleaseComponent(doc, manifest, currentCatalog) {
  const source = currentCatalog.pieces.find(p => p.pieceId === doc.anchor.pieceId)?.versions.find(v => v.versionId === doc.anchor.versionId);
  const previous = manifest?.components?.find(c => c.kind === doc.family && c.id === doc.recordId);
  if (!source || !previous) return null;
  return {...previous,kind:doc.family,id:doc.recordId,revisionDigest:contentDigest(doc),
    pieceId:doc.anchor.pieceId,versionId:doc.anchor.versionId,sourceFingerprint:source.fingerprint,fixture:doc.fixture};
}

export function recordNotePublication(snapshot,catalog,recordId,{manifest,clearance,event,revisionId,at,by} = {}) {
  const documents = [...(snapshot.notes || []),...(snapshot.contributions || [])];
  if (documents.some(d => d.revisionId === revisionId)) throw new Error('Publication revision ID already exists.');
  const candidates = projectPreview(documents,catalog).records.filter(r => r.id === recordId);
  if (candidates.length !== 1) throw new Error('One unconflicted, accepted, cleared source revision is required.');
  const previous = documents.find(d => d.revisionId === candidates[0].revisionId);
  if (previous.fixture) throw new Error('Technical fixtures cannot acquire a publication event.');
  if (previous.release.status !== 'cleared') throw new Error('Record must be cleared and not already released.');
  if (!event) throw new Error('An observed publication event is required.');
  if (!Array.isArray(manifest?.sources)) throw new Error('An exact-output manifest is required.');
  const currentSources = manifest.sources.map(s => {
    const v = catalog.pieces.find(p => p.pieceId === s.pieceId)?.versions.find(v => v.versionId === s.versionId);
    return {...s,sourceFingerprint:v?.fingerprint ?? null};
  });
  const component = noteReleaseComponent(previous,manifest,catalog);
  if (!component) throw new Error('The exact note component must be present in the output manifest.');
  const checked = evaluateRelease(manifest,clearance,{currentSources,component,event});
  if (!checked.eligible) throw new Error('Release evidence refused: '+checked.reasons.join(', '));
  if (by !== event.recordedBy || at !== event.at) throw new Error('Revision actor/date must match the observed event.');
  const doc = JSON.parse(JSON.stringify(previous));
  doc.revisionId=revisionId;doc.parents=[previous.revisionId];doc.editedAt=at;doc.editedBy=by;doc.changeReason='release-event';
  doc.release.status='released';
  doc.release.publication={revisionId,by,at,contentDigest:contentDigest(doc),evidence:'release-event:'+contractDigest(event)};
  assertRevision(doc.family === 'note' ? 'notes' : 'contributions',doc);
  return Object.freeze({revision:doc,event:JSON.parse(JSON.stringify(event)),manifestDigest:manifest.manifestDigest});
}
