import copy,json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from test_core import APP,ROOT,FakeWindows
from companion.core import Deck,APIError
from companion.diagnostics import report,safe_message
from companion.layout import _matches,requested_size
from companion.supervisor import restart_decision

class BetaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.deck=Deck(self.tmp.name,ROOT,adapter=FakeWindows());self.deck.apps=[copy.deepcopy(APP)]
        (Path(self.tmp.name)/'supervisor.json').write_text(json.dumps({'workerPid':os.getpid(),'at':time.time()}))
    def tearDown(self):self.deck.close();self.tmp.cleanup()
    def call(self,path,body=None):return self.deck.dispatch(path,{'requestId':str(time.time_ns()),**(body or {})},'local')
    def test_report_excludes_credentials_paths_and_urls(self):
        self.deck.devices=[{'id':'device','hash':'secret-hash','name':'private-name'}]
        self.deck.profile['cards']=[{'name':'private-title','url':'https://private.example'}]
        raw=json.dumps(report(self.deck))
        for hidden in ('secret-hash','private-name','private-title','private.example',self.deck.local_token,str(ROOT)):self.assertNotIn(hidden,raw)
    def test_support_message_redacts_sensitive_patterns(self):
        result=safe_message('Bearer abc123 token=xyz https://private.example/page C:\\Users\\Someone\\file.txt')
        for hidden in ('abc123','xyz','private.example','Someone'):self.assertNotIn(hidden,result)
    def test_repair_requires_confirmation_and_supervisor(self):
        with self.assertRaises(APIError):self.call('/api/repair')
        with patch.dict(os.environ,{'EDDY_DECK_SUPERVISED':'0'}),self.assertRaises(APIError):self.call('/api/repair',{'confirm':True})
        self.assertFalse((Path(self.tmp.name)/'restart-request.json').exists())
    def test_repair_preserves_identity_cancels_work_and_writes_report(self):
        original=copy.deepcopy(self.deck.profile);self.deck.pending={'action':'sleep'}
        self.deck.queue.submit('pending',[{'type':'wait','seconds':5}],'local')
        with patch.dict(os.environ,{'EDDY_DECK_SUPERVISED':'1'}):
            r=self.call('/api/repair',{'confirm':True});self.assertEqual(r['status'],'restarting')
            self.assertEqual(self.call('/api/repair',{'confirm':True})['status'],'restarting')
        self.assertEqual(original,self.deck.profile);self.assertIsNone(self.deck.pending)
        request=json.loads((Path(self.tmp.name)/'restart-request.json').read_text());self.assertEqual(request['pid'],os.getpid())
        self.assertTrue((Path(self.tmp.name)/'reports'/(r['reportId']+'.json')).exists())
        with self.assertRaises(APIError):self.call('/api/media',{'action':'next'})
    def test_repair_rate_limit_survives_new_deck(self):
        with patch.dict(os.environ,{'EDDY_DECK_SUPERVISED':'1'}):
            self.call('/api/repair',{'confirm':True});self.deck.close();self.deck=Deck(self.tmp.name,ROOT,adapter=FakeWindows())
            with self.assertRaises(APIError) as e:self.call('/api/repair',{'confirm':True})
            self.assertEqual(e.exception.status,429)
    def test_diagnostics_and_failed_operations_are_audited(self):
        self.call('/api/diagnostics')
        with self.assertRaises(ValueError):self.call('/api/cards/save',{'appId':'missing'})
        rows=[json.loads(x) for x in (Path(self.tmp.name)/'audit.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual([r['status'] for r in rows],['ready','failed'])
    def test_watchdog_stops_on_intentional_exit_and_limits_crash_loop(self):
        self.assertEqual(restart_decision(0,0),'stop');self.assertEqual(restart_decision(-1,1),'restart');self.assertEqual(restart_decision(-1,5),'pause');self.assertEqual(restart_decision(0,5,True),'restart')
    def test_fixed_size_windows_keep_their_size(self):
        self.assertEqual(requested_size('windowed',False,(5,10,605,410),1920,1080),(600,400))
        self.assertEqual(requested_size('windowed',True,(5,10,605,410),1920,1080),(1536,864))
    def test_steam_identity_is_confined_to_observed_install(self):
        app={'name':'A game','target':'steam://rungameid/1','kind':'protocol','installedRoot':r'C:\Games\Example'}
        for path,expected in [(r'C:\Games\Example\Game.exe',True),(r'C:\Games\ExampleOther\Game.exe',False),(r'C:\Games\Example\start_protected_game.exe',False)]:
            self.assertEqual(_matches(app,[{'path':path,'aumid':''}]),expected)
    def test_second_instance_never_initializes_or_interrupts_journal(self):
        from companion.desktop import main
        with patch('sys.argv',['run.py','--worker','--data',self.tmp.name]),patch('socket.create_connection',return_value=MagicMock()),patch('companion.desktop.Deck') as make:
            main();make.assert_not_called()
    def test_disk_write_failure_does_not_leave_a_phantom_button(self):
        original=copy.deepcopy(self.deck.profile)
        with patch.object(self.deck,'save',side_effect=OSError('Disco lleno')),self.assertRaises(OSError):self.call('/api/cards/save',{'appId':APP['id']})
        self.assertEqual(self.deck.profile,original)
    def test_explorer_only_matches_file_windows_never_desktop(self):
        app={'name':'Explorador de archivos','target':'Microsoft.Windows.Explorer','kind':'shell'};p=[{'path':r'C:\Windows\explorer.exe','aumid':''}]
        self.assertTrue(_matches(app,p,'CabinetWClass'))
        self.assertFalse(_matches(app,p,'Progman'));self.assertFalse(_matches(app,p,'WorkerW'))
    def test_shared_launcher_is_not_mistaken_for_one_specific_app(self):
        app={'name':'Special mode','target':r'C:\Example\host.exe','kind':'shortcut','sharedExecutable':True}
        self.assertFalse(_matches(app,[{'path':r'C:\Example\host.exe','aumid':''}]))
    def test_stale_supervisor_never_accepts_a_repair_it_cannot_do(self):
        (Path(self.tmp.name)/'supervisor.json').write_text(json.dumps({'workerPid':os.getpid(),'at':time.time()-60}))
        with patch.dict(os.environ,{'EDDY_DECK_SUPERVISED':'1'}),self.assertRaises(APIError):self.call('/api/repair',{'confirm':True})
    def test_disguised_shell_entry_cannot_restore_a_blocked_target(self):
        from companion.windows import normalize_inventory
        self.assertEqual(normalize_inventory({'apps':[{'name':'Friendly name','target':'Microsoft.AutoGenerated.Example','kind':'shell','blockedResolvedTarget':True}]}),[])

    def test_explorer_shell_folder_is_allowed_only_for_exact_identity(self):
        from companion.windows import blocked_shell_target
        folder='::{52205FD8-5DFB-447D-801A-D0B52F2E83E1}'
        self.assertFalse(blocked_shell_target('Microsoft.Windows.Explorer',folder))
        self.assertTrue(blocked_shell_target('Unknown.Application',folder))

    def test_auxiliary_audit_failure_does_not_turn_success_into_failure(self):
        real_open=Path.open
        def fail_audit(path,*args,**kwargs):
            if path.name=='audit.jsonl':raise OSError('Disco lleno')
            return real_open(path,*args,**kwargs)
        with patch.object(Path,'open',fail_audit):
            result=self.call('/api/cards/save',{'appId':APP['id']})
        self.assertEqual(result['status'],'saved')
        self.assertTrue(any(c['id']==result['card']['id'] for c in self.deck.profile['cards']))

    def test_failed_restart_request_does_not_lock_the_receiver(self):
        from companion.core import atomic_json
        def fail_restart(path,value):
            if path.name=='restart-request.json':raise OSError('Disco lleno')
            return atomic_json(path,value)
        with patch.dict(os.environ,{'EDDY_DECK_SUPERVISED':'1'}),patch('companion.core.atomic_json',fail_restart),self.assertRaises(OSError):
            self.call('/api/repair',{'confirm':True})
        self.assertFalse(self.deck.repairing)
        self.assertEqual(self.call('/api/cards/save',{'appId':APP['id']})['status'],'saved')

    def test_add_portable_persists_and_deduplicates(self):
        from companion.desktop import Desktop
        exe=Path(self.tmp.name)/'Demo.exe';exe.write_bytes(b'fixture, never executed')
        desktop=MagicMock();desktop.deck=self.deck
        with patch('companion.desktop.filedialog.askopenfilename',return_value=str(exe)),patch('companion.desktop.messagebox.showinfo'),patch.object(self.deck,'start_scan') as scan:
            Desktop.add_manual(desktop);Desktop.add_manual(desktop)
        self.assertEqual(len(self.deck.manual),1);self.assertEqual(scan.call_count,2)
        self.assertEqual(json.loads((self.deck.data/'manual-apps.json').read_text()),self.deck.manual)

    def test_add_portable_disk_failure_preserves_previous_list(self):
        from companion.desktop import Desktop
        exe=Path(self.tmp.name)/'Demo.exe';exe.write_bytes(b'fixture, never executed')
        desktop=MagicMock();desktop.deck=self.deck;original=copy.deepcopy(self.deck.manual)
        with patch('companion.desktop.filedialog.askopenfilename',return_value=str(exe)),patch('companion.desktop.atomic_json',side_effect=OSError('full')),patch('companion.desktop.messagebox.showerror') as error,patch.object(self.deck,'start_scan') as scan:
            Desktop.add_manual(desktop)
        self.assertEqual(self.deck.manual,original);error.assert_called_once();scan.assert_not_called()

    def test_add_portable_rejects_command_interpreter(self):
        from companion.desktop import Desktop
        exe=Path(self.tmp.name)/'cmd.exe';exe.write_bytes(b'fixture, never executed')
        desktop=MagicMock();desktop.deck=self.deck
        with patch('companion.desktop.filedialog.askopenfilename',return_value=str(exe)),patch('companion.desktop.messagebox.showerror') as error:
            Desktop.add_manual(desktop)
        self.assertFalse(self.deck.manual);error.assert_called_once()

if __name__=='__main__':unittest.main()
