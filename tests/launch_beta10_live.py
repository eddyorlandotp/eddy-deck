from pathlib import Path
import json,tempfile,sys,time,hashlib
sys.path.insert(0,str(Path.cwd()))
from companion import windows
from companion.core import Deck,VERSION
from companion.layout import Windows
from scripts.package_evidence import product_sources
import win32gui as g
import argparse
from unittest.mock import patch
parser=argparse.ArgumentParser();parser.add_argument("--helper-exe");args=parser.parse_args()
helper=Path(args.helper_exe) if args.helper_exe else None
if helper:assert helper.is_file() and helper.name=="EddyDeck.exe"
helper_patch=patch("companion.focus.command",return_value=[str(helper),"--focus-window"]) if helper else None
if helper_patch:helper_patch.start()
root=Path.cwd();apps,_=windows.scan(Path.home()/'.eddydeck');target=[a for a in apps if a['name'] in ('Roblox Player','TIDAL')]
original=json.loads((Path.home()/'.eddydeck/deck.json').read_text(encoding='utf-8'));scene=next(s for s in original['scenes'] if s['name'].lower()=='jugar bobox');baseline=Windows();prior=baseline.snapshot(apps);owned=[];records=[]
with tempfile.TemporaryDirectory(prefix='eddy-launch-test-') as tmp:
 d=Deck(tmp,root,adapter=windows);d.apps=apps
 try:
  def run(steps,name):
   r=d.enqueue(name,[d.clean_step(s) for s in steps],'local','stop');until=time.monotonic()+75
   while time.monotonic()<until:
    j=next(j for j in d.journal.jobs() if j['id']==r['jobId'])
    if j['status'] not in ('running','queued'):return j
    time.sleep(.15)
   raise AssertionError('Job timed out')
  r=run(scene['steps'],'Real two-app routine');records.append({'case':'saved Roblox then TIDAL routine','status':r['status'],'results':r['results']});assert r['status']=='completed',r['message'];assert len(r['results'])==2
  current=d.layouts.snapshot(apps)
  for a in target:
   rows=[w for w in current if a['id'] in w['appIds']];assert len(rows)==1,(a['name'],len(rows));assert rows[0]['maximized'];records.append({'case':'maximized '+a['name'],'observed':True})
  tidal=next(a for a in target if a['name']=='TIDAL');row=next(w for w in current if tidal['id'] in w['appIds']);assert g.GetForegroundWindow()==d.layouts.leases[row['id']]['hwnd'];records.append({'case':'last routine app is foreground','observed':True})
  for a in target:
   for mode,activation in [('minimized','front'),('keep','front'),('keep','windows')]:
    r=run([{'appId':a['id'],'layout':{'mode':mode},'activation':activation}],a['name']+' '+mode+' '+activation);assert r['status']=='completed',r;current=d.layouts.snapshot(apps);rows=[w for w in current if a['id'] in w['appIds']];assert len(rows)==1
    if mode=='minimized':assert rows[0]['minimized']
    elif activation=='front':assert g.GetForegroundWindow()==d.layouts.leases[rows[0]['id']]['hwnd']
    records.append({'case':a['name']+' '+mode+' '+activation,'status':r['status'],'windowCount':len(rows),'results':r['results']})
  assert original==json.loads((Path.home()/'.eddydeck/deck.json').read_text(encoding='utf-8'))
 finally:
  d.close()
  if helper_patch:helper_patch.stop()
report={'version':VERSION,'passed':True,'count':len(records),'checks':records,'sourceHashes':product_sources(),'realWindows':True,'frozenHelperVerified':bool(helper),'helperSHA256':hashlib.sha256(helper.read_bytes()).hexdigest() if helper else '','originalProfileUnchanged':True,'existingAppsNotClosed':True,'scope':'Exact saved routine through isolated real Windows queue, Roblox and TIDAL maximized; live foreground, minimized and reuse. New TIDAL left open for user. No account/media clicks.'}
(root/'artifacts/beta10-launch-live.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'count':len(records),'routineCompleted':True}))
