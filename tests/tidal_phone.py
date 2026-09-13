"""Touch real Eddy Deck controls on the authorized Samsung; observe TIDAL separately."""
import hashlib,json,os,re,subprocess,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion import tidal,windows
from companion.core import VERSION
from tidal_live import progress
ADB=ROOT/'.build/tools/platform-tools/platform-tools/adb.exe'
HELPER=Path(os.environ['LOCALAPPDATA'])/'Programs/EddyDeck/EddyDeck-Tidal.exe'

def adb(*args):return subprocess.run([str(ADB),'-s','ANDROID_SERIAL_HERE',*map(str,args)],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True,timeout=20).stdout
def dump():
    adb('shell','uiautomator','dump','/sdcard/eddy-ui.xml')
    xml=adb('shell','cat','/sdcard/eddy-ui.xml');root=ET.fromstring(xml)
    if not any(n.get('package')=='com.eddy.deck' for n in root.iter('node')):raise RuntimeError('Eddy Deck is not the current phone app')
    return root
def matches(root,label):
    return [n for n in root.iter('node') if (n.get('text')==label or n.get('content-desc')==label or n.get('resource-id')==label)]
def tap(label):
    found=matches(dump(),label);found=[n for n in found if n.get('clickable')=='true' and n.get('enabled')=='true']
    visible=[]
    for n in found:
        x1,y1,x2,y2=map(int,re.findall(r'\d+',n.get('bounds','')))
        if x2>x1 and y2>y1:visible.append(((x1+x2)//2,(y1+y2)//2))
    if len(visible)!=1:raise RuntimeError('Expected one visible control: '+label)
    adb('shell','input','tap',*visible[0])
def state(apps):
    lease=tidal.target(apps);p=lease['process']
    r=subprocess.run([str(HELPER),str(lease['hwnd']),str(p['pid']),str(p['created']),p['path'],'status'],capture_output=True,text=True,encoding='utf-8-sig',check=True,timeout=8)
    return json.loads(r.stdout)['state']
def expect_state(apps,expected):
    until=time.monotonic()+12
    while time.monotonic()<until:
        if state(apps)==expected:return
        time.sleep(.3)
    raise RuntimeError('Actual TIDAL did not become '+expected)
def visible_state(label):
    until=time.monotonic()+12
    while time.monotonic()<until:
        if matches(dump(),label):return
    raise RuntimeError('Phone did not show '+label)
def main():
    apps,_=windows.scan(ROOT);lease=tidal.target(apps);checks=[]
    assert VERSION in adb('shell','dumpsys','package','com.eddy.deck')
    assert HELPER.read_bytes()==(ROOT/'artifacts/windows/EddyDeck/EddyDeck-Tidal.exe').read_bytes()
    assert state(apps)=='paused','Begin with TIDAL paused; do not invert unknown state'
    report={'version':VERSION,'checks':checks,'installedHelperMatches':True,'testType':'Actual taps on Samsung, installed Windows helper readback and separate UI Automation timeline; no tracks stored'}
    def playback(name):
        visible_state('En pausa');tap('Reproducir o pausar');expect_state(apps,'playing');visible_state('Reproduciendo')
        tap('Reproducir o pausar');expect_state(apps,'paused');visible_state('En pausa')
        before=progress(lease['hwnd']);time.sleep(2.2);after=progress(lease['hwnd']);assert abs(before-after)<.001
        checks.append(name+' plays then pauses; actual TIDAL timeline remains still');print(checks[-1],flush=True)
    tap('Inicio');playback('Home');report['homePaused']=True
    tap('Música');playback('Music automatic');report['musicAutoPaused']=True
    # Native select dialog is inspected separately before choosing its visible label.
    tap('media-target');root=dump()
    option=[n for n in root.iter('node') if n.get('text')=='TIDAL · control directo']
    if len(option)!=1:raise RuntimeError('TIDAL selection was not available')
    x1,y1,x2,y2=map(int,re.findall(r'\d+',option[0].get('bounds','')));assert x2>x1 and y2>y1
    adb('shell','input','tap',(x1+x2)//2,(y1+y2)//2)
    playback('Music direct');report['musicDirectPaused']=True
    # Scroll content above the fixed navigation bar before touching pause.
    adb('shell','input','swipe',360,1200,360,700,350)
    for _ in range(2):tap('Pausar');expect_state(apps,'paused')
    checks.append('Repeated explicit pause remains paused')
    tap('Inicio');report.update(passed=True,timelineStopped=True,finalState=state(apps),appClosed=False,count=len(checks))
    assert report['finalState']=='paused'
    (ROOT/'artifacts/beta6-tidal-phone-tests.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
