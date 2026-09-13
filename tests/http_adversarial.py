"""Bounded fault injection into an isolated local receiver; no external targets."""
import copy,http.client,json,socket,ssl,sys,tempfile,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.core import Deck,start,VERSION
from test_core import APP,FakeWindows

def main():
 results=[];errors=[]
 with tempfile.TemporaryDirectory() as folder:
  fake=FakeWindows();d=Deck(folder,ROOT,adapter=fake);d.apps=[copy.deepcopy(APP)];start(d,local_port=0,port=0,bind='127.0.0.1')
  def send(path,raw,auth=True,extra=None,headers_only=False):
   c=http.client.HTTPConnection('127.0.0.1',d.local_port,timeout=4)
   h={'Content-Type':'application/json'}
   if auth:h['Authorization']='Bearer '+d.local_token
   h.update(extra or {})
   try:
    if headers_only:h['Content-Length']=str(len(raw));c.request('POST',path,None,h)
    else:c.request('POST',path,raw,h)
    r=c.getresponse();value=r.read();return r.status,value
   finally:c.close()
  try:
   cases=[('malformed-json','/api/cards/save',b'{',400),('invalid-unicode','/api/cards/save',b'{"x":"\xff"}',400),('nested-json','/api/cards/save',('['*10000+'0'+']'*10000).encode(),400),('array-root','/api/scenes/save',b'[]',400),('null-root','/api/scenes/save',b'null',400),('ordinary-body-limit','/api/media',b'x'*131073,413),('unauthenticated-import','/api/backup/import',b'{}',401)]
   for case,path,raw,expected in cases:
    print('Checking',case,flush=True)
    code,body=send(path,raw,auth=case!='unauthenticated-import',headers_only=case=='ordinary-body-limit');okay=code==expected;results.append({'case':case,'status':code,'passed':okay})
    if not okay:errors.append(case)
   # An HTTP server may close immediately after rejecting an oversized body.
   # A streaming sender can observe a reset instead of reading that 413.
   for i in range(5):
    try:code,_=send('/api/media',b'x'*131073);okay=code==413
    except (ConnectionResetError,ConnectionAbortedError,BrokenPipeError):code='transport-closed';okay=True
    results.append({'case':'oversized-stream-rejected-'+str(i),'status':code,'passed':okay})
    if not okay:errors.append('oversized-stream-rejected-'+str(i))
   endpoints={'/api/cards/save':[None,[],{},True,3],'/api/scenes/save':[None,[],{},True,3],'/api/launch':[None,[],{},True,3]}
   for endpoint,values in endpoints.items():
    for field in ('appId','layout','url','steps','onError'):
     for value in values:
      body={'requestId':uuid.uuid4().hex,'appId':'nonexistent','name':'Fuzz','steps':[{'appId':'nonexistent'}],field:value}
      code,_=send(endpoint,json.dumps(body).encode());okay=400<=code<500;results.append({'case':endpoint+':'+field+':'+type(value).__name__,'status':code,'passed':okay})
      if not okay:errors.append(results[-1]['case'])
   # The largest common preset (50 x 24 steps) is valid and larger than 128 KiB.
   profile={'version':2,'cards':[],'scenes':[{'id':'r'+str(i),'name':'Large routine','steps':[{'appId':APP['id'],'url':'https://example.com/'+('a'*300)} for _ in range(24)]} for i in range(50)]}
   raw=json.dumps({'requestId':uuid.uuid4().hex,'profile':profile}).encode();assert len(raw)>131072
   code,body=send('/api/backup/import',raw);okay=code==200 and len(d.profile['scenes'])==50;results.append({'case':'large-valid-import','bytes':len(raw),'status':code,'passed':okay})
   if not okay:errors.append('large-valid-import')
   stalled=[]
   try:
    for _ in range(24):stalled.append(socket.create_connection(('127.0.0.1',d.port),timeout=2));time.sleep(.02)
    c=http.client.HTTPConnection('127.0.0.1',d.local_port,timeout=3);c.request('GET','/health');r=c.getresponse();r.read();okay=r.status==200;c.close();results.append({'case':'24-incomplete-tls-clients-local-health-responsive','passed':okay})
    if not okay:errors.append('TLS starvation')
   finally:
    for s in stalled:s.close()
   context=ssl.create_default_context(cafile=str(Path(folder)/'server.crt'));until=time.monotonic()+5;recovered=False
   while time.monotonic()<until:
    try:
     c=http.client.HTTPSConnection('127.0.0.1',d.port,context=context,timeout=2);c.request('GET','/health');r=c.getresponse();r.read();recovered=r.status==200;c.close()
     if recovered:break
    except (OSError,http.client.HTTPException):time.sleep(.1)
   results.append({'case':'tls-capacity-recovers-after-stalled-clients-close','passed':recovered})
   if not recovered:errors.append('TLS recovery')
   assert not fake.calls
  finally:d.close()
 report={'checks':results,'count':len(results),'failures':errors,'physicalActions':0,'isolatedReceiver':True}
 (ROOT/'artifacts'/('beta'+VERSION.rsplit('beta.',1)[-1]+'-http-tests.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'checks':len(results),'failures':errors}));assert not errors
if __name__=='__main__':main()
