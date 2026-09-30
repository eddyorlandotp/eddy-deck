"""Beta 12: identity-preserving self-healing after an antivirus removal."""
import json, os, shutil, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from companion import resilience


def fake_exe(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(os.environ['WINDIR']) / 'System32' / 'where.exe', path)
    return path


def manifest(folder, version):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'release-manifest.json').write_text(json.dumps({'version': version}), encoding='utf-8')


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='eddy-resilience-'))
        self.local = self.root / 'Local'; self.roaming = self.root / 'Roaming'; self.data = self.root / 'data'
        for p in (self.local, self.roaming, self.data): p.mkdir()
        self.env = mock.patch.dict(os.environ, {'LOCALAPPDATA': str(self.local), 'APPDATA': str(self.roaming)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.root, ignore_errors=True)


class VersionOrder(unittest.TestCase):
    def test_matches_checker_ordering(self):
        key = resilience.version_key
        self.assertGreater(key('2.2.10-beta.12'), key('2.2.9-beta.11'))
        self.assertGreater(key('2.2.9-beta.11'), key('2.2.9-beta.2'))
        self.assertGreater(key('2.3.0'), key('2.3.0-rc.1'))
        self.assertGreater(key('2.3.0-rc.1'), key('2.3.0-beta.9'))
        for bad in ('', '2.2', 'v2.2.9', '2.2.9-beta', '2.2.9-gamma.1', None):
            with self.assertRaises(ValueError):
                key(bad)


class Shortcuts(Sandbox):
    def test_shortcut_never_drifts_to_a_previous_copy(self):
        """Reproduces the beta 11 incident: EddyDeck.exe disappears after an
        update moved the old folder aside. A tracked link follows the old copy;
        the new link keeps pointing to the installed path."""
        results = {}
        for kind in ('legacy', 'safe'):
            app = self.local / kind / 'EddyDeck'
            exe = fake_exe(app / 'EddyDeck.exe')
            link = self.root / (kind + '.lnk')
            if kind == 'legacy':
                import pythoncom, win32com.client
                pythoncom.CoInitialize()
                try:
                    shortcut = win32com.client.Dispatch('WScript.Shell').CreateShortcut(str(link))
                    shortcut.TargetPath = str(exe); shortcut.Save(); shortcut = None
                finally:
                    pythoncom.CoUninitialize()
            else:
                resilience.write_shortcut(link, exe, '', 'prueba')
            os.replace(app, app.with_name('EddyDeck-previous-abc'))
            app.mkdir()
            results[kind] = self.resolved(link)
        self.assertIn('EddyDeck-previous-abc', results['legacy'], 'the probe must reproduce the drift, otherwise it proves nothing')
        self.assertNotIn('previous', results['safe'])
        self.assertEqual(Path(results['safe']), self.local / 'safe' / 'EddyDeck' / 'EddyDeck.exe')

    @staticmethod
    def resolved(link):
        import pythoncom
        from win32com.shell import shell
        pythoncom.CoInitialize()
        try:
            item = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
            item.QueryInterface(pythoncom.IID_IPersistFile).Load(str(link))
            try:
                item.Resolve(0, 0x1 | (3000 << 16))  # SLR_NO_UI, 3 s
            except Exception:
                pass
            return item.GetPath(0)[0]
        finally:
            pythoncom.CoUninitialize()

    def test_shortcut_ok_requires_target_arguments_and_flags(self):
        exe = fake_exe(self.local / 'Programs' / 'EddyDeck' / 'EddyDeck.exe')
        link = self.root / 'a.lnk'
        resilience.write_shortcut(link, exe, '--tray')
        target, args, flags = resilience.read_shortcut(link)
        self.assertEqual(Path(target), exe)
        self.assertEqual(args, '--tray')
        self.assertEqual(flags & resilience.NO_TRACKING, resilience.NO_TRACKING)
        self.assertTrue(resilience.shortcut_ok(link, exe, '--tray'))
        self.assertFalse(resilience.shortcut_ok(link, exe, ''))
        self.assertFalse(resilience.shortcut_ok(link, exe.with_name('Otro.exe'), '--tray'))
        self.assertFalse(resilience.shortcut_ok(self.root / 'missing.lnk', exe))
        # Rewriting replaces the file and leaves no temporary shortcut behind.
        resilience.write_shortcut(link, exe, '')
        self.assertEqual([p.name for p in self.root.glob('*.lnk')], ['a.lnk'])


class StaleCopies(Sandbox):
    def test_only_previous_copies_are_disabled_and_files_kept(self):
        programs = self.local / 'Programs'
        current = fake_exe(programs / 'EddyDeck' / 'EddyDeck.exe')
        old = [fake_exe(programs / f'EddyDeck-previous-{i}' / 'EddyDeck.exe') for i in range(3)]
        (programs / 'EddyDeck-previous-0' / '_internal').mkdir()
        other = fake_exe(programs / 'OtraApp' / 'EddyDeck.exe')
        changed = resilience.disable_stale_copies(programs)
        self.assertEqual(sorted(changed), [f'EddyDeck-previous-{i}' for i in range(3)])
        self.assertTrue(current.is_file()); self.assertTrue(other.is_file())
        for exe in old:
            self.assertFalse(exe.exists())
            self.assertTrue(exe.with_name('EddyDeck.exe.anterior').is_file())
        self.assertTrue((programs / 'EddyDeck-previous-0' / '_internal').is_dir())
        self.assertEqual(resilience.disable_stale_copies(programs), [], 'idempotent')

    def test_running_copy_is_skipped_without_error(self):
        programs = self.local / 'Programs'
        exe = fake_exe(programs / 'EddyDeck-previous-busy' / 'EddyDeck.exe')
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        k.CreateFileW.restype = wintypes.HANDLE
        handle = k.CreateFileW(str(exe), 0x80000000, 1, None, 3, 0, None)  # like a running image: no delete sharing
        try:
            self.assertEqual(resilience.disable_stale_copies(programs), [])
            self.assertTrue(exe.is_file())
        finally:
            k.CloseHandle(handle)
        self.assertEqual(resilience.disable_stale_copies(programs), ['EddyDeck-previous-busy'])

    def test_missing_programs_folder(self):
        self.assertEqual(resilience.disable_stale_copies(self.root / 'nope'), [])


class Superseded(Sandbox):
    def test_older_copy_hands_over_to_installed(self):
        canonical = self.local / 'Programs' / 'EddyDeck'
        fake_exe(canonical / 'EddyDeck.exe'); manifest(canonical, '2.2.10-beta.12')
        old = fake_exe(self.local / 'Programs' / 'EddyDeck-previous-x' / 'EddyDeck.exe')
        self.assertEqual(resilience.superseded_by(old, '2.2.2-beta.4'), '2.2.10-beta.12')
        self.assertIsNone(resilience.superseded_by(old, '2.2.10-beta.12'), 'same version may run')
        self.assertIsNone(resilience.superseded_by(old, '2.3.0'), 'a newer package may run before installing')
        self.assertIsNone(resilience.superseded_by(canonical / 'EddyDeck.exe', '1.0.0'), 'the installed copy is never superseded')

    def test_unreadable_or_missing_install_never_blocks(self):
        other = fake_exe(self.root / 'Descargas' / 'EddyDeck.exe')
        self.assertIsNone(resilience.superseded_by(other, '1.0.0'))
        canonical = self.local / 'Programs' / 'EddyDeck'
        fake_exe(canonical / 'EddyDeck.exe')
        (canonical / 'release-manifest.json').write_text('{roto', encoding='utf-8')
        self.assertIsNone(resilience.superseded_by(other, '1.0.0'))


class Preferences(Sandbox):
    def test_startup_choice_survives_a_deleted_shortcut(self):
        link = resilience.startup_link(); link.parent.mkdir(parents=True)
        link.write_bytes(b'x')
        self.assertTrue(resilience.startup_wanted(self.data), 'inferred once from the legacy shortcut')
        link.unlink()  # antivirus removes the Startup shortcut
        self.assertTrue(resilience.startup_wanted(self.data), 'the saved choice remains')
        resilience.write_preferences(self.data, startup=False)
        self.assertFalse(resilience.startup_wanted(self.data))

    def test_no_shortcut_and_no_preference_means_disabled(self):
        self.assertFalse(resilience.startup_wanted(self.data))
        self.assertEqual(resilience.read_preferences(self.data), {'startup': False})

    def test_corrupt_preferences_are_ignored(self):
        (self.data / 'preferences.json').write_text('[1,2', encoding='utf-8')
        self.assertEqual(resilience.read_preferences(self.data), {})


class UserExit(Sandbox):
    def test_exit_is_respected_only_in_the_same_windows_session(self):
        self.assertFalse(resilience.user_exited(self.data))
        resilience.mark_user_exit(self.data)
        self.assertTrue(resilience.user_exited(self.data))
        self.assertTrue(resilience.user_exited(self.data, boot=time.time() - 3600))
        self.assertFalse(resilience.user_exited(self.data, boot=time.time() + 60), 'after a restart the app starts again')
        resilience.clear_user_exit(self.data)
        self.assertFalse(resilience.user_exited(self.data))

    def test_damaged_marker(self):
        (self.data / 'user-exit.json').write_text('no', encoding='utf-8')
        self.assertFalse(resilience.user_exited(self.data))


class Ensure(Sandbox):
    def setUp(self):
        super().setUp()
        programs = self.local / 'Programs'
        self.exe = fake_exe(programs / 'EddyDeck' / 'EddyDeck.exe')
        self.old = fake_exe(programs / 'EddyDeck-previous-1' / 'EddyDeck.exe')
        self.desktop = self.root / 'Desktop' / 'Eddy Deck.lnk'
        self.patch = mock.patch.object(resilience, 'desktop_link', return_value=self.desktop)
        self.patch.start()
        self.registered = mock.patch.object(resilience, 'watchdog_state', return_value='missing')
        self.register = mock.patch.object(resilience, 'register_watchdog')
        self.registered.start(); self.register_mock = self.register.start()

    def tearDown(self):
        mock.patch.stopall()
        super().tearDown()

    def test_repairs_the_observed_incident(self):
        # Desktop shortcut drifted to an old copy; Start menu and Startup deleted.
        resilience.write_shortcut(self.desktop, self.old)
        resilience.write_preferences(self.data, startup=True)
        rows = []
        result = resilience.ensure(self.data, lambda *a: rows.append(a))
        self.assertEqual(result['desktop'], 'repaired')
        self.assertEqual(result['menu'], 'repaired')
        self.assertEqual(result['startup'], 'repaired')
        self.assertEqual(result['staleCopies'], 1)
        self.assertTrue(resilience.shortcut_ok(self.desktop, self.exe))
        self.assertTrue(resilience.shortcut_ok(resilience.menu_link(), self.exe))
        self.assertTrue(resilience.shortcut_ok(resilience.startup_link(), self.exe, '--tray'))
        self.assertFalse(self.old.exists())
        self.register_mock.assert_called_once_with(self.data)
        self.assertEqual(rows[0][1:3], ('resilience.ensure', 'repaired'))

    def test_respects_user_choices_and_is_quiet_when_healthy(self):
        resilience.write_preferences(self.data, startup=False)
        rows = []
        first = resilience.ensure(self.data, lambda *a: rows.append(a))
        self.assertEqual(first['desktop'], 'absent', 'a deleted Desktop shortcut is not recreated')
        self.assertEqual(first['startup'], 'disabled')
        self.assertFalse(resilience.startup_link().exists())
        self.register_mock.assert_not_called()
        rows.clear()
        second = resilience.ensure(self.data, lambda *a: rows.append(a))
        self.assertEqual(second, {'menu': 'ok', 'desktop': 'absent', 'startup': 'disabled', 'staleCopies': 0})
        self.assertEqual(rows, [], 'no audit noise on every start')

    def test_watchdog_disabled_by_a_person_is_not_reenabled(self):
        resilience.write_preferences(self.data, startup=True)
        resilience.write_shortcut(resilience.startup_link(), self.exe, '--tray')
        with mock.patch.object(resilience, 'watchdog_state', return_value='disabled'):
            rows = []
            result = resilience.ensure(self.data, lambda *a: rows.append(a))
        self.register_mock.assert_not_called()
        self.assertEqual(result['startup'], 'watchdog-disabled-by-user')
        self.assertFalse(any('startup' in r[3] for r in rows), 'respected silently')

    def test_watchdog_pointing_elsewhere_is_replaced(self):
        resilience.write_preferences(self.data, startup=True)
        with mock.patch.object(resilience, 'watchdog_state', return_value='different'):
            resilience.ensure(self.data)
        self.register_mock.assert_called_once_with(self.data)

    def test_one_failing_step_does_not_stop_the_others(self):
        resilience.write_preferences(self.data, startup=True)
        self.register_mock.side_effect = RuntimeError('Task Scheduler no disponible')
        result = resilience.ensure(self.data)
        self.assertTrue(result['startup'].startswith('error:'))
        self.assertEqual(result['menu'], 'repaired')
        self.assertTrue(resilience.shortcut_ok(resilience.startup_link(), self.exe, '--tray'))


class WatchdogRegistration(Sandbox):
    def test_refuses_a_checker_that_differs_from_the_installed_release(self):
        from companion.integrity import CHECKER
        (self.data / 'Rescue').mkdir()
        (self.data / 'Rescue' / CHECKER).write_bytes(b'antiguo')
        canonical = self.local / 'Programs' / 'EddyDeck'; canonical.mkdir(parents=True)
        (canonical / CHECKER).write_bytes(b'nuevo')
        with mock.patch('win32com.client.Dispatch') as dispatch:
            with self.assertRaises(RuntimeError):
                resilience.register_watchdog(self.data)
            dispatch.assert_not_called()
        (self.data / 'Rescue' / CHECKER).unlink()
        with self.assertRaises(FileNotFoundError):
            resilience.register_watchdog(self.data)


class SupervisorGuard(unittest.TestCase):
    def test_old_copy_opens_installed_release_instead_of_itself(self):
        from companion import supervisor
        with mock.patch.object(sys, 'frozen', True, create=True), \
             mock.patch.object(sys, 'argv', ['EddyDeck.exe', '--tray']), \
             mock.patch.object(resilience, 'superseded_by', return_value='9.9.9'), \
             mock.patch('companion.supervisor.subprocess.Popen') as popen, \
             mock.patch('companion.storage.prepare_data') as prepare:
            supervisor.entry()
        prepare.assert_not_called()
        args = popen.call_args[0][0]
        self.assertEqual(Path(args[0]), resilience.canonical_exe())
        self.assertEqual(args[1:], ['--tray'])

    def test_only_salir_writes_the_exit_marker(self):
        """A worker also exits 0 when it finds another receiver; that must not
        stop the watchdog from reopening Eddy Deck later."""
        source = (ROOT / 'companion' / 'supervisor.py').read_text(encoding='utf-8')
        self.assertNotIn('mark_user_exit(', source)
        desktop = (ROOT / 'companion' / 'desktop.py').read_text(encoding='utf-8')
        quit_body = desktop[desktop.index('    def quit(self):'):desktop.index('    def run(self):')]
        self.assertIn('mark_user_exit(self.deck.data)', quit_body)

    def test_bypass_flags_are_never_redirected(self):
        from companion import supervisor
        with mock.patch.object(sys, 'frozen', True, create=True), \
             mock.patch.object(sys, 'argv', ['EddyDeck.exe', '--install-silent']), \
             mock.patch.object(resilience, 'superseded_by', return_value='9.9.9') as check, \
             mock.patch('companion.desktop.main') as main:
            supervisor.entry()
        main.assert_called_once()
        check.assert_not_called()


class SupervisorLiveness(unittest.TestCase):
    """The beta 11 audit showed 67 restarts after ~6 s of failed checks."""
    def setUp(self):
        self.data = Path(tempfile.mkdtemp(prefix='eddy-live-'))

    def tearDown(self):
        shutil.rmtree(self.data, ignore_errors=True)

    def runtime(self, pid, age=0):
        (self.data / 'runtime.json').write_text(json.dumps({'pid': pid, 'monotonic': time.monotonic() - age}), encoding='utf-8')

    @staticmethod
    def opener(status=200, error=None):
        class Response:
            def __init__(self): self.status = status
            def __enter__(self): return self
            def __exit__(self, *a): return False
        def open_(url, timeout):
            assert url == 'http://127.0.0.1:47989/health' and timeout >= 5
            if error: raise error
            return Response()
        return open_

    def test_reasons(self):
        from companion.supervisor import liveness_problem
        import urllib.error
        self.assertEqual(liveness_problem(self.data, 7, self.opener()), 'runtime-unreadable')
        self.runtime(8); self.assertEqual(liveness_problem(self.data, 7, self.opener()), 'runtime-other-pid')
        self.runtime(7, age=40); self.assertEqual(liveness_problem(self.data, 7, self.opener()), 'heartbeat-stale')
        self.runtime(7)
        self.assertIsNone(liveness_problem(self.data, 7, self.opener()))
        self.assertEqual(liveness_problem(self.data, 7, self.opener(error=urllib.error.HTTPError('u', 503, 'x', {}, None))), 'health-503')
        self.assertEqual(liveness_problem(self.data, 7, self.opener(error=TimeoutError())), 'health-TimeoutError')
        (self.data / 'runtime.json').write_text('[]', encoding='utf-8')
        self.assertEqual(liveness_problem(self.data, 7, self.opener()), 'runtime-unreadable')

    def test_short_stalls_do_not_restart(self):
        from companion.supervisor import unresponsive
        self.assertFalse(unresponsive(3, 100.0, 106.0), 'six seconds of load is tolerated')
        self.assertFalse(unresponsive(20, 100.0, 144.9))
        self.assertTrue(unresponsive(3, 100.0, 145.0))
        self.assertFalse(unresponsive(2, 100.0, 500.0), 'needs repeated evidence')
        self.assertFalse(unresponsive(0, None, 500.0))


CSC = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Microsoft.NET/Framework/v4.0.30319/csc.exe'

@unittest.skipUnless(CSC.is_file(), 'Requiere el compilador de .NET Framework')
class WatchdogDecision(unittest.TestCase):
    def test_decision_table(self):
        out = Path(tempfile.mkdtemp(prefix='eddy-watchdog-'))
        try:
            exe = out / 'WatchdogChecks.exe'
            subprocess.run([str(CSC), '/nologo', '/target:exe', '/r:System.Windows.Forms.dll', '/r:System.Drawing.dll', '/r:System.Web.Extensions.dll',
                            '/out:' + str(exe), str(ROOT / 'tests/WatchdogChecks.cs'), str(ROOT / 'installer/Watchdog.cs')], check=True, capture_output=True)
            result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('ALL OK', result.stdout)
        finally:
            shutil.rmtree(out, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
