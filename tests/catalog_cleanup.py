"""Normal-close only the fresh identities recorded by a catalog test."""
import argparse,json,time
from catalog_live import ROOT,identity,windows,process,g,win32process
from companion.layout import _matches,Windows
parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);args=parser.parse_args()
data=json.loads((ROOT/'.build/catalog-new-windows.json').read_text(encoding='utf-8'))
assert data['app']==args.name,'La captura pertenece a otra prueba.'
apps,_=windows.scan(ROOT/'companion');app=next(a for a in apps if a['name']==args.name)
layout=Windows();snapshot=layout.snapshot(apps);matched={layout.leases[w['id']]['hwnd'] for w in snapshot if app['id'] in w['appIds']}
results=[]
for hs,expected in data['windows'].items():
    h=int(hs)
    if not identity(h,expected):results.append({'window':h,'status':'already_closed_or_changed'});continue
    actual=process(win32process.GetWindowThreadProcessId(h)[1])
    if h not in matched:results.append({'window':h,'status':'unverified_owner_preserved'});continue
    g.PostMessage(h,0x10,0,0);time.sleep(1)
    results.append({'window':h,'status':'remains_needs_local_attention' if identity(h,expected) else 'closed'})
print(json.dumps(results))
with (ROOT/'artifacts/catalog-beta-cleanup-tests.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps({'app':args.name,'at':time.time(),'results':results})+'\n')
