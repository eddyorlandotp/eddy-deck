"""Download a local Android toolchain from Google and Microsoft; verify checksums."""
from pathlib import Path
import concurrent.futures, hashlib, json, urllib.request, xml.etree.ElementTree as ET, zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / '.build' / 'tools'
DEST.mkdir(parents=True, exist_ok=True)

def get(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()

def download(name, url, checksum, algorithm, folder):
    archive = DEST / (name + '.zip')
    if not archive.exists() or hashlib.new(algorithm, archive.read_bytes()).hexdigest() != checksum:
        print('Descargando ' + name, flush=True)
        archive.write_bytes(get(url))
    actual = hashlib.new(algorithm, archive.read_bytes()).hexdigest()
    if actual != checksum:
        raise RuntimeError('Checksum incorrecto: ' + name)
    out = DEST / folder
    if not (out / '.complete').exists():
        out.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as package:
            for entry in package.infolist():
                if not (out / entry.filename).resolve().is_relative_to(out.resolve()):
                    raise ValueError('Invalid archive path')
            package.extractall(out)
        (out / '.complete').touch()
    print('Verificado: ' + name, flush=True)
    return {'name': name, 'url': url, 'checksum': checksum, 'algorithm': algorithm}

def main():
    xml = ET.fromstring(get('https://dl.google.com/android/repository/repository2-1.xml'))
    for node in xml.iter():
        node.tag = node.tag.rsplit('}', 1)[-1]
    items = []
    for package in xml.findall('remotePackage'):
        path = package.attrib['path']
        if path not in ('platform-tools', 'build-tools;35.0.0', 'platforms;android-35'):
            continue
        if path == 'platforms;android-35' and package.findtext('display-name') != 'Android SDK Platform 35':
            continue
        for archive in package.findall('archives/archive'):
            host = archive.findtext('host-os')
            if host not in (None, 'windows'):
                continue
            complete = archive.find('complete')
            check = complete.find('checksum')
            name = path.replace(';', '-')
            items.append((name, 'https://dl.google.com/android/repository/' + complete.findtext('url'), check.text, check.get('type', 'sha1'), name))
    jdk = 'https://aka.ms/download-jdk/microsoft-jdk-17.0.20.1-windows-x64.zip'
    checksum = get(jdk + '.sha256sum.txt').decode().split()[0]
    items.append(('jdk17', jdk, checksum, 'sha256', 'jdk17'))
    if len(items) != 4:
        raise RuntimeError('No se encontraron los cuatro paquetes oficiales')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda args: download(*args), items))
    (DEST / 'sources.json').write_text(json.dumps(records, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
