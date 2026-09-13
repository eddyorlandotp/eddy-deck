"""Every discovered ordinary catalog app through isolated HTTP card CRUD."""
from pathlib import Path
import json,sys,tempfile,http.client,threading,uuid,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion.core import Deck,Server,validate_profile,VERSION
from companion.windows import scan
ROOT=Path(__file__).resolve().parents[1]
def main():
    apps,warnings=scan(ROOT/'companion');rows=[]
    with tempfile.TemporaryDirectory() as folder:
        deck=Deck(folder,ROOT,dry_run=True);deck.apps=apps
        server=Server(('127.0.0.1',0),deck,True);threading.Thread(target=server.serve_forever,daemon=True).start()
        def call(path,body):
            c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
            c.request('POST',path,json.dumps({**body,'requestId':uuid.uuid4().hex}),{'Authorization':'Bearer '+deck.local_token,'Content-Type':'application/json'})
            r=c.getresponse();value=json.loads(r.read());c.close()
            assert r.status==200,(r.status,value)
            return value
        try:
            for app in apps:
                if not app.get('available',True):rows.append({'name':app['name'],'status':'unavailable'});continue
                body={'appId':app['id'],'name':'QA '+app['name'],'color':'mint','ifOpen':'launch','layout':{'monitor':'right','mode':'windowed'}}
                if app['browser']:body['url']='https://example.com/eddy-deck-test'
                card=call('/api/cards/save',body)['card'];assert card['appId']==app['id']
                call('/api/cards/save',{**body,'id':card['id'],'name':'Actualizada','layout':{'monitor':'ask','mode':'keep'}})
                saved=validate_profile(json.loads((Path(folder)/'deck.json').read_text(encoding='utf-8')))
                assert saved['cards'][-1]['layout']['monitor']=='ask'
                assert saved['cards'][-1]['ifOpen']=='launch'
                call('/api/cards/delete',{'id':card['id']});assert not deck.profile['cards']
                rows.append({'name':app['name'],'status':'create_edit_persist_delete_passed'})
                if len(rows)%20==0:print('Verified',len(rows),'catalog entries',flush=True)
                time.sleep(1.1) # respect the real per-device limit of 180 actions/minute
        finally:server.shutdown();server.server_close();deck.close()
    (ROOT/'artifacts'/('catalog-beta'+VERSION.rsplit('beta.',1)[-1]+'-crud.json')).write_text(json.dumps({'version':VERSION,'rows':rows,'warnings':warnings,'productionProfileModified':False,'applicationsLaunched':0},ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS HTTP create/edit/save/delete for',len(rows),'catalog entries in an isolated profile.')
if __name__=='__main__':main()
