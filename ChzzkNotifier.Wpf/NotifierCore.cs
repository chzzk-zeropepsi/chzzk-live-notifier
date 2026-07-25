using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Media;
using Microsoft.Win32;

namespace ChzzkNotifier;

/// <summary>페이지들이 공유하는 앱 상태 + 폴링/알림 로직 (탭 전환에도 유지)</summary>
public class NotifierCore : INotifyPropertyChanged
{
    public static NotifierCore Instance { get; } = new();

    public AppConfig Config { get; } = AppConfig.Load();
    public ObservableCollection<FollowItem> FollowItems { get; } = [];
    public ObservableCollection<SearchItem> SearchItems { get; } = [];

    private string _status = "시작 중…";
    public string Status
    {
        get => _status;
        set { _status = value; PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(Status))); }
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    private CancellationTokenSource? _pollDelayCts;
    private bool _started;
    public bool Exiting { get; set; }

    private NotifierCore()
    {
        foreach (var ch in Config.Channels)
            FollowItems.Add(new FollowItem(ch));
    }

    /// <summary>UI 스레드에서 1회만 호출</summary>
    public void Start()
    {
        if (_started) return;
        _started = true;
        _ = PollLoopAsync();
    }

    private async Task PollLoopAsync()
    {
        while (!Exiting)
        {
            await PollOnceAsync();
            _pollDelayCts = new CancellationTokenSource();
            try
            {
                var sec = Math.Clamp(Config.PollIntervalSec, 10, 600);
                await Task.Delay(TimeSpan.FromSeconds(sec), _pollDelayCts.Token);
            }
            catch (TaskCanceledException) { /* 즉시 새로고침 */ }
        }
    }

    private async Task PollOnceAsync()
    {
        foreach (var item in FollowItems.ToList())
        {
            if (Exiting) return;
            try
            {
                var isLive = await ChzzkApi.IsLiveAsync(item.Channel.ChannelId);
                var prev = item.IsLiveState;
                item.IsLiveState = isLive;

                if (isLive)
                {
                    var detail = await ChzzkApi.GetLiveDetailAsync(item.Channel.ChannelId);
                    item.LiveTitle = detail.Title;

                    var wentLive = prev == false;
                    var startupLive = prev == null && Config.NotifyOnStartup;
                    if (wentLive || startupLive)
                        Notify(item.Channel, "🔴 방송을 시작했습니다",
                            string.Join(" · ", new[] { detail.Title, detail.Category }
                                .Where(s => !string.IsNullOrEmpty(s))));
                }
                else
                {
                    item.LiveTitle = "";
                }
            }
            catch (Exception ex)
            {
                Status = $"확인 실패({item.Name}): {ex.Message}";
            }
        }
        Status = $"마지막 확인: {DateTime.Now:HH:mm:ss} (주기 {Config.PollIntervalSec}초)";
    }

    public void RefreshNow() => _pollDelayCts?.Cancel();

    // ---------------- 알림 ----------------

    public void Notify(FollowedChannel channel, string header, string subtitle)
    {
        PlaySound();
        new PopupWindow(channel, header, subtitle,
            Math.Clamp(Config.PopupDurationSec, 2, 60)).ShowPopup();
    }

    public void TestNotification(FollowedChannel? selected)
    {
        var ch = selected
            ?? Config.Channels.FirstOrDefault()
            ?? new FollowedChannel { ChannelName = App.AppTitle };
        Notify(ch, "🔔 알림 테스트 — 클릭하면 방송이 열려요",
            "실제 방송이 켜지면 이렇게 알림이 옵니다.");
        Status = $"{ch.ChannelName} 테스트 알림을 보냈습니다.";
    }

    public void PlaySound()
    {
        try
        {
            string? path = Config.SoundMode switch
            {
                "none" => null,
                "file" when File.Exists(Config.SoundFile) => Config.SoundFile,
                _ => Path.Combine(AppConfig.BaseDir, "notify.wav"),
            };
            if (path is null || !File.Exists(path)) return;
            new SoundPlayer(path).Play();
        }
        catch { /* 소리 실패는 무시 */ }
    }

    // ---------------- 시작 프로그램 ----------------

    private const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string RunName = "ChzzkLiveNotifier";

    public static bool IsAutostartEnabled()
    {
        using var key = Registry.CurrentUser.OpenSubKey(RunKey);
        return key?.GetValue(RunName) is not null;
    }

    public static void SetAutostart(bool enabled)
    {
        using var key = Registry.CurrentUser.OpenSubKey(RunKey, writable: true);
        if (enabled)
            key?.SetValue(RunName, $"\"{Environment.ProcessPath}\" --minimized");
        else
            key?.DeleteValue(RunName, throwOnMissingValue: false);
    }
}
