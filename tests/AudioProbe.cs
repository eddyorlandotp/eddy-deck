// Test-only Core Audio observer. Holds the initial endpoint and restores only
// volume changes requested by the paired Python fixture. Does not play audio.
using System;
using System.Globalization;
using System.Runtime.InteropServices;

[ComImport,Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
class EnumeratorObject {}
[ComImport,Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface Enumerator {
 [PreserveSig]int EnumAudioEndpoints(int flow,int mask,out IntPtr collection);
 [PreserveSig]int GetDefaultAudioEndpoint(int flow,int role,out Device device);
}
[ComImport,Guid("D666063F-1587-4E43-81F1-B948E807363F"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface Device {
 [PreserveSig]int Activate(ref Guid iid,int context,IntPtr parameters,[MarshalAs(UnmanagedType.IUnknown)]out object value);
 [PreserveSig]int OpenPropertyStore(int access,out IntPtr properties);
 [PreserveSig]int GetId([MarshalAs(UnmanagedType.LPWStr)]out string id);
}
[ComImport,Guid("5CDF2C82-841E-4546-9722-0CF74078229A"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface EndpointVolume {
 [PreserveSig]int RegisterControlChangeNotify(IntPtr callback);
 [PreserveSig]int UnregisterControlChangeNotify(IntPtr callback);
 [PreserveSig]int GetChannelCount(out uint count);
 [PreserveSig]int SetMasterVolumeLevel(float value,IntPtr context);
 [PreserveSig]int SetMasterVolumeLevelScalar(float value,IntPtr context);
 [PreserveSig]int GetMasterVolumeLevel(out float value);
 [PreserveSig]int GetMasterVolumeLevelScalar(out float value);
 [PreserveSig]int SetChannelVolumeLevel(uint channel,float value,IntPtr context);
 [PreserveSig]int SetChannelVolumeLevelScalar(uint channel,float value,IntPtr context);
 [PreserveSig]int GetChannelVolumeLevel(uint channel,out float value);
 [PreserveSig]int GetChannelVolumeLevelScalar(uint channel,out float value);
 [PreserveSig]int SetMute([MarshalAs(UnmanagedType.Bool)]bool mute,IntPtr context);
 [PreserveSig]int GetMute([MarshalAs(UnmanagedType.Bool)]out bool mute);
}
class AudioProbe {
 static void OK(int hr){Marshal.ThrowExceptionForHR(hr);}
 static void Print(EndpointVolume volume,bool same){float value;bool mute;OK(volume.GetMasterVolumeLevelScalar(out value));OK(volume.GetMute(out mute));Console.WriteLine("{\"volume\":"+value.ToString("R",CultureInfo.InvariantCulture)+",\"mute\":"+(mute?"true":"false")+",\"sameEndpoint\":"+(same?"true":"false")+"}");Console.Out.Flush();}
 [STAThread]static int Main(){
  Enumerator enumerator=null;Device initial=null;EndpointVolume volume=null;bool armed=false,oldMute=false;float oldVolume=0;
  try{
   enumerator=(Enumerator)new EnumeratorObject();OK(enumerator.GetDefaultAudioEndpoint(0,0,out initial));
   string initialId;OK(initial.GetId(out initialId));Guid iid=typeof(EndpointVolume).GUID;object obj;OK(initial.Activate(ref iid,23,IntPtr.Zero,out obj));volume=(EndpointVolume)obj;
   OK(volume.GetMasterVolumeLevelScalar(out oldVolume));OK(volume.GetMute(out oldMute));Print(volume,true);
   string command;
   while((command=Console.ReadLine())!=null){
    if(command=="done")break;
    if(command=="arm"){armed=true;Console.WriteLine("armed");Console.Out.Flush();continue;}
    if(command!="sample")throw new Exception("Unexpected fixture command");
    Device current;OK(enumerator.GetDefaultAudioEndpoint(0,0,out current));string currentId;
    try{OK(current.GetId(out currentId));}finally{Marshal.ReleaseComObject(current);}
    Print(volume,currentId==initialId);
   }
   return 0;
  }catch(Exception e){Console.Error.WriteLine(e.GetType().Name+": "+e.Message);return 1;}
  finally{
   if(volume!=null){if(armed){OK(volume.SetMasterVolumeLevelScalar(oldVolume,IntPtr.Zero));OK(volume.SetMute(oldMute,IntPtr.Zero));Print(volume,true);}Marshal.ReleaseComObject(volume);}
   if(initial!=null)Marshal.ReleaseComObject(initial);if(enumerator!=null)Marshal.ReleaseComObject(enumerator);
  }
 }
}
