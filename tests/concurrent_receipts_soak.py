"""Seeded concurrent receipt/restart test; work is an in-memory fake counter."""
import argparse,concurrent.futures,datetime,hashlib,json,random,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.jobs import Journal,ReceiptError
from companion.core import VERSION,atomic_json

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=1800);parser.add_argument('--report',default='beta4-concurrent-receipts-soak.json');args=parser.parse_args()
    if not 1<=args.seconds<=3600 or Path(args.report).name!=args.report:raise ValueError('Bounded duration and plain report name required')
    rng=random.Random(20260912);started=time.monotonic();counter={};lock=threading.Lock()
    result={'version':VERSION,'status':'running','startedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'requestedSeconds':args.seconds,'seed':20260912,'cycles':0,'submissions':0,'inProgressResponses':0,'conflictsRejected':0,'replaysVerified':0,'restarts':0,'fakeExecutions':0,'failures':[],'physicalCommandsSent':0,'sourceHashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'companion').glob('*.py')},'scope':'Eight concurrent callers, identical receipt IDs, changed payload conflicts, device isolation, restart replay; actual Journal with fake effects, no Windows control.'}
    output=ROOT/'artifacts'/args.report
    with tempfile.TemporaryDirectory(prefix='eddy-receipt-stress-') as folder:
        journal=Journal(folder)
        def invoke(device,body):
            key=(device,body['requestId'])
            def work():
                with lock:counter[key]=counter.get(key,0)+1
                time.sleep(.003)
                return {'value':body['value']}
            return journal.invoke('/fixture/action',body,device,work)
        try:
            while time.monotonic()-started<args.seconds:
                batch=time.monotonic();cycle=result['cycles']
                originals=[{'requestId':f'fixture-{cycle:04d}-{n:03d}','value':n} for n in range(50)]
                submissions=[dict(body) for body in originals for _ in range(rng.randint(2,6))];rng.shuffle(submissions)
                def submit(body):
                    try:
                        value=invoke('fixture-device-a',body)
                        assert value=={'value':body['value']}
                        return 'received'
                    except ReceiptError as exc:
                        # Only an identical request currently executing may be pending.
                        assert exc.status==409 and 'curso' in str(exc)
                        return 'inProgress'
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:responses=list(pool.map(submit,submissions))
                result['submissions']+=len(responses);result['inProgressResponses']+=responses.count('inProgress')
                for body in originals:
                    assert invoke('fixture-device-a',body)=={'value':body['value']}
                    assert counter[('fixture-device-a',body['requestId'])]==1
                    try:invoke('fixture-device-a',{**body,'value':-1})
                    except ReceiptError as exc:assert exc.status==409;result['conflictsRejected']+=1
                    else:raise AssertionError('Changed payload reused a receipt')
                # The same ID on another device is a separate, authorized namespace.
                for body in originals[:5]:
                    assert invoke('fixture-device-b',body)=={'value':body['value']}
                    assert counter[('fixture-device-b',body['requestId'])]==1
                before=dict(counter);journal=Journal(folder);result['restarts']+=1
                for body in originals:
                    assert invoke('fixture-device-a',body)=={'value':body['value']};result['replaysVerified']+=1
                for body in originals[:5]:assert invoke('fixture-device-b',body)=={'value':body['value']};result['replaysVerified']+=1
                assert counter==before and all(n==1 for n in counter.values())
                result['cycles']+=1;result['fakeExecutions']=len(counter);result['elapsedSeconds']=round(time.monotonic()-started,3);atomic_json(output,result)
                print(json.dumps({k:result[k] for k in ('cycles','elapsedSeconds','submissions','inProgressResponses','fakeExecutions')}),flush=True)
                pause=min(45-(time.monotonic()-batch),args.seconds-(time.monotonic()-started))
                if pause>0:time.sleep(pause)
            result['status']='passed'
        except Exception as exc:result['status']='failed';result['failures'].append(type(exc).__name__+': '+str(exc));raise
        finally:
            result['elapsedSeconds']=round(time.monotonic()-started,3)
            result['sourceChangedDuringRun']=[name for name,digest in result['sourceHashes'].items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
            atomic_json(output,result);print(json.dumps({k:v for k,v in result.items() if k!='sourceHashes'}),flush=True)

if __name__=='__main__':main()
