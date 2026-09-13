"""Real installed players. No track names saved. Leaves playback paused and volume intact."""
import hashlib,importlib.util,json,os,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion import windows,tidal,media_sessions
from companion.core import VERSION
from companion.layout import Windows
from scripts.package_evidence import product_sources
from tidal_live import progress
import win32gui

def compile_probe():
    fw=Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319');gac=Path('C:/Windows/Microsoft.NET/assembly/GAC_MSIL')
    refs=[*list((gac/'System.Runtime').rglob('System.Runtime.dll')),*list((gac/'System.Runtime.InteropServices.WindowsRuntime').rglob('*.dll')),*[Path('C:/Windows/System32/WinMetadata')/n for n in ('Windows.Media.winmd','Windows.Foundation.winmd')]]
    subprocess.run([str(fw/'csc.exe'),'/nologo','/r:System.Web.Extensions.dll',*['/r:'+str(p) for p in refs],'/out:'+str(ROOT/'.build/MediaReadProbe.exe'),str(ROOT/'tests/MediaReadProbe.cs')],check=True)
def probe(source):
    r=subprocess.run([str(ROOT/'.build/MediaReadProbe.exe')],capture_output=True,text=True,check=True,timeout=6)
    rows=[x for x in json.loads(r.stdout) if x['source']==source];assert len(rows)==1;return rows[0]
def main():
    compile_probe();apps,_=windows.scan(ROOT);checks=[];tidal_hwnd=tidal.target(apps)['hwnd'];source='Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic'
    player=next(p for p in media_sessions.snapshot(apps,fresh=True)['players'] if p['source']==source)['id']
    aimp_before=windows.aimp_snapshot(apps);assert aimp_before['aimp']
    if not aimp_before['duration']:
        windows.media('play','aimp',apps);windows.media('pause','aimp',apps);aimp_before=windows.aimp_snapshot(apps)
    assert aimp_before['duration']>0,'AIMP must have a loaded track for this playback test'
    def check(name,condition):assert condition,name;checks.append(name);print(name,flush=True)
    def call(action,target='system',value=None):return windows.media(action,target,apps,value)
    try:
        call('pause','tidal');call('pause','aimp');call('play',player)
        # Replay the previously delivered adapter to demonstrate the cross-player defect.
        archive=Path('C:/Users/Example/Desktop/Eddy Deck/Versiones/2.2.4-beta.6/EddyDeck-Codigo.zip')
        with zipfile.ZipFile(archive) as z:old=z.read('EddyDeck-Codigo/companion/windows.py')
        path=ROOT/'.build/beta6-original-windows.py';path.write_bytes(old)
        spec=importlib.util.spec_from_file_location('old_windows_adapter',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        wrong=module.media('pause','system',apps)
        check('Beta6 reproduction: Auto paused TIDAL while actual Media Player kept playing',probe(source)['state']=='playing' and wrong.get('player')=='tidal')
        current=windows.media_snapshot(apps,fresh=True)
        others=[p for p in current['players'] if p['id']!=player and p['state']=='playing']
        if others:
            check('Auto detects a concurrently playing browser session without touching it',current['autoTarget']=='ambiguous')
            try:call('pause')
            except ValueError:check('Ambiguous Auto rejects the command and preserves existing browser playback',True)
            else:raise AssertionError('Auto selected a player despite ambiguity')
            call('pause',player)
        else:
            check('Corrected Auto selects the actually playing Media Player',current['autoTarget']==player)
            call('pause')
        check('Media Player pauses with TIDAL and AIMP still open',probe(source)['state']=='paused')
        check('Repeated Media Player pause is idempotent',call('pause',player)['invoked'] is False)
        call('play',player);call('play','aimp')
        try:call('pause')
        except ValueError:check('Two simultaneously playing players require an explicit choice',True)
        else:raise AssertionError('Ambiguous Auto acted')
        call('pause',player);call('pause','aimp')
        call('volume','aimp',max(0,aimp_before['volume']-10));time.sleep(.3)
        check('AIMP volume slider changes real player volume',windows.aimp_snapshot(apps)['volume']==max(0,aimp_before['volume']-10))
        call('mute','aimp');time.sleep(.3);check('AIMP mute changes real mute state',windows.aimp_snapshot(apps)['mute']!=aimp_before['mute'])
        call('mute','aimp');time.sleep(.3);check('AIMP second mute restores the previous state',windows.aimp_snapshot(apps)['mute']==aimp_before['mute'])
        call('play','aimp');a=windows.aimp_snapshot(apps)['position'];time.sleep(1.3);b=windows.aimp_snapshot(apps)['position'];check('AIMP play advances the actual position',b>a)
        call('pause','aimp');a=windows.aimp_snapshot(apps)['position'];time.sleep(1.3);b=windows.aimp_snapshot(apps)['position'];check('AIMP pause stops the actual position',b==a)
        check('AIMP repeated pause cannot resume music',call('pause','aimp')['invoked'] is False)
        call('toggle','aimp');check('AIMP toggle resumes from paused',windows.aimp_snapshot(apps)['state']=='playing');call('toggle','aimp');check('AIMP toggle pauses from playing',windows.aimp_snapshot(apps)['state']=='paused')
        call('stop','aimp');check('AIMP stop resets playback to stopped',windows.aimp_snapshot(apps)['state']=='stopped')
        call('play','aimp');call('pause','aimp')
        layout=Windows();row=next(r for r in layout.snapshot(apps) if r['process'].lower()=='aimp.exe');hwnd=layout.leases[row['id']]['hwnd']
        def identity():return hashlib.sha256(win32gui.GetWindowText(hwnd).encode()).hexdigest(),windows.aimp_snapshot(apps)['duration']
        before=identity();call('next','aimp');time.sleep(1);after=identity();check('AIMP next changes current title fingerprint or duration',after!=before)
        call('previous','aimp')
        if identity()!=before:call('previous','aimp')
        check('AIMP previous returns to the prior fingerprint and duration',identity()==before);call('pause','aimp')
        call('play',player);before=probe(source)['trackHash'];call('next',player);time.sleep(.3);check('Media Player next changes observed media identity',probe(source)['trackHash']!=before)
        call('previous',player);time.sleep(.3);check('Media Player previous returns to fixture one',probe(source)['trackHash']==before);call('pause',player)
        def tidal_identity():
            return subprocess.run([str(ROOT/'.build/TidalIdentity.exe'),str(tidal_hwnd)],capture_output=True,text=True,check=True,timeout=6).stdout.strip()
        before=tidal_identity();result=call('next','tidal')
        check('TIDAL next changes independently observed footer identity',result.get('verified') and tidal_identity()!=before)
        call('pause','tidal');time.sleep(1.2)
        check('Immediate TIDAL pause after next stays paused',tidal.snapshot(apps)['state']=='paused')
        call('previous','tidal')
        if tidal_identity()!=before:call('previous','tidal')
        check('TIDAL previous returns to prior footer identity',tidal_identity()==before);call('pause','tidal')
        a=progress(tidal_hwnd);time.sleep(1.2);check('TIDAL remains paused after track navigation',progress(tidal_hwnd)==a)
    finally:
        for target in ('aimp','tidal',player):
            try:call('pause',target)
            except Exception:pass
        call('volume','aimp',aimp_before['volume'])
        if windows.aimp_snapshot(apps)['mute']!=aimp_before['mute']:call('mute','aimp')
    report={'version':VERSION,'passed':True,'count':len(checks),'checks':checks,'sourceHashes':product_sources(),'originalAimpVolumeRestored':windows.aimp_snapshot(apps)['volume']==aimp_before['volume'],'scope':'Actual AIMP 5.40, TIDAL 2.43.2 and Media Player 11.2606.19.0 on this PC. No raw track names stored. Legacy stopped at first-run privacy setup; not certified. Phone taps and Windows mute are separate.'}
    (ROOT/'artifacts/beta7-media-audit-live.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='sourceHashes'}))
if __name__=='__main__':main()
