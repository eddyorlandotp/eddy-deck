import copy, http.client, json, socket, ssl, tempfile, threading, time, unittest
from pathlib import Path
from companion.core import APIError, Deck, Server, start, validate_profile, private_ip
from companion.windows import validate_url, normalize_inventory, safe_executable

ROOT=Path(__file__).resolve().parents[1]
APP={'id':'browser-one','name':'Navegador de prueba','kind':'manual','target':r'C:\example\browser.exe','browser':True,'available':True,'category':'Navegadores','symbol':'browser'}

class FakeWindows:
    def __init__(self):self.calls=[]
    def scan(self,root):return [copy.deepcopy(APP)],[]
    def launch(self,app,url):self.calls.append(('launch',app['id'],url));return {'status':'submitted','message':'Prueba'}
    def media_snapshot(self,apps):return {'aimp':False,'state':'unknown'}
    def media(self,*args):self.calls.append(('media',args));return {'status':'submitted'}
    def power(self,action):self.calls.append(('power',action))

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.fake=FakeWindows(); self.deck=Deck(Path(self.tmp.name),ROOT,adapter=self.fake);self.deck.apps=[copy.deepcopy(APP)]
    def tearDown(self):self.deck.close();self.tmp.cleanup()
    def call(self,path,body=None,device='local'):
        return self.deck.dispatch(path,{'requestId':str(time.time_ns()),**(body or {})},device)
    def test_url_input_rejects_command_schemes_credentials_and_argument_injection(self):
        for url in ['file:///C:/secret','javascript:alert(1)','https://user:pw@example.com','https://example.com\n--bad','https://example.com" --test','https://example.com\\bad','http://example.com:foo','--app=https://example.com']:
            with self.subTest(url=url),self.assertRaises(ValueError):validate_url(url)
        self.assertEqual(validate_url('example.com/a?x=1&y=2'),'https://example.com/a?x=1&y=2')
    def test_explicit_private_networks(self):
        for host in ['127.0.0.1','192.168.1.100','10.20.0.1','172.16.0.1']:self.assertTrue(private_ip(host))
        for host in ['8.8.8.8','0.0.0.0','169.254.1.1','192.0.2.1','evil.test','::1']:self.assertFalse(private_ip(host))
    def test_one_use_pairing_device_auth_and_revocation(self):
        pin=self.deck.renew_pin(); result=self.deck.pair({'pin':pin,'name':'Prueba'},'127.0.0.1')
        self.assertEqual(self.deck.authenticate(result['token']),result['deviceId'])
        with self.assertRaises(APIError):self.deck.pair({'pin':pin},'127.0.0.1')
        self.assertNotIn(result['token'],(Path(self.tmp.name)/'devices.json').read_text())
        self.call('/api/devices/revoke',{'id':result['deviceId']})
        with self.assertRaises(APIError):self.deck.authenticate(result['token'])
    def test_pairing_expiry_and_rate_limit(self):
        pin=self.deck.renew_pin();self.deck.pin_until=time.monotonic()-1
        with self.assertRaises(APIError):self.deck.pair({'pin':pin},'127.0.0.1')
        self.deck.renew_pin()
        for i in range(9):
            with self.assertRaises(APIError):self.deck.pair({'pin':'bad'},str(i))
        with self.assertRaises(APIError) as error:self.deck.pair({'pin':self.deck.pin},'another')
        self.assertEqual(error.exception.status,429)
    def test_local_secret_cannot_authenticate_over_lan(self):
        self.assertEqual(self.deck.authenticate(self.deck.local_token,True),'local')
        with self.assertRaises(APIError):self.deck.authenticate(self.deck.local_token,False)
    def test_idempotent_launch_no_double_action_on_retry(self):
        body={'requestId':'same-request','appId':APP['id'],'url':'https://example.com'}
        one=self.deck.dispatch('/api/launch',body,'local');two=self.deck.dispatch('/api/launch',body,'local')
        until=time.monotonic()+2
        while not self.fake.calls and time.monotonic()<until:time.sleep(.02)
        self.assertEqual(one,two);self.assertEqual(len(self.fake.calls),1)
        with self.assertRaises(APIError):self.deck.dispatch('/api/launch',{**body,'url':'https://different.com'},'local')
    def test_unknown_app_cannot_launch_arbitrary_path(self):
        with self.assertRaises(ValueError):self.call('/api/launch',{'appId':'C:\\Windows\\System32\\cmd.exe'})
        self.assertEqual(self.fake.calls,[])
    def test_cards_persist_and_url_is_bound_to_browser(self):
        result=self.call('/api/cards/save',{'appId':APP['id'],'name':'Mi web','url':'example.com','color':'mint'})
        self.assertEqual(result['card']['url'],'https://example.com')
        restored=Deck(Path(self.tmp.name),ROOT,adapter=self.fake)
        self.assertEqual(restored.profile['cards'][0]['name'],'Mi web')
        restored.close()
        self.deck.apps[0]['browser']=False
        with self.assertRaises(ValueError):self.call('/api/cards/save',{'appId':APP['id'],'url':'https://example.com'})
    def test_backup_does_not_import_commands_or_credentials(self):
        good={'version':1,'cards':[],'scenes':[],'token':'bad','commands':['evil'],'seeded':True}
        result=validate_profile(good);self.assertNotIn('commands',result);self.assertNotIn('token',result)
        evil={'version':1,'cards':[{'id':'a','appId':'x','name':'x','url':'file:///etc/secret'}],'scenes':[]}
        with self.assertRaises(ValueError):validate_profile(evil)
    def test_scene_partial_failure_reported_and_stops(self):
        self.call('/api/scenes/save',{'name':'Prueba','steps':[{'appId':APP['id']}]})
        sid=self.deck.profile['scenes'][0]['id']
        self.deck.apps=[]
        with self.assertRaises(ValueError):self.call('/api/scenes/run',{'id':sid})
        self.assertFalse(self.fake.calls)
    def test_power_requires_fresh_device_bound_challenge(self):
        prepared=self.call('/api/power/prepare',{'action':'shutdown'},'one')
        with self.assertRaises(APIError):self.call('/api/power/confirm',{'challenge':prepared['challenge']},'two')
        self.assertIsNone(self.deck.pending);self.assertFalse(self.fake.calls)
        prepared=self.call('/api/power/prepare',{'action':'shutdown'})
        self.deck.challenges[prepared['challenge']]['expires']=0
        with self.assertRaises(APIError):self.call('/api/power/confirm',{'challenge':prepared['challenge']})
    def test_power_cancel_and_nonblocking_cancellation(self):
        prepared=self.call('/api/power/prepare',{'action':'sleep'})
        self.call('/api/power/confirm',{'challenge':prepared['challenge']})
        self.deck.action_lock.acquire()
        try:self.call('/api/power/cancel')
        finally:self.deck.action_lock.release()
        time.sleep(.2);self.assertIsNone(self.deck.pending);self.assertFalse(self.fake.calls)
    def test_power_adapter_runs_only_after_countdown(self):
        pending={'id':'test','action':'shutdown','at':time.time()+.3,'deadline':time.monotonic()+.3};self.deck.pending=pending
        thread=threading.Thread(target=self.deck._power_countdown,args=(pending,));thread.start()
        self.assertFalse(self.fake.calls);thread.join(2);self.assertEqual(self.fake.calls,[('power','shutdown')])

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.deck=Deck(Path(cls.tmp.name),ROOT,adapter=FakeWindows())
        cls.deck.apps=[copy.deepcopy(APP)];start(cls.deck,local_port=0,port=0,bind='127.0.0.1')
    @classmethod
    def tearDownClass(cls):cls.deck.close();cls.tmp.cleanup()
    def get(self,path,headers=None,tls=False):
        if tls:
            context=ssl.create_default_context(cafile=str(Path(self.tmp.name)/'server.crt'))
            conn=http.client.HTTPSConnection('127.0.0.1',self.deck.port,context=context,timeout=3)
        else:conn=http.client.HTTPConnection('127.0.0.1',self.deck.local_port,timeout=3)
        conn.request('GET',path,headers=headers or {});r=conn.getresponse();body=r.read();status=r.status;conn.close();return status,body
    def test_no_unauthenticated_inventory_or_profile(self):
        self.assertEqual(self.get('/api/state')[0],401);self.assertEqual(self.get('/api/backup')[0],401)
    def test_dns_rebinding_and_cross_origin_blocked(self):
        auth={'Authorization':'Bearer '+self.deck.local_token}
        self.assertEqual(self.get('/api/state',{**auth,'Host':'attacker.example'})[0],403)
        self.assertEqual(self.get('/api/state',{**auth,'Origin':'https://attacker.example'})[0],403)
    def test_no_static_path_traversal(self):
        self.assertEqual(self.get('/../server.key')[0],404)
        self.assertEqual(self.get('/%2e%2e/server.key')[0],404)
    def test_local_ui_and_live_tls(self):
        self.assertEqual(self.get('/')[0],200)
        self.assertEqual(self.get('/health',tls=True)[0],200)
        self.assertEqual(self.get('/api/state',{'Authorization':'Bearer '+self.deck.local_token},tls=True)[0],401)
    def test_authenticated_get_and_encrypted_pairing(self):
        self.assertEqual(self.get('/api/state',{'Authorization':'Bearer '+self.deck.local_token})[0],200)
        pin=self.deck.renew_pin();context=ssl.create_default_context(cafile=str(Path(self.tmp.name)/'server.crt'))
        conn=http.client.HTTPSConnection('127.0.0.1',self.deck.port,context=context)
        conn.request('POST','/auth/pair',json.dumps({'pin':pin,'name':'TLS test'}),{'Content-Type':'application/json'})
        response=conn.getresponse();body=json.loads(response.read());self.assertEqual(response.status,200);conn.close()
        self.assertEqual(self.get('/api/state',{'Authorization':'Bearer '+body['token']},tls=True)[0],200)

if __name__=='__main__':unittest.main(verbosity=2)
