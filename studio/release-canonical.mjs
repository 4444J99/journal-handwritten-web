// Explicit cross-runtime encoding; not RFC 8785/JCS. Type tags keep number
// encodings distinct from ordinary arrays, strings and objects in the payload.
export function canonicalJSON(value) {
  const visiting=new Set();
  function string(value) {
    for(let i=0;i<value.length;i++) {
      const n=value.charCodeAt(i);
      if(n>=0xd800&&n<=0xdbff) {const next=value.charCodeAt(++i);if(!(next>=0xdc00&&next<=0xdfff))throw new Error('Lone Unicode surrogate.');}
      else if(n>=0xdc00&&n<=0xdfff)throw new Error('Lone Unicode surrogate.');
    }
    return value;
  }
  function node(item) {
    if(item===null)return ['null'];
    if(typeof item==='boolean')return ['boolean',item];
    if(typeof item==='string')return ['string',string(item)];
    if(typeof item==='number') {
      if(!Number.isFinite(item)||Number.isInteger(item)&&!Number.isSafeInteger(item))throw new Error('Release numbers must be finite and integers must be safe.');
      const data=new Uint8Array(8);new DataView(data.buffer).setFloat64(0,item===0?0:item,false);
      return ['number',[...data].map(n=>n.toString(16).padStart(2,'0')).join('')];
    }
    if(!item||typeof item!=='object'||!Array.isArray(item)&&Object.getPrototypeOf(item)!==Object.prototype)throw new Error('Release inputs must be plain JSON.');
    if(visiting.has(item))throw new Error('Cyclic release input.');
    const ownKeys=Reflect.ownKeys(item), array=Array.isArray(item);
    for(const key of ownKeys) {
      if(array&&key==='length')continue;
      const descriptor=Object.getOwnPropertyDescriptor(item,key);
      if(typeof key!=='string'||!descriptor.enumerable||!Object.hasOwn(descriptor,'value'))throw new Error('Hidden or computed release property.');
      if(array&&(!/^(0|[1-9][0-9]*)$/.test(key)||Number(key)>=item.length))throw new Error('Extended release array.');
    }
    visiting.add(item);
    try {
      if(Array.isArray(item)) {
        if(ownKeys.length!==item.length+1)throw new Error('Sparse or extended release array.');
        return ['array',item.map(node)];
      }
      return ['object',Object.keys(item).sort().map(k=>[string(k),node(item[k])])];
    } finally {visiting.delete(item);}
  }
  return JSON.stringify(['versforms.typed-json.v1',node(value)]);
}
