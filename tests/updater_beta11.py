"""Exercise real updater C# parsing/signature/extraction with a disposable key."""
from pathlib import Path
import base64, hashlib, json, subprocess, tempfile, zipfile
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
ROOT=Path(__file__).resolve().parents[1]
key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
with tempfile.TemporaryDirectory(prefix='eddy-updater-test-') as temporary:
    dest=Path(temporary)
    n=key.public_key().public_numbers().n
    (dest/'modulus.txt').write_text(base64.b64encode(n.to_bytes(256,'big')).decode())
    valid={'schema':1,'version':'2.2.9-beta.11','architecture':'x64','minWindowsBuild':22000,'file':'EddyDeck-Windows-2.2.9-beta.11.zip','size':123,'sha256':'0'*64,'url':'https://github.com/eddyorlandotp/eddy-deck/releases/download/v2.2.9-beta.11/EddyDeck-Windows-2.2.9-beta.11.zip'}
    def sign(name,data):
        raw=json.dumps(data).encode();(dest/(name+'.json')).write_bytes(raw);(dest/(name+'.sig')).write_bytes(base64.b64encode(key.sign(raw,padding.PKCS1v15(),hashes.SHA256())))
    sign('update',valid)
    for i,change in enumerate([{'schema':2},{'architecture':'arm64'},{'minWindowsBuild':19041},{'file':'else.zip'},{'size':0},{'size':500000001},{'sha256':'x'*64},{'url':'https://evil.example/package.zip'},{'version':'2.2.9-beta.12'}]):sign('invalid-'+str(i),{**valid,**change})
    for i,name in enumerate(['../escape','C:/escape','/root','a\\b','a:stream','CON.txt','nested/LPT1','same','link','a/../b','nested/a.']):
        with zipfile.ZipFile(dest/('unsafe-'+str(i)+'.zip'),'w') as z:
            entry=zipfile.ZipInfo(name)
            entry.filename=name  # Preserve the intentionally invalid backslash on Windows.
            if name=='link':entry.external_attr=(0o120777<<16)
            z.writestr(entry,'fixture')
            if name=='same':z.writestr('SAME','duplicate')
    with zipfile.ZipFile(dest/'good.zip','w') as z:z.writestr('nested/','');z.writestr('nested/file.txt','fixture')
    exe=dest/'UpdaterChecks.exe'
    subprocess.run(['C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe','/nologo','/target:exe','/r:System.Web.Extensions.dll','/r:System.IO.Compression.dll','/r:System.IO.Compression.FileSystem.dll','/out:'+str(exe),str(ROOT/'installer/GitHubUpdate.cs'),str(ROOT/'tests/UpdaterChecks.cs')],check=True,capture_output=True)
    result=subprocess.run([str(exe),str(dest)],capture_output=True,text=True,encoding='utf-8',timeout=45)
    (ROOT/'.build/beta11-updater-tests.txt').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    count=int(result.stdout.split('PASSED=')[-1].strip())
    (ROOT/'artifacts/beta11-updater-tests.json').write_text(json.dumps({'passed':True,'count':count,'checks':result.stdout.splitlines()[:-1],'scope':'Production C# updater with disposable fixture key; live GitHub download tested separately.','sourceSHA256':hashlib.sha256((ROOT/'installer/GitHubUpdate.cs').read_bytes()).hexdigest()},indent=2),encoding='utf-8')
    print('Updater checks passed:',count)
