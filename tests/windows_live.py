"""Opt-in integration check: opens a fresh Calculator, moves only its leased HWND,
then closes only that new window. Never calls power or alters other windows."""
import sys,time,json,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import win32gui
from companion import windows
from companion.layout import Windows,monitors,validate_layout

def main():
    apps,_=windows.scan(Path('.'));calculator=[a for a in apps if windows.folded(a['name']) in ('calculadora','calculator')]
    if len(calculator)!=1:raise RuntimeError('No se encontró una Calculadora única.')
    app=calculator[0];layout=Windows();before=layout.snapshot(apps)
    if any(app['id'] in w['appIds'] for w in before):raise RuntimeError('Calculadora ya está abierta. Se conserva; no se hizo la prueba.')
    result=layout.launch(app,'',{'monitor':'right','mode':'windowed'},apps,lambda:None)
    wid=result['windowId'];results=[result]
    try:
        for settings in [{'monitor':'vertical','mode':'maximized'},{'monitor':'right','mode':'left-half'},{'monitor':'keep','mode':'minimized'},{'monitor':'left','mode':'windowed'}]:
            results.append(layout.move(wid,settings,apps))
        try:layout.move(wid,{'monitor':'display:missing','mode':'maximized'},apps)
        except ValueError:results.append({'status':'passed','message':'Pantalla ausente rechazada sin mover la ventana.'})
        else:raise AssertionError('Aceptó monitor inexistente')
        results.append(layout.move(wid,{'monitor':'display:missing','mode':'windowed','missing':'primary'},apps))
    finally:
        layout.snapshot(apps)
        lease=layout.leases.get(wid)
        if lease:win32gui.PostMessage(lease['hwnd'],0x10,0,0)
    end=time.monotonic()+4
    while time.monotonic()<end and any(w['id']==wid for w in layout.snapshot(apps)):time.sleep(.1)
    assert not any(w['id']==wid for w in layout.snapshot(apps)),'La ventana de prueba no cerró'
    try:layout.move(wid,{'monitor':'left'},apps)
    except ValueError:results.append({'status':'passed','message':'Ventana cerrada rechazada.'})
    else:raise AssertionError('Aceptó HWND obsoleto')
    output={'monitors':monitors(),'results':results,'closedTestWindow':True,'otherWindowsPreserved':all(w['id'] in {x['id'] for x in layout.snapshot(apps)} for w in before)}
    Path('artifacts/windows-live-tests.json').write_text(json.dumps(output,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps(output,ensure_ascii=True))
if __name__=='__main__':main()
