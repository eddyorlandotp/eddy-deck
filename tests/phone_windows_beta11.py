"""Physical Samsung window/repair controls with independent Windows observations."""
import json,sys,time,hashlib,urllib.request
from pathlib import Path
from phone_design_beta8 import tap,ready,tree,nodes,bounds,adb
from catalog_live import observed,identity,visible,g
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion import windows
from companion.layout import Windows
from companion.core import VERSION
DATA=Path.home()/'.eddydeck';checks=[]

def check(label,value=True):
 assert value,label
 checks.append(label);print(label,flush=True)

def wait(predicate):
 end=time.monotonic()+15
 while time.monotonic()<end:
  if predicate():return
  time.sleep(.1)
 raise AssertionError('Expected Windows state was not observed')

def control(title):
 tap('Inicio');tap('Mi PC');tap('Actualizar',first=True)
 for _ in range(9):
  t=tree();candidates=[]
  for n in nodes(t,title):
   # WebView flattens the row in Android accessibility. Match the observed
   # button to its title by horizontal separation and vertical overlap.
   tx1,ty1,tx2,ty2=bounds(n)
   for button in nodes(t,'Controlar'):
    x1,y1,x2,y2=bounds(button)
    if button.get('clickable')=='true' and x1>=tx2 and y1<ty2 and y2>ty1:candidates.append(button)
  candidates=list({id(n):n for n in candidates}.values())
  if len(candidates)==1:
   x1,y1,x2,y2=bounds(candidates[0])
   if x2>x1 and y1>=60 and y2<=1370:
    adb('shell','input','tap',(x1+x2)//2,(y1+y2)//2);ready('Controlar ventana');return
  adb('shell','input','swipe',500,1270,500,550,350)
 raise AssertionError('Could not uniquely reach owned window control')

def main():
 before=(DATA/'deck.json').read_bytes();apps,_=windows.scan(DATA);app=next(a for a in apps if a['name']=='Calculator');layout=Windows()
 assert not [w for w in layout.snapshot(apps) if app['id'] in w['appIds']],'Calculator must not preexist this test'
 windows.launch(app);found=[]
 for _ in range(100):
  found=[w for w in layout.snapshot(apps) if app['id'] in w['appIds']]
  if len(found)==1:break
  time.sleep(.1)
 assert len(found)==1
 row=found[0];hwnd=layout.leases[row['id']]['hwnd'];owner=observed()[hwnd];title=row['title']
 (ROOT/'.build/beta11-phone-window-owner.json').write_text(json.dumps({'hwnd':hwnd,'identity':owner}))
 try:
  control(title);tap('Proteger de Eddy Deck');t=ready('Quitar protección')
  check('Phone protection disables movement and normal close',all(nodes(t,label)[0].get('enabled')=='false' for label in ('Minimizar','Cerrar normalmente','Pantalla y tamaño')))
  tap('Quitar protección');ready('Proteger de Eddy Deck');tap('Minimizar');wait(lambda:g.IsIconic(hwnd));check('Phone minimizes the independently observed owned Calculator')
  control(title);tap('Restaurar');wait(lambda:not g.IsIconic(hwnd));check('Phone restores Calculator')
  control(title);tap('Pantalla y tamaño');ready('Mover ventana')
  for field,value in [('Pantalla','Derecha'),('Ventana','Maximizada')]:tap(field+':',True);ready('ELIGE UNA OPCIÓN');tap(value,option_only=True)
  tap('Aplicar');wait(lambda:g.GetWindowPlacement(hwnd)[1]==3)
  target=next(w for w in layout.snapshot(apps) if layout.leases[w['id']]['hwnd']==hwnd)
  from companion.layout import monitors,resolve_monitor
  expected,_=resolve_monitor({'monitor':'right','missing':'stop'},monitors())
  check('Phone custom layout picker moves and maximizes Calculator on right monitor',target['monitor']==expected['id'])
  control(title);tap('Cerrar normalmente');ready('Pedir cierre');tap('Pedir cierre');wait(lambda:not identity(hwnd,owner) or not visible(hwnd));check('Phone normal close affects its owned Calculator')
  tap('Inicio');tap('Comprobar archivos de Windows');ready('Comprobación de Eddy Deck');t=tree();check('Phone installation check reports verified signed files',any('archivos verificados' in n.get('text','') for n in t.iter('node')));tap('Cerrar')
  tap('Manual de usuario');ready('Manual de usuario');check('Embedded manual opens from phone',len(list(tree().iter('node')))>20);tap('Cerrar')
  # Confirm only Eddy Deck connection restart. No Windows restart, power or task termination.
  oldpid=json.loads((DATA/'runtime.json').read_text())['pid'];tap('Reiniciar conexión de Windows');ready('Reparar receptor de la PC');tap('Reparar receptor')
  end=time.monotonic()+60
  while time.monotonic()<end:
   try:
    current=json.loads((DATA/'runtime.json').read_text())
    if current['pid']!=oldpid:break
   except (OSError,ValueError):pass
   time.sleep(.2)
  assert current['pid']!=oldpid
  tap('Inicio');ready('Hola, Eddy.');tap('Comprobar archivos de Windows');ready('Comprobación de Eddy Deck');tap('Cerrar');check('Phone reconnects after its explicit receiver repair and sends a new verified request')
  check('Profile and routines unchanged',before==(DATA/'deck.json').read_bytes());tap('Inicio')
  apk=adb('shell','pm','path','com.eddy.deck').strip().removeprefix('package:');sha=adb('shell','sha256sum',apk).split()[0];assert sha==hashlib.sha256((ROOT/'artifacts/EddyDeck-Android.apk').read_bytes()).hexdigest()
  (ROOT/'artifacts/beta11-phone-windows-tests.json').write_text(json.dumps({'version':VERSION,'passed':True,'checks':checks,'count':len(checks),'installedApkSHA256':sha,'originalProfilePreserved':True,'ownedCalculatorClosed':True,'scope':'Actual phone taps; independent HWND/monitor/profile/receiver PID observations. No power action, document decision or unrelated process termination.'},ensure_ascii=False,indent=2),encoding='utf-8')
 finally:
  if identity(hwnd,owner) and visible(hwnd):g.PostMessage(hwnd,0x10,0,0)

if __name__=='__main__':main()
