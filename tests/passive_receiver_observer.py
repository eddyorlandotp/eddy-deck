"""Observe only the installed Eddy Deck and authorized phone; no commands/settings.

Maintenance annotations are kept in every sample, never used to erase failures.
"""
import argparse,datetime as dt,hashlib,json,math,os,re,socket,ssl,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ADB=ROOT/'.build/tools/platform-tools/platform-tools/adb.exe'
DATA=Path(os.environ['LOCALAPPDATA'])/'EddyDeck'

def main():
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,required=True);p.add_argument('--report',default='beta4-installed-observation.json');a=p.parse_args()
    if not 60<=a.seconds<=10800 or not re.fullmatch(r'beta\d+-[a-z0-9-]+\.json',a.report):raise ValueError('Invalid observation bounds')
    output=ROOT/'artifacts'/a.report;started=time.monotonic();samples=[]
    def adb(*args):return subprocess.run([str(ADB),'-s','ANDROID_SERIAL_HERE','shell',*args],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True,timeout=15).stdout
    while True:
        sample={'atUTC':dt.datetime.now(dt.timezone.utc).isoformat(),'elapsedSeconds':round(time.monotonic()-started,1),'maintenance':''}
        note=ROOT/'.build/observation-maintenance.json'
        if note.exists():
            annotation=json.loads(note.read_text(encoding='utf-8'))
            if time.time()<annotation.get('untilEpoch',0):sample['maintenance']=annotation.get('reason','planned maintenance')
        try:
            runtime=json.loads((DATA/'runtime.json').read_text());last=max(runtime.get('recentClients',[]),key=lambda x:x['at'],default={})
            with urllib.request.urlopen('http://127.0.0.1:47989/health',timeout=3) as response:health=json.load(response)
            # Compare the loaded certificate with the existing on-disk identity.
            ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
            with socket.create_connection(('127.0.0.1',47990),timeout=3) as tcp:
                with ctx.wrap_socket(tcp,server_hostname='localhost') as tls:actual=hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest()
            expected=hashlib.sha256(ssl.PEM_cert_to_DER_cert((DATA/'server.crt').read_text()).__bytes__()).hexdigest()
            service=adb('dumpsys','activity','services','com.eddy.deck');power=adb('dumpsys','power');windows=adb('dumpsys','window')
            focus=re.search(r'mCurrentFocus=([^\n]+)',windows);hold=re.search(r'mHoldScreenWindow=([^\n]+)',windows);wake=re.search(r'mWakefulness=(\w+)',power)
            sample.update(receiverHealthy=health.get('healthy') is True,version=health.get('version'),runtimeAgeSeconds=round(time.time()-(DATA/'runtime.json').stat().st_mtime,1),receiverPid=runtime['pid'],certificateMatchesDisk=actual==expected,
              lastAuthenticatedSecondsAgo=round(time.time()-last['at'],1) if last else None,connectionRoute=last.get('via','unknown'),
              foregroundService='.ConnectionService' in service and 'isForeground=true' in service,
              ownAppForeground='com.eddy.deck/' in focus.group(1) if focus else None,ownAppHoldsScreen='com.eddy.deck/' in hold.group(1) if hold else False,
              phoneAwake=wake.group(1)=='Awake' if wake else None)
        except Exception as exc:sample['errorType']=type(exc).__name__
        issues=[]
        for key in ('receiverHealthy','certificateMatchesDisk','foregroundService'):
            if sample.get(key) is not True:issues.append(key)
        if sample.get('lastAuthenticatedSecondsAgo') is None or sample.get('lastAuthenticatedSecondsAgo',0)>90:issues.append('authenticationFreshness')
        if sample.get('runtimeAgeSeconds',100)>15:issues.append('runtimeFreshness')
        if sample.get('ownAppForeground') and (not sample.get('ownAppHoldsScreen') or not sample.get('phoneAwake')):issues.append('foregroundScreenHold')
        if 'errorType' in sample:issues.append('observationFailed')
        sample['issues']=issues;samples.append(sample)
        done=time.monotonic()-started>=a.seconds
        report={'status':'completed' if done else 'running','requestedSeconds':a.seconds,'elapsedSeconds':round(time.monotonic()-started,1),'samples':samples,
          'samplesWithIssues':sum(bool(s['issues']) for s in samples),'unplannedIssueSamples':sum(bool(s['issues']) and not s['maintenance'] for s in samples),
          'maintenanceSamples':sum(bool(s['maintenance']) for s in samples),'physicalCommandsSent':0,'settingsChanged':False,'scope':'Installed PC and phone over existing USB/Wi-Fi/private tunnel; no mobile-data or battery-saver claim'}
        if done:report['passedWithoutUnplannedIssues']=report['unplannedIssueSamples']==0
        temp=output.with_suffix('.tmp');temp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(output)
        if len(samples)%5==0 or done:print(json.dumps({k:v for k,v in report.items() if k!='samples'}),flush=True)
        if done:break
        time.sleep(min(30,max(0,a.seconds-(time.monotonic()-started))))
if __name__=='__main__':main()
