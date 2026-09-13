import concurrent.futures,contextlib,json,os,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from companion import storage
from companion.core import ensure_certificate

class StorageMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.old=self.root/'old';self.old.mkdir();self.target=self.root/'.eddydeck'
        (self.old/'deck.json').write_text(json.dumps({'version':2,'cards':[],'scenes':[]}),encoding='utf-8');(self.old/'devices.json').write_text('[]',encoding='utf-8')
        ensure_certificate(self.old);self.pin=storage.identity(self.old)
    def tearDown(self):self.tmp.cleanup()
    def test_home_location_does_not_follow_localappdata(self):
        with patch.dict(os.environ,USERPROFILE=str(self.root),LOCALAPPDATA='different'):
            self.assertEqual(storage.data_root(),self.target)
    def test_copies_exact_identity_and_database_retains_original(self):
        with contextlib.closing(sqlite3.connect(self.old/'operations.sqlite3')) as db:db.execute('create table receipt(id text)');db.execute("insert into receipt values ('unique-action')");db.commit()
        (self.old/'runtime.json').write_text('{"pid":123}')
        before={p.name:p.read_bytes() for p in self.old.iterdir() if p.suffix in ('.crt','.key','.json')}
        storage.prepare_data(self.old,self.pin,self.target)
        self.assertEqual(storage.identity(self.target),self.pin)
        self.assertFalse((self.target/'runtime.json').exists())
        with contextlib.closing(sqlite3.connect(self.target/'operations.sqlite3')) as db:self.assertEqual(db.execute('select id from receipt').fetchall(),[('unique-action',)])
        for n,b in before.items():self.assertEqual((self.old/n).read_bytes(),b)
    def test_failed_copy_publishes_nothing(self):
        with patch.object(storage.shutil,'copy2',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):storage.prepare_data(self.old,self.pin,self.target)
        self.assertFalse(self.target.exists());self.assertEqual(storage.identity(self.old),self.pin);self.assertFalse(list(self.root.glob('.eddydeck-migration-*')))
    def test_ambiguous_legacy_never_selects_an_identity(self):
        with patch.object(storage,'legacy_candidates',return_value=[self.old,self.root/'another']):
            with self.assertRaisesRegex(RuntimeError,'varias configuraciones'):storage.prepare_data(target=self.target)
        self.assertFalse(self.target.exists())
    def test_running_legacy_cannot_be_migrated_automatically(self):
        with patch.object(storage,'legacy_candidates',return_value=[self.old]),patch.object(storage,'require_legacy_stopped',side_effect=RuntimeError('receptor activo')):
            with self.assertRaisesRegex(RuntimeError,'receptor activo'):storage.prepare_data(target=self.target)
        self.assertFalse(self.target.exists());self.assertEqual(storage.identity(self.old),self.pin)
    def test_legacy_started_during_copy_prevents_publish(self):
        with patch.object(storage,'legacy_candidates',return_value=[self.old]),patch.object(storage,'require_legacy_stopped',side_effect=[None,RuntimeError('receptor activo')]):
            with self.assertRaisesRegex(RuntimeError,'receptor activo'):storage.prepare_data(target=self.target)
        self.assertFalse(self.target.exists())
    def test_existing_target_never_merges_legacy(self):
        storage.prepare_data(self.old,self.pin,self.target)
        (self.old/'deck.json').write_text('{"different":true}')
        storage.prepare_data(self.old,self.pin,self.target)
        self.assertNotIn('different',(self.target/'deck.json').read_text())
    def test_wrong_identity_cannot_publish(self):
        with self.assertRaisesRegex(RuntimeError,'no corresponde'):storage.prepare_data(self.old,'0'*64,self.target)
        self.assertFalse(self.target.exists())
    def test_corrupt_key_cannot_publish(self):
        (self.old/'server.key').write_text('broken')
        with self.assertRaises(ValueError):storage.prepare_data(self.old,self.pin,self.target)
        self.assertFalse(self.target.exists())
    def test_initialization_errors_have_safe_actionable_messages(self):
        for error in (ValueError('private bytes'),PermissionError('private path'),OSError('private file')):
            message=storage.startup_message(error)
            self.assertIn('Conserva',message);self.assertIn(type(error).__name__,message);self.assertNotIn('private',message)
    def test_corrupt_json_aborts_copy_with_recoverable_message(self):
        (self.old/'devices.json').write_text('{broken')
        with self.assertRaises(ValueError) as error:storage.prepare_data(self.old,self.pin,self.target)
        self.assertIn('restaura',storage.startup_message(error.exception));self.assertFalse(self.target.exists())
    def test_enrolled_identity_missing_both_files_is_not_regenerated(self):
        (self.old/'devices.json').write_text('[{"id":"paired"}]');(self.old/'server.crt').unlink();(self.old/'server.key').unlink()
        with self.assertRaisesRegex(RuntimeError,'ya vinculada'):ensure_certificate(self.old)
        self.assertFalse((self.old/'server.crt').exists())
    def test_migrated_identity_missing_both_files_is_not_regenerated(self):
        storage.prepare_data(self.old,self.pin,self.target)
        for n in ('server.crt','server.key'):(self.target/n).unlink()
        with self.assertRaises(RuntimeError):ensure_certificate(self.target)
    def test_concurrent_migrations_publish_one_complete_identity(self):
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:storage.prepare_data(self.old,self.pin,self.target),range(2)))
        self.assertEqual(results,[self.target,self.target]);self.assertEqual(storage.identity(self.target),self.pin)
    def test_redirected_existing_target_is_rejected(self):
        self.target.mkdir()
        with patch.object(storage,'physical_path',return_value=self.root/'redirected'):
            with self.assertRaisesRegex(RuntimeError,'redirigida'):storage.prepare_data(target=self.target)
    def test_new_install_creates_no_unrelated_data(self):
        with patch.object(storage,'legacy_candidates',return_value=[]):storage.prepare_data(target=self.target)
        self.assertEqual(list(self.target.iterdir()),[])

if __name__=='__main__':unittest.main()
