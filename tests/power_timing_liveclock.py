"""Real elapsed-time confirmation tests with a fake Windows adapter.
The installed receiver and physical Windows power state are never touched.
"""
import json,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.core import Deck,VERSION,atomic_json
from test_core import FakeWindows

def main():
    records=[];output=ROOT/'artifacts/beta4-power-real-clock.json';start=time.monotonic()
    report={'version':VERSION,'status':'running','cases':records,'physicalPowerActions':0,'scope':'Real monotonic time, isolated data, fake Windows adapter'}
    with tempfile.TemporaryDirectory(prefix='eddy-power-clock-') as directory:
        fake=FakeWindows();deck=Deck(directory,ROOT,adapter=fake);observed=[]
        fake.power=lambda action:observed.append((action,time.monotonic()))
        def call(path,body):return deck.dispatch(path,{**body,'requestId':str(time.time_ns())},'local')
        try:
            for action in ('lock','sleep','shutdown','restart'):
                c=call('/api/power/prepare',{'action':action})['challenge'];before=time.monotonic()
                body={'challenge':c,'requestId':'repeat-confirm-'+action}
                first=deck.dispatch('/api/power/confirm',body,'local');again=deck.dispatch('/api/power/confirm',body,'local');assert first==again
                while len(observed)<len(records)+1 and time.monotonic()-before<20:time.sleep(.05)
                assert len(observed)==len(records)+1,'Missing or duplicate fake adapter dispatch'
                elapsed=observed[-1][1]-before;assert observed[-1][0]==action and 15<=elapsed<20,(action,elapsed)
                records.append({'action':action,'delaySeconds':round(elapsed,3),'duplicateConfirmationReplayedReceipt':True,'adapterCalls':1})
                report['elapsedSeconds']=round(time.monotonic()-start,2);atomic_json(output,report);print(json.dumps(records[-1]),flush=True)
            for delay in (0,2,10):
                c=call('/api/power/prepare',{'action':'lock'})['challenge'];call('/api/power/confirm',{'challenge':c});before=len(observed)
                time.sleep(delay);call('/api/power/cancel',{});time.sleep(.3)
                assert len(observed)==before and deck.pending is None
                records.append({'action':'cancel','afterSeconds':delay,'adapterCalls':0});atomic_json(output,report)
            report['status']='passed'
        except Exception as exc:report.update(status='failed',error=type(exc).__name__+': '+str(exc));raise
        finally:
            deck.close();report['elapsedSeconds']=round(time.monotonic()-start,2);atomic_json(output,report)
    print(json.dumps({k:v for k,v in report.items() if k!='cases'}),flush=True)
if __name__=='__main__':main()
