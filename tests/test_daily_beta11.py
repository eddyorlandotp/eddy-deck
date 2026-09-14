"""Cross-feature failure cases, including effects which must never happen."""
import copy, itertools, json, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch
from companion.core import Deck, APIError
from companion.jobs import Cancelled
from companion import windows
from test_core import FakeWindows, APP, ROOT

class DailyBeta11(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.fake=FakeWindows();self.deck=Deck(self.tmp.name,ROOT,adapter=self.fake);self.deck.apps=[copy.deepcopy(APP)]
    def tearDown(self):self.deck.close();self.tmp.cleanup()
    def call(self,path,body):return self.deck.dispatch(path,{'requestId':str(time.time_ns()),**body},'local')
    def wait(self,jid):
        end=time.monotonic()+3
        while time.monotonic()<end:
            job=next(j for j in self.deck.journal.jobs() if j['id']==jid)
            if job['status'] not in ('queued','running'):return job
            time.sleep(.005)
        self.fail('Job remained orphaned')
    def test_invalid_card_policy_does_not_leave_phantom_card(self):
        before=copy.deepcopy(self.deck.profile)
        with self.assertRaises(ValueError):self.call('/api/cards/save',{'appId':APP['id'],'name':'Invalid','color':'mint','ifOpen':'bad'})
        self.assertEqual(self.deck.profile,before)
        self.call('/api/cards/save',{'appId':APP['id'],'name':'Valid','color':'mint'})
        self.assertEqual([c['name'] for c in json.loads((Path(self.tmp.name)/'deck.json').read_text())['cards']],['Valid'])
    def test_failed_save_rolls_back_cards_scenes_delete_and_reorder(self):
        a=self.call('/api/cards/save',{'appId':APP['id'],'name':'One','color':'mint'})['card']['id']
        self.call('/api/cards/save',{'appId':APP['id'],'name':'Two','color':'mint'})
        self.call('/api/scenes/save',{'name':'Routine','steps':[{'type':'wait','seconds':0}]})
        scene=self.deck.profile['scenes'][0]['id'];before=copy.deepcopy(self.deck.profile);disk=(Path(self.tmp.name)/'deck.json').read_bytes()
        actions=[('/api/cards/delete',{'id':a}),('/api/cards/move',{'id':a,'direction':1}),('/api/cards/save',{'id':a,'appId':APP['id'],'name':'Changed','color':'mint'}),('/api/scenes/delete',{'id':scene}),('/api/scenes/save',{'id':scene,'name':'Changed','steps':[{'type':'wait','seconds':1}]})]
        for path,body in actions:
            with self.subTest(path=path),patch('companion.core.atomic_json',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):self.call(path,body)
            self.assertEqual(self.deck.profile,before);self.assertEqual((Path(self.tmp.name)/'deck.json').read_bytes(),disk)
    def test_direct_music_busy_is_rejected_without_late_effect(self):
        self.deck.media_lock.acquire()
        try:
            start=time.monotonic()
            with self.assertRaises(APIError) as caught:self.call('/api/media',{'target':'tidal','action':'pause'})
            self.assertEqual(caught.exception.status,409);self.assertLess(time.monotonic()-start,3)
        finally:self.deck.media_lock.release()
        time.sleep(.03);self.assertFalse(self.fake.calls)
    def test_routine_cancel_while_waiting_for_direct_music(self):
        self.deck.media_lock.acquire()
        try:
            queued=self.deck.enqueue('Music waiting',[{'type':'media','target':'tidal','action':'pause'},{'type':'launch','appId':APP['id']}],'local')
            time.sleep(.08);self.deck.queue.cancel(queued['jobId'],'local')
            self.assertEqual(self.wait(queued['jobId'])['status'],'cancelled');self.assertFalse(self.fake.calls)
        finally:self.deck.media_lock.release()
    def test_close_while_media_lock_busy_leaves_no_worker(self):
        self.deck.media_lock.acquire()
        try:
            self.deck.enqueue('Close waiting',[{'type':'media','target':'tidal','action':'pause'}],'local');time.sleep(.06)
            self.deck.close();self.assertFalse(self.deck.queue.thread.is_alive());self.assertFalse(self.fake.calls)
        finally:self.deck.media_lock.release()
    def test_routine_keeps_saved_snapshot_after_edit_and_delete(self):
        self.deck.queue.pause(True)
        self.call('/api/scenes/save',{'name':'Before','steps':[{'type':'media','target':'tidal','action':'pause'}]})
        sid=self.deck.profile['scenes'][0]['id'];job=self.call('/api/scenes/run',{'id':sid})
        self.call('/api/scenes/save',{'id':sid,'name':'After','steps':[{'type':'media','target':'aimp','action':'play'}]})
        self.call('/api/scenes/delete',{'id':sid});self.deck.queue.pause(False)
        self.assertEqual(self.wait(job['jobId'])['status'],'completed');self.assertEqual(self.fake.calls[0][1][:2],('pause','tidal'))
    def test_cancel_during_last_effect_records_effect_but_not_completed(self):
        entered=threading.Event();release=threading.Event()
        def execute(step,check):entered.set();release.wait(2);return {'status':'completed','message':'Fixture effect already happened'}
        self.deck.queue.execute=execute
        job=self.deck.enqueue('Final media',[{'type':'media'}],'local');self.assertTrue(entered.wait(1))
        self.deck.queue.cancel(job['jobId'],'local');release.set();done=self.wait(job['jobId'])
        self.assertEqual(done['status'],'cancelled');self.assertEqual(len(done['results']),1)
    def test_disappeared_auto_pause_never_toggles_another_application(self):
        with patch('companion.windows.media_snapshot',return_value={'players':[]}),patch.object(windows.user32,'keybd_event') as key:
            with self.assertRaisesRegex(ValueError,'ya no está disponible'):windows.media('pause','system',[])
            key.assert_not_called()
    def test_direct_invalid_media_rejected_before_adapter_or_dry_run(self):
        for target,action in [('windows','pause'),('aimp','invalid'),('session:'+'a'*32,'mute')]:
            with self.subTest(target=target),self.assertRaises(ValueError):self.call('/api/media',{'target':target,'action':action})
        self.assertFalse(self.fake.calls)
    def test_twenty_player_states_never_guess_ambiguous_destination(self):
        for playing in range(21):
            players=[{'id':'session:'+format(i,'032x'),'state':'playing' if i<playing else 'paused'} for i in range(20)]
            with self.subTest(playing=playing):
                target=windows.preferred_media({'players':players})
                self.assertEqual(target,players[0]['id'] if playing==1 else 'ambiguous')
    def test_all_explicit_session_controls_route_to_one_of_twenty_targets(self):
        for i,action in itertools.product(range(20),('play','pause','toggle','stop','next','previous')):
            target='session:'+format(i,'032x')
            with patch('companion.media_sessions.control',return_value={'status':'completed'}) as effect,patch.object(windows.user32,'keybd_event') as global_key:
                windows.media(action,target,[]);effect.assert_called_once_with(action,target);global_key.assert_not_called()
    def test_pairwise_steps_fail_stop_continue_and_cancellation(self):
        # Actual queue and durable journal; OS effects are labeled fixtures.
        kinds=('launch','media','wait','failure')
        effects=[]
        def execute(step,check):
            check();effects.append(step['type'])
            if step['type']=='failure':raise ValueError('Fixture failure')
            return {'status':'completed'}
        self.deck.queue.execute=execute
        for first,last,policy in itertools.product(kinds,kinds,('stop','continue')):
            effects.clear();job=self.deck.enqueue('Pair '+first+last+policy,[{'type':first},{'type':last}],'local',policy)
            done=self.wait(job['jobId']);expected=[first] if first=='failure' and policy=='stop' else [first,last]
            with self.subTest(first=first,last=last,policy=policy):
                self.assertEqual(effects,expected);self.assertEqual(len(done['results']),len(expected));self.assertNotIn(done['status'],('queued','running'))
        self.assertEqual(self.deck.queue.status()['waiting'],0);self.assertIsNone(self.deck.queue.status()['active'])
