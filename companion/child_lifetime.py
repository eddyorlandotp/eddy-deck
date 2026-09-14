"""Kill only a native helper if its owning receiver exits unexpectedly.

Launched user applications silently break away and remain under user control.
"""
import os, time, uuid, subprocess
from pathlib import Path

class Lifetime:
    def __enter__(self):
        self.job=None
        if os.name=='nt':
            import win32job
            self.job=win32job.CreateJobObject(None,'Local\\EddyDeck-helper-'+uuid.uuid4().hex)
            try:
                info=win32job.QueryInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation)
                info['BasicLimitInformation']['LimitFlags']=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE|win32job.JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK
                win32job.SetInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation,info)
            except Exception:self.job.Close();self.job=None;raise
        return self
    def attach(self,child):
        if self.job is not None:
            import win32api,win32job
            if child.poll() is not None:return
            try:
                handle=win32api.OpenProcess(0x100|0x1,False,child.pid)
                try:win32job.AssignProcessToJobObject(self.job,handle)
                finally:handle.Close()
            except Exception:
                if child.poll() is None:raise
    def __exit__(self,*error):
        if self.job is not None:self.job.Close()

def await_gate(request):
    # A helper cannot touch Windows before the receiver attaches its lifetime
    # guard. Missing parent or failed attachment therefore has no side effect.
    gate=Path(request['gate']);deadline=time.monotonic()+5
    while not gate.is_file():
        if time.monotonic()>=deadline:raise RuntimeError('Owner did not authorize helper startup')
        time.sleep(.01)

def run_owned(command,*,timeout,capture_output=False,**options):
    if capture_output:options.update(stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    with Lifetime() as lifetime:
        child=subprocess.Popen(command,**options)
        try:
            lifetime.attach(child)
            stdout,stderr=child.communicate(timeout=timeout)
            return subprocess.CompletedProcess(command,child.returncode,stdout,stderr)
        finally:
            if child.poll() is None:child.kill()
            child.wait(timeout=3)
            for stream in (child.stdin,child.stdout,child.stderr):
                if stream is not None:stream.close()
