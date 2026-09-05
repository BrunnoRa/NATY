using System.Windows;
using System.Windows.Input;

namespace Naty.Desktop;

public partial class MiniHud : Window
{
    public event Func<string, Task>? Submitted;
    public event Action? ExpandRequested;

    public MiniHud()
    {
        InitializeComponent();
        Deactivated += (_, _) => { if (!InputBox.IsKeyboardFocusWithin) Hide(); };
    }

    public void Open(string state = "IDLE")
    {
        StateText.Text = state;
        Left = SystemParameters.WorkArea.Right - Width - 28;
        Top = SystemParameters.WorkArea.Bottom - Height - 28;
        Show(); Activate(); InputBox.Focus();
    }

    public void UpdateState(string state, string? response = null)
    {
        StateText.Text = state;
        if (!string.IsNullOrWhiteSpace(response)) ResponseText.Text = response;
    }

    private async void InputBox_KeyDown(object sender, System.Windows.Input.KeyEventArgs e)
    {
        if (e.Key == Key.Escape) { Hide(); return; }
        if (e.Key != Key.Enter || string.IsNullOrWhiteSpace(InputBox.Text)) return;
        var text = InputBox.Text.Trim(); InputBox.Clear();
        if (Submitted is not null) await Submitted.Invoke(text);
    }

    private void Expand_Click(object sender, RoutedEventArgs e) => ExpandRequested?.Invoke();
}
