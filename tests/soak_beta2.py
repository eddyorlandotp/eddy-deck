"""Bounded long-duration routine stress, with isolated data and fake OS effects.
Runs against the actual receipt/queue/profile implementation; never controls PC.
"""
import argparse,concurrent.futures,copy,hashlib,json,sys,tempfile,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.core import Deck,APIError,VERSION,atomic_json
from test_core import APP,FakeWindows

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=7200);parser.add_argument('--report',default='beta2-soak-tests.json');args=parser.parse_args()
    if Path(args.report).name!=args.report or not args.report.endswith('.json'):raise ValueError('Usa un nombre de informe JSON dentro de artifacts.')
    started=time.monotonic();metrics={'version':VERSION,'requestedSeconds':args.seconds,'cycles':0,'requests':0,'duplicateSubmissions':0,'cancelledWithoutExecution':0,'restarts':0,'faultsRejected':0,'unexpectedErrors':[],'status':'running'}
    code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'companion').glob('*.py')}
    metrics['sourceHashes']=code
    out=ROOT/'artifacts'/args.report
    with tempfile.TemporaryDirectory(prefix='eddydeck-soak-') as folder:
        fake=FakeWindows();deck=Deck(folder,ROOT,adapter=fake);deck.apps=[copy.deepcopy(APP)]
        def call(path,body,rid=None):
            metrics['requests']+=1
            return deck.dispatch(path,{**body,'requestId':rid or uuid.uuid4().hex},'local')
        def wait(jid):
            end=time.monotonic()+4
            while time.monotonic()<end:
                j=next(j for j in deck.journal.jobs() if j['id']==jid)
                if j['status'] not in ('queued','running'):return j
                time.sleep(.005)
            raise AssertionError('Queue stalled')
        try:
            sid=None
            while time.monotonic()-started<args.seconds:
                cycle=time.monotonic();i=metrics['cycles']
                steps=[{'appId':APP['id'],'url':'https://test.invalid/first'},{'type':'wait','seconds':.03},{'appId':APP['id'],'url':'https://test.invalid/second'}]
                call('/api/scenes/save',{'id':sid,'name':'Soak routine','steps':steps,'onError':'stop'});sid=deck.profile['scenes'][0]['id']
                deck.queue.pause(True)
                before=len(fake.calls)
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                    submitted=list(pool.map(lambda _:call('/api/scenes/run',{'id':sid}),range(5)))
                assert len({r['jobId'] for r in submitted})==1
                metrics['duplicateSubmissions']+=4
                held=call('/api/launch',{'appId':APP['id'],'url':'https://test.invalid/cancel'})
                call('/api/jobs/cancel',{'id':held['jobId']});assert wait(held['jobId'])['status']=='cancelled'
                metrics['cancelledWithoutExecution']+=1
                deck.queue.pause(False);assert wait(submitted[0]['jobId'])['status']=='completed'
                assert [c[2] for c in fake.calls[before:]]==['https://test.invalid/first','https://test.invalid/second']
                rid=uuid.uuid4().hex;body={'action':'next','target':'system'}
                call('/api/media',body,rid);n=len(fake.calls);call('/api/media',body,rid);assert len(fake.calls)==n
                try:call('/api/scenes/save',{'name':'invalid','steps':[{'type':'windowTerminate','windowId':'invented'}]})
                except (ValueError,APIError):metrics['faultsRejected']+=1
                else:raise AssertionError('Unsafe routine type accepted')
                if i%30==29:
                    profile=copy.deepcopy(deck.profile);deck.close();deck=Deck(folder,ROOT,adapter=fake);deck.apps=[copy.deepcopy(APP)]
                    assert deck.profile==profile
                    call('/api/media',body,rid);assert len(fake.calls)==n
                    metrics['restarts']+=1
                assert deck.queue.status()['healthy']
                metrics['cycles']+=1;metrics['elapsedSeconds']=round(time.monotonic()-started,1)
                atomic_json(out,metrics)
                if metrics['cycles']%5==0:print(json.dumps({'cycles':metrics['cycles'],'elapsedSeconds':metrics['elapsedSeconds'],'requests':metrics['requests']}),flush=True)
                # Stay below the real 180 actions/minute rate limit.
                remaining=min(12-(time.monotonic()-cycle),args.seconds-(time.monotonic()-started))
                if remaining>0:time.sleep(remaining)
        except Exception as e:
            metrics['unexpectedErrors'].append(type(e).__name__+': '+str(e));metrics['status']='failed';raise
        finally:
            deck.close();metrics['elapsedSeconds']=round(time.monotonic()-started,1)
            if metrics['status']!='failed':metrics['status']='passed'
            metrics['sourceChangedDuringRun']=[name for name,digest in code.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
            atomic_json(out,metrics);print(json.dumps(metrics),flush=True)
if __name__=='__main__':main()
