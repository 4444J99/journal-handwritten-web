#!/usr/bin/env node
// Actual generated T10/T08 packages through assembled private Studio, local D1,
// and the real reader. All copies, deliberately bad inputs and writes are local.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const arg = name => { const at = process.argv.indexOf(name); return at < 0 ? null : process.argv[at + 1]; };
const required = name => { const value = arg(name); if (!value) throw new Error('Required argument: ' + name); return path.resolve(value); };
const T10 = required('--t10-package'), HISTORY = required('--artifact-history');
const T08 = required('--region-package'), REGION_DESCRIPTOR = required('--region-descriptor');
const OUT = required('--out'), CHROME = required('--chrome');
if (fs.existsSync(OUT) && fs.readdirSync(OUT).length) throw new Error('Evidence directory must be empty.');
fs.mkdirSync(OUT, {recursive:true});
const SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'versforms-package-browser-'));
process.env.STUDIO_CF_SCRATCH = path.join(SCRATCH, 'runtime');
const {chromium} = createRequire(import.meta.url)(arg('--playwright') || path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES || '', 'playwright'));
const {makeKey, signRS256, claims, startJwks} = await import('../studio-cf/tests/helpers/jwt.mjs');
const {startPagesDev} = await import('../studio-cf/tests/helpers/wrangler.mjs');
const digest = bytes => 'sha256:' + createHash('sha256').update(bytes).digest('hex');
const read = name => JSON.parse(fs.readFileSync(name, 'utf8'));
const encoded = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');
function inventory(folder) {
  const result = [];
  function visit(dir) { for (const entry of fs.readdirSync(dir, {withFileTypes:true})) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) visit(file);
    else { assert.ok(entry.isFile() && !entry.isSymbolicLink()); const data = fs.readFileSync(file); result.push({path:path.relative(folder,file).split(path.sep).join('/'),bytes:data.length,sha256:digest(data)}); }
  } }
  visit(folder); return result.sort((a,b) => a.path.localeCompare(b.path));
}
const protectedPaths = ['site/index.html','site/reader-features.js','site/reader-packages.js','site/data/j.json','studio/data/review.json','studio/data/notes-versions.json','studio/artifact-preview.html','studio/artifact-preview.mjs','studio/artifact-model.mjs','studio/artifact-store.mjs','studio/notes-store.mjs','studio/notes-model.mjs','studio/source-fingerprint.mjs','studio-cf/build_dist.py','studio-cf/lib/api.js','tools/verify_reader_packages.mjs','release/public.json'];
const before = Object.fromEntries(protectedPaths.map(name => [name,digest(fs.readFileSync(path.join(ROOT,name)))]));
const fixtureInputs = {realization:inventory(T10),regions:inventory(T08),artifactHistory:digest(fs.readFileSync(HISTORY)),regionDescriptor:digest(fs.readFileSync(REGION_DESCRIPTOR))};
const history = read(HISTORY), t10Manifest = read(path.join(T10,'manifest.json'));
assert.ok(Array.isArray(history) && history.length >= 2, 'Use the actual immutable historical + rebound artifact history.');
const stored = history.find(r => r.revisionId === t10Manifest.artifactRevisionId);
assert.ok(stored && stored.parents.length, 'The generated package must bind the saved successor revision.');
assert.deepEqual(read(path.join(T10,'artifact.json')), stored);
const expectedRevision = stored.payload.realization.revisions.at(-1);
assert.equal(typeof stored.fixture,'boolean');assert.equal(typeof expectedRevision.fixture,'boolean');
assert.equal(t10Manifest.fixture,stored.fixture||expectedRevision.fixture,'Package fixture scope combines the stored artifact and latest realization flags.');
const t10Config = {source:stored.source,revisionId:stored.revisionId,package:{manifestUrl:'/private-fixtures/t10/manifest.json',sha256:digest(fs.readFileSync(path.join(T10,'manifest.json')))}};
const t08Config = {...read(REGION_DESCRIPTOR),package:{manifestUrl:'/private-fixtures/t08/region-preview.json',sha256:digest(fs.readFileSync(path.join(T08,'region-preview.json')))}};
const checks = [], errors = [], blockedRequests = [], networkTraps = [], expectedRequestFailures = [];
let browser, jwks, server, activePage;
const contexts = [];
function pass(name, detail = true) { checks.push({name,pass:true,detail}); console.log('PASS ' + name); }
async function check(name, run) {
  try { pass(name, await run()); }
  catch (error) { checks.push({name,pass:false,error:error.stack}); console.error('FAIL ' + name + ': ' + error.message); }
}
const dist = path.join(SCRATCH,'dist');
let token;
async function api(collection, id, data, method = data === undefined ? 'GET' : 'PUT') {
  const response = await fetch(server.base + '/api/db/' + collection + (id ? '/' + id : ''), {method,
    headers:{'Cf-Access-Jwt-Assertion':token(),...(data === undefined ? {} : {'content-type':'application/json'})},
    ...(data === undefined ? {} : {body:JSON.stringify(data)})});
  assert.ok(response.ok, 'Local API ' + collection + ' ' + response.status); return response.json();
}
function t10Variant(name, mutate, {rehash = true} = {}) {
  const folder = path.join(dist,'private-fixtures','variants',name);
  fs.cpSync(T10,folder,{recursive:true});
  const manifest = read(path.join(folder,'manifest.json'));
  mutate(manifest,folder);
  if (rehash) for (const entry of manifest.files) {
    const file = path.join(folder,entry.path);
    if (fs.existsSync(file) && fs.statSync(file).isFile()) { const bytes=fs.readFileSync(file); entry.bytes=bytes.length; entry.sha256=digest(bytes); }
  }
  const bytes=encoded(manifest);fs.writeFileSync(path.join(folder,'manifest.json'),bytes);
  return {...structuredClone(t10Config),package:{manifestUrl:'/private-fixtures/variants/'+name+'/manifest.json',sha256:digest(bytes)}};
}
function regionVariant(name, mutate) {
  const folder=path.join(dist,'private-fixtures','variants',name);fs.cpSync(T08,folder,{recursive:true});
  const manifest=read(path.join(folder,'region-preview.json'));mutate(manifest,folder);
  const digestNames={'region-manifest.json':'manifestDigest','geometry.json':'geometryDigest','assets/source.jpg':'mediaDigest','policy.json':'policyDigest'};
  for(const entry of manifest.files){const file=path.join(folder,entry.path);if(fs.existsSync(file)){const bytes=fs.readFileSync(file);entry.bytes=bytes.length;entry.sha256=digest(bytes);if(digestNames[entry.path])manifest[digestNames[entry.path]]=entry.sha256;}}
  const bytes=encoded(manifest);fs.writeFileSync(path.join(folder,'region-preview.json'),bytes);
  const descriptor={...structuredClone(t08Config),package:{manifestUrl:'/private-fixtures/variants/'+name+'/region-preview.json',sha256:digest(bytes)}};
  for(const key of Object.values(digestNames))descriptor[key]=manifest[key];return descriptor;
}
async function workbench(page, record = stored.recordId) {
  await page.goto(server.base+'/artifact-preview.html');
  await page.waitForFunction(() => document.getElementById('connection')?.textContent.includes('Connected') && !document.getElementById('editing').disabled, {timeout:20000});
  await page.selectOption('#piece',stored.source.pieceId);await page.selectOption('#version',stored.source.versionId);
  await page.selectOption('#record',record);
}
async function prepare(page, kind, descriptor, record = kind === 'realization' ? stored.recordId : '') {
  await page.selectOption('#record',record);
  await page.check('#enable-preview');await page.fill('#preview-config',JSON.stringify({[kind]:descriptor}));await page.click('#mount-preview');
  const result=await page.locator('#preview-status').innerText();assert.match(result,/Controls prepared/,result);
  await page.locator('#feature-preview').getByRole('button',{name:kind==='realization'?'Realization':'Source regions',exact:true}).click();
  if(kind==='realization')await page.getByRole('button',{name:'Start realization',exact:true}).click();
}
async function realized(page) {
  await page.locator('#feature-preview iframe').waitFor({timeout:15000});
  const handle=await page.locator('#feature-preview iframe').elementHandle();
  const frame=await handle.contentFrame();
  await frame.locator('#realization').waitFor();return frame;
}
async function noFrame(page) {await page.waitForFunction(() => document.querySelectorAll('#feature-preview iframe').length===0,{timeout:5000});}
async function seedProbe(page) {
  await page.evaluate(async ({source,recordId}) => {
    const Notes=await import('/notes-model.mjs'),Artifacts=await import('/artifact-model.mjs');
    const [map,review,reviewRows,artifactRows,policyRows]=await Promise.all(['/data/notes-versions.json','/data/review.json','/api/db/reviews','/api/db/artifacts','/api/db/release'].map(async url=>{const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error('Probe current data unavailable');return r.json();}));
    const catalog=Notes.buildSourceCatalog(map,review,{reviews:Object.fromEntries(reviewRows.docs.map(d=>[d.id,d.data]))});
    const version=catalog.pieces.find(p=>p.pieceId===source.pieceId)?.versions.find(v=>v.versionId===source.versionId);
    const currentSource={pieceId:source.pieceId,versionId:source.versionId,sourceFingerprint:version?.sourceFingerprint||version?.fingerprint};
    const groups=Artifacts.artifactHeads(artifactRows.docs.map(d=>d.data),[currentSource]);const group=groups.find(g=>g.recordId===recordId);
    if(!group||group.conflicted||group.stale)throw new Error('Actual saved fixture head is unavailable');
    const saved=group.heads[0];Artifacts.assertArtifact('artifacts',saved);
    const record=policyRows.docs.find(d=>d.id===source.pieceId)?.data||{};
    const currentPolicy={pool:Object.hasOwn(record,'pool')?record.pool:'unsorted',visibility:Object.hasOwn(record,'publicStatus')?record.publicStatus:'private'};
    window.packageProbe={source:currentSource,policy:currentPolicy,stored:saved,review};
  },{source:stored.source,recordId:stored.recordId});
}
async function probe(page,kind,descriptor,{mutation=null}={}) {
  return page.evaluate(async ({kind,descriptor,mutation})=>{
    const M=await import('/site/reader-packages.js'),p=window.packageProbe;
    const clone=structuredClone(p),control=new AbortController();
    if(mutation==='source')clone.source.sourceFingerprint='sha256:'+'f'.repeat(64);
    if(mutation==='stored')clone.stored.revisionId='other-stored-revision';
    if(mutation==='policy')clone.policy.visibility='withheld';
    const geometry=pageId=>{const page=clone.review.pages.find(p=>p.id===pageId);return{pageId:page.id,width:page.w,height:page.h,blocks:page.blocks.map((b,index)=>({index,lines:b.lines.map(l=>({lineId:l.id,box:l.box??null,sourceAnchor:l.sourceAnchor??null}))}))};};
    const options={descriptor,source:p.source,scope:{current:()=>!control.signal.aborted,signal:control.signal},doc:document,
      getCurrentSource:()=>clone.source,getCurrentPolicy:()=>clone.policy,getStoredArtifact:()=>clone.stored,getCurrentReviewGeometry:geometry,
      getCurrentRegionMedia:pageId=>clone.review.pages.find(p=>p.id===pageId).img};
    try { const result=await (kind==='realization'?M.loadRealizationPackage(options):M.loadRegionPackage(options));result.assertCurrent();return{accepted:true}; }
    catch(error){return{accepted:false,message:error.message,name:error.name};}
  },{kind,descriptor,mutation});
}

try {
  const built=spawnSync('python3',['studio-cf/build_dist.py','--out',dist],{cwd:ROOT,encoding:'utf8'});assert.equal(built.status,0,built.stderr||built.stdout);
  for(const name of ['reader-features.js','reader-packages.js'])assert.equal(digest(fs.readFileSync(path.join(dist,'site',name))),before['site/'+name]);
  fs.cpSync(T10,path.join(dist,'private-fixtures/t10'),{recursive:true});fs.cpSync(T08,path.join(dist,'private-fixtures/t08'),{recursive:true});
  fs.cpSync(path.join(ROOT,'site'),path.join(dist,'reader'),{recursive:true});
  const key=makeKey('package-browser-fixture');jwks=await startJwks({keys:[key]});const team='127.0.0.1:'+jwks.port,aud='package-browser-fixture';
  token=()=>signRS256(key,claims({iss:'https://'+team,aud,email:'package-owner@example.test'}));
  server=await startPagesDev({ACCESS_TEAM_DOMAIN:team,ACCESS_AUD:aud,OWNER_EMAILS:'package-owner@example.test',ACCESS_JWKS_URL_TEST:'http://'+team+'/cdn-cgi/access/certs'},'packages',{dir:dist});
  assert.equal((await fetch(server.base+'/private-fixtures/t10/manifest.json')).status,403);
  for(const record of history)await api('artifacts',record.revisionId,record);
  assert.deepEqual((await api('artifacts')).docs.map(d=>d.data).sort((a,b)=>a.revisionId.localeCompare(b.revisionId)),[...history].sort((a,b)=>a.revisionId.localeCompare(b.revisionId)));
  browser=await chromium.launch({executablePath:CHROME,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
  const context=await browser.newContext({viewport:{width:1280,height:900},acceptDownloads:true,serviceWorkers:'block',extraHTTPHeaders:{'Cf-Access-Jwt-Assertion':token()}});contexts.push(context);
  await context.route('**/*',route=>{const url=new URL(route.request().url());if(url.pathname.includes('network-trap')){networkTraps.push(url.href);return route.abort();}if(url.origin!==server.base){blockedRequests.push(url.href);return route.abort();}return route.continue();});
  const page=await context.newPage();activePage=page;page.on('pageerror',error=>errors.push(error.message));page.on('requestfailed',request=>expectedRequestFailures.push({url:request.url(),error:request.failure()?.errorText}));
  await workbench(page);
  await check('actual saved T10 history is imported, read back, exported and survives Studio reload',async()=>{
    assert.equal(await page.locator('#artifact-history details').count(),history.length);
    const download=page.waitForEvent('download');await page.click('#export-artifacts');await(await download).saveAs(path.join(OUT,'artifact-history-export.json'));
    const exported=read(path.join(OUT,'artifact-history-export.json'));assert.deepEqual(exported.artifacts.sort((a,b)=>a.revisionId.localeCompare(b.revisionId)),[...history].sort((a,b)=>a.revisionId.localeCompare(b.revisionId)));
    await workbench(page);assert.equal(await page.locator('#artifact-history details').count(),history.length);
    return{revisions:history.length,currentRevision:stored.revisionId,artifactDigest:stored.revisionDigest};
  });
  await check('actual generated T10 package starts explicitly with exact lines, layout, fixture label and loaded font',async()=>{
    await page.check('#enable-preview');await page.fill('#preview-config',JSON.stringify({realization:t10Config}));await page.click('#mount-preview');assert.equal(await page.locator('iframe').count(),0);
    await page.getByRole('button',{name:'Realization',exact:true}).click();assert.equal(await page.locator('iframe').count(),0);
    await page.getByRole('button',{name:'Start realization',exact:true}).click();const frame=await realized(page);
    const facts=await frame.evaluate(async()=>{await document.fonts.ready;const a=document.getElementById('realization');return{lines:[...a.querySelectorAll('.line')].map(l=>({text:l.textContent,stanza:l.classList.contains('stanza')})),lang:a.lang,dir:a.dir,script:a.dataset.script,writing:getComputedStyle(a).writingMode,fixture:document.querySelector('h1')?.textContent,fonts:[...document.fonts].map(f=>({family:f.family,status:f.status})),nfd:document.getElementById('nfd-probe').textContent,nfc:document.getElementById('nfc-probe').textContent};});
    assert.deepEqual(facts.lines,expectedRevision.lines.map(l=>({text:l.text,stanza:l.breakBefore})));assert.equal(facts.lang,expectedRevision.language);assert.equal(facts.dir,expectedRevision.layout.direction);assert.equal(facts.script,expectedRevision.script);assert.equal(facts.writing,expectedRevision.layout.writingMode);assert.equal(facts.fixture,expectedRevision.fixture?'Technical fixture — verbatim source; no translation or language adoption':'Private author-supplied realization — not cleared for release');assert.ok(facts.fonts.some(f=>f.family.includes('ajp-scribbles')&&f.status==='loaded'));assert.equal(facts.nfd,'A\u0301');assert.equal(facts.nfc,'Á');
    assert.match(await page.locator('#feature-preview').innerText(),/Private technical preview/);
    assert.equal(await frame.locator('#metadata').evaluate(node=>JSON.parse(node.textContent).fixture),expectedRevision.fixture);
    assert.equal(await page.locator('iframe').getAttribute('sandbox'),'allow-same-origin');assert.equal(await frame.locator('script').count(),0);
    assert.equal(await page.evaluate(()=>document.querySelector('iframe').sandbox.contains('allow-scripts')),false);
    await page.screenshot({path:path.join(OUT,'actual-realization.png')});return{logicalLines:facts.lines.length,fontLoaded:true,sandbox:'allow-same-origin only; scripts forbidden',language:facts.lang,script:facts.script,fixtureFlags:{artifact:stored.fixture,latestRevision:expectedRevision.fixture,package:t10Manifest.fixture},revisionHeading:facts.fixture};
  });
  await check('Escape while focused inside the actual no-scripts realization closes the shared preview and restores trigger focus',async()=>{
    const frame=await realized(page);await frame.locator('#details summary').click();await frame.locator('#details summary').press('Escape');await noFrame(page);
    assert.equal(await page.locator('#feature-preview').getByRole('button',{name:'Realization',exact:true}).evaluate(button=>button===document.activeElement),true);return{closed:true,focusRestored:true};
  });
  await workbench(page);
  await check('T10 source switch, outside dismissal, close and visibility event cancel the actual frame',async()=>{
    await prepare(page,'realization',t10Config);await realized(page);await page.getByRole('button',{name:'Close preview',exact:true}).click();await noFrame(page);
    await prepare(page,'realization',t10Config);await realized(page);await page.locator('h1').first().click();await noFrame(page);
    await prepare(page,'realization',t10Config);await realized(page);await page.selectOption('#version','p001-diary62a-0');await noFrame(page);await page.selectOption('#version',stored.source.versionId);
    await prepare(page,'realization',t10Config);await realized(page);await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));delete document.hidden;});await noFrame(page);
    return{close:true,outside:true,sourceSwitch:true,visibilityEvent:'explicit browser test event; no physical-device claim'};
  });
  await workbench(page,'');
  await check('actual T08 package verifies original image bytes and current geometry before labeled full-image display',async()=>{
    await prepare(page,'regions',t08Config,'');await page.locator('#feature-preview img').waitFor({timeout:15000});
    await page.waitForFunction(()=>{const img=document.querySelector('#feature-preview img');return img?.complete&&img.naturalWidth>0;},null,{timeout:15000});
    const result=await page.locator('#feature-preview img').evaluate(img=>({complete:img.complete,width:img.naturalWidth,height:img.naturalHeight,blob:img.src.startsWith('blob:')}));
    assert.deepEqual(result,{complete:true,width:1135,height:1600,blob:true});assert.match(await page.locator('#feature-preview').innerText(),/no crop is applied/);await page.screenshot({path:path.join(OUT,'actual-region.png')});await page.keyboard.press('Escape');assert.equal(await page.locator('#feature-preview img').count(),0);return result;
  });
  await workbench(page);await seedProbe(page);
  await check('production loaders independently accept the actual API-read head and current source/policy fixtures',async()=>{
    assert.deepEqual(await probe(page,'realization',t10Config),{accepted:true});assert.deepEqual(await probe(page,'regions',t08Config),{accepted:true});return{realization:true,regions:true};
  });
  await check('T10 refuses exact package, source, stored revision, HTML and font mismatches',async()=>{
    const variants=[['manifest bytes',{...structuredClone(t10Config),package:{...t10Config.package,sha256:'sha256:'+'f'.repeat(64)}}],
      ['stored revision',{...structuredClone(t10Config),revisionId:'unselected-revision'}],
      ['combined fixture flag',t10Variant('wrong-fixture-flag',m=>{m.fixture=!m.fixture;})],
      ['fixture flag type',t10Variant('wrong-fixture-type',m=>{m.fixture=[m.fixture];})],
      ['HTML bytes',t10Variant('bad-html-bytes',(_m,f)=>fs.appendFileSync(path.join(f,'index.html'),'changed'),{rehash:false})],
      ['font bytes',t10Variant('bad-font-bytes',(m,f)=>fs.appendFileSync(path.join(f,m.files.find(e=>e.path.startsWith('assets/')).path),'changed'),{rehash:false})],
      ['model-bound HTML',t10Variant('bad-html-content',(_m,f)=>fs.writeFileSync(path.join(f,'index.html'),fs.readFileSync(path.join(f,'index.html'),'utf8').replace('The walls','TECHNICAL MISMATCH')))],
      ['current source',t10Config,'source'],['current stored record',t10Config,'stored'],['current withheld policy',t10Config,'policy']];
    const results=[];for(const[name,descriptor,mutation]of variants){const r=await probe(page,'realization',descriptor,{mutation});assert.equal(r.accepted,false,name);results.push({name,reason:r.message});}return results;
  });
  await check('strict hash/ID/path and complete dependency inventory refuse malformed packages',async()=>{
    const variants=[['array hash',t10Variant('array-hash',m=>{m.files[0].sha256=[m.files[0].sha256];},{rehash:false})],['array ID',t10Variant('array-id',m=>{m.artifactRevisionId=[m.artifactRevisionId];})],
      ['unsafe path',t10Variant('unsafe-path',m=>{m.files[0].path='../outside';},{rehash:false})],['missing dependency',t10Variant('missing-inventory',m=>{m.files=m.files.filter(f=>!f.path.startsWith('assets/'));})],
      ['undeclared dependency',t10Variant('extra-inventory',(m,f)=>{const bytes=Buffer.from('{}');fs.writeFileSync(path.join(f,'extra.json'),bytes);m.files.push({path:'extra.json',bytes:bytes.length,sha256:digest(bytes),mediaType:'application/json'});})]];
    const results=[];for(const[name,descriptor]of variants){const r=await probe(page,'realization',descriptor);assert.equal(r.accepted,false,name);results.push({name,reason:r.message});}
    const raw=await page.evaluate(async()=>{const M=await import('/site/reader-features.js'),p=window.packageProbe,host=document.createElement('div');try{M.mountPrivateFeaturePreview(host,{enabled:true,source:p.source,realization:{source:p.source,url:'/private-fixtures/t10/index.html'},getCurrentSource:()=>p.source,getCurrentPolicy:()=>p.policy,getStoredArtifact:()=>p.stored});return{accepted:true};}catch(error){return{accepted:false,message:error.message};}});
    assert.equal(raw.accepted,false);assert.match(raw.message,/verified package/);results.push({name:'raw HTML fallback',reason:raw.message});return results;
  });
  await check('malformed generated HTML is refused without initiating undeclared resource requests',async()=>{
    const trap=server.base+'/network-trap';const cases=[['image',html=>html.replace('</body>','<img src="'+trap+'/image"></body>')],['iframe',html=>html.replace('</body>','<iframe src="'+trap+'/frame"></iframe></body>')],['stylesheet',html=>html.replace('</head>','<link rel="stylesheet" href="'+trap+'/style"></head>')],['body background',html=>html.replace('<body>','<body background="'+trap+'/background">')],['meta refresh',html=>html.replace('</head>','<meta http-equiv="refresh" content="0;url='+trap+'/refresh"></head>')],['event attribute',html=>html.replace('<body>','<body onload="fetch(\''+trap+'/event\')">')]];
    const results=[];for(const[name,mutate]of cases){const descriptor=t10Variant('malformed-'+name.replaceAll(' ','-'),(_m,f)=>{const file=path.join(f,'index.html');fs.writeFileSync(file,mutate(fs.readFileSync(file,'utf8')));});const result=await probe(page,'realization',descriptor);assert.equal(result.accepted,false,name);assert.match(result.message,/Generated preview|static preview/,name);results.push({name,reason:result.message});}
    await page.evaluate(()=>new Promise(requestAnimationFrame));assert.deepEqual(networkTraps,[]);return results;
  });
  await check('off-origin references and redirects are refused before package activation',async()=>{
    const foreign={...structuredClone(t10Config),package:{...t10Config.package,manifestUrl:'https://package.invalid/manifest.json'}};assert.equal((await probe(page,'realization',foreign)).accepted,false);
    const pattern='**/private-fixtures/redirect/manifest.json';await page.route(pattern,route=>route.fulfill({status:302,headers:{location:server.base+'/private-fixtures/t10/manifest.json'},body:''}));
    try {const redirect={...structuredClone(t10Config),package:{...t10Config.package,manifestUrl:'/private-fixtures/redirect/manifest.json'}};assert.equal((await probe(page,'realization',redirect)).accepted,false);}finally{await page.unroute(pattern);}
    assert.ok(!blockedRequests.some(url=>url.includes('package.invalid')));return{offOriginRefused:true,redirectRefused:true};
  });
  await check('T08 rejects changed declared geometry/media/scope and explicit withholding',async()=>{
    const altered=[['geometry identity',{...structuredClone(t08Config),geometryDigest:'sha256:'+'f'.repeat(64)}],['media identity',{...structuredClone(t08Config),mediaDigest:'sha256:'+'f'.repeat(64)}],
      ['scope',regionVariant('region-public',m=>{m.scope='public-release';m.mayPublish=true;})],['withheld asset',regionVariant('region-withheld',(_m,f)=>{const file=path.join(f,'policy.json'),rules=read(file);rules.withheld_assets=['scan:p/diary1'];fs.writeFileSync(file,encoded(rules));})]];
    const results=[];for(const[name,descriptor]of altered){const result=await probe(page,'regions',descriptor);assert.equal(result.accepted,false,name);results.push({name,reason:result.message});}return results;
  });
  await check('current Studio geometry and media changes refuse an old package with unchanged logical source',async()=>{
    const reviewPath=path.join(dist,'data/review.json'),mapPath=path.join(dist,'data/notes-versions.json'),imagePath=path.join(dist,'img/diary1.jpg');const originals=[reviewPath,mapPath,imagePath].map(file=>[file,fs.readFileSync(file)]);
    try {
      const review=read(reviewPath);review.pages.find(p=>p.id==='diary1').blocks[0].lines[0].box[0]+=.001;const bytes=encoded(review);fs.writeFileSync(reviewPath,bytes);
      const map=read(mapPath);map.provenance.sources.find(s=>s.path==='studio/data/review.json').sha256=digest(bytes).slice(7);fs.writeFileSync(mapPath,encoded(map));
      await workbench(page);assert.equal(await page.locator('#source-status').innerText(),stored.source.sourceFingerprint);await seedProbe(page);let r=await probe(page,'regions',t08Config);assert.equal(r.accepted,false);assert.match(r.message,/geometry/i);
      for(const[file,data]of originals)fs.writeFileSync(file,data);
      fs.appendFileSync(imagePath,'CHANGED TECHNICAL SOURCE BYTES');await workbench(page);await seedProbe(page);r=await probe(page,'regions',t08Config);assert.equal(r.accepted,false);assert.match(r.message,/length|digest|bytes/i);
    }finally{for(const[file,data]of originals)fs.writeFileSync(file,data);await workbench(page);await seedProbe(page);}
    return{coordinateOnly:true,logicalFingerprintUnchanged:true,currentImageBytes:true};
  });
  await check('live policy changes, explicit null fields and source corrections close or refuse saved previews',async()=>{
    await prepare(page,'realization',t10Config);await realized(page);await api('release','p001',{pool:'reserve',publicStatus:'private'});await noFrame(page);
    for(const value of [{pool:null},{publicStatus:null}]){await api('release','p001',value);await workbench(page);await page.check('#enable-preview');await page.fill('#preview-config',JSON.stringify({realization:t10Config}));await page.click('#mount-preview');await page.getByRole('button',{name:'Realization',exact:true}).click();await page.getByRole('button',{name:'Start realization',exact:true}).click();await page.waitForFunction(()=>/Unknown current source policy|Invalid current source policy/.test(document.getElementById('feature-preview').textContent));assert.equal(await page.locator('iframe').count(),0);}
    await api('release','p001',undefined,'DELETE');await workbench(page);await prepare(page,'realization',t10Config);await realized(page);
    await api('reviews','diary1-0-0',{status:'corrected',original:'The walls',text:'TECHNICAL FIXTURE SOURCE CHANGE',at:new Date().toISOString()});await noFrame(page);await page.waitForFunction(()=>document.getElementById('artifact-history').textContent.includes('stale'));
    await api('reviews','diary1-0-0',undefined,'DELETE');await workbench(page);return{policyChange:true,explicitNullsRefused:true,sourceCorrection:true};
  });
  await check('closing during an in-flight package load cancels work without inserting a late frame',async()=>{
    let startedResolve,release;const started=new Promise(resolve=>startedResolve=resolve),gate=new Promise(resolve=>release=resolve);
    const pattern='**/private-fixtures/t10/manifest.json?delayed=1';await page.route(pattern,async route=>{startedResolve();await gate;await route.fulfill({status:200,contentType:'application/json',body:fs.readFileSync(path.join(T10,'manifest.json'))}).catch(()=>{});});
    try {const slow={...structuredClone(t10Config),package:{...t10Config.package,manifestUrl:'/private-fixtures/t10/manifest.json?delayed=1'}};await prepare(page,'realization',slow);await started;await page.keyboard.press('Escape');release();await page.evaluate(()=>new Promise(requestAnimationFrame));await noFrame(page);assert.equal(await page.locator('#feature-preview').getByRole('status').count(),0);}finally{release?.();await page.unroute(pattern);}
    return true;
  });
  await check('actual reader entry consumes the saved T10 package and T08 current DATA geometry with shared cleanup',async()=>{
    const livePolicies=(await api('release')).docs,localRecord=livePolicies.find(d=>d.id===stored.source.pieceId)?.data||{};
    const currentPolicy={pool:Object.hasOwn(localRecord,'pool')?localRecord.pool:'unsorted',visibility:Object.hasOwn(localRecord,'publicStatus')?localRecord.publicStatus:'private'};
    await page.goto(server.base+'/reader/index.html?private-features=1#piece/p001/p001-diary1-0');await page.waitForFunction(()=>window.__jc?.sourceBinding?.()?.sourceFingerprint,{timeout:20000});
    assert.deepEqual(await page.evaluate(()=>__jc.sourceBinding()),stored.source);
    await page.evaluate(async({source,realization,saved,policy})=>{window.realReaderPreview=await __jc.mountFeatures({fixture:true,source,realization,getStoredArtifact:()=>saved,getCurrentPolicy:()=>policy});},{source:stored.source,realization:{...structuredClone(t10Config),package:{...t10Config.package,manifestUrl:server.base+t10Config.package.manifestUrl}},saved:(await api('artifacts')).docs.find(d=>d.id===stored.revisionId).data,policy:currentPolicy});
    await page.getByRole('button',{name:'Realization',exact:true}).click();await page.getByRole('button',{name:'Start realization',exact:true}).click();await page.locator('#private-features iframe').waitFor({timeout:15000});
    await page.evaluate(()=>realReaderPreview.destroy());assert.equal(await page.locator('#private-features iframe').count(),0);
    await page.evaluate(async({source,regions,policy})=>{window.realReaderPreview=await __jc.mountFeatures({fixture:true,source,regions,getCurrentPolicy:()=>policy});},{source:stored.source,regions:{...structuredClone(t08Config),package:{...t08Config.package,manifestUrl:server.base+t08Config.package.manifestUrl}},policy:currentPolicy});
    await page.getByRole('button',{name:'Source regions',exact:true}).click();await page.locator('#private-features img').waitFor({timeout:15000});await page.evaluate(()=>realReaderPreview.destroy());assert.equal(await page.locator('#private-features img').count(),0);
    const readerData=path.join(dist,'reader/data/j.json'),bytes=fs.readFileSync(readerData);try{const data=JSON.parse(bytes);data.pages.find(p=>p.id==='diary1').x[0][2]+=.001;fs.writeFileSync(readerData,encoded(data));await page.reload();await page.waitForFunction(()=>window.__jc?.sourceBinding?.()?.sourceFingerprint);assert.deepEqual(await page.evaluate(()=>__jc.sourceBinding()),stored.source);await page.evaluate(async({source,regions,policy})=>{window.realReaderPreview=await __jc.mountFeatures({fixture:true,source,regions,getCurrentPolicy:()=>policy});},{source:stored.source,regions:{...structuredClone(t08Config),package:{...t08Config.package,manifestUrl:server.base+t08Config.package.manifestUrl}},policy:currentPolicy});await page.getByRole('button',{name:'Source regions',exact:true}).click();await page.waitForFunction(()=>/geometry.*changed|changed.*geometry|differs/i.test(document.getElementById('private-features').textContent));assert.equal(await page.locator('#private-features img').count(),0);}finally{fs.writeFileSync(readerData,bytes);}
    return{realization:true,regions:true,actualReaderGeometryStaleRefusal:true,destroy:true};
  });
  for(const name of protectedPaths)assert.equal(digest(fs.readFileSync(path.join(ROOT,name))),before[name], 'Repository input changed during browser verification: '+name);
  assert.deepEqual(inventory(T10),fixtureInputs.realization);assert.deepEqual(inventory(T08),fixtureInputs.regions);assert.deepEqual(networkTraps,[]);assert.deepEqual(errors,[]);
  pass('protected repository and supplied fixtures remain byte-identical; no undeclared request or browser exception',{blockedRequests,expectedRequestFailures:expectedRequestFailures.length});
  const failed=checks.filter(c=>!c.pass);fs.writeFileSync(path.join(OUT,'acceptance.json'),encoded({status:failed.length?'FAIL':'PASS',observedAt:new Date().toISOString(),checks,errors,networkTraps,blockedRequests,sourceHashes:before,fixtureInputs,browser:await browser.version(),node:process.version,scope:'actual assembled private Studio/local D1 + private reader; no public execution',physicalDevice:'not tested',scratch:SCRATCH}));if(failed.length)process.exitCode=1;
}catch(error){
  if(activePage){try{await activePage.screenshot({path:path.join(OUT,'failure.png'),fullPage:true});fs.writeFileSync(path.join(OUT,'failure-state.txt'),await activePage.locator('body').innerText());}catch{}}
  fs.writeFileSync(path.join(OUT,'acceptance.json'),encoded({status:'FAIL',observedAt:new Date().toISOString(),checks,error:error.stack,errors,networkTraps,blockedRequests,sourceHashes:before,fixtureInputs,scratch:SCRATCH}));console.error(error);process.exitCode=1;
}finally{
  for(const context of contexts)await context.close().catch(()=>{});if(browser)await browser.close();if(server)await server.stop();if(jwks)await jwks.close();
}
