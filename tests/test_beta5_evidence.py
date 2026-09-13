import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.package_evidence import product_sources,validate_completed

class Beta5EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.out=Path(self.tmp.name)
        self.version=patch('scripts.package_evidence.VERSION','2.2.3-beta.5');self.version.start();self.addCleanup(self.version.stop)
        self.write('daily-campaign',{'passed':True,'cycles':30,'testsRun':300,'sourceHashes':product_sources(),'failures':[],'sourceChangedDuringRun':[]})
        self.write('core-tests',{'passed':True,'testsRun':162,'sourceHashes':product_sources()})
        self.write('ui-combined-tests',{'passed':True,'count':7,'sourceSHA256':product_sources()[str(Path('ui')/'extended.js')]})
        self.write('postinstall-observation',{'status':'completed','elapsedSeconds':90,'samplesWithIssues':0,'samples':[{'version':'2.2.3-beta.5'}]})
        self.write('android-installed-tests',{'passed':True,'installedVersion':'2.2.3-beta.5','cycles':3,'checks':24,'basicAssertions':56})
        self.write('release-verification',{'version':'2.2.3-beta.5','releaseVerified':True,'installedIntegrityVerified':True,'profileAndPairingPreserved':True,'phoneReconnectedAfterUpdate':True})
        self.write('final-device-verification',{'version':'2.2.3-beta.5','installedApkMatches':True,'phoneWindowsInstallerMatches':True,'phoneDocumentationMatches':True})
    def tearDown(self):self.tmp.cleanup()
    def write(self,name,data):(self.out/('beta5-'+name+'.json')).write_text(json.dumps(data),encoding='utf-8')
    def change(self,name,**data):
        value=json.loads((self.out/('beta5-'+name+'.json')).read_text());value.update(data);self.write(name,value)
    def test_current_complete_evidence_passes(self):validate_completed(self.out)
    def test_stale_campaign_or_failed_iteration_blocks_release(self):
        baseline=json.loads((self.out/'beta5-daily-campaign.json').read_text())
        for changes in ({'sourceHashes':{}},{'cycles':29},{'failures':[{'test':'fixture'}]}):
            with self.subTest(changes=changes):
                self.write('daily-campaign',baseline)
                self.change('daily-campaign',**changes)
                with self.assertRaises(RuntimeError):validate_completed(self.out)
    def test_stale_ui_code_blocks_release(self):
        self.change('ui-combined-tests',sourceSHA256='old')
        with self.assertRaises(RuntimeError):validate_completed(self.out)
    def test_old_android_version_blocks_release(self):
        self.change('android-installed-tests',installedVersion='2.2.2-beta.4')
        with self.assertRaises(RuntimeError):validate_completed(self.out)
    def test_observation_without_samples_or_with_incidents_blocks_release(self):
        baseline=json.loads((self.out/'beta5-postinstall-observation.json').read_text())
        for changes in ({'samples':[]},{'samplesWithIssues':1}):
            self.write('postinstall-observation',baseline)
            self.change('postinstall-observation',**changes)
            with self.assertRaises(RuntimeError):validate_completed(self.out)
    def test_missing_phone_or_receiver_verification_blocks_release(self):
        self.change('final-device-verification',installedApkMatches=False)
        with self.assertRaises(RuntimeError):validate_completed(self.out)

if __name__=='__main__':unittest.main()
