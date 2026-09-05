using System.Windows;
using System.IO;
using System.Threading;

namespace Naty.Desktop;

public partial class App : System.Windows.Application
{
    private const string InstanceName = "NATY.V3.Desktop.SingleInstance";
    private Mutex? _instanceMutex;
    private EventWaitHandle? _activationEvent;
    internal static string? ScreenshotPath { get; private set; }
    internal static string? StartupCommand { get; private set; }

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        _instanceMutex = new Mutex(true, InstanceName, out var firstInstance);
        if (!firstInstance)
        {
            try { EventWaitHandle.OpenExisting(InstanceName + ".Activate").Set(); }
            catch (WaitHandleCannotBeOpenedException) { }
            Shutdown();
            return;
        }
        _activationEvent = new EventWaitHandle(false, EventResetMode.AutoReset, InstanceName + ".Activate");
        var screenshotIndex = Array.IndexOf(e.Args, "--screenshot");
        if (screenshotIndex >= 0 && screenshotIndex + 1 < e.Args.Length)
            ScreenshotPath = Path.GetFullPath(e.Args[screenshotIndex + 1]);
        var commandIndex = Array.IndexOf(e.Args, "--command");
        if (commandIndex >= 0 && commandIndex + 1 < e.Args.Length)
            StartupCommand = e.Args[commandIndex + 1];
        ShutdownMode = ShutdownMode.OnExplicitShutdown;
        var window = new MainWindow();
        MainWindow = window;
        window.Show();
        var activationEvent = _activationEvent;
        _ = Task.Run(() =>
        {
            try
            {
                while (activationEvent.WaitOne())
                    Dispatcher.Invoke(() => { window.Show(); window.WindowState = WindowState.Normal; window.Activate(); window.Topmost = true; window.Topmost = false; });
            }
            catch (ObjectDisposedException) { }
        });
    }

    protected override void OnExit(ExitEventArgs e)
    {
        _activationEvent?.Dispose();
        _instanceMutex?.Dispose();
        base.OnExit(e);
    }
}
