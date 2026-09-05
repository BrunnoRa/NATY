using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using Naty.Desktop.Models;

namespace Naty.Desktop.ViewModels;

public sealed class MainViewModel : INotifyPropertyChanged
{
    private string _connection = "Core desconectado";
    private string _state = "IDLE";
    private string _clock = "--:--";
    private string _response = "Olá. Eu sou a Naty. O Core está sendo iniciado.";
    private string _input = "";
    private string _ram = "—";
    private string _cpu = "—";
    private string _contextTitle = "";
    private string _contextSummary = "";

    public string Connection { get => _connection; set => Set(ref _connection, value); }
    public string State { get => _state; set => Set(ref _state, value); }
    public string Clock { get => _clock; set => Set(ref _clock, value); }
    public string Response { get => _response; set => Set(ref _response, value); }
    public string Input { get => _input; set => Set(ref _input, value); }
    public string Ram { get => _ram; set => Set(ref _ram, value); }
    public string Cpu { get => _cpu; set => Set(ref _cpu, value); }
    public string ContextTitle { get => _contextTitle; set => Set(ref _contextTitle, value); }
    public string ContextSummary { get => _contextSummary; set => Set(ref _contextSummary, value); }
    public ObservableCollection<ProviderStatus> Providers { get; } = [];
    public ObservableCollection<TaskItem> Tasks { get; } = [];
    public ObservableCollection<ContextItem> ContextItems { get; } = [];

    public event PropertyChangedEventHandler? PropertyChanged;
    private void Set<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return;
        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
    }
}
