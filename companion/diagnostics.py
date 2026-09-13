"""Bounded support reports: no tokens, URLs, window titles or personal paths."""
import datetime as dt,json,logging,os,platform,re,threading,time,uuid
from pathlib import Path
LOCK=threading.RLock()
def safe_message(value):
    text=str(value)[:1000]
    text=re.sub(r'https?://\S+','[URL]',text)
    text=re.sub(r'(?i)(bearer\s+|token[=: ]+|pin[=: ]+|password[=: ]+)\S+',r'\1[oculto]',text)
    text=re.sub(r'[A-Za-z]:[\\/][^\n\r\"\']+','[ruta local]',text)
    return text[:400]
def record(folder,action,status,message=''):
    folder=Path(folder)
    path=folder/'audit.jsonl'
    row={'at':dt.datetime.now(dt.timezone.utc).isoformat(),'action':safe_message(action),'status':status,'message':safe_message(message)}
    try:
        with LOCK:
            folder.mkdir(parents=True,exist_ok=True)
            if path.exists() and path.stat().st_size>512000:
                previous=folder/'audit-previous.jsonl';os.replace(path,previous)
            with path.open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
    except OSError:
        # An auxiliary log failure must never turn an already executed command
        # into an apparent failure that invites the user to execute it twice.
        logging.getLogger(__name__).warning('No se pudo guardar el registro de soporte.')
        return None
    return row
def report(deck,reason='manual'):
    from companion.core import VERSION,atomic_json
    from companion.supervisor import active
    try:jobs=deck.journal.jobs();journal_error=''
    except Exception as exc:jobs=[];journal_error=type(exc).__name__
    with deck.lock:
        out={'id':uuid.uuid4().hex,'at':dt.datetime.now(dt.timezone.utc).isoformat(),'version':VERSION,'reason':reason,'platform':platform.system()+' '+platform.release(),
             'catalog':{'count':len(deck.apps),'scanning':deck.scanning,'warnings':[safe_message(x) for x in deck.warnings]},'profile':{'cards':len(deck.profile['cards']),'routines':len(deck.profile['scenes'])},
             'pairedDevices':len(deck.devices),'supervised':active(deck.data),'queueAlive':deck.queue.thread.is_alive(),
             'powerPending':deck.pending is not None,'jobs':[{'action':safe_message(j['name']),'status':j['status'],'step':j['step'],'total':j['total'],'message':safe_message(j['message'])} for j in jobs],'journalError':journal_error,'queue':deck.queue.status(),'architecture':platform.machine()}
    try:
        import shutil
        from companion.layout import monitors
        out['freeDiskBytes']=shutil.disk_usage(deck.data).free
        out['screens']=[{'width':m['bounds'][2]-m['bounds'][0],'height':m['bounds'][3]-m['bounds'][1],'primary':m['primary']} for m in monitors()]
    except Exception:out['systemDetailsAvailable']=False
    with LOCK:
        try:out['recentActions']=[json.loads(line) for line in (deck.data/'audit.jsonl').read_text(encoding='utf-8').splitlines()[-60:]]
        except (OSError,ValueError):out['recentActions']=[]
    folder=deck.data/'reports';folder.mkdir(exist_ok=True)
    atomic_json(folder/(out['id']+'.json'),out)
    # Only rotate report files made by this module, never user-selected files.
    own=sorted((p for p in folder.glob('*.json') if re.fullmatch('[a-f0-9]{32}',p.stem)),key=lambda p:p.stat().st_mtime)
    for p in own[:-100]:p.unlink(missing_ok=True)
    return out
