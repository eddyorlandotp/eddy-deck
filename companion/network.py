"""Read current IPv4 interfaces directly, including adapters added after startup."""
import ctypes as C
import os
import socket

def windows_addresses():
    # Prefixes only: trailing time_t fields differ between SDK architectures.
    class IP(C.Structure):pass
    IP._fields_=[('next',C.POINTER(IP)),('address',C.c_char*16),('mask',C.c_char*16),('context',C.c_uint32)]
    class Adapter(C.Structure):pass
    Adapter._fields_=[('next',C.POINTER(Adapter)),('combo',C.c_uint32),('name',C.c_char*260),('description',C.c_char*132),('length',C.c_uint32),('mac',C.c_ubyte*8),('index',C.c_uint32),('type',C.c_uint32),('dhcp',C.c_uint32),('current',C.POINTER(IP)),('ips',IP)]
    api=C.WinDLL('iphlpapi').GetAdaptersInfo
    api.argtypes=[C.c_void_p,C.POINTER(C.c_uint32)];api.restype=C.c_uint32
    size=C.c_uint32();result=api(None,C.byref(size))
    if result==232:return []
    for _ in range(3):
        if result!=111 or not 0<size.value<=4*1024*1024:raise OSError('No se pudieron enumerar las interfaces de red.')
        buffer=C.create_string_buffer(size.value);result=api(buffer,C.byref(size))
        if result==111:continue
        if result==232:return []
        if result:raise OSError(result,'No se pudieron enumerar las interfaces de red.')
        adapter=C.cast(buffer,C.POINTER(Adapter));addresses=[]
        for _ in range(256):
            if not adapter:break
            entry=adapter.contents.ips
            for _ in range(64):
                addresses.append(entry.address.decode('ascii'))
                if not entry.next:break
                entry=entry.next.contents
            adapter=adapter.contents.next
        return addresses
    raise OSError('Las interfaces cambiaron durante la lectura.')

def interface_addresses():
    if os.name=='nt':
        try:return windows_addresses()
        except OSError:pass
    try:return [item[4][0] for item in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET)]
    except OSError:return []
