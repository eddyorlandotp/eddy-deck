"""Exercise fresh/update installation in isolated folders on this Windows PC.
Uses a controlled shortcut adapter, never touches the user's shortcuts or
launches another receiver. This does not certify a second physical computer.
"""
import hashlib,json,os,sys,tempfile,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.installer import install_from
from companion.integrity import verify_release,CHECKER

def main():
    source=ROOT/'artifacts/windows/EddyDeck';signed=verify_release(source)
    checks=[]
    with tempfile.TemporaryDirectory(prefix='installer-compat-',dir=ROOT/'.build') as temporary:
        base=Path(temporary).resolve();assert base.parent==ROOT/'.build'
        local=base/'Local';roaming=base/'Roaming';desktop=base/'Desktop'
        class Shell:
            def SpecialFolders(self,name):
                assert name=='Desktop';return str(desktop)
            def CreateShortcut(self,name):
                assert Path(name).resolve().is_relative_to(base)
                class Shortcut:
                    def Save(self):Path(name).write_text(json.dumps(vars(self)),encoding='utf-8')
                return Shortcut()
        with patch.dict(os.environ,{'LOCALAPPDATA':str(local),'APPDATA':str(roaming)}),patch('win32com.client.Dispatch',return_value=Shell()):
            target=install_from(source);assert target==local/'Programs/EddyDeck';assert verify_release(target)==signed;checks.append('Fresh installation copies every signed file')
            data=local/'EddyDeck';assert not (data/'server.key').exists() and not (data/'devices.json').exists();checks.append('Fresh installation does not clone this PC identity or pairings')
            for file,expected in [(desktop/'Eddy Deck.lnk',target/'EddyDeck.exe'),(desktop/'Eddy Deck - Reparar.lnk',data/'Rescue'/CHECKER),(roaming/'Microsoft/Windows/Start Menu/Programs/Eddy Deck.lnk',target/'EddyDeck.exe')]:
                shortcut=json.loads(file.read_text(encoding='utf-8'));assert Path(shortcut['TargetPath'])==expected
            checks.append('Shortcut requests target only isolated program and rescue paths')
            cache=data/'recovery'/(signed['version']+'.zip')
            with zipfile.ZipFile(cache) as z:assert z.testzip() is None;assert z.read('EddyDeck.exe')==(source/'EddyDeck.exe').read_bytes()
            checks.append('Verified recovery cache included in fresh install')
            (data/'deck.json').write_text('{"fixture":"preserve"}');before=hashlib.sha256((data/'deck.json').read_bytes()).hexdigest()
            install_from(source);assert hashlib.sha256((data/'deck.json').read_bytes()).hexdigest()==before;assert len(list(target.parent.glob('EddyDeck-previous-*')))==1
            assert verify_release(target)==signed;checks.append('Update preserves data and keeps previous directory')
    report={'checks':checks,'count':len(checks),'passed':True,'system':'Same Windows PC, isolated LocalAppData/AppData/Desktop folders','shortcutAdapter':'controlled fixture; no user COM shortcuts','receiversLaunched':0,'userShortcutsModified':False,'secondPhysicalPCVerified':False}
    (ROOT/'artifacts'/('beta'+signed['version'].rsplit('beta.',1)[-1]+'-fresh-install-tests.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
