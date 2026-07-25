using System.Net.Http;
using System.Text.Json;

namespace ChzzkNotifier;

/// <summary>치지직 비공식 API (로그인 불필요, 공개 정보만 사용)</summary>
public static class ChzzkApi
{
    private const string ApiBase = "https://api.chzzk.naver.com";

    private static readonly HttpClient Http = CreateClient();

    private static HttpClient CreateClient()
    {
        var client = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
        client.DefaultRequestHeaders.UserAgent.ParseAdd(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36");
        return client;
    }

    public record SearchResult(
        string ChannelId, string ChannelName, string ChannelImageUrl,
        bool VerifiedMark, int FollowerCount, bool OpenLive);

    public static async Task<List<SearchResult>> SearchChannelsAsync(string keyword, int size = 20)
    {
        var url = $"{ApiBase}/service/v1/search/channels" +
                  $"?keyword={Uri.EscapeDataString(keyword)}&offset=0&size={size}&withFirstChannelContent=true";
        using var doc = JsonDocument.Parse(await Http.GetStringAsync(url));
        var results = new List<SearchResult>();
        if (!doc.RootElement.TryGetProperty("content", out var content) ||
            !content.TryGetProperty("data", out var data))
            return results;

        foreach (var item in data.EnumerateArray())
        {
            if (!item.TryGetProperty("channel", out var ch)) continue;
            var id = ch.GetPropertyOrNull("channelId")?.GetString();
            if (string.IsNullOrEmpty(id)) continue;
            results.Add(new SearchResult(
                id,
                ch.GetPropertyOrNull("channelName")?.GetString() ?? "",
                ch.GetPropertyOrNull("channelImageUrl")?.GetString() ?? "",
                ch.GetPropertyOrNull("verifiedMark")?.GetBoolean() ?? false,
                ch.GetPropertyOrNull("followerCount")?.TryGetInt32() ?? 0,
                ch.GetPropertyOrNull("openLive")?.GetBoolean() ?? false));
        }
        return results;
    }

    /// <summary>채널 정보의 openLive로 방송 여부 판단</summary>
    public static async Task<bool> IsLiveAsync(string channelId)
    {
        using var doc = JsonDocument.Parse(
            await Http.GetStringAsync($"{ApiBase}/service/v1/channels/{channelId}"));
        return doc.RootElement.TryGetProperty("content", out var content) &&
               (content.GetPropertyOrNull("openLive")?.GetBoolean() ?? false);
    }

    public record LiveDetail(string Title, string Category);

    /// <summary>방송 제목/카테고리 (실패해도 무방한 부가 정보)</summary>
    public static async Task<LiveDetail> GetLiveDetailAsync(string channelId)
    {
        try
        {
            using var doc = JsonDocument.Parse(
                await Http.GetStringAsync($"{ApiBase}/polling/v2/channels/{channelId}/live-status"));
            if (!doc.RootElement.TryGetProperty("content", out var content))
                return new LiveDetail("", "");
            return new LiveDetail(
                content.GetPropertyOrNull("liveTitle")?.GetString() ?? "",
                content.GetPropertyOrNull("liveCategoryValue")?.GetString() ?? "");
        }
        catch
        {
            return new LiveDetail("", "");
        }
    }

    public static string LiveUrl(string channelId) => $"https://chzzk.naver.com/live/{channelId}";

    private static JsonElement? GetPropertyOrNull(this JsonElement element, string name) =>
        element.TryGetProperty(name, out var value) && value.ValueKind is not JsonValueKind.Null
            ? value : null;

    private static int? TryGetInt32(this JsonElement element) =>
        element.TryGetInt32(out var v) ? v : null;
}
