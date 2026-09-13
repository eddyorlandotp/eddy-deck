import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion import windows,tidal
from scripts.package_evidence import product_sources
from tidal_live import progress
apps,_=windows.scan(ROOT);h=tidal.target(apps)['hwnd'];rows=[]
try:
 for i in range(5):
  changed=windows.media('next','tidal',apps);paused=windows.media('pause','tidal',apps);before=progress(h);time.sleep(1.3);after=progress(h);state=tidal.snapshot(apps,fresh=True)['state']
  assert state=='paused' and before==after,(i,state,before,after)
  rows.append({'cycle':i+1,'nextVerified':changed.get('verified'),'pauseVerified':paused.get('verified'),'timelineStopped':True});print('Cycle '+str(i+1)+' passed',flush=True)
finally:
 windows.media('pause','tidal',apps)
(ROOT/'artifacts/beta7-tidal-rapid-final.json').write_text(json.dumps({'passed':True,'cycles':len(rows),'rows':rows,'sourceHashes':product_sources()},indent=2))
