"""Timed TLS/resource regression against a new loopback-only disposable server.

At most 16 deliberately incomplete connections; never targets the installed
receiver or an external host. Requests with a fixture token only read heartbeat.
"""
import argparse,datetime as dt,hashlib,http.client,json,secrets,socket,ssl,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.core import Deck,start,VERSION,atomic_json
from test_core import FakeWindows

def main():
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=1800);a=p.parse_args()
    if not 30<=a.seconds<=3600:raise ValueError('Duration must be 30..3600 seconds')
    clock=time.monotonic();latencies=[];observations=[];fake=FakeWindows()
    result={'version':VERSION,'status':'running','startedAtUTC':dt.datetime.now(dt.timezone.utc).isoformat(),'requestedSeconds':a.seconds,'cycles':0,'authenticatedReads':0,'failures':[],'physicalCommandsSent':0,'target':'disposable loopback TLS receiver','maximumIncompleteClients':16}
    code={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in (ROOT/'companion').glob('*.py')};result['sourceHashes']=code
    output=ROOT/'artifacts/beta4-network-soak-tests.json'
    with tempfile.TemporaryDirectory(prefix='eddy-network-soak-') as folder:
        d=Deck(folder,ROOT,adapter=fake);token=secrets.token_urlsafe(32)
        d.devices=[{'id':'isolated-network-peer','name':'Fixture','hash':hashlib.sha256(token.encode()).hexdigest()}]
        start(d,local_port=0,port=0,bind='127.0.0.1')
        context=ssl.create_default_context(cafile=str(Path(folder)/'server.crt'))
        def heartbeat():
            before=time.monotonic();c=http.client.HTTPSConnection('127.0.0.1',d.port,context=context,timeout=4)
            try:
                c.request('GET','/api/heartbeat',headers={'Authorization':'Bearer '+token});r=c.getresponse();body=json.loads(r.read())
                assert r.status==200 and body['version']==VERSION
                latencies.append(time.monotonic()-before);result['authenticatedReads']+=1
            finally:c.close()
        try:
            while time.monotonic()-clock<a.seconds:
                incomplete=[];cycle=time.monotonic()
                try:
                    for _ in range(8):incomplete.append(socket.create_connection(('127.0.0.1',d.port),timeout=2))
                    for _ in range(8):
                        tcp=socket.create_connection(('127.0.0.1',d.port),timeout=2)
                        try:tls=context.wrap_socket(tcp,server_hostname='localhost')
                        except Exception:tcp.close();raise
                        incomplete.append(tls)
                        # Partial header exercises read deadlines before any dispatch.
                        tls.sendall(b'GET /api/heartbeat HTTP/1.1\r\nHost: localhost\r\n')
                    for _ in range(11):heartbeat();time.sleep(1)
                    observations.append({'elapsedSeconds':round(time.monotonic()-clock,1),'threadsAfterDeadline':threading.active_count(),'queueHealthy':d.queue.status()['healthy']})
                    assert d.queue.status()['healthy'] and not fake.calls
                finally:
                    for connection in incomplete:connection.close()
                result['cycles']+=1;result['elapsedSeconds']=round(time.monotonic()-clock,1)
                result['observations']=observations;atomic_json(output,result)
                if result['cycles']%5==0:print(json.dumps({k:result[k] for k in ('status','cycles','elapsedSeconds','authenticatedReads')}),flush=True)
                pause=min(15-(time.monotonic()-cycle),a.seconds-(time.monotonic()-clock))
                if pause>0:time.sleep(pause)
            heartbeat();result['status']='passed'
        except Exception as exc:result['status']='failed';result['failures'].append(type(exc).__name__+': '+str(exc));raise
        finally:
            d.close();result['elapsedSeconds']=round(time.monotonic()-clock,1)
            result['sourceChangedDuringRun']=[name for name,digest in code.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
            if latencies:
                ordered=sorted(latencies);result['latencySeconds']={'median':round(ordered[len(ordered)//2],4),'p95':round(ordered[int((len(ordered)-1)*.95)],4),'maximum':round(max(ordered),4)}
            result['observations']=observations;atomic_json(output,result)
            print(json.dumps({k:v for k,v in result.items() if k not in ('observations','sourceHashes')}),flush=True)

if __name__=='__main__':main()
