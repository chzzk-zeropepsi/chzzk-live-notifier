using System.IO;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;

namespace ChzzkNotifier;

public partial class SettingsPage : Page
{
    private readonly NotifierCore _core = NotifierCore.Instance;
    private readonly bool _uiReady;

    public SettingsPage()
    {
        InitializeComponent();
        PollBox.Value = _core.Config.PollIntervalSec;
        DurBox.Value = _core.Config.PopupDurationSec;
        SoundCombo.SelectedIndex = _core.Config.SoundMode switch
        { "none" => 1, "file" => 2, _ => 0 };
        UpdateSoundLabel();
        StartupNotifyToggle.IsChecked = _core.Config.NotifyOnStartup;
        AutostartToggle.IsChecked = NotifierCore.IsAutostartEnabled();
        _uiReady = true;
    }

    private void UpdateSoundLabel()
    {
        SoundFileLabel.Text = _core.Config.SoundMode switch
        {
            "none" => "무음",
            "file" when !string.IsNullOrEmpty(_core.Config.SoundFile) =>
                Path.GetFileName(_core.Config.SoundFile),
            _ => "기본 알림음 (내장)",
        };
    }

    private void Numbers_Changed(object sender, RoutedEventArgs e)
    {
        if (!_uiReady) return;
        _core.Config.PollIntervalSec = (int)Math.Clamp(PollBox.Value ?? 30, 10, 600);
        _core.Config.PopupDurationSec = (int)Math.Clamp(DurBox.Value ?? 8, 2, 60);
        PollBox.Value = _core.Config.PollIntervalSec;
        DurBox.Value = _core.Config.PopupDurationSec;
        _core.Config.Save();
        _core.Status = $"설정 저장됨 — 주기 {_core.Config.PollIntervalSec}초, " +
                       $"팝업 {_core.Config.PopupDurationSec}초";
    }

    private void SoundCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_uiReady) return;
        var mode = SoundCombo.SelectedIndex switch { 1 => "none", 2 => "file", _ => "default" };
        if (mode == "file" && string.IsNullOrEmpty(_core.Config.SoundFile))
        {
            PickSoundFile();
            return;
        }
        _core.Config.SoundMode = mode;
        _core.Config.Save();
        UpdateSoundLabel();
    }

    private void PickSoundButton_Click(object sender, RoutedEventArgs e) => PickSoundFile();

    private void PickSoundFile()
    {
        var dialog = new OpenFileDialog
        {
            Title = "알림 소리로 쓸 WAV 파일 선택",
            Filter = "WAV 파일|*.wav",
        };
        if (dialog.ShowDialog() != true)
        {
            SoundCombo.SelectedIndex = _core.Config.SoundMode switch
            { "none" => 1, "file" => 2, _ => 0 };
            return;
        }
        _core.Config.SoundMode = "file";
        _core.Config.SoundFile = dialog.FileName;
        _core.Config.Save();
        SoundCombo.SelectedIndex = 2;
        UpdateSoundLabel();
    }

    private void PreviewSoundButton_Click(object sender, RoutedEventArgs e) => _core.PlaySound();

    private void StartupNotifyToggle_Click(object sender, RoutedEventArgs e)
    {
        if (!_uiReady) return;
        _core.Config.NotifyOnStartup = StartupNotifyToggle.IsChecked == true;
        _core.Config.Save();
    }

    private void AutostartToggle_Click(object sender, RoutedEventArgs e)
    {
        if (!_uiReady) return;
        try
        {
            NotifierCore.SetAutostart(AutostartToggle.IsChecked == true);
            _core.Status = "부팅 시 자동 실행: " +
                (AutostartToggle.IsChecked == true ? "켬" : "끔");
        }
        catch (Exception ex)
        {
            AutostartToggle.IsChecked = NotifierCore.IsAutostartEnabled();
            _core.Status = $"시작 프로그램 등록 실패: {ex.Message}";
        }
    }
}
