// Public release discovery and bounded downloads. No account credentials.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;

static class GitHubUpdate {
    internal const string ReleasesUrl="https://github.com/eddyorlandotp/eddy-deck/releases";
    internal const string ApiUrl="https://api.github.com/repos/eddyorlandotp/eddy-deck/releases?per_page=30";
    internal const string AssetPrefix="https://github.com/eddyorlandotp/eddy-deck/releases/download/";
    static JavaScriptSerializer Json { get { return new JavaScriptSerializer {MaxJsonLength=2000000}; } }
    internal static int[] VersionParts(string value) {
        var m=Regex.Match(value??"",@"^(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})(?:-(alpha|beta|rc)\.([1-9][0-9]{0,5}))?$");
        if(!m.Success)throw new Exception("Versión de Eddy Deck inválida.");
        return new[]{Int32.Parse(m.Groups[1].Value),Int32.Parse(m.Groups[2].Value),Int32.Parse(m.Groups[3].Value),m.Groups[4].Success?Array.IndexOf(new[]{"alpha","beta","rc"},m.Groups[4].Value):3,m.Groups[5].Success?Int32.Parse(m.Groups[5].Value):0};
    }
    internal static int Compare(string a,string b) {
        var x=VersionParts(a);var y=VersionParts(b);for(int i=0;i<x.Length;i++){int c=x[i].CompareTo(y[i]);if(c!=0)return c;}return 0;
    }
    internal static bool AllowedUri(Uri uri,bool redirect) {
        if(uri.Scheme!="https"||!uri.IsDefaultPort||uri.UserInfo!=""||uri.Fragment!="")return false;
        if(redirect)return uri.Host=="release-assets.githubusercontent.com"||uri.Host=="objects.githubusercontent.com";
        return uri.AbsoluteUri==ApiUrl||(uri.Host=="github.com"&&uri.AbsoluteUri.StartsWith(AssetPrefix,StringComparison.Ordinal)&&uri.Query=="");
    }
    internal static void Transfer(string url,Stream output,long limit,CancellationToken token,Action<long> progress) {
        var uri=new Uri(url);if(!AllowedUri(uri,false))throw new Exception("El enlace no pertenece a las entregas oficiales de Eddy Deck.");
        ServicePointManager.SecurityProtocol|=SecurityProtocolType.Tls12;
        for(int redirects=0;redirects<=4;redirects++) {
            token.ThrowIfCancellationRequested();var request=(HttpWebRequest)WebRequest.Create(uri);
            request.UserAgent="EddyDeck-Updater";request.Accept="application/vnd.github+json";request.AllowAutoRedirect=false;request.Timeout=15000;request.ReadWriteTimeout=15000;
            using(token.Register(()=>request.Abort())) {
                try { using(var response=(HttpWebResponse)request.GetResponse()) {
                    int status=(int)response.StatusCode;
                    if(status>=300&&status<400){var next=new Uri(uri,response.Headers["Location"]);if(!AllowedUri(next,true))throw new Exception("GitHub redirigió a un destino no permitido.");uri=next;continue;}
                    if(status!=200||response.ContentLength>limit)throw new Exception("Descarga inválida o demasiado grande.");
                    long count=0;byte[] buffer=new byte[65536];using(var input=response.GetResponseStream()) {
                        int n;while((n=input.Read(buffer,0,buffer.Length))!=0){token.ThrowIfCancellationRequested();count+=n;if(count>limit)throw new Exception("La descarga excede el tamaño permitido.");output.Write(buffer,0,n);if(progress!=null)progress(count);}
                    }
                    if(response.ContentLength>=0&&count!=response.ContentLength)throw new Exception("La descarga quedó incompleta.");return;
                }} catch(WebException){token.ThrowIfCancellationRequested();throw new Exception("No se pudo descargar de GitHub. Revisa internet o espera si se alcanzó su límite de consultas. La copia instalada se conserva.");}
            }
        }
        throw new Exception("Demasiadas redirecciones de descarga.");
    }
    internal static byte[] Bytes(string url,long limit,CancellationToken token) {
        using(var output=new MemoryStream()){Transfer(url,output,limit,token,null);return output.ToArray();}
    }
    internal static Dictionary<string,object> Signed(byte[] raw,byte[] signature,string modulus) {
        if(raw.Length>64000||signature.Length>2048)throw new Exception("Información de actualización demasiado grande.");
        using(var rsa=new RSACryptoServiceProvider()){rsa.PersistKeyInCsp=false;rsa.ImportParameters(new RSAParameters {Modulus=Convert.FromBase64String(modulus),Exponent=new byte[]{1,0,1}});
            if(!rsa.VerifyData(raw,CryptoConfig.MapNameToOID("SHA256"),Convert.FromBase64String(Encoding.ASCII.GetString(signature).Trim())))throw new Exception("La firma de la actualización no es válida.");}
        var data=Json.Deserialize<Dictionary<string,object>>(Encoding.UTF8.GetString(raw));
        string version=Convert.ToString(data["version"]);VersionParts(version);
        if(Convert.ToInt32(data["schema"])!=1||Convert.ToString(data["architecture"])!="x64"||Convert.ToInt32(data["minWindowsBuild"])<22000)throw new Exception("Información de actualización incompatible.");
        string name="EddyDeck-Windows-"+version+".zip";
        if(Convert.ToString(data["file"])!=name||Convert.ToString(data["url"])!=AssetPrefix+"v"+version+"/"+name)throw new Exception("El paquete no corresponde a la versión firmada.");
        long size=Convert.ToInt64(data["size"]);if(size<1||size>500000000||!Regex.IsMatch(Convert.ToString(data["sha256"]),"^[0-9a-f]{64}$"))throw new Exception("Tamaño o huella de descarga inválidos.");
        return data;
    }
    internal static List<Dictionary<string,object>> Releases(byte[] raw) {
        var result=new List<Dictionary<string,object>>();var rows=Json.DeserializeObject(Encoding.UTF8.GetString(raw)) as object[];
        if(rows==null||rows.Length>30)throw new Exception("Lista de versiones inválida.");
        foreach(var value in rows){var row=value as Dictionary<string,object>;if(row==null||!row.ContainsKey("draft")||Convert.ToBoolean(row["draft"]))continue;
            string tag=Convert.ToString(row["tag_name"]);if(!tag.StartsWith("v"))continue;try{VersionParts(tag.Substring(1));}catch{continue;}
            var assets=row["assets"] as object[];if(assets==null)continue;
            bool complete=new[]{"EddyDeck-update.json","EddyDeck-update.sig","EddyDeck-Windows-"+tag.Substring(1)+".zip"}.All(name=>assets.OfType<Dictionary<string,object>>().Count(a=>Convert.ToString(a["name"])==name&&Convert.ToString(a["state"])=="uploaded"&&Convert.ToString(a["browser_download_url"])==AssetPrefix+tag+"/"+name)==1);
            if(complete)result.Add(row);
        }
        result.Sort((a,b)=>Compare(Convert.ToString(b["tag_name"]).Substring(1),Convert.ToString(a["tag_name"]).Substring(1)));return result;
    }
    internal static string Extract(string zip,string destination,CancellationToken token) {
        // Destination is a newly-created owned staging directory; no overwrite.
        Directory.CreateDirectory(destination);string prefix=Path.GetFullPath(destination).TrimEnd('\\')+"\\";
        using(var archive=ZipFile.OpenRead(zip)) {
            if(archive.Entries.Count==0||archive.Entries.Count>5000)throw new Exception("Archivo ZIP no válido.");
            long total=0;var names=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach(var e in archive.Entries){token.ThrowIfCancellationRequested();string name=e.FullName;
                bool directory=name.EndsWith("/");string clean=directory?name.TrimEnd('/'):name;
                if(String.IsNullOrEmpty(clean)||Path.IsPathRooted(clean)||clean.Contains("\\")||clean.Contains(":")||clean.Split('/').Any(p=>p=="."||p==".."||p==""||p.EndsWith(".")||p.EndsWith(" ")||Regex.IsMatch(p,@"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)",RegexOptions.IgnoreCase))||!names.Add(clean))throw new Exception("Ruta inválida o repetida en el ZIP.");
                if(((e.ExternalAttributes>>16)&0xf000)==0xa000)throw new Exception("El ZIP contiene enlaces no permitidos.");
                total+=e.Length;if(e.Length<0||total>500000000)throw new Exception("El ZIP excede el tamaño permitido.");
                string path=Path.GetFullPath(Path.Combine(destination,clean.Replace('/',Path.DirectorySeparatorChar)));if(!path.StartsWith(prefix,StringComparison.OrdinalIgnoreCase))throw new Exception("Ruta fuera del destino.");
                if(directory){Directory.CreateDirectory(path);continue;}Directory.CreateDirectory(Path.GetDirectoryName(path));
                using(var input=e.Open())using(var output=new FileStream(path,FileMode.CreateNew)){byte[] buffer=new byte[65536];long count=0;int n;while((n=input.Read(buffer,0,buffer.Length))!=0){token.ThrowIfCancellationRequested();count+=n;if(count>e.Length)throw new Exception("Archivo descomprimido demasiado grande.");output.Write(buffer,0,n);}if(count!=e.Length)throw new Exception("Archivo descomprimido incompleto.");}
            }
        }
        return destination;
    }
    internal static string Prepare(string current,int windowsBuild,string modulus,string stagingRoot,CancellationToken token,Action<string> progress,Func<string,Dictionary<string,object>> verify) {
        progress("Buscando entregas completas en GitHub…");var releases=Releases(Bytes(ApiUrl,2000000,token));
        if(releases.Count==0)throw new Exception("No hay una entrega con instalador disponible en GitHub. Puedes usar la copia del celular.");
        string tag=Convert.ToString(releases[0]["tag_name"]),baseUrl=AssetPrefix+tag+"/";
        var info=Signed(Bytes(baseUrl+"EddyDeck-update.json",64000,token),Bytes(baseUrl+"EddyDeck-update.sig",2048,token),modulus);
        if("v"+Convert.ToString(info["version"])!=tag)throw new Exception("La versión firmada no coincide con la entrega.");
        if(Compare(Convert.ToString(info["version"]),current)<0)throw new Exception("Tu copia es más reciente que la publicada. Se conserva la actual.");
        if(windowsBuild<Convert.ToInt32(info["minWindowsBuild"]))throw new Exception("La nueva versión necesita una actualización de Windows. No se cambió tu instalación.");
        string owned=Path.Combine(stagingRoot,Guid.NewGuid().ToString("N"));Directory.CreateDirectory(owned);
        try {
            var drive=new DriveInfo(Path.GetPathRoot(owned));if(drive.AvailableFreeSpace<Convert.ToInt64(info["size"])+600000000)throw new Exception("Falta espacio para descargar y comprobar la actualización.");
            string zip=Path.Combine(owned,"package.zip");long size=Convert.ToInt64(info["size"]);long lastMb=-1;
            using(var stream=new FileStream(zip,FileMode.CreateNew)){Transfer(Convert.ToString(info["url"]),stream,size,token,n=>{long mb=n/1048576;if(mb!=lastMb){lastMb=mb;progress("Descargando "+info["version"]+": "+mb+" / "+((size+1048575)/1048576)+" MB");}});}
            string hash;using(var algorithm=SHA256.Create())using(var stream=File.OpenRead(zip)){hash=BitConverter.ToString(algorithm.ComputeHash(stream)).Replace("-","").ToLowerInvariant();}
            if(new FileInfo(zip).Length!=size||hash!=Convert.ToString(info["sha256"]))throw new Exception("El archivo descargado está incompleto o modificado. No se instalará.");
            progress("Comprobando todos los archivos y su firma…");string folder=Extract(zip,Path.Combine(owned,"Windows"),token);var manifest=verify(folder);token.ThrowIfCancellationRequested();
            if(Convert.ToString(manifest["version"])!=Convert.ToString(info["version"]))throw new Exception("El contenido tiene otra versión.");
            File.Delete(zip);return folder;
        } catch {Clean(owned,stagingRoot);throw;}
    }
    internal static void Clean(string owned,string root) {
        Guid id;string full=Path.GetFullPath(owned),parent=Path.GetFullPath(root).TrimEnd('\\');
        if(Path.GetDirectoryName(full)!=parent||!Guid.TryParse(Path.GetFileName(full),out id))return;
        try{if(Directory.Exists(full)&&(File.GetAttributes(full)&FileAttributes.ReparsePoint)==0)Directory.Delete(full,true);}catch{/* Never broaden cleanup beyond this operation's staging directory. */}
    }
}
