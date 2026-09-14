"""Sequential real-app campaign with a durable per-window ownership ledger.

No application internals, login, install or permission dialogs are accepted.
Every entry is classified; a discovery is never reported as a successful launch.
"""
import argparse, copy, json, re, sys, tempfile, time
from pathlib import Path
from catalog_live import observed, identity, visible, g
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion import windows
from companion.layout import Windows
from companion.core import Deck, VERSION

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');parser.add_argument('--resume',action='store_true');parser.add_argument('--limit',type=int,default=200);args=parser.parse_args()
    if not args.execute:raise SystemExit('Requires explicit --execute and owner authorization.')
    apps,_=windows.scan(Path.home()/'.eddydeck');ledger=ROOT/'.build/beta11-catalog-ownership.json';out=ROOT/'artifacts/beta11-catalog-live.json'
    rows=json.loads(out.read_text(encoding='utf-8'))['rows'] if args.resume and out.exists() else []
    owners=json.loads(ledger.read_text(encoding='utf-8')) if args.resume and ledger.exists() else []
    baseline=observed();count=0
    excluded=re.compile(r'^(acceso por voz|voiceaccess|chatgpt|claude|codex|click to do|tailscale|exitlag|tor browser|onedrive|narrador|narrator|lupa|magnify|on-screen|teclado|livecaptions|subtitulos|camera|iriun|game bar|desktop overlay|wallpaper engine|mateengine|lossless scaling|op auto|rufus|balenaetcher|gcc|gigabyte|nvidia|msi afterburner|rivatuner|steelseries|razer|realtek|davinci control|fairlight|power automate|ollama)',re.I)
    def save():
        ledger.write_text(json.dumps(owners,ensure_ascii=False,indent=2),encoding='utf-8')
        out.write_text(json.dumps({'version':VERSION,'catalogCount':len(apps),'rows':rows,'baselineVisibleWindowsPreserved':all(identity(h,r) for h,r in baseline.items()),'scope':'Real serial launch/layout/reuse/close. App internals and sign-in are separate, not inferred. Exclusions have explicit reasons.'},ensure_ascii=False,indent=2),encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='eddy-catalog-') as tmp:
        deck=Deck(tmp,ROOT);deck.apps=apps;layout=deck.layouts
        try:
            for app in apps:
                if any(r['id']==app['id'] for r in rows):continue
                if count>=args.limit:break
                row={'id':app['id'],'name':app['name'],'discovery':'catalog_entry','launch':'not_tested','layout':[],'cleanup':'not_needed','internals':'not_tested'};rows.append(row)
                if excluded.search(windows.folded(app['name'])):row['launch']='manual_only';row['reason']='Hardware, accessibility, networking, security, persistent desktop service or active agent; starting it changes the test environment.';save();continue
                if app.get('sharedExecutable'):row['launch']='manual_only';row['reason']='Shared launcher cannot safely identify the intended app from its process.';save();continue
                before=observed();prior=layout.snapshot(apps);existing=[w for w in prior if app['id'] in w['appIds']]
                if existing:row['launch']='existing_window_observed';row['reason']='Existing user session preserved; not counted as a launch.';save();continue
                count+=1;pending=False;handles=[];start=time.monotonic()
                try:
                    job=deck.dispatch('/api/launch',{'requestId':'catalog-'+app['id'],'appId':app['id'],'activation':'front'},'local')
                    end=time.monotonic()+32;done=None
                    while time.monotonic()<end:
                        done=next((j for j in deck.journal.jobs() if j['id']==job['jobId']),None)
                        if done and done['status'] not in ('running','queued'):break
                        time.sleep(.15)
                    if not done or done['status'] in ('running','queued'):
                        row['launch']='submitted_timeout';deck.queue.cancel(job['jobId'],'local');raise RuntimeError('Launch exceeded campaign deadline; cancellation requested.')
                    found=[w for w in layout.snapshot(apps) if app['id'] in w['appIds'] and layout.leases[w['id']]['hwnd'] not in before]
                    row['jobStatus']=done['status'];row['jobMessages']=[r.get('message') for r in done['results']]
                    after=observed()
                    for w in found:
                        hwnd=layout.leases[w['id']]['hwnd'];record=after.get(hwnd)
                        if record:
                            owner={'appId':app['id'],'app':app['name'],'hwnd':hwnd,'identity':record,'createdByCampaign':True,'cleanup':'pending'};owners.append(owner);handles.append(owner)
                    save()
                    row['launch']='window_observed' if found else 'no_identifiable_window'
                    if len(found)==1:
                        row['foregroundObserved']=g.GetForegroundWindow()==layout.leases[found[0]['id']]['hwnd']
                        for mode in ('minimized','windowed','maximized'):
                            try:result=layout.move(found[0]['id'],{'monitor':'keep','mode':mode},apps);row['layout'].append({'mode':mode,'status':result['status']})
                            except Exception as error:row['layout'].append({'mode':mode,'status':'not_supported_or_failed','detail':str(error)})
                    unknown=[(h,r) for h,r in after.items() if h not in before and visible(h) and r.get('title') and h not in {o['hwnd'] for o in handles} and Path(r['path']).name.lower() not in ('nvidia overlay.exe','gamebar.exe','gamebarftserver.exe')]
                    if unknown:row['unidentifiedWindowProcesses']=[Path(r['path']).name for h,r in unknown];pending=True
                except Exception as error:row['error']=str(error)
                finally:
                    # Also catch identifiable late windows after a timed-out launch.
                    for w in layout.snapshot(apps):
                        h=layout.leases[w['id']]['hwnd']
                        if app['id'] in w['appIds'] and h not in before and h not in {o['hwnd'] for o in handles}:
                            record=observed().get(h)
                            if record:
                                owner={'appId':app['id'],'app':app['name'],'hwnd':h,'identity':record,'createdByCampaign':True,'cleanup':'pending'};owners.append(owner);handles.append(owner)
                    save()
                    for owner in handles:
                        h=owner['hwnd'];record=owner['identity']
                        if identity(h,record):g.PostMessage(h,0x10,0,0)
                    deadline=time.monotonic()+18
                    while any(identity(o['hwnd'],o['identity']) and visible(o['hwnd']) for o in handles) and time.monotonic()<deadline:time.sleep(.15)
                    for owner in handles:owner['cleanup']='closed' if not identity(owner['hwnd'],owner['identity']) else 'hidden_to_tray' if not visible(owner['hwnd']) else 'requires_attention'
                    row['cleanup']=[o['cleanup'] for o in handles] or ['no_owned_window']
                    pending=pending or any(o['cleanup']=='requires_attention' for o in handles)
                    # Closing a trial/game can itself create a promotion or dialog.
                    extra=[r for h,r in observed().items() if h not in before and visible(h) and r.get('title') and h not in {o['hwnd'] for o in handles} and Path(r['path']).name.lower() not in ('nvidia overlay.exe','gamebar.exe','gamebarftserver.exe')]
                    if extra:row['postCloseWindowProcesses']=[Path(r['path']).name for r in extra];pending=True
                    row['seconds']=round(time.monotonic()-start,2);row['reviewBeforeNextApp']=pending;save();print(json.dumps(row,ensure_ascii=True),flush=True)
                if pending:print('PAUSED_FOR_WINDOW_REVIEW',flush=True);break
        finally:deck.close();save()

if __name__=='__main__':main()
