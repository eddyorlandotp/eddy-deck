"""Exercise the independent Windows checker against signed disposable packages."""
import base64,copy,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding
from companion.core import VERSION

def main():
 subprocess.run([sys.executable,str(ROOT/'scripts/build_checker.py')],check=True)
 key=serialization.load_pem_private_key((ROOT/'private/release-signing.pem').read_bytes(),None);results=[]
 with tempfile.TemporaryDirectory() as tmp:
  base=Path(tmp)
  for case in ('valid','missing_dependency','modified_same_size','extra_dll','bad_signature','wrong_arch','traversal','absolute','alternate_stream','double_slash','trailing_dot','missing_manifest'):
   folder=base/case;folder.mkdir();(folder/'EddyDeck.exe').write_bytes(b'fixture never executed');(folder/'lib.dll').write_bytes(b'ABC')
   manifest={'schema':1,'version':VERSION,'architecture':'arm64' if case=='wrong_arch' else 'x64','minWindowsBuild':22000,'files':{p.name:{'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in folder.iterdir()}}
   paths={'traversal':'../escape.dll','absolute':'C:/escape.dll','alternate_stream':'file:stream','double_slash':'a//b','trailing_dot':'x.'}
   if case in paths:manifest['files']={paths[case]:{'size':0,'sha256':'0'*64}}
   raw=json.dumps(manifest).encode();(folder/'release-manifest.json').write_bytes(raw);(folder/'release-manifest.sig').write_bytes(base64.b64encode(key.sign(raw,padding.PKCS1v15(),hashes.SHA256())))
   if case=='missing_dependency':(folder/'lib.dll').unlink()
   if case=='modified_same_size':(folder/'lib.dll').write_bytes(b'XYZ')
   if case=='extra_dll':(folder/'extra.dll').write_bytes(b'X')
   if case=='bad_signature':(folder/'release-manifest.sig').write_bytes(b'A'*512)
   if case=='missing_manifest':(folder/'release-manifest.json').unlink()
   output=base/(case+'.json');process=subprocess.run([str(ROOT/'.build/EddyDeck-Compatibilidad.exe'),'--check',str(folder),str(output)],timeout=20)
   report=json.loads(output.read_text(encoding='utf-8-sig'));expected=case=='valid';assert report['integrityVerified']==expected and process.returncode==(0 if expected else 2),case
   results.append({'case':case,'passed':True,'accepted':expected})
  system={k:v for k,v in report.items() if k not in ('error','integrityVerified','packageVersion')}
 (ROOT/'artifacts'/('beta'+VERSION.rsplit('beta.',1)[-1]+'-installer-checker.json')).write_text(json.dumps({'checks':results,'count':len(results),'system':system,'packagesNeverExecuted':True},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'passed':len(results),'windows11':system['windows11Compatible']}))
if __name__=='__main__':main()
