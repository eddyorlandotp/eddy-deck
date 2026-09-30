const assert=require('assert'),fs=require('fs'),path=require('path');
const {start,root,snapshot}=require('./visual_fixture.cjs');
const id=n=>`{0.0.0.00000000}.{12345678-1234-1234-1234-123456789ab${n}}`;
snapshot.audio={outputs:[{id:id(1),name:'Altavoces Realtek'},{id:id(2),name:'Audífonos USB'}],defaultId:id(1),volume:22,mute:false,available:true,error:''};
snapshot.capabilities.audioOutputs=true;snapshot.version='2.2.11-beta.13';
(async()=>{const{browser,p,server}=await start();let checks=[],calls=[],delay=0,fail=false;const record=n=>checks.push(n);const out=path.join(root,'.build/beta13-ui');fs.mkdirSync(out,{recursive:true});
 try{
  p.on('pageerror',e=>{throw e});
  await p.route('**/api/audio',async r=>{const b=r.request().postDataJSON();calls.push(b);if(delay)await new Promise(ok=>setTimeout(ok,delay));if(fail)return r.fulfill({status:400,json:{error:'Salida desconectada'}});if(b.action==='select')snapshot.audio.defaultId=b.endpoint;else snapshot.audio[b.action]=b.value;await r.fulfill({json:{status:'completed',audio:snapshot.audio,message:'Sonido actualizado'}});});
  const slide=()=>p.locator('.system-volume');
  await slide().waitFor();assert.equal(await p.locator('[data-media=volume_up]').count(),0);record('Home uses absolute slider');
  await slide().evaluate(e=>{e.value='31';e.dispatchEvent(new Event('input',{bubbles:true}));});assert.equal(calls.length,0);assert.equal(await p.locator('.system-volume-row output').textContent(),'31%');record('Preview does not flood receiver');
  await slide().dispatchEvent('change');await p.waitForFunction(()=>!audioBusy);assert.equal(calls.length,1);assert.equal(calls[0].value,31);record('Release sends one absolute value');
  delay=160;await slide().evaluate(e=>{for(const v of [20,21,25]){e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}));}});await p.waitForFunction(()=>!audioBusy);assert.deepEqual(calls.slice(1).map(x=>x.value),[20,25]);record('Rapid changes coalesce and preserve order');delay=0;
  const before=calls.length;await slide().evaluate(e=>{e.dataset.epoch='-1';e.value='99';e.dispatchEvent(new Event('change',{bubbles:true}));});await p.waitForTimeout(80);assert.equal(calls.length,before);record('Old PC gesture discarded');
  await p.evaluate(()=>render());await p.locator('.audio-panel .choice-trigger').click();await p.getByRole('option',{name:'Audífonos USB',exact:true}).click();await p.waitForFunction(()=>!audioBusy);assert.equal(calls.at(-1).action,'select');assert.equal(calls.at(-1).expected,id(1));assert.equal(snapshot.audio.defaultId,id(2));record('Styled output picker binds expected previous endpoint');
  await p.locator('[data-action=audio-mute]').click();await p.waitForFunction(()=>!audioBusy);assert.equal(calls.at(-1).value,true);record('Mute is an explicit state');
  await p.locator('#bottom-nav [data-nav=music]').click();await slide().waitFor();assert.equal(await p.locator('[data-media=volume_down]').count(),0);record('Music uses same slider');
  await p.screenshot({path:path.join(out,'music.png'),fullPage:true});
  await slide().dispatchEvent('pointerdown');const handle=await slide().elementHandle();snapshot.audio.volume=19;await p.evaluate(()=>load(true));assert(await handle.evaluate(e=>e.isConnected));await slide().dispatchEvent('pointerup');record('Polling preserves held slider DOM');
  await p.evaluate(()=>render());fail=true;await slide().fill('15');await slide().dispatchEvent('change');await p.waitForFunction(()=>!audioBusy);assert((await p.locator('#toast').textContent()).includes('desconectada'));record('Device disappearance shown without retry');
  fail=false;await p.locator('#bottom-nav [data-nav=home]').click();await p.screenshot({path:path.join(out,'home.png'),fullPage:true});
  // Native offline boot: cached wake access remains independent of failed API.
  await p.addInitScript(()=>{window.EddyNative={request(op,payload,id){const data=op==='bootstrap'?{paired:true,pcId:'pc-test',wakeReady:true,pcs:[{id:'pc-test',name:'Mi PC',active:true}]}:op==='wake'?{status:'sent',powerOnVerified:false,message:'Señal enviada; esperando a la PC.'}:{error:'PC desconectada'};setTimeout(()=>window.eddyResult(id,data),10);}}});
  await p.reload();await p.getByRole('heading',{name:'Reconectando con tu PC.'}).waitFor();await p.getByRole('button',{name:'Encender por LAN',exact:true}).click();await p.getByRole('button',{name:'Enviar señal de encendido',exact:true}).click();await p.waitForFunction(()=>!document.querySelector('#modal').open);assert((await p.locator('#toast').textContent()).includes('esperando'));record('Offline native wake UI works without receiver');
  assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));record('Mobile layout fits viewport');
  const report={passed:true,count:checks.length,checks};fs.writeFileSync(path.join(root,'artifacts/beta13-ui-tests.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
