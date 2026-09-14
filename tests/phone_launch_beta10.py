"""Beta10 actual phone controls, existing routine and disposable unsaved editor."""
import json,hashlib,sqlite3,time,os,sys
from pathlib import Path
from phone_design_beta8 import tap,ready,nodes,tree,adb,choice
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.core import VERSION
from companion import windows
from companion.layout import Windows
import win32gui as g
folder=Path.home()/'.eddydeck';original=(folder/'deck.json').read_bytes();checks=[]
def check(name,ok=True):assert ok,name;checks.append(name);print(name,flush=True)
adb('shell','am','start','-n','com.eddy.deck/.MainActivity');tap('Inicio');ready('Hola, Eddy.');tap('Rutinas');ready('Tus rutinas')
begin=time.time();tap('Iniciar Jugar bobox');end=time.monotonic()+40;job=None
while time.monotonic()<end:
 with sqlite3.connect('file:'+str(folder/'operations.sqlite3')+'?mode=ro',uri=True) as db:
  jobs=[json.loads(r[0]) for r in db.execute('select data from jobs where at>=? order by at desc',(begin,))]
 job=next((j for j in jobs if j['name'].lower()=='jugar bobox'),None)
 if job and job['status'] not in ('running','queued'):break
 time.sleep(.1)
check('Saved routine sent from Samsung completed both steps',job is not None and job['status']=='completed' and len(job['results'])==2)
check('Both installed Windows steps confirmed foreground',all(r.get('foreground') for r in job['results']))
apps,_=windows.scan(folder);tidal=next(a for a in apps if a['name']=='TIDAL');w=Windows();rows=[r for r in w.snapshot(apps) if tidal['id'] in r['appIds']];check('TIDAL foreground independently observed',len(rows)==1 and g.GetForegroundWindow()==w.leases[rows[0]['id']]['hwnd'])
tap('Crear rutina',first=True);ready('Nueva rutina');tap('Agregar paso');ready('Qué hacer:',True)
tap('Al abrir la aplicación:',True);ready('ELIGE UNA OPCIÓN');check('Samsung shows both foreground choices',bool(nodes(tree(),'Traer al frente')) and bool(nodes(tree(),'Dejar que Windows decida')))
tap('Dejar que Windows decida');ready('Al abrir la aplicación: Dejar que Windows decida');choice('Qué hacer','Mover una app ya abierta');check('Move editor has no activation field',not nodes(tree(),'Al abrir la aplicación:',True));choice('Qué hacer','Abrir aplicación');ready('Al abrir la aplicación: Dejar que Windows decida');check('Choice survives switching routine step type')
tap('Agregar paso');ready('Nueva rutina');check('Routine summary preserves Windows choice',any('Windows decide' in n.get('text','') for n in tree().iter('node')))
tap('Cerrar');ready('Tus rutinas');tap('Inicio');ready('Hola, Eddy.');check('Unsaved phone draft did not change original profile',original==(folder/'deck.json').read_bytes())
apk=adb('shell','pm','path','com.eddy.deck').strip().removeprefix('package:');sha=adb('shell','sha256sum',apk).split()[0];check('Installed APK matches current build',sha==hashlib.sha256((ROOT/'artifacts/EddyDeck-Android.apk').read_bytes()).hexdigest())
report={'version':VERSION,'passed':True,'count':len(checks),'checks':checks,'installedApkSHA256':sha,'originalRoutineCompleted':True,'originalProfileUnchanged':True,'scope':'Samsung touches real installed Eddy Deck; existing routine executed, two foreground steps confirmed in Windows, independent TIDAL foreground observed. Disposable editor was discarded.'}
(ROOT/'artifacts/beta10-phone-launch-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'count':len(checks)}))
