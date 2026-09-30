package com.eddy.deck;
import android.app.*;
import android.content.Intent;
import android.os.IBinder;
import android.net.*;
import org.json.JSONObject;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** User-enabled service. Checks state and reacts to network changes; no commands. */
public class ConnectionService extends Service {
    private ScheduledExecutorService timer;
    private Connections connections;
    private ConnectivityManager manager;
    private ConnectivityManager.NetworkCallback networkCallback;
    private final AtomicBoolean kickPending=new AtomicBoolean(false);
    private volatile boolean destroyed=false;
    @Override public void onCreate(){
        super.onCreate();connections=new Connections(this);
        NotificationManager nm=getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("connection","Conexión con tus computadoras",NotificationManager.IMPORTANCE_LOW));
        startForeground(24,notification("Comprobando conexión…"));
        timer=Executors.newSingleThreadScheduledExecutor();timer.scheduleWithFixedDelay(()->check(),0,25,TimeUnit.SECONDS);
        manager=getSystemService(ConnectivityManager.class);
        networkCallback=new ConnectivityManager.NetworkCallback(){
            @Override public void onAvailable(Network n){Connections.networkChanged();kick();}
            @Override public void onLost(Network n){Connections.networkChanged();kick();}
            @Override public void onCapabilitiesChanged(Network n,NetworkCapabilities c){kick();}
        };
        try{manager.registerDefaultNetworkCallback(networkCallback);}catch(RuntimeException e){networkCallback=null;SupportReports.record(this,"network-monitor","unavailable",e);}
    }
    private void kick(){
        if(destroyed||!kickPending.compareAndSet(false,true))return;
        try{timer.schedule(()->{kickPending.set(false);check();},1,TimeUnit.SECONDS);}catch(RejectedExecutionException ignored){kickPending.set(false);}
    }
    private void check(){
        if(destroyed)return;
        if(!connections.background()){stopSelf();return;}
        String text="Sin PC vinculada",error="";
        try{
            JSONObject boot=connections.bootstrap();
            if(boot.optBoolean("paired")){
                JSONObject s=connections.api(new JSONObject().put("pcId",boot.getString("pcId")).put("path","/api/heartbeat").put("method","GET"));
                text="Conectado · "+s.optString("name","Tu PC");
            }
        }catch(Exception e){
            SupportReports.record(this,"background-connect","failed",e);error=e.getMessage();
            if(e instanceof Connections.Unreachable)text=((Connections.Unreachable)e).brief;
            else if(e instanceof javax.net.ssl.SSLException)text="Respondió otra copia de Eddy Deck · revisa la PC";
            else text="Esperando a tu PC · reintento automático";
        }
        if(destroyed)return;
        getSharedPreferences("deck-options",0).edit().putString("backgroundError",error).putString("backgroundStatus",text).putLong("backgroundAt",System.currentTimeMillis()).apply();
        getSystemService(NotificationManager.class).notify(24,notification(text));
    }
    private Notification notification(String text){
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Intent stop=new Intent(this,ConnectionService.class).setAction("stop");
        PendingIntent cancel=PendingIntent.getService(this,1,stop,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this,"connection").setSmallIcon(R.drawable.ic_launcher).setContentTitle("Eddy Deck").setContentText(text).setContentIntent(open).setOngoing(true).setOnlyAlertOnce(true).addAction(new Notification.Action.Builder(null,"Desconectar en segundo plano",cancel).build()).build();
    }
    @Override public int onStartCommand(Intent intent,int flags,int id){
        if(intent!=null&&"stop".equals(intent.getAction())){connections.background(false);stopForeground(true);stopSelf();return START_NOT_STICKY;}
        if(!connections.background()){stopSelf();return START_NOT_STICKY;}
        return START_STICKY;
    }
    @Override public IBinder onBind(Intent i){return null;}
    @Override public void onDestroy(){destroyed=true;if(networkCallback!=null)try{manager.unregisterNetworkCallback(networkCallback);}catch(RuntimeException ignored){}if(timer!=null)timer.shutdownNow();stopForeground(true);super.onDestroy();}
}
