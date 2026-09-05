using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using Naty.Desktop.Services;

namespace Naty.Desktop;

public partial class WorkspaceWindow : Window
{
    private readonly CoreClient _core;
    private int? _workspaceId;
    private sealed record WorkspaceRow(int Id, string Name, string Aliases, string Apps, string Urls, int? FocusMinutes, bool Enabled);

    public WorkspaceWindow(CoreClient core)
    {
        InitializeComponent();
        _core = core;
        Loaded += async (_, _) => await LoadAsync();
    }

    private async Task LoadAsync()
    {
        try
        {
            var payload = (await _core.RequestAsync("workspace_list")).Payload;
            var rows = new List<WorkspaceRow>();
            foreach (var item in payload.GetProperty("workspaces").EnumerateArray())
            {
                var aliases = item.GetProperty("aliases").EnumerateArray().Select(value => value.GetString() ?? "");
                var actions = item.GetProperty("actions").EnumerateArray().ToList();
                var apps = actions.Where(ActionIs("OPEN_APP")).Select(ActionValue);
                var urls = actions.Where(ActionIs("OPEN_URL")).Select(ActionValue);
                var focus = item.TryGetProperty("focus_minutes", out var focusValue) && focusValue.ValueKind == JsonValueKind.Number ? focusValue.GetInt32() : (int?)null;
                rows.Add(new WorkspaceRow(item.GetProperty("id").GetInt32(), item.GetProperty("name").GetString() ?? "Modo",
                    string.Join(", ", aliases), string.Join(", ", apps), string.Join("\n", urls), focus,
                    item.TryGetProperty("enabled", out var enabled) && enabled.GetBoolean()));
            }
            WorkspaceList.ItemsSource = rows;
            Status.Text = rows.Count == 0 ? "Crie seu primeiro modo; nenhuma ação é executada ao salvar." : $"{rows.Count} modo(s) configurado(s).";
        }
        catch (Exception exc) { Status.Text = $"Não foi possível carregar: {exc.Message}"; }
    }

    private static Func<JsonElement, bool> ActionIs(string type) => item => item.TryGetProperty("type", out var value) && value.GetString() == type;
    private static string ActionValue(JsonElement item) => item.TryGetProperty("value", out var value) ? value.GetString() ?? "" : "";
    private void WorkspaceList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (WorkspaceList.SelectedItem is not WorkspaceRow row) return;
        _workspaceId = row.Id; WorkspaceName.Text = row.Name; Aliases.Text = row.Aliases; Apps.Text = row.Apps;
        Urls.Text = row.Urls; FocusMinutes.Text = row.FocusMinutes?.ToString() ?? ""; Enabled.IsChecked = row.Enabled;
    }
    private void New_Click(object sender, RoutedEventArgs e)
    {
        _workspaceId = null; WorkspaceList.SelectedItem = null; WorkspaceName.Text = Aliases.Text = Apps.Text = Urls.Text = FocusMinutes.Text = "";
        Enabled.IsChecked = true; Status.Text = "Novo modo.";
    }
    private async void Save_Click(object sender, RoutedEventArgs e)
    {
        var actions = Apps.Text.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(value => new Dictionary<string, object> { ["type"] = "OPEN_APP", ["value"] = value.ToLowerInvariant() }).ToList();
        actions.AddRange(Urls.Text.Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(value => new Dictionary<string, object> { ["type"] = "OPEN_URL", ["value"] = value }));
        int? focus = int.TryParse(FocusMinutes.Text, out var minutes) ? minutes : null;
        if (focus is not null) actions.Add(new Dictionary<string, object> { ["type"] = "START_TIMER", ["minutes"] = focus.Value });
        var aliases = Aliases.Text.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        try
        {
            var response = await _core.RequestAsync("workspace_save", new { workspace_id = _workspaceId, name = WorkspaceName.Text, aliases, actions, focus_minutes = focus, enabled = Enabled.IsChecked == true });
            Status.Text = response.Payload.GetProperty("message").GetString() ?? "Modo salvo.";
            await LoadAsync();
        }
        catch (Exception exc) { Status.Text = $"Não foi possível salvar: {exc.Message}"; }
    }
    private async void Activate_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var response = await _core.RequestAsync("workspace_activate", new { name = WorkspaceName.Text });
            Status.Text = response.Payload.GetProperty("message").GetString() ?? "Modo ativado.";
        }
        catch (Exception exc) { Status.Text = $"Não foi possível ativar: {exc.Message}"; }
    }
    private void Close_Click(object sender, RoutedEventArgs e) => Close();
}
