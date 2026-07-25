using System.Diagnostics;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media.Animation;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

namespace ChzzkNotifier;

/// <summary>스팀 친구 접속 알림 스타일의 우하단 슬라이드 팝업</summary>
public partial class PopupWindow
{
    private const double Gap = 10;
    private const double Margin_ = 14;

    private static readonly List<PopupWindow> Active = [];

    private readonly FollowedChannel _channel;
    private readonly DispatcherTimer _stayTimer;
    private bool _closingAnim;

    public PopupWindow(FollowedChannel channel, string header, string subtitle, int durationSec)
    {
        InitializeComponent();
        _channel = channel;
        NameText.Text = channel.ChannelName;
        HeaderText.Text = header;
        SubtitleText.Text = subtitle;
        SubtitleText.Visibility = string.IsNullOrEmpty(subtitle)
            ? Visibility.Collapsed : Visibility.Visible;

        if (!string.IsNullOrEmpty(channel.ChannelImageUrl))
        {
            try
            {
                Avatar.Source = new BitmapImage(new Uri(channel.ChannelImageUrl));
            }
            catch { /* 이미지 실패는 무시 */ }
        }

        _stayTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(durationSec) };
        _stayTimer.Tick += (_, _) => { _stayTimer.Stop(); FadeOutAndClose(); };
    }

    public void ShowPopup()
    {
        Active.Add(this);
        var (x, y) = TargetPos();
        Left = x + 48;
        Top = y;
        Opacity = 0;
        Show();

        var slide = new DoubleAnimation(x + 48, x, TimeSpan.FromMilliseconds(220))
        { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut } };
        var fade = new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(200));
        BeginAnimation(LeftProperty, slide);
        BeginAnimation(OpacityProperty, fade);
        _stayTimer.Start();
    }

    private (double x, double y) TargetPos()
    {
        var wa = SystemParameters.WorkArea;
        var idx = Active.IndexOf(this);
        var x = wa.Right - Width - Margin_;
        var y = wa.Bottom - Margin_ - (idx + 1) * Height - idx * Gap;
        return (x, y);
    }

    private void FadeOutAndClose()
    {
        if (_closingAnim) return;
        _closingAnim = true;
        var fade = new DoubleAnimation(0, TimeSpan.FromMilliseconds(350));
        fade.Completed += (_, _) => ClosePopup();
        BeginAnimation(OpacityProperty, fade);
    }

    private void ClosePopup()
    {
        _stayTimer.Stop();
        Active.Remove(this);
        Close();
        foreach (var p in Active)   // 남은 팝업 아래로 정렬
        {
            var (x, y) = p.TargetPos();
            p.BeginAnimation(LeftProperty, null);
            p.Left = x;
            p.Top = y;
        }
    }

    private void Card_Click(object sender, MouseButtonEventArgs e)
    {
        if (!string.IsNullOrEmpty(_channel.ChannelId))
            Process.Start(new ProcessStartInfo(ChzzkApi.LiveUrl(_channel.ChannelId))
            { UseShellExecute = true });
        ClosePopup();
    }

    private void Close_Click(object sender, MouseButtonEventArgs e)
    {
        e.Handled = true;
        ClosePopup();
    }
}
