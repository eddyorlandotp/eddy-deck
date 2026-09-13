package com.eddy.deck;
import android.app.Instrumentation;
import android.content.Context;
import android.content.ContextWrapper;
import android.content.SharedPreferences;
import android.os.Bundle;
import org.json.JSONObject;

/** Normal mode uses isolated preferences. live-status only reads the paired PC
 * through the app's normal authenticated transport; it never prints credentials. */
public class ConnectionTests extends Instrumentation {
    int count=0;
    Bundle args;
    void check(boolean okay,String name)throws Exception{if(!okay)throw new Exception(name);count++;}
    @Override public void onCreate(Bundle b){super.onCreate(b);args=b;start();}
    @Override public void onStart(){
        Bundle result=new Bundle();
        try{
            if(args!=null&&"connection-info".equals(args.getString("mode"))){
                Connections live=new Connections(getTargetContext());JSONObject pc=live.active();
                JSONObject info=new JSONObject().put("paired",pc!=null).put("pcCount",live.bootstrap().getJSONArray("pcs").length());
                if(pc!=null)info.put("matchesExpected",pc.getString("fingerprint").equals(args.getString("expectedFingerprint"))).put("vpnSaved",!pc.optString("vpn").isEmpty());
                result.putString("stream",info.toString());finish(-1,result);return;
            }
            if(args!=null&&"discovery-info".equals(args.getString("mode"))){
                JSONObject info=new JSONObject();org.json.JSONArray networks=new org.json.JSONArray();
                android.net.ConnectivityManager manager=getTargetContext().getSystemService(android.net.ConnectivityManager.class);
                for(android.net.Network n:manager.getAllNetworks()){
                    android.net.NetworkCapabilities caps=manager.getNetworkCapabilities(n);android.net.LinkProperties prop=manager.getLinkProperties(n);
                    networks.put(new JSONObject().put("wifi",caps!=null&&caps.hasTransport(1)).put("vpn",caps!=null&&caps.hasTransport(4)).put("interface",prop==null?"":prop.getInterfaceName()));
                }
                org.json.JSONArray found=MainActivity.discoverOn(getTargetContext());JSONObject pc=new Connections(getTargetContext()).active();boolean matches=false;
                for(int i=0;i<found.length();i++)if(pc.getString("fingerprint").equals(found.getJSONObject(i).optString("fingerprint")))matches=true;
                info.put("networks",networks).put("foundCount",found.length()).put("matchingIdentity",matches);
                result.putString("stream",info.toString());finish(-1,result);return;
            }
            if(args!=null&&"live-network-recovery".equals(args.getString("mode"))){
                Connections live=new Connections(getTargetContext());JSONObject original=live.active();
                if(original==null||live.bootstrap().getJSONArray("pcs").length()!=1)throw new Exception("This controlled route test requires exactly one paired PC");
                JSONObject output=new JSONObject();
                try{
                    for(String kind:new String[]{"lan","vpn"}){
                        String host=MainActivity.validHost(args.getString(kind));
                        JSONObject state=MainActivity.request(host,47990,original.getString("fingerprint"),original.getString("token"),"/api/state","GET",null,false);
                        output.put(kind+"Connected",state.getString("version").equals(args.getString("version")));
                    }
                    JSONObject stale=new JSONObject(original.toString()).put("host","10.255.255.254").put("lan","").put("vpn","").put("routes",new org.json.JSONArray());
                    live.put(stale);Connections.networkChanged();long started=android.os.SystemClock.elapsedRealtime();
                    JSONObject state=live.api(new JSONObject().put("pcId",original.getString("id")).put("path","/api/state").put("method","GET"));
                    output.put("staleRouteRediscovered",state.getString("version").equals(args.getString("version"))).put("sameCallMillis",android.os.SystemClock.elapsedRealtime()-started).put("originalPinPreserved",live.active().getString("fingerprint").equals(original.getString("fingerprint"))).put("pairedPCs",live.bootstrap().getJSONArray("pcs").length());
                }finally{live.put(original);}
                output.put("originalSavedRoutesRestored",live.active().getString("host").equals(original.getString("host")));
                result.putString("stream",output.toString());finish(-1,result);return;
            }
            if(args!=null&&"live-status".equals(args.getString("mode"))){
                Connections live=new Connections(getTargetContext());
                JSONObject state=live.api(new JSONObject().put("pcId",live.bootstrap().getString("pcId")).put("path","/api/state").put("method","GET"));
                result.putString("stream",new JSONObject().put("version",state.getString("version")).put("keepAwake",state.optJSONObject("keepAwake")).put("queue",state.optJSONObject("queue")).toString());
                finish(-1,result);return;
            }
            if(args!=null&&"lifecycle".equals(args.getString("mode"))){
                JSONObject checks=ActivityLifecycleChecks.run(this,Integer.parseInt(args.getString("cycles","1")),Integer.parseInt(args.getString("pauseMillis","0")));result.putString("stream",checks.toString());finish(-1,result);return;
            }
            if(args!=null&&"network".equals(args.getString("mode"))){
                android.net.ConnectivityManager cm=(android.net.ConnectivityManager)getTargetContext().getSystemService(Context.CONNECTIVITY_SERVICE);
                org.json.JSONArray networks=new org.json.JSONArray();
                for(android.net.Network n:cm.getAllNetworks()){
                    android.net.NetworkCapabilities caps=cm.getNetworkCapabilities(n);if(caps==null)continue;
                    networks.put(new JSONObject().put("wifi",caps.hasTransport(1)).put("cellular",caps.hasTransport(0)).put("vpn",caps.hasTransport(4)).put("validated",caps.hasCapability(16)).put("internet",caps.hasCapability(12)));
                }
                JSONObject output=new JSONObject().put("networks",networks);
                try{output.put("eddyTLS",MainActivity.request(args.getString("host"),47990,args.getString("fingerprint"),"","/health","GET",null,false).has("version"));}catch(Exception e){output.put("eddyError",e.getClass().getSimpleName()+": "+e.getMessage());}
                result.putString("stream",output.toString());finish(-1,result);return;
            }
            String prefix="eddy-test-"+System.nanoTime()+"-";
            Context isolated=new ContextWrapper(getTargetContext()){
                @Override public Context getApplicationContext(){return this;}
                @Override public SharedPreferences getSharedPreferences(String name,int mode){return super.getSharedPreferences(prefix+name,mode);}
            };
            String a=new String(new char[64]).replace('\0','a'),b=new String(new char[64]).replace('\0','b');
            isolated.getSharedPreferences("connection",0).edit().putString("token","legacy-test-token").putString("fingerprint",a).putString("host","192.168.1.12").putString("deviceId","legacy").commit();
            Connections c=new Connections(isolated);
            check(c.bootstrap().getBoolean("paired"),"Migration paired");
            check(!isolated.getSharedPreferences("connection",0).contains("token"),"Legacy plaintext removed after durable vault write");
            String encrypted=isolated.getSharedPreferences("deck-vault",0).getString("encrypted","");
            check(!encrypted.contains("legacy-test-token"),"Vault encrypted");
            check(!c.bootstrap().toString().contains("token"),"No tokens exposed to JavaScript");
            c.put(new JSONObject().put("fingerprint",b).put("token","second-test-token").put("deviceId","second").put("name","PC de prueba B").put("host","100.64.0.12"));
            check(c.bootstrap().getJSONArray("pcs").length()==2,"Two separate computers");
            check(c.active().getString("token").equals("second-test-token"),"Second token isolated");
            c.select(a);check(c.active().getString("token").equals("legacy-test-token"),"Switch restores first token");
            try{c.api(new JSONObject().put("pcId",b).put("path","/api/media").put("method","POST"));throw new Exception("Cross-PC request accepted");}catch(Exception e){check(e.getMessage().contains("Cambiaste"),"Stale request rejected before network");}
            Connections reopened=new Connections(isolated);check(reopened.active().getString("id").equals(a),"Reopen preserves active PC");
            reopened.update(a,"vpn","100.81.0.1");check(reopened.active().getString("vpn").equals("100.81.0.1"),"VPN endpoint persisted");
            reopened.forget();check(reopened.bootstrap().getJSONArray("pcs").length()==1,"Forget one PC only");check(reopened.active().getString("token").equals("second-test-token"),"Other PC survives forget");
            for(String host:new String[]{"127.0.0.1","192.168.1.12","10.0.0.2","100.64.0.1","100.127.255.254"})check(MainActivity.validHost(host).equals(host),"Private endpoint accepted");
            for(String host:new String[]{"8.8.8.8","100.63.0.1","100.128.0.1","192.168.001.1","localhost","evil.test","192.168.1.1/path"}){
                boolean rejected=false;try{MainActivity.validHost(host);}catch(Exception e){rejected=true;}check(rejected,"Unsafe host rejected");
            }
            c.background(true);check(new Connections(isolated).background(),"Background preference survives reopen");c.background(false);
            // Deterministic transport failures, with the real encrypted vault and
            // routing algorithm; these send no packets and never use real peers.
            final java.util.ArrayList<String> routes=new java.util.ArrayList<>();
            c.update(b,"host","192.168.1.12");c.update(b,"lan","192.168.1.13");
            Connections failover=new Connections(isolated,(host,port,pin,token,path,method,payload,probe)->{
                routes.add(host);check(pin.equals(b)&&token.equals("second-test-token"),"Failover retains exact peer trust");
                if(method.equals("POST"))check(payload.getString("requestId").equals("retained-request"),"Command retains request identity");
                if(host.equals("192.168.1.12"))throw new java.net.ConnectException("injected offline");return new JSONObject().put("status","received");
            },context->{throw new Exception("POST must not rediscover");});
            JSONObject command=new JSONObject().put("pcId",b).put("path","/api/media").put("method","POST").put("body",new JSONObject().put("requestId","retained-request").put("action","next"));
            check(failover.api(command).getString("status").equals("received"),"Network failure falls back safely");check(routes.size()==3,"Two read probes then exactly one command");check(c.active().getString("host").equals("192.168.1.13"),"Verified route remembered");
            routes.clear();Connections denied=new Connections(isolated,(host,port,pin,token,path,method,payload,probe)->{routes.add(host);throw new MainActivity.ServerFailure(401,"revoked");},context->new org.json.JSONArray());
            try{denied.api(command);throw new Exception("Denied command accepted");}catch(MainActivity.ServerFailure e){check(e.status==401&&routes.size()==1,"Server rejection is not retried on other addresses");}
            final int[] discoveries={0};Connections offline=new Connections(isolated,(host,port,pin,token,path,method,payload,probe)->{throw new java.net.ConnectException("offline");},context->{discoveries[0]++;return new org.json.JSONArray();});
            try{offline.api(command);}catch(java.net.ConnectException expected){}
            check(discoveries[0]==1,"Offline command may discover before dispatch, without sending a POST");
            Connections.networkChanged();
            final int[] verified={0};String newHost="192.168.1.44";
            Connections discoverable=new Connections(isolated,(host,port,pin,token,path,method,payload,probe)->{
                if(host.equals(newHost)){check(pin.equals(b)&&path.equals("/api/heartbeat")&&method.equals("GET"),"Rediscovery proves existing peer identity with heartbeat");verified[0]++;return new JSONObject().put("ok",true);}throw new java.net.ConnectException("old route");
            },context->new org.json.JSONArray().put(new JSONObject().put("host","192.168.1.99").put("fingerprint",a)).put(new JSONObject().put("host",newHost).put("fingerprint",b)));
            check(discoverable.api(new JSONObject().put("pcId",b).put("path","/api/heartbeat").put("method","GET")).getBoolean("ok"),"Rediscovered GET completes in the same call");
            check(verified[0]==1&&c.active().getString("host").equals(newHost),"Only matching verified rediscovery updates route");
            final int[] posts={0};
            Connections ambiguous=new Connections(isolated,(host,port,pin,token,path,method,payload,probe)->{
                if(method.equals("GET"))return new JSONObject();posts[0]++;throw new java.net.SocketTimeoutException("response lost after accepting command");
            },context->{throw new Exception("Unexpected discovery after accepted POST");});
            try{ambiguous.api(command);throw new Exception("Ambiguous command reported success");}catch(java.net.SocketTimeoutException expected){}
            check(posts[0]==1,"Lost POST response never repeats the action on another route");
            Connections learning=new Connections(isolated,(host,port,pin,token,path,method,payload,probe)->new JSONObject().put("name","PC B").put("addresses",new org.json.JSONArray().put("8.8.8.8").put("bad").put("100.80.1.2").put("192.168.5.9").put("192.168.5.10")),context->new org.json.JSONArray());
            learning.api(new JSONObject().put("pcId",b).put("path","/api/heartbeat").put("method","GET"));
            check(c.active().getString("vpn").equals("100.80.1.2"),"Background heartbeat learns late VPN adapter");
            check(c.active().getJSONArray("routes").length()==3,"Multiple valid LAN routes retained, invalid addresses discarded individually");
            final int[] attempts={0};Connections.networkChanged();
            Connections poison=new Connections(isolated,(host,port,pin,token,path,method,payload,probe)->{
                if(host.equals("192.168.7.8"))return new JSONObject().put("ok",true);
                if(host.equals("192.168.7.7")){attempts[0]++;throw new javax.net.ssl.SSLHandshakeException("forged pin claim");}
                throw new java.net.ConnectException("unavailable");
            },context->new org.json.JSONArray().put(new JSONObject().put("host","192.168.7.7").put("fingerprint",b)).put(new JSONObject().put("host","192.168.7.8").put("fingerprint",b)));
            check(poison.api(new JSONObject().put("pcId",b).put("path","/api/heartbeat").put("method","GET")).getBoolean("ok")&&attempts[0]==1,"Forged discovery candidate cannot hide the next valid PC");
            check(c.active().getString("fingerprint").equals(b),"Discovery never replaces stored trust identity");
            c.put(new JSONObject().put("fingerprint",a).put("token","another-test-token").put("deviceId","another").put("host","192.168.1.21"));c.select(b);routes.clear();
            Connections switching=new Connections(isolated,(host,port,pin,token,path,method,payload,probe)->{routes.add(host);c.select(a);throw new java.net.ConnectException("switched during request");},context->new org.json.JSONArray());
            try{switching.api(command);throw new Exception("Switched request continued");}catch(Exception e){check(e.getMessage().contains("Cambiaste")&&routes.size()==1,"Changing PC stops retries toward previous PC");}
            c.forget();check(c.active().getString("id").equals(b),"Fixture PC removed without changing remaining peer");
            boolean oversize=false;try{MainActivity.request("127.0.0.1",47990,b,"","/api/media","POST",new JSONObject().put("data",new String(new char[140000]).replace('\0','x')),false);}catch(Exception e){oversize=e.getMessage().contains("grande");}
            check(oversize,"Oversize ordinary command rejected before transmission");
            WorkLanes lanes=new WorkLanes();java.util.concurrent.CountDownLatch held=new java.util.concurrent.CountDownLatch(4),release=new java.util.concurrent.CountDownLatch(1),localReady=new java.util.concurrent.CountDownLatch(1);
            try{
                for(int i=0;i<4;i++)lanes.submit("api",()->{held.countDown();try{release.await(5,java.util.concurrent.TimeUnit.SECONDS);}catch(InterruptedException ignored){}});
                check(held.await(2,java.util.concurrent.TimeUnit.SECONDS),"Four network tasks can be pending");
                for(int i=0;i<16;i++)lanes.submit("api",()->{});
                boolean limited=false;try{lanes.submit("api",()->{});}catch(java.util.concurrent.RejectedExecutionException expected){limited=true;}
                check(limited,"Network queue is bounded under saturation");
                lanes.submit("bootstrap",()->localReady.countDown());check(localReady.await(1,java.util.concurrent.TimeUnit.SECONDS),"Local connection management remains responsive under network saturation");
            }finally{release.countDown();lanes.close();}
            WorkLanes closing=new WorkLanes();java.util.concurrent.CountDownLatch writing=new java.util.concurrent.CountDownLatch(1),finishWrite=new java.util.concurrent.CountDownLatch(1),written=new java.util.concurrent.CountDownLatch(1);
            try{
                closing.submit("fileResult",()->{writing.countDown();try{finishWrite.await(3,java.util.concurrent.TimeUnit.SECONDS);}catch(InterruptedException e){return;}written.countDown();});
                check(writing.await(1,java.util.concurrent.TimeUnit.SECONDS),"File write started independently");closing.close();finishWrite.countDown();
                check(written.await(1,java.util.concurrent.TimeUnit.SECONDS),"Accepted file write finishes after Activity lanes close");
                boolean closed=false;try{closing.submit("fileResult",()->{});}catch(java.util.concurrent.RejectedExecutionException expected){closed=true;}check(closed,"Destroyed Activity cannot enqueue another file write");
            }finally{finishWrite.countDown();closing.close();}
            Context exportContext=new ContextWrapper(isolated){@Override public java.io.File getCacheDir(){return new java.io.File(super.getCacheDir(),prefix+"export-tests");}};
            ExportFiles exports=new ExportFiles(exportContext,null);String large=new String(new char[1200000]).replace('\0','x');exports.create(11,large);exports.create(14,"diagnostic fixture");
            check(exports.state().length()<300,"Large export keeps only tiny references in Activity state");
            boolean duplicate=false;try{exports.create(11,"wrong replacement");}catch(Exception expected){duplicate=true;}check(duplicate,"Same-type pending export cannot be overwritten");
            ExportFiles recreated=new ExportFiles(exportContext,exports.state());java.io.File profileCopy=recreated.take(11),reportCopy=recreated.take(14);
            check(profileCopy.length()==1200000,"Large export survives manager recreation from saved metadata");check(reportCopy.length()==18,"Report and profile exports remain separate");profileCopy.delete();reportCopy.delete();
            check(recreated.take(11)==null,"Consumed export cannot be reused accidentally");
            new java.io.File(exportContext.getCacheDir(),"deck-exports").delete();exportContext.getCacheDir().delete();
            if(args!=null&&args.containsKey("host")){
                String host=args.getString("host"),fp=args.getString("fingerprint");
                check(MainActivity.request(host,47990,fp,"","/health","GET",null,false).has("version"),"Real pinned TLS connection");
                boolean refused=false;
                try{MainActivity.request(host,47990,a,"","/health","GET",null,false);}catch(javax.net.ssl.SSLException e){refused=true;}
                check(refused,"Wrong certificate pin rejected on live connection");
            }
            int previousEvents=SupportReports.read(isolated).length();
            SupportReports.record(isolated,"api","failed",new Exception("Bearer private-secret https://private.example"));
            String diagnostic=SupportReports.snapshot(isolated,c).toString();
            check(new JSONObject(diagnostic).getString("version").equals(getTargetContext().getPackageManager().getPackageInfo(getTargetContext().getPackageName(),0).versionName),"Support report identifies installed version");
            check(!diagnostic.contains("private-secret")&&!diagnostic.contains("private.example")&&!diagnostic.contains("second-test-token"),"Support report excludes secrets and URLs");
            check(SupportReports.read(isolated).length()==previousEvents+1,"Failed action recorded");
            for(int i=0;i<110;i++)SupportReports.record(isolated,"test","ok",null);
            check(SupportReports.read(isolated).length()==100,"Support history bounded");
            check(SupportReports.snapshot(isolated,c).getInt("pairedPCs")==1,"Report records count without peer credentials");
            isolated.getSharedPreferences("deck-vault",0).edit().putString("encrypted","invalid").commit();
            check(!SupportReports.snapshot(isolated,c).getBoolean("vaultReadable"),"Broken vault can still generate a support report");
            check(isolated.getSharedPreferences("deck-vault",0).getString("encrypted","").equals("invalid"),"Diagnostics never deletes a broken vault");
            for(String name:new String[]{"connection","deck-vault","deck-options","deck-support"})isolated.getSharedPreferences(name,0).edit().clear().commit();
            result.putString("stream","\nPASS "+count+" Android assertions: Keystore encryption, migration, multiple PCs, stale command rejection, reopen, VPN hosts, background preference.\n");finish(-1,result);
        }catch(Exception e){result.putString("stream","FAIL: "+e.toString());finish(0,result);}
    }
}
