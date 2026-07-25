using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace ChzzkNotifier;

public class FollowedChannel
{
    [JsonPropertyName("channelId")] public string ChannelId { get; set; } = "";
    [JsonPropertyName("channelName")] public string ChannelName { get; set; } = "";
    [JsonPropertyName("channelImageUrl")] public string ChannelImageUrl { get; set; } = "";
}

/// <summary>config.json — 파이썬 버전과 같은 스키마</summary>
public class AppConfig
{
    [JsonPropertyName("poll_interval_sec")] public int PollIntervalSec { get; set; } = 30;
    [JsonPropertyName("notify_on_startup")] public bool NotifyOnStartup { get; set; } = false;
    [JsonPropertyName("use_windows_toast")] public bool UseWindowsToast { get; set; } = false;
    [JsonPropertyName("popup_duration_sec")] public int PopupDurationSec { get; set; } = 8;
    [JsonPropertyName("sound_mode")] public string SoundMode { get; set; } = "default";
    [JsonPropertyName("sound_file")] public string SoundFile { get; set; } = "";
    [JsonPropertyName("channels")] public List<FollowedChannel> Channels { get; set; } = [];

    public static string BaseDir => AppContext.BaseDirectory;
    private static string ConfigPath => Path.Combine(BaseDir, "config.json");

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    public static AppConfig Load()
    {
        try
        {
            if (File.Exists(ConfigPath))
                return JsonSerializer.Deserialize<AppConfig>(
                    File.ReadAllText(ConfigPath)) ?? new AppConfig();
        }
        catch { /* 손상된 설정은 기본값으로 */ }
        return new AppConfig();
    }

    public void Save()
    {
        File.WriteAllText(ConfigPath, JsonSerializer.Serialize(this, JsonOptions));
    }
}
