"""Actual Samsung taps; independent Windows observations, no profile mutation."""
import hashlib,json,os,re,sys,time,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion import windows,tidal,media_sessions
from companion.core import VERSION
from tidal_phone import adb,matches
from tidal_live import progress
def dump():
 for _ in range(4):
  target='/sdcard/eddy-beta7-'+str(time.time_ns())+'.xml'
  try:response=adb('shell','uiautomator','dump',target)
  except subprocess.CalledProcessError as exc:
   if exc.returncode!=137:raise
   continue
  if 'dumped' not in response.lower():continue
  raw=adb('shell','cat',target);adb('shell','rm',target);root=ET.fromstring(raw)
  if any(n.get('package')=='com.eddy.deck' for n in root.iter('node')):return root
 raise RuntimeError('No fresh Eddy Deck accessibility snapshot')
def tap(label):
 for _ in range(4):
  nodes=[n for n in matches(dump(),label) if n.get('clickable')=='true' and n.get('enabled')=='true'];points=[]
  for n in nodes:
   x1,y1,x2,y2=map(int,re.findall(r'\d+',n.get('bounds','')))
   if x2>x1 and y2>y1:points.append(((x1+x2)//2,(y1+y2)//2))
  if len(points)==1:adb('shell','input','tap',*points[0]);return
 raise RuntimeError('Expected one fresh visible control: '+label)
def pick(label):
 from phone_design_beta8 import tap as touch,ready
 touch('Reproductor:',True);ready('ELIGE UNA OPCIÓN');touch(label,option_only=True)

def scroll_to(label,activate=True):
 for _ in range(6):
  current=dump();nav=matches(current,'Inicio');bottom=min(int(re.findall(r'\d+',n.get('bounds',''))[1]) for n in nav)
  for n in matches(current,label):
   x1,y1,x2,y2=map(int,re.findall(r'\d+',n.get('bounds','')))
   if x2>x1 and y2>y1 and y1>180 and y2<bottom:
    if activate:adb('shell','input','tap',(x1+x2)//2,(y1+y2)//2)
    return
  adb('shell','input','swipe',500,bottom-100,500,550,350)
 raise RuntimeError('Cannot find '+label)
def main():
 apps,_=windows.scan(ROOT);lease=tidal.target(apps);player=next(p['id'] for p in media_sessions.snapshot(apps,fresh=True)['players'] if p['source']=='Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic');checks=[]
 installed=Path(os.environ['LOCALAPPDATA'])/'Programs/EddyDeck'
 assert VERSION in adb('shell','dumpsys','package','com.eddy.deck')
 for helper in ('EddyDeck-Tidal.exe','EddyDeck-Media.exe'):assert (installed/helper).read_bytes()==(ROOT/'artifacts/windows/EddyDeck'/helper).read_bytes()
 def observed(target):return tidal.snapshot(apps,fresh=True) if target=='tidal' else windows.aimp_snapshot(apps) if target=='aimp' else media_sessions.invoke('status',target)
 def wait(target,state):
  end=time.monotonic()+14
  while time.monotonic()<end:
   if observed(target)['state']==state:return
   time.sleep(.2)
  raise AssertionError('Phone action did not produce '+state+' on '+target)
 def ready(label):
  end=time.monotonic()+15
  while time.monotonic()<end:
   if matches(dump(),label):return
  raise AssertionError('Phone did not show '+label)
 def check(name):checks.append(name);print(name,flush=True)
 old_volume=windows.aimp_snapshot(apps)['volume']
 try:
  ready('Música')
  for target in ('tidal','aimp',player):windows.media('pause',target,apps)
  for target,label in [('tidal','TIDAL · control directo'),('aimp','AIMP · control directo'),(player,'Media Player · sesión de Windows')]:
   tap('Música');pick(label);ready('Detenido' if observed(target)['state']=='stopped' else 'En pausa');tap('Reproducir o pausar');wait(target,'playing');ready('Reproduciendo');tap('Reproducir o pausar');wait(target,'paused');ready('En pausa')
   before=progress(lease['hwnd']) if target=='tidal' else windows.aimp_snapshot(apps)['position'] if target=='aimp' else None;time.sleep(1.3)
   assert observed(target)['state']=='paused'
   if before is not None:assert (progress(lease['hwnd']) if target=='tidal' else windows.aimp_snapshot(apps)['position'])==before
   check(label+': phone play and pause change the actual player; playback remains paused')
   scroll_to('Pausar' if target!='aimp' else 'Detener');wait(target,'paused' if target!='aimp' else 'stopped');check(label+': secondary pause/stop has its actual effect')
   if target=='aimp':
    scroll_to('aimp-volume',False)
    nodes=matches(dump(),'aimp-volume');assert len(nodes)==1
    x1,y1,x2,y2=map(int,re.findall(r'\d+',nodes[0].get('bounds','')));assert x2>x1 and y2>y1
    adb('shell','input','swipe',(x1+x2)//2,(y1+y2)//2,x1+(x2-x1)//3,(y1+y2)//2,500);time.sleep(2)
    value=windows.aimp_snapshot(apps)['volume'];assert value!=old_volume and 0<=value<=100
    check('AIMP slider on Samsung changes real AIMP volume');windows.media('volume','aimp',apps,old_volume)
  # Actual global controls from the phone, read independently and restored.
  tap('Inicio');audio=subprocess.Popen([str(ROOT/'.build/AudioProbe.exe')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=0x08000000)
  original=json.loads(audio.stdout.readline())
  def sample_audio():audio.stdin.write('sample\n');audio.stdin.flush();return json.loads(audio.stdout.readline())
  def wait_audio(predicate):
   end=time.monotonic()+12
   while time.monotonic()<end:
    value=sample_audio();assert value['sameEndpoint']
    if predicate(value):return value
    time.sleep(.2)
   raise AssertionError('Phone audio command did not produce the expected endpoint change')
  try:
   audio.stdin.write('arm\n');audio.stdin.flush();assert audio.stdout.readline().strip()=='armed'
   scroll_to('Menos volumen');lower=wait_audio(lambda v:v['volume']<original['volume'] or original['volume']==0)
   scroll_to('Más volumen');higher=wait_audio(lambda v:v['volume']>lower['volume']);check('Phone Windows volume down/up changes the independently observed endpoint')
   before_mute=sample_audio()['mute'];scroll_to('Silenciar / activar sonido');wait_audio(lambda v:v['mute']!=before_mute)
   scroll_to('Silenciar / activar sonido');wait_audio(lambda v:v['mute']==before_mute);check('Phone Windows mute and unmute both change the actual endpoint')
  finally:
   audio.stdin.write('done\n');audio.stdin.flush();audio.stdin.close();restored=json.loads(audio.stdout.read().strip().splitlines()[-1]);audio.wait(timeout=5);assert restored['mute']==original['mute'] and abs(restored['volume']-original['volume'])<.0001
  # Home is tested without pausing an unrelated browser session.
  windows.media('play','tidal',apps);tap('Inicio');time.sleep(2);auto=windows.media_snapshot(apps,fresh=True)['autoTarget']
  if auto=='ambiguous':
   tap('Reproducir o pausar');ready('Hay varios reproductores disponibles. Elige cuál controlar en Música.');assert observed('tidal')['state']=='playing';check('Home ambiguity reports the conflict and does not pause an arbitrary player')
  elif auto=='tidal':
   ready('Reproduciendo');tap('Reproducir o pausar');wait('tidal','paused');check('Home Auto pauses the actually playing TIDAL')
  else:raise AssertionError('Unexpected Auto selection during TIDAL playback')
 finally:
  for target in ('tidal','aimp',player):
   try:windows.media('pause',target,apps)
   except Exception:pass
  windows.media('volume','aimp',apps,old_volume)
 report={'version':VERSION,'passed':True,'tidalPaused':observed('tidal')['state']=='paused','aimpPaused':observed('aimp')['state'] in ('paused','stopped'),'mediaPlayerPaused':observed(player)['state']=='paused','helpersMatch':True,'exportsVerified':False,'checks':checks,'count':len(checks),'scope':'Actual UIAutomator-observed controls and ADB taps in installed Samsung app; independent Windows state/timeline. Export test is separate and merged after verification.'}
 apk=adb('shell','pm','path','com.eddy.deck').strip().removeprefix('package:');actual=adb('shell','sha256sum',apk).split()[0];assert actual==hashlib.sha256((ROOT/'artifacts/EddyDeck-Android.apk').read_bytes()).hexdigest();report['installedApkSHA256']=actual
 exports=ROOT/'artifacts/beta11-native-exports.json'
 if exports.exists():
  proof=json.loads(exports.read_text());report['exportsVerified']=proof.get('passed') is True and proof.get('installedApkSHA256')==actual
 (ROOT/'artifacts/beta11-phone-visible-tests.json').write_text(json.dumps(report,indent=2));tap('Inicio');print(json.dumps(report))
if __name__=='__main__':main()
