"""Repeat synchronized real queue/journal failures; no real Windows side effects."""
import io,json,logging,sys,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.package_evidence import product_sources
from test_beta5 import Beta5Tests

def main():
    initial=product_sources();started=time.monotonic();cycles=30;total=0;failures=[]
    log=io.StringIO();before=logging.root.manager.disable;logging.disable(logging.CRITICAL)
    try:
        for cycle in range(cycles):
            suite=unittest.defaultTestLoader.loadTestsFromTestCase(Beta5Tests)
            result=unittest.TextTestRunner(stream=log,verbosity=1).run(suite);total+=result.testsRun
            failures.extend({'cycle':cycle+1,'test':test.id()} for test,_ in result.failures+result.errors)
            if failures:break
    finally:logging.disable(before)
    changed=[p for p,h in initial.items() if product_sources().get(p)!=h]
    data={'passed':not failures and not changed,'cycles':cycle+1,'testsRun':total,'elapsedSeconds':round(time.monotonic()-started,3),'failures':failures,'sourceHashes':initial,'sourceChangedDuringRun':changed,'physicalWindowsCommands':0,'scope':'Synchronized cancellation and repair disk failures, active/waiting routine, response lost before receiver reopening, four mid-routine topology policies. SQLite and queue real; OS and monitor effects synthetic. Repeated scheduling checks, not 300 distinct scenarios.'}
    (ROOT/'artifacts/beta5-daily-campaign.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    (ROOT/'artifacts/beta5-daily-campaign-tests.txt').write_text(log.getvalue(),encoding='utf-8')
    print(json.dumps({k:v for k,v in data.items() if k!='sourceHashes'}));assert data['passed']
if __name__=='__main__':main()
