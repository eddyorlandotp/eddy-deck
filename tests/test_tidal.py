import copy,json,subprocess,unittest
from unittest.mock import patch
from companion import windows,tidal

class TidalTests(unittest.TestCase):
    def tearDown(self):tidal._cached=None;tidal._until=0
    def test_auto_prefers_tidal_when_it_is_playing(self):
        self.assertEqual(windows.preferred_media({'aimp':True,'state':'paused','tidal':{'running':True,'state':'playing'}}),'tidal')
    def test_auto_rejects_ambiguous_two_playing_players(self):
        snapshot={'aimp':True,'state':'playing','tidal':{'running':True,'state':'playing'}}
        with patch('companion.windows.media_snapshot',return_value=snapshot),patch('companion.tidal.control') as call:
            with self.assertRaises(ValueError):windows.media('pause','system',[])
        call.assert_not_called()
    def test_auto_pause_and_stop_use_tidal_not_global_keys(self):
        for action in ('pause','stop','toggle','play'):
            with self.subTest(action=action),patch('companion.windows.media_snapshot',return_value={'tidal':{'running':True,'state':'playing'}}),patch('companion.tidal.control',return_value={'verified':True}) as call,patch.object(windows.user32,'keybd_event') as key:
                self.assertTrue(windows.media(action,'system',[])['verified']);call.assert_called_once_with(action,[]);key.assert_not_called()
    def test_failed_tidal_control_never_falls_back_to_global_toggle(self):
        with patch('companion.windows.media_snapshot',return_value={'tidal':{'running':True,'state':'unknown'}}),patch('companion.tidal.control',side_effect=RuntimeError('unavailable')),patch.object(windows.user32,'keybd_event') as key:
            with self.assertRaises(RuntimeError):windows.media('toggle','system',[])
        key.assert_not_called()
    def test_tidal_volume_remains_windows_volume(self):
        with patch.object(windows.user32,'keybd_event') as key,patch('companion.tidal.control') as control:
            windows.media('mute','tidal',[])
        self.assertEqual(key.call_count,2);control.assert_not_called()
    def test_invalid_target_or_action_cannot_invoke_helper(self):
        with patch('companion.tidal.target') as target:
            with self.assertRaises(ValueError):tidal.invoke('arbitrary-command',[])
        target.assert_not_called()
        with self.assertRaises(ValueError):windows.media('pause','not-player',[])
    def test_snapshot_reports_running_but_uncontrollable_without_claiming_paused(self):
        with patch('companion.tidal.invoke',side_effect=RuntimeError('changed UI')):
            state=tidal.snapshot([])
        self.assertTrue(state['running']);self.assertFalse(state['available']);self.assertEqual(state['state'],'unknown')
    def test_snapshot_cache_is_scoped_to_catalog_identity(self):
        with patch('companion.tidal.invoke',return_value={'available':True,'state':'paused'}) as invoke:
            tidal.snapshot([]);tidal.snapshot([]);tidal.snapshot([{'id':'new','name':'TIDAL','target':'new-path'}])
            self.assertEqual(invoke.call_count,2)
    def test_auto_action_refreshes_cached_tidal_before_selecting_player(self):
        with patch('companion.tidal.invoke',side_effect=[{'available':True,'state':'paused'},{'available':True,'state':'playing'}]),patch('companion.windows.aimp_snapshot',return_value={'aimp':True,'state':'playing'}),patch('companion.tidal.control') as control,patch.object(windows.user32,'keybd_event') as key:
            tidal.snapshot([])
            with self.assertRaises(ValueError):windows.media('pause','system',[])
        control.assert_not_called();key.assert_not_called()
    def test_control_invalidates_old_status_even_on_error(self):
        tidal._cached={'state':'paused'};tidal._until=100000
        with patch('companion.tidal.invoke',side_effect=RuntimeError('rejected')):
            with self.assertRaises(RuntimeError):tidal.control('play',[])
        self.assertIsNone(tidal._cached);self.assertEqual(tidal._until,0)
    def test_missing_tidal_does_not_run_a_helper(self):
        with patch('companion.tidal.target',return_value=None),patch('companion.tidal.run_owned') as run:
            with self.assertRaises(ValueError):tidal.invoke('pause',[])
        run.assert_not_called()
    def test_helper_timeout_and_invalid_json_never_report_success_or_retry(self):
        lease={'hwnd':1,'process':{'pid':2,'created':3,'path':'C:/fixture/TIDAL.exe'}}
        failures=[subprocess.TimeoutExpired('fixture',8),subprocess.CompletedProcess([],0,'[]'),subprocess.CompletedProcess([],0,'{"state":"unknown"}'),subprocess.CompletedProcess([],0,'bad json')]
        for failure in failures:
            with self.subTest(failure=str(failure)),patch('companion.tidal.target',return_value=lease),patch('companion.tidal.Path.is_file',return_value=True),patch('companion.tidal.run_owned',side_effect=failure if isinstance(failure,Exception) else None,return_value=failure) as run:
                with self.assertRaises(RuntimeError):tidal.invoke('pause',[])
                self.assertEqual(run.call_count,1)

if __name__=='__main__':unittest.main()
