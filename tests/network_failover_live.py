"""Bounded Samsung Wi-Fi/USB failover observation; no PC action commands.
Restores Wi-Fi and the original USB reverse even if a phase fails.
Run only with the user's authorized phone connected and an existing USB reverse.
"""
import datetime as dt,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ADB=ROOT/'.build/tools/platform-tools/platform-tools/adb.exe';DATA=Path(os.environ['LOCALAPPDATA'])/'EddyDeck'
sys.path.insert(0,str(ROOT))
from companion.core import VERSION

def main():
    def adb(*args):
        result=subprocess.run([str(ADB),'-s','ANDROID_SERIAL_HERE',*args],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15,check=True)
        return result.stdout
    def state():
        runtime=json.loads((DATA/'runtime.json').read_text());return max(runtime.get('recentClients',[]),key=lambda c:c['at'],default={})
    def wait_route(allowed,since,seconds=45):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            current=state()
            if current.get('at',0)>since and current.get('via') in allowed:return {'route':current['via'],'elapsedSeconds':round(seconds-(end-time.monotonic()),2)}
            time.sleep(.5)
        raise AssertionError('No fresh authenticated route observed within bounded phase')
    assert 'tcp:47990 tcp:47990' in adb('reverse','--list'),'Existing USB reverse required'
    assert 'enabled' in adb('shell','cmd','wifi','status').splitlines()[0].lower(),'Start only with Wi-Fi already enabled'
    fields=('deck.json','devices.json','server.crt');before={name:hashlib.sha256((DATA/name).read_bytes()).hexdigest() for name in fields}
    version=re.search(r'versionName=([^\s]+)',adb('shell','dumpsys','package','com.eddy.deck'))
    report={'startedAtUTC':dt.datetime.now(dt.timezone.utc).isoformat(),'installedAndroidVersion':version.group(1) if version else 'unknown','physicalPCCommands':0,'mobileDataTested':False,'phases':[],'status':'running'}
    marker=ROOT/'.build/observation-maintenance.json';marker.write_text(json.dumps({'untilEpoch':time.time()+150,'reason':'Prueba autorizada de perdida de Wi-Fi, alternativa USB y recuperacion Wi-Fi'}),encoding='utf-8')
    try:
        began=time.time();adb('shell','svc','wifi','disable')
        report['phases'].append({'phase':'Wi-Fi disabled; existing USB remains',**wait_route({'USB'},began)})
        adb('shell','svc','wifi','enable');time.sleep(8)
        began=time.time();adb('reverse','--remove','tcp:47990')
        report['phases'].append({'phase':'USB reverse briefly removed; Wi-Fi restored',**wait_route({'Wi-Fi','Internet / VPN'},began)})
        report['status']='passed'
    except Exception as exc:report.update(status='failed',errorType=type(exc).__name__,message=str(exc));raise
    finally:
        restore=[]
        for args in [('shell','svc','wifi','enable'),('reverse','tcp:47990','tcp:47990')]:
            try:adb(*args);restore.append(True)
            except Exception:restore.append(False)
        report['wifiEnableAndUsbReverseRestored']=all(restore)
        report['personalProfilePairingsAndCertificateUnchanged']=before=={name:hashlib.sha256((DATA/name).read_bytes()).hexdigest() for name in fields}
        report['completedAtUTC']=dt.datetime.now(dt.timezone.utc).isoformat()
        marker.write_text(json.dumps({'untilEpoch':0,'reason':'Prueba de red terminada; ajustes restaurados'}),encoding='utf-8')
        (ROOT/'artifacts'/('beta'+VERSION.rsplit('beta.',1)[-1]+'-network-failover-live.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
        assert all(restore),'Network restoration needs attention'
        assert report['personalProfilePairingsAndCertificateUnchanged'],'Unexpected personal state change'
    print(json.dumps(report))
if __name__=='__main__':main()
