"""Native launch calls are isolated from the action queue, with owned cleanup."""
import json, subprocess, sys, tempfile, time
from pathlib import Path
from companion.child_lifetime import Lifetime,await_gate

def command():
    return [sys.executable,'--launch-application'] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).resolve().parents[1]/'run.py'),'--launch-application']

def launch(app,url='',check=lambda:None,timeout=12):
    check()
    with tempfile.TemporaryDirectory(prefix='eddy-launch-') as folder,Lifetime() as lifetime:
        result=Path(folder)/'result.json';gate=Path(folder)/'ready';request=json.dumps({'app':app,'url':url,'result':str(result),'gate':str(gate)},ensure_ascii=True,separators=(',',':'))
        if len(request)>24000:raise ValueError('La información de apertura es demasiado larga.')
        child=subprocess.Popen([*command(),request],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            lifetime.attach(child);gate.write_bytes(b'ready')
            end=time.monotonic()+timeout
            while child.poll() is None:
                check()
                if time.monotonic()>=end:raise ValueError('Windows no terminó de recibir la apertura. Revisa si hay un aviso de permisos o una ventana abierta antes de repetir. Las siguientes tareas pueden continuar.')
                time.sleep(.025)
            check()
            if not result.is_file() or result.stat().st_size>8000:raise ValueError('El auxiliar de apertura no devolvió un resultado válido. Revisa Windows antes de repetir.')
            data=json.loads(result.read_text(encoding='utf-8'))
            if child.returncode or data.get('error'):raise ValueError(data.get('error') or 'La apertura no pudo completarse.')
            if data.get('status')!='submitted':raise ValueError('Resultado de apertura no reconocido.')
            return data
        finally:
            if child.poll() is None:child.kill()
            child.wait(timeout=3)

def main():
    request=json.loads(sys.argv[2])
    if len(sys.argv[2])>24000 or not isinstance(request.get('app'),dict):raise ValueError('Invalid launch request')
    result=Path(request['result'])
    try:
        await_gate(request)
        from companion.windows import launch_inline
        data=launch_inline(request['app'],request.get('url',''));code=0
    except OSError as error:
        data={'error':'Esta aplicación requiere permiso de administrador en la PC. Ábrela allí manualmente; Eddy Deck no solicita ni evita ese permiso.' if getattr(error,'winerror',None)==740 else 'Windows rechazó la apertura: '+str(error)};code=2
    except Exception as error:data={'error':str(error)};code=2
    result.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    raise SystemExit(code)
