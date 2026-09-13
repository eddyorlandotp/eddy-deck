"""Verify source, portable release and APK Windows payload agree byte-for-byte."""
from pathlib import Path
import hashlib,io,json,os,re,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.core import VERSION
from companion.integrity import verify_release
OUT=ROOT/'artifacts'
def sha(value):return hashlib.sha256(value).hexdigest()
results={'version':VERSION}
assert json.loads(re.search(r'EDDY_CLIENT_VERSION=("[^"]+")',(ROOT/'ui/manual.js').read_text(encoding='utf-8')).group(1))==VERSION
import xml.etree.ElementTree as ET
assert ET.parse(ROOT/'android/AndroidManifest.xml').getroot().attrib['{http://schemas.android.com/apk/res/android}versionName']==VERSION
results['declaredClientAndAndroidVersionMatch']=True
signed=verify_release(OUT/'windows/EddyDeck');results['signedWindowsFilesVerified']=len(signed['files']);assert signed['version']==VERSION
with zipfile.ZipFile(OUT/'EddyDeck-Codigo.zip') as z:
    assert z.testzip() is None
    for name in z.namelist():
        rel=Path(name).relative_to('EddyDeck-Codigo')
        assert not any(part in ('private','.build','artifacts','__pycache__') for part in rel.parts)
        assert rel.suffix.lower() not in ('.pem','.p12','.key','.sqlite3'),name
        assert z.read(name)==(ROOT/rel).read_bytes(),name
    results['sourceFilesVerified']=len(z.namelist())
with zipfile.ZipFile(OUT/'EddyDeck-Android.apk') as apk:
    assert apk.testzip() is None
    embedded=apk.read('assets/EddyDeck-Windows.zip')
    assert embedded==(OUT/f'EddyDeck-Windows-{VERSION}.zip').read_bytes()
    for name in ('index.html','app.js','extended.js','beta2.js','pickers.js','manual.js','styles.css','icon.svg'):
        assert apk.read('assets/ui/'+name)==(ROOT/'ui'/name).read_bytes(),name
        assert (OUT/'windows/EddyDeck/_internal/ui'/name).read_bytes()==(ROOT/'ui'/name).read_bytes(),'Windows UI: '+name
    with zipfile.ZipFile(io.BytesIO(apk.read('assets/EddyDeck-Documentacion.zip'))) as docs:
        for name in docs.namelist():
            if name=='EMPIEZA-AQUI.txt':continue
            assert docs.read(name)==(ROOT/name).read_bytes(),name
        for link in re.findall(r'\]\((docs/[^)]+)\)',docs.read('README.md').decode()):assert link in docs.namelist(),link
        results['documentationFilesVerified']=len(docs.namelist())
    results['embeddedWindowsSHA256']=sha(embedded)
    with zipfile.ZipFile(io.BytesIO(embedded)) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.endswith('/'):continue
            rel=Path(name)
            assert z.read(name)==(OUT/'windows/EddyDeck'/rel).read_bytes(),name
        results['embeddedWindowsFilesVerified']=len(z.namelist())
with zipfile.ZipFile(OUT/f'EddyDeck-{VERSION}.zip') as z:
    assert z.testzip() is None
    assert z.read('EddyDeck/Android/EddyDeck-Android.apk')==(OUT/'EddyDeck-Android.apk').read_bytes()
    assert z.read('EddyDeck/Windows/EddyDeck.exe')==(OUT/'windows/EddyDeck/EddyDeck.exe').read_bytes()
    for link in re.findall(r'\]\((Windows/docs/[^)]+)\)',z.read('EddyDeck/EMPIEZA-AQUI.md').decode()):assert 'EddyDeck/'+link in z.namelist(),link
    results['releaseVerified']=True
installed=Path(os.environ['LOCALAPPDATA'])/'Programs/EddyDeck/EddyDeck.exe'
assert installed.read_bytes()==(OUT/'windows/EddyDeck/EddyDeck.exe').read_bytes()
installed_manifest=verify_release(installed.parent);assert installed_manifest==signed;results['installedIntegrityVerified']=True
if VERSION in ('2.2.4-beta.6','2.2.5-beta.7','2.2.6-beta.8','2.2.7-beta.9'):
    helper=installed.parent/'EddyDeck-Tidal.exe'
    assert helper.read_bytes()==(OUT/'windows/EddyDeck/EddyDeck-Tidal.exe').read_bytes()
    assert sha(helper.read_bytes())==signed['files']['EddyDeck-Tidal.exe']['sha256']
    results['tidalHelperSignedAndInstalled']=True
if VERSION in ('2.2.5-beta.7','2.2.6-beta.8','2.2.7-beta.9'):
    helper=installed.parent/'EddyDeck-Media.exe'
    assert helper.read_bytes()==(OUT/'windows/EddyDeck/EddyDeck-Media.exe').read_bytes()
    assert sha(helper.read_bytes())==signed['files']['EddyDeck-Media.exe']['sha256']
    results['mediaHelperSignedAndInstalled']=True
results['installedWindowsSHA256']=sha(installed.read_bytes())
results['apkSHA256']=sha((OUT/'EddyDeck-Android.apk').read_bytes())
from companion.storage import data_root
data=data_root()
before=json.loads((ROOT/'.build/final-update-before.json').read_text(encoding='utf-8-sig'))
assert all(sha((data/name).read_bytes()).upper()==expected for name,expected in before['files'].items())
results['profileAndPairingPreserved']=True
runtime=json.loads((data/'runtime.json').read_text());supervisor=json.loads((data/'supervisor.json').read_text())
assert supervisor['workerPid']==runtime['pid']
assert any(c['at']>before['at'] for c in runtime['recentClients'])
results['phoneReconnectedAfterUpdate']=True
import pythoncom,win32com.client
from companion.integrity import CHECKER
pythoncom.CoInitialize()
try:
    shell=win32com.client.Dispatch('WScript.Shell')
    desktop=Path(shell.SpecialFolders('Desktop'))
    programs=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs'
    expected_links=[(desktop/'Eddy Deck.lnk',installed,''),(programs/'Eddy Deck.lnk',installed,''),(desktop/'Eddy Deck - Reparar.lnk',data/'Rescue'/CHECKER,'--repair'),(programs/'Startup/Eddy Deck.lnk',installed,'--tray')]
    for path,target,arguments in expected_links:
        assert path.is_file(),path.name
        link=shell.CreateShortcut(str(path))
        assert Path(link.TargetPath)==target and link.Arguments==arguments,path.name
        assert target.is_file(),target.name
    results['realWindowsShortcutsVerified']=len(expected_links)
    results['startupEnabledTargetVerified']=True
finally:
    link=None;shell=None;pythoncom.CoUninitialize()
(OUT/('beta'+VERSION.rsplit('beta.',1)[-1]+'-release-verification.json')).write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
