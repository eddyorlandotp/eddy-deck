"""Self-contained Windows release. Run with the project's build venv."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]

def write_version_info():
    """Standard Windows version resource. Unsigned binaries without any
    publisher or product metadata look more suspicious to antivirus models."""
    sys.path.insert(0,str(ROOT))
    from companion.core import VERSION
    from companion.resilience import version_key
    major,minor,patch,_,pre=version_key(VERSION)
    numbers=(major,minor,patch,pre)
    text=f'''VSVersionInfo(
  ffi=FixedFileInfo(filevers={numbers},prodvers={numbers},mask=0x3f,flags=0x0,OS=0x40004,fileType=0x1,subtype=0x0,date=(0,0)),
  kids=[StringFileInfo([StringTable('0C0A04B0',[
    StringStruct('CompanyName','Eddy Orlando'),
    StringStruct('FileDescription','Eddy Deck - control de tu PC desde tu celular'),
    StringStruct('FileVersion','{VERSION}'),
    StringStruct('InternalName','EddyDeck'),
    StringStruct('LegalCopyright','MIT License'),
    StringStruct('OriginalFilename','EddyDeck.exe'),
    StringStruct('ProductName','Eddy Deck'),
    StringStruct('ProductVersion','{VERSION}')])]),
  VarFileInfo([VarStruct('Translation',[0x0C0A,1200])])])
'''
    path=ROOT/'.build'/'version_info.txt';path.write_text(text,encoding='utf-8');return path

def main():
    sys.path.insert(0,str(ROOT))
    from scripts.sign_release import prepare_key,sign
    from scripts.build_checker import build
    from scripts.build_manual import main as build_manual
    build_manual()
    prepare_key()
    img=Image.new('RGBA',(256,256),(0,0,0,0));d=ImageDraw.Draw(img)
    d.rounded_rectangle((0,0,255,255),radius=58,fill='#3979ed')
    for x,y in ((55,55),(142,55),(55,142)):d.rounded_rectangle((x,y,x+60,y+60),radius=15,fill='white')
    d.polygon([(146,138),(207,172),(146,207)],fill='white')
    img.save(ROOT/'ui/app.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    version_file=write_version_info()
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--name','EddyDeck','--icon',str(ROOT/'ui/app.ico'),'--version-file',str(version_file),
             '--distpath',str(ROOT/'artifacts/windows'),'--workpath',str(ROOT/'.build/pyinstaller'),'--specpath',str(ROOT/'.build'),
             '--add-data',str(ROOT/'ui')+';ui','--hidden-import','win32com.client','--hidden-import','win32timezone',
             '--collect-submodules','pystray',str(ROOT/'run.py')]
    subprocess.run(command,cwd=ROOT,check=True)
    output=ROOT/'artifacts/windows/EddyDeck'
    usb=output/'usb';usb.mkdir(exist_ok=True)
    source=ROOT/'.build/tools/platform-tools/platform-tools'
    for name in ('adb.exe','AdbWinApi.dll','AdbWinUsbApi.dll','NOTICE.txt'):
        if (source/name).exists():shutil.copy2(source/name,usb/name)
    build(output/'EddyDeck-Compatibilidad.exe')
    from scripts.build_tidal import build as build_tidal
    build_tidal(output/'EddyDeck-Tidal.exe')
    from scripts.build_media import build as build_media
    build_media(output/'EddyDeck-Media.exe')
    from scripts.build_audio import build as build_audio
    build_audio(output/'EddyDeck-Audio.exe')
    (output/'Instalar.cmd').write_text('@echo off\r\nif not exist "%~dp0EddyDeck-Compatibilidad.exe" (\r\n echo Falta el comprobador. Extrae el ZIP completo de Eddy Deck.\r\n pause\r\n exit /b 1\r\n)\r\nstart "" "%~dp0EddyDeck-Compatibilidad.exe"\r\n',encoding='ascii')
    shutil.copy2(ROOT/'README.md',output/'LEEME.md')
    shutil.copy2(ROOT/'LICENSE',output/'LICENSE.txt')
    shutil.copy2(ROOT/'docs/THIRD_PARTY.md',output/'THIRD_PARTY.md')
    docs=output/'docs';docs.mkdir(exist_ok=True)
    for path in (ROOT/'docs').glob('*'):
        if path.is_file() and path.suffix in ('.md','.html'):shutil.copy2(path,docs/path.name)
    import importlib.metadata, pystray
    licenses=output/'licenses';licenses.mkdir(exist_ok=True);license_index=[]
    for package in ('cryptography','qrcode','pillow','pystray','pywin32','cffi','six','pywin32-ctypes'):
        dist=importlib.metadata.distribution(package)
        for file in dist.files or []:
            if any(word in str(file).lower() for word in ('license','copying','notice')) and ('.dist-info' in str(file) or 'licenses' in str(file)):
                actual=Path(dist.locate_file(file))
                if actual.is_file():
                    # Keep every notice, without deep wheel metadata paths that
                    # can exceed Windows MAX_PATH while staging an update.
                    short=hashlib.sha256(str(file).encode()).hexdigest()[:12]+'-'+Path(str(file)).name
                    dest=licenses/package/short;dest.parent.mkdir(parents=True,exist_ok=True)
                    if dest.exists() and dest.read_bytes()!=actual.read_bytes():raise RuntimeError('Colisión de nombres de licencia: '+short)
                    shutil.copy2(actual,dest)
                    license_index.append({'package':package,'version':dist.version,'original':str(file).replace('\\','/'),'copy':dest.relative_to(licenses).as_posix(),'sha256':hashlib.sha256(actual.read_bytes()).hexdigest()})
    (licenses/'INDICE.json').write_text(json.dumps(license_index,ensure_ascii=False,indent=2),encoding='utf-8')
    for name in ('LICENSE.txt','LICENSE'):
        if (Path(sys.base_prefix)/name).is_file():shutil.copy2(Path(sys.base_prefix)/name,licenses/'Python-LICENSE.txt')
    shutil.copytree(Path(pystray.__file__).parent,licenses/'pystray-source',ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
    sign(output)
    print('Ejecutable listo: '+str(output/'EddyDeck.exe'),flush=True)
    print('SHA256 '+hashlib.sha256((output/'EddyDeck.exe').read_bytes()).hexdigest(),flush=True)

if __name__=='__main__':main()
