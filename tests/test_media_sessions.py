import subprocess,unittest
from unittest.mock import patch
from companion import windows,media_sessions
from companion.core import Deck
SID='session:'+'a'*32
class MediaSessionTests(unittest.TestCase):
    def test_same_source_sessions_are_one_disabled_ambiguous_choice(self):
        rows=[{'id':SID,'source':'browser','state':state,'controls':{}} for state in ('playing','paused')]
        with patch('companion.media_sessions.invoke',return_value={'players':rows}):result=media_sessions.snapshot([])
        self.assertEqual(len(result['players']),1);self.assertTrue(result['players'][0]['ambiguous']);self.assertFalse(any(result['players'][0]['controls'].values()))
        self.assertEqual(windows.preferred_media(result),'ambiguous')
    def test_parallel_media_calls_cannot_overlap_adapter_effects(self):
        import tempfile,threading,time,concurrent.futures
        from pathlib import Path
        from test_core import FakeWindows,ROOT
        guard=threading.Lock();active=0;maximum=0;effects=[]
        class Slow(FakeWindows):
            def media(self,action,target,apps,value=None):
                nonlocal active,maximum
                with guard:active+=1;maximum=max(maximum,active)
                time.sleep(.04)
                with guard:effects.append(action);active-=1
                return {'status':'completed'}
        with tempfile.TemporaryDirectory() as tmp:
            deck=Deck(Path(tmp),ROOT,adapter=Slow())
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    jobs=[pool.submit(deck.dispatch,'/api/media',{'requestId':'parallel-'+str(i),'target':'tidal','action':action},'local') for i,action in enumerate(('next','pause','play','pause'))]
                    for job in jobs:job.result(timeout=5)
                self.assertEqual(maximum,1);self.assertEqual(len(effects),4)
            finally:deck.close()
    def tearDown(self):media_sessions._cached=None;media_sessions._until=0
    def test_auto_selects_actual_player_over_paused_tidal_and_stopped_aimp(self):
        s={'tidal':{'running':True,'state':'paused'},'aimp':True,'state':'stopped','players':[{'id':SID,'state':'playing'}]}
        self.assertEqual(windows.preferred_media(s),SID)
    def test_two_actual_players_are_ambiguous(self):
        self.assertEqual(windows.preferred_media({'tidal':{'state':'playing'},'players':[{'id':SID,'state':'playing'}]}),'ambiguous')
    def test_failed_session_enumeration_does_not_guess_auto_target(self):
        self.assertEqual(windows.preferred_media({'tidal':{'state':'playing'},'sessionError':'timeout'}),'unavailable')
    def test_explicit_raw_windows_keys_do_not_redirect_to_tidal(self):
        with patch.object(windows.user32,'keybd_event') as key,patch('companion.windows.media_snapshot') as scan:
            result=windows.media('toggle','windows',[])
        scan.assert_not_called();self.assertEqual(key.call_count,2);self.assertIn('no se ha verificado',result['message'])
    def test_session_action_routes_to_only_the_selected_id(self):
        with patch('companion.media_sessions.control',return_value={'state':'paused'}) as call,patch.object(windows.user32,'keybd_event') as key:
            windows.media('pause',SID,[])
        call.assert_called_once_with('pause',SID);key.assert_not_called()
    def test_no_global_fallback_if_session_disappears(self):
        with patch('companion.media_sessions.control',side_effect=RuntimeError('gone')),patch.object(windows.user32,'keybd_event') as key:
            with self.assertRaises(RuntimeError):windows.media('pause',SID,[])
        key.assert_not_called()
    def test_invalid_session_ids_and_actions_never_start_helper(self):
        with patch('companion.media_sessions.subprocess.run') as call:
            for target in ('session:../x','session:'+'a'*31,'file:///x',SID+'x',None):
                with self.assertRaises(ValueError):media_sessions.invoke('pause',target)
            with self.assertRaises(ValueError):media_sessions.invoke('launch',SID)
        call.assert_not_called()
    def test_routine_preserves_exact_session_and_rejects_unknown_actions(self):
        self.assertEqual(Deck.clean_step(None,{'type':'media','target':SID,'action':'pause'},False)['target'],SID)
        for target,action in ((SID,'mute'),('windows','pause'),('invalid','play')):
            with self.assertRaises(ValueError):Deck.clean_step(None,{'type':'media','target':target,'action':action},False)
    def test_malformed_helper_reply_is_an_error(self):
        for reply in ('[]','{}','{"players":[null]}','{"players":[{"id":"bad"}]}'):
            with patch('companion.media_sessions.Path.is_file',return_value=True),patch('companion.media_sessions.subprocess.run',return_value=subprocess.CompletedProcess([],0,reply)):
                with self.assertRaises(RuntimeError):media_sessions.invoke('list')
    def test_timeout_is_not_retried(self):
        with patch('companion.media_sessions.Path.is_file',return_value=True),patch('companion.media_sessions.subprocess.run',side_effect=subprocess.TimeoutExpired('fixture',10)) as run:
            with self.assertRaises(RuntimeError):media_sessions.invoke('pause',SID)
        self.assertEqual(run.call_count,1)
    def test_cached_snapshot_names_are_resolved_against_current_pc_catalog(self):
        raw={'players':[{'id':SID,'source':'fixture-app','state':'paused','controls':{}}]}
        with patch('companion.media_sessions.invoke',return_value=raw) as call:
            a=media_sessions.snapshot([{'target':'fixture-app','name':'First PC'}]);b=media_sessions.snapshot([{'target':'fixture-app','name':'Second PC'}])
        self.assertEqual(a['players'][0]['name'],'First PC');self.assertEqual(b['players'][0]['name'],'Second PC');self.assertEqual(call.call_count,1)
    def test_failed_control_invalidates_cached_state(self):
        media_sessions._cached={'players':[]};media_sessions._until=10**9
        with patch('companion.media_sessions.invoke',side_effect=RuntimeError('unavailable')):
            with self.assertRaises(RuntimeError):media_sessions.control('pause',SID)
        self.assertIsNone(media_sessions._cached)
    def test_aimp_unidentified_track_blocks_skip_before_action(self):
        with patch('companion.windows.aimp_handle',return_value=123),patch('companion.windows.aimp_snapshot',return_value={'state':'playing'}),patch('companion.windows.aimp_track_marker',side_effect=RuntimeError('unknown')),patch.object(windows.user32,'PostMessageW') as post:
            with self.assertRaises(RuntimeError):windows.media('next','aimp',[])
        post.assert_not_called()
