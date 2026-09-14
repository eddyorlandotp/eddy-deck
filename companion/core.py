"""Persistent deck, pairing, API and bounded action dispatch."""
from __future__ import annotations
import collections, copy, datetime as dt, hashlib, hmac, ipaddress, json, logging, os, secrets, shutil, socket, ssl, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from companion import windows
from companion.layout import Windows, monitors, validate_layout, resolve_monitor, validate_activation
from companion.jobs import Journal, Queue, ReceiptError
from companion.network import interface_addresses

VERSION='2.2.9-beta.11'
PORT=47990
LOCAL_PORT=47989
DISCOVERY_PORT=47991
COLORS={'peach','mint','blue','lavender','rose','sand'}
LOG=logging.getLogger('eddydeck')

class APIError(Exception):
    def __init__(self, status, message):
        self.status=status; super().__init__(message)

def atomic_json(path, value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    with temp.open('w',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
        stream.flush(); os.fsync(stream.fileno())
    os.replace(temp,path)

def read_json(path, default):
    if not path.exists():
        return copy.deepcopy(default)
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError,OSError):
        raise RuntimeError('No se pudo leer '+path.name+'. Conserva el archivo y restaura tu copia de respaldo.') from None

def clean_text(value, maximum=80):
    if not isinstance(value,str):
        raise ValueError('Se esperaba texto.')
    result=' '.join(value.split())
    if not result or len(result)>maximum:
        raise ValueError('Escribe un nombre de 1 a '+str(maximum)+' caracteres.')
    return result

def private_ip(host):
    try:
        ip=ipaddress.ip_address(host)
        # Explicitly limit to loopback and RFC1918, not every is_private range.
        return ip.version==4 and (ip.is_loopback or any(ip in ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','100.64.0.0/10')))
    except ValueError:
        return False

def local_addresses():
    addresses=set(interface_addresses())
    return sorted(a for a in addresses if private_ip(a) and not a.startswith('127.'))

def ensure_certificate(folder):
    folder=Path(folder)
    cert_path=folder/'server.crt'; key_path=folder/'server.key'
    if not cert_path.exists() or not key_path.exists():
        if (folder/'storage-migration.json').exists() or read_json(folder/'devices.json',[]):
            raise RuntimeError('Falta la identidad de una PC ya vinculada. Conserva los datos y restaura su certificado y llave; no se generó otra identidad.')
        if cert_path.exists() or key_path.exists():
            raise RuntimeError('El certificado está incompleto. Conserva la carpeta de datos antes de repararlo.')
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Eddy Deck local')])
        now=dt.datetime.now(dt.timezone.utc)
        cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
              .serial_number(x509.random_serial_number()).not_valid_before(now-dt.timedelta(days=1))
              .not_valid_after(now+dt.timedelta(days=3650))
              .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False)
              .sign(key,hashes.SHA256()))
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    cert=x509.load_pem_x509_certificate(cert_path.read_bytes())
    return cert_path,key_path,cert.fingerprint(hashes.SHA256()).hex()

class Deck:
    def __init__(self,data,resources,adapter=windows,dry_run=False):
        self.data=Path(data); self.resources=Path(resources); self.adapter=adapter; self.dry_run=dry_run
        self.data.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock(); self.action_lock=threading.Lock(); self.scan_lock=threading.Lock()
        self.profile=read_json(self.data/'deck.json',{'version':1,'cards':[],'scenes':[],'theme':'light','seeded':False})
        if self.profile.get('version')==1:
            if (self.data/'deck.json').exists():atomic_json(self.data/'deck-before-v2.json',self.profile)
            self.profile['version']=2
        self.devices=read_json(self.data/'devices.json',[])
        self.sessions={}
        self.manual=read_json(self.data/'manual-apps.json',[])
        self.catalog_hints=read_json(self.data/'catalog-hints.json',{})
        self.apps=[]; self.warnings=[]; self.scanned=None; self.scanning=False
        self.local_token=secrets.token_urlsafe(32)
        self.pin=None; self.pin_until=0; self.attempts=collections.deque()
        self.pending=None; self.closed=False; self.repairing=False;self.repair_until=None
        self.challenges={}; self.requests=collections.OrderedDict(); self.events=collections.deque(maxlen=30)
        self.servers=[]; self.fingerprint=''; self.port=PORT; self.local_port=LOCAL_PORT
        self.addresses=local_addresses(); self.power_error=''
        self.media_lock=threading.Lock();self.layouts=Windows()
        self.journal=Journal(self.data)
        self.queue=Queue(self.journal,self.execute_step,self.event,lambda device:device=='local' or any(d['id']==device for d in self.devices))
        self.awake=None

    def save(self):
        if len(json.dumps(self.profile).encode())>1500000:raise ValueError('El panel supera el límite de respaldo. Reduce URLs o pasos antes de guardar.')
        atomic_json(self.data/'deck.json',self.profile)

    def renew_pin(self):
        with self.lock:
            self.pin=f'{secrets.randbelow(100000000):08d}'; self.pin_until=time.monotonic()+600
            return self.pin

    def pair(self,body,client):
        with self.lock:
            now=time.monotonic()
            while self.attempts and self.attempts[0]<now-300:
                self.attempts.popleft()
            if len(self.attempts)>=10:
                raise APIError(429,'Demasiados intentos. Espera cinco minutos.')
            self.attempts.append(now)
            if not self.pin or now>=self.pin_until or not hmac.compare_digest(str(body.get('pin','')),self.pin):
                raise APIError(401,'Código incorrecto o vencido. Genera otro en la PC.')
            name=clean_text(body.get('name','Android'),60)
            token=secrets.token_urlsafe(32); device_id=uuid.uuid4().hex
            if len(self.devices)>=20:raise APIError(409,'Hay 20 vínculos guardados. Revoca uno desde Windows antes de agregar otro celular.')
            updated=self.devices+[{'id':device_id,'name':name,'hash':hashlib.sha256(token.encode()).hexdigest(),'paired':dt.datetime.now(dt.timezone.utc).isoformat()}]
            atomic_json(self.data/'devices.json',updated);self.devices=updated
            self.pin=None; self.pin_until=0
            return {'token':token,'deviceId':device_id,'name':socket.gethostname(),'version':VERSION}

    def authenticate(self,token,local=False,client=None):
        if local and hmac.compare_digest(token,self.local_token):
            return 'local'
        digest=hashlib.sha256(token.encode()).hexdigest()
        with self.lock:
            for device in self.devices:
                if hmac.compare_digest(digest,device['hash']):
                    if client:
                        self.sessions[device['id']]={'name':device['name'],'via':'USB' if client.startswith('127.') else 'Internet / VPN' if ipaddress.ip_address(client) in ipaddress.ip_network('100.64.0.0/10') else 'Wi-Fi','at':time.time()}
                    return device['id']
        raise APIError(401,'Conexión revocada o no vinculada. Vuelve a conectar tu celular.')

    def refresh(self):
        if not self.scan_lock.acquire(blocking=False):
            return {'status':'scanning'}
        self.scanning=True
        try:
            apps,warnings=self.adapter.scan(self.resources/'companion')
            with self.lock:
                before=self.export_profile();original=copy.deepcopy(self.profile)
                self.apps=apps+copy.deepcopy(self.manual)
                for app in self.apps:
                    if app['kind']=='manual': app['available']=windows.safe_executable(app['target'])
                self.warnings=warnings
                self.scanned=dt.datetime.now(dt.timezone.utc).isoformat()
                if self.profile.get('seeded'):
                    adapted,mapped,missing=self.remap_profile(before)
                    if mapped:
                        atomic_json(self.data/'deck.json',adapted);self.profile=adapted
                        self.warnings.append(f'Se adaptaron {mapped} referencias después de actualizar aplicaciones.')
                    if missing:self.warnings.append(f'{missing} aplicaciones del panel no están disponibles. Revisa sus botones y rutinas.')
                if not self.profile.get('seeded'):
                    preferred=['opera gx','aimp','discord','steam','obs studio','explorador de archivos']
                    for term in preferred:
                        candidates=[a for a in self.apps if term in windows.folded(a['name'])]
                        if len(candidates)==1:
                            self.profile['cards'].append(self.make_card(candidates[0],len(self.profile['cards'])))
                    self.profile['seeded']=True
                    try:self.save()
                    except Exception:self.profile=original;raise
                hints=self.export_profile()['catalogHints']
                atomic_json(self.data/'catalog-hints.json',hints);self.catalog_hints=hints
            return {'status':'ok','count':len(self.apps),'warnings':warnings}
        finally:
            self.scanning=False; self.scan_lock.release()

    def start_scan(self):
        def work():
            try: self.refresh()
            except Exception as exc:
                with self.lock: self.warnings=[str(exc)]
                LOG.exception('Falló la sincronización')
        threading.Thread(target=work,daemon=True).start()

    def make_card(self,app,index):
        return {'id':uuid.uuid4().hex,'appId':app['id'],'name':app['name'],'url':'','color':list(sorted(COLORS))[index%len(COLORS)]}

    def find_app(self,app_id):
        with self.lock:
            app=next((a for a in self.apps if a['id']==app_id),None)
            if not app or not app.get('available',True):
                raise ValueError('La aplicación no está disponible. Sincroniza el catálogo en Biblioteca.')
            return copy.deepcopy(app)

    def state(self):
        from companion.supervisor import active
        with self.lock:
            apps=copy.deepcopy(self.apps); profile=copy.deepcopy(self.profile)
            result={'version':VERSION,'protocolVersion':2,'capabilities':{'windowControls':True,'launchForeground':True,'fileRepair':True,'queuePause':True,'mediaSessions':True},'name':socket.gethostname(),'connected':True,'profile':profile,
                    'apps':apps,'scanned':self.scanned,'scanning':self.scanning,'warnings':self.warnings,
                    'events':list(self.events),'pending':self.pending_status(),'powerError':self.power_error,
                    'dryRun':self.dry_run,'addresses':self.addresses,'port':self.port,
                    'devices':[{k:v for k,v in d.items() if k!='hash'} for d in self.devices],
                    'repairing':self.repairing,'supervised':active(self.data),
                    'keepAwake':self.awake.status() if self.awake else {'active':False,'error':'','scope':'not-started','displayRequired':False}}
        try: result['media']=self.adapter.media_snapshot(apps)
        except Exception: result['media']={'aimp':False,'state':'unknown','label':'Reproductor de Windows'}
        result['displayWarning']=''
        try:result['monitors']=monitors()
        except Exception:result['monitors']=[];result['displayWarning']='Windows no pudo consultar las pantallas. La música y las aperturas sin diseño siguen disponibles.'
        try:result['windows']=self.layouts.snapshot(apps)
        except Exception:result['windows']=[]
        result['queue']=self.queue.status()
        from companion.integrity import repair_status
        result['installation']=repair_status(self.data)
        result['jobs']=[{k:v for k,v in job.items() if k!='device'} for job in self.journal.jobs()]
        result['internet']={'addresses':[a for a in local_addresses() if ipaddress.ip_address(a) in ipaddress.ip_network('100.64.0.0/10')],'method':'Tailscale'}
        result['startup']=(Path(os.environ.get('APPDATA',''))/'Microsoft/Windows/Start Menu/Programs/Startup/Eddy Deck.lnk').is_file()
        return result

    def event(self,message):
        with self.lock:
            self.events.appendleft({'time':dt.datetime.now().strftime('%H:%M'),'message':message})

    def execute_app(self,app_id,url=''):
        app=self.find_app(app_id); url=windows.validate_url(url)
        if url and not app['browser']:
            raise ValueError('Solo los navegadores compatibles admiten una URL.')
        if self.dry_run:
            return {'status':'simulated','message':'Prueba sin abrir: '+app['name']}
        result=self.adapter.launch(app,url)
        self.event(result['message'])
        return result

    def dispatch(self,path,body,device):
        if path=='/api/power/cancel':
            # Cancellation must never wait behind a slow launcher or a scene.
            with self.lock: self.pending=None
            self.event('Acción de energía cancelada')
            return {'status':'cancelled','message':'Acción cancelada'}
        if path=='/api/operations/status':return self.journal.receipt(device,body.get('id',''))
        from companion.diagnostics import record
        try:
            result=self.journal.invoke(path,body,device,lambda:self._transaction(path,body,device))
            record(self.data,path,result.get('status','ok'))
            return result
        except Exception as exc:
            record(self.data,path,'failed',str(exc))
            if isinstance(exc,ReceiptError):raise APIError(exc.status,str(exc)) from None
            raise

    def _transaction(self,path,body,device):
        if path not in {'/api/cards/save','/api/cards/delete','/api/cards/move','/api/scenes/save','/api/scenes/delete','/api/backup/import','/api/devices/revoke'}:
            return self._dispatch(path,body,device)
        with self.lock:
            profile=copy.deepcopy(self.profile);devices=copy.deepcopy(self.devices)
            try:return self._dispatch(path,body,device)
            except Exception:
                self.profile=profile;self.devices=devices;raise

    def clean_step(self,step,check_apps=True):
        if not isinstance(step,dict):raise ValueError('Paso de rutina no válido.')
        kind=step.get('type','launch')
        if kind=='wait':
            seconds=step.get('seconds',1)
            if type(seconds) not in (int,float) or not 0<=seconds<=30:raise ValueError('La espera debe durar de 0 a 30 segundos.')
            return {'type':'wait','seconds':seconds}
        if kind=='media':
            target=step.get('target','system');action=step.get('action')
            windows.validate_media_action(action,target,routine=True)
            return {'type':'media','target':target,'action':action}
        if kind not in ('launch','window'):raise ValueError('Tipo de paso no permitido.')
        aid=clean_text(step.get('appId',''),64);url=windows.validate_url(step.get('url',''))
        if check_apps:
            app=self.find_app(aid)
            if url and not app['browser']:raise ValueError('Esta aplicación no admite una URL.')
        policy=step.get('ifOpen','reuse')
        if policy not in ('reuse','launch'):raise ValueError('Opción de aplicación abierta no válida.')
        result={'type':kind,'appId':aid,'url':url,'layout':validate_layout(step.get('layout')),'ifOpen':policy}
        if kind=='launch':result['activation']=validate_activation(step.get('activation','front'))
        return result

    def enqueue(self,name,steps,device,on_error='stop'):
        # This lock is also used by energy confirmation and repair. There is no
        # gap between checking them and admitting a new window/routine command.
        with self.lock:
            if self.pending or self.repairing:raise APIError(409,'Hay una acción de energía o reparación pendiente. Cancélala o espera.')
            return self.queue.submit(name,steps,device,on_error)

    def export_profile(self):
        with self.lock:
            profile=copy.deepcopy(self.profile)
            referenced={c['appId'] for c in profile['cards']}|{s['appId'] for r in profile['scenes'] for s in r['steps'] if 'appId' in s}
            hints={**self.catalog_hints,**{a['id']:{'name':a['name'],'identity':a['target'] if a['kind'] in ('protocol','shell') and not Path(a['target']).is_absolute() else ''} for a in self.apps if a['id'] in referenced}}
            profile['catalogHints']={k:v for k,v in hints.items() if k in referenced}
            return profile

    def remap_profile(self,raw):
        profile=validate_profile(raw);hints=raw.get('catalogHints',{})
        if not isinstance(hints,dict) or len(hints)>2000:raise ValueError('Mapa de aplicaciones no válido.')
        with self.lock:apps=copy.deepcopy(self.apps)
        ids={a['id'] for a in apps};mapped={};missing=set()
        entries=profile['cards']+[s for scene in profile['scenes'] for s in scene['steps'] if 'appId' in s]
        for entry in entries:
            aid=entry['appId']
            if aid in ids:continue
            hint=hints.get(aid,{})
            if not isinstance(hint,dict):raise ValueError('Referencia de aplicación no válida.')
            identity=hint.get('identity');name=hint.get('name')
            found=[a for a in apps if identity and a['target']==identity]
            if not found and isinstance(name,str):found=[a for a in apps if windows.folded(a['name'])==windows.folded(name)]
            if len(found)==1:entry['appId']=found[0]['id'];mapped[aid]=found[0]['id']
            else:missing.add(aid)
        return profile,len(mapped),len(missing)

    def execute_step(self,step,check):
        check();kind=step['type']
        if kind=='wait':
            until=time.monotonic()+step['seconds']
            while time.monotonic()<until:check();time.sleep(min(.1,max(0,until-time.monotonic())))
            return {'status':'completed','message':'Espera completada'}
        if self.dry_run:return {'status':'simulated','message':'Paso validado sin modificar Windows.'}
        if kind=='media':
            # Waiting for a direct music control must remain cancellable too.
            while not self.media_lock.acquire(timeout=.1):check()
            try:check();return self.adapter.media(step['action'],step['target'],self.apps)
            finally:self.media_lock.release()
        if kind=='windowId':return self.layouts.move(step['windowId'],step['layout'],self.apps,check)
        if kind=='windowClose':return self.layouts.close_window(step['windowId'],self.apps,check)
        if kind=='windowRestore':return self.layouts.restore(step['windowId'],self.apps,check)
        if kind=='windowTerminate':
            if time.monotonic()>=step['expires']:raise ValueError('La finalización esperó demasiado en cola. Confírmala de nuevo si todavía la necesitas.')
            return self.layouts.terminate_window(step['windowId'],self.apps,check)
        app=self.find_app(step['appId']);settings=step['layout']
        if kind=='launch' and step.get('ifOpen','reuse')=='reuse' and not step['url'] and self.adapter is windows:
            found=[w for w in self.layouts.snapshot(self.apps) if app['id'] in w['appIds']]
            if found:
                if len(found)>1 and step.get('activation','front')=='windows' and settings['monitor']=='keep' and settings['mode']=='keep':
                    if all(w['minimized'] for w in found):raise ValueError('Hay varias ventanas minimizadas. Selecciona cuál restaurar en Mi PC.')
                    return {'status':'already_open','message':app['name']+' ya está abierta. Se conserva su ventana.'}
                if len(found)!=1:raise ValueError('Hay varias ventanas de '+app['name']+'. Selecciona una en Mi PC.')
                return self.layouts.present(found[0]['id'],settings,self.apps,check,step.get('activation','front'))
        if kind=='window':
            found=[w for w in self.layouts.snapshot(self.apps) if app['id'] in w['appIds']]
            if len(found)!=1:raise ValueError('No hay una ventana única de '+app['name']+'. Abre la app o selecciona su ventana en Mi PC.')
            return self.layouts.move(found[0]['id'],settings,self.apps,check)
        if self.adapter is windows:return self.layouts.launch(app,step['url'],settings,self.apps,check,step.get('activation','front'))
        if settings['monitor']=='keep' and settings['mode']=='keep':return self.execute_app(app['id'],step['url'])
        return self.layouts.launch(app,step['url'],settings,self.apps,check)

    def _dispatch(self,path,body,device):
        if path in ('/api/cards/save','/api/cards/delete','/api/cards/move','/api/scenes/save','/api/scenes/delete','/api/backup/import'):
            # Failed validation/disk writes cannot leave invisible edits in
            # memory which a later successful save accidentally persists.
            with self.lock:
                previous=copy.deepcopy(self.profile)
                try:return self._dispatch_inner(path,body,device)
                except Exception:self.profile=previous;raise
        return self._dispatch_inner(path,body,device)

    def _dispatch_inner(self,path,body,device):
        with self.lock:
            if self.closed:raise APIError(503,'Eddy Deck se está cerrando. Espera a que vuelva la conexión.')
        if self.repairing and path not in ('/api/diagnostics','/api/repair','/api/jobs/cancel'):
            raise APIError(409,'El receptor se está reparando. Espera a que vuelva la conexión.')
        if path=='/api/diagnostics':
            from companion.diagnostics import report
            return {'status':'ready','report':report(self)}
        if path=='/api/installation/check':
            if self.dry_run:return {'status':'verified','version':VERSION,'files':0,'message':'Comprobación simulada.'}
            import sys
            from companion.integrity import verify_release
            if not getattr(sys,'frozen',False):return {'status':'source','message':'Esta instancia ejecuta el código fuente; no es una instalación empaquetada.'}
            m=verify_release(Path(sys.executable).parent)
            return {'status':'verified','version':m['version'],'files':len(m['files']),'message':'Firma y archivos de Eddy Deck correctos.'}
        if path=='/api/installation/repair':
            if body.get('confirm') is not True:raise APIError(400,'Confirma la reparación de archivos de Eddy Deck.')
            if self.dry_run:return {'status':'simulated','message':'Reparación de archivos simulada.'}
            from companion.integrity import start_repair
            from companion.diagnostics import report
            with self.lock:
                if self.repairing:raise APIError(409,'Eddy Deck ya se está reparando.')
                self.check_repair_cooldown()
                self.pending=None;self.queue.cancel_all()
                diagnosis=report(self,'before-file-repair')
                atomic_json(self.data/'repair-state.json',{'at':time.time(),'reportId':diagnosis['id']})
                self.repair_until=time.monotonic()+60
                self.repairing=True
                try:result=start_repair(self.data)
                except Exception:
                    self.repairing=False
                    raise
                return result
        if path=='/api/repair':
            if body.get('confirm') is not True:raise APIError(400,'Confirma la reparación del receptor.')
            if self.dry_run:return {'status':'simulated','message':'Reparación simulada.'}
            from companion.supervisor import active
            if not active(self.data):raise APIError(409,'El supervisor no responde. Sal de Eddy Deck desde la bandeja de Windows y vuelve a abrirlo.')
            with self.lock:
                if self.repairing:return {'status':'restarting','message':'La reparación ya está en curso.'}
                self.check_repair_cooldown()
                self.pending=None;self.queue.cancel_all()
                from companion.diagnostics import report
                diagnosis=report(self,'before-repair')
                atomic_json(self.data/'repair-state.json',{'at':time.time(),'reportId':diagnosis['id']})
                self.repair_until=time.monotonic()+60
                self.repairing=True
                try:atomic_json(self.data/'restart-request.json',{'pid':os.getpid(),'after':time.time()+3,'afterMonotonic':time.monotonic()+3})
                except Exception:
                    self.repairing=False
                    raise
            return {'status':'restarting','message':'Reiniciando Eddy Deck en Windows. La conexión volverá automáticamente.','reportId':diagnosis['id']}
        if path in ('/api/launch','/api/windows/move','/api/scenes/run'):
            with self.lock:
                if self.pending:raise APIError(409,'Hay una acción de energía pendiente. Cancélala antes de abrir o mover aplicaciones.')
        if path=='/api/refresh':
            self.start_scan(); return {'status':'scanning'}
        if path=='/api/launch':
            step=self.clean_step(body)
            return self.enqueue('Abrir '+self.find_app(step['appId'])['name'],[step],device)
        if path=='/api/windows/move':
            wid=body.get('windowId');settings=validate_layout(body.get('layout'))
            if not any(w['id']==wid for w in self.layouts.snapshot(self.apps)):raise ValueError('La ventana ya se cerró. Actualiza Mi PC.')
            resolve_monitor(settings,monitors())
            return self.enqueue('Mover ventana',[{'type':'windowId','windowId':wid,'layout':settings}],device)
        if path=='/api/windows/protect':
            if type(body.get('protected')) is not bool:raise ValueError('Protección no válida.')
            return self.layouts.protect(body.get('windowId'),body['protected'],self.apps)
        if path=='/api/windows/restore':
            self.layouts.require_window(body.get('windowId'),self.apps)
            return self.enqueue('Restaurar ventana',[{'type':'windowRestore','windowId':body['windowId']}],device)
        if path=='/api/windows/close':
            if body.get('confirm') is not True:raise APIError(400,'Confirma el cierre normal de la ventana.')
            self.layouts.require_window(body.get('windowId'),self.apps)
            return self.enqueue('Cerrar ventana',[{'type':'windowClose','windowId':body['windowId']}],device)
        if path=='/api/windows/terminate/prepare':
            item=self.layouts.require_window(body.get('windowId'),self.apps,terminate=True)
            with self.lock:
                self.challenges={k:v for k,v in self.challenges.items() if v['expires']>time.monotonic()}
                challenge=secrets.token_urlsafe(24)
                self.challenges[challenge]={'action':'terminate','device':device,'windowId':item['id'],'expires':time.monotonic()+20}
            return {'challenge':challenge,'process':item['process'],'expiresIn':20}
        if path=='/api/windows/terminate/confirm':
            with self.lock:
                challenge=self.challenges.get(str(body.get('challenge','')))
                if not challenge or challenge['action']!='terminate' or challenge['device']!=device or challenge['expires']<=time.monotonic():raise APIError(409,'La confirmación venció o pertenece a otra acción.')
                self.layouts.require_window(challenge['windowId'],self.apps,terminate=True)
                if self.queue.status()['paused']:raise APIError(409,'Reanuda la cola antes de finalizar un proceso.')
                result=self.enqueue('Finalizar proceso',[{'type':'windowTerminate','windowId':challenge['windowId'],'expires':challenge['expires']}],device)
                self.challenges.pop(body['challenge'],None)
                return result
        if path=='/api/jobs/pause':
            if type(body.get('paused')) is not bool:raise ValueError('Pausa no válida.')
            return self.queue.pause(body['paused'])
        if path=='/api/jobs/cancel':return self.queue.cancel(body.get('id'),device)
        if path=='/api/startup':
            if device!='local':raise APIError(403,'Cambia el inicio automático desde el panel de Windows.')
            if type(body.get('enabled'))!=bool:raise ValueError('Opción no válida.')
            from companion.desktop import configure_startup
            configure_startup(body['enabled']);return {'status':'saved'}
        if path=='/api/media':
            windows.validate_media_action(body.get('action'),body.get('target','system'),body.get('value'))
            if self.dry_run: return {'status':'simulated','message':'Control simulado'}
            if not self.media_lock.acquire(timeout=2):raise APIError(409,'Otro control de música sigue en curso. Espera su resultado antes de repetirlo.')
            try:
                if self.closed or self.repairing:raise APIError(409,'Eddy Deck está reiniciando. No se envió el control de música.')
                return self.adapter.media(body.get('action'),body.get('target','system'),self.apps,body.get('value'))
            finally:self.media_lock.release()
        if path=='/api/cards/save':
            app=self.find_app(body.get('appId'))
            name=clean_text(body.get('name',app['name']))
            url=windows.validate_url(body.get('url',''))
            if url and not app['browser']: raise ValueError('Esta app no admite URLs.')
            color=body.get('color','peach')
            if color not in COLORS: raise ValueError('Color no válido.')
            layout=validate_layout(body.get('layout'),allow_ask=True)
            activation=validate_activation(body.get('activation','front'))
            with self.lock:
                card_id=body.get('id')
                if card_id:
                    card=next((c for c in self.profile['cards'] if c['id']==card_id),None)
                    if not card: raise ValueError('El botón ya no existe.')
                else:
                    if len(self.profile['cards'])>=200: raise ValueError('El máximo es 200 botones.')
                    card=self.make_card(app,len(self.profile['cards'])); self.profile['cards'].append(card)
                policy=body.get('ifOpen','reuse')
                if policy not in ('reuse','launch'):raise ValueError('Opción de aplicación abierta no válida.')
                card.update(appId=app['id'],name=name,url=url,color=color,layout=layout,ifOpen=policy,activation=activation); self.save()
                return {'status':'saved','card':copy.deepcopy(card)}
        if path=='/api/cards/delete':
            with self.lock:
                self.profile['cards']=[c for c in self.profile['cards'] if c['id']!=body.get('id')]; self.save()
            return {'status':'deleted'}
        if path=='/api/cards/move':
            with self.lock:
                cards=self.profile['cards']; idx=next((i for i,c in enumerate(cards) if c['id']==body.get('id')),None)
                if idx is None: raise ValueError('El botón ya no existe.')
                delta=body.get('direction')
                if delta not in (-1,1): raise ValueError('Dirección no válida.')
                target=max(0,min(len(cards)-1,idx+delta)); cards.insert(target,cards.pop(idx)); self.save()
            return {'status':'saved'}
        if path=='/api/scenes/save':
            name=clean_text(body.get('name',''))
            steps=body.get('steps')
            if not isinstance(steps,list) or not 1<=len(steps)<=24: raise ValueError('Elige de 1 a 24 pasos.')
            clean=[self.clean_step(step) for step in steps]
            on_error=body.get('onError','stop')
            if on_error not in ('stop','continue'):raise ValueError('Política de errores no válida.')
            with self.lock:
                scene_id=body.get('id')
                scene=next((s for s in self.profile['scenes'] if s['id']==scene_id),None)
                if scene_id and not scene:raise ValueError('La rutina ya no existe. Cierra el editor y crea una nueva si la necesitas.')
                if not scene:
                    if len(self.profile['scenes'])>=50: raise ValueError('El máximo es 50 modos.')
                    scene={'id':uuid.uuid4().hex}; self.profile['scenes'].append(scene)
                scene.update(name=name,steps=clean,onError=on_error); self.save()
            return {'status':'saved'}
        if path=='/api/scenes/delete':
            with self.lock:
                self.profile['scenes']=[s for s in self.profile['scenes'] if s['id']!=body.get('id')]; self.save()
            return {'status':'deleted'}
        if path=='/api/scenes/run':
            with self.lock:
                scene=next((copy.deepcopy(s) for s in self.profile['scenes'] if s['id']==body.get('id')),None)
            if not scene: raise ValueError('El modo ya no existe.')
            steps=[self.clean_step(s) for s in scene['steps']]
            if scene.get('onError','stop')=='stop':
                for s in steps:
                    if 'layout' in s and (s['type']=='window' or s['layout']['monitor']!='keep' or s['layout']['mode']!='keep'):resolve_monitor(s['layout'],monitors())
            return self.enqueue(scene['name'],steps,device,scene.get('onError','stop'))
        if path=='/api/power/prepare':
            action=body.get('action')
            if action not in ('shutdown','restart','sleep','lock'): raise ValueError('Acción no válida.')
            with self.lock:
                self.challenges={k:v for k,v in self.challenges.items() if v['expires']>time.monotonic()}
                challenge=secrets.token_urlsafe(24)
                self.challenges[challenge]={'action':action,'device':device,'expires':time.monotonic()+30}
            return {'challenge':challenge,'action':action,'expiresIn':30}
        if path=='/api/power/confirm':
            with self.lock:
                challenge=self.challenges.get(str(body.get('challenge','')))
                if not challenge or challenge['action'] not in ('shutdown','restart','sleep','lock') or challenge['device']!=device or challenge['expires']<=time.monotonic():
                    raise APIError(409,'La confirmación venció. Vuelve a elegir la acción.')
                if self.pending: raise APIError(409,'Ya hay una acción programada. Cancélala primero.')
                self.challenges.pop(str(body.get('challenge','')),None)
                self.queue.cancel_all()
                self.pending={'id':uuid.uuid4().hex,'action':challenge['action'],'at':time.time()+15,'deadline':time.monotonic()+15,'device':device}
                self.power_error=''
                pending=copy.deepcopy(self.pending)
                threading.Thread(target=self._power_countdown,args=(pending,),daemon=True).start()
                public_pending=self.pending_status()
            return {'status':'scheduled','pending':public_pending}
        if path=='/api/power/cancel':
            with self.lock: self.pending=None
            self.event('Acción de energía cancelada')
            return {'status':'cancelled','message':'Acción cancelada'}
        if path=='/api/devices/revoke':
            if device!='local': raise APIError(403,'Revoca dispositivos desde el panel de la PC.')
            with self.lock:
                self.devices=[d for d in self.devices if d['id']!=body.get('id')]
                atomic_json(self.data/'devices.json',self.devices)
            return {'status':'revoked'}
        if path=='/api/backup/import':
            profile,mapped,missing=self.remap_profile(body.get('profile'))
            with self.lock:
                atomic_json(self.data/('deck-before-import-'+str(int(time.time()))+'.json'),self.profile)
                self.profile=profile; self.save()
            return {'status':'saved','mappedApps':mapped,'missingApps':missing,'message':f'Copia restaurada. {mapped} referencias adaptadas; {missing} aplicaciones pendientes de seleccionar.'}
        raise APIError(404,'Acción no disponible.')

    def check_repair_cooldown(self):
        if self.repair_until is None:
            previous=read_json(self.data/'repair-state.json',{})
            age=max(0,time.time()-previous['at']) if 'at' in previous else 60
            self.repair_until=time.monotonic()+max(0,60-age)
        if time.monotonic()<self.repair_until:raise APIError(429,'Espera un minuto antes de otra reparación.')

    def pending_status(self):
        with self.lock:
            if not self.pending:return None
            result={k:v for k,v in self.pending.items() if k not in ('device','deadline')}
            result['remainingSeconds']=max(0,self.pending['deadline']-time.monotonic())
            return result

    def _power_countdown(self,pending):
        while time.monotonic()<pending['deadline']:
            time.sleep(.15)
            with self.lock:
                if self.closed or not self.pending or self.pending['id']!=pending['id']: return
                if pending.get('device','local')!='local' and not any(d['id']==pending['device'] for d in self.devices):self.pending=None;return
        with self.lock:
            if self.closed or not self.pending or self.pending['id']!=pending['id']: return
            # A stalled worker may skip the loop entirely. Recheck authorization
            # at the dispatch boundary before committing the physical command.
            if pending.get('device','local')!='local' and not any(d['id']==pending['device'] for d in self.devices):self.pending=None;return
            self.pending=None
        if self.dry_run:
            self.event('Prueba de energía completada sin cambiar Windows'); return
        try:
            self.adapter.power(pending['action']); self.event('Orden de energía enviada a Windows')
        except Exception as exc:
            with self.lock: self.power_error=str(exc)
            self.event(str(exc))

    def close(self):
        with self.lock: self.closed=True; self.pending=None
        # Every owned resource gets its cleanup attempt even when another
        # resource fails. Keep the original startup error available to its caller.
        for resource in ([self.awake] if self.awake else [])+[self.queue]:
            try:resource.close()
            except Exception:LOG.exception('No se pudo liberar un recurso de Eddy Deck')
        for server in self.servers:
            try:server.shutdown()
            except Exception:LOG.exception('No se pudo detener un servidor de Eddy Deck')
            finally:
                try:server.server_close()
                except Exception:LOG.exception('No se pudo cerrar un socket de Eddy Deck')

def validate_profile(profile):
    if not isinstance(profile,dict) or profile.get('version') not in (1,2): raise ValueError('Copia de seguridad incompatible.')
    if len(json.dumps({k:v for k,v in profile.items() if k!='catalogHints'}).encode())>1500000:raise ValueError('El panel supera el límite de respaldo. Reduce URLs o pasos.')
    cards=profile.get('cards'); scenes=profile.get('scenes')
    if not isinstance(cards,list) or not isinstance(scenes,list) or len(cards)>200 or len(scenes)>50:
        raise ValueError('Copia de seguridad no válida.')
    result={'version':2,'seeded':True,'theme':'light','cards':[],'scenes':[]}
    seen=set()
    for card in cards:
        cid=clean_text(card.get('id',''),64); aid=clean_text(card.get('appId',''),64)
        if cid in seen: raise ValueError('Hay identificadores duplicados.')
        seen.add(cid)
        color=card.get('color','peach')
        if color not in COLORS: raise ValueError('Color de botón no válido.')
        policy=card.get('ifOpen','reuse')
        if policy not in ('reuse','launch'):raise ValueError('Opción de aplicación abierta no válida.')
        result['cards'].append({'id':cid,'appId':aid,'name':clean_text(card.get('name','')),'url':windows.validate_url(card.get('url','')),'color':color,'layout':validate_layout(card.get('layout'),True),'ifOpen':policy,'activation':validate_activation(card.get('activation','front'))})
    for scene in scenes:
        sid=clean_text(scene.get('id',''),64)
        if sid in seen: raise ValueError('Hay identificadores duplicados.')
        seen.add(sid)
        steps=scene.get('steps')
        if not isinstance(steps,list) or not 1<=len(steps)<=24: raise ValueError('Modo no válido.')
        on_error=scene.get('onError','stop')
        if on_error not in ('stop','continue'):raise ValueError('Política de errores no válida.')
        result['scenes'].append({'id':sid,'name':clean_text(scene.get('name','')),'steps':[Deck.clean_step(None,s,False) for s in steps],'onError':on_error})
    if len(json.dumps(result).encode())>1500000:raise ValueError('El panel supera el límite de respaldo. Reduce URLs o pasos.')
    return result

class Server(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=False
    request_queue_size=16
    def __init__(self,address,deck,local):
        self.deck=deck; self.local=local; self.slots=threading.BoundedSemaphore(24)
        super().__init__(address,Handler)
    def process_request(self,request,address):
        if not private_ip(address[0]) or not self.slots.acquire(blocking=False):
            request.close(); return
        try: super().process_request(request,address)
        except Exception: self.slots.release(); raise
    def process_request_thread(self,request,address):
        try: super().process_request_thread(request,address)
        finally: self.slots.release()
    def handle_error(self,request,address):
        LOG.warning('Solicitud interrumpida')

class Handler(BaseHTTPRequestHandler):
    server_version='EddyDeck'
    sys_version=''
    def setup(self):
        self.request.settimeout(10)
        super().setup()
    def log_message(self,*args): pass
    def respond(self,status,value,content_type='application/json; charset=utf-8'):
        body=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers(); self.wfile.write(body)
    def guard(self):
        host=self.headers.get('Host','')
        if self.server.local:
            valid={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
            if host not in valid: raise APIError(403,'Host no permitido.')
        origin=self.headers.get('Origin')
        expected=('http' if self.server.local else 'https')+'://'+host
        if origin and origin!=expected: raise APIError(403,'Origen no permitido.')
        if not private_ip(self.client_address[0]): raise APIError(403,'Solo red local.')
    def authenticate(self):
        auth=self.headers.get('Authorization','')
        if not auth.startswith('Bearer '): raise APIError(401,'Vincula primero el dispositivo.')
        return self.server.deck.authenticate(auth[7:],self.server.local,self.client_address[0])
    def do_GET(self):
        try:
            self.guard(); path=urlsplit(self.path).path
            if path=='/health':
                healthy=self.server.deck.queue.status()['healthy']
                return self.respond(200 if healthy else 503,{'name':'Eddy Deck','version':VERSION,'healthy':healthy})
            if path=='/api/heartbeat':
                self.authenticate();return self.respond(200,{'name':socket.gethostname(),'version':VERSION,'addresses':local_addresses()})
            if path in ('/api/state','/api/backup'):
                self.authenticate()
                return self.respond(200,self.server.deck.state() if path.endswith('state') else self.server.deck.export_profile())
            files={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/extended.js':'extended.js','/beta2.js':'beta2.js','/pickers.js':'pickers.js','/manual.js':'manual.js','/styles.css':'styles.css','/icon.svg':'icon.svg'}
            if path not in files: raise APIError(404,'No encontrado.')
            filename=files[path]
            mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml'}[Path(filename).suffix]
            self.respond(200,(self.server.deck.resources/'ui'/filename).read_bytes(),mime)
        except APIError as exc: self.respond(exc.status,{'error':str(exc)})
        except (BrokenPipeError,ConnectionResetError): pass
        except Exception:
            LOG.exception('Error leyendo API'); self.respond(500,{'error':'No se pudo leer el estado.'})
    def do_POST(self):
        try:
            self.guard()
            if self.headers.get('Transfer-Encoding'): raise APIError(400,'Formato no compatible.')
            if self.headers.get_content_type()!='application/json': raise APIError(415,'Usa JSON.')
            path=urlsplit(self.path).path
            # Authenticate large imports before reading their bounded body.
            limit=4*1024*1024 if path=='/api/backup/import' else 131072
            if path=='/api/backup/import':self.authenticate()
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=limit: raise APIError(413,'Solicitud demasiado grande o vacía.')
            body=json.loads(self.rfile.read(size))
            if not isinstance(body,dict): raise APIError(400,'Solicitud no válida.')
            path=urlsplit(self.path).path
            if path=='/auth/pair': result=self.server.deck.pair(body,self.client_address[0])
            else: result=self.server.deck.dispatch(path,body,self.authenticate())
            self.respond(200,result)
        except APIError as exc: self.respond(exc.status,{'error':str(exc)})
        except ValueError as exc: self.respond(400,{'error':str(exc) if not isinstance(exc,json.JSONDecodeError) else 'JSON no válido.'})
        except (TypeError,KeyError,AttributeError,RecursionError): self.respond(400,{'error':'Datos no válidos o demasiado anidados. Revisa los campos y la aplicación seleccionada.'})
        except (BrokenPipeError,ConnectionResetError): pass
        except Exception as exc:
            LOG.exception('Falló una acción'); self.respond(500,{'error':str(exc) if isinstance(exc,RuntimeError) else 'No se pudo completar la acción.'})

def discovery(deck):
    last={};delay=1
    while not deck.closed:
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
                sock.bind(('0.0.0.0',DISCOVERY_PORT));sock.settimeout(1)
                while not deck.closed:
                    try:data,address=sock.recvfrom(512)
                    except socket.timeout:continue
                    if data!=b'EDDY_DECK_DISCOVER_V1' or not private_ip(address[0]):continue
                    now=time.monotonic()
                    if now-last.get(address[0],-2)<1:continue
                    if len(last)>256:last.clear()
                    last[address[0]]=now
                    sock.sendto(json.dumps({'app':'EddyDeck','name':socket.gethostname(),'port':deck.port,'fingerprint':deck.fingerprint}).encode(),address)
                    delay=1
        except OSError:
            LOG.warning('Detección de red interrumpida; se reintentará automáticamente.')
            until=time.monotonic()+delay
            while not deck.closed and time.monotonic()<until:time.sleep(.25)
            delay=min(30,delay*2)

def start(deck,local_port=LOCAL_PORT,port=PORT,bind='0.0.0.0'):
    cert,key,deck.fingerprint=ensure_certificate(deck.data)
    local=Server(('127.0.0.1',local_port),deck,True)
    remote=None
    try:
        remote=Server((bind,port),deck,False)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert,key)
        # Perform TLS handshakes inside per-request threads so a half-open client
        # cannot block the accept loop for every paired device.
        remote.socket=context.wrap_socket(remote.socket,server_side=True,do_handshake_on_connect=False)
    except Exception:
        if remote is not None:remote.server_close()
        local.server_close(); raise
    deck.local_port=local.server_port; deck.port=remote.server_port
    deck.servers=[]
    try:
        for server in (local,remote):
            threading.Thread(target=server.serve_forever,daemon=True).start()
            deck.servers.append(server)
    except Exception:
        # shutdown() may only wait for a serve_forever loop that actually began.
        # Unstarted listeners are closed directly; the caller closes live ones.
        for server in (local,remote):
            if server not in deck.servers:server.server_close()
        raise
    # A fixture on another port must not reserve the production discovery port
    # or advertise an endpoint that Android deliberately refuses to pair.
    if deck.port==PORT:threading.Thread(target=discovery,args=(deck,),daemon=True).start()
    def rescan():
        next_scan=time.monotonic()+300;next_addresses=0
        while not deck.closed:
            time.sleep(1)
            if time.monotonic()>=next_addresses:
                deck.addresses=local_addresses();next_addresses=time.monotonic()+10
            if time.monotonic()>=next_scan:
                deck.start_scan(); next_scan=time.monotonic()+300
    threading.Thread(target=rescan,daemon=True).start()
    return deck
