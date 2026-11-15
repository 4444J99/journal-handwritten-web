#!/usr/bin/env node
// T10 private fixture browser acceptance. Node >=22, no npm dependencies.
// Only a caller-specified local directory is served, on loopback, temporarily.
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import os from 'node:os';
import {spawn} from 'node:child_process';
import {CDP, withBrowser} from './cdp_client.mjs';
import silentBrowser from './silent_browser.cjs'; const {silentChromeArgs} = silentBrowser;

const args = process.argv.slice(2);
const opt = name => args[args.indexOf(name) + 1];
for (const name of ['--pilot', '--chrome', '--out']) if (!args.includes(name) || !opt(name)) throw new Error('Required: ' + name);
const pilot = fs.realpathSync(opt('--pilot'));
const glyphRoot = args.includes('--glyph-root') ? fs.realpathSync(opt('--glyph-root')) : null;
const out = path.resolve(opt('--out'));
if (fs.existsSync(out)) throw new Error('Use a new evidence directory.');
const envelope = JSON.parse(fs.readFileSync(path.join(pilot, 'realization.json'), 'utf8'));
const revision = envelope.realizations[0].revisions.at(-1);
const expectedLines = revision.lines.map(l => l.text);
await fsp.mkdir(out, {recursive: true});
const profile = await fsp.mkdtemp(path.join(os.tmpdir(), 't10-browser-'));
const mime = {'.html':'text/html; charset=utf-8','.otf':'font/otf','.ttf':'font/ttf','.png':'image/png','.json':'application/json'};
const server = http.createServer((req,res) => {
  try {
    let rel = decodeURIComponent(new URL(req.url, 'http://local').pathname).replace(/^\/+/, '') || 'index.html';
    const isGlyph = glyphRoot && rel.startsWith('__glyph/');
    const root = isGlyph ? glyphRoot : pilot;
    if (isGlyph) rel = rel.slice('__glyph/'.length);
    const file = path.resolve(root, rel);
    if (!file.startsWith(root + path.sep) || !fs.statSync(file).isFile() || fs.realpathSync(file) !== file) throw new Error('invalid file');
    res.writeHead(200, {'content-type':mime[path.extname(file)] || 'application/octet-stream','cache-control':'no-store','x-robots-tag':'noindex'});
    fs.createReadStream(file).pipe(res);
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const report = {fixture:true, origin:'loopback-only', generatedAt:new Date().toISOString(), cases:[], limitations:['Chromium only; touch emulation is not a physical iPhone.', 'Latin fixture only; other scripts need separate author input and shaping acceptance.']};
async function launch() {
  const proc = spawn(opt('--chrome'), silentChromeArgs(['--headless=new','--remote-debugging-port=0',`--user-data-dir=${profile}`,'--disable-background-networking','--no-first-run','--disable-extensions','about:blank']), {stdio:['ignore','ignore','pipe']});
  const wsUrl = await new Promise((resolve,reject) => {
    const timer = setTimeout(() => {proc.kill();reject(new Error('Chrome startup timeout'));}, 15000);
    let text = '';
    proc.stderr.on('data',d=> { text+=d; const m=text.match(/DevTools listening on (ws:\/\/\S+)/); if(m){clearTimeout(timer);resolve(m[1]);} });
    proc.once('error',e=>{clearTimeout(timer);reject(e);});
    proc.once('exit',code=>{clearTimeout(timer);reject(new Error('Chrome exited: '+code));});
  });
  return {proc,wsUrl};
}
try {
  await withBrowser({launch, connect:url=>CDP.connect(url)}, async cdp => {
    report.browser = await cdp.send('Browser.getVersion');
    for (const [name,width,height,mobile,scheme] of [
      ['desktop-light',1280,960,false,'light'],['phone-light',390,844,true,'light'],
      ['desktop-dark',1280,960,false,'dark'],['phone-dark',390,844,true,'dark']]) {
      const {browserContextId} = await cdp.send('Target.createBrowserContext');
      const {targetId} = await cdp.send('Target.createTarget',{url:'about:blank',browserContextId});
      const {sessionId} = await cdp.send('Target.attachToTarget',{targetId,flatten:true});
      const errors=[],requests=[];
      const handler=m=>{if(m.sessionId !== sessionId)return;
        if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);
        if(m.method==='Network.requestWillBeSent')requests.push(m.params.request.url);
      };
      cdp.on(handler);
      const send=(method,params={})=>cdp.send(method,params,sessionId);
      const evaluate=async expression=>{
        const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
        if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));
        return r.result.value;
      };
      await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('DOM.enable');await send('CSS.enable');
      await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile});
      await send('Emulation.setTouchEmulationEnabled',{enabled:mobile});
      await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:scheme}]});
      await send('Page.navigate',{url:origin+'/index.html'});
      await evaluate(`new Promise((resolve,reject)=>{let n=0;const timer=setInterval(()=>{if(document.querySelector('#realization')){clearInterval(timer);resolve(true);}else if(++n>100){clearInterval(timer);reject(new Error('preview timeout'));}},30);})`);
      await evaluate(`document.fonts.load('32px ajp-scribbles').then(()=>document.fonts.ready).then(()=>true)`);
      const observation=await evaluate(`(()=>{const a=document.querySelector('#realization'),s=getComputedStyle(a);return {
        lines:[...a.querySelectorAll('.line')].map(l=>l.textContent),
        lineCount:a.querySelectorAll('.line').length,language:a.lang,script:a.dataset.script,direction:s.direction,writingMode:s.writingMode,
        overflow:document.documentElement.scrollWidth>innerWidth+1,
        detailsClosed:!document.querySelector('#details').open,
        closedControlClear:[...a.querySelectorAll('.line')].every(l=>{const r=l.getBoundingClientRect(),b=document.querySelector('#details').getBoundingClientRect();return r.bottom<=b.top||r.top>=b.bottom||r.right<=b.left||r.left>=b.right;}),
        fontLoaded:[...document.fonts].some(f=>f.family==='ajp-scribbles'&&f.status==='loaded'),
        background:getComputedStyle(document.body).backgroundColor,
        fallbackRunCount:a.querySelectorAll('.fallback').length};})()`);
      const checks={sourceLinesExact:JSON.stringify(observation.lines)===JSON.stringify(expectedLines),lineCount:observation.lineCount===expectedLines.length,
        language:observation.language===revision.language,script:observation.script===revision.script,
        direction:observation.direction===revision.layout.direction,writingMode:observation.writingMode===revision.layout.writingMode,
        noHorizontalOverflow:!observation.overflow,detailsHidden:observation.detailsClosed,closedControlClear:observation.closedControlClear,fontLoaded:observation.fontLoaded};
      delete observation.lines;
      const doc=await send('DOM.getDocument');
      const first=await send('DOM.querySelector',{nodeId:doc.root.nodeId,selector:'#realization .line'});
      const fontUse=await send('CSS.getPlatformFontsForNode',{nodeId:first.nodeId});
      checks.authorFontUsed=fontUse.fonts.some(f=>f.isCustomFont && f.glyphCount>0);
      const metrics=await send('Page.getLayoutMetrics');
      const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height:Math.ceil(metrics.cssContentSize.height),scale:1}});
      await fsp.writeFile(path.join(out,name+'.png'),Buffer.from(shot.data,'base64'));
      await evaluate(`document.querySelector('#details').open=true;true`);
      // details content was display:none. Let layout and paint realize its font
      // runs before asking CDP for actual platform font usage.
      await evaluate(`new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))).then(()=>true)`);
      const unicode=await evaluate(`(()=>{const nfd=document.querySelector('#nfd-probe'),nfc=document.querySelector('#nfc-probe'),c=document.createElement('canvas').getContext('2d');c.font=getComputedStyle(nfd).font;return {nfd:[...nfd.textContent].map(c=>c.codePointAt(0)),nfc:[...nfc.textContent].map(c=>c.codePointAt(0)),nfdWidth:c.measureText(nfd.textContent).width,nfcWidth:c.measureText(nfc.textContent).width,nfdTextNodes:nfd.childNodes.length,nfdDirection:getComputedStyle(nfd).direction};})()`);
      checks.combiningSequencePreserved=JSON.stringify(unicode.nfd)==='[65,769]'&&JSON.stringify(unicode.nfc)==='[193]';
      checks.combiningRunIntact=unicode.nfdTextNodes===1&&Math.abs(unicode.nfdWidth-unicode.nfcWidth)<0.1;
      const probe=await send('DOM.querySelector',{nodeId:doc.root.nodeId,selector:'#nfd-probe'});
      const fallbackUse=await send('CSS.getPlatformFontsForNode',{nodeId:probe.nodeId});
      checks.fallbackUsed=fallbackUse.fonts.length>0&&fallbackUse.fonts.every(f=>!f.isCustomFont);
      checks.noExternalRequests=requests.every(url=>url.startsWith(origin+'/')||url.startsWith('data:'));
      checks.noRuntimeErrors=errors.length===0;
      const panelShot=await send('Page.captureScreenshot',{format:'png'});
      if(name==='desktop-light')await fsp.writeFile(path.join(out,'unicode-and-provenance.png'),Buffer.from(panelShot.data,'base64'));
      report.cases.push({name,viewport:{width,height,mobile,scheme},checks,observation,fontUse,fallbackUse,unicode,errors,pass:Object.values(checks).every(Boolean)});
      await cdp.send('Target.disposeBrowserContext',{browserContextId});
    }
    if (glyphRoot) {
      const expected = JSON.parse(fs.readFileSync(path.join(glyphRoot, 'glyph-report.json'), 'utf8'));
      report.glyphCases = [];
      for (const [name, relative] of [['capture-sheet','capture-sheet.html'],['glyph-proof','glyph-proof/preview.html']]) {
        const {browserContextId} = await cdp.send('Target.createBrowserContext');
        const {targetId} = await cdp.send('Target.createTarget',{url:'about:blank',browserContextId});
        const {sessionId} = await cdp.send('Target.attachToTarget',{targetId,flatten:true});
        const requests=[], errors=[];
        cdp.on(m=>{if(m.sessionId!==sessionId)return;
          if(m.method==='Network.requestWillBeSent') requests.push(m.params.request.url);
          if(m.method==='Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.text);});
        const send=(method,params={})=>cdp.send(method,params,sessionId);
        const evaluate=async expression=>{
          const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
          if(result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
          return result.result.value;
        };
        await send('Page.enable');await send('Runtime.enable');await send('Network.enable');
        await send('Emulation.setDeviceMetricsOverride',{width:1100,height:1000,deviceScaleFactor:1,mobile:false});
        await send('Page.navigate',{url:origin+'/__glyph/'+relative});
        await evaluate(`new Promise((resolve,reject)=>{let n=0;const t=setInterval(()=>{if(document.querySelector('tbody')){clearInterval(t);resolve(true);}else if(++n>100){clearInterval(t);reject(new Error('glyph preview timeout'));}},30);})`);
        await evaluate(`document.fonts.ready.then(()=>Promise.all([...document.images].map(i=>i.decode()))).then(()=>true)`);
        const observation=await evaluate(`(()=>({rows:document.querySelectorAll('tbody tr').length,slots:document.querySelectorAll('.slot').length,blankSlots:[...document.querySelectorAll('.slot')].every(e=>e.textContent===''),images:[...document.images].map(i=>({loaded:i.complete&&i.naturalWidth>0,width:i.naturalWidth,height:i.naturalHeight})),overflow:document.documentElement.scrollWidth>innerWidth+1,sourceHashPresent:document.body.textContent.includes('${expected.sourceFingerprint.slice(7)}'),privateLabel:document.body.textContent.includes('PRIVATE')}))()`);
        const checks={noHorizontalOverflow:!observation.overflow,sourceHashPresent:observation.sourceHashPresent,privateLabel:observation.privateLabel,noExternalRequests:requests.every(u=>u.startsWith(origin+'/')),noRuntimeErrors:errors.length===0};
        if(name==='capture-sheet') Object.assign(checks,{repertoire:observation.rows===expected.sheetDistinctSequences,threeBlankSamples:observation.slots===expected.sheetDistinctSequences*3&&observation.blankSlots});
        else Object.assign(checks,{oneDeclaredGlyph:observation.rows===1,cropLoaded:observation.images.length===1&&observation.images.every(i=>i.loaded)});
        const metrics=await send('Page.getLayoutMetrics');
        const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:1100,height:Math.ceil(metrics.cssContentSize.height),scale:1}});
        await fsp.writeFile(path.join(out,name+'.png'),Buffer.from(shot.data,'base64'));
        report.glyphCases.push({name,checks,observation,errors,pass:Object.values(checks).every(Boolean)});
        await cdp.send('Target.disposeBrowserContext',{browserContextId});
      }
    }
  });
} finally {
  await new Promise(resolve=>server.close(resolve));
  await fsp.rm(profile,{recursive:true,force:true});
}
report.pass=report.cases.length===4&&report.cases.every(c=>c.pass)&&(!report.glyphCases||report.glyphCases.every(c=>c.pass));
await fsp.writeFile(path.join(out,'browser.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({pass:report.pass,cases:[...report.cases,...(report.glyphCases||[])].map(c=>({name:c.name,pass:c.pass,failed:Object.entries(c.checks).filter(([,v])=>!v).map(([k])=>k)}))},null,2));
process.exitCode=report.pass?0:1;
