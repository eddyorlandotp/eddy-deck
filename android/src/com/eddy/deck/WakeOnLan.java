package com.eddy.deck;

import android.content.Context;
import android.net.*;
import org.json.*;
import java.net.*;
import java.util.*;

/** A single explicit LAN wake request, independent of the sleeping receiver. */
final class WakeOnLan {
    static byte[] magic(String mac)throws Exception{
        if(mac==null||!mac.matches("(?i)([0-9a-f]{2}:){5}[0-9a-f]{2}"))throw new Exception("Dirección de red no válida.");
        String[] parts=mac.split(":");byte[] address=new byte[6];for(int i=0;i<6;i++)address[i]=(byte)Integer.parseInt(parts[i],16);
        if((address[0]&1)!=0||mac.equals("00:00:00:00:00:00"))throw new Exception("Dirección de red no válida.");
        byte[] bytes=new byte[102];Arrays.fill(bytes,0,6,(byte)255);for(int i=0;i<16;i++)System.arraycopy(address,0,bytes,6+6*i,6);return bytes;
    }
    static long ipv4(String value)throws Exception{
        if(value==null||!value.matches("(?:0|[1-9][0-9]{0,2})(?:\\.(?:0|[1-9][0-9]{0,2})){3}"))throw new Exception("Red IPv4 no válida.");
        long out=0;for(String p:value.split("\\.")){int n=Integer.parseInt(p);if(n>255)throw new Exception("Red IPv4 no válida.");out=(out<<8)|n;}return out;
    }
    static boolean privateAddress(long value){return (value>>>24)==10||(value>>>20)==0xac1||(value>>>16)==0xc0a8;}
    static long mask(int prefix)throws Exception{if(prefix<8||prefix>30)throw new Exception("Prefijo de red no válido.");return (0xffffffffL<<(32-prefix))&0xffffffffL;}
    static String ip(long value){return ((value>>>24)&255)+"."+((value>>>16)&255)+"."+((value>>>8)&255)+"."+(value&255);}
    static JSONObject validate(JSONObject adapter)throws Exception{
        magic(adapter.optString("mac"));long address=ipv4(adapter.optString("address"));Object rawPrefix=adapter.get("prefix");if(!(rawPrefix instanceof Integer))throw new Exception("Prefijo de red no válido.");int prefix=(Integer)rawPrefix;long bits=mask(prefix),broadcast=(address&bits)|(~bits&0xffffffffL);
        if(!privateAddress(address)||address==(address&bits)||address==broadcast)throw new Exception("Se necesita una dirección de red local.");
        if(!adapter.optString("broadcast").equals(ip(broadcast)))throw new Exception("La red guardada no coincide con su dirección de difusión.");
        return new JSONObject().put("name",adapter.optString("name","Red local").substring(0,Math.min(120,adapter.optString("name","Red local").length()))).put("mac",adapter.getString("mac").toUpperCase(Locale.ROOT)).put("address",ip(address)).put("prefix",prefix).put("broadcast",ip(broadcast)).put("ethernet",adapter.optBoolean("ethernet",false));
    }
    static JSONArray validated(JSONArray incoming)throws Exception{
        JSONArray out=new JSONArray();if(incoming==null)return out;if(incoming.length()>8)throw new Exception("Demasiadas redes para despertar esta PC.");
        Set<String> seen=new HashSet<>();for(int i=0;i<incoming.length();i++){JSONObject a=validate(incoming.getJSONObject(i));String key=a.getString("mac")+"/"+a.getString("broadcast");if(seen.add(key))out.put(a);}return out;
    }
    // Equal network and broadcast ensure a moved phone cannot send to the old
    // subnet, a VPN route or an Internet address masquerading as a LAN target.
    static boolean sameLAN(JSONObject saved,String phone,int phonePrefix)throws Exception{
        if(phonePrefix<8||phonePrefix>30)return false;
        long a=ipv4(saved.getString("address")),b=ipv4(phone),m=mask(saved.getInt("prefix")),pm=mask(phonePrefix);
        return privateAddress(b)&&m==pm&&(a&m)==(b&pm)&&a!=b;
    }
    static JSONObject send(Context context,JSONArray saved)throws Exception{
        saved=validated(saved);if(saved.length()==0)throw new Exception("Conecta esta PC una vez para guardar sus datos de encendido.");
        ConnectivityManager manager=(ConnectivityManager)context.getSystemService(Context.CONNECTIVITY_SERVICE);
        int sent=0;boolean systemRouting=false;String failure="";Set<String> done=new HashSet<>();
        for(Network network:manager.getAllNetworks()){
            NetworkCapabilities caps=manager.getNetworkCapabilities(network);
            if(caps==null||caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN)||!(caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)||caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)))continue;
            LinkProperties links=manager.getLinkProperties(network);if(links==null)continue;
            for(LinkAddress local:links.getLinkAddresses()){
                if(!(local.getAddress() instanceof Inet4Address))continue;
                for(int i=0;i<saved.length();i++){
                    JSONObject a=saved.getJSONObject(i);
                    if(!sameLAN(a,local.getAddress().getHostAddress(),local.getPrefixLength()))continue;
                    String key=a.getString("mac")+"/"+a.getString("broadcast");if(!done.add(key))continue;
                    try(DatagramSocket socket=new DatagramSocket(null)){
                        // Some VPNs prohibit forcing a network even without
                        // lockdown. A normal OS-routed socket still obeys the
                        // VPN policy; never disable or bypass that policy.
                        try{network.bindSocket(socket);}catch(SocketException restricted){
                            if(!permissionDenied(restricted))throw restricted;
                            systemRouting=true;SupportReports.record(context,"wake-network","system-route",restricted);
                        }
                        socket.setBroadcast(true);socket.bind(new InetSocketAddress(local.getAddress(),0));
                        byte[] bytes=magic(a.getString("mac"));DatagramPacket packet=new DatagramPacket(bytes,bytes.length,InetAddress.getByName(a.getString("broadcast")),9);
                        for(int copy=0;copy<3;copy++)socket.send(packet);sent++;
                    }catch(Exception e){SupportReports.record(context,"wake-send","failed",e);failure="Android no pudo enviar la señal por esa red Wi-Fi. Revisa el acceso a la red local y la opción de bloquear conexiones fuera de la VPN.";}
                }
            }
        }
        if(sent==0)throw new Exception(failure.isEmpty()?"Conecta el celular al mismo Wi-Fi de la PC. Los datos móviles y Tailscale solos no pueden despertar una PC apagada.":failure);
        return new JSONObject().put("status","sent").put("adapters",sent).put("routing",systemRouting?"android-policy":"physical-network").put("powerOnVerified",false).put("message","Señal enviada por tu red local. Esperando a la PC; enviarla no confirma que haya encendido.");
    }
    static boolean permissionDenied(Exception e){
        for(Throwable cause=e;cause!=null;cause=cause.getCause())if(cause instanceof android.system.ErrnoException){int errno=((android.system.ErrnoException)cause).errno;return errno==android.system.OsConstants.EPERM||errno==android.system.OsConstants.EACCES;}
        return false;
    }
}
