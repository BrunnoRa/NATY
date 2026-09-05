using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using Naty.Desktop.Services;
using WpfComboBox = System.Windows.Controls.ComboBox;
using WpfComboBoxItem = System.Windows.Controls.ComboBoxItem;
using WpfTextBox = System.Windows.Controls.TextBox;

namespace Naty.Desktop;

public partial class SettingsWindow : Window
{
    private readonly CoreClient _core;
    private string _memoryFolder = "";
    private string _evolutionPath = "";
    private string _conflictsFolder = "";
    private string _technicalDetails = "Execute o diagnóstico primeiro.";

    public SettingsWindow(CoreClient core)
    {
        InitializeComponent();
        _core = core;
        Loaded += async (_, _) => await LoadSettingsAsync();
    }

    private static string String(JsonElement root, string name, string fallback = "") =>
        root.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() ?? fallback : fallback;
    private static bool Bool(JsonElement root, string name, bool fallback = false) =>
        root.TryGetProperty(name, out var value) && value.ValueKind is JsonValueKind.True or JsonValueKind.False ? value.GetBoolean() : fallback;
    private static int Int(JsonElement root, string name, int fallback = 0) =>
        root.TryGetProperty(name, out var value) && value.TryGetInt32(out var parsed) ? parsed : fallback;
    private static void Select(WpfComboBox combo, string value) => combo.SelectedIndex = Math.Max(0,
        combo.Items.Cast<WpfComboBoxItem>().ToList().FindIndex(item => Equals(item.Content?.ToString(), value)));
    private static string Selected(WpfComboBox combo) => (combo.SelectedItem as WpfComboBoxItem)?.Content?.ToString() ?? "";

    private async Task LoadSettingsAsync()
    {
        try
        {
            var root = (await _core.RequestAsync("settings_get")).Payload;
            StartWithWindows.IsChecked = Bool(root, "start_with_windows"); CloseToTray.IsChecked = Bool(root, "close_to_tray", true);
            DailyBriefing.IsChecked = Bool(root, "daily_briefing_enabled"); DailyBriefingTime.Text = String(root, "daily_briefing_time", "08:00");
            Hotkey.Text = String(root, "hotkey"); Select(InterfaceLanguage, String(root, "language", "pt-BR"));
            Microphone.Text = String(root, "microphone_name", $"Dispositivo {Int(root, "microphone_device", -1)}");
            Select(SttProvider, String(root, "stt_provider", "whisper_cpp")); WhisperModel.Text = String(root, "whisper_model_path");
            Select(TtsProvider, String(root, "tts_provider", "sapi")); PiperModel.Text = String(root, "piper_model_path");
            VoiceRate.Text = Int(root, "voice_rate").ToString(); VoiceVolume.Text = Int(root, "voice_volume", 100).ToString(); Followup.Text = Int(root, "conversation_followup_seconds", 8).ToString();
            GoogleEnabled.IsChecked = Bool(root, "google_enabled"); ChatGptHandoff.IsChecked = Bool(root, "chatgpt_handoff_enabled", true);
            ObsidianEnabled.IsChecked = Bool(root, "obsidian_enabled"); ObsidianVault.Text = String(root, "obsidian_vault_path"); NatyObsidian.Text = String(root, "naty_obsidian_path");
            SyncEnabled.IsChecked = Bool(root, "sync_enabled"); SyncFolder.Text = String(root, "sync_folder"); DeviceName.Text = String(root, "device_name");
            Select(LearningMode, String(root, "learning_mode", "assisted")); Select(Proactivity, String(root, "proactivity_level", "important")); PrivacyMode.IsChecked = Bool(root, "privacy_mode", true);
            ApplyRuntime(root.GetProperty("runtime")); StatusText.Text = "Configurações carregadas";
        }
        catch (Exception exc) { StatusText.Text = $"Erro: {exc.Message}"; }
    }

    private void ApplyRuntime(JsonElement runtime)
    {
        GoogleStatus.Text = RuntimeLabel(String(runtime, "google")); ObsidianStatus.Text = RuntimeLabel(String(runtime, "obsidian"));
        _memoryFolder = String(runtime, "memory_folder"); _evolutionPath = String(runtime, "evolution_path");
        var sync = runtime.GetProperty("sync"); var state = String(sync, "status", "offline");
        DeviceId.Text = String(sync, "device_id", "Será criado ao habilitar"); SyncStatus.Text = RuntimeLabel(state);
        LastSync.Text = String(sync, "last_sync", "Ainda não executado");
        var pending = Int(sync, "pending"); var conflicts = Int(sync, "conflicts"); SyncCounts.Text = $"{pending} pendente(s) · {conflicts} conflito(s)";
        _conflictsFolder = string.IsNullOrWhiteSpace(SyncFolder.Text) ? "" : Path.Combine(SyncFolder.Text, "conflicts");
        AboutStatus.Text = $"Desktop: OK\nCore/Pipe: OK\nWhisper/TTS: {RuntimeLabel(String(runtime, "voice"))}\nGoogle: {GoogleStatus.Text}\nObsidian: {ObsidianStatus.Text}\nSync: {SyncStatus.Text}";
    }

    private static string RuntimeLabel(string state) => state switch { "online" or "updated" => "OK", "conflict" => "Conflito", "attention" => "Atenção", "off" or "offline" => "Não configurado / offline", _ => state };
    private static int Parsed(WpfTextBox box, int fallback) => int.TryParse(box.Text, out var value) ? value : fallback;

    private async void Save_Click(object sender, RoutedEventArgs e)
    {
        var values = new Dictionary<string, object> {
            ["start_with_windows"] = StartWithWindows.IsChecked == true, ["close_to_tray"] = CloseToTray.IsChecked == true,
            ["daily_briefing_enabled"] = DailyBriefing.IsChecked == true, ["daily_briefing_time"] = DailyBriefingTime.Text.Trim(),
            ["hotkey"] = Hotkey.Text.Trim(), ["language"] = Selected(InterfaceLanguage), ["stt_provider"] = Selected(SttProvider),
            ["whisper_model_path"] = WhisperModel.Text.Trim(), ["tts_provider"] = Selected(TtsProvider), ["piper_model_path"] = PiperModel.Text.Trim(),
            ["voice_rate"] = Parsed(VoiceRate, 0), ["voice_volume"] = Math.Clamp(Parsed(VoiceVolume, 100), 0, 100),
            ["conversation_followup_seconds"] = Math.Max(0, Parsed(Followup, 8)), ["google_enabled"] = GoogleEnabled.IsChecked == true,
            ["chatgpt_handoff_enabled"] = ChatGptHandoff.IsChecked == true, ["obsidian_enabled"] = ObsidianEnabled.IsChecked == true,
            ["obsidian_vault_path"] = ObsidianVault.Text.Trim(), ["naty_obsidian_path"] = NatyObsidian.Text.Trim(),
            ["sync_enabled"] = SyncEnabled.IsChecked == true, ["sync_folder"] = SyncFolder.Text.Trim(), ["device_name"] = DeviceName.Text.Trim(),
            ["learning_mode"] = Selected(LearningMode), ["proactivity_level"] = Selected(Proactivity), ["privacy_mode"] = PrivacyMode.IsChecked == true,
        };
        try { await _core.RequestAsync("settings_save", values); StatusText.Text = "Salvo. Reinicie para aplicar mudanças de inicialização e sync."; }
        catch (Exception exc) { StatusText.Text = $"Não foi possível salvar: {exc.Message}"; }
    }

    private async void VoiceTest_Click(object sender, RoutedEventArgs e)
    {
        StatusText.Text = "Iniciando teste pelo pipeline de voz atual…";
        try { await _core.RequestAsync("voice_start", timeoutMilliseconds: 3000); StatusText.Text = "Teste iniciado; fale com a NATY."; }
        catch (Exception exc) { StatusText.Text = $"Teste indisponível: {exc.Message}"; }
    }
    private void PrecisionTest_Click(object sender, RoutedEventArgs e)
    {
        new VoiceAccuracyWindow(_core) { Owner = this }.ShowDialog();
        StatusText.Text = "Teste de precisão encerrado";
    }
    private async void SyncNow_Click(object sender, RoutedEventArgs e) { try { var result = await _core.RequestAsync("sync_now"); SyncStatus.Text = RuntimeLabel(String(result.Payload, "status")); } catch (Exception exc) { StatusText.Text = exc.Message; } }
    private async void RunDiagnostics_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            StatusText.Text = "Executando diagnóstico…";
            var hotkey = (Owner as MainWindow)?.HotkeyStatus ?? "unknown";
            var report = (await _core.RequestAsync("diagnostics", new { hotkey })).Payload;
            var display = new List<string>(); var technical = new List<string>();
            foreach (var item in report.GetProperty("items").EnumerateArray())
            {
                var name = String(item, "name"); var state = String(item, "state"); var message = String(item, "message");
                display.Add($"{name}: {StateLabel(state)} — {message}");
                technical.Add($"{name} | {state} | {message} | {String(item, "technical")}");
            }
            AboutStatus.Text = string.Join("\n", display);
            _technicalDetails = $"NATY diagnóstico {String(report, "generated_at")}\n" + string.Join("\n", technical);
            StatusText.Text = "Diagnóstico concluído";
        }
        catch (Exception exc) { StatusText.Text = $"Diagnóstico indisponível: {exc.Message}"; }
    }
    private static string StateLabel(string state) => state switch { "ok" => "OK", "not_configured" => "Não configurado", "warning" => "Aviso", "error" => "Erro", _ => state };
    private void CopyDiagnostics_Click(object sender, RoutedEventArgs e) { System.Windows.Clipboard.SetText(_technicalDetails); StatusText.Text = "Detalhes técnicos copiados"; }
    private void OpenConflicts_Click(object sender, RoutedEventArgs e) => OpenPath(_conflictsFolder);
    private void OpenMemory_Click(object sender, RoutedEventArgs e) => OpenPath(_memoryFolder);
    private void OpenEvolution_Click(object sender, RoutedEventArgs e) => OpenPath(_evolutionPath);
    private void Workspaces_Click(object sender, RoutedEventArgs e) => new WorkspaceWindow(_core) { Owner = this }.ShowDialog();
    private static void OpenPath(string path) { if (!string.IsNullOrWhiteSpace(path) && (Directory.Exists(path) || File.Exists(path))) Process.Start(new ProcessStartInfo(path) { UseShellExecute = true }); }
    private void Cancel_Click(object sender, RoutedEventArgs e) => Close();
}
