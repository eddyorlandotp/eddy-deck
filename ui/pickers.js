'use strict';
// The original select owns values, validation and change events. This layer
// supplies an accessible visual picker without changing request semantics.
(()=>{
  const dialog=document.createElement('dialog');dialog.id='choice-dialog';dialog.className='choice-dialog';dialog.setAttribute('aria-labelledby','choice-title');
  dialog.innerHTML=`<div class="choice-head"><div><span class="eyebrow">ELIGE UNA OPCIÓN</span><h2 id="choice-title"></h2></div><button type="button" class="icon-button" aria-label="Cerrar opciones">${icon('close')}</button></div><div class="choice-search" hidden>${icon('search')}<input type="search" autocomplete="off" placeholder="Buscar…" aria-label="Buscar en las opciones"></div><div class="choice-list" role="listbox" tabindex="0" aria-labelledby="choice-title"></div><p class="choice-empty" role="status" hidden>No hay coincidencias. Prueba otro nombre.</p>`;
  document.body.append(dialog);
  const list=dialog.querySelector('.choice-list'),search=dialog.querySelector('input'),empty=dialog.querySelector('.choice-empty'),enhanced=new WeakMap();
  let active=null,activeIndex=-1,serial=0,returnFocus=null;
  const labelFor=select=>select.closest('.field')?.querySelector(':scope > span')?.textContent?.trim()||select.labels?.[0]?.querySelector('span')?.textContent?.trim()||select.getAttribute('aria-label')||'Selecciona una opción';
  function sync(select){const button=enhanced.get(select);if(!button)return;const label=labelFor(select),option=select.selectedOptions[0],text=option&&!option.hidden?option.text:'Seleccionar…';button.querySelector('.choice-value').textContent=text;button.setAttribute('aria-label',label+': '+text);button.disabled=select.disabled;button.classList.toggle('choice-unset',!select.value);}
  function options(){return [...list.querySelectorAll('[role=option]')];}
  function move(index){const rows=options();if(!rows.length){activeIndex=-1;list.removeAttribute('aria-activedescendant');return;}activeIndex=Math.max(0,Math.min(index,rows.length-1));rows.forEach((r,i)=>r.classList.toggle('focused',i===activeIndex));list.setAttribute('aria-activedescendant',rows[activeIndex].id);rows[activeIndex].scrollIntoView({block:'nearest'});}
  function draw(){
    if(!active?.isConnected){close();return;}const q=search.value.trim().toLocaleLowerCase();list.replaceChildren();
    [...active.options].forEach((option,index)=>{if(option.hidden||!option.text.toLocaleLowerCase().includes(q))return;const row=document.createElement('button');row.type='button';row.className='choice-option';row.id='choice-option-'+index;row.setAttribute('role','option');row.setAttribute('aria-selected',String(index===active.selectedIndex));row.setAttribute('aria-disabled',String(option.disabled));row.tabIndex=-1;row.dataset.optionIndex=index;
      const text=document.createElement('span');text.textContent=option.text;row.append(text);const mark=document.createElement('span');mark.className='choice-mark';mark.innerHTML=icon('check');row.append(mark);row.addEventListener('click',()=>choose(index));list.append(row);});
    const rows=options();empty.hidden=rows.length>0;const selected=rows.findIndex(r=>r.getAttribute('aria-selected')==='true');move(selected<0?0:selected);
  }
  function close(){if(dialog.open)dialog.close();}
  function choose(index){const select=active,option=select?.options[index];if(!select?.isConnected||!option||option.hidden||option.disabled||select.disabled)return;const changed=select.selectedIndex!==index;select.selectedIndex=index;sync(select);close();if(changed){select.dispatchEvent(new Event('input',{bubbles:true}));select.dispatchEvent(new Event('change',{bubbles:true}));}}
  function open(select){if(select.disabled||!select.isConnected)return;if(dialog.open)close();active=select;returnFocus=enhanced.get(select);sync(select);returnFocus?.setAttribute('aria-expanded','true');search.value='';dialog.querySelector('#choice-title').textContent=labelFor(select);dialog.querySelector('.choice-search').hidden=[...select.options].filter(o=>!o.hidden).length<8;dialog.showModal();draw();list.focus({preventScroll:true});}
  function enhance(){
    document.querySelectorAll('#modal select:not([multiple])').forEach(select=>{if(enhanced.has(select)){sync(select);return;}const button=document.createElement('button');button.type='button';button.className='choice-trigger';button.dataset.choiceFor=select.id||('choice-source-'+(++serial));if(!select.id)select.id=button.dataset.choiceFor;button.innerHTML=`<span class="choice-value"></span>${icon('down')}`;button.setAttribute('aria-haspopup','dialog');button.setAttribute('aria-controls','choice-dialog');button.setAttribute('aria-expanded','false');
      select.classList.add('choice-native');select.tabIndex=-1;select.setAttribute('aria-hidden','true');select.after(button);enhanced.set(select,button);button.addEventListener('click',()=>open(select));select.addEventListener('change',()=>sync(select));select.addEventListener('invalid',e=>{e.preventDefault();open(select);});sync(select);
    });
    if(active&&!active.isConnected)close();
  }
  dialog.querySelector('.choice-head button').addEventListener('click',close);
  dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)close();}});
  dialog.addEventListener('close',()=>{if(dialog.open)return;const target=returnFocus;target?.setAttribute('aria-expanded','false');active=null;returnFocus=null;if(target?.isConnected&&$('#modal').open)target.focus({preventScroll:true});});
  search.addEventListener('input',draw);
  dialog.addEventListener('keydown',e=>{if(e.key==='Escape')return;const rows=options();if(e.target===search){if(e.key==='ArrowDown'){e.preventDefault();list.focus();move(0);}if(e.key==='Enter'&&rows[activeIndex]){e.preventDefault();choose(Number(rows[activeIndex].dataset.optionIndex));}return;}if(!list.contains(e.target)&&e.target!==list)return;
    if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();move(e.key==='Home'?0:e.key==='End'?rows.length-1:activeIndex+(e.key==='ArrowDown'?1:-1));}
    if((e.key==='Enter'||e.key===' ')&&rows[activeIndex]){e.preventDefault();choose(Number(rows[activeIndex].dataset.optionIndex));}
  });
  $('#modal').addEventListener('close',close);
  const observer=new MutationObserver(changes=>{if(changes.some(c=>c.type==='childList'&&[...c.addedNodes,...c.removedNodes].some(n=>n.nodeType===1&&(n.matches?.('select,option,form')||n.querySelector?.('select')))||c.target.matches?.('select,option')))enhance();});
  observer.observe($('#modal-content'),{childList:true,subtree:true,attributes:true,attributeFilter:['disabled','hidden','selected']});
  function decorate(){
    const routine=$('#routine-form'),step=$('#step-form');$('#modal').classList.toggle('routine-dialog',Boolean(routine||step));
    if(routine){routine.insertAdjacentHTML('afterbegin',`<div class="editor-intro"><span class="editor-emblem">${icon('modes')}</span><p>Tu espacio, a tu manera.<small>Ordena las acciones. Inicia todo con un toque.</small></p></div>`);const steps=routine.querySelector('.routine-steps');steps.insertAdjacentHTML('beforebegin',`<div class="steps-heading"><h3>Secuencia</h3><span>${routineDraft.length} de 24 pasos</span></div>`);if(!routineDraft.length)steps.innerHTML=`<div class="routine-empty">${icon('plus')}<strong>Empieza con una acción</strong><span>Abre una app, mueve su ventana o pon música.</span></div>`;
      routine.querySelector('[data-action=add-step]').classList.add('add-step-button');
      for(const row of routine.querySelectorAll('.routine-step')){const i=Number(row.querySelector('[data-action=edit-step]').dataset.index),s=routineDraft[i],mark=document.createElement('span');mark.className='step-emblem';mark.innerHTML=icon(s.type==='media'?'music':s.type==='wait'?'moon':s.type==='window'?'pc':'app');row.querySelector('.step-number').after(mark);row.querySelector('[data-action=edit-step]').innerHTML=icon('create');}
    }
    if(step){const type=$('#step-type').value,descriptions={launch:['Abrir una aplicación','Elige la app y cómo quieres verla.'],window:['Colocar una ventana','Mueve una app que ya está abierta.'],media:['Controlar la música','Elige el reproductor y la acción.'],wait:['Dar un respiro','Deja un intervalo entre dos pasos.']},[title,help]=descriptions[type];step.insertAdjacentHTML('afterbegin',`<div class="editor-intro"><span class="editor-emblem">${icon(type==='media'?'music':type==='wait'?'moon':type==='window'?'pc':'app')}</span><p>${title}<small>${help}</small></p></div>`);const layout=step.querySelector('.layout-fields');if(layout)layout.insertAdjacentHTML('beforebegin','<div class="form-section-label">En tu escritorio</div>');}
  }
  const previousShow=showModal;showModal=function(title,body){const oldForm=$('#modal form')?.id,oldTitle=$('#modal .modal-head h2')?.textContent;close();previousShow(title,body);$('#modal').setAttribute('aria-labelledby','modal-title');$('#modal .modal-head h2').id='modal-title';decorate();queueMicrotask(()=>{enhance();if(oldForm!==$('#modal form')?.id||oldTitle!==$('#modal-title').textContent)$('#modal').scrollTop=0;});};
  const previousBack=window.eddyBack;window.eddyBack=()=>dialog.open?(close(),true):previousBack();
})();
