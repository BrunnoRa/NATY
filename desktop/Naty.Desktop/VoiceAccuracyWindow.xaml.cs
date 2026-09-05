using System.Text.Json;
using System.Windows;
using System.Windows.Threading;
using Naty.Desktop.Services;

namespace Naty.Desktop;

public partial class VoiceAccuracyWindow : Window
{
    private static readonly string[] Phrases =
    {
        "Naty, pesquisa as principais novidades sobre inteligência artificial hoje.",
        "E qual dessas é mais importante?",
        "Me lembra amanhã às três de falar com o professor.",
        "Todo domingo às sete da noite me lembra de planejar a semana.",
        "O que você sabe sobre meu projeto?",
        "Abre Spotify.",
        "Próxima música.",
        "Quero analisar profundamente minha carreira.",
        "Prefiro respostas mais curtas pela manhã.",
        "Como está a sincronização dos meus dispositivos?",
    };

    private readonly CoreClient _core;
    private readonly DispatcherTimer _poll = new() { Interval = TimeSpan.FromMilliseconds(180) };
    private int _index;
    private bool _recording;

    public VoiceAccuracyWindow(CoreClient core)
    {
        InitializeComponent();
        _core = core;
        _poll.Tick += Poll_Tick;
        Closing += async (_, _) =>
        {
            _poll.Stop();
            if (_recording)
            {
                try { await _core.RequestAsync("voice_precision_stop", timeoutMilliseconds: 1500); }
                catch { }
            }
        };
        Results.Text = "# | Frase esperada | Transcrição | WER | Latência\n";
        ShowCurrentPhrase();
    }

    private void ShowCurrentPhrase()
    {
        if (_index >= Phrases.Length)
        {
            ProgressText.Text = "10 de 10 — concluído";
            ExpectedText.Text = "Teste concluído. Copie os resultados para o registro de aceite.";
            LiveStatus.Text = "Nenhuma frase foi enviada à assistente.";
            RecordButton.IsEnabled = false;
            return;
        }
        ProgressText.Text = $"Frase {_index + 1} de {Phrases.Length}";
        ExpectedText.Text = Phrases[_index];
        LiveStatus.Text = "Clique em Gravar frase e leia o texto acima.";
        RecordButton.IsEnabled = true;
    }

    private async void Record_Click(object sender, RoutedEventArgs e)
    {
        if (_recording || _index >= Phrases.Length) return;
        try
        {
            _recording = true;
            RecordButton.IsEnabled = false;
            LiveStatus.Text = "Ouvindo…";
            await _core.RequestAsync("voice_precision_start", new { expected = Phrases[_index] }, timeoutMilliseconds: 3000);
            _poll.Start();
        }
        catch (Exception exc)
        {
            _recording = false;
            RecordButton.IsEnabled = true;
            LiveStatus.Text = $"Teste indisponível: {exc.Message}";
        }
    }

    private async void Poll_Tick(object? sender, EventArgs e)
    {
        try
        {
            var payload = (await _core.RequestAsync("voice_precision_status", timeoutMilliseconds: 1500)).Payload;
            var active = payload.TryGetProperty("active", out var activeValue) && activeValue.GetBoolean();
            var state = Text(payload, "state", "IDLE");
            if (active)
            {
                var level = payload.TryGetProperty("level", out var levelValue) && levelValue.ValueKind == JsonValueKind.Number
                    ? levelValue.GetDouble() * 100 : 0;
                LiveStatus.Text = $"{StateLabel(state)} · nível {level:0}%";
                return;
            }
            _poll.Stop();
            _recording = false;
            if (state == "COMPLETE")
            {
                var transcription = Text(payload, "transcription").Replace("|", "/");
                var wer = payload.TryGetProperty("wer", out var werValue) && werValue.ValueKind == JsonValueKind.Number
                    ? $"{werValue.GetDouble():P1}" : "—";
                var latency = payload.TryGetProperty("latency_ms", out var latencyValue) && latencyValue.ValueKind == JsonValueKind.Number
                    ? $"{latencyValue.GetDouble():0} ms" : "—";
                Results.AppendText($"{_index + 1} | {Phrases[_index]} | {transcription} | {wer} | {latency}\n");
                Results.ScrollToEnd();
                _index++;
                ShowCurrentPhrase();
            }
            else
            {
                LiveStatus.Text = Text(payload, "error", "Não foi possível concluir esta frase.");
                RecordButton.IsEnabled = true;
            }
        }
        catch (Exception exc)
        {
            _poll.Stop();
            _recording = false;
            RecordButton.IsEnabled = true;
            LiveStatus.Text = $"Falha ao consultar o teste: {exc.Message}";
        }
    }

    private static string Text(JsonElement root, string name, string fallback = "") =>
        root.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? fallback : fallback;
    private static string StateLabel(string state) => state switch
    {
        "LISTENING" => "Ouvindo", "TRANSCRIBING" => "Transcrevendo", _ => state
    };
    private void Copy_Click(object sender, RoutedEventArgs e)
    {
        System.Windows.Clipboard.SetText(Results.Text);
        LiveStatus.Text = "Resultados copiados.";
    }
    private void Close_Click(object sender, RoutedEventArgs e) => Close();
}
