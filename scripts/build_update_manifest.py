"""Sign the exact Windows download offered by the public GitHub release."""
from pathlib import Path
import base64, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from scripts.sign_release import prepare_key
from companion.core import VERSION

def main():
    file=ROOT/'artifacts'/f'EddyDeck-Windows-{VERSION}.zip'
    if not file.is_file():raise RuntimeError('Compila Windows, Android y empaqueta antes de firmar la descarga.')
    key,_,_=prepare_key()
    document={'schema':1,'version':VERSION,'architecture':'x64','minWindowsBuild':22000,'file':file.name,'size':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'url':f'https://github.com/eddyorlandotp/eddy-deck/releases/download/v{VERSION}/{file.name}'}
    raw=json.dumps(document,sort_keys=True,separators=(',',':')).encode('utf-8')
    (ROOT/'artifacts/EddyDeck-update.json').write_bytes(raw)
    (ROOT/'artifacts/EddyDeck-update.sig').write_bytes(base64.b64encode(key.sign(raw,padding.PKCS1v15(),hashes.SHA256())))
    print('Descarga firmada para',VERSION)

if __name__=='__main__':main()
