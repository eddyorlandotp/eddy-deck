"""Bounded, non-retrying adapter for actual Windows media sessions."""
import json,re,subprocess,sys,threading,time
from pathlib import Path
from companion.windows import HIDDEN
_lock=threading.RLock();_cached=None;_until=0
def valid_target(value):return isinstance(value,str) and re.fullmatch(r'session:[0-9a-f]{32}',value) is not None
def invoke(action,target=''):
    if action not in ('list','status','play','pause','toggle','stop','next','previous') or (action!='list' and not valid_target(target)):raise ValueError('Sesión multimedia no válida.')
    helper=Path(sys.executable).parent/'EddyDeck-Media.exe' if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]/'.build/EddyDeck-Media.exe'
    if not helper.is_file():raise RuntimeError('Falta el controlador multimedia. Repara los archivos de Eddy Deck en Windows.')
    try:r=subprocess.run([str(helper),action,target],capture_output=True,text=True,encoding='utf-8-sig',creationflags=HIDDEN,timeout=10)
    except subprocess.TimeoutExpired:raise RuntimeError('El reproductor tardó demasiado. No se repitió la orden; comprueba su estado.') from None
    try:result=json.loads(r.stdout)
    except (ValueError,TypeError):raise RuntimeError('El controlador multimedia devolvió una respuesta ilegible.') from None
    if not isinstance(result,dict):raise RuntimeError('Respuesta multimedia no válida.')
    if r.returncode or result.get('error'):raise RuntimeError(result.get('error') or 'Windows no pudo controlar el reproductor.')
    if action=='list':
        rows=result.get('players')
        if not isinstance(rows,list) or len(rows)>32 or any(not isinstance(p,dict) or not valid_target(p.get('id')) or not isinstance(p.get('source'),str) or len(p['source'])>2048 or p.get('state') not in ('closed','opened','changing','stopped','playing','paused') or not isinstance(p.get('controls'),dict) or any(type(p['controls'].get(c)) is not bool for c in ('play','pause','stop','next','previous')) for p in rows):raise RuntimeError('Lista multimedia no válida.')
    elif result.get('state') not in ('closed','opened','changing','stopped','playing','paused'):raise RuntimeError('Estado multimedia no válido.')
    return result
def snapshot(apps,*,fresh=False):
    global _cached,_until
    with _lock:
        if fresh or _cached is None or time.monotonic()>=_until:
            try:_cached=invoke('list')
            except RuntimeError as exc:_cached={'players':[],'error':str(exc)}
            _until=time.monotonic()+1.5
        result={**_cached,'players':[]}
        groups={}
        for item in _cached['players']:groups.setdefault(item['id'],[]).append(item)
        for group in groups.values():
            item=group[0]
            source=item.get('source','');key=source.casefold()
            if key=='com.squirrel.tidal.tidal' or key.endswith('aimp.exe'):continue
            app=next((a for a in apps if a['target'].casefold()==key),None)
            name=app['name'] if app else Path(source.replace('\\','/')).name.split('!')[0][:100]
            if len(group)>1:
                result['players'].append({**item,'state':'opened','ambiguous':True,'controls':{k:False for k in ('play','pause','stop','next','previous','toggle')},'name':(name or 'Reproductor')+' · varias sesiones, deja solo una'})
            else:result['players'].append({**item,'name':name or 'Reproductor de Windows'})
        return result
def control(action,target):
    global _cached,_until
    with _lock:
        try:return invoke(action,target)
        finally:_cached=None;_until=0
