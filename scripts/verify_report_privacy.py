"""Check release reports against local secrets without printing those secrets.

Run only on the maintainer's PC. This is an exact-match check, not a general
personal-data or independent security audit. No report bytes are uploaded here.
"""
import json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.core import VERSION

def main():
    from companion.storage import data_root,legacy_candidates
    roots=[data_root(),*legacy_candidates()];needles=[]
    for data in roots:
        if (data/'devices.json').exists():
            for peer in json.loads((data/'devices.json').read_text(encoding='utf-8')):
                for key in ('id','hash'):
                    if peer.get(key):needles.append(peer[key].encode())
        if (data/'server.key').exists():needles.append((data/'server.key').read_bytes().strip())
        for name in ('test-runtime.json','runtime.json'):
            path=data/name
            if path.exists():
                value=json.loads(path.read_text(encoding='utf-8'))
                for key in ('localToken','token'):
                    if isinstance(value.get(key),str) and len(value[key])>=16:needles.append(value[key].encode())
    for path in (ROOT/'private/release-signing.pem',ROOT/'private/signing-password.txt'):
        raw=path.read_bytes().strip()
        if raw:needles.append(raw)
    marker=ROOT/'.build/v2-test-data/test-runtime.json'
    if marker.exists():
        value=json.loads(marker.read_text(encoding='utf-8'))
        for key in ('localToken','token'):
            if isinstance(value.get(key),str) and len(value[key])>=16:needles.append(value[key].encode())
    output='beta'+VERSION.rsplit('beta.',1)[-1]+'-privacy-verification.json'
    reports=[p for p in (ROOT/'artifacts').glob('beta*-*') if p.suffix in ('.json','.txt','.md') and p.name!=output]
    reports += [p for p in (ROOT/'artifacts').glob('catalog-beta[0-9]*-*') if p.suffix in ('.json','.txt','.md','.csv')]
    reports += [p for p in (ROOT/'docs').glob('*') if p.is_file()]
    reports += [ROOT/'README.md']
    findings=[]
    for path in reports:
        raw=path.read_bytes()
        if any(value in raw for value in needles) or re.search(rb'-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----',raw):findings.append(path.name)
    result={'version':VERSION,'filesChecked':len(reports),'livePairIdentifiersAndHashesAbsent':not findings,'privateKeyAndSigningPasswordAbsent':not findings,'knownLocalBearerTokensAbsent':not findings,'filesWithMatches':findings,'scope':'Exact current pairing identifiers/hashes, complete private key bytes, signing password, known local bearer tokens and PEM private key headers. Not a general personal-data audit.'}
    (ROOT/'artifacts'/output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    if findings:raise RuntimeError('Private material matched report files: '+', '.join(findings))
    print(json.dumps(result))

if __name__=='__main__':main()
