import copy, json, subprocess, sys, time, unittest
from unittest.mock import patch
from companion import launch_worker
from companion.jobs import Cancelled

class LaunchWorkerTests(unittest.TestCase):
    def test_timeout_reaps_real_owned_child(self):
        real=subprocess.Popen;children=[]
        def create(*args,**kwargs):
            child=real([sys.executable,'-c','import time;time.sleep(60)'],**kwargs);children.append(child);return child
        with patch('companion.launch_worker.subprocess.Popen',side_effect=create):
            with self.assertRaisesRegex(ValueError,'no terminó'):launch_worker.launch({},timeout=.1)
        self.assertEqual(len(children),1);self.assertIsNotNone(children[0].poll())
    def test_cancel_reaps_real_owned_child_before_return(self):
        real=subprocess.Popen;children=[];checks=0
        def create(*args,**kwargs):
            child=real([sys.executable,'-c','import time;time.sleep(60)'],**kwargs);children.append(child);return child
        def check():
            nonlocal checks;checks+=1
            if checks>2:raise Cancelled('fixture cancellation')
        with patch('companion.launch_worker.subprocess.Popen',side_effect=create):
            with self.assertRaises(Cancelled):launch_worker.launch({},check=check)
        self.assertIsNotNone(children[0].poll())
    def test_bad_reply_never_claims_launch(self):
        real=subprocess.Popen
        def create(command,**kwargs):
            dest=json.loads(command[-1])['result']
            return real([sys.executable,'-c',"from pathlib import Path;import sys;Path(sys.argv[1]).write_text('{}')",dest],**kwargs)
        with patch('companion.launch_worker.subprocess.Popen',side_effect=create):
            with self.assertRaisesRegex(ValueError,'no reconocido'):launch_worker.launch({})
    def test_reported_permission_failure_is_preserved(self):
        real=subprocess.Popen
        def create(command,**kwargs):
            dest=json.loads(command[-1])['result']
            return real([sys.executable,'-c',"from pathlib import Path;import sys;Path(sys.argv[1]).write_text('{\"error\":\"permission required\"}');sys.exit(2)",dest],**kwargs)
        with patch('companion.launch_worker.subprocess.Popen',side_effect=create):
            with self.assertRaisesRegex(ValueError,'permission required'):launch_worker.launch({})
    def test_long_request_rejected_without_process(self):
        with patch('companion.launch_worker.subprocess.Popen') as create:
            with self.assertRaises(ValueError):launch_worker.launch({'name':'x'*24000})
        create.assert_not_called()
