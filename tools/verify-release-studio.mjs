import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
// All application code and backend test helpers come from the immutable source root.
// The caller provides installed tools; this runner installs nothing and contacts no account.
const opts={};
for(let i=2;i<process.argv.length;i+=2){
  const k=process.argv[i],v=process.argv[i+1];
  if(!['--source-root','--scratch-root','--wrangler','--chromium','--revision','--dist'].includes(k)||!v)throw new Error('Usage: node verify-release-studio.mjs --source-root PATH --scratch-root FRESH_PATH --wrangler EXECUTABLE --chromium EXECUTABLE --revision FULL_SHA [--dist ASSEMBLED_STUDIO]');
  opts[k]=v;
}
for(const k of ['--source-root','--scratch-root','--wrangler','--chromium','--revision'])if(!opts[k])throw new Error('Missing '+k);
if(!/^[a-f0-9]{40}$/.test(opts['--revision']))throw new Error('--revision must identify the full tested Git SHA');
const SOURCE=path.resolve(opts['--source-root']);
const ROOT=path.resolve(opts['--scratch-root']);
const DIST=path.resolve(opts['--dist']||path.join(SOURCE,'studio-cf/dist'));
const git=(...args)=>execFileSync('git',['-C',SOURCE,...args],{encoding:'utf8'}).trim();
assert.equal(git('rev-parse','HEAD'),opts['--revision'],'--revision must match the source checkout');
assert.equal(git('status','--porcelain'),'','Commit the source before recording revision-bound acceptance');
assert.equal(fs.realpathSync(fileURLToPath(import.meta.url)),fs.realpathSync(path.join(SOURCE,'tools/verify-release-studio.mjs')),'Run the verifier from the tested checkout');
for(const k of ['--wrangler','--chromium'])fs.accessSync(path.resolve(opts[k]),fs.constants.X_OK);
for(const p of ['index.html','cf-adapter.js','data/review.json'])assert.ok(fs.readFileSync(path.join(SOURCE,'studio',p)).equals(fs.readFileSync(path.join(DIST,p))),'Rebuild the assembled studio: '+p);
if(fs.existsSync(ROOT)&&fs.readdirSync(ROOT).length)throw new Error('--scratch-root must be absent or empty; no existing state is overwritten');
fs.mkdirSync(ROOT,{recursive:true});
process.env.STUDIO_CF_SCRATCH=path.join(ROOT,'runtime');
process.env.WRANGLER_BIN=path.resolve(opts['--wrangler']);
const { makeKey, signRS256, claims, startJwks }=await import(pathToFileURL(path.join(SOURCE,'studio-cf/tests/helpers/jwt.mjs')));
const { startPagesDev }=await import(pathToFileURL(path.join(SOURCE,'studio-cf/tests/helpers/wrangler.mjs')));
const require=createRequire(import.meta.url);
const { chromium }=require('playwright');
fs.mkdirSync(path.join(ROOT,'results'),{recursive:true});
const result={tested_revision:opts['--revision'],source_tree:git('rev-parse','HEAD^{tree}'),runner_sha256:crypto.createHash('sha256').update(fs.readFileSync(fileURLToPath(import.meta.url))).digest('hex'),runtime:{node:process.version,platform:process.platform,playwright:require('playwright/package.json').version},source_root:SOURCE,started:new Date().toISOString(),scope:'Disposable local D1, actual studio + cf-adapter, loopback JWKS, synthetic release state; no live DB or publishing.',checks:[],source_hashes:{},blocked_external_requests:[]};
for(const p of ['studio/index.html','studio/cf-adapter.js','studio-cf/lib/api.js','studio-cf/lib/auth.js','studio-cf/functions/_middleware.js','studio-cf/schema.sql'])result.source_hashes[p]=crypto.createHash('sha256').update(fs.readFileSync(path.join(SOURCE,p))).digest('hex');
const record=(name,data={})=>{result.checks.push({name,status:'pass',...data});console.log('PASS '+name)};
let jwks,srv,browser;
try{
const key=makeKey('t03-local');jwks=await startJwks({keys:[key]});const team=`127.0.0.1:${jwks.port}`,iss=`https://${team}`,aud='t03-local';
const token=signRS256(key,claims({iss,aud,email:'owner@example.test'}));
const headers={'Cf-Access-Jwt-Assertion':token,'Content-Type':'application/json'};
console.log('Starting local D1 and Pages dev');
srv=await startPagesDev({ACCESS_TEAM_DOMAIN:team,ACCESS_AUD:aud,OWNER_EMAILS:'owner@example.test',READONLY_EMAILS:'reader@example.test',ACCESS_JWKS_URL_TEST:`http://${team}/cdn-cgi/access/certs`},'t03',{dir:DIST});
result.local_persist=srv.persist;
console.log('Local server ready '+srv.base);
const req=async(coll,id,body)=>{const r=await fetch(`${srv.base}/api/db/${coll}${id?'/'+id:''}`,{headers,method:body===undefined?'GET':'PUT',...(body===undefined?{}:{body:JSON.stringify(body)})});assert.equal(r.status,200);return r.json()};
const data=JSON.parse(fs.readFileSync(path.join(SOURCE,'studio/data/review.json'),'utf8'));const keys=data.items.filter(x=>x.g!==4).slice(0,2).map(x=>x.id);result.fixture_keys=keys;
for(let i=0;i<keys.length;i++)await req('release',keys[i],{pool:'series',order:i,exposures:[],fixture:'T03 LOCAL ONLY; not author approval'});
await req('decisions','release-numbering',{choice:'as-posted',fixture:'T03 LOCAL ONLY; not author decision'});
browser=await chromium.launch({executablePath:path.resolve(opts['--chromium']),headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
result.browser=browser.version();
const makeContext=async(options={})=>{
  const ctx=await browser.newContext({extraHTTPHeaders:{'Cf-Access-Jwt-Assertion':token},...options});
  ctx.on('page',p=>p.on('pageerror',e=>{result.page_errors??=[];result.page_errors.push(e.message)}));
  await ctx.route('**/*',route=>{
    if(new URL(route.request().url()).origin===srv.base)return route.continue();
    result.blocked_external_requests.push(new URL(route.request().url()).origin);
    return route.abort();
  });
  return ctx;
};
const ctx=await makeContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,colorScheme:'light'});const page=await ctx.newPage();
await page.goto(srv.base);await page.waitForFunction(()=>document.querySelector('#save')?.textContent==='Synced');
record('Owner connects to disposable D1');
await page.locator('[data-view="release"]').click();await page.getByRole('button',{name:'Calendar',exact:true}).click();
const row=(i)=>page.locator('.rrow.cal').nth(i);
await row(0).getByRole('button',{name:'Open',exact:true}).click();
const before=(await req('release')).rev;
await page.locator(`#pu-${keys[0]}`).fill('javascript:alert(1)');
await page.getByRole('button',{name:'Mark posted anyway',exact:true}).click();
assert.equal((await req('release')).rev,before);assert.equal(await page.getByRole('button',{name:'Not ready — tap again to confirm',exact:true}).count(),0);record('Invalid Mark posted URL neither arms nor writes');
await page.locator(`#pu-${keys[0]}`).fill('https://versforms.pages.dev/#p001');
await page.getByRole('button',{name:'Mark posted anyway',exact:true}).click();
assert.equal((await req('release')).rev,before);await page.getByRole('button',{name:'Not ready — tap again to confirm',exact:true}).waitFor();record('Unready first tap arms without DB write');
await page.getByRole('button',{name:'Not ready — tap again to confirm',exact:true}).click();
await page.waitForFunction(()=>document.querySelector('#save')?.textContent==='Saved');
let doc=(await req('release',keys[0])).data;assert.equal(doc.exposures.length,1);assert.equal(doc.exposures[0].type,'social');assert.equal(doc.exposures[0].where,'versforms.pages.dev');assert.equal(doc.exposures[0].account,'vers.forms');assert.equal(doc.num,1);assert.equal(doc.exposures[0].ver,'final');
result.mark_posted_record=doc;record('Unready second tap persists one social event and derived number 1');
await page.reload();await page.waitForFunction(()=>document.querySelector('#save')?.textContent==='Synced');await page.locator('[data-view="release"]').click();await page.getByRole('button',{name:'Calendar',exact:true}).click();
assert.ok((await row(0).getAttribute('class')).includes('posted'));await row(0).getByRole('button',{name:'Open',exact:true}).click();assert.equal(await row(0).getByRole('button',{name:/Mark posted/}).count(),0);assert.equal((await req('release',keys[0])).data.exposures.length,1);record('Reload reads persisted Mark posted record and removes repeat button');
await page.getByRole('button',{name:'Exposure',exact:true}).click();await page.locator('#pk-expoQ').fill(keys[1]);await page.locator('.picks button').first().click();
await page.locator('[data-choice="site"]').click();assert.equal(await page.locator('#ex-type').inputValue(),'site');assert.equal(await page.locator('#ex-where').inputValue(),'versforms.pages.dev');assert.equal(await page.locator('#ex-account').inputValue(),'');
const beforeExposure=await req('release');
for(const unsafe of ['javascript:alert(1)','data:text/html,x','/relative']){
  await page.locator('#ex-url').fill(unsafe);await page.getByRole('button',{name:'Log appearance',exact:true}).tap();
  assert.equal(await page.locator('#ex-url').getAttribute('aria-invalid'),'true');
  assert.match(await page.locator('#ex-url-error').innerText(),/https?:/);
  assert.deepEqual(await req('release'),beforeExposure);
  assert.equal(await page.locator('#ex-url').inputValue(),unsafe);
}
record('Unsafe Exposure links show an error, preserve the draft and do not write');
await page.locator('#ex-ver').fill('scan');await page.locator('#ex-url').fill('https://example.test/local-site-fixture');await page.getByRole('button',{name:'Log appearance',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#save')?.textContent==='Saved');
doc=(await req('release',keys[1])).data;assert.equal(doc.exposures.length,1);assert.equal(doc.exposures[0].type,'site');assert.equal(doc.exposures[0].ver,'scan');assert.ok(!('account'in doc.exposures[0]));record('Site shortcut writes site event, scan version, omitted empty account');result.site_record=doc;
await page.reload();await page.waitForFunction(()=>document.querySelector('#save')?.textContent==='Synced');await page.locator('[data-view="release"]').click();await page.getByRole('button',{name:'Calendar',exact:true}).click();assert.ok(!(await row(1).getAttribute('class')).includes('posted'));record('Site-only exposure persists after reload but Calendar remains unposted');
// Keep phone captures at viewport size: Chromium 153 full-page captures reset touch emulation.
await page.screenshot({path:path.join(ROOT,'results','calendar-390px.png'),fullPage:false});
await page.getByRole('button',{name:'Exposure',exact:true}).click();await page.locator('#pk-expoQ').fill(keys[1]);await page.locator('.picks button').first().click();await page.locator('[data-choice="instagram"]').click();assert.equal(await page.locator('#ex-type').inputValue(),'social');assert.equal(await page.locator('#ex-where').inputValue(),'Instagram');assert.equal(await page.locator('#ex-account').inputValue(),'vers.forms');await page.locator('#ex-where').fill('Local fixture manual edit');assert.equal(await page.locator('[data-choice="instagram"]').getAttribute('aria-pressed'),'false');record('Instagram shortcut defaults and manual-edit deselection');
await page.locator('[data-choice="instagram"]').click();await page.locator('#ex-ver').fill('draft');await page.locator('#ex-url').fill('https://example.test/local-instagram-fixture');await page.getByRole('button',{name:'Log appearance',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#save')?.textContent==='Saved');doc=(await req('release',keys[1])).data;assert.equal(doc.exposures.length,2);assert.equal(doc.exposures[1].type,'social');assert.equal(doc.exposures[1].account,'vers.forms');assert.equal(doc.exposures[1].ver,'draft');result.exposure_record=doc;record('Instagram event appends without replacing Site event');
await page.reload();await page.waitForFunction(()=>document.querySelector('#save')?.textContent==='Synced');await page.locator('[data-view="release"]').click();await page.getByRole('button',{name:'Exposure',exact:true}).click();assert.equal(await page.locator('.rrow.slim').count(),3);record('Fresh page reload reads all three persisted events');
const expoSource=fs.readFileSync(path.join(SOURCE,'studio/index.html'),'utf8').match(/const EXPO = (\[[\s\S]*?\n\]);/)[1]; const expo=new Function('return '+expoSource)(); result.publication_flags=Object.fromEntries(expo.filter(e=>['site','social'].includes(e[0])).map(e=>[e[0],e[2]])); assert.deepEqual(result.publication_flags,{site:false,social:false}); assert.equal(await page.getByText('copyright: published',{exact:true}).count(),0); record('Site and social source flags false and no published badge rendered for persisted events');
result.mobile_layout=await page.evaluate(()=>({viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth}));assert.ok(result.mobile_layout.documentWidth<=390);record('390px emulator has no document horizontal overflow',result.mobile_layout);await page.screenshot({path:path.join(ROOT,'results','exposure-390px.png'),fullPage:false});
const legacy=(await req('release',keys[1])).data;
legacy.exposures.push({type:'site',where:'Legacy invalid URL fixture',url:'javascript:alert(1)',date:'2026-01-01',ver:'scan'});
await req('release',keys[1],legacy);
const legacyRevision=(await req('release')).rev;
await page.reload();await page.waitForFunction(()=>document.querySelector('#save')?.textContent==='Synced');await page.locator('[data-view="release"]').click();await page.getByRole('button',{name:'Exposure',exact:true}).click();
assert.equal(await page.locator('.rrow.slim').count(),4);
const legacyRow=page.locator('.rrow.slim').filter({hasText:'Legacy invalid URL fixture'});
assert.equal(await legacyRow.count(),1);assert.equal(await legacyRow.locator('a').count(),0);
assert.deepEqual((await req('release',keys[1])).data,legacy);
assert.equal((await req('release')).rev,legacyRevision);
record('Legacy unsafe URL stays in the record without a clickable link or read-time rewrite');
result.appearance_matrix=[];
for(const colorScheme of ['light','dark']){
  await page.emulateMedia({colorScheme});
  for(const view of ['Calendar','Exposure']){
    await page.getByRole('button',{name:view,exact:true}).tap();
    const layout=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,bg:getComputedStyle(document.body).backgroundColor,color:getComputedStyle(document.body).color,touch:navigator.maxTouchPoints,dark:matchMedia('(prefers-color-scheme: dark)').matches}));
    assert.ok(layout.scrollWidth<=390);assert.ok(layout.touch>0);assert.equal(layout.dark,colorScheme==='dark');assert.notEqual(layout.bg,layout.color);
    result.appearance_matrix.push({view,colorScheme,...layout});
    await page.screenshot({path:path.join(ROOT,'results',`${view.toLowerCase()}-phone-${colorScheme}.png`),fullPage:false});
  }
}
assert.notEqual(result.appearance_matrix[0].bg,result.appearance_matrix[2].bg);
record('Calendar and Exposure fit touch phone layout in light and dark modes');
const desktop=await makeContext({viewport:{width:1280,height:900},colorScheme:'light'});
const desktopPage=await desktop.newPage();await desktopPage.goto(srv.base);await desktopPage.waitForFunction(()=>document.querySelector('#save')?.textContent==='Synced');await desktopPage.locator('[data-view="release"]').click();
for(const colorScheme of ['light','dark']){
  await desktopPage.emulateMedia({colorScheme});
  for(const view of ['Calendar','Exposure']){
    await desktopPage.getByRole('button',{name:view,exact:true}).click();
    assert.ok(await desktopPage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await desktopPage.screenshot({path:path.join(ROOT,'results',`${view.toLowerCase()}-desktop-${colorScheme}.png`),fullPage:true});
  }
}
record('Persisted release state renders on desktop in light and dark modes');await desktop.close();
const strangerToken=signRS256(key,claims({iss,aud,email:'unlisted@example.test'}));
const stranger=await makeContext({extraHTTPHeaders:{'Cf-Access-Jwt-Assertion':strangerToken}});
const strangerPage=await stranger.newPage();const denied=await strangerPage.goto(srv.base);
assert.equal(denied.status(),403);assert.equal(await denied.text(),'');assert.equal(await strangerPage.locator('#save').count(),0);
const beforeDeniedWrite=await req('release');
const deniedWrite=await stranger.request.put(`${srv.base}/api/db/release/${keys[0]}`,{data:{fixture:'must not save'}});
assert.equal(deniedWrite.status(),403);assert.deepEqual(await req('release'),beforeDeniedWrite);
record('Correctly signed unlisted email receives no studio and cannot save');await stranger.close();
assert.deepEqual(result.page_errors||[],[],'No uncaught browser errors');
assert.equal(git('rev-parse','HEAD'),opts['--revision']);assert.equal(git('status','--porcelain'),'');
result.release_collection=await req('release');result.status='pass';
}catch(e){result.status='fail';result.error=e.stack;console.error(e.stack);process.exitCode=1;}
finally{result.finished=new Date().toISOString();fs.writeFileSync(path.join(ROOT,'results','acceptance.json'),JSON.stringify(result,null,2)+'\n');if(srv)fs.writeFileSync(path.join(ROOT,'results','wrangler.log'),srv.log());if(browser)await browser.close();if(srv)await srv.stop();if(jwks)await jwks.close();}
