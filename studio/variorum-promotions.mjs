// Supplemental identities created explicitly in Sort. No canonical item is
// rewritten and no release decision is inferred from the originating poem.
import {sourceFingerprint} from './source-fingerprint.mjs';
const values=documents=>documents instanceof Map?[...documents.values()]:Object.values(documents||{});
export function promotionInventory(documents){
 const docs=values(documents),byRevision=new Map(docs.map(d=>[d.revisionId,d]));
 return docs.filter(d=>d.family==='promotion').map(p=>{
  const origin=byRevision.get(p.originComposite?.revisionId);
  if(!origin||origin.family!=='composite'||origin.recordId!==p.originComposite.recordId)throw new Error('promotion_source_missing');
  return {key:p.pieceId,pieceId:p.pieceId,title:origin.title||p.pieceId,meta:'Composite · '+origin.versionId,verified:origin.verified===true,prog:origin.verified?'verified':'not verified',seq:Number(p.pieceId.slice(1))||1e6,promotion:p,origin};
 }).sort((a,b)=>a.seq-b.seq);
}
export function projectPromotionsIntoCatalog(catalog,documents){
 const result=structuredClone(catalog);
 for(const c of promotionInventory(documents)){
  if(result.pieces.some(p=>p.pieceId===c.pieceId))throw new Error('promotion_piece_collision');
  const versionId=c.pieceId+'-'+c.origin.versionId;
  const lines=structuredClone(c.origin.lines||[]).map((l,i)=>({...l,lineId:versionId+'-L'+(i+1),verified:c.origin.verified===true}));
  const snapshot={pieceId:c.pieceId,versionId,members:[],lines};
  result.pieces.push({pieceId:c.pieceId,originComposite:structuredClone(c.promotion.originComposite),versions:[{...snapshot,kind:'composite',render:c.origin.render,photo:c.origin.photo||null,text:c.origin.text,available:lines.length>0,sourceFingerprint:sourceFingerprint(snapshot),issues:[],exposures:structuredClone(c.origin.exposures||[])}]});
 }
 return result;
}
export function installPromotionInventory(db,onChange,onError=()=>{}){
 return db.collection('composites').onSnapshot(snap=>{try{onChange(promotionInventory(Object.fromEntries(snap.docs.filter(d=>d.exists).map(d=>[d.id,d.data()]))));}catch(e){onError(e);}},onError);
}
