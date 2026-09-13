import copy,json,os,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from test_core import APP,ROOT,FakeWindows
from companion.core import Deck,APIError,validate_profile
from companion.layout import requested_size,resolve_monitor,validate_layout

class Beta2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.fake=FakeWindows();self.deck=Deck(self.tmp.name,ROOT,adapter=self.fake);self.deck.apps=[copy.deepcopy(APP)]
    def tearDown(self):self.deck.close();self.tmp.cleanup()
    def call(self,path,body=None):return self.deck.dispatch(path,{'requestId':str(time.time_ns()),**(body or {})},'local')
    def wait(self,jid):
        until=time.monotonic()+3
        while time.monotonic()<until:
            job=next(j for j in self.deck.journal.jobs() if j['id']==jid)
            if job['status'] not in ('queued','running'):return job
            time.sleep(.01)
        self.fail('La tarea no terminó')
    def test_import_maps_unique_app_name_without_trusting_paths(self):
        self.call('/api/cards/save',{'appId':APP['id'],'name':'My card'})
        profile=self.deck.export_profile();old=APP['id'];new=copy.deepcopy(APP);new['id']='other-pc';new['target']='C:/different.exe';self.deck.apps=[new]
        r=self.call('/api/backup/import',{'profile':profile});self.assertEqual(r['mappedApps'],1);self.assertEqual(self.deck.profile['cards'][0]['appId'],'other-pc')
        self.assertFalse(self.fake.calls)
    def test_import_never_guesses_between_same_name_apps(self):
        self.call('/api/cards/save',{'appId':APP['id'],'name':'My card'});profile=self.deck.export_profile()
        self.deck.apps=[{**APP,'id':'one'},{**APP,'id':'two'}]
        r=self.call('/api/backup/import',{'profile':profile});self.assertEqual(r['missingApps'],1);self.assertEqual(self.deck.profile['cards'][0]['appId'],APP['id'])
    def test_profile_write_failure_rolls_back_memory_and_restart(self):
        original=copy.deepcopy(self.deck.profile)
        with patch('companion.core.atomic_json',side_effect=OSError('full disk')):
            with self.assertRaises(OSError):self.call('/api/cards/save',{'appId':APP['id'],'name':'Not saved'})
        self.assertEqual(self.deck.profile,original)
    def test_broken_journal_still_generates_diagnostic_report(self):
        from companion.diagnostics import report
        with patch.object(self.deck.journal,'jobs',side_effect=OSError('corrupt')):
            result=report(self.deck)
        self.assertEqual(result['journalError'],'OSError')
    def test_refresh_remaps_updated_app_without_mutating_queued_snapshot(self):
        self.call('/api/cards/save',{'appId':APP['id'],'name':'Saved'})
        self.deck.profile['seeded']=True;self.deck.save();self.deck.queue.pause(True)
        job=self.call('/api/launch',{'appId':APP['id']})
        self.fake.scan=lambda _:([{**APP,'id':'updated-app'}],[])
        self.deck.refresh();self.assertEqual(self.deck.profile['cards'][0]['appId'],'updated-app')
        self.deck.queue.pause(False);self.assertEqual(self.wait(job['jobId'])['status'],'failed');self.assertFalse(self.fake.calls)
    def test_refresh_persists_app_hints_for_next_start(self):
        self.call('/api/cards/save',{'appId':APP['id'],'name':'Saved'});self.deck.profile['seeded']=True;self.deck.save()
        self.deck.refresh();self.assertIn(APP['id'],json.loads((self.deck.data/'catalog-hints.json').read_text()))
        self.deck.apps=[];self.fake.scan=lambda _:([{**APP,'id':'new-after-restart'}],[])
        self.deck.refresh();self.assertEqual(self.deck.profile['cards'][0]['appId'],'new-after-restart')
    def test_large_profile_is_valid_but_extreme_urls_are_bounded(self):
        steps=[{'appId':APP['id'],'url':'https://example.com/'+('a'*500)} for _ in range(24)]
        profile={'version':2,'cards':[],'scenes':[{'id':'routine-'+str(i),'name':'Many steps','steps':steps} for i in range(50)]}
        self.assertGreater(len(json.dumps(profile)),131072);self.assertEqual(len(validate_profile(profile)['scenes']),50)
        for s in steps:s['url']='https://example.com/'+('a'*1900)
        with self.assertRaises(ValueError):validate_profile(profile)
    def test_pause_cancel_removes_waiting_job_without_resuming(self):
        self.call('/api/jobs/pause',{'paused':True})
        r=self.call('/api/launch',{'appId':APP['id']})
        time.sleep(.05);self.assertFalse(self.fake.calls)
        self.assertEqual(self.call('/api/jobs/cancel',{'id':r['jobId']})['status'],'cancelled')
        self.assertEqual(self.wait(r['jobId'])['status'],'cancelled')
        self.assertEqual(self.deck.queue.status()['waiting'],0)
    def test_resume_runs_waiting_commands_in_order(self):
        self.call('/api/jobs/pause',{'paused':True})
        a=self.call('/api/launch',{'appId':APP['id'],'url':'https://a.example'})
        b=self.call('/api/launch',{'appId':APP['id'],'url':'https://b.example'})
        self.call('/api/jobs/pause',{'paused':False})
        self.assertEqual(self.wait(a['jobId'])['status'],'completed');self.assertEqual(self.wait(b['jobId'])['status'],'completed')
        self.assertEqual([c[2] for c in self.fake.calls],['https://a.example','https://b.example'])
    def test_different_failure_policies_are_not_deduplicated(self):
        self.deck.queue.pause(True);steps=[{'type':'wait','seconds':.01}]
        a=self.deck.queue.submit('Same',steps,'local','stop');b=self.deck.queue.submit('Same',steps,'local','continue')
        self.assertNotEqual(a['jobId'],b['jobId'])
    def test_queued_routine_is_a_snapshot_not_mutated_by_edit(self):
        self.deck.queue.pause(True)
        self.call('/api/scenes/save',{'name':'Old','steps':[{'appId':APP['id'],'url':'https://old.example'}]})
        sid=self.deck.profile['scenes'][-1]['id'];r=self.call('/api/scenes/run',{'id':sid})
        self.call('/api/scenes/save',{'id':sid,'name':'New','steps':[{'appId':APP['id'],'url':'https://new.example'}]})
        self.deck.queue.pause(False);self.assertEqual(self.wait(r['jobId'])['status'],'completed')
        self.assertEqual(self.fake.calls[0][2],'https://old.example')
    def test_pending_energy_and_repair_block_queue_admission(self):
        for key in ('pending','repairing'):
            setattr(self.deck,key,True)
            with self.assertRaises(APIError):self.deck.enqueue('bad',[{'type':'wait','seconds':0}],'local')
            setattr(self.deck,key,None if key=='pending' else False)
        self.assertFalse(self.fake.calls)
    def test_energy_cannot_cross_atomic_queue_admission(self):
        entered=threading.Event();release=threading.Event();confirmed=threading.Event();submit=self.deck.queue.submit
        def hold(*args,**kwargs):entered.set();release.wait(2);return submit(*args,**kwargs)
        self.deck.queue.pause(True)
        challenge=self.call('/api/power/prepare',{'action':'sleep'})['challenge']
        with patch.object(self.deck.queue,'submit',hold):
            first=threading.Thread(target=lambda:self.call('/api/launch',{'appId':APP['id']}));first.start();self.assertTrue(entered.wait(1))
            second=threading.Thread(target=lambda:(self.call('/api/power/confirm',{'challenge':challenge}),confirmed.set()));second.start()
            self.assertFalse(confirmed.wait(.05));release.set();first.join(2);second.join(2)
        self.assertTrue(confirmed.is_set());self.assertEqual(self.deck.queue.status()['waiting'],0);self.call('/api/power/cancel')
    def test_queue_journal_failure_is_detectable_not_silent(self):
        self.deck.queue.pause(True);r=self.call('/api/launch',{'appId':APP['id']})
        with patch.object(self.deck.journal,'save_job',side_effect=OSError('disk')):
            self.deck.queue.pause(False);self.deck.queue.thread.join(2)
        self.assertFalse(self.deck.queue.status()['healthy']);self.assertIsNone(self.deck.queue.active)
        with self.assertRaises(ValueError):self.deck.queue.submit('more',[{'type':'wait','seconds':0}],'local')
    def test_headless_routine_without_layout_still_runs(self):
        self.call('/api/scenes/save',{'name':'No display','steps':[{'appId':APP['id']} ]})
        with patch('companion.core.monitors',return_value=[]):r=self.call('/api/scenes/run',{'id':self.deck.profile['scenes'][-1]['id']})
        self.assertEqual(self.wait(r['jobId'])['status'],'completed')
    def test_pair_write_failure_does_not_grant_phantom_device(self):
        pin=self.deck.renew_pin()
        with patch('companion.core.atomic_json',side_effect=OSError('disk')),self.assertRaises(OSError):self.deck.pair({'pin':pin},'127.0.0.1')
        self.assertFalse(self.deck.devices);self.assertEqual(self.deck.pin,pin)
    def test_monitor_arrival_removal_and_laptop_single_screen(self):
        m={'id':'display:laptop','primary':True,'vertical':False};v={'id':'display:dock','primary':False,'vertical':True}
        settings=validate_layout({'monitor':'vertical','missing':'primary'})
        self.assertEqual(resolve_monitor(settings,[m])[0],m)
        self.assertEqual(resolve_monitor(settings,[m,v])[0],v)
        self.assertEqual(resolve_monitor(settings,[m])[0],m)
        self.assertEqual(resolve_monitor(validate_layout({'monitor':'right'}),[m])[0],m)
        with self.assertRaises(ValueError):resolve_monitor(settings,[])
    def test_small_screen_geometry_never_exceeds_work_area(self):
        for width,height in [(200,150),(800,600),(1920,1080),(3840,2160),(1080,1920)]:
            w,h=requested_size('windowed',True,(0,0,300,200),width,height)
            self.assertTrue(0<w<=width and 0<h<=height)
    def test_monitor_failure_does_not_hide_independent_windows(self):
        self.deck.layouts.snapshot=MagicMock(return_value=[{'id':'independent'}])
        with patch('companion.core.monitors',side_effect=RuntimeError('unplug')):state=self.deck.state()
        self.assertEqual(state['windows'],[{'id':'independent'}]);self.assertTrue(state['displayWarning'])
    def test_force_close_challenge_cannot_be_used_for_power(self):
        self.deck.layouts.require_window=MagicMock(return_value={'id':'window','process':'fixture.exe'})
        challenge=self.call('/api/windows/terminate/prepare',{'windowId':'window'})['challenge']
        with self.assertRaises(APIError):self.call('/api/power/confirm',{'challenge':challenge})
        self.assertIsNone(self.deck.pending)
    def test_power_challenge_cannot_be_used_to_terminate(self):
        challenge=self.call('/api/power/prepare',{'action':'sleep'})['challenge']
        with self.assertRaises(APIError):self.call('/api/windows/terminate/confirm',{'challenge':challenge})
    def test_expired_force_close_never_runs_after_slow_queue(self):
        self.deck.layouts.terminate_window=MagicMock()
        with self.assertRaises(ValueError):self.deck.execute_step({'type':'windowTerminate','windowId':'old','expires':time.monotonic()-1},lambda:None)
        self.deck.layouts.terminate_window.assert_not_called()
    def test_force_close_is_not_allowed_as_a_routine_step(self):
        for kind in ('windowClose','windowTerminate','terminate','shell'):
            with self.assertRaises(ValueError):self.deck.clean_step({'type':kind,'appId':APP['id']})
    def test_app_open_policy_survives_profile_export(self):
        self.call('/api/cards/save',{'appId':APP['id'],'ifOpen':'launch'})
        self.assertEqual(validate_profile(self.deck.profile)['cards'][0]['ifOpen'],'launch')
    def test_large_catalog_exports_only_referenced_apps(self):
        self.deck.apps=[{**APP,'id':'app-'+str(i),'name':'App '+str(i)} for i in range(1501)]
        self.call('/api/cards/save',{'appId':'app-1500','name':'Last app'})
        self.deck.profile['seeded']=True;self.deck.save()
        self.fake.scan=lambda _:(self.deck.apps,[])
        self.deck.refresh();backup=self.deck.export_profile()
        self.assertEqual(set(backup['catalogHints']),{'app-1500'})
        self.assertEqual(self.deck.remap_profile(backup)[2],0)
    def test_full_profile_can_reference_1400_different_apps(self):
        self.deck.apps=[{**APP,'id':'app-'+str(i),'name':'App '+str(i)} for i in range(1400)]
        profile={'version':2,'cards':[{'id':'c'+str(i),'appId':'app-'+str(i),'name':'Card'} for i in range(200)],'scenes':[{'id':'s'+str(i),'name':'Routine','steps':[{'appId':'app-'+str(200+i*24+j)} for j in range(24)]} for i in range(50)]}
        self.deck.profile=validate_profile(profile);backup=self.deck.export_profile()
        self.assertEqual(len(backup['catalogHints']),1400)
        self.assertEqual(self.deck.remap_profile(backup)[2],0)
    def test_backup_metadata_does_not_consume_profile_size_budget(self):
        profile=validate_profile({'version':2,'cards':[],'scenes':[{'id':'s'+str(i),'name':'Routine','steps':[{'appId':APP['id'],'url':'https://example.com/'+('a'*900)} for j in range(24)]} for i in range(50)]})
        size=len(json.dumps(profile).encode());self.assertLess(size,1500000)
        profile['catalogHints']={APP['id']:{'name':'x'*(1500000-size),'identity':''}}
        self.assertGreater(len(json.dumps(profile).encode()),1500000)
        self.assertEqual(len(validate_profile(profile)['scenes']),50)

if __name__=='__main__':unittest.main()
