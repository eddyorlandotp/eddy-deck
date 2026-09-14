import os, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from test_core import ROOT

@unittest.skipUnless(os.name=='nt','Windows Job Object test')
class ChildLifetimeTests(unittest.TestCase):
    def test_receiver_death_reaps_helper_but_preserves_launched_app(self):
        import win32api,win32event,win32process
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);script=root/'owner.py'
            (root/'helper.py').write_text('''import sys,time,subprocess
from pathlib import Path
p=Path(sys.argv[1]);end=time.monotonic()+10
while not (p/'gate').exists() and time.monotonic()<end:time.sleep(.01)
app=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
(p/'app').write_text(str(app.pid))
time.sleep(60)
''',encoding='utf-8')
            script.write_text('''import sys,subprocess,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from companion.child_lifetime import Lifetime
folder=Path(sys.argv[2])
with Lifetime() as lifetime:
 child=subprocess.Popen([sys.executable,str(folder/'helper.py'),str(folder)])
 lifetime.attach(child);(folder/'helper').write_text(str(child.pid));(folder/'gate').write_text('ready');time.sleep(60)
''',encoding='utf-8')
            owner=subprocess.Popen([sys.executable,str(script),str(ROOT),str(root)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            handles=[]
            try:
                end=time.monotonic()+8
                while not (root/'app').exists() and time.monotonic()<end:time.sleep(.02)
                self.assertTrue((root/'app').exists(),'Owned helper did not start its app fixture')
                helper=win32api.OpenProcess(0x100001,False,int((root/'helper').read_text()));handles.append(helper)
                app=win32api.OpenProcess(0x100001,False,int((root/'app').read_text()));handles.append(app)
                owner.kill();owner.wait(3)
                self.assertEqual(win32event.WaitForSingleObject(helper,3000),0)
                self.assertEqual(win32event.WaitForSingleObject(app,0),258)
            finally:
                if owner.poll() is None:owner.kill()
                owner.wait(3)
                if owner.stderr:owner.stderr.close()
                for handle in handles:
                    if win32event.WaitForSingleObject(handle,0)==258:win32api.TerminateProcess(handle,0);win32event.WaitForSingleObject(handle,3000)
                    handle.Close()
