const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..');
const reportPrefix=process.env.EDDY_TEST_PREFIX||'beta2';if(!/^beta[0-9]+$/.test(reportPrefix))throw Error('Invalid report prefix');
(async()=>{
 const config=JSON.parse(fs.readFileSync(path.join(root,'.build/v2-test-data/test-runtime.json'))),base='http://127.0.0.1:'+config.localPort;
 const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage({viewport:{width:1280,height:1000}}),errors=[],checks=[];
 page.on('pageerror',e=>errors.push(e.message));const pass=s=>checks.push(s);
 await page.addInitScript(t=>sessionStorage.setItem('eddy-token',t),config.localToken);await page.goto(base);await page.getByRole('heading',{name:'Hola, Eddy.'}).waitFor();
 assert(await page.evaluate(()=>EDDY_CLIENT_VERSION===state.version));assert.equal(await page.getByText('Las versiones son distintas',{exact:true}).count(),0);pass('Generated client version matches the receiver before release');
 await page.locator('[data-action=edit-card]').first().click();await page.locator('#card-form [name=ifOpen]').selectOption('launch');await page.locator('#card-form [type=submit]').click();await page.locator('#modal').waitFor({state:'hidden'});
 await page.locator('[data-action=edit-card]').first().click();assert.equal(await page.locator('#card-form [name=ifOpen]').inputValue(),'launch');await page.locator('[data-action=close-modal]').first().click();pass('Card existing-window policy persisted and reloaded');
 await page.locator('#side-nav [data-nav=scenes]').click();await page.locator('.heading [data-action=new-scene]').click();await page.locator('#routine-name').fill('Beta2 UI '+Date.now());await page.locator('[data-action=add-step]').click();await page.locator('#step-form [name=ifOpen]').selectOption('launch');await page.locator('#step-form [type=submit]').click();await page.locator('[data-action=edit-step]').click();assert.equal(await page.locator('#step-form [name=ifOpen]').inputValue(),'launch');await page.locator('#step-form [type=submit]').click();await page.locator('#routine-form [type=submit]').click();await page.locator('#modal').waitFor({state:'hidden'});pass('Routine editor preserves existing-window policy');
 await page.locator('[data-action=queue-pause]').click();await page.getByText('Cola en pausa',{exact:true}).waitFor();await page.locator('[data-action=queue-pause]').click();await page.getByText('Cola activa',{exact:true}).waitFor();pass('Pause and resume integrated with real queue API');
 await page.locator('#side-nav [data-nav=home]').click();await page.locator('[data-action=check-installation]').click();await page.getByRole('heading',{name:'Comprobación de Eddy Deck'}).waitFor();await page.locator('[data-action=close-modal]').first().click();await page.locator('[data-action=repair-files]').click();assert(await page.getByText('No reinicia Windows ni cierra tus otras aplicaciones.',{exact:false}).isVisible());await page.locator('[data-action=confirm-repair-files]').click();await page.locator('#modal').waitFor({state:'hidden'});pass('File verification and repair confirmation use dry-run API');
 await page.evaluate(()=>localStorage.setItem('eddy-pending-local','broken json'));await page.locator('[data-action=check-installation]').click();await page.getByText(/No se puede leer el registro de órdenes/).waitFor();await page.locator('[data-action=pending-records]').click();await page.locator('[data-action=clear-pending-records]').click();assert.equal(await page.evaluate(()=>localStorage.getItem('eddy-pending-local')),null);pass('Corrupt local receipt record blocks new commands and has explicit recovery');
 await page.context().setOffline(true);await page.waitForTimeout(4500);await page.locator('[data-action=user-manual]').click();await page.getByRole('heading',{name:'6. Crear una rutina',exact:true}).waitFor();pass('Full manual remains available without a PC connection');await page.locator('[data-action=close-modal]').first().click();await page.context().setOffline(false);await page.locator('#reconnect-button').click();
 // Window UI fixtures are deliberately synthetic; OS behavior is tested separately.
 await page.route('**/api/state',async route=>{const r=await route.fetch(),s=await r.json();s.windows=[{id:'ui-fixture',title:'Ventana de prueba',process:'EddyDeckTestWindow.exe',monitor:s.monitors[0]?.id,minimized:false,maximized:false,protected:false,appIds:[]}];await route.fulfill({response:r,json:s});});
 await page.locator('#side-nav [data-nav=pc]').click();await page.locator('[data-action=refresh-windows]').click();await page.locator('[data-action=window-controls][data-id=ui-fixture]').click();await page.locator('[data-action=window-close]').click();await page.getByRole('button',{name:'Pedir cierre'}).waitFor();await page.locator('[data-action=close-modal]').first().click();pass('Normal close has separate confirmation');
 for(const width of [1280,412,320]){await page.setViewportSize({width,height:915});await page.screenshot({path:path.join(root,`.build/${reportPrefix}-pc-${width}.png`),fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);pass(`Responsive layout ${width}px`);}
 await page.unroute('**/api/state');await page.route('**/api/state',async route=>{const r=await route.fetch(),s=await r.json();s.version='2.1.0-beta.1';delete s.capabilities;await route.fulfill({response:r,json:s});});
 await page.locator('#bottom-nav [data-nav=home]').click();await page.evaluate(()=>load(true));await page.getByText('Las versiones son distintas',{exact:true}).waitFor();assert(await page.locator('[data-action=check-installation]').isDisabled());pass('Older PC shows version mismatch and disables unsupported file controls');
 await page.unroute('**/api/state');await page.route('**/api/state',async route=>{const r=await route.fetch(),s=await r.json();s.protocolVersion=99;await route.fulfill({response:r,json:s});});await page.evaluate(()=>load(true));await page.locator('#bottom-nav [data-nav=music]').click();await page.locator('[data-media=next]').click();await page.getByText(/Esta PC usa otra versión del protocolo/).waitFor();pass('Unknown protocol blocks commands before transport');
 await page.unroute('**/api/state');await page.evaluate(()=>load(true));
 const receipts=await page.evaluate(async()=>{
   const original=transport,storage='eddy-pending-local',waiters=[];localStorage.removeItem(storage);
   const pending=()=>JSON.parse(localStorage.getItem(storage)||'{}');
   try{
     transport=(path,body)=>path==='/api/operations/status'?Promise.resolve({status:'inProgress'}):new Promise(resolve=>waiters.push({resolve,id:body.requestId}));
     const a=api('/api/media',{action:'next'}),b=api('/api/media',{action:'next'});
     if(waiters[0].id!==waiters[1].id)throw Error('Duplicate requests did not share receipt');
     waiters[0].resolve({status:'ok'});await a;
     const c=api('/api/media',{action:'next'}),newId=waiters[2].id;
     waiters[1].resolve({status:'ok'});await b;
     if(Object.values(pending())[0]!==newId)throw Error('Late response removed newer receipt');
     waiters[2].resolve({status:'ok'});await c;
     for(const status of [409,500]){
       transport=(path)=>path==='/api/operations/status'?Promise.resolve({status:'inProgress'}):Promise.reject(Object.assign(new Error('Still uncertain'),{server:true,status}));
       try{await api('/api/media',{action:'next'});}catch(_){}
       if(Object.keys(pending()).length!==1)throw Error('Uncertain server response discarded receipt '+status);
       localStorage.removeItem(storage);
     }
     return true;
   }finally{transport=original;localStorage.removeItem(storage);}
 });assert(receipts);pass('Late duplicate response cannot remove a newer action receipt');pass('In-progress and uncertain server responses retain the same receipt');
 const pairing=await browser.newPage({viewport:{width:412,height:915}});pairing.on('pageerror',e=>errors.push(e.message));await pairing.addInitScript(()=>{window.EddyNative={request:(op,json,id)=>setTimeout(()=>window.eddyResult(id,{paired:false,candidate:{host:'192.168.1.55',fingerprint:'a'.repeat(64),fromLink:true}}),0)};});await pairing.goto(base);await pairing.locator('[name=verified]').waitFor();assert(!(await pairing.locator('[name=verified]').isChecked()));pass('A pairing link still requires explicit fingerprint verification');
 assert.deepEqual(errors,[]);await browser.close();fs.writeFileSync(path.join(root,`artifacts/${reportPrefix}-ui-tests.json`),JSON.stringify({checks,count:checks.length,javascriptErrors:errors,windows:'synthetic fixture; see separate live Windows tests'},null,2));console.log(JSON.stringify({passed:checks.length,javascriptErrors:errors}));
})().catch(e=>{console.error(e);process.exit(1)});
