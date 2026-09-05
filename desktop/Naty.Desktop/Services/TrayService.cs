using Drawing = System.Drawing;
using Forms = System.Windows.Forms;
using System.IO;

namespace Naty.Desktop.Services;

public sealed class TrayService : IDisposable
{
    private readonly Forms.NotifyIcon _icon;

    public TrayService(Action open, Action listen, Action settings, Action exit)
    {
        var iconPath = Path.Combine(AppContext.BaseDirectory, "Assets", "naty.ico");
        _icon = new Forms.NotifyIcon
        {
            Text = "NATY",
            Icon = File.Exists(iconPath) ? new Drawing.Icon(iconPath) : System.Drawing.SystemIcons.Application,
            Visible = true,
            ContextMenuStrip = new Forms.ContextMenuStrip(),
        };
        _icon.ContextMenuStrip.Items.Add("Abrir NATY", null, (_, _) => open());
        _icon.ContextMenuStrip.Items.Add("Ouvir", null, (_, _) => listen());
        _icon.ContextMenuStrip.Items.Add("Configurações", null, (_, _) => settings());
        _icon.ContextMenuStrip.Items.Add(new Forms.ToolStripSeparator());
        _icon.ContextMenuStrip.Items.Add("Sair", null, (_, _) => exit());
        _icon.DoubleClick += (_, _) => open();
    }

    public void Notify(string title, string message)
    {
        _icon.BalloonTipTitle = title;
        _icon.BalloonTipText = message;
        _icon.ShowBalloonTip(3000);
    }

    public void Dispose()
    {
        _icon.Visible = false;
        _icon.Dispose();
    }
}
