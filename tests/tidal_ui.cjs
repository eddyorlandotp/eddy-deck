// Production HTML and JS on an isolated server. Media transport is synthetic.
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('assert'),cp=require('child_process');
const root=path.resolve(__dirname,'..');
(async()=>{
 const cfg=JSON.parse(fs.readFileSync(path.join(root,'.build/v2-test-data/test-runtime.json')));
 const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:412,height:915}}),checks=[],errors=[],sent=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.addInitScript(t=>sessionStorage.setItem('eddy-token',t),cfg.localToken);
  await page.goto('http://127.0.0.1:48089');await page.getByRole('heading',{name:'Hola, Eddy.'}).waitFor();
  await page.evaluate(()=>clearInterval(pollTimer));await page.waitForFunction(()=>!loading);
  let snapshot=await page.evaluate(()=>structuredClone(state));snapshot.media={aimp:false,state:'unknown',autoTarget:'tidal',tidal:{available:true,running:true,state:'playing'}};
  await page.route('**/api/state',r=>r.fulfill({json:snapshot}));
  await page.route('**/api/media',r=>{sent.push(r.request().postDataJSON());return r.fulfill({json:{status:'completed',message:'Fixture only'}})});
  await page.evaluate(()=>load(true));
  assert.equal(await page.locator('.mini-music strong').innerText(),'TIDAL');checks.push('Home shows the automatically selected TIDAL player');
  await page.locator('.mini-music button').click();assert.equal(sent.at(-1).action,'pause');assert.equal(sent.at(-1).target,'system');checks.push('Home sends explicit pause when TIDAL is playing');
  await page.locator('#bottom-nav [data-nav=music]').click();
  assert.deepEqual(await page.locator('#media-target option').evaluateAll(xs=>xs.map(x=>x.value)),['system','tidal','aimp']);checks.push('All three player options are valid HTML');
  await page.locator('.large-play').click();assert.equal(sent.at(-1).action,'pause');checks.push('Music automatic sends explicit pause');
  await page.locator('#media-target').selectOption('tidal');await page.locator('.large-play').click();assert.equal(sent.at(-1).target,'tidal');assert.equal(sent.at(-1).action,'pause');checks.push('Music direct sends pause to TIDAL');
  snapshot.media.tidal.state='paused';await page.evaluate(()=>load(true));await page.locator('.large-play').click();assert.equal(sent.at(-1).action,'play');checks.push('Paused TIDAL button sends play instead of a blind toggle');
  await page.locator('[data-media=stop]').click();assert.equal(sent.at(-1).action,'stop');assert.equal(await page.locator('[data-media=stop]').innerText(),'Pausar');checks.push('Stop is visibly labeled pause for TIDAL');
  await page.locator('[data-media=mute]').click();assert.equal(sent.at(-1).target,'system');assert.match(await page.locator('.player').innerText(),/Volumen general de Windows/);checks.push('Mute explicitly targets Windows and displays its actual scope');
  const label=await page.evaluate(()=>stepLabel({type:'media',target:'tidal',action:'mute'}));assert.match(label,/Windows/);assert(!label.includes('TIDAL'));checks.push('Routine mute label describes Windows rather than promising TIDAL-only mute');
  assert.deepEqual(errors,[]);checks.push('No JavaScript runtime errors');
  const sourceHashes=JSON.parse(cp.execFileSync(path.join(root,'.build/venv/Scripts/python.exe'),['-c','import json;from scripts.package_evidence import product_sources;print(json.dumps(product_sources()))'],{cwd:root,encoding:'utf8'}));
  fs.writeFileSync(path.join(root,'artifacts/beta6-tidal-ui-tests.json'),JSON.stringify({passed:true,count:checks.length,checks,sourceHashes,scope:'Production interface in Edge, isolated transport. Physical phone test is separate.'},null,2));console.log(JSON.stringify({passed:true,count:checks.length}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
