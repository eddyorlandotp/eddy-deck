// Independent .NET Framework bootstrapper: does not need the bundled Python.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

class Compatibility : Form {
    const string VersionName="@@VERSION@@",Modulus="@@MODULUS@@";
    CancellationTokenSource downloadCancel; bool downloading, closingDownload; string downloadedSource;
    static string Data=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),".eddydeck");
    static string Installed=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","EddyDeck");
    static string DownloadRoot=Path.Combine(Data,"update-staging");
    static JavaScriptSerializer Json=new JavaScriptSerializer {MaxJsonLength=2000000};
    string source=AppDomain.CurrentDomain.BaseDirectory;TextBox status=new TextBox();
    Dictionary<string,object> last;
    static string Hash(byte[] b){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(b)).Replace("-","").ToLowerInvariant();}
    static bool Confined(string folder,string file){return Path.GetFullPath(file).StartsWith(Path.GetFullPath(folder).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase);}
    static bool SafeName(string name){return !String.IsNullOrEmpty(name)&&!Path.IsPathRooted(name)&&!name.Contains("\\")&&!name.Contains(":")&&!name.Split('/').Any(x=>String.IsNullOrEmpty(x)||x==".."||x.EndsWith(".")||x.EndsWith(" "));}
    static Dictionary<string,object> Header(byte[] raw,string signature){
        if(raw.Length>2000000||signature.Length>2048)throw new Exception("Manifiesto demasiado grande.");
        using(var rsa=new RSACryptoServiceProvider()){
            rsa.PersistKeyInCsp=false;rsa.ImportParameters(new RSAParameters {Modulus=Convert.FromBase64String(Modulus),Exponent=new byte[]{1,0,1}});
            if(!rsa.VerifyData(raw,CryptoConfig.MapNameToOID("SHA256"),Convert.FromBase64String(signature.Trim())))throw new Exception("La firma no corresponde a Eddy Deck. Descarga una copia del respaldo.");
        }
        var m=Json.Deserialize<Dictionary<string,object>>(Encoding.UTF8.GetString(raw));
        if(Convert.ToInt32(m["schema"])!=1||Convert.ToString(m["architecture"])!="x64")throw new Exception("Paquete incompatible con este comprobador.");
        return m;
    }
    static Dictionary<string,object> Verify(string folder){
        var m=Header(File.ReadAllBytes(Path.Combine(folder,"release-manifest.json")),File.ReadAllText(Path.Combine(folder,"release-manifest.sig")));
        var files=(Dictionary<string,object>)m["files"];
        if(files.Count==0||files.Count>5000)throw new Exception("Lista de archivos inválida.");
        foreach(var row in files){
            if(!SafeName(row.Key))throw new Exception("El paquete contiene una ruta inválida.");
            string path=Path.Combine(folder,row.Key.Replace('/',Path.DirectorySeparatorChar));
            if(!Confined(folder,path))throw new Exception("Ruta fuera de la carpeta.");
            string walk=path;
            while(Confined(folder,walk)){
                if((File.GetAttributes(walk)&FileAttributes.ReparsePoint)!=0)throw new Exception("El paquete contiene un enlace de archivos.");
                walk=Path.GetDirectoryName(walk);
            }
            var item=(Dictionary<string,object>)row.Value;
            long size=Convert.ToInt64(item["size"]);if(size<0||size>500000000)throw new Exception("Tamaño de archivo inválido.");
            if(!File.Exists(path)||new FileInfo(path).Length!=Convert.ToInt64(item["size"])||Hash(File.ReadAllBytes(path))!=Convert.ToString(item["sha256"]))throw new Exception("Falta un archivo o cambió: "+row.Key);
        }
        // Reject extra executable/code files; never load a mixed installation.
        foreach(string path in Directory.GetFiles(folder,"*",SearchOption.AllDirectories)){
            string name=path.Substring(Path.GetFullPath(folder).TrimEnd('\\').Length+1).Replace('\\','/');
            if(name!="release-manifest.json"&&name!="release-manifest.sig"&&!files.ContainsKey(name))throw new Exception("Hay archivos ajenos en la carpeta. Extrae el ZIP en una carpeta nueva.");
        }
        return m;
    }
    static Dictionary<string,object> SystemReport(){
        int build=0;using(var k=Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Windows NT\CurrentVersion")){Int32.TryParse(Convert.ToString(k==null?null:k.GetValue("CurrentBuildNumber")),out build);}
        string arch=Environment.GetEnvironmentVariable("PROCESSOR_ARCHITEW6432")??Environment.GetEnvironmentVariable("PROCESSOR_ARCHITECTURE")??"unknown";
        bool compatible=Environment.Is64BitOperatingSystem&&build>=22000;
        return new Dictionary<string,object>{{"checkerVersion",VersionName},{"windowsBuild",build},{"architecture",arch},{"windows11Compatible",compatible},{"framework",Environment.Version.ToString()},{"screenCount",Screen.AllScreens.Length},{"screenSizes",Screen.AllScreens.Select(s=>s.Bounds.Width+"x"+s.Bounds.Height).ToArray()},{"armEmulationWarning",arch.IndexOf("ARM",StringComparison.OrdinalIgnoreCase)>=0},{"at",DateTime.UtcNow.ToString("o")}};
    }
    static void SaveReport(Dictionary<string,object> report,string path=null){
        if(path==null){string folder=Path.Combine(Data,"installer-reports");Directory.CreateDirectory(folder);path=Path.Combine(folder,DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff")+".json");}
        File.WriteAllText(path,Json.Serialize(report),new UTF8Encoding(false));
    }
    static string CachedSource(){
        string cache=Path.Combine(Data,"recovery",VersionName+".zip");
        string dest=Path.Combine(Data,"repair-staging",Guid.NewGuid().ToString("N"));
        using(var z=ZipFile.OpenRead(cache)){
            if(z.Entries.Count>5000||z.Entries.Sum(e=>e.Length)>500000000)throw new Exception("Copia de reparación demasiado grande.");
            foreach(var e in z.Entries)if(!SafeName(e.FullName)||!Confined(dest,Path.Combine(dest,e.FullName)))throw new Exception("Ruta inválida en la copia de reparación.");
            var manifest=z.GetEntry("release-manifest.json");var sig=z.GetEntry("release-manifest.sig");
            if(manifest==null||sig==null||manifest.Length>2000000||sig.Length>2048)throw new Exception("Copia sin firma válida.");
            using(var a=manifest.Open())using(var b=sig.Open())using(var ms=new MemoryStream())using(var reader=new StreamReader(b)){
                a.CopyTo(ms);var m=Header(ms.ToArray(),reader.ReadToEnd());
                if(Convert.ToString(m["version"])!=VersionName)throw new Exception("La copia corresponde a otra versión.");
            }
            Directory.CreateDirectory(dest);
            foreach(var e in z.Entries){string file=Path.Combine(dest,e.FullName);Directory.CreateDirectory(Path.GetDirectoryName(file));e.ExtractToFile(file);}
        }
        Verify(dest);return dest;
    }
    static void StopInstalled(){
        string expected=Path.Combine(Installed,"EddyDeck.exe");
        var found=new List<Process>();
        foreach(var p in Process.GetProcessesByName("EddyDeck")){try{if(String.Equals(p.MainModule.FileName,expected,StringComparison.OrdinalIgnoreCase)){IntPtr h=p.Handle;found.Add(p);}else p.Dispose();}catch{p.Dispose();}}
        // The supervisor starts first. Stop it before its worker to avoid respawn.
        foreach(var p in found.OrderBy(p=>{try{return p.StartTime;}catch{return DateTime.MaxValue;}}))using(p){
            try{if(!String.Equals(p.MainModule.FileName,expected,StringComparison.OrdinalIgnoreCase))continue;
                // Open and retain this process handle before checking identity.
                IntPtr handle=p.Handle;DateTime created=p.StartTime;
                if(!String.Equals(p.MainModule.FileName,expected,StringComparison.OrdinalIgnoreCase)||p.HasExited)continue;
                p.Kill();if(!p.WaitForExit(10000))throw new Exception("Eddy Deck no pudo detenerse.");
            }catch(InvalidOperationException){}catch(System.ComponentModel.Win32Exception){throw new Exception("No se pudo detener Eddy Deck. Sal desde su icono y repite la instalación.");}
        }
        // A supervisor stopped after its worker may have briefly replaced it.
        foreach(var p in Process.GetProcessesByName("EddyDeck"))using(p){try{if(String.Equals(p.MainModule.FileName,expected,StringComparison.OrdinalIgnoreCase))throw new Exception("Eddy Deck sigue activo. Sal desde su icono y vuelve a intentarlo.");}catch(InvalidOperationException){}}
    }
    static void WaitOwned(Process child,int milliseconds,string message){
        if(child.WaitForExit(milliseconds))return;
        // This handle belongs to the child started by this checker, not an app
        // found by name. Never leave profile validation or an installer orphaned.
        try{child.Kill();}catch(InvalidOperationException){}
        if(!child.WaitForExit(10000))throw new Exception("El proceso de instalación no terminó. No repitas la operación; revisa su informe.");
        throw new Exception(message);
    }
    static void Install(string folder,string profile=null){
        using(var gate=new Mutex(false,"Local\\EddyDeck-Installation")){
            bool held=false;try{try{held=gate.WaitOne(0);}catch(AbandonedMutexException){held=true;}
                if(!held)throw new Exception("Otra instalación de Eddy Deck está trabajando. Espera a que termine.");
                InstallCore(folder,profile);
            }finally{if(held)gate.ReleaseMutex();}
        }
    }
    static void InstallCore(string folder,string profile=null){
        var report=SystemReport();
        try{
            if(!(bool)report["windows11Compatible"])throw new Exception("Este paquete necesita Windows 11 de 64 bits. No se instaló nada.");
            var m=Verify(folder);report["packageVersion"]=m["version"];report["integrityVerified"]=true;
            if(Convert.ToInt32(m["minWindowsBuild"])>Convert.ToInt32(report["windowsBuild"]))throw new Exception("Esta versión necesita una actualización de Windows. Consulta el respaldo o conserva la versión actual.");
            string currentManifest=Path.Combine(Installed,"release-manifest.json"),currentSignature=Path.Combine(Installed,"release-manifest.sig");
            if(File.Exists(currentManifest)&&File.Exists(currentSignature)){
                Dictionary<string,object> current=null;
                try{current=Header(File.ReadAllBytes(currentManifest),File.ReadAllText(currentSignature));}catch{report["previousManifestDamaged"]=true;}
                if(current!=null){
                    if(GitHubUpdate.Compare(Convert.ToString(m["version"]),Convert.ToString(current["version"]))<0)throw new Exception("Ya tienes una versión más reciente. Busca su paquete en GitHub para reparar sin retroceder de versión.");
                }
            }
            long total=((Dictionary<string,object>)m["files"]).Values.Sum(v=>Convert.ToInt64(((Dictionary<string,object>)v)["size"]));
            var drive=new DriveInfo(Path.GetPathRoot(Installed));if(drive.AvailableFreeSpace<total*3+134217728)throw new Exception("Falta espacio para instalar, conservar la versión anterior y preparar la recuperación.");
            if(String.Equals(Path.GetFullPath(folder).TrimEnd('\\'),Path.GetFullPath(Installed).TrimEnd('\\'),StringComparison.OrdinalIgnoreCase))folder=CachedSource();
            if(profile!=null){
                // Validate with the verified runtime before stopping the receiver.
                var validation=new ProcessStartInfo(Path.Combine(folder,"EddyDeck.exe"),"--validate-profile \""+profile+"\""){UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=folder};
                using(var p=Process.Start(validation)){WaitOwned(p,20000,"La comprobación del panel tardó demasiado y se detuvo. No se sustituyó el panel.");if(p.ExitCode!=0)throw new Exception("La copia de botones y rutinas no es válida. Elige el JSON exportado por Eddy Deck. No se sustituyó el panel.");}
            }
            StopInstalled();
            var start=new ProcessStartInfo(Path.Combine(folder,"EddyDeck.exe"),"--install-silent"+(profile==null?"":" --restore-profile \""+profile+"\"")){UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=folder};
            using(var p=Process.Start(start)){WaitOwned(p,300000,"La instalación superó cinco minutos y se detuvo. Revisa su informe y conserva la copia anterior para recuperar.");if(p.ExitCode!=0)throw new Exception("La instalación no pudo terminar. Revisa el informe y el espacio disponible; conserva la copia anterior.");}
            report["installed"]=true;report["profileRestored"]=profile!=null;SaveReport(report);
            string staging=Path.Combine(Data,"repair-staging");Guid stagingId;
            if(Confined(staging,folder)&&Path.GetDirectoryName(Path.GetFullPath(folder))==staging&&Guid.TryParse(Path.GetFileName(folder),out stagingId)){
                try{Directory.Delete(folder,true);}catch{/* The verified cache remains reusable; a locked staging file can be inspected later. */}
            }
        }catch(Exception e){report["installed"]=false;report["error"]=e.Message;SaveReport(report);throw;}
    }
    Compatibility(bool repair){
        Text="Eddy Deck · Compatibilidad y reparación";Width=760;Height=620;MinimumSize=new System.Drawing.Size(570,430);StartPosition=FormStartPosition.CenterScreen;
        if(repair)source="";
        var panel=new FlowLayoutPanel{Dock=DockStyle.Top,Height=145,Padding=new Padding(12),AutoScroll=true};
        status.Multiline=true;status.ReadOnly=true;status.ScrollBars=ScrollBars.Vertical;status.Dock=DockStyle.Fill;status.Font=new System.Drawing.Font("Segoe UI",11);status.Padding=new Padding(12);
        Action<string,Action> button=(name,action)=>{var b=new Button{Text=name,AutoSize=true,Height=38,Margin=new Padding(4)};b.Click+=(s,e)=>{try{if(downloading){status.Text="Hay una descarga en curso. Espera o cancélala.";return;}action();}catch(Exception ex){status.Text=ex.Message+"\r\n\r\nBusca la versión en GitHub o elige otra copia del celular.";}};panel.Controls.Add(b);};
        button("Comprobar este paquete",()=>Check());
        button("Elegir carpeta descargada",()=>{using(var d=new FolderBrowserDialog{Description="Carpeta donde extrajiste todo el ZIP de Eddy Deck"})if(d.ShowDialog()==DialogResult.OK){source=d.SelectedPath;Check();}});
        button("Instalar / reparar",()=>{
            if(MessageBox.Show("Se verificará el paquete y se sustituirán solo los archivos de Eddy Deck. Sus tareas pendientes se interrumpen; se conservan botones y vínculos. Las otras aplicaciones siguen abiertas.","Eddy Deck",MessageBoxButtons.OKCancel)!=DialogResult.OK)return;
            if(String.IsNullOrEmpty(source))source=CachedSource();
            Install(source);status.Text="Eddy Deck instalado y abierto. En el celular puedes conectar con el código de esta PC. Se guardó el informe de instalación.";
        });
        button("Buscar y descargar de GitHub",()=>Download());
        button("Abrir versiones en GitHub",()=>Process.Start(new ProcessStartInfo(GitHubUpdate.ReleasesUrl){UseShellExecute=true}));
        var cancel=new Button{Text="Cancelar descarga",AutoSize=true,Margin=new Padding(4)};cancel.Click+=(s,e)=>{if(downloadCancel!=null)downloadCancel.Cancel();};panel.Controls.Add(cancel);
        FormClosing+=(s,e)=>{if(downloading){e.Cancel=true;closingDownload=true;downloadCancel.Cancel();status.Text="Cancelando la descarga antes de cerrar…";}else CleanupDownload();};
        button("Restaurar botones y rutinas…",()=>{
            using(var d=new OpenFileDialog{Filter="Copia de Eddy Deck|*.json",CheckFileExists=true}){
                if(d.ShowDialog()!=DialogResult.OK)return;
                if(MessageBox.Show("Se comprobará tu copia y se reemplazarán los botones y rutinas. Se conserva una copia del archivo anterior, incluso si está dañado. No se cambian los permisos de celulares ni la identidad de esta PC.","Restaurar panel de Eddy Deck",MessageBoxButtons.OKCancel)!=DialogResult.OK)return;
                if(String.IsNullOrEmpty(source))source=CachedSource();Install(source,d.FileName);status.Text="Panel restaurado y Eddy Deck abierto. Revisa las aplicaciones disponibles antes de ejecutar rutinas.";
            }
        });
        button("Guardar informe",()=>{if(last==null)last=SystemReport();using(var d=new SaveFileDialog{Filter="Informe JSON|*.json",FileName="EddyDeck-compatibilidad.json"})if(d.ShowDialog()==DialogResult.OK)SaveReport(last,d.FileName);});
        Controls.Add(status);Controls.Add(panel);Shown+=(s,e)=>Check();
    }
    void CleanupDownload(){if(downloadedSource!=null){GitHubUpdate.Clean(Path.GetDirectoryName(downloadedSource),DownloadRoot);downloadedSource=null;}}
    string CurrentVersion(){
        string path=Path.Combine(Installed,"release-manifest.json");
        if(File.Exists(path)){try{var current=Header(File.ReadAllBytes(path),File.ReadAllText(Path.Combine(Installed,"release-manifest.sig")));string v=Convert.ToString(current["version"]);if(GitHubUpdate.Compare(v,VersionName)>0)return v;}catch{}}
        return VersionName;
    }
    async void Download(){
        if(downloading)return;downloading=true;downloadCancel=new CancellationTokenSource();downloadCancel.CancelAfter(300000);
        var token=downloadCancel.Token;string current=CurrentVersion();int build=Convert.ToInt32(SystemReport()["windowsBuild"]);
        Action<string> progress=text=>{if(!IsDisposed&&IsHandleCreated)BeginInvoke((Action)(()=>{if(!IsDisposed)status.Text=text;}));};
        try{
            string result=await Task.Run(()=>GitHubUpdate.Prepare(current,build,Modulus,DownloadRoot,token,progress,Verify));
            CleanupDownload();downloadedSource=result;source=result;Check();status.AppendText("\r\n\r\nDescarga verificada. Pulsa Instalar / reparar para aplicar esta versión.");
        }catch(OperationCanceledException){status.Text="Descarga cancelada. Tu instalación se conserva.";}
        catch(Exception ex){status.Text="No se pudo preparar la actualización: "+ex.Message;SaveReport(new Dictionary<string,object>{{"operation","github-update"},{"error",ex.Message}});}
        finally{downloading=false;downloadCancel.Dispose();downloadCancel=null;if(closingDownload)Close();}
    }
    void Check(){
        last=SystemReport();var sb=new StringBuilder("Comprobador Eddy Deck "+VersionName+"\r\n\r\n");
        sb.AppendLine("Windows: compilación "+last["windowsBuild"]+" · "+last["architecture"]);
        sb.AppendLine("Pantallas actuales: "+last["screenCount"]);
        if(!(bool)last["windows11Compatible"])sb.AppendLine("No compatible: se necesita Windows 11 de 64 bits.");
        if((bool)last["armEmulationWarning"])sb.AppendLine("Windows ARM: requiere emulación x64. No se ha probado físicamente en ARM.");
        try{if(String.IsNullOrEmpty(source)){sb.AppendLine("Reparación desde la copia local verificada. Pulsa Instalar / reparar.");}else{var m=Verify(source);last["integrityVerified"]=true;last["packageVersion"]=m["version"];sb.AppendLine("Paquete "+m["version"]+": firma y todos sus archivos correctos.");}}
        catch(Exception e){last["integrityVerified"]=false;last["error"]=e.Message;sb.AppendLine("No se debe instalar esta copia: "+e.Message);}
        sb.AppendLine("\r\nEl paquete incluye Python y sus bibliotecas. GitHub ofrece las versiones públicas sin iniciar sesión. Buscar y descargar comprueba la firma, versión, tamaño y archivos antes de ofrecer la instalación. También puedes elegir una copia extraída del celular. Drive se conserva como respaldo privado separado.");
        status.Text=sb.ToString();SaveReport(last);
    }
    [STAThread] static int Main(string[] args){
        try{
            if(args.Length==2&&args[0]=="--download-release"){
                var report=SystemReport();using(var cancel=new CancellationTokenSource(300000)){
                    try{string folder=GitHubUpdate.Prepare(VersionName,Convert.ToInt32(report["windowsBuild"]),Modulus,DownloadRoot,cancel.Token,x=>{},Verify);report["downloadVerified"]=true;report["source"]=folder;SaveReport(report,args[1]);return 0;}
                    catch(Exception ex){report["downloadVerified"]=false;report["error"]=ex.Message;SaveReport(report,args[1]);return 2;}
                }
            }
            if(args.Length==3&&args[0]=="--check"){
                var report=SystemReport();try{var m=Verify(args[1]);report["integrityVerified"]=true;report["packageVersion"]=m["version"];}catch(Exception e){report["integrityVerified"]=false;report["error"]=e.Message;}
                SaveReport(report,args[2]);return (bool)report["integrityVerified"]?0:2;
            }
            if(args.Length==1&&args[0]=="--repair-now"){Thread.Sleep(2500);Install(CachedSource());return 0;}
            Application.EnableVisualStyles();Application.Run(new Compatibility(args.Length==1&&args[0]=="--repair"));return 0;
        }catch(Exception e){try{SaveReport(new Dictionary<string,object>{{"error",e.Message},{"version",VersionName}});}catch{}return 1;}
    }
}
