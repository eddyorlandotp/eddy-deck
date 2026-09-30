// Decision table for the beta 12 watchdog. Compiled with installer/Watchdog.cs.
using System;
using System.IO;

static class WatchdogChecks {
    static int failures;
    static void Check(bool ok,string name){Console.WriteLine((ok?"OK   ":"FAIL ")+name);if(!ok)failures++;}
    static int Main(){
        // Decide(userExited,installing,responds,folderExists,exeExists,running,recentLaunches)
        Check(Watchdog.Decide(true,false,false,true,true,false,0)=="user-exit","Salir is respected even if the receiver is down");
        Check(Watchdog.Decide(false,true,false,true,true,false,0)=="installing","Never interferes with an installation");
        Check(Watchdog.Decide(false,false,true,true,true,true,0)=="healthy","A responding receiver is left alone");
        Check(Watchdog.Decide(false,false,true,true,false,false,0)=="healthy","Health wins over file checks");
        Check(Watchdog.Decide(false,false,false,false,false,false,0)=="uninstalled","Removed program folder: silent, no notices");
        Check(Watchdog.Decide(false,false,false,true,false,false,0)=="missing","Only the executable missing (quarantine): notice, no reinstall");
        Check(Watchdog.Decide(false,false,false,true,true,true,0)=="starting","Running but not yet responding: wait for the supervisor");
        Check(Watchdog.Decide(false,false,false,true,true,false,0)=="relaunch","Crashed or killed: relaunch");
        Check(Watchdog.Decide(false,false,false,true,true,false,2)=="relaunch","Two recent launches still allowed");
        Check(Watchdog.Decide(false,false,false,true,true,false,3)=="gave-up","Crash loop: stop after three launches per hour");
        string dir=Path.Combine(Path.GetTempPath(),"eddy-watchdog-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(dir);
        try{
            double now=(DateTime.UtcNow-new DateTime(1970,1,1,0,0,0,DateTimeKind.Utc)).TotalSeconds;
            Check(!Watchdog.UserExited(dir,now-100),"No marker, no exit");
            File.WriteAllText(Path.Combine(dir,"user-exit.json"),"{\"at\": "+now.ToString(System.Globalization.CultureInfo.InvariantCulture)+", \"reason\": \"Salir\"}");
            Check(Watchdog.UserExited(dir,now-100),"Marker from this session");
            Check(!Watchdog.UserExited(dir,now+100),"Marker from before the last restart is ignored");
            File.WriteAllText(Path.Combine(dir,"user-exit.json"),"roto");
            Check(!Watchdog.UserExited(dir,now-100),"Damaged marker is ignored");
        }finally{Directory.Delete(dir,true);}
        Console.WriteLine(failures==0?"ALL OK":failures+" FAILED");
        return failures==0?0:1;
    }
}
