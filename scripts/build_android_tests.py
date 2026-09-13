from pathlib import Path
import zipfile
from build_android import ROOT,TOOLS,BUILD,PRIVATE,only,run

def main():
    out=ROOT/'.build/android-tests';out.mkdir(exist_ok=True)
    java=only(TOOLS/'jdk17','java.exe');android=only(TOOLS/'platforms-android-35','android.jar');aapt=only(TOOLS/'build-tools-35.0.0','aapt2.exe')
    d8=only(TOOLS/'build-tools-35.0.0','d8.jar');signer=only(TOOLS/'build-tools-35.0.0','apksigner.jar')
    for f in ('classes','dex'):(out/f).mkdir(exist_ok=True)
    run([aapt,'link','-o',out/'unsigned.apk','-I',android,'--manifest',ROOT/'tests/android/AndroidManifest.xml'])
    run([java.with_name('javac.exe'),'-encoding','UTF-8','--release','8','-classpath',str(android)+';'+str(BUILD/'classes'),'-d',out/'classes',*sorted((ROOT/'tests/android').glob('*.java'))])
    with zipfile.ZipFile(out/'classes.jar','w',zipfile.ZIP_DEFLATED) as z:
        for p in (out/'classes').rglob('*.class'):z.write(p,p.relative_to(out/'classes'))
    run([java,'-cp',d8,'com.android.tools.r8.D8','--release','--lib',android,'--classpath',BUILD/'classes.jar','--min-api','26','--output',out/'dex',out/'classes.jar'])
    with zipfile.ZipFile(out/'unsigned.apk','a',zipfile.ZIP_DEFLATED) as z:
        for p in (out/'dex').glob('*.dex'):z.write(p,p.name)
    run([aapt.with_name('zipalign.exe'),'-f','4',out/'unsigned.apk',out/'aligned.apk'])
    run([java,'-jar',signer,'sign','--ks',PRIVATE/'android-signing.p12','--ks-key-alias','eddy-deck','--ks-pass','file:'+str(PRIVATE/'signing-password.txt'),'--out',out/'tests.apk',out/'aligned.apk'])
    print('APK de pruebas firmado; usa preferencias aisladas.')
if __name__=='__main__':main()
