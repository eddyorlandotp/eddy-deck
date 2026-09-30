"""Read-only physical LAN metadata, disclosed only through authenticated state."""
import copy,ipaddress,json,os,re,subprocess,threading,time
from pathlib import Path
from companion.child_lifetime import run_owned
_lock=threading.Lock();_cached=None;_until=0
PRIVATE=[ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')]
SCRIPT=r'''[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference='Stop'
$rows=@(Get-NetAdapter -Physical | Where-Object Status -eq 'Up' | ForEach-Object {
 $a=$_
 Get-NetIPAddress -InterfaceIndex $a.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue | ForEach-Object {
  [pscustomobject]@{name=$a.InterfaceDescription;mac=$a.MacAddress;address=$_.IPAddress;prefix=$_.PrefixLength;ethernet=($a.MediaType -eq '802.3')}
 }
})
ConvertTo-Json -InputObject $rows -Compress
'''
def adapters(rows):
    if not isinstance(rows,list) or len(rows)>64:raise ValueError('Lista de red no válida.')
    result=[];seen=set()
    for row in rows:
        if not isinstance(row,dict):continue
        mac=str(row.get('mac','')).replace('-',':').upper()
        if not re.fullmatch(r'(?:[0-9A-F]{2}:){5}[0-9A-F]{2}',mac) or int(mac[:2],16)&1 or mac=='00:00:00:00:00:00':continue
        try:
            address=ipaddress.IPv4Address(row.get('address',''));prefix=row.get('prefix')
            if type(prefix) is not int or not 8<=prefix<=30 or not any(address in n for n in PRIVATE):continue
            network=ipaddress.ip_network(str(address)+'/'+str(prefix),strict=False)
            if address in (network.network_address,network.broadcast_address):continue
        except (ValueError,TypeError):continue
        key=(mac,str(network))
        if key in seen:continue
        seen.add(key);result.append({'name':str(row.get('name','Red local'))[:120],'mac':mac,'address':str(address),'prefix':prefix,'broadcast':str(network.broadcast_address),'ethernet':row.get('ethernet') is True})
    return sorted(result,key=lambda x:not x['ethernet'])[:8]
def snapshot():
    global _cached,_until
    with _lock:
        if _cached is None or time.monotonic()>=_until:
            try:
                exe=Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
                r=run_owned([str(exe),'-NoProfile','-NonInteractive','-Command',SCRIPT],capture_output=True,text=True,encoding='utf-8-sig',creationflags=0x08000000,timeout=5)
                if r.returncode:raise RuntimeError('Windows no pudo consultar la red física.')
                _cached={'adapters':adapters(json.loads(r.stdout)),'error':'','scope':'local-network','powerOnVerified':False}
            except (RuntimeError,OSError,ValueError,subprocess.TimeoutExpired) as e:_cached={'adapters':[],'error':'No se pudieron consultar los datos para Wake-on-LAN. Vuelve a conectar la PC.','scope':'local-network','powerOnVerified':False}
            _until=time.monotonic()+60
        return copy.deepcopy(_cached)
