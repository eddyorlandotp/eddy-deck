package com.eddy.deck;
import java.util.concurrent.*;

/** Local recovery and file choices cannot wait behind unavailable PC routes. */
final class WorkLanes {
    private final ExecutorService network=new ThreadPoolExecutor(4,4,0L,TimeUnit.MILLISECONDS,new ArrayBlockingQueue<Runnable>(16));
    private final ExecutorService local=new ThreadPoolExecutor(1,1,0L,TimeUnit.MILLISECONDS,new ArrayBlockingQueue<Runnable>(8));
    private final ExecutorService files=new ThreadPoolExecutor(1,1,0L,TimeUnit.MILLISECONDS,new ArrayBlockingQueue<Runnable>(4));
    void submit(String operation,Runnable task){
        if("fileResult".equals(operation)){files.execute(task);return;}
        boolean remote="api".equals(operation)||"probe".equals(operation)||"discover".equals(operation)||"pair".equals(operation)||"changeHost".equals(operation);
        (remote?network:local).execute(task);
    }
    // An Activity recreation must not abandon an already accepted file write.
    // These tasks only finish their selected URI; callbacks ignore a dead UI.
    void close(){network.shutdownNow();local.shutdownNow();files.shutdown();}
}
