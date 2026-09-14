using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;

class UpdaterChecks {
    static int count;
    static void Check(bool ok,string name){if(!ok)throw new Exception(name);count++;Console.WriteLine(name);}
    static void Reject(Action action,string name){try{action();}catch{Check(true,name);return;}throw new Exception("Accepted: "+name);}
    static int Main(string[] args){try{
        var root=args[0];string mod=File.ReadAllText(Path.Combine(root,"modulus.txt"));var raw=File.ReadAllBytes(Path.Combine(root,"update.json"));var sig=File.ReadAllBytes(Path.Combine(root,"update.sig"));
        Check(GitHubUpdate.Compare("2.2.9-beta.11","2.2.9-beta.2")>0,"Numeric prerelease ordering");
        Check(GitHubUpdate.Compare("2.2.9","2.2.9-rc.1")>0,"Stable follows release candidate");
        Check(GitHubUpdate.Compare("2.2.10-alpha.1","2.2.9")>0,"Core version ordering");
        foreach(string v in new[]{"2.2","2.2.9-beta.0","2.2.9-beta.01","2.2.9-test.1","../2.2.9","2.2.9+build","2.2.9-public-source","2.9999999.9"})Reject(()=>GitHubUpdate.VersionParts(v),"Invalid version: "+v);
        var valid=GitHubUpdate.Signed(raw,sig,mod);Check(Convert.ToString(valid["version"])=="2.2.9-beta.11","Signed download envelope");
        var changed=(byte[])raw.Clone();changed[10]^=1;Reject(()=>GitHubUpdate.Signed(changed,sig,mod),"Tampered envelope rejected");
        Reject(()=>GitHubUpdate.Signed(raw,new byte[2049],mod),"Oversized signature rejected");
        foreach(var file in Directory.GetFiles(root,"invalid-*.json")){string signature=Path.ChangeExtension(file,"sig");Reject(()=>GitHubUpdate.Signed(File.ReadAllBytes(file),File.ReadAllBytes(signature),mod),"Signed invalid envelope: "+Path.GetFileName(file));}
        Check(GitHubUpdate.AllowedUri(new Uri(GitHubUpdate.ApiUrl),false),"Official API permitted");
        foreach(string url in new[]{"http://github.com/eddyorlandotp/eddy-deck/releases/download/v2.2.9/a.zip","https://evil.example/a.zip","https://github.com/other/repo/releases/download/v1/a.zip","https://github.com:444/eddyorlandotp/eddy-deck/releases/download/v1/a.zip","https://user@github.com/eddyorlandotp/eddy-deck/releases/download/v1/a.zip","https://github.com/eddyorlandotp/eddy-deck/releases/download/v1/a.zip?foo"})Check(!GitHubUpdate.AllowedUri(new Uri(url),false),"Download URL rejected: "+url);
        Check(!GitHubUpdate.AllowedUri(new Uri("http://release-assets.githubusercontent.com/a"),true),"Redirect downgrade rejected");
        Check(!GitHubUpdate.AllowedUri(new Uri("https://localhost/a"),true),"Local redirect rejected");
        var json=new JavaScriptSerializer();var assets=new List<object>();foreach(string name in new[]{"EddyDeck-update.json","EddyDeck-update.sig","EddyDeck-Windows-2.2.9-beta.11.zip"})assets.Add(new {name=name,state="uploaded",browser_download_url=GitHubUpdate.AssetPrefix+"v2.2.9-beta.11/"+name});
        var release=new Dictionary<string,object>{{"tag_name","v2.2.9-beta.11"},{"draft",false},{"assets",assets}};
        Func<byte[]> encode=()=>Encoding.UTF8.GetBytes(json.Serialize(new[]{release}));Check(GitHubUpdate.Releases(encode()).Count==1,"Complete release discovered");
        release["draft"]=true;Check(GitHubUpdate.Releases(encode()).Count==0,"Draft skipped");release["draft"]=false;assets.RemoveAt(1);Check(GitHubUpdate.Releases(encode()).Count==0,"Incomplete upload skipped");
        release["tag_name"]="v2.2.9-beta.11-public-source";Check(GitHubUpdate.Releases(encode()).Count==0,"Source-only release skipped");
        using(var c=new CancellationTokenSource()){c.Cancel();Reject(()=>GitHubUpdate.Bytes(GitHubUpdate.ApiUrl,100,c.Token),"Cancelled request never starts");}
        foreach(string zip in Directory.GetFiles(root,"unsafe-*.zip")){string dest=Path.Combine(root,Guid.NewGuid().ToString("N"));try{Reject(()=>GitHubUpdate.Extract(zip,dest,CancellationToken.None),"Unsafe ZIP: "+Path.GetFileName(zip));}finally{GitHubUpdate.Clean(dest,root);}}
        string good=Path.Combine(root,Guid.NewGuid().ToString("N"));try{GitHubUpdate.Extract(Path.Combine(root,"good.zip"),good,CancellationToken.None);Check(File.ReadAllText(Path.Combine(good,"nested/file.txt"))=="fixture","Valid archive extracted");}finally{GitHubUpdate.Clean(good,root);}
        Console.WriteLine("PASSED="+count);return 0;
    }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}}
}
