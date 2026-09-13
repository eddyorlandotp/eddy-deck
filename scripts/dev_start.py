from pathlib import Path
import os,socket,subprocess,sys
root=Path(__file__).resolve().parents[1]
data=root/'.build/dev-data'
try:
    with socket.create_connection(('127.0.0.1',47989),timeout=1):
        raise SystemExit('Sal de Eddy Deck antes de iniciar el servidor de desarrollo.')
except OSError: pass
log=(root/'.build/dev-process.log').open('ab')
process=subprocess.Popen([str(root/'.build/venv/Scripts/pythonw.exe'),str(root/'run.py'),'--headless','--dry-run','--data',str(data)],cwd=root,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
(root/'.build/dev.pid').write_text(str(process.pid))
print('Servicio de desarrollo iniciado. PID '+str(process.pid))
