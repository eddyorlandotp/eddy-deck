"""Run the authorized foreground lifecycle check and retain structured evidence.
The test pauses for user navigation. Only a successful foreground completion
reopens Eddy Deck after Android ends instrumentation and stops its test process.
"""
import datetime as dt,json,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ADB=ROOT/'.build/tools/platform-tools/platform-tools/adb.exe'

def adb(*args):return subprocess.run([str(ADB),'-s','ANDROID_SERIAL_HERE',*args],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True,timeout=20).stdout
def note(seconds,reason):
    (ROOT/'.build/observation-maintenance.json').write_text(json.dumps({'untilEpoch':time.time()+seconds,'reason':reason}),encoding='utf-8')
def main():
    focus=adb('shell','dumpsys','window')
    if not re.search(r'mCurrentFocus=.*com\.eddy\.deck/',focus):raise RuntimeError('Leave Eddy Deck foreground before starting this test; no navigation forced.')
    version=re.search(r'versionName=([^\s]+)',adb('shell','dumpsys','package','com.eddy.deck')).group(1)
    note(60,'Inicio autorizado de instrumentacion Android; se reinicia solo su proceso')
    started=dt.datetime.now(dt.timezone.utc).isoformat();report=None
    command=[str(ADB),'-s','ANDROID_SERIAL_HERE','shell','am','instrument','-w','-e','mode','lifecycle','-e','cycles','120','-e','pauseMillis','30000','com.eddy.deck.tests/com.eddy.deck.ConnectionTests']
    with (ROOT/'artifacts/beta4-lifecycle-soak-device.txt').open('w',encoding='utf-8') as log:
        child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=0x08000000)
        for line in child.stdout:
            log.write(line);log.flush()
            try:value=json.loads(line[line.index('{'):])
            except (ValueError,TypeError):continue
            if value.get('cycle')==120:note(60,'Fin de instrumentacion Android; reapertura de Eddy Deck tras completar el ensayo')
            if 'passed' in value and 'cycles' in value:report=value
            if value.get('cycle',0)%10==0:print(json.dumps({k:v for k,v in value.items() if k not in ('observations','checks')}),flush=True)
        child.wait();child.stdout.close()
    if report is None:raise RuntimeError('Lifecycle run incomplete; raw output retained, no successful result created.')
    report.update(installedAndroidVersion=version,startedAtUTC=started,finishedAtUTC=dt.datetime.now(dt.timezone.utc).isoformat(),elapsedSeconds=round(report['elapsedMillis']/1000,3))
    (ROOT/'artifacts/beta4-lifecycle-soak-tests.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if not report.get('passed'):raise RuntimeError('Lifecycle run failed')
    adb('shell','am','start','-n','com.eddy.deck/.MainActivity')
    print(json.dumps({k:v for k,v in report.items() if k!='observations'}),flush=True)

if __name__=='__main__':main()
