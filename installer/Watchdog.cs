// Per-user watchdog run by Task Scheduler (--watchdog). Independent of Python.
// It may start the installed Eddy Deck or show a notice. It never reinstalls,
// never stops processes and never changes security settings: if an antivirus
// removed EddyDeck.exe, restoring it is the user's decision.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Net;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

static class Watchdog {
    [DllImport("kernel32.dll")] static extern ulong GetTickCount64();
    const int MaxLaunchesPerHour=3;
    const double NoticeEverySeconds=6*3600;
    const int UnhealthyRunsBeforeNotice=6; // about 30 minutes at 5-minute intervals
    static JavaScriptSerializer Json=new JavaScriptSerializer();

    static double Now(){return (DateTime.UtcNow-new DateTime(1970,1,1,0,0,0,DateTimeKind.Utc)).TotalSeconds;}
    static double BootTime(){return Now()-GetTickCount64()/1000.0;}

    internal static bool UserExited(string data,double boot){
        try{
            var m=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(data,"user-exit.json")));
            return Convert.ToDouble(m["at"],System.Globalization.CultureInfo.InvariantCulture)>=boot-5;
        }catch{return false;}
    }
    static bool Responds(){
        // Any answer that identifies Eddy Deck, including 503 while starting.
        try{
            var request=(HttpWebRequest)WebRequest.Create("http://127.0.0.1:47989/health");
            request.Timeout=3000;request.ReadWriteTimeout=3000;request.Proxy=null;
            using(var response=(HttpWebResponse)request.GetResponse())using(var reader=new StreamReader(response.GetResponseStream()))return reader.ReadToEnd().Contains("Eddy Deck");
        }catch(WebException e){
            try{if(e.Response!=null)using(var reader=new StreamReader(e.Response.GetResponseStream()))return reader.ReadToEnd().Contains("Eddy Deck");}catch{}
            return false;
        }catch{return false;}
    }
    static bool InstalledRunning(string exe){
        foreach(var p in Process.GetProcessesByName("EddyDeck"))using(p){
            try{if(String.Equals(p.MainModule.FileName,exe,StringComparison.OrdinalIgnoreCase))return true;}catch{}
        }
        return false;
    }
    static bool Installing(){
        try{using(Mutex.OpenExisting("Local\\EddyDeck-Installation"))return true;}catch{return false;}
    }
    static Dictionary<string,object> LoadState(string file){
        try{var s=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(file));if(s!=null)return s;}catch{}
        return new Dictionary<string,object>();
    }
    static List<double> Launches(Dictionary<string,object> state,double now){
        var list=new List<double>();
        object raw;if(state.TryGetValue("launches",out raw)&&raw is System.Collections.IEnumerable)
            foreach(var x in (System.Collections.IEnumerable)raw){try{double t=Convert.ToDouble(x,System.Globalization.CultureInfo.InvariantCulture);if(now-t<3600&&now-t>=0)list.Add(t);}catch{}}
        return list;
    }
    static double Number(Dictionary<string,object> state,string key){
        object raw;try{return state.TryGetValue(key,out raw)?Convert.ToDouble(raw,System.Globalization.CultureInfo.InvariantCulture):0;}catch{return 0;}
    }
    static void Audit(string data,string status,string message){
        try{
            var row=new Dictionary<string,object>{{"at",DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.ffffff+00:00")},{"action","watchdog"},{"status",status},{"message",message}};
            File.AppendAllText(Path.Combine(data,"audit.jsonl"),Json.Serialize(row)+"\n",new UTF8Encoding(false));
        }catch{}
    }
    static void Save(string file,Dictionary<string,object> state){
        try{string temp=file+".tmp";File.WriteAllText(temp,Json.Serialize(state),new UTF8Encoding(false));if(File.Exists(file))File.Replace(temp,file,null);else File.Move(temp,file);}catch{}
    }

    // Pure decision, covered by tests through --watchdog --dry-run.
    internal static string Decide(bool userExited,bool installing,bool responds,bool folderExists,bool exeExists,bool running,int recentLaunches){
        if(userExited)return "user-exit";
        if(installing)return "installing";
        if(responds)return "healthy";
        // The whole program folder gone means it was uninstalled: stay silent.
        // Only the executable missing is the quarantine signature.
        if(!folderExists)return "uninstalled";
        if(!exeExists)return "missing";
        if(running)return "starting";
        if(recentLaunches>=MaxLaunchesPerHour)return "gave-up";
        return "relaunch";
    }

    internal static int Run(string data,string installed,bool dryRun){
        bool created;
        using(var single=new Mutex(true,"Local\\EddyDeck-Watchdog",out created)){
            if(!created)return 0;
            string stateFile=Path.Combine(data,"watchdog.json");
            string exe=Path.Combine(installed,"EddyDeck.exe");
            double now=Now();
            var state=LoadState(stateFile);var launches=Launches(state,now);
            string decision=Decide(UserExited(data,BootTime()),Installing(),Responds(),Directory.Exists(Path.Combine(installed,"_internal")),File.Exists(exe),InstalledRunning(exe),launches.Count);
            double unhealthy=decision=="starting"?Number(state,"unhealthyRuns")+1:0;
            state["lastRun"]=now;state["decision"]=decision;state["dryRun"]=dryRun;state["unhealthyRuns"]=unhealthy;
            string notice=null,title="Eddy Deck";
            if(decision=="missing"){
                notice="Falta EddyDeck.exe. Windows Defender u otro antivirus pudo ponerlo en cuarentena. Revisa Seguridad de Windows → Historial de protección, o usa el acceso «Eddy Deck - Reparar».";
                title="Eddy Deck fue bloqueado o eliminado";
            }else if(decision=="gave-up"){
                notice="Eddy Deck se cerró varias veces en la última hora. No se volverá a abrir solo por ahora. Ábrelo desde el escritorio y guarda un informe si se repite.";
            }else if(decision=="starting"&&unhealthy>=UnhealthyRunsBeforeNotice){
                notice="Eddy Deck sigue abierto pero no responde. Usa «Reiniciar conexión» en su ventana o sal desde el icono y vuelve a abrirlo.";decision="unresponsive";
            }
            if(!dryRun&&decision=="relaunch"){
                try{
                    Process.Start(new ProcessStartInfo(exe,"--tray"){UseShellExecute=false,WorkingDirectory=installed,CreateNoWindow=true}).Dispose();
                    launches.Add(now);Audit(data,"relaunched","El receptor no respondía y no hubo salida intencional.");
                }catch(Exception e){decision="launch-failed";notice="Windows no permitió abrir Eddy Deck: "+e.Message;Audit(data,"launch-failed",e.Message);}
            }
            state["launches"]=launches.ToArray();
            bool show=false;
            if(notice!=null){
                string key="notice-"+decision;
                if(now-Number(state,key)>=NoticeEverySeconds){state[key]=now;state["lastNotice"]=decision;show=!dryRun;}
            }
            // Persist before the notice waits for the person, so the state is
            // kept even if Task Scheduler stops this run.
            Save(stateFile,state);
            if(show){Audit(data,decision,notice);Show(title,notice,decision=="missing");}
            return 0;
        }
    }
    static void Show(string title,string text,bool security){
        try{
            using(var icon=new NotifyIcon{Icon=SystemIcons.Warning,Visible=true,Text="Eddy Deck"}){
                icon.BalloonTipTitle=title;icon.BalloonTipText=text;icon.BalloonTipIcon=ToolTipIcon.Warning;
                bool done=false;
                icon.BalloonTipClicked+=(s,e)=>{
                    try{Process.Start(new ProcessStartInfo(security?"windowsdefender://threat/":Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","EddyDeck","EddyDeck.exe")){UseShellExecute=true}).Dispose();}catch{}
                    done=true;
                };
                icon.BalloonTipClosed+=(s,e)=>done=true;
                icon.ShowBalloonTip(20000);
                var until=DateTime.UtcNow.AddSeconds(25);
                while(!done&&DateTime.UtcNow<until){Application.DoEvents();Thread.Sleep(100);}
                icon.Visible=false;
            }
        }catch{}
    }
}
