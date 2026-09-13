package com.eddy.deck;
import android.content.Context;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.json.JSONObject;

/** Keep large profile bytes out of Android's limited saved-instance Bundle. */
final class ExportFiles {
    private final File folder;private final Map<Integer,String> pending=new HashMap<>();
    ExportFiles(Context context,String saved){
        folder=new File(context.getCacheDir(),"deck-exports");
        try{JSONObject o=new JSONObject(saved==null?"{}":saved);for(String key:new String[]{"11","14"}){String name=o.optString(key);if(name.matches("[a-f0-9-]{36}\\.json"))pending.put(Integer.parseInt(key),name);}}catch(Exception ignored){}
        File[] old=folder.listFiles();if(old!=null)for(File f:old)if(f.getName().matches("[a-f0-9-]{36}\\.json")&&!pending.containsValue(f.getName())&&System.currentTimeMillis()-f.lastModified()>86400000)f.delete();
    }
    synchronized void create(int code,String content)throws Exception{
        if(pending.containsKey(code))throw new Exception("Termina o cancela la exportación anterior de este tipo antes de empezar otra.");
        if(!folder.isDirectory()&&!folder.mkdirs())throw new IOException("No se pudo preparar la copia. Revisa el espacio del celular.");
        String name=UUID.randomUUID().toString()+".json";File file=new File(folder,name);
        try(FileOutputStream out=new FileOutputStream(file)){out.write(content.getBytes(StandardCharsets.UTF_8));out.getFD().sync();}
        catch(Exception e){file.delete();throw e;}
        pending.put(code,name);
    }
    synchronized File take(int code){String name=pending.remove(code);return name==null?null:new File(folder,name);}
    synchronized String state(){JSONObject o=new JSONObject();for(Map.Entry<Integer,String> e:pending.entrySet())try{o.put(String.valueOf(e.getKey()),e.getValue());}catch(Exception ignored){}return o.toString();}
}
