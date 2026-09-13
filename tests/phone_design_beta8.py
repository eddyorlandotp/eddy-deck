"""Visible beta8 menus on the connected Samsung. Draft only, no PC actions."""
import hashlib,json,os,re,sys,time,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.core import VERSION
from tidal_phone import adb,matches
OUT=ROOT/'.build/beta8-visual';OUT.mkdir(exist_ok=True)
def tree():
 for _ in range(4):
  name='/sdcard/eddy-beta8-'+str(time.time_ns())+'.xml'
  try:r=adb('shell','uiautomator','dump',name)
  except subprocess.CalledProcessError as e:
   if e.returncode==137:continue
   raise
  if 'dumped' not in r.lower():continue
  raw=adb('shell','cat',name);adb('shell','rm',name);t=ET.fromstring(raw)
  if any(n.get('package')=='com.eddy.deck' for n in t.iter('node')):return t
 raise AssertionError('Fresh app accessibility tree unavailable')
def nodes(t,label,prefix=False):
 # Android WebView omits the empty search input's ARIA label in UIAutomator.
 # Scope the fallback to the observed option dialog and require a unique field.
 if label=='Buscar en las opciones':
  dialogs=[n for n in t.iter('node') if n.get('resource-id')=='choice-dialog']
  edits=[n for d in dialogs for n in d.iter('node') if n.get('class')=='android.widget.EditText']
  if len(edits)==1:return edits
 return [n for n in t.iter('node') if any((n.get(k,'').startswith(label) if prefix else n.get(k)==label) for k in ('text','content-desc','resource-id'))]
def bounds(n):return list(map(int,re.findall(r'\d+',n.get('bounds',''))))
def seen(label,prefix=False):return bool(nodes(tree(),label,prefix))
def ready(label,prefix=False):
 end=time.monotonic()+22
 while time.monotonic()<end:
  t=tree()
  if nodes(t,label,prefix):return t
 raise AssertionError('Missing visible state: '+label)
def tap(label,prefix=False,first=False,option_only=False):
 for attempt in range(6):
  t=tree();rows=[]
  for n in nodes(t,label,prefix):
   own_option=re.fullmatch(r'choice-option-\d+',n.get('resource-id','')) is not None
   if option_only and not own_option:continue
   if (n.get('clickable')!='true' and not own_option) or n.get('enabled')!='true':continue
   x1,y1,x2,y2=bounds(n)
   if x2>x1 and y2-y1>=35 and y1>=60 and y2<=1533:rows.append((x1,y1,x2,y2))
  if len(rows)==1 or rows and first:
   x1,y1,x2,y2=sorted(rows,key=lambda r:r[1])[0];adb('shell','input','tap',(x1+x2)//2,(y1+y2)//2);return
  if not rows:adb('shell','input','swipe',500,1280,500,600,350)
  else:raise AssertionError('Ambiguous control '+label)
 raise AssertionError('Unreachable control '+label)
def screenshot(name):
 target='/sdcard/eddy-beta8-'+str(time.time_ns())+'.png';adb('shell','screencap','-p',target);adb('pull',target,OUT/name);adb('shell','rm',target)
def choice(field,option):tap(field+':',True);ready('ELIGE UNA OPCIÓN');tap(option);return ready('Agregar paso')
def main():
 profile=Path(os.environ['LOCALAPPDATA'])/'EddyDeck/deck.json';before=profile.read_bytes();checks=[]
 def check(name,value=True):assert value,name;checks.append(name);print(name,flush=True)
 # This test resumes only the disposable empty draft opened by its setup.
 current=tree()
 for _ in range(3):
  if not nodes(current,'ELIGE UNA OPCIÓN'):break
  adb('shell','input','keyevent','KEYCODE_BACK');current=tree()
 if nodes(current,'Nueva rutina') or nodes(current,'Agregar paso'):tap('Cerrar')
 tap('Inicio');screenshot('phone-home.png');tap('Rutinas');tap('Crear rutina',first=True);ready('Nueva rutina');tap('routine-name');adb('shell','input','text','Prueba%svisual%sbeta8');adb('shell','input','keyevent','KEYCODE_BACK');tap('Agregar paso');ready('Qué hacer:',True)
 tap('Qué hacer:',True);t=ready('ELIGE UNA OPCIÓN');check('Native WebView shows the four custom action choices',all(nodes(t,x) for x in ['Abrir aplicación','Mover una app ya abierta','Controlar música','Esperar']));screenshot('phone-picker.png')
 adb('shell','input','keyevent','KEYCODE_BACK');t=ready('Qué hacer:',True);check('Android Back closes only options and retains the step form',bool(nodes(t,'Agregar paso')) and not nodes(t,'ELIGE UNA OPCIÓN'))
 choice('Qué hacer','Esperar');check('Wait choice changes the actual step form',seen('Segundos · máximo 30'));tap('Agregar paso');t=ready('Nueva rutina');check('Returning from a step preserves the typed routine name',bool(nodes(t,'Prueba visual beta8')))
 tap('Agregar paso');choice('Qué hacer','Controlar música');choice('Reproductor','TIDAL directo');choice('Control','Pausar');tap('Agregar paso');t=ready('Nueva rutina');check('Native media step retains explicit TIDAL pause',any('pausar' in n.get('text','').casefold() and 'tidal' in n.get('text','').casefold() for n in t.iter('node')))
 tap('Agregar paso');tap('Aplicación:',True);ready('ELIGE UNA OPCIÓN');tap('Buscar en las opciones');adb('shell','input','text','noresultbetaocho');t=ready('No hay coincidencias. Prueba otro nombre.');check('Native application menu filters and announces empty results',bool(nodes(t,'No hay coincidencias. Prueba otro nombre.')));screenshot('phone-empty-search.png')
 # Android first dismisses the soft keyboard when present, then our option sheet.
 for _ in range(3):
  adb('shell','input','keyevent','KEYCODE_BACK');t=tree()
  if not nodes(t,'ELIGE UNA OPCIÓN'):break
 check('Back after search keeps the underlying step draft',bool(nodes(t,'Qué hacer:',True)))
 tap('Aplicación:',True);ready('ELIGE UNA OPCIÓN');tap('Buscar en las opciones');adb('shell','input','text','TIDAL');ready('TIDAL');tap('TIDAL',option_only=True);ready('Aplicación: TIDAL');choice('Ventana','Maximizada');tap('Agregar paso');t=ready('Nueva rutina');check('App choice and window mode reach the routine summary',any('TIDAL' in n.get('text','') and 'Maximizada' in n.get('text','') for n in t.iter('node')));screenshot('phone-routine.png')
 tap('Cerrar');ready('Tus rutinas');check('Discarding this test draft does not alter the saved profile',profile.read_bytes()==before);tap('Inicio');ready('Hola, Eddy.')
 apk=adb('shell','pm','path','com.eddy.deck').strip().removeprefix('package:');sha=adb('shell','sha256sum',apk).split()[0];assert sha==hashlib.sha256((ROOT/'artifacts/EddyDeck-Android.apk').read_bytes()).hexdigest()
 report={'version':VERSION,'passed':True,'pickerObserved':True,'backPreservesForm':True,'searchObserved':True,'draftPreserved':True,'profilePreserved':True,'installedApkSHA256':sha,'checks':checks,'count':len(checks),'scope':'Real Samsung taps and fresh accessibility snapshots, no routine executed or saved and no Windows media/power actions. Android keyboard may consume Back before the custom picker.'}
 (ROOT/'artifacts/beta8-phone-design-tests.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
