import copy,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from test_core import APP,ROOT,FakeWindows
from companion.core import Deck,APIError
from companion.jobs import Journal,ReceiptError
from companion.supervisor import marker_fresh,restart_due

class Clock:
    def __init__(self,wall=1000,mono=100):self.wall=wall;self.mono=mono;self.sleeps=0;self.jump=0;self.callback=None
    def time(self):return self.wall
    def monotonic(self):return self.mono
    def sleep(self,seconds):
        self.sleeps+=1
        if self.sleeps>200:raise AssertionError('Countdown exceeded its bounded monotonic duration')
        self.mono+=seconds;self.wall+=seconds+self.jump;self.jump=0
        if self.callback:self.callback()

class Beta4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.fake=FakeWindows();self.deck=Deck(self.tmp.name,ROOT,adapter=self.fake);self.deck.apps=[copy.deepcopy(APP)]
    def tearDown(self):self.deck.close();self.tmp.cleanup()
    def call(self,path,body=None,device='local'):
        return self.deck.dispatch(path,{'requestId':str(time.time_ns()),**(body or {})},device)
    def pending(self,clock,device='local',seconds=15):
        pending={'id':'fixture','action':'lock','at':clock.time()+seconds,'deadline':clock.monotonic()+seconds,'device':device}
        self.deck.pending=pending;return pending

    def test_close_with_unwritable_journal_stops_waiters_without_replay(self):
        self.deck.queue.pause(True)
        jobs=[self.deck.queue.submit('Close fixture '+str(i),[{'type':'wait','seconds':0}],'local')['jobId'] for i in range(2)]
        with patch.object(self.deck.journal,'save_job',side_effect=OSError('injected full disk')),patch('companion.jobs.logging.getLogger'):
            self.deck.close()
        self.assertTrue(self.deck.queue.stopped);self.assertFalse(self.deck.queue.waiting)
        self.assertFalse(self.deck.queue.thread.is_alive());self.assertTrue(self.deck.queue.fatal_error)
        restored=Journal(self.tmp.name)
        self.assertEqual({j['status'] for j in restored.jobs() if j['id'] in jobs},{'interrupted'})
        self.assertFalse(self.fake.calls)

    def test_cleanup_failure_does_not_skip_other_owned_resources(self):
        guard=MagicMock();guard.close.side_effect=OSError('injected guard failure');self.deck.awake=guard
        first,second=MagicMock(),MagicMock();first.shutdown.side_effect=OSError('injected socket shutdown failure');self.deck.servers=[first,second]
        with patch('companion.core.LOG'):self.deck.close()
        self.assertFalse(self.deck.queue.thread.is_alive())
        first.server_close.assert_called_once();second.shutdown.assert_called_once();second.server_close.assert_called_once()
        self.deck.awake=None;self.deck.servers=[]

    def test_closed_receiver_rejects_new_physical_work(self):
        self.deck.close()
        with self.assertRaises(APIError) as error:self.call('/api/media',{'action':'next','target':'system'})
        self.assertEqual(error.exception.status,503);self.assertFalse(self.fake.calls)
        self.assertEqual(self.call('/api/power/cancel')['status'],'cancelled')
    def test_forward_wall_jump_does_not_shorten_power_countdown(self):
        clock=Clock();clock.jump=86400;pending=self.pending(clock)
        with patch('companion.core.time',clock):self.deck._power_countdown(pending)
        self.assertGreaterEqual(clock.mono,115);self.assertLess(clock.mono,115.3)
        self.assertEqual(self.fake.calls,[('power','lock')])
    def test_backward_wall_jump_does_not_extend_power_countdown(self):
        clock=Clock();clock.jump=-86400;pending=self.pending(clock)
        with patch('companion.core.time',clock):self.deck._power_countdown(pending)
        self.assertLess(clock.mono,115.3);self.assertEqual(self.fake.calls,[('power','lock')])
    def test_revoked_device_is_rechecked_when_deadline_already_elapsed(self):
        clock=Clock();pending=self.pending(clock,device='revoked',seconds=-1)
        with patch('companion.core.time',clock):self.deck._power_countdown(pending)
        self.assertFalse(self.fake.calls);self.assertIsNone(self.deck.pending)
    def test_cancellation_on_last_wait_prevents_power(self):
        clock=Clock();pending=self.pending(clock,seconds=.1)
        clock.callback=lambda:setattr(self.deck,'pending',None)
        with patch('companion.core.time',clock):self.deck._power_countdown(pending)
        self.assertFalse(self.fake.calls)
    def test_revocation_on_last_wait_prevents_power(self):
        clock=Clock();self.deck.devices=[{'id':'phone'}];pending=self.pending(clock,'phone',.1)
        clock.callback=lambda:setattr(self.deck,'devices',[])
        with patch('companion.core.time',clock):self.deck._power_countdown(pending)
        self.assertFalse(self.fake.calls)
    def test_power_confirmation_expiry_uses_elapsed_time_after_wall_changes(self):
        for jump in (-86400,86400):
            with self.subTest(jump=jump):
                self.deck.pending=None
                clock=Clock()
                with patch('companion.core.time',clock),patch('companion.core.threading.Thread'):
                    c=self.call('/api/power/prepare',{'action':'lock'})['challenge']
                    clock.wall+=jump;clock.mono+=31
                    with self.assertRaises(APIError):self.call('/api/power/confirm',{'challenge':c})
                self.assertIsNone(self.deck.pending)
    def test_power_confirmation_still_valid_before_deadline_after_wall_jump(self):
        clock=Clock()
        with patch('companion.core.time',clock),patch('companion.core.threading.Thread'):
            c=self.call('/api/power/prepare',{'action':'lock'})['challenge'];clock.wall+=86400;clock.mono+=1
            result=self.call('/api/power/confirm',{'challenge':c})
        self.assertAlmostEqual(result['pending']['remainingSeconds'],15)
        self.assertNotIn('deadline',result['pending']);self.assertNotIn('device',result['pending'])
    def test_rejected_card_edit_leaves_memory_and_saved_profile_unchanged(self):
        original=copy.deepcopy(self.deck.profile)
        with self.assertRaises(ValueError):self.call('/api/cards/save',{'appId':APP['id'],'ifOpen':'invalid'})
        self.assertEqual(self.deck.profile,original)
        self.assertFalse((self.deck.data/'deck.json').exists())
    def test_editor_cannot_resurrect_a_deleted_routine_implicitly(self):
        self.call('/api/scenes/save',{'name':'Temporary','steps':[{'type':'wait','seconds':1}]})
        sid=self.deck.profile['scenes'][0]['id'];self.call('/api/scenes/delete',{'id':sid})
        with self.assertRaises(ValueError):self.call('/api/scenes/save',{'id':sid,'name':'Old editor','steps':[{'type':'wait','seconds':1}]})
        self.assertEqual(self.deck.profile['scenes'],[])

    def test_pairing_pin_uses_elapsed_time_and_exact_expiry(self):
        clock=Clock()
        with patch('companion.core.time',clock):
            pin=self.deck.renew_pin();clock.wall+=86400;clock.mono+=599
            self.deck.pair({'pin':pin,'name':'Isolated fixture'},'127.0.0.1')
            pin=self.deck.renew_pin();clock.wall-=172800;clock.mono+=600
            with self.assertRaises(APIError):self.deck.pair({'pin':pin},'127.0.0.1')

    def test_pairing_rate_window_expires_despite_backward_wall_jump(self):
        clock=Clock()
        with patch('companion.core.time',clock):
            pin=self.deck.renew_pin()
            for i in range(10):
                with self.assertRaises(APIError):self.deck.pair({'pin':'bad'},'127.0.0.1')
            clock.wall-=86400;clock.mono+=301
            self.assertIn('deviceId',self.deck.pair({'pin':pin},'127.0.0.1'))

    def test_termination_confirmation_has_monotonic_expiry(self):
        self.deck.layouts.require_window=MagicMock(return_value={'id':'window','process':'fixture.exe'})
        clock=Clock()
        with patch('companion.core.time',clock):
            c=self.call('/api/windows/terminate/prepare',{'windowId':'window'})['challenge']
            clock.wall-=86400;clock.mono+=20
            with self.assertRaises(APIError):self.call('/api/windows/terminate/confirm',{'challenge':c})
        self.assertFalse(self.fake.calls)

    def test_rate_limit_survives_wall_jumps_and_recovers_in_one_minute(self):
        clock=Clock();journal=self.deck.journal;calls=[]
        with patch('companion.jobs.time',clock):
            for i in range(180):journal.invoke('/fixture',{'requestId':f'fixture-{i:04}'},'fixture',lambda:(calls.append(1) or {}))
            clock.wall+=86400
            with self.assertRaises(ReceiptError):journal.invoke('/fixture',{'requestId':'fixture-blocked'},'fixture',lambda:{})
            clock.wall-=172800;clock.mono+=60
            journal.invoke('/fixture',{'requestId':'fixture-recovered'},'fixture',lambda:(calls.append(1) or {}))
        self.assertEqual(len(calls),181)

    def test_future_receipt_dates_after_restart_cannot_block_for_days(self):
        clock=Clock();journal=self.deck.journal
        with journal.connect() as db:
            db.executemany('INSERT INTO receipts VALUES(?,?,?,?,?,?)',(('fixture',f'future-{i:04}','digest','{}',200,clock.wall+86400) for i in range(180)))
        journal=Journal(self.tmp.name)
        with patch('companion.jobs.time',clock):
            with self.assertRaises(ReceiptError):journal.invoke('/fixture',{'requestId':'first-new-request'},'fixture',lambda:{})
            clock.wall-=86400;clock.mono+=60
            self.assertEqual(journal.invoke('/fixture',{'requestId':'new-after-wait'},'fixture',lambda:{'status':'fixture'}),{'status':'fixture'})

    def test_future_repair_record_after_restart_waits_at_most_one_minute(self):
        import json
        clock=Clock();(self.deck.data/'repair-state.json').write_text(json.dumps({'at':clock.wall+86400}))
        with patch('companion.core.time',clock):
            with self.assertRaises(APIError):self.deck.check_repair_cooldown()
            clock.wall-=86400;clock.mono+=60;self.deck.check_repair_cooldown()

    def test_supervisor_marker_and_restart_delay_ignore_wall_jump(self):
        clock=Clock()
        with patch('companion.supervisor.time',clock):
            marker={'monotonic':clock.mono,'at':clock.wall};request={'pid':77,'afterMonotonic':clock.mono+3,'after':clock.wall+3}
            clock.wall+=86400
            self.assertTrue(marker_fresh(marker,15));self.assertFalse(restart_due(request,77))
            clock.mono+=3;self.assertTrue(restart_due(request,77));self.assertFalse(restart_due(request,78))
            clock.mono+=12;self.assertFalse(marker_fresh(marker,15))
            self.assertFalse(marker_fresh({'monotonic':float('nan')},15))
            self.assertFalse(restart_due({'pid':77,'afterMonotonic':'bad'},77))

if __name__=='__main__':unittest.main()
