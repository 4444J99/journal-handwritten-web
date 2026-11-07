import {createPublishClient} from './publish-client.mjs';

function el(tag,attrs={},...children) {
  const n=document.createElement(tag);
  for(const [k,v]of Object.entries(attrs)) {
    if(k.startsWith('on'))n.addEventListener(k.slice(2),v);
    else if(k==='class')n.className=v;
    else if(k in n)n[k]=v;
    else n.setAttribute(k,v);
  }
  n.append(...children.filter(v=>v!==null && v!==undefined));return n;
}
function modal(title) {
  if(!document.querySelector('link[data-publish-style]'))document.head.append(el('link',{rel:'stylesheet',href:'publish.css','data-publish-style':''}));
  const dialog=el('dialog',{class:'publish-dialog','aria-label':title});
  const close=el('button',{type:'button',class:'btn small',onclick:()=>dialog.close()},'Close');
  dialog.append(el('div',{class:'publish-heading'},el('h2',{},title),close));
  const body=el('div');dialog.append(body);document.body.append(dialog);
  dialog.addEventListener('close',()=>dialog.remove(),{once:true});dialog.showModal();
  return {dialog,body,close};
}
const failText=error=>el('p',{class:'err',role:'alert'},String(error.message || error));
const progressText=s=>`${s.cursor || 0}/${s.total || 0} files`;

export async function openPublisher({pieceId,canWrite=()=>true,hasPending=()=>false,onDone=()=>{},unpublish=false}={}) {
  const {dialog,body,close}=modal(unpublish?'Unpublish':'Publish');
  const api=createPublishClient();
  const target=el('select',{'aria-label':'Publish destination'},el('option',{value:'staging'},'Staging'),el('option',{value:'production'},'Production'));
  const status=el('p',{role:'status','aria-live':'polite'}),output=el('div');
  let candidate=null,busy=false,accepted=new Set(),force=false,history=null;
  const buildButton=el('button',{type:'button',class:'btn primary',onclick:build},unpublish?'Preview without this poem':'Build preview');
  body.append(el('p',{class:'note'},'Preview the exact snapshot, then confirm. Check staging before publishing to production.'),el('label',{},'Destination ',target),buildButton,status,output);
  function lock(value) {busy=value;target.disabled=value;buildButton.disabled=value;close.disabled=value;}
  dialog.addEventListener('cancel',e=>{if(busy)e.preventDefault();});
  target.addEventListener('change',()=>{candidate=null;accepted.clear();force=false;output.replaceChildren();status.textContent='Destination changed. Build a new preview.';});
  async function build() {
    if(busy)return;
    if(!canWrite()) {status.textContent='Owner access is required.';return;}
    if(hasPending()) {status.textContent='Wait for Studio edits to save before building a preview.';return;}
    candidate=null;output.replaceChildren();lock(true);status.textContent='Checking publication gates…';
    try {
      history=await api.history();
      const current=history.pointers[target.value]?.id;
      const snapshot=history.records.find(r=>r.id===current && Array.isArray(r.pieces));
      const pieces=[...new Set([...(snapshot?.pieces || []),...(pieceId?[pieceId]:[])])];
      const options={target:target.value,pieces,allVersions:snapshot?.allVersions || [],accepted:[...accepted],force};
      const result=unpublish?await api.unpublish({target:target.value,piece:pieceId,accepted:[...accepted],force},s=>status.textContent='Preparing preview: '+progressText(s)):await api.build(options,s=>status.textContent='Preparing preview: '+progressText(s));
      if(!dialog.isConnected)return;
      renderChecks(result);
      if(result.blocked){status.textContent='Publication is blocked. Resolve the listed checks and rebuild.';return;}
      candidate=result;status.textContent='Preview ready. Nothing has been made public.';
      renderPreview(result);
    } catch(error) {output.append(failText(error));status.textContent='Preview did not finish.';}
    finally {lock(false);}
  }
  function renderChecks(result) {
    const checks=el('ul',{class:'publish-checks'});
    for(const g of result.gates || [])checks.append(el('li',{},`${g.ok?'Pass':g.overridden?'Overridden':'Fail'}: ${g.piece} ${g.name}${g.detail?' — '+g.detail:''}`));
    for(const s of result.stops || [])if(!s.name.startsWith('shared_scan:'))checks.append(el('li',{class:'err'},`Hard stop: ${s.piece} ${s.name}`));
    output.append(checks);
    for(const shared of new Map((result.shared || []).filter(s=>s.status!=='ok').map(s=>[s.id,s])).values()) {
      if(shared.status==='stop'){output.append(el('p',{class:'err'},`${shared.id}: shared scan is blocked by its pool.`));continue;}
      const checkbox=el('input',{type:'checkbox',checked:accepted.has(shared.id),onchange:()=>{if(checkbox.checked)accepted.add(shared.id);else accepted.delete(shared.id);candidate=null;output.querySelectorAll('.publish-confirm').forEach(b=>b.disabled=true);status.textContent='Shared-scan consent changed. Rebuild the preview.';}});
      output.append(el('label',{class:'publish-choice'},checkbox,` Accept ${shared.id} visible in the scan${shared.facing?' (facing page)':''}`));
    }
    const hardStop=(result.stops || []).some(s=>!s.name.startsWith('shared_scan:')) || (result.shared || []).some(s=>s.status==='stop');
    if(!hardStop && (result.gates || []).some(g=>!g.ok)) {
      const checkbox=el('input',{type:'checkbox',checked:force,onchange:()=>{force=checkbox.checked;candidate=null;output.querySelectorAll('.publish-confirm').forEach(b=>b.disabled=true);status.textContent='Override changed. Rebuild the preview.';}});
      output.append(el('label',{class:'publish-choice'},checkbox,' Publish anyway: override failed gates only. Reserve, Archive, stale transcripts and leaks cannot be overridden.'));
    }
    for(const w of result.warnings || [])output.append(el('p',{class:'note'},w));
  }
  function renderPreview(c) {
    for(const [pid,v]of Object.entries(c.versions || {}))output.append(el('p',{class:'note'},`${pid}: version ${v.indices.join(', ')} of ${v.total}; ${v.how}. Corrections on unpublished versions: ${v.unpublishedCorrected}.`));
    const width=el('select',{'aria-label':'Preview size'},el('option',{value:'390'},'Phone'),el('option',{value:'960'},'Desktop'));
    const frame=el('iframe',{title:'Exact public snapshot preview',src:c.preview,sandbox:'allow-scripts allow-same-origin',class:'publish-frame'});
    frame.style.width='390px';width.addEventListener('change',()=>frame.style.width=width.value+'px');
    output.append(el('label',{},'Preview size ',width),el('div',{class:'publish-frame-wrap'},frame));
    const strings=el('details',{},el('summary',{},'Reader-visible metadata'));
    strings.append(el('pre',{},JSON.stringify(c.readerStrings || {},null,2)));output.append(strings);
    const listing=el('details',{},el('summary',{},`${c.files.length} files in this exact upload`));
    listing.append(el('pre',{},c.files.map(f=>`${f.path}  ${f.size} bytes  ${f.sha256}`).join('\n')));output.append(listing);
    output.append(el('p',{class:'note publish-hash'},'Snapshot SHA-256: '+c.hash));
    const confirm=el('button',{type:'button',class:'btn primary publish-confirm',onclick:async()=>{
      if(busy || candidate?.id!==c.id){status.textContent='Build a new preview before confirming.';return;}
      lock(true);confirm.disabled=true;status.textContent='Publishing the confirmed preview…';
      try {
        const result=await api.confirm(c,s=>status.textContent='Publishing confirmed preview: '+progressText(s));
        status.textContent='Published. The reader refreshes within about a minute.';
        output.append(el('a',{href:result.url,target:'_blank',rel:'noopener noreferrer',class:'rlink'},'Open live page'));
        candidate=null;onDone(result);
      }catch(error){output.append(failText(error));confirm.disabled=false;status.textContent='Confirmation did not finish. Retry this exact preview or inspect History.';}
      finally{lock(false);}
    }},unpublish?'Confirm unpublish':`Confirm publish to ${c.target}`);
    output.append(confirm);
  }
  await build();
}

export async function openPublishHistory({canWrite=()=>true,onDone=()=>{}}={}) {
  const {body,close}=modal('Publication history'),api=createPublishClient();
  const message=el('p',{role:'status','aria-live':'polite'});body.append(message);
  try {
    const history=await api.history();
    const snapshots=history.records.filter(r=>Array.isArray(r.pieces) && r.hash).sort((a,b)=>b.createdAt.localeCompare(a.createdAt));
    if(!snapshots.length){message.textContent='No confirmed snapshots yet.';return;}
    for(const s of snapshots) {
      const current=history.pointers[s.target]?.id===s.id;
      const row=el('section',{class:'publish-history-row'},el('h3',{},`${s.target} · ${s.createdAt}${current?' · current':''}`),el('p',{},s.pieces.join(', ') || 'Blank paper'),el('code',{},s.id));
      if(!current) {
        let armed=false;
        const rollback=el('button',{type:'button',class:'btn small',disabled:!canWrite(),onclick:async()=>{
          if(!armed){armed=true;rollback.textContent='Tap again to roll back';return;}
          rollback.disabled=true;close.disabled=true;
          try{await api.rollback(s.id,s.target,history.pointers[s.target]);message.textContent='Rolled back. Reopen History for the current list.';onDone();}catch(e){body.append(failText(e));rollback.disabled=false;}finally{close.disabled=false;}
        }},'Roll back');row.append(rollback);
      }
      if(current)for(const pieceId of s.pieces)row.append(el('button',{type:'button',class:'btn small',disabled:!canWrite(),onclick:()=>openPublisher({pieceId,canWrite,onDone,unpublish:true})},`Unpublish ${pieceId}`));
      body.append(row);
    }
  }catch(error){body.append(failText(error));}
}
