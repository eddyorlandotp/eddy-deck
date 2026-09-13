using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Automation;

class TidalMedia {
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    static IntPtr hwnd; static int pid; static long created; static string expectedPath;
    static void Identity() {
        uint owner; GetWindowThreadProcessId(hwnd,out owner);
        if(owner!=(uint)pid)throw new Exception("La ventana de TIDAL cambió. Actualiza e inténtalo de nuevo.");
        using(var process=Process.GetProcessById(pid)) {
            if(process.StartTime.ToUniversalTime().ToFileTimeUtc()!=created || !String.Equals(Path.GetFullPath(process.MainModule.FileName),Path.GetFullPath(expectedPath),StringComparison.OrdinalIgnoreCase) || !String.Equals(Path.GetFileName(expectedPath),"TIDAL.exe",StringComparison.OrdinalIgnoreCase))
                throw new Exception("No se pudo verificar el proceso de TIDAL.");
        }
    }
    static AutomationElement Footer() {
        Identity();var root=AutomationElement.FromHandle(hwnd);
        var footer=root.FindFirst(TreeScope.Descendants,new PropertyCondition(AutomationElement.AutomationIdProperty,"footerPlayer"));
        if(footer==null)throw new Exception("TIDAL no expone su reproductor. Abre su ventana y carga una canción.");
        return footer;
    }
    static AutomationElement Button(AutomationElement footer,params string[] labels) {
        var buttons=footer.FindAll(TreeScope.Descendants,new PropertyCondition(AutomationElement.ControlTypeProperty,ControlType.Button));
        AutomationElement match=null;
        foreach(AutomationElement b in buttons)foreach(string label in labels)if(String.Equals(b.Current.Name,label,StringComparison.OrdinalIgnoreCase)) {
            if(match!=null)throw new Exception("TIDAL muestra varios controles iguales. No se eligió uno al azar.");
            match=b;
        }
        return match;
    }
    static string State(AutomationElement footer) {
        // Read each button name once: separate queries can straddle a rename.
        int pause=0,play=0;
        var buttons=footer.FindAll(TreeScope.Descendants,new PropertyCondition(AutomationElement.ControlTypeProperty,ControlType.Button));
        foreach(AutomationElement b in buttons) {
            string name=b.Current.Name;
            if(String.Equals(name,"Pausar",StringComparison.OrdinalIgnoreCase)||String.Equals(name,"Pause",StringComparison.OrdinalIgnoreCase))pause++;
            if(String.Equals(name,"Reproducir",StringComparison.OrdinalIgnoreCase)||String.Equals(name,"Play",StringComparison.OrdinalIgnoreCase))play++;
        }
        if(pause==1 && play==0)return "playing";
        if(play==1 && pause==0)return "paused";
        throw new Exception("No se reconoce el botón de reproducción de TIDAL. Revisa su ventana.");
    }
    static string Track(AutomationElement footer){
        var links=footer.FindAll(TreeScope.Descendants,new PropertyCondition(AutomationElement.ControlTypeProperty,ControlType.Hyperlink));
        if(links.Count==0)throw new Exception("TIDAL no permite identificar la pista actual.");
        string names="";foreach(AutomationElement link in links)names+=link.Current.Name+"\n";
        using(var sha=SHA256.Create())return Convert.ToBase64String(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(names)));
    }
    static double Position(AutomationElement footer){
        var slider=footer.FindFirst(TreeScope.Descendants,new PropertyCondition(AutomationElement.AutomationIdProperty,"progressBar"));
        object pattern;if(slider==null||!slider.TryGetCurrentPattern(RangeValuePattern.Pattern,out pattern))return -1;
        return ((RangeValuePattern)pattern).Current.Value;
    }
    static object Run(string action) {
        AutomationElement footer=null;
        // Chromium may publish its accessibility tree after the first query.
        for(int i=0;i<8;i++){try{footer=Footer();break;}catch{if(i==7)throw;Thread.Sleep(100);}}
        string before=State(footer),desired=before;bool invoked=false;bool transport=action=="next"||action=="previous";
        if(action=="status"){
            var next=Button(footer,"Siguiente","Next");var previous=Button(footer,"Anterior","Previous");
            return new {available=true,state=before,controls=new {play=true,pause=true,toggle=true,stop=true,next=next!=null&&next.Current.IsEnabled,previous=previous!=null&&previous.Current.IsEnabled}};
        }
        if(action=="toggle")desired=before=="playing"?"paused":"playing";
        else if(action=="pause"||action=="stop")desired="paused";
        else if(action=="play")desired="playing";
        else if(!transport)throw new Exception("Control de TIDAL no permitido.");
        string originalTrack=transport?Track(footer):null;double originalPosition=transport?Position(footer):-1;
        if(transport||desired!=before) {
            Identity();footer=Footer();string fresh=State(footer);
            // Resolve toggles once; do not invert again if TIDAL changed meanwhile.
            if(transport||fresh!=desired) {
                var button=action=="next"?Button(footer,"Siguiente","Next"):action=="previous"?Button(footer,"Anterior","Previous"):desired=="paused"?Button(footer,"Pausar","Pause"):Button(footer,"Reproducir","Play");
                if(button==null||!button.Current.IsEnabled)throw new Exception("TIDAL no permite ese control en este momento.");
                object pattern;if(!button.TryGetCurrentPattern(InvokePattern.Pattern,out pattern))throw new Exception("TIDAL no ofrece el control accesible esperado.");
                Identity();((InvokePattern)pattern).Invoke();invoked=true;
            }
        }
        if(transport){
            var settling=Stopwatch.StartNew();int observed=0;bool changed=false,restarted=false;string transportState="unknown",lastTrack=null;double startPosition=-1,lastPosition=-1;
            while(settling.ElapsedMilliseconds<6500){
                Identity();
                try{footer=Footer();transportState=State(footer);string currentTrack=Track(footer);changed=currentTrack!=originalTrack;double position=Position(footer);restarted=action=="previous"&&originalPosition>3&&position>=0&&position<3;
                    // TIDAL can start playback after its labels already changed.
                    // Wait for that transition so a following pause is not overtaken.
                    if(currentTrack!=lastTrack||position<lastPosition||transportState!="playing"){startPosition=position;observed=0;}
                    bool advancing=position>=0&&startPosition>=0&&position-startPosition>=.5;
                    observed=transportState=="playing"&&(changed||restarted)&&advancing?observed+1:0;
                    lastTrack=currentTrack;lastPosition=position;
                }catch{observed=0;}
                if(observed>=3)return new {status="completed",player="tidal",action=action,before=before,state=transportState,invoked=invoked,verified=true,message=changed?"TIDAL confirmó el cambio de pista.":"TIDAL volvió al inicio de la pista."};
                Thread.Sleep(150);
            }
            throw new Exception("TIDAL recibió el cambio de pista, pero no terminó de confirmarlo. Espera a que cargue antes de enviar otra orden.");
        }
        var until=Stopwatch.StartNew();string after="unknown";int stable=0;
        while(until.ElapsedMilliseconds<3500){
            // Tolerate a transient missing accessibility element, never repeat Invoke.
            Identity();
            try{after=State(Footer());}catch{after="unknown";}
            stable=after==desired?stable+1:0;
            if(stable>=2)return new {status="completed",player="tidal",action=action,before=before,state=after,invoked=invoked,verified=true,message=after=="paused"?"TIDAL quedó en pausa.":"TIDAL está reproduciendo."};
            Thread.Sleep(150);
        }
        throw new Exception("Se pidió el cambio a TIDAL, pero no se pudo confirmar. Revisa su reproductor antes de repetir.");
    }
    [MTAThread] static int Main(string[] args) {
        var json=new JavaScriptSerializer();
        try {
            if(args.Length!=5)throw new Exception("Argumentos de control no válidos.");
            hwnd=new IntPtr(long.Parse(args[0]));pid=int.Parse(args[1]);created=long.Parse(args[2]);expectedPath=args[3];
            Console.OutputEncoding=System.Text.Encoding.UTF8;Console.WriteLine(json.Serialize(Run(args[4])));return 0;
        }catch(Exception e){Console.OutputEncoding=System.Text.Encoding.UTF8;Console.WriteLine(json.Serialize(new {error=e.Message}));return 1;}
    }
}
