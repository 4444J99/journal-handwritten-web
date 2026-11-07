import {buildSourceCatalog} from './notes-model.mjs';
import {sourceFingerprint, stableJSON, sha256 as digest} from './source-fingerprint.mjs';
const clone=x=>structuredClone(x);
const requireValue=(ok,message)=>{if(!ok)throw new Error(message);};
const ID=/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/;
export const CASE_MODES=Object.freeze(['asis','lower','upper','sentence']);
export const rowKey=({partId,occurrence})=>`${partId}/${occurrence}`;
export function transformCase(text,mode='asis') {
 requireValue(CASE_MODES.includes(mode),'invalid_case');
 if(mode==='lower')return text.toLowerCase();if(mode==='upper')return text.toUpperCase();
 if(mode==='sentence')return text.split('\n').map(line=>line.replace(/^(\s*)(\S)(.*)$/u,(_,pad,first,rest)=>pad+first.toUpperCase()+rest.toLowerCase())).join('\n');
 return text;
}
export function buildVariorumCatalog({versionMap,review,reviews={},supplement={schemaVersion:1,sources:[],parts:[],composites:[]}}) {
 requireValue(supplement?.schemaVersion===1 && Array.isArray(supplement.sources),'invalid_supplement');
 const base=buildSourceCatalog(versionMap,review,{reviews});
 const pieces=clone(base.pieces);
 for(const p of pieces)for(const v of p.versions){v.kind='journal';const metadata=versionMap.pieces.find(p=>p.id===v.pieceId)?.V.find(x=>x.id===v.versionId);v.exposures=clone(metadata?.exposures||metadata?.exposure||[]);v.available=!v.issues.length;v.lines=v.lines.map(l=>({...l,verified:(()=>{const r=reviews[l.lineId]||review.acceptedReviews?.[l.lineId];return ['confirmed','corrected'].includes(r?.status)&&r.original===l.originalText;})()}));}
 const seen=new Set(pieces.flatMap(p=>p.versions.map(v=>v.versionId)));
 for(const src of supplement.sources){
  requireValue(ID.test(src.versionId)&&ID.test(src.pieceId)&&!seen.has(src.versionId),'duplicate_or_invalid_source');
  requireValue(['lyric','notebook'].includes(src.kind),'invalid_source_kind');seen.add(src.versionId);
  let p=pieces.find(p=>p.pieceId===src.pieceId);requireValue(p,'unknown_source_piece');
  const lines=clone(src.lines||[]),ids=new Set();
  for(const l of lines){requireValue(ID.test(l.lineId)&&!ids.has(l.lineId)&&typeof l.text==='string'&&typeof l.breakBefore==='boolean','invalid_source_line');ids.add(l.lineId);}
  for(const l of lines){const r=reviews[l.lineId]||review.acceptedReviews?.[l.lineId];l.originalText=l.originalText??l.text;l.blockType=l.blockType||'text';l.verified=['confirmed','corrected'].includes(r?.status)&&r.original===l.originalText;if(r?.status==='corrected'&&l.verified){requireValue(typeof r.text==='string','invalid_review');l.text=r.text;}}
  const snapshot={pieceId:src.pieceId,versionId:src.versionId,members:[],lines};
  p.versions.push({...clone(src),...snapshot,available:src.status!=='text-not-supplied'&&lines.length>0,sourceFingerprint:sourceFingerprint(snapshot),issues:lines.length?[]:['text-not-supplied']});
 }
 return {schemaVersion:1,pieces,fingerprint:digest(stableJSON(pieces.map(p=>({pieceId:p.pieceId,versions:p.versions.map(v=>({versionId:v.versionId,sourceFingerprint:v.sourceFingerprint}))}))))};
}
export function findVersion(catalog,pieceId,versionId){return catalog.pieces.find(p=>p.pieceId===pieceId)?.versions.find(v=>v.versionId===versionId);}
export function provisionalParts(catalog,pieceId){
 const p=catalog.pieces.find(p=>p.pieceId===pieceId);requireValue(p,'unknown_piece');
 const parts=[],maps={};let count=0;
 for(const v of p.versions){let groups=[];for(const l of v.lines){if(!groups.length||l.breakBefore)groups.push([]);groups.at(-1).push(l.lineId);}count=Math.max(count,groups.length);maps[v.versionId]={segments:Object.fromEntries(groups.map((lines,i)=>[`part-${i+1}`,[{occurrence:1,lines,accepted:false}]])),version_part_order:groups.map((_,i)=>({partId:`part-${i+1}`,occurrence:1}))};}
 for(let i=1;i<=count;i++)parts.push({id:`part-${i}`,name:null});
 return {pieceId,parts,canonicalOrder:parts.map(p=>p.id),linkedPieces:[],maps,provisional:true};
}
export function validateParts(catalog,record){
 requireValue(record&&ID.test(record.pieceId)&&catalog.pieces.some(p=>p.pieceId===record.pieceId),'unknown_piece');
 requireValue(Array.isArray(record.parts)&&Array.isArray(record.canonicalOrder)&&Array.isArray(record.linkedPieces),'invalid_parts');
 const ids=new Set();for(const p of record.parts){requireValue(ID.test(p.id)&&!ids.has(p.id)&&(p.name===null||typeof p.name==='string'),'invalid_part');ids.add(p.id);}
 requireValue(record.canonicalOrder.length===ids.size&&new Set(record.canonicalOrder).size===ids.size&&record.canonicalOrder.every(id=>ids.has(id)),'invalid_canonical_order');
 requireValue(record.linkedPieces.every(id=>id!==record.pieceId&&catalog.pieces.some(p=>p.pieceId===id))&&new Set(record.linkedPieces).size===record.linkedPieces.length,'invalid_linked_pieces');
 for(const [versionId,map] of Object.entries(record.maps||{})){
  const v=catalog.pieces.filter(p=>p.pieceId===record.pieceId||record.linkedPieces.includes(p.pieceId)).flatMap(p=>p.versions).find(v=>v.versionId===versionId);requireValue(v,'invalid_version_membership');
  const used=new Set(),keys=new Set();
  for(const [partId,occurrences] of Object.entries(map.segments||{})){
   requireValue(ids.has(partId)&&Array.isArray(occurrences),'invalid_segment');
   for(const o of occurrences){const key=rowKey({partId,occurrence:o.occurrence});requireValue(Number.isSafeInteger(o.occurrence)&&o.occurrence>0&&!keys.has(key)&&Array.isArray(o.lines)&&o.lines.length>0,'invalid_occurrence');keys.add(key);
    let previous=-1;for(const lid of o.lines){const index=v.lines.findIndex(l=>l.lineId===lid);requireValue(index>=0&&!used.has(lid)&&(previous<0||index===previous+1),'missing_duplicate_or_noncontiguous_line');used.add(lid);previous=index;}
    requireValue(typeof o.accepted==='boolean','missing_acceptance');
   }
  }
  requireValue(Array.isArray(map.version_part_order)&&map.version_part_order.length===keys.size&&new Set(map.version_part_order.map(rowKey)).size===keys.size&&map.version_part_order.every(k=>keys.has(rowKey(k))),'invalid_version_part_order');
 }
 return record;
}
export function materializeComposite(catalog,partsRevision,recipe,caseMode='asis'){
 validateParts(catalog,partsRevision);requireValue(Array.isArray(recipe)&&recipe.length,'empty_recipe');
 const snapshots=[],lines=[],exposures=[],unverified=[],keys=new Set();
 for(const [stepIndex,s] of recipe.entries()){
  const key=rowKey(s);requireValue(!keys.has(key),'duplicate_recipe_occurrence');keys.add(key);
  const v=catalog.pieces.flatMap(p=>p.versions).find(v=>v.versionId===s.from);requireValue(v?.available&&v.kind!=='composite','source_unavailable');
  const o=partsRevision.maps[s.from]?.segments?.[s.partId]?.find(o=>o.occurrence===s.occurrence);requireValue(o?.accepted,'unaccepted_or_missing_occurrence');
  const selected=o.lines.map(id=>{const l=v.lines.find(l=>l.lineId===id);requireValue(l,'missing_source_line');return clone(l);});
  snapshots.push({pieceId:v.pieceId,versionId:v.versionId,sourceFingerprint:v.sourceFingerprint,lines:selected});
  for(const [i,l]of selected.entries()){if(!l.verified)unverified.push(l.lineId);lines.push({lineId:`composite-${stepIndex}-${i}`,text:transformCase(l.text,caseMode),breakBefore:i===0&&stepIndex>0,sourceLineId:l.lineId,sourceVersionId:v.versionId,partId:s.partId,occurrence:s.occurrence});}
  for(const e of v.exposures||[])if(!exposures.some(x=>stableJSON(x)===stableJSON(e)))exposures.push(clone(e));
 }
 return {recipe:clone(recipe),caseMode,lines,text:lines.map(l=>(l.breakBefore?'\n':'')+l.text).join('\n'),sourceSnapshots:snapshots,sourceTranscriptSha:digest(stableJSON(snapshots)),verified:unverified.length===0,unverified,exposures,render:'typeset'};
}
export function pivotRows(record,versionId){
 const canonical=record.canonicalOrder.flatMap(partId=>{const values=[...new Set(Object.values(record.maps).flatMap(m=>(m.segments[partId]||[]).map(o=>o.occurrence)))].sort((a,b)=>a-b);return (values.length?values:[1]).map(occurrence=>({partId,occurrence}));});
 const first=record.maps[versionId]?.version_part_order||[],seen=new Set(first.map(rowKey));return [...first,...canonical.filter(k=>!seen.has(rowKey(k)))];
}
export function similaritySuggestions(catalog,record,versionId){
 const target=catalog.pieces.flatMap(p=>p.versions).find(v=>v.versionId===versionId);requireValue(target,'unknown_version');
 const words=s=>new Set(s.toLowerCase().match(/[\p{L}\p{N}]+/gu)||[]);
 return target.lines.map((line,index)=>{const a=words(line.text);const candidates=[];for(const [otherId,map]of Object.entries(record.maps)){if(otherId===versionId)continue;const other=catalog.pieces.flatMap(p=>p.versions).find(v=>v.versionId===otherId);for(const [partId,occurrences]of Object.entries(map.segments))for(const o of occurrences){const b=words(o.lines.map(id=>other.lines.find(l=>l.lineId===id)?.text||'').join(' '));const shared=[...a].filter(w=>b.has(w)).length;const textScore=a.size+b.size?2*shared/(a.size+b.size):0,sourceIndex=other.lines.findIndex(l=>l.lineId===o.lines[0]),positionScore=1-Math.abs(index/Math.max(1,target.lines.length-1)-sourceIndex/Math.max(1,other.lines.length-1));candidates.push({partId,occurrence:o.occurrence,textScore,positionScore,score:.9*textScore+.1*positionScore});}}candidates.sort((a,b)=>b.score-a.score||a.partId.localeCompare(b.partId));return {lineId:line.lineId,index,candidates,accepted:false};});
}
