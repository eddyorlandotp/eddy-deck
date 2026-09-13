package com.eddy.deck;
import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;

/** Local support metadata only. Never store API bodies, tokens, URLs or titles. */
final class SupportReports {
    static synchronized void record(Context c,String action,String status,Exception error){
        try{
            JSONArray rows=read(c);JSONArray next=new JSONArray();
            for(int i=Math.max(0,rows.length()-99);i<rows.length();i++)next.put(rows.get(i));
            next.put(new JSONObject().put("at",System.currentTimeMillis()).put("action",action).put("status",status).put("errorType",error==null?"":error.getClass().getSimpleName()));
            c.getSharedPreferences("deck-support",0).edit().putString("events",next.toString()).commit();
        }catch(Exception ignored){}
    }
    static JSONArray read(Context c){try{return new JSONArray(c.getSharedPreferences("deck-support",0).getString("events","[]"));}catch(Exception e){return new JSONArray();}}
    static JSONObject snapshot(Context c,Connections connections)throws Exception{
        String version="unknown";
        try{version=c.getPackageManager().getPackageInfo(c.getPackageName(),0).versionName;}catch(android.content.pm.PackageManager.NameNotFoundException unavailable){}
        JSONObject result=new JSONObject().put("version",version).put("androidSdk",android.os.Build.VERSION.SDK_INT).put("events",read(c));
        try{JSONObject b=connections.bootstrap();result.put("vaultReadable",true).put("pairedPCs",b.getJSONArray("pcs").length()).put("backgroundEnabled",b.getBoolean("background")).put("lastBackgroundCheck",b.optLong("backgroundAt"));}
        catch(Exception e){result.put("vaultReadable",false).put("errorType",e.getClass().getSimpleName());}
        return result;
    }
}
