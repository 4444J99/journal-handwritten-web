// A candidate is previewed only after every immutable draft file is ready.
// Public copying starts only from the separate, explicit Confirm action.
export function createPublishClient({fetchImpl=(...args)=>fetch(...args),mode='browser',compileImpl}={}) {
  async function request(action,body,method='POST') {
    const response=await fetchImpl('/api/publish/'+action,{method,credentials:'same-origin',redirect:'error',headers:{'content-type':'application/json'},...(method==='GET'?{}:{body:JSON.stringify(body)})});
    let data;try{data=await response.json();}catch{throw new Error('The Studio session may have expired. Sign in again before publishing.');}
    if(!response.ok)throw new Error(data.error || 'Publication request failed.');
    return data;
  }
  async function materialize(candidate,onProgress=()=>{}) {
    if(candidate.blocked)return candidate;
    if(!/^[a-f0-9]{64}$/.test(candidate.id) || candidate.hash!==candidate.id)throw new Error('Invalid preview candidate.');
    // At most 200 pieces and 1,000 files are admitted. Each used page
    // contributes files, so 2 + pieces + pages + files is below 2,202.
    for(let n=0;n<2202;n++) {
      const state=await request('materialize',{id:candidate.id,hash:candidate.hash});
      onProgress(state);
      if(state.ready)return candidate;
    }
    throw new Error('Draft preparation did not finish. Reopen Publish to retry.');
  }
  async function browserBuild(options,onProgress=()=>{}) {
    const context=await request('context',{target:options.target});
    const {digest}=await import('./publish-compiler.mjs');
    async function input(path,hash) {
      if(!/^\/publish\/[A-Za-z0-9_.-]+$/.test(path))throw new Error('Invalid publication source URL.');
      const r=await fetchImpl(path,{credentials:'same-origin',redirect:'error'});
      if(!r.ok)throw new Error('The private publication source could not be loaded.');
      const text=await r.text();if(await digest(text)!==hash)throw new Error('Publication source changed. Rebuild the preview.');return text;
    }
    const [sourceText,shell]=await Promise.all([input(context.sourceUrl,context.sourceHash),input(context.shellUrl,context.shellSha256)]);
    let pieces=options.pieces,allVersions=options.allVersions || [];
    if(options.removePiece) {
      if(!context.current?.pieces.includes(options.removePiece))throw new Error('This poem is not in the current snapshot.');
      pieces=context.current.pieces.filter(p=>p!==options.removePiece);
      allVersions=(context.current.allVersions || []).filter(p=>p!==options.removePiece);
    }
    const payload={target:options.target,source:JSON.parse(sourceText),db:context.db,shell,pieces,allVersions,accepted:options.accepted || [],force:options.force===true};
    onProgress({phase:'building',cursor:0,total:0});
    let result;
    if(compileImpl)result=await compileImpl(payload);
    else if(typeof Worker!=='undefined') {
      const worker=new Worker(new URL('./publish-worker.mjs',import.meta.url),{type:'module'});
      try{result=await new Promise((resolve,reject)=>{worker.onmessage=e=>e.data.error?reject(new Error(e.data.error)):resolve(e.data.result);worker.onerror=()=>reject(new Error('Browser publication build failed.'));worker.postMessage(payload);});}
      finally{worker.terminate();}
    } else {result=await (await import('./publish-compiler.mjs')).buildCandidate(payload);}
    if(result.blocked)return result;
    const proposed=await request('propose',{context:context.id,pieces:result.pieces,allVersions:result.allVersions,accepted:payload.accepted,force:payload.force,
      files:result.files.map(({text,...file})=>file),gates:result.gates,shared:result.shared,warnings:result.warnings,versions:result.versions});
    const data=result.files.find(f=>f.path==='data/j.json');
    if(data)await request('upload-data',{id:proposed.id,hash:proposed.hash,text:data.text});
    return materialize(proposed,onProgress);
  }
  return {
    history:()=>request('history',null,'GET'),
    build:async(options,onProgress)=>mode==='browser'?browserBuild(options,onProgress):materialize(await request('build',options),onProgress),
    unpublish:async(options,onProgress)=>mode==='browser'?browserBuild({...options,removePiece:options.piece},onProgress):materialize(await request('unpublish',options),onProgress),
    async rollback(id,target,expectedCurrent) {
      let state=await request('rollback',{id,target,expectedCurrent});
      for(let n=0;!state.done && n<1001;n++)state=await request('rollback',{id,target,job:state.job});
      if(!state.done)throw new Error('Rollback did not finish. Inspect History before retrying.');
      return state;
    },
    async confirm(candidate,onProgress=()=>{}) {
      if(!/^[a-f0-9]{64}$/.test(candidate?.id) || candidate.hash!==candidate.id)throw new Error('Invalid preview candidate.');
      // Up to 1,000 copies followed by bounded release-record recovery.
      for(let n=0;n<1100;n++) {
        const result=await request('confirm',{id:candidate.id,hash:candidate.hash});
        onProgress(result);
        if(result.done)return result;
      }
      throw new Error('Confirmation did not finish. Retry this exact candidate or inspect History.');
    },
  };
}
