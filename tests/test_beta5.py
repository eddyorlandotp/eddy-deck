"""Combined failures on real Queue/Journal with disposable data and fake OS effects."""
import concurrent.futures,copy,json,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from test_core import ROOT,APP,FakeWindows
from companion.core import Deck,APIError
from companion.jobs import Journal,ReceiptError

class Beta5Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='eddy-beta5-')
        self.fake=FakeWindows();self.deck=Deck(self.tmp.name,ROOT,adapter=self.fake)
        self.deck.apps=[copy.deepcopy(APP)]
    def tearDown(self):self.deck.close();self.tmp.cleanup()
    def call(self,path,body=None):
        return self.deck.dispatch(path,{'requestId':str(time.time_ns()),**(body or {})},'local')
    def waiting(self):
        self.deck.queue.pause(True)
        return [self.deck.queue.submit('Pending '+str(i),[{'type':'wait','seconds':0}],'local')['jobId'] for i in range(3)]
    def test_cancel_all_write_failure_clears_every_waiter_and_blocks_admission(self):
        ids=self.waiting();items=list(self.deck.queue.waiting)
        with patch.object(self.deck.journal,'save_job',side_effect=OSError('injected disk full')) as save:
            with self.assertRaises(Exception):self.deck.queue.cancel_all()
        self.assertTrue(all(item['cancel'].is_set() for item in items))
        self.assertEqual(save.call_count,3)
        self.assertFalse(self.deck.queue.waiting)
        self.assertFalse(self.deck.queue.status()['healthy'])
        with self.assertRaises((ValueError,ReceiptError)):self.deck.queue.submit('Later',[],'local')
        self.deck.close();restored=Journal(self.tmp.name)
        self.assertEqual({j['status'] for j in restored.jobs() if j['id'] in ids},{'interrupted'})
        self.assertFalse(self.fake.calls)
    def test_receiver_repair_does_not_schedule_restart_after_cancellation_write_failure(self):
        self.waiting()
        with patch('companion.supervisor.active',return_value=True),patch.object(self.deck.journal,'save_job',side_effect=OSError('injected disk full')):
            with self.assertRaises(Exception):self.call('/api/repair',{'confirm':True})
        self.assertFalse((self.deck.data/'restart-request.json').exists())
        self.assertFalse(self.deck.repairing);self.assertFalse(self.fake.calls)
    def test_file_repair_does_not_start_helper_after_cancellation_write_failure(self):
        self.waiting()
        with patch('companion.integrity.start_repair') as helper,patch.object(self.deck.journal,'save_job',side_effect=OSError('injected disk full')):
            with self.assertRaises(Exception):self.call('/api/installation/repair',{'confirm':True})
        helper.assert_not_called();self.assertFalse(self.deck.repairing)
    def test_file_repair_blocks_new_work_before_helper_starts(self):
        self.waiting();states=[]
        def helper(_):
            states.append(self.deck.repairing)
            with self.assertRaises(APIError):self.deck.enqueue('Late',[],'local')
            self.assertFalse(self.deck.queue.waiting)
            return {'status':'restarting'}
        with patch('companion.integrity.start_repair',side_effect=helper):
            self.assertEqual(self.call('/api/installation/repair',{'confirm':True})['status'],'restarting')
        self.assertEqual(states,[True])
    def test_failed_helper_releases_repair_flag_and_keeps_old_jobs_cancelled(self):
        ids=self.waiting()
        with patch('companion.integrity.start_repair',side_effect=OSError('injected helper failure')):
            with self.assertRaises(OSError):self.call('/api/installation/repair',{'confirm':True})
        self.assertFalse(self.deck.repairing);self.assertFalse(self.deck.queue.waiting)
        self.assertEqual({j['status'] for j in self.deck.journal.jobs() if j['id'] in ids},{'cancelled'})
    def test_power_not_scheduled_when_cancellation_storage_fails(self):
        self.waiting();challenge=self.call('/api/power/prepare',{'action':'lock'})['challenge']
        with patch.object(self.deck.journal,'save_job',side_effect=OSError('injected disk full')),patch('companion.core.threading.Thread') as thread:
            with self.assertRaises(Exception):self.call('/api/power/confirm',{'challenge':challenge})
        self.assertIsNone(self.deck.pending);thread.assert_not_called();self.assertFalse(self.fake.calls)

    def test_active_routine_cancels_remaining_steps_when_waiting_cancel_write_fails(self):
        entered,release=threading.Event(),threading.Event()
        def launch(app,url):
            self.fake.calls.append(url);entered.set()
            if not release.wait(2):raise AssertionError('Fixture synchronization timed out')
            return {'status':'submitted','message':'Fixture launch returned'}
        self.fake.launch=launch
        first=self.deck.queue.submit('Running',[self.deck.clean_step({'appId':APP['id'],'url':'https://first.example'}),self.deck.clean_step({'appId':APP['id'],'url':'https://must-not-open.example'})],'local')
        self.assertTrue(entered.wait(1))
        second=self.deck.queue.submit('Waiting',[{'type':'wait','seconds':0}],'local')
        try:
            with patch.object(self.deck.journal,'save_job',side_effect=OSError('injected disk full')):
                with self.assertRaises(ReceiptError):self.deck.queue.cancel_all()
        finally:release.set()
        self.deck.queue.thread.join(2);self.assertFalse(self.deck.queue.thread.is_alive())
        self.assertEqual(self.fake.calls,['https://first.example'])
        self.assertFalse(self.deck.queue.waiting)
        restored=Journal(self.tmp.name);statuses={j['id']:j['status'] for j in restored.jobs()}
        self.assertEqual(statuses[first['jobId']],'cancelled');self.assertEqual(statuses[second['jobId']],'interrupted')

    def test_one_failed_cancel_write_does_not_skip_other_durable_cancellations(self):
        ids=self.waiting();save=self.deck.journal.save_job;attempts=[]
        def flaky(job):
            attempts.append(job['id'])
            if job['id']==ids[1]:raise OSError('injected single write failure')
            save(job)
        with patch.object(self.deck.journal,'save_job',side_effect=flaky):
            with self.assertRaises(ReceiptError):self.deck.queue.cancel_all()
        self.assertEqual(attempts,ids)
        self.deck.close();statuses={j['id']:j['status'] for j in Journal(self.tmp.name).jobs()}
        self.assertEqual([statuses[i] for i in ids],['cancelled','interrupted','cancelled'])

    def test_lost_media_response_then_receiver_reopen_replays_receipt_not_effect(self):
        body={'requestId':'lost-media-response','action':'toggle','target':'system'}
        first=self.deck.dispatch('/api/media',body,'local')
        self.deck.close();self.deck=Deck(self.tmp.name,ROOT,adapter=self.fake)
        replay=self.deck.dispatch('/api/media',body,'local')
        self.assertEqual(first,replay);self.assertEqual(len(self.fake.calls),1)
        receipt=self.deck.journal.receipt('local',body['requestId'])
        self.assertEqual(receipt,{'status':'received','result':first})
        with self.assertRaises(APIError):self.deck.dispatch('/api/media',{**body,'action':'next'},'local')
        self.assertEqual(len(self.fake.calls),1)

    def test_two_repair_buttons_in_flight_start_only_one_repair(self):
        self.waiting();entered,release,second_started=threading.Event(),threading.Event(),threading.Event()
        def helper(_):
            entered.set()
            if not release.wait(5):raise AssertionError('Repair fixture timed out')
            return {'status':'restarting'}
        def receiver():
            second_started.set();return self.call('/api/repair',{'confirm':True})
        with patch('companion.integrity.start_repair',side_effect=helper) as start_helper,patch('companion.supervisor.active',return_value=True),concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(self.call,'/api/installation/repair',{'confirm':True})
            try:
                self.assertTrue(entered.wait(2));second=pool.submit(receiver)
                self.assertTrue(second_started.wait(2))
            finally:release.set()
            self.assertEqual(first.result(3)['status'],'restarting')
            self.assertEqual(second.result(3)['status'],'restarting')
            start_helper.assert_called_once()
        self.assertFalse((self.deck.data/'restart-request.json').exists())
        self.assertFalse(self.deck.queue.waiting);self.assertFalse(self.fake.calls)

    def test_monitor_disappears_between_routine_steps_with_each_policy(self):
        from companion.layout import resolve_monitor
        primary={'id':'display:primary','primary':True,'vertical':False}
        external={'id':'display:external','primary':False,'vertical':True}
        for missing in ('stop','primary'):
            for policy in ('stop','continue'):
                with self.subTest(missing=missing,onError=policy):
                    available=[primary,external];entered,release=threading.Event(),threading.Event();effects=[]
                    def launch(app,url,settings,apps,check):
                        check();target,fallback=resolve_monitor(settings,available)
                        effects.append((url,target['id']))
                        if 'first' in url:
                            entered.set()
                            if not release.wait(8):raise AssertionError('Topology fixture timed out')
                        return {'status':'completed','message':target['id']}
                    steps=[{'appId':APP['id'],'url':'https://'+name+'.example','layout':{'monitor':monitor,'mode':'windowed','missing':missing}} for name,monitor in [('first','primary'),('second','display:external'),('third','primary')]]
                    with patch('companion.core.monitors',side_effect=lambda:list(available)),patch.object(self.deck.layouts,'launch',side_effect=launch),patch.object(self.deck.layouts,'snapshot',return_value=[]):
                        self.call('/api/scenes/save',{'name':missing+policy,'steps':steps,'onError':policy})
                        result=self.call('/api/scenes/run',{'id':self.deck.profile['scenes'][-1]['id']})
                        try:
                            started=entered.wait(5)
                            if started:available[:]=[primary]
                        finally:release.set()
                        end=time.monotonic()+5
                        while time.monotonic()<end:
                            job=next(j for j in self.deck.journal.jobs() if j['id']==result['jobId'])
                            if job['status'] not in ('running','queued'):break
                            time.sleep(.005)
                    self.assertTrue(started,'First fixture step did not start within five seconds')
                    expected='completed' if missing=='primary' else 'failed' if policy=='stop' else 'partial'
                    self.assertEqual(job['status'],expected)
                    self.assertEqual(len(effects),3 if missing=='primary' else 1 if policy=='stop' else 2)
                    self.assertTrue(all(target=='display:primary' for _,target in effects))

if __name__=='__main__':unittest.main()
