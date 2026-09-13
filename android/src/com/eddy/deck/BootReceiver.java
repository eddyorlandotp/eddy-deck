package com.eddy.deck;
import android.content.*;
public class BootReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context,Intent intent){
        if(!Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())&&!Intent.ACTION_MY_PACKAGE_REPLACED.equals(intent.getAction()))return;
        if(new Connections(context).background())try{context.startForegroundService(new Intent(context,ConnectionService.class));}catch(RuntimeException ignored){/* Android may require reopening the app. */}
    }
}
