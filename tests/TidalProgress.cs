using System;
using System.Windows.Automation;
class TidalProgress {
    [MTAThread] static int Main(string[] args) {
        try {
            var root=AutomationElement.FromHandle(new IntPtr(long.Parse(args[0])));
            var footer=root.FindFirst(TreeScope.Descendants,new PropertyCondition(AutomationElement.AutomationIdProperty,"footerPlayer"));
            var slider=footer.FindFirst(TreeScope.Descendants,new PropertyCondition(AutomationElement.AutomationIdProperty,"progressBar"));
            object pattern;
            if(slider.TryGetCurrentPattern(RangeValuePattern.Pattern,out pattern))Console.WriteLine(((RangeValuePattern)pattern).Current.Value.ToString(System.Globalization.CultureInfo.InvariantCulture));
            else throw new Exception("Timeline does not expose RangeValuePattern");
            return 0;
        }catch(Exception e){Console.Error.WriteLine(e.Message);return 1;}
    }
}
