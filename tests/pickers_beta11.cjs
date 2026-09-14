// Uses real UI and browser input; remote PC is a fixture, not a live media test.
const {start,root}=require('./visual_fixture.cjs'),fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{const {browser,p,server,snapshot}=await start(),checks=[],errors=[];p.on('pageerror',e=>errors.push(e.message));const check=(n,b)=>{assert(b,n);checks.push(n);};
try {
 for(const width of [320,412,915,1440]){
  await p.setViewportSize({width,height:915});await p.evaluate(()=>{page='music';render()});
  const trigger=p.locator('[data-choice-for=media-target]');await trigger.waitFor();
  check('Music select enhanced at '+width,await p.locator('#media-target').evaluate(e=>e.classList.contains('choice-native')));
  check('Old native music selector is actually hidden '+width,await p.locator('#media-target').evaluate(e=>{const c=getComputedStyle(e),r=e.getBoundingClientRect();return c.display==='none'&&r.width===0&&r.height===0}));
  await trigger.click();await p.locator('#choice-dialog').waitFor({state:'visible'});
  check('Music options fit '+width,await p.locator('#choice-dialog').evaluate(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&e.scrollWidth<=e.clientWidth+1}));
  await p.getByRole('option',{name:'AIMP · control directo',exact:true}).click();
  check('Selection changes production media target '+width,await p.evaluate(()=>mediaTarget==='aimp'));
  await p.locator('[data-choice-for=media-target]').click();await p.keyboard.press('Escape');
  await p.waitForFunction(()=>document.activeElement?.dataset.choiceFor==='media-target');
  check('Escape returns to music trigger '+width,await p.evaluate(()=>page==='music'&&!document.querySelector('#modal').open));
 }
 snapshot.media.players=Array.from({length:20},(_,i)=>({id:'session:'+i.toString(16).padStart(32,'0'),name:'Reproductor '+i,state:'paused',controls:{play:true,pause:true,next:true,previous:true,stop:true}}));
 await p.evaluate(s=>{state=s;page='music';render()},snapshot);await p.locator('[data-choice-for=media-target]').click();await p.locator('#choice-dialog input').fill('Reproductor 19');
 check('20 players are searchable',await p.getByRole('option').count()===1);
 await p.getByRole('option').click();check('Exact player chosen',await p.evaluate(()=>mediaTarget==='session:00000000000000000000000000000013'));
 await p.locator('[data-choice-for=media-target]').click();await p.evaluate(()=>load(true));
 check('Refresh does not destroy active music menu',await p.locator('#choice-dialog').isVisible());
 await p.evaluate(()=>window.eddyBack());await p.locator('#choice-dialog').waitFor({state:'hidden'});
 check('Android Back returns to music',await p.evaluate(()=>page==='music'));
 await p.evaluate(()=>{state.media.players=[];render()});await p.locator('[data-choice-for=media-target]').waitFor();
 check('Vanished player remains explicitly unavailable',(await p.locator('[data-choice-for=media-target]').innerText()).includes('no disponible'));
 for(const dest of ['home','library','scenes','music','pc']){await p.evaluate(d=>{page=d;render()},dest);await p.waitForTimeout(30);check('Every page select enhanced: '+dest,await p.locator('#content select').evaluateAll(es=>es.every(e=>e.classList.contains('choice-native')&&e.nextElementSibling?.classList.contains('choice-trigger'))));}
 await p.setViewportSize({width:412,height:915});await p.evaluate(()=>{page='music';render()});await p.locator('[data-choice-for=media-target]').click();
 await p.screenshot({path:path.join(root,'.build/beta11-music-picker.png')});
 check('No uncaught browser errors',errors.length===0);
 fs.writeFileSync(path.join(root,'artifacts/beta11-pickers-tests.json'),JSON.stringify({passed:true,count:checks.length,checks,scope:'Production UI; 20 session fixture; no claim of 20 installed players.'},null,2));console.log('Passed '+checks.length);
}finally{await browser.close();server.close();}})().catch(e=>{console.error(e);process.exitCode=1});
