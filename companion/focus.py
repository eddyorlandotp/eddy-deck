"""Bounded foreground activation in a disposable process, never on the job worker."""
import json,subprocess,sys,time
from pathlib import Path

def command():
    return [sys.executable,'--focus-window'] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).resolve().parents[1]/'run.py'),'--focus-window']

def run_bounded(request,check=lambda:None,timeout=2.5):
    check()
    child=subprocess.Popen([*command(),json.dumps(request,separators=(',',':'))],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        deadline=time.monotonic()+timeout
        while child.poll() is None:
            check()
            if time.monotonic()>=deadline:return {'foreground':False,'timedOut':True}
            time.sleep(.025)
        return {'foreground':child.returncode==0}

    finally:
        # Cancellation/timeouts stop only this helper. No orphan may activate an
        # old window after the queue advances to another step or another app.
        if child.poll() is None:child.kill()
        child.wait(timeout=2)

def activate(request):
    import win32gui as g,win32process
    from companion.layout import process,u,k
    hwnd=request['hwnd'];pid=request['pid'];created=request['created'];cls=request['class']
    if type(hwnd) is not int or type(pid) is not int or type(created) is not int or not isinstance(cls,str):raise ValueError('Invalid focus identity')
    def valid():
        if not g.IsWindow(hwnd) or win32process.GetWindowThreadProcessId(hwnd)[1]!=pid or g.GetClassName(hwnd)!=cls:return False
        p=process(pid)
        return p is not None and p['created']==created
    if not valid() or u.IsHungAppWindow(hwnd):return {'foreground':False}
    g.PeekMessage(None,0,0,0) # Create this helper's input queue before attaching.
    try:g.SetForegroundWindow(hwnd)
    except Exception:pass
    if g.GetForegroundWindow()!=hwnd:
        foreground=g.GetForegroundWindow();current=k.GetCurrentThreadId()
        if foreground and not u.IsHungAppWindow(foreground):
            thread=win32process.GetWindowThreadProcessId(foreground)[0];attached=False
            try:
                if thread!=current:attached=bool(u.AttachThreadInput(current,thread,True))
                if (attached or thread==current) and valid():
                    g.SetWindowPos(hwnd,0,0,0,0,0,0x3)
                    # Foreground activation raises the window without TOPMOST,
                    # synthetic input, global preference changes or elevation.
                    try:g.SetForegroundWindow(hwnd)
                    except Exception:pass
            finally:
                if attached:u.AttachThreadInput(current,thread,False)
    until=time.monotonic()+.5
    while time.monotonic()<until:
        if not valid():return {'foreground':False}
        if g.GetForegroundWindow()==hwnd:return {'foreground':True}
        time.sleep(.025)
    return {'foreground':False}

def main():
    try:
        if len(sys.argv)!=3 or len(sys.argv[2])>2048:raise ValueError('Invalid request')
        request=json.loads(sys.argv[2])
        result=activate(request)
    except Exception:result={'foreground':False}
    raise SystemExit(0 if result.get('foreground') else 2)
