#!/usr/bin/env node
// Promotion inventory in the actual Studio release/Sort view; local fixtures only.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const origin={family:'composite',revisionId:'r.fixture',recordId:'c.fixture',versionId:'c.fixture',pieceId:'p001',text:'Technical fixture',verified:false,render:'typeset',lines:[{lineId:'composite-0-0',text:'Technical fixture',breakBefore:false}]};
const promotion={family:'promotion',revisionId:'promotion.fixture',pieceId:'p127',originComposite:{recordId:'c.fixture',revisionId:'r.fixture',versionId:'c.fixture'}};
const collections={composites:{'r.fixture':origin,'promotion.fixture':promotion},release:{p127:{pool:'unassigned',posted:false,exposures:[],originComposite:promotion.originComposite}}};
let rev=1;
const types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.css':'text/css','.jpg':'image/jpeg'};
const server=http.createServer(async(req,res)=>{
 const u=new URL(req.url,'http://localhost');
 const json=body=>{res.setHeader('content-type','application/json');res.end(JSON.stringify(body));};
 if(u.pathname==='/api/me')return json({email:'owner@fixture.invalid',canWrite:true});
 const match=/^\/api\/db\/([^/]+)(?:\/([^/]+))?$/.exec(u.pathname);
 if(match){const [,coll,id]=match;collections[coll]??={};if(req.method==='PUT'){let body='';for await(const b of req)body+=b;collections[coll][id]=JSON.parse(body);rev++;return json({ok:true,rev});}if(id)return json({id,data:collections[coll][id]});return json({rev,docs:Object.entries(collections[coll]).map(([id,data])=>({id,data}))});}
 const file=path.resolve(root,'.'+u.pathname);if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);res.end();return;}res.setHeader('content-type',types[path.extname(file)]||'application/octet-stream');fs.createReadStream(file).pipe(res);
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const require=createRequire(import.meta.url),{chromium}=require(path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES||'','playwright'));
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
try{
 const context=await browser.newContext({viewport:{width:390,height:844},hasTouch:true});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:'+server.address().port+'/studio/index.html');
 await page.getByRole('tab',{name:'Release',exact:true}).click();
 const row=page.locator('.rrow').filter({has:page.getByRole('button',{name:'p127',exact:true})});
 await row.waitFor();assert.match(await row.textContent(),/Composite/);
 await row.getByRole('button',{name:'Reserve',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('[data-view="release"]').getAttribute('aria-selected')==='true');
 await new Promise(r=>setTimeout(r,300));assert.equal(collections.release.p127.pool,'reserve');
 assert.equal(collections.release.p001,undefined);
 await page.reload();await page.getByRole('tab',{name:'Release',exact:true}).click();
 await page.getByRole('button',{name:'Reserve',exact:true}).first().click();
 await page.locator('.rrow').filter({has:page.getByRole('button',{name:'p127',exact:true})}).waitFor();
 assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,pieceId:'p127',pool:collections.release.p127.pool,originalPreserved:collections.composites['r.fixture'].pieceId==='p001'}));await context.close();
}finally{await browser.close();await new Promise(r=>server.close(r));}
