"""Windows tray and pairing window; no elevated daemon and no cloud services."""
import argparse, json, logging, os, subprocess, sys, threading, time, tkinter as tk, webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlencode
from PIL import Image, ImageDraw, ImageTk
import pystray, qrcode
from companion.core import Deck, start, atomic_json, VERSION
from companion import windows

def resource_root():
    return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))

def executable_command():
    if getattr(sys,'frozen',False): return [sys.executable]
    return [sys.executable,str(resource_root()/'run.py')]

def configure_startup(enabled):
    import pythoncom,win32com.client
    path=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/Startup/Eddy Deck.lnk'
    if not enabled:
        path.unlink(missing_ok=True);return
    pythoncom.CoInitialize()
    try:
        command=executable_command();shell=win32com.client.Dispatch('WScript.Shell');link=shell.CreateShortcut(str(path))
        link.TargetPath=command[0];link.Arguments=subprocess.list2cmdline(command[1:]+['--tray']);link.WorkingDirectory=str(Path(command[0]).parent);link.Save()
    finally:link=None;shell=None;pythoncom.CoUninitialize()

class Desktop:
    def __init__(self,deck,hidden=False):
        self.deck=deck
        self.root=tk.Tk(); self.root.title('Eddy Deck · Conexión con tu celular')
        x=max(20,(self.root.winfo_screenwidth()-640)//2)
        y=max(20,(self.root.winfo_screenheight()-830)//2)
        height=min(1000,max(650,self.root.winfo_screenheight()-120))
        self.root.geometry(f'680x{height}+{x}+20'); self.root.minsize(620,500); self.root.configure(bg='#f7f4ee')
        try: self.root.iconbitmap(str(deck.resources/'ui'/'app.ico'))
        except tk.TclError: pass
        style=ttk.Style(); style.theme_use('clam')
        style.configure('TFrame',background='#f7f4ee')
        style.configure('TLabel',background='#f7f4ee',foreground='#272b30',font=('Segoe UI',11))
        style.configure('TButton',font=('Segoe UI',10),padding=9)
        canvas=tk.Canvas(self.root,bg='#f7f4ee',highlightthickness=0)
        scrollbar=ttk.Scrollbar(self.root,orient='vertical',command=canvas.yview);scrollbar.pack(side='right',fill='y')
        canvas.configure(yscrollcommand=scrollbar.set);canvas.pack(fill='both',expand=True)
        frame=ttk.Frame(canvas,padding=24);item=canvas.create_window((0,0),window=frame,anchor='nw')
        frame.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
        self.root.bind('<MouseWheel>',lambda e:canvas.yview_scroll(int(-e.delta/120),'units'))
        ttk.Label(frame,text='Eddy Deck',font=('Segoe UI Semibold',27)).pack(anchor='w')
        ttk.Label(frame,text='Tu computadora, a un toque.',foreground='#777b80').pack(anchor='w',pady=(0,14))
        self.status=ttk.Label(frame,text='● Preparando catálogo de aplicaciones…',foreground='#248565'); self.status.pack(anchor='w')
        row=ttk.Frame(frame); row.pack(fill='x',pady=12)
        ttk.Button(row,text='Abrir mi panel',command=self.open_panel).pack(side='left',fill='x',expand=True,padx=(0,8))
        ttk.Button(row,text='Agregar app portable',command=self.add_manual).pack(side='left',fill='x',expand=True)
        support=ttk.Frame(frame);support.pack(fill='x')
        ttk.Button(support,text='Reiniciar conexión',command=self.repair).pack(side='left',fill='x',expand=True)
        ttk.Button(support,text='Reparar archivos',command=self.repair_files).pack(side='left',fill='x',expand=True)
        ttk.Button(support,text='Guardar informe',command=self.report).pack(side='left',fill='x',expand=True)
        ttk.Separator(frame).pack(fill='x',pady=8)
        ttk.Label(frame,text='Conecta tu Android',font=('Segoe UI Semibold',15)).pack(anchor='w',pady=(8,4))
        ips=', '.join(deck.addresses) or 'Conecta la PC a tu red local'
        self.ip_label=ttk.Label(frame,text='Dirección de la PC: '+ips); self.ip_label.pack(anchor='w')
        self.fp_label=ttk.Label(frame,text='Huella: '+deck.fingerprint[:8].upper(),foreground='#777b80'); self.fp_label.pack(anchor='w',pady=3)
        self.pin_label=ttk.Label(frame,text='',font=('Consolas',23)); self.pin_label.pack()
        self.qr_label=ttk.Label(frame); self.qr_label.pack(pady=4)
        self.pin_status=ttk.Label(frame,text='',foreground='#777b80',font=('Segoe UI',9)); self.pin_status.pack()
        controls=ttk.Frame(frame); controls.pack(fill='x',pady=8)
        ttk.Button(controls,text='Nuevo código',command=self.new_pin).pack(side='left',expand=True,fill='x',padx=(0,6))
        ttk.Button(controls,text='Copiar enlace',command=self.copy_link).pack(side='left',expand=True,fill='x',padx=6)
        ttk.Button(controls,text='Activar Wi-Fi',command=self.wifi).pack(side='left',expand=True,fill='x',padx=6)
        ttk.Button(controls,text='USB',command=self.connect_usb).pack(side='left',expand=True,fill='x',padx=(6,0))
        self.startup=tk.BooleanVar(value=self.startup_exists())
        ttk.Checkbutton(frame,text='Iniciar Eddy Deck al entrar a Windows',variable=self.startup,command=self.set_startup).pack(anchor='w',pady=5)
        ttk.Button(frame,text='Internet con Tailscale · ayuda y conexión',command=lambda:webbrowser.open('https://tailscale.com/download')).pack(anchor='w')
        ttk.Button(frame,text='Activar internet · permiso de firewall',command=lambda:self.wifi(internet=True)).pack(anchor='w')
        ttk.Label(frame,text='Escanea el QR con la cámara del celular, o usa Buscar PC\ny escribe el código. La primera conexión requiere la app Android.',font=('Segoe UI',9),foreground='#777b80').pack(anchor='w',pady=5)
        ttk.Label(frame,text='Al cerrar esta ventana, Eddy Deck queda junto al reloj.\nDesde su icono puedes detener la conexión.',font=('Segoe UI',9),foreground='#777b80').pack(anchor='w',pady=5)
        self.root.protocol('WM_DELETE_WINDOW',self.hide)
        img=Image.new('RGB',(64,64),'#3475ed'); d=ImageDraw.Draw(img)
        for x in (14,35):
            for y in (14,35): d.rounded_rectangle((x,y,x+15,y+15),radius=4,fill='#ffffff')
        self.tray=pystray.Icon('eddydeck',img,'Eddy Deck — control local',menu=pystray.Menu(
            pystray.MenuItem('Abrir panel',lambda:self.open_panel(),default=True),
            pystray.MenuItem('Conectar celular',lambda:self.root.after(0,self.show)),
            pystray.MenuItem('Cancelar apagado / suspensión',lambda:self.cancel_power()),
            pystray.MenuItem('Salir de Eddy Deck',lambda:self.root.after(0,self.quit))))
        threading.Thread(target=self.tray.run,daemon=True).start()
        self.new_pin(); self.root.after(1200,self.tick)
        if hidden: self.root.withdraw()

    def open_panel(self):
        webbrowser.open(f'http://127.0.0.1:{self.deck.local_port}/#token='+self.deck.local_token)
    def repair(self):
        if not messagebox.askyesno('Reparar Eddy Deck','Se cancelan las rutinas pendientes y se reinicia el receptor. Las otras aplicaciones permanecen abiertas. ¿Continuar?'):return
        try:self.deck.dispatch('/api/repair',{'requestId':__import__('uuid').uuid4().hex,'confirm':True},'local')
        except Exception as exc:messagebox.showerror('Eddy Deck',str(exc))
    def repair_files(self):
        from companion.integrity import CHECKER
        helper=self.deck.data/'Rescue'/CHECKER
        if not helper.is_file():
            messagebox.showerror('Eddy Deck','No hay copia local del comprobador. Abre el instalador o el descarga de GitHub.');return
        subprocess.Popen([str(helper),'--repair'],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    def report(self):
        from companion.diagnostics import report
        try:
            result=report(self.deck)
            messagebox.showinfo('Informe guardado',str(self.deck.data/'reports'/(result['id']+'.json')))
        except Exception as exc:messagebox.showerror('Eddy Deck',str(exc))
    def show(self): self.root.deiconify(); self.root.lift()
    def hide(self): self.root.withdraw()
    def cancel_power(self):
        with self.deck.lock: self.deck.pending=None
        self.deck.event('Acción de energía cancelada desde la PC')
    def new_pin(self): self.deck.renew_pin(); self.update_pairing()
    def pairing_link(self,usb=False):
        host='127.0.0.1' if usb else (self.deck.addresses[0] if self.deck.addresses else '127.0.0.1')
        params={'port':self.deck.port,'fp':self.deck.fingerprint,'pin':self.deck.pin or ''}
        if usb and self.deck.addresses: params['lan']=self.deck.addresses[0]
        return 'eddydeck://'+host+'?'+urlencode(params)
    def update_pairing(self):
        pin=self.deck.pin or '--------'
        self.pin_label.configure(text=pin[:4]+' '+pin[4:])
        if self.deck.pin:
            qr=qrcode.make(self.pairing_link()).convert('RGB').resize((208,208),Image.Resampling.NEAREST)
            self.qr=ImageTk.PhotoImage(qr); self.qr_label.configure(image=self.qr)
        else: self.qr_label.configure(image='')
    def copy_link(self):
        if not self.deck.pin or self.deck.pin_until<=time.monotonic(): self.new_pin()
        self.root.clipboard_clear(); self.root.clipboard_append(self.pairing_link())
    def connect_usb(self):
        import shlex
        base=Path(sys.executable).parent if getattr(sys,'frozen',False) else self.deck.resources
        adb=base/'usb'/'adb.exe'
        if not adb.exists():
            messagebox.showinfo('Conexión USB','Conserva la carpeta usb junto a EddyDeck.exe. Incluye las herramientas oficiales de Android.');return
        if not self.deck.pin or self.deck.pin_until<=time.monotonic(): self.new_pin()
        link=self.pairing_link(usb=True)
        def run_usb():
            try:
                result=subprocess.run([str(adb),'devices'],capture_output=True,text=True,creationflags=windows.HIDDEN,timeout=12)
                connected=[line.split()[0] for line in result.stdout.splitlines() if line.strip().endswith('\tdevice')]
                if len(connected)!=1:
                    raise RuntimeError('Conecta un solo Android por USB, desbloquéalo y acepta Permitir depuración USB si aparece.')
                serial=connected[0]
                reverse=subprocess.run([str(adb),'-s',serial,'reverse','tcp:47990','tcp:47990'],capture_output=True,creationflags=windows.HIDDEN,timeout=10)
                if reverse.returncode: raise RuntimeError('No se pudo preparar el enlace USB.')
                result=subprocess.run([str(adb),'-s',serial,'shell','am','start','--user','0','-a','android.intent.action.VIEW','-d',shlex.quote(link),'-n','com.eddy.deck/.MainActivity'],capture_output=True,text=True,creationflags=windows.HIDDEN,timeout=12)
                if result.returncode or 'Error' in result.stdout or 'Error' in result.stderr:raise RuntimeError('Instala Eddy Deck en el Android y vuelve a pulsar USB.')
                self.root.after(0,lambda:messagebox.showinfo('USB listo','Eddy Deck se abrió en tu celular. Si es la primera conexión, pulsa Conectar a mi PC. El código ya está rellenado.'))
            except Exception as exc:
                message=str(exc);self.root.after(0,lambda:messagebox.showinfo('Conexión USB',message))
        threading.Thread(target=run_usb,daemon=True).start()
    def tick(self):
        if self.deck.closed: return
        self.startup.set(self.startup_exists())
        self.ip_label.configure(text='Dirección de la PC: '+(', '.join(self.deck.addresses) or 'Sin red'))
        with self.deck.lock:
            count=len(self.deck.apps); devices=len(self.deck.devices); pending=self.deck.pending
            text=f'● {count} aplicaciones · {devices} celulares vinculados'
            recent=[s for s in self.deck.sessions.values() if s['at']>time.time()-25]
            if recent:text+=' · '+recent[-1]['via']+' activo'
            if self.deck.scanning: text='● Sincronizando aplicaciones…'
            if self.deck.warnings: text='● Catálogo disponible con avisos; revisa Biblioteca'
            if pending: text=f'● Energía: {pending["action"]} en {max(0,int(pending["deadline"]-time.monotonic()))} s'
            self.status.configure(text=text)
            if self.deck.pin and self.deck.pin_until<=time.monotonic(): self.deck.pin=None; self.update_pairing()
            if not self.deck.pin:
                self.pin_label.configure(text='Vinculación cerrada'); self.qr_label.configure(image='')
                self.pin_status.configure(text='Pulsa Nuevo código para vincular otro celular.')
            else:
                seconds=max(0,int(self.deck.pin_until-time.monotonic()))
                self.pin_status.configure(text=f'Código de un solo uso · vence en {seconds//60}:{seconds%60:02d}')
            atomic_json(self.deck.data/'runtime.json',{'pid':os.getpid(),'localPort':self.deck.local_port,'port':self.deck.port,'addresses':self.deck.addresses,'fingerprint':self.deck.fingerprint,'recentClients':recent,'monotonic':time.monotonic()})
        self.root.after(1500,self.tick)
    def add_manual(self):
        path=filedialog.askopenfilename(title='Elige el ejecutable de la aplicación',filetypes=[('Aplicación de Windows','*.exe')])
        if not path: return
        if not windows.safe_executable(path):
            messagebox.showerror('Aplicación no compatible','Elige el .exe de una aplicación normal, dentro de esta PC.'); return
        import hashlib
        name=Path(path).stem; group,symbol=windows.category(name,path)
        app={'id':hashlib.sha256(('manual:'+path.lower()).encode()).hexdigest()[:20],'name':name,'kind':'manual','source':path,'target':path,'category':group,'symbol':symbol,'browser':group=='Navegadores','available':True,'arguments':''}
        try:
            with self.deck.lock:
                updated=[a for a in self.deck.manual if a['id']!=app['id']]+[app]
                atomic_json(self.deck.data/'manual-apps.json',updated)
                self.deck.manual=updated
        except OSError:
            messagebox.showerror('No se pudo guardar','Comprueba el espacio y los permisos de la carpeta de Eddy Deck. La lista anterior se conservó.');return
        self.deck.start_scan(); messagebox.showinfo('Aplicación agregada','Ya puedes buscarla en Biblioteca y crear su botón.')
    def startup_path(self):
        return Path(os.environ['APPDATA'])/'Microsoft'/'Windows'/'Start Menu'/'Programs'/'Startup'/'Eddy Deck.lnk'
    def startup_exists(self): return self.startup_path().exists()
    def set_startup(self):
        path=self.startup_path()
        try:
            configure_startup(self.startup.get())
        except OSError as exc:
            self.startup.set(self.startup_exists()); messagebox.showerror('Inicio con Windows',str(exc))
    def wifi(self,internet=False):
        if not getattr(sys,'frozen',False):
            messagebox.showinfo('Wi-Fi','Usa el ejecutable instalado para crear una regla limitada a esta aplicación.'); return
        messagebox.showinfo('Permitir conexión','Windows pedirá permiso de administrador para permitir solamente Eddy Deck en '+('tu red privada de Tailscale.' if internet else 'tu red local.'))
        import ctypes
        result=ctypes.windll.shell32.ShellExecuteW(None,'runas',sys.executable,'--enable-internet' if internet else '--enable-wifi',None,0)
        if result<=32: messagebox.showinfo('Wi-Fi','La regla no se pudo crear o cancelaste el aviso. El modo USB sigue disponible.')
    def quit(self):
        self.cancel_power(); self.tray.stop()
        threading.Thread(target=self.deck.close,daemon=True).start(); self.root.destroy()
    def run(self): self.root.mainloop()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--tray',action='store_true'); parser.add_argument('--headless',action='store_true')
    parser.add_argument('--dry-run',action='store_true'); parser.add_argument('--data',type=Path)
    parser.add_argument('--enable-wifi',action='store_true')
    parser.add_argument('--enable-internet',action='store_true')
    parser.add_argument('--install',action='store_true')
    parser.add_argument('--install-silent',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--validate-profile',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--restore-profile',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.validate_profile:
        from companion.installer import read_profile_backup
        read_profile_backup(args.validate_profile);return
    if args.restore_profile and not args.install_silent:parser.error('--restore-profile solo se admite en el comprobador de instalación.')
    if args.install_silent:
        from companion.installer import install_from,read_profile_backup,restore_profile_backup
        if args.restore_profile:read_profile_backup(args.restore_profile)
        target=install_from(Path(sys.executable).parent)
        if args.restore_profile:
            from companion.storage import prepare_data
            restore_profile_backup(args.restore_profile,prepare_data())
        subprocess.Popen([str(target/'EddyDeck.exe'),'--tray'],creationflags=windows.HIDDEN);return
    if args.install:
        from companion.installer import main as install_main
        install_main();return
    if args.enable_wifi or args.enable_internet:
        import ctypes
        if not getattr(sys,'frozen',False) or not ctypes.windll.shell32.IsUserAnAdmin():
            messagebox.showerror('Eddy Deck','Esta opción requiere el ejecutable instalado y el permiso de Windows.'); return
        try:
            for protocol,port in ([('TCP',47990)] if args.enable_internet else [('TCP',47990),('UDP',47991)]):
                name=('Eddy Deck Tailscale ' if args.enable_internet else 'Eddy Deck local ')+protocol
                subprocess.run([str(windows.SYSTEM/'netsh.exe'),'advfirewall','firewall','delete','rule','name='+name,'program='+sys.executable],creationflags=windows.HIDDEN,capture_output=True,timeout=15)
                result=subprocess.run([str(windows.SYSTEM/'netsh.exe'),'advfirewall','firewall','add','rule','name='+name,'dir=in','action=allow','program='+sys.executable,'protocol='+protocol,'localport='+str(port),'remoteip='+('100.64.0.0/10' if args.enable_internet else 'localsubnet'),'profile=any'],creationflags=windows.HIDDEN,capture_output=True,timeout=15)
                if result.returncode: raise RuntimeError('Windows no pudo crear la regla '+protocol)
            messagebox.showinfo('Eddy Deck','Permiso listo para '+('Tailscale. Inicia sesión con la misma cuenta en ambos equipos.' if args.enable_internet else 'Wi-Fi. Conecta ambos equipos a la misma red.'))
        except Exception as exc: messagebox.showerror('Eddy Deck',str(exc))
        return
    from companion.storage import prepare_data
    data=args.data or prepare_data()
    from companion.ownership import receiver_lease
    with receiver_lease(data) as owned:
        if not owned:
            try:
                with __import__('socket').create_connection(('127.0.0.1',47988),timeout=.5) as connection:connection.sendall(b'SHOW_EDDY_DECK')
            except OSError:pass
            return
        return run_receiver(args,data)

def run_receiver(args,data):
    data.mkdir(parents=True,exist_ok=True)
    # Check a running receiver before constructing Deck: opening a second copy
    # must never mark the first copy's pending journal entries interrupted.
    try:
        with __import__('socket').create_connection(('127.0.0.1',47988),timeout=.5) as connection:
            connection.sendall(b'SHOW_EDDY_DECK');return
    except OSError:pass
    # A previous headless release has no activation socket or ownership file.
    # Detect its receiver before Journal recovery can touch its live work.
    try:
        import urllib.request,urllib.error,json
        with urllib.request.urlopen('http://127.0.0.1:47989/health',timeout=1) as response:
            if json.loads(response.read(4096)).get('name')=='Eddy Deck':return
    except urllib.error.HTTPError as response:
        try:
            if response.code==503 and json.loads(response.read(4096)).get('name')=='Eddy Deck':return
        except (OSError,ValueError,AttributeError):pass
        finally:response.close()
    except (OSError,ValueError,AttributeError):pass
    from logging.handlers import RotatingFileHandler
    handler=RotatingFileHandler(data/'eddydeck.log',maxBytes=512000,backupCount=2,encoding='utf-8')
    logging.basicConfig(level=logging.INFO,handlers=[handler],format='%(asctime)s %(levelname)s %(message)s')
    deck=None
    try:
        try:
            deck=Deck(data,resource_root(),dry_run=args.dry_run)
            start(deck)
            run_started_receiver(args,data,deck)
        finally:
            # Release sockets, queue and keep-awake before a dialog can wait
            # for a person. Initialization errors must not leave a live worker.
            if deck is not None:deck.close()
    except Exception as exc:
        logging.exception('No se pudo iniciar o continuar Eddy Deck.')
        detail=str(exc) if isinstance(exc,RuntimeError) else 'Revisa eddydeck.log y conserva la carpeta de datos antes de reparar.'
        if isinstance(exc,OSError) and (exc.errno in (48,98,10048) or getattr(exc,'winerror',None)==10048):
            detail='Otro programa utiliza uno de los puertos de Eddy Deck. Cierra solo la otra copia de Eddy Deck, si existe, y vuelve a intentar.'
        if args.headless:raise
        messagebox.showerror('Eddy Deck','No se pudo iniciar o continuar la aplicación.\n\n'+detail)


def run_started_receiver(args,data,deck):
    from companion.awake import start_receiver_guard
    deck.awake=start_receiver_guard(args.dry_run)
    deck.start_scan()
    if args.headless:
        deck.renew_pin()
        atomic_json(data/'test-runtime.json',{'localToken':deck.local_token,'pin':deck.pin,'fingerprint':deck.fingerprint,'port':deck.port,'localPort':deck.local_port})
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt: pass
        return
    desktop=Desktop(deck,args.tray)
    def activation():
        import socket
        with socket.socket() as server:
            try: server.bind(('127.0.0.1',47988)); server.listen(3); server.settimeout(1)
            except OSError: return
            while not deck.closed:
                try:
                    conn,_=server.accept()
                    with conn:
                        conn.settimeout(1)
                        if conn.recv(32)==b'SHOW_EDDY_DECK': desktop.root.after(0,desktop.show)
                except (OSError,TimeoutError): continue
    threading.Thread(target=activation,daemon=True).start()
    desktop.run()

if __name__=='__main__': main()
