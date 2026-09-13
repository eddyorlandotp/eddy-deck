"""Record observed build tools without usernames, serials, tokens or private paths."""
import hashlib,importlib.metadata,json,platform,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from companion.core import VERSION

def main():
    toolroot=ROOT/'.build/tools'
    versions={dist.metadata['Name']:dist.version for dist in importlib.metadata.distributions() if dist.metadata.get('Name')}
    binaries=[]
    for name in ('java.exe','javac.exe','aapt2.exe','zipalign.exe','adb.exe','d8.jar','apksigner.jar','android.jar'):
        matches=list(toolroot.rglob(name))
        if len(matches)!=1:raise RuntimeError('Herramienta ausente o ambigua: '+name)
        path=matches[0]
        binaries.append({'name':name,'relativePath':path.relative_to(toolroot).as_posix(),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    java=next(toolroot.rglob('java.exe'))
    version=subprocess.run([str(java),'-version'],capture_output=True,text=True,check=True).stderr.strip()
    report={'version':VERSION,'capturedAtUTC':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),'pythonArchitecture':platform.architecture()[0],'windowsVersion':platform.version(),'javaVersion':version,'pythonPackages':dict(sorted(versions.items(),key=lambda item:item[0].lower())),'downloadManifest':json.loads((toolroot/'sources.json').read_text(encoding='utf-8')),'toolFiles':binaries,'scope':'Observed build environment; tool SHA-256 hashes are local. Does not guarantee byte-identical future builds or capture signing keys.'}
    destination=ROOT/'artifacts'/('beta'+VERSION.rsplit('beta.',1)[-1]+'-build-environment.json')
    destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'report':destination.name,'python':report['python'],'packages':len(versions),'tools':len(binaries)}))

if __name__=='__main__':main()
