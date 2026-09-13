package com.eddy.deck;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import org.json.JSONArray;
import org.json.JSONObject;
import java.security.KeyStore;
import java.util.LinkedHashSet;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** One encrypted vault, separate trust identity and token for each Windows PC. */
final class Connections {
    private static final Object LOCK=new Object();
    private static final java.util.HashMap<String,Long> discoveries=new java.util.HashMap<>();
    static void networkChanged(){synchronized(LOCK){discoveries.clear();}}
    private final Context context;
    interface Sender{JSONObject request(String host,int port,String pin,String token,String path,String method,JSONObject body,boolean probe)throws Exception;}
    interface Finder{JSONArray discover(Context context)throws Exception;}
    private final Sender sender;private final Finder finder;
    Connections(Context c){this(c,MainActivity::request,MainActivity::discoverOn);}
    Connections(Context c,Sender s,Finder f){context=c.getApplicationContext();sender=s;finder=f;}
    private SecretKey key()throws Exception{
        KeyStore ks=KeyStore.getInstance("AndroidKeyStore");ks.load(null);
        if(!ks.containsAlias("eddy-deck-vault")){
            KeyGenerator gen=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
            gen.init(new KeyGenParameterSpec.Builder("eddy-deck-vault",KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());gen.generateKey();
        }
        return (SecretKey)ks.getKey("eddy-deck-vault",null);
    }
    private JSONObject read()throws Exception{
        SharedPreferences p=context.getSharedPreferences("deck-vault",0);
        String value=p.getString("encrypted","");
        if(!value.isEmpty()){
            String[] parts=value.split(":");if(parts.length!=2)throw new Exception("La conexión guardada está dañada. No se borró ningún equipo.");
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,Base64.decode(parts[0],Base64.NO_WRAP)));
            return new JSONObject(new String(cipher.doFinal(Base64.decode(parts[1],Base64.NO_WRAP)),java.nio.charset.StandardCharsets.UTF_8));
        }
        JSONObject data=new JSONObject().put("active","").put("pcs",new JSONArray());
        SharedPreferences old=context.getSharedPreferences("connection",0);
        if(old.contains("token")){
            JSONObject pc=new JSONObject().put("id",old.getString("fingerprint","")).put("name","Mi PC");
            for(String field:new String[]{"host","lan","fingerprint","token","deviceId"})pc.put(field,old.getString(field,""));
            data.getJSONArray("pcs").put(pc);data.put("active",pc.getString("id"));write(data);
            if(!old.edit().clear().commit())throw new Exception("No se pudo completar la migración de la conexión.");
        }
        return data;
    }
    private void write(JSONObject data)throws Exception{
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key());
        byte[] encrypted=cipher.doFinal(data.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
        String encoded=Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP)+":"+Base64.encodeToString(encrypted,Base64.NO_WRAP);
        if(!context.getSharedPreferences("deck-vault",0).edit().putString("encrypted",encoded).commit())throw new Exception("No se pudo guardar la conexión de forma segura.");
    }
    JSONObject active()throws Exception{synchronized(LOCK){JSONObject data=read();return find(data,data.optString("active"));}}
    private JSONObject find(JSONObject data,String id)throws Exception{
        JSONArray list=data.getJSONArray("pcs");for(int i=0;i<list.length();i++)if(list.getJSONObject(i).getString("id").equals(id))return list.getJSONObject(i);
        return null;
    }
    JSONObject bootstrap()throws Exception{synchronized(LOCK){
        JSONObject data=read(),pc=find(data,data.optString("active"));JSONArray list=new JSONArray();
        for(int i=0;i<data.getJSONArray("pcs").length();i++){
            JSONObject item=data.getJSONArray("pcs").getJSONObject(i);
            list.put(new JSONObject().put("id",item.getString("id")).put("name",item.optString("name","Mi PC")).put("host",item.optString("host")).put("vpn",item.optString("vpn")).put("active",item.getString("id").equals(data.optString("active"))));
        }
        SharedPreferences options=context.getSharedPreferences("deck-options",0);
        return new JSONObject().put("paired",pc!=null).put("pcId",pc==null?"":pc.getString("id")).put("host",pc==null?"":pc.optString("host")).put("pcs",list).put("background",background()).put("backgroundStatus",options.getString("backgroundStatus","")).put("backgroundError",options.getString("backgroundError","")).put("backgroundAt",options.getLong("backgroundAt",0));
    }}
    void put(JSONObject pc)throws Exception{synchronized(LOCK){
        JSONObject data=read();JSONArray list=data.getJSONArray("pcs");String id=pc.getString("fingerprint");pc.put("id",id);
        for(int i=list.length()-1;i>=0;i--)if(list.getJSONObject(i).getString("id").equals(id))list.remove(i);
        if(list.length()>=20)throw new Exception("Puedes guardar hasta 20 computadoras.");
        list.put(pc);data.put("active",id);write(data);
    }}
    void select(String id)throws Exception{synchronized(LOCK){JSONObject d=read();if(find(d,id)==null)throw new Exception("Esta PC no está vinculada.");d.put("active",id);write(d);}}
    void forget()throws Exception{synchronized(LOCK){JSONObject d=read();JSONArray list=d.getJSONArray("pcs");String active=d.optString("active");for(int i=list.length()-1;i>=0;i--)if(list.getJSONObject(i).getString("id").equals(active))list.remove(i);d.put("active",list.length()==0?"":list.getJSONObject(0).getString("id"));write(d);}}
    void update(String id,String field,String value)throws Exception{synchronized(LOCK){JSONObject d=read();JSONObject pc=find(d,id);if(pc==null)return;pc.put(field,value);write(d);}}
    boolean background(){return context.getSharedPreferences("deck-options",0).getBoolean("background",false);}
    void background(boolean enabled){context.getSharedPreferences("deck-options",0).edit().putBoolean("background",enabled).commit();}
    private void stillSelected(JSONObject pc)throws Exception{
        if(Thread.currentThread().isInterrupted())throw new java.io.InterruptedIOException("La conexión anterior se detuvo para reparar la app.");
        JSONObject selected=active();
        if(selected==null||!selected.getString("id").equals(pc.getString("id")))throw new Exception("Cambiaste de PC. No se envió otra orden al equipo anterior.");
    }
    private void remember(JSONObject original,String host,JSONObject response){
        try{synchronized(LOCK){
            JSONObject data=read(),pc=find(data,original.getString("id"));if(pc==null)return;
            String before=pc.toString();pc.put("host",host);
            if(response.has("name"))pc.put("name",response.getString("name"));
            LinkedHashSet<String> routes=new LinkedHashSet<>();
            JSONArray incoming=response.optJSONArray("addresses");
            if(incoming!=null)for(int i=0;i<Math.min(32,incoming.length());i++)try{
                String address=MainActivity.validHost(incoming.getString(i));
                if(!address.startsWith("127."))routes.add(address);
            }catch(Exception invalid){}
            // Keep the private VPN route when its adapter is temporarily absent.
            if(host.startsWith("100."))pc.put("vpn",host);
            else if(!host.startsWith("127."))pc.put("lan",host);
            for(String address:routes)if(address.startsWith("100."))pc.put("vpn",address);
            JSONArray saved=new JSONArray();for(String address:routes){if(saved.length()==8)break;saved.put(address);}
            if(incoming!=null)pc.put("routes",saved);
            if(!before.equals(pc.toString()))write(data);
        }}catch(Exception e){SupportReports.record(context,"remember-route","failed",e);}
    }
    private JSONObject heartbeat(JSONObject pc,String host)throws Exception{
        stillSelected(pc);
        return sender.request(MainActivity.validHost(host),47990,pc.getString("fingerprint"),pc.getString("token"),"/api/heartbeat","GET",null,false);
    }
    JSONObject api(JSONObject body)throws Exception{
        JSONObject pc=active();if(pc==null)throw new Exception("Vincula una PC para empezar.");
        if(!body.optString("pcId").equals(pc.getString("id")))throw new Exception("Cambiaste de PC. Vuelve a elegir la acción en el equipo actual.");
        String path=body.getString("path"),method=body.getString("method");
        if(!path.startsWith("/api/")||!(method.equals("GET")||method.equals("POST")))throw new Exception("Acción no permitida.");
        LinkedHashSet<String> hosts=new LinkedHashSet<>();
        for(String field:new String[]{"host","vpn","lan"})if(!pc.optString(field).isEmpty())hosts.add(pc.getString(field));
        JSONArray saved=pc.optJSONArray("routes");
        if(saved!=null)for(int i=0;i<Math.min(8,saved.length())&&hosts.size()<7;i++)hosts.add(saved.optString(i));
        hosts.add("127.0.0.1");hosts.remove("");
        long deadline=android.os.SystemClock.elapsedRealtime()+20000;
        String chosen=null;JSONObject beat=null;javax.net.ssl.SSLException identityError=null;
        // Only read-only probes may fail over. The actual command is sent once.
        for(String host:hosts){
            if(android.os.SystemClock.elapsedRealtime()>=deadline)break;
            try{beat=heartbeat(pc,host);chosen=host;break;}
            catch(javax.net.ssl.SSLException e){identityError=e;}
            catch(java.io.IOException e){stillSelected(pc);}
        }
        boolean discover=false;
        synchronized(LOCK){
            long now=android.os.SystemClock.elapsedRealtime();Long last=discoveries.get(pc.getString("id"));
            if(chosen==null&&(last==null||now-last>=15000)){if(discoveries.size()>20)discoveries.clear();discoveries.put(pc.getString("id"),now);discover=true;}
        }
        if(discover&&android.os.SystemClock.elapsedRealtime()<deadline){
            JSONArray candidates=new JSONArray();
            try{stillSelected(pc);candidates=finder.discover(context);}catch(java.io.IOException e){}
            for(int i=0;i<Math.min(16,candidates.length())&&android.os.SystemClock.elapsedRealtime()<deadline;i++){
                JSONObject candidate=candidates.optJSONObject(i);
                if(candidate==null||!candidate.optString("fingerprint").equals(pc.getString("fingerprint")))continue;
                String host;try{host=MainActivity.validHost(candidate.optString("host"));}catch(Exception invalid){continue;}
                try{beat=heartbeat(pc,host);chosen=host;SupportReports.record(context,"rediscovery","verified",null);break;}
                catch(javax.net.ssl.SSLException e){identityError=e;}
                catch(java.io.IOException e){stillSelected(pc);}
            }
        }
        stillSelected(pc);
        if(chosen==null){
            if(identityError!=null)throw new javax.net.ssl.SSLHandshakeException("Una dirección respondió con otra identidad. Conservé tu vinculación; revisa Eddy Deck en Windows. No se enviaron órdenes a esa PC.");
            throw new java.net.ConnectException("Esperando a "+pc.optString("name","tu PC")+". Reconectaré automáticamente. La PC debe estar encendida; fuera de casa, Tailscale debe estar conectado en ambos equipos.");
        }
        remember(pc,chosen,beat);
        if(path.equals("/api/heartbeat")&&method.equals("GET"))return beat;
        stillSelected(pc);
        // An IOException here is ambiguous: never replay a POST at another IP.
        // The UI retains the operation ID and consults the durable receipt.
        JSONObject result=sender.request(chosen,47990,pc.getString("fingerprint"),pc.getString("token"),path,method,body.optJSONObject("body"),false);
        if(path.equals("/api/state")&&method.equals("GET"))remember(pc,chosen,result);
        return result;
    }
}
