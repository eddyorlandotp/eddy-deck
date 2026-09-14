"""Release integrity and a private, verified local repair package."""
import base64,hashlib,json,os,subprocess,sys,uuid,zipfile
from pathlib import Path,PurePosixPath
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding,rsa

MANIFEST='release-manifest.json';SIGNATURE='release-manifest.sig'
CHECKER='EddyDeck-Compatibilidad.exe'
UPDATE_URL='https://github.com/eddyorlandotp/eddy-deck/releases'

def public_key():
    from companion.release_public import MODULUS,EXPONENT
    return rsa.RSAPublicNumbers(EXPONENT,int.from_bytes(base64.b64decode(MODULUS),'big')).public_key()
def manifest_bytes(raw,signature,key=None):
    if len(raw)>2000000 or len(signature)>2048:raise ValueError('El manifiesto tiene un tamaño inválido.')
    try:(key or public_key()).verify(base64.b64decode(signature,validate=True),raw,padding.PKCS1v15(),hashes.SHA256())
    except Exception:raise ValueError('La firma del paquete no coincide con Eddy Deck. Descarga otra copia del respaldo.') from None
    m=json.loads(raw)
    if m.get('schema')!=1 or m.get('architecture')!='x64' or not isinstance(m.get('files'),dict) or not 1<=len(m['files'])<=5000:raise ValueError('Manifiesto incompatible.')
    for name,info in m['files'].items():
        p=PurePosixPath(name)
        if not name or p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name or any(not x or x.endswith((' ','.')) for x in name.split('/')):raise ValueError('Ruta no permitida dentro del paquete.')
        if not isinstance(info,dict) or type(info.get('size')) is not int or not 0<=info['size']<=500000000 or len(info.get('sha256',''))!=64:raise ValueError('Archivo no válido en el manifiesto.')
    return m
def read_manifest(folder,key=None):
    folder=Path(folder)
    return manifest_bytes((folder/MANIFEST).read_bytes(),(folder/SIGNATURE).read_bytes(),key)
def verify_release(folder,key=None):
    folder=Path(folder).resolve();m=read_manifest(folder,key)
    for name,info in m['files'].items():
        file=folder/Path(name)
        if not file.resolve().is_relative_to(folder) or file.is_symlink():raise ValueError('El paquete contiene un enlace fuera de su carpeta.')
        if not file.is_file() or file.stat().st_size!=info['size'] or hashlib.sha256(file.read_bytes()).hexdigest()!=info['sha256']:raise ValueError('Archivo incompleto o modificado: '+name)
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual-set(m['files'])-{MANIFEST,SIGNATURE}:raise ValueError('Hay archivos ajenos mezclados con el programa. Extrae la copia en una carpeta nueva.')
    return m
def cache_release(source,data):
    source=Path(source);data=Path(data);m=verify_release(source)
    folder=data/'recovery';folder.mkdir(parents=True,exist_ok=True)
    name=m['version']
    if not name or any(c not in '0123456789abcdefghijklmnopqrstuvwxyz.-' for c in name):raise ValueError('Versión inválida.')
    dest=folder/(name+'.zip');temp=folder/(uuid.uuid4().hex+'.tmp')
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
        for file in [*m['files'],MANIFEST,SIGNATURE]:z.write(source/file,file)
    os.replace(temp,dest)
    rescue=data/'Rescue';rescue.mkdir(exist_ok=True)
    import shutil
    installed=rescue/CHECKER
    if not installed.exists() or hashlib.sha256(installed.read_bytes()).hexdigest()!=m['files'][CHECKER]['sha256']:
        temp=rescue/(uuid.uuid4().hex+'.tmp');shutil.copy2(source/CHECKER,temp);os.replace(temp,installed)
    return dest
def repair_status(data):
    from companion.core import VERSION
    data=Path(data)
    return {'available':(data/'recovery'/(VERSION+'.zip')).is_file() and (data/'Rescue'/CHECKER).is_file(),'backupUrl':UPDATE_URL,'version':VERSION}
def start_repair(data):
    from companion.core import VERSION
    data=Path(data);cache=data/'recovery'/(VERSION+'.zip');checker=data/'Rescue'/CHECKER
    with zipfile.ZipFile(cache) as z:m=manifest_bytes(z.read(MANIFEST),z.read(SIGNATURE))
    if m['version']!=VERSION or hashlib.sha256(checker.read_bytes()).hexdigest()!=m['files'][CHECKER]['sha256']:raise ValueError('La herramienta de reparación no coincide. Usa la copia del celular o de GitHub.')
    subprocess.Popen([str(checker),'--repair-now'],creationflags=0x08000000)
    return {'status':'restarting','message':'Comprobando y restaurando los archivos de Eddy Deck. La conexión volverá al terminar.'}
