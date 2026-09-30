// Windows Core Audio endpoint control. No playback or global keyboard events.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;

[ComImport,Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class AudioEnumeratorObject {}
[ComImport,Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] interface AudioEnumerator {
 [PreserveSig]int EnumAudioEndpoints(int flow,int mask,out AudioDevices devices);
 [PreserveSig]int GetDefaultAudioEndpoint(int flow,int role,out AudioDevice device);
}
[ComImport,Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] interface AudioDevices {
 [PreserveSig]int GetCount(out uint count);
 [PreserveSig]int Item(uint index,out AudioDevice device);
}
[ComImport,Guid("D666063F-1587-4E43-81F1-B948E807363F"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] interface AudioDevice {
 [PreserveSig]int Activate(ref Guid iid,int context,IntPtr parameters,[MarshalAs(UnmanagedType.IUnknown)]out object value);
 [PreserveSig]int OpenPropertyStore(int access,out AudioProperties properties);
 [PreserveSig]int GetId([MarshalAs(UnmanagedType.LPWStr)]out string id);
 [PreserveSig]int GetState(out uint state);
}
[StructLayout(LayoutKind.Sequential)] struct AudioPropertyKey { public Guid fmtid; public uint pid; }
[StructLayout(LayoutKind.Explicit,Size=24)] struct AudioVariant { [FieldOffset(0)]public ushort vt;[FieldOffset(8)]public IntPtr text; }
[ComImport,Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] interface AudioProperties {
 [PreserveSig]int GetCount(out uint count);
 [PreserveSig]int GetAt(uint index,out AudioPropertyKey key);
 [PreserveSig]int GetValue(ref AudioPropertyKey key,out AudioVariant value);
}
[ComImport,Guid("5CDF2C82-841E-4546-9722-0CF74078229A"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] interface AudioLevel {
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
 [PreserveSig]int SetMute([MarshalAs(UnmanagedType.Bool)]bool value,IntPtr context);
 [PreserveSig]int GetMute([MarshalAs(UnmanagedType.Bool)]out bool value);
}
// IPolicyConfig is undocumented. Keep it isolated and report refusal clearly.
// Slots 0..9 are deliberately unused; only SetDefaultEndpoint is invoked.
[ComImport,Guid("870AF99C-171D-4F9E-AF0D-E63DF40C2BC9")] class AudioPolicyObject {}
[ComImport,Guid("F8679F50-850A-41CF-9C72-430F290290C8"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] interface AudioPolicy {
 [PreserveSig]int Unused0();[PreserveSig]int Unused1();[PreserveSig]int Unused2();[PreserveSig]int Unused3();[PreserveSig]int Unused4();
 [PreserveSig]int Unused5();[PreserveSig]int Unused6();[PreserveSig]int Unused7();[PreserveSig]int Unused8();[PreserveSig]int Unused9();
 [PreserveSig]int SetDefaultEndpoint([MarshalAs(UnmanagedType.LPWStr)]string id,int role);
}
static class AudioOutput {
 [DllImport("ole32.dll")]static extern int PropVariantClear(ref AudioVariant value);
 static void OK(int hr){Marshal.ThrowExceptionForHR(hr);}
 static void Release(object obj){if(obj!=null&&Marshal.IsComObject(obj))Marshal.ReleaseComObject(obj);}
 static string Id(AudioDevice d){string id;OK(d.GetId(out id));return id;}
 static string Default(AudioEnumerator e,int role){AudioDevice d=null;try{int hr=e.GetDefaultAudioEndpoint(0,role,out d);return hr<0?"":Id(d);}finally{Release(d);}}
 static string Name(AudioDevice d){AudioProperties p=null;AudioVariant value=new AudioVariant();try{OK(d.OpenPropertyStore(0,out p));var key=new AudioPropertyKey{fmtid=new Guid("A45C254E-DF1C-4EFD-8020-67D146A850E0"),pid=14};OK(p.GetValue(ref key,out value));return value.vt==31?Marshal.PtrToStringUni(value.text):"Salida de audio";}finally{PropVariantClear(ref value);Release(p);}}
 static AudioLevel Level(AudioDevice d){Guid id=typeof(AudioLevel).GUID;object value;OK(d.Activate(ref id,23,IntPtr.Zero,out value));return (AudioLevel)value;}
 static Dictionary<string,object> Snapshot(AudioEnumerator e){
  string primary=Default(e,0);var rows=new List<object>();AudioDevices collection=null;int? volume=null;bool mute=false;
  try{OK(e.EnumAudioEndpoints(0,1,out collection));uint count;OK(collection.GetCount(out count));if(count>128)throw new Exception("Windows informó demasiadas salidas de audio.");
   for(uint i=0;i<count;i++){AudioDevice d=null;AudioLevel level=null;try{OK(collection.Item(i,out d));string id=Id(d);var row=new Dictionary<string,object>{{"id",id},{"name",Name(d)},{"default",id==primary}};rows.Add(row);if(id==primary){try{level=Level(d);float v;OK(level.GetMasterVolumeLevelScalar(out v));OK(level.GetMute(out mute));volume=(int)Math.Round(v*100);}catch(COMException){volume=null;}}}finally{Release(level);Release(d);}}
  }finally{Release(collection);}
  return new Dictionary<string,object>{{"outputs",rows},{"defaultId",primary},{"mediaDefaultId",Default(e,1)},{"communicationsDefaultId",Default(e,2)},{"volume",volume},{"mute",mute},{"available",volume.HasValue},{"error",""}};
 }
 static AudioDevice Find(AudioEnumerator e,string wanted){AudioDevices list=null;try{OK(e.EnumAudioEndpoints(0,1,out list));uint count;OK(list.GetCount(out count));if(count>128)throw new Exception("Demasiadas salidas de audio.");for(uint i=0;i<count;i++){AudioDevice d=null;OK(list.Item(i,out d));if(Id(d)==wanted)return d;Release(d);}throw new Exception("La salida se desconectó. Actualiza la lista y elige de nuevo.");}finally{Release(list);}}
 static void Select(AudioEnumerator e,string target,string expected){
  if(Default(e,0)!=expected)throw new Exception("La salida cambió desde que abriste el control. Actualiza y vuelve a elegir.");
  AudioDevice d=null;AudioPolicy policy=null;string[] before={Default(e,0),Default(e,1)};bool[] changed={false,false};
  try{d=Find(e,target);policy=(AudioPolicy)new AudioPolicyObject();for(int role=0;role<2;role++){string current=Default(e,role);if(current!=before[role]&&current!=target)throw new Exception("Windows cambió la salida durante la operación.");if(current!=target)OK(policy.SetDefaultEndpoint(target,role));for(int check=0;check<2;check++)if(before[check]!=target&&Default(e,check)==target)changed[check]=true;}if(Default(e,0)!=target||Default(e,1)!=target)throw new Exception("Windows no confirmó la salida elegida.");}
  catch{if(policy!=null)for(int role=0;role<2;role++)if(changed[role]&&before[role]!=""&&Default(e,role)==target){try{OK(policy.SetDefaultEndpoint(before[role],role));}catch{}}throw;}
  finally{Release(policy);Release(d);}
 }
 [STAThread]static int Main(string[] args){
  Console.OutputEncoding=new System.Text.UTF8Encoding(false);AudioEnumerator e=null;try{
   if(args.Length<1)throw new Exception("Falta la acción de audio.");e=(AudioEnumerator)new AudioEnumeratorObject();
   if(args[0]=="select"&&args.Length==3)Select(e,args[1],args[2]);
   else if((args[0]=="volume"||args[0]=="mute")&&args.Length==3){
    if(Default(e,0)!=args[1])throw new Exception("La salida cambió. No se ajustó otra salida por accidente.");
    AudioDevice d=null;AudioLevel level=null;try{d=Find(e,args[1]);level=Level(d);int value;if(!Int32.TryParse(args[2],NumberStyles.None,CultureInfo.InvariantCulture,out value))throw new Exception("Valor de audio no válido.");
     if(args[0]=="volume"){if(value<0||value>100)throw new Exception("Volumen fuera de rango.");OK(level.SetMasterVolumeLevelScalar(value/100f,IntPtr.Zero));float actual;OK(level.GetMasterVolumeLevelScalar(out actual));if(Math.Abs(actual*100-value)>1.1)throw new Exception("Windows no confirmó el volumen.");}
     else{if(value!=0&&value!=1)throw new Exception("Silencio no válido.");OK(level.SetMute(value==1,IntPtr.Zero));bool actual;OK(level.GetMute(out actual));if(actual!=(value==1))throw new Exception("Windows no confirmó el silencio.");}
    }finally{Release(level);Release(d);}
   }else if(args[0]!="list"||args.Length!=1)throw new Exception("Acción de audio no válida.");
   Console.WriteLine(new JavaScriptSerializer().Serialize(Snapshot(e)));return 0;
  }catch(Exception error){Console.WriteLine(new JavaScriptSerializer().Serialize(new{error=error.Message}));return 1;}finally{Release(e);}
 }
}
