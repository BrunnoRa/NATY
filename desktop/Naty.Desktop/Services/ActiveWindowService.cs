using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

namespace Naty.Desktop.Services;

public sealed record ActiveWindowSnapshot(string process_name, string window_title, string timestamp, long window_handle);

public sealed class ActiveWindowService
{
    private ActiveWindowSnapshot? _lastExternal;

    public void RememberForeground()
    {
        var snapshot = Capture();
        if (snapshot is not null) _lastExternal = snapshot;
    }

    public ActiveWindowSnapshot? GetForRequest()
    {
        RememberForeground();
        return _lastExternal;
    }

    public static bool TryActivate(long rawHandle)
    {
        var handle = new IntPtr(rawHandle);
        if (handle == IntPtr.Zero || !IsWindow(handle)) return false;
        if (IsIconic(handle)) ShowWindow(handle, 9);
        return SetForegroundWindow(handle);
    }

    private static ActiveWindowSnapshot? Capture()
    {
        var handle = GetForegroundWindow();
        if (handle == IntPtr.Zero) return null;
        GetWindowThreadProcessId(handle, out var processId);
        if (processId == 0 || processId == Environment.ProcessId) return null;
        try
        {
            using var process = Process.GetProcessById((int)processId);
            var length = Math.Min(GetWindowTextLength(handle), 500);
            var title = new StringBuilder(length + 1);
            if (length > 0) GetWindowText(handle, title, title.Capacity);
            return new ActiveWindowSnapshot(process.ProcessName, title.ToString(), DateTimeOffset.Now.ToString("O"), handle.ToInt64());
        }
        catch (ArgumentException) { return null; }
        catch (InvalidOperationException) { return null; }
    }

    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll")] private static extern int GetWindowTextLength(IntPtr hWnd);
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] private static extern bool IsIconic(IntPtr hWnd);
    [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr hWnd, int command);
    [DllImport("user32.dll")] private static extern bool IsWindow(IntPtr hWnd);
}
