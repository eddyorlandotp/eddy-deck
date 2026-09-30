package com.eddy.deck;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InterfaceAddress;
import java.net.NetworkInterface;
import java.net.SocketTimeoutException;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

/** Offline UI + pinned TLS transport. No JS can request arbitrary network URLs. */
public class MainActivity extends Activity {
    private static final String ORIGIN="https://app.eddydeck.local";
    private WebView web;
    private SharedPreferences prefs;
    private Connections connections;
    private final WorkLanes lanes=new WorkLanes();
    static final class ServerFailure extends Exception {final int status;ServerFailure(int code,String message){super(message);status=code;}}
    private volatile JSONObject candidate;
    private ExportFiles exports;
    private String importPCId;
    private boolean ready;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        prefs=getSharedPreferences("connection",MODE_PRIVATE);
        connections=new Connections(this);
        exports=new ExportFiles(this,state==null?null:state.getString("exportFiles"));
        if(state!=null)importPCId=state.getString("importPCId");
        getWindow().setStatusBarColor(Color.rgb(246,247,245));
        getWindow().setNavigationBarColor(Color.rgb(246,247,245));
        web=new WebView(this);
        web.setBackgroundColor(Color.rgb(246,247,245));
        android.widget.FrameLayout container=new android.widget.FrameLayout(this);
        container.setBackgroundColor(Color.rgb(246,247,245));
        container.addView(web,new android.widget.FrameLayout.LayoutParams(-1,-1));
        container.setOnApplyWindowInsetsListener((view,insets)->{
            int top=insets.getSystemWindowInsetTop();
            int bottom=insets.getSystemWindowInsetBottom();
            view.setPadding(insets.getSystemWindowInsetLeft(),top,insets.getSystemWindowInsetRight(),bottom);
            return insets.consumeSystemWindowInsets();
        });
        WebSettings settings=web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSupportMultipleWindows(false);
        settings.setBuiltInZoomControls(false);
        settings.setMediaPlaybackRequiresUserGesture(true);
        WebView.setWebContentsDebuggingEnabled(false);
        web.setWebChromeClient(new WebChromeClient());
        web.addJavascriptInterface(new Bridge(),"EddyNative");
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){
                // External pages must never receive our native bridge.
                return true;
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest request){
                Uri uri=request.getUrl();
                String path=uri.getPath();
                if(!"https".equals(uri.getScheme())||!"app.eddydeck.local".equals(uri.getHost()))return blocked();
                if(path==null||path.equals("/"))path="/index.html";
                if(!path.matches("/(index\\.html|audio\\.js|app\\.js|extended\\.js|beta2\\.js|pickers\\.js|manual\\.js|styles\\.css|icon\\.svg)"))return blocked();
                String mime=path.endsWith(".html")?"text/html":path.endsWith(".js")?"text/javascript":path.endsWith(".css")?"text/css":"image/svg+xml";
                try{
                    HashMap<String,String> headers=new HashMap<>();
                    headers.put("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'");
                    headers.put("Cache-Control","no-store");
                    return new WebResourceResponse(mime,"UTF-8",200,"OK",headers,getAssets().open("ui"+path));
                }catch(Exception e){return blocked();}
            }
            @Override public void onPageFinished(WebView view,String url){ready=true;}
            @Override public boolean onRenderProcessGone(WebView view,android.webkit.RenderProcessGoneDetail detail){
                SupportReports.record(MainActivity.this,"webview","renderer-stopped",null);
                new AlertDialog.Builder(MainActivity.this).setTitle("Reparar Eddy Deck").setMessage("La interfaz se cerró inesperadamente. Tus computadoras y botones siguen guardados.").setPositiveButton("Reabrir",(d,w)->recreate()).show();return true;
            }
        });
        parseIntent(getIntent());
        setContentView(container);
        web.loadUrl(ORIGIN+"/index.html");
        if(connections.background())try{startForegroundService(new Intent(this,ConnectionService.class));}catch(RuntimeException ignored){}
    }
    private String versionedFile(String stem,String extension){
        try{return stem+"-"+getPackageManager().getPackageInfo(getPackageName(),0).versionName+extension;}
        catch(Exception e){return stem+extension;}
    }
    private void openPicker(Intent intent,int code){
        if(isFinishing()||isDestroyed())return;
        try{startActivityForResult(intent,code);}
        catch(RuntimeException e){
            java.io.File cached=exports.take(code);if(cached!=null)cached.delete();if(code==12)importPCId=null;
            SupportReports.record(this,"file-picker","unavailable",e);
            showMessage("No se pudo elegir un archivo","Android no pudo abrir su selector de archivos. Revisa que la aplicación Archivos esté habilitada e inténtalo otra vez.");
        }
    }
    private WebResourceResponse blocked(){return new WebResourceResponse("text/plain","UTF-8",403,"Blocked",Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));}
    @Override public void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);parseIntent(intent);if(ready)web.evaluateJavascript("window.eddyPairLink && window.eddyPairLink()",null);}
    private void parseIntent(Intent intent){
        if(intent==null||intent.getData()==null)return;
        try{
            JSONObject incoming=parseLink(intent.getData().toString());
            String id=incoming.getString("fingerprint");boolean known=false;
            JSONArray pcs=connections.bootstrap().getJSONArray("pcs");
            for(int i=0;i<pcs.length();i++)if(pcs.getJSONObject(i).getString("id").equals(id))known=true;
            if(known){connections.select(id);connections.update(id,"host",incoming.getString("host"));if(incoming.has("lan"))connections.update(id,"lan",incoming.getString("lan"));candidate=null;}
            else candidate=incoming;
            intent.setData(null);
        }catch(Exception e){new AlertDialog.Builder(this).setTitle("Eddy Deck").setMessage("El enlace de conexión no es válido.").setPositiveButton("Entendido",null).show();}
    }
    private static JSONObject parseLink(String text)throws Exception{
        Uri uri=Uri.parse(text.trim());
        if(!"eddydeck".equals(uri.getScheme()))throw new Exception("Usa un enlace eddydeck:// de tu PC.");
        String host=validHost(uri.getHost());
        String fp=validFingerprint(uri.getQueryParameter("fp"));
        String pin=uri.getQueryParameter("pin");
        if(pin==null||!pin.matches("[0-9]{8}"))throw new Exception("El código del enlace no es válido.");
        int port=uri.getQueryParameter("port")==null?47990:Integer.parseInt(uri.getQueryParameter("port"));
        if(port!=47990)throw new Exception("Puerto no compatible.");
        JSONObject result=new JSONObject().put("host",host).put("port",port).put("fingerprint",fp).put("pin",pin).put("fromLink",true);
        if(uri.getQueryParameter("lan")!=null)result.put("lan",validHost(uri.getQueryParameter("lan")));
        return result;
    }
    static String validHost(String host)throws Exception{
        if(host==null||!host.matches("[0-9]{1,3}(\\.[0-9]{1,3}){3}"))throw new Exception("Escribe la IP local o la IP privada de Tailscale de tu PC.");
        String[] pieces=host.split("\\.");int[] nums=new int[4];
        for(int i=0;i<4;i++){nums[i]=Integer.parseInt(pieces[i]);if(nums[i]>255||(pieces[i].length()>1&&pieces[i].startsWith("0")))throw new Exception("Dirección IP no válida.");}
        if(!(nums[0]==127||nums[0]==10||(nums[0]==192&&nums[1]==168)||(nums[0]==172&&nums[1]>=16&&nums[1]<=31)||(nums[0]==100&&nums[1]>=64&&nums[1]<=127)))throw new Exception("Usa una dirección privada de tu red o de Tailscale.");
        return host;
    }
    private static String validFingerprint(String fp)throws Exception{
        if(fp==null||!fp.matches("[a-fA-F0-9]{64}"))throw new Exception("Primero verifica la huella de la PC.");
        return fp.toLowerCase(java.util.Locale.ROOT);
    }
    private static String fingerprint(X509Certificate cert)throws Exception{
        byte[] digest=MessageDigest.getInstance("SHA-256").digest(cert.getEncoded());StringBuilder s=new StringBuilder();for(byte b:digest)s.append(String.format("%02x",b&255));return s.toString();
    }
    static JSONObject request(String host,int port,String fp,String token,String path,String method,JSONObject body,boolean probe)throws Exception{
        validHost(host);if(port!=47990)throw new Exception("Puerto no válido.");
        if(!probe)validFingerprint(fp);
        if(!path.matches("/(health|auth/pair|api/[a-z/]+)"))throw new Exception("Acción no válida.");
        if(!method.equals("GET")&&!method.equals("POST"))throw new Exception("Método no válido.");
        if(probe&&(!path.equals("/health")||!method.equals("GET")||token.length()>0))throw new Exception("Verificación no válida.");
        final String[] observed={null};
        final String pinned=fp;
        SSLContext tls=SSLContext.getInstance("TLS");
        tls.init(null,new TrustManager[]{new X509TrustManager(){
            public X509Certificate[] getAcceptedIssuers(){return new X509Certificate[0];}
            public void checkClientTrusted(X509Certificate[] chain,String auth)throws java.security.cert.CertificateException{throw new java.security.cert.CertificateException("No client cert");}
            public void checkServerTrusted(X509Certificate[] chain,String auth)throws java.security.cert.CertificateException{
                try{
                    if(chain==null||chain.length==0)throw new Exception("Sin certificado");
                    chain[0].checkValidity();String actual=fingerprint(chain[0]);observed[0]=actual;
                    if(!probe&&!MessageDigest.isEqual(actual.getBytes(StandardCharsets.US_ASCII),pinned.getBytes(StandardCharsets.US_ASCII)))throw new Exception("La identidad de esta dirección no coincide con tu PC vinculada.");
                }catch(Exception e){throw new java.security.cert.CertificateException(e.getMessage(),e);}
            }
        }},new SecureRandom());
        HttpsURLConnection conn=(HttpsURLConnection)new URL("https://"+host+":"+port+path).openConnection();
        conn.setSSLSocketFactory(tls.getSocketFactory());
        // A self-signed local PC is identified by its exact SHA-256 pin, not DNS.
        conn.setHostnameVerifier((hostname,session)->{
            try{
                if(!hostname.equals(host))return false;
                String actual=fingerprint((X509Certificate)session.getPeerCertificates()[0]);
                return probe||MessageDigest.isEqual(actual.getBytes(StandardCharsets.US_ASCII),pinned.getBytes(StandardCharsets.US_ASCII));
            }catch(Exception e){return false;}
        });
        conn.setConnectTimeout(path.equals("/api/heartbeat")?1200:2500);conn.setReadTimeout(path.equals("/api/heartbeat")?1200:8000);conn.setInstanceFollowRedirects(false);conn.setRequestMethod(method);
        conn.setRequestProperty("Accept","application/json");
        if(!token.isEmpty())conn.setRequestProperty("Authorization","Bearer "+token);
        try{
            if(method.equals("POST")){
                byte[] bytes=(body==null?"{}":body.toString()).getBytes(StandardCharsets.UTF_8);
                if(bytes.length>(path.equals("/api/backup/import")?4*1024*1024:131072))throw new Exception("Solicitud demasiado grande.");
                conn.setDoOutput(true);conn.setRequestProperty("Content-Type","application/json");conn.setFixedLengthStreamingMode(bytes.length);
                try(OutputStream out=conn.getOutputStream()){out.write(bytes);}
            }
            int code=conn.getResponseCode();
            if(code>=300&&code<400)throw new Exception("La PC intentó redirigir la conexión.");
            InputStream input=code>=400?conn.getErrorStream():conn.getInputStream();
            if(input==null)throw new Exception("La PC no devolvió una respuesta.");
            JSONObject result;
            try(InputStream in=input){result=new JSONObject(readText(in,4*1024*1024));}
            if(code>=400)throw new ServerFailure(code,result.optString("error","La PC rechazó la acción."));
            if(probe)return new JSONObject().put("fingerprint",observed[0]);
            return result;
        }finally{conn.disconnect();}
    }
    private static String readText(InputStream in,int max)throws Exception{
        ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int count;
        while((count=in.read(buffer))!=-1){if(out.size()+count>max)throw new Exception("Archivo demasiado grande.");out.write(buffer,0,count);}
        return out.toString("UTF-8");
    }
    private JSONArray discover()throws Exception{return discoverOn(this);}
    static JSONArray discoverOn(android.content.Context context)throws Exception{
        JSONArray results=new JSONArray();Set<String> hosts=new HashSet<>();Set<String> broadcasts=new HashSet<>();broadcasts.add("255.255.255.255");
        WifiManager wm=(WifiManager)context.getApplicationContext().getSystemService(WIFI_SERVICE);
        WifiManager.MulticastLock multicast=wm==null?null:wm.createMulticastLock("EddyDeckDiscovery");
        try{
            if(multicast!=null){multicast.setReferenceCounted(false);multicast.acquire();}
            android.net.ConnectivityManager manager=(android.net.ConnectivityManager)context.getSystemService(CONNECTIVITY_SERVICE);
            android.net.Network lan=null;android.net.LinkProperties properties=null;
            for(android.net.Network network:manager.getAllNetworks()){
                android.net.NetworkCapabilities caps=manager.getNetworkCapabilities(network);
                if(caps!=null&&!caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_VPN)&&(caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_WIFI)||caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_ETHERNET))){lan=network;properties=manager.getLinkProperties(network);break;}
            }
            if(lan==null)return results;
            if(properties!=null&&properties.getInterfaceName()!=null){
                NetworkInterface iface=NetworkInterface.getByName(properties.getInterfaceName());
                if(iface!=null)for(InterfaceAddress addr:iface.getInterfaceAddresses())if(addr.getBroadcast()!=null)broadcasts.add(addr.getBroadcast().getHostAddress());
            }
            try(DatagramSocket sock=new DatagramSocket()){
                try{lan.bindSocket(sock);}catch(java.net.SocketException blocked){
                    // A VPN may disallow per-app bypass even without lockdown.
                    // Keep the system route for LAN broadcasts in that case.
                    SupportReports.record(context,"discovery-network","system-route",blocked);
                }
                sock.setBroadcast(true);sock.setSoTimeout(500);
                byte[] data="EDDY_DECK_DISCOVER_V1".getBytes(StandardCharsets.UTF_8);
                for(String broadcast:broadcasts)try{sock.send(new DatagramPacket(data,data.length,InetAddress.getByName(broadcast),47991));}catch(Exception ignored){}
                long until=android.os.SystemClock.elapsedRealtime()+2500;
                while(android.os.SystemClock.elapsedRealtime()<until&&results.length()<16&&!Thread.currentThread().isInterrupted()){
                    DatagramPacket packet=new DatagramPacket(new byte[1024],1024);
                    try{sock.receive(packet);}catch(SocketTimeoutException e){continue;}
                    try{
                        JSONObject item=new JSONObject(new String(packet.getData(),0,packet.getLength(),StandardCharsets.UTF_8));
                        String host=validHost(packet.getAddress().getHostAddress());
                        if(!item.optString("app").equals("EddyDeck")||item.optInt("port")!=47990||hosts.contains(host))continue;
                        validFingerprint(item.optString("fingerprint"));hosts.add(host);item.put("host",host);results.put(item);
                    }catch(Exception ignored){}
                }
            }
        }finally{if(multicast!=null&&multicast.isHeld())multicast.release();}
        return results;
    }
    private void reply(String id,JSONObject value){runOnUiThread(()->{if(!isFinishing()&&!isDestroyed())web.evaluateJavascript("window.eddyResult("+JSONObject.quote(id)+","+value.toString()+")",null);});}
    private void showMessage(String title,String message){runOnUiThread(()->{if(!isFinishing()&&!isDestroyed())new AlertDialog.Builder(this).setTitle(title).setMessage(message).setPositiveButton("Entendido",null).show();});}
    private class Bridge{
        @JavascriptInterface public void request(String operation,String json,String id){
            if(id==null||!id.matches("[0-9]{1,10}"))return;
            if(json==null||json.length()>4*1024*1024){try{reply(id,new JSONObject().put("error","La solicitud supera el tamaño permitido.").put("server",true));}catch(Exception ignored){}return;}
            if("repairApp".equals(operation)){
                runOnUiThread(()->{if(!isFinishing()&&!isDestroyed()){SupportReports.record(MainActivity.this,"repair-app","requested",null);stopService(new Intent(MainActivity.this,ConnectionService.class));recreate();}});return;
            }
            final long queuedAt=android.os.SystemClock.elapsedRealtime();
            try{lanes.submit(operation,()->{
                JSONObject result;
                try{if(android.os.SystemClock.elapsedRealtime()-queuedAt>8000)throw new ServerFailure(429,"La acción esperó demasiado en el celular y no se envió. Inténtalo cuando termine la conexión actual.");result=handle(operation,new JSONObject(json));if(!operation.equals("bootstrap")&&!operation.equals("haptic")&&(!operation.equals("api")||new JSONObject(json).optString("method").equals("POST")))SupportReports.record(MainActivity.this,operation,"completed",null);}
                catch(Exception e){SupportReports.record(MainActivity.this,operation,"failed",e);result=new JSONObject();try{String msg=e.getMessage();if(e instanceof java.net.SocketTimeoutException)msg="La conexión tardó demasiado. Se comprobará de nuevo sin repetir la orden a ciegas.";result.put("error",msg==null?"No se pudo completar la acción.":msg).put("server",e instanceof ServerFailure).put("status",e instanceof ServerFailure?((ServerFailure)e).status:0);}catch(Exception ignored){}}
                reply(id,result);
            });}catch(java.util.concurrent.RejectedExecutionException e){try{reply(id,new JSONObject().put("error","Hay demasiadas acciones pendientes o se está reparando la app. Espera un momento.").put("server",true));}catch(Exception ignored){}}
        }
    }
    private JSONObject handle(String op,JSONObject body)throws Exception{
        switch(op){
            case "repairApp":{
                SupportReports.record(this,"repair-app","requested",null);
                runOnUiThread(()->{stopService(new Intent(this,ConnectionService.class));recreate();});
                return new JSONObject().put("status","restarting");
            }
            case "supportReport":return SupportReports.snapshot(this,connections);
            case "exportDiagnostics":{
                JSONObject report=new JSONObject().put("phone",SupportReports.snapshot(this,connections));
                if(body.has("pc"))report.put("pc",body.getJSONObject("pc"));
                exports.create(14,report.toString(2));
                runOnUiThread(()->{Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("application/json");i.putExtra(Intent.EXTRA_TITLE,"EddyDeck-informe.json");openPicker(i,14);});
                return new JSONObject().put("choosing",true);
            }
            case "bootstrap":{
                JSONObject result=connections.bootstrap();
                if(candidate!=null)result.put("candidate",candidate);return result;
            }
            case "readLink":return parseLink(body.getString("link"));
            case "probe":return request(body.getString("host"),47990,"","","/health","GET",null,true);
            case "discover":return new JSONObject().put("devices",discover());
            case "pair":{
                String host=validHost(body.getString("host"));String fp=validFingerprint(body.getString("fingerprint"));
                String pin=body.getString("pin");if(!pin.matches("[0-9]{8}"))throw new Exception("Código no válido.");
                String lan=body.optString("lan","");if(!lan.isEmpty())validHost(lan);
                JSONObject response=request(host,47990,fp,"","/auth/pair","POST",new JSONObject().put("pin",pin).put("name",android.os.Build.MANUFACTURER+" "+android.os.Build.MODEL),false);
                connections.put(new JSONObject().put("host",host).put("lan",lan).put("fingerprint",fp).put("token",response.getString("token")).put("deviceId",response.getString("deviceId")).put("name",response.getString("name")));
                candidate=null;return connections.bootstrap();
            }
            case "wake":return connections.wake(body.getString("pcId"));
            case "api":{
                return connections.api(body);
            }
            case "changeHost":{
                String fp=validFingerprint(body.getString("fingerprint"));String host=validHost(body.getString("host"));
                JSONObject pc=connections.active();if(pc==null||!fp.equals(pc.getString("fingerprint")))throw new Exception("Esa PC tiene otra huella. Agrégala como una computadora nueva.");
                request(host,47990,fp,pc.getString("token"),"/api/heartbeat","GET",null,false);
                connections.update(fp,host.startsWith("100.")?"vpn":"lan",host);connections.update(fp,"host",host);return connections.bootstrap();
            }
            case "forget":connections.forget();candidate=null;return connections.bootstrap();
            case "selectPC":connections.select(body.getString("id"));candidate=null;return connections.bootstrap();
            case "background":{
                boolean enabled=body.getBoolean("enabled");connections.background(enabled);
                runOnUiThread(()->{
                    if(enabled){
                        if(android.os.Build.VERSION.SDK_INT>=33&&checkSelfPermission("android.permission.POST_NOTIFICATIONS")!=android.content.pm.PackageManager.PERMISSION_GRANTED)requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"},31);
                        try{startForegroundService(new Intent(this,ConnectionService.class));}catch(RuntimeException e){connections.background(false);}
                    }else stopService(new Intent(this,ConnectionService.class));
                });return new JSONObject().put("enabled",enabled);
            }
            case "batterySettings":runOnUiThread(()->{Intent i=new Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+getPackageName()));startActivity(i);});return new JSONObject();
            case "tailscale":runOnUiThread(()->{Intent i=getPackageManager().getLaunchIntentForPackage("com.tailscale.ipn");if(i==null)i=new Intent(Intent.ACTION_VIEW,Uri.parse("https://play.google.com/store/apps/details?id=com.tailscale.ipn"));startActivity(i);});return new JSONObject();
            case "openBackup":runOnUiThread(()->startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse("https://github.com/eddyorlandotp/eddy-deck/releases"))));return new JSONObject();
            case "exportDocumentation":runOnUiThread(()->{Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("application/zip");i.putExtra(Intent.EXTRA_TITLE,versionedFile("EddyDeck-Documentacion",".zip"));openPicker(i,15);});return new JSONObject().put("choosing",true);
            case "exportInstaller":runOnUiThread(()->{Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("application/zip");i.putExtra(Intent.EXTRA_TITLE,versionedFile("EddyDeck-Windows",".zip"));openPicker(i,13);});return new JSONObject().put("choosing",true);
            case "haptic":runOnUiThread(()->web.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS));return new JSONObject();
            case "export":{
                exports.create(11,body.getJSONObject("profile").toString(2));
                runOnUiThread(()->{Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("application/json");i.putExtra(Intent.EXTRA_TITLE,"Eddy-Deck-copia.json");openPicker(i,11);});
                return new JSONObject().put("choosing",true);
            }
            case "import":{
                importPCId=connections.bootstrap().optString("pcId","");
                runOnUiThread(()->{Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("application/json");openPicker(i,12);});
                return new JSONObject().put("choosing",true);
            }
            default:throw new Exception("Operación no disponible.");
        }
    }
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
        super.onActivityResult(requestCode,resultCode,data);
        final java.io.File cached=exports.take(requestCode);
        final String selectedImportPC=importPCId==null?"":importPCId;
        if(requestCode==12)importPCId=null;
        if(resultCode!=RESULT_OK||data==null||data.getData()==null){if(cached!=null)cached.delete();SupportReports.record(this,"file-choice","cancelled",null);return;}
        try{lanes.submit("fileResult",()->{
            try{
                if(requestCode==11||requestCode==14){if(cached==null||!cached.isFile())throw new Exception("La copia temporal ya no está disponible. Vuelve a exportarla.");try(InputStream in=new java.io.FileInputStream(cached);OutputStream out=getContentResolver().openOutputStream(data.getData())){if(out==null)throw new Exception("No se pudo guardar la copia.");byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1)out.write(b,0,n);}showMessage("Archivo guardado","El archivo quedó en la ubicación que elegiste.");}
                if(requestCode==13){try(InputStream in=getAssets().open("EddyDeck-Windows.zip");OutputStream out=getContentResolver().openOutputStream(data.getData())){if(out==null)throw new Exception("No se pudo guardar el instalador.");byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1)out.write(b,0,n);}showMessage("Instalador guardado","Copia el ZIP a la otra PC por USB, Bluetooth o Compartir. En Windows, extrae todo y abre Instalar.cmd. Después vincula esa PC con su propio código.");}
                if(requestCode==15){try(InputStream in=getAssets().open("EddyDeck-Documentacion.zip");OutputStream out=getContentResolver().openOutputStream(data.getData())){if(out==null)throw new Exception("No se pudo guardar la documentación.");byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1)out.write(b,0,n);}showMessage("Manual e informes guardados","Abre el ZIP y después MANUAL-USUARIO.html para leer todas las funciones. Incluye también los informes técnicos de esta versión.");}
                if(requestCode==12){JSONObject profile;try(InputStream in=getContentResolver().openInputStream(data.getData())){if(in==null)throw new Exception("No se pudo leer el archivo.");profile=new JSONObject(readText(in,4*1024*1024));}runOnUiThread(()->{if(!isFinishing()&&!isDestroyed())web.evaluateJavascript("window.eddyImported("+profile.toString()+","+JSONObject.quote(selectedImportPC)+")",null);});}
                SupportReports.record(this,"file-result","completed",null);
            }catch(Exception e){SupportReports.record(this,"file-result","failed",e);showMessage("Eddy Deck",e.getMessage());}
            finally{if(cached!=null)cached.delete();}
        });}catch(java.util.concurrent.RejectedExecutionException e){if(cached!=null)cached.delete();showMessage("Eddy Deck ocupado","Espera a que terminen las operaciones y vuelve a guardar el archivo.");}
    }
    @Override public void onBackPressed(){web.evaluateJavascript("window.eddyBack ? window.eddyBack() : false",result->{if(!"true".equals(result))moveTaskToBack(true);});}
    @Override protected void onResume(){super.onResume();getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);}
    @Override protected void onPause(){getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);super.onPause();}
    @Override protected void onSaveInstanceState(Bundle state){state.putString("exportFiles",exports.state());state.putString("importPCId",importPCId);super.onSaveInstanceState(state);}
    @Override protected void onDestroy(){lanes.close();web.removeJavascriptInterface("EddyNative");web.destroy();super.onDestroy();}
}
