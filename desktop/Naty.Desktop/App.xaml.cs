using System.Windows;
using System.IO;

namespace Naty.Desktop;

public partial class App : System.Windows.Application
{
    internal static string? ScreenshotPath { get; private set; }

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        var screenshotIndex = Array.IndexOf(e.Args, "--screenshot");
        if (screenshotIndex >= 0 && screenshotIndex + 1 < e.Args.Length)
            ScreenshotPath = Path.GetFullPath(e.Args[screenshotIndex + 1]);
        ShutdownMode = ShutdownMode.OnExplicitShutdown;
        new MainWindow().Show();
    }
}
