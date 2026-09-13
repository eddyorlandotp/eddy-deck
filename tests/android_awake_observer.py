"""Observe own Android foreground wake request past a shortened idle timeout.
Restores the exact system timeout in finally; HOME is used only with our own app
still focused, then our app is brought back immediately. No unlock is attempted.
"""
import argparse,json,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ADB=ROOT/'.build/tools/platform-tools/platform-tools/adb.exe'

def run(*args):
    return subprocess.check_output([str(ADB),'-s','ANDROID_SERIAL_HERE','shell',*args],text=True,encoding='utf-8',errors='replace',timeout=20).strip()

def sample():
    w=run('dumpsys','window');p=run('dumpsys','power')
    focus=next((s for s in w.splitlines() if 'mCurrentFocus=' in s),'')
    holds=[s for s in w.splitlines() if 'mHoldScreenWindow=' in s]
    power=re.search(r'mWakefulness=(\w+)',p)
    return {'focusKnown':bool(focus),'ownFocused':'com.eddy.deck' in focus,'ownHoldsScreen':any('com.eddy.deck' in s for s in holds),'wakefulness':power.group(1) if power else None}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=35);parser.add_argument('--report',default='beta3-phone-awake-observation.json');args=parser.parse_args()
    if Path(args.report).name!=args.report:raise ValueError('Report must be a filename')
    before=sample();assert before['ownFocused'] and before['ownHoldsScreen'],'Unlock and open Eddy Deck first'
    original=run('settings','get','system','screen_off_timeout');assert original.isdigit()
    report={'originalTimeoutMs':int(original),'testTimeoutMs':15000,'samples':[],'passed':False,'timeoutRestored':False}
    target=ROOT/'artifacts'/args.report
    try:
        run('settings','put','system','screen_off_timeout','15000')
        assert run('settings','get','system','screen_off_timeout')=='15000'
        started=time.monotonic()
        while time.monotonic()-started<args.seconds:
            s=sample();s['elapsedSeconds']=round(time.monotonic()-started,1);report['samples'].append(s)
            assert s['ownFocused'] and s['ownHoldsScreen'] and s['wakefulness']=='Awake',s
            time.sleep(5)
        report['foregroundSeconds']=round(time.monotonic()-started,1)
    finally:
        run('settings','put','system','screen_off_timeout',original)
        report['timeoutRestored']=run('settings','get','system','screen_off_timeout')==original
        target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert report['timeoutRestored'] and sample()['ownFocused']
    try:
        run('input','keyevent','3');time.sleep(1)
        background=sample();report['background']=background
        assert not background['ownFocused'] and not background['ownHoldsScreen']
    finally:
        run('am','start','-n','com.eddy.deck/.MainActivity');time.sleep(1)
        report['returnedToApp']=sample()
        target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert report['returnedToApp']['ownFocused'] and report['returnedToApp']['ownHoldsScreen']
    report['passed']=True;target.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
