"""Observe actual Windows volume-down/up and restore the original endpoint.
No playback, song changes, device selection, lock, sleep or shutdown is performed.
"""
import json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion import windows

def main():
    probe=ROOT/'.build/AudioProbe.exe';csc=Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe')
    subprocess.run([str(csc),'/nologo','/out:'+str(probe),str(ROOT/'tests/AudioProbe.cs')],check=True,capture_output=True,timeout=30)
    process=subprocess.Popen([str(probe)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=0x08000000)
    observations=[];report={'scope':'Real Windows adapter plus independent Core Audio endpoint observation','playbackCommands':0}
    def read():
        line=process.stdout.readline()
        if not line:raise RuntimeError('Audio probe ended: '+process.stderr.read())
        return json.loads(line)
    def sample():process.stdin.write('sample\n');process.stdin.flush();return read()
    before=read();report['before']=before
    try:
        if before['mute'] or before['volume']<.03:
            report.update(status='notRun',reason='The endpoint was muted or already near zero; preserved unchanged.')
        else:
            process.stdin.write('arm\n');process.stdin.flush();assert process.stdout.readline().strip()=='armed'
            windows.media('volume_down','system',[]);time.sleep(.6);lower=sample();observations.append(lower)
            assert lower['sameEndpoint'],'Endpoint changed during test; stop without further media keys'
            assert lower['volume']<before['volume'],'No volume decrease observed'
            windows.media('volume_up','system',[]);time.sleep(.6);higher=sample();observations.append(higher)
            assert higher['sameEndpoint'],'Endpoint changed during test'
            assert higher['volume']>lower['volume'],'No volume increase observed'
            report.update(status='passed',downObserved=True,upObserved=True)
    finally:
        process.stdin.write('done\n');process.stdin.flush();process.stdin.close()
        tail=process.stdout.read();error=process.stderr.read();process.wait(timeout=10)
        if tail:report['restored']=json.loads(tail.strip().splitlines()[-1])
        else:report['restored']=before
        report['observations']=observations
        report['initialLevelAndMuteRestored']=abs(report['restored']['volume']-before['volume'])<.0001 and report['restored']['mute']==before['mute']
        report['probeExitCode']=process.returncode
        (ROOT/'artifacts/beta4-system-volume-live.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        assert report['initialLevelAndMuteRestored'] and process.returncode==0,error
    print(json.dumps(report))
if __name__=='__main__':main()
