"""Verify exports actually created by Android's document picker, not copied by ADB."""
import hashlib,json,re,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.core import VERSION
from tidal_phone import adb
from phone_visible_beta7 import scroll_to,tap,dump
def tree():
 for _ in range(4):
  target='/sdcard/eddy-export-'+str(time.time_ns())+'.xml'
  try:response=adb('shell','uiautomator','dump',target)
  except __import__('subprocess').CalledProcessError as exc:
   if exc.returncode!=137:raise
   continue
  if 'dumped' not in response.lower():continue
  raw=adb('shell','cat',target);adb('shell','rm',target);return ET.fromstring(raw)
 raise RuntimeError('No fresh Android picker snapshot')
def click_node(n):
 x1,y1,x2,y2=map(int,re.findall(r'\d+',n.get('bounds','')));assert x2>x1 and y2>y1
 adb('shell','input','tap',(x1+x2)//2,(y1+y2)//2)
def main():
 progress=ROOT/'.build/beta11-native-exports-progress.json';reports=json.loads(progress.read_text()) if progress.exists() else []
 for kind,label,source in [('documentation','Guardar manual e informes',ROOT/'.build/android/assets/EddyDeck-Documentacion.zip'),('installer','Guardar instalador Windows',ROOT/'.build/android/assets/EddyDeck-Windows.zip')]:
  expected_hash=hashlib.sha256(source.read_bytes()).hexdigest()
  if any(r['kind']==kind and r['sha256']==expected_hash for r in reports):continue
  reports=[r for r in reports if r['kind']!=kind]
  tap('Inicio')
  if kind=='installer':tap('Mis PCs');tap('Llevar instalador');tap(label)
  else:scroll_to(label)
  t=tree();assert any('documentsui' in n.get('package','') for n in t.iter('node')),'Expected Android document picker'
  edits=[n for n in t.iter('node') if n.get('class')=='android.widget.EditText'];assert len(edits)==1
  name='EddyDeck-'+kind+'-'+VERSION+'-PruebaUI-'+expected_hash[:8]+'.zip'
  click_node(edits[0]);adb('shell','input','keycombination','113','29');adb('shell','input','text',name)
  t=tree();edits=[n for n in t.iter('node') if n.get('class')=='android.widget.EditText'];assert len(edits)==1 and edits[0].get('text')==name,'Filename edit failed; no save performed'
  saves=[n for n in t.iter('node') if n.get('text','').casefold() in ('guardar','save') and n.get('clickable')=='true' and n.get('enabled')=='true'];assert len(saves)==1
  click_node(saves[0]);deadline=time.monotonic()+40
  while time.monotonic()<deadline:
   t=tree();ok=[n for n in t.iter('node') if n.get('text','').casefold() in ('aceptar','ok','entendido') and n.get('clickable')=='true']
   if ok:
    expected='Manual e informes guardados' if kind=='documentation' else 'Instalador guardado'
    assert any(n.get('text')==expected for n in t.iter('node')),'Native app reported an unexpected result'
    click_node(ok[0]);break
   time.sleep(.3)
  else:raise AssertionError('Native save did not confirm completion')
  paths=adb('shell','find','/sdcard/Download','-type','f','-name',name).strip().splitlines();assert len(paths)==1,paths
  actual=adb('shell','sha256sum',paths[0]).split()[0];assert actual==hashlib.sha256(source.read_bytes()).hexdigest()
  reports.append({'kind':kind,'path':paths[0],'sha256':actual,'nativePicker':True,'matchesEmbeddedAsset':True});progress.write_text(json.dumps(reports));print(kind+' native export verified',flush=True)
  # Close only our instructional modal if it remains open.
  from tidal_phone import matches
  if matches(dump(),'Cerrar'):tap('Cerrar')
 apk=adb('shell','pm','path','com.eddy.deck').strip().removeprefix('package:');actual=adb('shell','sha256sum',apk).split()[0];assert actual==hashlib.sha256((ROOT/'artifacts/EddyDeck-Android.apk').read_bytes()).hexdigest()
 (ROOT/'artifacts/beta11-native-exports.json').write_text(json.dumps({'version':VERSION,'passed':True,'files':reports,'installedApkSHA256':actual},indent=2))
 p=ROOT/'artifacts/beta11-phone-visible-tests.json';r=json.loads(p.read_text());r['exportsVerified']=True;r['exportReport']='beta11-native-exports.json';p.write_text(json.dumps(r,indent=2));tap('Inicio')
if __name__=='__main__':main()
