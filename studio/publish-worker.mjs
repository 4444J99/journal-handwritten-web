import {buildCandidate} from './publish-compiler.mjs';
self.onmessage=async event=>{
  try{self.postMessage({result:await buildCandidate(event.data)});}
  catch{self.postMessage({error:'The browser could not compile this publication candidate.'});}
};
