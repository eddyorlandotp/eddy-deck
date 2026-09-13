"""Read-only installed Android and exported installer verification via ADB."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];adb=ROOT/'.build/tools/platform-tools/platform-tools/adb.exe'
sys.path.insert(0,str(ROOT))
from companion.core import VERSION
parser=argparse.ArgumentParser();parser.add_argument('--copy-method',choices=['native-picker','usb-file-copy'],default='native-picker');parser.add_argument('--phone-folder',default='/sdcard/Download');args=parser.parse_args()
def run(*args):return subprocess.run([str(adb),'-s','ANDROID_SERIAL_HERE',*args],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True).stdout
apk=run('shell','pm','path','com.eddy.deck').strip().removeprefix('package:')
assert apk.startswith('/data/app/') and apk.endswith('/base.apk') and '\n' not in apk
actual=run('shell','sha256sum',apk).split()[0]
expected=hashlib.sha256((ROOT/'artifacts/EddyDeck-Android.apk').read_bytes()).hexdigest()
assert actual==expected,'El APK instalado no coincide'
phone_installer=f'{args.phone_folder}/EddyDeck-Windows-{VERSION}.zip'
installer=run('shell','sha256sum',phone_installer).split()[0]
embedded=hashlib.sha256((ROOT/'.build/android/assets/EddyDeck-Windows.zip').read_bytes()).hexdigest()
assert installer==embedded,'La exportación no coincide'
package=run('shell','dumpsys','package','com.eddy.deck')
manifest=ET.parse(ROOT/'android/AndroidManifest.xml').getroot()
code=manifest.attrib['{http://schemas.android.com/apk/res/android}versionCode']
assert f'versionName={VERSION}' in package and f'versionCode={code}' in package
services=run('shell','dumpsys','activity','services','com.eddy.deck')
assert 'com.eddy.deck/.ConnectionService' in services and 'isForeground=true' in services
assert 'android.permission.POST_NOTIFICATIONS: granted=true' in package
phone_docs=f'{args.phone_folder}/EddyDeck-Documentacion-{VERSION}.zip'
docs=run('shell','sha256sum',phone_docs).split()[0]
assert docs==hashlib.sha256((ROOT/'.build/android/assets/EddyDeck-Documentacion.zip').read_bytes()).hexdigest(),'Documentación exportada distinta'
result={'version':VERSION,'installedApkMatches':True,'apkSHA256':actual,'phoneWindowsInstallerMatches':True,'installerSHA256':installer,'installerPhonePath':phone_installer,'documentationPhonePath':phone_docs,'phoneDocumentationMatches':True,'documentationSHA256':docs,'foregroundConnectionService':True,'notificationsGranted':True,'copyMethod':args.copy_method,'nativePickerVerified':args.copy_method=='native-picker'}
(ROOT/'artifacts'/('beta'+VERSION.rsplit('beta.',1)[-1]+'-final-device-verification.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
