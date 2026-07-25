using System.ComponentModel;

namespace ChzzkNotifier;

/// <summary>검색 결과 한 줄</summary>
public class SearchItem(ChzzkApi.SearchResult r)
{
    public ChzzkApi.SearchResult Result { get; } = r;
    public string ImageUrl => Result.ChannelImageUrl;
    public string DisplayName => Result.ChannelName + (Result.VerifiedMark ? " ✔" : "");
    public string FollowerText => $"팔로워 {Result.FollowerCount:N0}";
    public string LiveMark => Result.OpenLive ? "🔴" : "";
}

/// <summary>알림 목록 한 줄 (방송 상태 변경 시 UI 갱신)</summary>
public class FollowItem(FollowedChannel ch) : INotifyPropertyChanged
{
    public FollowedChannel Channel { get; } = ch;
    public string Name => Channel.ChannelName;
    public string ImageUrl => Channel.ChannelImageUrl;

    private bool? _isLiveState;   // null = 아직 확인 전
    private string _liveTitle = "";

    public bool? IsLiveState
    {
        get => _isLiveState;
        set
        {
            _isLiveState = value;
            Notify(nameof(IsLive)); Notify(nameof(Status)); Notify(nameof(ActivityText));
        }
    }

    public bool IsLive => _isLiveState == true;
    public string Status => _isLiveState switch
    {
        true => "🔴 LIVE",
        false => "⚫ 오프라인",
        null => "확인 중…",
    };

    public string LiveTitle
    {
        get => _liveTitle;
        set { _liveTitle = value; Notify(nameof(LiveTitle)); Notify(nameof(ActivityText)); }
    }

    /// <summary>디스코드 멤버 목록처럼 이름 아래에 표시할 활동 텍스트</summary>
    public string ActivityText => _isLiveState switch
    {
        true => string.IsNullOrEmpty(_liveTitle) ? "방송 중" : _liveTitle,
        false => "오프라인",
        null => "확인 중…",
    };

    public event PropertyChangedEventHandler? PropertyChanged;
    private void Notify(string name) => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
