// Isolated receiver only. This test never sends commands to the installed PC.
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('assert'),http=require('http');
const root=path.resolve(__dirname,'..');
(async()=>{
 let cfg;
 for(let attempt=0;attempt<100;attempt++){
  cfg=JSON.parse(fs.readFileSync(path.join(root,'.build/v2-test-data/test-runtime.json')));
  const ready=await new Promise(resolve=>{const r=http.get('http://127.0.0.1:48089/api/state',{headers:{Authorization:'Bearer '+cfg.localToken}},res=>{res.resume();res.on('end',()=>resolve(res.statusCode===200));});r.setTimeout(2000,()=>r.destroy());r.on('error',()=>resolve(false));});
  if(ready)break;if(attempt===99)throw Error('Fixture authentication did not become ready');
  await new Promise(resolve=>setTimeout(resolve,100));
 }
 assert.equal(cfg.localPort,48089);
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:412,height:915}}),checks=[],errors=[];
 const prefix=process.env.EDDY_TEST_PREFIX||'beta4';if(!/^beta[0-9]+$/.test(prefix))throw Error('Invalid report prefix');
 const output=path.join(root,'artifacts/'+prefix+'-ui-regressions.json');
 page.on('pageerror',e=>errors.push(e.message));
 try {
  await page.addInitScript(t=>sessionStorage.setItem('eddy-token',t),cfg.localToken);
  await page.goto('http://127.0.0.1:48089');
  await page.getByRole('heading',{name:'Hola, Eddy.'}).waitFor();
  await page.evaluate(()=>clearInterval(pollTimer));
  await page.waitForFunction(()=>!loading);
  // Freeze everything except the field under test, so a queue timestamp cannot hide a missed refresh.
  const snapshot=await page.evaluate(()=>structuredClone(state));
  let energy={active:true,error:'',errorCode:null};
  await page.route('**/api/state',r=>r.fulfill({json:{...snapshot,keepAwake:energy}}));
  await page.locator('#bottom-nav [data-nav=pc]').click();await page.evaluate(()=>load(true));
  assert.match(await page.locator('#availability-status').innerText(),/mantiene Windows despierto/);
  energy={active:false,error:'OSError',errorCode:5};await page.evaluate(()=>load(false));
  assert.match(await page.locator('#availability-status').innerText(),/OSError.*código 5/);
  checks.push('Energy failure alone updates visible status without forced reload');
  energy={active:true,error:'',errorCode:null};await page.evaluate(()=>load(false));
  assert.match(await page.locator('#availability-status').innerText(),/mantiene Windows despierto/);
  checks.push('Recovered energy status clears the old failure without forced reload');
  energy={active:false,error:'<img src=x onerror="window.injected=true">',errorCode:5};
  await page.evaluate(()=>load(false));assert.equal(await page.locator('#availability-status img').count(),0);
  assert.equal(await page.evaluate(()=>window.injected),undefined);
  checks.push('Synthetic error text remains text and cannot create executable markup');
  energy={active:true,error:'',errorCode:null};await page.evaluate(()=>load(false));
  await page.evaluate(()=>showModal('Prueba aislada','<input id="unsaved-fixture" value="Conservar edición">'));
  await page.locator('#unsaved-fixture').fill('Mi edición pendiente');
  energy={active:false,error:'OSError',errorCode:87};await page.evaluate(()=>load(false));
  assert.equal(await page.locator('#unsaved-fixture').inputValue(),'Mi edición pendiente');
  await page.locator('[data-action=close-modal]').click();await page.evaluate(()=>load(false));
  assert.match(await page.locator('#availability-status').innerText(),/código 87/);
  checks.push('Polling preserves open form edits and renders deferred state after dialog closes');
  const clockCheck=await page.evaluate(()=>{
   const real=Date.now,realState=state.pending;
   try{
    Date.now=()=>real()+86400000;
    state.pending={id:'synthetic-timing',action:'lock',at:real()/1000+15,remainingSeconds:15};updatePending();
    const first=parseInt(document.querySelector('#pending-banner b').textContent,10);
    Date.now=()=>real()-86400000;pendingClock.until-=5000;updatePending();
    const later=parseInt(document.querySelector('#pending-banner b').textContent,10);
    return {first,later};
   }finally{Date.now=real;state.pending=realState;pendingClock=null;updatePending();}
  });assert.deepEqual(clockCheck,{first:15,later:10});checks.push('Phone countdown uses server remaining time and ignores phone clock changes');
  snapshot.powerError='Fallo de energía sintético';snapshot.events=[{time:'12:34',message:'Evento aislado de prueba'}];await page.evaluate(()=>load(false));
  await page.getByText('Fallo de energía sintético',{exact:true}).waitFor();await page.getByText('Evento aislado de prueba',{exact:true}).waitFor();
  checks.push('Power failure and activity list update when only those fields change');
  snapshot.media={aimp:true,state:'stopped'};await page.locator('#bottom-nav [data-nav=home]').click();await page.evaluate(()=>load(false));
  const stoppedIcon=await page.locator('.mini-music .small-play svg').innerHTML();snapshot.media={aimp:true,state:'playing'};await page.evaluate(()=>load(false));
  assert.notEqual(await page.locator('.mini-music .small-play svg').innerHTML(),stoppedIcon);
  checks.push('Home playback indicator follows media state without visiting Music');
  for(const failFirst of [false,true]){
   const result=await page.evaluate(async failFirst=>{
    const original=api,old=structuredClone(state);let calls=0,release;
    const gate=new Promise(resolve=>release=resolve),fresh=structuredClone(old);
    fresh.name='PC después del guardado';
    api=async path=>{if(path!=='/api/state')throw Error('Only state reads allowed');calls++;if(calls===1){await gate;if(failFirst)throw Error('Injected old poll failure');return old;}return fresh;};
    try{
     const first=load(),forced=load(true),another=load(true);
     release();await Promise.all([first,forced,another]);
     return {calls,name:state.name,loading};
    }finally{api=original;}
   },failFirst);
   assert.deepEqual(result,{calls:2,name:'PC después del guardado',loading:false});
   checks.push(failFirst?'Forced refresh survives an earlier failed poll and resolves after fresh state':'Concurrent forced refreshes coalesce and wait for the post-save snapshot');
  }
  const epochResult=await page.evaluate(async()=>{
   const original=api;let releaseOld,releaseNew,calls=0;
   const oldGate=new Promise(resolve=>releaseOld=resolve),newGate=new Promise(resolve=>releaseNew=resolve);
   const previous=structuredClone(state),current=structuredClone(state);previous.name='Previous PC';current.name='Current PC';
   api=async()=>{calls++;if(calls===1){await oldGate;return previous;}await newGate;return current;};
   try{
    const first=load();connectionEpoch++;loading=false;
    const second=load(true);releaseOld();await first;
    const whileNewPending=loading;releaseNew();await second;
    return {whileNewPending,name:state.name,loading};
   }finally{api=original;}
  });
  assert.deepEqual(epochResult,{whileNewPending:true,name:'Current PC',loading:false});
  checks.push('An old PC response cannot replace current state or clear the newer loading task');
  await page.unroute('**/api/state');await page.evaluate(()=>load(true));
  const commands=[];
  page.on('request',r=>{if(r.method()==='POST'&&/\/api\/(media|power\/)/.test(r.url()))commands.push({path:new URL(r.url()).pathname,body:r.postDataJSON()});});
  await page.locator('#bottom-nav [data-nav=home]').click();
  for(const action of ['volume_down','volume_up','mute']){
   await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/media')&&r.request().method()==='POST'),page.locator(`.quick-controls [data-media=${action}]`).click()]);
   assert.equal(await page.locator('#modal').isVisible(),false);
  }
  assert.deepEqual(commands.filter(c=>c.path==='/api/media').map(c=>[c.body.action,c.body.target]),[['volume_down','system'],['volume_up','system'],['mute','system']]);
  checks.push('Three Home volume controls address Windows directly without monitor prompts');
  await page.locator('#bottom-nav [data-nav=pc]').click();
  await page.locator('[data-power=lock]').click();
  await page.getByRole('heading',{name:'Bloquear tu sesión'}).waitFor();
  assert.equal(commands.filter(c=>c.path==='/api/power/confirm').length,0);
  await page.locator('[data-action=close-modal]').first().click();
  assert.equal(commands.filter(c=>c.path==='/api/power/confirm').length,0);
  checks.push('Opening and closing lock confirmation does not submit a lock');
  await page.locator('[data-power=lock]').click();await page.locator('[data-action=confirm-power]').click();
  await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/power/cancel')),page.locator('[data-action=cancel-power]').click()]);
  assert(commands.some(c=>c.path==='/api/power/prepare'&&c.body.action==='lock'));
  assert.equal(commands.filter(c=>c.path==='/api/power/confirm').length,1);
  assert.equal(commands.filter(c=>c.path==='/api/power/cancel').length,1);
  checks.push('Lock confirmation and cancel reach isolated dry-run receiver once each');
  assert.deepEqual(errors,[]);
  fs.writeFileSync(output,JSON.stringify({passed:true,checks,count:checks.length,javascriptErrors:errors,physicalCommandsSent:0,scope:'isolated dry-run receiver and synthetic energy snapshots'},null,2));
  console.log(JSON.stringify({passed:checks.length}));
 } catch(error) {
  fs.writeFileSync(output,JSON.stringify({passed:false,checks,count:checks.length,javascriptErrors:errors,error:String(error),physicalCommandsSent:0},null,2));throw error;
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
