"""Sign the packaged manifest with a persistent private release key."""
from pathlib import Path
import base64,hashlib,json,sys
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding,rsa
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def prepare_key():
    file=ROOT/'private/release-signing.pem';file.parent.mkdir(exist_ok=True)
    if file.exists():key=serialization.load_pem_private_key(file.read_bytes(),None)
    else:
        key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        file.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    p=key.public_key().public_numbers();mod=base64.b64encode(p.n.to_bytes((p.n.bit_length()+7)//8,'big')).decode()
    source="# Public release verification key. The signing key stays in private/.\nMODULUS="+repr(mod)+"\nEXPONENT="+str(p.e)+"\n"
    (ROOT/'companion/release_public.py').write_text(source,encoding='utf-8')
    return key,mod,p.e
def sign(folder):
    from companion.core import VERSION
    from companion.integrity import UPDATE_URL,MANIFEST,SIGNATURE
    key,_,_=prepare_key();folder=Path(folder)
    files={p.relative_to(folder).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in sorted(folder.rglob('*')) if p.is_file() and p.name not in (MANIFEST,SIGNATURE)}
    m={'schema':1,'version':VERSION,'architecture':'x64','minWindowsBuild':22000,'backupFolderUrl':UPDATE_URL,'files':files}
    raw=json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    (folder/MANIFEST).write_bytes(raw);(folder/SIGNATURE).write_bytes(base64.b64encode(key.sign(raw,padding.PKCS1v15(),hashes.SHA256())))
    print('Manifiesto firmado:',len(files),'archivos; clave privada excluida.')
if __name__=='__main__':sign(ROOT/'artifacts/windows/EddyDeck')
