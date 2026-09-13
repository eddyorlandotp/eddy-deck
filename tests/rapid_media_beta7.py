"""Rapid next -> pause on the two test-opened players; does not affect browser media."""
import json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion import windows,media_sessions
from companion.core import VERSION
def main():
 apps,_=windows.scan(ROOT);player=next(p['id'] for p in media_sessions.snapshot(apps,fresh=True)['players'] if p['source']=='Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic');checks=[]
 for cycle in range(3):
  subprocess.run([str(ROOT/'.build/MediaPlayerOpen.exe'),str(ROOT/'.build/beta7-media-fixtures/EddyDeck-Test-1.wav'),str(ROOT/'.build/beta7-media-fixtures/EddyDeck-Test-2.wav')],check=True,capture_output=True);time.sleep(.5)
  for target in (player,'aimp'):
   windows.media('play',target,apps);windows.media('next',target,apps);windows.media('pause',target,apps)
   before=windows.aimp_snapshot(apps)['position'] if target=='aimp' else None
   time.sleep(1.3)
   state=windows.aimp_snapshot(apps) if target=='aimp' else media_sessions.invoke('status',target)
   assert state['state']=='paused',(cycle,target,state)
   if target=='aimp':assert state['position']==before;windows.media('previous',target,apps);windows.media('pause',target,apps)
   checks.append({'cycle':cycle+1,'target':'AIMP' if target=='aimp' else 'Media Player','pausedAfterNext':True})
 report={'version':VERSION,'passed':True,'checks':checks,'scope':'Actual adapters, immediate sequential next/pause, read again 1.3s later. Does not prove behavior of every Windows media app.'}
 (ROOT/'artifacts/beta7-rapid-media.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
