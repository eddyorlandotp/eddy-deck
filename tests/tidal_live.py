"""Authorized real TIDAL playback tests. Leaves music paused and geometry intact."""
import argparse,hashlib,json,subprocess,sys,tempfile,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion import windows,tidal
from companion.core import Deck,VERSION
from scripts.package_evidence import product_sources
import win32gui

def progress(hwnd):
    r=subprocess.run([str(ROOT/'.build/TidalProgress.exe'),str(hwnd)],capture_output=True,text=True,encoding='utf-8-sig',check=True,timeout=5)
    return float(r.stdout)

def main():
    framework=Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319')
    subprocess.run([str(framework/'csc.exe'),'/nologo',*[f'/r:{framework/"WPF"/name}' for name in ('UIAutomationClient.dll','UIAutomationTypes.dll','WindowsBase.dll')],'/out:'+str(ROOT/'.build/TidalProgress.exe'),str(ROOT/'tests/TidalProgress.cs')],check=True)
    apps,_=windows.scan(ROOT);lease=tidal.target(apps)
    if lease is None:raise RuntimeError('TIDAL must already be open with a loaded song')
    hwnd=lease['hwnd'];placement=win32gui.GetWindowPlacement(hwnd);checks=[]
    def check(name,value):assert value,name;checks.append(name)
    with tempfile.TemporaryDirectory(prefix='eddy-tidal-live-') as folder:
        deck=Deck(folder,ROOT,adapter=windows);deck.apps=apps
        def call(action,target='system',rid=None):return deck.dispatch('/api/media',{'requestId':rid or uuid.uuid4().hex,'action':action,'target':target},'local')
        try:
            call('pause','tidal');check('Explicit TIDAL pause observed',tidal.invoke('status',apps)['state']=='paused')
            check('Repeated pause does not invoke play',call('pause','tidal')['invoked'] is False)
            call('play');check('Automatic target resumes TIDAL',tidal.invoke('status',apps)['state']=='playing')
            a=progress(hwnd);time.sleep(2.2);b=progress(hwnd);check('Actual TIDAL timeline changes while playing',b!=a)
            call('pause');check('Automatic target pauses TIDAL',tidal.invoke('status',apps)['state']=='paused')
            a=progress(hwnd);time.sleep(2.2);b=progress(hwnd);check('Actual TIDAL timeline stays still while paused',abs(b-a)<.001)
            call('play','tidal');check('Stop means verified pause in TIDAL',call('stop')['state']=='paused')
            rid=uuid.uuid4().hex;one=call('toggle','tidal',rid);two=call('toggle','tidal',rid)
            check('Same request replay does not toggle twice',one==two and tidal.invoke('status',apps)['state']=='playing');call('pause')
            deck.dispatch('/api/scenes/save',{'requestId':uuid.uuid4().hex,'name':'Isolated TIDAL check','steps':[{'type':'media','target':'tidal','action':'play'},{'type':'media','target':'tidal','action':'pause'}]},'local')
            job=deck.dispatch('/api/scenes/run',{'requestId':uuid.uuid4().hex,'id':deck.profile['scenes'][-1]['id']},'local')
            until=time.monotonic()+20
            while time.monotonic()<until:
                done=next(j for j in deck.journal.jobs() if j['id']==job['jobId'])
                if done['status'] not in ('running','queued'):break
                time.sleep(.1)
            check('Real routine plays then pauses TIDAL in sequence',done['status']=='completed' and tidal.invoke('status',apps)['state']=='paused')
            win32gui.ShowWindow(hwnd,6);call('play','tidal');call('pause','tidal')
            check('Minimized TIDAL can play and pause without reopening it',win32gui.IsIconic(hwnd) and tidal.invoke('status',apps)['state']=='paused')
            pid=lease['process'];helper=ROOT/'.build/EddyDeck-Tidal.exe'
            for field,values in [('pid',[str(pid['pid']+1),str(pid['created'])]),('creation-time',[str(pid['pid']),str(pid['created']+1)])]:
                r=subprocess.run([str(helper),str(hwnd),*values,pid['path'],'play'],capture_output=True,timeout=5)
                check('Changed '+field+' rejects control before invocation',r.returncode!=0 and tidal.invoke('status',apps)['state']=='paused')
        finally:
            try:call('pause','tidal')
            finally:win32gui.SetWindowPlacement(hwnd,placement);deck.close()
    check('Original window placement restored',win32gui.GetWindowPlacement(hwnd)==placement)
    report={'version':VERSION,'passed':True,'count':len(checks),'checks':checks,'finalState':'paused','appClosed':False,'testUsedPersonalProfile':False,'scope':'Real existing TIDAL through actual Deck media route; independent UI Automation timeline observations, no titles or track names stored. Isolated Deck receipts; installed-phone button test is separate.','helperSourceSHA256':hashlib.sha256((ROOT/'companion/TidalMedia.cs').read_bytes()).hexdigest()}
    report['sourceHashes']=product_sources()
    (ROOT/'artifacts/beta6-tidal-live-tests.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='sourceHashes'}))
if __name__=='__main__':main()
