"""Physical Android touches with independent private-profile/job observations.

Resume from an unsaved Calculator card opened by the interactive setup.
Every created item carries a unique test name. No existing card/routine is edited.
"""
import json,sys,time,hashlib,sqlite3
from pathlib import Path
from phone_design_beta8 import tap,ready,tree,nodes,bounds,adb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.core import VERSION
DATA=Path.home()/'.eddydeck';OUT=ROOT/'artifacts/beta11-phone-walkthrough.json'
checks=[]
def profile():return json.loads((DATA/'deck.json').read_text(encoding='utf-8'))
def check(label,value=True):
    assert value,label
    checks.append(label);print(label,flush=True)
    OUT.write_text(json.dumps({'version':VERSION,'status':'in_progress','checks':checks,'count':len(checks),'scope':'Fresh Android accessibility snapshots, real ADB taps, real installed receiver and independent profile/job reads.'},ensure_ascii=False,indent=2),encoding='utf-8')
def edit(label,value):
    tap(label);adb('shell','input','keycombination','113','29');adb('shell','input','text',value.replace(' ','%s'));adb('shell','input','keyevent','KEYCODE_BACK');ready(value)
def pick(field,value):
    tap(field+':',True);ready('ELIGE UNA OPCIÓN');tap(value,option_only=True)
def job(name,after):
    with sqlite3.connect('file:'+str(DATA/'operations.sqlite3')+'?mode=ro',uri=True) as db:
        rows=[json.loads(r[0]) for r in db.execute('select data from jobs where at>=? order by at desc',(after,))]
    return next((j for j in rows if j['name']==name),None)
def wait_job(name,after,expected):
    end=time.monotonic()+25
    while time.monotonic()<end:
        j=job(name,after)
        if j and j['status']==expected:return j
        time.sleep(.1)
    raise AssertionError((name,expected,j))
def main():
    global checks
    resume='--resume-after-card-create' in sys.argv
    if resume:
        before=json.loads((ROOT/'.build/beta11-phone-profile-before.json').read_text(encoding='utf-8'));checks=json.loads(OUT.read_text(encoding='utf-8'))['checks'];tap('Inicio');ready('Hola, Eddy.')
    else:
        before=profile();(ROOT/'.build/beta11-phone-profile-before.json').write_text(json.dumps(before),encoding='utf-8')
    name='QA Beta11 Calculator';routine='QA Beta11 Rutina'
    assert not any(x['name'].startswith('QA Beta11') for x in before['cards']+before['scenes'])
    if not resume:
        if '--from-home' in sys.argv:
            tap('Inicio');tap('Biblioteca');ready('Tu biblioteca');edit('library-search','Calculator');tap('Agregar Calculator')
        ready('Agregar a mi panel');edit('Calculator',name);tap('Color mint');tap('Pantalla y tamaño al abrir');pick('Pantalla','Derecha');pick('Ventana','Modo ventana');pick('Al abrir la aplicación','Dejar que Windows decida');tap('Agregar botón');ready('Hola, Eddy.')
    card=next(c for c in profile()['cards'] if c['name']==name)
    if not resume:check('Phone creates Calculator card with explicit monitor, window mode and activation',card['layout']['monitor']=='right' and card['layout']['mode']=='windowed' and card['activation']=='windows')
    tap('Configurar '+name);ready('Personalizar botón');edit(name,name+' editado');tap('Guardar cambios');ready('Hola, Eddy.')
    check('Phone edit persisted on Windows',next(c for c in profile()['cards'] if c['id']==card['id'])['name']==name+' editado')
    tap('Configurar '+name+' editado');tap('Quitar botón');ready('Hola, Eddy.');check('Phone removes only its temporary card',profile()['cards']==before['cards'])
    tap('Rutinas');ready('Tus rutinas');tap('Crear rutina',first=True);ready('Nueva rutina');edit('routine-name',routine)
    for _ in range(2):
        tap('Agregar paso');ready('Qué hacer:',True);pick('Qué hacer','Esperar');tap('Agregar paso');ready('Nueva rutina')
    tap('Editar paso 2');ready('Qué hacer:',True)
    edits=[n for n in tree().iter('node') if n.get('class')=='android.widget.EditText'];assert len(edits)==1
    x1,y1,x2,y2=bounds(edits[0]);adb('shell','input','tap',(x1+x2)//2,(y1+y2)//2);adb('shell','input','keycombination','113','29');adb('shell','input','text','2');adb('shell','input','keyevent','KEYCODE_BACK');tap('Guardar paso');ready('Nueva rutina');tap('Subir paso 2');pick('Si falla un paso','Registrar el error y continuar con el siguiente');tap('Guardar rutina');ready('Tus rutinas')
    saved=next(s for s in profile()['scenes'] if s['name']==routine)
    check('Phone creates, edits and reorders routine steps with continue policy',[s['seconds'] for s in saved['steps']]==[2,1] and saved['onError']=='continue')
    began=time.time();tap('Iniciar '+routine);j=wait_job(routine,began,'completed');check('Routine started by phone completed both real wait steps',len(j['results'])==2)
    tap('Mi PC');tap('Pausar siguientes tareas');ready('Reanudar');tap('Rutinas');began=time.time();tap('Iniciar '+routine);wait_job(routine,began,'queued');check('Phone queue pause keeps the newly submitted routine queued')
    tap('Mi PC');tap('Cancelar',first=True);wait_job(routine,began,'cancelled');check('Phone cancels a queued routine without executing a step');tap('Reanudar');ready('Pausar siguientes tareas')
    tap('Rutinas');tap('Editar '+routine);ready('Editar rutina');tap('Eliminar rutina');ready('Tus rutinas');check('Phone deletes its routine and restores the original profile',profile()==before)
    tap('Música');ready('Que siga la música');tap('Reproductor:',True);ready('ELIGE UNA OPCIÓN');check('Music selector uses the same custom sheet as routine menus',bool(nodes(tree(),'TIDAL · control directo')));adb('shell','input','keyevent','KEYCODE_BACK');ready('Que siga la música');check('Android Back closes only the music option sheet')
    tap('Inicio');ready('Hola, Eddy.')
    raw=adb('shell','pm','path','com.eddy.deck').strip().removeprefix('package:');sha=adb('shell','sha256sum',raw).split()[0];assert sha==hashlib.sha256((ROOT/'artifacts/EddyDeck-Android.apk').read_bytes()).hexdigest()
    report=json.loads(OUT.read_text(encoding='utf-8'));report.update(status='passed',passed=True,profilePreserved=True,installedApkSHA256=sha);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
