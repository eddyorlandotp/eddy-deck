import copy,tempfile,time,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
from test_core import APP,ROOT,FakeWindows
from companion import windows
from companion.core import Deck,validate_profile
from companion.layout import Windows,validate_activation
from companion.jobs import Cancelled

class LaunchTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.deck=Deck(self.tmp.name,ROOT,adapter=FakeWindows());self.deck.apps=[copy.deepcopy(APP)]
 def tearDown(self):self.deck.close();self.tmp.cleanup()
 def call(self,path,body):return self.deck.dispatch(path,{'requestId':str(time.time_ns()),**body},'local')
 def test_saved_card_round_trip_and_invalid_choice_no_mutation(self):
  r=self.call('/api/cards/save',{'appId':APP['id'],'activation':'windows'});self.assertEqual(r['card']['activation'],'windows')
  before=self.deck.export_profile()
  self.assertEqual(validate_profile(before)['cards'][0]['activation'],'windows')
  for bad in [True,None,[],{},'always-on-top']:
   with self.assertRaises(ValueError):self.call('/api/cards/save',{'appId':APP['id'],'activation':bad})
  self.assertEqual(self.deck.export_profile(),before)
 def test_old_profiles_default_front_without_changing_other_choices(self):
  self.call('/api/cards/save',{'appId':APP['id'],'activation':'front'});raw=self.deck.export_profile();raw['cards'][0].pop('activation')
  raw['scenes']=[{'id':'routine','name':'Example','onError':'stop','steps':[{'type':'launch','appId':APP['id'],'layout':{'monitor':'primary','mode':'maximized'}},{'type':'window','appId':APP['id']}]}]
  clean=validate_profile(raw);self.assertEqual(clean['cards'][0]['activation'],'front');self.assertEqual(clean['scenes'][0]['steps'][0]['activation'],'front');self.assertEqual(clean['scenes'][0]['onError'],'stop');self.assertNotIn('activation',clean['scenes'][0]['steps'][1])
 def test_scene_edit_and_import_keep_activation_and_order(self):
  steps=[{'type':'launch','appId':APP['id'],'activation':'windows'},{'type':'launch','appId':APP['id'],'activation':'front'}]
  self.call('/api/scenes/save',{'name':'Example','steps':steps});saved=validate_profile(self.deck.export_profile())['scenes'][0]['steps'];self.assertEqual([s['activation'] for s in saved],['windows','front'])
 def test_open_existing_uses_presentation_without_relaunch(self):
  self.deck.adapter=windows;self.deck.layouts=MagicMock();self.deck.layouts.snapshot.return_value=[{'id':'existing','appIds':[APP['id']],'minimized':False}]
  with patch('companion.windows.launch') as launch:
   for activation in ['front','windows']:
    step=self.deck.clean_step({'appId':APP['id'],'activation':activation});self.deck.execute_step(step,lambda:None)
    self.assertEqual(self.deck.layouts.present.call_args.args[-1],activation)
   launch.assert_not_called()
 def test_new_open_keeps_activation_choice_and_url_only_once(self):
  self.deck.adapter=windows;self.deck.layouts=MagicMock();self.deck.layouts.snapshot.return_value=[]
  for activation in ['front','windows']:
   s=self.deck.clean_step({'appId':APP['id'],'url':'https://example.com','activation':activation});self.deck.execute_step(s,lambda:None)
   self.assertEqual(self.deck.layouts.launch.call_args.args[-1],activation);self.assertEqual(self.deck.layouts.launch.call_args.args[1],'https://example.com')
  self.assertEqual(self.deck.layouts.launch.call_count,2)
 def test_ambiguous_reuse_does_not_activate_arbitrary_window(self):
  self.deck.adapter=windows;self.deck.layouts=MagicMock();self.deck.layouts.snapshot.return_value=[{'id':n,'appIds':[APP['id']],'minimized':False} for n in ['a','b']]
  with self.assertRaisesRegex(ValueError,'varias ventanas'):self.deck.execute_step(self.deck.clean_step({'appId':APP['id']}),lambda:None)
  self.deck.layouts.present.assert_not_called();self.deck.layouts.launch.assert_not_called()
  self.assertEqual(self.deck.execute_step(self.deck.clean_step({'appId':APP['id'],'activation':'windows'}),lambda:None)['status'],'already_open')
 def test_move_does_not_activate(self):
  self.deck.layouts=MagicMock();self.deck.layouts.snapshot.return_value=[{'id':'a','appIds':[APP['id']]}]
  self.deck.execute_step(self.deck.clean_step({'type':'window','appId':APP['id']}),lambda:None);self.deck.layouts.move.assert_called_once();self.deck.layouts.foreground.assert_not_called()
 def test_minimized_overrides_front_and_preserves_layout(self):
  w=Windows();w.require_window=MagicMock(return_value={'minimized':False});w.move=MagicMock(return_value={'status':'completed','message':'Minimized'});w.foreground=MagicMock()
  w.present('w',{'mode':'minimized'},[],lambda:None,'front');w.move.assert_called_once();w.foreground.assert_not_called()
 def test_front_denied_is_reported(self):
  w=Windows();w.require_window=MagicMock(return_value={'minimized':False});w.leases={'w':{'hwnd':123,'process':{'pid':9,'created':123456}}}
  with patch('win32gui.IsIconic',return_value=False),patch('win32gui.GetClassName',return_value='Test'),patch('companion.focus.run_bounded',return_value={'foreground':False}):
   r=w.foreground('w',[]);self.assertEqual(r['status'],'needs_attention');self.assertFalse(r['foreground'])
 def test_hung_focus_helper_is_killed_before_return(self):
  import sys,subprocess
  from companion.focus import run_bounded
  children=[];real=subprocess.Popen
  def spawn(*a,**kw):
   p=real(*a,**kw);children.append(p);return p
  with patch('companion.focus.command',return_value=[sys.executable,'-c','import time;time.sleep(30)']),patch('companion.focus.subprocess.Popen',side_effect=spawn):
   start=time.monotonic();r=run_bounded({},timeout=.12)
  self.assertTrue(r['timedOut']);self.assertLess(time.monotonic()-start,3);self.assertIsNotNone(children[0].poll())
 def test_cancellation_kills_focus_helper_and_propagates(self):
  import sys,subprocess
  from companion.focus import run_bounded
  children=[];real=subprocess.Popen
  def spawn(*a,**kw):
   p=real(*a,**kw);children.append(p);return p
  with patch('companion.focus.command',return_value=[sys.executable,'-c','import time;time.sleep(30)']),patch('companion.focus.subprocess.Popen',side_effect=spawn):
   with self.assertRaises(Cancelled):run_bounded({},MagicMock(side_effect=[None,Cancelled('stop')]))
  self.assertIsNotNone(children[0].poll())
 def test_roblox_borderless_maximize_observed_and_halves_rejected(self):
  w=Windows();item={'id':'w','monitor':'display:1','minimized':False,'maximized':False};w.snapshot=MagicMock(return_value=[item]);w.require_window=MagicMock(return_value=item);w.leases={'w':{'hwnd':123,'identity':'same'}}
  monitor={'id':'display:1','label':'Main','primary':True,'work':[0,0,1920,1080]};placement=[1]
  def show(hwnd,mode):placement[0]=mode
  with patch('companion.layout.monitors',return_value=[monitor]),patch('companion.layout.u.ShowWindowAsync',side_effect=show),patch('win32gui.GetWindowLong',return_value=0x16000000),patch('win32gui.GetWindowRect',return_value=(0,0,800,600)),patch('win32gui.GetWindowPlacement',side_effect=lambda h:(0,placement[0],(0,0),(0,0),(0,0,800,600))),patch('win32gui.SetWindowPos'),patch('win32gui.IsWindow',return_value=True),patch('win32gui.IsIconic',return_value=False),patch('win32api.MonitorFromWindow',return_value=1),patch('win32api.GetMonitorInfo',return_value={'Device':'1'}):
   self.assertEqual(w.move('w',{'mode':'maximized'},[])['status'],'completed');self.assertEqual(placement[0],3)
   for mode in ['left-half','right-half']:
    with self.assertRaisesRegex(ValueError,'tamaño fijo'):w.move('w',{'mode':mode},[])
 def test_windows_default_without_layout_submits_once_and_skips_focus(self):
  w=Windows()
  with patch('companion.windows.launch',return_value={'status':'submitted'}) as launch,patch.object(w,'foreground') as front:
   self.assertEqual(w.launch(APP,'',{},[APP],lambda:None,'windows')['status'],'submitted');launch.assert_called_once();front.assert_not_called()

if __name__=='__main__':unittest.main()
