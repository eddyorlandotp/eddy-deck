"""AIMP IPC smoke test. Keeps the volume; never changes songs or playback."""
import sys,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion import windows
from companion.layout import Windows
import win32gui as g
apps,_=windows.scan(ROOT/'companion');app=next(a for a in apps if windows.folded(a['name'])=='aimp')
layout=Windows();before=set();g.EnumWindows(lambda h,_:before.add(h),None)
already_running=bool(windows.aimp_handle(apps))
if not already_running:windows.launch(app)
for _ in range(30):
    state=windows.media_snapshot(apps)
    if state['aimp']:break
    time.sleep(.5)
assert state['aimp'],'AIMP no respondió al adaptador directo'
result={'stateRead':state['state']!='unknown','sameVolumeAccepted':False,'volumePreserved':False,'playbackPreserved':False}
try:
    windows.media('volume','aimp',apps,state['volume'])
    after=windows.media_snapshot(apps)
    result.update(sameVolumeAccepted=True,volumePreserved=after['volume']==state['volume'],playbackPreserved=after['state']==state['state'])
finally:
    if not already_running:
        for w in layout.snapshot(apps):
            h=layout.leases[w['id']]['hwnd']
            if app['id'] in w['appIds'] and h not in before:g.PostMessage(h,0x10,0,0)
    (ROOT/'artifacts/beta2-media-live-tests.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
assert all(result.values()),result
print('PASS: estado y volumen directo AIMP, volumen y reproducción conservados.')
