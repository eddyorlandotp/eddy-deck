'use strict';
// Window layouts, durable requests, routines and native multi-PC controls.
let connectionEpoch=0,routineDraft=[],routineName='',routineId='',routinePolicy='stop';
const modeNames={keep:'Conservar tamaño',windowed:'Modo ventana',maximized:'Maximizada',minimized:'Minimizada','left-half':'Mitad izquierda','right-half':'Mitad derecha'};
const jobNames={queued:'En cola',running:'En curso',completed:'Completada',failed:'Falló',partial:'Con avisos',cancelled:'Cancelada',interrupted:'Interrumpida'};
sections[2][1]='Rutinas';
function layoutFields(value={},ask=false){
  const choices=[['keep','Como la dejé'],...(ask?[['ask','Preguntarme al abrir']]:[]),['left','Izquierda'],['right','Derecha'],['vertical','Vertical'],['primary','Principal'],...(state?.monitors||[]).map(m=>[m.id,m.label+' · pantalla fija'])];
  if(value.monitor&&!choices.some(c=>c[0]===value.monitor))choices.push([value.monitor,'Pantalla guardada · desconectada']);
  return `<div class="layout-fields"><label class="field"><span>Pantalla</span><select name="monitor">${choices.map(([id,label])=>`<option value="${esc(id)}" ${(value.monitor||'keep')===id?'selected':''}>${esc(label)}</option>`).join('')}</select></label><label class="field"><span>Ventana</span><select name="mode">${Object.entries(modeNames).map(([id,label])=>`<option value="${id}" ${(value.mode||'keep')===id?'selected':''}>${label}</option>`).join('')}</select></label><label class="field full"><span>Si esa pantalla no está disponible</span><select name="missing"><option value="stop" ${value.missing!=='primary'?'selected':''}>Detener y avisarme</option><option value="primary" ${value.missing==='primary'?'selected':''}>Usar la pantalla principal</option></select></label></div>`;
}
function activationField(value='front'){
  if(!state?.capabilities?.launchForeground)return '<p class="hint">Actualiza Eddy Deck en Windows para elegir si la app aparece al frente.</p>';
  return `<label class="field full"><span>Al abrir la aplicación</span><select name="activation"><option value="front" ${value!=='windows'?'selected':''}>Traer al frente</option><option value="windows" ${value==='windows'?'selected':''}>Dejar que Windows decida</option></select></label><p class="hint">También se aplica si ya estaba abierta. No la fija siempre encima. Si eliges Minimizada, se conserva minimizada.</p>`;
}
function readActivation(form){return new FormData(form).get('activation')||'front';}
function readLayout(form){const data=new FormData(form);return {monitor:data.get('monitor')||'keep',mode:data.get('mode')||'keep',missing:data.get('missing')||'stop'};}
const originalCardEditor=cardEditor;
cardEditor=function(app,card){originalCardEditor(app,card);$('#card-form .modal-actions').insertAdjacentHTML('beforebegin',`<details class="pairing-details" ${card?.layout?.monitor&&card.layout.monitor!=='keep'?'open':''}><summary>Pantalla y tamaño al abrir</summary>${layoutFields(card?.layout,true)}${activationField(card?.activation)}<p class="hint">Maximizar ocupa la pantalla dejando los controles de Windows. El modo de pantalla completa de un juego se configura dentro del juego.</p></details>`);};

async function transport(path,body,context){
  if(native)return nativeCall('api',{path,method:body===undefined?'GET':'POST',body,pcId:context});
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),12000);
  try{const r=await fetch(path,{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+token,...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal});const value=await r.json();if(!r.ok){const err=new Error(value.error||'La PC rechazó la acción.');err.server=true;err.status=r.status;throw err;}return value;}finally{clearTimeout(timeout);}
}
api=async function(path,body){
  if(body!==undefined&&state?.protocolVersion&&state.protocolVersion!==2)throw Error('Esta PC usa otra versión del protocolo. Actualiza la app desde tu respaldo antes de enviar órdenes.');
  if(native&&!bootstrap?.pcId)bootstrap=await nativeCall('bootstrap');
  const context=native?bootstrap?.pcId:'local',epoch=connectionEpoch;
  if(path==='/api/cards/save'&&$('#card-form'))body={...body,layout:readLayout($('#card-form')),activation:readActivation($('#card-form')),ifOpen:new FormData($('#card-form')).get('ifOpen')||'reuse'};
  let pending={},key='',storage='eddy-pending-'+context;
  if(body!==undefined){
    try{pending=JSON.parse(localStorage.getItem(storage)||'{}');if(!pending||Array.isArray(pending)||typeof pending!=='object')throw Error();}catch(_){throw Error('No se puede leer el registro de órdenes del celular. Abre Reparación y ayuda para revisarlo antes de enviar otra orden.');}
    key=JSON.stringify([path,body]);
    if(!pending[key]&&Object.keys(pending).length>=100)throw Error('Hay demasiadas órdenes sin resultado conocido. Revisa la actividad y el registro en Reparación y ayuda.');
    body={...body,requestId:pending[key]||requestId()};pending[key]=body.requestId;
    try{localStorage.setItem(storage,JSON.stringify(pending));}catch(_){throw Error('No se pudo guardar la orden antes de enviarla. Libera espacio en el celular.');}
  }
  const remove=()=>{if(!key)return;try{let latest=JSON.parse(localStorage.getItem(storage)||'{}');if(latest[key]===body.requestId)delete latest[key];localStorage.setItem(storage,JSON.stringify(latest));}catch(_){toast('La acción tuvo respuesta, pero no se pudo limpiar su registro local. Revisa la actividad antes de repetirla.');}};
  const ensureContext=()=>{if(epoch!==connectionEpoch)throw Object.assign(new Error('La orden pertenece a la PC anterior. Revisa su actividad allí.'),{staleContext:true});};
  try{
    const result=await transport(path,body,context);remove();
    ensureContext();return result;
  }catch(error){
    ensureContext();
    if(error.server&&error.status!==409&&!(error.status>=500))remove();
    else if(key&&epoch===connectionEpoch){
      try{const receipt=await transport('/api/operations/status',{id:body.requestId},context);ensureContext();if(receipt.status==='received'){remove();return receipt.result;}if(receipt.status==='failed'){remove();throw Object.assign(new Error(receipt.result.error),{server:true});}}catch(check){if(check.server||check.staleContext)throw check;ensureContext();}
    }
    throw error;
  }
};

let refreshTask=null;
load=function(force=false){
  const epoch=connectionEpoch;
  if(refreshTask?.epoch===epoch){refreshTask.force ||= force;return refreshTask.promise;}
  const task={epoch,force,promise:null};refreshTask=task;loading=true;
  task.promise=(async()=>{try{do{
    const requestedForce=task.force;task.force=false;
    let next;
    try{next=await api('/api/state');}
    catch(error){if(task.force&&epoch===connectionEpoch)continue;throw error;}
    if(epoch!==connectionEpoch)return;
    // A save finished during this request. Discard its possibly older snapshot
    // and coalesce all forced refreshes into one fresh request before resolving.
    if(task.force)continue;
    const first=!state;state=next;online=true;
    const sig=JSON.stringify([next.version,next.protocolVersion,next.capabilities,next.keepAwake,next.profile,next.apps,next.name,next.scanned,next.scanning,next.warnings,next.monitors,next.displayWarning,next.queue,next.installation,next.startup,next.internet,['home','music'].includes(page)?next.media:null,page==='pc'?[next.windows,next.events,next.powerError]:null,next.jobs,page==='settings'?next.devices:null]);
    // Do not mark a snapshot as rendered while a dialog is preserving an edit.
    // The next poll after closing it must still apply the deferred snapshot.
    if((requestedForce||first||sig!==signature)&&!$('#modal').open&&!$('#choice-dialog')?.open&&!document.activeElement?.matches('input,select,textarea')){render();signature=sig;}
    updatePending();
  }while(task.force&&epoch===connectionEpoch);
  }catch(error){if(epoch!==connectionEpoch)return;online=false;if(!state){renderPairing();if(token||bootstrap?.paired)toast(error.message);}}
  finally{if(refreshTask===task){refreshTask=null;if(epoch===connectionEpoch){loading=false;updateConnection();}}}})();
  return task.promise;
};

function monitorMap(){
  const list=state.monitors||[];if(!list.length)return '<p class="hint">Windows no reporta pantallas en este momento.</p>';
  return `<div class="monitor-map">${list.map(m=>`<div class="monitor-shape ${m.vertical?'vertical':''}"><div>${icon('pc')}<strong>${esc(m.label)}</strong><small>${m.bounds[2]-m.bounds[0]} × ${m.bounds[3]-m.bounds[1]}</small></div></div>`).join('')}</div>`;
}
function jobList(){return `<div class="section-bar"><h2>Cola y resultados</h2></div><p class="hint">Las aperturas y rutinas se ejecutan una por una. La música responde por separado.</p>${(state.jobs||[]).slice(0,12).map(j=>`<article class="job-row"><div><strong>${esc(j.name)}</strong><small>${jobNames[j.status]||esc(j.status)} · paso ${j.step}/${j.total}</small><p>${esc(j.message)}</p>${j.status==='failed'&&j.results?.length===j.step&&j.step<j.total?`<p class="notice">El paso ${j.step} falló. ${j.total-j.step===1?'El paso siguiente no se ejecutó':'Los '+(j.total-j.step)+' pasos siguientes no se ejecutaron'} porque la rutina se detuvo.</p>`:''}${j.results?.length?`<details><summary>Ver pasos</summary>${j.results.map((r,i)=>`<p>${i+1}. ${esc(r.message||r.status)}</p>`).join('')}</details>`:''}</div>${['queued','running'].includes(j.status)?`<button class="secondary" data-action="cancel-job" data-id="${esc(j.id)}">Cancelar</button>`:''}</article>`).join('')||'<p class="hint">Aquí aparecerá el resultado de cada apertura o rutina.</p>'}`;}
const originalRender=render;
render=function(){
  originalRender();if(!state)return;
  $('#version-label').textContent='v'+state.version;
  if(native&&!$('#pc-picker'))$('#settings-button').insertAdjacentHTML('beforebegin','<button id="pc-picker" class="text-button" data-action="manage-pcs">'+icon('pc')+'Mis PCs</button>');
  if(page==='home'){
    const small=$('.connection-card small');if(small)small.textContent=state.apps.length+' apps · '+(native?(bootstrap?.host?.startsWith('100.')?'internet privado':'conexión segura'):'Windows');
    const running=(state.jobs||[]).find(j=>['queued','running'].includes(j.status));
    if(running)$('#content').insertAdjacentHTML('beforeend',`<div class="notice"><strong>${esc(running.name)}</strong> · ${jobNames[running.status]} <button class="text-button" data-nav="pc">Ver actividad</button></div>`);
  }
  if(page==='scenes'){
    $('#content').innerHTML=heading('Tus rutinas','Apps, pantallas y música, en el orden que tú elijas.',`<button class="primary" data-action="new-scene">${icon('plus')}Crear rutina</button>`)+
      `<div class="routine-list">${state.profile.scenes.map(s=>`<article class="scene-card"><div class="scene-symbol">${icon('modes')}</div><div class="info"><strong>${esc(s.name)}</strong><small>${s.steps.length} pasos · ${s.onError==='continue'?'continúa si falla un paso':'se detiene si falla un paso'}</small></div><button class="card-more" data-action="edit-scene" data-id="${esc(s.id)}" aria-label="Editar ${esc(s.name)}">${icon('more')}</button><button class="launch" data-action="run-scene" data-id="${esc(s.id)}" aria-label="Iniciar ${esc(s.name)}">${icon('play')}</button></article>`).join('')||empty('modes','Diseña tu combinación','Por ejemplo: Roblox a la derecha y TIDAL en la vertical.',`<button class="primary" data-action="new-scene">Crear rutina</button>`)}</div>`+jobList();
  }
  if(page==='pc')$('#content .power-grid').insertAdjacentHTML('beforebegin',`<div class="section-bar"><h2>Tus pantallas</h2></div>${monitorMap()}<div class="section-bar"><h2>Ventanas abiertas</h2><button class="text-button" data-action="refresh-windows">Actualizar</button></div><div class="window-list">${(state.windows||[]).map(w=>`<div class="window-row"><div><strong>${esc(w.title)}</strong><small>${esc(w.process)} · ${esc(state.monitors.find(m=>m.id===w.monitor)?.label||'Pantalla desconectada')}${w.minimized?' · minimizada':''}</small></div><button class="secondary" data-action="window-layout" data-id="${esc(w.id)}">Mover</button></div>`).join('')||'<p class="hint">No hay ventanas disponibles para mover.</p>'}</div>${jobList()}<div class="section-bar"><h2>Energía</h2></div>`);
  if(page==='settings')$('#content .settings-list').insertAdjacentHTML('beforebegin',`<div class="setting-row"><div><strong>Inicio con Windows</strong><small>${state.startup?'Activado · Eddy Deck queda junto al reloj':'Desactivado'}</small></div>${native?'':`<button class="secondary" data-action="toggle-startup">${state.startup?'Desactivar':'Activar'}</button>`}</div><div class="setting-row"><div><strong>Internet privado</strong><small>${state.internet?.addresses?.length?'IP de Tailscale: '+esc(state.internet.addresses.join(', ')):'Inicia sesión en Tailscale en la PC y el celular.'}</small></div><button class="secondary" data-action="internet-guide">Configurar</button></div>${native?`<div class="setting-row"><div><strong>Conexión en segundo plano</strong><small>Notificación permanente y reconexión automática. Android puede detenerla para ahorrar batería.${bootstrap?.backgroundStatus?'<br>'+esc(bootstrap.backgroundStatus):''}${bootstrap?.backgroundError?'<br>'+esc(bootstrap.backgroundError):''}</small></div><button class="secondary" data-action="toggle-background">${bootstrap?.background?'Desactivar':'Activar'}</button></div><div class="setting-row"><div><strong>Tus otras computadoras</strong><small>Cambia de equipo o lleva el instalador de Windows.</small></div><button class="secondary" data-action="manage-pcs">Mis PCs</button></div>`:''}`);
};

function stepLabel(step){
  if(step.type==='wait')return `Esperar ${step.seconds} segundos`;
  if(step.type==='media')return `${step.action==='mute'&&step.target!=='aimp'?'Volumen de Windows':step.target==='aimp'?'AIMP':step.target==='tidal'?'TIDAL':step.target==='windows'?'Teclas de Windows':step.target?.startsWith('session:')?(state.media?.players?.find(p=>p.id===step.target)?.name||'Sesión multimedia guardada'):'Música automática'} · ${{toggle:'reproducir / pausar',play:'reproducir',pause:'pausar',next:'siguiente canción',previous:'canción anterior',stop:'detener',mute:'silenciar / activar'}[step.action]||step.action}`;
  const role={keep:'su pantalla actual',left:'izquierda',right:'derecha',vertical:'vertical',primary:'principal'}[step.layout?.monitor]||state.monitors.find(m=>m.id===step.layout?.monitor)?.label||'pantalla guardada';
  return `${step.type==='window'?'Mover':'Abrir'} ${appById(step.appId)?.name||'App no disponible'} · ${role} · ${modeNames[step.layout?.mode||'keep']}${step.type==='launch'?' · '+(step.activation==='windows'?'Windows decide':'al frente'):''}`;
}
sceneEditor=function(id){
  const scene=state.profile.scenes.find(s=>s.id===id);routineId=scene?.id||'';routineName=scene?.name||'';routinePolicy=scene?.onError||'stop';routineDraft=structuredClone(scene?.steps||[]);routineEditor();
};
function routineEditor(){showModal(routineId?'Editar rutina':'Nueva rutina',`<form id="routine-form"><label class="field"><span>Nombre</span><input id="routine-name" name="name" required maxlength="80" placeholder="Por ejemplo, Jugar y escuchar música" value="${esc(routineName)}"></label><div class="routine-steps">${routineDraft.map((s,i)=>`<div class="routine-step"><span class="step-number">${i+1}</span><div><strong>${esc(stepLabel(s))}</strong>${s.url?`<small>${esc(s.url)}</small>`:''}</div><div class="step-tools"><button type="button" data-action="edit-step" data-index="${i}" aria-label="Editar paso ${i+1}">${icon('more')}</button><button type="button" data-action="step-up" data-index="${i}" aria-label="Subir paso ${i+1}" ${!i?'disabled':''}>${icon('up')}</button><button type="button" data-action="remove-step" data-index="${i}" aria-label="Quitar paso ${i+1}">${icon('close')}</button></div></div>`).join('')||'<p class="hint">Agrega el primer paso de tu rutina.</p>'}</div><button type="button" class="secondary" data-action="add-step" ${routineDraft.length>=24?'disabled':''}>${icon('plus')}Agregar paso</button><label class="field"><span>Si falla un paso</span><select id="routine-policy"><option value="stop" ${routinePolicy==='stop'?'selected':''}>Detener la rutina y avisarme</option><option value="continue" ${routinePolicy==='continue'?'selected':''}>Registrar el error y continuar con el siguiente</option></select></label><p class="hint">Hasta 24 pasos y 5 minutos por ejecución. Cancelar detiene los pasos pendientes; conserva lo ya abierto.</p><div class="modal-actions"><button type="submit" class="primary">Guardar rutina</button></div></form>${routineId?`<button class="text-button danger-text" data-action="delete-scene" data-id="${esc(routineId)}">Eliminar rutina</button>`:''}`);}
function captureRoutine(){if($('#routine-name')){routineName=$('#routine-name').value;routinePolicy=$('#routine-policy').value;}}
let stepDraftCache={};
function stepEditor(index=-1,type,editing){
  const s=editing||routineDraft[index]||{type:'launch',layout:{},appId:state.apps[0]?.id,url:'',seconds:1,target:'system',action:'toggle'};type=type||s.type||'launch';stepDraftCache=structuredClone(s);
  showModal(index<0?'Agregar paso':'Editar paso',`<form id="step-form" data-index="${index}"><label class="field"><span>Qué hacer</span><select id="step-type" name="type">${[['launch','Abrir aplicación'],['window','Mover una app ya abierta'],['media','Controlar música'],['wait','Esperar']].map(([id,label])=>`<option value="${id}" ${type===id?'selected':''}>${label}</option>`).join('')}</select></label>${['launch','window'].includes(type)?`<label class="field"><span>Aplicación</span><input id="step-app-search" type="search" placeholder="Filtrar aplicaciones…" aria-label="Filtrar aplicaciones del paso"><select name="appId" id="step-app" required>${s.appId&&!appById(s.appId)?'<option value="" selected disabled>Aplicación no disponible · elige otra</option>':''}${state.apps.map(a=>`<option value="${esc(a.id)}" ${s.appId===a.id?'selected':''}>${esc(a.name)}</option>`).join('')}</select></label><label class="field" id="step-url-field"><span>URL · solo navegadores</span><input name="url" maxlength="2048" placeholder="https://…" value="${esc(s.url||'')}"></label>${layoutFields(s.layout)}${type==='launch'?activationField(s.activation):''}`:type==='wait'?`<label class="field"><span>Segundos · máximo 30</span><input name="seconds" type="number" min="0" max="30" step="0.5" value="${s.seconds??1}" required></label>`:`<label class="field"><span>Reproductor</span><select name="target"><option value="system" ${!['aimp','tidal','windows',...(state.media?.players||[]).map(p=>p.id)].includes(s.target)?'selected':''}>Automático · TIDAL / AIMP / Windows</option><option value="tidal" ${s.target==='tidal'?'selected':''}>TIDAL directo</option><option value="aimp" ${s.target==='aimp'?'selected':''}>AIMP directo</option>${(state.media?.players||[]).map(p=>`<option value="${esc(p.id)}" ${s.target===p.id?'selected':''}>${esc(p.name)}</option>`).join('')}${s.target?.startsWith('session:')&&!(state.media?.players||[]).some(p=>p.id===s.target)?`<option value="${esc(s.target)}" selected>Sesión guardada · abre el reproductor</option>`:''}<option value="windows" ${state.capabilities?.mediaSessions?'':'disabled'} ${s.target==='windows'?'selected':''}>Teclas de Windows · sin confirmación</option></select></label><label class="field"><span>Control</span><select name="action">${[['toggle','Reproducir / pausar'],['play','Reproducir'],['pause','Pausar'],['next','Siguiente canción'],['previous','Canción anterior'],['stop','Detener'],['mute','Silenciar / activar · Windows (excepto AIMP)']].map(([id,label])=>`<option value="${id}" ${s.action===id?'selected':''}>${label}</option>`).join('')}</select></label>`}<div class="modal-actions"><button type="button" class="secondary" data-action="back-routine">Volver</button><button type="submit" class="primary">${index<0?'Agregar':'Guardar'} paso</button></div></form>`);updateStepURL();updateStepMediaControls();
}
function updateStepURL(){if(!$('#step-url-field'))return;const compatible=appById($('#step-app').value)?.browser;$('#step-url-field').hidden=!compatible;if(!compatible)$('#step-url-field input').value='';}
function updateStepMediaControls(){const f=$('#step-form');if(!f?.elements.target)return;const target=f.elements.target.value,select=f.elements.action;for(const option of select.options)option.disabled=target==='windows'?['play','pause'].includes(option.value):target.startsWith('session:')?option.value==='mute':false;if(select.selectedOptions[0]?.disabled)select.value='toggle';}
function pcManager(){showModal('Mis computadoras',`<p class="subtitle">Cada equipo conserva sus propias aplicaciones, rutinas y permisos.</p>${(bootstrap?.pcs||[]).map(pc=>`<div class="setting-row"><div><strong>${esc(pc.name)}</strong><small>${esc(pc.host)}${pc.active?' · seleccionada':''}</small></div><button class="secondary" data-action="select-computer" data-id="${esc(pc.id)}">${pc.active?'Reconectar':'Conectar'}</button></div>`).join('')}<div class="modal-actions"><button class="primary" data-action="add-computer">Agregar PC</button><button class="secondary" data-action="installer-guide">Llevar instalador</button></div>`);}
async function switchPC(id){connectionEpoch++;loading=false;state=null;signature='';bootstrap=await nativeCall('selectPC',{id});online=false;$('#modal').close();page='home';await load(true);}
function internetGuide(){showModal('Conectar con datos móviles',`<ol class="setup-steps"><li>Instala Tailscale en el celular y en Windows, e inicia sesión en ambos con la misma cuenta.</li><li>Activa la VPN de Tailscale en Android. Windows debe estar encendido, con tu sesión abierta y Eddy Deck activo.</li><li>Vincula Eddy Deck una vez por USB o Wi-Fi. La IP privada se guardará al sincronizar. También puedes escribirla abajo.</li></ol><p class="notice">Mantiene el cifrado y la huella de esta PC. No necesitas abrir puertos en el router. Si usas otra VPN en Android, el sistema puede pedir cambiar de VPN.</p>${native?`<button class="secondary" data-action="open-tailscale">Abrir / instalar Tailscale</button><form id="vpn-form"><label class="field"><span>IP de Tailscale de esta PC</span><input name="host" placeholder="100.x.x.x" required inputmode="decimal" value="${esc(state?.internet?.addresses?.[0]||'')}"></label><button type="submit" class="primary">Verificar y guardar</button></form>`:`<p>IP detectada: <strong>${esc(state?.internet?.addresses?.join(', ')||'Tailscale todavía no está conectado')}</strong></p><p class="hint">Si el firewall bloquea el acceso privado, usa «Activar internet» en la ventana de Eddy Deck. Windows pedirá permiso para una regla limitada a esta app y a la red de Tailscale.</p>`}`);}
async function launchConfigured(card){
  if(card.layout?.monitor==='ask'){
    window.launchChoice=card;showModal('Dónde abrir '+esc(card.name),`<form id="launch-layout-form">${layoutFields({...card.layout,monitor:'right'})}${activationField(card.activation)}<div class="modal-actions"><button type="submit" class="primary">Abrir aplicación</button></div></form>`);return;
  }
  toast((await api('/api/launch',{appId:card.appId,url:card.url||'',layout:card.layout,activation:card.activation||'front',ifOpen:card.ifOpen||'reuse'})).message);await load();
}
const originalPerform=perform;
perform=async function(action,el){
  switch(action){
    case 'launch-card':return launchConfigured(state.profile.cards.find(c=>c.id===el.dataset.id));
    case 'open-url-once':{const f=$('#card-form');return launchConfigured({name:appById(f.appId?.value)?.name||'navegador',appId:new FormData(f).get('appId'),url:new FormData(f).get('url'),layout:readLayout(f),activation:readActivation(f)});}
    case 'cancel-job':toast((await api('/api/jobs/cancel',{id:el.dataset.id})).message);await load(true);return;
    case 'refresh-windows':await load(true);return;
    case 'window-layout':{const w=state.windows.find(w=>w.id===el.dataset.id);showModal('Mover ventana',`<p class="subtitle">${esc(w.title)}</p><form id="window-form" data-id="${esc(w.id)}">${layoutFields({monitor:w.monitor,mode:w.minimized?'minimized':w.maximized?'maximized':'keep'})}<div class="modal-actions"><button type="submit" class="primary">Aplicar</button></div></form>`);return;}
    case 'toggle-startup':await api('/api/startup',{enabled:!state.startup});await load(true);return;
    case 'add-step':captureRoutine();stepEditor();return;
    case 'edit-step':captureRoutine();stepEditor(Number(el.dataset.index));return;
    case 'step-up':{captureRoutine();const i=Number(el.dataset.index);if(i>0)[routineDraft[i-1],routineDraft[i]]=[routineDraft[i],routineDraft[i-1]];routineEditor();return;}
    case 'remove-step':captureRoutine();routineDraft.splice(Number(el.dataset.index),1);routineEditor();return;
    case 'back-routine':routineEditor();return;
    case 'manage-pcs':bootstrap=await nativeCall('bootstrap');pcManager();return;
    case 'select-computer':await switchPC(el.dataset.id);return;
    case 'add-computer':connectionEpoch++;loading=false;state=null;online=false;pairCandidate=null;bootstrap={...bootstrap,paired:false,host:''};$('#modal').close();renderPairing();return;
    case 'installer-guide':showModal('Agregar otra PC con Windows 11',`<ol class="setup-steps"><li>Guarda el instalador incluido en tu celular.</li><li>Copia el ZIP a la PC por USB, Bluetooth o la opción Compartir de tu celular.</li><li>En Windows extrae el ZIP completo y ejecuta <strong>Instalar.cmd</strong>.</li><li>Abre Eddy Deck en esa PC, permite la conexión y usa su propio código desde «Agregar PC».</li></ol><p class="hint">El instalador es para Windows de 64 bits. En ARM depende de la compatibilidad de emulación. La detección por Wi-Fi requiere que Eddy Deck ya esté ejecutándose. Bluetooth sirve para transferir el archivo; el control usa Wi-Fi, USB o Tailscale.</p><button class="primary" data-action="save-installer">Guardar instalador Windows</button>`);return;
    case 'save-installer':await nativeCall('exportInstaller');return;
    case 'internet-guide':internetGuide();return;
    case 'open-tailscale':await nativeCall('tailscale');return;
    case 'toggle-background':{await nativeCall('background',{enabled:!bootstrap?.background});bootstrap=await nativeCall('bootstrap');render();toast('Preferencia guardada. Android mostrará los permisos que necesite.');return;}
    case 'battery-settings':await nativeCall('batterySettings');return;
    case 'confirm-forget':bootstrap=await nativeCall('forget');connectionEpoch++;loading=false;state=null;online=false;$('#modal').close();if(bootstrap.paired)await load(true);else renderPairing();return;
  }
  return originalPerform(action,el);
};
document.addEventListener('submit',async event=>{
  const f=event.target;if(!['routine-form','step-form','window-form','launch-layout-form','vpn-form'].includes(f.id))return;
  event.preventDefault();const b=f.querySelector('[type=submit]');if(b.disabled)return;b.disabled=true;const data=new FormData(f);
  try{
    if(f.id==='routine-form'){captureRoutine();await api('/api/scenes/save',{id:routineId||undefined,name:routineName,steps:routineDraft,onError:routinePolicy});$('#modal').close();await load(true);toast('Rutina guardada');}
    if(f.id==='step-form'){const type=data.get('type');const step=type==='wait'?{type,seconds:Number(data.get('seconds'))}:type==='media'?{type,target:data.get('target'),action:data.get('action')}:{type,appId:data.get('appId'),url:data.get('url')||'',layout:readLayout(f),activation:readActivation(f),ifOpen:data.get('ifOpen')||'reuse'};if(['launch','window'].includes(type)&&!appById(step.appId))throw Error('Selecciona una aplicación disponible en esta PC.');const i=Number(f.dataset.index);if(i<0)routineDraft.push(step);else routineDraft[i]=step;routineEditor();}
    if(f.id==='window-form'){toast((await api('/api/windows/move',{windowId:f.dataset.id,layout:readLayout(f)})).message);$('#modal').close();await load(true);}
    if(f.id==='launch-layout-form'){toast((await api('/api/launch',{appId:window.launchChoice.appId,url:window.launchChoice.url||'',layout:readLayout(f),activation:readActivation(f),ifOpen:window.launchChoice.ifOpen||'reuse'})).message);$('#modal').close();await load(true);}
    if(f.id==='vpn-form'){await nativeCall('changeHost',{host:data.get('host').trim(),fingerprint:bootstrap.pcId});bootstrap=await nativeCall('bootstrap');$('#modal').close();await load(true);toast('Conexión privada verificada y guardada');}
  }catch(error){$('#modal-error').textContent=error.message;}finally{b.disabled=false;}
});
document.addEventListener('change',e=>{if(e.target.id==='step-type'){const f=$('#step-form'),d=new FormData(f);stepEditor(Number(f.dataset.index),e.target.value,{...stepDraftCache,activation:d.get('activation')??stepDraftCache.activation,ifOpen:d.get('ifOpen')??stepDraftCache.ifOpen,appId:d.get('appId')??stepDraftCache.appId,url:d.get('url')??stepDraftCache.url,layout:d.has('monitor')?readLayout(f):stepDraftCache.layout,seconds:d.has('seconds')?Number(d.get('seconds')):stepDraftCache.seconds,target:d.get('target')??stepDraftCache.target,action:d.get('action')??stepDraftCache.action});}if(e.target.id==='step-app')updateStepURL();if(e.target.name==='target'&&e.target.closest('#step-form'))updateStepMediaControls();});
document.addEventListener('input',e=>{if(e.target.id==='step-app-search'){const q=e.target.value.toLocaleLowerCase();const select=$('#step-app');for(const option of select.options)option.hidden=!option.text.toLocaleLowerCase().includes(q);const hit=[...select.options].find(o=>!o.hidden);select.value=hit?hit.value:'';select.required=true;updateStepURL();}});
const originalPairing=renderPairing;
renderPairing=function(){if(pairCandidate?.fingerprint&&bootstrap)bootstrap.paired=false;originalPairing();if(native){$('#content').insertAdjacentHTML('beforeend','<div class="offline-options"><button class="secondary" data-action="manage-pcs">Mis computadoras</button><button class="text-button" data-action="installer-guide">Llevar instalador a otra PC</button><button class="text-button" data-action="internet-guide">Conectar por internet</button></div>');}};
window.eddyPairLink=async()=>{connectionEpoch++;loading=false;bootstrap=await nativeCall('bootstrap');state=null;online=false;if(bootstrap.candidate){pairCandidate=bootstrap.candidate;renderPairing();}else if(bootstrap.paired){pairCandidate=null;await load(true);}else renderPairing();};

function repairSection(){return `<section class="repair-section"><div class="section-bar"><h2>Reparación y ayuda</h2><span class="tiny-label">BETA</span></div><p class="hint">Recupera Eddy Deck conservando tus computadoras, botones y rutinas.</p><div class="repair-actions">${native?'<button class="secondary" data-action="repair-app">Reparar app del celular</button>':''}<button class="secondary" data-action="repair-pc">Reparar receptor de la PC</button><button class="secondary" data-action="support-report">Guardar informe</button></div><p class="hint">El receptor de la PC necesita conexión para recibir la orden. Su supervisor también intenta recuperarlo si se cierra o deja de responder.</p></section>`;}
const supportRender=render;render=function(){supportRender();if(state&&['home','settings'].includes(page))$('#content').insertAdjacentHTML('beforeend',repairSection());};
const supportPairing=renderPairing;renderPairing=function(){supportPairing();$('#content').insertAdjacentHTML('beforeend',repairSection());};
const supportPerform=perform;perform=async function(action,el){
  if(action==='repair-app'){await nativeCall('repairApp');return;}
  if(action==='repair-pc'){
    if(!online){showModal('La PC no está conectada','<p>Prueba reparar la app del celular y comprueba Tailscale. La PC debe estar despierta. El supervisor de Windows intenta recuperar Eddy Deck si falla; si no puede, abre Eddy Deck desde Windows y consulta sus informes.</p>');return;}
    showModal('Reparar receptor de la PC','<p>Se reinician los procesos de Eddy Deck y su conexión. Se cancelan las rutinas pendientes y la cuenta atrás de energía. Las otras aplicaciones permanecen abiertas.</p><div class="modal-actions"><button class="secondary" data-action="close-modal">Volver</button><button class="primary" data-action="confirm-repair-pc">Reparar receptor</button></div>');return;
  }
  if(action==='confirm-repair-pc'){const r=await api('/api/repair',{confirm:true});$('#modal').close();toast(r.message);return;}
  if(action==='support-report'){
    let pc=null;try{if(online)pc=(await api('/api/diagnostics',{})).report;}catch(e){toast('Se incluirá el informe del celular; no se pudo consultar la PC.');}
    if(native){await nativeCall('exportDiagnostics',pc?{pc}:{});return;}
    if(!pc){toast('Espera la conexión para obtener el informe de Windows.');return;}
    const blob=new Blob([JSON.stringify(pc,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='EddyDeck-informe.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return;
  }
  return supportPerform(action,el);
};
