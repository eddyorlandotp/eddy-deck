"""Real Windows controls, restricted to a Popen-owned disposable fixture process."""
import copy,json,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.core import Deck,VERSION
from companion.layout import Windows,monitors
from companion import windows

def main():
 exe=ROOT/'.build/EddyDeckTestWindow.exe';compiler=Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe')
 subprocess.run([str(compiler),'/nologo','/target:winexe','/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/out:'+str(exe),str(ROOT/'tests/WindowFixture.cs')],check=True)
 p=subprocess.Popen([str(exe)]);results=[];layout=Windows()
 app={'id':'fixture','name':'Eddy Deck TEST','kind':'manual','target':str(exe),'browser':False,'category':'Herramientas','symbol':'app','available':True}
 def rows():return [w for w in layout.snapshot([app]) if app['id'] in w['appIds'] and layout.leases[w['id']]['process']['pid']==p.pid]
 def record(name,value=True):assert value,name;results.append({'case':name,'passed':True})
 def rejects(name,fn):
  try:fn()
  except ValueError:record(name);return
  raise AssertionError(name)
 def wait_job(d,jid):
  deadline=time.monotonic()+8
  while time.monotonic()<deadline:
   item=next(j for j in d.journal.jobs() if j['id']==jid)
   if item['status'] not in ('queued','running'):return item
   time.sleep(.1)
  raise AssertionError('job timeout')
 try:
  until=time.monotonic()+10
  while len(rows())!=2 and time.monotonic()<until:time.sleep(.1)
  found=rows();record('Two owned fixture windows identified',len(found)==2)
  normal=next(w for w in found if w['title'].endswith('normal'));guard=next(w for w in found if w['title'].endswith('pendiente'))
  import win32gui
  hwnd=layout.leases[normal['id']]['hwnd'];win32gui.EnableWindow(hwnd,False)
  try:
   record('A disabled parent window is identified as needing attention',next(w for w in rows() if w['id']==normal['id'])['needsAttention'])
   rejects('Moving a parent blocked by a dialog is rejected',lambda:layout.move(normal['id'],{'mode':'minimized'},[app]))
   rejects('Closing a parent blocked by a dialog is rejected',lambda:layout.close_window(normal['id'],[app]))
   record('Opening an app with a disabled parent reports attention without dismissing its dialog',layout.present(normal['id'],{'monitor':'keep','mode':'keep'},[app],lambda:None)['status']=='needs_attention')
  finally:win32gui.EnableWindow(hwnd,True)
  layout.protect(normal['id'],True,[app])
  rejects('Protected normal close rejected',lambda:layout.close_window(normal['id'],[app]))
  rejects('Protected termination rejected',lambda:layout.terminate_window(normal['id'],[app]))
  rejects('Protected movement rejected',lambda:layout.move(normal['id'],{'monitor':'keep','mode':'minimized'},[app]))
  layout.protect(normal['id'],False,[app]);record('Unprotect restores controls',not next(w for w in rows() if w['id']==normal['id'])['protected'])
  for monitor in monitors():
   for mode in ('windowed','maximized','minimized','windowed'):
    record('Observed '+monitor['label']+' / '+mode,layout.move(normal['id'],{'monitor':monitor['id'],'mode':mode},[app])['status']=='completed')
  with tempfile.TemporaryDirectory() as tmp:
   deck=Deck(tmp,ROOT,adapter=windows);deck.apps=[app];deck.layouts=layout
   try:
    job=deck.dispatch('/api/launch',{'requestId':'reuse-fixture','appId':'fixture','activation':'windows'},'local');done=wait_job(deck,job['jobId']);record('Already-open launch reuses existing windows',done['results'][0]['status']=='already_open' and len(rows())==2)
    record('WM_CLOSE closes only normal fixture',layout.close_window(normal['id'],[app])['status']=='closed_or_hidden' and len(rows())==1)
    rejects('Stale closed window identity rejected',lambda:layout.move(normal['id'],{'mode':'minimized'},[app]))
    import win32gui
    bounds=win32gui.GetWindowRect(layout.leases[guard['id']]['hwnd'])
    layout.move(guard['id'],{'monitor':'keep','mode':'minimized'},[app])
    job=deck.dispatch('/api/launch',{'requestId':'restore-existing-fixture','appId':'fixture'},'local');done=wait_job(deck,job['jobId'])
    record('Opening a unique minimized app restores it',not win32gui.IsIconic(layout.leases[guard['id']]['hwnd']))
    record('Restore preserves previous geometry',win32gui.GetWindowRect(layout.leases[guard['id']]['hwnd'])==bounds)
    closed=layout.close_window(guard['id'],[app]);print(json.dumps({'closeResult':closed,'remainingFixtures':rows(),'exitCode':p.poll()},ensure_ascii=False))
    record('Unsaved fixture refuses normal close',closed['status']=='needs_attention' and p.poll() is None)
    challenge=deck.dispatch('/api/windows/terminate/prepare',{'requestId':'prepare-fixture','windowId':guard['id']},'local')
    job=deck.dispatch('/api/windows/terminate/confirm',{'requestId':'confirm-fixture','challenge':challenge['challenge']},'local');done=wait_job(deck,job['jobId'])
    p.wait(timeout=5);record('Confirmed termination affects only owned fixture',done['results'][0]['status']=='terminated' and p.returncode==1)
   finally:deck.close()
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=5)
  (ROOT/'artifacts'/('beta'+VERSION.rsplit('beta.',1)[-1]+'-windows-controls.json')).write_text(json.dumps({'version':VERSION,'fixtureOnly':True,'checks':results,'count':len(results)},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'passed':len(results),'fixtureOnly':True}))
if __name__=='__main__':main()
