"""Ownership regression: independent processes, isolated directory only."""
import contextlib,json,os,subprocess,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from companion.ownership import receiver_lease
from companion.desktop import main,run_receiver
from companion.core import Deck,start
ROOT=Path(__file__).resolve().parents[1]
CHILD="""import sys,os
from companion.ownership import receiver_lease
with receiver_lease(sys.argv[1]) as owned:
 print('owned' if owned else 'busy',flush=True)
 if owned and sys.stdin.readline().strip()=='crash':os._exit(17)
"""

class OwnershipTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory(prefix='eddy-ownership-');self.data=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def child(self):
        return subprocess.Popen([sys.executable,'-c',CHILD,str(self.data)],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=0x08000000)
    def test_other_process_cannot_acquire_until_owner_exits(self):
        child=self.child()
        try:
            self.assertEqual(child.stdout.readline().strip(),'owned')
            with receiver_lease(self.data) as owned:self.assertFalse(owned)
            child.communicate('\n',timeout=5);self.assertEqual(child.returncode,0)
            with receiver_lease(self.data) as owned:self.assertTrue(owned)
        finally:
            if child.poll() is None:child.terminate();child.wait(5)
            for stream in (child.stdin,child.stdout,child.stderr):
                if stream:stream.close()
    def test_os_releases_lock_after_abrupt_exit_of_own_fixture(self):
        child=self.child()
        try:
            self.assertEqual(child.stdout.readline().strip(),'owned')
            # Exit inside the actual lock-owning interpreter, bypassing finally.
            # Killing only a Windows venv launcher would not prove owner exit.
            child.communicate('crash\n',timeout=5);self.assertEqual(child.returncode,17)
            with receiver_lease(self.data) as owned:self.assertTrue(owned)
        finally:
            if child.poll() is None:child.terminate();child.wait(5)
            for stream in (child.stdin,child.stdout,child.stderr):
                if stream:stream.close()
    def test_second_headless_cli_does_not_construct_or_recover_deck(self):
        with receiver_lease(self.data) as owned:
            self.assertTrue(owned)
            with patch('sys.argv',['run.py','--headless','--data',str(self.data)]),patch('companion.desktop.Deck') as deck,patch('socket.create_connection',side_effect=OSError('isolated fixture')):
                main();deck.assert_not_called()
        self.assertFalse((self.data/'operations.sqlite3').exists())
    def test_legacy_headless_health_is_checked_before_journal_recovery(self):
        response=MagicMock();response.__enter__.return_value.read.return_value=b'{"name":"Eddy Deck","healthy":true}'
        with patch('socket.create_connection',side_effect=OSError('no activation')),patch('urllib.request.urlopen',return_value=response),patch('companion.desktop.Deck') as deck:
            run_receiver(types.SimpleNamespace(headless=True,dry_run=False),self.data);deck.assert_not_called()

    def test_unhealthy_legacy_headless_is_still_an_active_owner(self):
        import io,urllib.error
        failure=urllib.error.HTTPError('http://127.0.0.1:47989/health',503,'Unhealthy fixture',None,io.BytesIO(b'{"name":"Eddy Deck","healthy":false}'))
        with patch('socket.create_connection',side_effect=OSError('no activation')),patch('urllib.request.urlopen',side_effect=failure),patch('companion.desktop.Deck') as deck:
            run_receiver(types.SimpleNamespace(headless=True,dry_run=False),self.data);deck.assert_not_called()

    @contextlib.contextmanager
    def isolated_entry(self):
        with patch('socket.create_connection',side_effect=OSError('no activation')),patch('urllib.request.urlopen',side_effect=OSError('no previous receiver')),patch('logging.handlers.RotatingFileHandler'),patch('logging.basicConfig'),patch('logging.exception'),patch('companion.desktop.messagebox.showerror') as dialog:
            yield dialog

    def test_corrupt_profile_is_preserved_and_explained(self):
        for name in ('deck.json','devices.json','manual-apps.json','catalog-hints.json'):
            with self.subTest(name=name):
                folder=self.data/name.replace('.json','');folder.mkdir();fixture=folder/name;fixture.write_bytes(b'{broken')
                with self.isolated_entry() as dialog:
                    run_receiver(types.SimpleNamespace(headless=False,dry_run=True),folder)
                    self.assertIn(name,dialog.call_args.args[1]);self.assertIn('restaura',dialog.call_args.args[1])
                self.assertEqual(fixture.read_bytes(),b'{broken')

    def test_partial_identity_is_preserved_and_queue_closed_before_dialog(self):
        for name in ('server.crt','server.key'):
            with self.subTest(name=name):
                folder=self.data/name;folder.mkdir();fixture=folder/name;fixture.write_bytes(b'original identity fixture')
                deck=Deck(folder,ROOT,dry_run=True)
                with self.isolated_entry() as dialog,patch('companion.desktop.Deck',return_value=deck):
                    dialog.side_effect=lambda *_:self.assertTrue(deck.closed and deck.queue.stopped)
                    run_receiver(types.SimpleNamespace(headless=False,dry_run=True),folder)
                    self.assertIn('certificado está incompleto',dialog.call_args.args[1])
                self.assertEqual(fixture.read_bytes(),b'original identity fixture')
                self.assertFalse(deck.queue.thread.is_alive())

    def test_failure_after_start_releases_resources_before_dialog(self):
        deck=MagicMock();closed=[];deck.close.side_effect=lambda:closed.append(True)
        with self.isolated_entry() as dialog,patch('companion.desktop.Deck',return_value=deck),patch('companion.desktop.start'),patch('companion.desktop.run_started_receiver',side_effect=RuntimeError('fallo simulado')):
            dialog.side_effect=lambda *_:self.assertEqual(closed,[True])
            run_receiver(types.SimpleNamespace(headless=False,dry_run=True),self.data)
        deck.close.assert_called_once()

    def test_headless_error_closes_without_opening_a_dialog(self):
        deck=MagicMock()
        with self.isolated_entry() as dialog,patch('companion.desktop.Deck',return_value=deck),patch('companion.desktop.start',side_effect=RuntimeError('fallo simulado')):
            with self.assertRaisesRegex(RuntimeError,'fallo simulado'):run_receiver(types.SimpleNamespace(headless=True,dry_run=True),self.data)
            dialog.assert_not_called()
        deck.close.assert_called_once()

    def test_certificate_load_failure_closes_both_unstarted_sockets(self):
        deck=types.SimpleNamespace(data=self.data)
        local=MagicMock();remote=MagicMock()
        with patch('companion.core.ensure_certificate',return_value=('cert','key','fixture')),patch('companion.core.Server',side_effect=[local,remote]),patch('companion.core.ssl.SSLContext') as tls:
            tls.return_value.load_cert_chain.side_effect=ValueError('fixture mismatched identity')
            with self.assertRaises(ValueError):start(deck)
        local.server_close.assert_called_once();remote.server_close.assert_called_once()

    def test_thread_start_failure_never_registers_unstarted_server_for_shutdown(self):
        for failing_thread in (1,2):
            with self.subTest(failing_thread=failing_thread):
                deck=types.SimpleNamespace(data=self.data)
                local=MagicMock();remote=MagicMock();threads=[MagicMock(),MagicMock()]
                threads[failing_thread-1].start.side_effect=RuntimeError('injected thread creation failure')
                with patch('companion.core.ensure_certificate',return_value=('cert','key','fixture')),patch('companion.core.Server',side_effect=[local,remote]),patch('companion.core.ssl.SSLContext'),patch('companion.core.threading.Thread',side_effect=threads):
                    with self.assertRaisesRegex(RuntimeError,'thread creation'):start(deck)
                self.assertEqual(deck.servers,[] if failing_thread==1 else [local])
                remote.server_close.assert_called_once();remote.shutdown.assert_not_called()
                if failing_thread==1:local.server_close.assert_called_once()
                else:local.server_close.assert_not_called()

    def test_real_remote_port_collision_releases_new_local_listener(self):
        import socket
        from companion.core import Server
        deck=Deck(self.data,ROOT,dry_run=True);created=[]
        def construct(*args):
            server=Server(*args);created.append(server);return server
        try:
            with socket.socket() as occupied:
                occupied.bind(('127.0.0.1',0));occupied.listen()
                with patch('companion.core.Server',side_effect=construct):
                    with self.assertRaises(OSError):start(deck,local_port=0,port=occupied.getsockname()[1],bind='127.0.0.1')
            self.assertEqual(len(created),1);self.assertEqual(created[0].socket.fileno(),-1);self.assertEqual(deck.servers,[])
        finally:deck.close()

if __name__=='__main__':unittest.main()
