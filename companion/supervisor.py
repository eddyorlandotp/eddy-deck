"""Per-user watchdog. It may restart only the exact child it created."""
import ctypes,hashlib,json,os,socket,subprocess,sys,time,urllib.error,urllib.request
from pathlib import Path
from companion.diagnostics import record

def marker_fresh(marker,seconds):
    """Processes on this Windows boot share the monotonic clock.
    Accept old markers during migration, but reject future wall timestamps.
    """
    try:
        age=time.monotonic()-marker['monotonic'] if 'monotonic' in marker else time.time()-marker['at']
        return 0<=age<seconds
    except (KeyError,TypeError,ValueError):return False

def restart_due(request,worker_pid):
    try:
        due=time.monotonic()>=request['afterMonotonic'] if 'afterMonotonic' in request else time.time()>=request['after']
        return request.get('pid')==worker_pid and due
    except (KeyError,TypeError,ValueError):return False

def active(data):
    if os.environ.get('EDDY_DECK_SUPERVISED')!='1':return False
    try:
        marker=json.loads((Path(data)/'supervisor.json').read_text())
        return marker['workerPid']==os.getpid() and marker_fresh(marker,15)
    except (OSError,ValueError,KeyError,TypeError):return False

UNRESPONSIVE_SECONDS=45

def liveness_problem(data,worker_pid,opener=urllib.request.urlopen):
    """None when the worker is alive; otherwise a short reason for the audit log."""
    try:
        runtime=json.loads((Path(data)/'runtime.json').read_text())
    except (OSError,ValueError):return 'runtime-unreadable'
    try:
        if runtime.get('pid')!=worker_pid:return 'runtime-other-pid'
        heartbeat=runtime if 'monotonic' in runtime else {'at':(Path(data)/'runtime.json').stat().st_mtime}
        if not marker_fresh(heartbeat,30):return 'heartbeat-stale'
    except (OSError,AttributeError):return 'runtime-unreadable'
    try:
        with opener('http://127.0.0.1:47989/health',timeout=5) as r:
            if r.status!=200:return 'health-'+str(r.status)
    except urllib.error.HTTPError as e:return 'health-'+str(e.code)
    except Exception as e:return 'health-'+type(e).__name__
    return None

def unresponsive(bad,first_bad,now):
    """A game or an update can starve the PC for several seconds; restarting
    then only disconnects the phone. Require a sustained failure."""
    return bad>=3 and first_bad is not None and now-first_bad>=UNRESPONSIVE_SECONDS

def restart_decision(exit_code,failures,requested=False):
    if requested:return 'restart'
    if exit_code==0:return 'stop'
    return 'pause' if failures>=5 else 'restart'

def entry():
    from companion.desktop import main
    bypass={'--worker','--headless','--dry-run','--data','--install','--install-silent','--validate-profile','--restore-profile','--enable-wifi','--enable-internet'}
    if any(a in bypass for a in sys.argv[1:]):return main()
    if getattr(sys,'frozen',False):
        # An older copy elsewhere may carry another data folder or identity.
        # Hand over to the installed release instead of starting it.
        from companion.core import VERSION
        from companion import resilience
        newer=resilience.superseded_by(sys.executable,VERSION)
        if newer:
            subprocess.Popen([str(resilience.canonical_exe())]+[x for x in sys.argv[1:] if x=='--tray'],cwd=str(resilience.canonical_dir()),creationflags=0x08000000)
            if '--tray' not in sys.argv[1:]:
                ctypes.windll.user32.MessageBoxW(None,'Esta es una copia antigua de Eddy Deck ('+VERSION+'). Se abrió la versión instalada '+newer+'.\n\nUsa el acceso directo "Eddy Deck" del escritorio o del menú Inicio.','Eddy Deck',0x40)
            return
    from companion.storage import prepare_data
    data=prepare_data()
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p];k.CreateMutexW.restype=ctypes.c_void_p;k.CloseHandle.argtypes=[ctypes.c_void_p]
    mutex=k.CreateMutexW(None,False,'Local\\EddyDeckSupervisor-'+hashlib.sha256(str(data).encode()).hexdigest()[:16])
    if not mutex:raise RuntimeError('No se pudo crear el supervisor de Eddy Deck.')
    if ctypes.get_last_error()==183:
        try:
            with socket.create_connection(('127.0.0.1',47988),timeout=2) as s:s.sendall(b'SHOW_EDDY_DECK')
        except OSError:pass
        k.CloseHandle(mutex);return
    from companion.core import atomic_json
    command=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).resolve().parents[1]/'run.py')]
    env={**os.environ,'EDDY_DECK_SUPERVISED':'1'};failures=[];request=data/'restart-request.json'
    try:
        # A pre-supervisor release may still own the receiver. Never interrupt it.
        try:
            with socket.create_connection(('127.0.0.1',47988),timeout=1) as s:s.sendall(b'SHOW_EDDY_DECK')
            return
        except OSError:pass
        request.unlink(missing_ok=True)
        from companion.resilience import clear_user_exit
        clear_user_exit(data)
        while True:
            child=subprocess.Popen(command+['--worker']+[x for x in sys.argv[1:] if x=='--tray'],env=env,creationflags=0x08000000)
            started=time.monotonic();bad=0;first_bad=None;reasons=[];requested=False
            record(data,'receiver.start','started')
            while child.poll() is None:
                time.sleep(2)
                atomic_json(data/'supervisor.json',{'pid':os.getpid(),'workerPid':child.pid,'at':time.time(),'monotonic':time.monotonic(),'failures':len(failures)})
                try:
                    r=json.loads(request.read_text())
                    requested=restart_due(r,child.pid)
                except (OSError,ValueError):pass
                if requested:
                    request.unlink(missing_ok=True);record(data,'receiver.repair','restarting');child.terminate();child.wait(timeout=10);break
                if time.monotonic()-started<30:continue
                problem=liveness_problem(data,child.pid)
                if problem is None:bad=0;first_bad=None;reasons=[]
                else:
                    bad+=1;first_bad=first_bad if first_bad is not None else time.monotonic()
                    if problem not in reasons:reasons.append(problem)
                if unresponsive(bad,first_bad,time.monotonic()):
                    record(data,'receiver.watchdog','unresponsive','No respondió durante '+str(int(time.monotonic()-first_bad))+' s: '+', '.join(reasons[:4]));child.terminate();child.wait(timeout=10);break
            failures=[t for t in failures if time.monotonic()-t<900]
            if child.returncode!=0 and not requested:record(data,'receiver.exit','unexpected','Código de salida '+str(child.returncode))
            if not requested and child.returncode!=0:failures.append(time.monotonic())
            decision=restart_decision(child.returncode,len(failures),requested)
            # Exit code 0 is not proof of Salir (a worker also exits 0 when it
            # finds another receiver); only Desktop.quit writes user-exit.json.
            if decision=='stop':record(data,'receiver.exit','normal');break
            if decision=='pause':
                record(data,'receiver.watchdog','paused','Cinco fallos en 15 minutos. Abre Eddy Deck de nuevo después de revisar los informes.');break
            time.sleep(1 if requested else min(30,2**len(failures)))
    finally:
        (data/'supervisor.json').unlink(missing_ok=True);k.CloseHandle(mutex)
