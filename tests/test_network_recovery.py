import http.client,json,socket,tempfile,unittest
from unittest.mock import patch,MagicMock
from pathlib import Path
from companion import core,network
from test_core import ROOT,FakeWindows

class NetworkRecoveryTests(unittest.TestCase):
    def test_interface_changes_are_not_dns_cached(self):
        with patch('companion.core.interface_addresses',side_effect=[['192.168.1.3'],['192.168.9.4','100.80.2.3','0.0.0.0','8.8.8.8','127.0.0.1']]):
            self.assertEqual(core.local_addresses(),['192.168.1.3'])
            self.assertEqual(core.local_addresses(),['100.80.2.3','192.168.9.4'])
    def test_empty_adapters_do_not_fall_back_to_stale_dns(self):
        with patch('companion.network.os.name','nt'),patch('companion.network.windows_addresses',return_value=[]),patch('socket.getaddrinfo') as dns:
            self.assertEqual(network.interface_addresses(),[]);dns.assert_not_called()
    def test_os_api_failure_has_bounded_dns_fallback(self):
        with patch('companion.network.os.name','nt'),patch('companion.network.windows_addresses',side_effect=OSError()),patch('socket.getaddrinfo',return_value=[(None,None,None,None,('10.1.2.3',0))]):
            self.assertEqual(network.interface_addresses(),['10.1.2.3'])
    def test_background_heartbeat_returns_current_routes_only_after_auth(self):
        with tempfile.TemporaryDirectory() as directory:
            deck=core.Deck(directory,ROOT,adapter=FakeWindows())
            try:
                core.start(deck,local_port=0,port=0,bind='127.0.0.1')
                conn=http.client.HTTPConnection('127.0.0.1',deck.local_port,timeout=3)
                try:
                    conn.request('GET','/api/heartbeat');response=conn.getresponse();self.assertEqual(response.status,401);self.assertNotIn('addresses',json.loads(response.read()))
                    with patch('companion.core.local_addresses',return_value=['192.168.2.3','100.81.2.1']):
                        conn.request('GET','/api/heartbeat',headers={'Authorization':'Bearer '+deck.local_token});response=conn.getresponse();data=json.loads(response.read());self.assertEqual(response.status,200);self.assertEqual(data['addresses'],['192.168.2.3','100.81.2.1'])
                        self.assertNotIn('token',data)
                finally:conn.close()
            finally:deck.close()
    def test_udp_adapter_failure_reopens_listener(self):
        deck=MagicMock(closed=False,port=47990,fingerprint='test')
        first=MagicMock();first.recvfrom.side_effect=OSError('adapter removed')
        second=MagicMock()
        def receive(*args):deck.closed=True;return b'EDDY_DECK_DISCOVER_V1',('192.168.1.5',1234)
        second.recvfrom.side_effect=receive
        first.__enter__.return_value=first;second.__enter__.return_value=second
        with patch('companion.core.socket.socket',side_effect=[first,second]) as factory,patch('companion.core.time.monotonic',side_effect=range(100)),patch('companion.core.time.sleep'):
            core.discovery(deck)
        self.assertEqual(factory.call_count,2);second.sendto.assert_called_once();first.__exit__.assert_called_once()

if __name__=='__main__':unittest.main()
