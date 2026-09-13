using System;using System.Runtime.InteropServices;
[ComImport,Guid("2e941141-7f97-4756-ba1d-9decde894a3d"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]interface Activation {
 [PreserveSig] int ActivateApplication([MarshalAs(UnmanagedType.LPWStr)]string id,[MarshalAs(UnmanagedType.LPWStr)]string args,int options,out uint pid);
 [PreserveSig] int ActivateForFile([MarshalAs(UnmanagedType.LPWStr)]string id,IntPtr array,[MarshalAs(UnmanagedType.LPWStr)]string verb,out uint pid);
 [PreserveSig] int ActivateForProtocol([MarshalAs(UnmanagedType.LPWStr)]string id,IntPtr array,out uint pid);
}
class OpenFixture{
 [DllImport("shell32.dll",CharSet=CharSet.Unicode,PreserveSig=false)]static extern void SHCreateItemFromParsingName(string name,IntPtr context,ref Guid iid,out IntPtr item);
 [DllImport("shell32.dll",PreserveSig=false)]static extern void SHCreateShellItemArrayFromShellItem(IntPtr item,ref Guid iid,out IntPtr array);
 [DllImport("shell32.dll",CharSet=CharSet.Unicode,PreserveSig=false)]static extern void SHParseDisplayName(string name,IntPtr context,out IntPtr pidl,uint flags,out uint attributes);
 [DllImport("shell32.dll",PreserveSig=false)]static extern void SHCreateShellItemArrayFromIDLists(uint count,IntPtr[] list,out IntPtr array);
 [STAThread]static int Main(string[] args){IntPtr item=IntPtr.Zero,array=IntPtr.Zero;object manager=null;try{Guid iid=new Guid("43826d1e-e718-42ee-bc55-a1e261c37bfe"),aid=new Guid("b63ea76d-1f85-456f-a19c-48159efa858b");var ids=new IntPtr[args.Length];for(int i=0;i<args.Length;i++){uint attributes;SHParseDisplayName(args[i],IntPtr.Zero,out ids[i],0,out attributes);}try{SHCreateShellItemArrayFromIDLists((uint)ids.Length,ids,out array);}finally{foreach(var id in ids)Marshal.FreeCoTaskMem(id);}manager=Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("45ba127d-10a8-46ea-8ab7-56ea9078943c")));uint pid;int hr=((Activation)manager).ActivateForFile("Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic",array,"open",out pid);Marshal.ThrowExceptionForHR(hr);Console.WriteLine(pid);return 0;}catch(Exception e){Console.Error.WriteLine(e.Message);return 1;}finally{if(manager!=null)Marshal.ReleaseComObject(manager);if(array!=IntPtr.Zero)Marshal.Release(array);if(item!=IntPtr.Zero)Marshal.Release(item);}}}
