"""Per-user installation. Existing user data is stored elsewhere and preserved."""
import os,shutil,subprocess,sys,uuid,hashlib
from pathlib import Path

def read_profile_backup(file):
    from companion.core import validate_profile
    import json
    file=Path(file)
    if not file.is_file() or file.stat().st_size>4*1024*1024:raise ValueError('La copia del panel no existe o es demasiado grande.')
    return validate_profile(json.loads(file.read_text(encoding='utf-8-sig')))

def restore_profile_backup(file,data):
    """Explicit local recovery, including an unreadable deck.json. No trust keys."""
    from companion.core import atomic_json
    profile=read_profile_backup(file);data=Path(data);data.mkdir(parents=True,exist_ok=True)
    current=data/'deck.json'
    if current.exists():shutil.copy2(current,data/('deck-before-recovery-'+uuid.uuid4().hex+'.json'))
    atomic_json(current,profile)
    return {'cards':len(profile['cards']),'routines':len(profile['scenes'])}

def install_from(source):
    source=Path(source).resolve()
    from companion.integrity import verify_release,cache_release,CHECKER
    verify_release(source)
    if not (source/'EddyDeck.exe').is_file() or not (source/'_internal').is_dir():
        raise RuntimeError('Conserva EddyDeck.exe junto a su carpeta _internal antes de instalar.')
    from companion.storage import prepare_data
    data=prepare_data()
    target=Path(os.environ['LOCALAPPDATA'])/'Programs'/'EddyDeck'
    if source!=target.resolve():
        if target.exists():
            if not (target/'EddyDeck.exe').is_file():
                raise RuntimeError('La carpeta de destino ya existe y no parece ser Eddy Deck. Revisa su contenido.')
            # Do not replace a running binary or silently mix release versions.
            import ctypes
            from ctypes import wintypes
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
            kernel.CreateFileW.restype=wintypes.HANDLE
            kernel.CloseHandle.argtypes=[wintypes.HANDLE]
            handle=kernel.CreateFileW(str(target/'EddyDeck.exe'),0x40000000,0,None,3,0,None)
            if handle==ctypes.c_void_p(-1).value:
                raise RuntimeError('Sal de Eddy Deck desde su icono junto al reloj antes de actualizar.')
            kernel.CloseHandle(handle)
        # Assemble and verify the new version before switching directories. Old
        # binaries remain available as a rollback copy; user data lives elsewhere.
        target.parent.mkdir(parents=True,exist_ok=True)
        staging=target.with_name('EddyDeck-update-'+uuid.uuid4().hex)
        previous=target.with_name('EddyDeck-previous-'+uuid.uuid4().hex)
        intended=Path(os.environ['LOCALAPPDATA']).resolve()/'Programs'
        if any(p.resolve().parent!=intended for p in (target,staging,previous)):
            raise RuntimeError('El destino de instalación no es el esperado.')
        shutil.copytree(source,staging)
        for file in source.rglob('*'):
            if file.is_file():
                other=staging/file.relative_to(source)
                if hashlib.sha256(file.read_bytes()).digest()!=hashlib.sha256(other.read_bytes()).digest():
                    raise RuntimeError('No se pudo verificar la copia. La instalación anterior permanece disponible.')
        cache_release(source,data)
        swapped=False
        try:
            if target.exists():os.replace(target,previous);swapped=True
            os.replace(staging,target)
        except OSError:
            if swapped and not target.exists():os.replace(previous,target)
            raise RuntimeError('Windows no pudo sustituir la aplicación. Cierra Eddy Deck antes de actualizar.') from None
    from companion import resilience
    # Rollback copies keep their files, but their executable can no longer be
    # started by a shortcut or a search. The verified ZIP in recovery restores.
    resilience.disable_stale_copies(target.parent)
    # Fresh shortcuts without link tracking: they cannot drift to a
    # previous copy if the executable is ever missing.
    description='Controla tu PC desde Android, sin IA ni suscripciones.'
    resilience.write_shortcut(resilience.desktop_link(),target/'EddyDeck.exe','',description)
    resilience.write_shortcut(resilience.menu_link(),target/'EddyDeck.exe','',description)
    resilience.write_shortcut(resilience.desktop_link().with_name('Eddy Deck - Reparar.lnk'),data/'Rescue'/CHECKER,'--repair','Comprueba y restaura los archivos de Eddy Deck conservando tus datos.')
    if resilience.startup_wanted(data):
        resilience.write_shortcut(resilience.startup_link(),target/'EddyDeck.exe','--tray','Inicia Eddy Deck junto al reloj.')
    return target

def main():
    from tkinter import messagebox
    try:
        target=install_from(Path(sys.executable).parent)
        subprocess.Popen([str(target/'EddyDeck.exe')],cwd=target,creationflags=subprocess.CREATE_NO_WINDOW)
        messagebox.showinfo('Eddy Deck instalado','Se creó el acceso directo Eddy Deck en el escritorio. Abre la app Android y vincula tu PC por USB o Wi-Fi.')
    except Exception as exc:messagebox.showerror('No se pudo instalar',str(exc))
