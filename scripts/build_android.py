"""Build and sign the APK using only the official SDK and Java compiler."""
from pathlib import Path
import hashlib, json, os, secrets, shutil, subprocess, zipfile

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'.build'/'tools'
BUILD=ROOT/'.build'/'android'
ARTIFACTS=ROOT/'artifacts'
PRIVATE=ROOT/'private'

def only(root,pattern):
    matches=list(root.rglob(pattern))
    if len(matches)!=1: raise RuntimeError(f'Se esperaba un {pattern}, se encontraron {len(matches)}')
    return matches[0]

def run(args):
    result=subprocess.run([str(x) for x in args],cwd=ROOT,capture_output=True)
    if result.returncode:
        print(result.stdout.decode(errors='replace'))
        print(result.stderr.decode(errors='replace'))
        raise RuntimeError('Falló '+str(args[0]))
    return result.stdout.decode(errors='replace')

def main():
    BUILD.mkdir(parents=True,exist_ok=True);ARTIFACTS.mkdir(exist_ok=True);PRIVATE.mkdir(exist_ok=True)
    java=only(TOOLS/'jdk17','java.exe');javac=java.with_name('javac.exe');keytool=java.with_name('keytool.exe')
    android=only(TOOLS/'platforms-android-35','android.jar')
    aapt=only(TOOLS/'build-tools-35.0.0','aapt2.exe');align=aapt.with_name('zipalign.exe')
    d8=only(TOOLS/'build-tools-35.0.0','d8.jar');signer=only(TOOLS/'build-tools-35.0.0','apksigner.jar')
    for executable in (java,javac,keytool,aapt,align):
        if not executable.is_file():raise RuntimeError('Falta '+str(executable))
    for folder in ('gen','classes','dex'):
        target=(BUILD/folder).resolve()
        if target.parent!=BUILD.resolve():raise RuntimeError('Directorio de compilación no válido.')
        if target.exists():shutil.rmtree(target)
    for folder in ('gen','classes','dex','assets/ui'):(BUILD/folder).mkdir(parents=True,exist_ok=True)
    for name in ('index.html','styles.css','app.js','extended.js','beta2.js','pickers.js','manual.js','icon.svg'):shutil.copy2(ROOT/'ui'/name,BUILD/'assets/ui'/name)
    program=ARTIFACTS/'windows/EddyDeck'
    if not (program/'EddyDeck.exe').is_file():raise RuntimeError('Compila Windows primero para incluir su instalador en Android.')
    with zipfile.ZipFile(BUILD/'assets/EddyDeck-Windows.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in program.rglob('*'):
            if path.is_file():z.write(path,path.relative_to(program))
    with zipfile.ZipFile(BUILD/'assets/EddyDeck-Documentacion.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in (ROOT/'docs').glob('*'):
            if path.is_file():z.write(path,'docs/'+path.name)
        z.write(ROOT/'README.md','README.md')
        z.writestr('EMPIEZA-AQUI.txt','Abre docs/MANUAL-USUARIO.html para leer el manual completo. README.md resume el uso y mantenimiento. docs/VALIDACION.md distingue pruebas y pendientes.\n')
    print('Compilando recursos Android',flush=True)
    run([aapt,'compile','--dir',ROOT/'android/res','-o',BUILD/'res.zip'])
    run([aapt,'link','-o',BUILD/'unsigned.apk','-I',android,'--manifest',ROOT/'android/AndroidManifest.xml','--java',BUILD/'gen','--auto-add-overlay','-A',BUILD/'assets',BUILD/'res.zip'])
    sources=list((ROOT/'android/src').rglob('*.java'))+list((BUILD/'gen').rglob('*.java'))
    print('Compilando aplicación',flush=True)
    run([javac,'-encoding','UTF-8','--release','8','-classpath',android,'-d',BUILD/'classes',*sources])
    with zipfile.ZipFile(BUILD/'classes.jar','w',zipfile.ZIP_DEFLATED) as package:
        for path in (BUILD/'classes').rglob('*.class'):package.write(path,path.relative_to(BUILD/'classes').as_posix())
    run([java,'-cp',d8,'com.android.tools.r8.D8','--release','--lib',android,'--min-api','26','--output',BUILD/'dex',BUILD/'classes.jar'])
    with zipfile.ZipFile(BUILD/'unsigned.apk','a',zipfile.ZIP_DEFLATED) as package:
        for path in (BUILD/'dex').glob('*.dex'):package.write(path,path.name)
    run([align,'-f','-p','4',BUILD/'unsigned.apk',BUILD/'aligned.apk'])
    keystore=PRIVATE/'android-signing.p12';password=PRIVATE/'signing-password.txt'
    if not keystore.exists():
        if password.exists():raise RuntimeError('Hay contraseña sin llave. Revisa private antes de generar otra.')
        password.write_text(secrets.token_urlsafe(36),encoding='ascii')
        run([keytool,'-genkeypair','-keystore',keystore,'-alias','eddy-deck','-keyalg','RSA','-keysize','3072','-validity','36500','-dname','CN=Eddy Deck, OU=Personal, O=Eddy, C=MX','-storetype','PKCS12','-storepass:file',password,'-keypass:file',password])
    output=ARTIFACTS/'EddyDeck-Android.apk'
    run([java,'-jar',signer,'sign','--ks',keystore,'--ks-key-alias','eddy-deck','--ks-pass','file:'+str(password),'--out',output,BUILD/'aligned.apk'])
    verification=run([java,'-jar',signer,'verify','--verbose','--print-certs',output])
    (ARTIFACTS/'android-verification.txt').write_text(verification,encoding='utf-8')
    print('APK verificado: '+str(output),flush=True)
    print('SHA256 '+hashlib.sha256(output.read_bytes()).hexdigest(),flush=True)

if __name__=='__main__':main()
