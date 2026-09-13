"""Own-thread Windows execution-state test; no power plan or display changes."""
import ctypes,json,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.awake import AwakeGuard,CONTINUOUS,SYSTEM_REQUIRED

def main():
    call=ctypes.WinDLL('kernel32',use_last_error=True).SetThreadExecutionState
    call.argtypes=[ctypes.c_uint];call.restype=ctypes.c_uint
    records=[];refreshed=threading.Event()
    def apply(flags):
        previous=call(flags)
        if not previous:raise ctypes.WinError(ctypes.get_last_error())
        records.append({'thread':threading.get_ident(),'requested':flags,'previous':previous})
        if flags&SYSTEM_REQUIRED and len(records)>=2:refreshed.set()
        if flags==CONTINUOUS:
            # Query the previous flags on the same owner after the explicit release.
            after=call(CONTINUOUS)
            records.append({'thread':threading.get_ident(),'requested':CONTINUOUS,'previous':after,'afterRelease':True})
    guard=AwakeGuard(apply,.1)
    try:
        guard.start();assert guard.status()['active'],guard.status()
        assert refreshed.wait(2),'No native refresh observed'
    finally:guard.close()
    checks={
      'singleOwnerThread':len({r['thread'] for r in records})==1,
      'requestPersistedOnOwner':bool(records[1]['previous']&SYSTEM_REQUIRED),
      'explicitReleaseOnOwner':records[-2]['requested']==CONTINUOUS,
      'noSystemRequirementAfterRelease':not records[-1]['previous']&SYSTEM_REQUIRED,
      'noDisplayOrAwayModeRequested':all(r['requested'] in (CONTINUOUS,CONTINUOUS|SYSTEM_REQUIRED) for r in records),
      'inactiveAfterClose':not guard.status()['active'],
    }
    report={'passed':all(checks.values()),'checks':checks,'observations':records,'scope':'Native API state on the test-owned thread; not a forced sleep or lid test','powerPlansChanged':False}
    (ROOT/'artifacts/beta4-native-awake-tests.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert report['passed'],checks
    print('PASS: six native execution-state checks; request released on its owner thread.')
if __name__=='__main__':main()
