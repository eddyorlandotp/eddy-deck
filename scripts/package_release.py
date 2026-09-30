"""Create source and portable release archives, excluding personal state and keys."""
from pathlib import Path
import hashlib,json,shutil,zipfile,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from companion.core import VERSION
OUT=ROOT/'artifacts'

def main():
    sources=[]
    for name in ('README.md','LICENSE','requirements.txt','.gitignore','run.py','AGENTS.md'):sources.append(ROOT/name)
    for folder in ('companion','ui','android','docs','tests','installer'):
        sources.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.md','.js','.cjs','.css','.html','.svg','.ico','.java','.xml','.cs'))
    sources.extend(ROOT/'scripts'/name for name in ('setup_toolchain.py','build_android.py','build_windows.py','package_release.py','dev_start.py','install_local.py','test_server.py','build_android_tests.py'))
    sources.append(ROOT/'scripts/publish_desktop.py')
    sources.append(ROOT/'scripts/build_tidal.py')
    sources.append(ROOT/'scripts/build_media.py')
    sources.append(ROOT/'scripts/build_audio.py')
    sources.append(ROOT/'scripts/build_update_manifest.py')
    sources.extend(ROOT/'scripts'/name for name in ('sign_release.py','build_checker.py','build_manual.py','package_evidence.py','verify_report_privacy.py','capture_build_environment.py'))
    source_zip=OUT/'EddyDeck-Codigo.zip'
    with zipfile.ZipFile(source_zip,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(set(sources)):z.write(path,Path('EddyDeck-Codigo')/path.relative_to(ROOT))
    program=OUT/'windows/EddyDeck'
    from companion.integrity import verify_release
    verify_release(program)
    for path in (ROOT/'docs').glob('*'):
        if not path.is_file() or path.suffix not in ('.md','.html'):continue
        if path.read_bytes()!=(program/'docs'/path.name).read_bytes():raise RuntimeError('La documentación cambió. Compila Windows y Android antes de empaquetar.')
    if (ROOT/'README.md').read_bytes()!=(program/'LEEME.md').read_bytes():raise RuntimeError('La guía cambió. Compila Windows y Android antes de empaquetar.')
    windows_zip=OUT/f'EddyDeck-Windows-{VERSION}.zip'
    shutil.copy2(ROOT/'.build/android/assets/EddyDeck-Windows.zip',windows_zip)
    release=OUT/f'EddyDeck-{VERSION}.zip'
    with zipfile.ZipFile(release,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in program.rglob('*'):
            if path.is_file():z.write(path,Path('EddyDeck/Windows')/path.relative_to(program))
        z.write(OUT/'EddyDeck-Android.apk','EddyDeck/Android/EddyDeck-Android.apk')
        z.write(source_zip,'EddyDeck/EddyDeck-Codigo.zip')
        z.writestr('EddyDeck/EMPIEZA-AQUI.md',(ROOT/'README.md').read_text(encoding='utf-8').replace('(docs/','(Windows/docs/'))
        z.writestr('EddyDeck/LLAVE-DE-ACTUALIZACION.txt','Las llaves para futuras actualizaciones están en la carpeta private del proyecto original. Respalda android-signing.p12, signing-password.txt y release-signing.pem de forma privada. No están en este paquete para compartir. No necesitas esa llave para usar la app ni para agregar botones.\n')
    files=[OUT/'EddyDeck-Android.apk',source_zip,windows_zip,release,program/'EddyDeck.exe']
    sums='\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(OUT).as_posix() for p in files)+'\n'
    (OUT/'SHA256SUMS.txt').write_text(sums,encoding='ascii')
    print(json.dumps([{'file':p.name,'bytes':p.stat().st_size} for p in files],indent=2))

if __name__=='__main__':main()
