"""Build against Windows metadata already present on the Windows 11 build host."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
def build(output):
    framework=Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319');gac=Path('C:/Windows/Microsoft.NET/assembly/GAC_MSIL')
    refs=[*sorted((gac/'System.Runtime').rglob('System.Runtime.dll')),*sorted((gac/'System.Runtime.InteropServices.WindowsRuntime').rglob('*.dll')),*[Path('C:/Windows/System32/WinMetadata')/name for name in ('Windows.Foundation.winmd','Windows.Media.winmd')]]
    if len(refs)!=4 or not all(p.is_file() for p in refs):raise RuntimeError('Faltan los metadatos de Windows para compilar el controlador multimedia.')
    subprocess.run([str(framework/'csc.exe'),'/nologo','/r:System.Web.Extensions.dll',*[('/r:'+str(p)) for p in refs],'/out:'+str(output),str(ROOT/'companion/MediaSessions.cs')],check=True)
if __name__=='__main__':build(ROOT/'.build/EddyDeck-Media.exe')
