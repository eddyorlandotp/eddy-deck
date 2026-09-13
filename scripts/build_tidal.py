from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
def build(output):
    framework=Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319')
    subprocess.run([str(framework/'csc.exe'),'/nologo','/target:exe','/platform:anycpu','/optimize+','/r:System.Web.Extensions.dll',*[f'/r:{framework/"WPF"/name}' for name in ('UIAutomationClient.dll','UIAutomationTypes.dll','WindowsBase.dll')],'/out:'+str(output),str(ROOT/'companion/TidalMedia.cs')],check=True,cwd=ROOT)
if __name__=='__main__':build(ROOT/'.build/EddyDeck-Tidal.exe')
