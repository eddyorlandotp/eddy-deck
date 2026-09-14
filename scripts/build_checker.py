from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.sign_release import prepare_key
from companion.core import VERSION
def build(output):
    _,mod,_=prepare_key();source=(ROOT/'installer/Compatibility.cs').read_text(encoding='utf-8').replace('@@VERSION@@',VERSION).replace('@@MODULUS@@',mod)
    dest=ROOT/'.build/Compatibility.cs';dest.write_text(source,encoding='utf-8')
    csc=Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe')
    subprocess.run([str(csc),'/nologo','/target:winexe','/platform:anycpu','/optimize+','/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll','/r:System.IO.Compression.dll','/r:System.IO.Compression.FileSystem.dll','/out:'+str(output),str(dest),str(ROOT/'installer/GitHubUpdate.cs')],check=True,cwd=ROOT)
    print('Comprobador independiente compilado.')
if __name__=='__main__':build(ROOT/'.build/EddyDeck-Compatibilidad.exe')
