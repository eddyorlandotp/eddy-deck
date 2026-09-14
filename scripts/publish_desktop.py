"""Publish a versioned, verified personal handoff on the actual Windows desktop."""
from pathlib import Path
import hashlib,json,shutil,sys,os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from companion.core import VERSION
def main():
    import win32com.client
    desktop=Path(win32com.client.Dispatch('WScript.Shell').SpecialFolders('Desktop'))
    base=desktop/'Eddy Deck';dest=base/'Versiones'/VERSION;dest.mkdir(parents=True,exist_ok=True)
    files=[(ROOT/'README.md',base/'GUIA-DE-USO.md'),(ROOT/'docs/VALIDACION.md',base/'PRUEBAS-Y-LIMITES.md')]
    files += [(ROOT/'docs/MANUAL-USUARIO.html',base/'MANUAL-USUARIO.html'),(ROOT/'docs/MANUAL-USUARIO.md',base/'MANUAL-USUARIO.md')]
    files += [(p,dest/p.name) for p in (ROOT/'artifacts').glob('EddyDeck-*.zip') if p.name in ('EddyDeck-Codigo.zip',f'EddyDeck-{VERSION}.zip',f'EddyDeck-Windows-{VERSION}.zip',f'EddyDeck-Pruebas-{VERSION}.zip')]
    files += [(ROOT/'artifacts/EddyDeck-Android.apk',dest/'EddyDeck-Android.apk'),(ROOT/'artifacts/SHA256SUMS.txt',dest/'SHA256SUMS.txt')]
    reports=[p for p in (ROOT/'artifacts').glob('*') if p.suffix in ('.json','.jsonl','.txt','.md','.csv') and ('test' in p.name or 'verification' in p.name or 'catalog-beta' in p.name or p.name.startswith('beta'))]
    files += [(p,base/'Informes'/p.name) for p in reports]
    files += [(p,dest/'Informes'/p.name) for p in reports]
    files += [(p,base/'docs'/p.name) for p in (ROOT/'docs').glob('*') if p.is_file() and p.suffix in ('.md','.html')]
    files += [(p,dest/'docs'/p.name) for p in (ROOT/'docs').glob('*') if p.is_file() and p.suffix in ('.md','.html')]
    # Preflight before even updating the top-level guide: a delivered version
    # cannot silently acquire different APKs or archives on a later run.
    for source,target in files:
        if target.parent==dest and target.suffix in ('.zip','.apk') and target.exists():
            if hashlib.sha256(source.read_bytes()).digest()!=hashlib.sha256(target.read_bytes()).digest():
                raise RuntimeError('Esta versión ya se entregó con otro paquete. Incrementa la versión antes de publicar: '+target.name)
    for source,target in files:
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        if hashlib.sha256(source.read_bytes()).digest()!=hashlib.sha256(target.read_bytes()).digest():raise RuntimeError('Copia incompleta: '+target.name)
    (base/'EMPIEZA-AQUI.txt').write_text(f"""Eddy Deck {VERSION}

Empieza con MANUAL-USUARIO.html: todas las funciones, rutinas y solución de problemas.
GUIA-DE-USO.md: resumen y mantenimiento del código.
PRUEBAS-Y-LIMITES.md: qué se probó y qué sigue pendiente.
docs: arquitectura, seguridad, compatibilidad e historia por aplicación.
Informes: evidencias de las pruebas.
Versiones/{VERSION}: código, APK y paquetes de Windows/Android.

Actualizaciones: https://github.com/eddyorlandotp/eddy-deck/releases
Respaldo privado: {os.environ.get("EDDY_DECK_BACKUP_URL","https://drive.google.com/drive/my-drive")}
Necesitas tu cuenta para descargarlo. El comprobador verifica después la copia.

El código es independiente de Codex. Las claves para firmar Android y Windows
se conservan en private dentro del proyecto original; no están en los paquetes
ni informes compartibles. El manual explica cómo conservarlas privadamente.
Proyecto original: {ROOT}
""",encoding='utf-8')
    (dest/'GUIA-DE-USO.md').write_bytes((ROOT/'README.md').read_bytes());(dest/'PRUEBAS-Y-LIMITES.md').write_bytes((ROOT/'docs/VALIDACION.md').read_bytes())
    print(json.dumps({'folder':str(base),'version':VERSION,'copiedAndVerified':len(files)},ensure_ascii=False))
if __name__=='__main__':main()
