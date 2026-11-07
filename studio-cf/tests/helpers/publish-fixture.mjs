export function fixture() {
 const pages = ['pg1','pg2','pg3'].map((id,i)=>({id,iw:100,ih:100,W:100,H:100,c:[0,0,1,1],a:[0,i*16,0,16,16],B:[{t:0,L:['machine-'+id],g:[i,0,0],v:0}],x:[[0,0,0,0,1,1]],u:['private-note'],sp:{k:id,cb:[0,0,1,1]}}));
 const pieces=pages.map((p,i)=>({id:'p00'+(i+1),V:[{id:'v'+i,P:[[p.id,[0]]]}],st:[0],top:0}));
 const source={j:{v:2,pages,pieces,groups:[pages.map(p=>p.id)],atlas:[[48,16]],prov:{repo:'private',commit:'private',path:'private',tdate:'2026-01-01',verified:false}},review:{pages:pages.map(p=>({id:p.id,blocks:[{t:'text',lines:[{id:p.id+'-0-0',tx:p.B[0].L[0]}]}]})),items:pieces.map((p,i)=>({id:p.id,versions:[{page:pages[i].id,blocks:[0]}]}))},twins:{},tiles:Object.fromEntries(pages.map(p=>[p.id,{size:[16,16],files:{t:'tiles/t-'+p.id+'.jpg',k:'tiles/k-'+p.id+'.jpg'}}])),assets:{},metadata:{PAL:[],HF:[]}};
 for(const p of pages)for(const k of ['p','i','m']) source.assets['img/'+k+'/'+p.id+'.jpg']={sha256:'a'.repeat(64),size:4,contentType:'image/jpeg'};
 for(const p of pages)for(const k of ['t','k'])source.assets['tiles/'+k+'-'+p.id+'.jpg']={sha256:'b'.repeat(64),size:4,contentType:'image/jpeg'};
 const db={release:Object.fromEntries(pieces.map(p=>[p.id,{pool:'series'}])),reviews:Object.fromEntries(pages.map(p=>[p.id+'-0-0',{status:'confirmed',original:p.B[0].L[0]}])),batches:{b:{items:pieces.map(p=>p.id),status:'filed'}},decisions:{},versions:{},rconfig:{}};
 const shell='<!doctype html><html><head><title>versforms</title><meta name="robots" content="noindex"></head><body><script>const PAL = []; const HF = [];</script></body></html>';
 return {source,db,shell};
}
