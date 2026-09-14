"""Observed monitors and window leases; never choose a window by fuzzy title."""
import ctypes as C, hashlib, os, threading, time
from ctypes import wintypes as W
from pathlib import Path
from companion import windows

MODES={'keep','windowed','maximized','minimized','left-half','right-half'}

def validate_activation(value='front'):
    if value not in ('front','windows'):raise ValueError('Opción de primer plano no válida.')
    return value

def validate_layout(value,allow_ask=False):
    if value is None:return {'monitor':'keep','mode':'keep','missing':'stop'}
    if not isinstance(value,dict):raise ValueError('Diseño de ventana no válido.')
    monitor=value.get('monitor','keep'); mode=value.get('mode','keep'); missing=value.get('missing','stop')
    roles={'keep','primary','left','right','vertical'}|({'ask'} if allow_ask else set())
    if not isinstance(monitor,str) or (monitor not in roles and not (monitor.startswith('display:') and len(monitor)<=100)):
        raise ValueError('Monitor no válido.')
    if mode not in MODES or missing not in ('stop','primary'):raise ValueError('Diseño de ventana no válido.')
    return {'monitor':monitor,'mode':mode,'missing':missing}

def monitors():
    import win32api
    physical_coordinates()
    result=[]
    for handle,_,_ in win32api.EnumDisplayMonitors():
        m=win32api.GetMonitorInfo(handle);r=m['Monitor']
        result.append({'id':'display:'+m['Device'],'bounds':list(r),'work':list(m['Work']),'primary':bool(m['Flags']&1),'vertical':r[3]-r[1]>r[2]-r[0]})
    result.sort(key=lambda m:(m['bounds'][0]+m['bounds'][2],m['bounds'][1]))
    for i,m in enumerate(result):
        m['label']=('Izquierda' if i==0 and len(result)>1 else 'Derecha' if i==len(result)-1 and len(result)>1 else 'Pantalla '+str(i+1))
        if m['vertical']:m['label']+=' · vertical'
        if m['primary']:m['label']+=' · principal'
    return result

def resolve_monitor(settings,available,current=None):
    role=settings['monitor']
    if not available:raise ValueError('Windows no reporta una pantalla disponible.')
    selected=[]
    if role=='keep':selected=[m for m in available if m['id']==current] or [m for m in available if m['primary']]
    elif role=='primary':selected=[m for m in available if m['primary']]
    elif role=='left':selected=available[:1]
    elif role=='right':selected=available[-1:]
    elif role=='vertical':selected=[m for m in available if m['vertical']]
    else:selected=[m for m in available if m['id']==role]
    if len(selected)==1:return selected[0],False
    if settings['missing']=='primary':return next((m for m in available if m['primary']),available[0]),True
    raise ValueError('La pantalla elegida falta o hay varias verticales. Elige una pantalla concreta o permite usar la principal.')

if os.name=='nt':
    k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True);dwm=C.WinDLL('dwmapi')
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    k.CloseHandle.argtypes=[W.HANDLE]
    k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)]
    k.GetProcessTimes.argtypes=[W.HANDLE,C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME)]
    k.GetApplicationUserModelId.argtypes=[W.HANDLE,C.POINTER(W.UINT),W.LPWSTR]
    u.ShowWindowAsync.argtypes=[W.HWND,C.c_int];u.ShowWindowAsync.restype=W.BOOL
    u.AttachThreadInput.argtypes=[W.DWORD,W.DWORD,W.BOOL];u.AttachThreadInput.restype=W.BOOL
    u.IsHungAppWindow.argtypes=[W.HWND];u.IsHungAppWindow.restype=W.BOOL
    u.SetThreadDpiAwarenessContext.argtypes=[W.HANDLE];u.SetThreadDpiAwarenessContext.restype=W.HANDLE
    dwm.DwmGetWindowAttribute.argtypes=[W.HWND,W.DWORD,C.c_void_p,W.DWORD]

def physical_coordinates():
    # Called by the API/action worker, not Tk's UI thread. Keep monitor and window
    # coordinates consistent when screens use different scaling factors.
    if os.name=='nt':u.SetThreadDpiAwarenessContext(C.c_void_p(-4))

def requested_size(mode,resizable,old,width,height):
    if mode=='windowed' and resizable:return min(width,max(320,int(width*.8))),min(height,max(240,int(height*.8)))
    return min(max(100,old[2]-old[0]),width),min(max(80,old[3]-old[1]),height)

def process(pid):
    handle=k.OpenProcess(0x1000,False,pid)
    if not handle:return None
    try:
        buf=C.create_unicode_buffer(32768);size=W.DWORD(len(buf))
        if not k.QueryFullProcessImageNameW(handle,0,buf,C.byref(size)):return None
        created=W.FILETIME();a=W.FILETIME();b=W.FILETIME();c=W.FILETIME()
        if not k.GetProcessTimes(handle,C.byref(created),C.byref(a),C.byref(b),C.byref(c)):return None
        n=W.UINT(512);aid=C.create_unicode_buffer(n.value)
        if k.GetApplicationUserModelId(handle,C.byref(n),aid)!=0:aid.value=''
        return {'pid':pid,'path':buf.value,'created':(created.dwHighDateTime<<32)|created.dwLowDateTime,'aumid':aid.value}
    finally:k.CloseHandle(handle)

def _matches(app,processes,window_class=''):
    target=app['target'];norm=os.path.normcase(target)
    for p in processes:
        path=os.path.normcase(p['path'])
        if Path(path).name.lower()=='explorer.exe':
            if window_class not in ('CabinetWClass','ExploreWClass'):continue
            if target=='Microsoft.Windows.Explorer':return True
        if p['aumid'] and p['aumid']==target:return True
        if not app.get('sharedExecutable') and (path==norm or path==os.path.normcase(app.get('resolvedTarget',''))):return True
        root=app.get('installedRoot')
        if root and app['kind']=='protocol':
            if Path(path).name.lower() not in {'start_protected_game.exe','easyanticheat.exe','easyanticheat_eos.exe','unitycrashhandler64.exe'} and Path(path).is_relative_to(Path(os.path.normcase(root))):return True
        # Explicit launcher-to-main-process adapters, confined to their install tree.
        name=windows.folded(app['name']);leaf=Path(path).name.lower()
        if name=='git gui' and Path(norm).name.lower()=='git-gui.exe' and path==os.path.normcase(str(Path(norm).parent.parent/'mingw64/bin/wish.exe')) and window_class=='TkTopLevel':return True
        siblings=[]
        if 'opera' in name and Path(norm).name.lower()=='launcher.exe':siblings=['opera.exe']
        if 'roblox' in name and Path(norm).name.lower() in ('robloxplayerlauncher.exe','robloxplayerbeta.exe'):siblings=['robloxplayerbeta.exe']
        if name=='discord' and Path(norm).name.lower()=='update.exe':siblings=['discord.exe']
        if name=='tidal' and Path(norm).name.lower() in ('update.exe','tidal.exe'):siblings=['tidal.exe']
        if name=='capcut' and Path(norm).name.lower()=='capcut.exe':siblings=['capcut.exe']
        if name=='roblox studio' and Path(norm).name.lower()=='robloxstudiolauncherbeta.exe':siblings=['robloxstudiobeta.exe']
        if name=='steam' and Path(norm).name.lower()=='steam.exe':siblings=['steamwebhelper.exe']
        if name.startswith('blender') and Path(norm).name.lower()=='blender-launcher.exe':siblings=['blender.exe']
        if leaf in siblings:
            try:
                if Path(path).is_relative_to(Path(norm).parent):return True
            except ValueError:pass
    return False

class Windows:
    def __init__(self):self.lock=threading.RLock();self.leases={};self.protected=set()
    def require_window(self,wid,apps,terminate=False,allow_protected=False,allow_attention=False):
        current=self.snapshot(apps);item=next((w for w in current if w['id']==wid),None)
        if not item:raise ValueError('La ventana cambió o se cerró. Actualiza Mi PC.')
        with self.lock:
            if wid in self.protected and not allow_protected:raise ValueError('Esta ventana está protegida en Eddy Deck. Quita su protección antes de controlarla.')
            lease=self.leases.get(wid)
            if not lease:raise ValueError('La ventana cambió durante la comprobación.')
            if item.get('needsAttention') and not (terminate or allow_protected or allow_attention):
                raise ValueError('La aplicación tiene su ventana bloqueada por un aviso o diálogo. Atiéndelo en la PC antes de moverla o cerrarla.')
            if terminate:
                path=Path(lease['process']['path'])
                if not item['appIds'] or path.name.lower() in windows.DENY_EXE|{'eddydeck.exe','explorer.exe','applicationframehost.exe','shellexperiencehost.exe','startmenuexperiencehost.exe','svchost.exe','csrss.exe','wininit.exe','winlogon.exe','dwm.exe','lsass.exe','services.exe'} or path.is_relative_to(Path(os.environ.get('WINDIR',r'C:\Windows'))):
                    raise ValueError('No se finalizan procesos de Windows, receptores ni hosts compartidos. Usa el cierre normal o revisa la aplicación en la PC.')
        return item
    def protect(self,wid,enabled,apps):
        self.require_window(wid,apps,allow_protected=True)
        with self.lock:
            if enabled:self.protected.add(wid)
            else:self.protected.discard(wid)
        return {'status':'protected' if enabled else 'unprotected','message':'Ventana protegida frente a movimientos y cierres de Eddy Deck.' if enabled else 'Protección retirada.'}
    def close_window(self,wid,apps,check=lambda:None):
        import win32gui as g
        self.require_window(wid,apps)
        with self.lock:lease=dict(self.leases[wid])
        if not any(w['id']==wid for w in self.snapshot(apps)):raise ValueError('La ventana ya cambió.')
        check();self.require_window(wid,apps)
        g.PostMessage(lease['hwnd'],0x10,0,0)
        for _ in range(15):
            check();time.sleep(.1)
            if not any(w['id']==wid for w in self.snapshot(apps)):return {'status':'closed_or_hidden','message':'La ventana se cerró u ocultó. Se respetó el cierre normal de la aplicación.'}
        return {'status':'needs_attention','message':'Cierre solicitado. La aplicación sigue abierta o pide guardar/confirmar en Windows; no se forzó.'}
    def restore(self,wid,apps,check=lambda:None):
        import win32gui as g
        self.require_window(wid,apps)
        with self.lock:hwnd=self.leases[wid]['hwnd']
        check();self.require_window(wid,apps)
        u.ShowWindowAsync(hwnd,9)
        until=time.monotonic()+2
        while time.monotonic()<until:
            check()
            if not g.IsWindow(hwnd):raise ValueError('La ventana se cerró mientras se restauraba.')
            if not g.IsIconic(hwnd):return {'status':'restored','message':'Ventana restaurada con su posición y tamaño anteriores.'}
            time.sleep(.05)
        raise ValueError('La aplicación no aceptó restaurar su ventana.')
    def terminate_window(self,wid,apps,check=lambda:None):
        import win32process
        self.require_window(wid,apps,terminate=True)
        with self.lock:lease=dict(self.leases[wid])
        expected=lease['process'];handle=k.OpenProcess(0x1001,False,expected['pid'])
        if not handle:raise ValueError('Windows no permite finalizar este proceso. No se elevan permisos.')
        try:
            a,b,c,d=(W.FILETIME() for _ in range(4));critical=W.BOOL()
            k.IsProcessCritical.argtypes=[W.HANDLE,C.POINTER(W.BOOL)];k.IsProcessCritical.restype=W.BOOL
            if not k.IsProcessCritical(handle,C.byref(critical)) or critical.value:raise ValueError('Windows protege este proceso.')
            if not k.GetProcessTimes(handle,C.byref(a),C.byref(b),C.byref(c),C.byref(d)) or ((a.dwHighDateTime<<32)|a.dwLowDateTime)!=expected['created']:raise ValueError('El proceso fue reemplazado. No se finalizó.')
            check();self.require_window(wid,apps,terminate=True)
            if win32process.GetWindowThreadProcessId(lease['hwnd'])[1]!=expected['pid']:raise ValueError('La ventana cambió de proceso.')
            k.TerminateProcess.argtypes=[W.HANDLE,W.UINT];k.TerminateProcess.restype=W.BOOL
            if not k.TerminateProcess(handle,1):raise ValueError('Windows rechazó la finalización.')
            return {'status':'terminated','message':'Se finalizó el proceso seleccionado. Sus ventanas pueden haberse cerrado.'}
        finally:k.CloseHandle(handle)
    def snapshot(self,apps):
        import win32gui as g, win32process as p, win32api
        physical_coordinates()
        result=[];fresh={};cache={}
        with self.lock:previous=list(self.leases.values())
        def info(pid):
            if pid not in cache:cache[pid]=process(pid)
            return cache[pid]
        def visit(hwnd,_):
            try:
                if not g.IsWindowVisible(hwnd) or g.GetWindow(hwnd,4):return
                title=g.GetWindowText(hwnd)
                if not title or g.GetWindowLong(hwnd,-20)&0x80:return
                cloaked=W.DWORD()
                if dwm.DwmGetWindowAttribute(hwnd,14,C.byref(cloaked),4)==0 and cloaked.value:return
                pid=p.GetWindowThreadProcessId(hwnd)[1];main=info(pid)
                if not main or pid==os.getpid():return
                if Path(main['path']).name.lower() in windows.DENY_EXE|{'logonui.exe','credentialuibroker.exe','consent.exe','lockapp.exe','systemsettings.exe'}:return
                processes=[main]
                if Path(main['path']).name.lower()=='applicationframehost.exe':
                    def child(ch,_):
                        cp=info(p.GetWindowThreadProcessId(ch)[1])
                        if cp and cp not in processes:processes.append(cp)
                    g.EnumChildWindows(hwnd,child,None)
                    # UWP detaches its child window while minimized. Retain a
                    # previously observed association only while those exact
                    # processes still exist, and only for the same frame HWND.
                    if len(processes)==1 and g.IsIconic(hwnd):
                        old=next((v for v in previous if v['hwnd']==hwnd and v['process']==main),None)
                        if old:
                            for attached in old.get('attached',[])[1:]:
                                observed=info(attached['pid'])
                                if observed and observed['created']==attached['created']:processes.append(observed)
                cls=g.GetClassName(hwnd)
                if Path(main['path']).name.lower()=='explorer.exe' and cls not in ('CabinetWClass','ExploreWClass'):return
                app_ids=[a['id'] for a in apps if _matches(a,processes,cls)]
                identity=str((hwnd,main['pid'],main['created'],cls,[(x['pid'],x['created'],x['aumid']) for x in processes]))
                wid=hashlib.sha256(identity.encode()).hexdigest()[:32]
                monitor=win32api.GetMonitorInfo(win32api.MonitorFromWindow(hwnd,2))
                item={'id':wid,'title':title[:160],'appIds':app_ids,'process':Path(main['path']).name,'monitor':'display:'+monitor['Device'],'minimized':bool(g.IsIconic(hwnd)),'maximized':g.GetWindowPlacement(hwnd)[1]==3,'protected':wid in self.protected}
                item['needsAttention']=not bool(g.IsWindowEnabled(hwnd))
                fresh[wid]={'hwnd':hwnd,'identity':identity,'process':main,'attached':processes};result.append(item)
            except Exception:return
        g.EnumWindows(visit,None)
        with self.lock:self.leases=fresh;self.protected.intersection_update(fresh)
        return result
    def move(self,wid,settings,apps,check=lambda:None):
        import win32gui as g,win32api
        settings=validate_layout(settings);available=self.snapshot(apps)
        item=next((w for w in available if w['id']==wid),None)
        if not item:raise ValueError('Esa ventana ya cambió o se cerró. Actualiza la lista y selecciónala otra vez.')
        self.require_window(wid,apps)
        with self.lock:lease=dict(self.leases[wid])
        target,fallback=resolve_monitor(settings,monitors(),item['monitor']);check()
        if settings['mode']=='keep' and target['id']==item['monitor']:
            return {'status':'completed','message':'La ventana ya está en '+target['label']+'.','windowId':wid}
        # Re-enumerate immediately before mutation; HWND/PID reuse is rejected.
        self.snapshot(apps)
        with self.lock:
            if wid not in self.leases or self.leases[wid]['identity']!=lease['identity']:raise ValueError('La ventana cambió antes de moverla.')
        # The monitor may have been unplugged while the window was validated.
        target,changed_fallback=resolve_monitor(settings,monitors(),item['monitor']);fallback=fallback or changed_fallback
        hwnd=lease['hwnd'];mode=settings['mode'];x,y,r,b=target['work'];width=r-x;height=b-y
        if width<=0 or height<=0:raise ValueError('Windows reportó una pantalla sin área utilizable. Actualiza las pantallas.')
        style=g.GetWindowLong(hwnd,-16);resizable=bool(style&0x40000)
        # Borderless apps such as Roblox accept SW_MAXIMIZE without advertising
        # WS_THICKFRAME or WS_MAXIMIZEBOX. Observe the result instead of guessing.
        if mode in ('left-half','right-half') and not resizable and not style&0x10000:
            raise ValueError('Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.')
        if mode=='minimized' and settings['monitor']=='keep':u.ShowWindowAsync(hwnd,6)
        else:
            # Keep restored bounds inside the work area (taskbar excluded).
            old=g.GetWindowRect(hwnd)
            if item['minimized'] or item['maximized']:old=g.GetWindowPlacement(hwnd)[4]
            w,h=requested_size(mode,resizable,old,width,height)
            px=x+(width-w)//2;py=y+(height-h)//2
            if mode in ('left-half','right-half'):w=width//2;h=height;px=x if mode=='left-half' else x+width//2;py=y
            u.ShowWindowAsync(hwnd,9);check()
            restored=time.monotonic()+.8
            while (g.IsIconic(hwnd) or g.GetWindowPlacement(hwnd)[1]==3) and time.monotonic()<restored:
                check()
                # Minimized-from-maximized restores to maximized first. A second
                # restore is needed before applying normal window geometry.
                if not g.IsIconic(hwnd) and g.GetWindowPlacement(hwnd)[1]==3:u.ShowWindowAsync(hwnd,9)
                time.sleep(.04)
            g.SetWindowPos(hwnd,0,px,py,w,h,0x14|0x4000)
            if mode=='maximized' or (mode=='keep' and item['maximized']):u.ShowWindowAsync(hwnd,3)
            elif mode=='minimized' or (mode=='keep' and item['minimized']):u.ShowWindowAsync(hwnd,6)
            else:u.ShowWindowAsync(hwnd,4)
        until=time.monotonic()+2
        while time.monotonic()<until:
            check()
            if not g.IsWindow(hwnd):raise ValueError('La aplicación cerró la ventana durante el movimiento.')
            actual=win32api.GetMonitorInfo(win32api.MonitorFromWindow(hwnd,2))
            on_monitor='display:'+actual['Device']==target['id']
            state_ok=(bool(g.IsIconic(hwnd)) if mode=='minimized' else g.GetWindowPlacement(hwnd)[1]==3 if mode=='maximized' else True)
            if mode=='windowed':
                # Windowed means restored and placed on the requested display.
                # 80% is a preferred size, not a requirement that defeats apps'
                # own minimum sizes, aspect ratios, skins or DPI handling.
                state_ok=not g.IsIconic(hwnd) and g.GetWindowPlacement(hwnd)[1]!=3
            elif mode in ('left-half','right-half'):
                rect=g.GetWindowRect(hwnd)
                state_ok=not g.IsIconic(hwnd) and max(abs(a-b) for a,b in zip(rect,(px,py,px+w,py+h)))<=24
            if on_monitor and state_ok:return {'status':'completed','message':'Ventana en '+target['label']+(' (se usó la principal porque faltó el destino).' if fallback else '.')+(' Se conservó su tamaño fijo.' if not resizable and mode=='windowed' else ''),'windowId':wid}
            time.sleep(.1)
        raise ValueError('La aplicación no aceptó el diseño. Prueba modo ventana desde la app; los juegos a pantalla completa pueden controlar su posición.')
    def foreground(self,wid,apps,check=lambda:None):
        import win32gui as g
        from companion.focus import run_bounded
        self.require_window(wid,apps)
        with self.lock:lease=dict(self.leases[wid]);hwnd=lease['hwnd']
        check()
        if g.IsIconic(hwnd):self.restore(wid,apps,check)
        self.require_window(wid,apps)
        request={'hwnd':hwnd,'pid':lease['process']['pid'],'created':lease['process']['created'],'class':g.GetClassName(hwnd)}
        result=run_bounded(request,check)
        check();self.require_window(wid,apps)
        if result.get('foreground') and g.GetForegroundWindow()==hwnd:
            return {'status':'completed','message':'Ventana mostrada al frente.','windowId':wid,'foreground':True}
        return {'status':'needs_attention','message':'La aplicación está abierta, pero Windows no permitió activarla al frente a tiempo. Revisa su ventana en la PC.','windowId':wid,'foreground':False}

    def present(self,wid,settings,apps,check,activation='front'):
        settings=validate_layout(settings);validate_activation(activation)
        item=self.require_window(wid,apps,allow_attention=True)
        if item.get('needsAttention'):
            return {'status':'needs_attention','message':'La aplicación está abierta y tiene un aviso o diálogo pendiente en la PC. No se mueve ni se confirma automáticamente.','windowId':wid,'foreground':False}
        if settings['monitor']!='keep' or settings['mode']!='keep':result=self.move(wid,settings,apps,check)
        elif item['minimized']:result=self.restore(wid,apps,check)
        else:result={'status':'already_open','message':'Se conserva la ventana existente.','windowId':wid}
        if activation=='front' and settings['mode']!='minimized':
            shown=self.foreground(wid,apps,check)
            return {**result,**shown,'message':result['message']+' '+shown['message']}
        return result

    def launch(self,app,url,settings,apps,check,activation='front'):
        settings=validate_layout(settings)
        validate_activation(activation)
        if activation=='windows' and settings['monitor']=='keep' and settings['mode']=='keep':check();return windows.launch(app,url,check)
        if settings['monitor']!='keep' or settings['mode']!='keep':resolve_monitor(settings,monitors()) # fail before launching on an absent monitor
        before=[w for w in self.snapshot(apps) if app['id'] in w['appIds']]
        check();result=windows.launch(app,url,check);launched=time.monotonic();deadline=launched+30;stable=None;since=launched
        while time.monotonic()<deadline:
            check();current=[w for w in self.snapshot(apps) if app['id'] in w['appIds']]
            new=[w for w in current if w['id'] not in {v['id'] for v in before}]
            chosen=new if new else current
            if len(chosen)==1:
                wid=chosen[0]['id']
                if stable!=wid:stable=wid;since=time.monotonic()
                if time.monotonic()-since>=1 and time.monotonic()-launched>=2:
                    result=self.present(wid,settings,apps,check,activation)
                    if settings['monitor']=='keep' and settings['mode']=='keep' and result['status']=='completed':result['message']='Apertura observada. '+result['message']
                    return result
            else:stable=None
            if len(chosen)>1 and time.monotonic()-launched>=3:raise ValueError('Hay varias ventanas de '+app['name']+'. Selecciona la ventana exacta en Mi PC.')
            time.sleep(.3)
        raise ValueError('Se envió la apertura, pero no apareció una ventana identificable en 30 segundos. Revisa la app; no se vuelve a abrir automáticamente.')
