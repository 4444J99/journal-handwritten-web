import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {CDP,withBrowser} from '../tools/cdp_client.mjs';
import {freePort} from '../studio-cf/tests/helpers/wrangler.mjs';
const CHROME=process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
test('reader bookmarks keep the public pathname across snapshot changes',{timeout:30000},async()=>{
 const source=await fs.readFile(new URL('../site/index.html',import.meta.url),'utf8');
 const hashFunction=source.slice(source.indexOf('function setHash(){'),source.indexOf('function readHash(){'));
 let snapshot='a'.repeat(64);
 const server=http.createServer((req,res)=>{if(req.url!=='/'){res.writeHead(404);res.end();return;}res.setHeader('content-type','text/html');res.end('<!doctype html><head><base href="/_snapshot/'+snapshot+'/"></head><script>const B={};const side="canvas";function selectedSource(){return {};}function sourceHash(){return "piece/p001/v0";}'+hashFunction+'setHash();</script>');});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base='http://127.0.0.1:'+server.address().port;
 const profile=await fs.mkdtemp(path.join(os.tmpdir(),'reader-bookmark-'));
 try {await withBrowser({connect:CDP.connect,launch:async()=>{const port=await freePort();const proc=spawn(CHROME,['--headless=new','--no-sandbox','--remote-debugging-port='+port,'--user-data-dir='+profile,'--no-first-run','--disable-gpu','about:blank'],{stdio:'ignore'});for(let i=0;i<60;i++){try{const j=await(await fetch('http://127.0.0.1:'+port+'/json/version')).json();return{proc,wsUrl:j.webSocketDebuggerUrl};}catch{await new Promise(r=>setTimeout(r,100));}}proc.kill();throw Error('Chrome did not start');}},async cdp=>{
 const {targetId}=await cdp.send('Target.createTarget',{url:'about:blank'}),{sessionId}=await cdp.send('Target.attachToTarget',{targetId,flatten:true});
 const send=(m,p={})=>cdp.send(m,p,sessionId);await send('Page.enable');await send('Runtime.enable');
 async function address(){for(let i=0;i<100;i++){const r=await send('Runtime.evaluate',{expression:'location.href',returnByValue:true});if(r.result.value.includes('#'))return r.result.value;await new Promise(r=>setTimeout(r,50));}throw Error('Reader hash missing');}
 await send('Page.navigate',{url:base+'/'});const bookmark=await address();assert.equal(bookmark,base+'/#piece/p001/v0');
 snapshot='b'.repeat(64);await send('Page.navigate',{url:bookmark});assert.equal(await address(),bookmark);
 assert.equal((await fetch(bookmark)).status,200);
 });}finally{await new Promise(r=>server.close(r));await fs.rm(profile,{recursive:true,force:true});}
});
