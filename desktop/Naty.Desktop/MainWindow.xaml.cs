using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Windows;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Naty.Desktop.Models;
using Naty.Desktop.Services;
using Naty.Desktop.ViewModels;

namespace Naty.Desktop;

public partial class MainWindow : Window
{
    private const int HotkeyId = 0x4E41;
    private readonly MainViewModel _viewModel = new();
    private readonly CoreClient _core = new();
    private readonly MiniHud _hud = new();
    private readonly DispatcherTimer _clock = new() { Interval = TimeSpan.FromSeconds(1) };
    private readonly DispatcherTimer _refresh = new() { Interval = TimeSpan.FromSeconds(5) };
    private TrayService? _tray;
    private bool _exiting;
    private static readonly HashSet<string> PrimaryProviders = new(StringComparer.OrdinalIgnoreCase)
        { "Voice", "Web", "Obsidian", "Sync" };

    public MainWindow()
    {
        InitializeComponent();
        DataContext = _viewModel;
        _core.ConnectionChanged += connected => Dispatcher.Invoke(() => _viewModel.Connection = connected ? "Core conectado" : "Core desconectado");
        _hud.Submitted += SendTextAsync;
        _hud.ExpandRequested += ShowDashboard;
        _clock.Tick += (_, _) => _viewModel.Clock = DateTime.Now.ToString("HH:mm");
        _refresh.Tick += async (_, _) => await RefreshDashboardAsync();
        Loaded += OnLoaded;
        Closing += OnClosing;
        StateChanged += (_, _) => Graph.SetPaused(WindowState == WindowState.Minimized || !IsVisible);
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        _tray = new TrayService(() => Dispatcher.Invoke(ShowDashboard), () => Dispatcher.Invoke(() => _hud.Open(_viewModel.State)),
            () => Dispatcher.Invoke(ShowDashboard), () => Dispatcher.Invoke(async () => await ExitAsync()));
        RegisterGlobalHotkey();
        _clock.Start(); _refresh.Start(); _viewModel.Clock = DateTime.Now.ToString("HH:mm");
        if (!await _core.EnsureConnectedAsync())
        {
            _viewModel.Response = "Core desconectado. Verifique o runtime Python e tente novamente.";
            return;
        }
        await RefreshDashboardAsync();
        _viewModel.Response = "Core conectado. O que você precisa?";
        if (!string.IsNullOrWhiteSpace(App.StartupCommand))
            await SendTextAsync(App.StartupCommand);
        if (!string.IsNullOrWhiteSpace(App.ScreenshotPath))
        {
            await Task.Delay(350);
            SaveScreenshot(App.ScreenshotPath);
            await ExitAsync();
        }
    }

    private async Task RefreshDashboardAsync()
    {
        if (!_core.IsConnected && !await _core.EnsureConnectedAsync()) return;
        try
        {
            var response = await _core.RequestAsync("dashboard");
            var payload = response.Payload;
            _viewModel.Providers.Clear();
            foreach (var item in payload.GetProperty("providers").EnumerateArray())
            {
                var name = item.GetProperty("name").GetString() ?? "";
                if (PrimaryProviders.Contains(name))
                    _viewModel.Providers.Add(new ProviderStatus(name, item.GetProperty("state").GetString() ?? "off"));
            }
            _viewModel.Tasks.Clear();
            foreach (var item in payload.GetProperty("tasks").EnumerateArray())
                _viewModel.Tasks.Add(new TaskItem(item.GetProperty("id").GetInt32(), item.GetProperty("title").GetString() ?? "",
                    item.TryGetProperty("due_at", out var due) && due.ValueKind != JsonValueKind.Null ? due.GetString() : null,
                    item.TryGetProperty("priority", out var priority) ? priority.GetString() ?? "normal" : "normal"));
            var metrics = payload.GetProperty("metrics");
            _viewModel.Ram = metrics.TryGetProperty("ram_mib", out var ram) && ram.ValueKind == JsonValueKind.Number ? $"{ram.GetDouble():0.0} MiB" : "—";
            _viewModel.Cpu = metrics.TryGetProperty("cpu_percent", out var cpu) && cpu.ValueKind == JsonValueKind.Number ? $"{cpu.GetDouble():0.0}%" : "—";
            SetGraph(payload.GetProperty("graph"));
            if (payload.TryGetProperty("notifications", out var notifications) && notifications.ValueKind == JsonValueKind.Array)
            {
                foreach (var notification in notifications.EnumerateArray())
                {
                    var title = notification.TryGetProperty("title", out var titleValue) ? titleValue.GetString() : "NATY";
                    var message = notification.TryGetProperty("message", out var messageValue) ? messageValue.GetString() : "";
                    if (!string.IsNullOrWhiteSpace(message))
                        _viewModel.Response = $"{title}: {message}";
                }
            }
        }
        catch { _viewModel.Connection = "Core desconectado"; }
    }

    private void SetGraph(JsonElement graph)
    {
        var nodes = graph.GetProperty("nodes").EnumerateArray().Select(n => new GraphNode(
            n.GetProperty("id").GetString() ?? "", n.GetProperty("type").GetString() ?? "note", n.GetProperty("title").GetString() ?? "",
            n.TryGetProperty("path", out var path) && path.ValueKind != JsonValueKind.Null ? path.GetString() : null,
            n.TryGetProperty("importance", out var importance) ? importance.GetDouble() : 1, n.TryGetProperty("active", out var active) && active.GetBoolean())).ToList();
        var edges = graph.GetProperty("edges").EnumerateArray().Select(e => new GraphEdge(
            e.GetProperty("source").GetString() ?? "", e.GetProperty("target").GetString() ?? "", e.GetProperty("relation").GetString() ?? "")).ToList();
        Graph.SetData(new GraphSnapshot { Nodes = nodes, Edges = edges });
    }

    private async Task SendTextAsync(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return;
        SetState("PROCESSING");
        try
        {
            if (!_core.IsConnected && !await _core.EnsureConnectedAsync()) throw new InvalidOperationException("Core desconectado");
            var response = await _core.RequestAsync("user_input", new { text }, timeoutMilliseconds: 30000);
            var answer = response.Payload.GetProperty("text").GetString() ?? "";
            _viewModel.Response = answer; _hud.UpdateState("IDLE", answer);
            await RefreshDashboardAsync();
            if (response.Payload.TryGetProperty("graph", out var graph)) SetGraph(graph);
            ApplyPresentation(response.Payload);
        }
        catch (Exception exc)
        {
            _viewModel.Response = $"Core desconectado: {exc.Message}";
            _hud.UpdateState("ERROR", _viewModel.Response);
        }
        finally { SetState("IDLE"); }
    }

    private void SetState(string state) { _viewModel.State = state; Graph.SetState(state); _hud.UpdateState(state); }
    private void ApplyPresentation(JsonElement payload)
    {
        if (!payload.TryGetProperty("ui", out var ui) || ui.ValueKind != JsonValueKind.Object) return;
        var mode = ui.TryGetProperty("mode", out var modeValue) ? modeValue.GetString() ?? "brain" : "brain";
        if (mode == "brain")
        {
            ContextDrawer.Visibility = Visibility.Collapsed;
            return;
        }
        _viewModel.ContextItems.Clear();
        _viewModel.ContextTitle = ui.TryGetProperty("title", out var title) ? title.GetString() ?? "Contexto" : "Contexto";
        _viewModel.ContextSummary = payload.TryGetProperty("message", out var message) ? message.GetString() ?? "" :
                                    payload.TryGetProperty("text", out var text) ? text.GetString() ?? "" : "";
        var panel = ui.TryGetProperty("panel", out var panelValue) ? panelValue.GetString() ?? "" : "";
        if (payload.TryGetProperty("data", out var data) && data.ValueKind == JsonValueKind.Object)
        {
            if (panel == "today")
            {
                AddObjectArray(data, "tasks", "title", "due_at", "Tarefa");
                AddObjectArray(data, "appointments", "title", "starts_at", "Compromisso");
                AddObjectArray(data, "reminders", "text", "remind_at", "Lembrete");
            }
            else if (panel == "project")
            {
                AddObjectArray(data, "notes", "title", "excerpt", "Nota");
            }
            else if (panel == "automation")
            {
                var name = data.TryGetProperty("name", out var n) ? n.GetString() ?? "Automação" : "Automação";
                var next = data.TryGetProperty("next_run_at", out var nextValue) ? nextValue.GetString() ?? "" : "";
                _viewModel.ContextItems.Add(new ContextItem(name, next));
            }
        }
        else if (panel == "shopping" && data.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in data.EnumerateArray())
                _viewModel.ContextItems.Add(new ContextItem(item.TryGetProperty("text", out var itemText) ? itemText.GetString() ?? "Item" : "Item", ""));
        }
        if (panel == "research" && payload.TryGetProperty("sources", out var sources) && sources.ValueKind == JsonValueKind.Array)
        {
            foreach (var source in sources.EnumerateArray())
            {
                var sourceTitle = source.TryGetProperty("title", out var t) ? t.GetString() ?? "Fonte" : "Fonte";
                var domain = source.TryGetProperty("domain", out var d) ? d.GetString() ?? "" : "";
                var retrieved = source.TryGetProperty("retrieved_at", out var r) ? r.GetString() ?? "" : "";
                _viewModel.ContextItems.Add(new ContextItem(sourceTitle, $"{domain}  {retrieved}".Trim()));
            }
        }
        ContextDrawer.Visibility = Visibility.Visible;
    }

    private void AddObjectArray(JsonElement data, string property, string titleProperty, string detailProperty, string fallback)
    {
        if (!data.TryGetProperty(property, out var items) || items.ValueKind != JsonValueKind.Array) return;
        foreach (var item in items.EnumerateArray())
        {
            var title = item.TryGetProperty(titleProperty, out var titleValue) ? titleValue.GetString() ?? fallback : fallback;
            var detail = item.TryGetProperty(detailProperty, out var detailValue) && detailValue.ValueKind != JsonValueKind.Null
                ? detailValue.GetString() ?? "" : "";
            _viewModel.ContextItems.Add(new ContextItem(title, detail));
        }
    }

    private void CloseContext_Click(object sender, RoutedEventArgs e) => ContextDrawer.Visibility = Visibility.Collapsed;
    private async void Send_Click(object sender, RoutedEventArgs e) { var text = _viewModel.Input; _viewModel.Input = ""; await SendTextAsync(text); }
    private async void CommandBox_KeyDown(object sender, System.Windows.Input.KeyEventArgs e) { if (e.Key == Key.Enter) { e.Handled = true; var text = _viewModel.Input; _viewModel.Input = ""; await SendTextAsync(text); } }
    private void Listen_Click(object sender, RoutedEventArgs e) => _hud.Open(_viewModel.State);
    private void Shortcut_Click(object sender, RoutedEventArgs e) { if (sender is FrameworkElement { Tag: string text }) { _viewModel.Input = text; CommandBox.Focus(); CommandBox.CaretIndex = CommandBox.Text.Length; } }
    private void Header_MouseLeftButtonDown(object sender, MouseButtonEventArgs e) { if (e.ClickCount == 2) ToggleMaximize(); else DragMove(); }
    private void Minimize_Click(object sender, RoutedEventArgs e) => WindowState = WindowState.Minimized;
    private void Maximize_Click(object sender, RoutedEventArgs e) => ToggleMaximize();
    private void ToggleMaximize() => WindowState = WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized;
    private void Close_Click(object sender, RoutedEventArgs e) => HideToTray();

    private void ShowDashboard() { Show(); WindowState = WindowState.Normal; Activate(); Graph.SetPaused(false); }
    private void HideToTray() { Hide(); Graph.SetPaused(true); }
    private void OnClosing(object? sender, CancelEventArgs e) { if (!_exiting) { e.Cancel = true; HideToTray(); } }

    private void RegisterGlobalHotkey()
    {
        var handle = new WindowInteropHelper(this).Handle;
        HwndSource.FromHwnd(handle)?.AddHook(WndProc);
        RegisterHotKey(handle, HotkeyId, 0x0001 | 0x0002, 0x20);
    }

    private IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == 0x0312 && wParam.ToInt32() == HotkeyId) { _hud.Open(_viewModel.State); handled = true; }
        return IntPtr.Zero;
    }

    private async Task ExitAsync()
    {
        if (_exiting) return;
        _exiting = true; _refresh.Stop(); _clock.Stop();
        UnregisterHotKey(new WindowInteropHelper(this).Handle, HotkeyId);
        _tray?.Dispose(); _hud.Close();
        await _core.DisposeAsync();
        System.Windows.Application.Current.Shutdown();
    }

    private void SaveScreenshot(string path)
    {
        var width = Math.Max(1, (int)Math.Ceiling(ActualWidth));
        var height = Math.Max(1, (int)Math.Ceiling(ActualHeight));
        var bitmap = new RenderTargetBitmap(width, height, 96, 96, PixelFormats.Pbgra32);
        bitmap.Render(this);
        var encoder = new PngBitmapEncoder();
        encoder.Frames.Add(BitmapFrame.Create(bitmap));
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        using var stream = File.Create(path);
        encoder.Save(stream);
    }

    [DllImport("user32.dll")] private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);
    [DllImport("user32.dll")] private static extern bool UnregisterHotKey(IntPtr hWnd, int id);
}
