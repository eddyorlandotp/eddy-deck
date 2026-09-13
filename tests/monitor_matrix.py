"""Deterministic display topology/geometry tests; never changes real monitors."""
import hashlib,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.layout import resolve_monitor,requested_size
from companion.core import VERSION

def main():
 rng=random.Random(20260911);checked=0;topologies=0
 for _ in range(1000):
  displays=[];x=-rng.randint(0,8000)
  for n in range(rng.randint(1,5)):
   width,height=rng.choice([(320,240),(800,600),(1366,768),(1920,1080),(2560,1440),(3840,2160),(1440,2560),(5120,1440)])
   scale=rng.choice([.75,1,1.25,1.5,2,3]);width=int(width*scale);height=int(height*scale);y=rng.randint(-3000,3000)
   displays.append({'id':'display:'+str(n),'bounds':[x,y,x+width,y+height],'work':[x,y,x+width,y+height-40],'primary':n==0,'vertical':height>width,'label':'Fixture '+str(n)});x+=width
  topologies+=1
  for role in ('left','right','vertical','primary','display:absent'):
   for fallback in ('stop','primary'):
    settings={'monitor':role,'mode':'windowed','missing':fallback}
    vertical=[d for d in displays if d['vertical']];missing=role=='display:absent' or (role=='vertical' and len(vertical)!=1)
    try:target,used=resolve_monitor(settings,displays)
    except ValueError:assert missing and fallback=='stop'
    else:
     assert target in displays
     if missing:assert fallback=='primary' and target['primary'] and used
     elif role=='left':assert target==displays[0] and not used
     elif role=='right':assert target==displays[-1] and not used
     elif role=='primary':assert target['primary'] and not used
    checked+=1
  for d in displays:
   width=d['work'][2]-d['work'][0];height=d['work'][3]-d['work'][1]
   for resize in (True,False):
    w,h=requested_size('windowed',resize,[-400,-800,2400,2000],width,height);assert 0<w<=width and 0<h<=height;checked+=1
  fixed={'monitor':displays[-1]['id'],'mode':'maximized','missing':'stop'}
  target,_=resolve_monitor(fixed,displays);assert target==displays[-1]
  try:resolve_monitor(fixed,displays[:-1])
  except ValueError:pass
  else:raise AssertionError('Removed monitor accepted')
  checked+=2
 for role in ('keep','primary','left','right','vertical'):
  try:resolve_monitor({'monitor':role,'missing':'primary'},[])
  except ValueError:checked+=1
  else:raise AssertionError('Missing desktop accepted')
 result={'version':VERSION,'layoutSourceSHA256':hashlib.sha256((ROOT/'companion/layout.py').read_bytes()).hexdigest(),'topologies':topologies,'assertions':checked,'passed':True,'seed':20260911,'realMonitorSettingsChanged':False,'scope':'Geometry, one-to-five displays, negative coordinates, simulated scale, absent and ambiguous targets. No physical hot-plug or actual DPI changes.'}
 (ROOT/'artifacts'/('beta'+VERSION.rsplit('beta.',1)[-1]+'-monitor-tests.json')).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
