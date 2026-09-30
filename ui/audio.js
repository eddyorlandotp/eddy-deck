'use strict';
// The displayed endpoint and PC are leases: a delayed gesture must not target
// a newly selected device. Only committed slider values are sent, in order.
let audioBusy=false,audioHeld=false,audioPending=null;
function audioEditing(){return audioBusy||audioHeld;}
function audioControls(area){
  const a=state?.audio,rows=a?.outputs||[],ready=Boolean(a?.available&&a.defaultId);
  const lease=`data-endpoint="${esc(a?.defaultId||'')}" data-epoch="${connectionEpoch}" data-pc="${esc(bootstrap?.pcId||'local')}"`;
  return `<section class="audio-panel" aria-label="Sonido de Windows"><div class="audio-heading">${icon('volume')}<strong>Sonido de tu PC</strong></div><label class="field"><span>Salida de sonido</span><select class="select audio-output" aria-label="Salida de sonido" ${lease} ${rows.length?'':'disabled'}>${!a?.defaultId?'<option value="">Elige una salida</option>':''}${rows.map(o=>`<option value="${esc(o.id)}" ${o.id===a.defaultId?'selected':''}>${esc(o.name)}</option>`).join('')}${!rows.length?'<option value="">No hay salidas disponibles</option>':''}</select></label><div class="system-volume-row"><button class="audio-mute secondary" data-action="audio-mute" ${lease} data-muted="${Boolean(a?.mute)}" ${ready?'':'disabled'} aria-label="${a?.mute?'Activar sonido':'Silenciar PC'}" aria-pressed="${Boolean(a?.mute)}">${icon(a?.mute?'mute':'volume')}</button><input class="system-volume" type="range" min="0" max="100" step="1" value="${a?.volume??0}" ${lease} ${ready?'':'disabled'} aria-label="Volumen de Windows" aria-valuetext="${a?.volume??0} por ciento"><output>${a?.volume??'—'}%</output></div><p class="help audio-status" role="status">${esc(a?.error||(a?.mute?'La PC está silenciada. Activa el sonido con el botón de la barra.':'Salida general de Windows · volumen independiente de cada reproductor.'))}</p></section>`;
}
function audioLease(el){return {endpoint:el.dataset.endpoint,epoch:Number(el.dataset.epoch),pc:el.dataset.pc};}
function audioLeaseValid(lease){return online&&lease.epoch===connectionEpoch&&lease.pc===(bootstrap?.pcId||'local')&&lease.endpoint===(state?.audio?.defaultId||'');}
async function queueAudio(el,action,value){
  const lease=audioLease(el);
  if(!audioLeaseValid(lease)){toast('Cambió la PC o la salida de sonido. Vuelve a elegir el ajuste.');el.blur();await load(true);return;}
  if(audioBusy&&action!=='volume'){toast('Espera a que termine el ajuste de sonido.');return;}
  audioPending={lease,action,value};if(audioBusy)return;
  audioBusy=true;
  try{
    while(audioPending){
      const task=audioPending;audioPending=null;
      if(!audioLeaseValid(task.lease))throw Error('Cambió la PC o la salida. Se descartó el ajuste pendiente.');
      const body={action:task.action,endpoint:task.action==='select'?task.value:task.lease.endpoint};
      if(task.action==='select')body.expected=task.lease.endpoint;else body.value=task.value;
      const result=await api('/api/audio',body);
      if(task.lease.epoch!==connectionEpoch)break;
      if(task.action==='select')toast(result.message);
    }
  }catch(error){audioPending=null;toast(error.message);}
  finally{audioBusy=false;audioPending=null;el.blur();await load(true);}
}
document.addEventListener('pointerdown',e=>{if(e.target.matches('.system-volume'))audioHeld=true;});
for(const kind of ['pointerup','pointercancel'])document.addEventListener(kind,()=>{audioHeld=false;});
window.addEventListener('blur',()=>{audioHeld=false;});
document.addEventListener('input',e=>{if(e.target.matches('.system-volume')){e.target.nextElementSibling.textContent=e.target.value+'%';e.target.setAttribute('aria-valuetext',e.target.value+' por ciento');}});
document.addEventListener('change',e=>{if(e.target.matches('.system-volume'))queueAudio(e.target,'volume',Number(e.target.value));if(e.target.matches('.audio-output'))queueAudio(e.target,'select',e.target.value);});
function wakeButton(){return native&&bootstrap?.paired?`<button class="secondary wake-button" data-action="wake-guide">${icon('power')}Encender por LAN</button>`:'';}
async function wakeGuide(){
  if(!native)return;
  bootstrap=await nativeCall('bootstrap');
  showModal('Encender por LAN',`<p class="subtitle">Envía una señal desde este celular a <strong>${esc(bootstrap.pcs?.find(p=>p.active)?.name||'tu PC')}</strong>, aunque Eddy Deck en Windows esté desconectado.</p><div class="notice">El celular debe estar en el mismo Wi-Fi de la PC. La PC necesita alimentación y una tarjeta de red compatible; Ethernet es lo más fiable. Activa Wake-on-LAN en su BIOS y controlador. El encendido desde apagado depende del equipo.</div><p class="help">Con datos móviles o desde otra casa, Tailscale solo no puede despertarla: se necesita otro dispositivo encendido en casa que envíe la señal.</p>${!bootstrap.wakeReady?'<p class="notice">Conecta esta PC una vez con la versión nueva para guardar sus datos de encendido.</p>':''}<div class="modal-actions"><button class="secondary" data-action="close-modal">Volver</button><button class="primary" data-action="wake-pc" data-pc="${esc(bootstrap.pcId)}" ${bootstrap.wakeReady?'':'disabled'}>Enviar señal de encendido</button></div>`);
}
async function wakePC(el){
  const epoch=connectionEpoch,result=await nativeCall('wake',{pcId:el.dataset.pc});
  if(epoch!==connectionEpoch)return;
  $('#modal').close();toast(result.message);load(true);
}
