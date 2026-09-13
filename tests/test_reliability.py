import copy,threading,time,tempfile,unittest
from companion.core import Deck,APIError,validate_profile
from companion.jobs import Journal,ReceiptError
from companion.layout import validate_layout,resolve_monitor
from test_core import ROOT,APP,FakeWindows

class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.fake=FakeWindows();self.deck=Deck(self.tmp.name,ROOT,adapter=self.fake);self.deck.apps=[copy.deepcopy(APP)]
    def tearDown(self):self.deck.close();self.tmp.cleanup()
    def call(self,path,body=None,device='local'):return self.deck.dispatch(path,{'requestId':str(time.time_ns()),**(body or {})},device)
    def wait_job(self,jid):
        end=time.monotonic()+4
        while time.monotonic()<end:
            job=next(j for j in self.deck.journal.jobs() if j['id']==jid)
            if job['status'] not in ('running','queued'):return job
            time.sleep(.02)
        self.fail('Job did not finish')
    def scene(self,steps,on_error='stop'):
        self.call('/api/scenes/save',{'name':'Prueba','steps':steps,'onError':on_error});return self.deck.profile['scenes'][-1]['id']
    def test_routines_and_launch_do_not_interleave_but_media_responds(self):
        order=[];started=threading.Event();release=threading.Event()
        def launch(app,url):
            order.append(url)
            if url=='https://one.example':started.set();release.wait(2)
            return {'status':'submitted','message':url}
        self.fake.launch=launch
        sid=self.scene([{'appId':APP['id'],'url':'https://one.example'},{'appId':APP['id'],'url':'https://two.example'}])
        a=self.call('/api/scenes/run',{'id':sid});self.assertTrue(started.wait(2))
        b=self.call('/api/launch',{'appId':APP['id'],'url':'https://three.example'})
        before=time.monotonic();self.call('/api/media',{'target':'system','action':'next'});self.assertLess(time.monotonic()-before,.5)
        self.assertEqual(order,['https://one.example']);release.set()
        self.assertEqual(self.wait_job(a['jobId'])['status'],'completed');self.wait_job(b['jobId'])
        self.assertEqual(order,['https://one.example','https://two.example','https://three.example'])
    def test_cancel_wait_leaves_remaining_apps_unopened(self):
        sid=self.scene([{'type':'wait','seconds':5},{'appId':APP['id']}]);result=self.call('/api/scenes/run',{'id':sid})
        time.sleep(.1);self.call('/api/jobs/cancel',{'id':result['jobId']})
        self.assertEqual(self.wait_job(result['jobId'])['status'],'cancelled');self.assertFalse(self.fake.calls)
    def test_other_devices_cannot_cancel_jobs(self):
        self.deck.devices=[{'id':'one'},{'id':'two'}]
        sid=self.scene([{'type':'wait','seconds':2}]);result=self.call('/api/scenes/run',{'id':sid},'one')
        with self.assertRaises(APIError):self.call('/api/jobs/cancel',{'id':result['jobId']},'two')
        self.call('/api/jobs/cancel',{'id':result['jobId']})
    def test_duplicate_taps_share_one_job(self):
        sid=self.scene([{'type':'wait','seconds':1}])
        a=self.call('/api/scenes/run',{'id':sid});b=self.call('/api/scenes/run',{'id':sid})
        self.assertEqual(a['jobId'],b['jobId'])
    def test_revocation_cancels_pending_work(self):
        self.deck.devices=[{'id':'one'}]
        sid=self.scene([{'type':'wait','seconds':2},{'appId':APP['id']}]);j=self.call('/api/scenes/run',{'id':sid},'one')
        self.deck.devices=[];self.assertEqual(self.wait_job(j['jobId'])['status'],'cancelled');self.assertFalse(self.fake.calls)
    def test_failures_stop_or_continue(self):
        def fail(app,url):
            self.fake.calls.append(url)
            if 'fail' in url:raise RuntimeError('App no respondió')
            return {'status':'submitted'}
        self.fake.launch=fail;steps=[{'appId':APP['id'],'url':'https://fail.example'},{'appId':APP['id'],'url':'https://okay.example'}]
        sid=self.scene(steps);job=self.call('/api/scenes/run',{'id':sid});self.assertEqual(self.wait_job(job['jobId'])['status'],'failed');self.assertEqual(len(self.fake.calls),1)
        sid=self.scene(steps,'continue');job=self.call('/api/scenes/run',{'id':sid});self.assertEqual(self.wait_job(job['jobId'])['status'],'partial');self.assertEqual(len(self.fake.calls),3)
    def test_wrong_device_cannot_consume_power_confirmation(self):
        c=self.call('/api/power/prepare',{'action':'sleep'},'one')['challenge']
        with self.assertRaises(APIError):self.call('/api/power/confirm',{'challenge':c},'two')
        self.assertEqual(self.call('/api/power/confirm',{'challenge':c},'one')['status'],'scheduled');self.call('/api/power/cancel')
    def test_backup_preserves_steps_layout_and_rejects_commands(self):
        self.scene([{'appId':APP['id'],'layout':{'monitor':'right','mode':'maximized'}},{'type':'wait','seconds':1},{'type':'media','action':'next'}])
        result=validate_profile(self.deck.profile)
        self.assertEqual(result['scenes'][0]['steps'][0]['layout']['monitor'],'right')
        self.assertEqual(result['scenes'][0]['steps'][2]['type'],'media')
        for invalid in [{'type':'shell','command':'echo test'},{'type':'wait','seconds':float('nan')},{'type':'power','action':'shutdown'},{'appId':APP['id'],'layout':{'monitor':'ask'}}]:
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):self.deck.clean_step(invalid)
    def test_invalid_card_layout_does_not_mutate_profile(self):
        before=copy.deepcopy(self.deck.profile)
        with self.assertRaises(ValueError):self.call('/api/cards/save',{'appId':APP['id'],'layout':{'mode':'execute-script'}})
        self.assertEqual(before,self.deck.profile)
    def test_queue_is_bounded(self):
        for i in range(21):
            try:self.deck.queue.submit(str(i),[{'type':'wait','seconds':5}],'local')
            except ValueError:break
        with self.assertRaises(ValueError):self.deck.queue.submit('overflow',[{'type':'wait','seconds':5}],'local')
    def test_receipt_survives_restart(self):
        body={'requestId':'durable-test','action':'next'}
        result=self.deck.dispatch('/api/media',body,'local');self.deck.close();self.deck=Deck(self.tmp.name,ROOT,adapter=self.fake)
        self.assertEqual(self.deck.dispatch('/api/media',body,'local'),result);self.assertEqual(len(self.fake.calls),1)
    def test_failure_receipt_is_durable_and_payload_bound(self):
        journal=self.deck.journal;body={'requestId':'failure-test'};calls=[]
        def work():calls.append(1);raise ValueError('bad')
        with self.assertRaises(ValueError):journal.invoke('/api/test',body,'local',work)
        with self.assertRaises(ReceiptError):journal.invoke('/api/test',body,'local',work)
        with self.assertRaises(ReceiptError):journal.invoke('/api/different',body,'local',work)
        self.assertEqual(calls,[1])
    def test_restart_marks_unfinished_uncertain(self):
        with self.deck.journal.connect() as db:db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)',('local','unfinished','digest',None,0,time.time()))
        journal=Journal(self.tmp.name);self.assertEqual(journal.receipt('local','unfinished')['status'],'failed')
    def test_receipt_is_device_scoped(self):self.assertEqual(self.deck.journal.receipt('another','missing')['status'],'notReceived')

class LayoutTests(unittest.TestCase):
    def setUp(self):self.ms=[{'id':'display:a','primary':False,'vertical':True},{'id':'display:b','primary':True,'vertical':False}]
    def test_left_right_vertical_primary(self):
        for role,expected in [('left','display:a'),('right','display:b'),('vertical','display:a'),('primary','display:b')]:self.assertEqual(resolve_monitor(validate_layout({'monitor':role}),self.ms)[0]['id'],expected)
    def test_missing_monitor_stop_or_explicit_fallback(self):
        with self.assertRaises(ValueError):resolve_monitor(validate_layout({'monitor':'vertical'}),self.ms[1:])
        chosen,fallback=resolve_monitor(validate_layout({'monitor':'vertical','missing':'primary'}),self.ms[1:]);self.assertTrue(fallback);self.assertTrue(chosen['primary'])
    def test_multiple_verticals_require_exact_choice(self):
        self.ms[1]['vertical']=True
        with self.assertRaises(ValueError):resolve_monitor(validate_layout({'monitor':'vertical'}),self.ms)
        self.assertEqual(resolve_monitor(validate_layout({'monitor':'display:b'}),self.ms)[0]['id'],'display:b')

if __name__=='__main__':unittest.main(verbosity=2)
