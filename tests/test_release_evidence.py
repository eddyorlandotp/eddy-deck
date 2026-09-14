"""Publication gate regressions using disposable reports, no real delivery."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.package_evidence import ROOT,validate_completed

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.version=patch('scripts.package_evidence.VERSION','2.2.2-beta.4');self.version.start();self.addCleanup(self.version.stop)
        self.tmp=tempfile.TemporaryDirectory(prefix='eddy-evidence-');self.out=Path(self.tmp.name)
        required={'beta2-soak-tests.json':7200,'beta2-soak-final-tests.json':4800,'beta2-background-tests.json':2400,'beta2-soak-final-source-tests.json':600,'beta3-resumed-soak-tests.json':9000,'beta4-soak-tests.json':7200,'beta4-soak-final-source-tests.json':5400,'beta4-installed-observation.json':8040,'beta4-network-soak-tests.json':1800,'beta4-postinstall-observation.json':90}
        required['beta4-concurrent-receipts-soak.json']=1800
        for name,seconds in required.items():self.write(name,{'status':'passed','elapsedSeconds':seconds,'unexpectedErrors':[]})
        hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'companion').glob('*.py')}
        self.change('beta4-soak-final-source-tests.json',requestedSeconds=5400,sourceHashes=hashes,sourceChangedDuringRun=[])
        self.write('beta4-lifecycle-soak-tests.json',{'passed':True,'cycles':120,'elapsedSeconds':3590})
    def tearDown(self):self.tmp.cleanup()
    def write(self,name,value):(self.out/name).write_text(json.dumps(value),encoding='utf-8')
    def change(self,name,**value):
        current=json.loads((self.out/name).read_text());current.update(value);self.write(name,current)
    def test_completed_reports_pass_without_creating_a_package(self):
        validate_completed(self.out);self.assertFalse(list(self.out.glob('*.zip')))
    def test_future_version_cannot_publish_only_historical_evidence(self):
        with patch('scripts.package_evidence.VERSION','999.0.0-beta.1'):
            with self.assertRaisesRegex(RuntimeError,'matriz de evidencias'):validate_completed(self.out)

    def test_beta11_cannot_publish_only_historical_evidence(self):
        with patch('scripts.package_evidence.VERSION','2.2.9-beta.11'):
            with self.assertRaisesRegex(RuntimeError,'informe válido de beta11'):validate_completed(self.out)
    def test_running_or_shortened_test_blocks_publication(self):
        for value in ({'status':'running'},{'elapsedSeconds':8999}):
            self.write('beta3-resumed-soak-tests.json',{'status':'passed','elapsedSeconds':9000,**value})
            with self.assertRaises(RuntimeError):validate_completed(self.out)
    def test_network_failures_block_publication(self):
        self.change('beta4-network-soak-tests.json',failures=['Fixture failure'])
        with self.assertRaises(RuntimeError):validate_completed(self.out)
    def test_final_source_requires_both_requested_and_elapsed_ninety_minutes(self):
        for elapsed,requested in ((600,600),(5399,5400),(5400,600)):
            self.change('beta4-soak-final-source-tests.json',elapsedSeconds=elapsed,requestedSeconds=requested)
            with self.assertRaises(RuntimeError):validate_completed(self.out)
    def test_stale_source_hashes_block_publication(self):
        self.change('beta4-soak-final-source-tests.json',sourceHashes={})
        with self.assertRaises(RuntimeError):validate_completed(self.out)
    def test_incomplete_phone_cycles_block_publication(self):
        self.change('beta4-lifecycle-soak-tests.json',cycles=45,elapsedSeconds=1324)
        with self.assertRaises(RuntimeError):validate_completed(self.out)
    def test_final_installed_observation_must_have_no_unplanned_issues(self):
        self.change('beta4-postinstall-observation.json',unplannedIssueSamples=1)
        with self.assertRaises(RuntimeError):validate_completed(self.out)
    def test_earlier_incident_requires_exact_review_and_observed_recovery(self):
        self.change('beta4-installed-observation.json',unplannedIssueSamples=1,samples=[{'atUTC':'first','issues':['fixture'],'maintenance':''},{'atUTC':'second','issues':[],'maintenance':''}])
        self.write('beta4-observation-incident-review.json',{'incidents':[{'observedAtUTC':'wrong','recoveredAtUTC':'second','resolution':'recovered'}]})
        with self.assertRaises(RuntimeError):validate_completed(self.out)
        self.write('beta4-observation-incident-review.json',{'incidents':[{'observedAtUTC':'first','recoveredAtUTC':'missing','resolution':'recovered'}]})
        with self.assertRaises(RuntimeError):validate_completed(self.out)
        self.write('beta4-observation-incident-review.json',{'incidents':[{'observedAtUTC':'first','recoveredAtUTC':'second','resolution':'recovered'}]})
        validate_completed(self.out)

if __name__=='__main__':unittest.main()
