"""Small, explicit Windows adapters. No arbitrary remote commands or shell text."""
from __future__ import annotations
import ctypes as C
from ctypes import wintypes as W
import hashlib, json, os, re, subprocess, time, unicodedata
from pathlib import Path
from urllib.parse import urlsplit

HIDDEN = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
SYSTEM = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32'
PS = SYSTEM / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'

def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))

DENY_NAME = re.compile(r'(uninstall|desinstal|readme|read me|release notes|manual|documentation|homepage|diagnost|administraci|administrador|registro|registry|powershell|terminal|command prompt|git (bash|cmd)|python|pydoc|idle|iscs|odbc|seguridad|security|defender|autentic|contrase|password|remote desktop|escritorio remoto|quick assist|asistencia rapida|ejecutar|programador de tareas|desfragment|liberador|disk cleanup|recovery|recuperaci|configuraci.n del sistema|system configuration|windows tools|herramientas de windows|monitor de (rendimiento|recursos)|preferencias de idioma)', re.I)
DENY_EXE = {'cmd.exe','powershell.exe','pwsh.exe','wt.exe','wscript.exe','cscript.exe','mshta.exe','rundll32.exe','regsvr32.exe','regedit.exe','mmc.exe','msiexec.exe','runas.exe','schtasks.exe','shutdown.exe','python.exe','pythonw.exe','bash.exe','ssh.exe','mstsc.exe','control.exe','unins000.exe','uninstall.exe','dfrgui.exe','resmon.exe','taskmgr.exe','msinfo32.exe','psr.exe','systemsettings.exe','consent.exe','logonui.exe','credentialuibroker.exe'}

def safe_executable(path):
    p = Path(path)
    return p.is_absolute() and p.suffix.lower() == '.exe' and p.name.lower() not in DENY_EXE and not p.name.lower().startswith(('unins','uninstall')) and p.is_file() and not str(p).startswith('\\\\')

def blocked_shell_target(aid,resolved):
    # Explorer's built-in AppsFolder item resolves to its shell folder CLSID,
    # not an executable. Permit only this exact Windows identity and target.
    if aid=='Microsoft.Windows.Explorer' and str(resolved).upper()=='::{52205FD8-5DFB-447D-801A-D0B52F2E83E1}':return False
    return bool(resolved) and not safe_executable(str(resolved))

def category(name, target):
    text = folded(name)
    if any(x in text for x in ('opera','edge','chrome','firefox','brave','vivaldi')):
        return 'Navegadores', 'browser'
    if any(x in text for x in ('aimp','spotify','tidal','media player','vlc','music','reproductor')):
        return 'Música', 'music'
    if target.startswith(('steam://','com.epicgames.launcher://')) or any(x in text for x in ('steam','xbox','riot','epic games','minecraft','fortnite','halo','forza','hollow knight','fallout','among us','balatro','silksong','roblox','hoyoplay','battle.net','blood strike')):
        return 'Juegos', 'game'
    if any(x in text for x in ('discord','whatsapp','telegram','teams','outlook')):
        return 'Social', 'chat'
    if any(x in text for x in ('blender','davinci','obs studio','capcut','studio','inkscape','paint','photos','photoshop')):
        return 'Crear', 'create'
    return 'Aplicaciones', 'app'

def normalize_inventory(raw):
    selected = {}
    for source in raw.get('apps', []):
        name = str(source.get('name', '')).strip()
        target = str(source.get('target') or '')
        kind = source.get('kind')
        key = folded(name)
        if not name or source.get('blockedResolvedTarget') or DENY_NAME.search(key) or key.startswith('eddy deck') or key in {'configuracion','panel de control','task manager','resource monitor','system information','dfrgui','visor de eventos','steps recorder','grabacion de acciones de usuario','website','more...'}:
            continue
        if kind == 'shortcut':
            if not safe_executable(target):
                continue
        elif kind == 'protocol':
            if not re.fullmatch(r'steam://(?:rungameid|run)/\d+/?', target) and not target.startswith('com.epicgames.launcher://apps/'):
                continue
        elif kind == 'shell':
            if target.startswith(('http:', 'https:')) or target.lower().endswith(('.html','.pdf','.msc','.cpl','.url','.bat','.cmd','.ps1')) or Path(target).name.lower() in DENY_EXE:
                continue
            if not ('!' in target or target.startswith(('Microsoft.','com.','OperaSoftware.','steam:','{')) or (Path(target).is_absolute() and Path(target).suffix.lower()=='.exe')):
                continue
        else:
            continue
        if key in selected and selected[key]['kind'] in ('shortcut','protocol'):
            continue
        group, icon = category(name, target)
        entry = dict(source)
        # Name-based identity survives ordinary versioned executable-path updates.
        entry.update(id=hashlib.sha256(key.encode()).hexdigest()[:20], name=name, category=group, symbol=icon,
                     browser=group=='Navegadores' and safe_executable(target), available=True)
        selected[key] = entry
    return sorted(selected.values(), key=lambda item: folded(item['name']))

def scan(root):
    import pythoncom, win32com.client
    pythoncom.CoInitialize()
    raw={'apps':[]}; warnings=[]
    try:
        shell=win32com.client.Dispatch('WScript.Shell')
        roots=[Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu',Path(os.environ['PROGRAMDATA'])/'Microsoft/Windows/Start Menu',Path(os.environ['USERPROFILE'])/'Desktop',Path(os.environ.get('PUBLIC',r'C:\Users\Public'))/'Desktop']
        for root in roots:
            if not root.is_dir(): continue
            for file in root.rglob('*'):
                try:
                    if file.suffix.lower()=='.lnk':
                        link=shell.CreateShortcut(str(file))
                        raw['apps'].append({'name':file.stem,'kind':'shortcut','source':str(file),'target':link.TargetPath,'arguments':link.Arguments,'working':link.WorkingDirectory})
                    elif file.suffix.lower()=='.url':
                        for line in file.read_text(encoding='utf-8-sig',errors='replace').splitlines():
                            if line.startswith('URL='):
                                raw['apps'].append({'name':file.stem,'kind':'protocol','source':str(file),'target':line[4:],'arguments':''}); break
                except Exception: warnings.append('No se pudo leer '+file.name)
        try:
            folder=win32com.client.Dispatch('Shell.Application').NameSpace('shell:AppsFolder')
            for item in folder.Items():
                aid=item.ExtendedProperty('System.AppUserModel.ID') or item.Path
                resolved=item.ExtendedProperty('System.Link.TargetParsingPath')
                raw['apps'].append({'name':item.Name,'kind':'shell','source':str(aid),'target':str(aid),'arguments':'','resolvedTarget':str(resolved) if resolved and safe_executable(str(resolved)) else '', 'blockedResolvedTarget':blocked_shell_target(aid,resolved)})
        except Exception: warnings.append('No se pudo completar el catálogo del menú Inicio.')
    finally:
        pythoncom.CoUninitialize()
    apps=normalize_inventory(raw)
    libraries=[]
    steam=next((Path(a['target']).parent for a in apps if folded(a['name'])=='steam' and safe_executable(a['target'])),None)
    if steam:
        libraries.append(steam)
        config=steam/'steamapps/libraryfolders.vdf'
        if config.is_file():
            for entry in re.findall(r'"path"\s+"([^"]+)"',config.read_text(encoding='utf-8',errors='replace')):
                path=Path(entry.replace('\\\\','\\'))
                if path.is_absolute() and not str(path).startswith('\\\\'):libraries.append(path)
    for app in apps:
        if app['kind']=='protocol' and app['target'].startswith('steam://'):
            aid=app['target'].rstrip('/').split('/')[-1]
            for library in libraries:
                manifest=library/'steamapps'/('appmanifest_'+aid+'.acf')
                if not manifest.is_file():continue
                text=manifest.read_text(encoding='utf-8',errors='replace')
                ident=re.search(r'"appid"\s+"(\d+)"',text);directory=re.search(r'"installdir"\s+"([^"]+)"',text)
                if not ident or ident[1]!=aid or not directory:continue
                base=(library/'steamapps/common').resolve();installed=(base/directory[1]).resolve()
                if installed.is_relative_to(base) and installed.is_dir():app['installedRoot']=str(installed);break
            app['available']=bool(app.get('installedRoot'))
    for app in apps:
        target=os.path.normcase(app.get('resolvedTarget') or app['target'])
        variants={a.get('arguments','') for a in apps if os.path.normcase(a.get('resolvedTarget') or a['target'])==target}
        app['sharedExecutable']=len(variants)>1
    return apps,warnings

def validate_url(value):
    if not isinstance(value, str) or len(value) > 2048 or any(c in value for c in '\r\n\t\x00"<>') or '\\' in value:
        raise ValueError('La URL no es válida.')
    value = value.strip()
    if not value:
        return ''
    if '://' not in value:
        value = 'https://' + value
    try:
        parts = urlsplit(value)
        if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password or parts.hostname.startswith('-'):
            raise ValueError()
        _ = parts.port
    except ValueError:
        raise ValueError('Usa una dirección http:// o https://, sin contraseñas.') from None
    return value

def launch(app, url=''):
    url = validate_url(url)
    target = app['target']
    if url:
        if not app['browser'] or not safe_executable(target):
            raise ValueError('Esta aplicación no tiene un navegador compatible para abrir URLs.')
        subprocess.Popen([target, url], cwd=str(Path(target).parent), close_fds=True)
    elif app['kind'] in ('shortcut','manual'):
        if not safe_executable(target):
            raise ValueError('La aplicación cambió de ubicación. Sincroniza el catálogo.')
        if app['kind'] == 'shortcut':
            # Re-read the observed shortcut before invoking it, so it cannot silently
            # become an arbitrary script or a different executable after discovery.
            actual = shortcut_target(app['source'])
            if os.path.normcase(actual) != os.path.normcase(target):
                raise ValueError('El acceso directo cambió. Sincroniza antes de abrirlo.')
            os.startfile(app['source'])
        else:
            subprocess.Popen([target], cwd=str(Path(target).parent), close_fds=True)
    elif app['kind'] == 'protocol':
        if not target.startswith(('steam://','com.epicgames.launcher://apps/')):
            raise ValueError('Protocolo no compatible.')
        os.startfile(target)
    else:
        subprocess.Popen([str(SYSTEM.parent / 'explorer.exe'), 'shell:AppsFolder\\' + target], creationflags=HIDDEN)
    return {'status':'submitted','message':'Solicitud enviada a Windows: ' + app['name']}

def shortcut_target(path):
    import pythoncom,win32com.client
    pythoncom.CoInitialize()
    try:
        if not Path(path).is_file(): raise ValueError('El acceso directo ya no existe.')
        return win32com.client.Dispatch('WScript.Shell').CreateShortcut(path).TargetPath
    finally: pythoncom.CoUninitialize()

if os.name == 'nt':
    user32 = C.WinDLL('user32', use_last_error=True)
    kernel32 = C.WinDLL('kernel32', use_last_error=True)
    user32.FindWindowW.argtypes = [W.LPCWSTR,W.LPCWSTR]
    user32.FindWindowW.restype = W.HWND
    user32.GetWindowThreadProcessId.argtypes = [W.HWND,C.POINTER(W.DWORD)]
    user32.SendMessageTimeoutW.argtypes = [W.HWND,W.UINT,C.c_size_t,C.c_ssize_t,W.UINT,W.UINT,C.POINTER(C.c_size_t)]
    user32.SendMessageTimeoutW.restype = C.c_ssize_t
    user32.PostMessageW.argtypes = [W.HWND,W.UINT,C.c_size_t,C.c_ssize_t]
    kernel32.OpenProcess.argtypes = [W.DWORD,W.BOOL,W.DWORD]
    kernel32.OpenProcess.restype = W.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)]
    kernel32.CloseHandle.argtypes = [W.HANDLE]

def aimp_handle(apps):
    hwnd = user32.FindWindowW('AIMP2_RemoteInfo', 'AIMP2_RemoteInfo')
    if not hwnd:
        return None
    pid = W.DWORD()
    user32.GetWindowThreadProcessId(hwnd, C.byref(pid))
    handle = kernel32.OpenProcess(0x1000,False,pid.value)
    if not handle:
        return None
    try:
        size=W.DWORD(32768); buffer=C.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle,0,buffer,C.byref(size)):
            return None
        expected = [a['target'] for a in apps if folded(a['name'])=='aimp' and safe_executable(a['target'])]
        if not any(os.path.normcase(p)==os.path.normcase(buffer.value) for p in expected):
            return None
    finally:
        kernel32.CloseHandle(handle)
    return hwnd

def aimp_property(hwnd, prop, value=0, write=False):
    output=C.c_size_t()
    ok=user32.SendMessageTimeoutW(hwnd,0x477,prop | int(write),value,2,700,C.byref(output))
    if not ok:
        raise RuntimeError('AIMP no respondió a tiempo.')
    return output.value

def aimp_track_marker(hwnd):
    # Only the main form belonging to the already validated AIMP process.
    import win32gui,win32process,hashlib
    pid=win32process.GetWindowThreadProcessId(hwnd)[1];found=[]
    def visit(window,_):
        try:
            if win32gui.GetClassName(window)=='TAIMPMainForm' and win32process.GetWindowThreadProcessId(window)[1]==pid:found.append(win32gui.GetWindowText(window))
        except OSError:pass
    win32gui.EnumWindows(visit,None)
    if len(found)!=1 or not found[0]:raise RuntimeError('No se pudo identificar la pista de AIMP. Abre su ventana y vuelve a comprobar.')
    return hashlib.sha256(found[0].encode('utf-8')).hexdigest()

def aimp_snapshot(apps):
    hwnd = aimp_handle(apps)
    if not hwnd:
        return {'aimp':False,'state':'unknown','label':'Reproductor de Windows'}
    try:
        return {'aimp':True,'state':{0:'stopped',1:'paused',2:'playing'}.get(aimp_property(hwnd,0x40),'unknown'),
                'volume':aimp_property(hwnd,0x50),'mute':bool(aimp_property(hwnd,0x60)),'position':aimp_property(hwnd,0x20),'duration':aimp_property(hwnd,0x30),'label':'AIMP'}
    except RuntimeError:
        return {'aimp':False,'state':'unknown','label':'AIMP no responde'}

def preferred_media(snapshot):
    if snapshot.get('sessionError'):return 'unavailable'
    if any(p.get('ambiguous') for p in snapshot.get('players',[])):return 'ambiguous'
    tidal=snapshot.get('tidal',{})
    playing=(['tidal'] if tidal.get('state')=='playing' else [])+(['aimp'] if snapshot.get('aimp') and snapshot.get('state')=='playing' else [])
    playing += [p['id'] for p in snapshot.get('players',[]) if p.get('state')=='playing']
    if len(playing)>1:return 'ambiguous'
    if playing:return playing[0]
    if tidal.get('running'):return 'tidal'
    if snapshot.get('aimp'):return 'aimp'
    if len(snapshot.get('players',[]))==1:return snapshot['players'][0]['id']
    if snapshot.get('players'):return 'ambiguous'
    return 'system'

def media_snapshot(apps,*,fresh=False):
    from companion import tidal,media_sessions
    result=aimp_snapshot(apps);result['tidal']=tidal.snapshot(apps,fresh=fresh)
    sessions=media_sessions.snapshot(apps,fresh=fresh);result['players']=sessions['players'];result['sessionError']=sessions.get('error','');result['autoTarget']=preferred_media(result)
    return result

def media(action, target, apps, value=None):
    actions={'previous':0xB1,'next':0xB0,'toggle':0xB3,'stop':0xB2,'volume_up':0xAF,'volume_down':0xAE,'mute':0xAD}
    from companion import media_sessions
    session=media_sessions.valid_target(target)
    if target not in ('system','windows','aimp','tidal') and not session:
        raise ValueError('Reproductor no válido.')
    playback=action in ('play','pause','toggle','stop','next','previous')
    if target=='tidal' and action in ('volume_up','volume_down','mute'):target='system'
    if target=='system' and playback:
        target=preferred_media(media_snapshot(apps,fresh=True))
        if target=='ambiguous':raise ValueError('Hay varios reproductores disponibles. Elige cuál controlar en Música.')
        if target=='unavailable':raise ValueError('No se pudo comprobar qué reproductor está activo. Elígelo directamente en Música.')
    if media_sessions.valid_target(target):
        if not playback:raise ValueError('Usa los controles de volumen general de Windows.')
        return media_sessions.control(action,target)
    if target=='tidal':
        if not playback:raise ValueError('Usa los botones de volumen de Windows para ajustar el sonido de TIDAL.')
        from companion import tidal
        return tidal.control(action,apps)
    if target=='aimp':
        hwnd=aimp_handle(apps)
        if not hwnd:
            raise ValueError('Abre AIMP en tu PC para controlarlo directamente.')
        initial=aimp_snapshot(apps)
        desired=None
        track=aimp_track_marker(hwnd) if action in ('next','previous') else None
        if action=='volume':
            if type(value)!=int or not 0<=value<=100:
                raise ValueError('Volumen no válido.')
            if not aimp_property(hwnd,0x50,value,True):
                raise RuntimeError('AIMP rechazó el volumen.')
        elif action=='mute':
            aimp_property(hwnd,0x60,int(not aimp_property(hwnd,0x60)),True)
        else:
            commands={'play':13,'pause':15,'toggle':14,'stop':16,'next':17,'previous':18}
            if action not in commands:
                raise ValueError('Control no compatible con AIMP.')
            effective=('pause' if initial['state']=='playing' else 'play') if action=='toggle' else action
            desired={'play':'playing','pause':'paused','stop':'stopped'}.get(effective)
            if desired and (initial['state']==desired or (effective=='pause' and initial['state']=='stopped')):
                return {'status':'completed','state':initial['state'],'verified':True,'invoked':False,'message':'AIMP ya estaba en ese estado.'}
            if not user32.PostMessageW(hwnd,0x475,commands[effective],0):
                raise RuntimeError('AIMP no aceptó el control.')
        if track:
            started=time.monotonic();until=started+4;stable=0;last_state=None
            while time.monotonic()<until:
                observed=aimp_snapshot(apps)
                changed=aimp_track_marker(hwnd)!=track
                restarted=action=='previous' and initial['position']>250 and observed.get('position',0)+100<initial['position']
                ready=observed['state']=='playing' or (initial['state']!='playing' and observed['state']=='paused' and time.monotonic()-started>=.75)
                stable=stable+1 if ready and (changed or restarted) and last_state==observed['state'] else 0
                last_state=observed['state']
                if stable>=3:return {'status':'completed','state':last_state,'verified':True,'invoked':True,'message':'AIMP terminó el cambio de pista o volvió al inicio.'}
                time.sleep(.15)
            raise RuntimeError('AIMP recibió el cambio de pista, pero no terminó de confirmarlo. Espera y revisa antes de repetir.')
        until=time.monotonic()+3.5;stable=0
        while desired and time.monotonic()<until:
            observed=aimp_snapshot(apps)
            stable=stable+1 if observed['state']==desired else 0
            if stable>=2:return {'status':'completed','state':desired,'verified':True,'invoked':True,'message':{'playing':'AIMP está reproduciendo.','paused':'AIMP quedó en pausa.','stopped':'AIMP quedó detenido.'}[desired]}
            time.sleep(.15)
        if desired:raise RuntimeError('AIMP recibió la orden, pero su estado no quedó confirmado. Revísalo antes de repetir.')
    elif action in actions:
        key=actions[action]
        user32.keybd_event(key,0,0,0)
        user32.keybd_event(key,0,2,0)
    else:
        raise ValueError('Control multimedia no válido.')
    return {'status':'submitted','message':'Control enviado a ' + ('AIMP' if target=='aimp' else 'Windows')+(' · el cambio del reproductor no se ha verificado.' if playback else '')}

def power(action):
    if action in ('shutdown','restart'):
        # Timeout 0 deliberately avoids shutdown /t > 0, which implies /f.
        # The cancellable countdown happens in our app before this call.
        result=subprocess.run([str(SYSTEM/'shutdown.exe'),'/s' if action=='shutdown' else '/r','/t','0'],capture_output=True,creationflags=HIDDEN,timeout=10)
        if result.returncode:
            raise RuntimeError('Windows rechazó la orden de energía.')
    elif action=='sleep':
        enable_shutdown_privilege()
        lib=C.WinDLL('powrprof',use_last_error=True)
        lib.SetSuspendState.argtypes=[C.c_ubyte,C.c_ubyte,C.c_ubyte]
        lib.SetSuspendState.restype=C.c_ubyte
        if not lib.SetSuspendState(False,False,False):
            raise RuntimeError('Windows no pudo suspender el equipo.')
    elif action=='lock':
        if not user32.LockWorkStation():
            raise RuntimeError('Windows no pudo bloquear la sesión.')
    else:
        raise ValueError('Acción de energía no válida.')

def enable_shutdown_privilege():
    class LUID(C.Structure): _fields_=[('LowPart',W.DWORD),('HighPart',W.LONG)]
    class PRIVILEGES(C.Structure): _fields_=[('Count',W.DWORD),('Luid',LUID),('Attributes',W.DWORD)]
    advapi=C.WinDLL('advapi32',use_last_error=True)
    advapi.OpenProcessToken.argtypes=[W.HANDLE,W.DWORD,C.POINTER(W.HANDLE)]
    advapi.LookupPrivilegeValueW.argtypes=[W.LPCWSTR,W.LPCWSTR,C.POINTER(LUID)]
    advapi.AdjustTokenPrivileges.argtypes=[W.HANDLE,W.BOOL,C.POINTER(PRIVILEGES),W.DWORD,C.c_void_p,C.c_void_p]
    kernel32.GetCurrentProcess.restype=W.HANDLE
    token=W.HANDLE(); privileges=PRIVILEGES(); privileges.Count=1; privileges.Attributes=2
    if not advapi.OpenProcessToken(kernel32.GetCurrentProcess(),0x28,C.byref(token)):
        raise RuntimeError('No se pudo solicitar la suspensión a Windows.')
    try:
        if not advapi.LookupPrivilegeValueW(None,'SeShutdownPrivilege',C.byref(privileges.Luid)):
            raise RuntimeError('Windows no admite el permiso de suspensión.')
        C.set_last_error(0)
        if not advapi.AdjustTokenPrivileges(token,False,C.byref(privileges),0,None,None) or C.get_last_error():
            raise RuntimeError('Tu sesión no tiene permiso para suspender Windows.')
    finally:
        kernel32.CloseHandle(token)
