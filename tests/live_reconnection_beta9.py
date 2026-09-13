"""Controlled receiver and phone-network outages. No PC reboot or user-app actions."""
import hashlib,json,os,socket,ssl,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root),str(root/'.build/inspection-libs')]
import psutil
from companion.core import VERSION
from companion.storage import data_root,physical_path,identity
from scripts.package_evidence import product_sources
data=data_root();exe=Path(os.environ['LOCALAPPDATA'])/'Programs/EddyDeck/EddyDeck.exe';adb=root/'.build/tools/platform-tools/platform-tools/adb.exe'
report={'version':VERSION,'sourceHashes':product_sources(),'scope':'Installed Windows and Samsung; controlled receiver cold starts and Wi-Fi interruption. No Windows reboot, no mobile-data Internet certification.','cases':[],'installedApkSHA256':hashlib.sha256((root/'artifacts/EddyDeck-Android.apk').read_bytes()).hexdigest()}
def save(): (root/'artifacts/beta9-live-reconnection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def phone(*args):return subprocess.run([str(adb),'-s','ANDROID_SERIAL_HERE',*args],capture_output=True,text=True,encoding='utf-8',check=True,timeout=50).stdout
def recent(after):
 try:
  r=json.loads((data/'runtime.json').read_text())
  return r if any(c['at']>=after for c in r.get('recentClients',[])) else None
 except (OSError,ValueError):return None
def await_phone(after):
 end=time.monotonic()+55
 while time.monotonic()<end:
  r=recent(after)
  if r:return r
  time.sleep(.5)
 raise AssertionError('No automatic authenticated phone traffic within 55 seconds')
def verify():
 with socket.create_connection(('127.0.0.1',47990),timeout=3) as s:
  with ssl._create_unverified_context().wrap_socket(s,server_hostname='localhost') as tls:actual=hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest()
 assert actual==identity(data),'Served identity differs'
 assert physical_path(data)==data
 worker=json.loads((data/'runtime.json').read_text())['pid']
 discovery=[c.pid for c in psutil.net_connections(kind='udp') if c.laddr and c.laddr.port==47991]
 assert discovery==[worker],'Production discovery listener is not owned by current receiver'
before=json.loads((root/'.build/final-update-before.json').read_text(encoding='utf-8-sig'))
assert not phone('reverse','--list').strip(),'USB forwarding would mask network recovery'
phone('shell','am','start','-n','com.eddy.deck/.MainActivity')
verify();report['originalIdentityPreserved']=True;report['canonicalPhysicalStorage']=True
for method in ('explorer','codex'):
 marker=json.loads((data/'supervisor.json').read_text());supervisor=psutil.Process(marker['pid']);worker=psutil.Process(marker['workerPid'])
 assert Path(supervisor.exe())==exe and Path(worker.exe())==exe and worker.ppid()==supervisor.pid
 supervisor.terminate();supervisor.wait(8);worker.terminate();worker.wait(8)
 begin=time.time();tick=time.monotonic()
 if method=='explorer':
  shortcut=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/Startup/Eddy Deck.lnk'
  subprocess.Popen([str(Path(os.environ['WINDIR'])/'explorer.exe'),str(shortcut)],creationflags=0x08000000)
 else:subprocess.Popen([str(exe),'--tray'],cwd=exe.parent,creationflags=0x08000000)
 r=await_phone(begin);verify();m=json.loads((data/'supervisor.json').read_text());parent=psutil.Process(m['pid']).parent().name()
 case={'kind':'receiver-cold-start','launch':method,'observedParent':parent,'automaticAuthenticatedPhoneTraffic':True,'seconds':round(time.monotonic()-tick,2),'identityPreserved':True}
 report['cases'].append(case);save();print(json.dumps(case),flush=True)
report['receiverColdStartReconnected']=True
# Preserve initial Wi-Fi state. This case requires and restores an enabled WLAN.
assert 'inet ' in phone('shell','ip','-o','addr','show','wlan0')
try:
 phone('shell','svc','wifi','disable');time.sleep(6)
 down='inet ' not in phone('shell','ip','-o','addr','show','wlan0')
finally:phone('shell','svc','wifi','enable')
begin=time.time();tick=time.monotonic();await_phone(begin);verify()
report['cases'].append({'kind':'wifi-off-on','interfaceLostObserved':down,'automaticAuthenticatedPhoneTraffic':True,'secondsAfterEnabling':round(time.monotonic()-tick,2),'usbForwardingAbsent':True})
raw=(root/'.build/beta9-live-network.txt').read_text(encoding='utf-8-sig')
assert 'INSTRUMENTATION_CODE: -1' in raw and 'stream=FAIL' not in raw,'Real route test did not pass; see beta9-live-network.txt'
net=json.loads(next(l.split('stream=',1)[1] for l in raw.splitlines() if l.startswith('INSTRUMENTATION_RESULT: stream=')));assert net['lanConnected'] and net['vpnConnected'] and net['staleRouteRediscovered'] and net['originalPinPreserved'] and net['originalSavedRoutesRestored']
report.update(lanConnected=True,vpnConnected=True,staleRouteTest=net)
report['tailscaleAlwaysOn']=phone('shell','settings','get','secure','always_on_vpn_app').strip()=='com.tailscale.ipn';report['vpnLockdownDisabled']=phone('shell','settings','get','secure','always_on_vpn_lockdown').strip()=='0'
report['originalProfilePreserved']=all(hashlib.sha256((data/n).read_bytes()).hexdigest().upper()==v for n,v in before['files'].items());assert report['originalProfilePreserved']
report['passed']=True;save();print('Live reconnection cases passed',flush=True)
