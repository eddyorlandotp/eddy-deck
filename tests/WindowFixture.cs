using System;using System.Windows.Forms;using System.Drawing;
class WindowFixture{
 [STAThread] static void Main(){Application.EnableVisualStyles();
  var normal=new Form{Text="Eddy Deck TEST normal",Size=new Size(520,340),StartPosition=FormStartPosition.Manual,Location=new Point(80,100)};
  var guarded=new Form{Text="Eddy Deck TEST pendiente",Size=new Size(480,300),StartPosition=FormStartPosition.Manual,Location=new Point(160,180)};
  normal.Controls.Add(new Label{Text="Ventana creada para pruebas de Eddy Deck. No contiene documentos.",Dock=DockStyle.Fill});
  var status=new Label{Text="Simula cambios sin guardar. Rechaza WM_CLOSE sin perder el estado.",Dock=DockStyle.Fill};guarded.Controls.Add(status);
  guarded.FormClosing+=(s,e)=>{e.Cancel=true;status.Text="Cierre recibido y detenido: cambios pendientes simulados. Motivo: "+e.CloseReason;};
  var timeout=new Timer{Interval=300000};timeout.Tick+=(s,e)=>Environment.Exit(0);timeout.Start();
  normal.Show();guarded.Show();Application.Run();
 }
}
