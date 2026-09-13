"""Keep this receiver available without changing the Windows power plan."""
import ctypes,threading

CONTINUOUS=0x80000000
SYSTEM_REQUIRED=0x00000001

def execution_state(flags):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    call=kernel.SetThreadExecutionState
    call.argtypes=[ctypes.c_uint];call.restype=ctypes.c_uint
    if not call(flags):raise OSError(ctypes.get_last_error(),'Windows no aceptó la solicitud de energía.')

class AwakeGuard:
    """Single-use request owner: close is final; create a new guard to restart."""
    def __init__(self,apply=execution_state,interval=30):
        self.apply=apply;self.interval=interval
        self.stop=threading.Event();self.ready=threading.Event();self.lock=threading.Lock()
        self.active=False;self.error='';self.error_code=None;self.thread=None;self.closed=False

    def start(self):
        with self.lock:
            if self.closed:raise RuntimeError('La protección de energía ya se cerró. Crea una instancia nueva para reiniciarla.')
            if self.thread is None:
                self.thread=threading.Thread(target=self._run,name='EddyDeck-keep-awake',daemon=True)
                self.thread.start()
        self.ready.wait(2)

    def _run(self):
        try:
            while not self.stop.is_set():
                try:
                    self.apply(CONTINUOUS|SYSTEM_REQUIRED)
                    with self.lock:self.active=True;self.error='';self.error_code=None
                except Exception as exc:
                    code=getattr(exc,'winerror',None)
                    if code is None:code=getattr(exc,'errno',None)
                    with self.lock:self.active=False;self.error=type(exc).__name__;self.error_code=code if type(code) is int else None
                self.ready.set()
                if self.stop.wait(self.interval):break
        finally:
            try:self.apply(CONTINUOUS)
            except Exception:pass
            with self.lock:self.active=False
            self.ready.set()

    def status(self):
        with self.lock:return {'active':self.active,'error':self.error,'errorCode':self.error_code,'closed':self.closed,'scope':'receiver','displayRequired':False}

    def close(self):
        with self.lock:self.closed=True;self.stop.set()
        if self.thread is not None and self.thread is not threading.current_thread():self.thread.join(2)

def start_receiver_guard(dry_run, factory=AwakeGuard):
    """Both graphical and headless real receivers need availability.
    Constructing Deck alone never acquires a real Windows request.
    """
    if dry_run:return None
    guard=factory();guard.start();return guard
