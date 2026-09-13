"""Validate recovery profiles with the packaged EXE, without changing user data."""
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from companion.core import VERSION

def main():
 exe=ROOT/'artifacts/windows/EddyDeck/EddyDeck.exe';data=Path(os.environ['LOCALAPPDATA'])/'EddyDeck';names=['deck.json','devices.json','server.crt'];before={n:hashlib.sha256((data/n).read_bytes()).hexdigest() for n in names};cases=[]
 with tempfile.TemporaryDirectory() as folder:
  for name,body,expected in [('valid-empty',{'version':2,'cards':[],'scenes':[]},0),('wrong-version',{'version':999,'cards':[],'scenes':[]},1),('commands-forbidden',{'version':2,'cards':[],'scenes':[{'id':'x','name':'no','steps':[{'type':'command','command':'anything'}]}]},1),('malformed','broken-json',1)]:
   file=Path(folder)/(name+'.json');file.write_text(body if isinstance(body,str) else json.dumps(body),encoding='utf-8')
   r=subprocess.run([str(exe),'--validate-profile',str(file)],timeout=20,creationflags=0x08000000);assert r.returncode==expected,(name,r.returncode)
   cases.append({'case':name,'passed':True,'exitCode':r.returncode})
 assert before=={n:hashlib.sha256((data/n).read_bytes()).hexdigest() for n in names}
 (ROOT/'artifacts'/('beta'+VERSION.rsplit('beta.',1)[-1]+'-profile-validator-tests.json')).write_text(json.dumps({'checks':cases,'productionDataUnchanged':True},indent=2));print(json.dumps({'checks':len(cases),'productionDataUnchanged':True}))
if __name__=='__main__':main()
