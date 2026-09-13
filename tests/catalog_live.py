"""Explicit opt-in catalog audit. Logs every row; closes only test-created HWNDs.
No in-app clicks, login, install, save, recording, privilege or power actions.
"""
from pathlib import Path
import argparse,collections,json,os,re,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion import windows
from companion.layout import Windows,process,dwm,C,W
import win32gui as g,win32process
ROOT=Path(__file__).resolve().parents[1]
def visible(h):
    if not g.IsWindow(h) or not g.IsWindowVisible(h):return False
    cloaked=W.DWORD();dwm.DwmGetWindowAttribute(h,14,C.byref(cloaked),4)
    return not cloaked.value

def observed():
    rows={}
    def visit(h,_):
        if not g.IsWindowVisible(h):return
        p=process(win32process.GetWindowThreadProcessId(h)[1])
        if p:rows[h]={'pid':p['pid'],'created':p['created'],'path':p['path'],'title':g.GetWindowText(h)}
    g.EnumWindows(visit,None);return rows
def identity(h,row):
    if not g.IsWindow(h):return False
    p=process(win32process.GetWindowThreadProcessId(h)[1])
    return p and p['pid']==row['pid'] and p['created']==row['created']
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');parser.add_argument('--only',nargs='*');parser.add_argument('--resume',action='store_true');parser.add_argument('--output',default='catalog-beta-live.json');args=parser.parse_args()
    if not args.execute:raise SystemExit('Es una prueba real: requiere --execute y autorización del propietario.')
    inventory=json.loads((ROOT/'artifacts/catalog-beta-before.json').read_text(encoding='utf-8'))['apps']
    current,_=windows.scan(ROOT/'companion');eligible={a['id']:a for a in current};layout=Windows();baseline=observed();rows=[]
    skip=re.compile(r'^(chatgpt|claude|codex|tailscale|exitlag|tor browser|onedrive|narrador|narrator|lupa|magnify|on-screen|teclado|voiceaccess|acceso por voz|livecaptions|subtitulos|camera|iriun|game bar|medal|desktop overlay|wallpaper engine|mateengine|lossless scaling|op auto|rufus|balenaetcher|gcc|gigabyte|nvidia|msi afterburner|rivatuner|steelseries|razer|realtek|davinci control|fairlight|power automate)',re.I)
    seen={}
    if Path(args.output).name!=args.output:raise ValueError('Usa solo un nombre de informe.')
    out=ROOT/'artifacts'/args.output
    if args.resume and out.exists():rows=json.loads(out.read_text(encoding='utf-8'))['rows']
    for app in inventory:
        if args.only and app['name'] not in args.only:continue
        if args.resume and any(r['id']==app['id'] for r in rows):continue
        row={'id':app['id'],'name':app['name'],'kind':app['kind'],'identity':'discovered','launch':'not_tested','layout':'not_tested','cleanup':'not_needed'};rows.append(row)
        try:
            if app['id'] not in eligible:row.update(identity='filtered_invalid_or_system',launch='excluded');continue
            app=eligible[app['id']]
            if not app.get('available',True):row.update(identity='shortcut_without_verified_installation',launch='unavailable');continue
            if app['kind']=='shortcut':
                if not windows.safe_executable(app['target']) or os.path.normcase(windows.shortcut_target(app['source']))!=os.path.normcase(app['target']):row.update(identity='stale',launch='unavailable');continue
                row['identity']='verified_executable_and_shortcut'
            else:row['identity']='verified_catalog_identity'
            if skip.search(windows.folded(app['name'])):row['launch']='manual_session_hardware_or_permission_check';continue
            if app.get('sharedExecutable'):row['launch']='shared_launcher_needs_manual_window_selection';continue
            key=(app['target'].casefold(),app.get('arguments',''))
            if key in seen:row.update(launch='same_target_as',sameTarget=seen[key]);continue
            seen[key]=app['name']
            prior=layout.snapshot(current);existing=[w for w in prior if app['id'] in w['appIds']]
            if existing:row.update(launch='existing_window_observed',windows=len(existing));continue
            before=observed();before_handles=set();g.EnumWindows(lambda h,_:before_handles.add(h),None)
            start=time.monotonic();windows.launch(app)
            found=[]
            while time.monotonic()-start<18:
                found=[w for w in layout.snapshot(current) if app['id'] in w['appIds'] and layout.leases[w['id']]['hwnd'] not in before_handles]
                if (len(found)==1 and time.monotonic()-start>=2) or (len(found)>1 and time.monotonic()-start>=6):break
                time.sleep(.5)
            after=observed();new={h:r for h,r in after.items() if h not in before_handles}
            (ROOT/'.build/catalog-new-windows.json').write_text(json.dumps({'app':app['name'],'windows':new},ensure_ascii=False,indent=2),encoding='utf-8')
            row['elapsedSeconds']=round(time.monotonic()-start,1)
            if len(found)==1:
                w=found[0];h=layout.leases[w['id']]['hwnd'];row['launch']='window_observed'
                # This does not claim sign-in or application internals are ready.
                try:
                    results=[]
                    for target in ({'monitor':'right','mode':'windowed'},{'monitor':'left','mode':'maximized'},{'monitor':'keep','mode':'minimized'},{'monitor':'right','mode':'windowed'}):
                        try:results.append({'mode':target['mode'],'status':layout.move(w['id'],target,current)['status']})
                        except Exception as e:results.append({'mode':target['mode'],'status':'unsupported_or_failed','detail':str(e)})
                    row['transitions']=results;row['layout']='four_transitions_verified' if all(r['status']=='completed' for r in results) else 'partial_transitions'
                except Exception as e:row['layout']='app_rejected_or_ambiguous';row['layoutDetail']=str(e)
                # A normal close can show a Save/exit prompt; never confirm one.
                newrow=new.get(h)
                if newrow and identity(h,newrow):
                    g.PostMessage(h,0x10,0,0);end=time.monotonic()+8
                    while identity(h,newrow) and visible(h) and time.monotonic()<end:time.sleep(.2)
                    row['cleanup']='closed_test_window' if not identity(h,newrow) else 'hidden_to_tray' if not visible(h) else 'window_or_prompt_remains'
            elif len(found)>1:
                row['launch']='multiple_windows_need_selection'
                pending=[]
                for w in found:
                    h=layout.leases[w['id']]['hwnd'];r=new.get(h)
                    if r and identity(h,r):g.PostMessage(h,0x10,0,0);pending.append((h,r))
                time.sleep(2)
                row['cleanup']='window_or_prompt_remains' if any(identity(h,r) and visible(h) for h,r in pending) else 'closed_or_hidden_test_windows'
            else:row['launch']='submitted_no_identifiable_window'
            unknown=[r for h,r in new.items() if not any(layout.leases.get(w['id'],{}).get('hwnd')==h for w in found)]
            row['unidentifiedNewWindows']=[Path(r['path']).name for r in unknown if r['title']]
            # Stop a batch if an unidentified new app window remains. Its
            # ownership is uncertain; subsequent tests must not pile up on it.
            if row['launch'] in ('multiple_windows_need_selection','submitted_no_identifiable_window') and any(n.lower() not in ('nvidia overlay.exe','gamebar.exe','gamebarftserver.exe') for n in row['unidentifiedNewWindows']):
                row['reviewBeforeContinuing']=True
        except Exception as e:row['launch']='failed';row['detail']=str(e)
        finally:
            out.write_text(json.dumps({'rows':rows,'baselineWindowsPreserved':all(identity(h,r) for h,r in baseline.items()),'counts':dict(collections.Counter(r['launch'] for r in rows))},ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(row,ensure_ascii=True),flush=True)
        if row.get('reviewBeforeContinuing') or row.get('cleanup')=='window_or_prompt_remains':
            print('PAUSED_FOR_REVIEW',flush=True);break
if __name__=='__main__':main()
