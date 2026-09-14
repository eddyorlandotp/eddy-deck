"""Exact TIDAL window identity plus a bounded Windows accessibility helper."""
import json,subprocess,sys,threading,time
from pathlib import Path
from companion.layout import Windows
from companion.windows import folded,HIDDEN
from companion.child_lifetime import run_owned
_lock=threading.RLock();_cached=None;_until=0;_cache_key=None

def target(apps):
    candidates=[a for a in apps if folded(a['name'])=='tidal']
    if not candidates:return None
    layout=Windows();ids={a['id'] for a in candidates}
    rows=[w for w in layout.snapshot(apps) if ids.intersection(w['appIds']) and w['process'].lower()=='tidal.exe']
    if len(rows)>1:raise RuntimeError('Hay varias ventanas de TIDAL. Deja un solo reproductor antes de controlarlo.')
    if not rows:return None
    return layout.leases[rows[0]['id']]

def invoke(action,apps):
    if action not in ('status','play','pause','toggle','stop','next','previous'):raise ValueError('Control de TIDAL no válido.')
    lease=target(apps)
    if lease is None:raise ValueError('Abre TIDAL y carga una canción para controlarlo directamente.')
    root=Path(__file__).resolve().parents[1]
    helper=Path(sys.executable).parent/'EddyDeck-Tidal.exe' if getattr(sys,'frozen',False) else root/'.build/EddyDeck-Tidal.exe'
    if not helper.is_file():raise RuntimeError('Falta el controlador de TIDAL. Repara los archivos de Eddy Deck en Windows.')
    p=lease['process']
    try:r=run_owned([str(helper),str(lease['hwnd']),str(p['pid']),str(p['created']),p['path'],action],capture_output=True,text=True,encoding='utf-8-sig',creationflags=HIDDEN,timeout=12)
    except subprocess.TimeoutExpired:raise RuntimeError('TIDAL tardó demasiado. No se repetirá el control automáticamente; revisa el reproductor.') from None
    try:result=json.loads(r.stdout)
    except (ValueError,TypeError):raise RuntimeError('El controlador de TIDAL no devolvió un resultado válido.') from None
    if not isinstance(result,dict):raise RuntimeError('El controlador de TIDAL no devolvió un resultado válido.')
    if r.returncode or result.get('error'):raise RuntimeError(result.get('error') or 'No se pudo controlar TIDAL.')
    if result.get('state') not in ('paused','playing'):raise RuntimeError('El controlador de TIDAL no confirmó un estado reconocido.')
    return result

def snapshot(apps,*,fresh=False):
    global _cached,_until,_cache_key
    with _lock:
        key=tuple(sorted((a['id'],a['target']) for a in apps if folded(a['name'])=='tidal'))
        if not fresh and _cached is not None and key==_cache_key and time.monotonic()<_until:return dict(_cached)
        try:_cached={**invoke('status',apps),'running':True}
        except ValueError as exc:_cached={'available':False,'running':False,'state':'unknown','error':str(exc)}
        except RuntimeError as exc:_cached={'available':False,'running':True,'state':'unknown','error':str(exc)}
        _cache_key=key
        _until=time.monotonic()+1.5
        return dict(_cached)

def control(action,apps):
    global _cached,_until
    with _lock:
        try:return invoke(action,apps)
        finally:_cached=None;_until=0
