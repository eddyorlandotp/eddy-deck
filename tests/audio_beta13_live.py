"""Opt-in hardware test: briefly selects each active output, restores all sound.
Does not start playback or change communications output. Do not run in CI.
"""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion import audio_output as audio
from scripts.package_evidence import product_sources

def probe():
 p=subprocess.Popen([str(ROOT/'.build/AudioProbe.exe')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=0x08000000)
 return p,json.loads(p.stdout.readline())
def command(p,value):
 p.stdin.write(value+'\n');p.stdin.flush();return p.stdout.readline().strip()
def main():
 subprocess.run(['C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe','/nologo','/out:'+str(ROOT/'.build/AudioProbe.exe'),str(ROOT/'tests/AudioProbe.cs')],capture_output=True,check=True,timeout=30)
 before=audio.invoke('list');original,originSample=probe();results=[];restored=False
 assert before['defaultId']==before['mediaDefaultId'],'Preserve distinct console/media roles; this fixture needs them initially equal'
 try:
  for row in before['outputs']:
   current=audio.invoke('list');audio.invoke('select',row['id'],expected=current['defaultId'])
   selected=audio.invoke('list');assert selected['defaultId']==row['id'] and selected['mediaDefaultId']==row['id'];assert selected['communicationsDefaultId']==before['communicationsDefaultId']
   assert json.loads(command(original,'sample'))['sameEndpoint']==(row['id']==before['defaultId'])
   p,old=probe();command(p,'arm')
   try:
    desired=max(0,round(old['volume']*100)-1)
    audio.control('volume',row['id'],desired);observed=json.loads(command(p,'sample'));assert abs(observed['volume']*100-desired)<1.1
    audio.control('mute',row['id'],not old['mute']);muted=json.loads(command(p,'sample'));assert muted['mute']!=old['mute']
    # The original endpoint's stale slider must not alter the new endpoint.
    if row['id']!=before['defaultId']:
     try:audio.control('volume',before['defaultId'],0);raise AssertionError('stale endpoint accepted')
     except RuntimeError as e:assert 'cambió' in str(e)
     check=json.loads(command(p,'sample'));assert check==muted
   finally:
    last=json.loads(command(p,'done'));p.stdin.close();p.wait(timeout=10)
    assert abs(last['volume']-old['volume'])<.0001 and last['mute']==old['mute'] and p.returncode==0
   results.append({'name':row['name'],'selectionObserved':True,'absoluteVolumeObserved':True,'muteObserved':True,'volumeAndMuteRestored':True})
 finally:
  current=audio.invoke('list');audio.invoke('select',before['defaultId'],expected=current['defaultId'])
  final=audio.invoke('list');observed=json.loads(command(original,'sample'));original.stdin.write('done\n');original.stdin.flush();original.communicate(timeout=10)
  restored=observed==originSample and final['defaultId']==before['defaultId'] and final['mediaDefaultId']==before['mediaDefaultId'] and final['communicationsDefaultId']==before['communicationsDefaultId']
  report={'passed':len(results)==len(before['outputs']) and restored,'outputs':results,'count':len(results),'initialStateRestored':restored,'sourceHashes':product_sources(),'scope':'Real Windows endpoint control; independent persistent Core Audio probe; no playback started'}
  (ROOT/'artifacts/beta13-audio-live.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='sourceHashes'},ensure_ascii=False));assert report['passed']
if __name__=='__main__':main()
