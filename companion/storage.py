"""Stable per-user data, outside inherited MSIX AppData redirection.

The same directory must be used from Explorer, Startup and a packaged launcher.
Legacy directories are copied transactionally and are never deleted or merged.
"""
from pathlib import Path
import contextlib,hashlib,json,os,shutil,socket,sqlite3,uuid

TRANSIENT={'runtime.json','supervisor.json','restart-request.json','receiver.lock','test-runtime.json'}

def startup_message(error):
    if isinstance(error,RuntimeError):return str(error)
    return ('No se pudo preparar Eddy Deck. Conserva la carpeta .eddydeck y las copias anteriores. '
            'Comprueba permisos, espacio disponible y que no haya otra actualización en curso. '
            'Si los archivos están dañados, restaura tu respaldo antes de volver a vincular. '
            'Detalle para soporte: '+type(error).__name__+'.')

def data_root():
    return Path(os.environ.get('USERPROFILE',str(Path.home())))/'.eddydeck'

def require_legacy_stopped():
    for port in (47988,47989,47990):
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.3):pass
        except OSError:continue
        raise RuntimeError('Cierra Eddy Deck desde Salir junto al reloj antes de migrar o actualizar. Hay un receptor activo; no se copiaron sus datos mientras se usan.')

def physical_path(path):
    """Inspect an existing Windows handle, rather than trusting its logical name."""
    path=Path(path)
    if os.name!='nt':return path.resolve()
    import ctypes as C
    from ctypes import wintypes as W
    k=C.WinDLL('kernel32',use_last_error=True)
    k.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,C.c_void_p,W.DWORD,W.DWORD,W.HANDLE];k.CreateFileW.restype=W.HANDLE
    k.GetFinalPathNameByHandleW.argtypes=[W.HANDLE,W.LPWSTR,W.DWORD,W.DWORD];k.GetFinalPathNameByHandleW.restype=W.DWORD
    k.CloseHandle.argtypes=[W.HANDLE]
    h=k.CreateFileW(str(path),0x80000000,7,None,3,0x02000000,None)
    if h==C.c_void_p(-1).value:raise C.WinError(C.get_last_error())
    try:
        b=C.create_unicode_buffer(32768)
        count=k.GetFinalPathNameByHandleW(h,b,len(b),0)
        if not count or count>=len(b):raise OSError('No se pudo comprobar la ubicación física de los datos.')
        return Path(b.value.removeprefix('\\\\?\\'))
    finally:k.CloseHandle(h)

def identity(source):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes,serialization
    source=Path(source);cert=source/'server.crt';key=source/'server.key'
    if not cert.is_file() or not key.is_file():raise RuntimeError('La configuración anterior tiene una identidad incompleta; conserva sus archivos antes de recuperar.')
    c=x509.load_pem_x509_certificate(cert.read_bytes());k=serialization.load_pem_private_key(key.read_bytes(),password=None)
    if c.public_key().public_numbers()!=k.public_key().public_numbers():raise RuntimeError('La llave y el certificado anteriores no corresponden.')
    for name,kind in [('deck.json',dict),('devices.json',list)]:
        if not isinstance(json.loads((source/name).read_text(encoding='utf-8')),kind):raise RuntimeError('La configuración anterior no es válida: '+name)
    return c.fingerprint(hashes.SHA256()).hex()

def legacy_candidates(local=None):
    local=Path(local or os.environ['LOCALAPPDATA']);paths=[local/'EddyDeck']
    # Only the Eddy Deck subdirectory is inspected, never another app's state.
    packages=local/'Packages'
    if packages.is_dir():paths.extend(p/'LocalCache/Local/EddyDeck' for p in packages.iterdir() if p.is_dir())
    found={}
    for p in paths:
        if (p/'deck.json').exists() or (p/'devices.json').exists() or (p/'server.crt').exists():
            physical=physical_path(p);found[os.path.normcase(str(physical))]=physical
    return list(found.values())

def _copy_legacy(source,stage):
    for path in source.rglob('*'):
        relative=path.relative_to(source)
        if path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()):raise RuntimeError('La configuración contiene un enlace; no se migró automáticamente.')
        if path.name in TRANSIENT or path.name.endswith(('.tmp','-wal','-shm')):continue
        target=stage/relative
        if path.is_dir():target.mkdir(parents=True,exist_ok=True);continue
        target.parent.mkdir(parents=True,exist_ok=True)
        if path.name=='operations.sqlite3':
            with contextlib.closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as old,contextlib.closing(sqlite3.connect(target)) as new:old.backup(new)
        else:
            shutil.copy2(path,target)
            if hashlib.sha256(path.read_bytes()).digest()!=hashlib.sha256(target.read_bytes()).digest():raise RuntimeError('La copia no pudo verificarse: '+path.name)

@contextlib.contextmanager
def migration_lock(parent):
    parent.mkdir(parents=True,exist_ok=True)
    with (parent/'.eddydeck-migration.lock').open('a+b') as f:
        if not f.tell():f.write(b'0');f.flush()
        f.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(f.fileno(),msvcrt.LK_LOCK,1)
        try:yield
        finally:
            if os.name=='nt':f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)

def prepare_data(source=None,expected_identity=None,target=None):
    target=Path(target) if target is not None else data_root()
    with migration_lock(target.parent):
        if target.exists():
            if not target.is_dir() or physical_path(target)!=target.resolve():raise RuntimeError('La carpeta de datos está redirigida. No se creó otra identidad.')
            if expected_identity and identity(target)!=expected_identity:raise RuntimeError('Ya existe otra identidad en el destino. No se sobrescribió.')
            return target
        candidates=[physical_path(source)] if source is not None else legacy_candidates()
        if len(candidates)>1:
            raise RuntimeError('Hay varias configuraciones anteriores de Eddy Deck. Se conservaron todas. La migración debe seleccionar la identidad vinculada a tu celular; no vuelvas a vincular para ocultar el conflicto.')
        if candidates and source is None:require_legacy_stopped()
        stage=target.with_name('.eddydeck-migration-'+uuid.uuid4().hex)
        try:
            stage.mkdir()
            if candidates:
                old=candidates[0];pin=identity(old)
                if expected_identity and pin!=expected_identity:raise RuntimeError('La copia no corresponde a la identidad elegida.')
                _copy_legacy(old,stage)
                if identity(stage)!=pin:raise RuntimeError('La identidad cambió al copiar; el origen permanece intacto.')
                if source is None:require_legacy_stopped()
                (stage/'storage-migration.json').write_text(json.dumps({'version':1,'source':str(old),'identityPreserved':True,'originalRetained':True},indent=2),encoding='utf-8')
            elif expected_identity:raise RuntimeError('No se encontró la configuración vinculada.')
            if physical_path(stage)!=stage.resolve():raise RuntimeError('Windows redirigió la nueva carpeta de datos.')
            os.replace(stage,target)
            return target
        finally:
            # Delete only this transaction's verified, same-parent staging path.
            if stage.exists() and stage.parent.resolve()==target.parent.resolve() and stage.name.startswith('.eddydeck-migration-'):
                shutil.rmtree(stage)
