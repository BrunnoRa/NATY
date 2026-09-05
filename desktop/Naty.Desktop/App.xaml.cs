using System.Windows;
using System.IO;

namespace Naty.Desktop;

public partial class App : System.Windows.Application
{
    internal static string? ScreenshotPath { get; private set; }
    internal static string? StartupCommand { get; private set; }

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        var screenshotIndex = Array.IndexOf(e.Args, "--screenshot");
        if (screenshotIndex >= 0 && screenshotIndex + 1 < e.Args.Length)
            ScreenshotPath = Path.GetFullPath(e.Args[screenshotIndex + 1]);
        var commandIndex = Array.IndexOf(e.Args, "--command");
        if (commandIndex >= 0 && commandIndex + 1 < e.Args.Length)
            StartupCommand = e.Args[commandIndex + 1];
        ShutdownMode = ShutdownMode.OnExplicitShutdown;
        new MainWindow().Show();
    }
}
