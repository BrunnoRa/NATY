using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Text;
using System.Text.Json;
using Naty.Desktop.Models;

namespace Naty.Desktop.Services;

public sealed class CoreClient : IAsyncDisposable
{
    public const string PipeName = "Naty.Core.v1";
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    private readonly SemaphoreSlim _requestLock = new(1, 1);
    private Process? _coreProcess;
    public bool IsConnected { get; private set; }
    public event Action<bool>? ConnectionChanged;

    public async Task<bool> EnsureConnectedAsync(CancellationToken cancellationToken = default)
    {
        if (await PingAsync(cancellationToken)) return true;
        StartCore();
        for (var attempt = 0; attempt < 24; attempt++)
        {
            await Task.Delay(250, cancellationToken);
            if (await PingAsync(cancellationToken)) return true;
        }
        SetConnected(false);
        return false;
    }

    public async Task<PipeEnvelope> RequestAsync(string type, object? payload = null,
        int timeoutMilliseconds = 5000, CancellationToken cancellationToken = default)
    {
        await _requestLock.WaitAsync(cancellationToken);
        try
        {
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(timeoutMilliseconds);
            var id = Guid.NewGuid().ToString("N");
            var message = JsonSerializer.Serialize(new { protocol = 1, type, request_id = id, payload = payload ?? new { } }, Json);
            await using var pipe = new NamedPipeClientStream(".", PipeName, PipeDirection.InOut, PipeOptions.Asynchronous);
            await pipe.ConnectAsync(timeout.Token);
            using var reader = new StreamReader(pipe, new UTF8Encoding(false), false, 4096, leaveOpen: true);
            await using var writer = new StreamWriter(pipe, new UTF8Encoding(false), 4096, leaveOpen: true) { AutoFlush = true };
            await writer.WriteLineAsync(message.AsMemory(), timeout.Token);
            var raw = await reader.ReadLineAsync(timeout.Token) ?? throw new IOException("Core encerrou a conexão sem resposta.");
            var response = JsonSerializer.Deserialize<PipeEnvelope>(raw, Json) ?? throw new InvalidDataException("Resposta vazia do Core.");
            if (response.Protocol != 1 || response.RequestId != id) throw new InvalidDataException("Resposta IPC incompatível.");
            if (response.Type == "error")
            {
                var reason = response.Payload.TryGetProperty("message", out var value) ? value.GetString() : "Erro do Core.";
                throw new InvalidOperationException(reason);
            }
            SetConnected(true);
            return response;
        }
        catch
        {
            SetConnected(false);
            throw;
        }
        finally
        {
            _requestLock.Release();
        }
    }

    private async Task<bool> PingAsync(CancellationToken cancellationToken)
    {
        try
        {
            var response = await RequestAsync("ping", timeoutMilliseconds: 700, cancellationToken: cancellationToken);
            return response.Type == "pong";
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested) { return false; }
        catch (IOException) { return false; }
        catch (TimeoutException) { return false; }
    }

    private void StartCore()
    {
        if (_coreProcess is { HasExited: false }) return;
        var packagedCore = Path.Combine(AppContext.BaseDirectory, "Core", "Naty.Core.exe");
        if (File.Exists(packagedCore))
        {
            _coreProcess = Process.Start(new ProcessStartInfo
            {
                FileName = packagedCore,
                Arguments = $"--pipe {PipeName}",
                WorkingDirectory = Path.GetDirectoryName(packagedCore)!,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden,
            });
            return;
        }
        var root = FindProjectRoot();
        if (root is null) return;
        var python = Path.Combine(root, ".venv", "Scripts", "pythonw.exe");
        if (!File.Exists(python)) python = Path.Combine(root, ".venv", "Scripts", "python.exe");
        if (!File.Exists(python)) return;
        _coreProcess = Process.Start(new ProcessStartInfo
        {
            FileName = python,
            Arguments = $"\"{Path.Combine(root, "core_host.py")}\" --pipe {PipeName}",
            WorkingDirectory = root,
            UseShellExecute = false,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden,
        });
    }

    private static string? FindProjectRoot()
    {
        foreach (var start in new[] { AppContext.BaseDirectory, Environment.CurrentDirectory })
        {
            var directory = new DirectoryInfo(start);
            while (directory is not null)
            {
                if (File.Exists(Path.Combine(directory.FullName, "core_host.py"))) return directory.FullName;
                directory = directory.Parent;
            }
        }
        return null;
    }

    private void SetConnected(bool connected)
    {
        if (IsConnected == connected) return;
        IsConnected = connected;
        ConnectionChanged?.Invoke(connected);
    }

    public async ValueTask DisposeAsync()
    {
        if (_coreProcess is { HasExited: false } && IsConnected)
        {
            try { await RequestAsync("shutdown", timeoutMilliseconds: 1500); }
            catch { }
        }
        if (_coreProcess is { HasExited: false })
        {
            if (!_coreProcess.WaitForExit(1500)) _coreProcess.Kill(entireProcessTree: true);
        }
        _coreProcess?.Dispose();
        _requestLock.Dispose();
    }
}
