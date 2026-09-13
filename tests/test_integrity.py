import base64,copy,hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding,rsa
from companion.integrity import MANIFEST,SIGNATURE,CHECKER,manifest_bytes,verify_release,cache_release,start_repair
from companion.installer import install_from,read_profile_backup,restore_profile_backup
from test_core import ROOT

class IntegrityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir()
  (self.source/'EddyDeck.exe').write_bytes(b'test executable not for execution');(self.source/'_internal').mkdir();(self.source/'_internal/a.dll').write_bytes(b'test library');(self.source/CHECKER).write_bytes(b'test checker')
  from companion.core import VERSION
  self.manifest={'schema':1,'architecture':'x64','version':VERSION,'files':{p.relative_to(self.source).as_posix():{'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in self.source.rglob('*') if p.is_file()}}
  self.sign()
 def tearDown(self):self.tmp.cleanup()
 def sign(self):
  raw=json.dumps(self.manifest).encode();(self.source/MANIFEST).write_bytes(raw);(self.source/SIGNATURE).write_bytes(base64.b64encode(self.key.sign(raw,padding.PKCS1v15(),hashes.SHA256())))
 def verify(self):return verify_release(self.source,self.key.public_key())
 def test_signed_complete_package_verifies(self):self.assertEqual(len(self.verify()['files']),3)
 def test_modified_same_size_file_rejected(self):
  p=self.source/'_internal/a.dll';p.write_bytes(b'X'*p.stat().st_size)
  with self.assertRaises(ValueError):self.verify()
 def test_missing_dependency_rejected(self):
  (self.source/'_internal/a.dll').unlink()
  with self.assertRaises(ValueError):self.verify()
 def test_extra_unlisted_library_rejected(self):
  (self.source/'_internal/evil.dll').write_bytes(b'fake')
  with self.assertRaises(ValueError):self.verify()
 def test_modified_manifest_rejected_without_valid_signature(self):
  (self.source/MANIFEST).write_text('{}')
  with self.assertRaises(ValueError):self.verify()
 def test_wrong_signing_key_rejected(self):
  other=rsa.generate_private_key(public_exponent=65537,key_size=2048)
  with self.assertRaises(ValueError):verify_release(self.source,other.public_key())
 def test_incompatible_architecture_rejected(self):
  self.manifest['architecture']='arm64';self.sign()
  with self.assertRaises(ValueError):self.verify()
 def test_signed_unsafe_paths_rejected(self):
  for name in ['../x','C:/x','/x','a\\b','x:stream','x.','x ','a//b','./x','a/../b']:
   with self.subTest(name=name):
    self.manifest['files']={name:{'size':0,'sha256':'0'*64}};self.sign()
    with self.assertRaises(ValueError):self.verify()
 def test_oversize_signature_rejected_before_parse(self):
  with self.assertRaises(ValueError):manifest_bytes(b'{}',b'A'*2049,self.key.public_key())
 def test_cache_and_checker_must_match_signed_version(self):
  with patch('companion.integrity.public_key',return_value=self.key.public_key()):
   dest=cache_release(self.source,self.root/'data');self.assertTrue(dest.is_file())
   (self.root/'data/Rescue'/CHECKER).write_bytes(b'changed')
   with patch('companion.integrity.subprocess.Popen') as popen,self.assertRaises(ValueError):start_repair(self.root/'data')
   popen.assert_not_called()
 def test_installer_keeps_old_version_when_cache_fails(self):
  local=self.root/'local';target=local/'Programs/EddyDeck';target.mkdir(parents=True);(target/'EddyDeck.exe').write_bytes(b'previous')
  with patch.dict(os.environ,{'LOCALAPPDATA':str(local)}),patch('companion.integrity.public_key',return_value=self.key.public_key()),patch('companion.integrity.cache_release',side_effect=OSError('disk full')):
   with self.assertRaises(OSError):install_from(self.source)
  self.assertEqual((target/'EddyDeck.exe').read_bytes(),b'previous')
 def test_installer_rolls_back_when_directory_swap_fails(self):
  local=self.root/'local';target=local/'Programs/EddyDeck';target.mkdir(parents=True);(target/'EddyDeck.exe').write_bytes(b'previous');real=os.replace
  def replace(a,b):
   if Path(a).name.startswith('EddyDeck-update-'):raise OSError('destination locked')
   return real(a,b)
  with patch.dict(os.environ,{'LOCALAPPDATA':str(local)}),patch('companion.integrity.public_key',return_value=self.key.public_key()),patch('companion.integrity.cache_release'),patch('companion.installer.os.replace',side_effect=replace):
   with self.assertRaises(RuntimeError):install_from(self.source)
  self.assertEqual((target/'EddyDeck.exe').read_bytes(),b'previous')
 def test_explicit_profile_recovery_preserves_damaged_original_and_trust(self):
  data=self.root/'data';data.mkdir();(data/'deck.json').write_bytes(b'invalid old data');(data/'server.key').write_bytes(b'fixture private data');(data/'devices.json').write_bytes(b'fixture peers')
  file=self.root/'backup.json';file.write_text(json.dumps({'version':2,'cards':[],'scenes':[]}))
  result=restore_profile_backup(file,data);self.assertEqual(result,{'cards':0,'routines':0});self.assertEqual((data/'server.key').read_bytes(),b'fixture private data');self.assertEqual((data/'devices.json').read_bytes(),b'fixture peers')
  backups=list(data.glob('deck-before-recovery-*.json'));self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_bytes(),b'invalid old data');self.assertEqual(json.loads((data/'deck.json').read_text())['version'],2)
 def test_invalid_recovery_never_replaces_existing_profile(self):
  data=self.root/'data';data.mkdir();(data/'deck.json').write_bytes(b'original');file=self.root/'backup.json';file.write_text('{broken')
  with self.assertRaises(ValueError):restore_profile_backup(file,data)
  self.assertEqual((data/'deck.json').read_bytes(),b'original');self.assertFalse(list(data.glob('deck-before-recovery-*')))
 def test_recovery_write_failure_keeps_original(self):
  data=self.root/'data';data.mkdir();(data/'deck.json').write_bytes(b'original');file=self.root/'backup.json';file.write_text(json.dumps({'version':2,'cards':[],'scenes':[]}))
  with patch('companion.core.atomic_json',side_effect=OSError('full disk')):
   with self.assertRaises(OSError):restore_profile_backup(file,data)
  self.assertEqual((data/'deck.json').read_bytes(),b'original')
