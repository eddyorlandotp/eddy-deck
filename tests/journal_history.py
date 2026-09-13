"""Replay and latency with a large historical receipt DB; no real PC actions."""
import json,statistics,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.jobs import Journal
from companion.core import VERSION

def main():
    with tempfile.TemporaryDirectory() as folder:
        journal=Journal(folder);calls=[];body={'requestId':'original-operation','action':'next'}
        expected=journal.invoke('/api/media',body,'fixture',lambda:(calls.append('sent') or {'status':'fixture'}))
        history=100000;past=time.time()-86400
        with journal.connect() as db:
            db.executemany('INSERT INTO receipts VALUES(?,?,?,?,?,?)',(('fixture','history-'+str(i),'synthetic-digest','{"status":"fixture"}',200,past-i) for i in range(history)))
        journal=Journal(folder)
        replay=journal.invoke('/api/media',body,'fixture',lambda:(calls.append('duplicate') or {}))
        assert replay==expected and calls==['sent']
        elapsed=[]
        for i in range(30):
            start=time.perf_counter()
            journal.invoke('/api/media',{'requestId':'current-operation-'+str(i)},'fixture',lambda:{'status':'fixture'})
            elapsed.append((time.perf_counter()-start)*1000)
        with journal.connect() as db:
            count=db.execute('SELECT count(*) FROM receipts').fetchone()[0]
            assert count==history+31
        report={'historicalReceipts':history,'oldReceiptSurvivedRestart':True,'oldOperationExecutedOnce':True,'newOperationsMeasured':len(elapsed),'latencyMillisecondsMedian':round(statistics.median(elapsed),3),'latencyMillisecondsMaximum':round(max(elapsed),3),'databaseBytes':journal.path.stat().st_size,'physicalActions':0,'allReceiptsPreserved':True}
    (ROOT/'artifacts'/('beta'+VERSION.rsplit('beta.',1)[-1]+'-journal-history-tests.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
