"""Passive observation of the installed receiver and Samsung foreground service.
No commands are sent through Eddy Deck, no power/network settings are changed.
"""
import argparse,json,os,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ADB=ROOT/'.build/tools/platform-tools/platform-tools/adb.exe'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=2400);args=parser.parse_args()
    if not 60<=args.seconds<=14400:raise ValueError('Observation duration out of bounds')
    start=time.monotonic();samples=[];errors=[]
    output=ROOT/'artifacts/beta2-background-tests.json'
    def adb(*cmd):return subprocess.run([str(ADB),'-s','ANDROID_SERIAL_HERE','shell',*cmd],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15,check=True).stdout
    while True:
        elapsed=time.monotonic()-start
        try:
            runtime=json.loads((Path(os.environ['LOCALAPPDATA'])/'EddyDeck/runtime.json').read_text())
            last=max(runtime.get('recentClients',[]),key=lambda c:c['at'],default={})
            service=adb('dumpsys','activity','services','com.eddy.deck')
            power=adb('dumpsys','power')
            screen=re.search(r'mWakefulness=(\w+)',power)
            sample={'elapsedSeconds':round(elapsed,1),'phoneLastAuthenticatedSecondsAgo':round(time.time()-last.get('at',0),1),'connectionRoute':last.get('via','unknown'),'receiverPid':runtime['pid'],'foregroundService':'.ConnectionService' in service and 'isForeground=true' in service,'phoneWakefulness':screen.group(1) if screen else 'unknown','phonePowered':'mIsPowered=true' in power}
            samples.append(sample)
        except Exception as e:errors.append({'elapsedSeconds':round(elapsed,1),'errorType':type(e).__name__})
        done=time.monotonic()-start>=args.seconds
        report={'requestedSeconds':args.seconds,'elapsedSeconds':round(time.monotonic()-start,1),'status':'completed' if done else 'running','samples':samples,'errors':errors,'physicalCommandsSent':0,'networkSettingsChanged':False,'batterySaverNotTested':True}
        if samples:
            report.update(maxAuthenticatedGapSeconds=max(s['phoneLastAuthenticatedSecondsAgo'] for s in samples),foregroundServiceInactiveSamples=sum(not s['foregroundService'] for s in samples),receiverProcessesObserved=len({s['receiverPid'] for s in samples}))
        if done:report['passed']=not errors and bool(samples) and report['maxAuthenticatedGapSeconds']<90 and report['foregroundServiceInactiveSamples']==0
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if len(samples)%5==0 or done:print(json.dumps({k:v for k,v in report.items() if k not in ('samples',)}),flush=True)
        if done:break
        time.sleep(min(30,max(0,args.seconds-(time.monotonic()-start))))
if __name__=='__main__':main()
