package com.eddy.deck;
import android.app.*;
import android.content.*;
import android.os.Bundle;
import java.io.File;
import java.lang.reflect.Field;
import org.json.*;

/** Recreate the real Activity with only an isolated pending-export fixture.
 * The normal UI may make read-only refreshes. No user profile is imported.
 */
final class ActivityLifecycleChecks {
    static JSONObject run(Instrumentation test,int cycles,int pauseMillis)throws Exception{
        if(cycles<1||cycles>120||pauseMillis<0||pauseMillis>30000)throw new Exception("Lifecycle test bounds exceeded");
        Context target=test.getTargetContext();
        Intent intent=new Intent(target,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        MainActivity current=(MainActivity)test.startActivitySync(intent);test.waitForIdleSync();
        JSONArray observations=new JSONArray();long started=android.os.SystemClock.elapsedRealtime(),focusWaitMillis=0;
        for(int cycle=0;cycle<cycles;cycle++){
            // Ordinary user navigation is not a failed product recreation.
            // Wait without bringing the app forward, and keep the delay visible.
            long waiting=android.os.SystemClock.elapsedRealtime(),lastNotice=0;
            while(!current.hasWindowFocus()){
                long now=android.os.SystemClock.elapsedRealtime();
                if(current.isDestroyed())throw new Exception("Fixture Activity was destroyed outside this test; no replacement was forced");
                if(now-waiting>600000)throw new Exception("INCOMPLETE: foreground was unavailable for ten minutes; no navigation forced");
                if(now-lastNotice>=10000){Bundle progress=new Bundle();progress.putString("stream",new JSONObject().put("status","waitingForForeground").put("nextCycle",cycle+1).put("waitMillis",now-waiting).toString()+"\n");test.sendStatus(1,progress);lastNotice=now;}
                Thread.sleep(250);
            }
            focusWaitMillis+=android.os.SystemClock.elapsedRealtime()-waiting;
            JSONObject observation=new JSONObject();current=recreate(test,current,observation);
            observation.put("cycle",cycle+1).put("elapsedMillis",android.os.SystemClock.elapsedRealtime()-started)
                .put("javaHeapBytes",Runtime.getRuntime().totalMemory()-Runtime.getRuntime().freeMemory()).put("javaThreads",Thread.getAllStackTraces().size());
            observations.put(observation);Bundle progress=new Bundle();progress.putString("stream",observation.toString()+"\n");test.sendStatus(1,progress);
            if(cycle+1<cycles)Thread.sleep(pauseMillis);
        }
        return new JSONObject().put("passed",true).put("cycles",cycles).put("checks",cycles*8).put("elapsedMillis",android.os.SystemClock.elapsedRealtime()-started).put("focusWaitMillis",focusWaitMillis).put("observations",observations).put("scope","Actual Activity recreation, isolated 1.2 MB export fixture; no user profile changes; waits for foreground without forcing navigation");
    }
    private static MainActivity recreate(Instrumentation test,MainActivity first,JSONObject observation)throws Exception{
        for(int i=0;i<30&&!first.hasWindowFocus();i++)Thread.sleep(100);
        if(!first.hasWindowFocus())throw new Exception("NOT RUN: unlock the phone and keep Eddy Deck visible; Activity has no focus");
        Field exports=MainActivity.class.getDeclaredField("exports");exports.setAccessible(true);
        ExportFiles fixture=(ExportFiles)exports.get(first);
        if(!fixture.state().equals("{}"))throw new Exception("A user export is pending; leave it untouched");
        String value=new String(new char[1200000]).replace('\0','x');fixture.create(11,value);
        Bundle saved=new Bundle();test.runOnMainSync(()->test.callActivityOnSaveInstanceState(first,saved));
        JSONArray checks=new JSONArray();
        if(saved.getString("exportFiles").length()>=300)throw new Exception("Saved state contains large file bytes");checks.put("Saved state contains references, not 1.2 MB bytes");
        String metadata=saved.getString("exportFiles");
        Instrumentation.ActivityMonitor monitor=test.addMonitor(MainActivity.class.getName(),null,false);
        try{
            test.runOnMainSync(first::recreate);
            Activity recreated=test.waitForMonitorWithTimeout(monitor,10000);
            if(recreated==null||recreated==first)throw new Exception("Activity did not recreate");checks.put("New Activity instance observed");
            test.waitForIdleSync();
            if(!first.isDestroyed())throw new Exception("Previous Activity is still alive");checks.put("Previous Activity destroyed");
            ExportFiles actual=(ExportFiles)exports.get(recreated);
            if(!actual.state().equals(metadata))throw new Exception("Export references not restored");checks.put("Pending export reference restored");
            File bytes=actual.take(11);
            if(bytes==null||bytes.length()!=1200000)throw new Exception("Fixture file lost during Activity recreation");checks.put("Exact 1.2 MB fixture preserved");
            if(!bytes.delete())throw new Exception("Fixture cleanup failed");checks.put("Only the test fixture was deleted");
            for(int i=0;i<30&&!recreated.hasWindowFocus();i++)Thread.sleep(100);
            if(!recreated.hasWindowFocus())throw new Exception("Recreated Activity did not regain focus");checks.put("Recreated Activity regained focus");
            if((recreated.getWindow().getAttributes().flags&android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)==0)throw new Exception("Foreground screen flag missing after recreation");checks.put("Foreground screen flag restored");
            observation.put("checks",checks);return (MainActivity)recreated;
        }finally{
            test.removeMonitor(monitor);File pending=fixture.take(11);if(pending!=null&&pending.isFile())pending.delete();
        }
    }
}
