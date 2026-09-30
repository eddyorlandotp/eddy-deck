import copy,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from companion import audio_output as audio,wake
from companion.core import Deck,APIError

ROOT=Path(__file__).resolve().parents[1]
ID='{0.0.0.00000000}.{12345678-1234-1234-1234-123456789abc}'
STATE={'outputs':[{'id':ID,'name':'Speakers','default':True}],'defaultId':ID,'volume':22,'mute':False,'available':True,'error':''}
ADAPTER={'name':'Ethernet','mac':'02-11-22-33-44-55','address':'192.168.8.12','prefix':24,'ethernet':True}
class AudioTests(unittest.TestCase):
 def tearDown(self):audio._cached=None;audio._until=0
 def test_rejects_bad_values_and_endpoint_injection(self):
  for val in (True,False,-1,101,1.5,'50',None,float('nan')):
   with self.subTest(val=val),self.assertRaises(ValueError):audio.validate('volume',ID,val)
  for val in ('','abc','--foo','file:///C:/x',None):
   with self.assertRaises(ValueError):audio.validate('volume',val,10)
  for val in (0,1,'false',None):
   with self.assertRaises(ValueError):audio.validate('mute',ID,val)
 def test_absolute_values_and_select_expected_validation(self):
  for val in (0,1,100):audio.validate('volume',ID,val)
  for val in (True,False):audio.validate('mute',ID,val)
  audio.validate('select',ID,expected=ID)
  with self.assertRaises(ValueError):audio.validate('select',ID,expected='bad')
 def invoke(self,data,code=0):
  with patch.object(Path,'is_file',return_value=True),patch.object(audio,'run_owned',return_value=subprocess.CompletedProcess([],code,json.dumps(data),'') ) as runner:
   value=audio.invoke('volume',ID,42);self.assertEqual(runner.call_args.args[0][-2:],[ID,'42']);self.assertEqual(runner.call_args.kwargs['timeout'],5);return value
 def test_helper_exact_result(self):self.assertEqual(self.invoke(STATE)['volume'],22)
 def test_rejects_malformed_helper_results(self):
  for bad in ([],{},dict(STATE,volume=True),dict(STATE,volume=101),dict(STATE,mute=1),dict(STATE,defaultId='bad'),dict(STATE,outputs=STATE['outputs']*2)):
   with self.subTest(data=bad),self.assertRaises(RuntimeError):self.invoke(bad)
 def test_timeout_never_replays_command(self):
  with patch.object(Path,'is_file',return_value=True),patch.object(audio,'run_owned',side_effect=subprocess.TimeoutExpired('audio',5)) as runner:
   with self.assertRaisesRegex(RuntimeError,'no se reenvió'):audio.invoke('mute',ID,True)
   runner.assert_called_once()
 def test_cache_is_copy_and_mutation_invalidates_even_on_failure(self):
  with patch.object(audio,'invoke',return_value=copy.deepcopy(STATE)) as fn:
   audio._cached=None;a=audio.snapshot();a['outputs'].clear();self.assertEqual(len(audio.snapshot()['outputs']),1);fn.assert_called_once()
  with patch.object(audio,'invoke',side_effect=RuntimeError('gone')):
   with self.assertRaises(RuntimeError):audio.control('volume',ID,20)
  self.assertIsNone(audio._cached)
 def test_helper_failure_readable_and_not_success(self):
  with patch.object(audio,'invoke',side_effect=OSError('missing')):
   audio._cached=None;self.assertFalse(audio.snapshot()['available']);self.assertEqual(audio.snapshot()['outputs'],[])
 def test_request_receipt_deduplicates_audio(self):
  with tempfile.TemporaryDirectory() as td:
   d=Deck(Path(td),ROOT)
   try:
    with patch.object(audio,'control',return_value={'status':'completed'}) as control:
     body={'requestId':'volume-test','action':'volume','endpoint':ID,'value':20}
     self.assertEqual(d.dispatch('/api/audio',body,'local'),d.dispatch('/api/audio',body,'local'));control.assert_called_once()
     with self.assertRaises(APIError):d.dispatch('/api/audio',dict(body,value=21),'local')
   finally:d.close()
 def test_repair_rejects_audio_without_helper(self):
  with tempfile.TemporaryDirectory() as td:
   d=Deck(Path(td),ROOT);d.repairing=True
   try:
    with patch.object(audio,'control') as control:
     with self.assertRaises(APIError):d.dispatch('/api/audio',{'requestId':'repair','action':'mute','endpoint':ID,'value':True},'local')
     control.assert_not_called()
   finally:d.close()

class WakeTests(unittest.TestCase):
 def test_broadcast_derivation(self):
  row=wake.adapters([ADAPTER])[0];self.assertEqual(row['broadcast'],'192.168.8.255');self.assertEqual(row['mac'],'02:11:22:33:44:55');self.assertTrue(row['ethernet'])
 def test_private_ranges(self):
  for address in ('10.8.2.3','172.16.7.8','172.31.8.9','192.168.8.12'):self.assertEqual(len(wake.adapters([dict(ADAPTER,address=address)])),1)
 def test_non_lan_malformed_mac_network_broadcast_rejected(self):
  for changes in ({'address':'100.64.0.1'},{'address':'8.8.8.8'},{'address':'127.0.0.1'},{'address':'169.254.1.1'},{'address':'::1'},{'address':'192.168.8.0'},{'address':'192.168.8.255'},{'mac':'FF:FF:FF:FF:FF:FF'},{'mac':'00:00:00:00:00:00'},{'mac':'03:11:22:33:44:55'},{'prefix':31},{'prefix':True},{'prefix':'24'}):
   with self.subTest(changes=changes):self.assertEqual(wake.adapters([dict(ADAPTER,**changes)]),[])
 def test_dedup_limit_and_ethernet_priority(self):
  self.assertEqual(len(wake.adapters([ADAPTER,ADAPTER])),1)
  rows=[dict(ADAPTER,mac=f'02:11:22:33:44:{i:02x}',ethernet=i==8) for i in range(10)]
  result=wake.adapters(rows);self.assertEqual(len(result),8);self.assertTrue(result[0]['ethernet'])
 def test_timeout_reports_unavailable_without_claiming_wake(self):
  wake._cached=None
  with patch.object(wake,'run_owned',side_effect=subprocess.TimeoutExpired('ps',5)):
   result=wake.snapshot();self.assertEqual(result['adapters'],[]);self.assertFalse(result['powerOnVerified']);self.assertTrue(result['error'])
  wake._cached=None;wake._until=0

if __name__=='__main__':unittest.main()
