using System;
using System.Windows.Automation;
class TidalIdentity {
    [MTAThread] static int Main(string[] args) {
        try {
            var root=AutomationElement.FromHandle(new IntPtr(long.Parse(args[0])));
            var footer=root.FindFirst(TreeScope.Descendants,new PropertyCondition(AutomationElement.AutomationIdProperty,"footerPlayer"));
            var links=footer.FindAll(TreeScope.Descendants,new PropertyCondition(AutomationElement.ControlTypeProperty,ControlType.Hyperlink));string names="";foreach(AutomationElement e in links)names+=e.Current.Name+"\n";using(var sha=System.Security.Cryptography.SHA256.Create())Console.WriteLine(BitConverter.ToString(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(names))).Replace("-",""));return 0;
        }catch(Exception e){Console.Error.WriteLine(e.Message);return 1;}
    }
}
