using System.Windows;
using System.Windows.Media;
using System.Windows.Threading;
using Naty.Desktop.Models;
using WpfColor = System.Windows.Media.Color;
using WpfPoint = System.Windows.Point;
using WpfPen = System.Windows.Media.Pen;

namespace Naty.Desktop.Controls;

public sealed class KnowledgeGraphControl : FrameworkElement
{
    private readonly DispatcherTimer _timer;
    private GraphSnapshot _snapshot = new();
    private double _phase;
    private string _state = "IDLE";

    public KnowledgeGraphControl()
    {
        _timer = new DispatcherTimer(TimeSpan.FromMilliseconds(42), DispatcherPriority.Render, (_, _) =>
        {
            _phase += .08;
            InvalidateVisual();
        }, Dispatcher);
        IsVisibleChanged += (_, _) => UpdateTimer();
    }

    public void SetData(GraphSnapshot snapshot) { _snapshot = snapshot; InvalidateVisual(); }
    public void SetState(string state) { _state = state; UpdateTimer(); InvalidateVisual(); }
    public void SetPaused(bool paused) { if (paused) _timer.Stop(); else UpdateTimer(); }

    private void UpdateTimer()
    {
        var animate = IsVisible && _state is "LISTENING" or "PROCESSING" or "RETRIEVING" or "SPEAKING";
        if (animate && !_timer.IsEnabled) _timer.Start();
        else if (!animate) _timer.Stop();
    }

    protected override void OnRender(DrawingContext dc)
    {
        base.OnRender(dc);
        var center = new WpfPoint(ActualWidth / 2, ActualHeight / 2);
        var nodes = _snapshot.Nodes.Where(n => n.Id != "naty").Take(14).ToList();
        var positions = new Dictionary<string, WpfPoint> { ["naty"] = center };
        var radius = Math.Max(80, Math.Min(ActualWidth, ActualHeight) * .34);
        for (var i = 0; i < nodes.Count; i++)
        {
            var angle = Math.PI * 2 * i / Math.Max(1, nodes.Count) - Math.PI / 2;
            var spread = radius * (.78 + (i % 3) * .1);
            positions[nodes[i].Id] = new WpfPoint(center.X + Math.Cos(angle) * spread, center.Y + Math.Sin(angle) * spread);
        }
        var edgePen = new WpfPen(new SolidColorBrush(WpfColor.FromArgb(115, 23, 70, 108)), 1.2);
        foreach (var edge in _snapshot.Edges)
            if (positions.TryGetValue(edge.Source, out var a) && positions.TryGetValue(edge.Target, out var b)) dc.DrawLine(edgePen, a, b);
        foreach (var node in nodes)
            DrawNode(dc, positions[node.Id], node.Title, NodeColor(node.Type), 5 + Math.Min(5, node.Importance));
        var pulse = _timer.IsEnabled ? 4 + Math.Sin(_phase) * 2 : 4;
        dc.DrawEllipse(null, new WpfPen(new SolidColorBrush(WpfColor.FromArgb(70, 38, 217, 255)), 2), center, 34 + pulse, 34 + pulse);
        DrawNode(dc, center, "NATY", WpfColor.FromRgb(24, 191, 255), 25);
    }

    private static void DrawNode(DrawingContext dc, WpfPoint point, string text, WpfColor color, double radius)
    {
        dc.DrawEllipse(new SolidColorBrush(WpfColor.FromArgb(215, color.R, color.G, color.B)), null, point, radius, radius);
        var label = new FormattedText(text.Length > 18 ? text[..17] + "…" : text,
            System.Globalization.CultureInfo.CurrentUICulture, System.Windows.FlowDirection.LeftToRight,
            new Typeface("Segoe UI Variable"), radius > 20 ? 14 : 11, System.Windows.Media.Brushes.White, 1.0);
        dc.DrawText(label, new WpfPoint(point.X - label.Width / 2, point.Y + radius + 5));
    }

    private static WpfColor NodeColor(string type) => type switch
    {
        "project" or "project_note" => WpfColor.FromRgb(114, 71, 255),
        "memory" or "memory_note" => WpfColor.FromRgb(155, 92, 255),
        "research" => WpfColor.FromRgb(38, 217, 255),
        "service" or "skill" => WpfColor.FromRgb(49, 230, 161),
        "list" => WpfColor.FromRgb(255, 143, 92),
        _ => WpfColor.FromRgb(140, 166, 197),
    };
}
