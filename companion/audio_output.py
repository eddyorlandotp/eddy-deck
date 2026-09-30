"""Bounded output controls with a lease on the displayed Windows endpoint."""
import copy,json,re,subprocess,sys,threading,time
from pathlib import Path
from companion.child_lifetime import run_owned
_lock=threading.RLock();_cached=None;_until=0
def valid_id(value):return isinstance(value,str) and bool(re.fullmatch(r'\{0\.0\.0\.\d+\}\.\{[0-9a-fA-F-]{36}\}',value))
def validate(action,endpoint='',value=None,expected=''):
    if action not in ('list','select','volume','mute'):raise ValueError('Control de audio no válido.')
    if action!='list' and not valid_id(endpoint):raise ValueError('Salida de audio no válida.')
    if action=='select' and expected!='' and not valid_id(expected):raise ValueError('Salida anterior no válida.')
    if action=='volume' and (type(value) is not int or not 0<=value<=100):raise ValueError('El volumen debe estar entre 0 y 100.')
    if action=='mute' and type(value) is not bool:raise ValueError('Silencio no válido.')
def invoke(action,endpoint='',value=None,expected=''):
    validate(action,endpoint,value,expected)
    helper=Path(sys.executable).parent/'EddyDeck-Audio.exe' if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]/'.build/EddyDeck-Audio.exe'
    if not helper.is_file():raise RuntimeError('Falta el controlador de sonido. Repara Eddy Deck en Windows.')
    args=[str(helper),action]
    if action!='list':args += [endpoint,expected if action=='select' else str(int(value))]
    try:r=run_owned(args,capture_output=True,text=True,encoding='utf-8-sig',creationflags=0x08000000,timeout=5)
    except subprocess.TimeoutExpired:raise RuntimeError('Windows tardó en responder. Comprueba el sonido antes de repetir; la orden no se reenvió.') from None
    try:data=json.loads(r.stdout)
    except (TypeError,ValueError):raise RuntimeError('La respuesta de sonido no es válida.') from None
    if not isinstance(data,dict) or r.returncode or data.get('error'):raise RuntimeError(data.get('error','Windows no pudo controlar el sonido.') if isinstance(data,dict) else 'Respuesta de sonido no válida.')
    rows=data.get('outputs');volume=data.get('volume')
    if not isinstance(rows,list) or len(rows)>128 or any(not isinstance(x,dict) or not valid_id(x.get('id')) or not isinstance(x.get('name'),str) or len(x['name'])>512 for x in rows) or len({x['id'] for x in rows})!=len(rows):raise RuntimeError('Lista de salidas no válida.')
    if volume is not None and (type(volume) is not int or not 0<=volume<=100):raise RuntimeError('Volumen de Windows no válido.')
    if type(data.get('mute')) is not bool or type(data.get('available')) is not bool or data.get('defaultId') not in ('',*[x['id'] for x in rows]):raise RuntimeError('La salida cambió mientras se consultaba. Actualiza la lista.')
    return data
def snapshot():
    global _cached,_until
    with _lock:
        if _cached is None or time.monotonic()>=_until:
            try:_cached=invoke('list')
            except (RuntimeError,OSError) as e:_cached={'outputs':[],'defaultId':'','volume':None,'mute':False,'available':False,'error':str(e)}
            _until=time.monotonic()+1
        return copy.deepcopy(_cached)
def control(action,endpoint,value=None,expected=''):
    global _cached,_until
    with _lock:
        try:
            result=invoke(action,endpoint,value,expected)
            return {'status':'completed','message':'Salida de audio cambiada.' if action=='select' else 'Sonido actualizado.','audio':result}
        finally:_cached=None;_until=0
