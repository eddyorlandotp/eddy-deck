using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using Windows.Foundation;
using Windows.Media.Control;

class MediaSessions {
    static string Hash(string text){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-","").ToLowerInvariant();}
    static T Wait<T>(IAsyncOperation<T> op,int milliseconds){
        var clock=Stopwatch.StartNew();try{
            while(op.Status==AsyncStatus.Started){if(clock.ElapsedMilliseconds>=milliseconds){op.Cancel();throw new Exception("El reproductor tardó demasiado; revisa su estado antes de repetir.");}Thread.Sleep(20);}
            if(op.Status!=AsyncStatus.Completed)throw new Exception("El reproductor rechazó la consulta o el control.");
            return op.GetResults();
        }finally{op.Close();}
    }
    static string State(GlobalSystemMediaTransportControlsSession s){return s.GetPlaybackInfo().PlaybackStatus.ToString().ToLowerInvariant();}
    static string Token(GlobalSystemMediaTransportControlsSession s){return "session:"+Hash(s.SourceAppUserModelId).Substring(0,32);}
    static string Track(GlobalSystemMediaTransportControlsSession s){var p=Wait(s.TryGetMediaPropertiesAsync(),1200);return Hash(p.Title+"\n"+p.Artist+"\n"+p.AlbumTitle+"\n"+p.TrackNumber);}
    static object Snapshot(GlobalSystemMediaTransportControlsSession s){
        var p=s.GetPlaybackInfo();var c=p.Controls;
        return new {id=Token(s),source=s.SourceAppUserModelId,state=p.PlaybackStatus.ToString().ToLowerInvariant(),controls=new {play=c.IsPlayEnabled,pause=c.IsPauseEnabled,stop=c.IsStopEnabled,next=c.IsNextEnabled,previous=c.IsPreviousEnabled}};
    }
    static object Run(string action,string target){
        var manager=Wait(GlobalSystemMediaTransportControlsSessionManager.RequestAsync(),1500);
        var sessions=manager.GetSessions();
        if(action=="list"){var rows=new List<object>();foreach(var s in sessions){if(rows.Count>=32)break;rows.Add(Snapshot(s));}return new {players=rows};}
        GlobalSystemMediaTransportControlsSession chosen=null;
        foreach(var s in sessions)if(Token(s)==target){if(chosen!=null)throw new Exception("Esa aplicación tiene varias sesiones multimedia. Deja una sola antes de controlarla.");chosen=s;}
        if(chosen==null)throw new Exception("El reproductor ya no está disponible. Abre música y actualiza la lista.");
        if(action=="status")return Snapshot(chosen);
        string before=State(chosen),effective=action;
        if(action=="toggle")effective=before=="playing"?"pause":"play";
        if(effective!="play"&&effective!="pause"&&effective!="stop"&&effective!="next"&&effective!="previous")throw new Exception("Control multimedia no permitido.");
        bool transport=effective=="next"||effective=="previous";
        string desired=effective=="play"?"playing":effective=="stop"?"stopped":"paused";
        if(!transport&&(before==desired||(effective=="pause"&&before=="stopped")))return new {status="completed",state=before,verified=true,invoked=false,message="El reproductor ya estaba en ese estado."};
        var c=chosen.GetPlaybackInfo().Controls;
        bool enabled=effective=="play"?c.IsPlayEnabled:effective=="pause"?c.IsPauseEnabled:effective=="stop"?c.IsStopEnabled:effective=="next"?c.IsNextEnabled:c.IsPreviousEnabled;
        if(!enabled)throw new Exception("Este reproductor no permite ese control ahora.");
        string track=transport?Track(chosen):null;
        bool accepted=Wait(effective=="play"?chosen.TryPlayAsync():effective=="pause"?chosen.TryPauseAsync():effective=="stop"?chosen.TryStopAsync():effective=="next"?chosen.TrySkipNextAsync():chosen.TrySkipPreviousAsync(),2000);
        if(!accepted)throw new Exception("El reproductor no aceptó la orden.");
        var until=Stopwatch.StartNew();int stable=0;
        while(until.ElapsedMilliseconds<3000){
            string after=State(chosen);
            if(transport){if(Track(chosen)!=track)return new {status="completed",state=after,verified=true,invoked=true,message="El reproductor confirmó el cambio de pista."};}
            else{stable=after==desired?stable+1:0;if(stable>=2)return new {status="completed",state=after,verified=true,invoked=true,message=after=="paused"?"El reproductor quedó en pausa.":after=="stopped"?"Reproducción detenida.":"El reproductor está reproduciendo."};}
            Thread.Sleep(150);
        }
        return new {status="submitted",state=State(chosen),verified=false,invoked=true,message="Orden aceptada, pero el cambio no quedó confirmado. Revisa el reproductor antes de repetir."};
    }
    [MTAThread]static int Main(string[] args){var json=new JavaScriptSerializer();Console.OutputEncoding=Encoding.UTF8;try{if(args.Length!=2)throw new Exception("Argumentos no válidos.");Console.WriteLine(json.Serialize(Run(args[0],args[1])));return 0;}catch(Exception e){Console.WriteLine(json.Serialize(new {error=e is System.Runtime.InteropServices.COMException?"Windows no pudo acceder a la sesión multimedia. Abre el reproductor sin privilegios de administrador e inténtalo de nuevo.":e.Message}));return 1;}}
}
