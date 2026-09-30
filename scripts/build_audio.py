"""Build the isolated Core Audio helper using the Windows .NET compiler."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
def build(output):
    compiler=Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe')
    subprocess.run([str(compiler),'/nologo','/r:System.Web.Extensions.dll','/out:'+str(output),str(ROOT/'companion/AudioOutput.cs')],check=True)
if __name__=='__main__':build(ROOT/'.build/EddyDeck-Audio.exe')
